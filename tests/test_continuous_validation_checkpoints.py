"""Default-off lifecycle checkpoint custody and bounded worker contracts."""

import fcntl
from contextlib import contextmanager
import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(runner.canonical(value) + b"\n")
    path.chmod(0o600)
    return path


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def checkpoints():
    return importlib.import_module("continuous_validation.checkpoints")


@pytest.fixture
def enrolled(tmp_path, monkeypatch):
    """Real linked Git checkout with the existing native DBSCTR fixture owner."""
    native = importlib.import_module("test_dbsctrctl")
    fixture = native.DbsctrctlTest("run")
    fixture.setUp()
    home = (tmp_path / "home").resolve()
    home.mkdir(mode=0o700)
    environment = {**native.isolated_env(), "HOME": str(home),
                   "XDG_CONFIG_HOME": str(home / "config")}
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    commands = tmp_path / "bin"
    commands.mkdir()
    wrapper = commands / "dbsctrctl"
    wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
                       + shlex.quote(str(native.SCRIPT)) + ' "$@"\n')
    wrapper.chmod(0o700)
    environment["PATH"] = str(commands) + os.pathsep + os.environ["PATH"]
    monkeypatch.setenv("PATH", environment["PATH"])
    try:
        fixture.start(env=environment)
        worktree = fixture.repo.resolve()
        adapter = worktree / "adapter.py"
        adapter.write_text("# Checkpoint boundary fixture: never executed.\n")
        git(worktree, "add", "adapter.py")
        git(worktree, "commit", "-m", "checkpoint fixture adapter")
        state = home / "shadow"
        value = {
            "schema_version": 1, "enabled": True, "mode": "shadow",
            "checkpoints_enabled": True, "worktree": str(worktree),
            "adapter": "adapter.py", "adapter_digest": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "adapter_python": sys.executable, "adapter_config": {},
            "repository_id": runner.repository_id(worktree),
            "session_id": str(uuid.uuid4()), "cycle_id": "cycle-1",
            "base": git(worktree, "rev-parse", "HEAD"), "state_dir": str(state),
            "feedback_enabled": False,
        }
        path = private_json(home / "enrollment.json", value)
        yield {"fixture": fixture, "native": native, "env": environment,
               "worktree": worktree, "state": state, "home": home,
               "path": path, "value": value}
    finally:
        fixture.tearDown()


def registry_path(enrolled):
    value = enrolled["value"]
    worktree_hash = hashlib.sha256(os.fsencode(value["worktree"])).hexdigest()
    return (runner.default_state_root() / "checkpoint-bindings" / value["repository_id"]
            / worktree_hash / (value["cycle_id"] + ".json"))


def manual_binding(enrolled):
    """Write the specified binding independently of the new register entry point."""
    value = enrolled["value"]
    return private_json(registry_path(enrolled), {
        "schema_version": 1, "enrollment": str(enrolled["path"]),
        "enrollment_digest": runner.digest(value), "repository_id": value["repository_id"],
        "worktree": value["worktree"], "cycle_id": value["cycle_id"],
    })


def events(enrolled):
    directory = enrolled["state"] / "checkpoints"
    return [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))]


def enqueue(checkpoints, enrolled, gates=("domain",)):
    return checkpoints.enqueue_gate_commit(enrolled["worktree"], "cycle-1",
        git(enrolled["worktree"], "rev-parse", "HEAD"), list(gates))


def native_gate_commit(enrolled, *, ok=True):
    native, root, environment = enrolled["native"], enrolled["worktree"], enrolled["env"]
    (root / "tracked.txt").write_text("validated checkpoint\n")
    native.run(root, "record-evidence", "domain", "--authority", "fixture",
               "--path", "tracked.txt", "--", sys.executable, "-c", "print('ok')",
               env=environment)
    return native.run(root, "gate-commit", "--message", "checkpoint", "--gates", "domain",
                      "--paths", "tracked.txt", env=environment, ok=ok)


def test_native_successful_gate_commit_enqueues_after_durable_record(enrolled):
    manual_binding(enrolled)
    result = native_gate_commit(enrolled)
    head = git(enrolled["worktree"], "rev-parse", "HEAD")
    record = json.loads(enrolled["fixture"].record_path().read_text())
    assert result.stdout.strip() == head
    assert record["commits"][-1]["id"] == head
    retained = events(enrolled)
    assert len(retained) == 1
    assert retained[0]["head"] == head
    assert retained[0]["gates"] == ["domain"]
    assert retained[0]["state"] == "queued"


def test_native_gate_commit_without_binding_preserves_no_optional_state(enrolled):
    result = native_gate_commit(enrolled)
    assert result.stdout.strip() == git(enrolled["worktree"], "rev-parse", "HEAD")
    assert not runner.default_state_root().exists()
    assert not enrolled["state"].exists()


def test_unsuccessful_native_gate_commit_does_not_enqueue(enrolled):
    manual_binding(enrolled)
    before = git(enrolled["worktree"], "rev-parse", "HEAD")
    result = enrolled["native"].run(enrolled["worktree"], "gate-commit", "--message", "not ready",
        "--gates", "domain", "--paths", "tracked.txt", env=enrolled["env"], ok=False)
    assert "gate is not complete" in result.stderr
    assert git(enrolled["worktree"], "rev-parse", "HEAD") == before
    assert events(enrolled) == []


