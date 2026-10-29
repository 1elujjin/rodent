"""Local JSONL search. Python 3.10+, standard library only."""
import argparse
import json
import math
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
MAX_LINE = 8 * 1024 * 1024


def connect(db):
    con = sqlite3.connect(db, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item, prefix + "[]")
    else:
        yield prefix or "value", str(value) if value is not None else "null"


def index_data(folder, db):
    """Build in one transaction: readers keep the last complete index on failure."""
    folder = folder.resolve(strict=True)
    if not folder.is_dir():
        raise ValueError("Dataset path must be a directory")
    con = connect(db)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        with con:
            con.execute("CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, source TEXT, line INTEGER, raw TEXT)")
            con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(body, tokenize='unicode61 remove_diacritics 2')")
            con.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
            con.execute("DELETE FROM records")
            con.execute("DELETE FROM search")
            fields, sources, errors, count = set(), [], [], 0
            for path in sorted(folder.rglob("*.jsonl")):
                if not path.is_file() or not path.resolve().is_relative_to(folder):
                    continue
                source = path.relative_to(folder).as_posix()
                sources.append(source)
                with path.open("rb") as stream:
                    number = 0
                    while True:
                        line = stream.readline(MAX_LINE + 1)
                        if not line:
                            break
                        number += 1
                        oversized = len(line) > MAX_LINE
                        if oversized:
                            while line and not line.endswith(b"\n"):
                                line = stream.readline(MAX_LINE + 1)
                        elif not line.strip():
                            continue
                        try:
                            if oversized:
                                raise ValueError("line exceeds 8 MiB")
                            value = json.loads(line.decode("utf-8-sig"))
                            pairs = list(flatten(value))
                        except (ValueError, UnicodeError, RecursionError) as exc:
                            if len(errors) < 100:
                                errors.append(f"{source}:{number}: {str(exc)[:160]}")
                            continue
                        fields.update(k for k, _ in pairs)
                        cur = con.execute("INSERT INTO records(source,line,raw) VALUES(?,?,?)", (source, number, json.dumps(value, ensure_ascii=False)))
                        con.execute("INSERT INTO search(rowid,body) VALUES(?,?)", (cur.lastrowid, "\n".join(k + " " + v for k, v in pairs)))
                        count += 1
            stats = dict(records=count, sources=sources, fields=sorted(fields), warnings=errors)
            con.execute("INSERT OR REPLACE INTO meta VALUES('stats',?)", (json.dumps(stats),))
        return stats
    finally:
        con.close()


def search_records(db, query="", source="", page=1, size=20):
    # Quote each token: user input is literal text, never SQL or FTS syntax.
    terms = query.split()
    expression = " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)
    with closing(connect(db)) as con:
        clauses, args = [], []
        join = " JOIN search ON search.rowid=r.id" if expression else ""
        if expression:
            clauses.append("search MATCH ?")
            args.append(expression)
        if source:
            clauses.append("r.source=?")
            args.append(source)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = con.execute("SELECT count(*) FROM records r" + join + where, args).fetchone()[0]
        pages = max(1, math.ceil(total / size))
        page = min(max(page, 1), pages)
        order = "bm25(search),r.id" if expression else "r.id"
        rows = con.execute("SELECT r.* FROM records r" + join + where + " ORDER BY " + order + " LIMIT ? OFFSET ?", args + [size, (page-1)*size]).fetchall()
        return dict(total=total, page=page, pages=pages, results=[dict(id=r['id'], source=r['source'], line=r['line'], data=json.loads(r['raw'])) for r in rows])


def make_handler(db, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Queries and record contents stay out of request logs.

        def send(self, status, body, kind="application/json; charset=utf-8"):
            payload = json.dumps(body).encode() if not isinstance(body, bytes) else body
            self.send_response(status)
            for k, v in {"Content-Type":kind, "Content-Length":str(len(payload)), "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff", "Referrer-Policy":"no-referrer", "Content-Security-Policy":"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            # Exact Host allowlist blocks DNS rebinding. No CORS; only loopback bind.
            if self.headers.get('Host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
                return self.send(403, {"error":"Invalid local host"})
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.send(403, {"error":"Cross-site access denied"})
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == '/api/stats':
                    with closing(connect(db)) as con:
                        return self.send(200, json.loads(con.execute("SELECT value FROM meta WHERE key='stats'").fetchone()[0]))
                if url.path == '/api/search':
                    query = params.get('q', [''])[0]
                    if len(query) > 500 or len(query.split()) > 30:
                        return self.send(400, {"error":"Use at most 500 characters and 30 words"})
                    return self.send(200, search_records(db, query, params.get('source', [''])[0], int(params.get('page', ['1'])[0])))
                files = {'/':('index.html','text/html'), '/app.js':('app.js','text/javascript'), '/style.css':('style.css','text/css')}
                if url.path in files:
                    name, mime = files[url.path]
                    return self.send(200, (ROOT/'static'/name).read_bytes(), mime + '; charset=utf-8')
                self.send(404, {"error":"Not found"})
            except (ValueError, sqlite3.Error):
                self.send(400, {"error":"Unable to process query"})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'data')
    parser.add_argument('--db', type=Path, default=ROOT/'.local'/'index.sqlite3')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--index-only', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    args.db.parent.mkdir(parents=True, exist_ok=True)
    stats = index_data(args.data, args.db)
    print(f"Indexed {stats['records']} records in {len(stats['sources'])} files; {len(stats['warnings'])} warnings (capped at 100).", flush=True)
    if args.index_only:
        return
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(args.db, args.port))
    print(f'Open http://127.0.0.1:{args.port} — Ctrl+C to stop', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
