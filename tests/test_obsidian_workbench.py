"""Behavioral checks for the optional, private Obsidian projection adapter.

All note data and executables in these tests are synthetic. No running Obsidian,
Prefect server, DuckDB installation, or real vault is required.
"""

import importlib.util
import json
import os
import plistlib
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "dot_local/share/pm-kernel/obsidian_workbench.py"


def load_adapter():
    name = "obsidian_workbench_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, ADAPTER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def adapter():
    return load_adapter()


FAKE_EXPORTER = '''"""Synthetic exporter: deliberately contains no database dependency."""
import json
from pathlib import Path

TABLES = ["issues"]

def validate_vault(vault_root):
    files = sorted(Path(vault_root).glob("Records/**/*.md"))
    return ["invalid source"] if any(b"INVALID_PRIVATE_NOTE" in p.read_bytes() for p in files) else []

def export_projection(vault_root, output_root):
    vault_root, output_root = Path(vault_root), Path(output_root)
    records = {str(p.relative_to(vault_root)): p.read_text() for root in ("Records", "Knowledge")
               for p in sorted((vault_root / root).rglob("*.md"))}
    if any("INVALID_PRIVATE_NOTE" in body for body in records.values()):
        raise ValueError("INVALID_PRIVATE_NOTE: private filename and SQL must not escape")
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "knowledge.duckdb").write_text(json.dumps(records, sort_keys=True))
    for kind, extension in (("parquet", "parquet"), ("json", "json")):
        target = vault_root / "Data" / kind
        target.mkdir(parents=True, exist_ok=True)
        (target / ("issues." + extension)).write_text(json.dumps(records, sort_keys=True))
    return {"issues": len(records)}
'''


@pytest.fixture
def setup(adapter, tmp_path):
    lab = tmp_path / "lab"
    vault = lab / "sample-vault"
    (vault / "Records").mkdir(parents=True)
    (vault / "Knowledge").mkdir()
    (lab / "workbench.py").write_text(FAKE_EXPORTER)
    note = vault / "Records/issue.md"
    note.write_text("---\nrecord_type: issue\nid: synthetic-1\n---\nState A\n")
    values = {
        "lab_root": str(lab),
        "vault_path": str(vault),
        "state_root": str(tmp_path / "private-state"),
        "python": str(Path(sys.executable).resolve()),
        "obsidian_cli": "/bin/echo",
        "vault_name": "sample-vault",
        "api_url": "http://127.0.0.1:4299/api",
        "reports": {"Views/SQL examples.md": 4, "Views/SQL and Bases.md": 2},
    }
    for report in values["reports"]:
        path = vault / report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic SQL report\n")
    config = adapter.Config.from_dict(values)
    return config, values, note


def occurrence():
    return uuid.uuid4().hex


def current_manifest(config):
    return json.loads((config.lab_root / "data/current/manifest.json").read_text())


def current_database(config):
    return (config.lab_root / "data/current/knowledge.duckdb").read_bytes()


def test_capture_is_stable_and_excludes_derived_or_unrelated_notes(adapter, setup):
    config, _, _ = setup
    first = adapter.capture(config)
    assert first.files.keys() == {"Records/issue.md"}
    assert all(isinstance(value, bytes) for value in first.files.values())
    for relative in (
        "Data/json/issues.json", "Views/SQL examples.md", ".obsidian/workspace.json",
        ".trash/removed.md", "Templates/Issue.md", "unrelated.md",
    ):
        target = config.vault_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Generated output changed\n")
    assert adapter.capture(config).digest == first.digest


def test_capture_detects_content_atomic_save_rename_and_deletion(adapter, setup):
    config, _, note = setup
    first = adapter.capture(config)
    replacement = note.with_suffix(".tmp")
    replacement.write_bytes(note.read_bytes().replace(b"State A", b"State B"))
    replacement.replace(note)
    second = adapter.capture(config)
    assert second.digest != first.digest
    renamed = note.with_name("renamed.md")
    note.rename(renamed)
    third = adapter.capture(config)
    assert third.digest != second.digest
    assert set(third.files) == {"Records/renamed.md"}
    renamed.unlink()
    assert adapter.capture(config).digest != third.digest


