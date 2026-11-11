"""Real approved local Initiative registration/capture; no remote runtime claims."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_initiative_cli_approval import initiative
from test_worktrunk_registration import fixture
from test_dbsctr_forgejo_completion import cycle, ready as local_ready


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


@pytest.mark.parametrize("tamper", ["none", "plan", "gate", "runtime", "history"])
def test_legacy_policy_enrollment_has_supported_capture_writer(initiative, capsys, tamper):
    core, target, path, argv, _, plan_path = initiative
    plan = json.loads(plan_path.read_text())
    for gate in ("deploy", "operate"):
        plan["gates"][gate] = {"applicability": "not_applicable", "reason": "Synthetic source-only delivery."}
    plan_path.write_text(json.dumps(plan))
    argv = argv[:-2]
    argv[argv.index("--expected-plan-digest") + 1] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    core.command_begin(core.parser().parse_args([*argv, "--preflight"]))
    prepared = json.loads(capsys.readouterr().out)
    core.command_begin(core.parser().parse_args([
        *argv, "--expected-launch-digest", prepared["launch_digest"], "--approval", "agent-confirmed"]))
    capsys.readouterr()
    before = core.read_cycle_record(target, path)
    original_plan = before["applicability_plan"]
    plan = json.loads(plan_path.read_text())
    program = [sys.executable, "-c", "print('passed')"]
    # Establish actual legacy source work before approving its updated document
    # authority. Enrollment must not silently bless dirty authority artifacts.
    changelog = "docs/specs/test/CHANGELOG.md"
    (target / changelog).write_text("Synthetic source completion.\n")
    (target / "tracked.txt").write_text("Synthetic source candidate.\n")
    core.command_record_evidence(core.parser().parse_args([
        "record-evidence", "domain", "--authority", "fixture", "--path", "tracked.txt", "--path", changelog,
        "--", *program]))
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture: prepare legacy candidate", "--gates", "domain",
        "--paths", "tracked.txt", changelog]))
    if tamper == "runtime":
        program = [sys.executable, "-c",
            "import hashlib,json,os; from pathlib import Path; "
            "h=lambda value: hashlib.sha256(value).hexdigest(); "
            "identity={'schema_version':1,'artifact_digest':h(Path('tracked.txt').read_bytes()),"
            "'configuration_digest':h(Path('docs/specs/test/README.md').read_bytes()),"
            "'target_digest':h(b'synthetic-target'),'environment_digest':h(b'synthetic-runtime')}; "
            "Path(os.environ['DBSCTR_EVIDENCE_OUTPUT']).write_text(json.dumps(identity)); print('passed')"]
    plan["evidence_policy"] = {"schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in before["initiative"]["requirements"]},
        "gates": {"domain": {"authority": "fixture", "argv": program,
            "inputs": ["tracked.txt"], "environment": [], "toolchain_paths": [], "scope_complete": True}}}
    if tamper == "runtime":
        plan["evidence_policy"]["gates"]["domain"]["runtime"] = {
            "probe_argv": program, "probe_timeout_seconds": 5, "max_age_seconds": 3600}
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
    (target / "tracked.txt").write_text("Validated synthetic source delivery.\n")
    closure_paths = ["tracked.txt"]  # Gate outputs, not unchanged authority/input files.
    captured = ["record-evidence", "domain", "--authority", "fixture"]
    for selected in closure_paths:
        captured.extend(["--path", selected])
    core.command_record_evidence(core.parser().parse_args([*captured, "--", *program]))
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture: validate enrolled legacy source", "--gates", "domain",
        "--paths", *closure_paths]))
    for name in core.GATES:
        if name != "domain" and enrolled["gates"][name]["applicability"] == "required":
            core.command_record_evidence(core.parser().parse_args([
                "record-evidence", name, "--authority", "fixture", "--", sys.executable, "-c", "print('passed')"]))
    for name in ("README", "BACKLOG", "CHANGELOG"):
        review = ["review-artifact", name, "--result", "changed" if name == "CHANGELOG" else "unchanged",
                  "--reason", "Synthetic source completion review."]
        if name == "CHANGELOG":
            review.extend(["--path", changelog])
        core.command_review(core.parser().parse_args(review))
    # Real native Git push to the fixture's disposable local bare upstream only.
    remote = core.git(target, "remote", "get-url", "upstream").stdout.strip()
    assert remote == str(target.parent / "remote.git")
    core.command_final_push(core.parser().parse_args(["final-push"]))
    completed = core.read_cycle_record(target, path, historical=True)
    assert completed["state"] == "completed"
    assert completed["applicability_plan"] == original_plan
    assert completed["initiative_approval"] == before["initiative_approval"]
    assert completed["evidence"]["items"][identifier] == after["evidence"]["items"][identifier]
    assert core.load_evidence_binding(target, completed, identifier)["coverage"]
    assert target.is_dir() and not core.resolved_active_path(target, bindings=False).exists()
    reference = completed["completion_reconciliation"]
    assert reference["schema_version"] == 2
    proof_path = core.reconciliation_location(target, "cycle-1", reference["digest"], "plan.json")
    proof = core.amendment_json(target, proof_path)
    assert proof["route"] == "final_push" and proof["requirements"]["requirements"]
    assert all(item["disposition"] == "retained" for item in proof["evidence_dispositions"].values())
    if tamper == "plan":
        proof_path.write_text("{}\n")
    elif tamper == "gate":
        completed["gates"]["domain"]["evidence"] = identifier
        core.private_json(path, completed, strict=True)
    elif tamper == "history":
        completed["evidence"]["items"][identifier]["summary"] = "failed"
        core.private_json(path, completed, strict=True)
    elif tamper == "runtime":
        assert proof["evidence_dispositions"]["domain"]["runtime_status"] == "passed"
        assert len(proof["runtime_observations"]) == 1
        observation = proof["runtime_observations"][0]["reference"]["sha256"]
        (core.cycle_dir(target) / "evidence" / "cycle-1" / observation).write_text("{}\n")
    if tamper != "none":
        with pytest.raises(RuntimeError):
            core.read_cycle_record(target, path, historical=True)


def test_local_policy_completion_retains_offline_applicability_custody(local_ready, capsys, monkeypatch):
    c = local_ready
    core, root = c.core, c.root
    before = core.read_cycle_record(root, c.path)
    plan_path = c.begin_argv[c.begin_argv.index("--plan") + 1]
    plan = json.loads(Path(plan_path).read_text())
    program = [sys.executable, "-c", "raise SystemExit(0)"]
    plan["evidence_policy"] = {"schema_version": 1,
        "requirements": {name: {"revision": "1", "depends_on": [], "gates": ["domain"]}
                         for name in before["initiative"]["requirements"]},
        "gates": {"domain": {"authority": "fixture", "argv": program, "inputs": ["tracked.txt"],
                             "environment": [], "toolchain_paths": [], "scope_complete": True}}}
    Path(plan_path).write_text(json.dumps(plan))
    argv = ["initiative-amend", "--cycle-id", "cycle-1", "--initiative-manifest",
        "docs/initiatives/forgejo-identity/MANIFEST.json", "--initiative-slice", "local",
        "--initiative-digest", before["initiative"]["manifest_digest"], "--plan", plan_path,
        "--expected-plan-digest", hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        "--reason", "Synthetic offline policy enrollment", "--json"]
    core.command_initiative_amend(core.parser().parse_args([*argv, "--preflight"]))
    prepared = json.loads(capsys.readouterr().out)
    core.command_initiative_amend(core.parser().parse_args([
        *argv, "--expected-launch-digest", prepared["state_digest"], "--approval", "agent-confirmed"]))
    capsys.readouterr()
    (root / "tracked.txt").write_text("Final offline source.\n")
    core.command_record_evidence(core.parser().parse_args([
        "record-evidence", "domain", "--authority", "fixture", "--path", "tracked.txt", "--", *program]))
    core.command_gate_commit(core.parser().parse_args([
        "gate-commit", "--message", "fixture: validate offline source", "--gates", "domain", "--paths", "tracked.txt"]))
    for name in core.GATES:
        if name != "domain" and before["gates"][name]["applicability"] == "required":
            core.command_record_evidence(core.parser().parse_args([
                "record-evidence", name, "--authority", "fixture", "--", *program]))
    for name in ("README", "BACKLOG", "CHANGELOG"):
        args = ["review-artifact", name, "--result", "changed" if name == "CHANGELOG" else "unchanged",
                "--reason", "Offline source review"]
        if name == "CHANGELOG":
            args.extend(["--path", "docs/specs/test/CHANGELOG.md"])
        core.command_review(core.parser().parse_args(args))
    monkeypatch.setattr(core, "evidence_runtime_probe", c.forbidden)
    capsys.readouterr()
    assert c.invoke("complete-local") == 0
    completed = core.read_cycle_record(root, c.path, historical=True)
    assert completed["completion_reconciliation"]["schema_version"] == 2
    reference = completed["completion_reconciliation"]
    proof = core.amendment_json(root, core.reconciliation_location(root, "cycle-1", reference["digest"], "plan.json"))
    assert proof["route"] == "local" and proof["runtime_observations"] == []
    capsys.readouterr()
    stable = c.path.read_bytes()
    assert c.invoke("complete-local", "--cycle-id", "cycle-1") == 0
    assert c.path.read_bytes() == stable


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
