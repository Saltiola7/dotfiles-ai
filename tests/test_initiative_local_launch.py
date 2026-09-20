"""Real Git launch from unpublished Discovery; only GitHub transport is faked."""
import importlib.machinery
import importlib.util
import json
import hashlib
import sys
import os
import sqlite3
import subprocess
import shutil
from pathlib import Path

import pytest
import test_dbsctrctl as fixtures


@pytest.fixture
def launch(tmp_path, monkeypatch):
    fixture = fixtures.DbsctrctlTest()
    fixture.setUp()
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
    monkeypatch.setattr(helper, "root_dir", lambda: repo)
    monkeypatch.setattr(helper, "git_repository_slug", lambda _: "example/test")
    monkeypatch.setattr(helper, "github_environment", lambda _: {})
    monkeypatch.setattr(helper, "github_remote_url", lambda *args: str(remote))
    monkeypatch.setattr(helper, "fetch_github_branch", lambda root, remote, url, branch, env:
                        helper.git(root, "fetch", remote, branch))
    monkeypatch.setattr(helper, "github_remote_head", lambda *args: [])
    monkeypatch.setenv("DBSCTR_WORKTREE_ROOT", str(tmp_path / "worktrees"))
    plan = fixture.plan_path("draft_pr")
    receipt = helper.initiative_receipt(manifest, "slice-a", repo)
    args = helper.parser().parse_args([
        "begin", "--cycle-id", "local-1", "--context", "test", "--risk", "critical",
        "--delivery-intent", "draft_pr", "--plan", str(plan), "--base-branch", "main",
        "--github-account", "example", "--github-repository", "example/test",
        "--initiative-manifest", str(manifest.relative_to(repo)), "--initiative-slice", "slice-a",
        "--initiative-digest", receipt["manifest_digest"], "--expected-repository", "example/test",
        "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
    ])
    yield helper, fixture, args
    fixture.tearDown()


def test_unpublished_discovery_launch_preserves_source_and_records_import(launch, capsys):
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
    assert (worktree / args.initiative_manifest).exists()
    assert (worktree / "docs/specs/test/BACKLOG.md").read_text() == "Discovery-owned bounded context backlog\n"
    assert (worktree / "tracked.txt").read_text() == "base\n"
    assert (fixture.repo / "tracked.txt").read_text() == "unrelated dirty work\n"
    assert helper.git(fixture.repo, "rev-parse", "HEAD").stdout.strip() == source_head
    helper.verify_discovery_import(worktree, record)
    args.resume_existing = True
    helper.command_begin(args)
    assert json.loads(capsys.readouterr().out)["resumed"] is True


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
    with pytest.raises(RuntimeError, match="launch plan changed"):
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
    args.cycle_id = "unsafe-2"
    args.preflight = True
    with pytest.raises(RuntimeError):
        helper.command_begin(args)
    assert not (fixture.repo / ".git/dbsctr/cycles/unsafe-2.json").exists()


def test_native_adapter_uses_real_helper_for_unpublished_discovery(launch, tmp_path):
    helper, fixture, args = launch
    repo = fixture.repo
    remote = helper.git(repo, "remote", "get-url", "origin").stdout.strip()
    helper.git(repo, "remote", "set-url", "origin", "https://github.com/example/test.git")
    home = tmp_path / "home"
    database = home / ".local/share/opencode/opencode.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as db:
        db.executescript("CREATE TABLE session(id TEXT PRIMARY KEY,parent_id TEXT,agent TEXT);"
                         "CREATE TABLE message(id TEXT PRIMARY KEY,session_id TEXT,data TEXT);")
        db.execute("INSERT INTO session VALUES ('native-owner',NULL,'build')")
        db.execute("INSERT INTO message VALUES ('native-message','native-owner',?)", (
            json.dumps({"model": {"providerID": "openai", "modelID": "fixture-model"}}),))
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
g['main']()
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
    tools = fixtures.SCRIPT.parents[2] / "private_dot_config/opencode/tools/dbsctr.ts"
    script = f'''
import {{begin}} from {json.dumps(str(tools))};
const approvals=[];
const args={{
cycleId:"native-local",context:"test",risk:"critical",deliveryIntent:"draft_pr",
planPath:{json.dumps(args.plan)},githubAccount:"example",githubRepository:"example/test",
initiative:{{manifestPath:{json.dumps(args.initiative_manifest)},sliceId:"slice-a",proceed:true}}
}};
const context={{worktree:process.cwd(),directory:process.cwd(),sessionID:"native-owner",messageID:"native-message",
ask:async value=>approvals.push(value)}};
const preview=JSON.parse(await begin.execute({{...args,preflight:true}},context));
if(approvals.length!==0||!preview.launch_digest)throw Error("Preview requested approval");
const result=await begin.execute(args,context);
console.log(JSON.stringify({{result:JSON.parse(result),approvals}}));
'''
    result = subprocess.run([shutil.which("bun"), "-e", script], cwd=repo,
                            env={**fixtures.isolated_env(), "HOME": str(home),
                                 "PATH": f"{binary}:{os.environ['PATH']}",
                                 "DBSCTR_WORKTREE_ROOT": str(tmp_path / "worktrees")},
                            text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert len(value["approvals"]) == 1
    approved = json.loads(value["approvals"][0]["patterns"][0])
    assert approved["launch_digest"]
    record = helper.load(Path(value["result"]["worktree"]))[1]
    assert record["discovery_import"]["source_commit"] == approved["manifest_commit"]
    assert record["runtime"]["opencode"]["session_ids"] == ["native-owner"]
