# service.py
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from gost_precheck.core.config import load_all
from gost_precheck.core.engine import analyze_file

HOST = "127.0.0.1"
PORT = 8765

def _json(obj, code=200):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return code, [("Content-Type","application/json; charset=utf-8"),
                  ("Content-Length", str(len(data)))], data

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # потише
        pass

    def do_GET(self):
        try:
            if self.path.startswith("/health"):
                code, hdrs, data = _json({"ok": True, "version": "service-1"})
            else:
                code, hdrs, data = _json({"error": "not_found"}, 404)
        except Exception as e:
            code, hdrs, data = _json({"error": str(e)}, 500)
        self.send_response(code); [self.send_header(k,v) for k,v in hdrs]; self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        try:
            if self.path.startswith("/analyze"):
                length = int(self.headers.get("Content-Length","0"))
                raw = self.rfile.read(length)
                req = json.loads(raw.decode("utf-8") or "{}")
                path = req.get("path")
                cfg_root = req.get("config")
                if not path or not os.path.exists(path):
                    code, hdrs, data = _json({"error":"file_not_found"}, 400)
                else:
                    cfg = load_all(cfg_root)
                    issues, by_cat, debug_meta = analyze_file(path, cfg)
                    result = {
                        "file": path,
                        "by_category": by_cat,
                        "issues": [i.to_dict() for i in issues],
                        "debug": debug_meta,
                    }
                    code, hdrs, data = _json(result, 200)
            else:
                code, hdrs, data = _json({"error": "not_found"}, 404)
        except Exception as e:
            code, hdrs, data = _json({"error": str(e)}, 500)
        self.send_response(code); [self.send_header(k,v) for k,v in hdrs]; self.end_headers(); self.wfile.write(data)

def main():
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"[svc] listening on http://{HOST}:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
