"""Operator adoption preserves the original cycle, dirty work and failed evidence."""
import importlib.machinery
import importlib.util
import io
import json
import contextlib
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    case = harness.DbsctrctlTest()
    case.setUp()
    try:
        target = case.repo.parent / "task"
        subprocess.run(["git", "worktree", "add", "-b", "task", str(target)], cwd=case.repo,
                       capture_output=True, check=True)
        harness.run(target, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
                    "--delivery-intent", "local", "--plan", str(case.plan_path()))
        path = case.record_path()
        record = json.loads(path.read_text())
        record.pop("execution", None)  # Model an existing record, not a new native cycle.
        record["worktree"].pop("git_dir", None)
        record["gates"]["test_driven_implementation"]["result"] = "failed"
        path.write_text(json.dumps(record, indent=2) + "\n")
        (target / "tracked.txt").write_text("dirty user work\n")
        (target / "untracked.txt").write_text("retain this too\n")
        loader = importlib.machinery.SourceFileLoader("workspace_adoption", str(harness.SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        core = importlib.util.module_from_spec(spec)
        loader.exec_module(core)
        monkeypatch.chdir(target)
        yield core, target, path, path.read_bytes()
    finally:
        monkeypatch.undo()
        case.tearDown()


def args(preview=False, digest=None):
    return SimpleNamespace(cycle_id="cycle-1", preview=preview, json=True, expected_state=digest)


def preview(core, capsys):
    core.command_workspace_adopt(args(preview=True))
    return json.loads(capsys.readouterr().out)


class Operator(io.StringIO):
    def isatty(self):
        return True


def test_preview_is_read_only_and_noninteractive_apply_refuses(legacy, monkeypatch, capsys):
    core, _, path, before = legacy
    value = preview(core, capsys)
    assert value["requires_operator_confirmation"] is True
    assert value["unresolved_legacy_operations"] is None
    assert path.read_bytes() == before
    monkeypatch.setattr(core.sys, "stdin", io.StringIO("ADOPT\n"))
    with pytest.raises(RuntimeError, match="interactive"):
        core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert path.read_bytes() == before


def test_adoption_preserves_original_record_and_work(legacy, monkeypatch, capsys):
    core, target, path, before = legacy
    value = preview(core, capsys)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    updated = json.loads(path.read_text())
    execution = updated.pop("execution")
    assert updated["worktree"].pop("git_dir") == core.git_dir(target).resolve().relative_to(core.common_git_dir(target).resolve()).as_posix()
    assert updated == json.loads(before)
    assert execution["origin"] == "adopted"
    backup = core.common_git_dir(target) / execution["adoption"]["record_backup"]
    assert backup.read_bytes() == before
    assert (target / "tracked.txt").read_text() == "dirty user work\n"
    assert (target / "untracked.txt").read_text() == "retain this too\n"
    assert updated["gates"]["test_driven_implementation"]["result"] == "failed"


def test_stale_preview_does_not_mutate(legacy, monkeypatch, capsys):
    core, _, path, _ = legacy
    value = preview(core, capsys)
    changed = json.loads(path.read_text())
    changed["metrics"]["gate_failure_count"] += 1
    path.write_text(json.dumps(changed))
    before = path.read_bytes()
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    with pytest.raises(RuntimeError, match="changed"):
        core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert path.read_bytes() == before


@pytest.mark.parametrize("schema", [3, 4])
def test_older_records_adopt_without_schema_upgrade(legacy, monkeypatch, capsys, schema):
    core, target, path, _ = legacy
    record = json.loads(path.read_text())
    record["schema_version"] = schema
    if schema == 3:
        record["worktree"].pop("locator")
        record["worktree"].update(path=str(target), git_dir=str(core.git_dir(target).resolve()),
                                  id=core.legacy_worktree_id(target))
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    value = preview(core, capsys)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    adopted = json.loads(path.read_text())
    assert adopted["schema_version"] == schema
    assert adopted["cycle_id"] == record["cycle_id"]
    assert adopted["gates"] == record["gates"]
    assert core.record_worktree_matches(target, adopted, target)
    assert core.record_worktree(target, adopted) == target.resolve()
    backup = core.common_git_dir(target) / adopted["execution"]["adoption"]["record_backup"]
    assert backup.read_bytes() == before


def test_failed_record_write_keeps_preimage_and_retry_is_safe(legacy, monkeypatch, capsys):
    core, _, path, before = legacy
    value = preview(core, capsys)
    original = core.private_json
    monkeypatch.setattr(core, "private_json", lambda *_: (_ for _ in ()).throw(OSError("synthetic interruption")))
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    with pytest.raises(OSError, match="synthetic interruption"):
        core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert path.read_bytes() == before
    backups = list((path.parent.parent / "migrations").glob("*.native-before.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == before
    monkeypatch.setattr(core, "private_json", original)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert json.loads(path.read_text())["execution"]["origin"] == "adopted"


def test_state_is_rechecked_after_operator_confirmation(legacy, monkeypatch, capsys):
    core, _, path, _ = legacy
    value = preview(core, capsys)

    class ChangingOperator(Operator):
        def readline(self, *_):
            changed = json.loads(path.read_text())
            changed["metrics"]["gate_failure_count"] += 1
            path.write_text(json.dumps(changed))
            return f"ADOPT cycle-1 {value['state_digest']}\n"

    monkeypatch.setattr(core.sys, "stdin", ChangingOperator())
    with pytest.raises(RuntimeError, match="changed"):
        core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert "execution" not in json.loads(path.read_text())


def test_uncertain_operation_evidence_is_retained_not_completed(legacy, monkeypatch, capsys):
    core, _, _, _ = legacy
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE cycles(cycle_id TEXT, writer TEXT);
        CREATE TABLE operations(operation_id TEXT, cycle_id TEXT, state TEXT, completion_class TEXT);
        CREATE TABLE activations(event_id INTEGER, cycle_id TEXT, session_key TEXT);
        CREATE TABLE routes(session_key TEXT, cycle_id TEXT);
        CREATE TABLE approvals(receipt_id TEXT, cycle_id TEXT);
        INSERT INTO cycles VALUES ('cycle-1','old-writer');
        INSERT INTO operations VALUES ('op-1','cycle-1','running','unknown_completion');
    """)

    @contextlib.contextmanager
    def connection(_root):
        yield db

    monkeypatch.setattr(core, "continuation_connection", connection)
    try:
        before = list(db.iterdump())
        value = preview(core, capsys)
        assert value["unresolved_legacy_operations"] == 1
        monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
        core.command_workspace_adopt(args(digest=value["state_digest"]))
        assert list(db.iterdump()) == before
    finally:
        db.close()


def test_changed_legacy_route_invalidates_preview_without_mutation(legacy, monkeypatch, capsys):
    core, target, path, before = legacy
    with core.continuation_connection(target, write=True, create=True) as db:
        db.execute("INSERT INTO cycles VALUES (?,?,?,?,?,?,?,?)",
                   ("cycle-1", core.worktree_id(target), core.worktree_id(target), "a" * 64,
                    None, 1, "reader_only", None))
        db.execute("INSERT INTO routes VALUES (?,?,?,?,?)",
                   ("session-key", "session", "cycle-1", core.worktree_id(target), None))
        core.continuation_v2_schema(db, create=True)
        db.execute("INSERT INTO route_versions VALUES (?,?)", ("session-key", 1))
    value = preview(core, capsys)
    assert value["unresolved_legacy_operations"] == 0
    with core.continuation_connection(target, write=True) as db:
        db.execute("UPDATE route_versions SET version=2 WHERE session_key='session-key'")
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    with pytest.raises(RuntimeError, match="changed"):
        core.command_workspace_adopt(args(digest=value["state_digest"]))
    assert path.read_bytes() == before


def test_unverifiable_adoption_marker_is_not_treated_as_valid(legacy, monkeypatch, capsys):
    core, target, path, _ = legacy
    value = preview(core, capsys)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    execution = json.loads(path.read_text())["execution"]
    (core.common_git_dir(target) / execution["adoption"]["record_backup"]).unlink()
    with pytest.raises(RuntimeError, match="backup"):
        core.command_workspace_adopt(args(preview=True))


def test_cli_preview_and_noninteractive_refusal(legacy):
    _, target, path, before = legacy
    value = json.loads(harness.run(target, "workspace-adopt", "--cycle-id", "cycle-1", "--preview", "--json").stdout)
    rejected = harness.run(target, "workspace-adopt", "--cycle-id", "cycle-1",
                           "--expected-state", value["state_digest"], input_text="ADOPT\n", ok=False)
    assert "interactive" in rejected.stderr
    assert path.read_bytes() == before


def test_unregistered_checkout_cannot_adopt(legacy, tmp_path, monkeypatch):
    core, target, path, before = legacy
    alias = tmp_path / "unregistered"
    alias.mkdir()
    (alias / ".git").write_text(f"gitdir: {core.git_dir(target).resolve()}\n")
    monkeypatch.chdir(alias)
    with pytest.raises(RuntimeError, match="registered"):
        core.command_workspace_adopt(args(preview=True))
    assert path.read_bytes() == before
