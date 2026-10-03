"""Worktrunk eligibility is read-only and never treats missing evidence as safe."""
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys

import pytest
import test_dbsctrctl as harness
from test_worktrunk_registration import fixture, git, task


@pytest.fixture
def removal(fixture, monkeypatch):
    target = task(fixture)
    loader = importlib.machinery.SourceFileLoader("workspace_removal", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.setattr(core, "workspace_processes", lambda _root: [])
    return core, fixture.repo, target


def test_clean_code_only_checkout_can_be_removed_without_a_cycle(removal):
    core, primary, target = removal
    before = git(primary, "worktree", "list", "--porcelain")
    assert core.workspace_remove_check(target)["eligible"] is True
    assert git(primary, "worktree", "list", "--porcelain") == before
    assert target.is_dir()


@pytest.mark.parametrize("problem", ["primary", "dirty", "ignored", "undelivered", "process"])
def test_preservation_blockers_refuse_without_removing_files(removal, monkeypatch, problem):
    core, primary, target = removal
    if problem == "primary":
        target = primary
    elif problem == "dirty":
        (target / "tracked.txt").write_text("retain dirty work\n")
    elif problem == "ignored":
        (target / ".gitignore").write_text("private-data\n")
        git(target, "add", ".gitignore")
        git(target, "commit", "-m", "ignore data")
        git(primary, "merge", "--ff-only", "task")
        (target / "private-data").write_bytes(b"unique data")
    elif problem == "undelivered":
        git(target, "commit", "--allow-empty", "-m", "unmerged task")
    else:
        monkeypatch.setattr(core, "workspace_processes", lambda _root: [123])
    result = core.workspace_remove_check(target)
    assert result["eligible"] is False
    assert result["reasons"]
    assert target.is_dir()
    if problem == "ignored":
        assert (target / "private-data").read_bytes() == b"unique data"


def test_unavailable_process_inventory_is_not_an_empty_inventory(removal, monkeypatch):
    core, _, target = removal

    def unavailable(_root):
        raise RuntimeError("process inventory unavailable")

    monkeypatch.setattr(core, "workspace_processes", unavailable)
    result = core.workspace_remove_check(target)
    assert result["eligible"] is False
    assert "process_inventory_unavailable" in result["reasons"]


def test_active_cycle_blocks_removal_even_when_git_is_clean(removal, fixture):
    core, _, target = removal
    harness.run(target, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
                "--delivery-intent", "local", "--plan", str(fixture.plan_path()))
    before = fixture.record_path().read_bytes()
    assert "active_cycle" in core.workspace_remove_check(target)["reasons"]
    assert fixture.record_path().read_bytes() == before


def test_native_dvc_status_distinguishes_absence_from_modified_data(removal):
    core, _, target = removal
    assert core.removal_dvc_paths(target, {"uncommitted": {"deleted": ["dataset/"]}}) == []
    assert core.removal_dvc_paths(target, {"unchanged": ["dataset/"]}) == ["dataset/"]
    for status in ({"uncommitted": {"modified": ["dataset/"]}}, {"committed": {"added": ["data"]}},
                   {"unknown": []}, {"unchanged": ["../escape"]}):
        with pytest.raises(RuntimeError):
            core.removal_dvc_paths(target, status)
    (target / "dataset").mkdir()
    with pytest.raises(RuntimeError):
        core.removal_dvc_paths(target, {"not_in_cache": ["dataset/"]})


@pytest.mark.skipif(shutil.which("lsof") is None, reason="native process inventory is unavailable")
def test_cli_eligibility_does_not_remove_checkout(fixture):
    target = task(fixture)
    result = json.loads(harness.run(target, "workspace-remove-check", "--json").stdout)
    assert result["eligible"] is True
    assert target.is_dir()


@pytest.mark.skipif(shutil.which("lsof") is None, reason="native process inventory is unavailable")
def test_open_file_process_blocks_even_when_its_cwd_is_elsewhere(fixture):
    target = task(fixture)
    code = "import sys,signal; f=open(sys.argv[1]); print('ready',flush=True); signal.pause()"
    with subprocess.Popen([sys.executable, "-c", code, str(target / "tracked.txt")], cwd=fixture.repo,
                          stdout=subprocess.PIPE, text=True) as child:
        try:
            assert child.stdout.readline().strip() == "ready"
            result = json.loads(harness.run(target, "workspace-remove-check", "--json", ok=False).stdout)
            assert "running_processes" in result["reasons"]
            assert target.is_dir()
        finally:
            child.terminate()
            child.wait(timeout=5)


@pytest.mark.parametrize("payload", [b"", b"unclassified inventory\0", b"p123\0xunknown\0"])
def test_empty_or_malformed_native_inventory_cannot_authorize_removal(fixture, tmp_path, payload):
    target = task(fixture)
    program = tmp_path / "lsof"
    program.write_text(f"#!{sys.executable}\nimport os\nos.write(1, {payload!r})\n")
    program.chmod(0o700)
    environment = harness.isolated_env()
    environment["PATH"] = str(tmp_path) + ":" + environment.get("PATH", "/usr/bin:/bin")
    response = harness.run(target, "workspace-remove-check", "--json", ok=False, env=environment)
    assert "process_inventory_unavailable" in json.loads(response.stdout)["reasons"]
    assert target.is_dir()


def test_native_evidence_overflow_stops_before_child_finishes(removal, tmp_path):
    core, _, target = removal
    marker = tmp_path / "should-not-finish"
    code = "import os,sys; from pathlib import Path; os.write(1,b'x'*(2*1024*1024)); Path(sys.argv[1]).touch()"
    with pytest.raises(RuntimeError, match="preservation evidence"):
        core.removal_run(target, [sys.executable, "-c", code, str(marker)])
    assert not marker.exists(), "output must be bounded while reading, not after communicate buffers everything"
