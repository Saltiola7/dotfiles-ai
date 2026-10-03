"""Native authority must select current V2 evidence, never retained V1 rows."""
import hashlib
import json
from pathlib import Path
import runpy
import sqlite3
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
ACTIVATION = {"schema_version": 1, "core_revision": "3.31", "overlays": {
    "build": "neutral-2026-07-26", "build-gpt": "openai-2026-07-26",
    "build-claude": "anthropic-2026-07-26"}}


@pytest.fixture
def native(tmp_path, monkeypatch):
    namespace = runpy.run_path(str(SOURCE))
    core = SimpleNamespace(**namespace)
    database = tmp_path / "native.db"
    with sqlite3.connect(database) as db:
        db.executescript("""
            CREATE TABLE session_v2(id TEXT PRIMARY KEY,parent_id TEXT,agent TEXT);
            CREATE TABLE session_message(id TEXT PRIMARY KEY,session_id TEXT,type TEXT,seq INTEGER,data TEXT);
            CREATE TABLE kv(key TEXT PRIMARY KEY,value TEXT);
            INSERT INTO session_v2 VALUES ('owner',NULL,NULL);
        """)
        body = {"agent": "build", "model": {"id": "fixture", "providerID": "openai"},
                "content": [{"type": "tool", "id": "call", "name": "write",
                             "state": {"status": "completed"}, "time": {"created": 1, "completed": 2}}]}
        db.execute("INSERT INTO session_message VALUES ('message','owner','assistant',0,?)", (json.dumps(body),))
    monkeypatch.setitem(core.session_for_message.__globals__, "opencode_database", lambda value=None: database)
    return core, database


def change_body(database, change):
    with sqlite3.connect(database) as db:
        body = json.loads(db.execute("SELECT data FROM session_message WHERE id='message'").fetchone()[0])
        change(body)
        db.execute("UPDATE session_message SET data=? WHERE id='message'", (json.dumps(body),))


def legacy(database, phase="completed"):
    with sqlite3.connect(database) as db:
        db.executescript("""
            CREATE TABLE session(id TEXT PRIMARY KEY,parent_id TEXT,agent TEXT);
            CREATE TABLE message(id TEXT PRIMARY KEY,session_id TEXT,data TEXT);
            INSERT INTO session VALUES ('stale',NULL,'build');
            INSERT INTO message VALUES ('message','stale','{}');
        """)
        if phase is not None:
            db.execute("INSERT INTO kv VALUES ('migration.v1-v2',?)", (json.dumps({"phase": phase}),))


def finish(core, kind="file", outcome="completed", message="message", call="call"):
    key = "v2_" + hashlib.sha256(f"{message}\0{call}".encode()).hexdigest()
    return core.continuation_finish_outcome(
        {"session_id": "owner", "outcome": outcome}, {"writer": "actor"},
        {"message_id": message, "call_id": key, "operation_class": kind, "completion_class": None}, "actor")


def test_native_v2_identity_and_activation_are_read_only(native):
    core, database = native
    before = database.read_bytes()
    assert core.session_for_message(None, "message", require_primary=True) == "owner"
    activation = core.harness_activation_for_message(None, "message", json.dumps(ACTIVATION))
    assert (activation["agent_id"], activation["model_id"], activation["provider_id"]) == ("build", "fixture", "openai")
    assert database.read_bytes() == before


def test_mixed_storage_never_uses_conflicting_legacy_rows(native):
    core, database = native
    legacy(database)
    assert core.session_for_message(None, "message", require_primary=True) == "owner"
    with sqlite3.connect(database) as db:
        db.execute("DELETE FROM session_message")
    with pytest.raises(RuntimeError):
        core.session_for_message(None, "message", require_primary=True)


@pytest.mark.parametrize("phase", [None, "sessions", "failed", "unknown"])
def test_incomplete_conversion_rejects_legacy_fallback(native, phase):
    core, database = native
    legacy(database, phase)
    with pytest.raises(RuntimeError):
        core.session_for_message(None, "message", require_primary=True)


@pytest.mark.parametrize("mutation", ["child", "agent_drift", "user", "missing_actor", "duplicate_json", "bad_json", "view"])
def test_invalid_actor_evidence_is_rejected(native, mutation):
    core, database = native
    with sqlite3.connect(database) as db:
        if mutation == "child":
            db.execute("UPDATE session_v2 SET parent_id='parent'")
        elif mutation == "agent_drift":
            db.execute("UPDATE session_v2 SET agent='plan'")
        elif mutation == "user":
            db.execute("UPDATE session_message SET type='user'")
        elif mutation == "duplicate_json":
            db.execute('UPDATE session_message SET data=\'{"agent":"plan","agent":"build","model":{"providerID":"openai","id":"fixture"}}\'')
        elif mutation == "bad_json":
            db.execute("UPDATE session_message SET data='private malformed data'")
        elif mutation == "view":
            db.execute("ALTER TABLE session_v2 RENAME TO hidden")
            db.execute("CREATE VIEW session_v2 AS SELECT * FROM hidden")
    if mutation == "missing_actor":
        change_body(database, lambda body: body.pop("agent"))
    with pytest.raises(RuntimeError) as error:
        core.harness_activation_for_message(None, "message", json.dumps(ACTIVATION))
    assert "private malformed data" not in str(error.value)