def test_capture_includes_exporter_and_projection_configuration(adapter, setup):
    config, values, _ = setup
    original = adapter.capture(config).digest
    config.exporter_path.write_text(config.exporter_path.read_text() + "\n# changed exporter\n")
    changed_exporter = adapter.capture(config).digest
    assert changed_exporter != original
    alternate = adapter.Config.from_dict({**values, "reports": {"Views/Other.md": 1}})
    assert adapter.capture(alternate).digest != changed_exporter


@pytest.mark.parametrize("kind", ["file", "directory", "canonical_root"])
def test_capture_rejects_symlinks_without_reading_outside_vault(adapter, setup, tmp_path, kind):
    config, _, _ = setup
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.md").write_text("outside data")
    if kind == "file":
        (config.vault_path / "Records/link.md").symlink_to(outside / "private.md")
    elif kind == "directory":
        (config.vault_path / "Records/linked").symlink_to(outside, target_is_directory=True)
    else:
        knowledge = config.vault_path / "Knowledge"
        knowledge.rmdir()
        knowledge.symlink_to(outside, target_is_directory=True)
    with pytest.raises(adapter.SafeFailure):
        adapter.capture(config)


def test_capture_rejects_missing_canonical_root(adapter, setup):
    config, _, _ = setup
    (config.vault_path / "Knowledge").rmdir()
    with pytest.raises(adapter.SafeFailure):
        adapter.capture(config)


@pytest.mark.parametrize("changes", [
    {"api_url": "https://api.prefect.cloud/api"},
    {"api_url": "http://192.0.2.1:4299/api"},
    {"api_url": "http://user:private-token@127.0.0.1:4299/api"},
    {"lab_root": "relative/lab"},
    {"reports": {"../outside.md": 1}},
    {"reports": {"/absolute.md": 1}},
    {"reports": {"Views/report.md": 0}},
    {"poll_seconds": 0},
    {"quiet_seconds": -1},
    {"retry_seconds": 0},
])
def test_configuration_rejects_unsafe_boundaries(adapter, setup, changes):
    _, values, _ = setup
    with pytest.raises(adapter.SafeFailure):
        adapter.Config.from_dict({**values, **changes})


def test_state_cannot_overlap_canonical_notes(adapter, setup):
    config, values, _ = setup
    with pytest.raises(adapter.SafeFailure):
        adapter.Config.from_dict({**values, "state_root": str(config.vault_path / "Records/state")})


def test_generation_uses_captured_bytes_and_publication_preserves_source(adapter, setup):
    config, _, note = setup
    snapshot = adapter.capture(config)
    note.write_bytes(note.read_bytes().replace(b"State A", b"State B"))
    with pytest.raises(adapter.SafeFailure, match="superseded"):
        adapter.build_generation(config, snapshot, occurrence())
    assert not (config.lab_root / "data/current").exists()
    note.write_bytes(snapshot.files["Records/issue.md"])
    live = note.read_bytes()
    manifest = adapter.build_generation(config, snapshot, occurrence())
    assert not (config.lab_root / "data/current").exists()
    staged = Path(manifest["path"])
    assert b"State A" in (staged / "knowledge.duckdb").read_bytes()
    assert b"State B" not in (staged / "knowledge.duckdb").read_bytes()
    assert (staged / "Data/parquet/issues.parquet").is_file()
    assert (staged / "Data/json/issues.json").is_file()
    adapter.publish_generation(config, manifest)
    assert current_manifest(config)["digest"] == snapshot.digest
    assert (config.vault_path / "Data").resolve() == (staged / "Data").resolve()
    assert (config.lab_root / "data/knowledge.duckdb").resolve() == (staged / "knowledge.duckdb").resolve()
    assert note.read_bytes() == live


