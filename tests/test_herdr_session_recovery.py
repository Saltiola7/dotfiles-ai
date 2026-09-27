import json
import os
import runpy
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_herdr_launchagent import ROOT, _render_herdr_script


SCRIPT = ROOT / "dot_local/bin/executable_herdr-opencode-restore"


def entry(tmp_path, state=None):
    value = {"pane_id": "w1:p1", "directory": str(tmp_path), "session_id": "ses_saved"}
    if state:
        value["recovery_state"] = state
    return value


def seed(tmp_path, state=None):
    manifest = tmp_path / "opencode-sessions.json"
    manifest.write_text(json.dumps({"schema_version": 2 if state else 1,
                                    "sessions": [entry(tmp_path, state)]}))
    return manifest


def inventory(monkeypatch, script, entries):
    def run(*args):
        if args == ("pane", "list"):
            return {"result": {"panes": [{"pane_id": item["pane_id"]} for item in entries]}}
        item = next(item for item in entries if item["pane_id"] == args[-1])
        return {"result": {"process_info": {"foreground_processes": [{
            "argv": ["opencode", "--session", item["session_id"]], "cwd": item["directory"],
        }]}}}
    monkeypatch.setitem(script["capture"].__globals__, "run", run)


def test_pending_survives_capture_restart_and_manual_reopen(monkeypatch, tmp_path):
    manifest = seed(tmp_path)
    for _ in range(2):
        script = runpy.run_path(str(SCRIPT))
        inventory(monkeypatch, script, [])
        script["capture"](manifest)
        assert json.loads(manifest.read_text()) == {
            "schema_version": 2, "sessions": [entry(tmp_path, "pending")],
        }
    reopened = {**entry(tmp_path), "pane_id": "w1:p2"}
    inventory(monkeypatch, script, [reopened])
    script["capture"](manifest)
    assert json.loads(manifest.read_text())["sessions"] == [
        {**reopened, "recovery_state": "observed"},
    ]
    inventory(monkeypatch, script, [])
    script["capture"](manifest)
    assert json.loads(manifest.read_text())["sessions"] == []
    assert manifest.stat().st_mode & 0o777 == 0o600


def test_pending_collision_preserves_previous_manifest(monkeypatch, tmp_path):
    manifest = seed(tmp_path, "pending")
    before = manifest.read_bytes()
    script = runpy.run_path(str(SCRIPT))
    inventory(monkeypatch, script, [{**entry(tmp_path), "session_id": "ses_other"}])
    with pytest.raises(ValueError):
        script["capture"](manifest)
    assert manifest.read_bytes() == before


@pytest.mark.parametrize("foreground", [{}, {"argv": "opencode"}, {"argv": ["opencode"]}])
def test_incomplete_process_inventory_does_not_erase_observed_session(monkeypatch, tmp_path, foreground):
    manifest = seed(tmp_path, "observed")
    before = manifest.read_bytes()
    script = runpy.run_path(str(SCRIPT))
    def run(*args):
        if args == ("pane", "list"):
            return {"result": {"panes": [{"pane_id": "w1:p1"}]}}
        return {"result": {"process_info": {"foreground_processes": [foreground]}}}
    monkeypatch.setitem(script["capture"].__globals__, "run", run)
    with pytest.raises(ValueError):
        script["capture"](manifest)
    assert manifest.read_bytes() == before


@pytest.mark.parametrize("fault", ["partial", "replace", "invalid", "symlink"])
def test_failed_capture_never_overwrites_intent(monkeypatch, tmp_path, fault):
    manifest = seed(tmp_path, "pending")
    script = runpy.run_path(str(SCRIPT))
    inventory(monkeypatch, script, [entry(tmp_path)])
    if fault == "partial":
        original = script["capture"].__globals__["run"]
        def failing(*args):
            if args[:2] == ("pane", "process-info"):
                raise OSError("private failure")
            return original(*args)
        monkeypatch.setitem(script["capture"].__globals__, "run", failing)
    elif fault == "replace":
        def failing(*args, **kwargs):
            raise OSError("interrupted atomic replacement")
        monkeypatch.setattr(os, "replace", failing)
    elif fault == "invalid":
        manifest.write_text('{"schema_version":2,"sessions":[{}]}')
    else:
        target = tmp_path / "outside.json"
        manifest.rename(target)
        manifest.symlink_to(target)
    before = manifest.read_bytes()
    with pytest.raises((OSError, ValueError)):
        script["capture"](manifest)
    assert manifest.read_bytes() == before


