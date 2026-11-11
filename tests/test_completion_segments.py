"""Composed public CLI journeys; native transport synthetic, Git and custody real."""

import copy
import json
from pathlib import Path

import pytest

from test_dbsctr_external_completion import (
    NUMBER, REPOSITORY, arguments, cycle, ready, record_evidence, snapshot,
)


pytestmark = pytest.mark.parametrize("cycle", ["source-only"], indirect=True)


def segments(ready, count=2):
    core, root = ready.core, ready.root
    selectors, pulls = [], {}
    for number in range(NUMBER - count + 1, NUMBER):
        merge = core.git(root, "commit-tree", ready.tree, "-p", ready.native.pull["base"]["sha"],
                         "-p", ready.head, "-m", f"Synthetic native merge #{number}").stdout.strip()
        pull = copy.deepcopy(ready.native.pull)
        pull.update(number=number, html_url=f"https://github.com/{REPOSITORY}/pull/{number}",
                    merge_commit_sha=merge)
        pulls[f"repos/{REPOSITORY}/pulls/{number}"] = pull
        selectors.append(f"{number}:{ready.head}:{merge}")
        core.git(root, "merge", "--ff-only", merge)
        (root / "docs/specs/test/CHANGELOG.md").write_text(f"Delivered through segment {number}.\n")
        record_evidence(ready, "domain", paths=["docs/specs/test/CHANGELOG.md"])
        core.command_gate_commit(core.parser().parse_args([
            "gate-commit", "--message", "Next synthetic changelog", "--gates", "domain",
            "--paths", "docs/specs/test/CHANGELOG.md",
        ]))
        ready.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
        ready.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
        ready.native.pull["head"]["sha"] = ready.head
        ready.native.pull["base"]["sha"] = merge
    required = core.load(root)[1]["gates"]
    for gate in core.GATES:
        if gate != "domain" and required[gate]["applicability"] == "required":
            record_evidence(ready, gate)
    ready.merge = core.git(root, "commit-tree", ready.tree, "-p", ready.native.pull["base"]["sha"],
                          "-p", ready.head, "-m", "Final synthetic native merge").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge)
    ready.native.pull["head"]["sha"] = ready.head
    ready.native.pull["merge_commit_sha"] = ready.merge
    native_json = ready.native.json

    def json_transport(target, env, *args):
        if args[-1] in pulls:
            ready.native.calls.append(args)
            return copy.deepcopy(pulls[args[-1]])
        return native_json(target, env, *args)

    return (selectors[0] if count == 2 else selectors), json_transport


