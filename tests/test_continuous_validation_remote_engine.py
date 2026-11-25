"""Remote authority is bounded, pinned and retained until exact cleanup proof."""

import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import remote_engine, runner


def private(path, payload):
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    short = tempfile.TemporaryDirectory(prefix="cv-e-", dir=Path(tempfile.gettempdir()).resolve())
    parent = Path(short.name)
    helper = tmp_path / "installed-control"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(0o700)
    receipt = {"schema_version": 1, "kind": "cv-native-remote-engine-v1",
               "repository_id": "fixture/repository", "endpoint_id": "fixture",
               **{key: str(index) * 64 for index, key in enumerate((
                   "endpoint_digest", "owner_digest", "installation_digest",
                   "runtime_digest", "resource_profile_digest", "budget_permission_digest"), 1)},
               "budget_id": "pilot-fixture", "engine_uri": "unix://" + str(parent / "e"),
               "max_execution_seconds": 7500}
    raw = json.dumps(receipt, indent=2).encode() + b"\n"
    path = private(tmp_path / "activation.json", raw)
    carrier = {"schema_version": 1, "endpoint_id": "fixture",
               "endpoint_digest": receipt["endpoint_digest"],
               "activation_receipt": str(path), "activation_sha256": hashlib.sha256(raw).hexdigest(),
               "control_helper": str(helper), "control_helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest()}
    config = {"dagger": {"engine": receipt["engine_uri"]}, "remote_engine": carrier}
    check = {"id": "fixture.full", "backend": "dagger", "timeout_seconds": 7500,
             "configuration": {"engine": receipt["engine_uri"]}}
    execution = {"execution_id": "execution-fixture", "repository_id": "fixture/repository",
                 "request_id": "request-fixture", "snapshot_id": "a" * 64,
                 "manifest_digest": "b" * 64, "selection_digest": "c" * 64,
                 "check_digest": runner.digest(check), "check_id": check["id"]}
    yield config, receipt, check, execution, root
    short.cleanup()


def validated(prepared):
    return remote_engine.validate_config(prepared[0], repository_id="fixture/repository", worktree=prepared[4])


def test_receipt_hash_binds_raw_bytes_and_closed_configuration(prepared):
    config, receipt, check, _, _ = prepared
    remote = validated(prepared)
    assert remote.receipt == receipt
    assert remote_engine.timeout_limit(remote, check) == 7500
    config["remote_engine"]["unexpected"] = True
    with pytest.raises(runner.ValidationError):
        validated(prepared)


@pytest.mark.parametrize("problem", ["raw_hash", "repository", "uri", "helper_hash", "hardlink", "duplicate", "permissions"])
def test_invalid_authority_never_reaches_owner(prepared, problem):
    config, receipt, _, _, _ = prepared
    carrier = config["remote_engine"]
    path = Path(carrier["activation_receipt"])
    if problem == "raw_hash":
        path.write_bytes(path.read_bytes() + b" ")
    elif problem == "repository":
        receipt["repository_id"] = "other/repository"
        private(path, runner.canonical(receipt))
        carrier["activation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif problem == "uri":
        config["dagger"]["engine"] += "changed"
    elif problem == "helper_hash":
        Path(carrier["control_helper"]).write_text("#!/bin/sh\nexit 1\n")
    elif problem == "hardlink":
        path.with_suffix(".link").hardlink_to(path)
    elif problem == "permissions":
        path.chmod(0o644)
    else:
        private(path, path.read_bytes().replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'))
        carrier["activation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(runner.ValidationError):
        validated(prepared)


def test_legacy_native_and_unmatched_uri_cannot_unlock_long_timeout(prepared):
    remote = validated(prepared)
    check = prepared[2]
    assert remote_engine.timeout_limit(None, check) == 3600
    assert remote_engine.timeout_limit(remote, {**check, "backend": "native"}) == 3600
    wrong = {**check, "configuration": {"engine": "unix:///different"}}
    with pytest.raises(runner.ValidationError):
        remote_engine.timeout_limit(remote, wrong)


class FakeOwner:
    def __init__(self, remote, parent):
        self.remote = remote
        self.parent = parent
        self.calls = []
        self.connection = None
        self.bad_open = False
        self.bad_stop = False
        self.open_failed = False
        self.closed = False
        self.proofs = []
        self.started = time.monotonic()
        self.socket_identity = None

    def response(self, request, status):
        start = self.started
        budget = {"boot_id": "fixture-boot", "clock_id": "linux-monotonic-v1",
                  "original_started_monotonic": start - 30,
                  "original_work_deadline_monotonic": start + 9000,
                  "original_cleanup_deadline_monotonic": start + 9300,
                  "work_deadline_monotonic": start + request["work_seconds"],
                  "cleanup_deadline_monotonic": start + request["work_seconds"] + request["cleanup_seconds"],
                  "observed_monotonic": time.monotonic()}
        return {"schema_version": 1, "request_sha256": runner.digest(request),
                "status": status, "lease_id": request["lease_id"],
                "runtime": remote_engine.runtime_identity(self.remote), "budget": budget,
                "engine_instance": "fixture-engine", "diagnostic_codes": [],
                "terminal": ({"execution_completion": "confirmed_terminal",
                              **{key: True for key in ("unit_inactive", "container_absent", "cgroup_empty", "relay_absent", "idle_lease_absent")}}
                             if status == "terminal" else None)}

    def status(self, request, *, cancel, timeout):
        self.calls.append("status")
        return self.response(request, "ready")

    def open(self, request, *, cancel, timeout):
        self.calls.append("open")
        self.connection = socket.socket(socket.AF_UNIX)
        self.connection.bind(self.remote.socket_path)
        details = Path(self.remote.socket_path).lstat()
        self.socket_identity = details.st_dev, details.st_ino
        if self.open_failed:
            raise runner.ValidationError("remote_open_fixture")
        result = self.response(request, "active")
        if self.bad_open:
            result["request_sha256"] = "0" * 64
        return result

    def stop(self, request, *, timeout):
        self.calls.append("stop")
        if self.connection:
            self.connection.close()
            self.connection = None
            path = Path(self.remote.socket_path)
            if path.exists():
                details = path.lstat()
                if (details.st_dev, details.st_ino) == self.socket_identity:
                    path.unlink()
        result = self.response(request, "terminal")
        if self.bad_stop:
            result["terminal"]["cgroup_empty"] = False
        return result

    def alive(self):
        return self.connection is not None

    def close(self):
        self.closed = True
        return True

    def record(self, request, proof):
        self.proofs.append(copy.deepcopy(proof))
        return {"path": str(self.parent / "proof.json"), "sha256": runner.digest(proof)}


def test_one_outer_session_validates_live_authority_and_exact_cleanup(prepared, tmp_path):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                             cancel=lambda: False, remaining_seconds=7500) as session:
        assert 0 < session.work_timeout <= 7200
        assert owner.alive()
        assert "remote_engine" not in session.runtime
    assert owner.calls == ["status", "open", "stop"]
    assert owner.closed
    assert session.runtime["remote_engine"] == remote_engine.runtime_identity(remote)
    assert session.runtime["remote_execution"]["cleanup_confirmed"] is True
    assert owner.proofs[-1]["cleanup_confirmed"] is True


@pytest.mark.parametrize("failure", ["malformed", "partial", "canceled", "child"])
def test_partial_acquisition_cancellation_and_child_failure_always_stop_original_lease(prepared, tmp_path, failure):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    owner.bad_open = failure == "malformed"
    owner.open_failed = failure == "partial"
    cancel = lambda: failure == "canceled" and owner.connection is not None
    with pytest.raises(runner.ValidationError):
        with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                 cancel=cancel, remaining_seconds=7500):
            raise runner.ValidationError("child_fixture")
    assert "stop" in owner.calls
    assert owner.closed
    assert owner.proofs[-1]["cleanup_confirmed"] is True


def test_incomplete_terminal_proof_retains_uncertain_admission(prepared, tmp_path):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    owner.bad_stop = True
    with pytest.raises(runner.UncertainTermination):
        with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                 cancel=lambda: False, remaining_seconds=7500):
            pass
    assert owner.proofs[-1]["cleanup_confirmed"] is False


def test_existing_socket_is_never_adopted(prepared, tmp_path):
    remote = validated(prepared)
    existing = socket.socket(socket.AF_UNIX)
    existing.bind(remote.socket_path)
    owner = FakeOwner(remote, tmp_path)
    try:
        with pytest.raises(runner.ValidationError):
            with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                     cancel=lambda: False, remaining_seconds=7500):
                pytest.fail("existing socket admitted")
        assert owner.calls == []
        assert Path(remote.socket_path).exists()
    finally:
        existing.close()