def test_failed_export_leaves_previous_generation_available_and_error_safe(adapter, setup):
    config, _, note = setup
    first = adapter.build_generation(config, adapter.capture(config), occurrence())
    adapter.publish_generation(config, first)
    previous = (config.lab_root / "data/current").resolve()
    previous_database = current_database(config)
    note.write_text("INVALID_PRIVATE_NOTE: synthetic secret\n")
    with pytest.raises(adapter.SafeFailure) as failure:
        adapter.build_generation(config, adapter.capture(config), occurrence())
    assert "INVALID_PRIVATE_NOTE" not in str(failure.value)
    assert str(note) not in str(failure.value)
    assert (config.lab_root / "data/current").resolve() == previous
    assert current_database(config) == previous_database


def test_incomplete_generation_cannot_replace_current(adapter, setup):
    config, _, note = setup
    first = adapter.build_generation(config, adapter.capture(config), occurrence())
    adapter.publish_generation(config, first)
    previous = (config.lab_root / "data/current").resolve()
    note.write_text("State B\n")
    second = adapter.build_generation(config, adapter.capture(config), occurrence())
    (Path(second["path"]) / "Data/parquet/issues.parquet").unlink()
    with pytest.raises(adapter.SafeFailure):
        adapter.publish_generation(config, second)
    assert (config.lab_root / "data/current").resolve() == previous


def test_process_lock_excludes_second_publisher_and_releases(adapter, tmp_path):
    lock = tmp_path / "publisher.lock"
    with adapter.process_lock(lock):
        with pytest.raises(adapter.Busy):
            with adapter.process_lock(lock):
                pytest.fail("a concurrent publisher acquired the lock")
    with adapter.process_lock(lock):
        pass


def test_closed_obsidian_retries_refresh_without_rebuilding_after_restart(adapter, setup, monkeypatch):
    config, values, _ = setup
    original_build = adapter.build_generation
    builds = []

    def counted_build(*args, **kwargs):
        builds.append(args[2])
        return original_build(*args, **kwargs)

    def closed(_config):
        raise adapter.SafeFailure("obsidian_unavailable")

    monkeypatch.setattr(adapter, "build_generation", counted_build)
    monkeypatch.setattr(adapter, "refresh", closed)
    adapter.reconcile(config)
    first = current_manifest(config)
    assert len(builds) == 1
    adapter.reconcile(config)
    assert len(builds) == 1
    assert current_manifest(config)["occurrence"] == first["occurrence"]

    restarted = load_adapter()
    refreshed = []
    monkeypatch.setattr(restarted, "refresh", lambda cfg: refreshed.append(cfg.vault_name))
    monkeypatch.setattr(restarted, "build_generation", lambda *a, **k: pytest.fail("published work rebuilt after restart"))
    status = restarted.reconcile(restarted.Config.from_dict(values))
    assert refreshed == [config.vault_name]
    assert status["state"] == "current"
    restarted.reconcile(restarted.Config.from_dict(values))
    assert refreshed == [config.vault_name]
    checkpoints = list(config.state_root.glob("*.json"))
    assert checkpoints
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in checkpoints)


def test_returning_to_old_content_creates_new_occurrence(adapter, setup, monkeypatch):
    config, _, note = setup
    monkeypatch.setattr(adapter, "refresh", lambda config: None)
    original = note.read_bytes()
    adapter.reconcile(config)
    first = current_manifest(config)
    note.write_bytes(original.replace(b"State A", b"State B"))
    adapter.reconcile(config)
    middle = current_manifest(config)
    note.write_bytes(original)
    adapter.reconcile(config)
    last = current_manifest(config)
    assert last["digest"] == first["digest"]
    assert len({first["occurrence"], middle["occurrence"], last["occurrence"]}) == 3


