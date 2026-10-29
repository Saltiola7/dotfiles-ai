"""Explicit enrollment and one-shot checkpoint drain integration."""

import hashlib
import json
from pathlib import Path

import pytest

from test_continuous_validation import ADAPTER, configured, private_json, request, worktree
from continuous_validation import runner


def arguments(path, value):
    return ["enroll", "--enable-shadow", "--worktree", value["worktree"],
            "--adapter", value["adapter"], "--session-id", value["session_id"],
            "--cycle-id", value["cycle_id"], "--base", value["base"],
            "--state-dir", value["state_dir"], "--enrollment", str(path)]


def test_ordinary_enrollment_does_not_register_checkpoint_binding(configured, monkeypatch):
    from continuous_validation import checkpoints
    path, value = configured
    monkeypatch.setattr(checkpoints, "register", lambda *args: pytest.fail("checkpoint activation was not requested"))
    assert runner.main(arguments(path, value)) == 0
    assert runner.load_enrollment(path)["checkpoints_enabled"] is False


def test_explicit_enrollment_registers_exact_binding_and_client(configured, monkeypatch):
    from continuous_validation import checkpoints
    path, value = configured
    calls = []
    monkeypatch.setattr(checkpoints, "register", lambda *args: calls.append(args))
    assert runner.main([*arguments(path, value), "--checkpoints"]) == 0
    assert calls[0][0] == path
    assert calls[0][1]["checkpoints_enabled"] is True
    assert calls[0][1]["client"] == "codex"


def test_opencode_target_has_own_format_and_transport(configured, tmp_path):
    path, value = configured
    value = {**value, "session_id": "ses_fixture001"}
    qualification = private_json(tmp_path / "qualification.json", {
        "schema_version": 1, "transport": "opencode-prompt", "client_version": "2.1.2",
        "active_delivery": True, "idle_wake": True})
    assert runner.main([*arguments(path, value), "--client", "opencode",
                        "--feedback-qualification", str(qualification)]) == 0
    enabled = runner.load_enrollment(path)
    assert enabled["client"] == "opencode"
    assert enabled["feedback_enabled"] is True
    with pytest.raises(runner.ValidationError, match="invalid_session"):
        runner.validate_enrollment({**enabled, "client": "codex"})
    with pytest.raises(runner.ValidationError, match="invalid_feedback_qualification"):
        runner.validate_enrollment({**enabled, "feedback_qualification": {
            "transport": "codex-queue", "client_version": "0.164.0", "qualified": True}})


def test_one_shot_worker_is_disabled_without_checkpoint_opt_in(configured, monkeypatch, capsys):
    from continuous_validation import checkpoints
    path, value = configured
    monkeypatch.setattr(checkpoints, "drain_one", lambda *args: pytest.fail("no checkpoint opt-in"))
    assert runner.main(["worker", "--enrollment", str(path), "--once"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"


def test_one_shot_worker_uses_same_request_owner(configured, monkeypatch, capsys):
    from continuous_validation import checkpoints
    path, value = configured
    private_json(path, {**value, "checkpoints_enabled": True})
    calls = []
    def drain(enrollment, request_owner):
        calls.append((enrollment, request_owner))
        return {"schema_version": 1, "status": "pending", "checkpoint_event": "fixture-event"}
    monkeypatch.setattr(checkpoints, "drain_one", drain)
    assert runner.main(["worker", "--enrollment", str(path), "--once"]) == 2
    assert calls == [(path, runner.run_request)]
    assert json.loads(capsys.readouterr().out)["checkpoint_event"] == "fixture-event"


def test_watcher_drains_checkpoint_before_edit_request(configured, monkeypatch):
    from continuous_validation import checkpoints
    path, value = configured
    private_json(path, {**value, "checkpoints_enabled": True})
    monkeypatch.setattr(checkpoints, "drain_one", lambda *args: {"status": "passed", "checkpoint_event": "first"})
    monkeypatch.setattr(runner, "run_request", lambda *args: pytest.fail("checkpoint must take precedence"))
    assert runner.watch(path, once=True)["checkpoint_event"] == "first"


@pytest.mark.parametrize("change", ["missing_receipt", "malformed_receipt", "wrong_manifest"])
def test_native_cache_cannot_bypass_new_identity_contract(configured, change):
    path, value = configured
    source = ADAPTER.replace("'cacheable':False,'configuration':{}",
        "'cacheable':True,'configuration':{'hermetic':True,'test_identity':'not_applicable'}")
    source = source.replace("'test_ids':['fixture::case']", "'test_ids':[]")
    source = source.replace("'runtime':{'python':platform.python_version()}",
        "'runtime':{'python':platform.python_version(),'test_identity':{'schema_version':1,'kind':'not_applicable'}}")
    adapter = Path(value["worktree"]) / value["adapter"]
    adapter.write_text(source)
    private_json(path, {**value, "adapter_digest": hashlib.sha256(source.encode()).hexdigest()})
    first = runner.run_request(request(path))["observations"][0]
    assert first["status"] == "passed"
    cache = Path(value["state_dir"]) / "cache" / (first["cache_key"] + ".json")
    cached = runner.read_private(cache)
    if change == "missing_receipt":
        cached["runtime"].pop("test_identity")
    elif change == "malformed_receipt":
        cached["runtime"]["test_identity"]["schema_version"] = True
    else:
        cached["manifest_digest"] = "0" * 64
    private_json(cache, cached)
    second = runner.run_request(request(path))["observations"][0]
    assert second["status"] == "unavailable"
    assert second["cache_reused"] is False