@pytest.mark.parametrize("field", ["activation_receipt", "control_helper"])
@pytest.mark.parametrize("value", [None, 1, [], {}])
def test_non_path_carrier_values_are_bounded_refusals(prepared, field, value):
    prepared[0]["remote_engine"][field] = value
    with pytest.raises(runner.ValidationError):
        validated(prepared)


def test_malformed_active_budget_can_still_receive_exact_terminal_cleanup(prepared, tmp_path, monkeypatch):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    ordinary = owner.open
    def malformed(request, **kwargs):
        response = ordinary(request, **kwargs)
        response["budget"] = None
        return response
    monkeypatch.setattr(owner, "open", malformed)
    with pytest.raises(runner.ValidationError):
        with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                 cancel=lambda: False, remaining_seconds=7500):
            pytest.fail("malformed active response admitted")
    assert owner.proofs[-1]["cleanup_confirmed"] is True
    assert owner.calls == ["status", "open", "stop"]


def test_terminal_engine_swap_is_not_cleanup_proof(prepared, tmp_path, monkeypatch):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    ordinary = owner.stop
    def swapped(request, **kwargs):
        response = ordinary(request, **kwargs)
        response["engine_instance"] = "unrelated-engine"
        return response
    monkeypatch.setattr(owner, "stop", swapped)
    with pytest.raises(runner.UncertainTermination):
        with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                 cancel=lambda: False, remaining_seconds=7500):
            pass
    assert owner.proofs[-1]["cleanup_confirmed"] is False


