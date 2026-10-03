"""Lifecycle registration never allocates or redirects a native checkout."""
import json
import subprocess

import pytest
import test_dbsctrctl as harness


@pytest.fixture
def fixture():
    case = harness.DbsctrctlTest()
    case.setUp()
    try:
        yield case
    finally:
        case.tearDown()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def task(case):
    target = case.repo.parent / "task"
    git(case.repo, "worktree", "add", "-b", "task", str(target))
    return target


def register(case, target, command="start", extra=(), ok=True):
    return harness.run(target, command, "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
                       "--delivery-intent", "local", "--base-branch", "protected",
                       "--plan", str(case.plan_path()), *extra, ok=ok)


@pytest.mark.parametrize("command", ["begin", "start"])
def test_primary_registration_refuses_without_writes(fixture, command):
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    result = register(fixture, fixture.repo, command, ok=False)
    assert "linked worktree" in result.stderr
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before
    assert not fixture.record_path().exists()


def test_start_records_native_checkout_and_unavailable_actor(fixture):
    target = task(fixture)
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    register(fixture, target)
    record = json.loads(fixture.record_path().read_text())
    assert record["execution"]["origin"] == "registered"
    assert record["execution"]["attribution"]["status"] == "unavailable"
    assert record["runtime"] == {"adapters": {}}
    assert record["worktree"]["created_by_dbsctr"] is False
    assert record["worktree"]["git_dir"].startswith("worktrees/")
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before


def test_begin_registers_existing_checkout_without_allocating(fixture):
    remote = fixture.repo.parent / "remote.git"
    git(fixture.repo, "init", "--bare", str(remote))
    git(fixture.repo, "remote", "add", "origin", str(remote))
    git(fixture.repo, "push", "origin", "HEAD:refs/heads/base")
    target = task(fixture)
    git(target, "branch", "--set-upstream-to", "origin/base")
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    result = json.loads(register(fixture, target, "begin").stdout)
    assert result["worktree"] == str(target.resolve())
    assert result["branch"] == "task"
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before


def test_branch_change_cannot_start_second_cycle_in_owned_checkout(fixture):
    target = task(fixture)
    register(fixture, target)
    before = fixture.record_path().read_bytes()
    git(target, "switch", "-c", "different-task")
    result = harness.run(target, "start", "--cycle-id", "cycle-2", "--context", "test",
                         "--risk", "routine", "--delivery-intent", "local",
                         "--plan", str(fixture.plan_path()), ok=False)
    assert "active cycle" in result.stderr
    assert fixture.record_path().read_bytes() == before
    assert not fixture.record_path().with_name("cycle-2.json").exists()


@pytest.mark.parametrize("failure", ["dirty", "actor_claim", "unconfigured_dvc"])
def test_registration_refusals_preserve_checkout(fixture, failure):
    target = task(fixture)
    extra = ()
    if failure == "dirty":
        (target / "tracked.txt").write_text("user work\n")
    elif failure == "actor_claim":
        extra = ("--opencode-session-id", "claimed-session", "--opencode-worktree", str(target),
                 "--opencode-directory", str(target))
    else:
        (target / ".dvc").mkdir()
        (target / ".dvc/config").write_text("")
        git(target, "add", ".dvc/config")
        git(target, "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid", "commit", "-m", "DVC metadata")
    before = git(fixture.repo, "worktree", "list", "--porcelain")
    result = register(fixture, target, extra=extra, ok=False)
    assert result.stderr
    assert not fixture.record_path().exists()
    assert git(fixture.repo, "worktree", "list", "--porcelain") == before
    if failure == "dirty":
        assert (target / "tracked.txt").read_text() == "user work\n"
