"""Behavioral boundaries for advisory feedback, without provider calls."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "private_dot_config/dotfiles-ai/continuous_validation/feedback.py"
spec = importlib.util.spec_from_file_location("shadow_feedback", SOURCE)
feedback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feedback)


@pytest.fixture
def data(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    enrollment = {
        "schema_version": 1,
        "enabled": True,
        "mode": "shadow",
        "worktree": str(worktree),
        "session_id": "12345678-1234-1234-1234-123456789abc",
        "cycle_id": "CVS-fixture",
        "feedback_enabled": True,
        "feedback_qualification": {
            "transport": "codex-queue", "codex_version": "0.163.0", "qualified": True
        },
    }
    observation = {
        "schema_version": 1, "id": "observation-one", "check_id": "unit",
        "snapshot_id": "a" * 64, "status": "failed",
        "test_ids": ["tests/test_unit.py::test_behavior"],
        "diagnostic_codes": ["assertion_failed"],
        "raw_output": "UNTRUSTED_RAW_OUTPUT_MUST_NOT_ENTER_CONTEXT",
    }
    return enrollment, observation, tmp_path / "state"


def runtime(monkeypatch, *, state="active", version="0.163.0", queue_code=0):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[:2] == ["dbsctrctl", "status"]:
            return subprocess.CompletedProcess(argv, 0, f"CVS-fixture {state} elevated local execution=native_workspace attribution=unavailable\n", "")
        if argv[:2] == ["codex", "--version"]:
            return subprocess.CompletedProcess(argv, 0, f"codex-cli {version}\n", "")
        assert argv[:2] == ["codex", "queue"]
        return subprocess.CompletedProcess(argv, queue_code, "accepted", "private native detail")

    monkeypatch.setattr(feedback, "run_command", run, raising=False)
    return calls


def invoke(data, **changes):
    enrollment, observation, state_dir = data
    options = {"eligible": changes["eligible"]} if "eligible" in changes else {}
    return feedback.deliver(enrollment, observation, current_snapshot_id=changes.get("current", "a" * 64), state_dir=state_dir, **options)


def private_log(data):
    folder = data[2] / "logs"
    folder.mkdir(parents=True, mode=0o700)
    path = folder / (data[1]["id"] + ".log")
    path.write_text("PRIVATE_LOG_CONTENT_MUST_STAY_LOCAL")
    path.chmod(0o600)
    data[1]["log_path"] = str(path)
    return path


def test_disabled_feedback_has_no_process_or_storage_effects(data, monkeypatch):
    data[0]["enabled"] = False
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "disabled"
    assert calls == []
    assert not data[2].exists()


def test_stale_failure_never_reaches_session(data, monkeypatch):
    calls = runtime(monkeypatch)
    assert invoke(data, current="b" * 64)["status"] == "stale"
    assert calls == []


def test_unqualified_transport_does_not_send(data, monkeypatch):
    data[0]["feedback_qualification"]["qualified"] = False
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "unavailable"
    assert not any(call[0][:2] == ["codex", "queue"] for call in calls)


def test_closed_cycle_never_wakes(data, monkeypatch):
    calls = runtime(monkeypatch, state="completed")
    assert invoke(data)["status"] == "closed"
    assert not any(call[0][:2] == ["codex", "queue"] for call in calls)


def test_exact_target_bounded_context_and_no_model_override(data, monkeypatch):
    calls = runtime(monkeypatch)
    result = invoke(data)
    assert result["status"] == "accepted"
    assert result["consumed"] is False
    queue = [argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]
    assert len(queue) == 1
    assert queue[0][queue[0].index("--thread") + 1] == data[0]["session_id"]
    message = queue[0][queue[0].index("--message") + 1]
    assert "UNTRUSTED_RAW_OUTPUT" not in message
    assert "CVS-fixture" in message and "a" * 64 in message
    assert "--model" not in queue[0] and "resume" not in queue[0]
    assert len(message) < 3500


def test_duplicate_observation_is_not_delivered_twice(data, monkeypatch):
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    assert invoke(data)["status"] == "duplicate"
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 1


def test_version_drift_invalidates_qualification(data, monkeypatch):
    calls = runtime(monkeypatch, version="0.164.0")
    assert invoke(data)["status"] == "unavailable"
    assert not any(argv[:2] == ["codex", "queue"] for argv, _ in calls)


@pytest.mark.parametrize("session", ["latest", "named session", "../elsewhere", ""])
def test_ambiguous_session_target_is_rejected(data, monkeypatch, session):
    data[0]["session_id"] = session
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "invalid"
    assert calls == []


def test_uncertain_queue_outcome_is_not_retried(data, monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["dbsctrctl", "status"]:
            return subprocess.CompletedProcess(argv, 0, "CVS-fixture active elevated local\n", "")
        if argv[:2] == ["codex", "--version"]:
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.163.0\n", "")
        raise subprocess.TimeoutExpired(argv, 10)

    monkeypatch.setattr(feedback, "run_command", run, raising=False)
    assert invoke(data)["status"] == "unknown"
    data[1]["id"] = "observation-after-unknown-outcome"
    assert invoke(data)["status"] == "duplicate"
    assert len([argv for argv in calls if argv[:2] == ["codex", "queue"]]) == 1


def test_feedback_identifies_failure_and_validated_private_log(data, monkeypatch):
    path = private_log(data)
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    sent = next(argv for argv, _ in calls if argv[:2] == ["codex", "queue"])
    message = sent[sent.index("--message") + 1]
    assert data[1]["id"] in message
    assert data[1]["test_ids"][0] in message
    assert str(path) in message
    assert "PRIVATE_LOG_CONTENT" not in message
    assert "UNTRUSTED_RAW_OUTPUT" not in message


def test_log_locator_outside_owned_log_directory_is_omitted(data, monkeypatch):
    outside = data[2].parent / "outside-private.log"
    outside.write_text("PRIVATE_CONTENT")
    outside.chmod(0o600)
    data[1]["log_path"] = str(outside)
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    sent = next(argv for argv, _ in calls if argv[:2] == ["codex", "queue"])
    assert str(outside) not in sent[sent.index("--message") + 1]


def test_many_test_ids_cannot_make_feedback_unbounded(data, monkeypatch):
    private_log(data)
    data[1]["test_ids"] = [f"tests/test_{i}.py::test_" + "x" * 450 for i in range(40)]
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    sent = next(argv for argv, _ in calls if argv[:2] == ["codex", "queue"])
    message = sent[sent.index("--message") + 1]
    assert "tests/test_0.py::test_" in message
    assert len(message) < 3500


def test_eligibility_is_rechecked_after_journal_and_runtime_probes(data, monkeypatch):
    calls = runtime(monkeypatch)
    checked = []

    def eligible():
        records = list((data[2] / "feedback").glob("*.json"))
        assert len(records) == 1
        assert json.loads(records[0].read_text())["status"] == "attempting"
        assert any(argv[:2] == ["codex", "--version"] for argv, _ in calls)
        checked.append(True)
        return False

    assert invoke(data, eligible=eligible)["status"] == "stale"
    assert checked == [True]
    assert not any(argv[:2] == ["codex", "queue"] for argv, _ in calls)


def test_cycle_closing_during_probes_prevents_dispatch(data, monkeypatch):
    calls = []
    statuses = iter(("active", "completed"))

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["dbsctrctl", "status"]:
            return subprocess.CompletedProcess(argv, 0, f"CVS-fixture {next(statuses)} elevated local\n", "")
        if argv[:2] == ["codex", "--version"]:
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.163.0\n", "")
        pytest.fail("closed cycle was queued")

    monkeypatch.setattr(feedback, "run_command", run)
    assert invoke(data)["status"] == "closed"
    assert not any(argv[:2] == ["codex", "queue"] for argv in calls)


def test_same_failure_new_observation_is_deduplicated_with_first_evidence(data, monkeypatch):
    first_log = private_log(data)
    calls = runtime(monkeypatch)
    first = invoke(data)
    assert first["status"] == "accepted"
    data[1]["id"] = "observation-two"
    data[1]["log_path"] = str(data[2] / "logs/observation-two.log")
    second = invoke(data)
    assert second["status"] == "duplicate"
    assert second["feedback_id"] == first["feedback_id"]
    records = list((data[2] / "feedback").glob("*.json"))
    assert len(records) == 1
    evidence = json.loads(records[0].read_text())["evidence"]
    assert evidence["observation_id"] == "observation-one"
    assert evidence["log_path"] == str(first_log)
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 1


def test_changed_failure_fingerprint_can_deliver_for_same_snapshot(data, monkeypatch):
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    data[1]["id"] = "observation-two"
    data[1]["test_ids"] = ["tests/test_unit.py::test_different_failure"]
    assert invoke(data)["status"] == "accepted"
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 2


def test_known_unsent_stale_attempt_does_not_suppress_later_current_failure(data, monkeypatch):
    calls = runtime(monkeypatch)
    assert invoke(data, eligible=lambda: False)["status"] == "stale"
    data[1]["id"] = "observation-two"
    assert invoke(data, eligible=lambda: True)["status"] == "accepted"
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 1


def test_failure_fingerprint_ignores_test_and_diagnostic_order(data, monkeypatch):
    calls = runtime(monkeypatch)
    data[1]["test_ids"] += ["tests/test_other.py::test_other"]
    data[1]["diagnostic_codes"] += ["pytest_failed"]
    assert invoke(data)["status"] == "accepted"
    data[1]["id"] = "observation-two"
    data[1]["test_ids"].reverse()
    data[1]["diagnostic_codes"].reverse()
    assert invoke(data)["status"] == "duplicate"
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 1


@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_aliased_log_locator_is_not_exposed(data, monkeypatch, alias):
    path = private_log(data)
    original = path.parent / "original.log"
    original.write_text("PRIVATE_ORIGINAL")
    original.chmod(0o600)
    path.unlink()
    if alias == "symlink":
        path.symlink_to(original)
    else:
        path.hardlink_to(original)
    calls = runtime(monkeypatch)
    assert invoke(data)["status"] == "accepted"
    sent = next(argv for argv, _ in calls if argv[:2] == ["codex", "queue"])
    message = sent[sent.index("--message") + 1]
    assert str(path) not in message and "PRIVATE_ORIGINAL" not in message


def test_failed_final_probe_is_known_unsent_and_can_be_revalidated(data, monkeypatch):
    statuses = 0

    def run(argv, **kwargs):
        nonlocal statuses
        if argv[:2] == ["dbsctrctl", "status"]:
            statuses += 1
            if statuses == 2:
                raise subprocess.TimeoutExpired(argv, 10)
            return subprocess.CompletedProcess(argv, 0, "CVS-fixture active elevated local\n", "")
        if argv[:2] == ["codex", "--version"]:
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.163.0\n", "")
        pytest.fail("failed preflight dispatched a message")

    monkeypatch.setattr(feedback, "run_command", run)
    assert invoke(data)["status"] == "unavailable"
    calls = runtime(monkeypatch)
    data[1]["id"] = "observation-after-preflight-recovery"
    assert invoke(data)["status"] == "accepted"
    assert len([argv for argv, _ in calls if argv[:2] == ["codex", "queue"]]) == 1


def typed_target(data, client="codex"):
    data[0]["client"] = client
    data[0]["session_id"] = ("12345678-1234-1234-1234-123456789abc" if client == "codex"
                              else "ses_shadowFixture001")
    data[0]["feedback_qualification"] = {
        "transport": "codex-queue" if client == "codex" else "opencode-prompt",
        "client_version": "0.164.0" if client == "codex" else "2.1.2",
        "qualified": True,
    }
    return data


def native_runtime(data, monkeypatch, *, lookup="current", native_version="2.1.2",
                   queue_error=None, response_target=None, endpoint="http://127.0.0.1:43127"):
    calls = []
    registry = data[2].parent / "native-state"
    registry.mkdir(mode=0o700)
    registration = registry / "service.json"
    registration.write_text(json.dumps({"url": endpoint, "pid": 9132,
                                        "password": "PRIVATE_NATIVE_TOKEN"}))
    registration.chmod(0o600)

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[:2] == ["dbsctrctl", "status"]:
            return subprocess.CompletedProcess(argv, 0, "CVS-fixture active elevated local\n", "")
        if argv[:2] == ["codex", "--version"]:
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.164.0\n", "")
        if argv[:2] == ["codex", "queue"]:
            if queue_error:
                raise queue_error
            return subprocess.CompletedProcess(argv, 0, "accepted", "")
        if argv[:2] == ["opencode", "--version"]:
            return subprocess.CompletedProcess(argv, 0, f"opencode v{native_version}\n", "")
        if argv[:3] == ["opencode", "service", "status"]:
            return subprocess.CompletedProcess(argv, 0, endpoint + "\n", "")
        if argv[:4] == ["opencode", "debug", "paths", "state"]:
            return subprocess.CompletedProcess(argv, 0, str(registry) + "\n", "")
        assert argv[:4] == ["opencode", "api", "--server", endpoint]
        assert kwargs["env"]["OPENCODE_PASSWORD"] == "PRIVATE_NATIVE_TOKEN"
        if "/api/info" in argv or "server.info" in argv:
            return subprocess.CompletedProcess(argv, 0,
                json.dumps({"version": native_version, "pid": 9132}), "")
        if "session.get" in argv or any(item.endswith(data[0]["session_id"]) and item.startswith("/api/session/") for item in argv):
            if lookup == "missing":
                return subprocess.CompletedProcess(argv, 1, "", "SessionNotFoundError")
            result = {"id": data[0]["session_id"] if lookup != "wrong" else "ses_unrelated",
                      "time": {**({"archived": 1} if lookup == "archived" else {})},
                      "location": {"directory": "/different/native/location"}}
            return subprocess.CompletedProcess(argv, 0, json.dumps({"data": result}), "")
        assert "session.prompt" in argv
        if queue_error:
            raise queue_error
        body = json.loads(argv[argv.index("--data") + 1])
        return subprocess.CompletedProcess(argv, 0, json.dumps({"data": {
            "id": body["id"], "sessionID": response_target or data[0]["session_id"],
            "type": "user", "delivery": "queue", "payload": {"text": body["text"]}}}), "")

    monkeypatch.setattr(feedback, "run_command", run)
    return calls, registration


def sent_commands(calls):
    return [argv for argv, _ in calls if argv[:2] == ["codex", "queue"] or "session.prompt" in argv]


def test_current_codex_typed_transport_preserves_exact_native_queue(data, monkeypatch):
    typed_target(data)
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "accepted"
    assert sent_commands(calls)[0][:4] == ["codex", "queue", "--thread", data[0]["session_id"]]
    assert not any("resume" in argv or "fork" in argv for argv, _ in calls)


def test_opencode_queues_existing_target_on_owned_explicit_service(data, monkeypatch):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch)
    result = invoke(data)
    assert result["status"] == "accepted"
    assert result["consumed"] is False
    queue = sent_commands(calls)
    assert len(queue) == 1
    assert queue[0][:4] == ["opencode", "api", "--server", "http://127.0.0.1:43127"]
    assert "sessionID=" + data[0]["session_id"] in queue[0]
    body = json.loads(queue[0][queue[0].index("--data") + 1])
    assert body["delivery"] == "queue" and body["resume"] is True
    assert body["id"].startswith("msg_")
    assert set(body) == {"id", "text", "delivery", "resume"}
    assert "PRIVATE_NATIVE_TOKEN" not in json.dumps(queue)
    assert not any(argv[:2] == ["opencode", "run"] or "start" in argv or "restart" in argv
                   or "session.create" in argv for argv, _ in calls)
    assert any("session.get" in argv for argv, _ in calls)


@pytest.mark.parametrize("lookup", ["missing", "wrong", "archived"])
def test_opencode_missing_wrong_or_archived_existing_target_never_sends(data, monkeypatch, lookup):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch, lookup=lookup)
    assert invoke(data)["status"] in {"closed", "unavailable"}
    assert sent_commands(calls) == []


def test_opencode_runtime_version_drift_suppresses_delivery(data, monkeypatch):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch, native_version="2.1.3")
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []


@pytest.mark.parametrize("endpoint", ["http://example.com:80", "http://127.0.0.1:1/path", "http://user:secret@localhost:1"])
def test_opencode_unowned_or_ambiguous_endpoint_never_sends(data, monkeypatch, endpoint):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch, endpoint=endpoint)
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []


@pytest.mark.parametrize("unsafe", ["public", "alias", "hardlink"])
def test_opencode_unsafe_native_registration_never_sends(data, monkeypatch, unsafe):
    typed_target(data, "opencode")
    calls, registration = native_runtime(data, monkeypatch)
    if unsafe == "public":
        registration.chmod(0o644)
    else:
        target = registration.with_name("original.json")
        registration.rename(target)
        if unsafe == "alias":
            registration.symlink_to(target)
        else:
            registration.hardlink_to(target)
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []


def test_opencode_uncertain_send_is_never_replayed(data, monkeypatch):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch, queue_error=subprocess.TimeoutExpired(["opencode"], 10))
    assert invoke(data)["status"] == "unknown"
    data[1]["id"] = "same-failure-later-observation"
    assert invoke(data)["status"] == "duplicate"
    assert len(sent_commands(calls)) == 1


def test_opencode_wrong_returned_target_keeps_send_uncertain_and_no_replay(data, monkeypatch):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch, response_target="ses_unrelated")
    assert invoke(data)["status"] == "unknown"
    assert invoke(data)["status"] == "duplicate"
    assert len(sent_commands(calls)) == 1


@pytest.mark.parametrize("client", ["codex", "opencode"])
def test_typed_disabled_feedback_has_zero_native_or_storage_effects(data, monkeypatch, client):
    typed_target(data, client)
    data[0]["feedback_enabled"] = False
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "disabled"
    assert calls == [] and not data[2].exists()


def test_failed_only_receipt_controls_feedback_and_fingerprint(data, monkeypatch):
    typed_target(data)
    data[1]["test_ids"] = ["tests/test_pass.py::test_success", "tests/test_fail.py::test_failure"]
    import hashlib
    data[1]["runtime"] = {"test_identity": {"schema_version": 1, "kind": "pytest-junit-v1",
        "encoding": "pytest-nodeid-or-sha256-v1", "scope": "completed", "complete": True,
        "case_count": 2, "reported_count": 2, "omitted_count": 0, "opaque_count": 0,
        "outcomes": {"passed": 1, "failed": 1, "error": 0, "skipped": 0},
        "ids_digest": hashlib.sha256(json.dumps(sorted(data[1]["test_ids"]),
            sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest(),
        "failed_test_ids": ["tests/test_fail.py::test_failure"]}}
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "accepted"
    message = sent_commands(calls)[0][-1]
    assert "tests/test_fail.py::test_failure" in message
    assert "tests/test_pass.py::test_success" not in message
    data[1]["id"] = "same-failure-new-passed-case"
    data[1]["test_ids"].append("tests/test_other.py::test_other_pass")
    receipt = data[1]["runtime"]["test_identity"]
    receipt.update(case_count=3, reported_count=3,
        outcomes={"passed": 2, "failed": 1, "error": 0, "skipped": 0},
        ids_digest=hashlib.sha256(json.dumps(sorted(data[1]["test_ids"]),
            sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest())
    assert invoke(data)["status"] == "duplicate"


def test_malformed_new_identity_receipt_never_falls_back_to_all_test_ids(data, monkeypatch):
    typed_target(data)
    data[1]["runtime"] = {"test_identity": {"kind": "pytest-junit-v1", "failed_test_ids": "wrong"}}
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []


def test_boolean_identity_schema_is_not_an_integer_receipt(data):
    data[1]["test_ids"] = []
    data[1]["runtime"] = {"test_identity": {"schema_version": True, "kind": "not_applicable"}}
    with pytest.raises(ValueError):
        feedback._failure_fields(data[1])


def test_untrusted_parameter_payload_is_opaque_in_agent_input(data, monkeypatch):
    typed_target(data)
    payload = "PRIVATE_PARAMETER_PAYLOAD"
    data[1]["test_ids"] = ["tests/test_bad.py::test_case[" + payload + "]"]
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "accepted"
    message = sent_commands(calls)[0][-1]
    assert payload not in message
    assert "pytest-junit-sha256:" in message


def test_native_probe_output_is_bounded_before_capture_completes(data):
    import sys
    with pytest.raises(subprocess.SubprocessError):
        feedback._command([sys.executable, "-c", "print('x' * 100000)"], data[0]["worktree"])


def test_prior_legacy_codex_attempt_is_not_replayed_after_typed_upgrade(data, monkeypatch):
    import hashlib
    typed_target(data)
    fields = {"status": "failed", "diagnostic_codes": data[1]["diagnostic_codes"],
              "test_ids": data[1]["test_ids"]}
    identity = {"session": data[0]["session_id"], "cycle": data[0]["cycle_id"],
                "snapshot": data[1]["snapshot_id"], "check": data[1]["check_id"], "failure": fields}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = data[2] / "feedback"
    directory.mkdir(mode=0o700, parents=True)
    record = directory / (key + ".json")
    record.write_text(json.dumps({"schema_version": 1, "key": key, "status": "unknown"}))
    record.chmod(0o600)
    calls, _ = native_runtime(data, monkeypatch)
    assert invoke(data)["status"] == "duplicate"
    assert sent_commands(calls) == []


def test_late_codex_version_drift_is_known_unsent(data, monkeypatch):
    typed_target(data)
    calls, _ = native_runtime(data, monkeypatch)
    original = feedback.run_command
    versions = 0

    def run(argv, **kwargs):
        nonlocal versions
        if argv[:2] == ["codex", "--version"]:
            versions += 1
            if versions > 1:
                return subprocess.CompletedProcess(argv, 0, "codex-cli 0.165.0", "")
        return original(argv, **kwargs)

    monkeypatch.setattr(feedback, "run_command", run)
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []


def test_opencode_session_archives_after_journal_without_dispatch(data, monkeypatch):
    typed_target(data, "opencode")
    calls, _ = native_runtime(data, monkeypatch)
    original = feedback.run_command
    lookups = 0

    def run(argv, **kwargs):
        nonlocal lookups
        result = original(argv, **kwargs)
        if "session.get" in argv:
            lookups += 1
            if lookups > 1:
                value = json.loads(result.stdout)
                value["data"]["time"]["archived"] = 1
                return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
        return result

    monkeypatch.setattr(feedback, "run_command", run)
    assert invoke(data)["status"] == "unavailable"
    assert sent_commands(calls) == []