def test_restore_failure_marks_intent_pending_before_capture(monkeypatch, tmp_path):
    root = tmp_path / "state"
    parent = root / "herdr"
    parent.mkdir(parents=True)
    manifest = seed(parent, "observed")
    script = runpy.run_path(str(SCRIPT))
    monkeypatch.setenv("DOTFILES_AI_STATE_ROOT", str(root))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "missing-data"))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setitem(script["main"].__globals__, "preflight_host", lambda **_: None)
    with pytest.raises((OSError, RuntimeError)):
        script["main"]()
    inventory(monkeypatch, script, [])
    script["capture"](manifest)
    assert json.loads(manifest.read_text())["sessions"] == [entry(parent, "pending")]


@pytest.mark.parametrize("fault", [None, "occupied", "directory", "unknown"])
def test_check_is_read_only_and_refuses_wrong_targets(monkeypatch, tmp_path, fault):
    parent = tmp_path / "state/herdr"
    parent.mkdir(parents=True)
    manifest = seed(parent)
    before = manifest.read_bytes()
    database = tmp_path / "data/opencode/opencode.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE session (id TEXT PRIMARY KEY)")
        if fault != "unknown":
            connection.execute("INSERT INTO session VALUES ('ses_saved')")
    wrapper = tmp_path / "home/.local/bin/opencode"
    wrapper.parent.mkdir(parents=True)
    wrapper.touch()
    script = runpy.run_path(str(SCRIPT))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DOTFILES_AI_STATE_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--check"])
    monkeypatch.setitem(script["main"].__globals__, "preflight_host", lambda **_: None)
    def run(*args):
        if args == ("agent", "list"):
            return {"result": {"agents": []}}
        if args[:2] == ("pane", "get"):
            return {"result": {"pane": {"cwd": str(tmp_path if fault == "directory" else parent)}}}
        if args[:2] == ("pane", "process-info"):
            return {"result": {"process_info": {"foreground_processes": (
                [{"argv": ["vim"]}] if fault == "occupied" else []
            )}}}
        raise AssertionError("check must not launch a process")
    monkeypatch.setitem(script["restore"].__globals__, "run", run)
    assert script["main"]() == (1 if fault else 0)
    assert manifest.read_bytes() == before


def test_capture_cannot_race_restore_lock(monkeypatch, tmp_path):
    import fcntl
    manifest = seed(tmp_path, "pending")
    before = manifest.read_bytes()
    script = runpy.run_path(str(SCRIPT))
    inventory(monkeypatch, script, [])
    with (tmp_path / "opencode-restore.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="busy"):
            script["capture"](manifest)
        assert manifest.read_bytes() == before
    script["capture"](manifest)
    assert json.loads(manifest.read_text())["sessions"] == [entry(tmp_path, "pending")]


def test_progress_does_not_remove_total_admission_deadline(monkeypatch, tmp_path, capsys):
    from types import SimpleNamespace
    script = runpy.run_path(str(SCRIPT))
    root = tmp_path / "herdr"
    root.mkdir()
    lock = root / "opencode-startup.lock"
    lock.write_text(f"{os.getpid()}\n")
    stamp = root / "opencode-startup.timestamp"
    stamp.write_text("0")
    clock = [0]
    def sleep(_):
        clock[0] += 10
        stamp.write_text(str(clock[0]))
    monkeypatch.setenv("DOTFILES_AI_STATE_ROOT", str(tmp_path))
    monkeypatch.setitem(script["pace_start"].__globals__, "time", SimpleNamespace(
        monotonic=lambda: clock[0], sleep=sleep,
    ))
    monkeypatch.setitem(script["pace_start"].__globals__, "signal", SimpleNamespace(
        SIGINT=2, SIGTERM=15, signal=lambda *_: None,
    ))
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: SimpleNamespace(returncode=1))
    assert script["pace_start"](["never-launch"]) == 75
    assert clock[0] == 300
    assert "five minutes" in capsys.readouterr().err
    assert lock.read_text() == f"{os.getpid()}\n"


