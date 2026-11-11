"""Bounded plain JSON-RPC for pinned core 0.1.18; never auto-start a runtime."""
import json
import os
from pathlib import Path
import socket
import stat
import struct
from typing import Protocol

MAX_MESSAGE = 2 * 1024 * 1024
METHODS = frozenset({'server.status', 'server.stop', 'terminal.list', 'terminal.get',
                     'terminal.run', 'terminal.kill', 'doc.get', 'doc.set'})


class CoreProtocolError(ValueError):
    """Only source-literal diagnostics may cross the private RPC boundary."""


class Peer(Protocol):
    def sendall(self, data: bytes, /) -> object: ...
    def recv(self, size: int, /) -> bytes: ...


def unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CoreProtocolError('core structured response invalid')
        result[key] = value
    return result


def decode(raw: bytes) -> dict:
    if len(raw) > MAX_MESSAGE:
        raise CoreProtocolError('core response exceeds bound')
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise CoreProtocolError('core structured response invalid') from None
    if not isinstance(value, dict):
        raise CoreProtocolError('core structured response invalid')
    return value


def exchange(peer: Peer, method: str, params: dict) -> dict:
    """One hello and one request; a failed mutation is never blindly retried."""
    if method not in METHODS or not isinstance(params, dict):
        raise CoreProtocolError('core request invalid')
    pending = b''

    def call(number: int, name: str, arguments: dict) -> dict:
        nonlocal pending
        try:
            outgoing = json.dumps({'jsonrpc': '2.0', 'id': number, 'method': name,
                                   'params': arguments}, allow_nan=False).encode() + b'\n'
            if len(outgoing) > MAX_MESSAGE:
                raise CoreProtocolError('core request exceeds bound')
            peer.sendall(outgoing)
            while b'\n' not in pending:
                part = peer.recv(min(65536, MAX_MESSAGE + 1 - len(pending)))
                if not part:
                    raise CoreProtocolError('core request outcome uncertain')
                pending += part
                if len(pending) > MAX_MESSAGE:
                    raise CoreProtocolError('core response exceeds bound')
            raw, pending = pending.split(b'\n', 1)
            answer = decode(raw)
        except CoreProtocolError:
            raise
        except (OSError, TypeError, ValueError, OverflowError, RecursionError):
            raise CoreProtocolError('core request outcome uncertain') from None
        if (answer.get('jsonrpc') != '2.0' or type(answer.get('id')) is not int
                or answer['id'] != number or 'error' in answer or not isinstance(answer.get('result'), dict)):
            raise CoreProtocolError('core response refused or invalid')
        return answer['result']

    hello = call(1, 'hello', {'framed': False})
    if (hello.get('version') != '0.1.18' or type(hello.get('generation')) is not int
            or hello['generation'] != 1 or hello.get('framed') is not False
            or not isinstance(hello.get('methods'), list) or method not in hello['methods']):
        raise CoreProtocolError('core version or protocol incompatible')
    return call(2, method, params)


def request(endpoint: Path, method: str, params: dict) -> dict:
    """Connect only to an existing owned endpoint; no CLI startup side effect."""
    try:
        for parent in (endpoint.parent, *endpoint.parent.parents):
            info = parent.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}
                    or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                raise CoreProtocolError('core endpoint unsafe')
        info = endpoint.lstat()
        # Linux pathname sockets require write permission to connect. Native
        # transient units use their own umask; read/execute bits grant no access.
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise CoreProtocolError('core endpoint unsafe')
        if not hasattr(socket, 'SO_PEERCRED'):
            raise CoreProtocolError('core peer identity unavailable')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(30)
            peer.connect(str(endpoint))
            _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise CoreProtocolError('core peer identity mismatch')
            return exchange(peer, method, params)
    except OSError:
        raise CoreProtocolError('core endpoint unavailable or outcome uncertain') from None
