"""Behavioral contracts for opt-in, synthetic Python performance tooling."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

import pytest


ROOT = Path(__file__).parents[1]
BENCHMARKS = ROOT / "tests/benchmarks"


def load_module(name):
    path = BENCHMARKS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def evidence():
    return load_module("performance_evidence")


def sample_record(evidence, values=(10, 20, 30, 40, 50)):
    source = {
        "commit": "a" * 40, "tree": "b" * 40, "tool_commit": "c" * 40,
        "lock_sha256": "d" * 64, "workload_sha256": "e" * 64, "clean": True,
    }
    environment = {
        "python": "3.14.9", "python_sha256": "1" * 64,
        "git_version": "git version 2.56.0", "git_sha256": "2" * 64,
        "os": "Darwin", "os_version": "25.0.0", "architecture": "arm64",
        "cpu_count": 8, "execution_cohort": "3" * 32,
    }
    cell = {
        "surface": "cli", "workload": "status_empty",
        "dimensions": {"history_commits": 1, "cohort": "smoke"},
        "fixture_sha256": "4" * 64, "instrumentation": "timing",
        "cache": "fresh_process_uncontrolled_filesystem",
        "metrics": {
            "wall_ns": {"unit": "ns", "scope": "whole_process", "required": True},
            "cpu_ns": {"unit": "ns", "scope": "owned_children", "required": False},
        },
    }
    attempts = []
    for sequence, value in enumerate((999999, *values)):
        attempts.append({
            "sequence": sequence, "warmup": sequence == 0, "status": "partial",
            "reason": None, "compatible": True, "returncode": 0,
            "metrics": {"wall_ns": value, "cpu_ns": None},
            "unavailable": {"cpu_ns": "unqualified_process_cpu"},
            "output_sha256": "5" * 64,
        })
    return evidence.build_record(source, environment, cell, attempts, len(values))


def test_partial_observations_retain_primary_timing_and_denominators(evidence):
    record = sample_record(evidence)
    assert evidence.validate_record(record) == record
    assert record["summary"]["wall_ns"] == {"n": 5, "mean": 30, "p50": 30, "p90": 50}
    assert record["summary"]["cpu_ns"] == {"n": 0, "mean": None, "p50": None, "p90": None}
    assert record["coverage"]["planned"] == 5
    assert record["coverage"]["attempted"] == 5
    assert record["coverage"]["partial"] == 5
    assert record["coverage"]["complete"] is True


def test_statistics_use_nearest_rank_and_integer_floor(evidence):
    record = sample_record(evidence, (1, 1, 2, 9))
    assert record["summary"]["wall_ns"] == {"n": 4, "mean": 3, "p50": 1, "p90": 9}


def test_summary_is_invariant_to_values_order_but_keeps_all_attempts(evidence):
    import itertools
    summaries = []
    for values in itertools.permutations((0, 2, 7)):
        record = sample_record(evidence, values)
        summaries.append(record["summary"])
        assert len(record["attempts"]) == 4
    assert all(item == summaries[0] for item in summaries)


@pytest.mark.parametrize("value", [True, -1, float("inf"), float("nan"), "10", {"ns": 10}])
def test_invalid_numeric_values_are_rejected_without_coercion(evidence, value):
    record = sample_record(evidence)
    record["attempts"][1]["metrics"]["wall_ns"] = value
    with pytest.raises(evidence.EvidenceError):
        evidence.validate_record(record)


@pytest.mark.parametrize("field", ["summary", "coverage"])
def test_derived_statistics_cannot_be_forged(evidence, field):
    record = sample_record(evidence)
    if field == "summary":
        record[field]["wall_ns"]["mean"] = 0
    else:
        record[field]["attempted"] = 999
    with pytest.raises(evidence.EvidenceError):
        evidence.validate_record(record)


def test_unknown_fields_and_inconsistent_attempts_are_rejected(evidence):
    for mutation in (
        lambda r: r.update({"extra": {}}),
        lambda r: r["source"].update({"clean": False}),
        lambda r: r["environment"].update({"cpu_count": True}),
        lambda r: r["attempts"][1].update({"sequence": 0}),
        lambda r: r["attempts"][1].update({"status": "measured"}),
        lambda r: r["attempts"][1]["unavailable"].clear(),
        lambda r: r["cell"]["dimensions"].update({"path": "/private/source"}),
    ):
        record = sample_record(evidence)
        mutation(record)
        with pytest.raises(evidence.EvidenceError):
            evidence.validate_record(record)


def test_failures_and_not_attempted_cells_remain_in_planned_population(evidence):
    record = sample_record(evidence, (10, 20, 30))
    for i, status in ((2, "timed_out"), (3, "not_attempted")):
        row = record["attempts"][i]
        row.update({
            "status": status, "reason": "budget_exhausted", "compatible": False,
            "returncode": None, "metrics": {"wall_ns": None, "cpu_ns": None},
            "unavailable": {"wall_ns": "budget_exhausted", "cpu_ns": "budget_exhausted"},
            "output_sha256": None,
        })
    record = evidence.build_record(
        record["source"], record["environment"], record["cell"], record["attempts"], 3
    )
    assert record["coverage"]["planned"] == 3
    assert record["coverage"]["attempted"] == 2
    assert record["coverage"]["timed_out"] == 1
    assert record["coverage"]["not_attempted"] == 1
    assert record["coverage"]["complete"] is False
    assert record["summary"]["wall_ns"]["n"] == 1


def test_builder_does_not_mutate_or_share_caller_state(evidence):
    record = sample_record(evidence)
    original = copy.deepcopy(record)
    rebuilt = evidence.build_record(
        record["source"], record["environment"], record["cell"], record["attempts"], 5
    )
    rebuilt["attempts"][1]["metrics"]["wall_ns"] = 100
    assert record == original


def test_private_records_roundtrip_without_overwriting(evidence, tmp_path):
    directory = evidence.create_private_output(tmp_path / "evidence")
    record = sample_record(evidence)
    path = evidence.write_private_json(directory, "cell.json", record)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert evidence.read_records([path]) == [record]
    before = path.read_bytes()
    with pytest.raises(evidence.EvidenceError):
        evidence.write_private_json(directory, "cell.json", record)
    assert path.read_bytes() == before


def test_duplicate_records_keys_and_links_are_refused(evidence, tmp_path):
    directory = evidence.create_private_output(tmp_path / "evidence")
    record = sample_record(evidence)
    path = evidence.write_private_json(directory, "first.json", record)
    other = evidence.write_private_json(directory, "other.json", record)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([path, other])
    linked = directory / "linked.json"
    linked.symlink_to(path)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([linked])
    bad = directory / "bad.json"
    bad.write_text('{"schema_version":1,"schema_version":1}')
    bad.chmod(0o600)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([bad])


def test_ingestion_checks_sizes_populations_and_private_modes(evidence, tmp_path, monkeypatch):
    directory = evidence.create_private_output(tmp_path / "evidence")
    path = evidence.write_private_json(directory, "cell.json", sample_record(evidence))
    path.chmod(0o644)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([path])
    path.chmod(0o600)
    monkeypatch.setattr(evidence, "MAX_FILE_BYTES", 32)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([path])
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([path] * 33)


def test_output_paths_cannot_alias_source_or_existing_state(evidence, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(evidence.EvidenceError):
        evidence.create_private_output(source / "results", source)
    link = tmp_path / "link"
    link.symlink_to(source, target_is_directory=True)
    with pytest.raises(evidence.EvidenceError):
        evidence.create_private_output(link / "results")
    output = evidence.create_private_output(tmp_path / "results")
    with pytest.raises(evidence.EvidenceError):
        evidence.create_private_output(output)
    for name in ("../escape.json", "/escape.json", "two/files.json"):
        with pytest.raises(evidence.EvidenceError):
            evidence.write_private_json(output, name, {})
