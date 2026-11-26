"""Execution reuse through a real lifecycle cycle, with a synthetic managed owner."""

import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys

import pytest
import test_dbsctrctl as harness
from test_completion_binding_cli import amend_policy
from test_completion_reconciliation import pending_deletion_merge
from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture, git, task


TRACKED = "tracked.txt"
SECOND_TRACKED = "docs/specs/test/CHANGELOG.md"
OUTSIDE_SCOPE = "docs/specs/test/BACKLOG.md"
CHECK = "focused"
SNAPSHOT = "a" * 64
PIN = "b" * 64
FAILED_TEST = "tests/test_example.py::test_example"


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    for key in harness.STATE_ENVIRONMENT:
        monkeypatch.delenv(key, raising=False)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(key, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


@pytest.fixture
def cycle(fixture):
    root = task(fixture)
    path = fixture.record_path()
    harness.run(root, "start", "--cycle-id", "cycle-1", "--context", "test",
                "--risk", "routine", "--delivery-intent", "local", "--base-branch",
                "master", "--plan", str(fixture.plan_path()))
    return root, path


def read_record(path):
    return json.loads(path.read_bytes())


def record_execution(root, gate="domain", *, program=None, path=TRACKED, authority="reuse-test"):
    if program is None:
        program = ("-c", "print('ok')")
    return harness.run(root, "record-evidence", gate, "--authority", authority,
                       "--path", path, "--", sys.executable, *program).stdout.strip()


def refuse_reference(cycle, gate, execution, code, *options):
    root, path = cycle
    before = path.read_bytes()
    head = git(root, "rev-parse", "HEAD")
    response = harness.run(root, "reference-evidence", gate, "--of", execution,
                           *options, ok=False)
    assert code in response.stderr + response.stdout
    assert path.read_bytes() == before
    assert git(root, "rev-parse", "HEAD") == head


def test_reference_preserves_merge_absence_proof(cycle):
    root, path = cycle
    pending_deletion_merge(root)
    source_id = record_execution(root)
    reference_id = harness.run(root, "reference-evidence", "behavior", "--of", source_id).stdout.strip()
    items = read_record(path)["evidence"]["items"]
    for key in ("absences", "absence_sources", "absence_merge_head"):
        assert items[reference_id][key] == items[source_id][key]


def test_reference_rejects_aborted_merge_predecessor(cycle):
    root, _ = cycle
    pending_deletion_merge(root)
    record_execution(root)
    source_id = record_execution(root, "behavior", path=SECOND_TRACKED, authority="independent")
    git(root, "merge", "--abort")
    refuse_reference(cycle, "spec", source_id, "evidence merge predecessor is no longer pending")


def test_reference_reads_literal_ignored_witness(cycle):
    root, path = cycle
    (root / ".gitignore").write_text("/.dbsctr/\n")
    witness = ".dbsctr/witness[1].txt"
    (root / witness).parent.mkdir()
    (root / witness).write_text("literal evidence\n")
    source_id = record_execution(root, path=witness)
    reference_id = harness.run(root, "reference-evidence", "behavior", "--of", source_id).stdout.strip()
    items = read_record(path)["evidence"]["items"]
    assert items[reference_id]["paths"] == items[source_id]["paths"]
    assert not git(root, "diff", "--cached", "--name-only")


def test_isolated_authority_reads_only_selected_witness_and_pending_merge(cycle):
    root, _ = cycle
    target, _ = pending_deletion_merge(root)
    (root / ".gitignore").write_text("/.dbsctr/\n")
    witness = ".dbsctr/witness[1].txt"
    (root / witness).parent.mkdir()
    (root / witness).write_bytes(b"selected\n")
    (root / ".dbsctr/other.txt").write_bytes(b"not selected\n")
    command = (
        "import pathlib, subprocess, sys; "
        "assert pathlib.Path.cwd() != pathlib.Path(sys.argv[1]); "
        "assert pathlib.Path(sys.argv[2]).read_bytes() == b'selected\\n'; "
        "assert not pathlib.Path('.dbsctr/other.txt').exists(); "
        "assert not pathlib.Path('tracked.txt').exists(); "
        "assert subprocess.check_output(['git', 'rev-parse', 'MERGE_HEAD'], "
        "text=True).strip() == sys.argv[3]"
    )
    harness.run(root, "record-evidence", "domain", "--authority", "Isolated inputs",
                "--path", witness, "--path", TRACKED, "--",
                sys.executable, "-c", command, str(root), witness, target)


def test_same_head_cross_gate_reference_owns_decision_and_can_gate_commit(cycle):
    root, path = cycle
    (root / TRACKED).write_text("validated worktree content\n")
    program = ("-c", "import pathlib,tempfile; "
               "p=pathlib.Path(tempfile.gettempdir())/'executions'; "
               "p.write_text('run\\n'); print('ok')")
    original_id = record_execution(root, program=program)
    before = read_record(path)
    original = before["evidence"]["items"][original_id]
    assert original["result"] == "passed"
    assert before["gates"]["behavior"]["result"] == "pending"

    # Existing set-gate must not bypass reference admission or gate ownership.
    denied = harness.run(root, "set-gate", "behavior", "--result", "passed",
                         "--evidence", original_id, ok=False)
    assert "matching stored evidence ID" in denied.stderr
    assert read_record(path) == before

    response = harness.run(root, "reference-evidence", "behavior", "--of", original_id, "--json")
    after = read_record(path)
    reference_id = after["gates"]["behavior"]["evidence"]
    assert json.loads(response.stdout)["id"] == reference_id
    assert reference_id != original_id
    assert after["gates"]["behavior"]["result"] == "passed"
    assert after["gates"]["domain"] == before["gates"]["domain"]
    assert after["metrics"] == before["metrics"]
    assert after["commits"] == before["commits"]
    assert set(after["evidence"]["items"]) == {original_id, reference_id}
    assert after["evidence"]["items"][original_id] == original
    reference = after["evidence"]["items"][reference_id]
    assert reference["gate"] == "behavior" and reference["result"] == "passed"
    assert reference["references"] == original_id
    assert reference["execution_head"] == original["head"]
    assert reference["head"] == git(root, "rev-parse", "HEAD").strip()
    for key in ("paths", "authority", "argv", "raw", "started_at", "finished_at"):
        assert reference[key] == original[key]
    assert reference["content"] == {"status": "withheld", "reason": "referenced_execution"}

    response = harness.run(root, "gate-commit", "--message", "Both gate decisions",
                           "--gates", "domain", "behavior", "--paths", TRACKED)
    committed = read_record(path)
    assert committed["commits"][-1] == {
        "id": response.stdout.strip(), "gates": ["domain", "behavior"],
    }


@pytest.mark.parametrize(("condition", "code"), [
    ("unknown", "evidence_not_found"),
    ("failed", "evidence_not_passed"),
    ("stale", "evidence_scope_changed"),
    ("stale_and_advanced", "evidence_scope_changed"),
    ("head_only", "evidence_head_advanced"),
    ("outside_scope", "path_outside_scope"),
    ("predecessor", "gate predecessors are incomplete"),
])
def test_reference_refuses_first_applicable_rule_without_changing_record(cycle, condition, code):
    root, path = cycle
    options = ()
    gate = "behavior"
    if condition == "unknown":
        source = "ev-" + "f" * 32
    elif condition == "failed":
        source = record_execution(root, program=("-c", "raise SystemExit(1)"))
        assert read_record(path)["evidence"]["items"][source]["result"] == "failed"
    else:
        source = record_execution(root)
        if condition in ("head_only", "stale_and_advanced"):
            git(root, "commit", "--allow-empty", "-m", "Advance HEAD without changing tree")
        if condition in ("stale", "stale_and_advanced"):
            (root / TRACKED).write_text("different contents at reference time\n")
        elif condition == "outside_scope":
            options = ("--path", OUTSIDE_SCOPE)
        elif condition == "predecessor":
            gate = "spec"
    refuse_reference(cycle, gate, source, code, *options)


@pytest.mark.parametrize("same_content", [True, False])
def test_later_failure_only_supersedes_a_pass_on_the_same_content(cycle, tmp_path, same_content):
    root, path = cycle
    failure_switch = tmp_path / "force-failure"
    program = ("-c", "import pathlib,sys; sys.exit(pathlib.Path(sys.argv[1]).exists())",
               str(failure_switch))
    source = record_execution(root, program=program)
    original_text = (root / TRACKED).read_text()
    if not same_content:
        (root / TRACKED).write_text("another tested blob\n")
    failure_switch.touch()
    failed = record_execution(root, "behavior", program=program)
    assert read_record(path)["evidence"]["items"][failed]["result"] == "failed"
    (root / TRACKED).write_text(original_text)
    if same_content:
        refuse_reference(cycle, "behavior", source, "evidence_superseded")
    else:
        harness.run(root, "reference-evidence", "behavior", "--of", source)
        record = read_record(path)
        reference = record["gates"]["behavior"]["evidence"]
        assert record["evidence"]["items"][reference]["references"] == source
        assert record["evidence"]["items"][failed]["result"] == "failed"


def test_rerun_reopens_referencing_gate_without_altering_original_execution(cycle):
    root, path = cycle
    source = record_execution(root)
    harness.run(root, "reference-evidence", "behavior", "--of", source)
    before = read_record(path)
    old_reference = before["gates"]["behavior"]["evidence"]
    record_execution(root, program=("-c", "raise SystemExit(1)"))
    after = read_record(path)
    assert after["gates"]["behavior"] == {"applicability": "required", "result": "pending"}
    for key in (source, old_reference):
        assert after["evidence"]["items"][key] == before["evidence"]["items"][key]
    assert after["metrics"]["gate_reopen_count"] == before["metrics"]["gate_reopen_count"] + 1


@pytest.mark.parametrize("stale", [False, True])
def test_plan_is_read_only_and_ignores_predecessor_disposal(cycle, stale):
    root, path = cycle
    source = record_execution(root)
    if stale:
        (root / TRACKED).write_text("unvalidated replacement\n")
    before = path.read_bytes()
    head = git(root, "rev-parse", "HEAD")
    tree = git(root, "status", "--porcelain=v1")
    response = harness.run(root, "evidence-plan", "--gate", "spec", "--path", TRACKED, "--json")
    plan = json.loads(response.stdout)
    assert set(plan["gates"]) == {"spec"}
    selected = plan["gates"]["spec"]
    assert selected["result"] == "pending"
    assert selected["obligation"] == "undeclared"
    assert plan["selection"]["status"] == "unavailable"
    assert (source in json.dumps(selected["reusable"])) != stale
    assert path.read_bytes() == before
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "status", "--porcelain=v1") == tree


