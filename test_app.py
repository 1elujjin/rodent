import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from app import index_data, search_records, make_handler


class SearchTests(unittest.TestCase):
    def setUp(self):
        (Path(__file__).parent/'.local').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent/'.local')
        self.root = Path(self.tmp.name)
        self.data = self.root/'data'
        self.data.mkdir()
        self.db = self.root/'index.db'
        rows = [dict(title=f'Observation {i}', nested={'type':'optics'}, literal='<script>alert(1)</script>') for i in range(45)]
        (self.data/'a.jsonl').write_text('\n'.join(map(json.dumps, rows))+'\ninvalid\n', encoding='utf-8')
        (self.data/'b.jsonl').write_text('123\n["other", "shape"]\n', encoding='utf-8')
        self.stats = index_data(self.data, self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dynamic_import_and_pagination(self):
        self.assertEqual(self.stats['records'],47)
        self.assertIn('nested.type',self.stats['fields'])
        self.assertEqual(len(self.stats['warnings']),1)
        found=search_records(self.db,'OPTICS',page=3)
        self.assertEqual(found['total'],45)
        self.assertEqual(len(found['results']),5)
        self.assertEqual(search_records(self.db,source='b.jsonl')['total'],2)
        self.assertEqual(search_records(self.db,'Observation 17')['total'],1)
        self.assertEqual(search_records(self.db,'" OR "')['total'],0)

    def test_rebuild_removes_deleted_records(self):
        (self.data/'b.jsonl').unlink()
        index_data(self.data,self.db)
        self.assertEqual(search_records(self.db)['total'],45)

    def test_http_boundaries(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.db,0))
        port=server.server_port
        server.RequestHandlerClass=make_handler(self.db,port)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base=f'http://127.0.0.1:{port}'
        try:
            with urllib.request.urlopen(base+'/api/search?q=optics') as response:
                self.assertEqual(json.load(response)['total'],45)
                self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
            with urllib.request.urlopen(base+'/') as response:
                self.assertIn(b'Data search',response.read())
            for path,headers in [('/',{'Host':'evil.example'}),('/api/stats',{'Sec-Fetch-Site':'cross-site'}),('/../app.py',{})]:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base+path,headers=headers))
                self.assertIn(error.exception.code,[403,404])
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    (Path(__file__).parent/'.local').mkdir(exist_ok=True)
    unittest.main()

