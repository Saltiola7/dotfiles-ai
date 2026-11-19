"""Parent ownership and compatibility for optional native remote-engine use."""

import copy
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import pytest

from test_continuous_validation import configured, private_json, request, runner, worktree


def manifest(*, backend="dagger", timeout=3600, engine=None):
    configuration = {} if engine is None else {"engine": engine}
    return {
        "schema_version": 1,
        "adapter_id": "remote-fixture",
        "input_patterns": ["**"],
        "checks": [{
            "id": "remote-check", "class": "expensive", "backend": backend,
            "lane": {"os": "linux", "architecture": "amd64", "python": "3.14",
                     "tools": {}, "dependencies": {}},
            "timeout_seconds": timeout, "cacheable": False,
            "configuration": configuration,
        }],
    }


@pytest.mark.parametrize("backend", ["native", "dagger"])
def test_unqualified_checks_preserve_the_existing_timeout_limit(backend):
    value = manifest(backend=backend)
    assert runner.validate_manifest(value) == value
    with pytest.raises(runner.ValidationError):
        runner.validate_manifest(manifest(backend=backend, timeout=3601))


def test_disabled_remote_enrollment_creates_no_state_or_adapter_process(tmp_path, monkeypatch):
    state = tmp_path / "absent"
    path = private_json(tmp_path / "disabled.json", {
        "schema_version": 1, "enabled": False, "state_dir": str(state),
        "adapter_config": {"remote_engine": {"invalid_but_disabled": True}},
    })
    monkeypatch.setattr(runner, "process", lambda *args, **kwargs: pytest.fail("disabled adapter"))
    result = runner.run_request(request(path, "checkpoint"))
    assert result["status"] == "disabled"
    assert not state.exists()


@pytest.mark.parametrize("action", ["describe", "select", "execute"])
def test_control_carrier_is_not_an_adapter_child_api(tmp_path, monkeypatch, action):
    config = {"dagger": {"engine": "unix:///private/fixture.sock"},
              "remote_engine": {"control_helper": "/private/prepared-control"}}
    enrolled = {"adapter_config": copy.deepcopy(config), "adapter_python": sys.executable,
                "adapter": ".ci/adapter.py"}
    calls = []

    def process(argv, payload, *args):
        calls.append((argv, payload))
        return {"fixture": True}

    monkeypatch.setattr(runner, "process", process)
    assert runner.adapter_call(enrolled, action, {"schema_version": 1}, tmp_path, tmp_path) == {"fixture": True}
    assert calls[0][1]["config"] == {"dagger": config["dagger"]}
    assert enrolled["adapter_config"] == config


@pytest.mark.parametrize("namespace", ["remote_engine", "remote_execution"])
def test_repository_results_cannot_supply_parent_owned_runtime_proof(configured, monkeypatch, namespace):
    path, _ = configured
    ordinary = runner.adapter_call

    def malicious(enrollment, action, *args, **kwargs):
        value = ordinary(enrollment, action, *args, **kwargs)
        if action == "execute":
            value["runtime"][namespace] = {"forged": True}
        return value

    monkeypatch.setattr(runner, "adapter_call", malicious)
    result = runner.run_request(request(path, "checkpoint"))
    assert result["status"] == "unavailable"
    observation = result["observations"][0]
    assert observation["status"] == "unavailable"
    assert namespace not in observation["runtime"]


def comparable_runtime(*, lease="lease-one", endpoint="a" * 64):
    return {
        "lane": {"os": "linux", "architecture": "amd64", "python": "3.14",
                 "tools": {}, "dependencies": {}},
        "runtime": {
            "os": "linux", "architecture": "amd64", "python": "3.14.1",
            "remote_engine": {"endpoint_digest": endpoint, "installation_digest": "b" * 64,
                              "runtime_digest": "c" * 64, "resource_profile_digest": "d" * 64,
                              "owner_digest": "e" * 64},
            "remote_execution": {"lease_id": lease, "elapsed_seconds": 1.0},
        },
    }


def test_remote_execution_measurements_do_not_change_comparison_identity():
    first, first_qualified = runner.comparison_runtime(comparable_runtime(lease="lease-one"))
    second, second_qualified = runner.comparison_runtime(comparable_runtime(lease="lease-two"))
    assert first_qualified is True and second_qualified is True
    assert first == second
    assert "remote_execution" not in first


