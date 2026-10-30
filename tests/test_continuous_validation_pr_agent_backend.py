"""Pinned review execution never expands credential or source disclosure implicitly."""

import asyncio
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
from types import ModuleType

import pytest


PACKAGE = Path(__file__).parents[1] / "private_dot_config/dotfiles-ai"


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.syspath_prepend(str(PACKAGE))
    return importlib.import_module("continuous_validation.pr_agent_backend")


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.syspath_prepend(str(PACKAGE))
    return importlib.import_module("continuous_validation.pr_agent_worker")


@pytest.fixture
def job(tmp_path):
    patch = tmp_path / "changes.diff"
    patch.write_text("diff --git a/example.py b/example.py\n--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-before\n+after\n")
    patch.chmod(0o600)
    adc = tmp_path / "adc.json"
    adc.write_text(json.dumps({"type": "authorized_user", "client_id": "synthetic-client", "client_secret": "synthetic-secret", "refresh_token": "synthetic-refresh", "quota_project_id": "fixture-project"}))
    adc.chmod(0o600)
    config = {"schema_version": 1, "provider": "vertex", "model": "vertex_ai/fixture-model", "project": "fixture-project", "location": "global", "adc_file": str(adc), "source_patterns": ["**"], "real_inference_enabled": True,
              "dagger": {"platform": "linux/arm64", "engine": "unix:///tmp/fixture-engine.sock", "cli": "/fixture/dagger", "cli_sha256": "a" * 64, "sdk_python": "/fixture/python"}}
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return {"schema_version": 1, "config": config, "patch_path": str(patch), "log_path": str(tmp_path / "logs" / "review.log"),
            "check": {"id": "pr-agent-review", "class": "expensive", "backend": "dagger", "cacheable": False, "timeout_seconds": 300,
                      "lane": {"os": "linux", "architecture": "arm64", "python": "3.14.9", "tools": {}, "dependencies": {}},
                      "configuration": {"strategy": "pr-agent-review-v1", "test_identity": "not_applicable", "config_digest": fingerprint}}}


