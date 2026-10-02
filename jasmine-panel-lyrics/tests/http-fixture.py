"""Local-only HTTP fixture for the isolated GNOME Shell test."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

root = Path(sys.argv[1])


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        song_id = parse_qs(url.query).get('id', [''])[0]
        text = (root / 'remote.lrc').read_text() if song_id == '123' else ''
        payload = json.dumps({'code': 200, 'lrc': {'lyric': text}}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


server = HTTPServer(('127.0.0.1', 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
