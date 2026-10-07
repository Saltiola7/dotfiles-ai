"""Adopted cycles execute locally without reviving historical admission state."""
import json
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness

from test_workspace_adoption import Operator, args, legacy, preview


@pytest.fixture
def adopted(legacy, monkeypatch, capsys):
    core, target, path, before = legacy
    with core.continuation_connection(target, write=True, create=True) as db:
        db.execute("INSERT INTO cycles VALUES (?,?,?,?,?,?,?,?)",
                   ("cycle-1", core.worktree_id(target), core.worktree_id(target), "b" * 64,
                    "a" * 64, 1, "owned", None))
        db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?)",
                   ("operation-1", "cycle-1", 1, "a" * 64, "msg-history", "call-history",
                    "file", "uncertain", "unknown_completion"))
    value = preview(core, capsys)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    capsys.readouterr()
    return core, target, path, before


def test_native_load_and_mutation_guard_do_not_consult_legacy_routing(adopted, monkeypatch):
    core, target, path, _ = adopted

    def forbidden(*_args, **_kwargs):
        raise AssertionError("retired routing consulted")

    monkeypatch.setattr(core, "continuation_connection", forbidden)
    assert core.load(target)[0].resolve() == path.resolve()
    core.continuation_guard(SimpleNamespace(command="set-gate"))


def test_native_mutation_refuses_missing_adoption_backup(adopted):
    core, target, path, _ = adopted
    record = json.loads(path.read_text())
    (core.common_git_dir(target) / record["execution"]["adoption"]["record_backup"]).unlink()
    with pytest.raises(RuntimeError, match="backup"):
        core.continuation_guard(SimpleNamespace(command="set-gate"))


@pytest.mark.parametrize("command", ["attach-runtime", "continuation-enroll", "continuation-v2",
                                     "cycle-portabilize", "cleanup", "cycle-retire-worktree"])
def test_native_cycles_reject_retired_execution_mutators(adopted, command):
    core, _, _, _ = adopted
    with pytest.raises(RuntimeError, match="retired"):
        core.continuation_guard(SimpleNamespace(command=command))


def test_legacy_snapshot_cannot_reenroll_adopted_cycle(adopted):
    core, _, path, _ = adopted
    record = json.loads(path.read_text())
    with pytest.raises(RuntimeError, match="retired"):
        core.continuation_snapshot(None, record, path, "actor", None, "enroll")


def test_v2_snapshot_cannot_restore_adopted_cycle_authority(adopted):
    core, target, _, _ = adopted
    with core.continuation_connection(target) as db:
        with pytest.raises(RuntimeError, match="retired"):
            core.continuation_v2_snapshot(db, target, {"action": "attach", "worktree": str(target)},
                                          "a" * 64, None, "attach")


def test_native_cli_preserves_uncertain_operations_during_gate_update(adopted):
    core, target, path, _ = adopted
    with core.continuation_connection(target) as db:
        before = list(db.iterdump())
    evidence = harness.run(target, "record-evidence", "domain", "--authority", "native-gate-check",
                           "--path", "docs/specs/test/README.md", "--", core.sys.executable,
                           "-c", "raise SystemExit(1)").stdout.strip()
    harness.run(target, "set-gate", "domain", "--result", "failed", "--evidence", evidence)
    record = json.loads(path.read_text())
    assert record["gates"]["domain"]["result"] == "failed"
    assert record["gates"]["test_driven_implementation"]["result"] == "failed"
    with core.continuation_connection(target) as db:
        assert list(db.iterdump()) == before


def test_status_labels_retained_runtime_as_historical(legacy, monkeypatch, capsys):
    core, target, path, _ = legacy
    record = json.loads(path.read_text())
    record["runtime"]["opencode"] = {"session_ids": ["historical-session"],
        "path_root": "cycle_worktree", "worktree": ".", "directory": "."}
    core.sync_schema5_opencode(record)
    path.write_text(json.dumps(record))
    value = preview(core, capsys)
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {value['state_digest']}\n"))
    core.command_workspace_adopt(args(digest=value["state_digest"]))
    before = path.read_bytes()
    status = json.loads(harness.run(target, "status", "--json").stdout)
    assert status["historical_runtime"] == record["runtime"]
    assert status["runtime"] == {"adapters": {}}
    assert status["execution"]["attribution"]["status"] == "unavailable"
    assert "attribution=unavailable" in harness.run(target, "status").stdout
    assert path.read_bytes() == before
