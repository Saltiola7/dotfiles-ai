"""Native launch reservations are bounded, checkout-local and non-destructive."""
import json
import fcntl
import hashlib
import os
from pathlib import Path
import pty
import selectors
import signal
import shutil
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
    home = tmp_path / "home"
    home.mkdir()
    env.update(PATH=f"{binary}:{env['PATH']}", HOME=str(home), FIXTURE_VALUE="synthetic-value")
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


@pytest.mark.skipif(not shutil.which("wt"), reason="pinned native Worktrunk unavailable")
def test_native_remove_hook_retains_parent_reservation_descriptor(workspace, tmp_path):
    main, trees, _, env = workspace
    assert subprocess.check_output(["wt", "--version"], text=True).strip() == "wt v0.80.0"
    target = trees[1]
    admin = Path(subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=target, text=True).strip()).resolve()
    directory = main / ".git/agent-worktree-locks"
    directory.mkdir(mode=0o700)
    lock = directory / (hashlib.sha256(os.fsencode(str(admin))).hexdigest() + ".lock")
    marker = tmp_path / "descriptor-result.json"
    probe = tmp_path / "descriptor-probe.py"
    probe.write_text('''import fcntl, json, os, stat
from pathlib import Path
fd = int(os.environ["SYNTHETIC_RESERVATION_FD"])
path = Path(os.environ["SYNTHETIC_RESERVATION_PATH"])
result = {"inherited": False, "contender_blocked": False}
try:
    held, named = os.fstat(fd), path.lstat()
    result["inherited"] = (stat.S_ISREG(held.st_mode) and held.st_uid == os.getuid()
        and held.st_nlink == 1 and stat.S_IMODE(held.st_mode) == 0o600
        and (held.st_dev, held.st_ino) == (named.st_dev, named.st_ino))
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with path.open("r+") as contender:
        try: fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: result["contender_blocked"] = True
except OSError: pass
Path(os.environ["SYNTHETIC_DESCRIPTOR_RESULT"]).write_text(json.dumps(result))
raise SystemExit(0 if all(result.values()) else 1)
''')
    config = tmp_path / "worktrunk.toml"
    config.write_text('[pre-remove]\nprobe = ' + json.dumps(f"exec {sys.executable} {probe}") + '\n')
    env = {**env, "WORKTRUNK_CONFIG_PATH": str(config), "WORKTRUNK_SYSTEM_CONFIG_PATH": str(tmp_path / "absent-system"),
           "SYNTHETIC_RESERVATION_PATH": str(lock), "SYNTHETIC_DESCRIPTOR_RESULT": str(marker)}
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(["wt", "remove", "--foreground", "--no-delete-branch", str(target)],
            cwd=main, env={**env, "SYNTHETIC_RESERVATION_FD": str(fd)}, pass_fds=(fd,),
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        assert marker.exists(), result.stderr
        assert json.loads(marker.read_text()) == {"inherited": True, "contender_blocked": True}
        assert result.returncode == 0, result.stderr
        assert not target.exists()
        assert subprocess.run(["git", "show-ref", "--verify", "refs/heads/b"], cwd=main, capture_output=True).returncode == 0
    finally:
        os.close(fd)


@pytest.mark.parametrize("kind", ["primary", "current", "relative", "unregistered", "alias"])
def test_remove_mode_refuses_unsafe_targets_without_native_mutation(workspace, tmp_path, kind):
    main, trees, alias, _ = workspace
    target = {"primary": main, "current": trees[0], "relative": Path("../b"),
              "unregistered": tmp_path, "alias": alias}[kind]
    cwd = trees[0] if kind == "current" else main
    result = invoke(workspace, cwd, tmp_path / "marker", "--remove", str(target))
    _, errors = result.communicate(timeout=10)
    assert result.returncode == 75, errors
    assert all(tree.exists() for tree in trees)
    assert subprocess.run(["git", "show-ref", "--verify", "refs/heads/b"], cwd=main, capture_output=True).returncode == 0


def test_remove_mode_refuses_extra_options_and_unqualified_hook_without_removing(workspace, tmp_path):
    main, trees, _, _ = workspace
    for suffix in (("--force",), ("--override-busy",), ()):
        result = invoke(workspace, main, tmp_path / "marker", "--remove", str(trees[1]), *suffix)
        _, errors = result.communicate(timeout=10)
        assert result.returncode != 0, errors
        assert trees[1].exists()


def test_removal_cannot_override_or_modify_an_existing_launch(workspace, tmp_path):
    main, trees, _, _ = workspace
    marker = tmp_path / "holder"
    holder = invoke(workspace, trees[1], marker, "opencode", "--hold")
    try:
        started(holder, marker)
        lock = next((main / ".git/agent-worktree-locks").glob("*.lock"))
        before = lock.read_bytes()
        refused = invoke(workspace, main, tmp_path / "removal", "--remove", str(trees[1]))
        assert refused.wait(timeout=5) == 75
        assert lock.read_bytes() == before
        assert holder.poll() is None and trees[1].exists()
        assert not (main / ".git/dbsctr/evidence/removal").exists()
    finally:
        finish(holder, marker)


def test_launch_override_never_bypasses_live_removal_reservation(workspace, tmp_path):
    main, trees, _, env = workspace
    helper = Path(env["HOME"]) / ".local/bin/dbsctrctl"
    helper.parent.mkdir(parents=True, mode=0o700)
    helper.write_text(f"#!{sys.executable}\n" + '''import json, os, time
from pathlib import Path
marker = Path(os.environ["FIXTURE_MARKER"])
fd = int(os.environ["DBSCTR_REMOVAL_FD"])
assert os.fstat(fd).st_uid == os.getuid()
marker.write_text("reserved")
deadline = time.monotonic() + 10
while not marker.with_suffix(".release").exists() and time.monotonic() < deadline: time.sleep(.02)
raise SystemExit(1)
''')
    helper.chmod(0o700)
    marker = tmp_path / "removal"
    remover = invoke(workspace, main, marker, "--remove", str(trees[1]))
    master, slave = pty.openpty()
    try:
        started(remover, marker)
        denied = invoke(workspace, trees[1], tmp_path / "denied", "--override-busy", "opencode", stdin=slave)
        _, errors = denied.communicate(timeout=5)
        assert denied.returncode == 75 and b"removal" in errors
        assert not (tmp_path / "denied").exists()
        independent = invoke(workspace, trees[0], tmp_path / "independent", "codex")
        assert independent.wait(timeout=5) == 0
    finally:
        os.close(master); os.close(slave)
        finish(remover, marker)
    assert trees[1].exists()
    again = invoke(workspace, trees[1], tmp_path / "after-block", "opencode")
    assert again.wait(timeout=5) == 0


@pytest.mark.skipif(not shutil.which("wt"), reason="pinned native Worktrunk unavailable")
def test_supervised_disposable_remove_keeps_branch_and_durable_attempt(workspace, tmp_path):
    main, trees, _, env = workspace
    # Transport/reservation fixture only: a synthetic checker is not retirement
    # authority or live handoff qualification. Real CLI decision tests are separate.
    helper = Path(env["HOME"]) / ".local/bin/dbsctrctl"
    helper.parent.mkdir(parents=True, mode=0o700)
    helper.write_text(f"#!{sys.executable}\n" + '''import fcntl, json, os
fd = int(os.environ["DBSCTR_REMOVAL_FD"])
attempt = json.loads(os.pread(fd, 8193, 0))
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
assert attempt["operation"] == "remove"
assert attempt["expected_state_digest"] in (None, "a" * 64)
print(json.dumps({"schema_version": 2, "eligible": True, "reasons": [],
    "state_digest": "a" * 64, "reservation_id": attempt["attempt_id"]}))
''')
    helper.chmod(0o700)
    config = tmp_path / "worktrunk.toml"
    config.write_text('[remove]\ndelete-branch = true\n[pre-remove]\npreservation = ' +
                      json.dumps(f"exec {helper} workspace-remove-check --json") + '\n')
    env.update(WORKTRUNK_CONFIG_PATH=str(config), WORKTRUNK_SYSTEM_CONFIG_PATH=str(tmp_path / "absent-system"))
    result = invoke(workspace, main, tmp_path / "removal", "--remove", str(trees[1]))
    _, errors = result.communicate(timeout=30)
    assert result.returncode == 0, errors
    assert not trees[1].exists()
    assert subprocess.run(["git", "show-ref", "--verify", "refs/heads/b"], cwd=main, capture_output=True).returncode == 0
    evidence = list((main / ".git/dbsctr/evidence/removal").glob("*.json"))
    assert len(evidence) == 1
    attempt = json.loads(evidence[0].read_text())
    assert attempt["outcome"] == "removed_branch_retained" and attempt["expected_state_digest"] == "a" * 64


@pytest.mark.parametrize("problem", [None, "missing-worktree", "changed-admin"])
def test_unknown_removal_attempt_is_observed_before_any_retry(workspace, tmp_path, problem):
    main, trees, _, env = workspace
    target = trees[1]
    admin = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=target, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
    directory = main / ".git/dbsctr/evidence/removal"
    directory.mkdir(parents=True, mode=0o700)
    identifier = "00000000-0000-4000-8000-000000000001"
    path = directory / (identifier + ".json")
    attempt = {"schema_version": 1, "operation": "remove", "attempt_id": identifier,
        "worktree": str(target), "common_git_dir": str(main / ".git"), "git_dir": admin,
        "branch": "refs/heads/b", "head": head, "expected_state_digest": "a" * 64, "outcome": "started"}
    if problem == "missing-worktree": attempt.pop("worktree")
    elif problem == "changed-admin": attempt["git_dir"] = str(Path(admin).with_name("different-admin"))
    path.write_text(json.dumps(attempt))
    path.chmod(0o600)
    before = path.read_bytes()
    counter = tmp_path / "native-remove-called"
    native = Path(env["PATH"].split(":")[0]) / "wt"
    native.write_text(f"#!/bin/sh\ntouch '{counter}'\nexit 1\n"); native.chmod(0o700)
    result = invoke(workspace, main, tmp_path / "removal", "--remove", str(target))
    assert result.wait(timeout=10) == 75
    assert not counter.exists() and target.exists()
    if problem is None:
        assert json.loads(path.read_text())["outcome"] == "observed_retained"
    else:
        assert path.read_bytes() == before


def test_override_rechecks_replacement_removal_holder_after_prompt(workspace, tmp_path):
    main, trees, _, _ = workspace
    marker = tmp_path / "holder"
    holder = invoke(workspace, trees[1], marker, "opencode", "--hold")
    master, slave = pty.openpty()
    override, fd = None, None
    try:
        started(holder, marker)
        override = invoke(workspace, trees[1], tmp_path / "overridden", "--override-busy", "codex", stdin=slave)
        with selectors.DefaultSelector() as selector:
            selector.register(override.stderr, selectors.EVENT_READ)
            assert selector.select(5), "override prompt unavailable"
            assert b"OVERRIDE" in os.read(override.stderr.fileno(), 256)
        finish(holder, marker)
        lock = next((main / ".git/agent-worktree-locks").glob("*.lock"))
        fd = os.open(lock, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = b'{"schema_version":1,"operation":"remove"}'
        os.ftruncate(fd, 0); os.pwrite(fd, raw, 0); os.fsync(fd)
        os.write(master, b"OVERRIDE\n")  # Synthetic operator fixture only.
        _, errors = override.communicate(timeout=5)
        assert override.returncode == 75 and b"removal transition" in errors
        assert not (tmp_path / "overridden").exists()
    finally:
        if fd is not None: os.close(fd)
        os.close(master); os.close(slave)
        finish(holder, marker)
        if override is not None and override.poll() is None: override.communicate(timeout=5)


@pytest.mark.parametrize("version,reasons", [(2.0, []), (2, "none"), (2, ["unknown"]), (2, [1])])
def test_malformed_strict_decision_never_dispatches_worktrunk(workspace, tmp_path, version, reasons):
    main, trees, _, env = workspace
    helper = Path(env["HOME"]) / ".local/bin/dbsctrctl"
    helper.parent.mkdir(parents=True, mode=0o700)
    payload = {"schema_version": version, "eligible": True, "reasons": reasons, "state_digest": "a" * 64}
    helper.write_text(f"#!{sys.executable}\nimport json,os\nvalue={payload!r}\n"
        'value["reservation_id"]=json.loads(os.pread(int(os.environ["DBSCTR_REMOVAL_FD"]),8193,0))["attempt_id"]\n'
        'print(json.dumps(value))\n')
    helper.chmod(0o700)
    counter = tmp_path / "native-called"
    native = Path(env["PATH"].split(":")[0]) / "wt"
    native.write_text(f"#!/bin/sh\ntouch '{counter}'\nexit 1\n"); native.chmod(0o700)
    result = invoke(workspace, main, tmp_path / "removal", "--remove", str(trees[1]))
    assert result.wait(timeout=10) == 75
    assert trees[1].exists() and not counter.exists()