def test_source_changed_during_build_cannot_publish_stale_snapshot(adapter, setup, monkeypatch):
    config, _, note = setup
    stale_digest = adapter.capture(config).digest
    original_build = adapter.build_generation

    def edit_after_build(*args, **kwargs):
        manifest = original_build(*args, **kwargs)
        note.write_bytes(note.read_bytes().replace(b"State A", b"State B"))
        return manifest

    monkeypatch.setattr(adapter, "build_generation", edit_after_build)
    monkeypatch.setattr(adapter, "refresh", lambda config: None)
    adapter.reconcile(config)
    pointer = config.lab_root / "data/current"
    assert not pointer.exists() or current_manifest(config)["digest"] != stale_digest


def test_current_manifest_recovers_publication_before_checkpoint(adapter, setup, monkeypatch):
    config, _, note = setup
    refreshes = []
    monkeypatch.setattr(adapter, "refresh", lambda config: refreshes.append("refresh"))
    adapter.reconcile(config)
    assert len(refreshes) == 1
    note.write_text("State B\n")
    second = adapter.build_generation(config, adapter.capture(config), occurrence())
    adapter.publish_generation(config, second)
    monkeypatch.setattr(adapter, "build_generation", lambda *a, **k: pytest.fail("committed generation rebuilt after checkpoint interruption"))
    adapter.reconcile(config)
    assert current_manifest(config)["occurrence"] == second["occurrence"]
    assert len(refreshes) == 2


def test_invalid_edit_preserves_current_and_correction_recovers(adapter, setup, monkeypatch):
    config, _, note = setup
    monkeypatch.setattr(adapter, "refresh", lambda config: None)
    adapter.reconcile(config)
    original = current_manifest(config)
    original_database = current_database(config)
    note.write_text("INVALID_PRIVATE_NOTE\n")
    status = adapter.reconcile(config)
    assert status["state"] != "current"
    assert "INVALID_PRIVATE_NOTE" not in json.dumps(status)
    assert current_manifest(config)["occurrence"] == original["occurrence"]
    assert current_database(config) == original_database
    note.write_text("Corrected State C\n")
    assert adapter.reconcile(config)["state"] == "current"
    assert current_manifest(config)["occurrence"] != original["occurrence"]


def test_corrupt_checkpoint_is_explicit_failure(adapter, setup, monkeypatch):
    config, _, _ = setup
    monkeypatch.setattr(adapter, "refresh", lambda config: None)
    adapter.reconcile(config)
    checkpoints = list(config.state_root.glob("*.json"))
    assert checkpoints
    for path in checkpoints:
        path.write_text("{malformed-private-state")
    with pytest.raises(adapter.SafeFailure):
        adapter.reconcile(config)


@pytest.mark.parametrize("reply", [
    {"ok": False, "reports": 2},
    {"ok": True, "reports": 1},
    {"error": "wrong_vault"},
    "Refreshed 4 block(s), 1 error(s) in Views/SQL examples.md",
])
def test_refresh_rejects_resolved_false_success_without_exposing_cli_output(adapter, setup, monkeypatch, reply):
    config, _, _ = setup
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        output = "private SQL log must stay local\n=> " + json.dumps(reply) + "\n"
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    monkeypatch.setattr(adapter.subprocess, "run", run)
    with pytest.raises(adapter.SafeFailure) as failure:
        adapter.refresh(config)
    assert "private SQL" not in str(failure.value)
    assert commands[0] == ["/usr/bin/pgrep", "-x", "Obsidian"]
    expression = commands[1][-1]
    assert commands[1][0] == str(config.obsidian_cli)
    assert commands[1][1:3] == ["vault=" + config.vault_name, "eval"]
    assert json.dumps(str(config.vault_path.resolve())) in expression
    assert expression.index("getBasePath()") < expression.index("await c.callback()")
    assert "Number(m[1])===expected" in expression
    assert "Number(m[2])===0" in expression
    assert "Records/issue.md" not in expression


def test_closed_obsidian_is_checked_without_launching_cli(adapter, setup, monkeypatch):
    config, _, _ = setup
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(adapter.subprocess, "run", run)
    with pytest.raises(adapter.SafeFailure, match="obsidian_closed"):
        adapter.refresh(config)
    assert commands == [["/usr/bin/pgrep", "-x", "Obsidian"]]