def begin_bound_cycle(initiative, capsys, *, mismatch=False):
    core, root, record_path, begin, _, plan_path = initiative
    program = (sys.executable, "-c", "print('ok')")
    receipt = core.initiative_receipt(root / "docs/initiatives/test/MANIFEST.json", "slice-a", root)
    declaration = {"authority": "reuse-test", "argv": list(program), "inputs": [TRACKED, OUTSIDE_SCOPE],
                   "environment": [], "toolchain_paths": [], "scope_complete": True}
    plan = read_record(plan_path)
    plan["evidence_policy"] = {
        "schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in receipt["requirements"]},
        "gates": {"domain": declaration, "behavior": {
            **declaration, "inputs": [TRACKED] if mismatch else declaration["inputs"],
        }},
    }
    plan_path.write_text(json.dumps(plan))
    args = begin[:-2]
    args[args.index("--expected-plan-digest") + 1] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    core.command_begin(core.parser().parse_args([*args, "--preflight"]))
    preflight = json.loads(capsys.readouterr().out)
    harness.run(root, *args, "--expected-launch-digest", preflight["launch_digest"],
                "--approval", "agent-confirmed")
    return core, root, record_path, plan_path


@pytest.mark.parametrize("scenario", ["identical", "mismatch", "binding_stale"])
def test_cross_head_binding_is_recomputed_for_the_receiving_gate(initiative, capsys, scenario):
    core, root, path, _ = begin_bound_cycle(initiative, capsys, mismatch=scenario == "mismatch")
    source = record_execution(root)
    before = read_record(path)
    payload = core.load_evidence_binding(root, before, source)
    if scenario == "binding_stale":
        # Change a declared input not included in the source's recorded output paths.
        (root / OUTSIDE_SCOPE).write_text("different declared input\n")
    git(root, "commit", "--allow-empty", "-m", "Advance head outside the declaration")
    if scenario != "identical":
        code = "declaration_mismatch" if scenario == "mismatch" else "binding_unavailable"
        refuse_reference((root, path), "behavior", source, code)
        return
    result = harness.run(root, "reference-evidence", "behavior", "--of", source, "--json")
    identifier = json.loads(result.stdout)["id"]
    after = read_record(path)
    inherited = core.load_evidence_binding(root, after, identifier)
    assert inherited["gate"] == "behavior"
    assert inherited["gate_policy_digest"] != payload["gate_policy_digest"]
    for field in ("command_digest", "inputs", "toolchain", "environment"):
        assert inherited[field] == payload[field]
    assert after["evidence"]["items"][source] == before["evidence"]["items"][source]
    assert core.completion_evidence_dispositions(root, after)["behavior"]["disposition"] == "retained"


