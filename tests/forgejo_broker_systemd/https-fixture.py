import base64
import http.server
from pathlib import Path
import ssl
import subprocess
import urllib.parse


class GitFixture(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_GET(self):
        self.serve_git()

    def do_POST(self):
        self.serve_git()

    def serve_git(self):
        target = urllib.parse.urlsplit(self.path)
        if target.path not in ("/example/repo.git/info/refs", "/example/repo.git/git-upload-pack"):
            self.send_error(404)
            return
        scheme, _, encoded = self.headers.get("Authorization", "").partition(" ")
        matched = scheme.lower() == "basic" and encoded == base64.b64encode(b"reader:dummy-native-fixture").decode()
        if not matched:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        headers, _, body = subprocess.check_output(
            ["/usr/lib/git-core/git-http-backend"], input=data, timeout=5,
            env={"PATH": "/usr/bin:/bin", "GIT_PROJECT_ROOT": "/opt/git-fixture",
                 "GIT_HTTP_EXPORT_ALL": "1", "PATH_INFO": target.path,
                 "QUERY_STRING": target.query, "REQUEST_METHOD": self.command,
                 "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                 "CONTENT_LENGTH": str(len(data)),
                 "HTTP_GIT_PROTOCOL": self.headers.get("Git-Protocol", "")},
        ).partition(b"\r\n\r\n")
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        for line in headers.decode().splitlines():
            if ":" in line:
                name, value = line.split(":", 1)
                if name != "Status":
                    self.send_header(name, value.strip())
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 18443), GitFixture)
tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain("/opt/git-fixture/cert.pem", "/opt/git-fixture/key.pem")
server.socket = tls.wrap_socket(server.socket, server_side=True)
Path("/opt/git-fixture/ready").touch()
server.serve_forever()
