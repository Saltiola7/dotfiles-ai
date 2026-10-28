"""Complete bounded identities and honest comparison qualification."""

import hashlib
import importlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def identity_module():
    return importlib.import_module("continuous_validation.test_identity")


def artifact(tmp_path, cases):
    root = ET.Element("testsuite")
    for attributes, outcome in cases:
        case = ET.SubElement(root, "testcase", attributes)
        if outcome:
            ET.SubElement(case, outcome, {"message": "private fixture payload"})
    path = tmp_path / "junit.xml"
    ET.ElementTree(root).write(path, encoding="utf-8")
    return path


def observation(tmp_path, number, *, receipt=None):
    ids = ["tests/test_core.py::test_ok"]
    value = {
        "schema_version": 1, "id": f"observation-{number}", "request_id": f"request-{number}",
        "snapshot_id": "a" * 64, "generation": number, "check_id": "unit",
        "lane": {"os": "linux", "architecture": "arm64", "python": "3.14",
                 "tools": {}, "dependencies": {}},
        "manifest_digest": "b" * 64, "selection_digest": "c" * 64, "cache_key": "d" * 64,
        "status": "passed", "exit_code": 0,
        "runtime": {"os": "linux", "architecture": "arm64", "python": "3.14.0"},
        "test_ids": ids, "diagnostic_codes": [], "executed": True, "cache_reused": False,
        "queue_seconds": 0.0, "elapsed_seconds": 1.0, "execution_seconds": 1.0,
        "at": "2026-10-28T00:00:00+00:00", "log_path": str(tmp_path / "private.log"),
        "advisory": True, "resource_metrics": "unavailable", "dagger_cache_metrics": "unavailable",
    }
    if receipt is not None:
        value["runtime"]["test_identity"] = receipt
    return value


def pair(tmp_path, left, right):
    paths = []
    for index, value in enumerate([left, right]):
        path = tmp_path / f"observation-{index}.json"
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        paths.append(str(path))
    return runner.compare({"schema_version": 1, "observations": paths})


def receipt(ids, **changes):
    return {"schema_version": 1, "kind": "pytest-junit-v1",
            "encoding": "pytest-nodeid-or-sha256-v1", "scope": "completed", "complete": True,
            "case_count": len(ids), "reported_count": len(ids),
            "outcomes": {"passed": len(ids), "failed": 0, "error": 0, "skipped": 0},
            "opaque_count": 0, "omitted_count": 0,
            "ids_digest": hashlib.sha256(canonical(ids)).hexdigest(), "failed_test_ids": [], **changes}


def test_identical_legacy_partial_identity_lists_are_not_qualified(tmp_path):
    result = pair(tmp_path, observation(tmp_path, 1), observation(tmp_path, 2))
    assert result["status"] == "unqualified"
    assert all("test_identity_unqualified" in reasons for reasons in result["qualification_reasons"])


def test_explicit_non_pytest_evidence_remains_comparable(tmp_path):
    values = [observation(tmp_path, n, receipt={"schema_version": 1, "kind": "not_applicable"})
              for n in [1, 2]]
    for value in values:
        value["test_ids"] = []
    assert pair(tmp_path, *values)["status"] == "matched"


def test_complete_receipts_compare_inputs_and_report_outcomes_separately(tmp_path):
    left = observation(tmp_path, 1)
    ids = left["test_ids"]
    left["runtime"]["test_identity"] = receipt(ids)
    right = observation(tmp_path, 2, receipt=receipt(ids,
        outcomes={"passed": 0, "failed": 1, "error": 0, "skipped": 0}, failed_test_ids=ids))
    right.update(status="failed", exit_code=1)
    result = pair(tmp_path, left, right)
    assert result["status"] == "matched"
    assert result["test_outcomes"] == [left["runtime"]["test_identity"]["outcomes"],
                                       right["runtime"]["test_identity"]["outcomes"]]


@pytest.mark.parametrize("changes", [
    {"case_count": 2}, {"complete": False}, {"ids_digest": "0" * 64},
    {"omitted_count": 1}, {"failed_test_ids": ["not-a-completed-case"]},
    {"outcomes": {"passed": True, "failed": 0, "error": 0, "skipped": 0}},
])
def test_malformed_receipt_cannot_qualify_or_hide_omissions(tmp_path, changes):
    left = observation(tmp_path, 1)
    left["runtime"]["test_identity"] = receipt(left["test_ids"], **changes)
    with pytest.raises(runner.ValidationError):
        runner.validate_observation(left)


def test_long_cases_module_skip_and_all_outcomes_are_complete(tmp_path):
    cases = [({"classname": "tests.test_core", "name": "test_ok"}, None),
             ({"classname": "tests.test_core", "name": "test_failed"}, "failure"),
             ({"classname": "tests.test_core", "name": "test_error"}, "error"),
             ({"name": "tests.test_core"}, "skipped")]
    for length in [517, 984, 1369, 4225, 65618]:
        cases.append(({"classname": "tests.test_core", "name": "test_long[" + "x" * length + "]"}, None))
    ids, evidence = identity_module().collect_junit(artifact(tmp_path, cases), ["tests/test_core.py"])
    assert len(ids) == evidence["case_count"] == evidence["reported_count"] == 9
    assert evidence["outcomes"] == {"passed": 6, "failed": 1, "error": 1, "skipped": 1}
    assert evidence["opaque_count"] == 5
    assert evidence["omitted_count"] == 0
    assert evidence["failed_test_ids"] == ["tests/test_core.py::test_error", "tests/test_core.py::test_failed"]
    assert all(len(value) <= 512 for value in ids)
    assert "x" * 517 not in json.dumps(ids)
    assert evidence["ids_digest"] == hashlib.sha256(canonical(ids)).hexdigest()
    identity_module().validate_receipt(evidence, ids)


@pytest.mark.parametrize("name", ["test_λ", "test_bad\ncase"])
def test_nonprintable_case_uses_stable_opaque_identity(tmp_path, name):
    path = artifact(tmp_path, [({"classname": "tests.test_core", "name": name, "time": "1"}, None)])
    first = identity_module().collect_junit(path, ["tests/test_core.py"])
    path = artifact(tmp_path, [({"classname": "tests.test_core", "name": name, "time": "9"}, "failure")])
    second = identity_module().collect_junit(path, ["tests/test_core.py"])
    assert first[0] == second[0]
    assert first[0][0].startswith("pytest-junit-sha256:")


@pytest.mark.parametrize("cases", [
    [({"classname": "outside.test_core", "name": "test_other"}, None)],
    [({"name": "unknown.module"}, "skipped")],
    [({"classname": "tests.test_core", "name": "test_same"}, None)] * 2,
    [],
])
def test_unknown_duplicate_and_empty_case_evidence_fails_closed(tmp_path, cases):
    with pytest.raises(ValueError):
        identity_module().collect_junit(artifact(tmp_path, cases), ["tests/test_core.py"])


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
def test_doctype_ban_is_independent_of_xml_byte_encoding(tmp_path, encoding):
    path = tmp_path / "junit.xml"
    path.write_bytes(('<?xml version="1.0" encoding="' + encoding + '"?>'
        '<!DOCTYPE testsuite [<!ENTITY fixture "expanded">]>'
        '<testsuite><testcase classname="tests.test_core" name="test_&fixture;"/></testsuite>').encode(encoding))
    with pytest.raises(ValueError):
        identity_module().collect_junit(path, ["tests/test_core.py"])
