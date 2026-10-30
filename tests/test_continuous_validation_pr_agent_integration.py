"""Controller-owned review selection never expands repository adapter authority."""
import json
import sys
from types import SimpleNamespace

import pytest

from test_continuous_validation import (
    configured, git, private_json, request, runner, worktree,
)


def review_descriptor():
    return {"id": "pr-agent-review", "class": "expensive", "backend": "dagger",
            "lane": {"os": "linux", "architecture": "arm64", "python": "3.14.9",
                     "tools": {"pr-agent": "0.49.0"}, "dependencies": {}},
            "timeout_seconds": 300, "cacheable": False,
            "configuration": {"strategy": "pr-agent-review-v1", "test_identity": "not_applicable"}}


def review_module(calls):
    def execute(enrollment, snapshot, log_path, cancel=None):
        calls.append((enrollment, snapshot, log_path))
        return {"schema_version": 1, "check_id": "pr-agent-review", "status": "unavailable",
                "exit_code": None, "runtime": {}, "test_ids": [],
                "diagnostic_codes": ["pr_agent_inference_not_activated"]}
    return SimpleNamespace(validate_config=lambda value: value,
                           descriptor=lambda value: review_descriptor(), execute=execute)


def install_review_double(monkeypatch, module):
    import continuous_validation
    monkeypatch.setitem(sys.modules, "continuous_validation.pr_agent_review", module)
    monkeypatch.setattr(continuous_validation, "pr_agent_review", module, raising=False)


def enable_review(path, value):
    updated = {**value, "reviews_enabled": True,
               "review_config": {"private_fixture": "must-not-enter-adapter"}}
    private_json(path, updated)
    return updated


def test_opted_in_checkpoint_runs_controller_review_without_adapter_credentials(configured, monkeypatch):
    path, value = configured
    calls = []
    install_review_double(monkeypatch, review_module(calls))
    enable_review(path, value)
    original = runner.adapter_call
    def checked(enrollment, action, payload, *args, **kwargs):
        assert "review_config" not in payload
        assert "private_fixture" not in json.dumps(payload)
        return original(enrollment, action, payload, *args, **kwargs)
    monkeypatch.setattr(runner, "adapter_call", checked)
    result = runner.run_request(request(path, "checkpoint"))
    assert len(calls) == 1
    assert [x["check_id"] for x in result["observations"]] == ["quick", "slow", "pr-agent-review"]
    assert result["observations"][-1]["status"] == "unavailable"
    assert result["advisory"] is True


def test_review_opt_in_never_selects_review_on_edits(configured, monkeypatch):
    path, value = configured
    calls = []
    install_review_double(monkeypatch, review_module(calls))
    enable_review(path, value)
    result = runner.run_request(request(path, "edit"))
    assert not calls
    assert [x["check_id"] for x in result["observations"]] == ["quick"]
    assert "pr-agent-review" not in result["pending_checks"]


def test_unenrolled_review_does_not_load_optional_module(configured, monkeypatch):
    path, _ = configured
    monkeypatch.setitem(sys.modules, "continuous_validation.pr_agent_review", None)
    result = runner.run_request(request(path, "checkpoint"))
    assert [x["check_id"] for x in result["observations"]] == ["quick", "slow"]


def test_repository_manifest_cannot_claim_reserved_review_check():
    descriptor = review_descriptor()
    descriptor["id"] = "pr-agent-review"
    with pytest.raises(runner.ValidationError, match="reserved_review_check"):
        runner.validate_manifest({"schema_version": 1, "adapter_id": "fixture",
                                  "input_patterns": ["**"], "checks": [descriptor]})


def test_review_completion_feedback_requires_independent_opt_in(configured, monkeypatch):
    path, value = configured
    private_json(path, {**value, "reviews_enabled": False, "review_feedback_enabled": True})
    with pytest.raises(runner.ValidationError, match="invalid_review_feedback"):
        runner.load_enrollment(path)


@pytest.mark.parametrize("field", ["reviews_enabled", "review_feedback_enabled"])
def test_review_flags_reject_non_boolean_values(configured, field):
    path, value = configured
    private_json(path, {**value, field: 1})
    with pytest.raises(runner.ValidationError, match="invalid_review_flag"):
        runner.load_enrollment(path)


@pytest.mark.parametrize("notify", [False, True])
def test_successful_review_completion_is_advisory_and_independently_routed(configured, monkeypatch, notify):
    from continuous_validation import feedback, test_identity
    path, value = configured
    calls = []
    module = review_module([])
    def completed(enrollment, snapshot, log_path, cancel=None):
        return {"schema_version": 1, "check_id": "pr-agent-review", "status": "passed",
                "exit_code": 0, "runtime": {"backend": "dagger", "test_identity": test_identity.not_applicable(),
                    "advisory_review": {"schema_version": 1, "kind": "pr-agent-review", "event": "review_completed",
                        "coverage_disposition": "partial", "artifact_locator": str(log_path.with_suffix('.artifacts') / 'review.md'),
                        "artifact_sha256": "a" * 64}}, "test_ids": [], "diagnostic_codes": []}
    module.execute = completed
    install_review_double(monkeypatch, module)
    receipt = {"schema_version": 1, "transport": "codex-queue", "client_version": "0.164.0",
               "active_delivery": True, "idle_wake": True, "assertion": "operator_supplied"}
    enabled = enable_review(path, value)
    private_json(path, {**enabled, "review_feedback_enabled": notify, "feedback_enabled": True,
        "feedback_qualification_receipt": receipt,
        "feedback_qualification": {"transport": "codex-queue", "client_version": "0.164.0", "qualified": True}})
    def deliver(enrollment, observation, **kwargs):
        assert kwargs["eligible"]() is True
        calls.append(observation)
        return {"status": "accepted", "consumed": False}
    monkeypatch.setattr(feedback, "deliver", deliver)
    result = runner.run_request(request(path, "manual"))
    assert result["status"] == "passed" and result["advisory"] is True
    assert len(calls) == int(notify)
    assert result["observations"][-1]["test_ids"] == []
    assert result["observations"][-1]["runtime"]["advisory_review"]["coverage_disposition"] == "partial"


@pytest.mark.parametrize("uncertain", [False, True])
def test_review_cancellation_preserves_shared_admission_uncertainty(configured, monkeypatch, uncertain):
    path, value = configured
    module = review_module([])
    def interrupted(*args, **kwargs):
        if uncertain:
            raise runner.UncertainTermination("termination_unconfirmed")
        raise runner.Interrupted("superseded")
    module.execute = interrupted
    install_review_double(monkeypatch, module)
    enable_review(path, value)
    result = runner.run_request(request(path, "checkpoint"))
    review = result["observations"][-1]
    assert review["status"] == ("unavailable" if uncertain else "interrupted")
    assert review["diagnostic_codes"] == ["termination_unconfirmed" if uncertain else "superseded"]
    entries = runner.read_private(runner.budget_root() / "index.json")["entries"]
    assert [entry["state"] for entry in entries] == (["unknown"] if uncertain else [])
