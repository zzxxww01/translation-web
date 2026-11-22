"""CLI 调本机翻译服务时不走环境变量里的代理。"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def test_cli_connects_to_local_service_without_env_proxy(monkeypatch):
    from src.cli._http import urlopen as cli_urlopen

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - http.server API
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # 指向一个不存在的代理：要是还走代理就会连不上
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    try:
        with cli_urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
            assert response.read() == b"ok"
    finally:
        server.shutdown()
        server.server_close()
