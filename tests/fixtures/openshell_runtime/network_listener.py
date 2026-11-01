"""Bounded synthetic HTTP listener; never serves files or forwards requests."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import selectors
import socket
import socketserver
import stat
import time


BODY = b"openshell-network-probe\n"
HEADER = "x-qualification-case"
TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
MAX_RECORD_BYTES = 65536
MAX_RECORDS = 256


class RecordWriter:
    def __init__(self, fd: int):
        self.fd = fd
        self.records = 0
        self.max_records = MAX_RECORDS

    def append(self, value: dict) -> None:
        raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        info = os.fstat(self.fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600
                or self.records >= self.max_records or info.st_size + len(raw) > MAX_RECORD_BYTES):
            raise ValueError("listener_record_limit")
        offset = 0
        while offset < len(raw):
            written = os.write(self.fd, raw[offset:])
            if written <= 0:
                raise OSError("listener_record_write")
            offset += written
        os.fsync(self.fd)
        self.records += 1


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(2)
        data = bytearray()
        while b"\r\n\r\n" not in data and len(data) <= 8192:
            chunk = self.request.recv(min(1024, 8193 - len(data)))
            if not chunk:
                return
            data.extend(chunk)
        if len(data) > 8192 or b"\r\n\r\n" not in data:
            return
        try:
            text = bytes(data).split(b"\r\n\r\n", 1)[0].decode("ascii")
            lines = text.split("\r\n")
            method, target, version = lines[0].split(" ")
            headers = {}
            for line in lines[1:]:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                if not key or key in headers:
                    raise ValueError()
                headers[key] = value.strip()
            token = headers.get(HEADER, "")
            if TOKEN.fullmatch(token) is None:
                token = ""
            accepted = (method == "GET" and target == "/probe" and version == "HTTP/1.1"
                        and bool(token) and "upgrade" not in headers
                        and "upgrade" not in headers.get("connection", "").lower()
                        and "transfer-encoding" not in headers
                        and headers.get("content-length", "0") == "0")
            event = {"schema_version": 1, "token": token, "port": self.server.server_address[1],
                     "method": method if method in {"GET", "POST", "HEAD", "OPTIONS", "CONNECT"} else "OTHER",
                     "path": "/probe" if target == "/probe" else "other", "accepted": accepted}
        except (UnicodeError, ValueError):
            return
        self.server.writer.append(event)
        status, body = ("200 OK", BODY) if accepted else ("403 Forbidden", b"fixture-rejected\n")
        response = (f"HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\n"
                    "Content-Type: text/plain\r\nConnection: close\r\n\r\n").encode() + body
        self.request.sendall(response)


class ListenerServer(socketserver.TCPServer):
    """Internal ephemeral-address seam for local tests; CLI fixes production scope."""

    allow_reuse_address = False
    request_queue_size = 4

    def __init__(self, address: tuple[str, int], record_fd: int | RecordWriter):
        self.writer = record_fd if isinstance(record_fd, RecordWriter) else RecordWriter(record_fd)
        self.failed = False
        super().__init__(address, _Handler)

    def handle_error(self, request, client_address) -> None:
        # Never print request data, tracebacks or private paths.
        self.failed = True

    def verify_request(self, request, client_address) -> bool:
        return not self.failed


def serve(address: str, record_directory: Path, deadline: float) -> None:
    """Serve only the two reviewed ports until the bounded deadline or first error."""
    info = record_directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or record_directory.resolve() != record_directory):
        raise ValueError("listener_record_directory")
    fd = os.open(record_directory / "events.jsonl",
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_APPEND, 0o600)
    servers = []
    try:
        writer = RecordWriter(fd)
        with selectors.DefaultSelector() as selector:
            for port in (18080, 18081):
                server = ListenerServer((address, port), writer)
                servers.append(server)
                selector.register(server, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                for key, _ in selector.select(min(0.5, max(0, deadline - time.monotonic()))):
                    key.fileobj._handle_request_noblock()
                    if key.fileobj.failed:
                        raise ValueError("listener_request_failed")
    finally:
        for server in servers:
            server.server_close()
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True)
    parser.add_argument("--seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        address = ipaddress.IPv4Address(args.address)
        private = any(address in ipaddress.IPv4Network(value) for value in
                      ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
        if str(address) != args.address or not private or not 0 < args.seconds <= 1800:
            raise ValueError("listener_scope")
        home = Path.home().resolve(strict=True)
        parent = home / "openshell-qualification"
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("listener_record_directory")
        serve(str(address), parent / "network-records", time.monotonic() + args.seconds)
    except (OSError, ValueError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
