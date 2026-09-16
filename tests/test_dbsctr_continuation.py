"""Continuation admission contracts use disposable Git and native identity."""

import json
import runpy
import os
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest
import test_dbsctrctl as fixtures


@pytest.fixture
def cycle():
    fixture = fixtures.DbsctrctlTest()
    fixture.setUp()
    fixture.start()
    home = Path(fixture.temp.name) / "home"
    database = home / ".local/share/opencode/opencode.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE session (id TEXT PRIMARY KEY, parent_id TEXT, agent TEXT);
            CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT);
        """)
        for session, agent, parent in (("owner", "build", None), ("reader", "build", None),
                                       ("plan", "plan", None), ("child", "build", "owner")):
            connection.execute("INSERT INTO session VALUES (?,?,?)", (session, parent, agent))
            for suffix, provider, model in (("old", "openai", "model-one"),
                                             ("new", "openai", "model-two"),
                                             ("other", "google-vertex-anthropic", "model-three")):
                connection.execute("INSERT INTO message VALUES (?,?,?)", (
                    f"{session}-{suffix}", session,
                    json.dumps({"model": {"providerID": provider, "modelID": model}})))
    fixture.continuation_env = {**fixtures.isolated_env(), "HOME": str(home),
                                "DBSCTR_WORKTREE_ROOT": fixture.temp.name}
    fixture.native_database = database
    fixture.continuation_path = fixture.repo / ".git/dbsctr/continuation/continuation.sqlite3"
    fixture.request = {
        "schema_version": 1, "worktree": str(fixture.repo),
        "session_id": "owner", "message_id": "owner-old",
        "runtime_worktree": str(fixture.repo), "runtime_directory": str(fixture.repo),
        "harness_activation": {"schema_version": 1, "core_revision": "3.31", "overlays": {
            "build": "neutral-2026-07-26", "build-gpt": "openai-2026-07-26",
            "build-claude": "anthropic-2026-07-26"}},
    }
    yield fixture
    fixture.tearDown()


def call(cycle, command="check", *, ok=True, **changes):
    payload = {**cycle.request, **changes}
    result = fixtures.run(cycle.repo, f"continuation-{command}", "--request-json", "-",
                          ok=ok, env=cycle.continuation_env, input_text=json.dumps(payload))
    value = json.loads(result.stdout)
    assert value["ok"] is ok
    assert str(cycle.repo) not in result.stdout
    assert str(cycle.native_database) not in result.stdout
    assert result.stderr == ""
    return value


def approve(cycle, action, **changes):
    check = call(cycle, action=action, **changes)
    return {"receipt_id": "receipt-" + os.urandom(12).hex(), "binding": check["approval_binding"]}


def enroll(cycle):
    call(cycle, "enroll", approval=approve(cycle, "enroll"))
    return call(cycle, "attach", mode="writer", generation=0)


def test_continuation_read_only_and_model_resume_preserve_record(cycle):
    original = cycle.record_path().read_bytes()
    native = cycle.native_database.read_bytes()
    check = call(cycle)
    assert check["reason"] == "not_enrolled"
    assert not cycle.continuation_path.parent.exists()
    first = enroll(cycle)
    assert first["generation"] == 1
    changed = call(cycle, "attach", mode="writer", generation=1, message_id="owner-new")
    assert changed["activation_changes"] == ["model_id"]
    assert changed["generation"] == 1
    assert call(cycle, "attach", mode="writer", generation=1,
                message_id="owner-new")["event_id"] == changed["event_id"]
    assert cycle.record_path().read_bytes() == original
    assert cycle.native_database.read_bytes() == native
    assert cycle.continuation_path.stat().st_mode & 0o077 == 0
    assert cycle.continuation_path.parent.stat().st_mode & 0o077 == 0


def test_continuation_readers_do_not_steal_writer(cycle):
    enroll(cycle)
    read = call(cycle, "attach", mode="reader", generation=1,
                session_id="reader", message_id="reader-old")
    assert read["writer_relation"] == "other"
    denied = call(cycle, "attach", mode="writer", generation=1,
                  session_id="reader", message_id="reader-old", ok=False)
    assert denied["reason"] == "writer_occupied"
    assert call(cycle)["writer_relation"] == "self"


def test_continuation_handover_drains_and_fences(cycle):
    enroll(cycle)
    operation = call(cycle, "admit", generation=1, call_id="call-one", operation_class="lifecycle")
    repeated = call(cycle, "admit", generation=1, call_id="call-one", operation_class="lifecycle")
    assert repeated["operation_id"] == operation["operation_id"]
    approval = approve(cycle, "handover", target_session_id="reader")
    draining = call(cycle, "handover", generation=1, target_session_id="reader", approval=approval)
    assert draining["state"] == "draining"
    assert call(cycle, "admit", generation=1, call_id="call-two", operation_class="file",
                ok=False)["reason"] == "operation_in_flight"
    call(cycle, "finish", operation_id=operation["operation_id"], outcome="completed")
    approval = approve(cycle, "handover", target_session_id="reader")
    result = call(cycle, "handover", generation=1, target_session_id="reader", approval=approval)
    assert result["generation"] == 2
    assert call(cycle, "admit", generation=1, call_id="stale", operation_class="file",
                ok=False)["reason"] == "generation_changed"
    call(cycle, "attach", mode="writer", generation=2, session_id="reader", message_id="reader-new")


def test_continuation_uncertain_operation_requires_bound_recovery(cycle):
    enroll(cycle)
    operation = call(cycle, "admit", generation=1, call_id="uncertain", operation_class="shell")
    call(cycle, "finish", operation_id=operation["operation_id"], outcome="uncertain")
    assert call(cycle)["state"] == "recovery_required"
    assert call(cycle, "admit", generation=1, call_id="next", operation_class="file",
                ok=False)["reason"] == "recovery_required"
    approval = approve(cycle, "recover")
    result = call(cycle, "recover", generation=1, approval=approval)
    assert result["state"] == "reader_only"
    assert result["generation"] == 2
    assert call(cycle, "recover", generation=1, approval=approval)["generation"] == 2
    assert call(cycle, "finish", operation_id=operation["operation_id"], outcome="completed",
                ok=False)["reason"] == "generation_changed"


@pytest.mark.parametrize("session,message", [("plan", "plan-old"), ("child", "child-old"),
                                            ("owner", "reader-old")])
def test_continuation_rejects_invalid_native_mutators_before_creation(cycle, session, message):
    approval = approve(cycle, "enroll")
    result = call(cycle, "enroll", session_id=session, message_id=message, approval=approval, ok=False)
    assert result["reason"] == "invalid_identity"
    assert not cycle.continuation_path.exists()


def test_continuation_approval_race_and_provider_transition(cycle):
    enroll(cycle)
    approval = approve(cycle, "attach", message_id="owner-other")
    operation = call(cycle, "admit", generation=1, call_id="race", operation_class="file")
    assert call(cycle, "attach", mode="writer", generation=1, message_id="owner-other",
                approval=approval, ok=False)["reason"] == "approval_required"
    call(cycle, "finish", operation_id=operation["operation_id"], outcome="completed")
    assert call(cycle, "attach", mode="writer", generation=1, message_id="owner-other",
                ok=False)["reason"] == "provider_confirmation_required"
    approval = approve(cycle, "attach", message_id="owner-other")
    assert call(cycle, "attach", mode="writer", generation=1, message_id="owner-other",
                approval=approval)["generation"] == 1


def test_continuation_rejects_unknown_payload_without_creating_state(cycle):
    assert call(cycle, unknown="value", ok=False)["reason"] == "invalid_state"
    assert not cycle.continuation_path.exists()


def test_continuation_common_repository_not_remote_identity(cycle):
    linked = Path(cycle.temp.name) / "linked"
    subprocess.run(["git", "worktree", "add", "-b", "sibling", str(linked)],
                   cwd=cycle.repo, check=True, capture_output=True)
    cycle.request.update(runtime_worktree=str(linked), runtime_directory=str(linked))
    enroll(cycle)
    outsider = Path(cycle.temp.name) / "outsider"
    subprocess.run(["git", "clone", "--quiet", str(cycle.repo), str(outsider)], check=True)
    result = call(cycle, runtime_worktree=str(outsider), runtime_directory=str(outsider), ok=False)
    assert result["reason"] == "repository_mismatch"


def test_continuation_blocks_unmediated_legacy_mutation(cycle):
    enroll(cycle)
    before = cycle.record_path().read_bytes()
    blocked = fixtures.run(cycle.repo, "set-gate", "domain", "--result", "failed",
                           env=cycle.continuation_env, ok=False)
    assert "continuation_admission_required" in blocked.stderr
    assert cycle.record_path().read_bytes() == before
    operation = call(cycle, "admit", generation=1, call_id="lifecycle", operation_class="lifecycle")
    env = {**cycle.continuation_env, "DBSCTR_CONTINUATION_OPERATION": operation["operation_id"]}
    fixtures.run(cycle.repo, "set-gate", "domain", "--result", "pending", env=env)
    call(cycle, "finish", operation_id=operation["operation_id"], outcome="completed")
    assert fixtures.run(cycle.repo, "set-gate", "domain", "--result", "pending", env=env,
                        ok=False).returncode


def test_continuation_unsafe_storage_is_not_followed(cycle):
    target = Path(cycle.temp.name) / "outside"
    target.mkdir()
    cycle.continuation_path.parent.symlink_to(target, target_is_directory=True)
    assert call(cycle, ok=False)["reason"] == "invalid_state"
    assert list(target.iterdir()) == []


def test_continuation_plan_can_inspect_without_mutation(cycle):
    result = call(cycle, session_id="plan", message_id="plan-old")
    assert result["next_action"] == "switch_to_build"
    assert not cycle.continuation_path.exists()


@pytest.mark.parametrize("approval", [None, [], True, {"receipt_id": "only"}])
def test_continuation_malformed_approval_is_bounded_and_read_only(cycle, approval):
    assert call(cycle, "enroll", approval=approval, ok=False)["reason"] == "approval_required"
    assert not cycle.continuation_path.exists()


def test_continuation_finish_after_finalization_closes_ownership(cycle):
    enroll(cycle)
    operation = call(cycle, "admit", generation=1, call_id="finalize", operation_class="lifecycle")
    record = json.loads(cycle.record_path().read_text())
    record.update(state="completed", completed_at=record["created_at"])
    cycle.record_path().write_text(json.dumps(record))
    assert call(cycle, "finish", operation_id=operation["operation_id"], outcome="completed")["state"] == "closed"
    assert call(cycle, ok=False)["reason"] == "invalid_target"


def test_continuation_handover_rejects_nonprimary_target(cycle):
    enroll(cycle)
    approval = approve(cycle, "handover", target_session_id="child")
    assert call(cycle, "handover", generation=1, target_session_id="child", approval=approval,
                ok=False)["reason"] == "invalid_identity"
    assert call(cycle)["writer_relation"] == "self"


def test_continuation_history_retains_sessions_but_withholds_single_model(cycle, monkeypatch):
    enroll(cycle)
    call(cycle, "attach", mode="writer", generation=1, message_id="owner-new")
    module = runpy.run_path(str(fixtures.SCRIPT))
    for key in fixtures.STATE_ENVIRONMENT:
        monkeypatch.delenv(key, raising=False)
    for key, value in cycle.continuation_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(cycle.repo)
    projection = module["continuation_runtime"](cycle.repo, "cycle-1")
    assert projection["activation"] is None
    assert projection["session_ids"] == ["owner"]
    correlated, quality = module["correlated_cycles"](str(cycle.repo), [], exact_session_id="owner", with_quality=True)
    assert quality == "exact"
    assert len(correlated) == 1
    assert "harness_activation" not in correlated[0]


def test_continuation_current_agent_is_checked_at_legacy_mutation(cycle):
    enroll(cycle)
    operation = call(cycle, "admit", generation=1, call_id="before-switch", operation_class="lifecycle")
    with sqlite3.connect(cycle.native_database) as db:
        db.execute("UPDATE session SET agent='plan' WHERE id='owner'")
    env = {**cycle.continuation_env, "DBSCTR_CONTINUATION_OPERATION": operation["operation_id"]}
    result = fixtures.run(cycle.repo, "set-gate", "domain", "--result", "pending", env=env, ok=False)
    assert "invalid_identity" in result.stderr


def test_continuation_stale_route_does_not_fall_back_to_home(cycle):
    enroll(cycle)
    record = json.loads(cycle.record_path().read_text())
    record.update(state="completed", completed_at=record["created_at"])
    cycle.record_path().write_text(json.dumps(record))
    request = cycle.request.pop("worktree")
    try:
        assert call(cycle, ok=False)["reason"] == "invalid_target"
    finally:
        cycle.request["worktree"] = request


@pytest.mark.parametrize("schema", [3, 4, 5])
def test_continuation_legacy_records_remain_byte_identical_and_routes_resume(cycle, schema):
    if schema == 3:
        cycle.make_schema3_fixture("cycle-1", cycle.repo)
    elif schema == 4:
        record = json.loads(cycle.record_path().read_text())
        record["schema_version"] = 4
        record.pop("runtime", None)
        cycle.record_path().write_text(json.dumps(record))
    before = cycle.record_path().read_bytes()
    enroll(cycle)
    cycle.request.pop("worktree")
    assert call(cycle)["writer_relation"] == "self"
    assert call(cycle, "admit", generation=1, call_id="resume", operation_class="file")["operation_id"]
    assert cycle.record_path().read_bytes() == before


def test_continuation_readers_do_not_change_writer_activation(cycle):
    enroll(cycle)
    approval = approve(cycle, "attach", mode="reader", session_id="reader", message_id="reader-other")
    call(cycle, "attach", mode="reader", generation=1, session_id="reader", message_id="reader-other",
         approval=approval)
    result = call(cycle, "attach", mode="writer", generation=1)
    assert result["activation_changes"] == []


def test_continuation_database_contention_is_bounded(cycle, monkeypatch):
    enroll(cycle)
    module = runpy.run_path(str(fixtures.SCRIPT))
    # Measure lock acquisition, not unrelated Git subprocess startup under host load.
    monkeypatch.setitem(module["continuation_connection"].__wrapped__.__globals__,
                        "cycle_dir", lambda root: cycle.repo / ".git/dbsctr")
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        with pytest.raises(module["ContinuationError"], match="state_busy"):
            with module["continuation_connection"](cycle.repo, write=True):
                pytest.fail("writer entered a locked transaction")
        assert time.monotonic() - started < 3
    assert call(cycle)["state"] == "owned"


def test_continuation_failed_transaction_does_not_consume_approval(cycle):
    enroll(cycle)
    approval = approve(cycle, "handover", target_session_id="missing")
    call(cycle, "handover", generation=1, target_session_id="missing", approval=approval, ok=False)
    with sqlite3.connect(cycle.continuation_path) as db:
        assert db.execute("SELECT 1 FROM approvals WHERE receipt_id=?", (approval["receipt_id"],)).fetchone() is None
    assert call(cycle)["generation"] == 1


def test_continuation_rejects_foreign_keys_and_insecure_storage(cycle):
    enroll(cycle)
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("UPDATE routes SET cycle_id='missing'")
    assert call(cycle, ok=False)["reason"] == "invalid_state"
    cycle.continuation_path.chmod(0o644)
    assert call(cycle, ok=False)["reason"] == "invalid_state"


def test_continuation_handover_does_not_approve_provider_change(cycle):
    enroll(cycle)
    approval = approve(cycle, "handover", target_session_id="reader")
    call(cycle, "handover", generation=1, target_session_id="reader", approval=approval)
    assert call(cycle, "attach", mode="writer", generation=2, session_id="reader", message_id="reader-other",
                ok=False)["reason"] == "provider_confirmation_required"


def test_continuation_unknown_harness_revision_is_not_compatible(cycle):
    approval = approve(cycle, "enroll")
    activation = {**cycle.request["harness_activation"], "core_revision": "future"}
    assert call(cycle, "enroll", harness_activation=activation, approval=approval,
                ok=False)["reason"] == "revision_incompatible"
    assert not cycle.continuation_path.exists()


def test_continuation_distinct_cycles_have_distinct_writers(cycle):
    enroll(cycle)
    linked = Path(cycle.temp.name) / "second-cycle"
    subprocess.run(["git", "worktree", "add", "-b", "second-cycle", str(linked)],
                   cwd=cycle.repo, check=True, capture_output=True)
    fixtures.run(linked, "start", "--cycle-id", "cycle-2", "--context", "test", "--risk", "routine",
                 "--delivery-intent", "local", "--plan", str(cycle.plan_path()), env=cycle.continuation_env)
    second = {"worktree": str(linked), "session_id": "reader", "message_id": "reader-old"}
    approval = approve(cycle, "enroll", **second)
    call(cycle, "enroll", approval=approval, **second)
    assert call(cycle, "attach", mode="writer", generation=0, **second)["generation"] == 1
    assert call(cycle)["writer_relation"] == "self"
    assert call(cycle, **second)["writer_relation"] == "self"
    first = call(cycle, "admit", generation=1, call_id="one", operation_class="shell")
    other = call(cycle, "admit", generation=1, call_id="two", operation_class="file", **second)
    assert first["operation_id"] != other["operation_id"]
    assert call(cycle, "finish", operation_id=other["operation_id"], outcome="completed",
                ok=False)["reason"] == "invalid_identity"
    env = {**cycle.continuation_env, "DBSCTR_CONTINUATION_OPERATION": first["operation_id"]}
    refused = fixtures.run(cycle.repo, "cleanup", "--completed", env=env, ok=False)
    assert "continuation_admission_required" in refused.stderr


def test_continuation_corrupt_writer_state_is_not_authority(cycle):
    enroll(cycle)
    with sqlite3.connect(cycle.continuation_path) as db:
        db.execute("UPDATE cycles SET writer=NULL")
    assert call(cycle, ok=False)["reason"] == "invalid_state"