def test_native_enqueue_failure_does_not_change_commit_exit_or_stdout(enrolled):
    path = manual_binding(enrolled)
    path.write_text("not JSON")
    result = native_gate_commit(enrolled)
    assert result.stdout.strip() == git(enrolled["worktree"], "rev-parse", "HEAD")
    assert "continuous_validation_checkpoint_unavailable" in result.stderr
    assert events(enrolled) == []


def test_disabled_registration_creates_nothing(checkpoints, tmp_path):
    missing = tmp_path / "absent" / "enrollment.json"
    assert checkpoints.register(missing, {"schema_version": 1, "enabled": False}) is None
    assert checkpoints.register(missing, {"schema_version": 1, "enabled": True,
                                         "checkpoints_enabled": False}) is None
    assert not missing.parent.exists()


def test_register_binds_exact_private_enrollment(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    path = registry_path(enrolled)
    binding = json.loads(path.read_text())
    assert binding["enrollment_digest"] == runner.digest(enrolled["value"])
    assert binding["worktree"] == str(enrolled["worktree"])
    assert binding["cycle_id"] == "cycle-1"
    assert path.stat().st_mode & 0o777 == 0o600


def test_missing_binding_is_noop_without_execution_or_creation(checkpoints, enrolled, monkeypatch):
    monkeypatch.setattr(runner, "cycle_open", lambda value: pytest.fail("absent binding inspected cycle"))
    assert enqueue(checkpoints, enrolled)["status"] == "disabled"
    assert not runner.default_state_root().exists()
    assert not enrolled["state"].exists()


def test_duplicate_multi_gate_checkpoint_has_one_private_event(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    first = enqueue(checkpoints, enrolled, ("domain", "behavior"))
    repeated = enqueue(checkpoints, enrolled, ("behavior", "domain"))
    assert first["status"] == "queued"
    assert repeated["status"] == "duplicate"
    assert first["event_id"] == repeated["event_id"]
    assert len(events(enrolled)) == 1
    assert events(enrolled)[0]["gates"] == ["behavior", "domain"]


@pytest.mark.parametrize("change", ["disabled", "changed_enrollment", "head", "closed_cycle", "binding"])
def test_drain_rejects_stale_or_revoked_checkpoint(checkpoints, enrolled, change):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    if change in {"disabled", "changed_enrollment"}:
        value = dict(enrolled["value"])
        value["enabled" if change == "disabled" else "feedback_enabled"] = False if change == "disabled" else True
        private_json(enrolled["path"], value)
    elif change == "head":
        git(enrolled["worktree"], "commit", "--allow-empty", "-m", "advance")
    elif change == "closed_cycle":
        path = enrolled["fixture"].record_path()
        value = json.loads(path.read_text())
        value["state"] = "completed"
        path.write_text(json.dumps(value))
    else:
        value = json.loads(registry_path(enrolled).read_text())
        value["cycle_id"] = "other-cycle"
        private_json(registry_path(enrolled), value)
    assert checkpoints.drain_one(enrolled["path"], lambda request: pytest.fail("stale event executed")) is None


def test_drain_claims_before_ordinary_request_and_does_not_replay(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    queued = enqueue(checkpoints, enrolled)
    calls = []
    def run_request(request):
        calls.append(request)
        assert events(enrolled)[0]["state"] == "attempting"
        assert request == {"schema_version": 1, "enrollment": str(enrolled["path"]),
                           "trigger": "checkpoint", "request_id": "checkpoint-" + queued["event_id"]}
        return {"schema_version": 1, "status": "pending", "observations": [], "pending_checks": ["heavy"]}
    result = checkpoints.drain_one(enrolled["path"], run_request)
    assert result["status"] == "pending"
    assert checkpoints.drain_one(enrolled["path"], run_request) is None
    assert len(calls) == 1
    assert events(enrolled)[0]["state"] == "terminal"


def test_uncertain_worker_crash_retains_attempt_and_prevents_replay(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    def interrupted(request):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        checkpoints.drain_one(enrolled["path"], interrupted)
    assert events(enrolled)[0]["state"] == "attempting"
    assert checkpoints.drain_one(enrolled["path"], lambda request: pytest.fail("unknown attempt replayed")) is None


def test_queue_capacity_retains_old_events_and_refuses_new(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    directory = enrolled["state"] / "checkpoints"
    first = next(directory.glob("*.json"))
    payload = first.read_bytes()
    for index in range(1, 128):
        path = directory / (f"{index:064x}.json")
        path.write_bytes(payload)
        path.chmod(0o600)
    before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    git(enrolled["worktree"], "commit", "--allow-empty", "-m", "next checkpoint")
    with pytest.raises(runner.ValidationError, match="checkpoint_queue_full"):
        enqueue(checkpoints, enrolled)
    assert {path.name: path.read_bytes() for path in directory.glob("*.json")} == before


def test_checkpoint_queue_lock_has_one_second_bound(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    lock = enrolled["state"] / "checkpoints" / "queue.lock"
    with lock.open("a+") as stream:
        lock.chmod(0o600)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = time.monotonic()
        with pytest.raises(runner.ValidationError, match="checkpoint_lock_timeout"):
            enqueue(checkpoints, enrolled)
        assert time.monotonic() - started < 1.25


def test_registry_symlink_is_rejected_without_following(checkpoints, enrolled, tmp_path):
    path = registry_path(enrolled)
    path.parent.mkdir(parents=True, mode=0o700)
    target = private_json(tmp_path / "unrelated.json", {"private": "fixture"})
    path.symlink_to(target)
    before = target.read_bytes()
    with pytest.raises(runner.ValidationError):
        checkpoints.register(enrolled["path"], enrolled["value"])
    assert target.read_bytes() == before


def helper_module():
    loader = importlib.machinery.SourceFileLoader("checkpoint_native_helper", str(ROOT / "dot_local/bin/executable_dbsctrctl"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_revoked_native_binding_does_not_import_optional_package(enrolled, monkeypatch, capsys):
    import builtins
    manual_binding(enrolled)
    private_json(enrolled["path"], {**enrolled["value"], "enabled": False})
    core = helper_module()
    original = builtins.__import__
    def forbid_optional(name, *args, **kwargs):
        if name.startswith("continuous_validation"):
            pytest.fail("disabled native hook imported optional package")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", forbid_optional)
    core.optional_shadow_checkpoint({"worktree": enrolled["worktree"], "cycle": "cycle-1",
        "head": git(enrolled["worktree"], "rev-parse", "HEAD"), "gates": ["domain"]})
    assert capsys.readouterr().err == ""
    assert not enrolled["state"].exists()


def test_real_native_hook_runs_only_after_mutation_guard_exit(enrolled, monkeypatch, capsys):
    manual_binding(enrolled)
    native, root = enrolled["native"], enrolled["worktree"]
    (root / "tracked.txt").write_text("validated outside-guard checkpoint\n")
    native.run(root, "record-evidence", "domain", "--authority", "fixture", "--path", "tracked.txt",
               "--", sys.executable, "-c", "print('ok')", env=enrolled["env"])
    core = helper_module()
    held = [False]
    original_guard = core.local_cli_mutation_guard
    original_hook = core.optional_shadow_checkpoint
    @contextmanager
    def guard(args, selected):
        with original_guard(args, selected):
            held[0] = True
            try:
                yield
            finally:
                held[0] = False
    def after_guard(descriptor):
        assert held[0] is False
        original_hook(descriptor)
    monkeypatch.setattr(core, "local_cli_mutation_guard", guard)
    monkeypatch.setattr(core, "optional_shadow_checkpoint", after_guard)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", [str(native.SCRIPT), "gate-commit", "--message", "outside lock",
        "--gates", "domain", "--paths", "tracked.txt"])
    assert core.main() == 0
    assert capsys.readouterr().out.strip() == git(root, "rev-parse", "HEAD")
    assert len(events(enrolled)) == 1


def test_drain_rejects_event_filename_identity_mismatch(checkpoints, enrolled):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    directory = enrolled["state"] / "checkpoints"
    next(directory.glob("*.json")).rename(directory / ("f" * 64 + ".json"))
    with pytest.raises(runner.ValidationError, match="checkpoint_event_filename"):
        checkpoints.drain_one(enrolled["path"], lambda request: pytest.fail("misnamed event executed"))


def test_cycle_probe_runs_outside_checkpoint_queue_lock(checkpoints, enrolled, monkeypatch):
    checkpoints.register(enrolled["path"], enrolled["value"])
    enqueue(checkpoints, enrolled)
    original = runner.cycle_open
    def verify_unlocked(value):
        with (enrolled["state"] / "checkpoints/queue.lock").open("r+") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pytest.fail("native cycle probe ran under queue lock")
        return original(value)
    monkeypatch.setattr(runner, "cycle_open", verify_unlocked)
    result = checkpoints.drain_one(enrolled["path"], lambda request: {"status": "passed"})
    assert result["status"] == "passed"


@pytest.mark.parametrize("gates", [[], ["unknown"], ["domain", "domain"]])
def test_invalid_gate_sets_do_not_enqueue(checkpoints, enrolled, gates):
    checkpoints.register(enrolled["path"], enrolled["value"])
    with pytest.raises(runner.ValidationError, match="invalid_checkpoint_gates"):
        enqueue(checkpoints, enrolled, gates)
    assert events(enrolled) == []


@pytest.mark.parametrize("value", [[], {"schema_version": 2, "enabled": False},
    {"schema_version": 1, "enabled": "yes"},
    {"schema_version": 1, "enabled": True, "checkpoints_enabled": 1}])
def test_malformed_private_checkpoint_enrollment_fails_closed(checkpoints, tmp_path, value):
    path = private_json(tmp_path.resolve() / "enrollment.json", value)
    with pytest.raises(runner.ValidationError):
        checkpoints.drain_one(path, lambda request: pytest.fail("malformed enrollment executed"))
