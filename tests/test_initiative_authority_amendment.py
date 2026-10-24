"""Public amendment journey; disposable Git, no live authority or network consent."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

import pytest
import test_dbsctrctl as harness
from test_initiative_cli_approval import initiative
from test_dbsctr_forgejo_completion import cycle
from test_worktrunk_registration import fixture, git
from test_workspace_adoption import Operator, args as adoption_args


@pytest.fixture
def amendment(initiative, fixture, capsys):
    core, target, path, begin, _, plan = initiative
    core.command_begin(core.parser().parse_args([*begin, "--approval", "agent-confirmed"]))
    capsys.readouterr()
    harness.run(target, "record-evidence", "contract", "--authority", "fixture", "--",
                sys.executable, "-c", "raise SystemExit(1)")
    assert json.loads(path.read_text())["gates"]["contract"]["result"] == "failed"
    manifest = fixture.repo / "docs/initiatives/test/MANIFEST.json"
    value = json.loads(manifest.read_text())
    value["title"] += " amended authority"
    manifest.write_text(json.dumps(value))
    git(fixture.repo, "add", str(manifest.relative_to(fixture.repo)))
    git(fixture.repo, "commit", "-m", "Amended Discovery authority")
    checked = json.loads(harness.run(
        fixture.repo, "initiative-check", "--manifest", str(manifest), "--json").stdout)
    argv = ["initiative-amend", "--cycle-id", "cycle-1",
            "--initiative-manifest", "docs/initiatives/test/MANIFEST.json",
            "--initiative-slice", "slice-a", "--initiative-source", str(fixture.repo),
            "--initiative-digest", checked["manifest_digest"], "--plan", str(plan),
            "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
            "--reason", "PRIVATE_REASON_SENTINEL", "--json"]
    return target, path, argv


def preview(amendment):
    target, _, argv = amendment
    result = json.loads(harness.run(target, *argv, "--preflight").stdout)
    assert set(result) == {"schema_version", "cycle_id", "status", "state_digest",
                           "reasons", "next_action"}
    assert result["schema_version"] == 1
    assert result["status"] == "preflight"
    assert len(result["state_digest"]) == 64
    assert "PRIVATE_REASON_SENTINEL" not in json.dumps(result)
    return result["state_digest"]


def git_snapshot(target):
    return tuple(git(target, *args) for args in (
        ("rev-parse", "HEAD"), ("ls-files", "--stage", "-z"), ("status", "--porcelain=v1"),
        ("show-ref",)))


def test_preflight_preserves_cycle_and_git(amendment):
    target, path, _ = amendment
    before, checkout = path.read_bytes(), git_snapshot(target)
    assert preview(amendment) == preview(amendment)
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def test_apply_preserves_history_reopens_gates_and_replays_exactly(amendment):
    target, path, argv = amendment
    before = json.loads(path.read_text())
    checkout = git_snapshot(target)
    digest = preview(amendment)
    apply = [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]
    result = json.loads(harness.run(target, *apply).stdout)
    assert result["status"] == "applied"
    assert result["state_digest"] == digest
    after = json.loads(path.read_text())
    for field in ("initiative", "initiative_approval", "discovery_import", "git", "commits", "evidence"):
        assert after.get(field) == before.get(field)
    assert len(after["initiative_amendments"]) == 1
    for gate in after["gates"].values():
        if gate["applicability"] == "required":
            assert gate["result"] == "pending"
            assert "evidence" not in gate and "exception" not in gate
    assert git_snapshot(target) == checkout
    applied = path.read_bytes()
    replay = json.loads(harness.run(target, *apply).stdout)
    assert replay["status"] == "already_applied"
    assert path.read_bytes() == applied
    status = json.loads(harness.run(target, "status", "--json").stdout)
    assert "PRIVATE_REASON_SENTINEL" not in json.dumps(status)


def test_stale_consent_preserves_unrelated_work(amendment):
    target, path, argv = amendment
    digest = preview(amendment)
    (target / "tracked.txt").write_text("unrelated new work\n")
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--expected-launch-digest", digest,
                         "--approval", "agent-confirmed", ok=False)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "blocked"
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def assert_result(result, status, digest=None):
    assert set(result) == {"schema_version", "cycle_id", "status", "state_digest",
                           "reasons", "next_action"}
    assert result["schema_version"] == 1
    assert result["cycle_id"] == "cycle-1"
    assert result["status"] == status
    if digest is not None:
        assert result["state_digest"] == digest
    else:
        assert result["state_digest"] is None or (
            len(result["state_digest"]) == 64
            and set(result["state_digest"]) <= set("0123456789abcdef"))
    assert "PRIVATE_REASON_SENTINEL" not in json.dumps(result)
    assert not any(value in json.dumps(result) for value in ("/Volumes/", "/private/", "/tmp/"))


def apply_amendment(amendment):
    target, _, argv = amendment
    digest = preview(amendment)
    command = [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]
    result = json.loads(harness.run(target, *command).stdout)
    assert_result(result, "applied", digest)
    return digest, command


def evidence(target, gate="domain", paths=()):
    command = ["record-evidence", gate, "--authority", "fixture"]
    for path in paths:
        command.extend(["--path", path])
    harness.run(target, *command, "--", sys.executable, "-c", "raise SystemExit(0)")


def private_file(target, locator):
    """Resolve only a record-owned locator under its native Git private owner."""
    relative = Path(locator)
    assert not relative.is_absolute() and ".." not in relative.parts
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    matches = {candidate for candidate in (common / relative, common / "dbsctr" / relative)
               if candidate.is_file()}
    assert len(matches) == 1
    return matches.pop()


@pytest.mark.parametrize("change", ["source_document", "source_index", "checkout_document",
                                   "unrelated_index", "unrelated_content", "head", "plan", "reason"])
def test_changed_bound_state_refuses_without_mutation(amendment, fixture, change):
    target, path, argv = amendment
    if change in {"unrelated_content", "unrelated_index"}:
        (target / "tracked.txt").write_text("permitted unrelated work\n")
    digest = preview(amendment)
    manifest = "docs/initiatives/test/MANIFEST.json"
    if change in {"source_document", "source_index"}:
        source = fixture.repo / manifest
        source.write_text(source.read_text() + "\n")
        if change == "source_index":
            git(fixture.repo, "add", manifest)
    elif change == "checkout_document":
        selected = target / manifest
        selected.write_text(selected.read_text() + "\n")
    elif change == "unrelated_index":
        git(target, "add", "tracked.txt")
    elif change == "unrelated_content":
        (target / "tracked.txt").write_text("changed unrelated work\n")
    elif change == "head":
        git(target, "commit", "--allow-empty", "-m", "intervening work")
    elif change == "plan":
        plan = Path(argv[argv.index("--plan") + 1])
        plan.write_text(plan.read_text() + "\n")
    else:
        argv = [*argv]
        argv[argv.index("--reason") + 1] += " changed"
    before, checkout, source = path.read_bytes(), git_snapshot(target), git_snapshot(fixture.repo)
    result = harness.run(target, *argv, "--expected-launch-digest", digest,
                         "--approval", "agent-confirmed", ok=False)
    assert result.returncode == 1
    assert_result(json.loads(result.stdout), "blocked")
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout
    assert git_snapshot(fixture.repo) == source


def test_unrelated_dirty_work_is_allowed_and_preserved(amendment):
    target, _, _ = amendment
    (target / "tracked.txt").write_text("keep operator work\n")
    (target / "untracked.txt").write_text("keep untracked work\n")
    checkout = git_snapshot(target)
    apply_amendment(amendment)
    assert git_snapshot(target) == checkout
    assert (target / "tracked.txt").read_text() == "keep operator work\n"
    assert (target / "untracked.txt").read_text() == "keep untracked work\n"


@pytest.mark.parametrize("change", ["unknown_schema", "completed", "wrong_cycle", "wrong_slice",
                                   "plan_digest", "selected_dirty"])
def test_admission_rejections_are_bounded_and_preserve_state(amendment, change):
    target, path, argv = amendment
    argv = [*argv]
    if change in {"unknown_schema", "completed"}:
        record = json.loads(path.read_text())
        record.update({"schema_version": 999} if change == "unknown_schema" else {"state": "completed"})
        path.write_text(json.dumps(record))
    elif change in {"wrong_cycle", "wrong_slice", "plan_digest"}:
        flag = {"wrong_cycle": "--cycle-id", "wrong_slice": "--initiative-slice",
                "plan_digest": "--expected-plan-digest"}[change]
        argv[argv.index(flag) + 1] = "0" * 64 if change == "plan_digest" else "wrong"
    else:
        selected = target / "docs/initiatives/test/MANIFEST.json"
        selected.write_text(selected.read_text() + "\n")
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 1
    body = json.loads(result.stdout)
    # Invalid selection cannot be reported under the caller's claimed cycle.
    if change == "wrong_cycle":
        assert body["cycle_id"] == "wrong"
        body["cycle_id"] = "cycle-1"
    assert_result(body, "blocked")
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def test_schema5_old_record_status_needs_no_migration(amendment):
    target, path, _ = amendment
    before = path.read_bytes()
    record = json.loads(before)
    assert record["schema_version"] == 5
    assert "initiative_amendments" not in record
    status = json.loads(harness.run(target, "status", "--json").stdout)
    assert not status.get("initiative_amendments", {}).get("count", 0)
    assert path.read_bytes() == before


def test_entry_private_hashes_summary_and_no_checkpoint_on_apply(amendment):
    target, path, _ = amendment
    before = path.read_bytes()
    digest, _ = apply_amendment(amendment)
    record = json.loads(path.read_text())
    entry = record["initiative_amendments"][0]
    assert set(entry) == {"schema_version", "previous_effective_receipt_digest", "receipt",
                          "before_record_sha256", "preimage_locator", "launch_digest", "reason",
                          "approval_method", "approved_at", "plan_digest", "envelope_sha256",
                          "envelope_locator"}
    assert entry["schema_version"] == 1
    assert entry["launch_digest"] == digest
    assert entry["reason"] == "PRIVATE_REASON_SENTINEL"
    assert entry["approval_method"] == "agent_confirmed"
    assert entry["approved_at"].endswith("Z")
    assert entry["before_record_sha256"] == hashlib.sha256(before).hexdigest()
    assert private_file(target, entry["preimage_locator"]).read_bytes() == before
    envelope = private_file(target, entry["envelope_locator"]).read_bytes()
    assert hashlib.sha256(envelope).hexdigest() == entry["envelope_sha256"]
    assert "PRIVATE_REASON_SENTINEL" in envelope.decode()
    assert not record.get("initiative_authority_checkpoints")
    status = json.loads(harness.run(target, "status", "--json").stdout)
    summary = status["initiative_amendments"]
    assert set(summary) == {"schema_version", "count", "effective_receipt_digest", "latest_launch_digest"}
    assert summary["schema_version"] == 1 and summary["count"] == 1
    assert summary["latest_launch_digest"] == digest
    assert summary["effective_receipt_digest"] != entry["previous_effective_receipt_digest"]
    public = json.dumps(status)
    for private in (entry["reason"], entry["envelope_locator"], entry["preimage_locator"]):
        assert private not in public


@pytest.mark.parametrize("corruption", ["link", "version", "reason", "prefix", "preimage_bytes",
                                       "envelope_bytes", "missing_preimage", "missing_envelope",
                                       "symlink_preimage", "symlink_envelope"])
def test_corrupt_chain_never_falls_back_to_original_authority(amendment, tmp_path, corruption):
    target, path, _ = amendment
    _, replay = apply_amendment(amendment)
    record = json.loads(path.read_text())
    entry = record["initiative_amendments"][0]
    if corruption in {"link", "version", "reason", "prefix"}:
        if corruption == "link":
            entry["previous_effective_receipt_digest"] = "0" * 64
        elif corruption == "version":
            entry["schema_version"] = 99
        elif corruption == "reason":
            entry["reason"] += " tampered"
        else:
            record["initiative"]["manifest_digest"] = "0" * 64
        path.write_text(json.dumps(record))
    else:
        field = "preimage_locator" if "preimage" in corruption else "envelope_locator"
        owned = private_file(target, entry[field])
        if corruption.startswith("missing"):
            owned.unlink()
        elif corruption.startswith("symlink"):
            outside = tmp_path / "outside-evidence"
            outside.write_bytes(owned.read_bytes())
            owned.unlink()
            owned.symlink_to(outside)
        else:
            owned.write_bytes(owned.read_bytes() + b"\n")
    before, checkout = path.read_bytes(), git_snapshot(target)
    status = harness.run(target, "status", "--json", ok=False)
    assert status.returncode != 0
    result = harness.run(target, *replay, ok=False)
    body = json.loads(result.stdout)
    assert body["status"] in {"blocked", "recovery_required"}
    assert result.returncode == (75 if body["status"] == "recovery_required" else 1)
    assert_result(body, body["status"])
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def test_old_successful_evidence_cannot_dispose_reopened_gate(amendment):
    target, path, _ = amendment
    evidence(target)
    before = json.loads(path.read_text())
    old_id = before["gates"]["domain"]["evidence"]
    apply_amendment(amendment)
    applied = path.read_bytes()
    result = harness.run(target, "set-gate", "domain", "--result", "passed", "--evidence", old_id, ok=False)
    assert result.returncode == 1
    assert path.read_bytes() == applied
    evidence(target)
    current = json.loads(path.read_text())
    assert current["gates"]["domain"]["result"] == "passed"
    assert current["gates"]["domain"]["evidence"] != old_id
    assert current["evidence"]["items"][old_id] == before["evidence"]["items"][old_id]
    harness.run(target, "status", "--json")


@pytest.mark.parametrize("corruption", ["missing", "replacement_hash"])
def test_missing_or_inconsistent_durable_outcome_requires_recovery(amendment, corruption):
    target, path, _ = amendment
    digest, replay = apply_amendment(amendment)
    record = json.loads(path.read_text())
    entry = record["initiative_amendments"][-1]
    replacement_hash = hashlib.sha256(path.read_bytes()).hexdigest().encode()
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    # Outcome filename is private implementation detail. Its two contract-bound
    # identities distinguish it from envelope, preimage and mutable record.
    candidates = []
    for owned in (common / "dbsctr").rglob("*"):
        if owned.is_file() and not owned.is_symlink() and owned != path:
            content = owned.read_bytes()
            if replacement_hash in content and entry["envelope_sha256"].encode() in content:
                candidates.append(owned)
    assert len(candidates) == 1, "Expected one durably retained replacement outcome descriptor"
    outcome = candidates[0]
    if corruption == "missing":
        outcome.unlink()
    else:
        outcome.write_bytes(outcome.read_bytes().replace(replacement_hash, b"0" * 64))
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *replay, ok=False)
    assert result.returncode == 75
    assert_result(json.loads(result.stdout), "recovery_required", digest)
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


def test_ordinary_progress_blocks_old_replay_but_second_amendment_works(amendment, fixture):
    target, path, argv = amendment
    first_digest, replay = apply_amendment(amendment)
    first = json.loads(path.read_text())
    evidence(target)
    progressed = path.read_bytes()
    harness.run(target, "status", "--json")
    result = harness.run(target, *replay, ok=False)
    assert result.returncode == 1
    assert_result(json.loads(result.stdout), "blocked")
    assert path.read_bytes() == progressed
    manifest = fixture.repo / "docs/initiatives/test/MANIFEST.json"
    value = json.loads(manifest.read_text())
    value["title"] += " second amendment"
    manifest.write_text(json.dumps(value))
    git(fixture.repo, "add", str(manifest.relative_to(fixture.repo)))
    git(fixture.repo, "commit", "-m", "Second Discovery authority")
    checked = json.loads(harness.run(fixture.repo, "initiative-check", "--manifest", str(manifest), "--json").stdout)
    argv = [*argv]
    argv[argv.index("--initiative-digest") + 1] = checked["manifest_digest"]
    second_digest, _ = apply_amendment((target, path, argv))
    after = json.loads(path.read_text())
    assert second_digest != first_digest
    assert len(after["initiative_amendments"]) == 2
    assert after["initiative_amendments"][0] == first["initiative_amendments"][0]
    second = after["initiative_amendments"][1]
    assert second["before_record_sha256"] == hashlib.sha256(progressed).hexdigest()
    assert private_file(target, second["preimage_locator"]).read_bytes() == progressed
    assert after["evidence"] == json.loads(progressed)["evidence"]
    assert after["gates"]["domain"]["result"] == "pending"
    harness.run(target, "status", "--json")


@pytest.mark.parametrize("corruption", [None, "duplicate", "foreign", "closure", "commit"])
def test_gate_commit_records_full_closure_checkpoint(amendment, fixture, corruption):
    target, path, _ = amendment
    digest, _ = apply_amendment(amendment)
    relative = "docs/initiatives/test/MANIFEST.json"
    (target / relative).write_bytes((fixture.repo / relative).read_bytes())
    evidence(target, paths=(relative,))
    harness.run(target, "gate-commit", "--message", "Import effective authority",
                "--gates", "domain", "--paths", relative)
    record = json.loads(path.read_text())
    checkpoints = record["initiative_authority_checkpoints"]
    assert len(checkpoints) == 1
    checkpoint = checkpoints[0]
    assert set(checkpoint) == {"schema_version", "launch_digest", "commit", "closure_sha256"}
    assert checkpoint["schema_version"] == 1
    assert checkpoint["launch_digest"] == digest
    assert checkpoint["commit"] == git(target, "rev-parse", "HEAD").strip()
    assert record["commits"][-1] == {"id": checkpoint["commit"], "gates": ["domain"]}
    entry = record["initiative_amendments"][-1]
    envelope = json.loads(private_file(target, entry["envelope_locator"]).read_text())

    def closures(value):
        if isinstance(value, list):
            if value and all(isinstance(item, dict) and set(item) == {"path", "blob", "mode"}
                             for item in value):
                yield value
            for item in value:
                yield from closures(item)
        elif isinstance(value, dict):
            for item in value.values():
                yield from closures(item)

    selected = list(closures(envelope))
    assert selected, "Immutable envelope must retain approved exact selected closure"
    matching = [items for items in selected if hashlib.sha256(json.dumps(
        sorted(items, key=lambda item: item["path"]), sort_keys=True,
        separators=(",", ":")).encode()).hexdigest() == checkpoint["closure_sha256"]]
    assert matching
    closure = matching[0]
    assert relative in {item["path"] for item in closure}
    assert "docs/specs/test/README.md" in {item["path"] for item in closure}
    for item in closure:
        mode, kind, blob_and_path = git(target, "ls-tree", checkpoint["commit"], "--", item["path"]).split(maxsplit=2)
        assert kind == "blob"
        assert mode == item["mode"] and blob_and_path.split("\t", 1)[0] == item["blob"]
    harness.run(target, "status", "--json")
    if corruption is not None:
        if corruption == "duplicate":
            checkpoints.append(dict(checkpoint))
        elif corruption == "foreign":
            checkpoint["launch_digest"] = "0" * 64
        elif corruption == "closure":
            checkpoint["closure_sha256"] = "0" * 64
        else:
            checkpoint["commit"] = git(target, "rev-parse", "HEAD^").strip()
        path.write_text(json.dumps(record))
        before = path.read_bytes()
        assert harness.run(target, "status", "--json", ok=False).returncode != 0
        assert path.read_bytes() == before


@pytest.mark.parametrize("closure_state", ["missing_checkpoint", "checkpoint", "head_drift"])
def test_schema6_amendment_keeps_local_identity_without_provider_calls(cycle, capsys, closure_state):
    source = cycle.root.parent / "amendment-authority"
    git(cycle.root, "worktree", "add", "-b", "amendment-authority", str(source))
    relative = "docs/initiatives/forgejo-identity/MANIFEST.json"
    manifest = source / relative
    value = json.loads(manifest.read_text())
    value["title"] += " amended authority"
    manifest.write_text(json.dumps(value))
    changelog = "docs/specs/test/CHANGELOG.md"
    (source / changelog).write_text("Imported amended local Initiative authority.\n")
    git(source, "add", relative, changelog)
    git(source, "commit", "-m", "Amended local authority")
    checked = json.loads(harness.run(source, "initiative-check", "--manifest", relative, "--json").stdout)
    plan = cycle.fixture.plan_path()
    argv = ["initiative-amend", "--cycle-id", "cycle-1", "--initiative-manifest", relative,
            "--initiative-slice", "local", "--initiative-source", str(source),
            "--initiative-digest", checked["manifest_digest"], "--plan", str(plan),
            "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest(),
            "--reason", "PRIVATE_REASON_SENTINEL", "--json"]
    before = json.loads(cycle.path.read_text())
    assert cycle.invoke(*argv, "--preflight") == 0
    prepared = json.loads(capsys.readouterr().out)
    assert_result(prepared, "preflight")
    apply = [*argv, "--expected-launch-digest", prepared["state_digest"], "--approval", "agent-confirmed"]
    assert cycle.invoke(*apply) == 0
    assert_result(json.loads(capsys.readouterr().out), "applied", prepared["state_digest"])
    after = json.loads(cycle.path.read_text())
    assert before["schema_version"] == after["schema_version"] == 6
    for field in ("initiative", "initiative_approval", "discovery_import", "git", "execution"):
        assert after.get(field) == before.get(field)
    assert cycle.invoke(*apply) == 0
    assert_result(json.loads(capsys.readouterr().out), "already_applied", prepared["state_digest"])
    assert cycle.invoke("status", "--json") == 0
    assert "PRIVATE_REASON_SENTINEL" not in capsys.readouterr().out
    (cycle.root / relative).write_bytes(manifest.read_bytes())
    (cycle.root / changelog).write_bytes((source / changelog).read_bytes())
    paths = [relative, changelog]
    if closure_state == "missing_checkpoint":
        # Even an exactly matching tree is not a recorded nonempty-gate checkpoint.
        git(cycle.root, "add", *paths)
        git(cycle.root, "commit", "-m", "Unrecorded exact authority tree")
    else:
        assert cycle.invoke("record-evidence", "domain", "--authority", "fixture", "--path", relative,
                            "--path", changelog,
                            "--", sys.executable, "-c", "raise SystemExit(0)") == 0
        capsys.readouterr()
        assert cycle.invoke("gate-commit", "--message", "Effective local authority", "--gates", "domain",
                            "--paths", *paths) == 0
        capsys.readouterr()
        checkpoint = json.loads(cycle.path.read_text())["initiative_authority_checkpoints"][-1]
        assert checkpoint["launch_digest"] == prepared["state_digest"]
        assert checkpoint["commit"] == git(cycle.root, "rev-parse", "HEAD").strip()
        if closure_state == "head_drift":
            selected = cycle.root / relative
            selected.write_text(selected.read_text() + "\n")
            git(cycle.root, "add", relative)
            git(cycle.root, "commit", "-m", "Unapproved editorial closure drift")
            assert cycle.invoke("status", "--json") == 0
            capsys.readouterr()
    gates = json.loads(cycle.path.read_text())["gates"]
    for gate in cycle.core.GATES:
        disposition = gates[gate]
        if disposition["applicability"] == "required":
            assert cycle.invoke("record-evidence", gate, "--authority", "fixture", "--",
                                sys.executable, "-c", "raise SystemExit(0)") == 0
            capsys.readouterr()
    for artifact in ("README", "BACKLOG"):
        assert cycle.invoke("review-artifact", artifact, "--result", "unchanged", "--reason", "fixture review") == 0
        capsys.readouterr()
    assert cycle.invoke("review-artifact", "CHANGELOG", "--result", "changed", "--reason", "fixture review",
                        "--path", changelog) == 0
    capsys.readouterr()
    before_completion = cycle.path.read_bytes()
    if closure_state == "checkpoint":
        assert cycle.invoke("complete-local") == 0
        capsys.readouterr()
        completed = cycle.path.read_bytes()
        assert json.loads(completed)["state"] == "completed"
        assert cycle.invoke("complete-local", "--cycle-id", "cycle-1") == 0
        capsys.readouterr()
        assert cycle.path.read_bytes() == completed
    else:
        assert cycle.invoke("complete-local") == 1
        capsys.readouterr()
        assert cycle.path.read_bytes() == before_completion


@pytest.mark.parametrize("owner", ["source", "checkout"])
@pytest.mark.parametrize("driver", ["clean", "process"])
def test_safety_filters_refused_before_executable_runs(amendment, fixture, tmp_path, owner, driver):
    target, path, argv = amendment
    selected = fixture.repo if owner == "source" else target
    marker = tmp_path / "FILTER_EXECUTED"
    script = tmp_path / "filter-marker"
    script.write_text(f"#!/bin/sh\nprintf executed > {shlex.quote(str(marker))}\nexit 1\n")
    script.chmod(0o700)
    git(selected, "config", "extensions.worktreeConfig", "true")
    git(selected, "config", "--worktree", f"filter.amendment-marker.{driver}", shlex.quote(str(script)))
    git(selected, "config", "--worktree", "filter.amendment-marker.required", "true")
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    attributes = common / "info/attributes"
    attributes.write_text("docs/initiatives/test/MANIFEST.json filter=amendment-marker\n")
    # Force a stat mismatch so unsafe status/receipt inspection would run clean.
    os.utime(selected / "docs/initiatives/test/MANIFEST.json", (1, 1))
    index = Path(git(target, "rev-parse", "--path-format=absolute", "--git-path", "index").strip())
    before, index_before = path.read_bytes(), index.read_bytes()
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 1
    assert_result(json.loads(result.stdout), "blocked")
    assert not marker.exists(), "Admission must refuse executable filters before Git can invoke one"
    assert path.read_bytes() == before
    assert index.read_bytes() == index_before


@pytest.mark.parametrize("owner", ["source", "checkout"])
@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_safety_hidden_selected_bytes_refused(amendment, fixture, owner, flag):
    target, path, argv = amendment
    selected = fixture.repo if owner == "source" else target
    relative = "docs/initiatives/test/MANIFEST.json"
    git(selected, "update-index", flag, "--", relative)
    document = selected / relative
    document.write_text(document.read_text() + "\n")
    assert not git(selected, "diff", "--name-only", "--", relative).strip()
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 1
    assert_result(json.loads(result.stdout), "blocked")
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout
    assert document.read_text().endswith("\n")


def test_safety_source_profile_blob_change_refused(amendment, fixture):
    target, path, argv = amendment
    profile = "docs/specs/test/README.md"
    document = fixture.repo / profile
    document.write_text(document.read_text() + "\nChanged source Engineering Profile.\n")
    git(fixture.repo, "add", profile)
    git(fixture.repo, "commit", "-m", "Changed source profile")
    before, checkout = path.read_bytes(), git_snapshot(target)
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 1
    assert_result(json.loads(result.stdout), "blocked")
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout


@pytest.mark.parametrize("interruption", ["envelope", "before_replace", "after_replace"])
def test_safety_interrupted_custody_exact_retry_retains_consent_time(
        amendment, initiative, monkeypatch, capsys, interruption):
    target, path, argv = amendment
    core = initiative[0]
    digest = preview(amendment)
    apply = [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]
    before, checkout = path.read_bytes(), git_snapshot(target)
    timestamp = "2026-10-23T12:34:56Z"
    monkeypatch.setattr(core, "now", lambda: timestamp)
    original_write = core.amendment_write_once
    original_replace = core.private_json

    def interrupted_write(root, destination, data):
        original_write(root, destination, data)
        if Path(destination).name == "envelope.json":
            raise OSError("synthetic loss after durable envelope")

    def interrupted_replace(destination, value, **kwargs):
        if Path(destination) != path:
            return original_replace(destination, value, **kwargs)
        if interruption == "after_replace":
            original_replace(destination, value, **kwargs)
        raise OSError("synthetic record replacement interruption")

    if interruption == "envelope":
        monkeypatch.setattr(core, "amendment_write_once", interrupted_write)
    else:
        monkeypatch.setattr(core, "private_json", interrupted_replace)
    with pytest.raises(SystemExit) as stopped:
        core.command_initiative_amend(core.parser().parse_args(apply))
    assert stopped.value.code == 75
    assert_result(json.loads(capsys.readouterr().out), "recovery_required", digest)
    assert git_snapshot(target) == checkout
    if interruption != "after_replace":
        assert path.read_bytes() == before
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    envelopes = list((common / "dbsctr/evidence/cycle-1").rglob("envelope.json"))
    assert len(envelopes) == 1
    envelope_before = envelopes[0].read_bytes()
    assert json.loads(envelope_before)["approved_at"] == timestamp
    monkeypatch.setattr(core, "amendment_write_once", original_write)
    monkeypatch.setattr(core, "private_json", original_replace)
    monkeypatch.setattr(core, "now", lambda: "2026-10-24T01:02:03Z")
    if interruption != "after_replace":
        different = [*argv]
        different[different.index("--reason") + 1] += " different effect"
        custody = {item: item.read_bytes() for item in envelopes[0].parent.iterdir() if item.is_file()}
        for command in ([*different, "--preflight"],
                        [*different, "--expected-launch-digest", digest, "--approval", "agent-confirmed"]):
            with pytest.raises(SystemExit) as refused:
                core.command_initiative_amend(core.parser().parse_args(command))
            assert refused.value.code == 75
            assert_result(json.loads(capsys.readouterr().out), "recovery_required")
            assert path.read_bytes() == before
            assert {item: item.read_bytes() for item in envelopes[0].parent.iterdir() if item.is_file()} == custody
    core.command_initiative_amend(core.parser().parse_args(apply))
    expected = "already_applied" if interruption == "after_replace" else "applied"
    assert_result(json.loads(capsys.readouterr().out), expected, digest)
    record = json.loads(path.read_text())
    assert len(record["initiative_amendments"]) == 1
    assert record["initiative_amendments"][0]["approved_at"] == timestamp
    assert envelopes[0].read_bytes() == envelope_before
    applied = path.read_bytes()
    replay = json.loads(harness.run(target, *apply).stdout)
    assert_result(replay, "already_applied", digest)
    assert path.read_bytes() == applied


@pytest.mark.parametrize("command,lock", [("set-gate", "local-mutation-cycle-1"),
                                         ("initiative-amend", "local-mutation-cycle-1"),
                                         ("initiative-amend", "cycle-1")])
def test_safety_native_lock_contention_preserves_record(amendment, initiative, command, lock):
    target, path, argv = amendment
    core = initiative[0]
    digest = preview(amendment)
    selection = (["set-gate", "domain", "--result", "pending"] if command == "set-gate" else
                 [*argv, "--expected-launch-digest", digest, "--approval", "agent-confirmed"])
    before, checkout = path.read_bytes(), git_snapshot(target)
    with core.evidence_lock(target, lock, timeout=1):
        result = harness.run(target, *selection, ok=False)
    assert result.returncode == 1
    if command == "initiative-amend":
        assert_result(json.loads(result.stdout), "blocked")
    else:
        assert "busy" in result.stderr
    assert path.read_bytes() == before
    assert git_snapshot(target) == checkout
    if command == "initiative-amend":
        assert_result(json.loads(harness.run(target, *selection).stdout), "applied", digest)
    else:
        harness.run(target, *selection)


@pytest.mark.parametrize("schema", [3, 4])
def test_safety_adopted_older_schema_amends_without_upgrade(
        amendment, initiative, fixture, monkeypatch, capsys, schema):
    target, path, _ = amendment
    core = initiative[0]
    if schema == 3:
        fixture.make_schema3_fixture("cycle-1", target)
    else:
        record = json.loads(path.read_text())
        record["schema_version"] = schema
        record.pop("execution")
        record["worktree"].pop("git_dir")
        path.write_text(json.dumps(record))
    legacy = path.read_bytes()
    core.command_workspace_adopt(adoption_args(preview=True))
    prepared = json.loads(capsys.readouterr().out)
    # Existing fixture's synthetic terminal qualifies only disposable adoption;
    # it establishes neither real operator consent nor authenticated identity.
    monkeypatch.setattr(core.sys, "stdin", Operator(f"ADOPT cycle-1 {prepared['state_digest']}\n"))
    core.command_workspace_adopt(adoption_args(digest=prepared["state_digest"]))
    capsys.readouterr()
    adopted = json.loads(path.read_text())
    assert adopted["execution"]["origin"] == "adopted"
    common = Path(git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    backup = common / adopted["execution"]["adoption"]["record_backup"]
    assert backup.read_bytes() == legacy
    digest, replay = apply_amendment(amendment)
    after = json.loads(path.read_text())
    assert after["schema_version"] == schema
    assert after["execution"] == adopted["execution"]
    assert after["initiative"] == adopted["initiative"]
    assert after["evidence"] == adopted["evidence"]
    assert backup.read_bytes() == legacy
    assert_result(json.loads(harness.run(target, *replay).stdout), "already_applied", digest)
    harness.run(target, "status", "--json")


@pytest.mark.parametrize("change", ["push_destination", "upstream", "source_mode"])
def test_safety_destination_and_source_mode_are_bound(amendment, fixture, change):
    target, path, argv = amendment
    digest = preview(amendment)
    if change == "push_destination":
        git(target, "remote", "set-url", "--push", "upstream", "https://github.com/example/other.git")
    elif change == "upstream":
        git(target, "config", "branch.task.merge", "refs/heads/other")
    else:
        git(fixture.repo, "config", "core.filemode", "false")
        (fixture.repo / "docs/initiatives/test/MANIFEST.json").chmod(0o755)
    before = path.read_bytes()
    result = harness.run(target, *argv, "--expected-launch-digest", digest,
                         "--approval", "agent-confirmed", ok=False)
    assert_result(json.loads(result.stdout), "blocked")
    assert path.read_bytes() == before


def test_safety_missing_applied_outcome_needs_recovery_even_in_fresh_preflight(amendment):
    target, path, argv = amendment
    apply_amendment(amendment)
    record = json.loads(path.read_text())
    private_file(target, record["initiative_amendments"][0]["envelope_locator"]).with_name("outcome.json").unlink()
    before = path.read_bytes()
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 75
    assert_result(json.loads(result.stdout), "recovery_required")
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", ["unknown_leaf", "symlink_plan"])
def test_safety_unknown_custody_is_retained_not_ignored(amendment, change):
    target, path, argv = amendment
    apply_amendment(amendment)
    record = json.loads(path.read_text())
    directory = private_file(target, record["initiative_amendments"][0]["envelope_locator"]).parent
    if change == "unknown_leaf":
        evidence_file = directory / "interrupted-temporary"
        evidence_file.write_bytes(b"retain recovery evidence")
        evidence_file.chmod(0o600)
    else:
        other = directory.parent / ("0" * 64)
        other.mkdir(mode=0o700)
        evidence_file = other / "plan.json"
        evidence_file.symlink_to(directory / "plan.json")
    before = path.read_bytes()
    result = harness.run(target, *argv, "--preflight", ok=False)
    assert result.returncode == 75
    assert_result(json.loads(result.stdout), "recovery_required")
    assert evidence_file.exists() and path.read_bytes() == before


def test_safety_inapplicable_only_commit_does_not_create_invalid_checkpoint(amendment, fixture):
    target, path, _ = amendment
    apply_amendment(amendment)
    relative = "docs/initiatives/test/MANIFEST.json"
    (target / relative).write_bytes((fixture.repo / relative).read_bytes())
    harness.run(target, "gate-commit", "--message", "Ordinary non-qualifying commit",
                "--gates", "release", "--paths", relative)
    assert not json.loads(path.read_text()).get("initiative_authority_checkpoints")
    harness.run(target, "status", "--json")


@pytest.mark.parametrize("tamper_plan", [False, True])
def test_safety_required_gates_cannot_be_weakened_after_amendment(amendment, tamper_plan):
    target, path, _ = amendment
    apply_amendment(amendment)
    record = json.loads(path.read_text())
    record["gates"]["domain"] = {"applicability": "not_applicable", "result": "not_run", "reason": "forged waiver"}
    if tamper_plan:
        record["applicability_plan"]["gates"]["domain"] = {"applicability": "not_applicable", "reason": "forged waiver"}
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    harness.run(target, "status", "--json", ok=False)
    harness.run(target, "final-push", ok=False)
    assert path.read_bytes() == before


def test_safety_large_native_record_still_shares_mutation_lock(amendment, initiative):
    target, path, _ = amendment
    record = json.loads(path.read_text())
    record["retained_fixture_metadata"] = "x" * (1024 * 1024 + 1)
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    with initiative[0].evidence_lock(target, "local-mutation-cycle-1", timeout=1):
        result = harness.run(target, "set-gate", "domain", "--result", "pending", ok=False)
    assert "busy" in result.stderr and path.read_bytes() == before


def test_safety_prior_exception_is_preserved_but_not_reused(amendment):
    target, path, _ = amendment
    harness.run(target, "approve-exception", "contract", "--kind", "accepted_risk", "--rationale", "fixture",
                "--owner", "fixture", "--review-condition", "before next authority")
    before = json.loads(path.read_text())
    apply_amendment(amendment)
    after = json.loads(path.read_text())
    entry = after["initiative_amendments"][0]
    preimage = json.loads(private_file(target, entry["preimage_locator"]).read_text())
    assert preimage["gates"]["contract"]["exception"] == before["gates"]["contract"]["exception"]
    assert after["gates"]["contract"] == {"applicability": "required", "result": "pending"}
