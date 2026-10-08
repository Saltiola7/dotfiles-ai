"""Retire only an explicitly confirmed superseded empty detached registration."""
import io
import json
from types import SimpleNamespace

import pytest

from test_workspace_adoption import Operator, legacy


@pytest.fixture
def orphan(legacy):
    core, root, path, _ = legacy
    record = json.loads(path.read_text())
    record.update(schema_version=4, source=None)
    record.pop("runtime", None)
    record["worktree"].update(branch=None, created_by_dbsctr=False,
                               locator={"root": "cycle_worktree", "path": "."})
    core.private_json(path, record)
    successor = {**record, "cycle_id": "successor", "state": "completed",
                 "commits": [{"id": core.git(root, "rev-parse", "HEAD").stdout.strip()}]}
    core.private_json(path.with_name("successor.json"), successor)
    return core, root, path, path.read_bytes()


def arguments(digest=None, preview=False):
    return SimpleNamespace(cycle_id="cycle-1", superseded_by="successor",
                           expected_state=digest, preview=preview)


def test_preview_and_noninteractive_refusal_preserve_record(orphan, monkeypatch, capsys):
    core, _, path, before = orphan
    core.command_workspace_recover_orphan(arguments(preview=True))
    preview = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(core.sys, "stdin", io.StringIO())
    with pytest.raises(RuntimeError, match="interactive"):
        core.command_workspace_recover_orphan(arguments(preview["state_digest"]))
    assert path.read_bytes() == before


def test_confirmed_recovery_preserves_evidence_work_and_preimage(orphan, monkeypatch):
    core, root, path, before = orphan
    fresh = root.parent / "fresh-checkout"
    core.git(root, "worktree", "add", "-b", "fresh", str(fresh))
    with pytest.raises(RuntimeError, match="cycle worktree is missing"):
        core.require_registration_available(fresh, "new-cycle")
    digest = core.orphan_recovery_snapshot(root, "cycle-1", "successor")[3]
    monkeypatch.setattr(core.sys, "stdin", Operator(f"RETIRE-ORPHAN cycle-1 {digest}\n"))
    core.command_workspace_recover_orphan(arguments(digest))
    updated = json.loads(path.read_text())
    retirement = updated.pop("retirement")
    updated.pop("retired_at")
    assert updated.pop("state") == "retired"
    original = json.loads(before)
    original.pop("state")
    assert updated == original
    assert (core.common_git_dir(root) / retirement["record_backup"]).read_bytes() == before
    assert (root / "tracked.txt").read_text() == "dirty user work\n"
    assert (root / "untracked.txt").read_text() == "retain this too\n"
    core.require_registration_available(fresh, "new-cycle")


@pytest.mark.parametrize("change", ["commits", "branch", "successor", "detached"])
def test_recovery_rejects_possible_owned_or_unsuperseded_work(orphan, monkeypatch, change):
    core, root, path, _ = orphan
    record = json.loads(path.read_text())
    if change == "commits":
        record["commits"] = [{"id": record["git"]["head"]}]
    elif change == "branch":
        record["worktree"]["branch"] = "task"
    elif change == "successor":
        successor_path = path.with_name("successor.json")
        successor = json.loads(successor_path.read_text())
        successor["state"] = "active"
        core.private_json(successor_path, successor)
    else:
        monkeypatch.setattr(core, "git_worktrees", lambda _: [{"HEAD": record["git"]["head"]}])
    core.private_json(path, record)
    before = path.read_bytes()
    with pytest.raises(RuntimeError):
        core.orphan_recovery_snapshot(root, "cycle-1", "successor")
    assert path.read_bytes() == before


def test_stale_confirmation_cannot_retire_changed_record(orphan, monkeypatch):
    core, root, path, _ = orphan
    digest = core.orphan_recovery_snapshot(root, "cycle-1", "successor")[3]
    record = json.loads(path.read_text())
    record["metrics"]["gate_failure_count"] += 1
    core.private_json(path, record)
    before = path.read_bytes()
    monkeypatch.setattr(core.sys, "stdin", Operator(f"RETIRE-ORPHAN cycle-1 {digest}\n"))
    with pytest.raises(RuntimeError, match="changed"):
        core.command_workspace_recover_orphan(arguments(digest))
    assert path.read_bytes() == before
