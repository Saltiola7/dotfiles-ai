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


@pytest.mark.parametrize("target", ["surface", "unit", "warmup"])
def test_malformed_shapes_and_missing_warmup_fail_with_contract_error(evidence, target):
    record = sample_record(evidence)
    if target == "surface":
        record["cell"]["surface"] = []
    elif target == "unit":
        record["cell"]["metrics"]["wall_ns"]["unit"] = {}
    else:
        record["attempts"] = record["attempts"][1:]
        for i, attempt in enumerate(record["attempts"]):
            attempt["sequence"] = i
    with pytest.raises(evidence.EvidenceError):
        evidence.build_record(
            record["source"], record["environment"], record["cell"], record["attempts"], 5
        )


def test_non_regular_and_hardlinked_evidence_is_refused(evidence, tmp_path):
    directory = evidence.create_private_output(tmp_path / "evidence")
    path = evidence.write_private_json(directory, "cell.json", sample_record(evidence))
    os.link(path, directory / "hardlink.json")
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([path])
    fifo = directory / "fifo.json"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(evidence.EvidenceError):
        evidence.read_records([fifo])


def test_analysis_deadline_covers_validation_and_ingestion(evidence, tmp_path, monkeypatch):
    record = sample_record(evidence)
    directory = evidence.create_private_output(tmp_path / "evidence")
    path = evidence.write_private_json(directory, "cell.json", record)
    with pytest.raises(evidence.EvidenceError, match="analysis_budget_exhausted"):
        evidence.validate_record(record, deadline=0)
    with pytest.raises(evidence.EvidenceError, match="analysis_budget_exhausted"):
        evidence.read_records([path], deadline=0)
    clock = iter(range(1000))
    monkeypatch.setattr(evidence.time, "monotonic", lambda: next(clock))
    with pytest.raises(evidence.EvidenceError, match="analysis_budget_exhausted"):
        evidence.read_records([path], deadline=10)

