"""Recovery must never turn a stale V1 row into a new V2 conversation."""
import json
import runpy
import sqlite3

import pytest

from test_herdr_session_recovery import SCRIPT, entry, seed


@pytest.mark.parametrize("fault", [None, "legacy_only", "incomplete", "duplicate_marker",
                                  "extra_marker", "view", "directory", "unknown_version"])
@pytest.mark.parametrize("check", [True, False])
def test_native_v2_recovery_admits_only_current_identity(tmp_path, monkeypatch, fault, check):
    database = tmp_path / "history.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT)")
        connection.execute("INSERT INTO session VALUES (?,?)", ("ses_saved", str(tmp_path)))
        connection.execute("CREATE TABLE kv (key TEXT PRIMARY KEY,value TEXT)")
        marker = {"phase": "converting" if fault == "incomplete" else "completed"}
        if fault == "extra_marker":
            marker["unknown"] = True
        connection.execute("INSERT INTO kv VALUES ('migration.v1-v2',?)", (
            '{"phase":"converting","phase":"completed"}' if fault == "duplicate_marker" else json.dumps(marker),))
        if fault != "legacy_only":
            connection.execute("CREATE TABLE session_message (id TEXT,session_id TEXT)")
            if fault == "view":
                connection.execute("CREATE VIEW session_v2 AS SELECT * FROM session")
            else:
                connection.execute("CREATE TABLE session_v2 (id TEXT PRIMARY KEY,directory TEXT)")
                connection.execute("INSERT INTO session_v2 VALUES (?,?)", (
                    "ses_saved", str(tmp_path / "wrong" if fault == "directory" else tmp_path)))
    before = database.read_bytes()
    wrapper = tmp_path / "opencode"
    wrapper.write_text("#!/bin/sh\nprintf '%s\\n' '" + ("unknown" if fault == "unknown_version" else "opencode v2.0.22") + "'\n")
    wrapper.chmod(0o700)
    script = runpy.run_path(str(SCRIPT))
    launched = []
    def run(*args):
        if args == ("agent", "list"):
            return {"result": {"agents": []}}
        if args[:2] == ("pane", "get"):
            return {"result": {"pane": {"cwd": str(tmp_path)}}}
        raise AssertionError("unexpected invocation")
    monkeypatch.setitem(script["restore"].__globals__, "run", run)
    monkeypatch.setitem(script["restore"].__globals__, "pane_state", lambda _: (None, False))
    monkeypatch.setitem(script["restore"].__globals__, "pane_session", lambda _: "ses_saved")
    monkeypatch.setattr(script["subprocess"], "run", lambda argv, **kwargs: launched.append(argv))
    manifest = seed(tmp_path)
    if fault in {"legacy_only", "incomplete", "duplicate_marker", "extra_marker", "view", "unknown_version"}:
        with pytest.raises((RuntimeError, ValueError)):
            script["restore"](manifest, [entry(tmp_path)], database, wrapper, check)
    else:
        assert script["restore"](manifest, [entry(tmp_path)], database, wrapper, check) == (1 if fault else 0)
    assert database.read_bytes() == before
    assert len(launched) == (1 if not check and fault is None else 0)


def test_v1_refuses_v2_database_and_missing_database_stays_absent(tmp_path):
    script = runpy.run_path(str(SCRIPT))
    database = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        script["recovery_sessions"](database, [], 2)
    assert not database.exists()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE session_v2 (id TEXT,directory TEXT)")
    with pytest.raises(RuntimeError, match="mismatch"):
        script["recovery_sessions"](database, [], 1)