def wrapper_fixture(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / ".dotfiles-ai-state").touch()
    target = tmp_path / "target"
    target.write_text(f"#!{sys.executable}\nimport json,sys,time\n"
                      "print(json.dumps([sys.argv[1:],time.monotonic()]))\n")
    target.chmod(0o755)
    wrapper = tmp_path / "wrapper"
    wrapper.write_text(_render_herdr_script(".local/bin/opencode", {
        "dotfiles_ai": {"state": {"root": str(state)}, "herdr": {"host_enabled": False}},
    }).replace("/opt/homebrew/bin/opencode", str(target)))
    wrapper.chmod(0o755)
    helper = tmp_path / "home/.local/bin/herdr-opencode-restore"
    helper.parent.mkdir(parents=True)
    helper.write_text(SCRIPT.read_text().replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1))
    helper.chmod(0o755)
    env = {"HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin", "HERDR_ENV": "1"}
    return wrapper, state / "herdr", env


def test_thirty_concurrent_resumes_drain_with_spacing(tmp_path):
    wrapper, _, env = wrapper_fixture(tmp_path)
    processes = [subprocess.Popen([wrapper, "--session", f"ses_{index}"], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for index in range(30)]
    try:
        results = [(process.communicate(timeout=240), process.returncode) for process in processes]
        assert all(code == 0 for _, code in results), results
        starts = sorted(json.loads(output[0]) for output, _ in results)
        assert {row[0][1] for row in starts} == {f"ses_{index}" for index in range(30)}
        assert all(row[0][-1] == "--auto" for row in starts)
        times = sorted(row[1] for row in starts)
        assert all(right - left >= 4.8 for left, right in zip(times, times[1:]))
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def test_stalled_startup_is_reported_as_contention(tmp_path):
    wrapper, state, env = wrapper_fixture(tmp_path)
    state.mkdir()
    lock = state / "opencode-startup.lock"
    lock.write_text(f"{os.getpid()}\n")
    result = subprocess.run([wrapper, "--session", "ses_wait"], env=env,
                            capture_output=True, text=True, timeout=35)
    assert result.returncode == 75
    assert "pacing queue stalled" in result.stderr
    assert lock.read_text() == f"{os.getpid()}\n"


@pytest.mark.parametrize("filename", ["opencode-startup.lock", "opencode-startup.timestamp"])
def test_startup_rejects_links_without_touching_target(tmp_path, filename):
    wrapper, state, env = wrapper_fixture(tmp_path)
    state.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("preserve\n")
    (state / filename).symlink_to(outside)
    result = subprocess.run([wrapper, "--session", "ses_bad"], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 75
    assert "unsafe" in result.stderr
    assert outside.read_text() == "preserve\n"


def test_cancelled_pacing_releases_its_lock(tmp_path):
    wrapper, state, env = wrapper_fixture(tmp_path)
    state.mkdir()
    (state / "opencode-startup.timestamp").write_text(str(int(time.time())))
    process = subprocess.Popen([wrapper, "--session", "ses_cancel"], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lock = state / "opencode-startup.lock"
    try:
        deadline = time.monotonic() + 3
        while not lock.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert lock.exists()
        process.terminate()
        process.communicate(timeout=10)
        assert process.returncode == 143
        assert not lock.exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
