"""Managed user hooks guard native Worktrunk; no custom allocator participates."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tomllib

import pytest
from test_worktrunk_registration import fixture, git


ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "private_dot_config/worktrunk/config.toml"


def test_managed_policy_keeps_branches_and_uses_blocking_user_hook():
    value = tomllib.loads(CONFIG.read_text())
    assert value["worktree-path"] == "{{ repo_path }}.worktrees/{{ branch | sanitize }}"
    assert value["remove"]["delete-branch"] is False
    assert value["pre-remove"]["preservation"] == "exec dbsctrctl workspace-remove-check --json"
    assert "post-start" not in value and "pre-start" not in value
    assert value["commit"]["stage"] == "none"


@pytest.mark.skipif(not shutil.which("wt") or not shutil.which("lsof"), reason="native Worktrunk/process authority unavailable")
def test_native_user_hook_blocks_forced_dirty_removal_then_preserves_branch(fixture):
    base = fixture.repo.parent
    home, tools = base / "home", base / "bin"
    home.mkdir()
    tools.mkdir()
    shim = tools / "dbsctrctl"
    shim.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} "
                    f"{shlex.quote(str(ROOT / 'dot_local/bin/executable_dbsctrctl'))} \"$@\"\n")
    shim.chmod(0o755)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "DVC_", "DBSCTR_", "WORKTRUNK_"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_CACHE_HOME=str(home / "cache"),
               XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"),
               PATH=f"{tools}:{os.environ['PATH']}", WORKTRUNK_CONFIG_PATH=str(CONFIG),
               WORKTRUNK_SYSTEM_CONFIG_PATH=str(base / "no-system-config"))

    def wt(*argv, ok=True):
        value = subprocess.run([shutil.which("wt"), *argv], cwd=fixture.repo, env=env,
                               text=True, capture_output=True, timeout=90)
        assert (value.returncode == 0) is ok, value.stderr + value.stdout
        return value

    wt("switch", "--create", "task", "--no-cd", "--yes")
    target = Path(str(fixture.repo) + ".worktrees") / "task"
    assert target.is_dir()
    (target / "tracked.txt").write_text("disposable dirty fixture\n")
    refused = wt("remove", "task", "--force", "--yes", ok=False)
    assert "dirty_worktree" in refused.stdout + refused.stderr
    assert (target / "tracked.txt").read_text() == "disposable dirty fixture\n"
    git(target, "restore", "tracked.txt")
    wt("remove", "task", "--yes")
    assert not target.exists()
    assert git(fixture.repo, "branch", "--show-current").strip() == "master"
    git(fixture.repo, "show-ref", "--verify", "refs/heads/task")
