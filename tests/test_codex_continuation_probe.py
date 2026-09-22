"""Passive native probe must not turn tool content into retained evidence."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROBE = Path(__file__).parents[1] / "dot_local/bin/executable_codex-continuation-probe"


def payload(event="PreToolUse"):
    return {
        "hook_event_name": event,
        "session_id": "session-public-fixture",
        "turn_id": "turn-public-fixture",
        "tool_use_id": "call-public-fixture",
        "model": "model-public-fixture",
        "permission_mode": "default",
        "tool_name": "Bash",
        "cwd": "/SECRET_WORKSPACE",
        "transcript_path": "/SECRET_TRANSCRIPT",
        "tool_input": {"command": "echo SECRET_ARGUMENT"},
        "tool_response": "SECRET_RESPONSE",
        "SECRET_FIELD_NAME": "SECRET_VALUE",
    }


def invoke(state, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    return subprocess.run(
        [sys.executable, str(PROBE), "--state", str(state)],
        input=raw, capture_output=True, timeout=5,
    )


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "probe"
    path.mkdir(mode=0o700)
    return path


def records(state):
    return [json.loads(p.read_text()) for p in state.glob("*.json")]


def test_sanitized_pre_post_pair(state):
    for event in ("PreToolUse", "PostToolUse"):
        result = invoke(state, payload(event))
        assert result.returncode == 0
        assert result.stdout == result.stderr == b""
    rows = records(state)
    assert len(rows) == 2
    assert {r["event"] for r in rows} == {"PreToolUse", "PostToolUse"}
    for name in ("session_id", "turn_id", "tool_use_id", "model"):
        digest = hashlib.sha256(payload()[name].encode()).hexdigest()
        assert {r[name + "_sha256"] for r in rows} == {digest}
    assert "SECRET" not in json.dumps(rows)
    assert "session-public-fixture" not in json.dumps(rows)
    assert {r["tool"] for r in rows} == {"Bash"}
    assert {r["authority"] for r in rows} == {"diagnostic_only"}
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in state.iterdir())


@pytest.mark.parametrize("raw", [b"{", b'{}', b'[]', b'\xff',
    b'{"session_id":"x","session_id":"y"}', b' ' * (1024 * 1024 + 1)], ids=['malformed', 'empty', 'array', 'utf8', 'duplicate', 'oversized'])
def test_invalid_input_retains_nothing_and_never_blocks(state, raw):
    result = invoke(state, raw)
    assert result.returncode == 0
    assert result.stdout == result.stderr == b""
    assert records(state) == []


@pytest.mark.parametrize("key,value", [
    ("session_id", "bad/path"), ("turn_id", True), ("model", "x" * 257),
    ("hook_event_name", "UNKNOWN_SECRET"), ("tool_use_id", "secret\nvalue"),
])
def test_invalid_metadata_refused(state, key, value):
    data = payload()
    data[key] = value
    assert invoke(state, data).returncode == 0
    assert not records(state)


def test_unknown_optional_fields_are_unavailable(state):
    data = {"hook_event_name": "SessionStart", "session_id": "session-public-fixture",
            "tool_name": "SECRET_TOOL", "permission_mode": "SECRET_MODE"}
    assert invoke(state, data).returncode == 0
    row, = records(state)
    assert row["tool"] == "other"
    assert row["permission_mode"] == "unavailable"
    assert row["turn_id_sha256"] is None
    assert row["model_sha256"] is None
    assert "SECRET" not in json.dumps(row)


def test_unsafe_state_or_symlink_refused(state, tmp_path):
    state.chmod(0o755)
    assert invoke(state, payload()).returncode == 0
    assert not records(state)
    state.chmod(0o700)
    link = tmp_path / "link"
    link.symlink_to(state, target_is_directory=True)
    assert invoke(link, payload()).returncode == 0
    assert not records(state)


def test_capacity_preserves_old_records(state):
    for i in range(256):
        (state / f"record-{i}.json").write_text("{}")
    before = {p.name: p.read_bytes() for p in state.glob("*.json")}
    assert invoke(state, payload()).returncode == 0
    assert {p.name: p.read_bytes() for p in state.glob("*.json")} == before


def test_lock_busy_refuses_without_waiting(state):
    import fcntl
    with (state / ".lock").open("w") as stream:
        os.chmod(stream.name, 0o600)
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert invoke(state, payload()).returncode == 0
    assert not records(state)


def test_linked_lock_never_mutates_target(state, tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"unchanged")
    (state / ".lock").symlink_to(target)
    assert invoke(state, payload()).returncode == 0
    assert target.read_bytes() == b"unchanged"
    assert not records(state)
