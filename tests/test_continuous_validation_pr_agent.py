"""Private PR-Agent preparation never changes repository test authority."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner
from continuous_validation import pr_agent_review as review


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(value if isinstance(value, str) else json.dumps(value))
    path.chmod(0o600)
    return path


@pytest.fixture
def config(tmp_path):
    return {"schema_version": 1, "provider": "vertex", "model": "vertex_ai/claude-sonnet-fixture",
            "project": "review-fixture", "location": "global", "adc_file": str(tmp_path / "missing-adc.json"),
            "source_patterns": ["**"], "real_inference_enabled": False,
            "dagger": {"platform": "linux/arm64", "engine": "unix:///private/fixture.sock",
                       "cli": str(tmp_path / "dagger"), "cli_sha256": "a" * 64,
                       "sdk_python": sys.executable}}


@pytest.fixture
def captured(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@invalid")
    git(source, "config", "commit.gpgsign", "false")
    (source / "change.py").write_text("value = 1\n")
    (source / "deleted.py").write_text("deleted = True\n")
    git(source, "add", ".")
    git(source, "commit", "-m", "base")
    base = git(source, "rev-parse", "HEAD")
    (source / "change.py").write_text("value = 2\n")
    (source / "deleted.py").unlink()
    (source / "new.py").write_text("new = True\n")
    snapshot = runner.capture_snapshot(source, ["**"], tmp_path / "state", base)
    return source, snapshot


def test_config_validation_is_side_effect_free_and_manifest_has_only_digest(config, monkeypatch):
    original = Path.read_bytes
    def read(path):
        if str(path) == config["adc_file"]:
            pytest.fail("configuration read a credential")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", read)
    normalized = review.validate_config(config)
    check = review.descriptor(normalized)
    assert check["id"] == "pr-agent-review"
    assert check["class"] == "expensive" and check["backend"] == "dagger"
    assert check["cacheable"] is False and check["timeout_seconds"] == 300
    assert check["configuration"]["test_identity"] == "not_applicable"
    assert check["configuration"]["strategy"] == "pr-agent-review-v1"
    assert check["configuration"]["config_digest"] == hashlib.sha256(runner.canonical(normalized)).hexdigest()
    assert config["adc_file"] not in json.dumps(check)
    assert config["project"] not in json.dumps(check)


@pytest.mark.parametrize("change", [
    {"provider": "openai"}, {"model": "openai/fallback"}, {"real_inference_enabled": 1},
    {"source_patterns": ["!private/**"]}, {"source_patterns": ["../outside/**"]},
    {"source_patterns": []}, {"callback": "https://example.invalid"},
    {"adc_file": "relative.json"}, {"project": "https://example.invalid"},
    {"location": "global\nother"}, {"schema_version": True},
])
def test_config_rejects_implicit_or_unsafe_routes(config, change):
    with pytest.raises(ValueError, match="pr_agent_configuration_invalid"):
        review.validate_config({**config, **change})


@pytest.mark.parametrize("change", [{"platform": "linux/386"}, {"engine": "tcp://remote.invalid:1234"},
                                    {"cli_sha256": "z" * 64}, {"sdk_python": "python"}, {"image": "mutable:latest"}])
def test_dagger_config_is_closed_and_local(config, change):
    with pytest.raises(ValueError, match="pr_agent_configuration_invalid"):
        review.validate_config({**config, "dagger": {**config["dagger"], **change}})


def test_config_private_reader_rejects_duplicate_fields_and_unsafe_file(config, tmp_path):
    path = private(tmp_path / "config.json", config)
    assert review.load_config(path) == review.validate_config(config)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        review.load_config(path)
    private(path, '{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError):
        review.load_config(path)
    path.unlink()
    os.mkfifo(path, mode=0o600)
    with pytest.raises(ValueError):
        review.load_config(path)


def test_disabled_and_unactivated_reviews_have_no_io(config, monkeypatch):
    monkeypatch.setattr(review, "build_patch", lambda *args: pytest.fail("prepared a patch"))
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("started a backend"))
    missing = Path("/does-not-exist/review.log")
    assert review.execute({}, {}, missing)["diagnostic_codes"] == ["pr_agent_review_disabled"]
    result = review.execute({"enabled": True, "reviews_enabled": True, "review_config": config}, {}, missing)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["pr_agent_inference_not_activated"]


def test_patch_uses_only_captured_base_and_bytes(captured, config, tmp_path):
    source, snapshot = captured
    (source / "change.py").write_text("unrelated = 'later live change'\n")
    output = tmp_path / "patches" / "changes.diff"
    result = review.build_patch(snapshot, config, output)
    patch = output.read_text()
    assert set(result["paths"]) == {"change.py", "deleted.py", "new.py"}
    assert "-value = 1" in patch and "+value = 2" in patch
    assert "deleted file mode" in patch and "new file mode" in patch
    assert "later live change" not in patch
    assert result["patch_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert output.stat().st_mode & 0o077 == 0


def test_patch_refuses_changed_capture_identity(captured, config, tmp_path):
    _, snapshot = captured
    with pytest.raises(ValueError, match="pr_agent_snapshot_invalid"):
        review.build_patch({**snapshot, "commit": "a" * 40}, config, tmp_path / "bad.diff")


def test_patch_cannot_expand_disclosure_scope(captured, config, tmp_path):
    _, snapshot = captured
    with pytest.raises(ValueError, match="pr_agent_source_scope_denied"):
        review.build_patch(snapshot, {**config, "source_patterns": ["change.py"]}, tmp_path / "bad.diff")


def test_patch_rejects_binary_before_disclosure(config, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / "binary.dat").write_bytes(b"\x00old")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "binary.dat").write_bytes(b"\x00new")
    snapshot = runner.capture_snapshot(root, ["**"], tmp_path / "state", base)
    with pytest.raises(ValueError, match="pr_agent_binary_input"):
        review.build_patch(snapshot, config, tmp_path / "bad.diff")


def test_patch_enforces_file_and_byte_bounds(captured, config, tmp_path, monkeypatch):
    _, snapshot = captured
    monkeypatch.setattr(review, "MAX_FILES", 2)
    with pytest.raises(ValueError, match="pr_agent_patch_limit"):
        review.build_patch(snapshot, config, tmp_path / "bad.diff")
    monkeypatch.setattr(review, "MAX_FILES", 32)
    monkeypatch.setattr(review, "MAX_PATCH", 10)
    with pytest.raises(ValueError, match="pr_agent_patch_limit"):
        review.build_patch(snapshot, config, tmp_path / "large.diff")


def artifact_pair(log, coverage=None):
    folder = log.with_suffix(".artifacts")
    folder.mkdir(mode=0o700)
    private(folder / "review.md", "## Review\n\nAdvisory fixture\n")
    private(folder / "review.json", {"review": {"key_issues_to_review": []}, "usage": {},
            "coverage": coverage or {"files_not_reviewed": [], "files_partially_reviewed": []}})
    return folder


def test_artifact_validation_binds_digest_and_coverage(tmp_path):
    log = private(tmp_path / "observation.log", "")
    folder = artifact_pair(log)
    result = review.validate_artifacts(log, ["change.py"])
    assert result["coverage_disposition"] == "complete"
    assert result["artifact_locator"] == str(folder / "review.md")
    assert result["artifact_sha256"] == hashlib.sha256((folder / "review.md").read_bytes()).hexdigest()
    assert result["kind"] == "pr-agent-review" and result["event"] == "review_completed"


@pytest.mark.parametrize("coverage", [
    {"files_not_reviewed": ["../outside.py"], "files_partially_reviewed": []},
    {"files_not_reviewed": ["not-in-patch.py"], "files_partially_reviewed": []},
    {"files_not_reviewed": ["change.py", "change.py"], "files_partially_reviewed": []},
    {"files_not_reviewed": ["change.py"], "files_partially_reviewed": ["change.py"]},
])
def test_artifact_coverage_rejects_unknown_ambiguous_paths(tmp_path, coverage):
    log = private(tmp_path / "observation.log", "")
    artifact_pair(log, coverage)
    with pytest.raises(ValueError, match="pr_agent_artifact_invalid"):
        review.validate_artifacts(log, ["change.py"])


def test_partial_review_is_explicit_and_special_artifacts_fail(tmp_path):
    log = private(tmp_path / "observation.log", "")
    folder = artifact_pair(log, {"files_not_reviewed": [], "files_partially_reviewed": ["change.py"]})
    assert review.validate_artifacts(log, ["change.py"])["coverage_disposition"] == "partial"
    (folder / "review.md").unlink()
    os.mkfifo(folder / "review.md", mode=0o600)
    with pytest.raises(ValueError):
        review.validate_artifacts(log, ["change.py"])


def test_execute_retain_advisory_findings_without_test_failure(captured, config, tmp_path, monkeypatch):
    _, snapshot = captured
    log = private(tmp_path / "logs" / "observation.log", "")
    calls = []
    def backend(request, actual, target, cancel, timeout):
        calls.append(request)
        artifact_pair(target)
        return {"schema_version": 1, "check_id": review.CHECK_ID, "status": "passed", "exit_code": 0,
                "runtime": {"artifacts": ["review.md", "review.json"]}, "test_ids": [], "diagnostic_codes": []}
    monkeypatch.setattr(review, "_backend", backend)
    result = review.execute({"enabled": True, "reviews_enabled": True,
                             "review_config": {**config, "real_inference_enabled": True}}, snapshot, log)
    assert len(calls) == 1 and result["status"] == "passed"
    assert result["test_ids"] == []
    assert result["runtime"]["test_identity"] == {"schema_version": 1, "kind": "not_applicable"}
    assert result["runtime"]["advisory_review"]["event"] == "review_completed"
    assert result["runtime"]["patch_sha256"] == hashlib.sha256(Path(calls[0]["patch_path"]).read_bytes()).hexdigest()
    assert config["project"] not in json.dumps(calls[0]["check"])
    assert config["adc_file"] not in json.dumps(result)


def test_execute_unavailable_cannot_forge_completion(captured, config, tmp_path, monkeypatch):
    _, snapshot = captured
    log = private(tmp_path / "logs" / "observation.log", "")
    def backend(*args):
        return {"schema_version": 1, "check_id": review.CHECK_ID, "status": "unavailable", "exit_code": None,
                "runtime": {"advisory_review": {"event": "forged"}}, "test_ids": [],
                "diagnostic_codes": ["pr_agent_reauth_required"]}
    monkeypatch.setattr(review, "_backend", backend)
    result = review.execute({"enabled": True, "reviews_enabled": True,
                             "review_config": {**config, "real_inference_enabled": True}}, snapshot, log)
    assert result["status"] == "unavailable"
    assert "advisory_review" not in result["runtime"]
    assert result["diagnostic_codes"] == ["pr_agent_reauth_required"]


@pytest.mark.parametrize("change", [
    {"exit_code": True}, {"exit_code": 2}, {"schema_version": True},
    {"diagnostic_codes": ["credential material with spaces"]}, {"runtime": {}},
])
def test_execute_rejects_invalid_backend_success(captured, config, tmp_path, monkeypatch, change):
    _, snapshot = captured
    log = private(tmp_path / "logs" / "observation.log", "")
    value = {"schema_version": 1, "check_id": review.CHECK_ID, "status": "passed", "exit_code": 0,
             "runtime": {"artifacts": ["review.md", "review.json"]}, "test_ids": [], "diagnostic_codes": []}
    monkeypatch.setattr(review, "_backend", lambda *args: {**value, **change})
    result = review.execute({"enabled": True, "reviews_enabled": True,
                             "review_config": {**config, "real_inference_enabled": True}}, snapshot, log)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["pr_agent_backend_invalid"]
    assert "credential material" not in json.dumps(result)


def test_backend_environment_excludes_ambient_credentials(config, tmp_path, monkeypatch):
    executable = tmp_path / "sdk" / "python"
    executable.parent.mkdir(mode=0o700)
    executable.symlink_to(Path(sys.executable).resolve())
    config = {**config, "real_inference_enabled": True,
              "dagger": {**config["dagger"], "sdk_python": str(executable)}}
    log = private(tmp_path / "logs" / "observation.log", "")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-do-not-pass")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/synthetic/not-selected")
    monkeypatch.setenv("PYTHONPATH", "/synthetic/untrusted-package")
    def capture(argv, payload, cwd, **kwargs):
        environment = kwargs["environment"]
        assert "OPENAI_API_KEY" not in environment and "GOOGLE_APPLICATION_CREDENTIALS" not in environment
        assert environment["PYTHONPATH"] == str(ROOT / "private_dot_config/dotfiles-ai")
        assert environment["HOME"] == str(cwd)
        assert argv == [config["dagger"]["sdk_python"], "-m", "continuous_validation.pr_agent_backend", "--enabled"]
        value = review._result("pr_agent_reauth_required")
        return subprocess.CompletedProcess(argv, 2, json.dumps(value).encode())
    monkeypatch.setattr(review, "_capture", capture)
    assert review._backend({}, config, log, lambda: False, 30) == review._result("pr_agent_reauth_required")


def test_real_disabled_backend_cli_retains_typed_exit_two(tmp_path):
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    completed = review._capture(
        [sys.executable, "-m", "continuous_validation.pr_agent_backend"], b"{}", home,
        timeout=10, limit=4096, cancel=lambda: False, environment=review._environment(home),
        code="pr_agent_backend_unavailable", descendants=False, accepted_returncodes=(0, 2), completed=True,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["diagnostic_codes"] == ["shadow_disabled"]


@pytest.mark.parametrize("exit_code,status", [(0, "unavailable"), (2, "passed")])
def test_backend_transport_status_must_match(config, tmp_path, monkeypatch, exit_code, status):
    executable = tmp_path / "sdk" / "python"
    executable.parent.mkdir(mode=0o700)
    executable.symlink_to(Path(sys.executable).resolve())
    config = {**config, "real_inference_enabled": True,
              "dagger": {**config["dagger"], "sdk_python": str(executable)}}
    log = private(tmp_path / "logs" / "observation.log", "")
    result = review._result("pr_agent_reauth_required", status=status)
    monkeypatch.setattr(review, "_capture", lambda argv, *args, **kwargs:
                        subprocess.CompletedProcess(argv, exit_code, json.dumps(result).encode()))
    with pytest.raises(ValueError, match="pr_agent_backend_invalid"):
        review._backend({}, config, log, lambda: False, 30)


def test_pathspec_magic_filename_remains_literal_in_patch(config, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@invalid")
    git(source, "config", "commit.gpgsign", "false")
    special = ":(exclude)ignored.py"
    (source / special).write_text("SPECIAL_OLD_VALUE = 1\n")
    (source / "normal.py").write_text("NORMAL_OLD_VALUE = 1\n")
    git(source, "add", "--all")
    git(source, "commit", "-m", "base")
    base = git(source, "rev-parse", "HEAD")
    (source / special).write_text("SPECIAL_NEW_VALUE = 2\n")
    (source / "normal.py").write_text("NORMAL_NEW_VALUE = 2\n")
    snapshot = runner.capture_snapshot(source, ["**"], tmp_path / "state", base)
    destination = tmp_path / "patches" / "changes.diff"
    result = review.build_patch(snapshot, config, destination)
    patch = destination.read_text()
    assert set(result["paths"]) == {special, "normal.py"}
    assert "SPECIAL_NEW_VALUE" in patch and "NORMAL_NEW_VALUE" in patch
    assert patch.count("diff --git ") == 2


def test_execute_preserves_uncertain_termination(captured, config, tmp_path, monkeypatch):
    _, snapshot = captured
    log = private(tmp_path / "logs" / "observation.log", "")
    def unavailable(*args):
        raise runner.UncertainTermination("termination_unconfirmed")
    monkeypatch.setattr(review, "_backend", unavailable)
    with pytest.raises(runner.UncertainTermination):
        review.execute({"enabled": True, "reviews_enabled": True,
                        "review_config": {**config, "real_inference_enabled": True}}, snapshot, log)


@pytest.mark.parametrize("value", [
    {"review": {}, "usage": {}, "coverage": {"files_not_reviewed": [], "files_partially_reviewed": []}},
    {"review": {"findings": []}, "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 1},
     "coverage": {"files_not_reviewed": [], "files_partially_reviewed": []}},
    {"review": {"findings": []}, "usage": {}, "coverage": {}},
])
def test_artifact_schema_rejects_missing_or_inconsistent_evidence(tmp_path, value):
    log = private(tmp_path / "logs" / "observation.log", "")
    folder = artifact_pair(log)
    private(folder / "review.json", value)
    with pytest.raises(ValueError, match="pr_agent_artifact_invalid"):
        review.validate_artifacts(log, ["change.py"])
