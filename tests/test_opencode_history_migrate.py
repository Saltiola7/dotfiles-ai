import importlib.machinery
import importlib.util
import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_opencode-history-migrate"


def load_helper():
    loader = importlib.machinery.SourceFileLoader("opencode_history_migrate", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


SCHEMA = """
CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT NOT NULL, vcs TEXT, name TEXT,
  icon_url TEXT, icon_color TEXT, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL,
  time_initialized INTEGER, sandboxes TEXT NOT NULL, commands TEXT, icon_url_override TEXT);
CREATE TABLE project_directory (project_id TEXT NOT NULL, directory TEXT NOT NULL, type TEXT,
  strategy TEXT, time_created INTEGER NOT NULL, PRIMARY KEY(project_id, directory),
  FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE);
CREATE TABLE workspace (id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
  branch TEXT, directory TEXT, extra TEXT, project_id TEXT NOT NULL, time_used INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE);
CREATE TABLE session (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, parent_id TEXT, slug TEXT NOT NULL,
  directory TEXT NOT NULL, title TEXT NOT NULL, version TEXT NOT NULL, share_url TEXT,
  summary_additions INTEGER, summary_deletions INTEGER, summary_files INTEGER, summary_diffs TEXT,
  revert TEXT, permission TEXT, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL,
  time_compacting INTEGER, time_archived INTEGER, workspace_id TEXT, path TEXT, agent TEXT, model TEXT,
  cost REAL NOT NULL DEFAULT 0, tokens_input INTEGER NOT NULL DEFAULT 0,
  tokens_output INTEGER NOT NULL DEFAULT 0, tokens_reasoning INTEGER NOT NULL DEFAULT 0,
  tokens_cache_read INTEGER NOT NULL DEFAULT 0, tokens_cache_write INTEGER NOT NULL DEFAULT 0,
  metadata TEXT, FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE);
CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, time_created INTEGER NOT NULL,
  time_updated INTEGER NOT NULL, data TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT NOT NULL, session_id TEXT NOT NULL,
  time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, data TEXT NOT NULL,
  FOREIGN KEY(message_id) REFERENCES message(id) ON DELETE CASCADE);
CREATE TABLE todo (session_id TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL,
  priority TEXT NOT NULL, position INTEGER NOT NULL, time_created INTEGER NOT NULL,
  time_updated INTEGER NOT NULL, PRIMARY KEY(session_id, position),
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, type TEXT NOT NULL,
  time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, data TEXT NOT NULL, seq INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE session_input (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, prompt TEXT NOT NULL,
  delivery TEXT NOT NULL, admitted_seq INTEGER NOT NULL, promoted_seq INTEGER, time_created INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE session_context_epoch (session_id TEXT PRIMARY KEY, baseline TEXT NOT NULL,
  snapshot TEXT NOT NULL, baseline_seq INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE session_share (session_id TEXT PRIMARY KEY, id TEXT NOT NULL, secret TEXT NOT NULL,
  url TEXT NOT NULL, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE);
CREATE TABLE permission (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, action TEXT NOT NULL,
  resource TEXT NOT NULL, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL,
  FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE);
CREATE TABLE event_sequence (aggregate_id TEXT PRIMARY KEY, seq INTEGER NOT NULL, owner_id TEXT);
CREATE TABLE event (id TEXT PRIMARY KEY, aggregate_id TEXT NOT NULL, seq INTEGER NOT NULL,
  type TEXT NOT NULL, data TEXT NOT NULL,
  FOREIGN KEY(aggregate_id) REFERENCES event_sequence(aggregate_id) ON DELETE CASCADE);
CREATE TABLE account (id TEXT PRIMARY KEY, email TEXT NOT NULL, url TEXT NOT NULL,
  access_token TEXT NOT NULL, refresh_token TEXT NOT NULL, token_expiry INTEGER,
  time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL);
CREATE TABLE account_state (id INTEGER PRIMARY KEY, active_account_id TEXT, active_org_id TEXT,
  FOREIGN KEY(active_account_id) REFERENCES account(id) ON DELETE SET NULL);
CREATE TABLE control_account (email TEXT NOT NULL, url TEXT NOT NULL, access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL, token_expiry INTEGER, active INTEGER NOT NULL,
  time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, PRIMARY KEY(email, url));
CREATE TABLE credential (id TEXT PRIMARY KEY, integration_id TEXT, label TEXT NOT NULL, value TEXT NOT NULL,
  connector_id TEXT, method_id TEXT, active INTEGER, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL);
CREATE TABLE migration (id TEXT PRIMARY KEY, time_completed INTEGER NOT NULL);
CREATE TABLE data_migration (name TEXT PRIMARY KEY, time_completed INTEGER NOT NULL);
CREATE TABLE __drizzle_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT NOT NULL,
  created_at INTEGER);
"""


def database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        for project, worktree in (("keep", "/host/repo"), ("drop", "/host/other")):
            db.execute("INSERT INTO project VALUES (?,?,NULL,NULL,NULL,NULL,1,1,NULL,'[]',NULL,NULL)",
                       (project, worktree))
            db.execute("INSERT INTO project_directory VALUES (?,?,NULL,NULL,1)", (project, worktree))
            db.execute("INSERT INTO workspace VALUES (?,?,?,NULL,?,NULL,?,0)",
                       (f"w-{project}", "local", project, worktree, project))
            db.execute("INSERT INTO permission VALUES (?,?,?,?,1,1)",
                       (f"perm-{project}", project, "read", "*"))
        sessions = (
            ("root", "keep", None, "/host/repo", "w-keep"),
            ("child", "keep", "root", "/host/worktrees/task", "w-keep"),
            ("other", "drop", None, "/host/other", "w-drop"),
        )
        for session, project, parent, directory, workspace in sessions:
            db.execute(
                "INSERT INTO session (id,project_id,parent_id,slug,directory,title,version,time_created,time_updated,workspace_id,path) "
                "VALUES (?,?,?,?,?,?,?,1,1,?,NULL)",
                (session, project, parent, session, directory, session, "1.18.21", workspace),
            )
            db.execute("INSERT INTO message VALUES (?,?,1,1,'{}')", (f"m-{session}", session))
            db.execute("INSERT INTO part VALUES (?,?,?,1,1,'{}')", (f"p-{session}", f"m-{session}", session))
            db.execute("INSERT INTO todo VALUES (?,'todo','pending','high',0,1,1)", (session,))
            db.execute("INSERT INTO session_message VALUES (?,?, 'event',1,1,'{}',1)", (f"sm-{session}", session))
            db.execute("INSERT INTO session_input VALUES (?,?,'prompt','sent',1,NULL,1)", (f"si-{session}", session))
            db.execute("INSERT INTO session_context_epoch VALUES (?,'{}','{}',1)", (session,))
            db.execute("INSERT INTO session_share VALUES (?,?,'secret','url',1,1)", (session, f"share-{session}"))
            db.execute("INSERT INTO event_sequence VALUES (?,1,NULL)", (session,))
            db.execute("INSERT INTO event VALUES (?,?,1,'session.updated.1','{}')", (f"event-{session}", session))
        db.execute("INSERT INTO account VALUES ('a','e','u','access','refresh',NULL,1,1)")
        db.execute("INSERT INTO account_state VALUES (1,'a',NULL)")
        db.execute("INSERT INTO control_account VALUES ('e','u','access','refresh',NULL,1,1,1)")
        db.execute("INSERT INTO credential VALUES ('c',NULL,'label','secret',NULL,NULL,1,1,1)")
        db.execute("INSERT INTO migration VALUES ('m',1)")
        db.execute("INSERT INTO data_migration VALUES ('d',1)")
        db.execute("INSERT INTO __drizzle_migrations (hash,created_at) VALUES ('h',1)")


def test_migrate_keeps_complete_selected_history_and_scrubs_identity(tmp_path: Path) -> None:
    helper = load_helper()
    source, output = tmp_path / "source.db", tmp_path / "output.db"
    database(source)

    result = helper.migrate(source, output, {"/host/repo": "/guest/repo"}, {"/host/worktrees": "/guest/worktrees"})

    assert result == {
        "projects": 1, "sessions": 2, "messages": 2, "parts": 2, "events": 2,
        "opaque_path_mentions": 0,
    }
    with sqlite3.connect(output) as db:
        assert db.execute("SELECT worktree FROM project").fetchall() == [("/guest/repo",)]
        assert db.execute("SELECT id,directory FROM session ORDER BY id").fetchall() == [
            ("child", "/guest/worktrees/task"), ("root", "/guest/repo")]
        assert db.execute("SELECT session_id FROM todo ORDER BY session_id").fetchall() == [("child",), ("root",)]
        assert db.execute("SELECT aggregate_id FROM event_sequence ORDER BY aggregate_id").fetchall() == [("child",), ("root",)]
        for table in ("account", "account_state", "control_account", "credential"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT COUNT(*) FROM project").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM account").fetchone()[0] == 1


def test_migrate_fails_closed(tmp_path: Path) -> None:
    helper = load_helper()
    source, output = tmp_path / "source.db", tmp_path / "output.db"
    database(source)

    output.touch()
    with pytest.raises(ValueError, match="output already exists"):
        helper.migrate(source, output, {"/host/repo": "/guest/repo"}, {})
    output.unlink()

    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE unsupported (value TEXT)")
    with pytest.raises(ValueError, match="unsupported tables"):
        helper.migrate(source, output, {"/host/repo": "/guest/repo"}, {})
    assert not output.exists()