def fingerprint(job):
    job["check"]["configuration"]["config_digest"] = hashlib.sha256(json.dumps(job["config"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def run(backend, job, **kwargs):
    return asyncio.run(backend.execute(job, **kwargs))


def test_default_off_is_inert(backend, job, monkeypatch):
    monkeypatch.setattr(backend, "_validated", lambda *_: pytest.fail("disabled path parsed private input"))
    assert run(backend, job)["diagnostic_codes"] == ["shadow_disabled"]


def test_inactive_real_review_does_not_read_adc_or_probe(backend, job, monkeypatch):
    job["config"]["real_inference_enabled"] = False
    job["config"]["adc_file"] = "/unavailable/private/adc.json"
    fingerprint(job)
    monkeypatch.setattr(backend, "_read_adc", lambda *_: pytest.fail("inactive review read credentials"))
    monkeypatch.setattr(backend.dagger_backend, "_configured_cli", lambda *_: pytest.fail("inactive review probed runtime"))
    assert run(backend, job, enabled=True)["diagnostic_codes"] == ["pr_agent_inference_not_activated"]


@pytest.mark.parametrize("mutate", [
    lambda j: j.update(extra=True),
    lambda j: j["config"].update(extra=True),
    lambda j: j["config"].update(provider="openai"),
    lambda j: j["config"].update(model="openai/other"),
    lambda j: j["config"]["dagger"].update(engine="tcp://remote.invalid:1234"),
    lambda j: j["check"].update(cacheable=True),
    lambda j: j["check"]["lane"].update(architecture="amd64"),
    lambda j: j["check"]["configuration"].update(config_digest="0" * 64),
])
def test_closed_typed_inputs_reject_before_runtime(backend, job, monkeypatch, mutate):
    mutate(job)
    monkeypatch.setattr(backend.dagger_backend, "_configured_cli", lambda *_: pytest.fail("invalid input probed CLI"))
    assert run(backend, job, enabled=True)["status"] == "unavailable"


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "public", "fifo", "oversized"])
def test_adc_reader_rejects_unsafe_files_without_exposing_contents(backend, job, kind):
    adc = Path(job["config"]["adc_file"])
    if kind == "symlink":
        target = adc.with_name("target.json")
        adc.rename(target)
        adc.symlink_to(target)
    elif kind == "hardlink":
        adc.with_name("alias.json").hardlink_to(adc)
    elif kind == "public":
        adc.chmod(0o644)
    elif kind == "fifo":
        adc.unlink()
        backend.os.mkfifo(adc, 0o600)
    else:
        adc.write_bytes(b"x" * (65536 + 1))
    with pytest.raises(ValueError, match="pr_agent_credentials_unavailable"):
        backend._read_adc(adc)


class FakeFile:
    def __init__(self, client, source):
        self.client, self.source = client, source

    async def size(self):
        if self.client.artifact_size is not None:
            return self.client.artifact_size
        return len(self.content().encode())

    def content(self):
        return "review\n" if self.source.endswith(".md") else json.dumps({"review": {"key_issues_to_review": []}, "usage": {}, "coverage": {"files_not_reviewed": [], "files_partially_reviewed": []}})

    async def export(self, destination):
        Path(destination).write_text(self.content())


class FakeContainer:
    def __init__(self, client):
        self.client = client
        self.command = None

    def __getattr__(self, name):
        def operation(*args, **kwargs):
            self.client.calls.append((name, args, kwargs))
            if name == "with_exec":
                self.command = args[0]
            return self
        return operation

    def file(self, source):
        return FakeFile(self.client, source)

    async def stdout(self):
        if self.command[-1:] == ["--probe"]:
            return json.dumps({"python": "3.14.9", "package_version": "0.49.0", "litellm": "1.105.1", "uid": 10001})
        return self.client.reply

    async def exit_code(self):
        return self.client.exit_code


@pytest.fixture
def sdk(backend, monkeypatch):
    client = SimpleNamespace(calls=[], engine_version="0.21.10", engine_platform="linux/arm64", exit_code=0, artifact_size=None,
                             reply=json.dumps({"schema_version": 1, "status": "passed", "diagnostic_code": None}))
    async def version(): return client.engine_version
    async def platform(): return client.engine_platform
    client.version, client.default_platform = version, platform
    client.container = lambda **kwargs: FakeContainer(client)
    def secret(name, value):
        client.calls.append(("set_secret", (name, value), {}))
        return object()
    client.set_secret = secret
    class Connection:
        def __init__(self, *_): pass
        async def __aenter__(self): return client
        async def __aexit__(self, *_): pass
    fake = SimpleNamespace(Connection=Connection, Config=lambda **kwargs: kwargs, Timeout=lambda *args, **kwargs: args,
                           Retry=lambda **kwargs: kwargs, Platform=str, ReturnType=SimpleNamespace(ANY="ANY"))
    monkeypatch.setattr(backend.dagger_backend, "_load_sdk", lambda: fake)
    monkeypatch.setattr(backend.dagger_backend, "_configured_cli", lambda *_: ("/fixture/dagger", "0.21.10"))
    return client


def test_review_mounts_only_patch_wrapper_and_explicit_secret(backend, job, sdk):
    result = run(backend, job, enabled=True)
    assert result["status"] == "passed"
    assert result["runtime"]["artifacts"] == ["review.md", "review.json"]
    assert result["runtime"]["package_version"] == "0.49.0"
    assert not any(name.startswith("host.") or name == "with_directory" for name, *_ in sdk.calls)
    assert any(name == "with_mounted_secret" and args[0] == "/run/secrets/vertex-adc.json" for name, args, _ in sdk.calls)
    for name, args, _ in sdk.calls:
        if name in {"with_new_file", "with_env_variable", "with_exec"}:
            assert "synthetic-refresh" not in str(args)
    assert "synthetic-refresh" not in json.dumps(result)
    for name in ["review.md", "review.json"]:
        assert (Path(job["log_path"]).with_suffix(".artifacts") / name).stat().st_mode & 0o777 == 0o600


def test_distinct_execution_nonce_prevents_hidden_dagger_reuse(backend, job, sdk):
    assert run(backend, job, enabled=True)["status"] == "passed"
    job["log_path"] = str(Path(job["log_path"]).with_name("second.log"))
    assert run(backend, job, enabled=True)["status"] == "passed"
    nonces = [args[1] for name, args, _ in sdk.calls if name == "with_env_variable" and args[0] == "PR_AGENT_EXECUTION_NONCE"]
    assert len(nonces) == 2 and len(set(nonces)) == 2


def test_engine_platform_or_version_drift_never_executes(backend, job, sdk):
    sdk.engine_platform = "linux/amd64"
    result = run(backend, job, enabled=True)
    assert result["diagnostic_codes"] == ["dagger_native_platform_unavailable"]
    assert not sdk.calls


def test_bounded_export_rejects_large_or_replaced_report(backend, job, sdk):
    sdk.artifact_size = 1024 * 1024 + 1
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["pr_agent_artifact_unavailable"]


def test_provider_failure_is_fixed_not_raw_error(backend, job, sdk):
    sdk.reply = json.dumps({"schema_version": 1, "status": "unavailable", "diagnostic_code": "pr_agent_reauth_required"})
    sdk.exit_code = 2
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["pr_agent_reauth_required"]


def test_qualification_is_separate_from_ordinary_execution(backend, job, sdk, monkeypatch):
    job["config"]["real_inference_enabled"] = False
    fingerprint(job)
    monkeypatch.setattr(backend, "_read_adc", lambda *_: pytest.fail("qualification read real credentials"))
    result = asyncio.run(backend.qualify(job, mode="synthetic", enabled=True))
    assert result["status"] == "passed"
    assert result["runtime"]["qualification"] == "synthetic"
    assert not any(name == "set_secret" for name, *_ in sdk.calls)


def test_worker_configuration_disables_external_sinks_and_replay(worker):
    settings = worker._overrides("vertex_ai/fixture-model", "fixture-project", "global")
    assert settings["config.model"] == "vertex_ai/fixture-model"
    assert settings["config.num_retries"] == 0
    assert settings["config.fallback_models"] == []
    assert settings["config.use_repo_settings_file"] is False
    assert settings["config.use_global_settings_file"] is False
    assert settings["config.extra_config_url"] == ""
    assert settings["config.repo_context_files"] == []
    assert settings["skills.enabled"] is False
    assert settings["artifacts.enable"] is False
    assert settings["push_outputs.enable"] is False
    assert settings["litellm.enable_callbacks"] is False
    assert settings["otel.is_enabled"] is False


@pytest.mark.parametrize("mode", ["help", "synthetic", "review"])
def test_worker_scrubs_ambient_credentials_before_provider_import(worker, monkeypatch, mode):
    environment = {"PATH": "/app/.venv/bin", "PYTHONPATH": "/app", "HOME": "/work/home",
                   "OPENAI_API_KEY": "do-not-inherit", "GITHUB_TOKEN": "do-not-inherit",
                   "GOOGLE_APPLICATION_CREDENTIALS": "/unrelated/adc.json", "PR_AGENT_EXTRA_CONFIG_URL": "https://untrusted.invalid/config"}
    monkeypatch.setattr(worker.os, "environ", environment)
    worker._environment(mode)
    assert "OPENAI_API_KEY" not in environment
    assert "GITHUB_TOKEN" not in environment
    assert "PR_AGENT_EXTRA_CONFIG_URL" not in environment
    assert environment.get("GOOGLE_APPLICATION_CREDENTIALS") == (str(worker.ADC_PATH) if mode == "review" else None)
    assert environment["LITELLM_LOCAL_MODEL_COST_MAP"] == "true"


def test_worker_native_factory_limits_attempts_and_records_sanitized_auth_failure(worker, monkeypatch):
    completion_calls, retry_limits = [], []
    class Stop:
        def __init__(self, attempts):
            self.attempts = attempts
    async def native_call(self, *args, **kwargs):
        completion_calls.append(args)
        raise ValueError("invalid_rapt: PRIVATE_REFRESH_CREDENTIAL")
    def retry_with(*, stop):
        retry_limits.append(stop.attempts)
        return native_call
    native_call.retry_with = retry_with
    class Handler:
        _chat_completion_with_retry = native_call
        async def chat_completion(self, *args, **kwargs):
            return await self._chat_completion_with_retry(*args, **kwargs)
    package = ModuleType("pr_agent.algo.ai_handlers.litellm_ai_handler")
    package.LiteLLMAIHandler = Handler
    tenacity = ModuleType("tenacity")
    tenacity.stop_after_attempt = Stop
    monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(sys.modules, "tenacity", tenacity)
    state = {"calls": 0, "failure": None}
    handler = worker._native_factory(state)
    with pytest.raises(ValueError):
        asyncio.run(handler.chat_completion("model", "system", "user"))
    with pytest.raises(ValueError, match="pr_agent_execution_failed"):
        asyncio.run(handler.chat_completion("model", "system", "user"))
    assert len(completion_calls) == 1 and retry_limits == [1]
    assert state == {"calls": 1, "failure": "pr_agent_reauth_required"}
    assert "PRIVATE" not in json.dumps(state)


@pytest.mark.parametrize("message,code", [("invalid_rapt SECRET", "pr_agent_reauth_required"), ("PERMISSION_DENIED SECRET", "pr_agent_access_denied"), ("unrelated provider exception SECRET", "pr_agent_execution_failed")])
def test_worker_main_never_returns_raw_provider_failure(worker, monkeypatch, tmp_path, capsys, message, code):
    monkeypatch.setattr(worker, "_environment", lambda *_: None)
    monkeypatch.setattr(worker.logging, "disable", lambda *_: None)
    monkeypatch.setattr(worker, "_read_inputs", lambda: ({}, "synthetic"))
    monkeypatch.setattr(worker, "OUTPUT_ROOT", tmp_path)
    async def broken(*_):
        print("PRIVATE_PROVIDER_STDOUT")
        raise ValueError(message)
    monkeypatch.setattr(worker, "_review", broken)
    assert worker.main(["--mode", "synthetic"]) == 2
    result = capsys.readouterr()
    assert result.err == ""
    assert json.loads(result.out) == {"schema_version": 1, "status": "unavailable", "diagnostic_code": code}
    assert "SECRET" not in result.out and "PRIVATE" not in result.out


def test_export_never_overwrites_or_follows_existing_report(backend, job, sdk, tmp_path):
    root = Path(job["log_path"]).with_suffix(".artifacts")
    root.mkdir(parents=True, mode=0o700)
    root.parent.chmod(0o700)
    outside = tmp_path / "outside.txt"
    outside.write_text("keep me")
    (root / "review.md").symlink_to(outside)
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["pr_agent_artifact_unavailable"]
    assert outside.read_text() == "keep me"


def test_worker_output_is_not_a_clean_review_when_structured_file_is_invalid(worker, monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "OUTPUT_ROOT", tmp_path)
    (tmp_path / "review.md").write_text("No findings")
    (tmp_path / "review.json").write_text(json.dumps({"review": {}, "usage": {}, "coverage": {}}))
    with pytest.raises(ValueError, match="pr_agent_output_invalid"):
        worker._validate_outputs()