def test_refresh_subprocess_error_is_sanitized(adapter, setup, monkeypatch):
    config, _, _ = setup

    def run(command, **kwargs):
        if command[0] == "/usr/bin/pgrep":
            return subprocess.CompletedProcess(command, 0)
        raise subprocess.CalledProcessError(1, command, output="PRIVATE_SQL_AND_NOTE")

    monkeypatch.setattr(adapter.subprocess, "run", run)
    with pytest.raises(adapter.SafeFailure) as failure:
        adapter.refresh(config)
    assert str(failure.value) == "obsidian_unavailable"
    assert failure.value.__suppress_context__


def test_environment_uses_private_local_prefect_and_drops_inherited_credentials(adapter, setup, monkeypatch):
    config, _, _ = setup
    inherited = {
        "PREFECT_API_URL": "https://api.prefect.cloud/api",
        "PREFECT_API_KEY": "private-api-key",
        "PREFECT_API_DATABASE_CONNECTION_URL": "postgresql://private-db",
        "PREFECT_PROFILE": "work-cloud",
        "PREFECT_HOME": "/some/other/profile",
        "PREFECT_LOGGING_LOG_PRINTS": "true",
    }
    for name, value in inherited.items():
        monkeypatch.setenv(name, value)
    environment = adapter.isolated_environment(config)
    assert environment["PREFECT_API_URL"] == config.api_url
    assert environment["PREFECT_HOME"] == str(config.state_root / "prefect")
    assert environment["PREFECT_PROFILES_PATH"].startswith(str(config.state_root))
    assert environment["PREFECT_LOGGING_LOG_PRINTS"] == "false"
    assert environment["PREFECT_RESULTS_PERSIST_BY_DEFAULT"] == "false"
    assert environment["PREFECT_SERVER_ANALYTICS_ENABLED"] == "false"
    assert environment["PREFECT_SERVER_EPHEMERAL_ENABLED"] == "false"
    assert environment["PREFECT_API_KEY"] == ""
    assert not {"PREFECT_API_DATABASE_CONNECTION_URL", "PREFECT_PROFILE"} & environment.keys()
    assert "private-api-key" not in json.dumps(environment)
    assert os.environ["PREFECT_API_KEY"] == inherited["PREFECT_API_KEY"]


def test_configuration_loads_selected_json_without_global_machine_configuration(adapter, setup, tmp_path):
    config, values, _ = setup
    selected = tmp_path / "selected-private-config.json"
    selected.write_text(json.dumps(values))
    loaded = adapter.Config.load(selected)
    assert loaded.vault_path == config.vault_path
    assert loaded.api_url == config.api_url
    selected.write_text('{"api_key":"PRIVATE_BROKEN_CONFIG",')
    with pytest.raises(adapter.SafeFailure) as failure:
        adapter.Config.load(selected)
    assert str(failure.value) == "invalid_config"
    assert "PRIVATE_BROKEN_CONFIG" not in str(failure.value)


def test_watcher_coalesces_burst_and_generated_refresh_cannot_retrigger(adapter, setup, monkeypatch):
    config, _, note = setup
    ticks = {"now": 0.0}
    runs = []

    class StopWatch(BaseException):
        pass

    def sleep(seconds):
        ticks["now"] += seconds
        if ticks["now"] in (1, 2):
            note.write_text("Burst revision " + str(ticks["now"]))
        elif ticks["now"] == 5:
            report = config.vault_path / "Views/SQL examples.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("Generated frozen query output")
        elif ticks["now"] >= 9:
            raise StopWatch

    def run_flow(selected):
        runs.append((ticks["now"], adapter.capture(selected).digest))
        return adapter.reconcile(selected)

    monkeypatch.setattr(adapter.time, "monotonic", lambda: ticks["now"])
    monkeypatch.setattr(adapter.time, "sleep", sleep)
    monkeypatch.setattr(adapter, "healthy", lambda selected: True)
    monkeypatch.setattr(adapter, "refresh", lambda selected: None)
    monkeypatch.setattr(adapter, "run_flow", run_flow)
    with pytest.raises(StopWatch):
        adapter.watch(config)
    assert len(runs) == 1
    assert runs[0][0] == 4
    assert current_manifest(config)["digest"] == runs[0][1]


