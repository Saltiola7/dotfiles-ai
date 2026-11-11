"""Real approved local Initiative registration/capture; no remote runtime claims."""

import hashlib
import json
import sys

import pytest

from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture


def register_policy(initiative, capsys, *, program=None, runtime=False):
    core, target, path, argv, _, plan_path = initiative
    program = program or [sys.executable, "-c", "print('passed')"]
    receipt = core.initiative_receipt(target / "docs/initiatives/test/MANIFEST.json", "slice-a", target)
    plan = json.loads(plan_path.read_text())
    declaration = {"authority": "fixture", "argv": program, "inputs": ["tracked.txt"],
                   "environment": ["PROJECT_MODE"], "toolchain_paths": [], "scope_complete": True}
    if runtime:
        declaration["runtime"] = {"probe_argv": program, "probe_timeout_seconds": 5, "max_age_seconds": 3600}
    plan["evidence_policy"] = {"schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in receipt["requirements"]}, "gates": {"domain": declaration}}
    plan_path.write_text(json.dumps(plan))
    argv = argv[:-2]
    argv[argv.index("--expected-plan-digest") + 1] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    core.command_begin(core.parser().parse_args([*argv, "--preflight"]))
    prepared = json.loads(capsys.readouterr().out)
    core.command_begin(core.parser().parse_args([
        *argv, "--expected-launch-digest", prepared["launch_digest"], "--approval", "agent-confirmed"]))
    capsys.readouterr()
    return core, target, path, program


def capture(core, program):
    args = core.parser().parse_args(["record-evidence", "domain", "--authority", "fixture", "--", *program])
    return core.command_record_evidence(args)


def test_approved_policy_capture_is_immutable_and_private(initiative, capsys, monkeypatch):
    core, target, path, program = register_policy(initiative, capsys)
    monkeypatch.setenv("PROJECT_MODE", "PRIVATE_ENVIRONMENT_SENTINEL")
    capture(core, program)
    record = core.read_cycle_record(target, path)
    identifier = record["gates"]["domain"]["evidence"]
    original = json.loads(path.read_text())["evidence"]["items"][identifier]
    binding = core.load_evidence_binding(target, record, identifier)
    assert binding["command_digest"] == core.continuation_digest(program)
    assert binding["coverage"] == [{"id": name, "revision": "1"} for name in sorted(record["initiative"]["requirements"])]
    assert "PRIVATE_ENVIRONMENT_SENTINEL" not in repr(binding)
    assert json.loads(path.read_text())["evidence"]["items"][identifier] == original
    capsys.readouterr()
    core.command_status(core.parser().parse_args(["status", "--json"]))
    output = capsys.readouterr().out
    assert "PRIVATE_ENVIRONMENT_SENTINEL" not in output
    assert sys.executable not in output


def test_input_drift_retains_original_execution_but_no_binding(initiative, capsys):
    program = [sys.executable, "-c", "from pathlib import Path; Path('tracked.txt').write_text('changed'); print('passed')"]
    core, target, path, program = register_policy(initiative, capsys, program=program)
    with pytest.raises(RuntimeError, match="binding unavailable"):
        capture(core, program)
    record = core.read_cycle_record(target, path)
    assert record["gates"]["domain"]["result"] == "passed"  # Actual executed child, not applicability credit.
    assert not record["evidence"].get("bindings")
    assert (target / "tracked.txt").read_text() == "changed"


def test_invocation_mismatch_does_not_execute_or_mint_binding(initiative, capsys):
    core, target, path, _ = register_policy(initiative, capsys)
    program = [sys.executable, "-c", "raise AssertionError('must not execute')"]
    with pytest.raises(RuntimeError, match="invocation_mismatch"):
        capture(core, program)
    record = core.read_cycle_record(target, path)
    assert record["gates"]["domain"]["result"] == "unavailable"
    assert not record["evidence"].get("bindings")


def test_binding_write_failure_preserves_successful_original_execution(initiative, capsys, monkeypatch):
    core, target, path, program = register_policy(initiative, capsys)

    def unavailable(*args, **kwargs):
        raise OSError("Synthetic binding storage unavailable")

    monkeypatch.setattr(core, "store_evidence_binding", unavailable)
    with pytest.raises(RuntimeError, match="binding_custody_unavailable"):
        capture(core, program)
    record = core.read_cycle_record(target, path)
    gate = record["gates"]["domain"]
    assert gate["result"] == "passed" and record["evidence"]["items"][gate["evidence"]]["result"] == "passed"
    assert not record["evidence"].get("bindings")
    assert core.evidence_binding_applicability(target, record, "domain")["disposition"] == "unavailable"


def test_runtime_identity_comes_from_fresh_child_output(initiative, capsys, monkeypatch):
    identity = {"schema_version": 1, "artifact_digest": "a" * 64, "configuration_digest": "b" * 64,
                "target_digest": "c" * 64, "environment_digest": "d" * 64}
    code = "import json, os; from pathlib import Path; Path(os.environ['DBSCTR_EVIDENCE_OUTPUT']).write_text(" + repr(json.dumps(identity)) + "); print('passed')"
    program = [sys.executable, "-c", code]
    core, target, path, program = register_policy(initiative, capsys, program=program, runtime=True)
    monkeypatch.setenv("DBSCTR_EVIDENCE_OUTPUT", "DO_NOT_USE_CALLER_PATH")
    capture(core, program)
    record = core.read_cycle_record(target, path)
    payload = core.load_evidence_binding(target, record, record["gates"]["domain"]["evidence"])
    assert payload["runtime"]["identity"] == identity
    assert not (target / "DO_NOT_USE_CALLER_PATH").exists()


def amend_policy(core, target, path, plan_path, capsys):
    record = core.read_cycle_record(target, path)
    argv = ["initiative-amend", "--cycle-id", "cycle-1", "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
            "--initiative-slice", "slice-a", "--initiative-digest", record["initiative"]["manifest_digest"],
            "--plan", str(plan_path), "--expected-plan-digest", hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "--reason", "Synthetic policy revision", "--json"]
    capsys.readouterr()
    core.command_initiative_amend(core.parser().parse_args([*argv, "--preflight"]))
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["status"] == "preflight"
    apply = [*argv, "--expected-launch-digest", prepared["state_digest"], "--approval", "agent-confirmed"]
    core.command_initiative_amend(core.parser().parse_args(apply))
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "applied"
    return apply


def test_policy_only_revision_retains_unaffected_binding_and_retries_without_fake_git_commit(initiative, capsys):
    core, target, path, program = register_policy(initiative, capsys)
    capture(core, program)
    before = core.read_cycle_record(target, path)
    identifier = before["gates"]["domain"]["evidence"]
    original_head = core.git(target, "rev-parse", "HEAD").stdout
    plan_path = initiative[-1]
    plan = json.loads(plan_path.read_text())
    plan["evidence_policy"]["gates"]["contract"] = dict(plan["evidence_policy"]["gates"]["domain"])
    plan_path.write_text(json.dumps(plan))
    apply = amend_policy(core, target, path, plan_path, capsys)
    after = core.read_cycle_record(target, path)
    assert after["gates"]["domain"] == before["gates"]["domain"]
    assert after["evidence"]["items"][identifier] == before["evidence"]["items"][identifier]
    assert after["initiative_amendments"][-1]["schema_version"] == 3
    assert after["applicability_plan"] == before["applicability_plan"]
    assert core.git(target, "rev-parse", "HEAD").stdout == original_head
    core.require_amendment_completion(target, after)
    core.verify_envelope(target, after, "domain")
    snapshot = path.read_bytes()
    core.command_initiative_amend(core.parser().parse_args(apply))
    assert json.loads(capsys.readouterr().out)["status"] == "already_applied"
    assert path.read_bytes() == snapshot


def test_policy_revision_reopens_changed_requirement_and_keeps_original_run(initiative, capsys):
    core, target, path, program = register_policy(initiative, capsys)
    capture(core, program)
    before = core.read_cycle_record(target, path)
    identifier = before["gates"]["domain"]["evidence"]
    plan_path = initiative[-1]
    plan = json.loads(plan_path.read_text())
    for requirement in plan["evidence_policy"]["requirements"].values():
        requirement["revision"] = "2"
    plan_path.write_text(json.dumps(plan))
    amend_policy(core, target, path, plan_path, capsys)
    after = core.read_cycle_record(target, path)
    assert after["gates"]["domain"]["result"] == "pending"
    assert after["evidence"]["items"][identifier] == before["evidence"]["items"][identifier]
    with pytest.raises(RuntimeError, match="predates"):
        core.amendment_fresh_evidence(target, after, identifier)


def test_legacy_policy_enrollment_has_supported_capture_writer(initiative, capsys):
    core, target, path, argv, _, plan_path = initiative
    core.command_begin(core.parser().parse_args([*argv, "--approval", "agent-confirmed"]))
    capsys.readouterr()
    before = core.read_cycle_record(target, path)
    original_plan = before["applicability_plan"]
    plan = json.loads(plan_path.read_text())
    program = [sys.executable, "-c", "print('passed')"]
    plan["evidence_policy"] = {"schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in before["initiative"]["requirements"]},
        "gates": {"domain": {"authority": "fixture", "argv": program,
            "inputs": ["tracked.txt"], "environment": [], "toolchain_paths": [], "scope_complete": True}}}
    plan_path.write_text(json.dumps(plan))
    amend_policy(core, target, path, plan_path, capsys)
    enrolled = core.read_cycle_record(target, path)
    assert enrolled["initiative_amendments"][-1]["evidence_policy_revision"]["kind"] == "enroll"
    assert enrolled["applicability_plan"] == original_plan
    assert core.effective_evidence_policy(enrolled) == plan["evidence_policy"]
    assert not enrolled["evidence"].get("bindings")
    capture(core, program)
    after = core.read_cycle_record(target, path)
    identifier = after["gates"]["domain"]["evidence"]
    assert core.load_evidence_binding(target, after, identifier)["coverage"]
    assert core.evidence_binding_applicability(target, after, "domain")["disposition"] == "retained"


def test_bound_source_reuses_across_unrelated_head_but_not_changed_inputs(initiative, capsys):
    core, target, path, program = register_policy(initiative, capsys)
    capture(core, program)
    before = path.read_bytes()
    (target / "notes.md").write_text("Unrelated source note.\n")
    core.git(target, "add", "notes.md")
    core.git(target, "commit", "-m", "unrelated fixture note")
    record = core.read_cycle_record(target, path)
    assert core.evidence_binding_applicability(target, record, "domain")["disposition"] == "retained"
    (target / "tracked.txt").write_text("Relevant source change.\n")
    decision = core.evidence_binding_applicability(target, record, "domain")
    assert decision == {"disposition": "rerun_required", "reason_code": "validation_inputs_changed"}
    assert path.read_bytes() == before


def test_observed_target_cannot_revert_previously_delivered_paths(initiative, capsys):
    core, target, path, program = register_policy(initiative, capsys)
    record = core.read_cycle_record(target, path)
    base = core.git(target, "rev-parse", "HEAD").stdout.strip()
    old_tree = core.git(target, "rev-parse", "HEAD^{tree}").stdout.strip()
    (target / "tracked.txt").write_text("Delivered behavior\n")
    core.git(target, "add", "tracked.txt")
    core.git(target, "commit", "-m", "Deliver behavior")
    source = core.git(target, "rev-parse", "HEAD").stdout.strip()
    reverted = core.git(target, "commit-tree", old_tree, "-p", source, "-m", "Later revert").stdout.strip()
    record["git"]["head"] = base
    with core.local_completion_git_context(), pytest.raises(RuntimeError, match="changes delivered source paths"):
        core.completion_target_equivalence(target, record, source, reverted)


def test_pure_accepted_target_context_preserves_exact_native_tree(initiative, capsys):
    core, target, path, _ = register_policy(initiative, capsys)
    source = core.git(target, "rev-parse", "HEAD").stdout.strip()
    tree = core.git(target, "rev-parse", "HEAD^{tree}").stdout.strip()
    merge = core.git(target, "commit-tree", tree, "-p", source, "-m", "Accepted source").stdout.strip()
    selected = [(1, source, merge)]
    with core.local_completion_git_context():
        core.completion_acceptance_context(target, selected, merge, merge)
    (target / "tracked.txt").write_text("Unaccepted change\n")
    core.git(target, "add", "tracked.txt")
    changed_tree = core.git(target, "write-tree").stdout.strip()
    bad = core.git(target, "commit-tree", changed_tree, "-p", merge, "-m", "Unaccepted delta").stdout.strip()
    with core.local_completion_git_context(), pytest.raises(RuntimeError, match="differs from observed target"):
        core.completion_acceptance_context(target, selected, bad, merge)


@pytest.fixture
def runtime_bound(initiative, capsys):
    identity = {"schema_version": 1, "artifact_digest": "a" * 64, "configuration_digest": "b" * 64,
                "target_digest": "c" * 64, "environment_digest": "d" * 64}
    code = "import os; from pathlib import Path; Path(os.environ['DBSCTR_EVIDENCE_OUTPUT']).write_text(" + repr(json.dumps(identity)) + "); print('passed')"
    registered = register_policy(initiative, capsys, program=[sys.executable, "-c", code], runtime=True)
    capture(registered[0], registered[3])
    capsys.readouterr()
    return registered


def test_runtime_applicability_deduplicates_probe_without_reexecuting_acceptance(runtime_bound, monkeypatch):
    core, target, path, _ = runtime_bound
    before = path.read_bytes()
    native = core._forgejo_run
    calls = []

    def observed(*args, **kwargs):
        calls.append(args[0])
        return native(*args, **kwargs)

    monkeypatch.setattr(core, "_forgejo_run", observed)
    record = core.read_cycle_record(target, path)
    cache = {}
    for _ in range(2):
        result = core.evidence_binding_applicability(target, record, "domain", allow_runtime=True, probe_cache=cache)
        assert result["disposition"] == "retained" and result["runtime_status"] == "passed"
    assert len(calls) == 1
    assert path.read_bytes() == before


def test_runtime_probe_denial_is_unavailable_and_never_retried(runtime_bound, monkeypatch, capsys):
    import subprocess

    core, target, path, _ = runtime_bound
    calls = []

    def denied(*args, **kwargs):
        calls.append(args[0])
        return subprocess.CompletedProcess(args[0], 1, "", "PRIVATE_CREDENTIAL_SENTINEL")

    monkeypatch.setattr(core, "_forgejo_run", denied)
    record = core.read_cycle_record(target, path)
    cache = {}
    before = path.read_bytes()
    for _ in range(2):
        assert core.evidence_binding_applicability(target, record, "domain", allow_runtime=True,
                                                  probe_cache=cache)["disposition"] == "unavailable"
    assert len(calls) == 1 and path.read_bytes() == before
    output = capsys.readouterr()
    assert "PRIVATE_CREDENTIAL_SENTINEL" not in output.out + output.err


def test_historical_runtime_binding_reader_never_probes_or_recaptures(runtime_bound, monkeypatch):
    core, target, path, _ = runtime_bound

    def forbidden(*args, **kwargs):
        pytest.fail("Historical evidence reading attempted runtime/source execution")

    monkeypatch.setattr(core, "evidence_runtime_probe", forbidden)
    monkeypatch.setattr(core, "evidence_binding_snapshot", forbidden)
    monkeypatch.setattr(core, "_forgejo_run", forbidden)
    record = core.read_cycle_record(target, path, historical=True)
    payload = core.load_evidence_binding(target, record, record["gates"]["domain"]["evidence"])
    assert payload["runtime"]["identity"]["target_digest"] == "c" * 64


@pytest.mark.parametrize("invalid_output", ["missing", "malformed", "oversized", "symlink", "hardlink"])
def test_untrusted_runtime_output_keeps_execution_without_identity_credit(initiative, capsys, invalid_output):
    setup = "import os; from pathlib import Path; p=Path(os.environ['DBSCTR_EVIDENCE_OUTPUT']); "
    snippets = {
        "missing": "pass",
        "malformed": "p.write_text('{invalid')",
        "oversized": "p.write_text('x' * 65537)",
        "symlink": "p.unlink(); p.symlink_to('identity-does-not-exist')",
        "hardlink": "p.unlink(); os.link('tracked.txt', p)",
    }
    program = [sys.executable, "-c", setup + snippets[invalid_output] + "; print('passed')"]
    core, target, path, program = register_policy(initiative, capsys, program=program, runtime=True)
    with pytest.raises(RuntimeError, match="binding unavailable"):
        capture(core, program)
    record = core.read_cycle_record(target, path)
    assert record["gates"]["domain"]["result"] == "passed"
    assert not record["evidence"].get("bindings")
