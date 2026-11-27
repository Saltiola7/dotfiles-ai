"""Offline checks of the Forgejo comparison wire contract."""

import hashlib
import io
import json
from pathlib import Path
import runpy
import socket
import stat
import struct
import subprocess
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENROLLMENT = "a" * 64
COMMIT = "b" * 40


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "dot_local/bin/executable_dbsctrctl"))


def test_endpoint_digest_binds_uid_and_exact_ref(helper):
    identity = {"provider": "forgejo", "origin": "https://forge.example.invalid",
                "repository": "example/repo"}
    args = (1000, identity, "fixture-reader", "refs/heads/main")
    expected = hashlib.sha256(
        b'[1000,"https://forge.example.invalid","example/repo","fixture-reader","refs/heads/main"]'
    ).hexdigest()
    digest = helper["_forgejo_broker_enrollment"]
    assert digest(*args) == expected
    assert digest(1001, *args[1:]) != expected
    assert digest(*args[:-1], "refs/heads/next") != expected


def response(**changes):
    value = {"version": 1, "enrollment": ENROLLMENT, "object_format": "sha1",
             "commit": COMMIT, "size": 4}
    return json.dumps(value | changes).encode() + b"\ndata"


def exchange(helper, wire, destination):
    left, right = socket.socketpair()
    with left, right:
        left.sendall(wire)
        left.shutdown(socket.SHUT_WR)
        return helper["_forgejo_broker_receive"](
            right, destination, ENROLLMENT, "sha1", time.monotonic() + 1
        )


def test_bounded_response_copies_exact_bytes(helper):
    output = io.BytesIO()
    assert exchange(helper, response(), output) == COMMIT
    assert output.getvalue() == b"data"


@pytest.mark.parametrize("wire", [
    response(enrollment="c" * 64), response(version=True), response(size=True),
    response(size=128 * 1024 * 1024 + 1), response(object_format="sha256"),
    response(commit="f" * 64), response(extra="unused"), response()[:-1],
    response() + b"extra", b"x" * 1024 + response(), b"",
    response().replace(b'"version": 1', b'"version": 1, "version": 1'),
])
def test_bad_response_cannot_return_a_commit(helper, wire):
    with pytest.raises(RuntimeError, match="Forgejo broker response unavailable"):
        exchange(helper, wire, io.BytesIO())


def test_expired_deadline_fails_without_reading(helper):
    left, right = socket.socketpair()
    with left, right, pytest.raises(RuntimeError, match="Forgejo broker response unavailable"):
        helper["_forgejo_broker_receive"](
            right, io.BytesIO(), ENROLLMENT, "sha1", time.monotonic() - 1
        )


def test_system_manager_credential_owner_and_acl(helper, monkeypatch):
    allowed = helper["_forgejo_broker_credential_mode"]
    uid = 1001
    raw = struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *entry) for entry in [
        (1, 4, 0xFFFFFFFF), (2, 4, uid), (4, 0, 0xFFFFFFFF),
        (16, 4, 0xFFFFFFFF), (32, 0, 0xFFFFFFFF),
    ])
    monkeypatch.setattr("os.getxattr", lambda _fd, _name: raw)
    details = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o440)
    assert allowed(3, details, uid)
    assert not allowed(3, details, uid + 1)
    fallback = SimpleNamespace(st_uid=uid, st_mode=stat.S_IFREG | 0o400)
    monkeypatch.setattr("os.fstatvfs", lambda _fd: SimpleNamespace(f_flag=0))
    assert not allowed(3, fallback, uid)
    monkeypatch.setattr("os.fstatvfs", lambda _fd: SimpleNamespace(f_flag=1))
    assert allowed(3, fallback, uid)


@pytest.mark.parametrize("mode", ["complete", "truncated", "race"])
def test_bundle_import_updates_only_comparison_ref(helper, tmp_path, monkeypatch, mode):
    source, client = tmp_path / "source", tmp_path / "client"
    identity = {"provider": "forgejo", "origin": "https://forge.example.invalid",
                "repository": "example/repo"}
    tracking = "refs/remotes/origin/main"

    def git(root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    for repo in (source, client):
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main", "--object-format=sha1")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--allow-empty", "-qm", "previous")
    old = git(source, "rev-parse", "HEAD")
    git(client, "fetch", "-q", str(source), f"refs/heads/main:{tracking}")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--allow-empty", "-qm", "next")
    new = git(source, "rev-parse", "HEAD")
    fixture = tmp_path / "fixture.bundle"
    git(source, "bundle", "create", str(fixture), "refs/heads/main")
    git(client, "remote", "add", "origin", identity["origin"] + "/example/repo.git")

    def deliver(_enrollment, path, object_format, _deadline):
        assert object_format == "sha1"
        payload = fixture.read_bytes()
        path.write_bytes(payload[:-12] if mode == "truncated" else payload)
        if mode == "race":
            git(client, "update-ref", "-d", tracking, old)
        return new

    fetch = helper["fetch_forgejo_branch"]
    monkeypatch.setitem(fetch.__globals__, "_forgejo_broker_request", deliver)
    if mode == "complete":
        assert fetch(client, "origin", identity, "main", "fixture-reader", "systemd-broker") == new
        assert git(client, "rev-parse", tracking) == new
        assert git(client, "rev-parse", f"{tracking}^") == old
    elif mode == "truncated":
        with pytest.raises(RuntimeError, match="Forgejo broker comparison import unavailable"):
            fetch(client, "origin", identity, "main", "fixture-reader", "systemd-broker")
        assert git(client, "rev-parse", tracking) == old
    else:
        with pytest.raises(RuntimeError, match="Forgejo comparison ref changed"):
            fetch(client, "origin", identity, "main", "fixture-reader", "systemd-broker")
        assert git(client, "for-each-ref", "--format=%(refname)", tracking) == ""
    assert git(client, "for-each-ref", "--format=%(refname)", "refs/dbsctr-fetch") == ""


def test_server_reply_round_trips_native_bundle(helper, tmp_path, monkeypatch):
    reply = helper["_forgejo_broker_reply"]
    receiver = helper["_forgejo_broker_receive"]
    identity = {"provider": "forgejo", "origin": "https://forge.example.invalid",
                "repository": "example/repo"}
    result = []

    def fetch_fixture(root, remote, supplied, branch, account, source, *, broker):
        assert (remote, supplied, branch, account, source, broker) == (
            "origin", identity, "main", "fixture-reader", "systemd", True)
        def plumbing(*args, data):
            return subprocess.check_output(
                ["git", "-C", str(root), "-c", "user.name=Fixture",
                 "-c", "user.email=fixture@example.invalid", *args], input=data, text=True
            ).strip()

        tree = plumbing("mktree", data="")
        commit = plumbing("commit-tree", tree, data="fixture\n")
        result.append(commit)
        return commit

    monkeypatch.setitem(reply.__globals__, "_fetch_forgejo_branch", fetch_fixture)
    sender, client = socket.socketpair()
    # Small fixture bundle fits in the socket buffer; sending synchronously
    # avoids a test-only thread lifetime or timing dependency.
    with sender:
        reply(sender, ENROLLMENT, identity, {"branch": "main", "account": "fixture-reader",
                                             "object_format": "sha1"},
              "refs/heads/main", time.monotonic() + 5)
    bundle = tmp_path / "received.bundle"
    with client, bundle.open("xb") as output:
        assert receiver(client, output, ENROLLMENT, "sha1", time.monotonic() + 5) == result[0]
    assert subprocess.check_output(["git", "bundle", "list-heads", str(bundle)], text=True).strip() == (
        f"{result[0]} refs/heads/main")