def test_watcher_retries_pending_ui_without_note_edit(adapter, setup, monkeypatch):
    config, _, _ = setup
    ticks = {"now": 0.0}
    runs = []

    class StopWatch(BaseException):
        pass

    def sleep(seconds):
        ticks["now"] += seconds
        if ticks["now"] >= 19:
            raise StopWatch

    def run_flow(selected):
        runs.append(ticks["now"])
        return adapter.reconcile(selected)

    def refresh(selected):
        if len(runs) == 1:
            raise adapter.SafeFailure("obsidian_closed")

    monkeypatch.setattr(adapter.time, "monotonic", lambda: ticks["now"])
    monkeypatch.setattr(adapter.time, "sleep", sleep)
    monkeypatch.setattr(adapter, "healthy", lambda selected: True)
    monkeypatch.setattr(adapter, "refresh", refresh)
    monkeypatch.setattr(adapter, "run_flow", run_flow)
    with pytest.raises(StopWatch):
        adapter.watch(config)
    assert runs == [2, 17]
    assert adapter.read_json(config.state_root / "checkpoint.json")["state"] == "current"


def test_facade_routes_only_its_configured_paths_and_preserves_original_exporter(adapter, setup, monkeypatch):
    config, _, _ = setup
    original = config.exporter_path.read_bytes()
    adapter.install_facade(config)
    assert (config.lab_root / "workbench_source.py").read_bytes() == original
    assert config.exporter_path.name == "workbench_source.py"
    monkeypatch.syspath_prepend(str(config.lab_root))
    sys.modules.pop("workbench_source", None)
    specification = importlib.util.spec_from_file_location("facade_" + occurrence(), config.lab_root / "workbench.py")
    facade = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(facade)
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"counts": {"issues": 1}}))

    monkeypatch.setattr(facade.subprocess, "run", run)
    assert facade.export_projection(config.vault_path, config.lab_root / "data") == {"issues": 1}
    assert commands[0][-1] == "run"
    assert commands[0][commands[0].index("--config") + 1] == str(config.lab_root / ".automation/config.json")
    for vault, output in (
        (config.lab_root / "other-vault", config.lab_root / "data"),
        (config.vault_path, config.lab_root / "other-output"),
    ):
        with pytest.raises(ValueError):
            facade.export_projection(vault, output)
    assert len(commands) == 1


