"""Focused subprocess contracts for dbsctrctl."""

import json
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import os
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
GATES = (
    "domain", "behavior", "spec", "contract", "test_driven_implementation",
    "refactor", "review_integrate", "release", "deploy", "operate", "maintain_retire",
)


def run(repo, *args, ok=True, env=None, input_text=None):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=repo, text=True, capture_output=True,
        env=env, input=input_text,
    )
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr}")
    if not ok and not result.returncode:
        raise AssertionError(f"{args}: unexpectedly succeeded")
    return result


def ledger_text(state):
    connection = sqlite3.connect(state / "reviews/ledger.sqlite3")
    try:
        values = []
        for table, column in (("review_reports", "payload"), ("history_evidence", "payload"),
                              ("history_reports", "payload"), ("ledger_entries", "text")):
            values.extend(row[0] for row in connection.execute(f"SELECT {column} FROM {table}"))
        return "".join(values)
    finally:
        connection.close()


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

    def start(self, intent="local"):
        plan = self.plan_path(intent)
        command = ["start", "--cycle-id", "cycle-1", "--context", "test",
                   "--risk", "routine", "--delivery-intent", intent, "--plan", str(plan)]
        if intent == "draft_pr":
            command += ["--github-account", "Saltiola7", "--github-repository", "Saltiola7/dotfiles-ai"]
        return run(self.repo, *command)

    def record_path(self, repo=None):
        return (repo or self.repo) / ".git/dbsctr/cycles/cycle-1.json"

    def review_artifacts(self):
        for name, result, reason in (
            ("README", "unchanged", "no durable truth changed"),
            ("BACKLOG", "unchanged", "already tracked"),
            ("CHANGELOG", "unchanged", "not finalized"),
        ):
            run(self.repo, "review-artifact", name, "--result", result, "--reason", reason)

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

    def test_start_records_current_method_revision_and_release_default(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["method_revision"], "3.19")
        self.assertEqual(record["schema_version"], 3)
        self.assertEqual(record["evidence"], {"version": 1, "items": {}})
        self.assertEqual(record["engineering_profile"]["path"], "docs/specs/test/README.md")
        self.assertRegex(record["engineering_profile"]["blob"], r"^[0-9a-f]+$")
        self.assertEqual(record["state"], "active")
        self.assertIsNone(record["git"]["upstream"])
        self.assertEqual(record["gates"]["release"], {
            "applicability": "not_applicable", "result": "not_run", "reason": "delivery intent is not release"
        })
        self.assertEqual(set(record["artifact_reviews"]), {"README", "BACKLOG", "CHANGELOG"})

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
        record["schema_version"] = 99
        record_path.write_text(json.dumps(record))
        result = run(self.repo, "status", ok=False)
        self.assertIn("unsupported Cycle Record schema", result.stderr)

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
        self.assertEqual(record["worktree"]["path"], str(isolated))
        self.assertEqual(record["source"]["path"], str(self.repo.resolve()))
        self.assertEqual(record["source"]["dirty_paths"], ["tracked.txt"])
        self.assertEqual(record["runtime"]["opencode"]["session_ids"], ["session-structured"])
        self.assertEqual(json.loads(run(isolated, "status", "--json").stdout)["cycle_id"], "isolated-1")
        self.assertEqual(run(self.repo, "status", "--json").stdout.strip(), "null")

    def test_attach_runtime_is_idempotent_and_worktree_bounded(self):
        self.start()
        run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed",
            "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo))
        run(self.repo, "attach-runtime", "--opencode-session-id", "session-resumed",
            "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo))
        record = json.loads(self.record_path().read_text())
        self.assertEqual(record["runtime"]["opencode"]["session_ids"], ["session-resumed"])
        other = Path(self.temp.name) / "other"
        other.mkdir()
        wrong = run(self.repo, "attach-runtime", "--opencode-session-id", "session-wrong",
                    "--opencode-directory", str(other),
                    "--opencode-worktree", str(other), ok=False)
        self.assertIn("recorded cycle worktree", wrong.stderr)

        record["state"] = "completed"
        self.record_path().write_text(json.dumps(record))
        completed = run(self.repo, "attach-runtime", "--opencode-session-id", "session-late",
                        "--opencode-directory", str(self.repo), "--opencode-worktree", str(self.repo),
                        ok=False)
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
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        fake_dvc = fake_bin / "dvc"
        custom_cache = Path(self.temp.name) / "custom-dvc-cache"
        custom_cache.mkdir()
        fake_dvc.write_text(
            f"#!/bin/sh\nif [ \"$#\" -eq 2 ]; then printf '%s\\n' '{custom_cache}'; "
            "else printf '%s\\n' \"$4\" > .dvc/config.local; fi\n"
        )
        fake_dvc.chmod(0o755)
        env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
        handoff = json.loads(run(
            self.repo, "begin", "--cycle-id", "isolated-1", "--context", "test",
            "--risk", "routine", "--delivery-intent", "local", "--plan", str(self.plan_path()),
            "--worktree-root", str(Path(self.temp.name) / "isolated"), env=env,
        ).stdout)
        configured = (Path(handoff["worktree"]) / ".dvc/config.local").read_text().strip()
        self.assertEqual(configured, str(custom_cache.resolve()))

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
        loader = importlib.machinery.SourceFileLoader("dbsctrctl_cleanup_module", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with mock.patch.object(module, "root_dir", return_value=self.repo), \
             mock.patch.object(module.shutil, "rmtree", side_effect=OSError("interrupted cleanup")):
            with self.assertRaises(OSError):
                module.command_cleanup(SimpleNamespace(cycle_id="isolated-1", now=True))
        parked_record = json.loads(record_path.read_text())
        self.assertEqual(parked_record["cleanup"]["state"], "evidence_parked")
        self.assertTrue((evidence.parent / "isolated-1.cleanup").exists())
        run(self.repo, "cleanup", "--cycle-id", "isolated-1", "--now")
        self.assertFalse(Path(handoff["worktree"]).exists())
        self.assertFalse(record_path.exists())
        self.assertFalse(evidence.exists())

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
        self.assertIn("cycle worktree branch changed", result.stderr)

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
        self.assertIn(("missing_lifecycle_artifact", "docs/specs/incomplete/BACKLOG.md"), findings)
        self.assertIn(("missing_lifecycle_artifact", "docs/specs/incomplete/CHANGELOG.md"), findings)
        self.assertIn(("stale_graph", "graphify-out/GRAPH_REPORT.md"), findings)

    def test_audit_flags_unverifiable_graph_metadata(self):
        graph = self.repo / "graphify-out"
        graph.mkdir()
        (graph / "GRAPH_REPORT.md").write_text("Built from commit: `abc`\n")
        subprocess.run(["git", "add", "graphify-out"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "bad graph marker"], cwd=self.repo, check=True,
                       capture_output=True)
        result = json.loads(run(self.repo, "audit", "--json").stdout)
        self.assertIn("unverified_graph_freshness", {item["code"] for item in result["findings"]})

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

    def test_final_push_targets_recorded_upstream_branch(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD:main"], cwd=self.repo, check=True,
            capture_output=True,
        )
        self.start()
        (self.repo / "tracked.txt").write_text("cycle\n")
        (self.repo / "docs/specs/test/CHANGELOG.md").write_text("completed\n")
        self.record_gate("domain", paths=("tracked.txt", "docs/specs/test/CHANGELOG.md"))
        run(
            self.repo, "gate-commit", "--message", "cycle change", "--gates", "domain", "--paths",
            "tracked.txt", "docs/specs/test/CHANGELOG.md",
        )
        run(self.repo, "review-artifact", "README", "--result", "unchanged", "--reason", "accurate")
        run(self.repo, "review-artifact", "BACKLOG", "--result", "unchanged", "--reason", "accurate")
        run(
            self.repo, "review-artifact", "CHANGELOG", "--result", "changed",
            "--reason", "recorded", "--path", "docs/specs/test/CHANGELOG.md",
        )
        self.pass_gates()
        run(self.repo, "final-push")
        local = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                               capture_output=True).stdout.strip()
        pushed = subprocess.run(["git", "rev-parse", "refs/heads/main"], cwd=remote, check=True,
                                text=True, capture_output=True).stdout.strip()
        self.assertEqual(local, pushed)

    def test_draft_pr_pushes_only_feature_branch_and_verifies_draft(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=self.repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD:main"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "checkout", "-b", "dbsctr/test/cycle-1"], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(["git", "branch", "--set-upstream-to", "origin/main"], cwd=self.repo, check=True,
                       capture_output=True)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True,
                              capture_output=True).stdout.strip()
        self.start("draft_pr")
        home = Path(self.temp.name) / "home"
        home.mkdir()
        worker_env = {**os.environ, "HOME": str(home)}
        run(self.repo, "improvement-register", "--worker-id", "worker-1", "--session-id", "session-1",
            env=worker_env)
        run(self.repo, "improvement-claim", "--session-id", "session-1",
            "--summary", "Improve draft delivery", env=worker_env)
        run(self.repo, "improvement-update", "--session-id", "session-1", "--state", "discovery",
            env=worker_env)
        run(self.repo, "improvement-update", "--session-id", "session-1", "--state", "implementing",
            "--cycle-id", "cycle-1", "--path", "tracked.txt", env=worker_env)
        record = json.loads(self.record_path().read_text())
        record["runtime"] = {"opencode": {"session_ids": ["session-1"],
                                             "worktree": str(self.repo), "directory": str(self.repo)}}
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
        fake_bin = Path(self.temp.name) / "bin"
        fake_bin.mkdir()
        gh_log = Path(self.temp.name) / "gh.log"
        gh = fake_bin / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            "printf '<%s>\\n' \"$@\" >> \"$GH_LOG\"\n"
            "[ -n \"${GH_TOKEN:-}\" ] && printf 'TOKEN_SET\\n' >> \"$GH_LOG\"\n"
            "case \"$1 $2\" in\n"
            "  'auth token') printf 'test-token\\n' ;;\n"
            "  'pr list') printf '[]\\n' ;;\n"
            "  'pr create') printf 'https://github.com/Saltiola7/dotfiles-ai/pull/1\\n' ;;\n"
            "  'pr view') printf '%s\\n' '{\"number\":1,\"url\":\"https://github.com/Saltiola7/dotfiles-ai/pull/1\",\"isDraft\":true,\"state\":\"OPEN\",\"baseRefName\":\"main\",\"headRefName\":\"dbsctr/test/cycle-1\"}' ;;\n"
            "esac\n"
        )
        gh.chmod(0o755)
        env = {**worker_env, "PATH": f"{fake_bin}:{os.environ['PATH']}", "GH_LOG": str(gh_log)}
        result = run(self.repo, "final-push", env=env)
        self.assertIn("draft_pr", result.stdout)
        feature = subprocess.run(["git", "rev-parse", "refs/heads/dbsctr/test/cycle-1"], cwd=remote,
                                 check=True, text=True, capture_output=True).stdout.strip()
        main = subprocess.run(["git", "rev-parse", "refs/heads/main"], cwd=remote, check=True,
                              text=True, capture_output=True).stdout.strip()
        self.assertEqual(feature, subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
                                                 text=True, capture_output=True).stdout.strip())
        self.assertEqual(main, base)
        log = gh_log.read_text()
        self.assertIn("<auth>\n<token>\n<--hostname>\n<github.com>\n<--user>\n<Saltiola7>", log)
        self.assertIn("<pr>\n<create>", log)
        self.assertNotIn("<merge>", log)
        record = json.loads(self.record_path().read_text())
        self.assertTrue(record["delivery"]["pull_request"]["draft"])
        self.assertEqual(record["source_sync"]["status"], "not_applicable")
        worker = json.loads(run(self.repo, "improvement-status", "--worker-id", "worker-1",
                                env=worker_env).stdout)["workers"][0]
        self.assertEqual(worker["state"], "draft_pr")
        self.assertEqual(worker["pr_number"], 1)

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
        env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}", "DVC_LOG": str(dvc_log)}
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
        env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
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
        self.assertEqual(module.correlated_cycles(str(self.repo / "docs"), set()), [
            {"cycle_id": "cycle-1", "state": "active"},
        ])

    def test_review_correlation_rejects_ambiguous_source_checkout(self):
        self.start()
        first = json.loads(self.record_path().read_text())
        first["worktree"]["path"] = str(Path(self.temp.name) / "removed-worktree")
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
        record["worktree"]["path"] = str(Path(self.temp.name) / "other")
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
            self.assertEqual(module.correlated_cycles(
                str(Path(self.temp.name) / "missing"), set(), {"session-linked"}), [
                {"cycle_id": "cycle-1", "state": "abandoned"},
            ])
        finally:
            os.chdir(previous)

    def test_review_correlation_uses_tiered_unambiguous_identity(self):
        self.start()
        first = json.loads(self.record_path().read_text())
        first["runtime"] = {"opencode": {"session_ids": ["runtime-root"]}}
        first["source"] = {"path": str(self.repo)}
        self.record_path().write_text(json.dumps(first))
        second = json.loads(json.dumps(first))
        second["cycle_id"] = "cycle-2"
        second["runtime"] = {"opencode": {"session_ids": ["other-root"]}}
        second["worktree"]["path"] = str(Path(self.temp.name) / "other-worktree")
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
        self.assertEqual(exact, [{"cycle_id": "cycle-1", "state": "active"}])
        self.assertEqual(quality, "exact")
        exact, quality = module.correlated_cycles(
            str(self.repo), {"cycle-2"}, {"runtime-root"}, exact_session_id="runtime-root",
            with_quality=True,
        )
        self.assertEqual(exact, [{"cycle_id": "cycle-1", "state": "active"}])
        self.assertEqual(quality, "exact")
        family, quality = module.correlated_cycles(
            str(self.repo), set(), {"runtime-root"}, exact_session_id="child", with_quality=True,
        )
        self.assertEqual(family, [{"cycle_id": "cycle-1", "state": "active"}])
        self.assertEqual(quality, "family")

        first["runtime"] = {"opencode": {"session_ids": ["shared-parent"]}}
        self.record_path().write_text(json.dumps(first))
        second["runtime"] = {"opencode": {"session_ids": ["shared-parent"]}}
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        ambiguous, quality = module.correlated_cycles(
            str(self.repo), set(), {"shared-parent"}, exact_session_id="shared-parent",
            with_quality=True,
        )
        self.assertEqual(ambiguous, [])
        self.assertEqual(quality, "ambiguous")
        worktree, quality = module.correlated_cycles(
            str(self.repo), set(), {"shared-parent"}, exact_session_id="child", with_quality=True,
        )
        self.assertEqual(worktree, [{"cycle_id": "cycle-1", "state": "active"}])
        self.assertEqual(quality, "worktree")

        first["worktree"]["path"] = str(Path(self.temp.name) / "missing-one")
        self.record_path().write_text(json.dumps(first))
        second["worktree"]["path"] = str(Path(self.temp.name) / "missing-two")
        (self.record_path().parent / "cycle-2.json").write_text(json.dumps(second))
        ambiguous, quality = module.correlated_cycles(
            str(self.repo), set(), set(), exact_session_id="unlinked", with_quality=True,
        )
        self.assertEqual(ambiguous, [])
        self.assertEqual(quality, "ambiguous")

    def test_review_correlates_recursive_family_and_reports_quality(self):
        self.start()
        record = json.loads(self.record_path().read_text())
        record["runtime"] = {"opencode": {"session_ids": ["runtime-root"]}}
        record["worktree"]["path"] = str(Path(self.temp.name) / "missing")
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
        self.assertEqual(candidates["grandchild"]["cycles"], [
            {"cycle_id": "cycle-1", "state": "abandoned"},
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
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [{"cycle_id": "cycle-1", "state": "blocked"}])
        record["gates"]["domain"]["exception"] = {"kind": "accepted_risk"}
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [{"cycle_id": "cycle-1", "state": "blocked"}])
        record["gates"]["domain"]["exception"] = {
            "kind": "accepted_risk", "rationale": "bounded", "owner": "maintainer",
            "review_condition": "next revision", "approved_at": "not-a-time",
        }
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [{"cycle_id": "cycle-1", "state": "blocked"}])
        record["gates"]["domain"]["exception"]["approved_at"] = "2026-07-15T00:00:00Z"
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [{"cycle_id": "cycle-1", "state": "active"}])
        record["gates"]["domain"]["applicability"] = "not_applicable"
        record["gates"]["domain"].pop("exception")
        self.record_path().write_text(json.dumps(record))
        self.assertEqual(module.correlated_cycles(str(self.repo), set()), [{"cycle_id": "cycle-1", "state": "active"}])

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
        self.assertRegex(history["candidates"][0]["project_digest"], r"^[0-9a-f]{64}$")
        older = json.loads(run(
            self.repo, "review-history", "--database", str(database), "--state-root", str(state),
            "--limit", "100", "--cursor", "100", "--snapshot", str(history["snapshot"]),
            "--session-ceiling", str(history["session_ceiling"]), "--part-ceiling", str(history["part_ceiling"]),
            "--database-digest", history["database_digest"],
        ).stdout)
        self.assertEqual(older["session_ids"], ["session-000"])
        backfill = {
            "schema_version": 1, "cohort": ["session-100"], "query_digest": history["digest"],
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
        self.assertEqual(first["candidates"][0]["method_revision"], "3.19")
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
        connection.execute("insert into review_tombstones values ('forgotten_session', 'forgotten-1', 1784073600003)")
        connection.commit()
        connection.close()
        run(self.repo, "review-restore", "--state-root", str(state), "--backup", backup["backup"])
        connection = sqlite3.connect(ledger)
        self.assertEqual(connection.execute(
            "select timestamp from review_tombstones where kind='forgotten_session'"
        ).fetchone()[0], 1784073600003)
        connection.close()

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
            "--workspace-id", "workspace-1", "--tab-id", "tab-1", "--pane-id", "pane-1",
        ).stdout)
        self.assertEqual(registered["state"], "reviewing")
        self.assertIsNone(registered["opportunity_id"])
        first = json.loads(run(
            self.repo, "improvement-claim", "--state-root", str(state),
            "--session-id", "session-1", "--summary", summary,
        ).stdout)
        self.assertRegex(first["opportunity_id"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["state"], "claimed")
        bypass = run(
            self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "implementing",
            "--cycle-id", "cycle-1", "--path", "tracked.txt", ok=False,
        )
        self.assertIn("claimed -> implementing", bypass.stderr)
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery")
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
        ledger = state / "reviews/ledger.sqlite3"
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)

    def test_improvement_scope_claims_reject_overlapping_paths(self):
        state = Path(self.temp.name) / "improvement-scope"
        for worker, session, summary in (
            ("worker-1", "session-1", "Improve lifecycle helper"),
            ("worker-2", "session-2", "Improve supervisor policy"),
        ):
            run(self.repo, "improvement-claim", "--state-root", str(state),
                "--worker-id", worker, "--session-id", session, "--summary", summary)
            run(self.repo, "improvement-update", "--state-root", str(state),
                "--worker-id", worker, "--state", "discovery")
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
            "--summary", "Recover exact worker sessions")
        run(self.repo, "improvement-update", "--state-root", str(state),
            "--worker-id", "worker-1", "--state", "discovery",
            "--workspace-id", "workspace-1", "--tab-id", "tab-1", "--pane-id", "pane-1")
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


if __name__ == "__main__":
    unittest.main()