class TestRunner:
    def test_owned_process_captures_both_streams_and_actual_status(self, tmp_path):
        runner = load_module("python_performance")
        result = runner.run_owned(
            [sys.executable, "-I", "-S", "-c",
             "import sys;print('out');print('err',file=sys.stderr);sys.exit(3)"],
            tmp_path, {"PATH": os.defpath}, 2,
        )
        assert result.status == "completed"
        assert result.returncode == 3
        assert result.stdout == b"out\n"
        assert result.stderr == b"err\n"
        assert result.wall_ns > 0
        assert result.cleanup_complete

    def test_blocked_stdin_cannot_bypass_timeout(self, tmp_path):
        import time
        runner = load_module("python_performance")
        started = time.monotonic()
        result = runner.run_owned(
            [sys.executable, "-I", "-S", "-c", "import time;time.sleep(10)"],
            tmp_path, {"PATH": os.defpath}, .15, input_data=b"x" * 262144,
        )
        assert result.status == "timed_out"
        assert result.cleanup_complete
        assert time.monotonic() - started < 3

    def test_output_before_reading_input_is_serviced_concurrently(self, tmp_path):
        runner = load_module("python_performance")
        result = runner.run_owned(
            [sys.executable, "-I", "-S", "-c",
             "import sys;sys.stdout.buffer.write(b'x'*131072);sys.stdout.flush();"
             "print(len(sys.stdin.buffer.read()))"],
            tmp_path, {"PATH": os.defpath}, 2, input_data=b"y" * 131072,
        )
        assert result.status == "completed"
        assert result.returncode == 0
        assert result.stdout.endswith(b"131072\n")
        assert result.cleanup_complete

    def test_overflow_and_cancellation_have_terminal_dispositions(self, tmp_path):
        runner = load_module("python_performance")
        result = runner.run_owned(
            [sys.executable, "-I", "-S", "-c", "print('x'*100000)"],
            tmp_path, {"PATH": os.defpath}, 2, stream_limit=1024,
        )
        assert result.status == "output_overflow"
        assert len(result.stdout) <= 1024
        assert result.cleanup_complete
        cancelled = runner.run_owned(
            [sys.executable, "-I", "-S", "-c", "import time;time.sleep(10)"],
            tmp_path, {"PATH": os.defpath}, 2, cancelled=lambda: True,
        )
        assert cancelled.status == "cancelled"
        assert cancelled.cleanup_complete

    def test_isolated_environment_drops_credential_and_source_injection(self, tmp_path, monkeypatch):
        runner = load_module("python_performance")
        for key in ("GH_TOKEN", "OPENAI_API_KEY", "PYTHONPATH", "GIT_DIR",
                    "SSH_AUTH_SOCK", "DBSCTR_IMPROVEMENT_WORKER_ID", "DYLD_INSERT_LIBRARIES"):
            monkeypatch.setenv(key, "private_sentinel")
        env = runner.isolated_environment(tmp_path, Path("/usr/bin/git"))
        assert set(env).isdisjoint({
            "GH_TOKEN", "OPENAI_API_KEY", "PYTHONPATH", "GIT_DIR",
            "SSH_AUTH_SOCK", "DBSCTR_IMPROVEMENT_WORKER_ID", "DYLD_INSERT_LIBRARIES",
        })
        assert env["HOME"] == str(tmp_path / "home")
        assert env["GIT_OPTIONAL_LOCKS"] == "0"

    def test_fixture_manifest_is_deterministic_and_has_no_approval(self):
        runner = load_module("python_performance")
        first = runner.fixture_manifest(100)
        assert first == runner.fixture_manifest(100)
        assert len(first["slices"]) == 100
        assert all(row["state"] == "captured" for row in first["slices"])
        assert all(row["state"] != "delivered" for row in first["slices"])
        assert "approval" not in json.dumps(first)

    def test_offline_report_keeps_files_and_host_cohorts_separate(self, evidence, tmp_path):
        runner = load_module("python_performance")
        directory = evidence.create_private_output(tmp_path / "inputs")
        first = sample_record(evidence)
        second = copy.deepcopy(first)
        second["environment"]["execution_cohort"] = "6" * 32
        paths = [
            evidence.write_private_json(directory, "first.json", first),
            evidence.write_private_json(directory, "second.json", second),
        ]
        report = runner.report_records(paths)
        assert report["input_authenticity"] == "unverified"
        assert len(report["records"]) == 2
        assert report["aggregated_across_inputs"] is False
        assert all("attempts" not in row for row in report["records"])
        assert all(row["summary"] == first["summary"] for row in report["records"])

    def test_report_never_executes_input_and_refuses_bad_summaries(self, evidence, tmp_path):
        runner = load_module("python_performance")
        directory = evidence.create_private_output(tmp_path / "inputs")
        record = sample_record(evidence)
        record["summary"]["wall_ns"]["mean"] = 0
        path = evidence.write_private_json(directory, "bad.json", record)
        with pytest.raises(evidence.EvidenceError):
            runner.report_records([path])

    def test_smoke_cohorts_use_committed_source_and_retain_profiles(self, evidence, tmp_path):
        import shutil
        import subprocess
        runner = load_module("python_performance")
        git = Path(shutil.which("git")).resolve()
        env = runner.isolated_environment(tmp_path / "setup", git)
        selected = tmp_path / "source"
        selected.mkdir()
        templates = tmp_path / "empty"
        templates.mkdir()
        def call(*args):
            return subprocess.run(
                [str(git), "-c", "core.hooksPath=/dev/null", "-c",
                 "commit.gpgsign=false", *args], cwd=selected, env=env,
                capture_output=True, check=True,
            )
        call("init", "--initial-branch=main", "--template=" + str(templates))
        for relative in (
            "dot_local/bin/executable_dbsctrctl", "uv.lock",
            "tests/benchmarks/python_performance.py",
            "tests/benchmarks/performance_evidence.py",
            "tests/benchmarks/fixtures/cli_workloads.json",
        ):
            destination = selected / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / relative).read_bytes())
        call("config", "user.name", "Synthetic Benchmark")
        call("config", "user.email", "benchmark@example.invalid")
        call("add", ".")
        call("commit", "-m", "synthetic source")
        before = call("rev-parse", "HEAD").stdout
        output = tmp_path / "results"
        executed = subprocess.run(
            [sys.executable, "-I", "-S", "-B",
             str(selected / "tests/benchmarks/python_performance.py"), "cli",
             "--source-tree", str(selected), "--output", str(output),
             "--smoke", "--profile"],
            env={**env, "GH_TOKEN": "private_sentinel", "GIT_DIR": "/unavailable"},
            capture_output=True, text=True, timeout=90,
        )
        assert executed.returncode == 0, executed.stdout + executed.stderr
        assert call("rev-parse", "HEAD").stdout == before
        assert call("status", "--porcelain").stdout == b""
        index = json.loads((output / "index.json").read_text())
        assert index["cohort"] == "smoke"
        assert len(index["records"]) == 24
        records = evidence.read_records([output / name for name in index["records"]])
        assert all(record["coverage"]["complete"] for record in records)
        assert all(record["coverage"]["planned"] == 1 for record in records)
        assert all(record["coverage"]["warmups"] == 1 for record in records)
        assert not (output / "scratch").exists()
        profiles = list((output / "profiles").glob("*.pstats"))
        assert len(profiles) == 16
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in profiles)
        assert "private_sentinel" not in json.dumps(records)
        import time
        snapshot = runner.SourceSnapshot.observe(selected, git, env, time.monotonic() + 10)
        lock = selected / "uv.lock"
        before_lock = lock.read_bytes()
        lock.write_bytes(before_lock + b"\n")
        with pytest.raises(runner.BenchmarkError):
            snapshot.verify(git, env, time.monotonic() + 10)
        lock.write_bytes(before_lock)
        assert call("status", "--porcelain").stdout == b""

    def test_cancelled_or_uncertain_control_never_admits_another_child(self, tmp_path, monkeypatch):
        runner = load_module("python_performance")
        launched = []
        def forbidden(*args, **kwargs):
            launched.append(args)
            raise AssertionError("new process after stop")
        monkeypatch.setattr(runner, "run_owned", forbidden)
        import time
        for control in (
            runner.RunControl(cancelled=True), runner.RunControl(cleanup_known=False),
        ):
            with pytest.raises(runner.BenchmarkError):
                runner.git_call(Path("/usr/bin/git"), tmp_path, {}, time.monotonic() + 10,
                                "status", control=control)
        assert not launched

    def test_mid_setup_cancellation_is_terminal_before_next_launch(self, tmp_path, monkeypatch):
        runner = load_module("python_performance")
        control = runner.RunControl()
        launched = []
        def cancelled_after_start(*args, **kwargs):
            launched.append(args)
            control.cancelled = True
            return runner.ProcessResult("completed", 0, b"", b"", 1, None, True)
        monkeypatch.setattr(runner, "run_owned", cancelled_after_start)
        import time
        with pytest.raises(runner.BenchmarkError, match="cancelled"):
            runner.create_fixture(tmp_path / "fixture", 100, Path("/usr/bin/git"), {},
                                  time.monotonic() + 10, control)
        assert len(launched) == 1

    def test_launch_and_fixture_identity_changes_refuse_freshness(self, tmp_path, monkeypatch):
        import shutil
        import time
        runner = load_module("python_performance")
        binary = tmp_path / "binary"
        binary.write_bytes(b"original")
        proof = runner.LaunchProof.observe([binary])
        binary.write_bytes(b"changed")
        with pytest.raises(runner.BenchmarkError, match="launch_identity_changed"):
            proof.verify()
        git = Path(shutil.which("git")).resolve()
        env = runner.isolated_environment(tmp_path / "state", git)
        fixture, _ = runner.create_fixture(tmp_path / "fixture", 1, git, env, time.monotonic() + 10)
        frozen = runner.FixtureProof.observe(fixture, git, env, time.monotonic() + 10)
        (fixture / "README.md").write_bytes(b"changed")
        def forbidden(*args, **kwargs):
            raise AssertionError("altered fixture triggered Git")
        monkeypatch.setattr(runner, "git_call", forbidden)
        with pytest.raises(runner.BenchmarkError, match="fixture_changed"):
            frozen.verify(git, env, time.monotonic() + 10)

    def test_source_filters_are_refused_before_status_can_execute(self, tmp_path):
        import shlex
        import shutil
        import subprocess
        import time
        runner = load_module("python_performance")
        git = Path(shutil.which("git")).resolve()
        env = runner.isolated_environment(tmp_path / "state", git)
        selected = tmp_path / "source"
        selected.mkdir()
        empty = tmp_path / "empty"
        empty.mkdir()
        def call(*args):
            return subprocess.run(
                [str(git), "-c", "core.hooksPath=/dev/null",
                 "-c", "commit.gpgsign=false", *args],
                cwd=selected, env=env, capture_output=True, check=True,
            )
        call("init", "--initial-branch=main", "--template=" + str(empty))
        call("config", "user.name", "Synthetic Benchmark")
        call("config", "user.email", "benchmark@example.invalid")
        (selected / ".gitattributes").write_text("tracked.txt filter=canary\n")
        tracked = selected / "tracked.txt"
        tracked.write_text("original\n")
        call("add", ".")
        call("commit", "-m", "synthetic")
        marker = tmp_path / "executed"
        code = f"from pathlib import Path;import sys;Path({str(marker)!r}).write_text('executed');print(sys.stdin.read())"
        call("config", "filter.canary.clean",
             shlex.quote(sys.executable) + " -I -S -c " + shlex.quote(code))
        tracked.write_text("changed\n")
        with pytest.raises(runner.BenchmarkError, match="source_filters_unqualified"):
            runner.SourceSnapshot.observe(selected, git, env, time.monotonic() + 10)
        assert not marker.exists()