def test_installer_and_uninstaller_touch_only_their_two_labels(adapter, setup, tmp_path, monkeypatch):
    config, values, _ = setup
    home = tmp_path / "home"
    agents = home / "Library/LaunchAgents"
    agents.mkdir(parents=True)
    unrelated = agents / "org.example.existing.plist"
    unrelated.write_bytes(b"unrelated agent must survive")
    config_path = config.lab_root / ".automation/config.json"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps(values))
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(adapter.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(adapter.sys, "platform", "darwin")
    monkeypatch.setattr(adapter.os, "umask", lambda value: 0o077)
    monkeypatch.setattr(adapter.subprocess, "run", run)
    monkeypatch.setenv("PREFECT_API_KEY", "PRIVATE_WORK_TOKEN")
    monkeypatch.setenv("UNRELATED_SECRET", "PRIVATE_UNRELATED_TOKEN")
    adapter.install(config, config_path)
    labels = set(adapter.agent_labels(config))
    assert len(labels) == 2
    created = [path for path in agents.glob("*.plist") if path != unrelated]
    assert {path.stem for path in created} == labels
    for path in created:
        document = plistlib.loads(path.read_bytes())
        assert document["ProgramArguments"][0] == str(config.python)
        assert document["WorkingDirectory"] == str(config.state_root / "runtime")
        assert document["LimitLoadToSessionType"] == "Aqua"
        assert document["EnvironmentVariables"]["PREFECT_API_URL"] == config.api_url
        assert path.stat().st_mode & 0o777 == 0o600
        assert "PRIVATE_WORK_TOKEN" not in json.dumps(document)
        assert "PRIVATE_UNRELATED_TOKEN" not in json.dumps(document)
        if path.stem.endswith("-watcher"):
            assert document["ProgramArguments"][-3:] == ["--config", str(config_path.resolve()), "watch"]
        else:
            assert document["ProgramArguments"][-3:] == ["--config", str(config_path.resolve()), "server"]
    adapter.uninstall(config)
    assert list(agents.glob("*.plist")) == [unrelated]
    assert unrelated.read_bytes() == b"unrelated agent must survive"
    for command in commands:
        assert command[0] == "/bin/launchctl"
        if command[1] == "bootout":
            assert command[2].rsplit("/", 1)[-1] in labels
        else:
            assert command[1] == "bootstrap" and Path(command[-1]).stem in labels


def test_server_wrapper_executes_selected_python_on_loopback_with_clean_environment(adapter, setup, tmp_path, monkeypatch):
    config, values, _ = setup
    config_path = tmp_path / "service-config.json"
    config_path.write_text(json.dumps(values))
    executed = []

    class StopExec(BaseException):
        pass

    def execve(executable, command, environment):
        executed.append((executable, command, environment))
        raise StopExec

    environment = dict(os.environ)
    environment.update({"PREFECT_API_KEY": "PRIVATE_OLD_KEY", "PREFECT_API_URL": "https://api.prefect.cloud/api"})
    monkeypatch.setattr(adapter.os, "environ", environment)
    monkeypatch.setattr(adapter.os, "umask", lambda value: 0o077)
    monkeypatch.setattr(adapter.os, "execve", execve)
    monkeypatch.setattr(adapter.sys, "argv", [str(ADAPTER), "--config", str(config_path), "server"])
    with pytest.raises(StopExec):
        adapter.main()
    executable, command, isolated = executed[0]
    assert Path(executable) == config.python
    assert command[:5] == [str(config.python), "-m", "prefect", "server", "start"]
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == "4299"
    assert isolated["PREFECT_API_URL"] == config.api_url
    assert isolated["PREFECT_HOME"] == str(config.state_root / "prefect")
    assert isolated["PREFECT_API_KEY"] == ""
    assert "PRIVATE_OLD_KEY" not in json.dumps(isolated)


def test_interrupted_first_migration_recovers_before_invalid_source(adapter, setup, monkeypatch):
    config, _, note = setup
    old = config.vault_path / 'Data'
    old.mkdir(); (old / 'previous.txt').write_text('last valid')
    manifest = adapter.build_generation(config, adapter.capture(config), occurrence())
    original_link = adapter._link

    def fail_data(target, path):
        if path == old:
            raise OSError('synthetic interruption')
        return original_link(target, path)

    monkeypatch.setattr(adapter, '_link', fail_data)
    with pytest.raises(OSError):
        adapter.publish_generation(config, manifest)
    assert (old / 'previous.txt').read_text() == 'last valid'
    assert (config.lab_root / 'data/current/knowledge.duckdb').is_file()
    monkeypatch.setattr(adapter, '_link', original_link)
    note.write_text('INVALID_PRIVATE_NOTE')
    result = adapter.reconcile(config)
    assert result['state'] == 'error'
    assert old.is_symlink() and (old / 'parquet/issues.parquet').is_file()
    assert (config.lab_root / 'data/initial-recovery/Data/previous.txt').read_text() == 'last valid'


def test_completed_generations_are_bounded_and_current_is_retained(adapter, setup, monkeypatch):
    config, _, note = setup
    monkeypatch.setattr(adapter, 'refresh', lambda config: None)
    for number in range(5):
        note.write_text(f'State {number}')
        assert adapter.reconcile(config)['state'] == 'current'
    generations = list((config.lab_root / 'data/generations').iterdir())
    assert len(generations) == 2
    assert (config.lab_root / 'data/current').resolve() in generations
