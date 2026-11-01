import fcntl
import importlib.machinery
import importlib.util
import json
import os
import plistlib
import signal
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest


ROOT = Path(__file__).parents[1]
FIELDS = ("schema_version", "state", "failure_class", "consecutive_failures", "started_at",
          "finished_at", "duration_seconds", "snapshot_age_seconds", "snapshot_size_bytes")
WALL_START_NS = 1_700_000_000_123_456_789
WALL_FINISH_NS = WALL_START_NS + 10_000_000_000
MONOTONIC_START_NS = 10_900_000_000


def data(enabled=False, hour=4, minute=30, timeout=3600):
    return {"dotfiles_ai": {"history_projection": {
        "enabled": enabled, "refresh_hour": hour, "refresh_minute": minute,
        "refresh_timeout_seconds": timeout,
    }}}


def render(path, values=None):
    return subprocess.run([
        "chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
        "--override-data", json.dumps(values or data()), "execute-template",
    ], input=(ROOT / path).read_text(), text=True, capture_output=True, check=True).stdout


def wrapper(tmp_path):
    path = tmp_path / "history-projection-refresh"
    path.write_text(render("dot_local/bin/executable_history-projection-refresh.tmpl"))
    path.chmod(0o755)
    return path


@pytest.fixture
def loaded_wrapper(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTFILES_AI_STATE_ROOT", str(tmp_path / "state"))
    path = wrapper(tmp_path)
    loader = importlib.machinery.SourceFileLoader("history_projection_refresh", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def scheduled_run(loaded_wrapper, monkeypatch):
    module = loaded_wrapper
    previous = {
        "schema_version": 1, "state": "failed", "failure_class": "refresh_failed",
        "consecutive_failures": 2, "started_at": 1000, "finished_at": 2500,
        "duration_seconds": 1500, "snapshot_age_seconds": 37, "snapshot_size_bytes": 4096,
    }
    module.write_status(previous)
    clock = SimpleNamespace(
        time_ns=Mock(side_effect=[WALL_START_NS, WALL_FINISH_NS]),
        monotonic_ns=Mock(side_effect=[MONOTONIC_START_NS, MONOTONIC_START_NS + 1_500_000_000]),
    )
    child = SimpleNamespace(pid=12345, wait=Mock(return_value=0))
    popen = Mock(return_value=child)
    killpg = Mock()
    monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(module, "subprocess", SimpleNamespace(
        Popen=popen, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired,
    ))
    monkeypatch.setattr(module.os, "killpg", killpg)
    summaries = []
    persist = module.write_status

    def record_summary(value):
        summaries.append(value.copy())
        persist(value)

    monkeypatch.setattr(module, "write_status", record_summary)
    return SimpleNamespace(module=module, previous=previous, clock=clock, child=child,
                           popen=popen, killpg=killpg, summaries=summaries)


def assert_terminal_summary(run, duration, state="succeeded", failure=None,
                            started_at=WALL_START_NS // 1_000_000,
                            finished_at=WALL_FINISH_NS // 1_000_000):
    running, final = run.summaries
    assert tuple(running) == tuple(final) == FIELDS
    assert running == {
        **run.previous, "state": "running", "failure_class": None,
        "started_at": started_at, "finished_at": None, "duration_seconds": None,
    }
    assert final == {
        **running, "state": state, "failure_class": failure, "finished_at": finished_at,
        "duration_seconds": duration, "consecutive_failures": 0 if failure is None else 3,
    }
    assert type(final["duration_seconds"]) is int
    assert json.loads(run.module.STATUS.read_text()) == final
    assert stat.S_IMODE(run.module.STATUS.stat().st_mode) == 0o600
    assert stat.S_IMODE(run.module.DIRECTORY.stat().st_mode) == 0o700
    assert not (run.module.DIRECTORY / ".status.tmp").exists()
    assert run.clock.monotonic_ns.call_count == 2
    run.popen.assert_called_once_with(
        ["dbsctrctl", "history-source-index-refresh"], start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def test_default_is_disabled_and_enabled_plist_is_daily_background():
    loader = render("run_onchange_after_load-history-projection-refresh.sh.tmpl")
    disabled = render("run_onchange_after_load-history-projection-refresh.sh.tmpl", data(False))
    plist = plistlib.loads(render(
        "private_Library/LaunchAgents/dev.dotfiles-ai.history-projection-refresh.plist.tmpl",
        data(True),
    ).encode())
    assert "bootout" in disabled and "bootstrap" in loader
    subprocess.run(["bash", "-n"], input=loader, text=True, check=True)
    assert plist["StartCalendarInterval"] == {"Hour": 4, "Minute": 30}
    assert plist["ProcessType"] == "Background"
    assert plist["ProgramArguments"][-2:] == ["run", "3600"]
    with pytest.raises(subprocess.CalledProcessError):
        render("run_onchange_after_load-history-projection-refresh.sh.tmpl", data(True, hour=24))


def test_status_missing_and_invalid_state(tmp_path):
    script = wrapper(tmp_path)
    state = tmp_path / "state"
    env = {**os.environ, "DOTFILES_AI_STATE_ROOT": str(state)}
    missing = subprocess.run([script, "status"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(missing.stdout) == {
        "schema_version": 1, "state": "never_run", "failure_class": None,
        "consecutive_failures": 0, "started_at": None, "finished_at": None,
        "duration_seconds": None, "snapshot_age_seconds": None, "snapshot_size_bytes": None,
    }
    path = state / "dotfiles-ai/history-projection-refresh/status.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json")
    invalid = subprocess.run([script, "status"], env=env, text=True, capture_output=True)
    assert invalid.returncode == 75 and invalid.stdout == ""
    assert invalid.stderr == "scheduler_state_invalid\n"
    path.unlink()
    path.symlink_to("missing")
    unsafe = subprocess.run([script, "status"], env=env, text=True, capture_output=True)
    assert unsafe.returncode == 75 and unsafe.stdout == ""


def test_run_records_success_and_overlap_preserves_running_state(tmp_path):
    script = wrapper(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    command = bin_dir / "dbsctrctl"
    command.write_text("#!/bin/sh\nprintf 'private source body\\n'\nexit 0\n")
    command.chmod(0o755)
    env = {**os.environ, "DOTFILES_AI_STATE_ROOT": str(tmp_path / "state"),
           "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    completed = subprocess.run([script, "run", "900"], env=env, text=True, capture_output=True)
    assert completed.returncode == 0
    assert completed.stdout == "history_projection_refresh=succeeded\n"
    status = subprocess.run([script, "status"], env=env, text=True, capture_output=True, check=True)
    assert json.loads(status.stdout)["state"] == "succeeded"
    lock = tmp_path / "state/dotfiles-ai/history-projection-refresh/run.lock"
    before = status.stdout
    with lock.open("a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        overlap = subprocess.run([script, "run", "900"], env=env, text=True, capture_output=True)
    assert overlap.returncode == 0
    after = subprocess.run([script, "status"], env=env, text=True, capture_output=True, check=True)
    assert after.stdout == before


@pytest.mark.parametrize(("elapsed_ns", "expected_seconds"), [
    pytest.param(0, 0, id="zero"),
    pytest.param(999_999_999, 0, id="subsecond"),
    pytest.param(1_000_000_000, 1, id="exact-second"),
    pytest.param(1_500_000_000, 1, id="fractional-second"),
])
def test_terminal_duration_uses_completed_monotonic_seconds(
        scheduled_run, capsys, elapsed_ns, expected_seconds):
    run = scheduled_run
    run.clock.monotonic_ns.side_effect = [MONOTONIC_START_NS, MONOTONIC_START_NS + elapsed_ns]
    assert run.module.run(900) == 0
    assert_terminal_summary(run, expected_seconds)
    run.child.wait.assert_called_once_with(timeout=900)
    run.killpg.assert_not_called()
    assert capsys.readouterr() == ("history_projection_refresh=succeeded\n", "")


@pytest.mark.parametrize(("outcome", "wait_ns", "expected_seconds", "signals"), [
    pytest.param("nonzero", [1_500_000_000], 1, [], id="nonzero-exit"),
    pytest.param("spawn", [], 1, [], id="spawn-failure"),
    pytest.param("term", [900_000_000_000, 5_500_000_000], 905, [signal.SIGTERM],
                 id="timeout-grace"),
    pytest.param("kill", [900_000_000_000, 30_000_000_000, 1_500_000_000], 931,
                 [signal.SIGTERM, signal.SIGKILL], id="timeout-kill"),
])
def test_failed_duration_includes_execution_and_timeout_cleanup(
        scheduled_run, capsys, outcome, wait_ns, expected_seconds, signals):
    run = scheduled_run
    now = MONOTONIC_START_NS
    run.clock.monotonic_ns.side_effect = lambda: now
    waits = iter(enumerate(wait_ns))

    def wait(timeout=None):
        nonlocal now
        index, elapsed = next(waits)
        now += elapsed
        if outcome in {"term", "kill"} and index < len(wait_ns) - 1:
            raise subprocess.TimeoutExpired("private source body", timeout)
        return 7 if outcome == "nonzero" else 0

    def spawn_failure(*args, **kwargs):
        nonlocal now
        now += 1_500_000_000
        raise OSError("private source body")

    run.child.wait.side_effect = wait
    if outcome == "spawn":
        run.popen.side_effect = spawn_failure
    assert run.module.run(900) == 1
    timed_out = outcome in {"term", "kill"}
    failure = "timeout" if timed_out else "refresh_failed"
    assert_terminal_summary(run, expected_seconds,
                            state="timed_out" if timed_out else "failed", failure=failure)
    expected_waits = [] if outcome == "spawn" else [call(timeout=900)]
    if timed_out:
        expected_waits.append(call(timeout=30))
    if outcome == "kill":
        expected_waits.append(call())
    assert run.child.wait.call_args_list == expected_waits
    assert run.killpg.call_args_list == [call(run.child.pid, value) for value in signals]
    assert capsys.readouterr() == (f"history_projection_refresh={failure}\n", "")


@pytest.mark.parametrize("wall_delta_ns", [
    pytest.param(-60_000_000_000, id="backward"),
    pytest.param(60_000_000_000, id="forward"),
])
def test_wall_clock_adjustment_preserves_timestamps_without_changing_duration(
        scheduled_run, capsys, wall_delta_ns):
    run = scheduled_run
    finished = WALL_START_NS + wall_delta_ns
    run.clock.time_ns.side_effect = [WALL_START_NS, finished]
    assert run.module.run(900) == 0
    assert_terminal_summary(run, 1, finished_at=finished // 1_000_000)
    assert capsys.readouterr() == ("history_projection_refresh=succeeded\n", "")


def test_duration_includes_running_persistence_and_excludes_prior_read_and_final_write(
        scheduled_run, monkeypatch, capsys):
    run = scheduled_run
    now = MONOTONIC_START_NS
    run.clock.monotonic_ns.side_effect = lambda: now
    read_status = run.module.read_status
    write_status = run.module.write_status

    def read_previous():
        nonlocal now
        value = read_status()
        now += 20_000_000_000
        return value

    def write_summary(value):
        nonlocal now
        write_status(value)
        now += 800_000_000 if value["state"] == "running" else 10_000_000_000

    def spawn(*args, **kwargs):
        nonlocal now
        now += 100_000_000
        return run.child

    def wait(timeout):
        nonlocal now
        now += 600_000_000
        return 0

    monkeypatch.setattr(run.module, "read_status", read_previous)
    monkeypatch.setattr(run.module, "write_status", write_summary)
    run.popen.side_effect = spawn
    run.child.wait.side_effect = wait
    assert run.module.run(900) == 0
    assert_terminal_summary(run, 1)
    assert capsys.readouterr() == ("history_projection_refresh=succeeded\n", "")


def test_status_preserves_legacy_summary_until_next_acquired_run(
        scheduled_run, monkeypatch, capsys):
    run = scheduled_run
    legacy = (json.dumps(run.previous, indent=2) + "\n").encode()
    run.module.STATUS.write_bytes(legacy)
    monkeypatch.setattr(run.module, "sys", SimpleNamespace(
        argv=["history-projection-refresh", "status"], stderr=sys.stderr,
    ))
    run.module.main()
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out == json.dumps(run.previous, separators=(",", ":")) + "\n"
    assert run.module.STATUS.read_bytes() == legacy
    assert run.summaries == []
    run.clock.time_ns.assert_not_called()
    run.clock.monotonic_ns.assert_not_called()
    run.popen.assert_not_called()
    assert run.module.run(900) == 0
    assert_terminal_summary(run, 1)
    assert run.module.STATUS.read_bytes() != legacy
    assert capsys.readouterr() == ("history_projection_refresh=succeeded\n", "")


def test_overlap_preserves_actual_running_summary_without_sampling_clocks(scheduled_run, capsys):
    run = scheduled_run
    running = {
        **run.previous, "state": "running", "failure_class": None,
        "finished_at": None, "duration_seconds": None,
    }
    run.module.STATUS.write_text(json.dumps(running, indent=2) + "\n")
    before = run.module.STATUS.read_bytes()
    with run.module.LOCK.open("a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert run.module.run(900) == 0
    assert run.module.STATUS.read_bytes() == before
    assert run.summaries == []
    run.clock.time_ns.assert_not_called()
    run.clock.monotonic_ns.assert_not_called()
    run.popen.assert_not_called()
    run.killpg.assert_not_called()
    assert capsys.readouterr() == ("", "")
