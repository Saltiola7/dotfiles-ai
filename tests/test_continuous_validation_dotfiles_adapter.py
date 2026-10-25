"""Repository-owned shadow selection and native-platform boundaries."""

import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / ".github/continuous_validation.py"


@pytest.fixture
def adapter():
    spec = importlib.util.spec_from_file_location("dotfiles_shadow_adapter", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_definitions_are_uncached_and_preserve_native_and_dagger_lanes(adapter):
    value = adapter.describe()
    checks = {check["id"]: check for check in value["checks"]}
    assert value["schema_version"] == 1
    assert all(check["cacheable"] is False for check in checks.values())
    assert checks["dotfiles.full"]["class"] == "expensive"
    assert checks["dotfiles.swift"]["lane"]["os"] == "darwin"
    assert checks["dotfiles.portable"]["backend"] == "dagger"


def test_repository_manifest_is_accepted_by_shared_runner(adapter):
    source = SOURCE.parents[1] / "private_dot_config/dotfiles-ai/continuous_validation/runner.py"
    spec = importlib.util.spec_from_file_location("shadow_manifest_contract", source)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    value = adapter.describe()
    assert runner.validate_manifest(value) == value


def test_changes_request_cheap_checks_and_keep_full_validation_pending(adapter):
    value = adapter.select({"schema_version": 1, "trigger": "edit", "changed_paths": ["dot_agents/skills/dbsctr/SKILL.md"], "config": {}})
    assert {"dotfiles.syntax", "dotfiles.instructions", "dotfiles.full"} <= set(value["checks"])
    assert value["complete"] is False


def test_checkpoint_includes_native_and_portable_comparators(adapter):
    value = adapter.select({"schema_version": 1, "trigger": "checkpoint", "changed_paths": [], "config": {}})
    assert {"dotfiles.full", "dotfiles.swift", "dotfiles.portable"} <= set(value["checks"])
    assert value["complete"] is True


def test_unknown_adapter_configuration_is_rejected(adapter):
    with pytest.raises(ValueError):
        adapter.describe({"shell": "unexpected"})


def test_native_check_cannot_report_linux_as_macos(adapter, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.platform, "system", lambda: "Linux", raising=False)
    check = next(check for check in adapter.describe()["checks"] if check["id"] == "dotfiles.swift")
    result = adapter.execute({"schema_version": 1, "snapshot": str(tmp_path), "base": "a" * 40, "trigger": "checkpoint", "check": check, "log_path": str(tmp_path / "log"), "config": {}})
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["native_macos_required"]


def test_missing_dagger_pins_are_visible_instead_of_native_fallback(adapter, tmp_path):
    check = next(check for check in adapter.describe()["checks"] if check["id"] == "dotfiles.portable")
    result = adapter.execute({"schema_version": 1, "snapshot": str(tmp_path), "base": "a" * 40, "trigger": "checkpoint", "check": check, "log_path": str(tmp_path / "log"), "config": {}})
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["dagger_runtime_unconfigured"]


def test_rejected_hardlinked_log_does_not_truncate_existing_data(adapter, tmp_path):
    root = tmp_path / "snapshot"
    root.mkdir()
    private = tmp_path / "logs"
    private.mkdir()
    original = private / "original"
    original.write_text("preserve existing private data")
    target = private / "check.log"
    target.hardlink_to(original)
    with pytest.raises(ValueError):
        adapter._run(["unused"], root, target, 1)
    assert original.read_text() == "preserve existing private data"


def test_syntax_checks_concrete_python_and_leaves_templates_to_rendering_authority(adapter, tmp_path, monkeypatch):
    import subprocess

    (tmp_path / "concrete.py").write_text("def invalid(:\n")
    (tmp_path / "script.tmpl").write_text("#!/usr/bin/env python3\nvalue = {{ .configured_value }}\n")
    monkeypatch.setattr(adapter.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args, 0, b"concrete.py\0script.tmpl\0", b""))
    assert adapter._syntax(tmp_path) == ["concrete.py"]


def test_native_signal_preserves_crash_diagnostic_in_protocol_exit_range(adapter, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(adapter, "_snapshot", lambda request: tmp_path)
    monkeypatch.setattr(adapter.shutil, "which", lambda name: "/prepared/" + name)
    monkeypatch.setattr(adapter, "_run", lambda *args: (-9, None))
    check = next(item for item in adapter.describe()["checks"] if item["id"] == "dotfiles.instructions")
    result = adapter.execute({"schema_version":1,"snapshot":str(tmp_path),"base":"a"*40,
        "trigger":"edit","check":check,"log_path":str(tmp_path.parent / "log"),"config":{}})
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["native_process_crashed"]
    assert result["exit_code"] == 137