def test_stable_remote_engine_pins_remain_comparison_inputs():
    first, _ = runner.comparison_runtime(comparable_runtime(endpoint="a" * 64))
    second, _ = runner.comparison_runtime(comparable_runtime(endpoint="f" * 64))
    assert first != second
    assert first["remote_engine"]["endpoint_digest"] == "a" * 64


def test_only_remote_execution_is_added_to_measurement_projection():
    assert runner.RUNTIME_MEASUREMENTS == {
        "cache", "cache_metrics", "cache_counters", "metrics", "resource_metrics",
        "dagger_cache_metrics", "artifacts", "termination_signal", "test_identity",
        "advisory_review", "remote_execution",
    }


@pytest.fixture
def remote_enrollment(configured):
    path, enrollment = configured
    # Native Unix socket limits are smaller than pytest's normal macOS paths.
    with tempfile.TemporaryDirectory(prefix="cv-runner-", dir="/private/tmp") as folder:
        private = Path(folder)
        helper = private / "control"
        helper.write_text("#!" + sys.executable + "\nraise SystemExit(99)\n")
        helper.chmod(0o700)
        engine = "unix://" + str(private / "engine.sock")
        receipt = {
            "schema_version": 1, "kind": "cv-native-remote-engine-v1",
            "repository_id": enrollment["repository_id"], "endpoint_id": "fixture-endpoint",
            "endpoint_digest": "a" * 64, "owner_digest": "b" * 64,
            "installation_digest": "c" * 64, "runtime_digest": "d" * 64,
            "resource_profile_digest": "e" * 64, "budget_id": "fixture-budget",
            "budget_permission_digest": "f" * 64, "engine_uri": engine,
            "max_execution_seconds": 7500,
        }
        receipt_path = private / "activation.json"
        raw = (json.dumps(receipt, indent=2) + "\n").encode()
        receipt_path.write_bytes(raw)
        receipt_path.chmod(0o600)
        enrollment = {**enrollment, "adapter_config": {
            "dagger": {"engine": engine},
            "remote_engine": {
                "schema_version": 1, "endpoint_id": receipt["endpoint_id"],
                "endpoint_digest": receipt["endpoint_digest"],
                "activation_receipt": str(receipt_path),
                "activation_sha256": hashlib.sha256(raw).hexdigest(),
                "control_helper": str(helper),
                "control_helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
            },
        }}
        private_json(path, enrollment)
        yield path, enrollment, receipt


def test_qualified_manifest_can_declare_remote_total_limit(remote_enrollment):
    _, enrollment, receipt = remote_enrollment
    value = manifest(timeout=7500, engine=receipt["engine_uri"])
    assert runner.validate_manifest(value, enrollment=enrollment) == value
    with pytest.raises(runner.ValidationError):
        runner.validate_manifest(manifest(timeout=7501, engine=receipt["engine_uri"]), enrollment=enrollment)


def test_remote_permission_does_not_unlock_a_long_native_check(remote_enrollment):
    _, enrollment, receipt = remote_enrollment
    with pytest.raises(runner.ValidationError):
        runner.validate_manifest(manifest(backend="native", timeout=3601, engine=receipt["engine_uri"]),
                                 enrollment=enrollment)


@pytest.mark.parametrize("timeout", [3600, 7500])
def test_remote_descriptor_must_project_exact_preselected_uri(remote_enrollment, timeout):
    _, enrollment, _ = remote_enrollment
    with pytest.raises(runner.ValidationError):
        runner.validate_manifest(manifest(timeout=timeout, engine="unix:///private/another.sock"),
                                 enrollment=enrollment)


