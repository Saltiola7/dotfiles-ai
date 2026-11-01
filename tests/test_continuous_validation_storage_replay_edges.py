"""Replay compatibility and optional telemetry cannot destroy retained results."""
from pathlib import Path

import pytest

from test_continuous_validation import configured, git, private_json, request, runner, worktree
from test_continuous_validation_storage import journal_path, refuse_execution
from test_continuous_validation_storage_capacity import seed_observations


def legacy_record(path, value, payload, result):
    patterns = ["**", value["adapter"]]
    return {"schema_version": 1, "request_digest": runner.digest(payload),
            "enrollment_digest": runner.digest(runner.read_private(path)),
            "patterns": patterns, "files": runner.inventory(Path(value["worktree"]), patterns),
            "head": git(Path(value["worktree"]), "rev-parse", "HEAD"), "result": result}


def test_legacy_exact_canonical_observation_limit_remains_readable(configured, monkeypatch):
    path, value = configured
    payload = {**request(path), "request_id": "legacy-framing-boundary"}
    first = runner.run_request(payload)
    observation = first["observations"][0]
    observation["runtime"]["padding"] = ""
    observation["runtime"]["padding"] = "x" * (runner.MAX_JSON - len(runner.canonical(observation)))
    assert len(runner.canonical(observation)) == runner.MAX_JSON
    record = private_json(journal_path(value, payload), legacy_record(path, value, payload, first))
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    assert runner.run_request(payload)["observations"] == first["observations"]
    assert record.read_bytes() == before


@pytest.mark.parametrize("field,replacement", [("request_id", "foreign-request"), ("snapshot_id", "0" * 64), ("generation", 999)])
def test_legacy_observations_cannot_claim_another_request_identity(configured, monkeypatch, field, replacement):
    path, value = configured
    payload = {**request(path), "request_id": "legacy-bound-identity"}
    first = runner.run_request(payload)
    first["observations"][0][field] = replacement
    record = private_json(journal_path(value, payload), legacy_record(path, value, payload, first))
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert result["status"] == "unavailable"
    assert result["new_execution"] is False
    assert record.read_bytes() == before


def test_unrepresentable_summary_timing_fails_closed(configured, monkeypatch):
    path, value = configured
    payload = {**request(path), "request_id": "malformed-summary-time"}
    assert runner.run_request(payload)["observations"]
    record = journal_path(value, payload)
    stored = runner.read_private(record)
    stored["result"]["elapsed_seconds"] = 10 ** 400
    private_json(record, stored)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert result["status"] == "unavailable"
    assert result["new_execution"] is False
    assert record.read_bytes() == before


def test_terminal_summary_is_source_free_and_has_bounded_diagnostic(configured, monkeypatch):
    path, value = configured
    payload = {**request(path), "request_id": "malformed-terminal"}
    runner.private_dir(Path(value["state_dir"]))
    terminal = {**runner.request_record_base(payload, runner.digest(runner.read_private(path)), "terminal"),
                "result": {"schema_version": 1, "request_id": payload["request_id"], "status": "unavailable",
                           "pending_checks": [], "advisory": True, "new_execution": False, "observations": [],
                           "snapshot_id": [], "generation": {}, "error_code": {}}}
    record = private_json(journal_path(value, payload), terminal)
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    result = runner.run_request(payload)
    assert result["status"] == "unavailable" and isinstance(result["error_code"], str)
    assert "snapshot_id" not in result and "generation" not in result
    assert record.read_bytes() == before


@pytest.mark.parametrize("feedback_overflow", [False, True])
def test_optional_event_failure_cannot_replace_durable_completion(configured, monkeypatch, feedback_overflow):
    from continuous_validation import feedback

    path, value = configured
    if feedback_overflow:
        (Path(value["worktree"]) / "source.py").write_text("fail = True\n")
    original_event = runner.event

    def event(state, event_value):
        if event_value["type"] in {"feedback_storage_unavailable", "finished"}:
            raise runner.ValidationError("event_retention_limit")
        return original_event(state, event_value)

    monkeypatch.setattr(runner, "event", event)
    monkeypatch.setattr(feedback, "deliver", lambda *_args, **_kwargs: {"status": "accepted", "padding": "x" * runner.MAX_JSON})
    payload = {**request(path), "request_id": "completion-without-optional-event"}
    first = runner.run_request(payload)
    assert first["status"] == ("failed" if feedback_overflow else "pending")
    assert len(first["observations"]) == 1
    record = journal_path(value, payload)
    assert runner.read_private(record)["kind"] == "completed"
    before = record.read_bytes()
    refuse_execution(monkeypatch)
    assert runner.run_request(payload) == {**first, "new_execution": False, "coalesced_with": payload["request_id"]}
    assert record.read_bytes() == before


def test_capacity_refusal_remains_structured_when_optional_diagnostic_fails(configured, monkeypatch):
    path, value = configured
    seed_observations(Path(value["state_dir"]), 200)

    def unavailable_event(*_args):
        raise runner.ValidationError("event_retention_limit")

    monkeypatch.setattr(runner, "event", unavailable_event)
    payload = {**request(path), "request_id": "capacity-without-event-room"}
    result = runner.run_request(payload)
    assert result["status"] == "unavailable"
    assert result["error_code"] == "observation_retention_limit"
    assert result["observations"] == []
    before = journal_path(value, payload).read_bytes()
    assert runner.run_request(payload)["error_code"] == "observation_retention_limit"
    assert journal_path(value, payload).read_bytes() == before
