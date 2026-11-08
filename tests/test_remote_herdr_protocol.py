"""Pinned core protocol contracts; fake Unix peers only, never a live core."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct

import pytest

ROOT = Path(__file__).parents[1]


def module():
    path = ROOT / 'dot_local/share/dotfiles-ai/remote-herdr/protocol.py'
    spec = importlib.util.spec_from_file_location('remote_core_protocol', path)
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Peer:
    def __init__(self, answers):
        self.answers = b''.join(json.dumps(value).encode() + b'\n' for value in answers)
        self.sent = []

    def sendall(self, value):
        self.sent.append(json.loads(value))

    def recv(self, limit):
        result, self.answers = self.answers[:limit], self.answers[limit:]
        return result


def hello(version='0.1.18'):
    return {'jsonrpc': '2.0', 'id': 1, 'result': {
        'version': version, 'generation': 1, 'framed': False,
        'core': {'id': 'fixture-core', 'name': 'fixture'},
        'methods': ['doc.get', 'doc.set', 'terminal.list'], 'features': []}}


def test_plain_rpc_requires_pinned_hello_and_matching_request():
    core = module()
    peer = Peer([hello(), {'jsonrpc': '2.0', 'id': 2, 'result': {'version': 0, 'value': None}}])
    assert core.exchange(peer, 'doc.get', {'name': 'herdr-app'}) == {'version': 0, 'value': None}
    assert peer.sent[0]['method'] == 'hello' and peer.sent[0]['params']['framed'] is False
    assert peer.sent[1]['method'] == 'doc.get'


@pytest.mark.parametrize('fault', ['version', 'generation', 'id', 'error', 'eof'])
def test_uncertain_or_incompatible_peer_never_leaks_response(fault):
    core = module()
    first = hello('99.0.0' if fault == 'version' else '0.1.18')
    if fault == 'generation':
        first['result']['generation'] = 2
    second = {'jsonrpc': '2.0', 'id': 3 if fault == 'id' else 2,
              'result': {'value': 'private-session-or-path'}}
    if fault == 'error':
        second = {'jsonrpc': '2.0', 'id': 2, 'error': {'message': 'private-session-or-path'}}
    peer = Peer([first] if fault == 'eof' else [first, second])
    with pytest.raises(core.CoreProtocolError) as captured:
        core.exchange(peer, 'doc.get', {'name': 'herdr-app'})
    assert 'private' not in str(captured.value)


def test_mutations_are_not_retried_after_unknown_outcome():
    core = module()
    peer = Peer([hello()])
    with pytest.raises(core.CoreProtocolError):
        core.exchange(peer, 'doc.set', {'name': 'herdr-app', 'version': 0, 'value': {'spaces': []}})
    assert sum(item['method'] == 'doc.set' for item in peer.sent) == 1


def test_private_json_refuses_duplicates_and_oversize():
    core = module()
    with pytest.raises(core.CoreProtocolError):
        core.decode(b'{"id":1,"id":2}')
    with pytest.raises(core.CoreProtocolError):
        core.decode(b' ' * (core.MAX_MESSAGE + 1))


@pytest.mark.parametrize('mode', [0o600, 0o700, 0o755, 0o770, 0o777])
def test_linux_socket_permissions_follow_connect_write_access(tmp_path, monkeypatch, mode):
    core = module()
    endpoint = tmp_path.resolve() / 'core.sock'
    monkeypatch.chdir(tmp_path)
    # Only a synthetic local socket inode; never contact a native runtime.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as inode:
        inode.bind(endpoint.name)
        endpoint.chmod(mode)
        connections = []
        class FakePeer:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def settimeout(self, value):
                pass
            def connect(self, value):
                connections.append(value)
            def getsockopt(self, *args):
                return struct.pack('3i', 123, os.getuid(), os.getgid())
        monkeypatch.setattr(core.socket, 'SO_PEERCRED', 17, raising=False)
        monkeypatch.setattr(core.socket, 'socket', lambda *args: FakePeer())
        monkeypatch.setattr(core, 'exchange', lambda *args: {'observed': True})
        if mode & 0o022:
            with pytest.raises(core.CoreProtocolError):
                core.request(endpoint, 'server.status', {})
            assert not connections
        else:
            assert core.request(endpoint, 'server.status', {}) == {'observed': True}