def fake_remote_execution(monkeypatch, remote_enrollment, *, unknown_cleanup=False,
                          child_namespace=None, interrupted=False):
    """Use a local adapter and controlled host owner, without any SSH or engine."""
    path, enrollment, receipt = remote_enrollment
    module = importlib.import_module("continuous_validation.remote_engine")
    check = manifest(timeout=7500, engine=receipt["engine_uri"])["checks"][0]
    seen = []
    session = SimpleNamespace(work_timeout=17, runtime={}, cancel=lambda: False)

    def active_admission():
        index = runner.read_private(runner.budget_root() / "index.json")
        return [entry for entry in index["entries"] if entry["state"] == "running"]

    class Owner:
        def __init__(self, config, proof_dir):
            seen.append(("owner", Path(proof_dir)))

    @contextmanager
    def engine_session(config, selected, *, execution, owner, cancel, remaining_seconds):
        admitted = active_admission()
        assert len(admitted) == 1 and admitted[0]["class"] == "expensive"
        assert selected == check
        assert execution["repository_id"] == enrollment["repository_id"]
        assert execution["check_digest"] == runner.digest(check)
        assert execution["check_id"] == check["id"]
        for field in ("snapshot_id", "manifest_digest", "selection_digest"):
            assert len(execution[field]) == 64
        assert remaining_seconds <= 7500
        seen.append(("open", execution))
        try:
            yield session
        finally:
            assert len(active_admission()) == 1
            seen.append(("stop", None))
            if unknown_cleanup:
                raise runner.UncertainTermination("remote_cleanup_unconfirmed")
            session.runtime = {
                "remote_engine": {name: receipt[name] for name in (
                    "endpoint_digest", "installation_digest", "runtime_digest",
                    "resource_profile_digest", "owner_digest")},
                "remote_execution": {"lease_id": "fixture-lease", "cleanup_confirmed": True},
            }

    ordinary = runner.adapter_call

    def adapter(enrolled, action, payload, root, state, cancel=lambda: False, timeout=60):
        if action == "describe":
            assert not seen
            return manifest(timeout=7500, engine=receipt["engine_uri"])
        if action == "select":
            assert not seen
            return {"schema_version": 1, "checks": [check["id"]], "reason": "fixture", "complete": True}
        assert action == "execute"
        assert [event[0] for event in seen] == ["owner", "open"]
        assert len(active_admission()) == 1
        assert timeout <= session.work_timeout
        assert set(payload) == {"schema_version", "snapshot", "base", "trigger", "check", "log_path"}
        assert payload["check"] == check
        assert Path(payload["snapshot"]) != Path(enrollment["worktree"])
        seen.append(("execute", timeout))
        if interrupted:
            raise runner.Interrupted("execution_timeout")
        value = ordinary(enrolled, action, payload, root, state, cancel, timeout)
        if child_namespace:
            value["runtime"][child_namespace] = {"forged": True}
        return value

    monkeypatch.setattr(module, "OwnerControl", Owner)
    monkeypatch.setattr(module, "remote_engine_session", engine_session)
    monkeypatch.setattr(runner, "adapter_call", adapter)
    return runner.run_request(request(path, "checkpoint")), seen, session


def test_one_outer_guard_holds_admission_around_adapter_and_cleanup(remote_enrollment, monkeypatch):
    result, seen, session = fake_remote_execution(monkeypatch, remote_enrollment)
    assert result["status"] == "passed"
    assert [event[0] for event in seen] == ["owner", "open", "execute", "stop"]
    observation = result["observations"][0]
    assert observation["runtime"]["remote_engine"] == session.runtime["remote_engine"]
    assert observation["runtime"]["remote_execution"] == session.runtime["remote_execution"]
    assert runner.read_private(runner.budget_root() / "index.json")["entries"] == []


def test_unknown_remote_cleanup_keeps_the_admission_charged(remote_enrollment, monkeypatch):
    result, seen, _ = fake_remote_execution(monkeypatch, remote_enrollment, unknown_cleanup=True)
    assert result["status"] == "unavailable"
    assert [event[0] for event in seen] == ["owner", "open", "execute", "stop"]
    entries = runner.read_private(runner.budget_root() / "index.json")["entries"]
    assert len(entries) == 1 and entries[0]["state"] == "unknown"


def test_child_timeout_still_leaves_the_outer_guard_for_exact_cleanup(remote_enrollment, monkeypatch):
    result, seen, _ = fake_remote_execution(monkeypatch, remote_enrollment, interrupted=True)
    assert result["status"] == "unavailable"
    assert [event[0] for event in seen] == ["owner", "open", "execute", "stop"]
    assert runner.read_private(runner.budget_root() / "index.json")["entries"] == []


@pytest.mark.parametrize("namespace", ["remote_engine", "remote_execution"])
def test_remote_child_proof_is_rejected_before_parent_enrichment(remote_enrollment, monkeypatch, namespace):
    result, seen, _ = fake_remote_execution(monkeypatch, remote_enrollment, child_namespace=namespace)
    assert result["status"] == "unavailable"
    assert [event[0] for event in seen] == ["owner", "open", "execute", "stop"]
    assert namespace not in result["observations"][0]["runtime"]
