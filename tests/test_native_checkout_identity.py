"""Branch names and retired continuation rows cannot redirect native cycles."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def native(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
    loader = importlib.machinery.SourceFileLoader("native_checkout_identity", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    main = tmp_path / "main"
    main.mkdir()
    for argv in (("init", "-b", "main"), ("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
                 "commit", "--allow-empty", "-m", "fixture")):
        subprocess.run(["git", *argv], cwd=main, check=True, capture_output=True)
    task = tmp_path / "task"
    subprocess.run(["git", "worktree", "add", "-b", "task", str(task)], cwd=main,
                   check=True, capture_output=True)
    record = {"schema_version": 5, "cycle_id": "native-1", "state": "active",
              "worktree": {"id": core.worktree_id(task), "branch": "task",
                  "locator": {"root": "cycle_worktree", "path": "."},
                  "git_dir": core.git_dir(task).resolve().relative_to(core.common_git_dir(task).resolve()).as_posix()},
              "execution": {"schema_version": 1, "mode": "native_workspace", "origin": "registered",
                  "attribution": {"status": "unavailable", "reason": "native_identity_not_collected"}, "adoption": None}}

    def no_legacy(*_args, **_kwargs):
        raise AssertionError("native checkout resolution must not consult retired routing")

    monkeypatch.setattr(core, "continuation_connection", no_legacy)
    return core, main, task, record


def test_native_cycle_resolves_through_git_not_legacy_routing(native):
    core, main, task, record = native
    assert core.record_worktree(main, record) == task.resolve()
    assert core.record_worktree_matches(main, record, task)


def test_historical_source_removal_does_not_retarget_native_checkout(native, tmp_path):
    core, main, task, record = native
    source = tmp_path / "historical-source"
    subprocess.run(["git", "worktree", "add", "-b", "launch-source", str(source)], cwd=main,
                   check=True, capture_output=True)
    record["source"] = {"id": core.worktree_id(source), "branch": "launch-source",
                        "locator": {"root": "primary_worktree", "path": "."}}
    before = json.dumps(record, sort_keys=True)
    subprocess.run(["git", "worktree", "remove", str(source)], cwd=main, check=True, capture_output=True)
    assert core.record_worktree(main, record) == task.resolve()
    assert core.record_worktree_matches(main, record, task)
    assert json.dumps(record, sort_keys=True) == before


def test_reused_branch_does_not_redirect_cycle_to_another_checkout(native, tmp_path):
    core, main, task, record = native
    subprocess.run(["git", "switch", "-c", "different-task"], cwd=task, check=True, capture_output=True)
    other = tmp_path / "other"
    subprocess.run(["git", "worktree", "add", str(other), "task"], cwd=main, check=True, capture_output=True)
    assert not core.record_worktree_matches(main, record, other)
    assert not core.record_worktree_matches(main, record, task)
    with pytest.raises(RuntimeError, match="branch changed"):
        core.record_worktree(other, record)


def test_duplicate_branch_does_not_share_cycle_identity(native, tmp_path):
    core, main, task, record = native
    other = tmp_path / "duplicate"
    subprocess.run(["git", "worktree", "add", "--force", str(other), "task"], cwd=main,
                   check=True, capture_output=True)
    assert core.record_worktree(other, record) == task.resolve()
    assert not core.record_worktree_matches(main, record, other)


def test_unregistered_checkout_cannot_borrow_a_registered_git_directory(native, tmp_path):
    core, main, task, record = native
    alias = tmp_path / "unregistered"
    alias.mkdir()
    (alias / ".git").write_text(f"gitdir: {core.git_dir(task).resolve()}\n")
    assert not core.record_worktree_matches(main, record, alias)


def test_unsafe_or_missing_admin_binding_refuses(native):
    core, main, _, record = native
    for binding in (None, "../outside", "/outside", "."):
        record["worktree"]["git_dir"] = binding
        with pytest.raises(RuntimeError, match="native worktree"):
            core.record_worktree(main, record)


def test_git_inventory_tracks_moved_checkout_without_a_second_registry(native, tmp_path):
    core, main, task, record = native
    moved = tmp_path / "moved"
    subprocess.run(["git", "worktree", "move", str(task), str(moved)], cwd=main,
                   check=True, capture_output=True)
    assert core.record_worktree(main, record) == moved.resolve()
    assert core.record_worktree_matches(main, record, moved)


def test_schema_three_adoption_retains_absolute_admin_provenance(native):
    core, main, task, record = native
    record["schema_version"] = 3
    record["execution"]["origin"] = "adopted"
    record["execution"]["adoption"] = {"before_sha256": "a" * 64, "state_digest": "b" * 64,
        "record_backup": "dbsctr/migrations/native-1." + "a" * 64 + ".native-before.json"}
    record["worktree"]["git_dir"] = str(core.git_dir(task).resolve())
    assert core.record_worktree(main, record) == task.resolve()
    assert core.record_worktree_matches(main, record, task)