def test_vertex_canonical_provider_is_retained(native):
    core, database = native
    change_body(database, lambda body: body.update(agent="build-claude", model={"providerID": "google-vertex", "id": "fixture"}))
    activation = core.harness_activation_for_message(None, "message", json.dumps(ACTIVATION))
    assert activation["provider_id"] == "google-vertex"


@pytest.mark.parametrize("status,outcome,expected", [
    ("completed", "completed", ("completed", "native_completion")),
    ("error", "native_error", ("completed", "native_error")),
])
def test_file_terminal_proof(native, status, outcome, expected):
    core, database = native
    change_body(database, lambda body: body["content"][0]["state"].update(status=status))
    assert finish(core, outcome=outcome) == expected


@pytest.mark.parametrize("mutation", ["running", "duplicate", "bad_time", "missing_time", "wrong_tool", "background"])
def test_completion_rejects_unsafe_proof(native, mutation):
    core, database = native
    def mutate(body):
        tool = body["content"][0]
        if mutation == "running":
            tool["state"]["status"] = "running"
        elif mutation == "duplicate":
            body["content"].append(tool.copy())
        elif mutation == "bad_time":
            tool["time"]["completed"] = True
        elif mutation == "missing_time":
            tool["time"].pop("completed")
        elif mutation == "wrong_tool":
            tool["name"] = "unrelated"
        else:
            tool.update(name="shell")
            tool["state"]["metadata"] = {"status": "running"}
    change_body(database, mutate)
    with pytest.raises(RuntimeError):
        finish(core, kind="shell" if mutation == "background" else "file")


def test_reused_call_id_requires_exact_message(native):
    core, database = native
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO session_message SELECT 'other',session_id,type,1,data FROM session_message")
    change_body(database, lambda body: body["content"][0]["state"].update(status="running"))
    with pytest.raises(RuntimeError):
        finish(core)
    assert finish(core, message="other") == ("completed", "native_completion")


def test_plan_and_handover_actor_use_message_evidence(native):
    core, database = native
    assert core.native_session_actor(None, "owner") == (None, "build")
    change_body(database, lambda body: body.update(agent="plan"))
    assert core.native_session_actor(None, "owner", "message") == (None, "plan")


def test_v1_session_message_table_does_not_select_v2(native):
    core, database = native
    legacy(database)
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE session_v2")
    assert core.session_for_message(None, "message", require_primary=True) == "stale"


def test_codex_completion_does_not_consult_opencode_storage(native):
    core, database = native
    legacy(database, "sessions")
    assert core.continuation_finish_outcome(
        {"outcome": "completed"}, {}, {"completion_class": None}, "actor", opencode=False
    ) == ("completed", "native_completion")


@pytest.mark.parametrize("tool,kind", [("shell", "shell"), ("dbsctr_status", "lifecycle")])
def test_matching_non_file_completion(native, tool, kind):
    core, database = native
    def mutate(body):
        body["content"][0]["name"] = tool
        body["content"][0]["state"]["metadata"] = {"status": "completed"}
    change_body(database, mutate)
    assert finish(core, kind=kind) == ("completed", "native_completion")


def test_native_read_diagnostics_accept_plan_without_mutation_authority(native):
    core, database = native
    change_body(database, lambda body: body.update(agent="plan"))
    request = {"session_id": "owner", "message_id": "message", "harness_activation": ACTIVATION}
    key, activation = core.continuation_native(request, read_only=True)
    assert len(key) == 64 and activation is None
    with pytest.raises(RuntimeError):
        core.continuation_native(request)


def test_native_tool_count_is_bounded(native):
    core, database = native
    change_body(database, lambda body: body["content"].extend(
        {"type": "tool", "id": f"other-{index}"} for index in range(100)))
    with pytest.raises(RuntimeError):
        finish(core)


@pytest.mark.parametrize("end", [-1, float("inf"), float("nan"), 2**53, "2"])
def test_invalid_terminal_times_fail_closed(native, end):
    core, database = native
    change_body(database, lambda body: body["content"][0]["time"].update(completed=end))
    with pytest.raises(RuntimeError):
        finish(core)


def test_foreign_session_cannot_finish(native):
    core, _ = native
    with pytest.raises(RuntimeError):
        core.continuation_finish_outcome(
            {"session_id": "foreign", "outcome": "completed"}, {"writer": "actor"},
            {"message_id": "message", "call_id": "v2_" + hashlib.sha256(b"message\0call").hexdigest(),
             "operation_class": "file", "completion_class": None}, "actor")


@pytest.mark.parametrize("actor", ["build", "plan", "child"])
def test_v2_evidence_does_not_reactivate_retired_admission(native, actor):
    core, database = native
    before = database.read_bytes()
    payload = {"schema_version": 1, "session_id": "owner", "message_id": "message",
               "harness_activation": ACTIVATION, "agent": actor}
    response = core.subprocess.run(
        [core.sys.executable, str(SOURCE), "continuation-enroll", "--request-json", "-"],
        input=json.dumps(payload), cwd=database.parent, text=True, capture_output=True,
        env={"HOME": str(database.parent), "PATH": "/usr/bin:/bin",
             "XDG_DATA_HOME": str(database.parent / "data"), "XDG_STATE_HOME": str(database.parent / "state")},
        timeout=10,
    )
    assert response.returncode == 1 and "commands are retired" in response.stderr
    assert not response.stdout
    assert database.read_bytes() == before
