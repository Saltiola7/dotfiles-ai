"""Repository pytest collection supplies complete receipts to the shared runner."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dotfiles_validation_adapter", ROOT / ".github/continuous_validation.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


@pytest.fixture
def snapshot(tmp_path):
    root = tmp_path / "snapshot"
    (root / "tests").mkdir(parents=True)
    (root / "tests/test_core.py").write_text("def test_ok(): pass\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "tests"], check=True)
    return root


def test_manifest_explicitly_classifies_pytest_and_non_test_checks():
    checks = adapter.describe()["checks"]
    assert {c["id"]: c["configuration"]["test_identity"] for c in checks} == {
        "dotfiles.syntax": "not_applicable", "dotfiles.instructions": "pytest-junit-v1",
        "dotfiles.full": "pytest-junit-v1", "dotfiles.swift": "pytest-junit-v1",
        "dotfiles.portable": "pytest-junit-v1"}


def test_failed_pytest_keeps_completed_and_failed_identities_separate(snapshot, tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite><testcase classname="tests.test_core" name="test_ok"/>'
                     '<testcase classname="tests.test_core" name="test_bad"><failure/></testcase></testsuite>')
    result = adapter._with_identities(adapter._result("dotfiles.instructions", "failed", exit_code=1), junit, snapshot)
    assert result["status"] == "failed"
    assert result["test_ids"] == ["tests/test_core.py::test_bad", "tests/test_core.py::test_ok"]
    assert result["runtime"]["test_identity"]["failed_test_ids"] == ["tests/test_core.py::test_bad"]


def test_passing_result_cannot_hide_failed_junit(snapshot, tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite><testcase classname="tests.test_core" name="test_bad"><failure/></testcase></testsuite>')
    result = adapter._with_identities(adapter._result("dotfiles.instructions", "passed", exit_code=0), junit, snapshot)
    assert result["status"] == "unavailable"
    assert result["test_ids"] == []


def test_missing_junit_is_not_a_complete_passing_result(snapshot, tmp_path):
    result = adapter._with_identities(adapter._result("dotfiles.instructions", "passed", exit_code=0),
                                     tmp_path / "missing.xml", snapshot)
    assert result["status"] == "unavailable"


def test_native_pytest_command_collects_private_junit(snapshot, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(adapter, "_snapshot", lambda _: snapshot)
    monkeypatch.setattr(adapter.shutil, "which", lambda _: "/fixture/tool")
    captured = []
    def run(argv, root, log, timeout):
        captured.append(argv)
        path = Path(next(item.split("=", 1)[1] for item in argv if item.startswith("--junitxml=")))
        assert not path.is_relative_to(root)
        path.write_text('<testsuite><testcase classname="tests.test_core" name="test_ok"/></testsuite>')
        return 0, None
    monkeypatch.setattr(adapter, "_run", run)
    check = next(item for item in adapter.describe()["checks"] if item["id"] == "dotfiles.instructions")
    result = adapter.execute({"schema_version": 1, "snapshot": str(snapshot), "base": "a" * 40,
                              "trigger": "edit", "check": check, "log_path": str(tmp_path / "check.log")})
    assert result["status"] == "passed"
    assert result["runtime"]["test_identity"]["case_count"] == 1
    assert len(captured) == 1


def test_syntax_failure_retains_file_locator_in_private_log(snapshot, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(adapter, "_snapshot", lambda _: snapshot)
    monkeypatch.setattr(adapter, "_syntax", lambda _: ["broken.py"])
    path = tmp_path / "syntax.log"
    check = next(item for item in adapter.describe()["checks"] if item["id"] == "dotfiles.syntax")
    result = adapter.execute({"schema_version": 1, "snapshot": str(snapshot), "base": "a" * 40,
                              "trigger": "edit", "check": check, "log_path": str(path)})
    assert result["status"] == "failed"
    assert result["test_ids"] == []
    assert result["runtime"]["test_identity"] == {"schema_version": 1, "kind": "not_applicable"}
    assert json.loads(path.read_text())["syntax_error_paths"] == ["broken.py"]


def test_portable_junit_export_uses_per_observation_directory(snapshot, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "_snapshot", lambda _: snapshot)
    original = adapter.subprocess.run
    def run(argv, **options):
        if argv[0] != "/fixture/helper":
            return original(argv, **options)
        request = json.loads(options["input"])
        # Match the backend's actual export rule: log_path.parent / relative.
        output = Path(request["log_path"]).parent / ".ci-select/junit.xml"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('<testsuite><testcase classname="tests.test_core" name="test_ok"/></testsuite>')
        assert "--junitxml=.ci-select/junit.xml" in request["check"]["configuration"]["argv"]
        return subprocess.CompletedProcess(argv, 0, json.dumps(adapter._result("dotfiles.portable", "passed", exit_code=0,
            runtime={"platform": "linux/arm64", "python": "3.14.0"})), "")
    monkeypatch.setattr(adapter.subprocess, "run", run)
    config = {"dagger": {"engine": "unix:///fixture.sock", "image": "fixture-pinned-image",
                         "python_version": "3.14.0", "uv_version": "0.9.2"},
              "dagger_helper_argv": ["/fixture/helper"]}
    check = next(item for item in adapter.describe(config)["checks"] if item["id"] == "dotfiles.portable")
    result = adapter.execute({"schema_version": 1, "snapshot": str(snapshot), "base": "a" * 40,
        "trigger": "checkpoint", "check": check, "config": config, "log_path": str(tmp_path / "portable.log")})
    assert result["status"] == "passed"
    assert result["runtime"]["test_identity"]["case_count"] == 1