def test_reopening_amendment_refuses_earlier_execution(initiative, capsys):
    core, root, path, plan_path = begin_bound_cycle(initiative, capsys)
    source = record_execution(root)
    plan = read_record(plan_path)
    for requirement in plan["evidence_policy"]["requirements"].values():
        requirement["revision"] = "2"
    plan_path.write_text(json.dumps(plan))
    amend_policy(core, root, path, plan_path, capsys)
    assert read_record(path)["gates"]["domain"]["result"] == "pending"
    refuse_reference((root, path), "domain", source, "evidence_predates_authority")


@pytest.fixture
def lifecycle_cli(cycle, monkeypatch, capsys):
    """Run the real parser, dispatcher and storage, replacing only the owner call."""
    root, _ = cycle
    loader = importlib.machinery.SourceFileLoader("evidence_reuse_lifecycle", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.chdir(root)
    monkeypatch.setattr(core, "managed_validation_enabled", lambda: True)

    def invoke(owner, *args):
        monkeypatch.setattr(core, "managed_validation_action", owner)
        monkeypatch.setattr(sys, "argv", [str(harness.SCRIPT), *args])
        try:
            status = core.main()
        except SystemExit as error:
            status = error.code
        output = capsys.readouterr()
        return status, output.out, output.err

    return invoke


class SyntheticOwner:
    """Minimal versioned owner payloads; none of the lifecycle decisions are faked."""

    def __init__(self, root, *observations, checks=None, applicable=True):
        self.root = root
        self.checks = [CHECK] if checks is None else checks
        self.observations = observations
        self.applicable = applicable
        self.calls = []
        self.test_identity = {"schema_version": 1, "kind": "not_applicable"}
        self.base = git(root, "rev-parse", "HEAD").strip()
        self.snapshot = SNAPSHOT
        self.content_digest = "f" * 64
        self.selection_pin = PIN
        self.generation = 1
        self.started_at = "2026-11-24T00:00:00Z"
        self.finished_at = "2026-11-24T00:00:01Z"

    def __call__(self, action, event):
        assert event["worktree"] == self.root.resolve()
        assert event["cycle"] == "cycle-1"
        self.calls.append((action, event))
        if action == "selection":
            return {"schema_version": 1, "status": "completed", "basis": "affected",
                    "checks": list(self.checks),
                    "selection_pin": self.selection_pin, "snapshot_id": self.snapshot,
                    "head": git(self.root, "rev-parse", "HEAD").strip(), "base": self.base,
                    "content_digest": self.content_digest,
                    "manifest_digest": "c" * 64, "selection_digest": "d" * 64,
                    "adapter": {"id": "synthetic", "digest": "c" * 64}}
        if action == "applicability":
            assert event["snapshot_id"] == self.snapshot
            return {"schema_version": 1, "applicable": self.applicable,
                    "reason": "current" if self.applicable else "source_changed",
                    "paths_in_scope": set(event.get("paths", [])) <= {TRACKED, SECOND_TRACKED}}
        assert action == "validate"
        request = event["request_id"]
        facts = {"head": git(self.root, "rev-parse", "HEAD").strip(), "base": self.base,
                 "adapter": {"id": "synthetic", "digest": "c" * 64},
                 "manifest_digest": "c" * 64,
                 "selection_digest": "d" * 64, "basis": "affected", "content_digest": self.content_digest,
                 "lane": {"executor": "native"}, "test_identity": self.test_identity,
                 "started_at": self.started_at, "finished_at": self.finished_at,
                 "elapsed_seconds": 0.5}
        return {"schema_version": 1, "status": "completed", "request_id": request,
                "snapshot_id": self.snapshot, "generation": self.generation, "new_execution": True,
                "selection_complete": True, "pending_checks": [],
                "manifest_digest": "c" * 64, "selection_digest": "d" * 64,
                "observations": [
                    {"id": f"{index + 1:032x}", "request_id": request, "check_id": check,
                      "status": status, "snapshot_id": self.snapshot, "generation": self.generation,
                     "executed": executed, "cache_reused": not executed,
                     "receipt": facts,
                     "failed_test_ids": [FAILED_TEST] if status == "failed" else [],
                     "diagnostic_codes": []}
                    for index, (check, status, executed) in enumerate(self.observations)
                ]}


@pytest.mark.parametrize(("status", "executed", "exit_code", "retained"), [
    ("passed", True, 0, True),
    ("failed", True, 1, True),
    ("passed", False, 0, False),
    ("unavailable", True, 2, False),
    ("interrupted", True, 2, False),
    ("pending", False, 2, False),
])
def test_validate_stores_only_executed_terminal_observations_without_touching_gate_state(
        cycle, lifecycle_cli, status, executed, exit_code, retained):
    root, path = cycle
    (root / TRACKED).write_text("exploratory edit\n")
    before, head = read_record(path), git(root, "rev-parse", "HEAD")
    owner = SyntheticOwner(root, (CHECK, status, executed))
    rc, out, err = lifecycle_cli(owner, "validate", "--check", CHECK, "--json")
    assert rc == exit_code, out + err
    report = json.loads(out)
    if status == "failed":
        assert FAILED_TEST in json.dumps(report)
    executions = [event for action, event in owner.calls if action == "validate"]
    assert len(executions) == 1 and executions[0]["check_ids"] == [CHECK]

    after = read_record(path)
    receipts = after["evidence"].pop("receipts", {})
    assert len(receipts) == int(retained)
    if retained:
        identifier, receipt = next(iter(receipts.items()))
        assert identifier in json.dumps(report)
        assert receipt["result"] == status
        assert receipt["check_id"] == CHECK
        assert receipt["snapshot_id"] == SNAPSHOT
    assert not before["evidence"].pop("receipts", {})
    assert after == before
    assert git(root, "rev-parse", "HEAD") == head


def test_affected_validate_skips_reusable_receipt_and_receipt_survives_gate_commit(cycle, lifecycle_cli):
    root, path = cycle
    (root / TRACKED).write_text("captured before the first gate commit\n")
    (root / SECOND_TRACKED).write_text("also captured before the first gate commit\n")
    owner = SyntheticOwner(root, (CHECK, "passed", True))
    rc, out, err = lifecycle_cli(owner, "validate", "--json")
    assert rc == 0, out + err
    assert ("validate", [CHECK]) in [(action, event.get("check_ids")) for action, event in owner.calls]
    execution = next(event for action, event in owner.calls if action == "validate")
    assert execution["selection_pin"] == PIN
    receipts = read_record(path)["evidence"]["receipts"]
    identifier, receipt = next(iter(receipts.items()))
    before = path.read_bytes()
    owner.calls.clear()
    rc, out, err = lifecycle_cli(owner, "validate", "--json")
    assert rc == 0, out + err
    assert "reused" in out and identifier in out
    assert all(action != "validate" for action, _ in owner.calls)
    assert path.read_bytes() == before

    rc, out, err = lifecycle_cli(owner, "reference-evidence", "domain", "--of", identifier,
                                 "--path", TRACKED, "--json")
    assert rc == 0, out + err
    harness.run(root, "gate-commit", "--message", "First decision", "--gates", "domain", "--paths", TRACKED)
    head = git(root, "rev-parse", "HEAD").strip()
    assert head != receipt["head"]

    before = path.read_bytes()
    rc, out, err = lifecycle_cli(owner, "reference-evidence", "behavior", "--of", identifier,
                                 "--path", OUTSIDE_SCOPE)
    assert rc != 0 and "path_outside_scope" in out + err
    assert path.read_bytes() == before
    rc, out, err = lifecycle_cli(owner, "reference-evidence", "behavior", "--of", identifier,
                                 "--path", SECOND_TRACKED, "--json")
    assert rc == 0, out + err
    record = read_record(path)
    reference = record["evidence"]["items"][json.loads(out)["id"]]
    assert reference["references"] == identifier
    assert reference["head"] == head
    assert reference["execution_head"] == receipt["head"]
    assert record["evidence"]["receipts"] == receipts
    response = harness.run(root, "gate-commit", "--message", "Second decision", "--gates", "behavior",
                           "--paths", SECOND_TRACKED)
    assert read_record(path)["evidence"]["items"][reference["id"]]["commit"] == response.stdout.strip()


def test_later_failed_receipt_supersedes_same_content_across_snapshot_and_head(cycle, lifecycle_cli):
    root, path = cycle
    (root / TRACKED).write_text("same validated source across HEADs\n")
    passing = SyntheticOwner(root, (CHECK, "passed", True))
    rc, out, err = lifecycle_cli(passing, "validate", "--check", CHECK, "--json")
    assert rc == 0, out + err
    [source_id] = json.loads(out)["receipts"]

    git(root, "commit", "--allow-empty", "-m", "Advance HEAD without changing tested content")
    failing = SyntheticOwner(root, (CHECK, "failed", True))
    failing.base = passing.base
    failing.snapshot = "8" * 64
    failing.generation = 2
    failing.started_at = "2026-11-24T00:00:02Z"
    failing.finished_at = "2026-11-24T00:00:03Z"
    rc, out, err = lifecycle_cli(failing, "validate", "--check", CHECK, "--json")
    assert rc == 1, out + err
    [failure_id] = json.loads(out)["receipts"]
    receipts = read_record(path)["evidence"]["receipts"]
    old, new = receipts[source_id], receipts[failure_id]
    assert old["content_digest"] == new["content_digest"]
    assert old["snapshot_id"] != new["snapshot_id"]
    assert old["head"] != new["head"]
    assert old["finished_at"] < new["started_at"]

    before = path.read_bytes()
    rc, out, err = lifecycle_cli(passing, "reference-evidence", "domain", "--of", source_id,
                                 "--path", TRACKED, "--json")
    assert rc != 0 and "evidence_superseded" in out + err
    assert path.read_bytes() == before


@pytest.mark.parametrize(("field", "conflict"), [
    ("request_id", "7" * 32),
    ("generation", 2),
    ("snapshot_id", "8" * 64),
    ("cache_reused", True),
])
def test_validate_rejects_conflicting_observation_lineage_or_cache_flags(
        cycle, lifecycle_cli, field, conflict):
    root, path = cycle
    owner = SyntheticOwner(root, (CHECK, "passed", True))

    def conflicting_owner(action, event):
        result = owner(action, event)
        assert action == "validate"
        [observation] = result["observations"]
        assert observation[field] != conflict
        observation[field] = conflict
        return result

    before = path.read_bytes()
    rc, out, err = lifecycle_cli(conflicting_owner, "validate", "--check", CHECK, "--json")
    assert rc == 2, out + err
    assert json.loads(out)["receipts"] == []
    assert path.read_bytes() == before


@pytest.mark.parametrize(("action", "field"), [
    ("selection", "head"),
    ("selection", "content_digest"),
    ("validate", "content_digest"),
    ("validate", "manifest_digest"),
])
def test_validate_refuses_missing_owner_identity(cycle, lifecycle_cli, action, field):
    root, path = cycle
    owner = SyntheticOwner(root, (CHECK, "passed", True))

    def incomplete_owner(name, event):
        result = owner(name, event)
        if name == action:
            facts = result if name == "selection" else result["observations"][0]["receipt"]
            del facts[field]
        return result

    before = path.read_bytes()
    args = () if action == "selection" else ("--check", CHECK)
    rc, out, err = lifecycle_cli(incomplete_owner, "validate", *args, "--json")
    assert rc == 2, out + err
    assert not json.loads(out).get("receipts")
    assert [name for name, _ in owner.calls] == [action]
    assert path.read_bytes() == before


def test_validate_with_no_selected_checks_does_not_execute_or_store(cycle, lifecycle_cli):
    root, path = cycle
    before = path.read_bytes()
    owner = SyntheticOwner(root, checks=[])
    rc, out, err = lifecycle_cli(owner, "validate", "--json")
    assert rc == 0, out + err
    assert [action for action, _ in owner.calls] == ["selection"]
    assert path.read_bytes() == before


def test_plan_reports_stale_and_missing_selected_checks_without_execution(cycle, lifecycle_cli):
    root, path = cycle
    owner = SyntheticOwner(root, (CHECK, "passed", True), checks=[CHECK, "other"])
    (root / TRACKED).write_text("first exploration\n")
    rc, out, err = lifecycle_cli(owner, "validate", "--check", CHECK, "--json")
    assert rc == 0, out + err
    (root / TRACKED).write_text("other source content\n")
    owner.applicable = False
    owner.calls.clear()
    before = path.read_bytes()
    rc, out, err = lifecycle_cli(owner, "evidence-plan", "--gate", "domain", "--path", TRACKED, "--json")
    assert rc == 0, out + err
    plan = json.loads(out)
    assert plan["gates"]["domain"]["reusable"] == []
    assert plan["selection"]["checks"] == {
        CHECK: {"status": "stale", "reason": "evidence_scope_changed"},
        "other": {"status": "missing"},
    }
    assert all(action != "validate" for action, _ in owner.calls)
    assert path.read_bytes() == before


def test_export_writes_new_private_manifest_only_from_a_clean_head(cycle, lifecycle_cli, tmp_path):
    root, path = cycle
    owner = SyntheticOwner(root, (CHECK, "passed", True))
    rc, out, err = lifecycle_cli(owner, "validate", "--check", CHECK, "--json")
    assert rc == 0, out + err
    before = path.read_bytes()
    head = git(root, "rev-parse", "HEAD").strip()
    destination = tmp_path / "manifest.json"
    args = ("evidence-export", "--head", head, "--output")

    (root / TRACKED).write_text("dirty source\n")
    rc, out, err = lifecycle_cli(owner, *args, str(destination))
    assert rc != 0, out + err
    assert not destination.exists()
    git(root, "restore", TRACKED)
    tracked_bytes = (root / TRACKED).read_bytes()
    rc, out, err = lifecycle_cli(owner, *args, str(root / TRACKED))
    assert rc != 0, out + err
    assert (root / TRACKED).read_bytes() == tracked_bytes

    rc, out, err = lifecycle_cli(owner, *args, str(destination))
    assert rc == 0, out + err
    mode = destination.stat().st_mode
    assert stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o600
    manifest = json.loads(destination.read_bytes())
    assert manifest["schema_version"] == 1
    assert manifest["kind"] == "dbsctr-validation-manifest"
    assert manifest["head"] == head
    assert [item["check_id"] for item in manifest["executions"]] == [CHECK]
    assert str(root) not in destination.read_text() and "cycle-1" not in destination.read_text()
    exported = destination.read_bytes()
    rc, out, err = lifecycle_cli(owner, *args, str(destination))
    assert rc != 0, out + err
    assert destination.read_bytes() == exported

    owner.applicable = False
    stale_destination = tmp_path / "stale-manifest.json"
    rc, out, err = lifecycle_cli(owner, *args, str(stale_destination))
    assert rc == 0, out + err
    assert json.loads(stale_destination.read_bytes())["executions"] == []
    assert path.read_bytes() == before


@pytest.mark.parametrize("changed", ["selection", "record"])
def test_export_rejects_changed_selection_or_cycle_record(cycle, lifecycle_cli, tmp_path, changed):
    root, path = cycle
    owner = SyntheticOwner(root, (CHECK, "passed", True))
    rc, out, err = lifecycle_cli(owner, "validate", "--check", CHECK, "--json")
    assert rc == 0, out + err
    before = path.read_bytes()
    head = git(root, "rev-parse", "HEAD").strip()
    destination = tmp_path / "manifest.json"
    intervening_record = None
    checked_scope = False

    def changing_owner(action, event):
        nonlocal checked_scope, intervening_record
        result = owner(action, event)
        if action == "applicability" and not checked_scope:
            checked_scope = True
            if changed == "selection":
                owner.selection_pin = "8" * 64
            else:
                record_execution(root)
                intervening_record = path.read_bytes()
                assert intervening_record != before
        return result

    rc, out, err = lifecycle_cli(changing_owner, "evidence-export", "--head", head,
                                 "--output", str(destination))
    assert checked_scope
    assert rc != 0, out + err
    assert not destination.exists()
    assert path.read_bytes() == (intervening_record if changed == "record" else before)
    assert git(root, "rev-parse", "HEAD").strip() == head
    assert git(root, "status", "--porcelain=v1") == ""


def test_real_owner_preview_validate_reference_and_reuse(cycle, tmp_path, monkeypatch):
    from test_continuous_validation import ADAPTER, private_json
    from continuous_validation import checkpoints, cli, runner

    root, record_path = cycle
    # The owner's real cycle check resolves the uninstalled source CLI through this test-only PATH.
    shim = tmp_path / "bin/dbsctrctl"
    shim.parent.mkdir()
    shim.write_text(f"#!/bin/sh\nexec {shlex.join([sys.executable, str(harness.SCRIPT)])} \"$@\"\n")
    shim.chmod(0o700)
    monkeypatch.setenv("PATH", str(shim.parent) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    policy = private_json(Path.home() / ".config/dotfiles-ai/continuous-validation-policy.json",
                          {"enabled": True, "enrollment": "explicit-only"})
    adapter = root / ".ci/adapter.py"
    adapter.parent.mkdir()
    adapter.write_text(
        ADAPTER.replace("/'source.py'", "/'tracked.txt'")
        .replace("'configuration':{}", "'configuration':{'test_identity':'not_applicable'}")
        .replace("'runtime':{'python':platform.python_version()},'test_ids':['fixture::case']",
                 "'runtime':{'python':platform.python_version(),"
                 "'test_identity':{'schema_version':1,'kind':'not_applicable'}},'test_ids':[]")
    )
    (root / TRACKED).write_text("settled before committing\n")
    head = git(root, "rev-parse", "HEAD").strip()
    state = tmp_path / "validation-state"
    enrollment = {
        "schema_version": 1, "enabled": True, "mode": "shadow", "checkpoints_enabled": True,
        "worktree": str(root), "adapter": ".ci/adapter.py", "adapter_config": {},
        "adapter_digest": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "adapter_python": sys.executable, "repository_id": runner.repository_id(root),
        "session_id": "11111111-1111-4111-8111-111111111111", "cycle_id": "cycle-1",
        "base": head, "state_dir": str(state), "feedback_enabled": False, "load_limit": 1_000_000,
    }
    checkpoints.register(private_json(tmp_path / "enrollment.json", enrollment), enrollment)

    initial_record = record_path.read_bytes()
    preview = cli.managed_action("selection", worktree=root, cycle="cycle-1", policy_path=policy)
    assert preview["status"] == "completed", preview
    assert preview["checks"] == ["quick", "slow"]
    assert not state.exists()
    assert record_path.read_bytes() == initial_record

    result = subprocess.run([sys.executable, str(harness.SCRIPT), "validate", "--json"], cwd=root,
                            env=harness.isolated_env(), capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    initial = json.loads(result.stdout)
    record = read_record(record_path)
    receipts = {receipt["check_id"]: receipt for receipt in record["evidence"]["receipts"].values()}
    assert set(receipts) == set(preview["checks"])
    assert set(initial["receipts"]) == {receipt["id"] for receipt in receipts.values()}
    observations = state / "observations"
    for receipt in receipts.values():
        assert receipt["snapshot_id"] == preview["snapshot_id"]
        assert receipt["test_identity"] == {"schema_version": 1, "kind": "not_applicable"}
        observed = read_record(observations / (receipt["observation_id"] + ".json"))
        assert observed["status"] == "passed" and observed["executed"] is True
        assert observed["cache_reused"] is False

    original = receipts["quick"]["id"]
    reference_id = json.loads(harness.run(root, "reference-evidence", "domain", "--of", original,
                                          "--path", TRACKED, "--json").stdout)["id"]
    record = read_record(record_path)
    assert record["evidence"]["items"][reference_id]["references"] == original
    assert record["gates"]["domain"]["evidence"] == reference_id

    # A repeat must skip at the lifecycle selection boundary, not even submit an owner request.
    request_files = sorted((state / "requests").glob("*.json"))
    observation_files = sorted(observations.glob("*.json"))
    assert len(request_files) == 1 and len(observation_files) == len(receipts)
    before_repeat = record_path.read_bytes()
    repeat = json.loads(harness.run(root, "validate", "--json").stdout)
    assert repeat["receipts"] == []
    assert repeat["reused"] == {check: receipt["id"] for check, receipt in receipts.items()}
    assert sorted((state / "requests").glob("*.json")) == request_files
    assert sorted(observations.glob("*.json")) == observation_files
    assert record_path.read_bytes() == before_repeat
    assert git(root, "rev-parse", "HEAD").strip() == head