def test_two_pr_fast_forward_completes_without_rewriting_ledger(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    before = json.loads(ready.path.read_text())
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 0
    receipt = json.loads(capsys.readouterr().out)
    after = ready.core.read_cycle_record(ready.root, ready.path, historical=True)
    assert after["state"] == "completed"
    assert receipt["schema_version"] == 3
    assert [item["pull_request"]["number"] for item in receipt["segments"]] == [16, NUMBER]
    for name in ("git", "commits", "evidence", "gates", "artifact_reviews"):
        assert after[name] == before[name]
    assert after["completion_reconciliation"]["schema_version"] == 1
    assert ready.root.is_dir()
    saved = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--cycle-id", "cycle-1")) == 0
    capsys.readouterr()
    assert snapshot(ready) == saved


def test_multi_segment_preview_never_writes_cycle_or_refs(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    capsys.readouterr()
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--preview")) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == 3
    assert snapshot(ready) == before


@pytest.mark.parametrize("checkout_context", ["source", "landed"])
def test_mixed_exact_and_rebased_segments_use_separate_source_custody(ready, monkeypatch, capsys, checkout_context):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    base = ready.native.pull["base"]["sha"]
    ready.merge = core.git(root, "commit-tree", ready.tree, "-p", base,
                           "-m", "Native individual-commit rebase").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge)
    ready.native.pull["merge_commit_sha"] = ready.merge
    if checkout_context == "landed":
        # Same tree, fixture-owned branch only; retain original source through
        # the reconciliation's own refs rather than rewriting its gate ledger.
        assert core.git(root, "rev-parse", ready.merge + "^{tree}").stdout.strip() == ready.tree
        task_ref = core.git(root, "symbolic-ref", "HEAD").stdout.strip()
        core.git(root, "update-ref", task_ref, ready.merge, ready.head)

    def composed_transport(target, env, *args):
        if args[-1] == f"repos/{REPOSITORY}":
            return {"full_name": REPOSITORY, "default_branch": "main"}
        if args[-1] == f"repos/{REPOSITORY}/commits/{ready.merge}/pulls?per_page=2":
            return [copy.deepcopy(ready.native.pull)]
        return transport(target, env, *args)

    monkeypatch.setattr(core, "github_json", composed_transport)
    before = json.loads(ready.path.read_text())
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--proof", "rebased_commits")) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert [item["schema_version"] for item in receipt["segments"]] == [1, 4]
    segment = receipt["segments"][-1]
    assert segment["source_retention_ref"] == f"refs/dbsctr/reconciliation/cycle-1/{ready.head}"
    assert core.git(root, "show-ref", "--verify", "--quiet", "refs/dbsctr/evidence/cycle-1", check=False).returncode != 0
    after = core.read_cycle_record(root, ready.path, historical=True)
    assert after["commits"] == before["commits"] and after["evidence"] == before["evidence"]


def test_later_target_revert_prevents_composed_completion(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    baseline_tree = core.git(root, "rev-parse", ready.base + "^{tree}").stdout.strip()
    reverted = core.git(root, "commit-tree", baseline_tree, "-p", ready.merge,
                        "-m", "Later target reverted delivered work").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", reverted)
    monkeypatch.setattr(core, "github_json", transport)
    before = snapshot(ready)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    assert snapshot(ready) == before
    assert "changes delivered source paths" in capsys.readouterr().err


def test_single_pr_fast_forward_checkout_uses_one_segment_reconciliation(ready, capsys):
    core, root = ready.core, ready.root
    ready.merge = core.git(root, "commit-tree", ready.tree, "-p", ready.base, "-p", ready.head,
                           "-m", "Native exact accepted tree").stdout.strip()
    ready.native.pull["merge_commit_sha"] = ready.merge
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge)
    core.git(root, "merge", "--ff-only", ready.merge)
    before = json.loads(ready.path.read_text())
    capsys.readouterr()
    assert ready.invoke(*arguments(ready)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["schema_version"] == 3 and len(receipt["segments"]) == 1
    after = core.read_cycle_record(root, ready.path, historical=True)
    assert after["commits"] == before["commits"] and after["evidence"] == before["evidence"]
    assert core.git(root, "rev-parse", "HEAD").stdout.strip() == ready.merge
    assert ready.invoke(*arguments(ready, "--cycle-id", "cycle-1")) == 0


def test_target_change_during_custody_preparation_blocks_completion(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    monkeypatch.setattr(core, "github_json", transport)
    before = ready.path.read_bytes()
    original_write = core.amendment_write_once
    moved = False

    def changing_target(target, path, data):
        nonlocal moved
        result = original_write(target, path, data)
        if not moved and path.name == "outcome.json":
            moved = True
            later = core.git(root, "commit-tree", ready.tree, "-p", ready.merge,
                             "-m", "Concurrent native target advance").stdout.strip()
            core.git(root, "update-ref", "refs/remotes/origin/main", later)
        return result

    monkeypatch.setattr(core, "amendment_write_once", changing_target)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    assert moved and ready.path.read_bytes() == before
    assert core.resolved_active_path(root, bindings=False).exists()
    assert "target changed before completion persistence" in capsys.readouterr().err


def test_three_pr_completion_retains_sources_and_reads_offline(ready, monkeypatch, capsys):
    selectors, transport = segments(ready, count=3)
    core, root = ready.core, ready.root
    monkeypatch.setattr(core, "github_json", transport)
    before = ready.path.read_bytes()
    flags = [flag for selector in selectors for flag in ("--delivery-segment", selector)]
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, *flags)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert [item["pull_request"]["number"] for item in receipt["segments"]] == [15, 16, NUMBER]
    for item in receipt["segments"]:
        ref = f"refs/dbsctr/reconciliation/cycle-1/{item['head']}"
        assert core.git(root, "rev-parse", ref).stdout.strip() == item["head"]
        assert core.git(root, "cat-file", "-t", ref).stdout.strip() == "commit"
    digest = receipt["reconciliation_digest"]
    custody = core.cycle_dir(root) / "evidence/cycle-1/completion-reconciliation" / digest
    assert (custody / "before.json").read_bytes() == before

    def offline(*_args, **_kwargs):
        raise AssertionError("historical reading must not access native transport or credentials")

    monkeypatch.setattr(core, "github_environment", offline)
    monkeypatch.setattr(core, "github_json", offline)
    # Historical custody remains meaningful without the original checked-out source.
    core.git(root, "checkout", "--detach", ready.base)
    record = core.read_cycle_record(root, ready.path, historical=True)
    assert record["state"] == "completed"
    assert record["external_completion"] == receipt
    assert record["commits"] == json.loads(before)["commits"]


def test_native_exact_tree_does_not_launder_unrecorded_code(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    (root / "tracked.txt").write_text("Unapproved code on an already familiar path.\n")
    core.git(root, "add", "tracked.txt")
    core.git(root, "commit", "-m", "Unrecorded arbitrary code")
    ready.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    ready.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    ready.merge = core.git(root, "commit-tree", ready.tree, "-p", ready.native.pull["base"]["sha"],
                           "-p", ready.head, "-m", "Native merge containing unapproved code").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge)
    ready.native.pull["head"]["sha"] = ready.head
    ready.native.pull["merge_commit_sha"] = ready.merge
    # Even fresh passing executions do not authorize adopting an unknown commit.
    required = core.load(root)[1]["gates"]
    for gate in core.GATES:
        if required[gate]["applicability"] == "required":
            record_evidence(ready, gate)
    monkeypatch.setattr(core, "github_json", transport)
    capsys.readouterr()
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--preview")) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["stages"]["topology"]["reason_codes"] == ["provenance_unavailable"]
    assert report["stages"]["evidence"]["status"] == "passed"
    assert report["stages"]["delivery"]["status"] == "not_evaluated"
    assert not ready.native.calls
    assert snapshot(ready) == before


@pytest.mark.parametrize("boundary", ["save", "pointer"])
def test_durable_completion_retry_after_save_or_pointer_interruption(
        ready, monkeypatch, capsys, boundary):
    selector, transport = segments(ready)
    core = ready.core
    monkeypatch.setattr(core, "github_json", transport)
    pointer = core.resolved_active_path(ready.root, bindings=False)
    save, unlink = core.save, Path.unlink

    def late_save(path, record):
        save(path, record)
        if path == ready.path and record.get("completion_reconciliation"):
            raise RuntimeError("synthetic lost save acknowledgement")

    def interrupted_unlink(path, *args, **kwargs):
        if path == pointer:
            raise RuntimeError("synthetic pointer interruption")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(core, "save", late_save if boundary == "save" else save)
    monkeypatch.setattr(Path, "unlink", interrupted_unlink if boundary == "pointer" else unlink)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    saved = ready.path.read_bytes()
    assert json.loads(saved)["state"] == "completed"
    assert pointer.read_text() == "cycle-1\n"
    monkeypatch.setattr(core, "save", save)
    monkeypatch.setattr(Path, "unlink", unlink)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 0
    capsys.readouterr()
    assert ready.path.read_bytes() == saved
    assert not pointer.exists()
    custody = core.cycle_dir(ready.root) / "evidence/cycle-1/completion-reconciliation"
    assert len(list(custody.iterdir())) == 1


@pytest.mark.parametrize("tamper", ["before.json", "plan.json", "outcome.json", "source-ref"])
def test_completed_reconciliation_rejects_custody_tamper(ready, monkeypatch, capsys, tamper):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    monkeypatch.setattr(core, "github_json", transport)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 0
    receipt = json.loads(capsys.readouterr().out)
    if tamper == "source-ref":
        head = receipt["segments"][0]["head"]
        core.git(root, "update-ref", f"refs/dbsctr/reconciliation/cycle-1/{head}", ready.base)
    else:
        target = (core.cycle_dir(root) / "evidence/cycle-1/completion-reconciliation"
                  / receipt["reconciliation_digest"] / tamper)
        value = json.loads(target.read_bytes())
        if tamper == "before.json":
            value["state"] = "retired"
        elif tamper == "plan.json":
            value["tree"] = core.git(root, "rev-parse", f"{ready.base}^{{tree}}").stdout.strip()
        else:
            value["replacement_sha256"] = "f" * 64
        target.write_text(json.dumps(value))
    before = snapshot(ready)
    with pytest.raises(RuntimeError):
        core.read_cycle_record(root, ready.path, historical=True)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--cycle-id", "cycle-1")) == 1
    capsys.readouterr()
    assert snapshot(ready) == before


@pytest.mark.parametrize("interruption", [1, 2, 3])
def test_prepared_completion_retry_uses_one_outcome(ready, monkeypatch, capsys, interruption):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    capsys.readouterr()
    before = snapshot(ready)
    write_once = ready.core.amendment_write_once
    writes = 0

    def interrupted(root, path, data):
        nonlocal writes
        write_once(root, path, data)
        if "completion-reconciliation" in path.parts:
            writes += 1
            if writes == interruption:
                raise RuntimeError("synthetic preparation interruption")

    monkeypatch.setattr(ready.core, "amendment_write_once", interrupted)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert snapshot(ready) == before
    monkeypatch.setattr(ready.core, "amendment_write_once", write_once)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 0
    capsys.readouterr()
    parent = ready.core.cycle_dir(ready.root) / "evidence/cycle-1/completion-reconciliation"
    assert len(list(parent.iterdir())) == 1
    after = ready.core.read_cycle_record(ready.root, ready.path, historical=True)
    assert after["state"] == "completed"


def test_source_drift_during_preparation_retains_active_record(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    capsys.readouterr()
    before = ready.path.read_bytes()
    write_once = ready.core.amendment_write_once

    def drift(root, path, data):
        write_once(root, path, data)
        if "completion-reconciliation" in path.parts:
            (root / "tracked.txt").write_text("Preserve concurrent operator change.\n")

    monkeypatch.setattr(ready.core, "amendment_write_once", drift)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert ready.path.read_bytes() == before
    assert ready.core.resolved_active_path(ready.root, bindings=False).exists()
    assert (ready.root / "tracked.txt").read_text() == "Preserve concurrent operator change.\n"


def test_foreign_pointer_during_preparation_is_not_overwritten(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    core = ready.core
    monkeypatch.setattr(core, "github_json", transport)
    pointer = core.resolved_active_path(ready.root, bindings=False)
    before = ready.path.read_bytes()
    write_once = core.amendment_write_once

    def replace_pointer(root, path, data):
        write_once(root, path, data)
        if "completion-reconciliation" in path.parts and path.name == "outcome.json":
            pointer.write_text("other-cycle\n")

    monkeypatch.setattr(core, "amendment_write_once", replace_pointer)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert ready.path.read_bytes() == before
    assert pointer.read_text() == "other-cycle\n"
    assert json.loads(before)["state"] == "active"


def test_prepared_completion_conflicting_preimage_blocks_retry(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    core = ready.core
    monkeypatch.setattr(core, "github_json", transport)
    write_once = core.amendment_write_once
    prepared = []

    def interrupted(root, path, data):
        write_once(root, path, data)
        if "completion-reconciliation" in path.parts and path.name == "before.json":
            prepared.append(path)
            raise RuntimeError("synthetic interruption after preimage")

    monkeypatch.setattr(core, "amendment_write_once", interrupted)
    capsys.readouterr()
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert snapshot(ready) == before
    assert len(prepared) == 1
    prepared[0].write_bytes(prepared[0].read_bytes() + b" ")
    monkeypatch.setattr(core, "amendment_write_once", write_once)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert snapshot(ready) == before
    assert len(list(prepared[0].parent.parent.iterdir())) == 1


@pytest.mark.parametrize("exception", [{}, {"kind": "accepted_risk"}, {"approved_at": "not-a-date"}])
def test_multi_segment_rejects_invalid_gate_exception(ready, monkeypatch, capsys, exception):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    record_evidence(ready, "contract", code=1)
    value = json.loads(ready.path.read_text())
    value["gates"]["contract"]["exception"] = exception
    ready.core.private_json(ready.path, value, strict=True)
    capsys.readouterr()
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 1
    capsys.readouterr()
    assert snapshot(ready) == before
    assert not ready.native.calls


def test_structural_report_aggregates_before_credentials(ready, monkeypatch, capsys):
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    (ready.root / "tracked.txt").write_text("Preserve dirty source.\n")

    def no_credentials(*_args):
        raise AssertionError("structural blockers must precede credential access")

    monkeypatch.setattr(ready.core, "github_environment", no_credentials)
    capsys.readouterr()
    before = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--preview",
                                    "--expected-head", "f" * 40)) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert set(report["stages"]["source"]["reason_codes"]) >= {"head_pin_mismatch", "tracked_source_dirty"}
    assert report["stages"]["topology"]["status"] == "blocked"
    assert report["stages"]["delivery"]["status"] == "not_evaluated"
    assert report["stages"]["cleanup"]["reason_codes"] == ["cleanup_independent"]
    assert snapshot(ready) == before


@pytest.mark.parametrize("regular_document", [True, False])
def test_only_reviewed_regular_documentation_can_be_non_gate_history(
        ready, monkeypatch, capsys, regular_document):
    selector, transport = segments(ready)
    core, root = ready.core, ready.root
    document = "docs/operations/final-note.md"
    (root / document).parent.mkdir(parents=True, exist_ok=True)
    (root / document).write_text("Reviewed synthetic final note.\n")
    if not regular_document:
        (root / document).chmod(0o755)
    core.git(root, "add", document)
    core.git(root, "commit", "-m", "Reviewed non-gate documentation")
    ready.head = core.git(root, "rev-parse", "HEAD").stdout.strip()
    ready.tree = core.git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    parent = core.git(root, "rev-parse", ready.merge + "^1").stdout.strip()
    ready.merge = core.git(root, "commit-tree", ready.tree, "-p", parent, "-p", ready.head,
                          "-m", "Synthetic final exact-tree merge").stdout.strip()
    core.git(root, "update-ref", "refs/remotes/origin/main", ready.merge)
    ready.native.pull["head"]["sha"] = ready.head
    ready.native.pull["merge_commit_sha"] = ready.merge
    for gate in core.GATES:
        if core.load(root)[1]["gates"][gate]["applicability"] == "required":
            record_evidence(ready, gate, paths=[document] if gate == "review_integrate" else [])
    monkeypatch.setattr(core, "github_json", transport)
    capsys.readouterr()
    before = json.loads(ready.path.read_text())
    result = ready.invoke(*arguments(ready, "--delivery-segment", selector))
    output = capsys.readouterr()
    assert result == (0 if regular_document else 1), output.err
    after = json.loads(ready.path.read_text())
    assert after["commits"] == before["commits"]
    assert after["evidence"] == before["evidence"]
    assert not any(item["id"] == ready.head for item in after["commits"])
    assert after["state"] == ("completed" if regular_document else "active")
