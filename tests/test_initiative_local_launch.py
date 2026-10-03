"""Real Git import from unpublished Discovery into an explicit native checkout.

GitHub transport and operator input are synthetic; no production consent or
native actor identity is inferred from these fixtures.
"""
import importlib.machinery
import importlib.util
import json
import hashlib
import sys
import os
import subprocess
import shutil
from pathlib import Path

import pytest
import test_dbsctrctl as fixtures
from test_initiative_cli_approval import Operator


@pytest.fixture
def launch(tmp_path, monkeypatch, request):
    fixture = fixtures.DbsctrctlTest()
    fixture.setUp()
    request.addfinalizer(fixture.tearDown)
    loader = importlib.machinery.SourceFileLoader("local_launch", str(fixtures.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    helper = importlib.util.module_from_spec(spec)
    loader.exec_module(helper)
    repo = fixture.repo
    remote = tmp_path / "remote.git"
    helper.git(repo, "init", "--bare", str(remote))
    helper.git(repo, "branch", "-M", "main")
    helper.git(repo, "remote", "add", "origin", str(remote))
    helper.git(repo, "push", "-u", "origin", "main")
    helper.git(repo, "switch", "-c", "discovery/local")
    manifest = fixture.write_initiative()
    (repo / "docs/specs/test/BACKLOG.md").write_text("Discovery-owned bounded context backlog\n")
    helper.git(repo, "add", str(manifest))
    helper.git(repo, "add", "docs/specs/test/BACKLOG.md")
    helper.git(repo, "commit", "-m", "Discovery authority")
    fixture.native_task = tmp_path / "native-task"
    helper.git(repo, "worktree", "add", "-b", "native-task", str(fixture.native_task), "origin/main")
    helper.git(fixture.native_task, "branch", "--set-upstream-to", "origin/main")
    monkeypatch.chdir(fixture.native_task)
    monkeypatch.setattr(helper, "root_dir", lambda: fixture.native_task)
    monkeypatch.setattr(helper, "git_repository_slug", lambda _: "example/test")
    monkeypatch.setattr(helper, "github_environment", lambda _: {})
    monkeypatch.setattr(helper, "github_remote_url", lambda *args: str(remote))
    monkeypatch.setattr(helper, "fetch_github_branch", lambda root, remote, url, branch, env:
                        helper.git(root, "fetch", remote, branch))
    monkeypatch.setattr(helper, "github_remote_head", lambda *args: [])
    monkeypatch.setenv("DBSCTR_WORKTREE_ROOT", str(tmp_path / "worktrees"))
    plan = fixture.plan_path("draft_pr")
    receipt = helper.initiative_receipt(manifest, "slice-a", repo)
    fixture.launch_argv = [
        "begin", "--cycle-id", "local-1", "--context", "test", "--risk", "critical",
        "--delivery-intent", "draft_pr", "--plan", str(plan), "--base-branch", "main",
        "--github-account", "example", "--github-repository", "example/test",
        "--initiative-manifest", str(manifest.relative_to(repo)), "--initiative-slice", "slice-a",
        "--initiative-source", str(repo),
        "--initiative-digest", receipt["manifest_digest"], "--expected-repository", "example/test",
        "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
    ]
    args = helper.parser().parse_args(fixture.launch_argv)

    class FixtureConfirmation(Operator):
        def readline(self, *_):
            return f"BEGIN {args.cycle_id} {args.expected_launch_digest}\n"

    # Synthetic operator input only. Native CLI noninteractive refusal is tested below.
    monkeypatch.setattr(helper.sys, "stdin", FixtureConfirmation())
    yield helper, fixture, args


def test_unpublished_discovery_launch_preserves_source_and_records_import(launch, capsys, monkeypatch):
    helper, fixture, args = launch
    source_head = helper.git(fixture.repo, "rev-parse", "HEAD").stdout.strip()
    (fixture.repo / "tracked.txt").write_text("unrelated dirty work\n")
    args.preflight = True
    helper.command_begin(args)
    preview = json.loads(capsys.readouterr().out)
    assert preview["launch_digest"]
    assert not (fixture.repo / ".git/dbsctr/cycles/local-1.json").exists()
    args.preflight = False
    args.expected_launch_digest = preview["launch_digest"]
    helper.command_begin(args)
    handoff = json.loads(capsys.readouterr().out)
    worktree = Path(handoff["worktree"])
    record = helper.load(worktree)[1]
    assert record["git"]["pre_cycle_ahead_commits"] == []
    assert record["git"]["upstream"] == "origin/main"
    assert record["commits"][0]["gates"] == []
    assert record["discovery_import"]["source_commit"] == source_head
    assert worktree == fixture.native_task
    assert record["initiative_approval"]["method"] == "interactive_cli"
    assert record["runtime"] == {"adapters": {}}
    assert record["execution"]["attribution"]["status"] == "unavailable"
    assert (worktree / args.initiative_manifest).exists()
    assert (worktree / "docs/specs/test/BACKLOG.md").read_text() == "Discovery-owned bounded context backlog\n"
    assert (worktree / "tracked.txt").read_text() == "base\n"
    assert (fixture.repo / "tracked.txt").read_text() == "unrelated dirty work\n"
    assert helper.git(fixture.repo, "rev-parse", "HEAD").stdout.strip() == source_head
    helper.verify_discovery_import(worktree, record)
    args.resume_existing = True
    args.preflight = True
    helper.command_begin(args)
    args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    args.preflight = False

    class NoNewConfirmation(Operator):
        def readline(self, *_):
            raise AssertionError("resuming a registered cycle must not renew consent")

    monkeypatch.setattr(helper.sys, "stdin", NoNewConfirmation())
    helper.command_begin(args)
    assert json.loads(capsys.readouterr().out)["resumed"] is True
    assert helper.load(worktree)[1]["initiative_approval"] == record["initiative_approval"]


def test_launch_rejects_unapproved_commit_and_stale_plan(launch, capsys):
    helper, fixture, args = launch
    args.preflight = True
    helper.command_begin(args)
    preview = json.loads(capsys.readouterr().out)
    (fixture.repo / "tracked.txt").write_text("unrelated committed code\n")
    helper.git(fixture.repo, "commit", "-am", "Unrelated")
    args.preflight = False
    args.expected_launch_digest = preview["launch_digest"]
    with pytest.raises(RuntimeError):
        helper.command_begin(args)
    assert not (fixture.repo / ".git/dbsctr/cycles/local-1.json").exists()


def test_import_reaches_final_push_without_publishing_discovery_branch(launch, capsys, monkeypatch):
    helper, fixture, args = launch
    args.preflight = True
    helper.command_begin(args)
    args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    args.preflight = False
    helper.command_begin(args)
    worktree = Path(json.loads(capsys.readouterr().out)["worktree"])
    changelog = "docs/specs/test/CHANGELOG.md"
    (worktree / changelog).write_text("Implemented and checked.\n")
    for gate in fixtures.GATES:
        if gate == "release":
            continue
        fixtures.run(worktree, "record-evidence", gate, "--authority", "fixture",
                     "--path", changelog, "--", sys.executable, "-c", "print('passed')")
    fixtures.run(worktree, "gate-commit", "--message", "Implement", "--gates",
                 *[gate for gate in fixtures.GATES if gate != "release"], "--paths", changelog)
    for name in ("README", "BACKLOG"):
        fixtures.run(worktree, "review-artifact", name, "--result", "unchanged", "--reason", "verified")
    fixtures.run(worktree, "review-artifact", "CHANGELOG", "--result", "changed",
                 "--reason", "recorded", "--path", changelog)
    remote = helper.git(worktree, "remote", "get-url", "origin").stdout.strip()
    base = helper.git(worktree, "rev-parse", "origin/main").stdout.strip()
    monkeypatch.setattr(helper, "github_remote_head", lambda root, url, ref, env:
                        helper.git(root, "ls-remote", "--heads", url, ref).stdout.split())
    monkeypatch.setattr(helper, "push_github_branch", lambda root, url, branch, env:
                        helper.git(root, "push", url, f"HEAD:{branch}"))
    monkeypatch.setattr(helper, "deliver_draft_pr", lambda *args:
                        {"number": 1, "url": "https://github.com/example/test/pull/1", "draft": True})
    path, record = helper.load(worktree)
    helper.finish_push(worktree, path, record)
    assert record["state"] == "completed"
    assert helper.git(worktree, "ls-remote", remote, "refs/heads/main").stdout.split()[0] == base
    assert not helper.git(worktree, "ls-remote", remote, "refs/heads/discovery/local").stdout


def test_protected_base_movement_invalidates_launch_before_creation(launch, capsys):
    helper, fixture, args = launch
    args.preflight = True
    helper.command_begin(args)
    args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    # Advance only the protected ref; the approved Discovery branch stays intact.
    base = helper.git(fixture.repo, "rev-parse", "origin/main").stdout.strip()
    tree = helper.git(fixture.repo, "rev-parse", f"{base}^{{tree}}").stdout.strip()
    advanced = helper.git(fixture.repo, "commit-tree", tree, "-p", base, "-m", "Upstream advance").stdout.strip()
    helper.git(fixture.repo, "push", "origin", f"{advanced}:refs/heads/main")
    args.preflight = False
    with pytest.raises(RuntimeError, match="launch plan changed|approved base"):
        helper.command_begin(args)
    assert not (fixture.repo / ".git/dbsctr/cycles/local-1.json").exists()


def test_import_rejects_symlink_authority_and_provenance_tampering(launch, capsys):
    helper, fixture, args = launch
    args.preflight = True
    helper.command_begin(args)
    args.expected_launch_digest = json.loads(capsys.readouterr().out)["launch_digest"]
    args.preflight = False
    helper.command_begin(args)
    worktree = Path(json.loads(capsys.readouterr().out)["worktree"])
    record = helper.load(worktree)[1]
    record["discovery_import"]["artifacts"][0]["blob"] = "0" * 40
    with pytest.raises(RuntimeError, match="blob identity"):
        helper.verify_discovery_import(worktree, record)
    source = fixture.repo / "docs/specs/test/README.md"
    source.unlink()
    source.symlink_to("CHANGELOG.md")
    helper.git(fixture.repo, "add", str(source))
    helper.git(fixture.repo, "commit", "-m", "Unsafe authority")
    fixture.native_task = fixture.native_task.parent / "unsafe-task"
    helper.git(fixture.repo, "worktree", "add", "-b", "unsafe-task", str(fixture.native_task), "origin/main")
    helper.git(fixture.native_task, "branch", "--set-upstream-to", "origin/main")
    args.cycle_id = "unsafe-2"
    args.preflight = True
    with pytest.raises(RuntimeError):
        helper.command_begin(args)
    assert not (fixture.repo / ".git/dbsctr/cycles/unsafe-2.json").exists()


def test_native_cli_preflight_needs_no_adapter_and_cannot_fake_confirmation(launch, tmp_path):
    helper, fixture, args = launch
    repo = fixture.repo
    remote = helper.git(repo, "remote", "get-url", "origin").stdout.strip()
    helper.git(repo, "remote", "set-url", "origin", "https://github.com/example/test.git")
    home = tmp_path / "home"
    home.mkdir()
    binary = tmp_path / "bin"
    binary.mkdir()
    transport = binary / "dbsctrctl"
    transport.write_text(f'''#!{sys.executable}
import runpy
n=runpy.run_path({str(fixtures.SCRIPT)!r})
g=n['main'].__globals__
g['github_environment']=lambda account: {{}}
g['github_remote_url']=lambda *args: {remote!r}
g['fetch_github_branch']=lambda root,remote,url,branch,env: g['git'](root,'fetch',url,f'refs/heads/{{branch}}:refs/remotes/{{remote}}/{{branch}}')
g['github_remote_head']=lambda *args: []
raise SystemExit(g['main']())
''')
    transport.chmod(0o700)
    git = binary / "git"
    git.write_text(f'''#!/bin/sh
if [ "$1 $2 $3 $4" = "ls-remote --symref origin HEAD" ]; then
  printf 'ref: refs/heads/main\\tHEAD\\n'
else
  exec {shutil.which('git')} "$@"
fi
''')
    git.chmod(0o700)
    env = {**fixtures.isolated_env(), "HOME": str(home), "PATH": f"{binary}:{os.environ['PATH']}"}
    result = subprocess.run([str(transport), *fixture.launch_argv, "--preflight"], cwd=fixture.native_task,
                            env=env, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr
    preview = json.loads(result.stdout)
    assert preview["launch_digest"]
    before = helper.git(fixture.native_task, "rev-parse", "HEAD").stdout
    rejected = subprocess.run(
        [str(transport), *fixture.launch_argv, "--expected-launch-digest", preview["launch_digest"]],
        input=f"BEGIN {args.cycle_id} {preview['launch_digest']}\n", cwd=fixture.native_task,
        env=env, text=True, capture_output=True, timeout=90,
    )
    assert rejected.returncode != 0 and "interactive operator confirmation" in rejected.stderr
    assert helper.git(fixture.native_task, "rev-parse", "HEAD").stdout == before
    assert not (helper.cycle_dir(fixture.native_task) / "cycles" / f"{args.cycle_id}.json").exists()
