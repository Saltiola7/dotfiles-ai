import importlib.util
import json
import re
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / ".github/validation_shadow.py"
SPEC = importlib.util.spec_from_file_location("validation_shadow", SCRIPT)
shadow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shadow)

HEAD, BASE, TESTED = (char * 40 for char in "abc")
NODE = "tests/test_example.py::test_one"
REPOSITORY = "example/project"


def test_workflow_keeps_comparison_read_only_and_on_trusted_source():
    workflow = SCRIPT.with_name("workflows").joinpath("validation-shadow.yml").read_text()
    affected, compare = workflow.split("\n  compare:\n", 1)
    assert "\n  pull_request:\n" in affected
    assert "workflows: [test]\n    types: [completed]" in affected
    assert "\n  workflow_dispatch:\n" in affected
    assert "\npermissions:\n  contents: read\n  actions: read\n" in affected
    assert not re.search(r"\bwrite\b\s*(?:#.*)?$", workflow, re.MULTILINE)
    assert "secrets." not in workflow
    actions = re.findall(r"^\s*(?:-\s+)?uses:\s+(\S+)", workflow, re.MULTILINE)
    assert actions and all(re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", action) for action in actions)
    assert "ref: ${{ github.sha }}" in compare
    assert "persist-credentials: false" in compare
    assert "head_sha }}" not in compare and "actions/download-artifact" not in compare
    assert 'python3 -I .github/validation_shadow.py compare' in compare
    assert "timeout-minutes: 15" in affected and "cancel-in-progress: true" in affected


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def run_data():
    return {"id": 17, "run_attempt": 1, "event": "pull_request",
            "repository": {"full_name": REPOSITORY},
            "created_at": stamp(0), "run_started_at": stamp(2)}


def stamp(seconds):
    return f"2026-01-01T00:00:{seconds:02d}Z"


def interval(start, end):
    return {"started_at": stamp(start), "completed_at": stamp(end)}


def worker(shard):
    return {"name": f"Full suite (3.14, partition {shard})", "run_id": 17, "run_attempt": 1,
            **interval(4 + shard, 24 + 2 * shard), "steps": [
                {"name": "Check publication and instruction contracts", **interval(10, 13 + shard)},
                {"name": "Check full-suite partition", **interval(14 + shard, 22 + 2 * shard)},
            ]}


def manifest():
    return {"schema_version": 1, "kind": "dbsctr-validation-manifest",
            "head": HEAD, "base": BASE, "exported_at": stamp(1),
            "adapter": {"id": "dotfiles.continuous-validation", "digest": "d" * 64},
            "selection": {"basis": "affected", "checks": [
                {"id": "dotfiles.full", "test_identity": {}},
            ]}, "executions": [
                {"id": "receipt-1", "check_id": "dotfiles.full", "head": HEAD, "result": "passed",
                 "snapshot_id": "c" * 64, "lane": {}, "test_identity": {},
                 "elapsed_seconds": 7, "referenced_by": []},
            ]}


def receipt(shard):
    return {"schema_version": 2, "shard": shard, "collection_complete": True, "exit_code": 0,
            "identity": {"repository": REPOSITORY, "run_id": "17", "attempt": "1",
                         "commit": TESTED, "tree": "e" * 40, "python_version": "3.14",
                         "worktrunk_version": "0.81.0",
                         "authority": {"tests/ci_shard.py": "a" * 64,
                                       ".github/workflows/test.yml": "b" * 64}},
            "collected": [NODE], "selected": [NODE], "collection_reports": [], "subtests": [],
            "reports": [{"nodeid": NODE, "when": phase, "outcome": "passed"}
                        for phase in ("setup", "call", "teardown")],
            "python_full": "3.14.5"}


def identity_summary():
    return {"schema_version": 1, "kind": "pytest-junit-v1",
            "encoding": "pytest-nodeid-or-sha256-v1", "scope": "completed",
            "complete": True, "case_count": 1, "reported_count": 1, "omitted_count": 0,
            "opaque_count": 0, "ids_digest": "b" * 64, "failed_test_ids": [],
            "outcomes": {"passed": 1, "failed": 0, "error": 0, "skipped": 0}}


@pytest.fixture
def inputs(tmp_path):
    write(tmp_path, "run.json", run_data())
    write(tmp_path, "source.json", {"head": HEAD, "base": BASE, "tested_oid": TESTED})
    write(tmp_path, "note.json", manifest())
    return tmp_path


def test_cli_missing_inputs_and_claims_do_not_prove_source(inputs):
    shard = shadow.partition_for(NODE)
    root = inputs / f"partitions/pytest-3.14-0.81.0-{shard}"
    write(root, "manifest.json", receipt(shard))
    (root / "junit.xml").write_text(
        '<testsuites><testsuite tests="1" skipped="0" errors="0" failures="0">'
        '<testcase classname="tests.test_example" name="test_one"><properties>'
        f'<property name="ci_nodeid" value="{NODE}"/>'
        '</properties></testcase></testsuite></testsuites>'
    )
    out = inputs / "report"
    assert shadow.main(["compare", "--input-dir", str(inputs), "--output-dir", str(out)]) == 0
    report = json.loads((out / "validation-shadow.json").read_text())
    assert report["schema_version"] == 1
    assert (report["head"], report["base"], report["tested_oid"]) == (HEAD, BASE, TESTED)
    assert report["checks"][0]["must_run"] == [{"reason": "source_unverified", "count": 1}]
    assert report["repeated_early_selection"] == {"identities": None, "extra_executions": None}
    assert {"jobs", "affected", "partitions", "early_step_execution_identities"} <= set(report["unavailable"])
    markdown = (out / "validation-shadow.md").read_text()
    assert "source_unverified" in markdown
    assert REPOSITORY not in markdown and NODE not in markdown


def test_non_pr_produces_no_report(inputs):
    write(inputs, "run.json", {**run_data(), "event": "push"})
    out = inputs / "report"
    assert shadow.main(["compare", "--input-dir", str(inputs), "--output-dir", str(out)]) == 0
    assert not out.exists()


@pytest.mark.parametrize("raw", [
    b"\xff", b"[]", b'{"schema_version": 1, "schema_version": 1}', b"{" * 3000,
    b" " * (4 * 1024 * 1024 + 1),
])
def test_bad_note_has_no_admitted_claims(inputs, raw):
    (inputs / "note.json").write_bytes(raw)
    note, status, digest = shadow.load_note(inputs)
    assert (note, status, digest) == (None, "manifest_malformed", None)


def test_timing_uses_native_job_and_step_intervals(inputs):
    jobs = [worker(shard) for shard in range(4)]
    jobs.append({"name": "test (3.14)", "run_id": 17, "run_attempt": 1,
                 **interval(31, 48), "steps": [
                     {"name": "Verify complete lane coverage", **interval(43, 46)},
                 ]})
    write(inputs, "jobs.json", {"total_count": len(jobs), "jobs": jobs})
    report = shadow.compare(inputs)
    assert report["timing"] == {
        "queue_seconds": 2, "worker_seconds": {"min": 20, "max": 23},
        "early_step_seconds": {"min": 3, "max": 6}, "summary_tail_seconds": 18,
        "verification_seconds": 3,
    }
    del jobs[0]["steps"][0]["completed_at"]
    write(inputs, "jobs.json", {"total_count": len(jobs), "jobs": jobs})
    report = shadow.compare(inputs)
    assert report["timing"]["early_step_seconds"] == {"min": None, "max": None}
    assert "early_step_seconds" in report["unavailable"]


@pytest.mark.parametrize(("change", "evidence", "expected"), [
    ("missing", {}, ("must_run", "manifest_unavailable")),
    ("malformed", {}, ("must_run", "manifest_malformed")),
    ("head", {}, ("must_run", "head_mismatch")),
    ("base", {}, ("must_run", "base_advanced")),
    ("omitted", {}, ("must_run", "not_selected_locally")),
    ("receipts", {}, ("must_run", "no_receipt")),
    ("failed", {}, ("must_run", "receipt_failed")),
    (None, {"source": "changed"}, ("must_run", "source_changed")),
    (None, {}, ("must_run", "source_unverified")),
    (None, {"source": "equivalent"}, ("must_run", "test_identity_unverified")),
    (None, {"source": "equivalent", "hosted_group": identity_summary()},
     ("would_reuse_if_lane_equivalent", "lane_unverified")),
    (None, {"source": "equivalent", "hosted_group": identity_summary(), "lane": "mismatch"},
     ("would_reuse_if_lane_equivalent", "lane_mismatch")),
    (None, {"source": "equivalent", "hosted_group": identity_summary(), "lane": "match"}, ("would_reuse", None)),
])
def test_reason_order_and_dispositions(change, evidence, expected):
    note = manifest()
    note["executions"][0]["test_identity"] = identity_summary()
    status = "present"
    if change in {"missing", "malformed"}:
        note, status = None, ("manifest_unavailable" if change == "missing" else "manifest_malformed")
    if change in {"head", "base"}:
        note[change] = TESTED
    if change == "omitted":
        note["selection"]["checks"] = []
    if change == "receipts":
        note["executions"] = []
    if change == "failed":
        note["executions"][0]["result"] = "failed"
    assert shadow.classify(note, status, HEAD, BASE, "dotfiles.full", **evidence) == expected


def test_repetition_counts_only_actual_same_source_and_runtime():
    one = (TESTED, ("linux", "3.14.5"))
    other = (TESTED, ("linux", "3.14.6"))
    early = [(one, {NODE, "another"}), (one, {NODE}), (other, {NODE})]
    partitions = [(one, {NODE}), (other, {"another"})]
    assert shadow.repetition(early, partitions) == {"identities": 1, "extra_executions": 2}
    assert shadow.repetition(None, partitions) == {"identities": None, "extra_executions": None}


@pytest.mark.parametrize(("key", "value"), [
    ("encoding", "other"), ("ids_digest", "a" * 64), ("case_count", 2),
    ("complete", False), ("reported_count", 0), ("omitted_count", 1),
    ("outcomes", {"passed": 0, "skipped": 1, "failed": 0, "error": 0}),
])
def test_exact_group_rejects_mismatched_or_incomplete_summaries(key, value):
    identity = identity_summary()
    assert shadow.whole_group(identity, identity)
    assert not shadow.whole_group({**identity, key: value}, identity)


def test_absent_run_and_note_and_wrong_type_event_report_unavailable(inputs):
    (inputs / "run.json").unlink()
    (inputs / "note.json").unlink()
    report = shadow.compare(inputs)
    assert report["manifest"] == {"status": "manifest_unavailable", "digest": None}
    assert {"run", "manifest_unavailable"} <= set(report["unavailable"])
    write(inputs, "run.json", {**run_data(), "event": []})
    assert "run" in shadow.compare(inputs)["unavailable"]


def test_affected_uses_exact_tested_commit_and_safe_runtime_projection(inputs):
    value = {"schema_version": 1, "kind": "dotfiles-validation-run",
             "adapter_id": "dotfiles.continuous-validation", "base": BASE, "head": TESTED,
             "executed": [{"check_id": "dotfiles.instructions", "status": "failed"}]}
    write(inputs, "affected/result.json", value)
    write(inputs, "affected/runtime.json", {
        "os": "linux", "architecture": "x86_64", "python": "3.14.5", "tools": {"uv": "uv 0.10.0"},
        "ignored": "not projected",
    })
    report = shadow.compare(inputs)
    assert report["lane"]["hosted"] == {"affected": {
        "os": "linux", "architecture": "x86_64", "python": "3.14.5", "tools": {"uv": "0.10.0"},
    }}
    assert report["checks"][0]["must_run"] == [{"reason": "not_selected_locally", "count": 1}]
    write(inputs, "affected/result.json", {**value, "head": HEAD})
    assert "affected" in shadow.compare(inputs)["unavailable"]