def test_active_socket_replacement_cancels_and_preserves_foreign_endpoint(prepared, tmp_path):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    replacement = socket.socket(socket.AF_UNIX)
    try:
        with pytest.raises(runner.UncertainTermination):
            with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                                     cancel=lambda: False, remaining_seconds=7500) as session:
                Path(remote.socket_path).unlink()
                replacement.bind(remote.socket_path)
                replacement_id = Path(remote.socket_path).stat().st_ino
                assert session.cancel() is True
        assert Path(remote.socket_path).stat().st_ino == replacement_id
        assert owner.proofs[-1]["cleanup_confirmed"] is False
    finally:
        replacement.close()


def test_installed_helper_inside_another_git_checkout_is_refused(prepared, tmp_path):
    other = tmp_path / "other-repo"
    other.mkdir()
    runner.git(other, "init")
    helper = other / "control"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(0o700)
    carrier = prepared[0]["remote_engine"]
    carrier.update(control_helper=str(helper), control_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
    with pytest.raises(runner.ValidationError):
        validated(prepared)


def test_writable_helper_parent_is_refused(prepared, tmp_path):
    parent = tmp_path / "shared"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)
    helper = parent / "control"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(0o700)
    carrier = prepared[0]["remote_engine"]
    carrier.update(control_helper=str(helper), control_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
    with pytest.raises(runner.ValidationError):
        validated(prepared)


def test_helper_that_never_reads_input_has_a_bounded_deadline(prepared, tmp_path):
    carrier = prepared[0]["remote_engine"]
    helper = Path(carrier["control_helper"])
    helper.write_text("#!/bin/sh\nexec sleep 30\n")
    carrier["control_helper_sha256"] = hashlib.sha256(helper.read_bytes()).hexdigest()
    remote = validated(prepared)
    owner = remote_engine.OwnerControl(remote, tmp_path / "proofs")
    started = time.monotonic()
    with pytest.raises(runner.ValidationError, match="control_timeout"):
        owner.status({"padding": "x" * 60000}, cancel=lambda: False, timeout=0.2)
    assert time.monotonic() - started < 5
    assert owner.close() is True
    assert all(child.poll() is not None for child in owner.children)


def test_terminal_cleanup_remains_valid_after_original_deadline(prepared, tmp_path, monkeypatch):
    remote = validated(prepared)
    owner = FakeOwner(remote, tmp_path)
    ordinary = owner.stop
    def expired(request, **kwargs):
        response = ordinary(request, **kwargs)
        response["budget"]["observed_monotonic"] += 10000
        return response
    monkeypatch.setattr(owner, "stop", expired)
    with remote_engine.remote_engine_session(remote, prepared[2], execution=prepared[3], owner=owner,
                                             cancel=lambda: False, remaining_seconds=7500) as session:
        pass
    assert session.runtime["remote_execution"]["cleanup_confirmed"] is True


def test_confirmed_terminal_helper_is_not_signaled_again_later(prepared, tmp_path, monkeypatch):
    carrier = prepared[0]["remote_engine"]
    helper = Path(carrier["control_helper"])
    helper.write_text("#!/bin/sh\ncat >/dev/null\nprintf '{}\\n'\n")
    carrier["control_helper_sha256"] = hashlib.sha256(helper.read_bytes()).hexdigest()
    owner = remote_engine.OwnerControl(validated(prepared), tmp_path / "proofs")
    calls = []
    ordinary = owner._kill
    def counted(child):
        calls.append(child.pid)
        return ordinary(child)
    monkeypatch.setattr(owner, "_kill", counted)
    assert owner.status({}, cancel=lambda: False, timeout=2) == {}
    assert len(calls) == 1
    assert owner.close() is True
    assert len(calls) == 1


def test_unconfirmed_local_helper_remains_tracked_for_cleanup(prepared, tmp_path, monkeypatch):
    owner = remote_engine.OwnerControl(validated(prepared), tmp_path / "proofs")
    child = object()
    owner.children.append(child)
    monkeypatch.setattr(owner, "_kill", lambda _: False)
    assert owner.close() is False
    assert owner.children == [child]
