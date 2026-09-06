import json
import os
import fcntl
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


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
