"""Native launch reservations are bounded, checkout-local and non-destructive."""
import json
import hashlib
import os
from pathlib import Path
import pty
import signal
import subprocess
import sys
import time

import pytest

SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_agent-worktree"


@pytest.fixture
def workspace(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    for args in (("init", "-b", "main"),
                 ("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
                  "commit", "--allow-empty", "-m", "fixture")):
        subprocess.run(["git", *args], cwd=main, check=True, capture_output=True)
    trees = [tmp_path / name for name in ("a", "b")]
    for tree in trees:
        subprocess.run(["git", "worktree", "add", "-b", tree.name, str(tree)], cwd=main,
                       capture_output=True, check=True)
    alias = tmp_path / "alias"
    alias.symlink_to(trees[0], target_is_directory=True)
    binary = tmp_path / "bin"
    binary.mkdir()
    program = f"#!{sys.executable}\n" + '''import json, os, sys, time
from pathlib import Path
marker = Path(os.environ["FIXTURE_MARKER"])
value = {"cwd": os.getcwd(), "argv": sys.argv[1:], "env": os.environ.get("FIXTURE_VALUE")}
marker.write_text(json.dumps(value))
if "--hold" in sys.argv:
    deadline = time.monotonic() + 20
    while not marker.with_suffix(".release").exists() and time.monotonic() < deadline:
        time.sleep(.02)
print(json.dumps(value), flush=True)
sys.exit(7 if "--exit-seven" in sys.argv else 0)
'''
    for name in ("opencode", "codex"):
        target = binary / name
        target.write_text(program)
        target.chmod(0o700)
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(PATH=f"{binary}:{env['PATH']}", FIXTURE_VALUE="synthetic-value")
    return main, trees, alias, env


def invoke(workspace, cwd, marker, *args, **kwargs):
    return subprocess.Popen([sys.executable, str(SCRIPT), *args], cwd=cwd,
                            env={**workspace[3], "FIXTURE_MARKER": str(marker)},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def started(process, marker):
    deadline = time.monotonic() + 5
    while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(.02)
    assert marker.exists(), process.communicate(timeout=5)


def finish(process, marker):
    marker.with_suffix(".release").touch()
    if process.poll() is None:
        process.communicate(timeout=5)


def test_same_checkout_and_alias_refuse_while_other_checkout_is_independent(workspace, tmp_path):
    _, (a, b), alias, _ = workspace
    marker = tmp_path / "holder"
    holder = invoke(workspace, a, marker, "--", "opencode", "--hold")
    try:
        started(holder, marker)
        subprocess.run(["git", "switch", "-c", "changed-branch"], cwd=a, check=True, capture_output=True)
        for cwd in (a, alias):
            denied = invoke(workspace, cwd, tmp_path / "denied", "codex")
            _, error = denied.communicate(timeout=5)
            assert denied.returncode == 75
            assert b"busy" in error
            assert not (tmp_path / "denied").exists()
        other = invoke(workspace, b, tmp_path / "other", "codex", "--exit-seven", "argument with spaces")
        output, error = other.communicate(timeout=5)
        assert other.returncode == 7, error
        value = json.loads(output)
        assert Path(value["cwd"]) == b.resolve()
        assert value["argv"] == ["--exit-seven", "argument with spaces"]
        assert value["env"] == "synthetic-value"
    finally:
        finish(holder, marker)
    again = invoke(workspace, a, tmp_path / "again", "opencode")
    assert again.wait(timeout=5) == 0


def test_override_requires_terminal_and_never_steals_existing_lock(workspace, tmp_path):
    a = workspace[1][0]
    marker = tmp_path / "holder"
    holder = invoke(workspace, a, marker, "opencode", "--hold")
    master, slave = pty.openpty()
    try:
        started(holder, marker)
        denied = invoke(workspace, a, tmp_path / "denied", "--override-busy", "codex", stdin=subprocess.DEVNULL)
        _, error = denied.communicate(timeout=5)
        assert denied.returncode != 0 and b"interactive" in error
        override = invoke(workspace, a, tmp_path / "override", "--override-busy", "codex", stdin=slave)
        os.write(master, b"OVERRIDE\n")
        _, error = override.communicate(timeout=5)
        assert override.returncode == 0, error
        assert b"without exclusive" in error
        still_busy = invoke(workspace, a, tmp_path / "still-denied", "opencode")
        assert still_busy.wait(timeout=5) == 75
    finally:
        os.close(master)
        os.close(slave)
        finish(holder, marker)


def test_termination_releases_owned_launch_without_killing_other_checkout(workspace, tmp_path):
    a, b = workspace[1]
    first_marker, other_marker = tmp_path / "first", tmp_path / "other"
    first = invoke(workspace, a, first_marker, "opencode", "--hold")
    other = invoke(workspace, b, other_marker, "codex", "--hold")
    try:
        started(first, first_marker)
        started(other, other_marker)
        first.terminate()
        assert first.wait(timeout=5) == 128 + signal.SIGTERM
        assert other.poll() is None
        replacement = invoke(workspace, a, tmp_path / "replacement", "opencode")
        assert replacement.wait(timeout=5) == 0
    finally:
        finish(first, first_marker)
        finish(other, other_marker)


def test_child_retains_reservation_if_supervisor_is_killed(workspace, tmp_path):
    a = workspace[1][0]
    marker = tmp_path / "holder"
    holder = invoke(workspace, a, marker, "opencode", "--hold")
    try:
        started(holder, marker)
        holder.kill()
        holder.wait(timeout=5)
        denied = invoke(workspace, a, tmp_path / "denied", "opencode")
        assert denied.wait(timeout=5) == 75
    finally:
        marker.with_suffix(".release").touch()
        holder.communicate(timeout=5)


def test_unsafe_lock_directory_does_not_launch_or_follow_symlink(workspace, tmp_path):
    main, trees, _, _ = workspace
    outside = tmp_path / "outside"
    outside.mkdir()
    (main / ".git/agent-worktree-locks").symlink_to(outside, target_is_directory=True)
    process = invoke(workspace, trees[0], tmp_path / "marker", "opencode")
    _, error = process.communicate(timeout=5)
    assert process.returncode == 75 and b"unsafe" in error
    assert not (tmp_path / "marker").exists()
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("args", [("opencode", "--help"), ("codex", "--version"), ("opencode", "service", "status")])
def test_non_session_commands_do_not_need_a_checkout(workspace, tmp_path, args):
    process = invoke(workspace, tmp_path, tmp_path / "utility", *args)
    assert process.wait(timeout=5) == 0


def test_primary_checkout_cannot_be_claimed_as_a_task_workspace(workspace, tmp_path):
    process = invoke(workspace, workspace[0], tmp_path / "marker", "opencode")
    _, error = process.communicate(timeout=5)
    assert process.returncode == 75 and b"linked worktree" in error
    assert not (tmp_path / "marker").exists()


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "permissions"])
def test_unsafe_lock_file_is_not_modified_or_used(workspace, tmp_path, unsafe):
    main, trees, _, _ = workspace
    admin = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=trees[0], text=True).strip()
    directory = main / ".git/agent-worktree-locks"
    directory.mkdir(mode=0o700)
    lock = directory / (hashlib.sha256(os.fsencode(str(Path(admin).resolve()))).hexdigest() + ".lock")
    protected = tmp_path / "protected"
    protected.write_text("retain")
    protected.chmod(0o600)
    if unsafe == "symlink":
        lock.symlink_to(protected)
    elif unsafe == "hardlink":
        os.link(protected, lock)
    else:
        lock.write_text("retain")
        lock.chmod(0o644)
    process = invoke(workspace, trees[0], tmp_path / "marker", "opencode")
    assert process.wait(timeout=5) == 75
    assert not (tmp_path / "marker").exists()
    assert protected.read_text() == "retain"
    assert lock.read_text() == "retain"


def test_git_location_override_is_not_silently_accepted(workspace, tmp_path):
    workspace[3]["GIT_WORK_TREE"] = str(workspace[0])
    process = invoke(workspace, workspace[1][0], tmp_path / "marker", "opencode")
    _, error = process.communicate(timeout=5)
    assert process.returncode == 75 and b"overrides" in error
    assert not (tmp_path / "marker").exists()
