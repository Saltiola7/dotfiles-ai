import hashlib
import fcntl
import json
import os
import runpy
import stat
import subprocess
import sys
import time
import threading
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
CONTROL = ROOT / "dot_local/bin/executable_codex-control-plane"
MANAGED = ROOT / "private_dot_config/dotfiles-ai/codex-managed"
EVENTS = ("SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "Stop")


def run_control(*args: str, stdin: bytes = b"", env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(CONTROL), *args],
        input=stdin,
        capture_output=True,
        env={**os.environ, **(env or {})},
        timeout=10,
    )


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True, check=True
    ).stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    (root / "tracked").write_text("initial\n")
    git(root, "add", "tracked")
    git(root, "commit", "-m", "initial")
    return root


def payload(cwd: Path, event: str = "SessionStart") -> dict:
    value = {
        "session_id": "session-1",
        "transcript_path": "/path/that/does/not/exist.jsonl",
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    if event in {"SubagentStart", "SubagentStop", "Stop"}:
        value["turn_id"] = "turn-1"
    if event in {"SessionStart", "SubagentStart", "SubagentStop", "Stop"}:
        value["model"] = "gpt-5.6-sol"
    return value


def records(state_root: Path) -> list[dict]:
    directory = state_root / "codex-hooks"
    return [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))]


def fake_dbsctrctl(directory: Path, cycle_id: str, worktree_id: str, state: str = "active") -> None:
    executable = directory / "dbsctrctl"
    executable.write_text(
        "#!/bin/sh\n"
        "cat <<'JSON'\n"
        + json.dumps({
            "cycle_id": cycle_id,
            "state": state,
            "git": {"branch": "cycle"},
            "worktree": {"id": worktree_id},
        })
        + "\nJSON\n"
    )
    executable.chmod(0o755)


def test_managed_config_has_only_five_inline_identity_hooks() -> None:
    config = tomllib.loads((MANAGED / "config.toml").read_text())

    assert set(config) == {"hooks"}
    assert set(config["hooks"]) == set(EVENTS)
    for event in EVENTS:
        assert config["hooks"][event] == [{
            "hooks": [{
                "type": "command",
                "command": f"codex-control-plane hook {event}",
                "timeout": 5,
            }]
        }]


def test_managed_roles_are_minimal_and_inherit_model_and_provider() -> None:
    roles = {
        path.stem: tomllib.loads(path.read_text())
        for path in (MANAGED / "agents").rglob("*.toml")
    }

    assert set(roles) == {"build", "discovery", "plan", "review", "explore", "scout"}
    for name, role in roles.items():
        assert role["name"] == name
        assert role["description"]
        assert role["developer_instructions"]
        assert "model" not in role
        assert "provider" not in role
        assert "/" not in json.dumps(role)
    assert roles["build"]["sandbox_mode"] == "workspace-write"
    assert roles["discovery"]["sandbox_mode"] == "workspace-write"
    assert roles["build"]["sandbox_workspace_write"]["network_access"] is False
    assert roles["discovery"]["sandbox_workspace_write"]["network_access"] is False
    assert set(roles["build"]) == {
        "name", "description", "developer_instructions", "sandbox_mode",
        "sandbox_workspace_write",
    }
    assert set(roles["discovery"]) == set(roles["build"])
    for name in ("plan", "review", "explore", "scout"):
        assert roles[name]["sandbox_mode"] == "read-only"
        assert set(roles[name]) == {
            "name", "description", "developer_instructions", "sandbox_mode",
        }


