"""Repository-owned shadow selection, ownership table and native-lane boundaries."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SOURCE = Path(__file__).parents[1] / ".github/continuous_validation.py"
ALL = ["dotfiles.syntax", "dotfiles.instructions", "dotfiles.adapter", "dotfiles.full", "dotfiles.portable"]
ADAPTER_PATHS = [".github/continuous_validation.py", "tests/test_continuous_validation_dotfiles_adapter.py",
                 "tests/test_dotfiles_validation_adapter.py"]
DAGGER = {"dagger": {"engine": "unix:///fixture.sock", "image": "fixture-pinned-image",
                     "python_version": "3.14.0", "uv_version": "0.9.2"},
          "dagger_helper_argv": ["/fixture/helper"]}


@pytest.fixture
def adapter():
    spec = importlib.util.spec_from_file_location("dotfiles_shadow_adapter", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _select(adapter, trigger, paths):
    return adapter.select({"schema_version": 1, "trigger": trigger, "changed_paths": paths, "config": {}})


def _check(adapter, identity, config=None):
    return next(check for check in adapter.describe(config)["checks"] if check["id"] == identity)


def _serve(adapter, monkeypatch, components, dependencies=()):
    """Serve a synthetic ownership table; the shipped table stays digest-bound."""
    table = {"schema_version": 1, "components": list(components), "dependencies": list(dependencies),
             "broad_check_ids": ALL}
    monkeypatch.setattr(adapter, "_ownership", lambda: table)
    return table


def _git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True).stdout.strip()


def _repository(name):
    root = name / "snapshot"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "fixture@invalid")
    _git(root, "config", "commit.gpgsign", "false")
    (root / "README").write_text("base\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / ".github").mkdir()
    (root / ".github" / "continuous_validation.py").write_text("# fixture adapter change\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "adapter change")
    return root, base


@pytest.fixture
def snapshot(tmp_path):
    """A self-contained Git snapshot whose only change is the owned adapter path."""
    return _repository(tmp_path)


def test_definitions_are_uncached_and_preserve_native_and_dagger_lanes(adapter):
    value = adapter.describe()
    checks = {check["id"]: check for check in value["checks"]}
    assert value["schema_version"] == 1
    assert all(check["cacheable"] is False for check in checks.values())
    assert checks["dotfiles.full"]["class"] == "expensive"
    assert checks["dotfiles.adapter"]["lane"]["os"] == "linux"
    assert checks["dotfiles.portable"]["backend"] == "dagger"


def test_repository_manifest_is_accepted_by_shared_runner(adapter):
    source = SOURCE.parents[1] / "private_dot_config/dotfiles-ai/continuous_validation/runner.py"
    spec = importlib.util.spec_from_file_location("shadow_manifest_contract", source)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    value = adapter.describe()
    assert runner.validate_manifest(value) == value


def test_described_lanes_follow_the_hosted_linux_matrix(adapter):
    checks = adapter.describe()["checks"]
    assert [check["id"] for check in checks] == ALL
    assert all(check["lane"]["os"] == "linux" for check in checks)
    assert {check["id"] for check in checks if check["backend"] == "native"} == {
        "dotfiles.syntax", "dotfiles.instructions", "dotfiles.adapter", "dotfiles.full"}
    assert _check(adapter, "dotfiles.portable")["lane"]["python"] == "3.14"
    assert _check(adapter, "dotfiles.portable", DAGGER)["lane"]["python"] == "3.14.0"
    assert _check(adapter, "dotfiles.instructions", DAGGER)["lane"]["python"] == "3.14"


def test_shipped_table_maps_only_the_adapter_and_its_tests(adapter):
    table = adapter._ownership()
    assert [(component["id"], component["owned_path_patterns"], component["check_ids"])
            for component in table["components"]] == [("validation-adapter", ADAPTER_PATHS, ["dotfiles.adapter"])]
    assert table["dependencies"] == [] and table["broad_check_ids"] == ALL
    check = _check(adapter, "dotfiles.adapter")
    assert check["class"] == "cheap" and check["configuration"]["test_identity"] == "pytest-junit-v1"
    assert check["configuration"]["argv"][-4:] == ["pytest", *ADAPTER_PATHS[1:], "-q"]


def test_repository_keeps_no_second_ownership_table(adapter):
    root = SOURCE.parents[1]
    shipped = {component["id"]: component["owned_path_patterns"] for component in adapter._ownership()["components"]}
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                              "--", "*.json"], capture_output=True, check=True).stdout.split(b"\0")
    tables = []
    for raw in tracked:
        path = root / raw.decode()
        if not raw or path.stat().st_size > 1024 * 1024:
            continue
        try:
            value = json.loads(path.read_bytes())
        except ValueError:
            continue
        components = value.get("components") if isinstance(value, dict) else None
        if isinstance(components, list) and any(isinstance(item, dict) and "owned_path_patterns" in item for item in components):
            tables.append((raw.decode(), {item["id"]: item["owned_path_patterns"] for item in components}))
    assert tables == [(".github/validation-ownership.json", shipped)]


@pytest.mark.parametrize("path, basis, checks", [
    (".github/continuous_validation.py", "affected", ["dotfiles.adapter"]),
    ("tests/test_dotfiles_validation_adapter.py", "affected", ["dotfiles.adapter"]),
    ("dot_agents/skills/dbsctr/SKILL.md", "broad", ALL),
    (".github/workflows/test.yml", "broad", ALL),
    (".github/actions/integration-coordinator/action.yml", "broad", ALL),
    ("uv.lock", "broad", ALL),
    ("pyproject.toml", "broad", ALL),
    ("tests/ci_shard.py", "broad", ALL),
])
def test_selection_follows_changed_paths_through_the_ownership_table(adapter, path, basis, checks):
    for trigger in ("edit", "affected"):
        value = _select(adapter, trigger, [path])
        assert (value["basis"], value["checks"], value["complete"]) == (basis, checks, False)


def test_selection_without_changed_paths_selects_nothing(adapter):
    value = _select(adapter, "affected", [])
    assert (value["basis"], value["checks"], value["complete"]) == ("affected", [], False)


def test_changes_request_cheap_checks_and_keep_full_validation_pending(adapter):
    value = _select(adapter, "edit", ["dot_agents/skills/dbsctr/SKILL.md"])
    assert {"dotfiles.syntax", "dotfiles.instructions", "dotfiles.full"} <= set(value["checks"])
    assert value["complete"] is False and value["basis"] == "broad"


def test_checkpoint_includes_native_and_portable_comparators(adapter):
    value = _select(adapter, "checkpoint", [])
    assert {"dotfiles.full", "dotfiles.portable"} <= set(value["checks"])
    assert value["complete"] is True and value["basis"] == "full"


@pytest.mark.parametrize("trigger", ["checkpoint", "manual"])
def test_checkpoint_and_manual_select_the_complete_obligation(adapter, trigger):
    value = _select(adapter, trigger, [".github/continuous_validation.py"])
    assert (value["basis"], value["checks"], value["complete"]) == ("full", ALL, True)
    assert value["reason"] == "full_validation_at_checkpoint"


def test_affected_includes_expensive_checks_and_edit_keeps_the_deferral(adapter, monkeypatch, tmp_path):
    _serve(adapter, monkeypatch, [{"id": "core", "owned_path_patterns": ["src/**"], "check_ids": ["dotfiles.full"]}])
    assert _select(adapter, "affected", ["src/module.py"])["checks"] == ["dotfiles.full"]
    monkeypatch.setattr(adapter.platform, "system", lambda: "Darwin")
    request = {"schema_version": 1, "snapshot": str(tmp_path), "base": "a" * 40, "check": _check(adapter, "dotfiles.full"),
               "log_path": str(tmp_path / "log"), "config": {}}
    deferred = adapter.execute({**request, "trigger": "edit"})
    assert (deferred["status"], deferred["diagnostic_codes"]) == ("unavailable", ["checkpoint_required"])
    monkeypatch.setattr(adapter, "_snapshot", lambda _: tmp_path)
    monkeypatch.setattr(adapter, "_changed", lambda root, base: ["src/module.py"])
    included = adapter.execute({**request, "trigger": "affected"})
    assert (included["status"], included["diagnostic_codes"]) == ("unavailable", ["native_lane_unavailable"])


def test_dependency_edges_add_consumer_checks(adapter, monkeypatch):
    _serve(adapter, monkeypatch, [
        {"id": "library", "owned_path_patterns": ["lib/**"], "check_ids": ["dotfiles.instructions"]},
        {"id": "service", "owned_path_patterns": ["svc/**"], "check_ids": ["dotfiles.full"]}],
        dependencies=[{"consumer": "service", "dependency": "library"}])
    assert _select(adapter, "affected", ["lib/core.py"])["checks"] == ["dotfiles.instructions", "dotfiles.full"]
    assert _select(adapter, "affected", ["svc/main.py"])["checks"] == ["dotfiles.full"]


@pytest.mark.parametrize("pattern, path, expected", [
    ("tests/**/*.py", "tests/a/b/c.py", True),
    ("tests/**/*.py", "tests/c.py", True),
    ("tests/*.py", "tests/a/b.py", False),
    ("tests/*.py", "tests/b.py", True),
    ("*.py", "a/b.py", False),
    ("**", "a/b/c", True),
    (".github/workflows/**", ".github/workflows/test.yml", True),
    (".github/workflows/**", ".github/workflows", True),
    (".github/continuous_validation.py", ".github/continuous_validation.py", True),
    ("docs/**/README.md", "docs/a/b/README.md", True),
])
def test_pattern_matching_follows_the_lifecycle_ci_mapping_rules(adapter, pattern, path, expected):
    assert adapter._matches(pattern, path) is expected


def test_ownership_table_change_requires_a_new_adapter_digest(adapter, monkeypatch, tmp_path):
    (tmp_path / "continuous_validation.py").write_text("# relocated adapter\n")
    table = tmp_path / "validation-ownership.json"
    table.write_bytes(SOURCE.with_name("validation-ownership.json").read_bytes() + b"\n")
    monkeypatch.setattr(adapter, "__file__", str(tmp_path / "continuous_validation.py"))
    with pytest.raises(ValueError, match="ownership_table_changed"):
        adapter._ownership()
    table.write_text(json.dumps({"schema_version": 1, "components": "none", "dependencies": [], "broad_check_ids": ALL}))
    monkeypatch.setattr(adapter, "OWNERSHIP_DIGEST", hashlib.sha256(table.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="invalid_ownership_table"):
        adapter._ownership()


@pytest.mark.parametrize("trigger", ["affected", "edit", "checkpoint"])
def test_unknown_triggers_and_paths_are_rejected(adapter, trigger):
    with pytest.raises(ValueError):
        _select(adapter, "continuous", [])
    with pytest.raises(ValueError):
        _select(adapter, trigger, ["../escape.py"])
    with pytest.raises(ValueError):
        _select(adapter, trigger, ["a.py", "a.py"])


def test_execute_refuses_a_check_outside_the_derived_selection(adapter, snapshot, tmp_path, monkeypatch):
    root, base = snapshot
    monkeypatch.setattr(adapter.platform, "system", lambda: "Darwin")

    def execute(identity, trigger="affected"):
        return adapter.execute({"schema_version": 1, "snapshot": str(root), "base": base, "trigger": trigger,
                                "check": _check(adapter, identity), "log_path": str(tmp_path / "log"), "config": {}})

    refused = execute("dotfiles.instructions")
    assert (refused["status"], refused["diagnostic_codes"]) == ("unavailable", ["selection_mismatch"])
    # A mapped change selects its own check; execution then stops at the lane rule, not at selection.
    selected = execute("dotfiles.adapter")
    assert (selected["status"], selected["diagnostic_codes"]) == ("unavailable", ["native_lane_unavailable"])
    assert execute("dotfiles.instructions", "checkpoint")["diagnostic_codes"] == ["native_lane_unavailable"]


def test_unknown_adapter_configuration_is_rejected(adapter):
    with pytest.raises(ValueError):
        adapter.describe({"shell": "unexpected"})


def test_missing_dagger_pins_are_visible_instead_of_native_fallback(adapter, tmp_path):
    check = _check(adapter, "dotfiles.portable")
    result = adapter.execute({"schema_version": 1, "snapshot": str(tmp_path), "base": "a" * 40, "trigger": "checkpoint", "check": check, "log_path": str(tmp_path / "log"), "config": {}})
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["dagger_runtime_unconfigured"]


def test_unreachable_engine_result_is_returned_once_without_a_native_substitution(adapter, snapshot, monkeypatch):
    root, base = snapshot
    calls = []
    original = adapter.subprocess.run

    def run(argv, **options):
        if argv[0] != "/fixture/helper":
            return original(argv, **options)
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(
            adapter._result("dotfiles.portable", "unavailable", "dagger_engine_unavailable")), "")

    monkeypatch.setattr(adapter.subprocess, "run", run)
    monkeypatch.setattr(adapter, "_native", lambda *args: pytest.fail("native substitution"))
    # A synthetic unmapped change selects the Dagger check alongside the native ones.
    monkeypatch.setattr(adapter, "_snapshot", lambda request: root)
    monkeypatch.setattr(adapter, "_changed", lambda root, base: ["dot_agents/skills/dbsctr/SKILL.md"])
    result = adapter.execute({"schema_version": 1, "snapshot": str(root), "base": base, "trigger": "affected",
                              "check": _check(adapter, "dotfiles.portable", DAGGER), "config": DAGGER,
                              "log_path": str(root.parent / "portable.log")})
    assert (result["status"], result["diagnostic_codes"]) == ("unavailable", ["dagger_engine_unavailable"])
    assert len(calls) == 1 and calls[0][0] == "/fixture/helper"


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
    monkeypatch.setattr(adapter.platform, "system", lambda: "Linux")
    monkeypatch.setattr(adapter, "_snapshot", lambda request: tmp_path)
    monkeypatch.setattr(adapter, "_changed", lambda root, base: ["dot_agents/skills/dbsctr/SKILL.md"])
    monkeypatch.setattr(adapter.shutil, "which", lambda name: "/prepared/" + name)
    monkeypatch.setattr(adapter, "_run", lambda *args: (-9, None))
    check = _check(adapter, "dotfiles.instructions")
    result = adapter.execute({"schema_version": 1, "snapshot": str(tmp_path), "base": "a" * 40,
                              "trigger": "edit", "check": check, "log_path": str(tmp_path.parent / "log"), "config": {}})
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["native_process_crashed"]
    assert result["exit_code"] == 137


@pytest.fixture
def checkout(tmp_path, adapter, monkeypatch):
    """A plain clean checkout whose only change from its base is the owned adapter path."""
    root, base = _repository(tmp_path)
    monkeypatch.setattr(adapter, "ROOT", root)
    return root, base


def test_plan_reports_basis_and_commands_without_executing(adapter, checkout, monkeypatch, capsys):
    root, base = checkout
    original = adapter.subprocess.run

    def run(argv, *args, **options):
        assert argv[0] != "uv", argv
        return original(argv, *args, **options)

    monkeypatch.setattr(adapter.subprocess, "run", run)
    assert adapter.main(["plan", "--base", base, "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["schema_version"] == 1 and value["base"] == base
    assert value["head"] == _git(root, "rev-parse", "HEAD")
    assert value["selection"] == {"basis": "affected", "checks": ["dotfiles.adapter"], "complete": False}
    assert [item["id"] for item in value["checks"]] == ["dotfiles.adapter"]
    assert value["checks"][0]["argv"] == _check(adapter, "dotfiles.adapter")["configuration"]["argv"]
    assert adapter.main(["plan", "--base", base]) == 0
    text = capsys.readouterr().out
    assert "basis: affected" in text and "dotfiles.adapter" in text and "uv run" in text
    assert adapter.main(["plan", "--base", base, "--trigger", "checkpoint", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["selection"] == {"basis": "full", "checks": ALL, "complete": True}


def test_run_executes_linux_native_checks_and_writes_one_result(adapter, checkout, tmp_path, monkeypatch, capsys):
    root, base = checkout
    executed = []

    def native(check, root, log_path):
        executed.append(check["id"])
        return adapter._result(check["id"], "failed", "pytest_failed", exit_code=1)

    monkeypatch.setattr(adapter, "_native", native)
    output = tmp_path / "results" / "validation.json"
    assert adapter.main(["run", "--base", base, "--output", str(output)]) == 1
    summary = json.loads(capsys.readouterr().out)
    value = json.loads(output.read_text())
    assert value["schema_version"] == 1 and (value["base"], value["head"]) == (base, _git(root, "rev-parse", "HEAD"))
    assert value["selection"] == {"basis": "affected", "checks": ["dotfiles.adapter"], "complete": False}
    assert [item["check_id"] for item in value["executed"]] == executed == ["dotfiles.adapter"]
    assert value["executed"][0]["diagnostic_codes"] == ["pytest_failed"]
    assert value["not_executed"] == []
    assert output.stat().st_mode & 0o077 == 0
    assert (summary["output"], summary["executed"], summary["not_executed"]) == (str(output), ["dotfiles.adapter"], [])


def test_run_leaves_dagger_lane_and_deferred_checks_unexecuted(adapter, checkout, tmp_path, monkeypatch):
    root, base = checkout
    (root / "README").write_text("base\nunowned change\n")
    _git(root, "commit", "-q", "-am", "unowned change")
    executed = []
    monkeypatch.setattr(adapter, "_native", lambda check, *args: executed.append(check["id"]) or adapter._result(check["id"], "passed", exit_code=0))
    monkeypatch.setattr(adapter, "ALWAYS_BROAD", ("README",))
    output = tmp_path / "validation.json"
    assert adapter.main(["run", "--base", base, "--output", str(output), "--trigger", "edit"]) == 0
    value = json.loads(output.read_text())
    assert value["selection"]["basis"] == "broad"
    assert executed == ["dotfiles.syntax", "dotfiles.instructions", "dotfiles.adapter"]
    assert value["not_executed"] == [{"id": "dotfiles.full", "reason": "checkpoint_required"},
                                     {"id": "dotfiles.portable", "reason": "dagger_lane"}]


def test_unavailable_result_exits_two(adapter, checkout, tmp_path, monkeypatch):
    _, base = checkout
    monkeypatch.setattr(adapter, "_native", lambda check, *args: adapter._result(check["id"], "unavailable", "native_lane_unavailable"))
    output = tmp_path / "validation.json"
    assert adapter.main(["run", "--base", base, "--output", str(output)]) == 2
    assert json.loads(output.read_text())["executed"][0]["diagnostic_codes"] == ["native_lane_unavailable"]


def test_plan_and_run_refuse_unsafe_checkouts_before_running_a_check(adapter, checkout, tmp_path, monkeypatch, capsys):
    root, base = checkout
    monkeypatch.setattr(adapter, "_native", lambda *args: pytest.fail("check executed"))
    foreign = _git(root, "commit-tree", _git(root, "rev-parse", "HEAD^{tree}"))
    output = tmp_path / "validation.json"
    cases = [
        (["plan", "--base", "f" * 40, "--json"], "base_unknown"),
        (["plan", "--base=--output=x", "--json"], "base_unknown"),
        (["plan", "--base", "--output=x", "--json"], "arguments_invalid"),
        (["plan", "--base", foreign, "--json"], "base_not_in_history"),
        (["run", "--base", base], "arguments_invalid"),
        (["run", "--base", base, "--output", str(root / "result.json")], "output_inside_checkout"),
        (["run", "--base", base, "--output", str(output), "--extra"], "arguments_invalid"),
    ]
    for argv, code in cases:
        assert adapter.main(argv) == 2, argv
        assert json.loads(capsys.readouterr().out) == {"schema_version": 1, "error": code}
    output.write_text("preserve existing result")
    assert adapter.main(["run", "--base", base, "--output", str(output)]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "output_exists"
    assert output.read_text() == "preserve existing result"
    (root / "README").write_text("dirty\n")
    for argv in (["plan", "--base", base, "--json"], ["run", "--base", base, "--output", str(tmp_path / "other.json")]):
        assert adapter.main(argv) == 2
        assert json.loads(capsys.readouterr().out)["error"] == "checkout_dirty"
    assert not (tmp_path / "other.json").exists()
