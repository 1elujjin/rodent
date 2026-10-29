# Data search

A local JSONL explorer with a minimal black interface, SQLite FTS5 search, dataset filtering, 20-record pagination, and full JSON record details. Includes only fictional project/equipment examples. No packages, build step, cloud service, or internet connection required.

## Start

Install Python 3.10 or newer with SQLite FTS5 enabled (standard python.org builds include it). Open a terminal in this project folder:

```powershell
py app.py
```

On macOS/Linux, use `python3 app.py`. Open **http://127.0.0.1:8765**. Stop with Ctrl+C.

To search your own authorized local datasets:

```powershell
py app.py --data "C:\path\to\datasets"
```

The server recursively scans `.jsonl` files at startup. Each nonblank line must be one UTF-8 JSON value. Different fields, nested objects, arrays, and scalar records are supported. Source file names and original line numbers appear in results. Symlinks resolving outside the configured folder are skipped. Invalid JSON, encoding errors, and lines larger than 8 MiB are skipped; inspect the first 100 warnings in the interface. Startup fails if a file cannot be read, preserving the previous complete index.

Add, edit, or remove dataset files, then restart to rebuild the index. There is no automatic file watcher. Rebuilding is transactional; running readers see a complete index. Do not run multiple server instances against the same database. Startup rebuilds the complete index, so large collections need time and free disk space.

## Search

Search matches all entered words across field names and values, regardless of case. SQLite's Unicode word tokenizer handles punctuation; a multiword quoted input is treated as ordinary text rather than an advanced query language. This is word search, not arbitrary substring, fuzzy, or wildcard search. Results are ranked by FTS5 relevance. Empty search browses all records. Select a dataset to narrow results. Press `/` to focus search and Escape to close record details. The field inspector lists fields discovered across the collection; result cards preview four fields, while View Record shows the complete JSON.

## Options

```powershell
py app.py --data "C:\datasets" --port 9000 --db ".local\custom.sqlite3"
py app.py --data "C:\datasets" --index-only
py -m unittest -v
```

The default dataset is `data/` beside the application; the default index is `.local/index.sqlite3`. Both defaults are independent of your terminal's current folder. Custom relative paths resolve from the terminal's current folder. If Python reports `no such module: fts5`, use a Python installation built with FTS5 support. If the port is busy, choose another using `--port`.

## Local privacy

The app binds to `127.0.0.1` only. It sends no analytics, uses no external fonts/scripts, offers no publication/upload feature, checks the Host header against the chosen local port, and blocks cross-site browser requests. Dataset content is inserted into the page as text, never HTML. Dataset paths cannot be requested through the static server. Request URLs and search terms are not logged.

Use datasets you are authorized to process. Keep this tool local; do not expose it through port forwarding, tunnels, proxies, or public hosting. There is no login: other users or programs with access to your computer can access it. The SQLite index contains a full plaintext copy of indexed data. Keep the data folder and `.local/` private and outside shared/synced folders when needed. To remove indexed copies, stop the app and delete `.local/` (including SQLite WAL/SHM files). This does not delete the source datasets. The ignore file excludes custom datasets and index files from Git by default, but it is not an access-control mechanism.

The centered text logo can be edited in static/index.html. Results preview four fields beneath the title; Details shows the complete record.



The crosshair cursor is applied throughout. Snowfall and an original white pixel rat are drawn locally on a non-interactive canvas. The rat follows mouse movement on devices with a fine pointer. Use the checkbox below the results to disable both effects. Effects start enabled; the checkbox turns them off. The pure-white side-view rat follows at the display animation rate with a four-frame running cycle and square pixels.