def test_valid_hook_writes_only_private_normalized_identity(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    raw = json.dumps(payload(repo)).encode()

    result = run_control(
        "hook", "SessionStart", stdin=raw, env={"DBSCTR_STATE_ROOT": str(state_root)}
    )

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    directory = state_root / "codex-hooks"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    paths = list(directory.glob("*.json"))
    assert len(paths) == 1
    assert stat.S_IMODE(paths[0].stat().st_mode) == 0o600
    record = json.loads(paths[0].read_text())
    assert record["result"] == "accepted"
    assert record["record"] == {
        "schema_version": 1,
        "adapter_revision": "codex-adapter-1",
        "event": "SessionStart",
        "session_id": "session-1",
        "model_id": "gpt-5.6-sol",
        "workspace": "primary_worktree",
        "observed_at": record["record"]["observed_at"],
    }
    serialized = json.dumps(record)
    assert str(repo) not in serialized
    assert "transcript" not in serialized


@pytest.mark.parametrize("event", EVENTS)
def test_each_identity_hook_accepts_only_its_content_free_shape(
    tmp_path: Path, event: str
) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"

    result = run_control(
        "hook", event, stdin=json.dumps(payload(repo, event)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert result.returncode == 0
    record = records(state_root)[0]
    assert record["result"] == "accepted"
    assert record["record"]["event"] == event
    assert "transcript" not in json.dumps(record)


@pytest.mark.parametrize(
    ("event", "raw", "failure"),
    [
        ("SessionStart", b'{"session_id":"one","session_id":"two"}', "invalid_json"),
        ("SessionStart", b"\xff", "invalid_utf8"),
        ("SessionStart", b"{" + b"x" * 65536 + b"}", "input_too_large"),
        ("SessionStart", b'{"unknown":"value"}', "unknown_field"),
        ("SessionStart", b'{"transcript_path":null}', "missing_field"),
        ("Stop", b'{"last_assistant_message":"private"}', "content_field"),
        ("SubagentStop", b'{"agent_transcript_path":"/private"}', "path_field"),
    ],
)
def test_hook_rejects_unsafe_input_without_becoming_execution_authority(
    tmp_path: Path, event: str, raw: bytes, failure: str
) -> None:
    state_root = tmp_path / "state"

    result = run_control("hook", event, stdin=raw, env={"DBSCTR_STATE_ROOT": str(state_root)})

    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    assert records(state_root) == [{
        "schema_version": 1,
        "adapter_revision": "codex-adapter-1",
        "result": "rejected",
        "failure": failure,
        "observed_at": records(state_root)[0]["observed_at"],
        "expires_at": records(state_root)[0]["expires_at"],
    }]


def test_hook_rejects_del_and_c1_controls_in_transient_paths(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    value = payload(repo)
    value["transcript_path"] = "/private/\u007f\u0085"

    run_control(
        "hook", "SessionStart", stdin=json.dumps(value).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert records(state_root)[0]["failure"] == "invalid_transcript_path"


def test_hook_classifies_active_cycle_and_unknown_workspaces(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-b", "cycle", str(linked))
    root_commit = git(repo, "rev-list", "--max-parents=0", "HEAD")
    worktree_id = hashlib.sha256(f"{root_commit}\0cycle".encode()).hexdigest()[:16]
    active = repo / ".git/dbsctr/worktrees" / worktree_id / "active"
    active.parent.mkdir(parents=True)
    active.write_text("test-cycle\n")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_dbsctrctl(fake_bin, "test-cycle", worktree_id)
    unknown = tmp_path / "unknown"
    unknown.mkdir()

    for index, (cwd, expected) in enumerate(
        ((repo, "primary_worktree"), (linked, "cycle_worktree"), (unknown, "unknown"))
    ):
        state_root = tmp_path / f"state-{index}"
        result = run_control(
            "hook", "SessionStart", stdin=json.dumps(payload(cwd)).encode(),
            env={
                "DBSCTR_STATE_ROOT": str(state_root),
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
            },
        )
        assert result.returncode == 0
        assert records(state_root)[0]["record"]["workspace"] == expected


def test_hook_rejects_stale_cycle_authority(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-b", "cycle", str(linked))
    root_commit = git(repo, "rev-list", "--max-parents=0", "HEAD")
    worktree_id = hashlib.sha256(f"{root_commit}\0cycle".encode()).hexdigest()[:16]
    active = repo / ".git/dbsctr/worktrees" / worktree_id / "active"
    active.parent.mkdir(parents=True)
    active.write_text("stale-cycle\n")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_dbsctrctl(fake_bin, "stale-cycle", worktree_id, state="retired")
    state_root = tmp_path / "state"

    run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(linked)).encode(),
        env={
            "DBSCTR_STATE_ROOT": str(state_root),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert records(state_root)[0]["record"]["workspace"] == "unknown"


def test_hook_prunes_expired_private_records(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    directory = state_root / "codex-hooks"
    directory.mkdir(parents=True, mode=0o700)
    expired = directory / "expired.json"
    expired.write_text(json.dumps({
        "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    }))
    expired.chmod(0o600)

    run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert not expired.exists()
    assert len(records(state_root)) == 1


def test_hook_caps_private_record_count(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    directory = state_root / "codex-hooks"
    directory.mkdir(parents=True, mode=0o700)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    for index in range(1024):
        path = directory / f"{index:04d}.json"
        path.write_text(json.dumps({"expires_at": expires}))
        path.chmod(0o600)

    run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert len(records(state_root)) == 1024
    assert not (directory / "0000.json").exists()


def test_hook_caps_aggregate_private_record_bytes(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    directory = state_root / "codex-hooks"
    directory.mkdir(parents=True, mode=0o700)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    for index in range(10):
        path = directory / f"{index:04d}.json"
        path.write_text(json.dumps({"expires_at": expires, "padding": "x" * 999_900}))
        path.chmod(0o600)

    run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    paths = list(directory.glob("*.json"))
    assert sum(path.stat().st_size for path in paths) <= 8 * 1024 * 1024
    assert not (directory / "0000.json").exists()


def test_concurrent_hooks_preserve_private_record_caps(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    directory = state_root / "codex-hooks"
    directory.mkdir(parents=True, mode=0o700)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    for index in range(1023):
        path = directory / f"{index:04d}.json"
        path.write_text(json.dumps({"expires_at": expires}))
        path.chmod(0o600)
    raw = json.dumps(payload(repo)).encode()
    processes = [subprocess.Popen(
        [sys.executable, str(CONTROL), "hook", "SessionStart"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "DBSCTR_STATE_ROOT": str(state_root)},
    ) for _ in range(8)]

    results = [process.communicate(raw, timeout=10) for process in processes]

    assert all(process.returncode == 0 for process in processes)
    assert all(stdout == b"" and stderr == b"" for stdout, stderr in results)
    paths = list(directory.glob("*.json"))
    assert len(paths) <= 1024
    assert sum(path.stat().st_size for path in paths) <= 8 * 1024 * 1024


def test_hook_lock_timeout_is_silent_and_preserves_valid_records(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = tmp_path / "state"
    directory = state_root / "codex-hooks"
    directory.mkdir(parents=True, mode=0o700)
    existing = directory / "existing.json"
    existing.write_text(json.dumps({
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }))
    existing.chmod(0o600)
    lock_path = directory / ".lock"
    lock = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX)
    release = threading.Timer(4.2, lambda: fcntl.flock(lock, fcntl.LOCK_UN))
    release.start()
    started = time.monotonic()

    result = run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )
    elapsed = time.monotonic() - started
    release.join()
    os.close(lock)

    assert elapsed < 4.5
    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    assert list(directory.glob("*.json")) == [existing]


def test_hook_refuses_private_state_inside_git_worktree(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state_root = repo / "private-state"

    result = run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert result.returncode == 0
    assert not state_root.exists()


@pytest.mark.parametrize("nested", [False, True])
def test_hook_refuses_symlinked_private_state_roots(tmp_path: Path, nested: bool) -> None:
    repo = repository(tmp_path)
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked-state"
    link.symlink_to(real, target_is_directory=True)
    state_root = link / "nested" if nested else link

    result = run_control(
        "hook", "SessionStart", stdin=json.dumps(payload(repo)).encode(),
        env={"DBSCTR_STATE_ROOT": str(state_root)},
    )

    assert result.returncode == 0
    assert not (real / "codex-hooks").exists()
    assert not (real / "nested/codex-hooks").exists()


def test_bounded_command_kills_descendants_after_leader_exits(tmp_path: Path) -> None:
    module = runpy.run_path(str(CONTROL))
    fake = tmp_path / "forking-command"
    child_pid = tmp_path / "child.pid"
    fake.write_text(
        "#!/bin/sh\n"
        "(sleep 30) >/dev/null 2>&1 &\n"
        "printf '%s' \"$!\" > \"$1\"\n"
    )
    fake.chmod(0o755)

    module["run_bounded"]([str(fake), str(child_pid)], 1, 1024)
    pid = int(child_pid.read_text())
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        pytest.fail("bounded command left a descendant running")


def test_probe_uses_exact_frozen_cli_and_keeps_sessions_unavailable(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex = fake_bin / "codex"
    codex.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  --version) printf 'codex-cli 0.151.0\\n' ;;\n"
        "  --help) printf 'Codex help\\n' ;;\n"
        "  *) exit 2 ;;\n"
        "esac\n"
    )
    codex.chmod(0o755)

    result = run_control("probe", env={"PATH": f"{fake_bin}:{os.environ['PATH']}"})

    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["release"] == "0.151.0"
    assert body["runtime"] == {"status": "available", "version": "codex-cli 0.151.0"}
    assert body["session"] == {"status": "unavailable", "reason": "capability_not_probed"}


def test_probe_fails_closed_on_version_drift(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex = fake_bin / "codex"
    codex.write_text("#!/bin/sh\nprintf 'codex-cli 0.152.0\\n'\n")
    codex.chmod(0o755)

    result = run_control("probe", env={"PATH": f"{fake_bin}:{os.environ['PATH']}"})

    assert result.returncode == 1
    assert json.loads(result.stdout)["runtime"]["reason"] == "version_mismatch"


def test_probe_fails_closed_on_unbounded_command_output(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex = fake_bin / "codex"
    codex.write_text(
        "#!/bin/sh\n"
        "dd if=/dev/zero bs=1048577 count=1 2>/dev/null\n"
    )
    codex.chmod(0o755)

    result = run_control("probe", env={"PATH": f"{fake_bin}:{os.environ['PATH']}"})

    assert result.returncode == 1
    assert json.loads(result.stdout)["runtime"]["reason"] == "runtime_probe_failed"


@pytest.mark.parametrize("args", [("session", "list"), ("dbsctr", "status")])
def test_unprobed_operations_are_explicitly_unavailable(args: tuple[str, str]) -> None:
    result = run_control(*args)

    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "unavailable"
    assert json.loads(result.stdout)["reason"] == "capability_not_probed"


def test_usage_errors_return_two() -> None:
    result = run_control("hook", "UnknownEvent")

    assert result.returncode == 2
