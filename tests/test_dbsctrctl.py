"""Focused subprocess contracts for dbsctrctl."""

import json
import contextlib
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import io
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
HISTORY_SOURCE_SCHEMA = (
    Path(__file__).parents[1]
    / "docs/specs/dbsctr_v3_lifecycle/features/harness-history-source.schemas.json"
)
GATES = (
    "domain", "behavior", "spec", "contract", "test_driven_implementation",
    "refactor", "review_integrate", "release", "deploy", "operate", "maintain_retire",
)
STATE_ENVIRONMENT = {
    "DBSCTR_RND_RECEIPTS", "DBSCTR_RND_STATE", "DBSCTR_STATE_ROOT",
    "DBSCTR_WORKTREE_ROOT", "DOTFILES_AI_STATE_ROOT", "XDG_DATA_HOME", "XDG_STATE_HOME",
}


def isolated_env():
    return {key: value for key, value in os.environ.items() if key not in STATE_ENVIRONMENT}


def discovery_report(digest="d" * 64):
    return json.dumps({"schema_version": 1, "interview": [
        {"question": "What changes?", "answer": "The bounded improvement workflow."}],
        "assumptions": [], "citations": ["source:workflow"], "risks": [],
        "evidence_digest": digest})


def initiative_manifest():
    return {
        "schema_version": 1,
        "id": "test-initiative",
        "title": "Test initiative",
        "state": "discovering",
        "coordinator_repository": "example/test",
        "statements": [
            {"id": "INT-001", "kind": "requirement", "text": "Durable requirement.",
             "disposition": "ready", "artifacts": ["docs/specs/test/README.md"]},
        ],
        "contexts": [
            {"id": "test", "repository": "example/test", "status": "approved",
             "depends_on": []},
        ],
        "slices": [
            {"id": "slice-a", "context": "test", "state": "ready",
             "requirements": ["INT-001"], "depends_on": [],
             "artifacts": ["docs/specs/test/CHANGELOG.md"], "tickets": ["V3.38-1"],
             "release_group": "release-a"},
        ],
        "release_groups": [{"id": "release-a", "members": ["slice-a"], "state": "planning"}],
    }


def run(repo, *args, ok=True, env=None, input_text=None, script=SCRIPT):
    result = subprocess.run(
        [sys.executable, str(script), *args], cwd=repo, text=True, capture_output=True,
        env=isolated_env() if env is None else env, input=input_text,
    )
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr}")
    if not ok and not result.returncode:
        raise AssertionError(f"{args}: unexpectedly succeeded")
    return result


def cycle_core(cycles):
    return [{key: value for key, value in cycle.items()
             if key not in {"context", "started_at", "ended_at"}} for cycle in cycles]


def ledger_text(state):
    connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
    try:
        values = []
        for table, column in (("review_reports", "payload"), ("history_evidence", "payload"),
                               ("history_reports", "payload"), ("ledger_entries", "text")):
            values.extend(row[0] for row in connection.execute(f"SELECT {column} FROM {table}"))
        if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='incidents'").fetchone():
            values.extend("".join(str(value or "") for value in row) for row in connection.execute(
                "SELECT title,summary,diagnostics,evidence FROM incidents"))
        return "".join(values)
    finally:
        connection.close()


def history_source_envelope(continued=False):
    source = {"harness_id": "codex", "adapter_revision": "codex-adapter-1", "release": "0.151.0"}
    members = [
        {"session_id": "session-new", "updated_at": 20},
        {"session_id": "session-old", "updated_at": 10},
    ]
    snapshot = hashlib.sha256(json.dumps(
        {"members": members, "overflow": False, "source": source},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()

    def entry(session_id, created, updated):
        return {
            "session_id": session_id,
            "family_id": session_id,
            "parent_id": None,
            "created_at": created,
            "updated_at": updated,
            "workspace": "primary_worktree",
            "project_digest": "a" * 64,
            "source_kind": "exec",
            "provider_id": "openai",
            "content": [
                {"role": "user", "text": "bounded request"},
                {"role": "assistant", "text": "bounded response"},
            ],
            "tool_signals": [{
                "signal_id": "b" * 24,
                "tool": "bash",
                "status": "failed",
                "failure_class": "command",
                "recovered": False,
                "timestamp": updated,
            }],
            "aggregates": {
                "turn_count": 1,
                "user_message_count": 1,
                "assistant_message_count": 1,
                "tool_call_count": 1,
                "tool_error_count": 1,
            },
            "metrics": {"token_total": 10, "cost_total": "1.25"},
            "availability": {
                "content": {"status": "available"},
                "tokens": {"status": "available"},
                "cost": {"status": "available"},
            },
        }

    first_page = {
        "schema_version": 1,
        "source": source,
        "snapshot_digest": snapshot,
        "overflow": False,
        "members": members,
        "entries": [entry("session-new", 15, 20)],
    }
    first_digest = hashlib.sha256(json.dumps(
        first_page, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()
    continuation = {
        "source": source,
        "snapshot_digest": snapshot,
        "overflow": False,
        "members": members,
        "offset": 1,
        "previous_page_digest": first_digest,
    }
    if not continued:
        first_page.update({"continuation": continuation, "page_digest": first_digest})
        return {"request": {"schema_version": 1, "limit": 1, "continuation": None}, "page": first_page}
    second_page = {
        "schema_version": 1,
        "source": source,
        "snapshot_digest": snapshot,
        "overflow": False,
        "members": members,
        "entries": [entry("session-old", 5, 10)],
    }
    second_digest = hashlib.sha256(json.dumps(
        second_page, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()
    second_page.update({"continuation": None, "page_digest": second_digest})
    return {"request": {"schema_version": 1, "limit": 1, "continuation": continuation}, "page": second_page}


def update_history_page_digest(envelope):
    page = envelope["page"]
    preimage = {key: page[key] for key in (
        "entries", "members", "overflow", "schema_version", "snapshot_digest", "source",
    )}
    page["page_digest"] = hashlib.sha256(json.dumps(
        preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()
    if page["continuation"] is not None:
        page["continuation"]["previous_page_digest"] = page["page_digest"]
    return envelope


def run_history_source(tmp_path, value, *, ok=True, input_text=None, argument="-"):
    state = tmp_path / "state"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "history-source-validate", "--envelope-json", argument],
        input=json.dumps(value) if input_text is None else input_text,
        text=True,
        capture_output=True,
        env={**isolated_env(), "DBSCTR_STATE_ROOT": str(state)},
    )
    assert (result.returncode == 0) is ok
    assert not state.exists()
    return result


def test_history_source_validator_accepts_first_and_continued_pages_without_content_output(tmp_path):
    for continued in (False, True):
        envelope = history_source_envelope(continued)
        if not continued:
            assert envelope["page"]["snapshot_digest"] == "cfa70abb7cfcb8aca9c397f0091cf168cd842978bce7df7ed64c9018ed9cd0a2"
            assert envelope["page"]["page_digest"] == "b5123fc3c74928792781bb95d7f144ab2f77fc02c2ca2dd3ff82c6f2f54bccc1"
        result = run_history_source(tmp_path, envelope)
        assert json.loads(result.stdout) == {
            "schema_version": 1,
            "status": "valid",
            "page_digest": envelope["page"]["page_digest"],
        }
        assert "bounded" not in result.stdout
        assert result.stderr == ""


def test_history_source_unicode_digest_matches_python_and_javascript(tmp_path):
    envelope = history_source_envelope()
    envelope["page"]["entries"][0]["content"][0]["text"] = "café 😀"
    update_history_page_digest(envelope)
    assert envelope["page"]["page_digest"] == "4bd30972bd3331115ccef542c26bb3724b3dfac1a4d4eb4a8e920731f64f9ef3"
    result = run_history_source(tmp_path, envelope)
    assert json.loads(result.stdout)["page_digest"] == envelope["page"]["page_digest"]

    node = shutil.which("node")
    assert node is not None
    script = r'''
const crypto = require("crypto");
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const sort = value => Array.isArray(value) ? value.map(sort) : value && typeof value === "object"
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sort(value[key])])) : value;
let canonical = JSON.stringify(sort(input));
let ascii = "";
for (const character of canonical) {
  let point = character.codePointAt(0);
  if (point <= 127) { ascii += character; continue; }
  if (point <= 65535) { ascii += "\\u" + point.toString(16).padStart(4, "0"); continue; }
  point -= 65536;
  ascii += "\\u" + (55296 + (point >> 10)).toString(16).padStart(4, "0");
  ascii += "\\u" + (56320 + (point & 1023)).toString(16).padStart(4, "0");
}
process.stdout.write(crypto.createHash("sha256").update(ascii).digest("hex"));
'''
    preimage = {key: envelope["page"][key] for key in (
        "entries", "members", "overflow", "schema_version", "snapshot_digest", "source",
    )}
    javascript = subprocess.run(
        [node, "-e", script], input=json.dumps(preimage, ensure_ascii=False),
        text=True, capture_output=True, check=True,
    )
    assert javascript.stdout == envelope["page"]["page_digest"]


def test_history_source_validator_rejects_schema_privacy_and_semantic_failures(tmp_path):
    cases = [
        (lambda value: value["page"].update({"unknown": True}), "invalid_schema"),
        (lambda value: value["page"].update({"snapshot_digest": "0" * 64}), "snapshot_mismatch"),
        (lambda value: value["page"]["members"].reverse(), "invalid_membership"),
        (lambda value: value["page"]["entries"][0].update({"updated_at": 1}), "invalid_timestamp"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": "https://unsafe.invalid"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": r"C:\Users\private\secret.txt"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": r"\\server\share\secret.txt"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": r"\Users\private\secret.txt"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": r"path=\Users\private\secret.txt"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": r"root:\Users\private\secret.txt"}), "unsafe_content"),
        (lambda value: value["page"]["entries"][0]["content"][0].update({"text": "é" * 5000}), "unsafe_content"),
        (lambda value: value["request"].update({"schema_version": True}), "invalid_schema"),
        (lambda value: value["page"].update({"schema_version": True}), "invalid_schema"),
        (lambda value: value["page"]["entries"][0].update({"workspace": []}), "invalid_schema"),
        (lambda value: value["page"]["entries"][0].update({"source_kind": {}}), "invalid_schema"),
        (lambda value: value["page"]["entries"][0]["tool_signals"][0].update({"status": []}), "invalid_tool_signals"),
        (lambda value: value["page"]["entries"][0]["tool_signals"][0].update({"failure_class": []}), "invalid_tool_signals"),
        (lambda value: value["page"]["members"][0].update({"updated_at": 9007199254740992}), "invalid_schema"),
        (lambda value: value["page"]["members"].__setitem__(1, dict(value["page"]["members"][0])), "invalid_membership"),
        (lambda value: value["page"].update({"overflow": True}), "invalid_membership"),
        (lambda value: value["page"]["entries"][0].update({"session_id": "wrong-session"}), "entry_membership_mismatch"),
        (lambda value: value["page"]["entries"][0].update({"updated_at": 19}), "entry_membership_mismatch"),
        (lambda value: value["page"]["entries"][0]["availability"]["tokens"].update({"status": "unavailable", "reason": "missing"}), "availability_mismatch"),
        (lambda value: value["page"].update({"page_digest": "0" * 64}), "page_digest_mismatch"),
        (lambda value: value["page"]["continuation"].update({"offset": 2}), "invalid_membership"),
        (lambda value: value["page"]["continuation"].update({"previous_page_digest": "0" * 64}), "continuation_mismatch"),
    ]
    for mutation, reason in cases:
        envelope = history_source_envelope()
        mutation(envelope)
        result = run_history_source(tmp_path, envelope, ok=False)
        assert result.stdout == ""
        assert result.stderr.strip() == f"dbsctrctl: history_source_{reason}"


def test_history_source_validator_rejects_stale_continuation_and_unsafe_input(tmp_path):
    stale = history_source_envelope(continued=True)
    stale["request"]["continuation"]["source"] = {
        **stale["request"]["continuation"]["source"], "release": "0.152.0",
    }
    result = run_history_source(tmp_path, stale, ok=False)
    assert "history_source_stale_continuation" in result.stderr

    stale = history_source_envelope(continued=True)
    stale["request"]["continuation"]["members"] = list(reversed(
        stale["request"]["continuation"]["members"]
    ))
    result = run_history_source(tmp_path, stale, ok=False)
    assert "history_source_invalid_membership" in result.stderr

    stale = history_source_envelope(continued=True)
    stale["request"]["continuation"]["snapshot_digest"] = "0" * 64
    result = run_history_source(tmp_path, stale, ok=False)
    assert "history_source_stale_continuation" in result.stderr

    terminal = history_source_envelope(continued=True)
    terminal["page"]["continuation"] = history_source_envelope()["page"]["continuation"]
    result = run_history_source(tmp_path, terminal, ok=False)
    assert "history_source_continuation_mismatch" in result.stderr

    duplicate = '{"request":{},"request":{},"page":{}}'
    result = run_history_source(tmp_path, {}, ok=False, input_text=duplicate)
    assert "history_source_duplicate_key" in result.stderr

    state = tmp_path / "invalid-utf8-state"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "history-source-validate", "--envelope-json", "-"],
        input=b"\xff", capture_output=True,
        env={**isolated_env(), "DBSCTR_STATE_ROOT": str(state)},
    )
    assert result.returncode == 1
    assert result.stdout == b""
    assert result.stderr.strip() == b"dbsctrctl: history_source_invalid_utf8"
    assert not state.exists()

    result = run_history_source(tmp_path, {}, ok=False, input_text="x" * (1024 * 1024 + 1))
    assert "history_source_input_too_large" in result.stderr

    result = run_history_source(tmp_path, {}, ok=False, input_text="[" * 1000)
    assert result.stderr.strip() == "dbsctrctl: history_source_invalid_json"

    result = run_history_source(tmp_path, {}, ok=False, input_text='{"value":' + "9" * 5000 + "}")
    assert result.stderr.strip() == "dbsctrctl: history_source_invalid_json"

    private = tmp_path / "private.json"
    private.write_text(json.dumps(history_source_envelope()))
    result = run_history_source(tmp_path, {}, ok=False, argument=str(private))
    assert result.stderr.strip() == "dbsctrctl: history_source_stdin_required"
    assert private.exists()


def test_history_source_parser_failures_are_bounded(tmp_path):
    commands = [
        ["history-source-validate"],
        ["history-source-validate", "--unknown", "private"],
        ["history-source-validate", "--envelope-json", "-", "--envelope-json", "-"],
    ]
    for arguments in commands:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True,
            env=isolated_env(),
        )
        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == "dbsctrctl: history_source_invalid_arguments"
        assert len(result.stderr.encode()) <= 256


def test_history_source_authoritative_schema_matches_portability_contract():
    schema = json.loads(HISTORY_SOURCE_SCHEMA.read_text())
    assert schema["$ref"] == "#/$defs/envelope"
    assert schema["$defs"]["page"]["additionalProperties"] is False
    assert schema["$defs"]["envelope"]["additionalProperties"] is False
    integer_nodes = []

    def visit(value):
        if isinstance(value, dict):
            kind = value.get("type")
            if kind == "integer" or isinstance(kind, list) and "integer" in kind:
                integer_nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    assert integer_nodes
    assert all(node["maximum"] <= 9007199254740991 for node in integer_nodes)
    assert schema["$defs"]["metrics"]["properties"]["cost_total"]["anyOf"][0] == {
        "type": "string", "pattern": "^(0|[1-9][0-9]*)(\\.[0-9]{1,6})?$",
    }


class DbsctrctlTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        artifacts = self.repo / "docs/specs/test"
        artifacts.mkdir(parents=True)
        for args in (("init",), ("config", "user.email", "test@example.com"),
                     ("config", "user.name", "Test")):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "tracked.txt").write_text("base\n")
        for name in ("README.md", "BACKLOG.md", "CHANGELOG.md"):
            (artifacts / name).write_text("base\n")
        subprocess.run(
            ["git", "add", "tracked.txt", "docs/specs/test"],
            cwd=self.repo, check=True,
        )
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.repo, check=True,
                       capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def plan_path(self, intent="local"):
        gates = {
            gate: {"applicability": "required"}
            for gate in GATES
        }
        if intent != "release":
            gates["release"] = {
                "applicability": "not_applicable",
                "reason": "delivery intent is not release",
            }
        plan = Path(self.temp.name) / "plan.json"
        plan.write_text(json.dumps({
            "profile": "docs/specs/test/README.md",
            "gates": gates,
        }))
        return plan

    def start(self, intent="local", base_branch="main", account="example-user",
              repository="example-user/dotfiles-ai", env=None):
        plan = self.plan_path(intent)
        command = ["start", "--cycle-id", "cycle-1", "--context", "test",
                   "--risk", "routine", "--delivery-intent", intent, "--plan", str(plan),
                   "--base-branch", base_branch]
        if intent == "draft_pr":
            command += ["--github-account", account, "--github-repository", repository]
        return run(self.repo, *command, env=env)

    def record_path(self, repo=None):
        return (repo or self.repo) / ".git/dbsctr/cycles/cycle-1.json"

    def make_schema3_fixture(self, cycle_id, worktree):
        path = self.repo / f".git/dbsctr/cycles/{cycle_id}.json"
        record = json.loads(path.read_text())
        current_pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        current_pointer.unlink()
        worktree = Path(worktree).resolve()
        git_directory = Path(subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-dir"], cwd=worktree,
            check=True, text=True, capture_output=True,
        ).stdout.strip())
        record["schema_version"] = 3
        record["method_revision"] = "3.28"
        record["worktree"] = {
            **{key: value for key, value in record["worktree"].items()
               if key not in {"id", "locator", "path", "git_dir"}},
            "id": hashlib.sha256(str(worktree).encode()).hexdigest()[:16],
            "path": str(worktree),
            "git_dir": str(git_directory),
        }
        if "source" in record:
            record["source"] = {
                **{key: value for key, value in record["source"].items()
                   if key not in {"locator", "path"}},
                "path": str(self.repo.resolve()),
            }
        opencode = record.get("runtime", {}).get("opencode")
        if opencode is None:
            record.pop("runtime", None)
        else:
            base = worktree if opencode["path_root"] == "cycle_worktree" else self.repo.resolve()
            record["runtime"] = {"opencode": {
                **{key: value for key, value in opencode.items()
                   if key not in {"path_root", "worktree", "directory"}},
                "worktree": str(base),
                "directory": str((Path(base) / opencode["directory"]).resolve()),
            }}
        path.write_text(json.dumps(record))
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(cycle_id + "\n")
        return record

    def review_artifacts(self):
        for name, result, reason in (
            ("README", "unchanged", "no durable truth changed"),
            ("BACKLOG", "unchanged", "already tracked"),
            ("CHANGELOG", "unchanged", "not finalized"),
        ):
            run(self.repo, "review-artifact", name, "--result", result, "--reason", reason)

    def write_initiative(self, value=None):
        path = self.repo / "docs/initiatives/test/MANIFEST.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value or initiative_manifest()))
        return path

    def pass_gates(self):
        for gate in GATES:
            if gate != "release":
                self.record_gate(gate)

    def pass_gate(self, gate="domain"):
        self.record_gate(gate)

    def record_gate(self, gate, code=0, paths=()):
        command = ["record-evidence", gate, "--authority", "test"]
        for path in paths:
            command += ["--path", path]
        return run(self.repo, *command, "--", sys.executable, "-c", f"raise SystemExit({code})")

    def start_remote_cycle(self):
        remote = Path(self.temp.name) / "remote.git"
        other = Path(self.temp.name) / "other"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo,
                       check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo,
                       check=True, capture_output=True)
        subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "other@example.com"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.name", "Other"], cwd=other, check=True)
        self.start("merge")
        return other

    def test_start_records_current_method_revision_and_release_default(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["method_revision"], "3.29")
        self.assertEqual(record["schema_version"], 5)
        self.assertEqual(record["runtime"], {"adapters": {}})
        self.assertEqual(record["worktree"]["locator"], {
            "root": "cycle_worktree", "path": ".",
        })

    def test_initiative_check_and_receipt_are_deterministic_and_content_free(self):
        path = self.write_initiative()
        checked = json.loads(run(
            self.repo, "initiative-check", "--manifest", str(path), "--json",
        ).stdout)
        self.assertEqual(checked["ready_slices"], ["slice-a"])
        self.assertEqual(checked["counts"], {
            "contexts": 1, "statements": 1, "release_groups": 1, "slices": 1,
        })
        self.assertRegex(checked["manifest_digest"], r"^[0-9a-f]{64}$")
        self.assertNotIn("path", json.dumps(checked))

        value = initiative_manifest()
        value["slices"][0]["tickets"] = ["IGNORED-1"]
        path.write_text(json.dumps(value))
        ignored = json.loads(run(
            self.repo, "initiative-check", "--manifest", str(path), "--json",
        ).stdout)
        self.assertEqual(ignored["manifest_digest"], checked["manifest_digest"])
        value["slices"][0].pop("tickets")
        path.write_text(json.dumps(value))
        omitted = json.loads(run(
            self.repo, "initiative-check", "--manifest", str(path), "--json",
        ).stdout)
        self.assertEqual(omitted["manifest_digest"], checked["manifest_digest"])

        subprocess.run(["git", "add", str(path.relative_to(self.repo))],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "initiative"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/example/test.git"],
                       cwd=self.repo, check=True)
        receipt = json.loads(run(
            self.repo, "initiative-receipt", "--manifest", str(path),
            "--slice", "slice-a", "--json",
        ).stdout)
        self.assertEqual(receipt["manifest_digest"], checked["manifest_digest"])
        self.assertRegex(receipt["manifest_blob"], r"^[0-9a-f]{40,64}$")
        self.assertRegex(receipt["manifest_commit"], r"^[0-9a-f]{40,64}$")
        self.assertEqual(receipt["release_group"], "release-a")
        self.assertNotIn("tickets", receipt)
        self.assertEqual(receipt["execution_owner"], "build")
        self.assertEqual(receipt["requirements"], ["INT-001"])
        self.assertEqual(receipt["artifacts"], [
            "docs/specs/test/CHANGELOG.md", "docs/specs/test/README.md",
        ])
        self.assertNotIn("Durable requirement", json.dumps(receipt))

        (self.repo / "docs/specs/test/README.md").write_text("dirty\n")
        dirty = run(self.repo, "initiative-receipt", "--manifest", str(path),
                    "--slice", "slice-a", "--json", ok=False)
        self.assertIn("artifact must be committed and clean", dirty.stderr)
        subprocess.run(["git", "restore", "docs/specs/test/README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/other/repo.git"],
                       cwd=self.repo, check=True)
        mismatch = run(self.repo, "initiative-receipt", "--manifest", str(path),
                       "--slice", "slice-a", "--json", ok=False)
        self.assertIn("coordinator repository does not match", mismatch.stderr)
        subprocess.run(["git", "remote", "set-url", "origin",
                        "https://evil.example/github.com/example/test.git"], cwd=self.repo, check=True)
        deceptive = run(self.repo, "initiative-receipt", "--manifest", str(path),
                        "--slice", "slice-a", "--json", ok=False)
        self.assertIn("must have a GitHub origin", deceptive.stderr)

    def test_initiative_source_resolves_git_root(self):
        nested = self.repo / "nested/source"
        nested.mkdir(parents=True)
        override = Path(self.temp.name) / "override"
        override.mkdir()
        subprocess.run(["git", "init"], cwd=override, check=True, capture_output=True)
        with mock.patch.dict(os.environ, {
            "GIT_DIR": str(override / ".git"), "GIT_WORK_TREE": str(override),
        }):
            loader = importlib.machinery.SourceFileLoader("dbsctrctl_repo_root_module", str(SCRIPT))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)

            self.assertEqual(module.repo_root(nested), self.repo.resolve())
        with self.assertRaisesRegex(RuntimeError, "Initiative source must be a Git repository"):
            module.repo_root(Path(self.temp.name) / "not-a-repository")

    def test_initiative_check_rejects_duplicate_ids_and_unknown_requirements(self):
        value = initiative_manifest()
        value["contexts"].append(dict(value["contexts"][0]))
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("duplicate context ID", result.stderr)

        value = initiative_manifest()
        value["slices"][0]["requirements"] = ["INT-999"]
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("unknown material statement", result.stderr)

    def test_initiative_cycle_check_rejects_occupied_identity(self):
        manifest = self.write_initiative()
        subprocess.run(["git", "add", str(manifest.relative_to(self.repo))], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "initiative"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/example/test.git"],
                       cwd=self.repo, check=True)
        command = ("initiative-receipt", "--manifest", str(manifest),
                   "--slice", "slice-a", "--json")
        receipt = json.loads(run(self.repo, *command).stdout)
        expected = {**receipt, "manifest_path": "docs/initiatives/test/MANIFEST.json"}
        check = ("initiative-cycle-check", "--cycle-id", "V3.38-1",
                 "--receipt-json", json.dumps(expected))
        run(self.repo, "start", "--cycle-id", "V3.38-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()))
        record = self.repo / ".git/dbsctr/cycles/V3.38-1.json"
        cycle = json.loads(record.read_text())
        cycle["source"] = {}
        record.write_text(json.dumps(cycle))

        occupied = run(self.repo, *check, ok=False)
        self.assertIn("occupied by an unbound cycle", occupied.stderr)

        cycle["initiative"] = expected
        record.write_text(json.dumps(cycle))
        self.assertEqual(json.loads(run(self.repo, *command).stdout), receipt)
        self.assertTrue(json.loads(run(self.repo, *check).stdout)["available"])

        bound = json.loads(record.read_text())
        bound["initiative"]["manifest_digest"] = "0" * 64
        record.write_text(json.dumps(bound))
        mismatch = run(self.repo, *check, ok=False)
        self.assertIn("occupied by a different Initiative receipt", mismatch.stderr)

        cycle["state"] = "private-secret"
        record.write_text(json.dumps(cycle))
        terminal = run(self.repo, *check, ok=False)
        self.assertIn("occupied by a non-active cycle", terminal.stderr)
        self.assertNotIn("private-secret", terminal.stderr)

        malformed = dict(cycle)
        malformed["gates"] = []
        malformed["state"] = "active"
        record.write_text(json.dumps(malformed))
        invalid = run(self.repo, *check, ok=False)
        self.assertIn("record identity mismatch", invalid.stderr)

        record.unlink()
        record.symlink_to(record.with_name("missing.json"))
        unsafe = run(self.repo, *check, ok=False)
        self.assertIn("cycle record is unsafe", unsafe.stderr)

    def test_initiative_check_rejects_cycles_uncovered_intent_and_blocked_completion(self):
        value = initiative_manifest()
        value["contexts"].append({
            "id": "beta", "repository": "example/test", "status": "approved",
            "depends_on": ["test"],
        })
        value["contexts"][0]["depends_on"] = ["beta"]
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("context dependency cycle", result.stderr)

        value = initiative_manifest()
        value["statements"][0]["artifacts"] = []
        value["slices"][0]["state"] = "captured"
        value["slices"][0]["requirements"] = []
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("uncovered material statement", result.stderr)

        value = initiative_manifest()
        value["state"] = "complete"
        value["statements"][0]["disposition"] = "blocked"
        value["slices"][0]["state"] = "delivered"
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("cannot complete", result.stderr)

    def test_initiative_check_rejects_unsatisfied_dependencies_and_unsafe_receipt_fields(self):
        value = initiative_manifest()
        value["slices"].append({
            "id": "slice-b", "context": "test", "state": "captured",
            "requirements": ["INT-001"], "depends_on": [], "artifacts": [],
            "tickets": [], "release_group": "release-a",
        })
        value["release_groups"][0]["members"].append("slice-b")
        value["slices"][0]["depends_on"] = ["slice-b"]
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("dependency is not delivered", result.stderr)

        value = initiative_manifest()
        value["slices"][0]["artifacts"] = ["/Users/test/private.md"]
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("repository-relative path", result.stderr)

        value = initiative_manifest()
        value["contexts"][0]["status"] = "blocked"
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("context is not promotable", result.stderr)

        value = initiative_manifest()
        value["coordinator_repository"] = "https://github.com/example/test"
        result = run(self.repo, "initiative-check", "--manifest", str(self.write_initiative(value)),
                     "--json", ok=False)
        self.assertIn("canonical owner/repository", result.stderr)

        manifest = self.write_initiative()
        manifest.write_bytes(b" " * (1024 * 1024 + 1))
        result = run(self.repo, "initiative-check", "--manifest", str(manifest), "--json", ok=False)
        self.assertIn("exceeds 1 MiB", result.stderr)

    def test_new_cycles_prefer_profile_md_while_readme_cycles_remain_bound(self):
        profile = self.repo / "docs/specs/test/PROFILE.md"
        profile.write_text("profile\n")
        subprocess.run(["git", "add", str(profile)], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "profile"], cwd=self.repo, check=True,
                       capture_output=True)
        plan = json.loads(self.plan_path().read_text())
        rejected = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-", ok=False,
            input_text=json.dumps(plan),
        )
        self.assertIn("PROFILE.md", rejected.stderr)
        plan["profile"] = "docs/specs/test/PROFILE.md"
        run(self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-",
            input_text=json.dumps(plan))
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["engineering_profile"]["path"], "docs/specs/test/PROFILE.md")

        record["engineering_profile"]["path"] = "docs/specs/test/README.md"
        record["engineering_profile"]["blob"] = subprocess.run(
            ["git", "rev-parse", "HEAD:docs/specs/test/README.md"], cwd=self.repo,
            text=True, check=True, capture_output=True,
        ).stdout.strip()
        record["applicability_plan"]["profile"] = "docs/specs/test/README.md"
        self.record_path().write_text(json.dumps(record))
        plan["profile"] = "docs/specs/test/README.md"
        run(self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan))
        self.assertNotIn("path", record["worktree"])
        self.assertNotIn("git_dir", record["worktree"])
        self.assertEqual(record["evidence"], {"version": 1, "items": {}})
        self.assertEqual(record["engineering_profile"]["path"], "docs/specs/test/README.md")
        self.assertRegex(record["engineering_profile"]["blob"], r"^[0-9a-f]+$")
        self.assertEqual(record["state"], "active")
        self.assertIsNone(record["git"]["upstream"])
        self.assertEqual(record["gates"]["release"], {
            "applicability": "not_applicable", "result": "not_run", "reason": "delivery intent is not release"
        })
        self.assertEqual(set(record["artifact_reviews"]), {"README", "BACKLOG", "CHANGELOG"})

    def test_start_binds_discovery_ready_guest_projection(self):
        home = Path(self.temp.name) / "guest-home"
        home.mkdir()
        env = {**isolated_env(), "HOME": str(home),
               "DBSCTR_IMPROVEMENT_WORKER_ID": "worker-1"}
        run(self.repo, "improvement-register", "--worker-id", "worker-1",
            "--session-id", "session-1", env=env)
        claim = json.loads(run(self.repo, "improvement-claim", "--session-id", "session-1",
            "--summary", "Implement guest projection", "--priority", "P1", env=env).stdout)
        run(self.repo, "improvement-update", "--session-id", "session-1", "--state", "discovery",
            "--operator-confirm", "worker-1", "--discovery-json", discovery_report(), env=env)
        remote = Path(self.temp.name) / "guest-remote.git"
        worktrees = Path(self.temp.name) / "guest-worktrees"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo,
                       check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo,
                       check=True, capture_output=True)
        plan = self.plan_path()
        command = (
            "begin", "--cycle-id", "cycle-1", "--context", "test", "--risk", "elevated",
            "--delivery-intent", "local", "--plan", str(plan), "--base-branch", "main",
            "--worktree-root", str(worktrees),
            "--opencode-session-id", "session-1", "--opencode-worktree", str(self.repo),
            "--opencode-directory", str(self.repo),
        )
        failed = run(self.repo, *command, ok=False,
                     env={**env, "DBSCTR_IMPROVEMENT_WORKER_ID": "worker-2"})
        self.assertIn("Discovery-ready guest projection", failed.stderr)
        result = json.loads(run(self.repo, *command, env=env).stdout)
        self.assertEqual(json.loads(self.record_path().read_text())["improvement"],
                         {"worker_id": "worker-1", "session_id": "session-1",
                          "opportunity_id": claim["opportunity_id"]})
        self.assertEqual(Path(result["worktree"]), (worktrees / "cycle-1").resolve())
        connection = sqlite3.connect(home / ".local/state/dbsctr/reviews/ledger.sqlite3")
        connection.execute("update improvement_workers set opportunity_id=? where worker_id='worker-1'",
                           ("e" * 64,))
        connection.commit()
        connection.close()
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_bound_worker", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        record = json.loads(self.record_path().read_text())
        with mock.patch.dict(os.environ, env, clear=True), \
                self.assertRaisesRegex(RuntimeError, "bound improvement worker projection is missing"):
            module.link_improvement_pull_request(
                record, {"number": 1, "url": "https://github.com/example/repo/pull/1"},
                Path(result["worktree"]), record["git"]["head"])

    def test_low_level_start_rejects_structured_opencode_runtime(self):
        result = run(self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
                     "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
                     "--opencode-session-id", "session-structured", ok=False)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_exclusive_record_failure_leaves_no_reserved_target(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_test_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        target = Path(self.temp.name) / "record.json"
        with mock.patch.object(module.json, "dump", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                module.exclusive_json(target, {"cycle": "test"})
        self.assertFalse(target.exists())

    def test_start_refuses_dirty_worktree(self):
        (self.repo / "tracked.txt").write_text("pre-cycle\n")
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()), ok=False,
        )
        self.assertIn("clean worktree", result.stderr)

    def test_start_rejects_unknown_delivery_intent(self):
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "relase", "--plan", "missing.json", ok=False,
        )
        self.assertIn("invalid choice", result.stderr)

    def test_start_requires_complete_valid_plan(self):
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", ok=False,
        )
        self.assertIn("--plan", result.stderr)

        plan = {"profile": "docs/specs/test/README.md", "gates": {}}
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-", ok=False,
            input_text=json.dumps(plan),
        )
        self.assertIn("every gate", result.stderr)

        duplicate = '{"profile":"docs/specs/test/README.md","profile":"docs/specs/test/README.md","gates":{}}'
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-", ok=False,
            input_text=duplicate,
        )
        self.assertIn("duplicate JSON key", result.stderr)

        plan = json.loads(self.plan_path().read_text())
        plan["unknown"] = True
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-", ok=False,
            input_text=json.dumps(plan),
        )
        self.assertIn("only profile, gates, and optional graphify", result.stderr)

    def test_graphify_selection_binds_managed_adapter_and_only_tightens(self):
        plan = json.loads(self.plan_path().read_text())
        plan["graphify"] = {"version": "0.9.50"}
        run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-",
            input_text=json.dumps(plan),
        )
        record = json.loads(self.record_path().read_text())
        selection = record["applicability_plan"]["graphify"]
        self.assertEqual(selection["version"], "0.9.50")
        self.assertEqual(selection["adapter_contract"], "dbsctr-project-graphify-v1")
        self.assertRegex(selection["adapter_sha256"], r"^[0-9a-f]{64}$")
        snapshot = self.repo / ".git/dbsctr/graphify/adapters" / selection["adapter_sha256"]
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o700)
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                         selection["adapter_sha256"])

        changed = {**plan, "graphify": {**plan["graphify"], "version": "0.9.51"}}
        result = run(self.repo, "update-plan", "--plan", "-", input_text=json.dumps(changed), ok=False)
        self.assertIn("Graphify selection cannot change", result.stderr)
        plan.pop("graphify")
        result = run(self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan), ok=False)
        self.assertIn("Graphify selection cannot be removed", result.stderr)
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_graphify_selection", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "requires exactly version"):
            module.validate_graphify_selection(
                self.repo, {"adapter": "scripts/graphify", "version": "0.9.50"})

    def test_graphify_check_runs_in_disposable_worktree_and_records_private_receipt(self):
        invalid_timeout = run(self.repo, "graphify-check", "--timeout", "0", ok=False)
        self.assertIn("timeout must be 1 through 3600 seconds", invalid_timeout.stderr)
        managed = Path(self.temp.name) / "managed"
        managed.mkdir()
        controller = managed / "dbsctrctl"
        shutil.copy2(SCRIPT, controller)
        adapter = managed / "dbsctr-project-graphify"
        adapter.write_text(
            "#!/bin/sh\nset -eu\n"
            "test \"$1\" = --output-dir\nmkdir -p \"$2\"\n"
            "printf 'Built from commit: `%s`\\n' \"$(git rev-parse HEAD)\" > \"$2/GRAPH_REPORT.md\"\n"
            "printf '{\"schema_version\":1}\\n' > \"$2/manifest.json\"\n"
            "printf '{\"cache_hits\":2,\"cache_misses\":1}\\n'\n"
        )
        adapter.chmod(0o755)
        plan = json.loads(self.plan_path().read_text())
        plan["graphify"] = {"version": "0.9.50"}
        run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-",
            input_text=json.dumps(plan), script=controller,
        )
        result = json.loads(run(self.repo, "graphify-check", script=controller).stdout)
        record = json.loads(self.record_path().read_text())
        receipt = self.repo / ".git/dbsctr" / record["graphify_check"]["receipt"]
        self.assertEqual(result["head"], subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
            check=True, capture_output=True).stdout.strip())
        self.assertEqual(result["cache"], {"hits": 2, "misses": 1})
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(receipt.read_text())["output_files"],
                         sorted(["GRAPH_REPORT.md", "manifest.json"]))
        self.assertEqual(subprocess.run(
            ["git", "worktree", "list", "--porcelain"], cwd=self.repo, text=True,
            check=True, capture_output=True).stdout.count("worktree "), 1)
        adapter.write_text(adapter.read_text() + "# changed\n")
        changed = json.loads(run(self.repo, "graphify-check", script=controller).stdout)
        self.assertEqual(changed["cache"], {"hits": 2, "misses": 1})
        tools = Path(self.temp.name) / "cleanup-tools"
        scratch = Path(self.temp.name) / "cleanup-scratch"
        tools.mkdir()
        scratch.mkdir()
        fake_git = tools / "git"
        fake_git.write_text(
            "#!/bin/sh\n"
            "if [ \"${1:-} ${2:-}\" = \"worktree remove\" ]; then\n"
            "  printf 'forced removal failure\\n' >&2\n  exit 9\nfi\n"
            f'exec "{shutil.which("git")}" "$@"\n'
        )
        fake_git.chmod(0o755)
        failed_cleanup = run(
            self.repo, "graphify-check", script=controller, ok=False,
            env={**isolated_env(), "PATH": f"{tools}:{os.environ['PATH']}", "TMPDIR": str(scratch)},
        )
        self.assertIn("forced removal failure", failed_cleanup.stderr)
        self.assertFalse(list(scratch.iterdir()))
        subprocess.run(["git", "worktree", "prune"], cwd=self.repo, check=True)
        value = json.loads(receipt.read_text())
        value["output_files"] = []
        receipt.write_text(json.dumps(value))
        record["graphify_check"]["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
        self.record_path().write_text(json.dumps(record))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_graphify_receipt", str(controller))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "receipt identity is invalid"):
            module.require_graphify_check(self.repo, record)

    def test_graphify_finalization_reports_and_preserves_failed_rollback(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_graphify_rollback", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        output = self.repo / "graphify-out"
        output.mkdir()
        (output / "manifest.json").write_text("{}\n")
        backup = Path(self.temp.name) / "failed-rollback"
        backup.mkdir()
        with mock.patch.object(module.tempfile, "mkdtemp", return_value=str(backup)), \
                mock.patch.object(module.os, "replace", side_effect=OSError("restore denied")):
            with self.assertRaisesRegex(RuntimeError, "batch Graphify rollback failed: restore denied"):
                with module.graphify_finalization_transaction(self.repo, output):
                    (output / "manifest.json").write_text('{"changed":true}\n')
                    raise RuntimeError("operation failed")
        self.assertTrue((backup / "graphify-out/manifest.json").exists())

    def test_graphify_finalization_retains_interrupted_output_on_index_restore_failure(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_graphify_index_rollback", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        output = self.repo / "graphify-out"
        output.mkdir()
        (output / "manifest.json").write_text("baseline\n")
        backup = Path(self.temp.name) / "failed-index-rollback"
        backup.mkdir()
        replace = module.os.replace
        calls = 0

        def fail_index_restore(source, destination):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("index restore denied")
            return replace(source, destination)

        with mock.patch.object(module.tempfile, "mkdtemp", return_value=str(backup)), \
                mock.patch.object(module.os, "replace", side_effect=fail_index_restore):
            with self.assertRaisesRegex(RuntimeError, "index restore denied"):
                with module.graphify_finalization_transaction(self.repo, output):
                    (output / "manifest.json").write_text("interrupted\n")
                    raise RuntimeError("operation failed")
        self.assertEqual((output / "manifest.json").read_text(), "baseline\n")
        self.assertEqual((backup / "interrupted/manifest.json").read_text(), "interrupted\n")

    def test_start_rejects_dirty_or_wrong_profile_and_delivery_conflict(self):
        gates = {gate: {"applicability": "required"} for gate in GATES}
        gates["release"] = {"applicability": "not_applicable", "reason": "not releasing"}
        plan = {"profile": "docs/specs/test/README.md", "gates": gates}
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "release", "--plan", "-", ok=False,
            input_text=json.dumps(plan),
        )
        self.assertIn("release delivery", result.stderr)

        plan["profile"] = "tracked.txt"
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", "-", ok=False,
            input_text=json.dumps(plan),
        )
        self.assertIn("Engineering Profile", result.stderr)

    def test_gate_pass_requires_predecessors_but_failure_does_not(self):
        self.start()
        result = run(
            self.repo, "record-evidence", "behavior", "--authority", "test", "--",
            sys.executable, "-c", "raise SystemExit(0)", ok=False,
        )
        self.assertIn("predecessor", result.stderr)
        self.record_gate("behavior", 1)
        self.record_gate("domain")
        run(
            self.repo, "approve-exception", "behavior", "--kind", "deferred",
            "--rationale", "approved", "--owner", "owner", "--review-condition", "next cycle",
        )
        self.record_gate("spec")
        run(self.repo, "set-gate", "domain", "--result", "pending")
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["gates"]["spec"]["result"], "pending")

    def test_record_evidence_runs_literal_command_and_binds_gate(self):
        self.start()
        marker = self.repo / "shell-expanded"
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", "import sys; assert sys.stdin.read() == ''; print('ok')", f"$(touch {marker})")
        record = json.loads(self.record_path().read_text())
        evidence_id = record["gates"]["domain"]["evidence"]
        envelope = record["evidence"]["items"][evidence_id]
        self.assertEqual(envelope["result"], "passed")
        self.assertEqual(envelope["argv"][-1], "[REDACTED]")
        self.assertFalse(marker.exists())
        self.assertEqual(envelope["urls"], [])
        self.assertNotIn("environment", json.dumps(record))

    def test_record_evidence_redacts_or_withholds_secrets(self):
        self.start()
        secret = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", f"print('{secret}')", "--token", secret)
        record = json.loads(self.record_path().read_text())
        envelope = next(iter(record["evidence"]["items"].values()))
        serialized = json.dumps(envelope)
        self.assertNotIn(secret, serialized)
        self.assertEqual(envelope["argv"][-1], "[REDACTED]")
        self.assertEqual(envelope["content"], {"status": "withheld", "reason": "unclassified"})

    def test_record_evidence_retains_only_allowlisted_output_and_sanitizes_argv(self):
        self.start()
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", "print('ok')", "--file=private.txt", "short-secret", "-psecret")
        envelope = next(iter(json.loads(self.record_path().read_text())["evidence"]["items"].values()))
        self.assertEqual(envelope["argv"], [Path(sys.executable).name, "[REDACTED]", "[REDACTED]",
                                             "--file=[REDACTED]", "[REDACTED]", "[REDACTED]"])
        self.assertEqual(envelope["content"]["status"], "sidecar")
        self.assertIn("path", envelope["content"])

    def test_record_evidence_failure_and_set_gate_rejects_arbitrary_schema3_evidence(self):
        self.start()
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", "raise SystemExit(2)")
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["gates"]["domain"]["result"], "failed")
        result = run(self.repo, "set-gate", "domain", "--result", "passed", "--evidence", "arbitrary", ok=False)
        self.assertIn("evidence ID", result.stderr)

    def test_record_evidence_withholds_binary_and_overflow_output(self):
        self.start()
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", "import os; os.write(1, b'\\xff')")
        record = json.loads(self.record_path().read_text())
        binary = next(iter(record["evidence"]["items"].values()))
        self.assertEqual(binary["content"]["status"], "withheld")
        self.assertEqual(binary["result"], "passed")

        run(self.repo, "record-evidence", "behavior", "--authority", "unit", "--", sys.executable, "-c",
            "import os; os.write(1, b'x' * (1024 * 1024 + 1))")
        overflow = next(item for item in json.loads(self.record_path().read_text())["evidence"]["items"].values()
                        if item["gate"] == "behavior")
        self.assertEqual(overflow["result"], "unavailable")
        self.assertTrue(overflow["raw"]["truncated"])
        self.assertEqual(overflow["content"], {"status": "withheld", "reason": "overflow"})

    def test_record_evidence_sidecar_is_hashed_private_and_deduplicated(self):
        self.start()
        command = [sys.executable, "-c", "print('ok')"]
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--", *command)
        run(self.repo, "record-evidence", "behavior", "--authority", "unit", "--", *command)
        items = list(json.loads(self.record_path().read_text())["evidence"]["items"].values())
        digest = items[0]["content"]["sha256"]
        sidecar = self.repo / ".git/dbsctr/evidence/cycle-1" / digest
        self.assertEqual(hashlib.sha256(sidecar.read_bytes()).hexdigest(), digest)
        self.assertEqual(sidecar.stat().st_mode & 0o777, 0o600)
        self.assertEqual(items[1]["content"]["sha256"], digest)

    def test_gate_commit_binds_current_evidence_and_rejects_tampered_sidecar(self):
        self.start()
        (self.repo / "tracked.txt").write_text("domain\n")
        run(self.repo, "record-evidence", "domain", "--authority", "unit", "--path", "tracked.txt",
            "--", sys.executable, "-c", "print('ok')")
        run(self.repo, "gate-commit", "--message", "domain", "--gates", "domain", "--paths", "tracked.txt")
        record = json.loads(self.record_path().read_text())
        domain = record["evidence"]["items"][record["gates"]["domain"]["evidence"]]
        self.assertEqual(domain["commit"], subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                         text=True, capture_output=True, check=True).stdout.strip())
        (self.repo / "tracked.txt").write_text("behavior\n")
        run(self.repo, "record-evidence", "behavior", "--authority", "unit", "--path", "tracked.txt",
            "--", sys.executable, "-c", "print('ok')")
        behavior = next(item for item in json.loads(self.record_path().read_text())["evidence"]["items"].values()
                        if item["gate"] == "behavior")
        (self.repo / ".git/dbsctr" / behavior["content"]["path"]).unlink()
        result = run(self.repo, "gate-commit", "--message", "behavior", "--gates", "behavior",
                     "--paths", "tracked.txt", ok=False)
        self.assertIn("sidecar", result.stderr)

    def test_schema3_rejects_stale_cross_gate_and_precreated_sidecar_evidence(self):
        self.start()
        evidence_id = self.record_gate("domain", paths=("tracked.txt",)).stdout.strip()
        cross_gate = run(self.repo, "set-gate", "behavior", "--result", "passed",
                         "--evidence", evidence_id, ok=False)
        self.assertIn("matching stored evidence ID", cross_gate.stderr)
        (self.repo / "tracked.txt").write_text("new head\n")
        subprocess.run(["git", "commit", "-am", "advance"], cwd=self.repo, check=True,
                       capture_output=True)
        stale = run(self.repo, "gate-commit", "--message", "stale", "--gates", "domain",
                    "--paths", "tracked.txt", ok=False)
        self.assertIn("evidence HEAD is stale", stale.stderr)

    def test_schema3_rejects_precreated_sidecar_symlink(self):
        self.start()
        directory = self.repo / ".git/dbsctr/evidence/cycle-1"
        directory.mkdir(parents=True, mode=0o700)
        digest = hashlib.sha256(b"ok\n").hexdigest()
        (directory / digest).symlink_to(self.repo / "tracked.txt")
        unsafe = run(self.repo, "record-evidence", "domain", "--authority", "test", "--",
                     sys.executable, "-c", "print('ok')", ok=False)
        self.assertIn("unsafe evidence sidecar", unsafe.stderr)

    def test_schema3_rejects_paths_changed_after_evidence(self):
        self.start()
        (self.repo / "tracked.txt").write_text("validated\n")
        self.record_gate("domain", paths=("tracked.txt",))
        (self.repo / "tracked.txt").write_text("changed later\n")
        result = run(self.repo, "gate-commit", "--message", "unsafe", "--gates", "domain",
                     "--paths", "tracked.txt", ok=False)
        self.assertIn("changed after validation", result.stderr)

    def test_schema3_rejects_commit_hook_path_changes(self):
        self.start()
        (self.repo / "tracked.txt").write_text("validated\n")
        self.record_gate("domain", paths=("tracked.txt",))
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'hook changed\\n' > tracked.txt\ngit add tracked.txt\n")
        hook.chmod(0o755)
        result = run(self.repo, "gate-commit", "--message", "hook", "--gates", "domain",
                     "--paths", "tracked.txt", ok=False)
        self.assertIn("committed paths differ from evidence", result.stderr)

    def test_record_evidence_kills_resistant_process_group_without_leaking_argv(self):
        self.start()
        script = (
            "import os,signal,time; child=os.fork(); "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10)"
        )
        result = run(self.repo, "record-evidence", "domain", "--authority", "unit", "--timeout", "1",
                     "--", sys.executable, "-c", script)
        evidence_id = result.stdout.strip()
        envelope = json.loads(self.record_path().read_text())["evidence"]["items"][evidence_id]
        self.assertEqual(envelope["result"], "unavailable")
        self.assertEqual(envelope["content"], {"status": "withheld", "reason": "timeout"})
        self.assertNotIn(script, json.dumps(envelope))

    def test_record_evidence_defaults_to_ten_minutes(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_evidence_timeout", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        args = module.parser().parse_args([
            "record-evidence", "domain", "--authority", "unit", "--",
            sys.executable, "-c", "pass",
        ])
        self.assertEqual(args.timeout, 600)

    def test_risk_and_applicability_only_tighten(self):
        self.start()
        record_path = self.record_path()
        record = json.loads(record_path.read_text())
        gates = {
            gate: {"applicability": value["applicability"], **(
                {"reason": value["reason"]} if value["applicability"] == "not_applicable" else {}
            )}
            for gate, value in record["gates"].items()
        }
        gates["release"] = {"applicability": "required"}
        plan = {"profile": "docs/specs/test/README.md", "gates": gates}
        run(
            self.repo, "raise-risk", "--to", "elevated", "--reason", "public contract",
            "--plan", "-", input_text=json.dumps(plan),
        )
        result = run(
            self.repo, "raise-risk", "--to", "routine", "--reason", "changed mind",
            "--plan", "-", input_text=json.dumps(plan), ok=False,
        )
        self.assertIn("only increase", result.stderr)
        record = json.loads(record_path.read_text())
        self.assertEqual(record["risk"], "elevated")
        self.assertEqual(record["gates"]["release"]["applicability"], "required")
        self.assertEqual(record["risk_history"][0]["from"], "routine")

    def test_schema_less_v31_record_uses_legacy_transitions(self):
        self.start()
        record_path = self.record_path()
        record = json.loads(record_path.read_text())
        record.pop("schema_version")
        record.pop("engineering_profile")
        record.pop("applicability_plan")
        record["method_revision"] = "3.1"
        record_path.write_text(json.dumps(record))
        run(self.repo, "set-gate", "behavior", "--result", "passed", "--evidence", "legacy")

    def test_unknown_cycle_schema_is_rejected(self):
        self.start()
        record_path = self.record_path()
        record = json.loads(record_path.read_text())
        for schema in (99, True, 5.0):
            with self.subTest(schema=schema):
                record["schema_version"] = schema
                record_path.write_text(json.dumps(record))
                result = run(self.repo, "status", ok=False)
                self.assertIn("unsupported Cycle Record schema", result.stderr)

    def test_schema5_validates_synthetic_adapters_and_opencode_agreement(self):
        self.start()
        path = self.record_path()
        record = json.loads(path.read_text())
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_schema5", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        availability = {
            "session": {"status": "available"},
            "turn": {"status": "not_requested"},
            "family": {"status": "not_requested"},
            "activation": {"status": "not_requested"},
            "history": {"status": "unavailable", "reason": "synthetic_fixture"},
        }
        codex = {
            "schema_version": 1,
            "harness_id": "codex",
            "adapter_revision": "codex-adapter-1",
            "session_ids": ["codex-session"],
            "worktree": {"root": "cycle_worktree", "path": "."},
            "availability": availability,
        }
        record["runtime"] = {"adapters": {"codex": codex}}
        path.write_text(json.dumps(record))
        self.assertEqual(module.validate_schema5_runtime(
            self.repo, record, allow_synthetic_codex=True)["adapters"]["codex"], codex)
        production = run(self.repo, "status", "--json", ok=False)
        self.assertIn("Codex adapter is unavailable", production.stderr)

        invalid = {}
        invalid["unknown adapter"] = {"adapters": {"other": {**codex, "harness_id": "other"}}}
        invalid["wrong revision"] = {"adapters": {"codex": {
            **codex, "adapter_revision": "codex-adapter-2",
        }}}
        invalid["boolean adapter schema"] = {"adapters": {"codex": {
            **codex, "schema_version": True,
        }}}
        invalid["float adapter schema"] = {"adapters": {"codex": {
            **codex, "schema_version": 1.0,
        }}}
        invalid["empty sessions"] = {"adapters": {"codex": {**codex, "session_ids": []}}}
        invalid["unsorted sessions"] = {"adapters": {"codex": {
            **codex, "session_ids": ["session-b", "session-a"],
        }}}
        invalid["too many sessions"] = {"adapters": {"codex": {
            **codex, "session_ids": [f"session-{index:03d}" for index in range(101)],
        }}}
        invalid["invalid session"] = {"adapters": {"codex": {
            **codex, "session_ids": ["invalid/session"],
        }}}
        invalid["unknown field"] = {"adapters": {"codex": {
            **codex, "native_session": "unproven",
        }}}
        invalid["unsafe worktree"] = {"adapters": {"codex": {
            **codex, "worktree": {"root": "cycle_worktree", "path": "../escape"},
        }}}
        invalid["missing reason"] = {"adapters": {"codex": {
            **codex, "availability": {**availability, "history": {"status": "unavailable"}},
        }}}
        invalid["false activation"] = {"adapters": {"codex": {
            **codex, "availability": {**availability, "activation": {"status": "available"}},
        }}}
        opencode = {
            **codex,
            "harness_id": "opencode",
            "adapter_revision": "opencode-adapter-1",
        }
        invalid["missing legacy opencode"] = {"adapters": {"opencode": opencode}}
        invalid["OpenCode disagreement"] = {
            "adapters": {"opencode": opencode},
            "opencode": {
                "session_ids": ["different-session"], "path_root": "cycle_worktree",
                "worktree": ".", "directory": ".",
            },
        }
        invalid["legacy OpenCode extra field"] = {
            "adapters": {"opencode": opencode},
            "opencode": {
                "session_ids": ["codex-session"], "path_root": "cycle_worktree",
                "worktree": ".", "directory": ".", "extra": True,
            },
        }
        invalid["legacy OpenCode missing directory"] = {
            "adapters": {"opencode": opencode},
            "opencode": {
                "session_ids": ["codex-session"], "path_root": "cycle_worktree",
                "worktree": ".",
            },
        }
        for name, runtime in invalid.items():
            with self.subTest(name=name):
                record["runtime"] = runtime
                with self.assertRaisesRegex(RuntimeError, "invalid schema 5 runtime"):
                    module.validate_schema5_runtime(
                        self.repo, record, allow_synthetic_codex=True)

    def test_cycle_portabilize_does_not_upgrade_schema5(self):
        self.start()
        result = run(self.repo, "cycle-portabilize", "--cycle-id", "cycle-1", ok=False)
        self.assertIn("cycle is not an unmigrated schema 3 record", result.stderr)

    def test_cycle_portabilize_rejects_noninteger_rollback_schema(self):
        self.start()
        legacy = self.make_schema3_fixture("cycle-1", self.repo)
        backup = self.repo / ".git/dbsctr/migrations/cycle-1.schema3.json"
        backup.parent.mkdir(parents=True)
        for schema in (True, 3.0):
            with self.subTest(schema=schema):
                backup.write_text(json.dumps({**legacy, "schema_version": schema}))
                result = run(
                    self.repo, "cycle-portabilize", "--cycle-id", "cycle-1", ok=False)
                self.assertIn("unsupported Cycle Record schema", result.stderr)

    def test_schema5_validation_applies_outside_active_load(self):
        self.start()
        path = self.record_path()
        record = json.loads(path.read_text())
        record["runtime"] = {"opencode": {
            "session_ids": ["legacy-only"], "path_root": "cycle_worktree",
            "worktree": ".", "directory": ".",
        }}
        path.write_text(json.dumps(record))

        inventory = run(self.repo, "worktree-list", "--json", ok=False)
        self.assertIn("invalid schema 5 runtime", inventory.stderr)
        performance = run(self.repo, "cycle-performance", "--json", ok=False)
        self.assertIn("invalid schema 5 runtime", performance.stderr)

        path.write_text('{"schema_version":5,"schema_version":5}')
        duplicate = run(self.repo, "worktree-list", "--json", ok=False)
        self.assertIn("duplicate JSON key", duplicate.stderr)

    def test_linked_worktrees_have_isolated_active_cycles_and_global_ids(self):
        second = Path(self.temp.name) / "second"
        third = Path(self.temp.name) / "third"
        subprocess.run(["git", "worktree", "add", "-b", "second", str(second), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "worktree", "add", "-b", "third", str(third), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        self.start()
        plan = Path(self.temp.name) / "plan.json"
        duplicate = run(
            second, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
            "--delivery-intent", "local", "--plan", str(plan), ok=False,
        )
        self.assertIn("cycle record already exists", duplicate.stderr)
        run(
            second, "start", "--cycle-id", "cycle-2", "--context", "test", "--risk", "routine",
            "--delivery-intent", "local", "--plan", str(plan),
        )
        first_status = json.loads(run(self.repo, "status", "--json").stdout)
        second_status = json.loads(run(second, "status", "--json").stdout)
        self.assertEqual(first_status["cycle_id"], "cycle-1")
        self.assertEqual(second_status["cycle_id"], "cycle-2")
        self.assertEqual(run(third, "status", "--json").stdout.strip(), "null")
        self.assertNotEqual(first_status["worktree"]["id"], second_status["worktree"]["id"])
        self.assertTrue((self.repo / ".git/dbsctr/cycles/cycle-2.json").exists())

    def test_concurrent_linked_starts_reserve_cycle_id_atomically(self):
        second = Path(self.temp.name) / "second"
        subprocess.run(["git", "worktree", "add", "-b", "second", str(second), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        self.start()
        first_record = self.record_path().read_text()
        first_pointer = next((self.repo / ".git/dbsctr/worktrees").glob("*/active"))
        first_pointer.unlink()
        self.record_path().unlink()
        plan = str(Path(self.temp.name) / "plan.json")
        command = [sys.executable, str(SCRIPT), "start", "--cycle-id", "race", "--context", "test",
                   "--risk", "routine", "--delivery-intent", "local", "--plan", plan]
        processes = [
            subprocess.Popen(command, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for repo in (self.repo, second)
        ]
        results = [process.communicate() + (process.returncode,) for process in processes]
        self.assertEqual(sorted(result[2] for result in results), [0, 1])
        self.assertIn("cycle record already exists", "".join(result[1] for result in results))
        self.assertTrue((self.repo / ".git/dbsctr/cycles/race.json").exists())
        self.assertEqual(sum(1 for path in (self.repo / ".git/dbsctr/worktrees").glob("*/active")
                             if path.read_text().strip() == "race"), 1)
        self.assertTrue(first_record)

    def test_remote_aliases_share_delivery_lock(self):
        remote = Path(self.temp.name) / "remote.git"
        second = Path(self.temp.name) / "second"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "mirror", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "fetch", "mirror"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "worktree", "add", "-b", "second", str(second), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "branch", "--set-upstream-to=mirror/master", "second"],
                       cwd=self.repo, check=True, capture_output=True)
        self.start()
        plan = str(Path(self.temp.name) / "plan.json")
        run(second, "start", "--cycle-id", "cycle-2", "--context", "test", "--risk", "routine",
            "--delivery-intent", "local", "--plan", plan)
        first = json.loads(self.record_path().read_text())
        second_record = json.loads((self.repo / ".git/dbsctr/cycles/cycle-2.json").read_text())
        self.assertEqual(first["delivery"]["lock_id"], second_record["delivery"]["lock_id"])

    def test_final_push_refuses_contended_target_lock(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "team/origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "team/origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        record = json.loads(self.record_path().read_text())
        lock = self.repo / ".git/dbsctr/locks" / f"{record['delivery']['lock_id']}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = run(self.repo, "final-push", ok=False)
        self.assertIn("locked by another DBSCTR cycle", result.stderr)

    def test_begin_isolates_cycle_from_dirty_source_worktree(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("unrelated dirty work\n")
        result = run(
            self.repo, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(worktrees),
            "--opencode-session-id", "session-structured",
            "--opencode-directory", str(self.repo / "docs"),
            "--opencode-worktree", str(self.repo),
        )
        handoff = json.loads(result.stdout)
        isolated = Path(handoff["worktree"])
        self.assertTrue(isolated.is_dir())
        self.assertEqual((self.repo / "tracked.txt").read_text(), "unrelated dirty work\n")
        record = json.loads((self.repo / ".git/dbsctr/cycles/isolated-1.json").read_text())
        self.assertTrue(record["worktree"]["created_by_dbsctr"])
        self.assertEqual(record["worktree"]["locator"], {
            "root": "cycle_worktree", "path": ".",
        })
        self.assertEqual(record["source"]["locator"], {
            "root": "primary_worktree", "path": ".",
        })
        self.assertEqual(record["source"]["dirty_paths"], ["tracked.txt"])
        self.assertEqual(record["runtime"]["opencode"]["session_ids"], ["session-structured"])
        adapter = record["runtime"]["adapters"]["opencode"]
        self.assertEqual(adapter["session_ids"], ["session-structured"])
        self.assertEqual(adapter["worktree"], {
            "root": record["runtime"]["opencode"]["path_root"],
            "path": record["runtime"]["opencode"]["worktree"],
        })
        self.assertEqual(json.loads(run(isolated, "status", "--json").stdout)["cycle_id"], "isolated-1")
        self.assertEqual(run(self.repo, "status", "--json").stdout.strip(), "null")

    def test_begin_normalizes_protected_merge_and_repository_identity(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_begin_delivery", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        args = SimpleNamespace(
            delivery_intent="merge", base_branch="develop", github_account="Saltiola7",
            github_repository=None,
        )
        with mock.patch.object(module, "git_repository_slug",
                               return_value="Saltiola7/dotfiles-ai"):
            module.normalize_begin_delivery(self.repo, args, "develop")
        self.assertEqual(args.delivery_intent, "draft_pr")
        self.assertEqual(args.github_repository, "Saltiola7/dotfiles-ai")

        args.github_repository = "other/dotfiles-ai"
        with mock.patch.object(module, "git_repository_slug",
                               return_value="Saltiola7/dotfiles-ai"), \
                self.assertRaisesRegex(RuntimeError, "must match configured GitHub repository"):
            module.normalize_begin_delivery(self.repo, args, "develop")

        with self.assertRaisesRegex(RuntimeError, "invalid remote"):
            module.github_repository_from_url(
                "https://token@github.com/Saltiola7/dotfiles-ai.git", "invalid remote"
            )
        destinations = [
            SimpleNamespace(stdout="https://github.com/Saltiola7/dotfiles-ai.git\n"),
            SimpleNamespace(stdout="git@github.com:other/dotfiles-ai.git\n"),
        ]
        with mock.patch.object(module, "git", side_effect=destinations), \
                self.assertRaisesRegex(RuntimeError, "remote must match"):
            module.github_remote_url(self.repo, "origin", "Saltiola7/dotfiles-ai")
        local = SimpleNamespace(
            delivery_intent="local", base_branch="develop", github_account=None,
            github_repository=None,
        )
        with self.assertRaisesRegex(RuntimeError, "protected base branch"):
            module.normalize_begin_delivery(self.repo, local, "develop")

    def test_begin_binds_fresh_initiative_receipt_to_cycle_record(self):
        remote = Path(self.temp.name) / "initiative-remote.git"
        worktrees = Path(self.temp.name) / "initiative-worktrees"
        value = initiative_manifest()
        value["slices"][0].pop("tickets")
        manifest = self.write_initiative(value)
        subprocess.run(["git", "add", str(manifest.relative_to(self.repo))], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "initiative"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/example/test.git"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "upstream", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "upstream", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        checked = json.loads(run(
            self.repo, "initiative-check", "--manifest", str(manifest), "--json",
        ).stdout)
        plan = self.plan_path()
        stale = run(
            self.repo, "begin", "--cycle-id", "initiative-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(plan),
            "--worktree-root", str(worktrees),
            "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
            "--initiative-slice", "slice-a", "--initiative-digest", checked["manifest_digest"],
            "--expected-plan-digest", "0" * 64, "--expected-repository", "example/test",
            ok=False,
        )
        self.assertIn("plan changed after approval", stale.stderr)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "initiative-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(plan),
            "--worktree-root", str(worktrees),
            "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
            "--initiative-slice", "slice-a", "--initiative-digest", checked["manifest_digest"],
            "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
            "--expected-repository", "example/test",
        ).stdout)
        record = json.loads((self.repo / ".git/dbsctr/cycles/initiative-1.json").read_text())
        self.assertEqual(record["initiative"], handoff["initiative"])
        self.assertEqual(record["initiative"]["manifest_digest"], checked["manifest_digest"])
        self.assertEqual(record["initiative"]["manifest_path"],
                         "docs/initiatives/test/MANIFEST.json")

    def test_schema5_managed_worktree_rebinds_to_configured_registry(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "portable-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            env=env,
        ).stdout)
        record_path = self.repo / ".git/dbsctr/cycles/portable-1.json"
        record = json.loads(record_path.read_text())
        self.assertEqual(record["schema_version"], 5)
        self.assertEqual(record["worktree"]["locator"]["root"], "dbsctr_worktrees")
        self.assertFalse(Path(record["worktree"]["locator"]["path"]).is_absolute())
        self.assertNotIn(str(registry), json.dumps(record))
        self.assertNotIn("git_dir", record["worktree"])
        self.assertEqual(record["source"]["locator"], {"root": "primary_worktree", "path": "."})
        self.assertNotIn("path", record["source"])

        relocated = Path(self.temp.name) / "relocated"
        relocated.parent.mkdir(parents=True, exist_ok=True)
        registry.rename(relocated)
        rebound = {**env, "DBSCTR_WORKTREE_ROOT": str(relocated)}
        moved = relocated / Path(record["worktree"]["locator"]["path"])
        subprocess.run(["git", "worktree", "repair", str(moved)], cwd=self.repo, check=True,
                       capture_output=True)
        self.assertEqual(json.loads(run(moved, "status", "--json", env=rebound).stdout)["cycle_id"],
                         "portable-1")
        self.assertEqual(Path(handoff["worktree"]).name, moved.name)

    def test_schema4_rejects_worktree_locator_traversal(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["worktree"]["locator"] = {"root": "cycle_worktree", "path": "../escape"}
        self.record_path().write_text(json.dumps(record))
        result = run(self.repo, "status", "--json", ok=False)
        self.assertIn("invalid cycle worktree locator", result.stderr)

    def test_status_rejects_unsafe_active_pointer(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        target = Path(self.temp.name) / "foreign-pointer"
        target.write_text("../escape\n")
        pointer.unlink()
        pointer.symlink_to(target)
        result = run(self.repo, "status", "--json", ok=False)
        self.assertIn("active pointer is unsafe", result.stderr)
        pointer.unlink()
        pointer.parent.rmdir()
        external = Path(self.temp.name) / "pointer-parent"
        external.mkdir()
        (external / "active").write_text("cycle-1\n")
        pointer.parent.symlink_to(external, target_is_directory=True)
        result = run(self.repo, "status", "--json", ok=False)
        self.assertIn("managed DBSCTR directory is unsafe", result.stderr)

    def test_schema3_cycle_record_remains_readable(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["schema_version"] = 3
        record["worktree"] = {
            "id": hashlib.sha256(str(self.repo.resolve()).encode()).hexdigest()[:16],
            "path": str(self.repo.resolve()), "git_dir": str((self.repo / ".git").resolve()),
            "branch": "master", "base_commit": record["git"]["head"],
            "created_by_dbsctr": False,
        }
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(json.loads(run(self.repo, "status", "--json").stdout)["schema_version"], 3)
        self.assertTrue(run(
            self.repo, "record-evidence", "domain", "--authority", "legacy", "--",
            sys.executable, "-c", "print('ok')",
        ).stdout.strip())

    def test_schema_less_linked_worktree_pointer_remains_readable(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        common_pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        common_pointer.unlink()
        linked = Path(self.temp.name) / "linked"
        subprocess.run(["git", "worktree", "add", "-b", "linked", str(linked), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        record.pop("schema_version")
        record["cycle_id"] = "legacy-linked"
        record["worktree"]["locator"] = {"root": "cycle_worktree", "path": "."}
        git_dir_value = subprocess.run(
            ["git", "rev-parse", "--git-dir"], cwd=linked, check=True, text=True,
            capture_output=True,
        ).stdout.strip()
        linked_git = Path(git_dir_value)
        if not linked_git.is_absolute():
            linked_git = linked / linked_git
        legacy = linked_git.resolve() / "dbsctr"
        legacy.mkdir()
        (legacy / "active").write_text("legacy-linked\n")
        (legacy / "legacy-linked.json").write_text(json.dumps(record))
        status = json.loads(run(linked, "status", "--json").stdout)
        self.assertEqual(status["cycle_id"], "legacy-linked")

    def test_portable_identity_rejects_incomplete_or_multiple_root_history(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_identity_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)

        def result(stdout):
            return subprocess.CompletedProcess([], 0, stdout, "")

        with mock.patch.object(module, "git", return_value=result("true\n")):
            with self.assertRaisesRegex(RuntimeError, "complete Git history"):
                module.repository_identity(self.repo)
        with mock.patch.object(module, "git", side_effect=[
                result("false\n"), result("a\nb\n")]):
            with self.assertRaisesRegex(RuntimeError, "exactly one Git root"):
                module.repository_identity(self.repo)
        legacy = module.legacy_active_path(self.repo)
        legacy.parent.mkdir(parents=True)
        legacy.write_text("cycle-legacy\n")
        with mock.patch.object(module, "active_path", side_effect=RuntimeError("incomplete history")):
            self.assertEqual(module.resolved_active_path(self.repo), legacy)

    def test_schema4_rejects_noncanonical_runtime_worktree(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        result = run(
            self.repo, "begin", "--cycle-id", "cycle-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--opencode-session-id", "session-structured",
            "--opencode-worktree", str(self.repo / "docs"),
            "--opencode-directory", str(self.repo / "docs"),
            env={**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}, ok=False,
        )
        self.assertIn("invalid OpenCode runtime paths", result.stderr)

    def test_cycle_portabilize_is_reversible(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "legacy-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(registry), "--opencode-session-id", "session-legacy",
            "--opencode-worktree", str(self.repo), "--opencode-directory", str(self.repo / "docs"),
        ).stdout)
        record_path = self.repo / ".git/dbsctr/cycles/legacy-1.json"
        original = self.make_schema3_fixture("legacy-1", handoff["worktree"])
        self.assertEqual(original["schema_version"], 3)
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}

        converted = json.loads(run(
            self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env,
        ).stdout)
        self.assertEqual(converted, {"cycle_id": "legacy-1", "schema_version": 4})
        portable = json.loads(record_path.read_text())
        self.assertNotIn(original["worktree"]["path"], json.dumps(portable))
        self.assertNotIn(original["source"]["path"], json.dumps(portable["source"]))
        self.assertEqual(portable["runtime"]["opencode"]["path_root"], "primary_worktree")
        self.assertEqual(json.loads(run(Path(handoff["worktree"]), "status", "--json", env=env).stdout)[
            "schema_version"], 4)

        restored = json.loads(run(
            self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", "--rollback", env=env,
        ).stdout)
        self.assertEqual(restored, {"cycle_id": "legacy-1", "schema_version": 3})
        self.assertEqual(json.loads(record_path.read_text()), original)

    def test_cycle_portabilize_rejects_worktree_outside_registry(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(self.repo, "begin", "--cycle-id", "legacy-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(Path(self.temp.name) / "outside")).stdout)
        self.make_schema3_fixture("legacy-1", handoff["worktree"])
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(Path(self.temp.name) / "registry")}
        result = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("outside configured registry", result.stderr)

    def test_cycle_portabilize_requires_owned_legacy_pointer(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(self.repo, "begin", "--cycle-id", "legacy-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(registry)).stdout)
        record = self.make_schema3_fixture("legacy-1", handoff["worktree"])
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}
        pointer.unlink()
        missing = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("active pointer is missing", missing.stderr)
        pointer.write_text("other-cycle\n")
        foreign = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("active pointer identity changed", foreign.stderr)
        pointer.unlink()
        target = Path(self.temp.name) / "pointer-target"
        target.write_text("legacy-1\n")
        pointer.symlink_to(target)
        unsafe = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("active pointer is unsafe", unsafe.stderr)
        pointer.unlink()
        pointer.write_text("legacy-1\n")
        migrations = self.repo / ".git/dbsctr/migrations"
        (Path(self.temp.name) / "legacy-1.schema3.json").write_text(json.dumps(record))
        migrations.symlink_to(Path(self.temp.name), target_is_directory=True)
        escaped = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("managed DBSCTR directory is unsafe", escaped.stderr)

    def test_cycle_portabilize_recovers_interrupted_migration_and_rollback(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(self.repo, "begin", "--cycle-id", "legacy-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(registry)).stdout)
        self.make_schema3_fixture("legacy-1", handoff["worktree"])
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_portable_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        arguments = SimpleNamespace(cycle_id="legacy-1", rollback=False)
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(module, "root_dir", return_value=self.repo), \
                mock.patch.object(module, "write_active_pointer", side_effect=OSError("interrupted")):
            with self.assertRaisesRegex(OSError, "interrupted"):
                module.command_cycle_portabilize(arguments)
        record_path = self.repo / ".git/dbsctr/cycles/legacy-1.json"
        self.assertEqual(json.loads(record_path.read_text())["schema_version"], 4)
        run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env)

        original_save = module.save
        def interrupt_after_restore(path, value):
            original_save(path, value)
            if value.get("schema_version") == 3:
                raise OSError("interrupted restore")

        arguments.rollback = True
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(module, "root_dir", return_value=self.repo), \
                mock.patch.object(module, "save", side_effect=interrupt_after_restore):
            with self.assertRaisesRegex(OSError, "interrupted restore"):
                module.command_cycle_portabilize(arguments)
        self.assertEqual(json.loads(record_path.read_text())["schema_version"], 3)
        run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", "--rollback", env=env)
        self.assertFalse((self.repo / ".git/dbsctr/migrations/legacy-1.schema3.json").exists())

    def test_cycle_portabilize_retry_revalidates_legacy_pointer(self):
        remote = Path(self.temp.name) / "remote.git"
        registry = Path(self.temp.name) / "registry"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "legacy-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(registry),
        ).stdout)
        self.make_schema3_fixture("legacy-1", handoff["worktree"])
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_retry_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(module, "root_dir", return_value=self.repo), \
                mock.patch.object(module, "save", side_effect=OSError("before conversion")):
            with self.assertRaisesRegex(OSError, "before conversion"):
                module.command_cycle_portabilize(SimpleNamespace(cycle_id="legacy-1", rollback=False))
        record_path = self.repo / ".git/dbsctr/cycles/legacy-1.json"
        record = json.loads(record_path.read_text())
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        pointer.write_text("other-cycle\n")
        retry = run(self.repo, "cycle-portabilize", "--cycle-id", "legacy-1", env=env, ok=False)
        self.assertIn("active pointer identity changed", retry.stderr)
        self.assertEqual(json.loads(record_path.read_text())["schema_version"], 3)
        stable = module.worktree_id(Path(handoff["worktree"]))
        self.assertFalse((self.repo / ".git/dbsctr/worktrees" / stable / "active").exists())

    def test_attach_runtime_is_idempotent_for_cross_repository_primary(self):
        self.start()
        home = Path(self.temp.name) / "attach-home"
        database = home / ".local/share/opencode/opencode.db"
        database.parent.mkdir(parents=True)
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, agent text);
            create table message (id text primary key, session_id text, data text);
            insert into session values ('session-resumed', null, 'build-gpt');
            insert into session values ('session-child', 'session-resumed', 'builder-openai');
            insert into message values ('message-resumed', 'session-resumed',
                '{"model":{"providerID":"openai","modelID":"gpt-5.6-sol"}}');
            insert into message values ('message-child', 'session-child', '{}');
        """)
        connection.commit()
        connection.close()
        env = {**isolated_env(), "HOME": str(home)}
        activation = json.dumps({"schema_version": 1, "core_revision": "3.29", "overlays": {
            "build": "neutral-2026-07-26", "build-gpt": "openai-2026-07-26",
            "build-claude": "anthropic-2026-07-26",
        }})
        common = ("--opencode-message-id", "message-resumed", "--harness-activation-json", activation)
        run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed", *common,
            "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo), env=env)
        run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed", *common,
            "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo), env=env)
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["runtime"]["opencode"]["session_ids"], ["session-resumed"])
        self.assertEqual(record["runtime"]["opencode"]["harness_activation"], {
            "schema_version": 1, "provider_id": "openai", "model_id": "gpt-5.6-sol",
            "agent_id": "build-gpt", "core_revision": "3.29", "overlay_revision": "openai-2026-07-26",
        })
        adapter = record["runtime"]["adapters"]["opencode"]
        self.assertEqual(adapter["session_ids"], ["session-resumed"])
        self.assertEqual(adapter["activation"], record["runtime"]["opencode"]["harness_activation"])
        self.assertEqual(adapter["worktree"], {
            "root": record["runtime"]["opencode"]["path_root"],
            "path": record["runtime"]["opencode"]["worktree"],
        })
        child = run(self.repo, "attach-runtime", "--opencode-session-id", "session-child",
                    "--opencode-message-id", "message-child",
                    "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo), env=env, ok=False)
        self.assertIn("primary OpenCode session", child.stderr)
        unstructured = run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed",
                           "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo), env=env, ok=False)
        self.assertIn("structured message identity", unstructured.stderr)
        mismatch = run(self.repo, "attach-runtime", "--opencode-session-id", "session-wrong", *common,
                       "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo), env=env, ok=False)
        self.assertIn("does not own", mismatch.stderr)
        other = Path(self.temp.name) / "other"
        other.mkdir()
        subprocess.run(["git", "init"], cwd=other, check=True, capture_output=True)
        run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed", *common,
            "--opencode-directory", str(other), "--opencode-worktree", str(other), env=env)
        cross_record = json.loads(self.record_path().read_text())
        self.assertEqual(cross_record["runtime"]["opencode"]["session_ids"], ["session-resumed"])
        self.assertNotEqual(cross_record["runtime"]["opencode"].get("worktree"), str(other))

        record["state"] = "completed"
        self.record_path().write_text(json.dumps(record))
        completed = run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed", *common,
                        "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo),
                        env=env, ok=False)
        self.assertIn("not active", completed.stderr)

    def test_begin_fetches_before_classifying_ahead_commits(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("already remote\n")
        subprocess.run(["git", "commit", "-am", "already remote"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "push", str(remote), "HEAD:master"], cwd=self.repo, check=True,
                       capture_output=True)
        result = run(
            self.repo, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(Path(self.temp.name) / "isolated"),
        )
        self.assertEqual(json.loads(result.stdout)["cycle_id"], "isolated-1")

    def test_begin_configures_local_shared_dvc_cache(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        (self.repo / ".dvc/cache").mkdir(parents=True)
        (self.repo / ".dvc/config").write_text("[core]\n")
        (self.repo / ".dvc/.gitignore").write_text("/config.local\n/cache\n")
        subprocess.run(["git", "add", ".dvc/config", ".dvc/.gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "dvc"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        linked_source = Path(self.temp.name) / "linked-source"
        subprocess.run(["git", "worktree", "add", "-b", "linked-source", str(linked_source), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "branch", "--set-upstream-to", "origin/master", "linked-source"],
                       cwd=self.repo, check=True, capture_output=True)
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        fake_dvc = fake_bin / "dvc"
        custom_cache = self.repo / ".dvc/cache"
        query_log = Path(self.temp.name) / "dvc-query.log"
        fake_dvc.write_text(
            "#!/bin/sh\nif [ \"$#\" -eq 2 ]; then pwd > \"$DVC_QUERY_LOG\"; printf '%s\\n' '.dvc/cache'; "
            "elif [ \"$1 $2\" = \"cache dir\" ]; then printf '[cache]\\n    dir = %s\\n' \"$4\" > .dvc/config.local; "
            "else printf '    type = %s\\n' \"$4\" >> .dvc/config.local; fi\n"
        )
        fake_dvc.chmod(0o755)
        env = {**isolated_env(), "PATH": f"{fake_bin}:{os.environ['PATH']}", "DVC_QUERY_LOG": str(query_log)}
        handoff = json.loads(run(
            linked_source, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(Path(self.temp.name) / "isolated"), env=env,
        ).stdout)
        configured = (Path(handoff["worktree"]) / ".dvc/config.local").read_text()
        self.assertIn(f"dir = {custom_cache.resolve()}", configured)
        self.assertIn("type = reflink,copy", configured)
        self.assertEqual(Path(query_log.read_text().strip()).resolve(), self.repo.resolve())

    def test_source_sync_updates_clean_and_skips_dirty_checkout(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_sync_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        source = {"path": str(self.repo), "branch": "master", "upstream": "origin/master",
                  "remote": module.remote_destination(self.repo, "origin/master")}
        self.assertEqual(module.sync_source_checkout({"source": source}, "origin", "master")["status"], "updated")
        (self.repo / "tracked.txt").write_text("dirty\n")
        result = module.sync_source_checkout({"source": source}, "origin", "master")
        self.assertEqual(result, {"status": "skipped", "reason": "dirty"})

    def test_begin_rejects_unknown_ahead_commits(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("ahead\n")
        subprocess.run(["git", "commit", "-am", "ahead"], cwd=self.repo, check=True, capture_output=True)
        result = run(
            self.repo, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(Path(self.temp.name) / "isolated"), ok=False,
        )
        self.assertIn("unknown commits are ahead", result.stderr)

    def test_cleanup_removes_only_clean_completed_dbsctr_worktree(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(worktrees),
        ).stdout)
        record_path = self.repo / ".git/dbsctr/cycles/isolated-1.json"
        record = json.loads(record_path.read_text())
        record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
        record_path.write_text(json.dumps(record))
        evidence = self.repo / ".git/dbsctr/evidence/isolated-1"
        evidence.mkdir(parents=True)
        (evidence / "retained-sidecar").write_bytes(b"safe")
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        pointer.unlink()
        inventory = json.loads(run(self.repo, "worktree-list", "--json", "--now").stdout)["worktrees"]
        item = next(item for item in inventory if item["cycle_id"] == "isolated-1")
        self.assertTrue(item["cleanup_candidate"])
        self.assertGreater(item["bytes"], 0)
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_cleanup_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        original_save = module.save

        def fail_removed_marker(path, value):
            if value.get("cleanup", {}).get("state") == "worktree_removed":
                raise OSError("interrupted cleanup")
            return original_save(path, value)

        with mock.patch.object(module, "root_dir", return_value=self.repo), \
              mock.patch.object(module, "save", side_effect=fail_removed_marker):
            with self.assertRaises(OSError):
                module.command_cleanup(SimpleNamespace(cycle_id="isolated-1", now=True))
        removing_record = json.loads(record_path.read_text())
        self.assertEqual(removing_record["cleanup"]["state"], "removing_worktree")
        self.assertFalse(Path(handoff["worktree"]).exists())

        def fail_parked_marker(path, value):
            if value.get("cleanup", {}).get("state") == "evidence_parked":
                raise OSError("interrupted cleanup")
            return original_save(path, value)

        with mock.patch.object(module, "root_dir", return_value=self.repo), \
              mock.patch.object(module, "save", side_effect=fail_parked_marker):
            with self.assertRaises(OSError):
                module.command_cleanup(SimpleNamespace(cycle_id="isolated-1", now=True))
        parked_record = json.loads(record_path.read_text())
        self.assertEqual(parked_record["cleanup"]["state"], "worktree_removed")
        self.assertTrue((evidence.parent / "isolated-1.cleanup").exists())
        run(self.repo, "cleanup", "--cycle-id", "isolated-1", "--now")
        self.assertFalse(Path(handoff["worktree"]).exists())
        self.assertFalse(record_path.exists())
        self.assertFalse(evidence.exists())

    def test_cycle_retirement_preserves_record_and_branch_and_rejects_dirty_work(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo,
                       check=True, capture_output=True)

        created = {}
        for cycle_id in ("retire-empty", "retire-integrated", "retire-superseded",
                         "retire-dirty", "retire-retry"):
            handoff = json.loads(run(
                self.repo, "begin", "--cycle-id", cycle_id, "--context", "test",
                "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
                "--worktree-root", str(worktrees),
            ).stdout)
            created[cycle_id] = Path(handoff["worktree"])
            if cycle_id not in {"retire-empty", "retire-retry"}:
                target = created[cycle_id]
                (target / "tracked.txt").write_text(cycle_id + "\n")
                subprocess.run(["git", "commit", "-am", cycle_id], cwd=target,
                               check=True, capture_output=True)
                commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target, text=True,
                                        check=True, capture_output=True).stdout.strip()
                record_path = self.repo / f".git/dbsctr/cycles/{cycle_id}.json"
                record = json.loads(record_path.read_text())
                record["commits"] = [{"id": commit, "gates": ["domain"]}]
                record_path.write_text(json.dumps(record))
                if cycle_id == "retire-integrated":
                    subprocess.run(["git", "push", "origin", "HEAD:master"], cwd=target,
                                   check=True, capture_output=True)
            if cycle_id == "retire-dirty":
                (created[cycle_id] / "dirty.txt").write_text("dirty\n")

        mismatch = run(
            self.repo, "cycle-retire", "--cycle-id", "retire-empty", "--confirm", "wrong",
            "--disposition", "empty", "--reason", "No cycle work exists", ok=False,
        )
        self.assertIn("confirmation does not match", mismatch.stderr)
        dirty = run(
            self.repo, "cycle-retire", "--cycle-id", "retire-dirty", "--confirm", "retire-dirty",
            "--disposition", "superseded", "--reason", "Current behavior supersedes this cycle", ok=False,
        )
        self.assertIn("dirty cycle worktree", dirty.stderr)

        for cycle_id, disposition in (("retire-empty", "empty"),
                                      ("retire-integrated", "integrated"),
                                      ("retire-superseded", "superseded")):
            result = json.loads(run(
                self.repo, "cycle-retire", "--cycle-id", cycle_id, "--confirm", cycle_id,
                "--disposition", disposition, "--reason", "Explicit stale cycle reconciliation",
            ).stdout)
            self.assertEqual(result["state"], "retired")
            self.assertFalse(created[cycle_id].exists())
            record = json.loads((self.repo / f".git/dbsctr/cycles/{cycle_id}.json").read_text())
            self.assertEqual(record["retirement"]["disposition"], disposition)
            self.assertEqual(record["state"], "retired")
            branch_name = f"dbsctr/test/{cycle_id}"
            subprocess.run(["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                           cwd=self.repo, check=True, capture_output=True)
        inventory = json.loads(run(self.repo, "worktree-list", "--json", "--now").stdout)["worktrees"]
        retired = [item for item in inventory if item["state"] == "retired"]
        self.assertEqual(len(retired), 3)
        self.assertTrue(all(not item["present"] and not item["cleanup_candidate"]
                            and not item["cleanup_blockers"] for item in retired))

        loader = importlib.machinery.SourceFileLoader("dbsctrctl_retire_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        original_save = module.save

        def interrupt_terminal_save(path, value):
            if value.get("state") == "retired":
                raise OSError("interrupted retirement")
            return original_save(path, value)

        arguments = SimpleNamespace(cycle_id="retire-retry", confirm="retire-retry",
                                    disposition="empty", reason="Explicit retry evidence")
        with mock.patch.object(module, "root_dir", return_value=self.repo), \
              mock.patch.object(module, "save", side_effect=interrupt_terminal_save):
            with self.assertRaises(OSError):
                module.command_cycle_retire(arguments)
        self.assertFalse(created["retire-retry"].exists())
        interrupted = json.loads((self.repo / ".git/dbsctr/cycles/retire-retry.json").read_text())
        self.assertEqual(interrupted["retirement"]["state"], "removing_worktree")
        recovered = json.loads(run(
            self.repo, "cycle-retire", "--cycle-id", "retire-retry", "--confirm", "retire-retry",
            "--disposition", "empty", "--reason", "Explicit retry evidence",
        ).stdout)
        self.assertEqual(recovered["state"], "retired")

    def test_completed_shared_worktree_retirement_proves_every_cycle_is_integrated(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo,
                       check=True, capture_output=True)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "shared-owner", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(worktrees),
        ).stdout)
        worktree = Path(handoff["worktree"])
        record_path = self.repo / ".git/dbsctr/cycles/shared-owner.json"
        owner = json.loads(record_path.read_text())
        commits = []
        for number in (1, 2):
            (worktree / "tracked.txt").write_text(f"shared {number}\n")
            subprocess.run(["git", "commit", "-am", f"shared {number}"], cwd=worktree,
                           check=True, capture_output=True)
            commits.append(subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=worktree, text=True,
                check=True, capture_output=True,
            ).stdout.strip())
        owner.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z",
                      "commits": [{"id": commits[0], "gates": ["domain"]}]})
        record_path.write_text(json.dumps(owner))
        followup = {**owner, "cycle_id": "shared-followup",
                    "commits": [{"id": commits[1], "gates": ["review_integrate"]}],
                    "worktree": {**owner["worktree"], "created_by_dbsctr": False}}
        (self.repo / ".git/dbsctr/cycles/shared-followup.json").write_text(json.dumps(followup))
        (self.repo / ".git/dbsctr/worktrees" / owner["worktree"]["id"] / "active").unlink()
        subprocess.run(["git", "push", "origin", "HEAD:master"], cwd=worktree,
                       check=True, capture_output=True)

        result = json.loads(run(
            self.repo, "cycle-retire-worktree", "--cycle-id", "shared-owner",
            "--confirm", "shared-owner", "--reason", "All shared cycles are integrated",
        ).stdout)
        self.assertEqual(result["worktree"], "retired")
        self.assertFalse(worktree.exists())
        retired = json.loads(record_path.read_text())
        self.assertEqual(retired["state"], "completed")
        self.assertEqual(retired["worktree_retirement"]["related_cycles"],
                         ["shared-followup", "shared-owner"])
        subprocess.run(["git", "show-ref", "--verify", "refs/heads/dbsctr/test/shared-owner"],
                       cwd=self.repo, check=True, capture_output=True)
        inventory = json.loads(run(self.repo, "worktree-list", "--json", "--now").stdout)["worktrees"]
        item = next(item for item in inventory if item["cycle_id"] == "shared-owner")
        self.assertFalse(item["present"] or item["cleanup_candidate"] or item["cleanup_blockers"])

    def test_batch_cleanup_continues_after_dirty_completed_worktree(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        paths = {}
        for cycle_id in ("batch-clean", "batch-dirty"):
            handoff = json.loads(run(
                self.repo, "begin", "--cycle-id", cycle_id, "--context", "test",
                "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
                "--worktree-root", str(worktrees),
            ).stdout)
            paths[cycle_id] = Path(handoff["worktree"])
            record_path = self.repo / f".git/dbsctr/cycles/{cycle_id}.json"
            record = json.loads(record_path.read_text())
            record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
            record_path.write_text(json.dumps(record))
            (self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active").unlink()
        (paths["batch-dirty"] / "dirty.txt").write_text("dirty\n")
        (self.repo / ".git/dbsctr/cycles/malformed.json").write_text("{")
        mismatch = json.loads((self.repo / ".git/dbsctr/cycles/batch-dirty.json").read_text())
        mismatch["cycle_id"] = "redirected"
        (self.repo / ".git/dbsctr/cycles/mismatch.json").write_text(json.dumps(mismatch))
        structural = json.loads((self.repo / ".git/dbsctr/cycles/batch-dirty.json").read_text())
        structural["cycle_id"] = "structural"
        structural.pop("context")
        (self.repo / ".git/dbsctr/cycles/structural.json").write_text(json.dumps(structural))

        result = run(self.repo, "cleanup", "--completed", "--now", ok=False)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["removed"], ["batch-clean"])
        self.assertEqual([item["cycle_id"] for item in summary["failed"]],
                         ["malformed", "mismatch", "batch-dirty", "structural"])
        self.assertFalse(paths["batch-clean"].exists())
        self.assertTrue(paths["batch-dirty"].exists())

    def test_global_inventory_and_cleanup_are_bounded_and_fail_closed(self):
        registry = Path(self.temp.name) / "registry"
        registry.mkdir()

        def completed_worktree(repo, name, dirty=False, worktree_root=None):
            remote = Path(self.temp.name) / f"{name}.git"
            if subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo,
                              capture_output=True).returncode:
                subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
                subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo,
                               check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo,
                           check=True, capture_output=True)
            handoff = json.loads(run(
                repo, "begin", "--cycle-id", name, "--context", "test", "--risk", "routine",
                "--delivery-intent", "local", "--plan", str(self.plan_path()),
                "--worktree-root", str(worktree_root or registry / name),
            ).stdout)
            record_path = repo / f".git/dbsctr/cycles/{name}.json"
            record = json.loads(record_path.read_text())
            record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
            record_path.write_text(json.dumps(record))
            (repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active").unlink()
            worktree = Path(handoff["worktree"])
            if dirty:
                (worktree / "dirty.txt").write_text("dirty\n")
            return worktree

        clean = completed_worktree(self.repo, "global-clean")
        escaped = completed_worktree(
            self.repo, "global-outside", worktree_root=Path(self.temp.name) / "outside-worktrees")
        second = Path(self.temp.name) / "second"
        second.mkdir()
        subprocess.run(["git", "init"], cwd=second, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=second, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=second, check=True)
        (second / "tracked.txt").write_text("base\n")
        artifacts = second / "docs/specs/test"
        artifacts.mkdir(parents=True)
        for name in ("README.md", "BACKLOG.md", "CHANGELOG.md"):
            (artifacts / name).write_text("base\n")
        subprocess.run(["git", "add", "."], cwd=second, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=second, check=True, capture_output=True)
        dirty = completed_worktree(second, "global-dirty", dirty=True)

        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (registry / "escape").symlink_to(outside, target_is_directory=True)
        env = {**isolated_env(), "DBSCTR_WORKTREE_ROOT": str(registry)}
        inventory = json.loads(run(self.repo, "worktree-list", "--all", "--json", env=env).stdout)
        self.assertEqual(len(inventory["repositories"]), 2)
        self.assertNotIn(str(self.temp.name), json.dumps(inventory))

        result = run(self.repo, "cleanup", "--completed", "--all", env=env, ok=False)
        report = json.loads(result.stdout)
        self.assertEqual([item["cycle_id"] for item in report["removed"]], ["global-clean"])
        self.assertEqual({item["error"] for item in report["failed"]}, {"dirty", "outside_registry"})
        self.assertFalse(clean.exists())
        self.assertTrue(dirty.exists())
        self.assertTrue(escaped.exists())
        self.assertNotIn(str(self.temp.name), result.stdout + result.stderr)

    def test_cleanup_rejects_missing_or_changed_worktree_identity(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        for cycle_id in ("changed-identity", "missing-worktree"):
            handoff = json.loads(run(
                self.repo, "begin", "--cycle-id", cycle_id, "--context", "test",
                "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
                "--worktree-root", str(worktrees),
            ).stdout)
            record_path = self.repo / f".git/dbsctr/cycles/{cycle_id}.json"
            record = json.loads(record_path.read_text())
            record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
            (self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active").unlink()
            if cycle_id == "changed-identity":
                record["worktree"]["id"] = "0" * 16
                record_path.write_text(json.dumps(record))
                result = run(self.repo, "cleanup", "--cycle-id", cycle_id, "--now", ok=False)
                self.assertIn("identity changed", result.stderr)
                self.assertTrue(Path(handoff["worktree"]).exists())
            else:
                record_path.write_text(json.dumps(record))
                subprocess.run(["git", "worktree", "remove", "--force", handoff["worktree"]],
                               cwd=self.repo, check=True, capture_output=True)
                result = run(self.repo, "cleanup", "--cycle-id", cycle_id, "--now", ok=False)
                self.assertIn("worktree is missing", result.stderr)

    def test_cleanup_retries_after_branch_deletion_failure(self):
        remote = Path(self.temp.name) / "remote.git"
        worktrees = Path(self.temp.name) / "isolated"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "branch-retry", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(worktrees),
        ).stdout)
        record_path = self.repo / ".git/dbsctr/cycles/branch-retry.json"
        record = json.loads(record_path.read_text())
        record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
        record_path.write_text(json.dumps(record))
        (self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active").unlink()
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_branch_cleanup_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        original_git = module.git

        def fail_branch(root, *args, **kwargs):
            if args[:2] == ("branch", "-d"):
                return subprocess.CompletedProcess(args, 1, "", "branch locked")
            return original_git(root, *args, **kwargs)

        with mock.patch.object(module, "root_dir", return_value=self.repo), \
             mock.patch.object(module, "git", side_effect=fail_branch):
            with self.assertRaisesRegex(RuntimeError, "branch locked"):
                module.command_cleanup(SimpleNamespace(cycle_id="branch-retry", completed=False, now=True))
        self.assertFalse(Path(handoff["worktree"]).exists())
        self.assertEqual(json.loads(record_path.read_text())["cleanup"]["state"], "worktree_removed")
        legacy = json.loads(record_path.read_text())
        legacy["cleanup"].pop("branch")
        record_path.write_text(json.dumps(legacy))
        with mock.patch.object(module, "root_dir", return_value=self.repo), \
             mock.patch.object(module, "git", side_effect=fail_branch):
            with self.assertRaisesRegex(RuntimeError, "branch locked"):
                module.command_cleanup(SimpleNamespace(cycle_id="branch-retry", completed=False, now=True))
        self.assertEqual(json.loads(record_path.read_text())["cleanup"]["branch"], record["worktree"]["branch"])
        drifted = json.loads(record_path.read_text())
        drifted["worktree"]["branch"] = "master"
        record_path.write_text(json.dumps(drifted))
        result = run(self.repo, "cleanup", "--cycle-id", "branch-retry", "--now", ok=False)
        self.assertIn("invalid cycle worktree branch", result.stderr)
        drifted["worktree"]["branch"] = record["worktree"]["branch"]
        record_path.write_text(json.dumps(drifted))
        run(self.repo, "cleanup", "--cycle-id", "branch-retry", "--now")
        self.assertFalse(record_path.exists())

    def test_cleanup_rejects_low_level_or_drifted_worktree(self):
        self.start()
        record_path = self.record_path()
        record = json.loads(record_path.read_text())
        record.update({"state": "completed", "completed_at": "2026-01-01T00:00:00Z"})
        record_path.write_text(json.dumps(record))
        result = run(self.repo, "cleanup", "--cycle-id", "cycle-1", "--now", ok=False)
        self.assertIn("DBSCTR-created", result.stderr)

        record["worktree"]["created_by_dbsctr"] = True
        record_path.write_text(json.dumps(record))
        other = Path(self.temp.name) / "other"
        subprocess.run(["git", "worktree", "add", "-b", "other", str(other), "HEAD"],
                       cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "switch", "-c", "drift"], cwd=self.repo, check=True,
                       capture_output=True)
        result = run(other, "cleanup", "--cycle-id", "cycle-1", "--now", ok=False)
        self.assertIn("worktree is missing", result.stderr)

    def test_audit_reads_fixed_commit_and_excludes_dirty_overlay(self):
        built_from = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                    text=True, capture_output=True).stdout.strip()
        incomplete = self.repo / "docs/specs/incomplete"
        incomplete.mkdir(parents=True)
        (incomplete / "README.md").write_text("# Incomplete\n")
        graph = self.repo / "graphify-out"
        graph.mkdir()
        (graph / "GRAPH_REPORT.md").write_text(f"Built from commit: `{built_from}`\n")
        old_name = self.repo / "old name.txt"
        old_name.write_text("rename fixture\n")
        subprocess.run(["git", "add", "docs/specs/incomplete", "graphify-out", "old name.txt"], cwd=self.repo,
                       check=True)
        subprocess.run(["git", "commit", "-m", "audit fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        audited = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                 text=True, capture_output=True).stdout.strip()
        (incomplete / "BACKLOG.md").write_text("dirty overlay\n")
        subprocess.run(["git", "mv", "old name.txt", "new name.txt"], cwd=self.repo, check=True)
        index_mtime = (self.repo / ".git/index").stat().st_mtime_ns
        result = json.loads(run(self.repo, "audit", "--commit", audited, "--json").stdout)
        self.assertEqual(result["commit"], audited)
        self.assertIn("docs/specs/incomplete/BACKLOG.md", result["dirty_overlay_excluded"])
        self.assertIn("old name.txt", result["dirty_overlay_excluded"])
        self.assertIn("new name.txt", result["dirty_overlay_excluded"])
        self.assertEqual((self.repo / ".git/index").stat().st_mtime_ns, index_mtime)
        findings = {(item["code"], item["path"]) for item in result["findings"]}
        self.assertFalse(any(code == "missing_context_ticket" for code, _path in findings))
        self.assertIn(("missing_lifecycle_artifact", "docs/specs/incomplete/CHANGELOG.md"), findings)
        self.assertIn(("stale_graph", "graphify-out/GRAPH_REPORT.md"), findings)
        self.assertIn(("missing_graph_receipt", "graphify-out/graph.receipt.json"), findings)

    def test_audit_accepts_canonical_backlog(self):
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                              text=True, capture_output=True).stdout.strip()
        context = self.repo / "docs/specs/canonical"
        context.mkdir(parents=True)
        (context / "README.md").write_text("# Canonical\n")
        (context / "CHANGELOG.md").write_text("# Changelog\n")
        (context / "BACKLOG.md").write_text(
            "# Backlog\n\n## Active\n\n"
            "| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n\n"
            "## Completed\n\n| id | outcome | completed | commit |\n|---|---|---|---|\n"
            f"| CAN-1 | Shipped | 2026-01-01 | `{base[:7]}` |\n"
        )
        replacement_path = self.repo / "replacement-backlog.md"
        replacement_path.write_text("# Replaced\n")
        subprocess.run(["git", "add", "docs/specs/canonical", "replacement-backlog.md"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "canonical backlog"], cwd=self.repo, check=True,
                       capture_output=True)
        original = subprocess.run(["git", "rev-parse", "HEAD:docs/specs/canonical/BACKLOG.md"],
                                  cwd=self.repo, check=True, text=True,
                                  capture_output=True).stdout.strip()
        replacement = subprocess.run(["git", "rev-parse", "HEAD:replacement-backlog.md"],
                                     cwd=self.repo, check=True, text=True,
                                     capture_output=True).stdout.strip()
        subprocess.run(["git", "replace", original, replacement], cwd=self.repo, check=True)

        result = json.loads(run(self.repo, "audit", "--json").stdout)
        self.assertEqual([], [item for item in result["findings"]
                              if item.get("context") == "canonical"])

    def test_audit_reports_deterministic_backlog_findings_from_commit(self):
        context = self.repo / "docs/specs/broken"
        context.mkdir(parents=True)
        (context / "README.md").write_text("# Broken\n")
        (context / "CHANGELOG.md").write_text("# Changelog\n")
        (context / "BACKLOG.md").write_text(
            "# Broken\n\n## Active\n\n"
            "| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| SAME | First | high | done | - | x | y | no | stale | S | audit |\n"
            "| SAME | Second | high | pending | - | x | y | no | duplicate | S | audit |\n"
            "| SAME | malformed |\n\n"
            "## Completed\n\n| id | outcome | completed | commit |\n|---|---|---|---|\n"
            "| SAME | Broken | 2026-1-1 | `deadbee` |\n"
        )
        subprocess.run(["git", "add", "docs/specs/broken"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "broken backlog"], cwd=self.repo, check=True,
                       capture_output=True)
        audited = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                 text=True, capture_output=True).stdout.strip()
        (context / "BACKLOG.md").write_text("dirty replacement\n")

        result = json.loads(run(self.repo, "audit", "--commit", audited, "--json").stdout)
        findings = [item for item in result["findings"] if item.get("context") == "broken"]
        self.assertEqual([], findings)

    def test_audit_assigns_missing_sections_to_document_line_one(self):
        context = self.repo / "docs/specs/missing_sections"
        context.mkdir(parents=True)
        for name, content in (("README.md", "# Missing\n"), ("BACKLOG.md", "# Backlog\n"),
                              ("CHANGELOG.md", "# Changelog\n")):
            (context / name).write_text(content)
        subprocess.run(["git", "add", "docs/specs/missing_sections"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "missing backlog sections"], cwd=self.repo,
                       check=True, capture_output=True)

        result = json.loads(run(self.repo, "audit", "--json").stdout)
        findings = [item for item in result["findings"]
                    if item.get("context") == "missing_sections"]
        self.assertEqual([], findings)

    def test_audit_flags_unverifiable_graph_metadata(self):
        graph = self.repo / "graphify-out"
        graph.mkdir()
        (graph / "GRAPH_REPORT.md").write_text("Built from commit: `abc`\n")
        subprocess.run(["git", "add", "graphify-out"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "bad graph marker"], cwd=self.repo, check=True,
                       capture_output=True)
        result = json.loads(run(self.repo, "audit", "--json").stdout)
        self.assertIn("unverified_graph_freshness", {item["code"] for item in result["findings"]})

    def test_audit_accepts_receipted_graph_only_descendant(self):
        adapter = self.repo / "scripts/graphify"
        adapter.parent.mkdir()
        adapter.write_text("#!/bin/sh\nexit 0\n")
        adapter.chmod(0o755)
        subprocess.run(["git", "add", "scripts/graphify"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "adapter"], cwd=self.repo,
                       check=True, capture_output=True)
        source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
                                check=True, capture_output=True).stdout.strip()
        adapter_blob = subprocess.run(
            ["git", "rev-parse", "HEAD:scripts/graphify"], cwd=self.repo, text=True,
            check=True, capture_output=True).stdout.strip()
        graph = self.repo / "graphify-out"
        graph.mkdir()
        report = f"Built from commit: `{source}`\n"
        manifest = '{"schema_version":1}\n'
        (graph / "GRAPH_REPORT.md").write_text(report)
        (graph / "manifest.json").write_text(manifest)
        (graph / "graph.receipt.json").write_text(json.dumps({
            "schema_version": 1, "command_contract": "dbsctr-batch-graphify-v1",
            "batch_id": "batch-1", "source_head": source,
            "adapter": {"adapter": "scripts/graphify", "version": "0.9.50", "blob": adapter_blob},
            "output_files": ["GRAPH_REPORT.md", "manifest.json"],
            "manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            "output_sha256": {"GRAPH_REPORT.md": hashlib.sha256(report.encode()).hexdigest(),
                              "manifest.json": hashlib.sha256(manifest.encode()).hexdigest()},
            "created_at": "2026-08-25T00:00:00Z",
        }))
        subprocess.run(["git", "add", "graphify-out"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "graph only"], cwd=self.repo,
                       check=True, capture_output=True)
        result = json.loads(run(self.repo, "audit", "--json").stdout)
        self.assertFalse(result["graph"]["stale"])
        self.assertFalse({"stale_graph", "invalid_graph_receipt"}.intersection(
            item["code"] for item in result["findings"]))

    def test_audit_reports_non_utf8_dirty_filename(self):
        raw = os.fsencode(self.repo) + b"/bad-\xff"
        try:
            descriptor = os.open(raw, os.O_WRONLY | os.O_CREAT, 0o600)
        except OSError as error:
            self.skipTest(f"filesystem rejects non-UTF-8 names: {error}")
        os.close(descriptor)
        result = json.loads(run(self.repo, "audit", "--json").stdout)
        self.assertIn(b"bad-\xff", [os.fsencode(path) for path in result["dirty_overlay_excluded"]])

    def test_inspect_reads_only_the_resolved_commit_and_reports_overlay(self):
        (self.repo / "tracked.txt").write_text("committed needle\n")
        (self.repo / "nested").mkdir()
        (self.repo / "nested" / "match.txt").write_text("needle twice: needle\n")
        (self.repo / "binary.bin").write_bytes(b"\0binary")
        subprocess.run(["git", "add", "tracked.txt", "nested", "binary.bin"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "inspect fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                                capture_output=True).stdout.strip()
        (self.repo / "tracked.txt").write_text("dirty overlay\n")

        read = json.loads(run(
            self.repo, "inspect", "--commit", "HEAD", "--action", "read", "--path", "tracked.txt", "--json"
        ).stdout)
        self.assertEqual(read["commit"], commit)
        self.assertEqual(read["content"], "committed needle\n")
        self.assertIn("tracked.txt", read["dirty_overlay_excluded"])
        self.assertFalse(read["truncated"])

        binary = json.loads(run(
            self.repo, "inspect", "--commit", commit, "--action", "read", "--path", "binary.bin", "--json"
        ).stdout)
        self.assertTrue(binary["binary"])
        self.assertNotIn("content", binary)

        metadata = json.loads(run(
            self.repo, "inspect", "--commit", commit, "--action", "object", "--path", "tracked.txt", "--json"
        ).stdout)
        self.assertEqual(metadata["type"], "blob")
        self.assertEqual(metadata["size"], len("committed needle\n"))

        search = json.loads(run(
            self.repo, "inspect", "--commit", commit, "--action", "search", "--query", "needle", "--json"
        ).stdout)
        self.assertEqual([item["path"] for item in search["matches"]], ["nested/match.txt", "tracked.txt"])

    def test_inspect_rejects_unsafe_paths_and_has_deterministic_continuations(self):
        (self.repo / "many").mkdir()
        for index in range(3):
            (self.repo / "many" / f"{index}.txt").write_text(f"line {index}\n")
        subprocess.run(["git", "add", "many"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "tree fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        first = json.loads(run(
            self.repo, "inspect", "--action", "tree", "--path", "many", "--limit", "2", "--json"
        ).stdout)
        self.assertEqual([item["path"] for item in first["entries"]], ["many/0.txt", "many/1.txt"])
        self.assertEqual(first["continuation"], {"cursor": 2})
        second = json.loads(run(
            self.repo, "inspect", "--action", "tree", "--path", "many", "--limit", "2", "--cursor", "2", "--json"
        ).stdout)
        self.assertEqual([item["path"] for item in second["entries"]], ["many/2.txt"])
        self.assertIsNone(second["continuation"])
        for path in ("/etc/passwd", "../tracked.txt", "many/../0.txt", "bad\npath"):
            result = run(
                self.repo, "inspect", "--action", "read", "--path", path, "--json", ok=False
            )
            self.assertIn("unsafe path", result.stderr)

    def test_inspect_bounds_scopes_and_validates_action_arguments(self):
        (self.repo / "scope").mkdir()
        (self.repo / "scope" / "literal.txt").write_text("a.b\nneedle\n")
        (self.repo / "outside.txt").write_text("needle\n")
        (self.repo / "large.txt").write_bytes(b"needle\n" + b"x" * (4 * 1024 * 1024))
        subprocess.run(["git", "add", "scope", "outside.txt", "large.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "inspect bounds fixture"], cwd=self.repo, check=True,
                       capture_output=True)

        root = json.loads(run(self.repo, "inspect", "--action", "tree", "--json").stdout)
        self.assertIn("scope", [item["path"] for item in root["entries"]])
        scoped = json.loads(run(
            self.repo, "inspect", "--action", "search", "--path", "scope", "--query", "needle", "--json"
        ).stdout)
        self.assertEqual([item["path"] for item in scoped["matches"]], ["scope/literal.txt"])
        literal = json.loads(run(
            self.repo, "inspect", "--action", "search", "--query", "a.b", "--json"
        ).stdout)
        self.assertEqual([item["path"] for item in literal["matches"]], ["scope/literal.txt"])
        self.assertEqual(json.loads(run(
            self.repo, "inspect", "--action", "search", "--query", "a.b*", "--json"
        ).stdout)["matches"], [])

        for args, message in (
            (("--action", "read", "--path", "large.txt"), "4194304"),
            (("--action", "tree", "--limit", "101"), "tree limit"),
            (("--action", "search", "--query", "needle", "--excerpt", "2049"), "excerpt limit"),
            (("--action", "object", "--query", "needle"), "not valid"),
            (("--action", "read", "--path", "tracked.txt", "--cursor", "1"), "not valid"),
            (("--action", "tree", "--cursor", "999"), "cursor is outside"),
        ):
            result = run(self.repo, "inspect", *args, "--json", ok=False)
            self.assertIn(message, result.stderr)

    def test_inspect_disables_replacements_and_preserves_utf8_byte_boundaries(self):
        (self.repo / "original.txt").write_text("original\n")
        (self.repo / "replacement.txt").write_text("replacement\n")
        (self.repo / "unicode.txt").write_text("a" * 32767 + "é" + "z\n")
        (self.repo / "excerpt.txt").write_text("ééé needle\n")
        subprocess.run(["git", "add", "original.txt", "replacement.txt", "unicode.txt", "excerpt.txt"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "replacement fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        original = subprocess.run(["git", "rev-parse", "HEAD:original.txt"], cwd=self.repo, check=True,
                                  text=True, capture_output=True).stdout.strip()
        replacement = subprocess.run(["git", "rev-parse", "HEAD:replacement.txt"], cwd=self.repo, check=True,
                                     text=True, capture_output=True).stdout.strip()
        subprocess.run(["git", "replace", original, replacement], cwd=self.repo, check=True)

        read = json.loads(run(
            self.repo, "inspect", "--action", "read", "--path", "original.txt", "--json"
        ).stdout)
        self.assertEqual(read["content"], "original\n")
        first = json.loads(run(
            self.repo, "inspect", "--action", "read", "--path", "unicode.txt", "--json"
        ).stdout)
        self.assertEqual(first["continuation"], {"offset": 32767})
        second = json.loads(run(
            self.repo, "inspect", "--action", "read", "--path", "unicode.txt",
            "--offset", "32767", "--limit", "3", "--json"
        ).stdout)
        self.assertEqual(second["content"], "éz")
        invalid = run(
            self.repo, "inspect", "--action", "read", "--path", "unicode.txt",
            "--offset", "32768", "--json", ok=False,
        )
        self.assertIn("UTF-8 boundary", invalid.stderr)

        excerpt = json.loads(run(
            self.repo, "inspect", "--action", "search", "--path", "excerpt.txt",
            "--query", "needle", "--excerpt", "5", "--json",
        ).stdout)["matches"][0]
        self.assertEqual(excerpt["excerpt"], "éé")
        self.assertTrue(excerpt["excerpt_truncated"])

    def test_inspect_bounds_dirty_overlay_reporting(self):
        for index in range(101):
            (self.repo / f"dirty-{index:03}.txt").write_text("dirty\n")
        result = json.loads(run(self.repo, "inspect", "--action", "tree", "--json").stdout)
        self.assertEqual(len(result["dirty_overlay_excluded"]), 100)
        self.assertEqual(result["dirty_overlay_total"], 101)
        self.assertTrue(result["dirty_overlay_truncated"])

    def test_inspect_bounds_overlay_bytes_and_reports_both_rename_paths(self):
        (self.repo / "tracked.txt").rename(self.repo / "renamed.txt")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        renamed = json.loads(run(self.repo, "inspect", "--action", "tree", "--json").stdout)
        self.assertIn("tracked.txt", renamed["dirty_overlay_excluded"])
        self.assertIn("renamed.txt", renamed["dirty_overlay_excluded"])

        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        nested = self.repo
        for character in "abcd":
            nested /= character * 150
            nested.mkdir()
        for index in range(100):
            (nested / f"{index:03}-{'x' * 180}").write_text("dirty\n")
        bounded = json.loads(run(self.repo, "inspect", "--action", "tree", "--json").stdout)
        self.assertEqual(bounded["dirty_overlay_total"], 100)
        self.assertLess(len(bounded["dirty_overlay_excluded"]), 100)
        self.assertTrue(bounded["dirty_overlay_truncated"])

    def test_profile_change_requires_plan_update_before_commit(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        profile = self.repo / "docs/specs/test/README.md"
        profile.write_text("new profile\n")
        self.record_gate("domain", paths=("docs/specs/test/README.md",))
        run(
            self.repo, "gate-commit", "--message", "profile", "--gates", "domain",
            "--paths", "docs/specs/test/README.md",
        )
        record = json.loads(self.record_path().read_text())
        plan = {"profile": "docs/specs/test/README.md", "gates": {
            name: {key: value for key, value in gate.items() if key in ("applicability", "reason")}
            for name, gate in record["gates"].items()
        }}
        (self.repo / "tracked.txt").write_text("change\n")
        self.record_gate("domain", paths=("tracked.txt",))
        result = run(
            self.repo, "gate-commit", "--message", "change", "--gates", "domain",
            "--paths", "tracked.txt", ok=False,
        )
        self.assertIn("update the applicability plan", result.stderr)
        run(self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan))
        run(
            self.repo, "gate-commit", "--message", "change", "--gates", "domain",
            "--paths", "tracked.txt",
        )
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md",))
        run(
            self.repo, "gate-commit", "--message", "changelog", "--gates", "domain",
            "--paths", "docs/specs/test/CHANGELOG.md",
        )
        run(
            self.repo, "review-artifact", "README", "--result", "changed", "--reason", "profile",
            "--path", "docs/specs/test/README.md",
        )
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(
            self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md",
        )
        self.pass_gates()
        run(self.repo, "final-push")

    def test_plan_update_adopts_only_unrecorded_profile_commit(self):
        self.start()
        (self.repo / "tracked.txt").write_text("recorded behavior\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(
            self.repo, "gate-commit", "--message", "recorded", "--gates", "domain",
            "--paths", "tracked.txt",
        )
        record = json.loads(self.record_path().read_text())
        gate_entry = record["commits"][0]
        plan = {"profile": "docs/specs/test/README.md", "gates": {
            name: {key: value for key, value in gate.items() if key in ("applicability", "reason")}
            for name, gate in record["gates"].items()
        }}
        profile = self.repo / "docs/specs/test/README.md"
        profile.write_text("committed profile update\n")
        subprocess.run(["git", "add", str(profile)], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "profile update"], cwd=self.repo,
                       check=True, capture_output=True)
        profile_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
            capture_output=True, check=True).stdout.strip()
        run(self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan))
        self.assertEqual(json.loads(self.record_path().read_text())["commits"], [
            gate_entry,
            {"id": profile_commit, "gates": []},
        ])

        (self.repo / "tracked.txt").write_text("unrecorded behavior\n")
        subprocess.run(["git", "commit", "-am", "unrecorded behavior"], cwd=self.repo,
                       check=True, capture_output=True)
        rejected = run(
            self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan), ok=False)
        self.assertIn("changes more than the Engineering Profile", rejected.stderr)

    def test_plan_update_rejects_corrupt_recorded_lineage(self):
        self.start()
        (self.repo / "tracked.txt").write_text("recorded behavior\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(
            self.repo, "gate-commit", "--message", "recorded", "--gates", "domain",
            "--paths", "tracked.txt",
        )
        record = json.loads(self.record_path().read_text())
        plan = {"profile": "docs/specs/test/README.md", "gates": {
            name: {key: value for key, value in gate.items() if key in ("applicability", "reason")}
            for name, gate in record["gates"].items()
        }}
        record["commits"].append(record["commits"][0])
        self.record_path().write_text(json.dumps(record))
        duplicate = run(
            self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan), ok=False)
        self.assertIn("contain a duplicate", duplicate.stderr)

        record["commits"] = [{"id": "a" * 40, "gates": ["domain"]}]
        self.record_path().write_text(json.dumps(record))
        missing = run(
            self.repo, "update-plan", "--plan", "-", input_text=json.dumps(plan), ok=False)
        self.assertIn("missing from first-parent lineage", missing.stderr)

    def test_artifact_check_and_gate_transition_validation(self):
        self.start()
        self.assertNotEqual(run(self.repo, "check", "artifacts", ok=False).returncode, 0)
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "still accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "tracked")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "unchanged", "--reason", "pending completion")
        run(self.repo, "check", "artifacts")
        run(self.repo, "set-gate", "domain", "--result", "not_run", ok=False)
        run(self.repo, "set-gate", "domain", "--result", "passed", ok=False)
        run(self.repo, "set-gate", "release", "--result", "passed", ok=False)
        run(
            self.repo, "approve-exception", "contract", "--kind", "deferred",
            "--rationale", "too early", "--owner", "owner",
            "--review-condition", "later", ok=False,
        )
        run(
            self.repo, "set-applicability", "operate", "--value", "not_applicable",
            "--reason", "no runtime", ok=False,
        )
        run(self.repo, "set-gate", "operate", "--result", "passed", "--evidence", "x", ok=False)
        self.record_gate("domain", 1)
        run(
            self.repo, "approve-exception", "domain", "--kind", "deferred",
            "--rationale", "approved later", "--owner", "owner",
            "--review-condition", "next cycle",
        )
        self.record_gate("domain", 1)
        record = json.loads(self.record_path().read_text())
        self.assertNotIn("exception", record["gates"]["domain"])

    def test_changed_artifact_review_rejects_wrong_context_path(self):
        self.start()
        result = run(
            self.repo, "review-artifact", "CHANGELOG", "--result", "changed",
            "--reason", "wrong file", "--path", "tracked.txt", ok=False,
        )
        self.assertIn("docs/specs/test/CHANGELOG.md", result.stderr)

    def test_final_push_refuses_no_upstream(self):
        self.start()
        self.review_artifacts()
        self.pass_gates()
        run(self.repo, "final-push", ok=False)

    def test_final_push_refuses_dirty_worktree(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        self.review_artifacts()
        self.pass_gates()
        (self.repo / "tracked.txt").write_text("dirty\n")
        run(self.repo, "final-push", ok=False)

    def test_gate_commit_refuses_unrelated_staged_paths(self):
        self.start()
        (self.repo / "tracked.txt").write_text("wanted\n")
        self.record_gate("domain", paths=("tracked.txt",))
        (self.repo / "other.txt").write_text("base\n")
        subprocess.run(["git", "add", "other.txt"], cwd=self.repo, check=True)
        run(self.repo, "gate-commit", "--message", "wanted", "--gates", "domain", "--paths", "tracked.txt", ok=False)

    def test_gate_commit_accepts_explicit_new_file(self):
        self.start()
        (self.repo / "new.txt").write_text("new\n")
        self.record_gate("domain", paths=("new.txt",))
        result = run(self.repo, "gate-commit", "--message", "new file", "--gates", "domain", "--paths", "new.txt")
        self.assertEqual(len(result.stdout.strip()), 40)
        tracked = subprocess.run(
            ["git", "ls-files", "new.txt"], cwd=self.repo, check=True, text=True, capture_output=True
        ).stdout.strip()
        self.assertEqual(tracked, "new.txt")

    def test_gate_commit_accepts_tracked_deletion_and_nonsecret_source_name(self):
        (self.repo / "test_secret_loader.py").write_text("safe source\n")
        subprocess.run(["git", "add", "test_secret_loader.py"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=self.repo, check=True, capture_output=True)
        self.start()
        (self.repo / "tracked.txt").unlink()
        (self.repo / "test_secret_loader.py").write_text("changed safe source\n")
        self.record_gate("domain", paths=("tracked.txt", "test_secret_loader.py"))
        run(
            self.repo, "gate-commit", "--message", "delete and edit", "--gates", "domain", "--paths",
            "tracked.txt", "test_secret_loader.py",
        )

    def test_final_push_refuses_precycle_ahead_commit(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("before cycle\n")
        subprocess.run(["git", "commit", "-am", "before"], cwd=self.repo, check=True, capture_output=True)
        self.start()
        self.pass_gate()
        self.review_artifacts()
        self.pass_gates()
        run(self.repo, "final-push", ok=False)

    def test_final_push_fetches_and_rejects_advanced_target_before_finalizing(self):
        remote = Path(self.temp.name) / "remote.git"
        other = Path(self.temp.name) / "other"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain", "--paths",
            "docs/specs/test/CHANGELOG.md")
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "other@example.com"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.name", "Other"], cwd=other, check=True)
        (other / "other.txt").write_text("advance\n")
        subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)
        result = run(self.repo, "final-push", ok=False)
        self.assertIn("delivery target advanced", result.stderr)
        self.assertEqual(json.loads(self.record_path().read_text())["state"], "active")

    def test_final_push_accepts_recorded_linear_target_advance(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        original_baseline = json.loads(self.record_path().read_text())["git"]["head"]
        (self.repo / "integrated.txt").write_text("upstream advance\n")
        subprocess.run(["git", "add", "integrated.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "integrated upstream"], cwd=self.repo,
                       check=True, capture_output=True)
        advance = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                 text=True, capture_output=True).stdout.strip()
        subprocess.run(["git", "push"], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "tracked.txt").write_text("first gate\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "first gate", "--gates", "domain", "--paths", "tracked.txt")
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("behavior", paths=("docs/specs/test/CHANGELOG.md",))
        run(self.repo, "gate-commit", "--message", "closure", "--gates", "behavior", "--paths",
            "docs/specs/test/CHANGELOG.md")
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        hook = remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        run(self.repo, "final-push", ok=False)
        failed = json.loads(self.record_path().read_text())
        self.assertEqual(failed["state"], "finalizing")
        self.assertEqual(failed["git"]["head"], original_baseline)
        hook.unlink()
        run(self.repo, "final-push")
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["git"]["head"], advance)
        self.assertIn("reconciled_at", record["git"])

    def test_reconcile_target_previews_and_prepares_recorded_divergence(self):
        other = self.start_remote_cycle()
        (self.repo / "tracked.txt").write_text("cycle\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain",
            "--paths", "tracked.txt")
        (other / "other.txt").write_text("upstream\n")
        subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        before = json.loads(self.record_path().read_text())
        preview = json.loads(run(
            self.repo, "reconcile-target", "--mode", "preview", "--json").stdout)
        self.assertEqual(preview["status"], "diverged")
        self.assertEqual(preview["staged_paths"], [])
        self.assertEqual(preview["conflict_paths"], [])
        self.assertFalse((self.repo / ".git/MERGE_HEAD").exists())
        self.assertFalse(subprocess.run(["git", "status", "--porcelain"], cwd=self.repo,
                                        text=True, capture_output=True).stdout)

        prepared = json.loads(run(
            self.repo, "reconcile-target", "--mode", "prepare", "--json").stdout)
        self.assertEqual(prepared["status"], "prepared")
        self.assertEqual(prepared["staged_paths"], ["other.txt"])
        self.assertEqual(prepared["conflict_paths"], [])
        self.assertTrue((self.repo / ".git/MERGE_HEAD").exists())
        self.assertEqual(json.loads(self.record_path().read_text()), before)

    def test_reconcile_target_preserves_conflicts_for_primary_resolution(self):
        other = self.start_remote_cycle()
        (self.repo / "tracked.txt").write_text("cycle\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain",
            "--paths", "tracked.txt")
        (other / "tracked.txt").write_text("upstream\n")
        subprocess.run(["git", "commit", "-am", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        result = json.loads(run(
            self.repo, "reconcile-target", "--mode", "prepare", "--json").stdout)
        self.assertEqual(result["status"], "conflicts")
        self.assertEqual(result["conflict_paths"], ["tracked.txt"])
        self.assertEqual(result["staged_paths"], ["tracked.txt"])
        self.assertTrue((self.repo / ".git/MERGE_HEAD").exists())

    def test_reconcile_target_supports_recorded_merge_and_repeated_advance(self):
        other = self.start_remote_cycle()
        (self.repo / "tracked.txt").write_text("cycle\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain",
            "--paths", "tracked.txt")
        for gate in ("behavior", "spec", "contract", "test_driven_implementation", "refactor"):
            self.record_gate(gate)
        (other / "other.txt").write_text("upstream\n")
        subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        prepared = json.loads(run(
            self.repo, "reconcile-target", "--mode", "prepare", "--json").stdout)
        self.assertEqual(prepared["status"], "prepared")
        self.record_gate("review_integrate", paths=("other.txt",))
        run(self.repo, "gate-commit", "--message", "integrate", "--gates", "review_integrate",
            "--paths", "other.txt")
        integrated = json.loads(run(
            self.repo, "reconcile-target", "--mode", "preview", "--json").stdout)
        self.assertEqual(integrated["status"], "integrated")

        (other / "later.txt").write_text("later\n")
        subprocess.run(["git", "add", "later.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "later"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)
        repeated = json.loads(run(
            self.repo, "reconcile-target", "--mode", "preview", "--json").stdout)
        self.assertEqual(repeated["status"], "diverged")

    def test_reconcile_target_refuses_dirty_worktree(self):
        other = self.start_remote_cycle()
        (self.repo / "tracked.txt").write_text("cycle\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain",
            "--paths", "tracked.txt")
        (other / "other.txt").write_text("upstream\n")
        subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)
        (self.repo / "dirty.txt").write_text("dirty\n")

        result = run(self.repo, "reconcile-target", "--mode", "prepare", "--json", ok=False)
        self.assertIn("clean worktree", result.stderr)

    def test_reconcile_target_rejects_unrecorded_first_parent_commit(self):
        other = self.start_remote_cycle()
        (self.repo / "tracked.txt").write_text("unrecorded\n")
        subprocess.run(["git", "commit", "-am", "unrecorded"], cwd=self.repo, check=True,
                       capture_output=True)
        (other / "other.txt").write_text("upstream\n")
        subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=other, check=True,
                       capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        result = run(self.repo, "reconcile-target", "--mode", "preview", "--json", ok=False)
        self.assertIn("first-parent", result.stderr)

    def test_final_push_rejects_unrecorded_commit_in_linear_advance(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "unrecorded.txt").write_text("unrecorded\n")
        subprocess.run(["git", "add", "unrecorded.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "unrecorded"], cwd=self.repo, check=True, capture_output=True)
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain", "--paths",
            "docs/specs/test/CHANGELOG.md")
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        result = run(self.repo, "final-push", ok=False)
        self.assertIn("ahead commits are not exactly", result.stderr)

    def test_final_push_accepts_fully_integrated_recorded_target(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md",))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain", "--paths",
            "docs/specs/test/CHANGELOG.md")
        for name in ("README", "BACKLOG"):
            run(self.repo, "review-artifact", name, "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        subprocess.run(["git", "push"], cwd=self.repo, check=True, capture_output=True)
        record = json.loads(self.record_path().read_text())
        record["state"] = "finalizing"
        self.record_path().write_text(json.dumps(record))
        run(self.repo, "final-push")
        self.assertEqual(json.loads(self.record_path().read_text())["state"], "completed")

    def test_final_push_rejects_reordered_recorded_commits(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "tracked.txt").write_text("first\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "first", "--gates", "domain", "--paths", "tracked.txt")
        changelog = self.repo / "docs/specs/test/CHANGELOG.md"
        changelog.write_text("completed\n")
        self.record_gate("behavior", paths=("docs/specs/test/CHANGELOG.md",))
        run(self.repo, "gate-commit", "--message", "second", "--gates", "behavior", "--paths",
            "docs/specs/test/CHANGELOG.md")
        for name in ("README", "BACKLOG"):
            run(self.repo, "review-artifact", name, "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        record = json.loads(self.record_path().read_text())
        record["commits"].reverse()
        self.record_path().write_text(json.dumps(record))
        result = run(self.repo, "final-push", ok=False)
        self.assertIn("ahead commits are not exactly", result.stderr)

    def test_final_push_refuses_changed_remote_url(self):
        remote = Path(self.temp.name) / "remote.git"
        other = Path(self.temp.name) / "other.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "--bare", str(other)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md",))
        run(
            self.repo, "gate-commit", "--message", "cycle change", "--gates", "domain", "--paths",
            "docs/specs/test/CHANGELOG.md",
        )
        self.review_artifacts()
        run(
            self.repo, "review-artifact", "CHANGELOG", "--result", "changed",
            "--reason", "recorded", "--path", "docs/specs/test/CHANGELOG.md",
        )
        self.pass_gates()
        subprocess.run(["git", "remote", "set-url", "origin", str(other)], cwd=self.repo, check=True)
        result = run(self.repo, "final-push", ok=False)
        self.assertIn("destination changed", result.stderr)

    def test_final_push_to_local_bare_remote(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "tracked.txt").write_text("cycle\n")
        (self.repo / "docs/specs/test/BACKLOG.md").write_text("done\n")
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        self.record_gate("domain", paths=(
            "tracked.txt", "docs/specs/test/BACKLOG.md", "docs/specs/test/CHANGELOG.md",
        ))
        run(
            self.repo, "gate-commit", "--message", "cycle change", "--gates", "domain", "--paths",
            "tracked.txt", "docs/specs/test/BACKLOG.md", "docs/specs/test/CHANGELOG.md",
        )
        for name, result, reason, artifact_path in (
            ("README", "unchanged", "no durable truth changed", None),
            ("BACKLOG", "changed", "cycle completed", "docs/specs/test/BACKLOG.md"),
            ("CHANGELOG", "changed", "completion recorded", "docs/specs/test/CHANGELOG.md"),
        ):
            command = ["review-artifact", name, "--result", result, "--reason", reason]
            if artifact_path:
                command += ["--path", artifact_path]
            run(self.repo, *command)
        self.pass_gates()
        run(self.repo, "final-push")
        self.assertFalse(any((self.repo / ".git/dbsctr/worktrees").glob("*/active")))
        self.assertEqual(json.loads(self.record_path().read_text())["state"], "completed")
        self.assertEqual(run(self.repo, "status", "--json").stdout.strip(), "null")
        record = json.loads(self.record_path().read_text())
        pointer = self.repo / ".git/dbsctr/worktrees" / record["worktree"]["id"] / "active"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text("cycle-1\n")
        run(self.repo, "final-push")
        self.assertFalse(pointer.exists())

    def test_start_rejects_direct_protected_branch_delivery(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD:main"], cwd=self.repo, check=True,
            capture_output=True,
        )
        result = run(
            self.repo, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
            "--delivery-intent", "local", "--plan", str(self.plan_path()), "--base-branch", "main",
            ok=False,
        )
        self.assertIn("protected base branch", result.stderr)
        self.assertFalse(self.record_path().exists())

    def test_draft_pr_records_configured_base_for_existing_feature_branch(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD:develop"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "checkout", "-b", "teammate/change"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)

        self.start("draft_pr", base_branch="develop")

        delivery = json.loads(self.record_path().read_text())["delivery"]
        self.assertEqual(delivery["branch"], "teammate/change")
        self.assertEqual(delivery["base_branch"], "develop")

    def test_draft_reconciliation_requires_merge_and_fresh_gate_evidence(self):
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                              capture_output=True).stdout.strip()
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("cycle\n")
        subprocess.run(["git", "commit", "-am", "cycle"], cwd=self.repo, check=True,
                       capture_output=True)
        cycle = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                               capture_output=True).stdout.strip()
        subprocess.run(["git", "checkout", "-b", "target", base], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "upstream.txt").write_text("advance\n")
        subprocess.run(["git", "add", "upstream.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=self.repo, check=True,
                       capture_output=True)
        target = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                                capture_output=True).stdout.strip()
        subprocess.run(["git", "checkout", "feature"], cwd=self.repo, check=True, capture_output=True)
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_reconcile", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)

        with self.assertRaisesRegex(RuntimeError, "without reconciliation"):
            module.validate_draft_reconciliation(self.repo, base, target, [cycle], [cycle])
        subprocess.run(["git", "merge", "--no-ff", "target", "-m", "reconcile"], cwd=self.repo,
                       check=True, capture_output=True)
        reconciliation = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                        text=True, capture_output=True).stdout.strip()
        with self.assertRaisesRegex(RuntimeError, "evidence predates"):
            module.validate_draft_reconciliation(self.repo, base, target, [cycle], [cycle])
        self.assertEqual(
            module.validate_draft_reconciliation(
                self.repo, base, target, [cycle], [reconciliation]
            ),
            [cycle],
        )
        with self.assertRaisesRegex(RuntimeError, "reviewed Gate Commit"):
            module.validate_draft_reconciliation(
                self.repo, base, target, [cycle, reconciliation], [cycle], cycle
            )
        self.assertEqual(
            module.validate_draft_reconciliation(
                self.repo, base, target, [cycle, reconciliation], [reconciliation], reconciliation
            ),
            [cycle, reconciliation],
        )
        (self.repo / "later.txt").write_text("later\n")
        subprocess.run(["git", "add", "later.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "later gate"], cwd=self.repo,
                       check=True, capture_output=True)
        later = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                               text=True, capture_output=True).stdout.strip()
        with self.assertRaisesRegex(RuntimeError, "evidence predates"):
            module.validate_draft_reconciliation(
                self.repo, base, target, [cycle, reconciliation, later], [cycle], reconciliation
            )
        self.assertEqual(
            module.validate_draft_reconciliation(
                self.repo, base, target, [cycle, reconciliation, later], [later], later
            ),
            [cycle, reconciliation, later],
        )

    def test_ordinary_draft_pr_does_not_require_improvement_worker(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_ordinary_pr", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        home = Path(self.temp.name) / "home"
        home.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(home), "DBSCTR_STATE_ROOT": str(home / "state")}):
            module.link_improvement_pull_request(
                {"runtime": {"opencode": {"session_ids": ["ordinary-session"]}}},
                {"number": 1, "url": "https://github.com/example/repo/pull/1"},
            )
        self.assertFalse((home / ".local/state/dbsctr/reviews/ledger.sqlite3").exists())

    def test_draft_pr_pushes_only_feature_branch_and_verifies_draft(self):
        remote = Path(self.temp.name) / "remote.git"
        github_url = "https://github.com/example-org/dotfiles-ai.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD:main"], cwd=self.repo, check=True,
                       capture_output=True)
        main_before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                                     capture_output=True).stdout.strip()
        subprocess.run(["git", "checkout", "-b", "dbsctr/test/cycle-1"], cwd=self.repo, check=True,
                       capture_output=True)
        (self.repo / "tracked.txt").write_text("teammate baseline\n")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "teammate baseline"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "branch", "--set-upstream-to", "origin/main"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "remote", "set-url", "origin", github_url], cwd=self.repo, check=True)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                              capture_output=True).stdout.strip()
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        git_wrapper = fake_bin / "git"
        git_wrapper.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "values = sys.argv[1:]\n"
            "with open(os.environ['GIT_WRAPPER_LOG'], 'a') as log: log.write(repr(values) + '\\n')\n"
            "rewrite = not (values[:2] == ['ls-remote', '--get-url'])\n"
            "network = values and values[0] in {'fetch', 'ls-remote', 'push'}\n"
            "args = [os.environ['REAL_GIT'], *[os.environ['LOCAL_GIT_REMOTE'] if rewrite and "
            "(value == os.environ['GITHUB_GIT_URL'] or network and value == 'origin') else value "
            "for value in values]]\n"
            "os.execv(args[0], args)\n"
        )
        git_wrapper.chmod(0o755)
        git_env = {
            **isolated_env(), "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "REAL_GIT": shutil.which("git"), "LOCAL_GIT_REMOTE": str(remote),
            "GITHUB_GIT_URL": github_url,
            "GIT_WRAPPER_LOG": str(Path(self.temp.name) / "git-wrapper.log"),
        }
        self.start("draft_pr", account="example-user", repository="example-org/dotfiles-ai",
                   env=git_env)
        git_log_path = Path(git_env["GIT_WRAPPER_LOG"])
        start_git_log = git_log_path.read_text()
        self.assertIn("'origin'", start_git_log)
        self.assertNotIn(github_url, start_git_log)
        git_log_path.write_text("")
        home = Path(self.temp.name) / "home"
        home.mkdir()
        worker_env = {**git_env, "HOME": str(home)}
        run(self.repo, "improvement-register", "--worker-id", "worker-1", "--session-id", "session-1",
            env=worker_env)
        claim = json.loads(run(self.repo, "improvement-claim", "--session-id", "session-1",
            "--summary", "Improve draft delivery", "--priority", "P1", env=worker_env).stdout)
        run(self.repo, "improvement-update", "--session-id", "session-1", "--state", "discovery",
            "--operator-confirm", "worker-1", "--discovery-json", discovery_report(), env=worker_env)
        run(self.repo, "improvement-update", "--session-id", "session-1", "--state", "implementing",
            "--cycle-id", "cycle-1", "--path", "tracked.txt", env=worker_env)
        record = json.loads(self.record_path().read_text())
        legacy_runtime = {
            "session_ids": ["session-1"], "path_root": "cycle_worktree",
            "worktree": ".", "directory": ".",
        }
        record["runtime"] = {
            "adapters": {"opencode": {
                "schema_version": 1, "harness_id": "opencode",
                "adapter_revision": "opencode-adapter-1",
                "session_ids": ["session-1"],
                "worktree": {"root": "cycle_worktree", "path": "."},
                "availability": {
                    "session": {"status": "available"},
                    "turn": {"status": "not_requested"},
                    "family": {"status": "not_requested"},
                    "activation": {"status": "not_requested"},
                    "history": {"status": "unavailable", "reason": "not_collected"},
                },
            }},
            "opencode": legacy_runtime,
        }
        record["improvement"] = {"worker_id": "worker-1", "session_id": "session-1",
                                 "opportunity_id": claim["opportunity_id"]}
        self.record_path().write_text(json.dumps(record))
        (self.repo / "tracked.txt").write_text("draft cycle\n")
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        self.record_gate("domain", paths=("tracked.txt", "docs/specs/test/CHANGELOG.md"))
        run(self.repo, "gate-commit", "--message", "draft cycle", "--gates", "domain", "--paths",
            "tracked.txt", "docs/specs/test/CHANGELOG.md")
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        gh_log = Path(self.temp.name) / "gh.log"
        gh = fake_bin / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            "printf '<%s>\\n' \"$@\" >> \"$GH_LOG\"\n"
            "[ -n \"${GH_TOKEN:-}\" ] && printf 'TOKEN_SET\\n' >> \"$GH_LOG\"\n"
            "case \"$1 $2\" in\n"
            "  'auth token') printf 'test-token\\n' ;;\n"
            "  'pr list') printf '[]\\n' ;;\n"
            "  'pr create') printf 'https://github.com/example-org/dotfiles-ai/pull/1\\n' ;;\n"
            "  'pr view') printf '%s\\n' '{\"number\":1,\"url\":\"https://github.com/example-org/dotfiles-ai/pull/1\",\"isDraft\":true,\"state\":\"OPEN\",\"baseRefName\":\"main\",\"headRefName\":\"dbsctr/test/cycle-1\",\"headRepositoryOwner\":{\"login\":\"example-org\"}}' ;;\n"
            "esac\n"
        )
        gh.chmod(0o755)
        env = {**worker_env, "PATH": f"{fake_bin}:{os.environ['PATH']}", "GH_LOG": str(gh_log)}
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_github_env", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with mock.patch.dict(os.environ, {
            **env, "GH_TOKEN": "ambient-wrong",
            "GIT_CONFIG_PARAMETERS": "'http.extraHeader=Authorization: wrong'",
            "GIT_TRACE": "1",
        }, clear=True):
            credential_env = module.github_environment("example-user")
        self.assertNotIn("GIT_CONFIG_PARAMETERS", credential_env)
        self.assertNotIn("GIT_TRACE", credential_env)
        self.assertEqual(credential_env["GIT_CONFIG_KEY_2"], "http.extraHeader")
        self.assertEqual(credential_env["GIT_CONFIG_VALUE_2"], "")
        credentials = subprocess.run(
            [shutil.which("git"), "credential", "fill"], text=True, capture_output=True,
            input="protocol=https\nhost=github.com\n\n", env=credential_env, check=True,
        ).stdout
        self.assertIn("username=x-access-token", credentials)
        self.assertIn("password=test-token", credentials)
        self.assertNotIn("test-token", credential_env["GIT_CONFIG_VALUE_1"])
        rewrite_key = f"url.{remote}.insteadOf"
        subprocess.run([git_env["REAL_GIT"], "config", rewrite_key, github_url], cwd=self.repo,
                       check=True)
        with self.assertRaisesRegex(RuntimeError, "URL rewriting"):
            module.require_canonical_github_url(self.repo, github_url, credential_env)
        subprocess.run([git_env["REAL_GIT"], "config", "--unset-all", rewrite_key], cwd=self.repo,
                       check=True)
        result = run(self.repo, "final-push", env=env)
        self.assertIn("draft_pr", result.stdout)
        self.assertNotIn("test-token", result.stdout + result.stderr + self.record_path().read_text())
        git_log = git_log_path.read_text()
        self.assertIn(github_url, git_log)
        self.assertIn("'fetch'", git_log)
        self.assertIn("'push'", git_log)
        feature = subprocess.run(["git", "rev-parse", "refs/heads/dbsctr/test/cycle-1"], cwd=remote,
                                 check=True, text=True, capture_output=True).stdout.strip()
        main = subprocess.run(["git", "rev-parse", "refs/heads/main"], cwd=remote, check=True,
                              text=True, capture_output=True).stdout.strip()
        self.assertEqual(feature, subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                                 text=True, capture_output=True).stdout.strip())
        self.assertEqual(main, main_before)
        self.assertEqual(
            subprocess.run(["git", "show", "refs/heads/dbsctr/test/cycle-1^:tracked.txt"], cwd=remote,
                           check=True, text=True, capture_output=True).stdout,
            "teammate baseline\n",
        )
        log = gh_log.read_text()
        self.assertIn("<auth>\n<token>\n<--hostname>\n<github.com>\n<--user>\n<example-user>", log)
        self.assertIn("<--head>\n<dbsctr/test/cycle-1>", log)
        self.assertIn("<--head>\n<example-org:dbsctr/test/cycle-1>", log)
        self.assertIn("<pr>\n<create>", log)
        self.assertNotIn("<merge>", log)
        record = json.loads(self.record_path().read_text())
        self.assertTrue(record["delivery"]["pull_request"]["draft"])
        self.assertEqual(record["source_sync"]["status"], "not_applicable")
        worker = json.loads(run(self.repo, "improvement-status", "--worker-id", "worker-1",
                                env=worker_env).stdout)["workers"][0]
        self.assertEqual(worker["state"], "draft_pr")
        self.assertEqual(worker["pr_number"], 1)
        implementation = json.loads(worker["implementation_report"])
        self.assertEqual(implementation["pull_request_url"],
                         "https://github.com/example-org/dotfiles-ai/pull/1")
        self.assertEqual(implementation["changed_paths"],
                          ["docs/specs/test/CHANGELOG.md", "tracked.txt"])
        self.assertRegex(implementation["diff_digest"], r"^[0-9a-f]{64}$")
        self.assertIn("domain", implementation["passed_gates"])

        loader = importlib.machinery.SourceFileLoader("dbsctrctl_report_base", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with mock.patch.dict(os.environ, worker_env, clear=True):
            module.link_improvement_pull_request(
                record, record["delivery"]["pull_request"], self.repo, base)
        worker = json.loads(run(self.repo, "improvement-status", "--worker-id", "worker-1",
                                env=worker_env).stdout)["workers"][0]
        expected_diff = subprocess.run(
            ["git", "diff", "--binary", f"{base}...HEAD"], cwd=self.repo,
            check=True, text=True, capture_output=True,
        ).stdout
        self.assertEqual(json.loads(worker["implementation_report"])["diff_digest"],
                         hashlib.sha256(expected_diff.encode()).hexdigest())

    def test_draft_pr_reuses_only_same_repository_branch(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_pr_reuse", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        record = {"cycle_id": "cycle-1", "context": "test", "delivery": {
            "base_branch": "main", "branch": "dbsctr/test/cycle-1",
            "github": {"account": "example-user", "repository": "example-org/dotfiles-ai"},
        }}
        pull_requests = [
            {"number": 1, "url": "https://github.com/fork/pull/1", "isDraft": True,
             "state": "OPEN", "baseRefName": "main", "headRefName": "dbsctr/test/cycle-1",
             "headRepositoryOwner": {"login": "fork"}},
            {"number": 2, "url": "https://github.com/example-org/dotfiles-ai/pull/2", "isDraft": True,
             "state": "OPEN", "baseRefName": "main", "headRefName": "dbsctr/test/cycle-1",
             "headRepositoryOwner": {"login": "example-org"}},
        ]
        with mock.patch.object(module, "github_environment", return_value={}), \
                mock.patch.object(module, "github_json", return_value=pull_requests), \
                mock.patch.object(module.subprocess, "run") as create:
            result = module.deliver_draft_pr(self.repo, record)
        self.assertEqual(result["number"], 2)
        create.assert_not_called()

    def test_final_push_requires_changelog_change(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "tracked.txt").write_text("cycle\n")
        self.record_gate("domain", paths=("tracked.txt",))
        run(self.repo, "gate-commit", "--message", "cycle change", "--gates", "domain", "--paths", "tracked.txt")
        self.review_artifacts()
        self.pass_gates()
        result = run(self.repo, "final-push", ok=False)
        self.assertIn("CHANGELOG", result.stderr)

    def test_final_push_rejects_dirty_dvc_status(self):
        (self.repo / ".dvc").mkdir()
        (self.repo / ".dvc/config").write_text("[core]\n")
        subprocess.run(["git", "add", ".dvc/config"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "dvc fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        run(
            self.repo, "record-dvc-push", "--head", "0" * 40,
            "--evidence", "wrong", ok=False,
        )
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        (self.repo / "data.dvc").write_text("outs:\n- path: data\n")
        self.record_gate("domain", paths=("docs/specs/test/CHANGELOG.md", "data.dvc"))
        run(
            self.repo, "gate-commit", "--message", "cycle change", "--gates", "domain", "--paths",
            "docs/specs/test/CHANGELOG.md", "data.dvc",
        )
        self.review_artifacts()
        run(
            self.repo, "review-artifact", "CHANGELOG", "--result", "changed",
            "--reason", "recorded", "--path", "docs/specs/test/CHANGELOG.md",
        )
        self.pass_gates()
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                              capture_output=True).stdout.strip()
        run(self.repo, "record-dvc-push", "--head", head, "--evidence", "approved dvc push")
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        fake_dvc = fake_bin / "dvc"
        fake_dvc.write_text("#!/bin/sh\nprintf '<%s>\\n' \"$@\" > \"$DVC_LOG\"\nprintf 'changed data.dvc\\n'\n")
        fake_dvc.chmod(0o755)
        dvc_log = Path(self.temp.name) / "dvc.log"
        env = {**isolated_env(), "PATH": f"{fake_bin}:{os.environ['PATH']}", "DVC_LOG": str(dvc_log)}
        result = run(self.repo, "final-push", ok=False, env=env)
        self.assertIn("changed or missing", result.stderr)
        self.assertEqual(dvc_log.read_text().splitlines(), ["<status>", "<data.dvc>"])

    def test_final_push_ignores_dvc_for_unrelated_cycle(self):
        (self.repo / ".dvc").mkdir()
        (self.repo / ".dvc/config").write_text("[core]\n")
        subprocess.run(["git", "add", ".dvc/config"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "dvc fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=self.repo, check=True,
                       capture_output=True)
        self.start()
        (self.repo / "tracked.txt").write_text("cycle\n")
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        self.record_gate("domain", paths=("tracked.txt", "docs/specs/test/CHANGELOG.md"))
        run(self.repo, "gate-commit", "--message", "cycle", "--gates", "domain", "--paths",
            "tracked.txt", "docs/specs/test/CHANGELOG.md")
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "CHANGELOG", "--result", "changed", "--reason", "recorded",
            "--path", "docs/specs/test/CHANGELOG.md")
        self.pass_gates()
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        fake_dvc = fake_bin / "dvc"
        fake_dvc.write_text("#!/bin/sh\nexit 99\n")
        fake_dvc.chmod(0o755)
        env = {**isolated_env(), "PATH": f"{fake_bin}:{os.environ['PATH']}"}
        run(self.repo, "final-push", env=env)

    def test_review_scan_is_read_only_and_completion_excludes_reviewed(self):
        database = Path(self.temp.name) / "opencode.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR cycle', 1784073600000);
            insert into session values ('child-1', 'session-1', 'Reviewer', 1784073601000);
            insert into session values ('grandchild-1', 'child-1', 'Neutral', 1784073602000);
            insert into session values ('long-1', null, 'Neutral', 1784073603000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{"role":"assistant"}');
            insert into message values ('message-2', 'child-1', 1784073601000, '{"role":"assistant"}');
            insert into message values ('message-3', 'grandchild-1', 1784073602000, '{"role":"assistant"}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000,
                                     '{"type":"text","text":"DBSCTR V3.3 blocked","cycle_id":"cycle-20260715"}');
            insert into part values ('part-2', 'message-2', 'child-1', 1784073601000,
                                     '{"type":"text","text":"review complete","cycle_id":"cycle-20260715"}');
            insert into part values ('part-3', 'message-3', 'grandchild-1', 1784073602000,
                                     '{"type":"text","text":"neutral child"}');
        """)
        connection.executemany("insert into message values (?, 'long-1', ?, '{\"role\":\"assistant\"}')",
                               [(f"long-message-{index}", 1784073603000 + index) for index in range(40)])
        connection.executemany("insert into part values (?, ?, 'long-1', ?, ?)", [
            (f"long-part-{index}", f"long-message-{index}", 1784073603000 + index,
             json.dumps({"type": "text", "text": "/qa lifecycle" if index == 0 else "neutral"}))
            for index in range(40)
        ])
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "state"
        before = database.stat().st_mtime_ns
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
                              "--limit", "10", "--cursor", "0").stdout)
        self.assertEqual(database.stat().st_mtime_ns, before)
        self.assertEqual(scan["session_ids"], ["session-1", "child-1", "grandchild-1", "long-1"])
        self.assertEqual(scan["schema_version"], 2)
        self.assertEqual(scan["candidates"][0]["cycles"], [])
        self.assertEqual(scan["candidates"][0]["attention"], [])
        self.assertNotIn("state", scan["candidates"][0])
        self.assertEqual(scan["scorecard"]["unknown"], 4)
        self.assertEqual(sum(scan["scorecard"].values()), len(scan["candidates"]))
        self.assertEqual(scan["candidates"][-1]["last_activity"], "1784073603039")
        self.assertNotIn(str(Path.home()), json.dumps(scan))
        report = Path(self.temp.name) / "report.json"
        report.write_text(json.dumps({"session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
                                       "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
                                       "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
                                       "database_digest": scan["database_digest"],
                                      "limit": 10, "cursor": 0,
                                      "decision": "reviewed"}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", scan["digest"],
            "--database", str(database), "--state-root", str(state))
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        self.assertGreater(connection.execute("SELECT reviewed_at FROM review_reports").fetchone()[0], scan["snapshot"])
        connection.close()
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)
        self.assertEqual(ledger.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual((ledger.parent / ".lock").stat().st_mode & 0o777, 0o600)
        repeated = json.loads(run(self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
                                  "--limit", "10", "--cursor", "0").stdout)
        self.assertEqual(repeated["session_ids"], [])

        page_state = Path(self.temp.name) / "page-state"
        page_one = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                  "--state-root", str(page_state), "--limit", "1", "--cursor", "0").stdout)
        page_report = Path(self.temp.name) / "page-report.json"
        page_report.write_text(json.dumps({"session_ids": page_one["session_ids"],
                                           "cycle_ids": page_one["cycle_ids"],
                                           "scan_digest": page_one["digest"], "snapshot": page_one["snapshot"],
                                           "session_ceiling": page_one["session_ceiling"],
                                           "part_ceiling": page_one["part_ceiling"],
                                           "database_digest": page_one["database_digest"],
                                           "limit": 1, "cursor": 0,
                                           "decision": "reviewed"}))
        run(self.repo, "review-complete", "--report", str(page_report), "--scan-digest", page_one["digest"],
            "--database", str(database), "--state-root", str(page_state))
        stable = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                "--state-root", str(page_state), "--limit", "1", "--cursor", "0",
                                "--snapshot", str(page_one["snapshot"]),
                                "--session-ceiling", str(page_one["session_ceiling"]),
                                "--part-ceiling", str(page_one["part_ceiling"]),
                                "--database-digest", page_one["database_digest"]).stdout)
        self.assertEqual(stable, page_one)
        page_two = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                  "--state-root", str(page_state), "--limit", "1", "--cursor", "1",
                                  "--snapshot", str(page_one["snapshot"]),
                                  "--session-ceiling", str(page_one["session_ceiling"]),
                                  "--part-ceiling", str(page_one["part_ceiling"]),
                                  "--database-digest", page_one["database_digest"]).stdout)
        self.assertEqual(page_two["cycle_ids"], [])

    def test_incident_workflow_preserves_redacted_fork_evidence_and_verified_fix(self):
        database = Path(self.temp.name) / "incidents.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('root-1', null, 'DBSCTR cycle', 1784073600000);
            insert into session values ('fork-1', 'root-1', 'Incident fork', 1784073601000);
            insert into session values ('foreign-1', null, 'QA cycle', 1784073602000);
            insert into session values ('foreign-child', 'foreign-1', 'Other fork', 1784073603000);
            insert into message values ('message-root', 'root-1', 1784073600000, '{}');
            insert into message values ('message-fork', 'fork-1', 1784073601000, '{}');
            insert into message values ('message-foreign', 'foreign-1', 1784073602000, '{}');
            insert into message values ('message-other', 'foreign-child', 1784073603000, '{}');
            insert into part values ('part-root', 'message-root', 'root-1', 1784073600000,
                                     '{"type":"text","text":"DBSCTR cycle"}');
        """)
        parts = [
            ("part-bash-error", "message-fork", "fork-1", 1784073601001,
             {"type": "tool", "tool": "bash", "state": {"status": "error", "error": "password=hunter2 /tmp/build"}}),
            ("part-bash-ok", "message-fork", "fork-1", 1784073601002,
             {"type": "tool", "tool": "bash", "state": {"status": "completed", "output": "ok"}}),
            ("part-read-error", "message-fork", "fork-1", 1784073601003,
             {"type": "tool", "tool": "read", "state": {"status": "failed", "error": "api_key=abcdefghijklmnop /tmp/input"}}),
            ("part-foreign-seed", "message-foreign", "foreign-1", 1784073602000,
             {"type": "text", "text": "/qa cycle"}),
            ("part-foreign", "message-foreign", "foreign-1", 1784073602001,
             {"type": "tool", "tool": "read", "state": {"status": "error", "error": "foreign"}}),
        ]
        connection.executemany("insert into part values (?, ?, ?, ?, ?)",
                               [(*row[:4], json.dumps(row[4])) for row in parts])
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "incident-state"

        scan = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                              "--state-root", str(state), "--session-id", "fork-1").stdout)
        self.assertFalse((state / "reviews/ledger.sqlite3").exists())
        self.assertEqual(scan["schema_version"], 1)
        self.assertEqual([(item["tool"], item["recovered"]) for item in scan["signals"]],
                         [("read", False), ("bash", True)])
        self.assertNotIn("hunter2", json.dumps(scan))
        self.assertNotIn("abcdefghijklmnop", json.dumps(scan))
        self.assertIn("/tmp/input", json.dumps(scan))

        root_registration = run(
            self.repo, "incident-register", "--database", str(database), "--state-root", str(state),
            "--session-id", "root-1", "--message-id", "message-root", "--kind", "defect",
            "--title", "INCIDENT: root", "--summary", "not a fork", ok=False,
        )
        self.assertIn("child session", root_registration.stderr)
        foreign = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                 "--state-root", str(state), "--session-id", "foreign-1").stdout)
        invalid_signal = run(
            self.repo, "incident-register", "--database", str(database), "--state-root", str(state),
            "--session-id", "fork-1", "--message-id", "message-fork", "--kind", "defect",
            "--title", "INCIDENT: failed read", "--summary", "Preserve the failed read.",
            "--signal-id", foreign["signals"][0]["signal_id"], ok=False,
        )
        self.assertIn("outside the incident family", invalid_signal.stderr)

        selected = scan["signals"][0]["signal_id"]
        registered = json.loads(run(
            self.repo, "incident-register", "--database", str(database), "--state-root", str(state),
            "--session-id", "fork-1", "--message-id", "message-fork", "--kind", "defect",
            "--title", "INCIDENT: failed read", "--summary", "Preserve token=secret-value and diagnose.",
            "--signal-id", selected, "--diagnostic", "Expected readable input.",
            "--evidence", 'Bearer "private phrase" --password "secret phrase" '
                          "op://vault/item/field\nAuthorization: Basic dXNlcjpwYXNz\n"
                          'Proxy-Authorization: Digest username="admin", response="abc123"\n'
                          '{"Authorization":"Basic c3RydWN0dXJlZA==","password":"abc\\\"remaining-secret"}'
                          "\n/tmp/input",
        ).stdout)
        incident_id = registered["incident"]["incident_id"]
        self.assertEqual(registered["incident"]["state"], "open")
        self.assertNotIn("secret-value", ledger_text(state))
        self.assertNotIn("private phrase", ledger_text(state))
        self.assertNotIn("secret phrase", ledger_text(state))
        self.assertNotIn("vault/item/field", ledger_text(state))
        self.assertNotIn("dXNlcjpwYXNz", ledger_text(state))
        self.assertNotIn("admin", ledger_text(state))
        self.assertNotIn("c3RydWN0dXJlZA==", ledger_text(state))
        self.assertNotIn("remaining-secret", ledger_text(state))
        self.assertEqual((state / "reviews/ledger.sqlite3").stat().st_mode & 0o777, 0o600)
        duplicate = run(
            self.repo, "incident-register", "--database", str(database), "--state-root", str(state),
            "--session-id", "fork-1", "--message-id", "message-fork", "--kind", "defect",
            "--title", "INCIDENT: duplicate", "--summary", "duplicate", ok=False,
        )
        self.assertIn("already registered", duplicate.stderr)
        ledger = sqlite3.connect(state / "reviews/ledger.sqlite3")
        ledger.execute("update incidents set summary='token=restored-secret' where incident_id=?", (incident_id,))
        ledger.commit()
        ledger.close()
        inbox = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                               "--state-root", str(state)).stdout)
        self.assertEqual([item["incident_id"] for item in inbox["incidents"]], [incident_id])
        self.assertNotIn("restored-secret", json.dumps(inbox))
        self.assertNotIn(selected, [item["signal_id"] for item in inbox["signals"]])
        backup = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        backup_path = state / "reviews/backups" / backup["backup"]
        self.assertTrue(backup_path.is_file())
        external_backup = Path(self.temp.name) / "pre-forget.sqlite3"
        shutil.copyfile(backup_path, external_backup)

        actor = ("--database", str(database), "--session-id", "fork-1", "--message-id", "message-fork")
        cross_fork = run(self.repo, "incident-update", "--state-root", str(state),
                         "--database", str(database), "--session-id", "foreign-child",
                         "--message-id", "message-other", "--incident-id", incident_id,
                         "--state", "investigating", ok=False)
        self.assertIn("another fork", cross_fork.stderr)
        run(self.repo, "incident-update", "--state-root", str(state), *actor, "--incident-id", incident_id,
            "--state", "investigating")
        self.start()
        cycle = json.loads(self.record_path().read_text())
        cycle.update({"source": {
            "head": cycle["git"]["head"], "branch": cycle["git"]["branch"],
            "upstream": cycle["git"]["upstream"], "dirty_paths": [],
            "remote": cycle["git"]["remote"], "locator": {"root": "primary_worktree", "path": "."},
        }, "runtime": {"adapters": {}}})
        self.record_path().write_text(json.dumps(cycle))
        active_cycle = json.loads(json.dumps(cycle))
        run(self.repo, "incident-update", "--state-root", str(state), *actor, "--incident-id", incident_id,
            "--state", "fixing", "--cycle-id", "cycle-1")
        unresolved = run(self.repo, "incident-update", "--state-root", str(state), *actor,
                         "--incident-id", incident_id, "--state", "resolved", ok=False)
        self.assertIn("verified activation", unresolved.stderr)
        cycle.update({"state": "completed", "gates": {}})
        self.record_path().write_text(json.dumps(cycle))
        missing_gates = run(self.repo, "incident-update", "--state-root", str(state), *actor,
                            "--incident-id", incident_id, "--state", "resolved", ok=False)
        self.assertIn("Cycle Record", missing_gates.stderr)
        cycle = active_cycle
        evidence = {}
        completed_gates = {}
        for gate in GATES:
            if gate == "release":
                completed_gates[gate] = {"applicability": "not_applicable", "result": "not_run"}
                continue
            evidence_id = f"ev-{gate}"
            completed_gates[gate] = {"applicability": "required", "result": "passed",
                                     "evidence": evidence_id}
            evidence[evidence_id] = {"id": evidence_id, "gate": gate, "result": "passed",
                                     "authority": "test", "paths": {}, "head": cycle["git"]["head"],
                                     "argv": [], "summary": "passed", "urls": [],
                                     "started_at": cycle["created_at"], "finished_at": cycle["created_at"],
                                     "raw": {"byte_count": 0, "lower_bound": False, "truncated": False},
                                     "content": {"status": "no_content"}}
        for review in cycle["artifact_reviews"].values():
            review.update({"result": "unchanged", "reason": "verified", "reviewed_at": cycle["created_at"]})
        cycle.update({"state": "completed", "completed_at": cycle["created_at"],
                      "gates": completed_gates, "evidence": {"version": 1, "items": evidence}})
        invalid_exception = json.loads(json.dumps(cycle))
        invalid_exception["gates"]["domain"] = {
            "applicability": "required", "result": "pending", "exception": {
                "kind": "accepted_risk", "rationale": "invalid pending disposition", "owner": "test",
                "review_condition": "never", "approved_at": cycle["created_at"],
            },
        }
        self.record_path().write_text(json.dumps(invalid_exception))
        pending_exception = run(self.repo, "incident-update", "--state-root", str(state), *actor,
                                "--incident-id", incident_id, "--state", "resolved", ok=False)
        self.assertIn("incomplete gate", pending_exception.stderr)
        self.record_path().write_text(json.dumps(cycle))
        resolved = json.loads(run(self.repo, "incident-update", "--state-root", str(state), *actor,
                                  "--incident-id", incident_id, "--state", "resolved").stdout)
        self.assertEqual(resolved["incident"]["state"], "resolved")

        run(self.repo, "incident-forget", "--state-root", str(state), *actor, "--incident-id", incident_id)
        forgotten = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                   "--state-root", str(state), "--session-id", "fork-1").stdout)
        self.assertEqual(forgotten["incidents"], [])
        self.assertNotIn(selected, [item["signal_id"] for item in forgotten["signals"]])
        self.assertFalse((state / "reviews/backups").exists())
        restored_backups = state / "reviews/backups"
        restored_backups.mkdir(mode=0o700)
        restored_backup = restored_backups / backup["backup"]
        shutil.copyfile(external_backup, restored_backup)
        os.chmod(restored_backup, 0o600)
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        after_restore = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                       "--state-root", str(state), "--session-id", "fork-1").stdout)
        self.assertEqual(after_restore["incidents"], [])
        self.assertNotIn(selected, [item["signal_id"] for item in after_restore["signals"]])
        legacy_backup = restored_backups / "legacy.sqlite3"
        shutil.copyfile(external_backup, legacy_backup)
        legacy = sqlite3.connect(legacy_backup)
        legacy.executescript("""
            drop table incident_signal_dispositions;
            drop table incidents;
            delete from ledger_meta where key='incident_schema';
        """)
        legacy.commit()
        legacy.close()
        os.chmod(legacy_backup, 0o600)
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", "legacy.sqlite3")
        legacy_restored = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                         "--state-root", str(state), "--session-id", "fork-1").stdout)
        self.assertEqual(legacy_restored["incidents"], [])
        self.assertNotIn(selected, [item["signal_id"] for item in legacy_restored["signals"]])

    def test_incident_scan_bounds_registered_inbox(self):
        database = Path(self.temp.name) / "incident-cap.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('root-1', null, 'DBSCTR cycle', 1784073600000);
            insert into session values ('fork-1', 'root-1', 'Incident fork', 1784073601000);
            insert into message values ('message-root', 'root-1', 1784073600000, '{}');
            insert into message values ('message-1', 'fork-1', 1784073601000, '{}');
            insert into part values ('part-1', 'message-root', 'root-1', 1784073600000,
                                     '{"type":"text","text":"DBSCTR cycle"}');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "incident-cap-state"
        run(self.repo, "incident-register", "--database", str(database), "--state-root", str(state),
            "--session-id", "fork-1", "--message-id", "message-1", "--kind", "defect",
            "--title", "INCIDENT: first", "--summary", "first")
        ledger = sqlite3.connect(state / "reviews/ledger.sqlite3")
        seed = ledger.execute("select * from incidents").fetchone()
        base_timestamp = seed[-1]
        ledger.executemany(
            "insert into incidents values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(f"{index:024x}", f"fork-{index}", seed[2], seed[3], *seed[4:-2],
              base_timestamp + index, base_timestamp + index)
             for index in range(2, 102)],
        )
        ledger.commit()
        ledger.close()
        source = sqlite3.connect(database)
        source.executemany(
            "insert into part values (?,?,?,?,?)",
            [(f"failed-{index:03}", "message-1", "fork-1", 1784073602000 + index,
              json.dumps({"type": "tool", "tool": "read",
                          "state": {"status": "failed", "error": f"failure {index}"}}))
             for index in range(101)],
        )
        source.commit()
        source.close()

        inbox = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                               "--state-root", str(state)).stdout)
        self.assertEqual(len(inbox["incidents"]), 100)
        self.assertTrue(inbox["incident_overflow"])
        self.assertEqual(inbox["incidents"][0]["incident_id"], f"{101:024x}")
        self.assertEqual(len(inbox["signals"]), 100)
        self.assertTrue(inbox["signal_overflow"])
        self.assertEqual(inbox["signals"][0]["part_id"], "failed-100")
        ledger = sqlite3.connect(state / "reviews/ledger.sqlite3")
        ledger.executemany(
            "insert into incident_signal_dispositions values (?,null,'forgotten',1784073603000)",
            [(hashlib.sha256(f"fork-1\0message-1\0failed-{index:03}\0read".encode()).hexdigest()[:24],)
             for index in range(101)],
        )
        ledger.commit()
        ledger.close()
        source = sqlite3.connect(database)
        source.execute("insert into part values (?,?,?,?,?)", (
            "older-unclaimed", "message-1", "fork-1", 1784073601500,
            json.dumps({"type": "tool", "tool": "read",
                        "state": {"status": "failed", "error": "older unclaimed"}}),
        ))
        source.commit()
        source.close()
        undisposed = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                    "--state-root", str(state)).stdout)
        self.assertEqual([item["part_id"] for item in undisposed["signals"]], ["older-unclaimed"])
        self.assertFalse(undisposed["signal_overflow"])

    def test_history_source_index_refresh_builds_compact_schema_three_snapshot(self):
        database = Path(self.temp.name) / "history-refresh.db"
        source = sqlite3.connect(database)
        source.executescript("""
            create table session (id text primary key, parent_id text, time_created integer,
                                  agent text, tokens_input integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text,
                               time_created integer, data text);
            insert into session values ('session-refresh', null, 1784073600000,
                                        'reviewer-openai', 1);
            insert into message values ('message-refresh', 'session-refresh', 1784073600000,
                                        '{"model":{"modelID":"model-refresh"}}');
        """)
        source.executemany(
            "insert into part values (?, 'message-refresh', 'session-refresh', ?, ?)",
            [(f"part-{index}", 1784073500000 if index == 21 else 1784073600000 + index, json.dumps(
                {"type": "tool", "tool": "read", "state": {"status": "failed"}}
                if index == 20 else {"type": "text", "text": "DBSCTR" if index == 0 else f"neutral-{index}"}
            )) for index in range(40)],
        )
        source.commit()
        source.close()
        state = Path(self.temp.name) / "history-refresh-state"
        reviews = state / "reviews"
        reviews.mkdir(parents=True, mode=0o700)
        stale = sqlite3.connect(reviews / "history-source-index.sqlite3")
        stale.executescript("create table index_meta (key text primary key,value text);"
                            "insert into index_meta values ('schema_version','3');"
                            "create table stale_schema (value text);")
        stale.commit()
        stale.close()
        os.chmod(reviews / "history-source-index.sqlite3", 0o600)

        refreshed = json.loads(run(
            self.repo, "history-source-index-refresh", "--database", str(database),
            "--state-root", str(state),
        ).stdout)
        self.assertEqual(set(refreshed), {
            "schema_version", "state", "captured_at", "duration_ms", "indexed_sessions",
            "material_rows",
        })
        self.assertEqual((refreshed["schema_version"], refreshed["state"],
                          refreshed["indexed_sessions"], refreshed["material_rows"]),
                         (1, "ready", 1, 33))
        sidecar = state / "reviews/history-source-index.sqlite3"
        indexed = sqlite3.connect(sidecar)
        self.assertEqual(indexed.execute(
            "select value from index_meta where key='schema_version'").fetchone(), ("3",))
        self.assertEqual(tuple(row[1] for row in indexed.execute(
            "pragma table_info(index_generations)")), (
                "generation_id", "state", "source_device", "source_inode", "schema_digest",
                "privacy_epoch_digest", "captured_at", "target_session_ceiling",
                "target_message_ceiling", "target_part_ceiling", "covered_session_ceiling",
                "covered_message_ceiling", "covered_part_ceiling", "session_row_count",
                "message_row_count", "part_row_count", "material_row_count", "created_at",
                "completed_at",
            ))
        self.assertEqual(tuple(row[1] for row in indexed.execute("pragma table_info(index_rows)")), (
            "generation_id", "part_rowid", "session_id", "part_time", "material_kind",
            "eligibility_flags", "tool_name", "tool_key_digest", "tool_state", "failure_class",
            "disposition_digest",
        ))
        self.assertEqual(indexed.execute(
            "select material_kind,tool_name,failure_class from index_rows where part_rowid=21"
        ).fetchone(), ("tool", "read", "tool_failed"))
        self.assertEqual(indexed.execute(
            "select material_kind from index_rows where part_rowid=22").fetchone(), ("boundary",))
        indexed.close()
        self.assertNotIn(b"neutral-20", sidecar.read_bytes())

        status = json.loads(run(
            self.repo, "history-source-index-status", "--state-root", str(state),
        ).stdout)
        self.assertEqual(set(status), {
            "schema_version", "state", "captured_at", "age_seconds", "covered_part_ceiling",
        })
        self.assertEqual((status["schema_version"], status["state"], status["captured_at"],
                          status["covered_part_ceiling"]),
                         (1, "ready", refreshed["captured_at"], 40))
        self.assertGreaterEqual(status["age_seconds"], 0)
        retired = run(self.repo, "history-source-index-maintain", "--database", str(database),
                      "--state-root", str(state), ok=False)
        self.assertIn("invalid choice", retired.stderr)
        aggregate = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--aggregate-only",
        ).stdout)
        self.assertEqual((aggregate["mode"], aggregate["selected_count"]), ("aggregate", 1))

    def test_history_aggregate_and_incident_summary_use_private_source_index(self):
        database = Path(self.temp.name) / "history-summary.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer,
                                  model text, tokens_input integer, project_id text);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        for index in range(3):
            timestamp = 1784073600000 + index
            connection.execute("insert into session values (?, ?, 'DBSCTR', ?, ?, ?, ?)",
                               (f"session-{index}", "session-1" if index == 2 else None,
                                timestamp, f"model-{index}", index + 1, f"project-{index}"))
            connection.execute("insert into message values (?, ?, ?, '{}')",
                               (f"message-{index}", f"session-{index}", timestamp))
            connection.execute("insert into part values (?, ?, ?, ?, ?, ?)",
                               (f"part-{index}", f"message-{index}", f"session-{index}",
                                timestamp, timestamp, json.dumps({"type": "text", "text": "DBSCTR"})))
        connection.execute("insert into part values ('failed-read', 'message-2', 'session-2', "
                           "1784073600100, 1784073600100, ?)", (json.dumps({
                               "type": "tool", "tool": "read", "state": {
                                   "status": "failed", "error": {"code": "TIMEOUT"},
                               },
                           }),))
        connection.execute("insert into part values ('failed-private', 'message-2', 'session-2', "
                           "1784073600101, 1784073600101, ?)", (json.dumps({
                               "type": "tool", "tool": "private_tool", "state": {
                                   "status": "error", "error": {"name": "EACCES"},
                               },
                           }),))
        connection.executemany(
            "insert into part values (?, 'message-1', 'session-1', ?, ?, ?)",
            [(f"interior-{index:02}", 1784073600010 + index, 1784073600010 + index,
              json.dumps({"type": "text", "text": f"neutral {index}"})) for index in range(34)],
        )
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-summary-state"

        unavailable = run(self.repo, "review-history", "--database", str(database),
                          "--state-root", str(state), "--limit", "2", "--aggregate-only", ok=False)
        self.assertEqual(unavailable.returncode, 75)
        self.assertEqual(unavailable.stderr, "source_index_unavailable\n")
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_source_index", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        index_module = importlib.util.module_from_spec(spec)
        loader.exec_module(index_module)
        maintenance = SimpleNamespace(database=str(database), state_root=str(state))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            index_module.command_history_source_index_refresh(maintenance)
        maintained = json.loads(output.getvalue())
        self.assertEqual((maintained["state"], maintained["material_rows"]), ("ready", 36))
        sidecar = state / "reviews/history-source-index.sqlite3"
        self.assertEqual(sidecar.stat().st_mode & 0o777, 0o600)
        indexed = sqlite3.connect(sidecar)
        self.assertEqual(indexed.execute(
            "select value from index_meta where key='schema_version'").fetchone(), ("3",))
        self.assertEqual({row[0] for row in indexed.execute(
            "select name from sqlite_master where type='table'")}, {
                "index_meta", "index_generations", "index_sessions", "index_session_values",
                "index_rows", "active_generation",
            })
        self.assertEqual({row[0] for row in indexed.execute(
            "select name from sqlite_master where type='index' and name not like 'sqlite_autoindex_%'")}, {
                "index_sessions_membership", "index_rows_ascending", "index_rows_recovery",
                "index_rows_incident",
            })
        index_sql = dict(indexed.execute(
            "select name,sql from sqlite_master where type='index' and name in "
            "('index_rows_recovery','index_rows_incident')"))
        self.assertIn("WHERE tool_key_digest IS NOT NULL", index_sql["index_rows_recovery"])
        self.assertIn("WHERE tool_state='failed'", index_sql["index_rows_incident"])
        self.assertEqual(indexed.execute("select count(*) from index_rows").fetchone()[0], 36)
        self.assertEqual({row[1] for row in indexed.execute("pragma table_info(index_rows)")},
                         {"generation_id", "part_rowid", "session_id", "part_time", "material_kind",
                          "eligibility_flags", "tool_name", "tool_key_digest",
                          "tool_state", "failure_class", "disposition_digest"})
        generation_before = indexed.execute("select generation_id from active_generation").fetchone()[0]
        indexed_boundaries = indexed.execute("""
            select session_id,part_time,part_rowid from index_rows
            where generation_id=? and material_kind in ('boundary','both')
            order by session_id,part_time,part_rowid
        """, (generation_before,)).fetchall()
        indexed.close()
        source = sqlite3.connect(database)
        source_boundaries = source.execute("""
            select session_id,time_created,rowid from (
              select session_id,time_created,rowid,
                     row_number() over (partition by session_id order by time_created,rowid) first_rank,
                     row_number() over (partition by session_id order by time_created desc,rowid desc) last_rank
              from part
            ) where first_rank<=16 or last_rank<=16 order by session_id,time_created,rowid
        """).fetchall()
        source.close()
        self.assertEqual(indexed_boundaries, source_boundaries)
        self.assertNotIn(b"DBSCTR", sidecar.read_bytes())
        self.assertNotIn(b"failed-private", sidecar.read_bytes())

        def maintain_cli():
            return json.loads(run(
                self.repo, "history-source-index-refresh", "--database", str(database),
                "--state-root", str(state)).stdout)

        validated_index = index_module.require_history_source_index(SimpleNamespace(
            database=str(database), state_root=str(state)))
        source = sqlite3.connect(database)
        source.execute("insert into part values ('ceiling-race', 'message-0', 'session-0', "
                       "1784073600005, 1784073600005, '{}')")
        source.commit()
        stable = index_module.review_scan(SimpleNamespace(
            database=str(database), state_root=str(state), limit=100, cursor=0, snapshot=None,
            session_ceiling=None, part_ceiling=None, database_digest=None, exclusion_digest=None,
            excluded_session_id=None, excluded_message_id=None, source_index=validated_index,
            lock_held=True, include_reviewed=True, history_metrics=False, history_all=True,
            bind_history=True, membership_only=True, metric_session_ids=None,
        ))
        self.assertEqual(stable["part_ceiling"], validated_index["validated_part_ceiling"])
        source.execute("delete from part where id='ceiling-race'")
        source.commit()
        source.close()

        first_run = subprocess.run(
            [sys.executable, str(SCRIPT), "review-history", "--database", str(database),
             "--state-root", str(state), "--limit", "2", "--aggregate-only"],
            cwd=self.repo, text=True, capture_output=True, env=isolated_env(),
        )
        self.assertEqual(first_run.returncode, 0, first_run.stderr)
        first = json.loads(first_run.stdout)
        self.assertEqual(first["mode"], "aggregate")
        self.assertEqual(first["selected_count"], 2)
        self.assertEqual(first["metrics"]["tokens"], {
            "available_count": 2, "unavailable_count": 0, "mean": 2, "p50": 2, "p90": 3,
        })
        self.assertEqual(first["cohort"]["sessions"]["relation"],
                         {"primary": 1, "child": 1, "unavailable": 0})
        self.assertNotIn("session-", json.dumps(first))
        self.assertNotIn("cycle_id", json.dumps(first))
        detailed = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "100",
        ).stdout)
        ledger = sqlite3.connect(state / "reviews/ledger.sqlite3")
        captured_ids = [row[0] for row in ledger.execute(
            "select session_id from history_capture_members where capture_id=? order by position",
            (first["capture_id"],))]
        ledger.close()
        self.assertEqual(captured_ids, [item["session_id"] for item in detailed["candidates"]])
        source = sqlite3.connect(database)
        source.execute("update part set data=?,time_updated=time_updated+1 where id='part-1'",
                       (json.dumps({"type": "text", "text": "DBSCTR changed"}),))
        source.commit()
        source.close()
        changed_page = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--cursor", "0", "--capture-id", first["capture_id"],
            "--aggregate-only",
        ).stdout)
        self.assertEqual(changed_page["digest"], first["digest"])
        source = sqlite3.connect(database)
        source.execute("update part set data=?,time_updated=time_updated-1 where id='part-1'",
                       (json.dumps({"type": "text", "text": "DBSCTR"}),))
        source.commit()
        source.close()
        source = sqlite3.connect(database)
        source.execute("update part set data=?,time_updated=time_updated+1 where id='interior-10'",
                       (json.dumps({"type": "text", "text": "interior changed"}),))
        source.commit()
        source.close()
        changed_interior = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--cursor", "0", "--capture-id", first["capture_id"],
            "--aggregate-only",
        ).stdout)
        self.assertEqual(changed_interior["digest"], first["digest"])
        source = sqlite3.connect(database)
        source.execute("update part set data=?,time_updated=time_updated-1 where id='interior-10'",
                       (json.dumps({"type": "text", "text": "neutral 10"}),))
        source.commit()
        source.close()
        source = sqlite3.connect(database)
        source.execute("update message set data='{\"changed\":true}' where id='message-1'")
        source.commit()
        source.close()
        changed_message = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--cursor", "0", "--capture-id", first["capture_id"],
            "--aggregate-only",
        ).stdout)
        self.assertEqual(changed_message["digest"], first["digest"])
        source = sqlite3.connect(database)
        source.execute("update message set data='{}' where id='message-1'")
        source.commit()
        source.close()
        second_run = subprocess.run(
            [sys.executable, str(SCRIPT), "review-history", "--database", str(database),
             "--state-root", str(state), "--limit", "2", "--cursor", "2",
             "--capture-id", first["capture_id"], "--aggregate-only"],
            cwd=self.repo, text=True, capture_output=True, env=isolated_env(),
        )
        self.assertEqual(second_run.returncode, 0, second_run.stderr)
        second = json.loads(second_run.stdout)
        self.assertEqual(second["selected_count"], 1)
        self.assertIsNone(second["continuation"])
        source = sqlite3.connect(database)
        source.execute("update message set data='{\"page\":2}' where id='message-0'")
        source.commit()
        source.close()
        changed_second = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--cursor", "2", "--capture-id", first["capture_id"],
            "--aggregate-only",
        ).stdout)
        self.assertEqual(changed_second["digest"], second["digest"])
        source = sqlite3.connect(database)
        source.execute("update message set data='{}' where id='message-0'")
        source.commit()
        source.close()
        filtered = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--project-digest", hashlib.sha256(b"project-1").hexdigest(),
            "--aggregate-only",
        ).stdout)
        self.assertEqual((filtered["selected_count"], filtered["metrics"]["tokens"]["mean"]), (1, 2))
        detailed_capture = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--capture",
        ).stdout)
        unbound_capture = run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--capture-id", detailed_capture["capture_id"],
            "--aggregate-only", ok=False,
        )
        self.assertEqual((unbound_capture.returncode, unbound_capture.stderr),
                         (75, "source_index_unavailable\n"))

        source = sqlite3.connect(database)
        source.execute("insert into session values "
                       "('session-empty', null, 'empty', 1784073600300, null, null, null)")
        source.commit()
        source.close()
        session_stale = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                       "--state-root", str(state), "--summary-only").stdout)
        self.assertEqual(session_stale["signal_count"], 2)
        maintain_cli()
        extension = sqlite3.connect(sidecar)
        session_generation = extension.execute(
            "select generation_id from active_generation").fetchone()[0]
        self.assertNotEqual(session_generation, generation_before)
        extension.close()

        summary = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                 "--state-root", str(state), "--summary-only").stdout)
        self.assertEqual(summary["mode"], "summary")
        self.assertEqual(summary["signal_count"], 2)
        self.assertEqual(summary["groups"], [
            {"tool": "read", "failure_class": "timed_out", "recovered": False, "count": 1},
            {"tool": "unknown", "failure_class": "permission_denied", "recovered": False, "count": 1},
        ])
        self.assertNotIn("session-", json.dumps(summary))
        self.assertNotIn("failed-", json.dumps(summary))

        source = sqlite3.connect(database)
        source.execute("insert into part values ('late-failure', 'message-2', 'session-2', "
                       "1784073600200, 1784073600200, ?)", (json.dumps({
                           "type": "tool", "tool": "bash", "state": {"status": "failed"},
                       }),))
        source.commit()
        source.close()
        stale = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                               "--state-root", str(state), "--summary-only").stdout)
        self.assertEqual(stale["signal_count"], 2)
        maintain_cli()
        extension = sqlite3.connect(sidecar)
        part_generation = extension.execute("select generation_id from active_generation").fetchone()[0]
        self.assertNotEqual(part_generation, session_generation)
        extension.close()
        refreshed = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                    "--state-root", str(state), "--summary-only").stdout)
        self.assertEqual(refreshed["signal_count"], 3)
        source = sqlite3.connect(database)
        source.execute("insert into part values ('late-success', 'message-2', 'session-2', "
                       "1784073600201, 1784073600201, ?)", (json.dumps({
                           "type": "tool", "tool": "bash", "state": {"status": "completed"},
                       }),))
        source.commit()
        source.close()
        maintain_cli()
        recovered = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                   "--state-root", str(state), "--summary-only").stdout)
        self.assertIn({"tool": "bash", "failure_class": "tool_failed", "recovered": True, "count": 1},
                      recovered["groups"])
        extended_run = subprocess.run(
            [sys.executable, str(SCRIPT), "review-history", "--database", str(database),
             "--state-root", str(state), "--limit", "2", "--cursor", "2",
             "--capture-id", first["capture_id"], "--aggregate-only"], cwd=self.repo,
            text=True, capture_output=True, env=isolated_env(),
        )
        self.assertEqual(extended_run.returncode, 0, extended_run.stderr)
        self.assertEqual(json.loads(extended_run.stdout)["selected_count"], 1)
        source = sqlite3.connect(database)
        source.execute("update part set time_created=time_created+1 where id='part-0'")
        source.commit()
        source.close()
        stale_key = json.loads(run(self.repo, "incident-scan", "--database", str(database),
                                   "--state-root", str(state), "--summary-only").stdout)
        self.assertEqual(stale_key["signal_count"], 3)
        maintain_cli()
        replacement = sqlite3.connect(sidecar)
        replacement_generation = replacement.execute(
            "select generation_id from active_generation").fetchone()[0]
        replacement.close()
        self.assertNotEqual(replacement_generation, generation_before)
        source = sqlite3.connect(database)
        source.execute("delete from part where id in ('late-failure','late-success')")
        source.commit()
        source.close()
        maintain_cli()
        regression = sqlite3.connect(sidecar)
        regression_generation = regression.execute(
            "select generation_id from active_generation").fetchone()[0]
        regression.close()
        self.assertNotEqual(regression_generation, replacement_generation)

        loader = importlib.machinery.SourceFileLoader("dbsctrctl_incident_summary", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.assertEqual(module.incident_failure_class(
            {"error": {"code": "not mapped", "name": "EACCES"}}, "error"), "tool_error")

        run(self.repo, "review-forget", "--database", str(database),
            "--state-root", str(state), "--session-id", "session-2")
        self.assertFalse(sidecar.exists())
        maintain_cli()
        rebuilt = sqlite3.connect(sidecar)
        self.assertEqual(rebuilt.execute(
            "select count(*) from index_rows where session_id in ('session-1','session-2')").fetchone()[0], 0)
        post_forget = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--aggregate-only",
        ).stdout)
        self.assertEqual(post_forget["selected_count"], 1)
        post_forget_incidents = json.loads(run(
            self.repo, "incident-scan", "--database", str(database), "--state-root", str(state),
            "--summary-only",
        ).stdout)
        self.assertEqual(post_forget_incidents["signal_count"], 0)
        os.chmod(sidecar, 0o644)
        unsafe_mode = run(self.repo, "incident-scan", "--database", str(database),
                          "--state-root", str(state), "--summary-only", ok=False)
        self.assertEqual((unsafe_mode.returncode, unsafe_mode.stderr),
                         (75, "source_index_unavailable\n"))
        os.chmod(sidecar, 0o600)
        rebuilt.execute("create table unexpected_payload (value text)")
        rebuilt.commit()
        extra_object = run(self.repo, "incident-scan", "--database", str(database),
                           "--state-root", str(state), "--summary-only", ok=False)
        self.assertEqual((extra_object.returncode, extra_object.stderr),
                         (75, "source_index_unavailable\n"))
        rebuilt.execute("drop table unexpected_payload")
        rebuilt.execute("alter table index_rows add column payload text")
        rebuilt.commit()
        rebuilt.close()
        corrupt = run(self.repo, "incident-scan", "--database", str(database),
                      "--state-root", str(state), "--summary-only", ok=False)
        self.assertEqual((corrupt.returncode, corrupt.stderr), (75, "source_index_unavailable\n"))
        sidecar.unlink()
        sidecar.symlink_to(database)
        unsafe_link = run(self.repo, "history-source-index-refresh", "--database", str(database),
                          "--state-root", str(state), ok=False)
        self.assertIn("history source index is unsafe", unsafe_link.stderr)

    def test_history_aggregate_reports_authoritative_zero_tool_calls(self):
        database = Path(self.temp.name) / "history-zero.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer,
                                  agent text, tokens_input integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               data text);
            insert into session values ('session-zero', null, 'empty', 1784073600000,
                                        'reviewer-openai', 0);
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-zero-state"
        for _ in range(20):
            maintained = json.loads(run(
                self.repo, "history-source-index-refresh", "--database", str(database),
                "--state-root", str(state)).stdout)
            if maintained["state"] == "ready":
                break
        self.assertEqual(maintained["state"], "ready")
        aggregate = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--aggregate-only",
        ).stdout)
        self.assertEqual(aggregate["metrics"]["tool_calls"], {
            "available_count": 1, "unavailable_count": 0, "mean": 0, "p50": 0, "p90": 0,
        })

    def test_history_source_index_finishes_captured_target_while_source_appends(self):
        database = Path(self.temp.name) / "history-append.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text,
                               time_created integer, data text);
            insert into session values ('session-append', 1784073600000);
            insert into message values ('message-append', 'session-append', 1784073600000, '{}');
        """)
        connection.executemany(
            "insert into part values (?, 'message-append', 'session-append', ?, '{}')",
            [(f"part-{index}", 1784073600000 + index) for index in range(25)],
        )
        connection.commit()
        connection.execute("pragma journal_mode=wal")
        connection.close()
        state = Path(self.temp.name) / "history-append-state"
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_append_index", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        args = SimpleNamespace(database=str(database), state_root=str(state))
        original_insert = module.history_projection_insert_session
        appended = [False]

        def insert_and_append(*values):
            result = original_insert(*values)
            if not appended[0]:
                writer = sqlite3.connect(database)
                writer.execute("insert into part values "
                               "('part-appended', 'message-append', 'session-append', "
                               "1784073600100, '{}')")
                writer.commit()
                writer.close()
                appended[0] = True
            return result

        output = io.StringIO()
        with mock.patch.object(module, "history_projection_insert_session", side_effect=insert_and_append), \
                contextlib.redirect_stdout(output):
            module.command_history_source_index_refresh(args)
        captured = json.loads(output.getvalue())
        self.assertEqual((captured["state"], captured["material_rows"]), ("ready", 25))
        sidecar = sqlite3.connect(state / "reviews/history-source-index.sqlite3")
        captured_generation = sidecar.execute("select generation_id from active_generation").fetchone()[0]
        self.assertEqual(sidecar.execute(
            "select covered_part_ceiling from index_generations where generation_id=?",
            (captured_generation,)).fetchone(), (25,))
        sidecar.close()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.command_history_source_index_refresh(args)
        extended = json.loads(output.getvalue())
        sidecar = sqlite3.connect(state / "reviews/history-source-index.sqlite3")
        extended_generation = sidecar.execute("select generation_id from active_generation").fetchone()[0]
        sidecar.close()
        self.assertEqual((extended["state"], extended["material_rows"]), ("ready", 26))
        self.assertNotEqual(extended_generation, captured_generation)

    def test_review_snapshot_excludes_sessions_created_during_pagination(self):
        database = Path(self.temp.name) / "snapshot.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR one', 1784073600000);
            insert into session values ('session-2', null, 'DBSCTR two', 1784073601000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into message values ('message-2', 'session-2', 1784073601000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
            insert into part values ('part-2', 'message-2', 'session-2', 1784073601000, 'DBSCTR two');
        """)
        connection.commit()
        state = Path(self.temp.name) / "snapshot-state"
        first = json.loads(run(self.repo, "review-scan", "--database", str(database),
                               "--state-root", str(state), "--limit", "1", "--cursor", "0").stdout)
        connection.execute("insert into session values ('session-new', null, 'DBSCTR new', ?)",
                           (first["snapshot"],))
        connection.execute("insert into message values ('message-new', 'session-new', ?, '{}')",
                           (first["snapshot"],))
        connection.execute("insert into part values ('part-new', 'message-new', 'session-new', ?, 'DBSCTR new')",
                           (first["snapshot"],))
        connection.commit()
        continuation = ["review-scan", "--database", str(database), "--state-root", str(state),
                        "--limit", "10", "--cursor", "1", "--snapshot", str(first["snapshot"]),
                        "--session-ceiling", str(first["session_ceiling"]),
                        "--part-ceiling", str(first["part_ceiling"]),
                        "--database-digest", first["database_digest"]]
        second = json.loads(run(self.repo, *continuation).stdout)
        self.assertNotIn("session-new", second["session_ids"])
        connection.execute("update part set data='neutral mutation' where id='part-2'")
        connection.commit()
        connection.close()
        changed = run(self.repo, *continuation, ok=False)
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_excludes_active_reviewer_tree_from_snapshot_completion_and_history_save(self):
        database = Path(self.temp.name) / "excluded-reviewer.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('active-tool', null, 'DBSCTR active', 1784073600000);
            insert into session values ('active-child', 'active-tool', 'DBSCTR child', 1784073600001);
            insert into session values ('included-1', null, 'DBSCTR one', 1784073600002);
            insert into session values ('included-2', null, 'DBSCTR two', 1784073600003);
            insert into message values ('message-active', 'active-tool', 1784073600000, '{}');
            insert into message values ('message-child', 'active-child', 1784073600001, '{}');
            insert into message values ('message-one', 'included-1', 1784073600002, '{}');
            insert into message values ('message-two', 'included-2', 1784073600003, '{}');
            insert into part values ('part-active', 'message-active', 'active-tool', 1784073600000, 'DBSCTR active');
            insert into part values ('part-child', 'message-child', 'active-child', 1784073600001, 'DBSCTR child');
            insert into part values ('part-one', 'message-one', 'included-1', 1784073600002, 'DBSCTR one');
            insert into part values ('part-two', 'message-two', 'included-2', 1784073600003, 'DBSCTR two');
        """)
        connection.commit()
        state = Path(self.temp.name) / "excluded-reviewer-state"
        invalid = run(self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
                      "--limit", "1", "--cursor", "0", "--excluded-session-id", "/active-tool", ok=False)
        self.assertIn("invalid excluded session ID", invalid.stderr)
        first = json.loads(run(self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
                               "--limit", "1", "--cursor", "0", "--excluded-session-id", "active-tool").stdout)
        self.assertEqual(first["session_ids"], ["included-1"])
        self.assertNotIn("active-tool", json.dumps(first))
        self.assertNotIn("active-child", json.dumps(first))
        from_child = json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "10", "--cursor", "0", "--excluded-session-id", "active-child",
        ).stdout)
        self.assertEqual(from_child["session_ids"], ["included-1", "included-2"])
        self.assertNotIn("active-tool", json.dumps(from_child))
        from_message = json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "10", "--cursor", "0", "--excluded-session-id", "detached-tool",
            "--excluded-message-id", "message-active",
        ).stdout)
        self.assertEqual(from_message["session_ids"], ["included-1", "included-2"])
        self.assertNotIn("active-tool", json.dumps(from_message))
        connection.execute("update part set data='active mutation' where id='part-child'")
        connection.commit()
        continued = json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--cursor", "1", "--snapshot", str(first["snapshot"]),
            "--session-ceiling", str(first["session_ceiling"]), "--part-ceiling", str(first["part_ceiling"]),
            "--database-digest", first["database_digest"], "--exclusion-digest", first["exclusion_digest"],
        ).stdout)
        self.assertEqual(continued["session_ids"], ["included-2"])
        report = {
            "session_ids": first["session_ids"], "cycle_ids": first["cycle_ids"], "scan_digest": first["digest"],
            "snapshot": first["snapshot"], "session_ceiling": first["session_ceiling"],
            "part_ceiling": first["part_ceiling"], "database_digest": first["database_digest"],
            "exclusion_digest": first["exclusion_digest"],
            "limit": 1, "cursor": 0, "decision": "reviewed",
        }
        run(self.repo, "review-complete", "--report-json", json.dumps(report), "--scan-digest", first["digest"],
            "--database", str(database), "--state-root", str(state))
        saved = ledger_text(state)
        self.assertNotIn("active-tool", saved)
        self.assertNotIn("active-child", saved)
        history_scan = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--excluded-session-id", "active-tool",
        ).stdout)
        history = {
            "schema_version": 1, "cohort": ["included-2"], "query_digest": history_scan["digest"],
            "rubric": {"name": "history", "version": "1", "digest": "a" * 64},
            "snapshot": history_scan["snapshot"], "session_ceiling": history_scan["session_ceiling"],
            "part_ceiling": history_scan["part_ceiling"], "database_digest": history_scan["database_digest"],
            "findings": ["sanitized"],
        }
        connection.execute("update part set data='another active mutation' where id='part-active'")
        connection.commit()
        run(self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
            "--report-json", json.dumps(history), "--excluded-session-id", "active-tool")
        self.assertNotIn("active-tool", ledger_text(state))
        connection.execute("update part set data='included mutation' where id='part-two'")
        connection.commit()
        connection.close()
        changed = run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--cursor", "1", "--snapshot", str(first["snapshot"]),
            "--session-ceiling", str(first["session_ceiling"]), "--part-ceiling", str(first["part_ceiling"]),
            "--database-digest", first["database_digest"], "--exclusion-digest", first["exclusion_digest"], ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_completion_allows_unrelated_snapshot_mutation(self):
        database = Path(self.temp.name) / "concurrent-completion.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR one', 1784073600000);
            insert into session values ('session-2', null, 'DBSCTR two', 1784073601000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into message values ('message-2', 'session-2', 1784073601000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
            insert into part values ('part-2', 'message-2', 'session-2', 1784073601000, 'DBSCTR two');
        """)
        connection.commit()
        state = Path(self.temp.name) / "concurrent-completion-state"
        scan = json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--cursor", "0",
        ).stdout)
        self.assertEqual(scan["session_ids"], ["session-1"])
        connection.execute("update part set data='unrelated active mutation' where id='part-2'")
        connection.commit()
        connection.close()
        report = {
            "session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
            "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
            "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
            "database_digest": "f" * 64, "limit": 1, "cursor": 0,
            "decision": "reviewed",
        }
        run(self.repo, "review-complete", "--report-json", json.dumps(report),
            "--scan-digest", scan["digest"], "--database", str(database), "--state-root", str(state))
        stored = ledger_text(state)
        self.assertIn("session-1", stored)
        self.assertNotIn("f" * 64, stored)

    def test_review_completion_rejects_selected_source_mutation(self):
        database = Path(self.temp.name) / "selected-source.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (
                id text primary key, parent_id text, title text, time_created integer,
                project_id text, cost real, tokens_input integer
            );
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR one', 1784073600000, 'project-1', 1.0, 10);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
        """)
        connection.commit()
        state = Path(self.temp.name) / "selected-source-state"
        scan = json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "1", "--cursor", "0",
        ).stdout)
        report = {
            "session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
            "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
            "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
            "database_digest": scan["database_digest"], "limit": 1, "cursor": 0,
            "decision": "reviewed",
        }
        connection.execute("update session set cost=2.0, tokens_input=20 where id='session-1'")
        connection.execute("update part set data='DBSCTR changed' where id='part-1'")
        connection.commit()
        connection.close()
        changed = run(
            self.repo, "review-complete", "--report-json", json.dumps(report),
            "--scan-digest", scan["digest"], "--database", str(database),
            "--state-root", str(state), ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_completion_rejects_changed_candidate_metadata(self):
        database = Path(self.temp.name) / "changed.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR one', 1784073600000);
            insert into session values ('session-2', 'session-1', 'child', 1784073601000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
        """)
        connection.commit()
        state = Path(self.temp.name) / "changed-state"
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database),
                              "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        report = Path(self.temp.name) / "changed-report.json"
        report.write_text(json.dumps({"session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
                                       "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
                                       "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
                                       "database_digest": scan["database_digest"],
                                      "limit": 10, "cursor": 0, "decision": "reviewed"}))
        connection.execute("update session set parent_id = null where id = 'session-2'")
        connection.commit()
        connection.close()
        result = run(self.repo, "review-complete", "--report", str(report),
                     "--scan-digest", scan["digest"], "--database", str(database),
                     "--state-root", str(state), ok=False)
        self.assertIn("changed within the review snapshot", result.stderr)
        self.assertEqual(list((state / "reviews").glob("*.json")), [])

    def test_review_snapshot_excludes_later_parts_and_children(self):
        database = Path(self.temp.name) / "later-content.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'one', 1784073600000);
            insert into session values ('session-2', null, 'two', 1784073601000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
        """)
        connection.commit()
        state = Path(self.temp.name) / "later-content-state"
        first = json.loads(run(self.repo, "review-scan", "--database", str(database),
                               "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        later = first["snapshot"] + 1
        connection.execute("insert into message values ('message-2', 'session-2', ?, '{}')", (later,))
        connection.execute("insert into part values ('part-2', 'message-2', 'session-2', ?, 'DBSCTR two')", (later,))
        connection.execute("insert into session values ('child-new', 'session-1', 'child', ?)", (later,))
        connection.commit()
        connection.close()
        repeated = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                   "--state-root", str(state), "--limit", "10", "--cursor", "0",
                                   "--snapshot", str(first["snapshot"]),
                                   "--session-ceiling", str(first["session_ceiling"]),
                                   "--part-ceiling", str(first["part_ceiling"]),
                                   "--database-digest", first["database_digest"]).stdout)
        self.assertEqual(repeated, first)

    def test_historical_exclusion_covers_archives_replays_and_existing_evidence(self):
        database = Path(self.temp.name) / "historical-family.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('caller', null, 1784073600000);
            insert into session values ('child', 'caller', 1784073600001);
            insert into session values ('grandchild', 'child', 1784073600002);
            insert into session values ('other', null, 1784073600003);
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "historical-family-state"
        history = state / "reviews/history"
        history.mkdir(parents=True)
        os.chmod(state / "reviews", 0o700)
        os.chmod(history, 0o700)
        (state / "reviews/.lock").touch()
        for index, session_id in enumerate(("caller", "child", "grandchild", "other")):
            path = history / f"{session_id}.json"
            path.write_text(json.dumps({
                "schema_version": 1, "session_id": session_id,
                "completed_at": str(1784073600000 + index), "method_revision": "3.16", "context": "test",
                "project_digest": "a" * 64, "cycles": [], "aggregates": {}, "reviewed_status": "reviewed",
            }))
            os.chmod(path, 0o600)
        archive_only = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--archive-only", "--excluded-session-id", "caller",
        ).stdout)
        self.assertEqual(archive_only["session_ids"], ["other"])
        report = {"schema_version": 1, "cohort": ["child"], "query_digest": "b" * 64,
                  "rubric": {"name": "history", "version": "1", "digest": "c" * 64}, "findings": ["safe"]}
        run(self.repo, "review-migrate", "--state-root", str(state))
        saved = json.loads(run(self.repo, "review-history-save", "--database", str(database),
                               "--state-root", str(state), "--report-json", json.dumps(report)).stdout)
        replay = run(self.repo, "review-history", "--database", str(database), "--state-root", str(state),
                     "--replay", saved["report_id"], "--excluded-session-id", "caller", ok=False)
        self.assertIn("intersects the excluded session family", replay.stderr)
        report["cohort"] = ["grandchild"]
        rejected = run(self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
                       "--report-json", json.dumps(report), "--excluded-session-id", "caller", ok=False)
        self.assertIn("contains an excluded session", rejected.stderr)

    def test_review_exclusion_handles_no_parent_schema_and_orphan_part_mutation(self):
        no_parent = Path(self.temp.name) / "no-parent.db"
        connection = __import__("sqlite3").connect(no_parent)
        connection.executescript("""
            create table session (id text primary key, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('caller', 1784073600000);
            insert into session values ('other', 1784073600001);
            insert into message values ('caller-message', 'caller', 1784073600000, '{}');
            insert into message values ('other-message', 'other', 1784073600001, '{}');
            insert into part values ('caller-part', 'caller-message', 'caller', 1784073600000, 'DBSCTR');
            insert into part values ('other-part', 'other-message', 'other', 1784073600001, 'DBSCTR');
        """)
        connection.commit()
        no_parent_scan = json.loads(run(
            self.repo, "review-scan", "--database", str(no_parent), "--state-root", str(Path(self.temp.name) / "no-parent-state"),
            "--limit", "10", "--cursor", "0", "--excluded-session-id", "caller",
        ).stdout)
        self.assertEqual(no_parent_scan["session_ids"], ["other"])
        orphan = Path(self.temp.name) / "orphan.db"
        connection = __import__("sqlite3").connect(orphan)
        connection.executescript("""
            create table session (id text primary key, parent_id text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('included', null, 1784073600000);
            insert into message values ('included-message', 'included', 1784073600000, '{}');
            insert into part values ('included-part', 'included-message', 'included', 1784073600000, 'DBSCTR');
            insert into part values ('orphan-part', 'missing-message', 'included', 1784073600001, 'before');
        """)
        connection.commit()
        first = json.loads(run(self.repo, "review-scan", "--database", str(orphan),
                               "--state-root", str(Path(self.temp.name) / "orphan-state"),
                               "--limit", "10", "--cursor", "0").stdout)
        connection.execute("update part set data='after' where id='orphan-part'")
        connection.commit()
        connection.close()
        changed = run(
            self.repo, "review-scan", "--database", str(orphan), "--state-root", str(Path(self.temp.name) / "orphan-state"),
            "--limit", "10", "--cursor", "0", "--snapshot", str(first["snapshot"]),
            "--session-ceiling", str(first["session_ceiling"]), "--part-ceiling", str(first["part_ceiling"]),
            "--database-digest", first["database_digest"], ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_rejects_non_millisecond_timestamps(self):
        database = Path(self.temp.name) / "bad-time.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created text);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR', '1784073600000');
        """)
        connection.commit()
        connection.close()
        result = run(self.repo, "review-scan", "--database", str(database),
                     "--state-root", str(Path(self.temp.name) / "bad-time-state"),
                     "--limit", "10", "--cursor", "0", ok=False)
        self.assertIn("integer milliseconds", result.stderr)

    def test_review_completion_serializes_revalidation(self):
        database = Path(self.temp.name) / "race.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'one', 1784073600000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR one');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "race-state"
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database),
                              "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        report = Path(self.temp.name) / "race-report.json"
        report.write_text(json.dumps({"session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
                                       "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
                                       "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
                                       "database_digest": scan["database_digest"],
                                      "limit": 10, "cursor": 0, "decision": "reviewed"}))
        lock_path = state / "reviews/.lock"
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            command = [sys.executable, str(SCRIPT), "review-complete", "--report", str(report),
                       "--scan-digest", scan["digest"], "--database", str(database),
                       "--state-root", str(state)]
            processes = [subprocess.Popen(command, cwd=self.repo, text=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            time.sleep(0.2)
            fcntl.flock(lock, fcntl.LOCK_UN)
            results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
        self.assertEqual(sorted(result[2] for result in results), [0, 1])
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        self.assertEqual(connection.execute("SELECT count(*) FROM review_reports").fetchone()[0], 1)
        connection.close()

    def test_review_completion_rejection_writes_no_marker(self):
        state = Path(self.temp.name) / "state"
        report = Path(self.temp.name) / "unsafe-report.json"
        report.write_text(json.dumps({"session_ids": ["session-1"], "cycle_ids": [], "scan_digest": "bad",
                                      "limit": 10, "cursor": 0, "decision": "see https://unsafe.invalid"}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", "bad",
            "--state-root", str(state), ok=False)
        self.assertFalse((state / "reviews").exists())

    def test_review_rejects_paths_and_nonopaque_identifiers(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_review_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        for value in ("`/Users/x/file`", "(/tmp/file)", "path:/tmp/file", "~/file",
                      "[/tmp/private]", "{/Users/x}", ",/tmp/x"):
            self.assertTrue(module.review_unsafe(value), value)
        state = Path(self.temp.name) / "state"
        report = Path(self.temp.name) / "unsafe-id.json"
        sessions = ["/tmp/session"]
        digest = module.review_digest(sessions, [])
        report.write_text(json.dumps({"session_ids": sessions, "cycle_ids": [], "scan_digest": digest,
                                      "limit": 10, "cursor": 0, "decision": "reviewed"}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", digest,
            "--state-root", str(state), ok=False)
        self.assertFalse((state / "reviews").exists())
        sessions = ["session-1"]
        digest = module.review_digest(sessions, [])
        report.write_text(json.dumps({"session_ids": sessions, "cycle_ids": [], "scan_digest": digest,
                                      "limit": 10, "cursor": 0, "decision": "x" * 257}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", digest,
            "--state-root", str(state), ok=False)
        self.assertFalse((state / "reviews").exists())

    def test_review_correlates_current_cycle_record(self):
        self.start()
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_review_cycle_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        cycles = module.correlated_cycles(str(self.repo / "docs"), set())
        self.assertEqual(cycle_core(cycles), [
            {"cycle_id": "cycle-1", "state": "active", "risk": "routine", "delivery_intent": "local"},
        ])
        self.assertEqual(cycles[0]["context"], "test")
        self.assertIsInstance(cycles[0]["started_at"], int)
        self.assertIsNone(cycles[0]["ended_at"])

    def test_review_correlation_rejects_ambiguous_source_checkout(self):
        self.start()
        first = json.loads(self.record_path().read_text())
        first["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "removed-worktree"}
        first["source"] = {"path": str(self.repo)}
        first["gates"]["domain"]["result"] = "failed"
        self.record_path().write_text(json.dumps(first))
        second = json.loads(json.dumps(first))
        second["cycle_id"] = "cycle-2"
        second["state"] = "completed"
        second["gates"]["domain"]["result"] = "passed"
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_multi_cycle_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [])

    def test_review_correlates_structured_session_without_path_match(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["schema_version"] = 4
        record["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "other"}
        record["source"] = {"path": str(Path(self.temp.name) / "source")}
        record["runtime"] = {"opencode": {"session_ids": ["session-linked"]}}
        self.record_path().write_text(json.dumps(record))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_structured_cycle_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            self.assertEqual(cycle_core(module.correlated_cycles(
                str(Path(self.temp.name) / "missing"), set(), {"session-linked"})), [
                {"cycle_id": "cycle-1", "state": "abandoned", "risk": "routine", "delivery_intent": "local"},
            ])
        finally:
            os.chdir(previous)

    def test_review_correlation_uses_tiered_unambiguous_identity(self):
        self.start()
        first = json.loads(self.record_path().read_text())
        first["schema_version"] = 4
        first["runtime"] = {"opencode": {"session_ids": ["runtime-root"]}}
        first["source"] = {"path": str(self.repo)}
        self.record_path().write_text(json.dumps(first))
        second = json.loads(json.dumps(first))
        second["cycle_id"] = "cycle-2"
        second["runtime"] = {"opencode": {"session_ids": ["other-root"]}}
        second["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "other-worktree"}
        second["source"] = {"path": str(self.repo)}
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_tiered_cycle_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)

        exact, quality = module.correlated_cycles(
            str(self.repo), set(), {"runtime-root", "other-root"}, exact_session_id="runtime-root",
            with_quality=True,
        )
        self.assertEqual(cycle_core(exact), [{"cycle_id": "cycle-1", "state": "active",
                                  "risk": "routine", "delivery_intent": "local"}])
        self.assertEqual(quality, "exact")
        exact, quality = module.correlated_cycles(
            str(self.repo), {"cycle-2"}, {"runtime-root"}, exact_session_id="runtime-root",
            with_quality=True,
        )
        self.assertEqual(cycle_core(exact), [{"cycle_id": "cycle-1", "state": "active",
                                  "risk": "routine", "delivery_intent": "local"}])
        self.assertEqual(quality, "exact")
        family, quality = module.correlated_cycles(
            str(self.repo), set(), {"runtime-root"}, exact_session_id="child", with_quality=True,
        )
        self.assertEqual(cycle_core(family), [{"cycle_id": "cycle-1", "state": "active",
                                   "risk": "routine", "delivery_intent": "local"}])
        self.assertEqual(quality, "family")

        first["runtime"] = {"opencode": {"session_ids": ["shared-parent"]}}
        self.record_path().write_text(json.dumps(first))
        second["runtime"] = {"opencode": {"session_ids": ["shared-parent"]}}
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        ambiguous, quality = module.correlated_cycles(
            str(self.repo), set(), {"shared-parent"}, exact_session_id="shared-parent",
            with_quality=True,
        )
        self.assertEqual([item["cycle_id"] for item in ambiguous], ["cycle-1", "cycle-2"])
        self.assertEqual(quality, "ambiguous")
        worktree, quality = module.correlated_cycles(
            str(self.repo), set(), {"shared-parent"}, exact_session_id="child", with_quality=True,
        )
        self.assertEqual(cycle_core(worktree), [{"cycle_id": "cycle-1", "state": "active",
                                     "risk": "routine", "delivery_intent": "local"}])
        self.assertEqual(quality, "worktree")

        first["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "missing-one"}
        self.record_path().write_text(json.dumps(first))
        second["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "missing-two"}
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        ambiguous, quality = module.correlated_cycles(
            str(self.repo), set(), set(), exact_session_id="unlinked", with_quality=True,
        )
        self.assertEqual(ambiguous, [])
        self.assertEqual(quality, "ambiguous")

    def test_review_correlates_recursive_family_and_reports_quality(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["schema_version"] = 4
        record["runtime"] = {"opencode": {"session_ids": ["runtime-root"]}}
        record["worktree"]["locator"] = {"root": "dbsctr_worktrees", "path": "missing"}
        self.record_path().write_text(json.dumps(record))
        database = Path(self.temp.name) / "recursive-family.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('runtime-root', null, 'DBSCTR root', 1784073600000);
            insert into session values ('child', 'runtime-root', 'child', 1784073600001);
            insert into session values ('grandchild', 'child', 'grandchild', 1784073600002);
            insert into message values ('message-root', 'runtime-root', 1784073600000, '{}');
            insert into part values ('part-root', 'message-root', 'runtime-root', 1784073600000, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database),
                              "--state-root", str(Path(self.temp.name) / "family-state"),
                              "--limit", "10", "--cursor", "0").stdout)
        candidates = {item["session_id"]: item for item in scan["candidates"]}
        self.assertEqual(candidates["runtime-root"]["correlation_quality"], "exact")
        self.assertEqual(candidates["grandchild"]["correlation_quality"], "family")
        self.assertEqual(cycle_core(candidates["grandchild"]["cycles"]), [
            {"cycle_id": "cycle-1", "state": "abandoned", "risk": "routine",
             "delivery_intent": "local"},
        ])

    def test_review_treats_failed_gate_with_null_exception_as_blocked(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["gates"]["domain"]["result"] = "failed"
        record["gates"]["domain"]["exception"] = None
        self.record_path().write_text(json.dumps(record))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_blocked_cycle_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.assertEqual(cycle_core(module.correlated_cycles(str(self.repo), set())), [
            {"cycle_id": "cycle-1", "state": "blocked", "risk": "routine", "delivery_intent": "local"},
        ])
        record["gates"]["domain"]["exception"] = {"kind": "accepted_risk"}
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(cycle_core(module.correlated_cycles(str(self.repo), set())), [
            {"cycle_id": "cycle-1", "state": "blocked", "risk": "routine", "delivery_intent": "local"},
        ])
        record["gates"]["domain"]["exception"] = {
            "kind": "accepted_risk", "rationale": "bounded", "owner": "maintainer",
            "review_condition": "next revision", "approved_at": "not-a-time",
        }
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(cycle_core(module.correlated_cycles(str(self.repo), set())), [
            {"cycle_id": "cycle-1", "state": "blocked", "risk": "routine", "delivery_intent": "local"},
        ])
        record["gates"]["domain"]["exception"]["approved_at"] = "2026-07-15T00:00:00Z"
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(cycle_core(module.correlated_cycles(str(self.repo), set())), [
            {"cycle_id": "cycle-1", "state": "active", "risk": "routine", "delivery_intent": "local"},
        ])
        record["gates"]["domain"]["applicability"] = "not_applicable"
        record["gates"]["domain"].pop("exception")
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(cycle_core(module.correlated_cycles(str(self.repo), set())), [
            {"cycle_id": "cycle-1", "state": "active", "risk": "routine", "delivery_intent": "local"},
        ])

    def test_review_prune_keeps_tombstone_until_explicit_forget(self):
        database = Path(self.temp.name) / "retention.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-retained', null, 'DBSCTR', 1784073600000);
            insert into message values ('message-retained', 'session-retained', 1784073600000, '{}');
            insert into part values ('part-retained', 'message-retained', 'session-retained', 1784073600000, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "retention-state"
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database),
                              "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        report = Path(self.temp.name) / "retention-report.json"
        report.write_text(json.dumps({"session_ids": scan["session_ids"], "cycle_ids": [],
                                       "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
                                       "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
                                       "database_digest": scan["database_digest"],
                                       "limit": 10, "cursor": 0, "decision": "reviewed"}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", scan["digest"],
            "--database", str(database), "--state-root", str(state))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_retention_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        module.REVIEW_RETENTION_SECONDS = -1
        self.assertEqual(module.prune_review_reports(state), 1)
        self.assertIn("session-retained", module.review_index(state)["sessions"])
        repeated = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                  "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        self.assertEqual(repeated["session_ids"], [])
        run(self.repo, "review-forget", "--state-root", str(state), "--session-id", "session-retained")
        eligible = json.loads(run(self.repo, "review-scan", "--database", str(database),
                                  "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        self.assertEqual(eligible["session_ids"], ["session-retained"])

    def test_review_priority_and_dormancy_are_presentational(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_review_priority_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        candidates = [
            {"cycles": [], "attention": []},
            {"cycles": [{"cycle_id": "active", "state": "active"}], "attention": []},
            {"cycles": [{"cycle_id": "complete", "state": "completed"}], "attention": []},
            {"cycles": [{"cycle_id": "dormant", "state": "active"}], "attention": ["dormant"]},
            {"cycles": [{"cycle_id": "abandoned", "state": "abandoned"}], "attention": []},
            {"cycles": [{"cycle_id": "blocked", "state": "blocked"}], "attention": []},
        ]
        self.assertEqual([module.review_priority(item) for item in reversed(candidates)], [0, 1, 2, 3, 4, 5])
        self.assertEqual(module.review_priority({
            "cycles": [{"cycle_id": "blocked", "state": "blocked"},
                       {"cycle_id": "active", "state": "active"}],
            "attention": ["dormant"],
        }), 0)
        cutoff = 1784073600000
        active = [{"cycle_id": "active", "state": "active"}]
        self.assertEqual(module.review_attention(active, cutoff - module.REVIEW_DORMANT_MS, cutoff), ["dormant"])
        self.assertEqual(module.review_attention(active, cutoff - module.REVIEW_DORMANT_MS + 1, cutoff), [])

    def test_review_malformed_tombstone_fails_closed(self):
        state = Path(self.temp.name) / "malformed-state"
        (state / "reviews").mkdir(parents=True)
        os.chmod(state / "reviews", 0o700)
        index = state / "reviews/reviewed.json"
        index.write_text(
            '{"schema_version":1,"sessions":[],"cycles":{},"forgotten_sessions":{}}')
        os.chmod(index, 0o600)
        (state / "reviews/.lock").touch()
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_malformed_review_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "invalid schema"):
            module.reviewed_ids(str(state))

    def test_review_history_includes_reviewed_with_stable_bounded_pagination(self):
        database = Path(self.temp.name) / "history.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer,
                                  project_id text, cost real, tokens_input integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        raw_payload = "DBSCTR secret prose /Users/private https://unsafe.invalid"
        rows = [(f"session-{index:03}", None, "DBSCTR", 1784073600000 + index,
                 "project-one", 1.25 if index == 100 else 0, 10 if index == 100 else 0)
                for index in range(101)]
        connection.executemany("insert into session values (?, ?, ?, ?, ?, ?, ?)", rows)
        connection.executemany("insert into message values (?, ?, ?, '{}')",
                               [(f"message-{index:03}", f"session-{index:03}", 1784073600000 + index)
                                for index in range(101)])
        connection.executemany("insert into part values (?, ?, ?, ?, ?, ?)",
                               [(f"part-{index:03}", f"message-{index:03}", f"session-{index:03}",
                                 1784073600000 + index, 1784073600000 + index, raw_payload) for index in range(101)])
        connection.execute("update part set data=? where id='part-100'", (json.dumps({
            "type": "tool", "tool": "bash", "state": {"status": "error", "input": "DBSCTR /Users/private"}
        }),))
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-state"
        read_only_state = Path(self.temp.name) / "history-read-only"
        first_history = json.loads(run(self.repo, "review-history", "--database", str(database),
                                       "--state-root", str(read_only_state)).stdout)
        self.assertFalse(read_only_state.exists())
        self.assertEqual(first_history["session_ids"][0], "session-100")
        inbox = json.loads(run(self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
                               "--limit", "100", "--cursor", "0").stdout)
        report = Path(self.temp.name) / "history-review.json"
        report.write_text(json.dumps({"session_ids": inbox["session_ids"], "cycle_ids": inbox["cycle_ids"],
                                      "scan_digest": inbox["digest"], "snapshot": inbox["snapshot"],
                                      "session_ceiling": inbox["session_ceiling"], "part_ceiling": inbox["part_ceiling"],
                                      "database_digest": inbox["database_digest"], "limit": 100, "cursor": 0,
                                      "decision": "reviewed"}))
        run(self.repo, "review-complete", "--report", str(report), "--scan-digest", inbox["digest"],
            "--database", str(database), "--state-root", str(state))
        run(self.repo, "improvement-register", "--state-root", str(state),
            "--worker-id", "history-worker", "--session-id", "session-100")
        connection = sqlite3.connect(database)
        connection.execute("delete from part where id='part-099'")
        connection.execute("delete from message where id='message-099'")
        connection.execute("delete from session where id='session-099'")
        connection.commit()
        connection.close()

        self.assertEqual(json.loads(run(
            self.repo, "review-scan", "--database", str(database), "--state-root", str(state),
            "--limit", "100", "--cursor", "0").stdout)["session_ids"], ["session-100"])
        history = json.loads(run(self.repo, "review-history", "--database", str(database),
                                 "--state-root", str(state)).stdout)
        self.assertEqual(history["session_ids"], [f"session-{index:03}" for index in range(100, 0, -1)])
        self.assertEqual(history["limit"], 100)
        self.assertEqual(history["cursor"], 0)
        self.assertEqual(history["candidates"][0]["aggregates"]["tool_call_count"], 1)
        self.assertEqual(history["candidates"][0]["aggregates"]["tool_error_count"], 1)
        self.assertEqual(history["candidates"][0]["aggregates"]["token_total"], 10)
        self.assertEqual(history["candidates"][0]["aggregates"]["cost_total"], 1.25)
        self.assertTrue(history["candidates"][0]["review_session"])
        self.assertFalse(history["candidates"][1]["review_session"])
        self.assertRegex(history["candidates"][0]["project_digest"], r"^[0-9a-f]{64}$")
        older = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "100", "--cursor", "100", "--snapshot", str(history["snapshot"]),
            "--session-ceiling", str(history["session_ceiling"]), "--part-ceiling", str(history["part_ceiling"]),
            "--database-digest", history["database_digest"],
        ).stdout)
        self.assertEqual(older["session_ids"], ["session-000"])
        backfill = {
            "schema_version": 1, "cohort": ["session-100", "session-099"], "query_digest": history["digest"],
            "rubric": {"name": "history", "version": "1", "digest": "c" * 64},
            "snapshot": history["snapshot"], "session_ceiling": history["session_ceiling"],
            "part_ceiling": history["part_ceiling"], "database_digest": history["database_digest"],
            "findings": ["sanitized"],
        }
        run(self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
            "--report-json", json.dumps(backfill))
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute("SELECT count(*) FROM history_reports").fetchone()[0], 1)
        saved_report = json.loads(connection.execute(
            "SELECT payload FROM history_reports WHERE kind='report'"
        ).fetchone()[0])
        self.assertEqual(saved_report["evidence"][0]["aggregates"]["tool_error_count"], 1)
        self.assertEqual(saved_report["evidence"][0]["aggregates"]["token_total"], 10)
        self.assertNotEqual(saved_report["evidence"][0]["project_digest"], "unavailable")
        self.assertEqual(saved_report["evidence"][1]["session_id"], "session-099")
        self.assertEqual(saved_report["evidence"][1]["project_digest"], "unavailable")
        connection.close()
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(raw_payload, ledger_text(state))
        bounded = run(self.repo, "review-history", "--database", str(database), "--state-root", str(state),
                      "--limit", "101", ok=False)
        self.assertIn("100", bounded.stderr)
        replay = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--snapshot", str(history["snapshot"]), "--session-ceiling", str(history["session_ceiling"]),
            "--part-ceiling", str(history["part_ceiling"]), "--database-digest", history["database_digest"],
        ).stdout)
        self.assertEqual(replay, history)
        connection = __import__("sqlite3").connect(database)
        connection.execute("update part set data=? where id='part-100'", (json.dumps({
            "type": "tool", "tool": "bash", "state": {"status": "completed", "input": "DBSCTR"}
        }),))
        connection.commit()
        connection.close()
        changed = run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--snapshot", str(history["snapshot"]), "--session-ceiling", str(history["session_ceiling"]),
            "--part-ceiling", str(history["part_ceiling"]), "--database-digest", history["database_digest"],
            ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_history_save_revalidates_exact_continuation_cohort(self):
        database = Path(self.temp.name) / "history-continuation-save.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        for index in range(103):
            timestamp = 1784073600000 + index
            connection.execute("insert into session values (?, null, 'DBSCTR', ?)",
                               (f"session-{index:03}", timestamp))
            connection.execute("insert into message values (?, ?, ?, '{}')",
                               (f"message-{index:03}", f"session-{index:03}", timestamp))
            connection.execute("insert into part values (?, ?, ?, ?, ?, 'DBSCTR')",
                               (f"part-{index:03}", f"message-{index:03}",
                                f"session-{index:03}", timestamp, timestamp))
        connection.commit()
        state = Path(self.temp.name) / "history-continuation-save-state"
        first = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "100", "--cursor", "0",
        ).stdout)
        older = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "100", "--cursor", "100", "--snapshot", str(first["snapshot"]),
            "--session-ceiling", str(first["session_ceiling"]),
            "--part-ceiling", str(first["part_ceiling"]), "--database-digest", first["database_digest"],
        ).stdout)
        self.assertEqual(older["session_ids"], ["session-002", "session-001", "session-000"])

        def report(page, session_ids):
            return json.dumps({
                "schema_version": 1, "cohort": session_ids, "query_digest": page["digest"],
                "rubric": {"name": "history", "version": "1", "digest": "c" * 64},
                "snapshot": page["snapshot"], "session_ceiling": page["session_ceiling"],
                "part_ceiling": page["part_ceiling"], "database_digest": page["database_digest"],
                "limit": page["limit"], "cursor": page["cursor"],
                "findings": ["sanitized"],
            })

        for mutation in (
            {"cohort": older["session_ids"][1:]},
            {"cohort": list(reversed(older["session_ids"]))},
            {"limit": 99},
            {"cursor": 99},
        ):
            altered = json.loads(report(older, older["session_ids"]))
            altered.update(mutation)
            rejected = run(
                self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
                "--report-json", json.dumps(altered), ok=False,
            )
            self.assertIn("changed within the review snapshot", rejected.stderr)

        connection.execute("update part set data='DBSCTR selected change' where id='part-001'")
        connection.commit()
        changed = run(
            self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
            "--report-json", report(older, older["session_ids"]), ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

        connection.execute("update part set data='DBSCTR' where id='part-001'")
        connection.execute("update part set data='unrelated change' where id='part-102'")
        connection.commit()
        saved = json.loads(run(
            self.repo, "review-history-save", "--database", str(database), "--state-root", str(state),
            "--report-json", report(older, older["session_ids"]),
        ).stdout)
        self.assertRegex(saved["report_id"], r"^[0-9a-f]{24}$")

        missing_state = Path(self.temp.name) / "history-continuation-missing-state"
        missing_first = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(missing_state),
            "--limit", "100", "--cursor", "0",
        ).stdout)
        missing_older = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(missing_state),
            "--limit", "100", "--cursor", "100", "--snapshot", str(missing_first["snapshot"]),
            "--session-ceiling", str(missing_first["session_ceiling"]),
            "--part-ceiling", str(missing_first["part_ceiling"]),
            "--database-digest", missing_first["database_digest"],
        ).stdout)

        connection.execute("delete from part where id='part-001'")
        connection.execute("delete from message where id='message-001'")
        connection.execute("delete from session where id='session-001'")
        connection.commit()
        connection.close()
        missing = run(
            self.repo, "review-history-save", "--database", str(database), "--state-root", str(missing_state),
            "--report-json", report(missing_older, missing_older["session_ids"]), ok=False,
        )
        self.assertIn("cohort evidence is unavailable", missing.stderr)

    def test_review_history_exposes_structured_telemetry_without_error_content(self):
        database = Path(self.temp.name) / "history-telemetry.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer,
                                  model text, cost real, tokens_input integer, tokens_output integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
            insert into session values ('session-parent', null, 'DBSCTR', 1784073600000,
                                        'unknown/private-model', 1.5, 10, 20);
            insert into session values ('session-child', 'session-parent', 'DBSCTR', 1784073600001,
                                        'global.anthropic.claude-sonnet-5', 0.5, 3, 4);
        """)
        private_error = "provider secret /Users/private https://unsafe.invalid"
        connection.execute("insert into message values ('message-parent', 'session-parent', 1784073600000, ?)",
                           (json.dumps({"role": "assistant", "model": {"modelID": "gpt-5.6-sol"},
                                        "error": {"message": private_error}}),))
        connection.execute("insert into message values ('message-child', 'session-child', 1784073600001, '{}')")
        connection.execute("insert into part values ('part-parent', 'message-parent', 'session-parent', "
                           "1784073600000, 1784073600000, ?)", (json.dumps({
                               "type": "tool", "tool": "bash", "marker": "DBSCTR", "state": {
                                   "status": "error", "error": private_error,
                               },
                           }),))
        connection.execute("insert into part values ('part-child', 'message-child', 'session-child', "
                           "1784073600001, 1784073600001, ?)", (json.dumps({"type": "text", "text": private_error}),))
        connection.commit()
        connection.close()

        result = json.loads(run(self.repo, "review-history", "--database", str(database),
                                "--state-root", str(Path(self.temp.name) / "telemetry-state")).stdout)
        parent = next(item for item in result["candidates"] if item["session_id"] == "session-parent")
        telemetry = parent["telemetry"]
        self.assertEqual(telemetry["model_families"], ["claude", "gpt"])
        self.assertEqual(telemetry["delegation_count"], 1)
        self.assertEqual(telemetry["error_classes"], {"provider_error": 1, "tool_error": 1})
        self.assertEqual(telemetry["availability"]["approval_count"], "unavailable")
        self.assertEqual(telemetry["availability"]["retry_count"], "unavailable")
        self.assertEqual(telemetry["availability"]["model_families"], "available")
        self.assertEqual(telemetry["attribution_status"], parent["correlation_quality"])
        serialized = json.dumps(result)
        self.assertNotIn(private_error, serialized)
        self.assertNotRegex(serialized, r"(?:/Users|https?://)")

        optional = Path(self.temp.name) / "history-telemetry-optional.db"
        connection = sqlite3.connect(optional)
        connection.executescript("""
            create table session (id text primary key, title text, time_created integer);
            create table message (id text primary key, session_id text);
            create table part (id text primary key, message_id text, session_id text,
                               time_created integer, data text);
            insert into session values ('session-minimal', 'DBSCTR', 1784073600000);
            insert into message values ('message-minimal', 'session-minimal');
            insert into part values ('part-minimal', 'message-minimal', 'session-minimal',
                                     1784073600000, '{"type":"text","text":"DBSCTR"}');
        """)
        connection.close()
        minimal = json.loads(run(self.repo, "review-history", "--database", str(optional),
                                 "--state-root", str(Path(self.temp.name) / "optional-state")).stdout)
        telemetry = minimal["candidates"][0]["telemetry"]
        self.assertEqual(telemetry["model_families"], "unavailable")
        self.assertEqual(telemetry["delegation_count"], "unavailable")
        self.assertEqual(telemetry["cost_total"], "unavailable")
        self.assertEqual(telemetry["availability"]["cost_total"], "unavailable")
        self.assertEqual(telemetry["availability"]["error_classes"], "available")
        self.assertEqual(telemetry["error_classes"], {"tool_error": 0})

    def test_write_connection_migrates_capture_schema_before_integrity(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_capture_migration", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        state = Path(self.temp.name) / "capture-migration-state"
        reviews = state / "reviews"
        reviews.mkdir(parents=True, mode=0o700)
        os.chmod(reviews, 0o700)
        ledger = reviews / "ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        module.ledger_schema(connection)
        connection.commit()
        module.ensure_capture_schema(connection)
        connection.execute("drop table history_capture_page_sources")
        connection.execute("update ledger_meta set value='1' where key='capture_schema'")
        connection.commit()
        connection.close()
        os.chmod(ledger, 0o600)

        with module.ledger_connection(state, write=True) as migrated:
            self.assertEqual(migrated.execute(
                "select value from ledger_meta where key='capture_schema'").fetchone(),
                (str(module.CAPTURE_SCHEMA),))
            self.assertEqual(migrated.execute(
                "select count(*) from sqlite_master where type='table' "
                "and name='history_capture_page_sources'").fetchone(), (1,))

    def test_benchmarks_bind_windows_replay_and_classify_association(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_benchmark_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        state = Path(self.temp.name) / "benchmark-state"
        reviews = state / "reviews"
        reviews.mkdir(parents=True, mode=0o700)
        os.chmod(reviews, 0o700)
        ledger = reviews / "ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        module.ledger_schema(connection)
        connection.commit()
        module.ensure_capture_schema(connection)

        activation = module.REVIEW_START_MS + module.BENCHMARK_WINDOW_MS
        evaluated = activation + module.BENCHMARK_WINDOW_MS

        def capture(label, after, before, errors):
            members = []
            for index, count in enumerate(errors):
                members.append({
                    "schema_version": 1, "session_id": f"{label}-{index}",
                    "completed_at": str(max(after, module.REVIEW_START_MS)),
                    "method_revision": "unavailable", "context": "unavailable",
                    "project_digest": "unavailable", "cycles": [],
                    "aggregates": {"candidate_count": 1, "tool_error_count": count},
                    "reviewed_status": "unreviewed", "correlation_quality": "unavailable",
                })
            query = {name: None for name in (
                "after", "before", "method_revision", "cycle_id", "state", "context",
                "project_digest", "reviewed_status")}
            query.update({"after": after, "before": before, "archive_only": False})
            manifest = {
                "schema_version": 1, "query": query, "snapshot": evaluated,
                "session_ceiling": len(members), "part_ceiling": len(members),
                "database_digest": "0" * 64, "exclusion_digest": None,
                "page_size": 100, "pages": [{"cursor": 0, "limit": 100,
                                               "count": len(members), "continuation": None,
                                               "digest": "1" * 64}],
                "member_count": len(members),
                "members_digest": hashlib.sha256(module.ledger_payload(members).encode()).hexdigest(),
                "aggregates": module.history_capture_aggregates(members),
            }
            manifest["capture_id"] = hashlib.sha256(module.ledger_payload(manifest).encode()).hexdigest()[:24]
            module.validate_history_capture(manifest, members)
            connection.execute("insert into history_captures values (?, ?)",
                               (manifest["capture_id"], module.ledger_payload(manifest)))
            connection.executemany("insert into history_capture_members values (?, ?, ?, ?)",
                                   ((manifest["capture_id"], index, member["session_id"],
                                     module.ledger_payload(member)) for index, member in enumerate(members)))
            return manifest

        baseline = capture("baseline", activation - module.BENCHMARK_WINDOW_MS, activation - 1, [4])
        observation = capture("observation", activation, activation + module.BENCHMARK_WINDOW_MS - 1, [1])
        drifted = capture("drifted", activation, activation + module.BENCHMARK_WINDOW_MS - 1, [4, 0])
        regressed = capture("regressed", activation, activation + module.BENCHMARK_WINDOW_MS - 1, [6])
        connection.commit()
        connection.close()
        os.chmod(ledger, 0o600)
        lock = reviews / ".lock"
        lock.touch(mode=0o600)
        os.chmod(lock, 0o600)

        evaluated_now = int(time.time() * 1000)
        common = (
            "--state-root", str(state), "--definition-version", "tool-errors-v1",
            "--metric", "tool_error_count", "--direction", "lower",
            "--baseline-capture-id", baseline["capture_id"],
            "--observation-capture-id", observation["capture_id"],
            "--merge-identity", "a" * 40, "--merged-at", str(evaluated_now - 1000),
            "--activation-status", "missing", "--evaluated-at", str(evaluated_now),
        )
        saved = json.loads(run(self.repo, "benchmark-save", *common).stdout)
        self.assertEqual(saved["result"]["classification"], "insufficient")
        self.assertEqual(saved["result"]["reason"], "activation_missing")
        self.assertTrue(saved["result"]["association_only"])
        self.assertEqual(json.loads(run(self.repo, "benchmark-save", *common).stdout), saved)
        replay = json.loads(run(self.repo, "benchmark", "--state-root", str(state),
                                "--benchmark-id", saved["benchmark_id"]).stdout)
        self.assertEqual(replay, saved)
        protected = run(self.repo, "history-capture-delete", "--state-root", str(state),
                        "--capture-id", baseline["capture_id"], ok=False)
        self.assertIn("FOREIGN KEY constraint failed", protected.stderr)

        future = list(common)
        future[future.index("--evaluated-at") + 1] = str(evaluated_now + 60_000)
        invalid = run(self.repo, "benchmark-save", *future, ok=False)
        self.assertIn("cannot be in the future", invalid.stderr)

        immutable = run(self.repo, "benchmark-save", *(common[:7] + ("higher",) + common[8:]), ok=False)
        self.assertIn("definition version is immutable", immutable.stderr)
        changed_merge = list(common)
        changed_merge[changed_merge.index("--merged-at") + 1] = str(evaluated_now - 2000)
        self.assertIn("merge identity is immutable",
                      run(self.repo, "benchmark-save", *changed_merge, ok=False).stderr)
        ambiguous = json.loads(run(
            self.repo, "benchmark-save", "--state-root", str(state),
            "--definition-version", "tool-errors-v2", "--metric", "tool_error_count",
            "--direction", "lower", "--baseline-capture-id", baseline["capture_id"],
            "--observation-capture-id", observation["capture_id"], "--merge-identity", "b" * 40,
            "--merged-at", str(evaluated_now - 1000), "--activation-status", "ambiguous",
            "--evaluated-at", str(evaluated_now),
        ).stdout)
        self.assertEqual(ambiguous["result"]["classification"], "insufficient")
        self.assertEqual(ambiguous["result"]["reason"], "activation_ambiguous")

        verified = (
            "--state-root", str(state), "--definition-version", "tool-errors-v3",
            "--metric", "tool_error_count", "--direction", "lower",
            "--baseline-capture-id", baseline["capture_id"],
            "--observation-capture-id", observation["capture_id"],
            "--merge-identity", "c" * 40, "--merged-at", str(evaluated_now - 1000),
            "--activation-status", "verified", "--activation-identity", "deploy-first",
            "--activated-at", str(evaluated_now - 500), "--evaluated-at", str(evaluated_now),
        )
        run(self.repo, "benchmark-save", *verified)
        changed_activation = list(verified)
        changed_activation[changed_activation.index("--activation-identity") + 1] = "deploy-second"
        self.assertIn("first verified activation is immutable",
                      run(self.repo, "benchmark-save", *changed_activation, ok=False).stderr)

        args = SimpleNamespace(definition_version="tool-errors-v4", metric="tool_error_count",
                               direction="lower", merge_identity="c" * 40,
                               merged_at=activation - 1000, activation_status="verified",
                               activation_identity="deploy-2", activated_at=activation,
                               evaluated_at=evaluated, confounder=["overlapping_change"])
        self.assertEqual(module.benchmark_report(args, baseline, observation)["result"]["classification"],
                         "improved")
        drift = module.benchmark_report(args, baseline, drifted)
        self.assertEqual(drift["result"]["classification"], "neutral")
        self.assertEqual(drift["result"]["confounders"], ["overlapping_change", "population_drift"])
        self.assertEqual(module.benchmark_report(args, baseline, regressed)["result"]["classification"],
                         "regressed")
        mismatch = module.benchmark_report(args, {**baseline, "query": {**baseline["query"], "after": activation}}, observation)
        self.assertEqual(mismatch["result"]["reason"], "window_mismatch")
        self.assertEqual(mismatch["result"]["classification"], "insufficient")
        incomplete_args = SimpleNamespace(**{**vars(args), "evaluated_at": evaluated - 1})
        self.assertEqual(module.benchmark_report(incomplete_args, baseline, observation)["result"]["reason"],
                         "window_incomplete")
        ambiguous_args = SimpleNamespace(**{**vars(args), "activation_status": "ambiguous",
                                             "activation_identity": None, "activated_at": None})
        self.assertEqual(module.benchmark_report(ambiguous_args, baseline, observation)["result"]["reason"],
                         "activation_ambiguous")
        unavailable_args = SimpleNamespace(**{**vars(args), "definition_version": "approvals-v1",
                                               "metric": "approval_count"})
        self.assertEqual(module.benchmark_report(unavailable_args, baseline, observation)["result"]["reason"],
                         "metric_unavailable")

        backup = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        connection = sqlite3.connect(ledger)
        connection.execute("delete from benchmark_effects where benchmark_id=?", (saved["benchmark_id"],))
        connection.commit()
        connection.close()
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        restored = json.loads(run(self.repo, "benchmark", "--state-root", str(state),
                                  "--benchmark-id", saved["benchmark_id"]).stdout)
        self.assertEqual(restored, saved)

        connection = sqlite3.connect(ledger)
        payload = json.loads(connection.execute(
            "select payload from benchmark_effects where benchmark_id=?", (saved["benchmark_id"],)).fetchone()[0])
        payload["result"]["classification"] = "neutral"
        connection.execute("update benchmark_effects set payload=? where benchmark_id=?",
                           (json.dumps(payload), saved["benchmark_id"]))
        connection.commit()
        connection.close()
        malformed = run(self.repo, "benchmark", "--state-root", str(state),
                        "--benchmark-id", saved["benchmark_id"], ok=False)
        self.assertIn("invalid result", malformed.stderr)

    def test_phase_spans_are_private_bounded_and_report_partial_truthfully(self):
        self.start()
        state = Path(self.temp.name) / "phase-state"
        unavailable = json.loads(run(
            self.repo, "phase-report", "--state-root", str(state),
        ).stdout)
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertFalse(state.exists())

        reviews = state / "reviews"
        reviews.mkdir(parents=True)
        with (reviews / ".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            invalid = subprocess.run(
                [sys.executable, str(SCRIPT), "phase-span", "--state-root", str(state),
                 "--span-id", "invalid", "--event", "start", "--phase", "domain",
                 "--operation", "read"],
                cwd=self.repo, text=True, capture_output=True, env=isolated_env(), timeout=1,
            )
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("phase span start requires phase, operation, and attribution only", invalid.stderr)

        common = (
            "--state-root", str(state), "--span-id", "read-a",
            "--phase", "domain", "--operation", "read",
            "--attribution", "explicit", "--path", "docs/specs/a.md",
        )
        partial = json.loads(run(self.repo, "phase-span", *common, "--event", "start").stdout)
        self.assertEqual(partial["status"], "partial")
        self.assertNotIn("docs/specs/a.md", json.dumps(partial))
        self.assertEqual(json.loads(run(
            self.repo, "phase-span", *common, "--event", "start",
        ).stdout), partial)
        self.assertIn("dependency is incomplete", run(
            self.repo, "phase-span", "--state-root", str(state), "--span-id", "too-early",
            "--phase", "behavior", "--operation", "read", "--attribution", "explicit",
            "--dependency", "read-a", "--path", "docs/early", "--event", "start", ok=False,
        ).stderr)
        self.assertIn("parent is missing", run(
            self.repo, "phase-span", "--state-root", str(state), "--span-id", "orphan",
            "--parent-span-id", "missing", "--phase", "behavior", "--operation", "read",
            "--attribution", "explicit", "--path", "docs/orphan", "--event", "start", ok=False,
        ).stderr)
        time.sleep(0.002)
        complete = json.loads(run(
            self.repo, "phase-span", "--state-root", str(state), "--span-id", "read-a",
            "--event", "finish", "--result", "passed",
        ).stdout)
        self.assertEqual(complete["status"], "complete")
        self.assertGreaterEqual(complete["total_wall_ms"], 1)
        self.assertEqual(complete["critical_path_ms"], complete["total_wall_ms"])
        self.assertEqual(complete["repeated_work"], 0)
        self.assertEqual(json.loads(self.record_path().read_text())["phase_profile"], complete)
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_phase_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.assertEqual(module.correlated_cycles(str(self.repo), {"cycle-1"})[0]["phase_profile"],
                         complete)
        self.assertEqual(json.loads(run(
            self.repo, "phase-span", "--state-root", str(state), "--span-id", "read-a",
            "--event", "finish", "--result", "passed",
        ).stdout), complete)
        time.sleep(0.002)
        run(self.repo, "phase-span", "--state-root", str(state), "--span-id", "read-b",
            "--phase", "behavior", "--operation", "read", "--attribution", "explicit",
            "--dependency", "read-a", "--path", "docs/specs/b.md", "--event", "start")
        time.sleep(0.002)
        chain = json.loads(run(
            self.repo, "phase-span", "--state-root", str(state), "--span-id", "read-b",
            "--event", "finish", "--result", "passed",
        ).stdout)
        self.assertEqual(chain["critical_path_ms"], chain["total_wall_ms"])

        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        stored = connection.execute(
            "select ownership_paths from phase_spans where span_id='read-a'"
        ).fetchone()[0]
        self.assertEqual(json.loads(stored), ["docs/specs/a.md"])
        connection.close()
        self.assertNotRegex(json.dumps(complete), r"(?:/Users|docs/specs/a\.md)")

        for index, unsafe in enumerate(("/Users/private/file", "../outside", ".",
                                        "https:/host/token", "password=secret", "bad\npath")):
            rejected = run(
                self.repo, "phase-span", "--state-root", str(state),
                "--span-id", f"unsafe-{index}", "--phase", "domain",
                "--operation", "read", "--attribution", "explicit",
                "--path", unsafe, "--event", "start", ok=False,
            )
            self.assertIn("invalid phase ownership path", rejected.stderr)

        connection = sqlite3.connect(ledger)
        connection.execute("update phase_spans set started_at=?, finished_at=?",
                           (module.REVIEW_START_MS, module.REVIEW_START_MS))
        connection.commit()
        connection.close()
        module.REVIEW_RETENTION_SECONDS = -1
        self.assertEqual(module.prune_phase_spans(state), 2)
        self.assertEqual(json.loads(run(
            self.repo, "phase-report", "--state-root", str(state),
        ).stdout)["status"], "unavailable")

    def test_cycle_performance_separates_autonomous_calendar_and_incomplete_timing(self):
        self.start()
        state = Path(self.temp.name) / "performance-state"
        run(self.repo, "phase-span", "--state-root", str(state), "--span-id", "seed",
            "--phase", "domain", "--operation", "operator_wait", "--attribution", "explicit",
            "--event", "start")
        run(self.repo, "phase-span", "--state-root", str(state), "--span-id", "seed",
            "--event", "finish", "--result", "passed")

        records = self.record_path().parent
        template = json.loads(self.record_path().read_text())
        linked = Path(self.temp.name) / "linked"
        subprocess.run(["git", "worktree", "add", "-b", "linked", str(linked)], cwd=self.repo,
                       check=True, capture_output=True)
        linked_git = Path(subprocess.run(
            ["git", "rev-parse", "--git-dir"], cwd=linked, check=True, text=True,
            capture_output=True,
        ).stdout.strip())
        for index in range(1, 7):
            record = {**template, "cycle_id": f"cycle-{index}", "state": "completed",
                      "created_at": "2026-08-29T00:00:00Z",
                      "completed_at": f"2026-08-29T00:{index // 6:02d}:{index * 10 % 60:02d}Z",
                      "context": "test" if index < 4 else "other" if index == 4 else "legacy",
                      "method_revision": "3.28", "metrics": {
                          "gate_failure_count": index,
                          "gate_reopen_count": index + 1,
                          "remediation_round_count": index + 2,
                      }}
            directory = records if index < 5 else records.parent if index == 5 else linked_git / "dbsctr"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"cycle-{index}.json").write_text(json.dumps(record))
        duplicate = records.parent / "cycle-1.json"
        duplicate.write_bytes((records / "cycle-1.json").read_bytes())

        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        connection.execute("delete from phase_spans")
        base = int(time.time() * 1000) - 10000
        rows = (
            ("cycle-1", "active", None, "domain", "task", "explicit", "[]", "[]",
             base, base + 1000, "passed"),
            ("cycle-1", "nested", "active", "behavior", "read", "explicit", "[]", "[]",
             base + 200, base + 800, "passed"),
            ("cycle-1", "pause", None, "contract", "operator_wait", "explicit", "[]", "[]",
             base + 1200, base + 1400, "passed"),
            ("cycle-2", "active", None, "domain", "task", "explicit", "[]", "[]",
             base, base + 2000, "passed"),
            ("cycle-2", "pause", None, "contract", "external_wait", "explicit", "[]", "[]",
             base + 1500, base + 1600, "passed"),
            ("cycle-3", "active", None, "domain", "task", "explicit", "[]", "[]",
             base, None, None),
        )
        connection.executemany("insert into phase_spans values (?,?,?,?,?,?,?,?,?,?,?)", rows)
        connection.commit()
        connection.close()
        before_ledger = ledger.read_bytes()
        record_paths = list(records.parent.glob("**/*.json")) + list((linked_git / "dbsctr").glob("*.json"))
        before_records = {path: path.read_bytes() for path in record_paths}

        report = json.loads(run(
            self.repo, "cycle-performance", "--state-root", str(state), "--json",
        ).stdout)
        self.assertEqual(report, {
            "schema_version": 1, "filters": {},
            "counts": {"completed": 6, "complete": 1, "partial": 2, "unavailable": 3},
            "coverage_basis_points": 1666,
            "autonomous_runtime_ms": {"mean": 1000, "p50": 1000, "p90": 1000},
            "calendar_elapsed_ms": {"mean": 35000, "p50": 30000, "p90": 60000},
            "quality": {"gate_failures": 21, "gate_reopenings": 27,
                        "remediation_rounds": 33},
        })
        self.assertNotRegex(json.dumps(report), r"(?:cycle-[1-6]|/Users|span|ownership)")
        self.assertEqual(ledger.read_bytes(), before_ledger)
        self.assertEqual({path: path.read_bytes() for path in record_paths}, before_records)

        filtered = json.loads(run(
            self.repo, "cycle-performance", "--state-root", str(state), "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--method-revision", "3.28",
            "--json",
        ).stdout)
        self.assertEqual(filtered["filters"], {
            "context": "test", "risk": "routine", "delivery_intent": "local",
            "method_revision": "3.28",
        })
        self.assertEqual(filtered["counts"]["completed"], 3)
        self.assertEqual(filtered["calendar_elapsed_ms"], {
            "mean": 20000, "p50": 20000, "p90": 30000,
        })

        empty = Path(self.temp.name) / "no-performance-state"
        unavailable = json.loads(run(
            self.repo, "cycle-performance", "--state-root", str(empty), "--context", "missing",
            "--json",
        ).stdout)
        self.assertEqual(unavailable["counts"]["completed"], 0)
        self.assertEqual(unavailable["autonomous_runtime_ms"]["mean"], "unavailable")
        self.assertFalse(empty.exists())
        self.assertIn("invalid context", run(
            self.repo, "cycle-performance", "--context", "../private", "--json", ok=False,
        ).stderr)
        conflicting = json.loads(duplicate.read_text())
        conflicting["risk"] = "elevated"
        duplicate.write_text(json.dumps(conflicting))
        self.assertIn("identity is ambiguous", run(
            self.repo, "cycle-performance", "--state-root", str(state), "--json", ok=False,
        ).stderr)

    def test_execution_dag_authorizes_only_proven_independent_work(self):
        safe = {"nodes": [
            {"id": "read-a", "depends_on": [], "operation": "read",
             "ownership_paths": ["docs/a"]},
            {"id": "qa-b", "depends_on": [], "operation": "readonly_qa",
             "ownership_paths": ["tests/b"]},
            {"id": "read-c", "depends_on": ["read-a"], "operation": "read",
             "ownership_paths": ["docs/a/child"]},
            {"id": "reconcile", "depends_on": ["qa-b", "read-c"], "operation": "reconcile",
             "ownership_paths": []},
        ], "completed": []}
        required_gates = sorted(("domain", "behavior", "spec", "contract",
                                 "test_driven_implementation", "refactor", "review_integrate"))
        fixture_dag = {"nodes": [
            {"id": "fixture-a", "depends_on": [], "operation": "read",
             "ownership_paths": ["tracked.txt"]},
            {"id": "fixture-b", "depends_on": [], "operation": "read",
             "ownership_paths": ["docs/specs/test/README.md"]},
            {"id": "fixture-c", "depends_on": ["fixture-a"], "operation": "read",
             "ownership_paths": ["docs/specs/test/BACKLOG.md"]},
            {"id": "fixture-reconcile", "depends_on": ["fixture-b", "fixture-c"],
             "operation": "reconcile", "ownership_paths": []},
        ], "completed": []}
        fixture_value = {"schema_version": 1, "fixture_id": "test-read-v1", "warmup_pairs": 1,
                         "measured_pairs": 5, "synthetic_delay_ms": 200,
                         "required_gates": required_gates, "dag": fixture_dag}
        fixture_path = self.repo / "tests/fixtures/execution.json"
        fixture_path.parent.mkdir(parents=True)
        fixture_path.write_text(json.dumps(fixture_value))
        subprocess.run(["git", "add", "tests/fixtures/execution.json"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=self.repo, check=True,
                       capture_output=True)
        fixture_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo,
                                        text=True, capture_output=True, check=True).stdout.strip()
        fixture_blob = subprocess.run(
            ["git", "rev-parse", f"{fixture_commit}:tests/fixtures/execution.json"], cwd=self.repo,
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        fixture = {"id": "test-read-v1", "commit": fixture_commit,
                   "path": "tests/fixtures/execution.json", "blob": fixture_blob}

        self.start()
        blocked = json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)
        self.assertEqual(blocked["mode"], "serial")
        self.assertEqual(blocked["reasons"], ["benchmark_not_qualified"])
        experiment = json.loads(run(
            self.repo, "execution-dag", "--mode", "benchmark",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)
        self.assertEqual(experiment["mode"], "concurrent")
        self.assertEqual(experiment["reasons"], ["benchmark_only"])
        benchmark = json.loads(run(
            self.repo, "execution-benchmark", "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--fixture-id", fixture["id"], "--fixture-commit", fixture["commit"],
            "--fixture-path", fixture["path"], "--fixture-blob", fixture["blob"],
        ).stdout)
        self.assertTrue(benchmark["activated"])
        self.assertGreaterEqual(benchmark["improvement_percent"], 10)
        concurrent = json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)
        self.assertEqual(concurrent, {
            "schema_version": 1, "requested_mode": "concurrent", "mode": "concurrent",
            "order": ["qa-b", "read-a", "read-c", "reconcile"], "ready": ["qa-b", "read-a"],
            "forced_serial": [], "reconciliation_id": "reconcile", "reasons": [],
        })
        reconciler = {**safe, "completed": ["qa-b", "read-a", "read-c"]}
        self.assertEqual(json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(reconciler),
        ).stdout)["ready"], ["reconcile"])
        backup = json.loads(run(
            self.repo, "review-backup", "--state-root", str(Path(self.temp.name) / "dag-state"),
        ).stdout)
        connection = sqlite3.connect(Path(self.temp.name) / "dag-state/reviews/ledger.sqlite3")
        connection.execute("delete from execution_activation")
        connection.commit()
        connection.close()
        self.assertEqual(json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)["mode"], "serial")
        run(self.repo, "review-restore", "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--backup", backup["backup"])
        self.assertEqual(json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)["mode"], "concurrent")

        overlap = {"nodes": safe["nodes"][:2] + [{
            "id": "read-b", "depends_on": [], "operation": "read",
            "ownership_paths": ["docs/a/file"],
        }, {"id": "reconcile", "depends_on": ["qa-b", "read-a", "read-b"],
            "operation": "reconcile", "ownership_paths": []}], "completed": []}
        serial = json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(overlap),
        ).stdout)
        self.assertEqual(serial["mode"], "serial")
        self.assertEqual(serial["forced_serial"], ["read-a", "read-b"])
        self.assertEqual(serial["reasons"], ["ownership_overlap"])

        for invalid, message in (
            ({"nodes": [{"id": "a", "depends_on": ["missing"], "operation": "read",
                          "ownership_paths": ["a"]}, {"id": "reconcile", "depends_on": ["a"],
                          "operation": "reconcile", "ownership_paths": []}], "completed": []},
             "unknown dependency"),
            ({"nodes": [{"id": "a", "depends_on": ["b"], "operation": "read",
                          "ownership_paths": ["a"]},
                         {"id": "b", "depends_on": ["a"], "operation": "read",
                          "ownership_paths": ["b"]},
                         {"id": "reconcile", "depends_on": ["a"], "operation": "reconcile",
                          "ownership_paths": []}], "completed": []}, "cycle"),
            ({"nodes": [{"id": "a", "depends_on": [], "operation": "write",
                          "ownership_paths": ["a"]},
                         {"id": "reconcile", "depends_on": ["a"], "operation": "reconcile",
                          "ownership_paths": []}], "completed": []}, "operation"),
            ({**safe, "completed": ["read-c"]}, "completed dependencies"),
            ({**safe, "completed": ["reconcile"]}, "completed dependencies"),
        ):
            rejected = run(self.repo, "execution-dag", "--mode", "concurrent",
                           "--state-root", str(Path(self.temp.name) / "dag-state"),
                           "--dag-json", json.dumps(invalid), ok=False)
            self.assertIn(message, rejected.stderr)

        record = json.loads(self.record_path().read_text())
        record["risk"] = "critical"
        self.record_path().write_text(json.dumps(record))
        critical = json.loads(run(
            self.repo, "execution-dag", "--mode", "concurrent",
            "--state-root", str(Path(self.temp.name) / "dag-state"),
            "--dag-json", json.dumps(safe),
        ).stdout)
        self.assertEqual(critical["mode"], "serial")
        self.assertEqual(critical["forced_serial"], ["qa-b", "read-a", "read-c"])
        self.assertEqual(critical["reasons"], ["critical_risk"])

    def test_history_capture_saves_complete_snapshot_and_replays_bounded(self):
        database = Path(self.temp.name) / "history-capture.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        for index in range(201):
            timestamp = 1784073600000 + index
            connection.execute("insert into session values (?, null, 'DBSCTR', ?)",
                               (f"session-{index:03}", timestamp))
            connection.execute("insert into message values (?, ?, ?, '{}')",
                               (f"message-{index:03}", f"session-{index:03}", timestamp))
            connection.execute("insert into part values (?, ?, ?, ?, ?, 'DBSCTR')",
                               (f"part-{index:03}", f"message-{index:03}",
                                f"session-{index:03}", timestamp, timestamp))
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-capture-state"

        started = time.monotonic()
        saved = json.loads(run(
            self.repo, "history-capture-save", "--database", str(database),
            "--state-root", str(state), "--page-size", "100",
        ).stdout)
        self.assertLess(time.monotonic() - started, 30)
        self.assertRegex(saved["capture_id"], r"^[0-9a-f]{24}$")
        self.assertEqual(saved["member_count"], 201)
        self.assertEqual(saved["page_count"], 3)
        self.assertEqual(saved["aggregates"]["candidate_count"], 201)

        lens = json.loads(run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], "--lens-summary", "performance_cost",
            "--review-sessions", "exclude",
        ).stdout)
        self.assertEqual(lens["member_count"], 201)
        self.assertEqual(lens["telemetry"], {
            "page_count": 3, "session_count": 201, "review_session_count": 0,
            "excluded_review_session_count": 0, "unattributed_session_count": 0,
        })
        self.assertLessEqual(len(lens["evidence"]), 20)
        self.assertRegex(lens["members_digest"], r"^[0-9a-f]{64}$")

        loader = importlib.machinery.SourceFileLoader("dbsctrctl_lens_summary", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        capture_db = sqlite3.connect(state / "reviews/ledger.sqlite3")
        manifest = json.loads(capture_db.execute(
            "select payload from history_captures where capture_id=?", (saved["capture_id"],)).fetchone()[0])
        members = [json.loads(row[0]) for row in capture_db.execute(
            "select payload from history_capture_members where capture_id=? order by position", (saved["capture_id"],))]
        capture_db.close()
        members[0]["review_session"] = True
        ordinary = module.history_lens_summary(manifest, members, "performance_cost", "exclude")
        review = module.history_lens_summary(manifest, members, "review_session_governance", "only")
        self.assertEqual((ordinary["member_count"], ordinary["telemetry"]["session_count"]), (200, 200))
        self.assertEqual((review["member_count"], review["telemetry"]["session_count"]), (1, 1))
        self.assertNotEqual(ordinary["members_digest"], review["members_digest"])

        transient = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "25", "--capture",
        ).stdout)
        started = time.monotonic()
        latest = json.loads(run(
            self.repo, "history-capture-latest", "--database", str(database),
            "--state-root", str(state), "--page-size", "25",
        ).stdout)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(latest["capture_id"], transient["capture_id"])
        self.assertEqual((latest["page_size"], latest["member_count"]), (25, 201))
        reused = json.loads(run(
            self.repo, "history-capture-latest", "--database", str(database),
            "--state-root", str(state), "--page-size", "50",
        ).stdout)
        self.assertEqual((reused["capture_id"], reused["page_size"]), (transient["capture_id"], 25))

        capture_db = sqlite3.connect(state / "reviews/ledger.sqlite3")
        future = json.loads(capture_db.execute(
            "select payload from history_captures where capture_id=?", (transient["capture_id"],)).fetchone()[0])
        future["created_at"] = int(time.time() * 1000) + 10 * 60 * 1000
        future.pop("capture_id")
        future_id = hashlib.sha256(module.ledger_payload(future).encode()).hexdigest()[:24]
        future["capture_id"] = future_id
        capture_db.execute("insert into history_captures values (?, ?)",
                           (future_id, module.ledger_payload(future)))
        capture_db.execute(
            "insert into history_capture_members select ?,position,session_id,payload "
            "from history_capture_members where capture_id=?", (future_id, transient["capture_id"]))
        capture_db.commit()
        capture_db.close()
        bounded = json.loads(run(
            self.repo, "history-capture-latest", "--database", str(database),
            "--state-root", str(state), "--page-size", "25",
        ).stdout)
        self.assertEqual(bounded["capture_id"], transient["capture_id"])

        archived = json.loads(run(
            self.repo, "history-capture-latest", "--database", str(database),
            "--state-root", str(Path(self.temp.name) / "archive-capture-state"),
            "--page-size", "25", "--archive-only",
        ).stdout)
        self.assertTrue(archived["query"]["archive_only"])

        summary = json.loads(run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"],
        ).stdout)
        self.assertEqual(summary, saved)
        self.assertNotIn("members", summary)
        started = time.monotonic()
        middle = json.loads(run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], "--cursor", "100", "--limit", "100",
        ).stdout)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual([item["session_id"] for item in middle["members"]],
                         [f"session-{index:03}" for index in range(100, 0, -1)])
        self.assertEqual(middle["continuation"], 200)
        last = json.loads(run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], "--cursor", "200", "--limit", "100",
        ).stdout)
        self.assertEqual([item["session_id"] for item in last["members"]], ["session-000"])
        self.assertIsNone(last["continuation"])
        self.assertLess(len(json.dumps(middle).encode()), 256 * 1024)
        self.assertEqual((state / "reviews/ledger.sqlite3").stat().st_mode & 0o777, 0o600)

        backup = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        run(self.repo, "history-capture-delete", "--state-root", str(state),
            "--capture-id", saved["capture_id"])
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        missing_after_restore = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"],
            ok=False)
        self.assertIn("history capture is missing", missing_after_restore.stderr)

    def test_history_capture_rejects_manifest_and_projection_tampering(self):
        database = Path(self.temp.name) / "history-capture-integrity.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
            insert into session values ('session-2', null, 'DBSCTR', 1784073600002);
            insert into session values ('session-1', null, 'DBSCTR', 1784073600001);
            insert into session values ('session-0', null, 'DBSCTR', 1784073600000);
            insert into message values ('message-2', 'session-2', 1784073600002, '{}');
            insert into message values ('message-1', 'session-1', 1784073600001, '{}');
            insert into message values ('message-0', 'session-0', 1784073600000, '{}');
            insert into part values ('part-2', 'message-2', 'session-2', 1784073600002, 1784073600002, 'DBSCTR');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600001, 1784073600001, 'DBSCTR');
            insert into part values ('part-0', 'message-0', 'session-0', 1784073600000, 1784073600000, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-capture-integrity-state"
        saved = json.loads(run(
            self.repo, "history-capture-save", "--database", str(database),
            "--state-root", str(state), "--page-size", "2",
        ).stdout)
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        payload = json.loads(connection.execute(
            "select payload from history_captures where capture_id=?", (saved["capture_id"],)
        ).fetchone()[0])
        original = json.loads(json.dumps(payload))
        payload["aggregates"]["candidate_count"] = 99
        connection.execute("update history_captures set payload=? where capture_id=?",
                           (json.dumps(payload, sort_keys=True, separators=(",", ":")), saved["capture_id"]))
        connection.commit()
        connection.close()
        mismatched = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("aggregate projection mismatch", mismatched.stderr)

        connection = sqlite3.connect(ledger)
        payload = json.loads(json.dumps(original))
        payload["pages"][1]["cursor"] = 3
        connection.execute("update history_captures set payload=? where capture_id=?",
                           (json.dumps(payload, sort_keys=True, separators=(",", ":")), saved["capture_id"]))
        connection.commit()
        connection.close()
        gap = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("page coverage", gap.stderr)

        connection = sqlite3.connect(ledger)
        payload = json.loads(json.dumps(original))
        payload["pages"][0]["count"] = 1
        connection.execute("update history_captures set payload=? where capture_id=?",
                           (json.dumps(payload, sort_keys=True, separators=(",", ":")), saved["capture_id"]))
        connection.commit()
        connection.close()
        short = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("page coverage", short.stderr)

        connection = sqlite3.connect(ledger)
        connection.execute("update history_captures set payload=? where capture_id=?",
                           (json.dumps(original, sort_keys=True, separators=(",", ":")), saved["capture_id"]))
        connection.execute("update history_capture_members set session_id='other-session' "
                           "where capture_id=? and position=0", (saved["capture_id"],))
        connection.commit()
        connection.close()
        columns = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("member columns mismatch", columns.stderr)
        forgotten = run(
            self.repo, "review-forget", "--state-root", str(state), "--session-id", "session-2", ok=False,
        )
        self.assertIn("member columns mismatch", forgotten.stderr)

        connection = sqlite3.connect(ledger)
        connection.execute("update history_capture_members set session_id='session-2' "
                           "where capture_id=? and position=0", (saved["capture_id"],))
        connection.execute("update history_capture_members set position=5 "
                           "where capture_id=? and position=0", (saved["capture_id"],))
        connection.commit()
        connection.close()
        position = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("member columns mismatch", position.stderr)

        connection = sqlite3.connect(ledger)
        connection.execute("update history_capture_members set position=0 "
                           "where capture_id=? and position=5", (saved["capture_id"],))
        connection.commit()
        connection.close()
        privacy_before = json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state)).stdout)
        run(self.repo, "review-forget", "--state-root", str(state), "--session-id", "session-2")
        privacy_after = json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state)).stdout)
        self.assertGreater(privacy_after["privacy_sequence"], privacy_before["privacy_sequence"])
        self.assertNotEqual(privacy_after["privacy_digest"], privacy_before["privacy_digest"])
        missing = run(
            self.repo, "history-capture", "--state-root", str(state),
            "--capture-id", saved["capture_id"], ok=False,
        )
        self.assertIn("capture is missing", missing.stderr)

    def test_review_history_capture_supports_empty_immutable_pages(self):
        database = Path(self.temp.name) / "empty-history.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        connection.close()
        state = Path(self.temp.name) / "empty-history-state"
        rejected = run(
            self.repo, "history-capture-save", "--database", str(database),
            "--state-root", str(state), "--page-size", "5", ok=False,
        )
        self.assertIn("selected no evidence", rejected.stderr)
        first = json.loads(run(
            self.repo, "review-history", "--database", str(database),
            "--state-root", str(state), "--limit", "5", "--cursor", "0", "--capture",
        ).stdout)
        self.assertRegex(first["capture_id"], r"^[0-9a-f]{24}$")
        self.assertEqual(first["candidates"], [])
        self.assertIsNone(first["continuation"])
        ledger = sqlite3.connect(state / "reviews/ledger.sqlite3")
        manifest = json.loads(ledger.execute(
            "select payload from history_captures where capture_id=?", (first["capture_id"],)).fetchone()[0])
        ledger.close()
        self.assertEqual(manifest["kind"], "federated")
        self.assertGreaterEqual(manifest["created_at"], 1783814400000)
        replay = json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--limit", "5", "--cursor", "0",
            "--capture-id", first["capture_id"],
        ).stdout)
        self.assertEqual(replay, first)

    def test_review_history_continuation_does_not_rescan_live_database(self):
        database = Path(self.temp.name) / "captured-history.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
        """)
        for index in range(3):
            timestamp = 1784073600000 + index
            connection.execute("insert into session values (?, null, 'DBSCTR', ?)", (f"session-{index}", timestamp))
            connection.execute("insert into message values (?, ?, ?, '{}')",
                               (f"message-{index}", f"session-{index}", timestamp))
            connection.execute("insert into part values (?, ?, ?, ?, ?, 'DBSCTR')",
                               (f"part-{index}", f"message-{index}", f"session-{index}", timestamp, timestamp))
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "captured-history-state"
        first = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "2", "--cursor", "0", "--capture",
        ).stdout)
        self.assertEqual(first["session_ids"], ["session-2", "session-1"])
        connection = sqlite3.connect(database)
        connection.executescript("delete from part; delete from message; delete from session;")
        connection.commit()
        connection.close()
        second = json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--limit", "2", "--cursor", "2",
            "--capture-id", first["capture_id"],
        ).stdout)
        self.assertEqual(second["session_ids"], ["session-0"])
        self.assertEqual(second["database_digest"], first["database_digest"])
        self.assertIsNone(second["continuation"])

    def test_federated_capture_pruning_preserves_current_and_benchmark_evidence(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_capture_prune_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        connection = sqlite3.connect(":memory:")
        connection.executescript("""
            create table history_captures (capture_id text primary key, payload text not null);
            create table benchmark_effects (baseline_capture_id text not null, observation_capture_id text not null);
        """)
        now = module.REVIEW_START_MS + module.FEDERATED_CAPTURE_RETENTION_MS * 2
        old = now - module.FEDERATED_CAPTURE_RETENTION_MS - 1
        for capture_id, created_at in (("expired", old), ("referenced", old), ("current", now)):
            connection.execute("insert into history_captures values (?, ?)", (
                capture_id, json.dumps({"kind": "federated", "created_at": created_at}),
            ))
        connection.execute("insert into benchmark_effects values ('referenced', 'referenced')")
        module.prune_federated_captures(connection, now)
        self.assertEqual(
            {row[0] for row in connection.execute("select capture_id from history_captures")},
            {"referenced", "current"},
        )
        connection.close()

    def test_history_capture_uses_one_read_under_the_write_lock(self):
        database = Path(self.temp.name) / "history-capture-lock.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer,
                               time_updated integer, data text);
            insert into session values ('session-1', null, 'DBSCTR', 1784073600001);
            insert into message values ('message-1', 'session-1', 1784073600001, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600001, 1784073600001, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-capture-lock-state"
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_capture_lock_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        original_lock = module.review_lock
        original_page = module.review_history_page
        active = False
        calls = 0

        @contextlib.contextmanager
        def tracked_lock(root):
            nonlocal active
            with original_lock(root) as handle:
                active = True
                try:
                    yield handle
                finally:
                    active = False

        def tracked_page(args, lock_held=False):
            nonlocal calls
            self.assertTrue(active)
            self.assertTrue(lock_held)
            calls += 1
            return original_page(args, lock_held=lock_held)

        args = SimpleNamespace(
            database=str(database), state_root=str(state), page_size=100, after=None, before=None,
            method_revision=None, cycle_id=None, state=None, context=None, project_digest=None,
            reviewed_status=None, excluded_session_id=None, excluded_message_id=None,
        )
        with mock.patch.object(module, "review_lock", tracked_lock), \
                mock.patch.object(module, "review_history_page", tracked_page), \
                mock.patch("builtins.print"):
            module.command_history_capture_save(args)
        self.assertEqual(calls, 1)

    def test_review_history_filters_archives_replays_and_forgets_closed(self):
        state = Path(self.temp.name) / "history-private"
        history = state / "reviews/history"
        history.mkdir(parents=True)
        raw = "secret prose /Users/private https://unsafe.invalid"
        evidence = {
            "schema_version": 1, "session_id": "session-1", "completed_at": "1784073600001",
            "method_revision": "3.16", "context": "test", "project_digest": "a" * 64,
            "cycles": [{"cycle_id": "cycle-1", "state": "completed"}],
            "aggregates": {"tool_count": 2, "retry_count": 0},
        }
        (history / "session-1.json").write_text(json.dumps(evidence))
        (state / "reviews/.lock").touch()
        report = {
            "schema_version": 1, "cohort": ["session-1"], "query_digest": "b" * 64,
            "rubric": {"name": "baseline", "version": "1", "digest": "c" * 64},
            "findings": ["sanitized"],
        }
        self.assertFalse((state / "reviews/reviewed.json").exists())
        run(self.repo, "review-migrate", "--state-root", str(state))
        saved = json.loads(run(
            self.repo, "review-history-save", "--state-root", str(state), "--report-json", json.dumps(report)
        ).stdout)
        self.assertFalse((state / "reviews/reviewed.json").exists())
        result = json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--after", "1784073600000",
            "--before", "1784073600002", "--method-revision", "3.16", "--cycle-id", "cycle-1",
            "--state", "completed", "--context", "test", "--project-digest", "a" * 64,
            "--reviewed-status", "reviewed", "--replay", saved["report_id"],
        ).stdout)
        self.assertEqual(result["session_ids"], ["session-1"])
        serialized = json.dumps(result)
        self.assertNotIn(raw, serialized)
        self.assertNotRegex(serialized, r"(?:/Users|https?://)")
        (history / "session-1.json").unlink()
        self.assertEqual(json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--replay", saved["report_id"]
        ).stdout)["session_ids"], ["session-1"])
        run(self.repo, "review-forget", "--state-root", str(state), "--session-id", "session-1")
        self.assertFalse((history / "session-1.json").exists())
        self.assertFalse((state / "reviews/backups").exists())
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        self.assertEqual(connection.execute("SELECT count(*) FROM history_reports").fetchone()[0], 0)
        connection.close()
        (history / "cohorts").mkdir(exist_ok=True)
        (history / "cohorts/bad.json").write_text("not-json")
        self.assertEqual(json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--archive-only"
        ).stdout)["session_ids"], [])

    def test_review_history_save_rejects_before_private_state_mutation(self):
        state = Path(self.temp.name) / "invalid-history-save"
        report = {"schema_version": 1, "cohort": ["session-1"], "query_digest": "b" * 64,
                  "findings": ["sanitized"]}
        result = run(self.repo, "review-history-save", "--state-root", str(state),
                     "--report-json", json.dumps(report), ok=False)
        self.assertIn("invalid schema", result.stderr)
        self.assertFalse(state.exists())
        report.update({
            "rubric": {"name": "history", "version": "1", "digest": "c" * 64},
            "snapshot": 1784073600000, "session_ceiling": 1, "part_ceiling": 1,
            "database_digest": "d" * 64, "limit": 1,
        })
        result = run(self.repo, "review-history-save", "--state-root", str(state),
                     "--report-json", json.dumps(report), ok=False)
        self.assertIn("incomplete page identity", result.stderr)
        self.assertFalse(state.exists())

    def test_review_history_snapshot_binds_cycle_identity(self):
        self.start()
        database = Path(self.temp.name) / "history-cycle.db"
        connection = __import__("sqlite3").connect(database)
        connection.executescript(f"""
            create table session (id text primary key, parent_id text, directory text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-cycle', null, {json.dumps(str(self.repo))}, 1784073600000);
            insert into message values ('message-cycle', 'session-cycle', 1784073600000, '{{}}');
            insert into part values ('part-cycle', 'message-cycle', 'session-cycle', 1784073600000, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "history-cycle-state"
        first = json.loads(run(self.repo, "review-history", "--database", str(database),
                               "--state-root", str(state)).stdout)
        self.assertEqual(first["candidates"][0]["method_revision"], "3.29")
        record = json.loads(self.record_path().read_text())
        record["method_revision"] = "3.15"
        self.record_path().write_text(json.dumps(record))
        changed = run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--snapshot", str(first["snapshot"]), "--session-ceiling", str(first["session_ceiling"]),
            "--part-ceiling", str(first["part_ceiling"]), "--database-digest", first["database_digest"],
            ok=False,
        )
        self.assertIn("changed within the review snapshot", changed.stderr)

    def test_review_ledger_migrates_once_and_ignores_legacy_after_cutover(self):
        state = Path(self.temp.name) / "ledger-migration"
        history = state / "reviews/history"
        history.mkdir(parents=True)
        (state / "reviews/.lock").touch()
        evidence = {
            "schema_version": 1, "session_id": "session-1", "completed_at": "1784073600001",
            "method_revision": "3.18", "context": "test", "project_digest": "a" * 64,
            "cycles": [], "aggregates": {}, "reviewed_status": "reviewed",
        }
        (history / "session-1.json").write_text(json.dumps(evidence))
        (state / "reviews/reviewed.json").write_text(json.dumps({
            "schema_version": 1, "sessions": {"session-1": 1784073600001},
            "cycles": {}, "forgotten_sessions": {},
        }))
        operational = {
            "session_ids": ["session-1"], "cycle_ids": [], "scan_digest": "b" * 64,
            "snapshot": 1784073600000, "session_ceiling": 1, "part_ceiling": 1,
            "database_digest": "c" * 64, "limit": 1, "cursor": 0,
            "decision": "reviewed", "reviewed_at": 1784073600001,
        }
        marker = hashlib.sha256((operational["scan_digest"] + "\0" + json.dumps(
            operational, sort_keys=True)).encode()).hexdigest()[:24]
        (state / "reviews" / f"{marker}.json").write_text(json.dumps(operational))
        saved = {
            "schema_version": 1, "cohort": ["session-1"], "evidence": [evidence],
            "query_digest": "d" * 64,
            "rubric": {"name": "migration", "version": "1", "digest": "e" * 64},
            "findings": ["sanitized"],
        }
        saved["report_id"] = hashlib.sha256(json.dumps(
            saved, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
        reports = history / "reports"
        reports.mkdir()
        (reports / f"{saved['report_id']}.json").write_text(json.dumps(saved))

        migrated = json.loads(run(self.repo, "review-migrate", "--state-root", str(state)).stdout)
        self.assertTrue(migrated["migrated"])
        self.assertRegex(migrated["digest"], r"^[0-9a-f]{64}$")
        ledger = state / "reviews/ledger.sqlite3"
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)
        self.assertEqual(ledger.parent.stat().st_mode & 0o777, 0o700)
        backup = state / "reviews/backups" / migrated["backup"]
        self.assertTrue((backup / "history/session-1.json").is_file())
        self.assertEqual((backup / "history/session-1.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((history / "session-1.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(history.stat().st_mode & 0o777, 0o700)
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute("select count(*) from review_reports").fetchone()[0], 1)
        self.assertEqual(connection.execute("select count(*) from history_reports").fetchone()[0], 1)
        self.assertEqual(connection.execute("select count(*) from review_tombstones").fetchone()[0], 1)
        connection.close()
        backup_result = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        backup_path = state / "reviews/backups" / backup_result["backup"]
        semantic = backup_path.with_name("semantic.sqlite3")
        semantic.write_bytes(backup_path.read_bytes())
        os.chmod(semantic, 0o600)
        connection = sqlite3.connect(semantic)
        connection.execute("delete from history_report_members")
        connection.commit()
        connection.close()
        failed = run(self.repo, "review-restore", "--state-root", str(state),
                     "--backup", semantic.name, ok=False)
        self.assertIn("history membership mismatch", failed.stderr)
        repeated = json.loads(run(self.repo, "review-migrate", "--state-root", str(state)).stdout)
        self.assertFalse(repeated["migrated"])
        self.assertEqual(repeated["digest"], migrated["digest"])

        (history / "session-1.json").write_text("not-json")
        archived = json.loads(run(
            self.repo, "review-history", "--state-root", str(state), "--archive-only"
        ).stdout)
        self.assertEqual(archived["session_ids"], ["session-1"])
        os.chmod(ledger, 0o644)
        failed = run(self.repo, "review-history", "--state-root", str(state), "--archive-only", ok=False)
        self.assertIn("review ledger is unsafe", failed.stderr)
        os.chmod(ledger, 0o600)

    def test_review_ledger_migration_rejects_malformed_legacy_without_cutover(self):
        state = Path(self.temp.name) / "ledger-malformed"
        history = state / "reviews/history"
        history.mkdir(parents=True)
        (state / "reviews/.lock").touch()
        (history / "bad.json").write_text("not-json")
        failed = run(self.repo, "review-migrate", "--state-root", str(state), ok=False)
        self.assertIn("cannot read review history evidence", failed.stderr)
        self.assertFalse((state / "reviews/ledger.sqlite3").exists())
        (history / "bad.json").unlink()
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text("{}")
        (history / "linked.json").symlink_to(outside)
        failed = run(self.repo, "review-history", "--state-root", str(state),
                     "--archive-only", ok=False)
        self.assertIn("unsafe", failed.stderr)
        failed = run(self.repo, "review-migrate", "--state-root", str(state), ok=False)
        self.assertIn("unsafe", failed.stderr)
        self.assertFalse((state / "reviews/ledger.sqlite3").exists())

    def test_review_ledger_backup_restore_and_future_schema_fail_closed(self):
        state = Path(self.temp.name) / "ledger-backup"
        run(self.repo, "review-prune", "--state-root", str(state))
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        connection.execute("insert into review_tombstones values ('session', 'session-1', 1784073600001)")
        connection.commit()
        connection.close()
        backup = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        backup_path = state / "reviews/backups" / backup["backup"]
        self.assertEqual(backup_path.stat().st_mode & 0o777, 0o600)

        connection = sqlite3.connect(ledger)
        connection.execute("update review_tombstones set timestamp=1784073600002")
        connection.commit()
        connection.close()
        restored = json.loads(run(
            self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"]
        ).stdout)
        self.assertRegex(restored["rollback"], r"rollback.*\.sqlite3$")
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute("select timestamp from review_tombstones").fetchone()[0], 1784073600001)
        connection.close()
        forgotten_at = 1784073600003
        connection = sqlite3.connect(ledger)
        connection.execute("insert into review_tombstones values ('forgotten_session', 'forgotten-1', ?)",
                           (forgotten_at,))
        connection.execute("insert into knowledge_privacy_tombstones values "
                           "('telemetry', 'forgotten-1', 'forgotten', ?)", (forgotten_at,))
        connection.execute("insert into knowledge_privacy_tombstones values "
                           "('review', 'review-1', 'expired', ?)", (forgotten_at,))
        connection.execute("insert into knowledge_privacy_tombstones values "
                           "('provider_evaluation', 'evaluation-1', 'forgotten', ?)", (forgotten_at,))
        tombstones = [["provider_evaluation", "evaluation-1", "forgotten", forgotten_at],
                      ["review", "review-1", "expired", forgotten_at],
                      ["telemetry", "forgotten-1", "forgotten", forgotten_at]]
        digest = hashlib.sha256(json.dumps(
            {"schema_version": 1, "tombstones": tombstones},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        connection.execute("update ledger_meta set value='3' where key='knowledge_privacy_sequence'")
        connection.execute("update ledger_meta set value=? where key='knowledge_privacy_digest'", (digest,))
        connection.commit()
        connection.close()
        privacy_before_restore = json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state)).stdout)
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute(
            "select timestamp from review_tombstones where kind='forgotten_session'"
        ).fetchone()[0], connection.execute(
            "select timestamp from knowledge_privacy_tombstones "
            "where family='telemetry' and item_id='forgotten-1'"
        ).fetchone()[0])
        self.assertEqual(connection.execute(
            "select count(*) from knowledge_privacy_tombstones").fetchone()[0], 3)
        connection.close()
        self.assertEqual(json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state)).stdout),
            privacy_before_restore)

        future = backup_path.with_name("future.sqlite3")
        future.write_bytes(backup_path.read_bytes())
        os.chmod(future, 0o600)
        connection = sqlite3.connect(future)
        connection.execute("update ledger_meta set value='99' where key='schema_version'")
        connection.commit()
        connection.close()
        failed = run(self.repo, "review-restore", "--state-root", str(state),
                     "--backup", future.name, ok=False)
        self.assertIn("unsupported schema", failed.stderr)
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute(
            "select timestamp from review_tombstones where kind='session'"
        ).fetchone()[0], 1784073600001)
        connection.close()
        backups = state / "reviews/backups"
        real_backups = state / "reviews/backups-real"
        backups.rename(real_backups)
        backups.symlink_to(real_backups, target_is_directory=True)
        failed = run(self.repo, "review-backup", "--state-root", str(state), ok=False)
        self.assertIn("backup directory is unsafe", failed.stderr)
        backups.unlink()
        real_backups.rename(backups)

    def test_review_forget_staging_can_restore_recovery_material(self):
        state = Path(self.temp.name) / "forget-staging"
        history = state / "reviews/history"
        history.mkdir(parents=True)
        legacy = history / "session-1.json"
        legacy.write_text("{}")
        backups = state / "reviews/backups"
        backups.mkdir()
        backup = backups / "ledger.sqlite3"
        backup.write_bytes(b"backup")
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_forget_staging", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        staged = module.stage_pre_forget_state(state)
        self.assertFalse(legacy.exists())
        self.assertFalse(backups.exists())
        module.restore_staged_forget(*staged)
        self.assertTrue(legacy.exists())
        self.assertEqual(backup.read_bytes(), b"backup")

    def test_review_forget_recovers_pre_and_post_commit_crashes(self):
        state = Path(self.temp.name) / "forget-recovery"
        run(self.repo, "review-prune", "--state-root", str(state))
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_forget_recovery", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        history = state / "reviews/history"
        history.mkdir()
        legacy = history / "session-1.json"
        legacy.write_text("{}")
        orphan_name = f".forget-{'a' * 32}"
        module.stage_pre_forget_state(state, orphan_name)
        run(self.repo, "review-prune", "--state-root", str(state))
        self.assertTrue(legacy.exists())
        self.assertFalse((state / "reviews" / orphan_name).exists())

        legacy.write_text("{}")
        pending_name = f".forget-{'b' * 32}"
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        connection.execute("insert into ledger_meta values ('pending_forget_cleanup', ?)", (pending_name,))
        module.stage_pre_forget_state(state, pending_name)
        connection.commit()
        connection.close()
        run(self.repo, "review-prune", "--state-root", str(state))
        self.assertFalse(legacy.exists())
        self.assertFalse((state / "reviews" / pending_name).exists())
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        self.assertIsNone(connection.execute(
            "select value from ledger_meta where key='pending_forget_cleanup'"
        ).fetchone())
        connection.close()

    def test_review_lock_symlink_fails_without_touching_target(self):
        state = Path(self.temp.name) / "lock-symlink"
        reviews = state / "reviews"
        reviews.mkdir(parents=True, mode=0o700)
        outside = Path(self.temp.name) / "outside-lock"
        outside.write_text("unchanged")
        (reviews / ".lock").symlink_to(outside)
        failed = run(self.repo, "review-history", "--state-root", str(state), "--archive-only", ok=False)
        self.assertTrue(failed.stderr)
        failed = run(self.repo, "review-prune", "--state-root", str(state), ok=False)
        self.assertTrue(failed.stderr)
        self.assertEqual(outside.read_text(), "unchanged")
        self.assertFalse((reviews / "ledger.sqlite3").exists())

    def test_review_recovery_rejects_unowned_quarantine_names(self):
        state = Path(self.temp.name) / "quarantine-name"
        run(self.repo, "review-prune", "--state-root", str(state))
        quarantine = state / "reviews/.forget-user-data"
        quarantine.mkdir(mode=0o700)
        marker = quarantine / "keep"
        marker.write_text("unchanged")
        failed = run(self.repo, "review-prune", "--state-root", str(state), ok=False)
        self.assertIn("quarantine is unsafe", failed.stderr)
        self.assertEqual(marker.read_text(), "unchanged")

    def test_review_completion_rolls_back_archives_when_marker_insert_fails(self):
        database = Path(self.temp.name) / "ledger-atomic.db"
        connection = sqlite3.connect(database)
        connection.executescript("""
            create table session (id text primary key, parent_id text, title text, time_created integer);
            create table message (id text primary key, session_id text, time_created integer, data text);
            create table part (id text primary key, message_id text, session_id text, time_created integer, data text);
            insert into session values ('session-1', null, 'DBSCTR', 1784073600000);
            insert into message values ('message-1', 'session-1', 1784073600000, '{}');
            insert into part values ('part-1', 'message-1', 'session-1', 1784073600000, 'DBSCTR');
        """)
        connection.commit()
        connection.close()
        state = Path(self.temp.name) / "ledger-atomic"
        scan = json.loads(run(self.repo, "review-scan", "--database", str(database),
                              "--state-root", str(state), "--limit", "10", "--cursor", "0").stdout)
        run(self.repo, "review-prune", "--state-root", str(state))
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        connection.execute("create trigger fail_report before insert on review_reports "
                           "begin select raise(abort, 'forced failure'); end")
        connection.commit()
        connection.close()
        report = {
            "session_ids": scan["session_ids"], "cycle_ids": scan["cycle_ids"],
            "scan_digest": scan["digest"], "snapshot": scan["snapshot"],
            "session_ceiling": scan["session_ceiling"], "part_ceiling": scan["part_ceiling"],
            "database_digest": scan["database_digest"], "limit": 10, "cursor": 0,
            "decision": "reviewed",
        }
        failed = run(self.repo, "review-complete", "--report-json", json.dumps(report),
                     "--scan-digest", scan["digest"], "--database", str(database),
                     "--state-root", str(state), ok=False)
        self.assertIn("forced failure", failed.stderr)
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        self.assertEqual(connection.execute("select count(*) from review_reports").fetchone()[0], 0)
        self.assertEqual(connection.execute("select count(*) from history_evidence").fetchone()[0], 0)
        connection.close()

    def test_improvement_claim_is_atomic_private_and_deduplicated(self):
        state = Path(self.temp.name) / "improvement-claim"
        summary = "Generalize repeated lifecycle recovery failures"
        registered = json.loads(run(
            self.repo, "improvement-register", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
            "--workspace-id", "w1", "--tab-id", "w1:t1", "--pane-id", "w1:p1",
        ).stdout)
        self.assertEqual(registered["state"], "reviewing")
        self.assertEqual(registered["tab_id"], "w1:t1")
        self.assertEqual(registered["pane_id"], "w1:p1")
        self.assertIsNone(registered["opportunity_id"])
        self.assertIsNone(registered["priority"])
        repeated = json.loads(run(
            self.repo, "improvement-register", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
        ).stdout)
        self.assertEqual((repeated["worker_id"], repeated["session_id"]), ("worker-1", "session-1"))
        mismatch = run(
            self.repo, "improvement-register", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-other", ok=False,
        )
        self.assertIn("already registered", mismatch.stderr)
        invalid_worker = run(
            self.repo, "improvement-register", "--state-root", str(state),
            "--worker-id", "worker:2", "--session-id", "session-2", ok=False,
        )
        self.assertIn("invalid improvement worker ID", invalid_worker.stderr)
        first = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--session-id", "session-1", "--summary", summary, "--priority", "P1",
        ).stdout)
        self.assertRegex(first["opportunity_id"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["state"], "claimed")
        self.assertEqual(first["priority"], "P1")
        bypass = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "implementing",
            "--cycle-id", "cycle-1", "--path", "tracked.txt", ok=False,
        )
        self.assertIn("claimed -> implementing", bypass.stderr)
        missing_discovery = run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery",
            "--operator-confirm", "worker-1", ok=False)
        self.assertIn("persisted interview", missing_discovery.stderr)
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery",
            "--operator-confirm", "worker-1", "--discovery-json", discovery_report())
        missing_scope = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "implementing", ok=False,
        )
        self.assertIn("requires a cycle ID and declared scope", missing_scope.stderr)
        duplicate = run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-2", "--session-id", "session-2",
            "--summary", "  generalize  repeated lifecycle recovery failures ", ok=False,
        )
        self.assertIn("already claimed", duplicate.stderr)
        unsafe = run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-3", "--session-id", "session-3",
            "--summary", "Observed in /Users/private/repo", ok=False,
        )
        self.assertIn("unsafe improvement summary", unsafe.stderr)
        missing_plan = run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-8", "--session-id", "session-8",
            "--summary", "Add measurable candidate reporting", "--priority", "P1",
            "--kind", "feature", ok=False,
        )
        self.assertIn("require a measurement plan", missing_plan.stderr)
        plan = {"schema_version": 1, "hypothesis": "Candidate reports improve review decisions.",
                "baseline": "Current reports omit candidate measurements.",
                "metric": "Reviewed feature candidates with a complete plan",
                "procedure": "Run the affected R&D contract tests.",
                "success_threshold": "Every feature candidate has all required fields.",
                "evidence_path": "tests/test_dbsctrctl.py"}
        feature = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-8", "--session-id", "session-8",
            "--summary", "Add measurable candidate reporting", "--priority", "P1",
            "--kind", "feature", "--measurement-plan-json", json.dumps(plan),
        ).stdout)
        self.assertEqual(feature["kind"], "feature")
        self.assertEqual(json.loads(feature["measurement_plan"]), plan)
        p2 = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-4", "--session-id", "session-4",
            "--summary", "Queue a bounded operator improvement",
        ).stdout)
        self.assertEqual(p2["priority"], "P2")
        rejected = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-4", "--state", "discovery", ok=False,
        )
        self.assertIn("P2/P3 require promotion", rejected.stderr)
        recovery = run(
            self.repo, "improvement-recover", "--state-root", str(state),
            "--worker-id", "worker-4", "--action", "failed", ok=False,
        )
        self.assertIn("remain queued", recovery.stderr)
        mismatch = run(
            self.repo, "improvement-promote", "--state-root", str(state),
            "--worker-id", "worker-4", "--confirm", "worker-x", ok=False,
        )
        self.assertIn("confirmation does not match", mismatch.stderr)
        promoted = json.loads(run(
            self.repo, "improvement-promote", "--state-root", str(state),
            "--worker-id", "worker-4", "--confirm", "worker-4",
        ).stdout)
        self.assertEqual((promoted["priority"], promoted["state"]), ("P1", "discovery"))
        blocked_implementation = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-4", "--state", "implementing", "--cycle-id", "cycle-4",
            "--path", "tracked.txt", ok=False,
        )
        self.assertIn("persisted Discovery interview", blocked_implementation.stderr)
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-4", "--state", "discovery",
            "--discovery-json", discovery_report())
        autonomous = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-5", "--session-id", "session-5",
            "--summary", "Autonomously refine bounded operator telemetry", "--priority", "P1",
        ).stdout)
        self.assertEqual((autonomous["priority"], autonomous["state"]), ("P1", "claimed"))
        readiness = {"schema_version": 1, "worker_id": "worker-5", "session_id": "session-5",
                     "opportunity_id": autonomous["opportunity_id"], "risk": "elevated",
                     "material_questions_resolved": True, "evidence_digest": "d" * 64}
        discovery = {"schema_version": 1, "interview": [
            {"question": "What fails?", "answer": "The bounded operator workflow fails."}],
            "assumptions": [], "citations": ["source:operator-workflow"], "risks": [],
            "evidence_digest": "d" * 64}
        run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-7", "--session-id", "session-7",
            "--summary", "Reject readiness replay against another claim", "--priority", "P2",
        )
        replay = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-7", "--state", "discovery", "--autonomous",
            "--readiness-json", json.dumps(readiness), ok=False,
        )
        self.assertIn("P2/P3 require promotion", replay.stderr)
        readiness_home = Path(self.temp.name) / "readiness-home"
        scheduler = readiness_home / ".local/state/dotfiles-ai/dbsctr-rnd.sqlite3"
        unavailable = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-5", "--state", "discovery", "--autonomous",
            "--readiness-json", json.dumps(readiness), "--discovery-json", json.dumps(discovery), ok=False,
            env={**isolated_env(), "HOME": str(readiness_home)},
        )
        self.assertIn("autonomous readiness evidence is unavailable", unavailable.stderr)
        scheduler.parent.mkdir(parents=True)
        connection = sqlite3.connect(scheduler)
        connection.executescript("""
            CREATE TABLE scheduler_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
            INSERT INTO scheduler_meta VALUES ('schema_version','8');
            CREATE TABLE parallel_lens_passes (
                worker_id TEXT PRIMARY KEY, lens_name TEXT NOT NULL, capture_day TEXT NOT NULL,
                manifest_digest TEXT NOT NULL, outcome TEXT NOT NULL, recorded_at INTEGER NOT NULL,
                cadence TEXT NOT NULL, no_yield_count INTEGER NOT NULL, quarter TEXT NOT NULL,
                next_eligible_at INTEGER NOT NULL, page_count INTEGER NOT NULL,
                session_count INTEGER NOT NULL, review_session_count INTEGER NOT NULL,
                excluded_review_session_count INTEGER NOT NULL,
                unattributed_session_count INTEGER NOT NULL, source_count INTEGER NOT NULL,
                opportunity_id TEXT, session_id TEXT
            ) WITHOUT ROWID;
        """)
        connection.execute("INSERT INTO parallel_lens_passes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("worker-5", "correctness_safety", "2026-07-31", "d" * 64,
                            "yield", 1, "daily", 0, "2026-Q3", 1, 1, 1, 0, 0, 0, 1,
                            autonomous["opportunity_id"], "session-5"))
        connection.commit()
        connection.close()
        scheduler.chmod(0o600)
        autonomous = json.loads(run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-5", "--state", "discovery", "--autonomous",
            "--readiness-json", json.dumps(readiness), "--discovery-json", json.dumps(discovery),
            env={**isolated_env(), "HOME": str(readiness_home)},
        ).stdout)
        self.assertEqual((autonomous["priority"], autonomous["state"]), ("P1", "discovery"))
        self.assertEqual(autonomous["authorization"], "autonomous")
        self.assertEqual(json.loads(autonomous["readiness"]), readiness)
        self.assertEqual(json.loads(autonomous["discovery_report"]), discovery)
        autonomous = json.loads(run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-5", "--state", "implementing",
            "--cycle-id", "cycle-5", "--path", "autonomous.txt",
        ).stdout)
        self.assertEqual((autonomous["priority"], autonomous["state"]), ("P1", "implementing"))
        recovered = json.loads(run(
            self.repo, "improvement-recover", "--state-root", str(state),
            "--worker-id", "worker-5", "--action", "success",
        ).stdout)
        self.assertEqual((recovered["state"], recovered["recovery_attempts"]), ("implementing", 0))
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-5", "--state", "abandoned")
        run(self.repo, "improvement-forget", "--state-root", str(state),
            "--worker-id", "worker-5", "--confirm", "worker-5")
        replacement = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-5", "--session-id", "session-5b",
            "--summary", "Reject stale evidence after worker reuse", "--priority", "P1",
        ).stdout)
        connection = sqlite3.connect(scheduler)
        connection.execute(
            "update parallel_lens_passes set opportunity_id=? where worker_id='worker-5'",
            (replacement["opportunity_id"],),
        )
        connection.commit()
        connection.close()
        stale = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-5", "--state", "discovery", "--autonomous",
            "--readiness-json", json.dumps({**readiness, "session_id": "session-5b",
                                              "opportunity_id": replacement["opportunity_id"]}),
            "--discovery-json", json.dumps(discovery),
            env={**isolated_env(), "HOME": str(readiness_home)}, ok=False,
        )
        self.assertIn("evidence does not match the worker", stale.stderr)
        critical_claim = json.loads(run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-6", "--session-id", "session-6",
            "--summary", "Escalate a critical autonomous finding", "--priority", "P0").stdout)
        critical_readiness = {**readiness, "worker_id": "worker-6", "session_id": "session-6",
                              "opportunity_id": critical_claim["opportunity_id"],
                              "risk": "critical", "evidence_digest": "e" * 64}
        critical_discovery = {**discovery, "evidence_digest": "e" * 64}
        connection = sqlite3.connect(scheduler)
        connection.execute("INSERT INTO parallel_lens_passes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("worker-6", "correctness_safety", "2026-07-31", "e" * 64,
                            "yield", 1, "daily", 0, "2026-Q3", 1, 1, 1, 0, 0, 0, 1,
                            critical_readiness["opportunity_id"], "session-6"))
        connection.commit()
        connection.close()
        critical = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-6", "--state", "discovery", ok=False,
        )
        self.assertIn("autonomous readiness or operator confirmation", critical.stderr)
        critical = json.loads(run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-6", "--state", "discovery", "--autonomous",
            "--readiness-json", json.dumps(critical_readiness),
            "--discovery-json", json.dumps(critical_discovery),
            env={**isolated_env(), "HOME": str(readiness_home)},
        ).stdout)
        self.assertEqual((critical["priority"], critical["state"]), ("P0", "discovery"))
        self.assertEqual(critical["authorization"], "autonomous")
        repeated = run(
            self.repo, "improvement-promote", "--state-root", str(state),
            "--worker-id", "worker-4", "--confirm", "worker-4", ok=False,
        )
        self.assertIn("only a claimed P2/P3", repeated.stderr)
        ledger = state / "reviews/ledger.sqlite3"
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)

    def test_batch_commands_reject_invalid_or_unconfirmed_identity(self):
        invalid = run(
            self.repo, "batch-create", "--batch-id", "../main",
            "--github-account", "owner", "--github-repository", "owner/repo", ok=False,
        )
        self.assertIn("invalid batch ID", invalid.stderr)
        missing = run(
            self.repo, "batch-publish", "--batch-id", "batch-1", "--confirm", "batch-2", ok=False,
        )
        self.assertIn("batch confirmation does not match", missing.stderr)

    def test_batch_integration_creates_no_ff_merge_and_preview_is_ephemeral(self):
        bare = Path(self.temp.name) / "origin.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=self.repo,
                       check=True, capture_output=True)
        records = self.repo / ".git/dbsctr/cycles"
        records.mkdir(parents=True)
        for number in (1, 2):
            branch = f"dbsctr/test/cycle-{number}"
            subprocess.run(["git", "switch", "-c", branch, "main"], cwd=self.repo,
                           check=True, capture_output=True)
            (self.repo / f"source-{number}.txt").write_text(f"source {number}\n")
            subprocess.run(["git", "add", f"source-{number}.txt"], cwd=self.repo, check=True)
            subprocess.run(["git", "commit", "-m", f"source {number}"], cwd=self.repo,
                           check=True, capture_output=True)
            sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
                                 check=True, capture_output=True).stdout.strip()
            subprocess.run(["git", "push", "origin", branch], cwd=self.repo,
                           check=True, capture_output=True)
            (records / f"cycle-{number}.json").write_text(json.dumps({
                "state": "completed", "delivery_intent": "draft_pr",
                "delivery": {"branch": branch, "published_feature_head": sha},
            }))
        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True, capture_output=True)
        env = {**isolated_env(), "HOME": str(Path(self.temp.name) / "home")}
        created = json.loads(run(
            self.repo, "batch-create", "--batch-id", "batch-1",
            "--github-account", "owner", "--github-repository", "owner/repo", env=env,
        ).stdout)
        integrated = json.loads(run(
            self.repo, "batch-integrate", "--batch-id", "batch-1",
            "--source", "dbsctr/test/cycle-1", env=env,
        ).stdout)
        merge = integrated["sources"][0]["merge"]
        parents = subprocess.run(
            ["git", "show", "-s", "--format=%P", merge], cwd=self.repo,
            text=True, check=True, capture_output=True,
        ).stdout.split()
        self.assertEqual(len(parents), 2)
        preview = json.loads(run(
            self.repo, "batch-integrate", "--batch-id", "batch-1",
            "--source", "dbsctr/test/cycle-2", "--preview", env=env,
        ).stdout)
        self.assertTrue(preview["preview"])
        worktrees = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=self.repo,
                                   text=True, check=True, capture_output=True).stdout
        self.assertNotIn("dbsctr-batch-batch-1-", worktrees)
        duplicate = run(
            self.repo, "batch-integrate", "--batch-id", "batch-1",
            "--source", "dbsctr/test/cycle-1", env=env, ok=False,
        )
        self.assertIn("already integrated", duplicate.stderr)
        batch_worktree = Path(created["worktree"])
        (batch_worktree / "unrecorded.txt").write_text("unrecorded\n")
        subprocess.run(["git", "add", "unrecorded.txt"], cwd=batch_worktree, check=True)
        subprocess.run(["git", "commit", "-m", "unrecorded"], cwd=batch_worktree,
                       check=True, capture_output=True)
        unrecorded = run(
            self.repo, "batch-publish", "--batch-id", "batch-1", "--confirm", "batch-1",
            env=env, ok=False,
        )
        self.assertIn("batch tip is not the recorded merge history", unrecorded.stderr)
        subprocess.run(["git", "worktree", "remove", "--force", created["worktree"]],
                       cwd=self.repo, check=True, capture_output=True)

    def test_batch_finalize_closes_admission_and_requires_current_dvc_evidence(self):
        managed = Path(self.temp.name) / "batch-managed"
        managed.mkdir()
        controller = managed / "dbsctrctl"
        shutil.copy2(SCRIPT, controller)
        adapter = managed / "dbsctr-project-graphify"
        adapter.write_text(
            "#!/bin/sh\nset -eu\ntest \"$1\" = --output-dir\nmkdir -p \"$2\"\n"
            "printf 'Built from commit: `%s`\\n' \"$(git rev-parse HEAD)\" > \"$2/GRAPH_REPORT.md\"\n"
            "printf '{\"schema_version\":1}\\n' > \"$2/manifest.json\"\n"
            "printf 'stages: {}\\n' > \"$2/dvc.yaml\"\n"
            "printf 'stale\\n' > \"$2/graph.receipt.json\"\n"
        )
        adapter.chmod(0o755)
        selection = {
            "version": "0.9.50",
            "adapter_contract": "dbsctr-project-graphify-v1",
            "adapter_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        }
        archive = self.repo / ".git/dbsctr/graphify/adapters"
        archive.mkdir(parents=True)
        snapshot = archive / selection["adapter_sha256"]
        shutil.copy2(adapter, snapshot)
        snapshot.chmod(0o700)
        graph = self.repo / "graphify-out"
        graph.mkdir()
        (graph / "GRAPH_REPORT.md").write_text("old report\n")
        (graph / "manifest.json").write_text("{}\n")
        subprocess.run(["git", "add", "graphify-out"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "graph baseline"], cwd=self.repo,
                       check=True, capture_output=True)
        bare = Path(self.temp.name) / "graph-origin.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=self.repo,
                       check=True, capture_output=True)
        branch = "dbsctr/test/graph-source"
        subprocess.run(["git", "switch", "-c", branch], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "source.txt").write_text("source\n")
        subprocess.run(["git", "add", "source.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "source"], cwd=self.repo,
                       check=True, capture_output=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
                             check=True, capture_output=True).stdout.strip()
        subprocess.run(["git", "push", "origin", branch], cwd=self.repo, check=True, capture_output=True)
        records = self.repo / ".git/dbsctr/cycles"
        records.mkdir(parents=True)
        (records / "graph-source.json").write_text(json.dumps({
            "state": "completed", "delivery_intent": "draft_pr",
            "delivery": {"branch": branch, "published_feature_head": sha},
            "applicability_plan": {"graphify": selection},
        }))
        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True, capture_output=True)
        env = {**isolated_env(), "HOME": str(Path(self.temp.name) / "graph-home")}
        batch_path = self.repo / ".git/dbsctr/batches/graph-batch.json"
        run(self.repo, "batch-create", "--batch-id", "graph-batch",
            "--github-account", "owner", "--github-repository", "owner/repo", env=env,
            script=controller)
        created_metadata = batch_path.read_text()
        run(self.repo, "batch-integrate", "--batch-id", "graph-batch", "--source", branch,
            env=env, script=controller)
        batch_path.write_text(created_metadata)
        recovered = json.loads(run(
            self.repo, "batch-integrate", "--batch-id", "graph-batch", "--source", branch,
            env=env, script=controller).stdout)
        self.assertEqual(recovered["sources"][0]["sha"], sha)
        plain_branch = "dbsctr/test/plain-source"
        subprocess.run(["git", "switch", "-c", plain_branch], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "plain.txt").write_text("plain\n")
        subprocess.run(["git", "add", "plain.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "plain"], cwd=self.repo, check=True, capture_output=True)
        plain_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True,
                                   check=True, capture_output=True).stdout.strip()
        subprocess.run(["git", "push", "origin", plain_branch], cwd=self.repo, check=True, capture_output=True)
        (records / "plain-source.json").write_text(json.dumps({
            "state": "completed", "delivery_intent": "draft_pr",
            "delivery": {"branch": plain_branch, "published_feature_head": plain_sha},
        }))
        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True, capture_output=True)
        mixed = run(self.repo, "batch-integrate", "--batch-id", "graph-batch",
                    "--source", plain_branch, env=env, ok=False, script=controller)
        self.assertIn("Graphify selection changed", mixed.stderr)
        integrated_metadata = batch_path.read_text()
        batch_worktree = Path(recovered["worktree"])
        batch_graph = batch_worktree / "graphify-out"
        before = {path.relative_to(batch_graph): path.read_bytes()
                  for path in batch_graph.rglob("*") if path.is_file()}
        tools = Path(self.temp.name) / "batch-tools"
        tools.mkdir()
        fake_git = tools / "git"
        fake_git.write_text(
            "#!/bin/sh\nif [ \"${1:-}\" = commit ]; then\n"
            "  printf 'forced commit failure\\n' >&2\n  exit 9\nfi\n"
            f'exec "{shutil.which("git")}" "$@"\n'
        )
        fake_git.chmod(0o755)
        failed = run(
            self.repo, "batch-finalize", "--batch-id", "graph-batch", ok=False,
            env={**env, "PATH": f"{tools}:{os.environ['PATH']}"}, script=controller,
        )
        self.assertIn("forced commit failure", failed.stderr)
        after = {path.relative_to(batch_graph): path.read_bytes()
                 for path in batch_graph.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertFalse(subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=batch_worktree, text=True,
            check=True, capture_output=True).stdout)
        finalized = json.loads(run(
            self.repo, "batch-finalize", "--batch-id", "graph-batch", env=env,
            script=controller).stdout)
        self.assertEqual(finalized["state"], "finalized")
        self.assertTrue(finalized["graph"]["requires_dvc_push"])
        batch_path.write_text(integrated_metadata)
        recovered_graph = json.loads(run(
            self.repo, "batch-finalize", "--batch-id", "graph-batch", env=env,
            script=controller).stdout)
        self.assertEqual(recovered_graph["graph"]["commit"], finalized["graph"]["commit"])
        closed = run(self.repo, "batch-integrate", "--batch-id", "graph-batch",
                     "--source", branch, env=env, ok=False, script=controller)
        self.assertIn("admission is closed", closed.stderr)
        blocked = run(self.repo, "batch-publish", "--batch-id", "graph-batch",
                      "--confirm", "graph-batch", env=env, ok=False, script=controller)
        self.assertIn("DVC push evidence", blocked.stderr)
        run(self.repo, "batch-record-dvc-push", "--batch-id", "graph-batch",
            "--head", finalized["graph"]["commit"], "--evidence", "approved dvc push", env=env,
            script=controller)
        metadata = json.loads((self.repo / ".git/dbsctr/batches/graph-batch.json").read_text())
        self.assertEqual(metadata["dvc_push"]["head"], finalized["graph"]["commit"])
        subprocess.run(["git", "worktree", "remove", "--force", metadata["worktree"]],
                       cwd=self.repo, check=True, capture_output=True)

    def test_improvement_scope_claims_reject_overlapping_paths(self):
        state = Path(self.temp.name) / "improvement-scope"
        for worker, session, summary in (
            ("worker-1", "session-1", "Improve lifecycle helper"),
            ("worker-2", "session-2", "Improve supervisor policy"),
        ):
            run(self.repo, "improvement-claim", "--state-root", str(state),
                "--worker-id", worker, "--session-id", session, "--summary", summary,
                "--priority", "P1")
            run(self.repo, "improvement-update", "--state-root", str(state),
                "--worker-id", worker, "--state", "discovery", "--operator-confirm", worker,
                "--discovery-json", discovery_report())
        updated = json.loads(run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "implementing",
            "--cycle-id", "cycle-1",
            "--path", "dot_local/bin/executable_dbsctrctl",
        ).stdout)
        self.assertEqual(updated["paths"], ["dot_local/bin/executable_dbsctrctl"])
        conflict = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-2", "--state", "implementing",
            "--cycle-id", "cycle-2",
            "--path", "dot_local/bin", ok=False,
        )
        self.assertIn("scope conflicts", conflict.stderr)
        draft = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "draft_pr", ok=False,
        )
        self.assertIn("invalid improvement transition", draft.stderr)

    def test_improvement_recovery_blocks_then_requires_retry_or_abandon(self):
        state = Path(self.temp.name) / "improvement-recovery"
        run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
            "--summary", "Recover exact worker sessions", "--priority", "P1")
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery",
            "--operator-confirm", "worker-1", "--workspace-id", "workspace-1",
            "--tab-id", "tab-1", "--pane-id", "pane-1", "--discovery-json", discovery_report())
        for attempt in range(1, 4):
            worker = json.loads(run(
                self.repo, "improvement-recover", "--state-root", str(state),
                "--worker-id", "worker-1", "--action", "failed",
            ).stdout)
            self.assertEqual(worker["recovery_attempts"], attempt)
        self.assertEqual(worker["state"], "blocked")
        retried = json.loads(run(
            self.repo, "improvement-recover", "--state-root", str(state),
            "--worker-id", "worker-1", "--action", "retry",
        ).stdout)
        self.assertEqual(retried["state"], "discovery")
        self.assertEqual(retried["recovery_attempts"], 0)
        abandoned = json.loads(run(
            self.repo, "improvement-recover", "--state-root", str(state),
            "--worker-id", "worker-1", "--action", "abandon",
        ).stdout)
        self.assertEqual(abandoned["state"], "abandoned")
        status = json.loads(run(
            self.repo, "improvement-status", "--state-root", str(state),
            "--worker-id", "worker-1",
        ).stdout)
        self.assertEqual(status["workers"], [abandoned])

    def test_improvement_forget_requires_exact_abandoned_worker(self):
        state = Path(self.temp.name) / "improvement-forget"
        summary = "Retire stale improvement history"
        claimed = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1", "--summary", summary,
            "--priority", "P1",
        ).stdout)
        active = run(
            self.repo, "improvement-forget", "--state-root", str(state),
            "--worker-id", "worker-1", "--confirm", "worker-1", ok=False,
        )
        self.assertIn("only an abandoned improvement worker", active.stderr)
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery",
            "--operator-confirm", "worker-1", "--discovery-json", discovery_report())
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "implementing",
            "--cycle-id", "cycle-1", "--path", "tracked.txt")
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "abandoned")
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        connection.execute("insert into improvement_scope values ('worker-1', 'retained.txt')")
        connection.commit()
        connection.close()
        mismatch = run(
            self.repo, "improvement-forget", "--state-root", str(state),
            "--worker-id", "worker-1", "--confirm", "worker-2", ok=False,
        )
        self.assertIn("confirmation does not match", mismatch.stderr)
        forgotten = json.loads(run(
            self.repo, "improvement-forget", "--state-root", str(state),
            "--worker-id", "worker-1", "--confirm", "worker-1",
        ).stdout)
        self.assertEqual(forgotten, {"forgotten_worker_id": "worker-1"})
        self.assertEqual(json.loads(run(
            self.repo, "improvement-status", "--state-root", str(state),
        ).stdout), {"workers": []})
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        self.assertEqual(connection.execute("select count(*) from improvement_scope").fetchone()[0], 0)
        connection.close()
        replacement = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-2", "--session-id", "session-2", "--summary", summary,
            "--priority", "P1",
        ).stdout)
        self.assertEqual(replacement["opportunity_id"], claimed["opportunity_id"])

        run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-3", "--session-id", "session-3",
            "--summary", "Preserve closed improvement history", "--priority", "P1")
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        connection.execute("update improvement_workers set state='merged' where worker_id='worker-2'")
        connection.execute("update improvement_workers set state='closed' where worker_id='worker-3'")
        connection.commit()
        connection.close()
        for worker_id in ("worker-2", "worker-3"):
            protected = run(
                self.repo, "improvement-forget", "--state-root", str(state),
                "--worker-id", worker_id, "--confirm", worker_id, ok=False,
            )
            self.assertIn("only an abandoned improvement worker", protected.stderr)

    def test_improvement_write_rolls_back_failed_integrity(self):
        state = Path(self.temp.name) / "improvement-integrity-rollback"
        run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
            "--summary", "Retain failed improvement writes")
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_improvement_rollback", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with mock.patch.object(module, "ledger_integrity", side_effect=RuntimeError("forced integrity failure")):
            with self.assertRaisesRegex(RuntimeError, "forced integrity failure"):
                module.improvement_write(state, lambda connection: connection.execute(
                    "delete from improvement_workers where worker_id='worker-1'"))
        status = json.loads(run(
            self.repo, "improvement-status", "--state-root", str(state),
            "--worker-id", "worker-1",
        ).stdout)
        self.assertEqual(status["workers"][0]["worker_id"], "worker-1")

    def test_improvement_schema_install_rolls_back_as_one_transaction(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_improvement_schema", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        connection = sqlite3.connect(":memory:")
        connection.execute("create table ledger_meta (key text primary key, value text not null)")
        connection.execute("insert into ledger_meta values ('schema_version', '1')")
        connection.commit()

        def deny_scope(action, name, *_args):
            return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_CREATE_TABLE and name == "improvement_scope" else sqlite3.SQLITE_OK

        connection.set_authorizer(deny_scope)
        with self.assertRaises(sqlite3.DatabaseError):
            module.ensure_improvement_schema(connection)
        connection.set_authorizer(None)
        tables = {row[0] for row in connection.execute(
            "select name from sqlite_master where type='table' and name like 'improvement_%'")}
        self.assertEqual(tables, set())
        self.assertIsNone(connection.execute(
            "select value from ledger_meta where key='improvement_schema'").fetchone())
        connection.close()

    def test_improvement_schema_migrates_existing_claims_to_p2(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_improvement_migration", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        connection = sqlite3.connect(":memory:")
        connection.executescript("""
            create table ledger_meta (key text primary key, value text not null);
            insert into ledger_meta values ('improvement_schema', '1');
            create table improvement_workers (
                worker_id text primary key, session_id text not null unique,
                opportunity_id text unique, summary text, state text not null,
                resume_state text not null, recovery_attempts integer not null default 0,
                workspace_id text, tab_id text, pane_id text, cycle_id text,
                pr_number integer, pr_url text, created_at integer not null,
                updated_at integer not null) without rowid;
            create table improvement_scope (
                worker_id text not null references improvement_workers(worker_id) on delete cascade,
                path text not null, primary key (worker_id,path)) without rowid;
        """)
        connection.execute(
            "insert into improvement_workers values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("worker-1", "session-1", "a" * 64, "Existing claim", "claimed", "claimed", 0,
             None, None, None, None, None, None, module.REVIEW_START_MS, module.REVIEW_START_MS))
        for index, state, resume_state in (
            (2, "discovery", "discovery"), (3, "implementing", "implementing"),
            (4, "draft_pr", "draft_pr"), (5, "blocked", "discovery"),
        ):
            connection.execute(
                "insert into improvement_workers values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"worker-{index}", f"session-{index}", f"{index:x}" * 64,
                 f"Existing {state}", state, resume_state, 0, None, None, None, None,
                 None, None, module.REVIEW_START_MS, module.REVIEW_START_MS))
        connection.commit()
        module.ensure_improvement_schema(connection)
        self.assertEqual(connection.execute(
            "select value from ledger_meta where key='improvement_schema'").fetchone(), ("5",))
        self.assertEqual(connection.execute(
            "select priority from improvement_workers where worker_id='worker-1'").fetchone(), ("P2",))
        self.assertEqual(connection.execute(
            "select distinct priority from improvement_workers where worker_id!='worker-1'"
        ).fetchall(), [("P1",)])
        self.assertEqual(connection.execute(
            "select authorization from improvement_workers where worker_id='worker-1'").fetchone(), ("none",))
        self.assertEqual(connection.execute(
            "select distinct authorization from improvement_workers where worker_id!='worker-1'"
        ).fetchall(), [("operator",)])
        self.assertEqual(connection.execute(
            "select distinct readiness from improvement_workers").fetchall(), [(None,)])
        self.assertEqual(connection.execute(
            "select distinct kind from improvement_workers").fetchall(), [("fix",)])
        module.improvement_integrity(connection)
        connection.close()

    def test_improvement_status_migrates_v1_ledger_under_lock(self):
        state = Path(self.temp.name) / "improvement-status-migration"
        run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
            "--summary", "Migrate an existing queued claim")
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        connection.execute("update ledger_meta set value='1' where key='improvement_schema'")
        connection.execute("alter table improvement_workers drop column priority")
        connection.execute("alter table improvement_workers drop column authorization")
        connection.execute("alter table improvement_workers drop column readiness")
        connection.execute("alter table improvement_workers drop column kind")
        connection.execute("alter table improvement_workers drop column measurement_plan")
        connection.execute("alter table improvement_workers drop column discovery_report")
        connection.execute("alter table improvement_workers drop column implementation_report")
        connection.commit()
        connection.close()
        status = json.loads(run(
            self.repo, "improvement-status", "--state-root", str(state),
            "--worker-id", "worker-1",
        ).stdout)
        self.assertEqual(status["workers"][0]["priority"], "P2")
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute(
            "select value from ledger_meta where key='improvement_schema'").fetchone(), ("5",))
        connection.close()

        state = Path(self.temp.name) / "improvement-status-migration-v3"
        run(self.repo, "improvement-claim", "--state-root", str(state),
            "--worker-id", "worker-1", "--session-id", "session-1",
            "--summary", "Migrate an authorized queued claim")
        ledger = state / "reviews/ledger.sqlite3"
        connection = sqlite3.connect(ledger)
        connection.execute("update ledger_meta set value='3' where key='improvement_schema'")
        connection.execute("alter table improvement_workers drop column readiness")
        connection.execute("alter table improvement_workers drop column kind")
        connection.execute("alter table improvement_workers drop column measurement_plan")
        connection.execute("alter table improvement_workers drop column discovery_report")
        connection.execute("alter table improvement_workers drop column implementation_report")
        connection.commit()
        connection.close()
        status = json.loads(run(
            self.repo, "improvement-status", "--state-root", str(state),
            "--worker-id", "worker-1",
        ).stdout)
        self.assertIsNone(status["workers"][0]["readiness"])
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute(
            "select value from ledger_meta where key='improvement_schema'").fetchone(), ("5",))
        connection.close()

    def test_provider_evaluation_derives_exact_five_cycle_report(self):
        state = Path(self.temp.name) / "provider-evaluation"
        activation = {"schema_version": 1, "provider_id": "openai", "model_id": "gpt-5.6-sol",
                      "agent_id": "build-gpt", "core_revision": "3.29",
                      "overlay_revision": "openai-2026-07-26"}
        availability = {name: "available" for name in (
            "delegation_count", "model_families", "error_classes", "token_total", "cost_total",
            "provider_ids", "model_ids", "agent_ids", "session_relation", "core_revisions",
            "overlay_revisions", "gate_failure_count", "gate_reopen_count", "remediation_round_count")}
        availability.update({"approval_count": "unavailable", "retry_count": "unavailable"})
        candidates = []
        for index in range(5):
            metrics = {"elapsed_ms": 100 + index, "gate_failure_count": 0,
                       "gate_reopen_count": 0, "remediation_round_count": 0}
            telemetry = {"schema_version": 2, "approval_count": "unavailable", "retry_count": "unavailable",
                         "delegation_count": 0, "model_families": ["gpt"], "error_classes": {"tool_error": 0},
                         "token_total": 10, "cost_total": 1, "provider_ids": ["openai"],
                         "model_ids": ["gpt-5.6-sol", "gpt-5.6-terra"],
                         "agent_ids": ["build-gpt", "builder-openai"],
                         "session_relation": "primary", "core_revisions": ["3.29"],
                         "overlay_revisions": ["openai-2026-07-26"], "gate_failure_count": 0,
                         "gate_reopen_count": 0, "remediation_round_count": 0,
                         "availability": availability, "attribution_status": "exact"}
            candidates.append({"schema_version": 1, "session_id": f"session-{index}",
                               "completed_at": str(1784073600000 + index), "method_revision": "3.27",
                               "context": "opencode_control_plane", "project_digest": "0" * 64,
                               "correlation_quality": "exact", "reviewed_status": "unreviewed",
                               "aggregates": {}, "snapshot": 1, "session_ceiling": 1,
                               "part_ceiling": 1, "database_digest": "1" * 64,
                               "cycles": [{"cycle_id": f"cycle-{index}", "state": "completed",
                                           "risk": "elevated", "delivery_intent": "deploy",
                                           "metrics": metrics, "harness_activation": activation}],
                               "telemetry": telemetry})
        receipt = {"schema_version": 1, "manifest_digest": "", "manifest_identity": {}, "sources": [{
            "source_id": "host", "capture_id": "c" * 24, "privacy_epoch_digest": "d" * 64,
            "pages": [{"schema_version": 1, "capture_id": "c" * 24, "cursor": 0, "limit": 5,
                       "continuation": None, "snapshot": 1, "session_ceiling": 1, "part_ceiling": 1,
                       "database_digest": "1" * 64, "exclusion_digest": None,
                       "query": {"after": None, "before": None, "method_revision": None,
                                 "cycle_id": None, "state": None, "context": None,
                                 "project_digest": None, "reviewed_status": None, "archive_only": False},
                       "digest": "e" * 64, "session_ids": [f"session-{index}" for index in range(5)],
                       "member_digests": [hashlib.sha256(json.dumps(
                           candidate, sort_keys=True, separators=(",", ":")
                       ).encode()).hexdigest() for candidate in candidates],
                       "candidates": candidates}],
        }]}
        page = receipt["sources"][0]["pages"][0]
        receipt["manifest_identity"] = {"filters": page["query"], "sources": [{
            "source_id": "host", "availability": "available",
            **{name: page[name] for name in ("capture_id", "snapshot", "session_ceiling", "part_ceiling",
                                              "database_digest", "exclusion_digest", "limit", "cursor",
                                              "continuation", "digest")},
        }]}
        receipt["manifest_digest"] = hashlib.sha256(json.dumps(
            receipt["manifest_identity"], sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        report_input = {"rubric": {"name": "provider-harness", "version": "1", "digest": "a" * 64},
                        "findings": ["No regression"], "recommendations": []}
        report = json.loads(run(
            self.repo, "provider-evaluation-save", "--state-root", str(state),
            "--receipt-json", json.dumps(receipt), "--report-json", json.dumps(report_input),
        ).stdout)
        self.assertRegex(report["report_id"], r"^[0-9a-f]{24}$")
        self.assertEqual([item["cycle_id"] for item in report["members"]],
                         [f"cycle-{index}" for index in range(5)])
        self.assertEqual(report["aggregates"]["elapsed_ms_median"], 102)
        self.assertEqual(report["aggregates"]["token_total"], 50)
        self.assertEqual(report["availability"]["token_total"], "available")
        self.assertEqual(report["confounders"], ["child_agent_distribution"])
        self.assertEqual(report["evidence"][0]["capture_id"], "c" * 24)
        replay = json.loads(run(
            self.repo, "provider-evaluation", "--state-root", str(state),
            "--report-id", report["report_id"],
        ).stdout)
        self.assertEqual(replay, report)
        duplicate = json.loads(run(
            self.repo, "provider-evaluation-save", "--state-root", str(state),
            "--receipt-json", json.dumps(receipt), "--report-json", json.dumps(report_input),
        ).stdout)
        self.assertEqual(duplicate, report)
        ledger = state / "reviews/ledger.sqlite3"
        with sqlite3.connect(ledger) as connection:
            connection.execute("UPDATE provider_evaluation_sources SET verified_at=?",
                               (int((time.time() - 9 * 24 * 60 * 60) * 1000),))
        quarantined = run(
            self.repo, "provider-evaluation", "--state-root", str(state),
            "--report-id", report["report_id"], ok=False,
        )
        self.assertIn("quarantined", quarantined.stderr)
        with sqlite3.connect(ledger) as connection:
            connection.execute("UPDATE provider_evaluation_sources SET verified_at=?", (int(time.time() * 1000),))
        backup = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        restored = json.loads(run(
            self.repo, "provider-evaluation", "--state-root", str(state),
            "--report-id", report["report_id"],
        ).stdout)
        self.assertEqual(restored, report)
        unaffected = json.loads(run(self.repo, "review-backup", "--state-root", str(state)).stdout)
        unaffected_path = state / "reviews/backups" / unaffected["backup"]
        with sqlite3.connect(unaffected_path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("DELETE FROM provider_evaluation_reports WHERE report_id=?", (report["report_id"],))
        run(self.repo, "provider-evaluation-forget", "--state-root", str(state),
            "--report-id", report["report_id"])
        self.assertTrue(unaffected_path.is_file())
        missing = run(
            self.repo, "provider-evaluation", "--state-root", str(state),
            "--report-id", report["report_id"], ok=False,
        )
        self.assertIn("missing", missing.stderr)
        resaved = json.loads(run(
            self.repo, "provider-evaluation-save", "--state-root", str(state),
            "--receipt-json", json.dumps(receipt), "--report-json", json.dumps(report_input),
        ).stdout)
        self.assertEqual(resaved["report_id"], report["report_id"])
        run(self.repo, "review-backup", "--state-root", str(state))
        changed_receipt = json.loads(json.dumps(receipt))
        changed_receipt["sources"][0]["privacy_epoch_digest"] = "f" * 64
        changed_receipt["sources"][0]["pages"][0]["candidates"] = []
        changed_receipt["sources"][0]["pages"][0]["session_ids"] = []
        changed_receipt["sources"][0]["pages"][0]["member_digests"] = []
        insufficient = json.loads(run(
            self.repo, "provider-evaluation-save", "--state-root", str(state),
            "--receipt-json", json.dumps(changed_receipt), "--report-json", json.dumps(report_input),
        ).stdout)
        self.assertEqual(insufficient["status"], "insufficient")
        self.assertTrue(unaffected_path.is_file())
        removed = run(
            self.repo, "provider-evaluation", "--state-root", str(state),
            "--report-id", report["report_id"], ok=False,
        )
        self.assertIn("missing", removed.stderr)

    def test_review_privacy_epoch_ignores_worker_exclusion(self):
        state = Path(self.temp.name) / "privacy-epoch"
        first = json.loads(run(self.repo, "review-privacy-epoch", "--state-root", str(state)).stdout)
        self.assertRegex(first["privacy_epoch_digest"], r"^[0-9a-f]{64}$")
        root = state / "reviews"
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
        path = root / "reviewed.json"
        path.write_text(json.dumps({"schema_version": 1, "sessions": {}, "cycles": {},
                                    "forgotten_sessions": {"session-1": 1784073600000}}))
        path.chmod(0o600)
        changed = json.loads(run(self.repo, "review-privacy-epoch", "--state-root", str(state)).stdout)
        self.assertNotEqual(changed["privacy_epoch_digest"], first["privacy_epoch_digest"])

    def test_knowledge_privacy_status_and_guard(self):
        state = Path(self.temp.name) / "knowledge-privacy"
        status = json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state),
        ).stdout)
        self.assertEqual(status["schema_version"], 1)
        self.assertEqual(status["privacy_sequence"], 0)
        self.assertRegex(status["privacy_digest"], r"^[0-9a-f]{64}$")
        run(self.repo, "review-prune", "--state-root", str(state))
        self.assertEqual(json.loads(run(
            self.repo, "knowledge-privacy-status", "--state-root", str(state)).stdout), status)

        guarded = run(
            self.repo, "knowledge-privacy-guard", "--state-root", str(state),
            "--expected-sequence", "0", "--expected-digest", status["privacy_digest"],
            "--", sys.executable, "-c", "print('guarded')",
        )
        self.assertEqual(guarded.stdout, "guarded\n")

        marker = Path(self.temp.name) / "must-not-run"
        mismatch = run(
            self.repo, "knowledge-privacy-guard", "--state-root", str(state),
            "--expected-sequence", "1", "--expected-digest", status["privacy_digest"],
            "--", sys.executable, "-c", f"open({str(marker)!r}, 'w').close()",
            ok=False,
        )
        self.assertIn("privacy status mismatch", mismatch.stderr)
        self.assertFalse(marker.exists())

    def test_capture_benchmark_deletion_records_privacy_tombstone(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_benchmark_privacy", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        connection = sqlite3.connect(":memory:")
        connection.executescript("""
            create table ledger_meta (key text primary key, value text not null);
            create table knowledge_privacy_tombstones (
                family text not null, item_id text not null, reason text not null,
                timestamp integer not null, primary key (family,item_id));
            create table benchmark_effects (
                benchmark_id text primary key, baseline_capture_id text, observation_capture_id text);
            insert into ledger_meta values ('benchmark_schema','1');
            insert into ledger_meta values ('knowledge_privacy_sequence','0');
            insert into ledger_meta values ('knowledge_privacy_digest','0');
            insert into benchmark_effects values ('benchmark-1','capture-1','capture-2');
        """)
        timestamp = 1784073600003
        self.assertEqual(module.delete_capture_benchmarks(
            connection, ["capture-1"], timestamp), ["benchmark-1"])
        self.assertEqual(connection.execute(
            "select family,item_id,reason,timestamp from knowledge_privacy_tombstones").fetchone(),
            ("benchmark", "benchmark-1", "forgotten", timestamp))
        self.assertEqual(connection.execute(
            "select value from ledger_meta where key='knowledge_privacy_sequence'").fetchone(), ("1",))
        self.assertIsNone(connection.execute("select 1 from benchmark_effects").fetchone())
        connection.close()

    def test_knowledge_privacy_digest_corruption_fails_closed(self):
        state = Path(self.temp.name) / "knowledge-privacy-corrupt"
        run(self.repo, "review-prune", "--state-root", str(state))
        connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
        connection.execute("insert into knowledge_privacy_tombstones values "
                           "('telemetry','session-1','forgotten',1784073600000)")
        connection.commit()
        connection.close()
        failed = run(self.repo, "knowledge-privacy-status", "--state-root", str(state), ok=False)
        self.assertIn("privacy digest mismatch", failed.stderr)

    def test_knowledge_export_is_deterministic_and_digest_bound(self):
        state = Path(self.temp.name) / "knowledge-export"
        first = run(self.repo, "knowledge-export", "--state-root", str(state)).stdout
        second = run(self.repo, "knowledge-export", "--state-root", str(state)).stdout
        self.assertEqual(first, second)
        lines = first.splitlines()
        records = [json.loads(line) for line in lines]
        self.assertEqual(records[0]["type"], "manifest")
        self.assertEqual(records[-1]["type"], "terminal")
        self.assertEqual(records[0]["privacy_sequence"], 0)
        self.assertEqual(
            records[-1]["digest"],
            hashlib.sha256("".join(f"{line}\n" for line in lines[:-1]).encode()).hexdigest(),
        )
        self.assertEqual(
            set(records[0]["families"]),
            {"cycle", "gate_evidence", "review", "history_report", "history_capture",
             "telemetry", "benchmark", "execution", "provider_evaluation", "improvement"},
        )

    def test_knowledge_export_rejects_unsafe_payload(self):
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_knowledge_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "unsafe content"):
            module.knowledge_record("review", "example", {"notes": "https://example.invalid/raw"})
        with self.assertRaisesRegex(RuntimeError, "unsafe content"):
            module.knowledge_record("review", "example", {"summary": "A" * 40})
        with self.assertRaisesRegex(RuntimeError, "unsafe content"):
            module.knowledge_record("review", "example", {"scorecards": ["B" * 40]})


if __name__ == "__main__":
    unittest.main()
