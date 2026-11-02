"""Managed Prefect adapter boundaries; synthetic files and subprocesses only."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher():
    path = ROOT / "dot_local/bin/executable_prefect-mcp"
    loader = importlib.machinery.SourceFileLoader("prefect_mcp_launcher", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def layout(tmp_path, launcher):
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    paths = launcher.Layout(home)
    paths.base.mkdir(mode=0o700, parents=True)
    for parent in (home / ".config", home / ".config/dotfiles-ai", paths.base.parent):
        parent.chmod(0o700)
    for name, value in {"pyproject.toml": '[project]\nname="fixture"\n',
                        "uv.lock": "version=1\n", "server.py": "# synthetic bootstrap\n"}.items():
        (paths.base / name).write_text(value)
        (paths.base / name).chmod(0o644)
    write_config(paths)
    return paths


def write_config(paths, **overrides):
    values = dict(schema_version=1, enabled=True, profiles_path="", profile="",
                  api_url="http://127.0.0.1:4200/api", api_auth_string_env="", api_key_env="")
    values.update(overrides)
    paths.config.write_text("\n".join(key + " = " + json.dumps(value)
                                    for key, value in values.items()) + "\n")
    paths.config.chmod(0o600)


def test_named_profile_selection_ignores_active_and_ambient_target(launcher, layout):
    profiles = layout.home / "profiles.toml"
    profiles.write_text('active="cloud"\n[profiles.cloud]\nPREFECT_API_URL="https://wrong.invalid/api"\n'
                        '[profiles.local_dev]\nPREFECT_API_URL="http://localhost:4200/api"\n')
    profiles.chmod(0o644)
    write_config(layout, api_url="", profiles_path=str(profiles), profile="local_dev")
    before = profiles.read_bytes()
    url, credentials = launcher.selection(launcher.read_config(layout),
                                          {"PREFECT_API_URL": "https://wrong.invalid"}, layout.home)
    assert url == "http://localhost:4200/api" and credentials == {}
    assert profiles.read_bytes() == before


@pytest.mark.parametrize("url", ["", "ftp://localhost/api", "http://user:CANARY@localhost/api",
                                  "http://localhost/api?token=CANARY", "http://localhost/api#CANARY",
                                  "http://local\nhost/api", "http://localhost:bad/api"])
def test_invalid_targets_fail_without_exposing_values(launcher, layout, url, capsys):
    write_config(layout, api_url=url)
    assert launcher.main(["serve"], layout=layout) == 78
    output = capsys.readouterr()
    assert output.out == "" and "CANARY" not in output.err
    assert "localhost" not in output.err


def test_credentials_are_selected_once_and_never_in_status(launcher, layout, monkeypatch, capsys):
    write_config(layout, api_key_env="FIXTURE_SECRET")
    monkeypatch.setenv("FIXTURE_SECRET", "secret-CANARY")
    monkeypatch.setenv("PREFECT_API_AUTH_STRING", "unrelated-CANARY")
    url, credentials = launcher.selection(launcher.read_config(layout), os.environ, layout.home)
    assert credentials == {"PREFECT_API_KEY": "secret-CANARY"}
    launcher.main(["status"], layout=layout)
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err and url not in output.out
    write_config(layout, api_key_env="FIXTURE_SECRET", api_auth_string_env="OTHER")
    with pytest.raises(launcher.Unavailable):
        launcher.selection(launcher.read_config(layout), os.environ, layout.home)


def test_profile_credentials_and_named_environment_are_ambiguous(launcher, layout):
    profiles = layout.home / "profiles.toml"
    profiles.write_text('[profiles.local]\nPREFECT_API_URL="http://localhost/api"\n'
                        'PREFECT_API_KEY="profile-CANARY"\n')
    profiles.chmod(0o600)
    write_config(layout, api_url="", profiles_path=str(profiles), profile="local",
                 api_auth_string_env="FIXTURE_SECRET")
    with pytest.raises(launcher.Unavailable):
        launcher.selection(launcher.read_config(layout), {"FIXTURE_SECRET": "env-CANARY"}, layout.home)


def test_private_settings_and_profile_paths_reject_links_and_writes(launcher, layout):
    layout.config.chmod(0o644)
    with pytest.raises(launcher.Unavailable):
        launcher.read_config(layout)
    write_config(layout)
    original = layout.home / "real-profile.toml"
    original.write_text('[profiles.local]\nPREFECT_API_URL="http://localhost/api"\n')
    original.chmod(0o600)
    alias = layout.home / "profile-link.toml"
    alias.symlink_to(original)
    write_config(layout, api_url="", profiles_path=str(alias), profile="local")
    with pytest.raises(launcher.Unavailable):
        launcher.selection(launcher.read_config(layout), {}, layout.home)
    write_config(layout, api_url="", profiles_path=str(original), profile="local")
    original.chmod(0o666)
    with pytest.raises(launcher.Unavailable):
        launcher.selection(launcher.read_config(layout), {}, layout.home)


def test_tool_size_allowance_preserves_default_input_limit(launcher, layout, monkeypatch):
    tool = layout.home / "uv"
    with tool.open("wb") as stream:
        stream.truncate(24 * 1024 * 1024)
    tool.chmod(0o700)
    with pytest.raises(launcher.Unavailable, match="unsafe_file"):
        launcher.safe(tool)
    with pytest.raises(launcher.Unavailable, match="unsafe_file"):
        launcher.checked_path(tool, layout.home)
    assert launcher.checked_path(tool, layout.home, max_bytes=256 * 1024 * 1024) == tool
    monkeypatch.setattr(launcher.shutil, "which", lambda name: str(tool) if name == "uv" else None)
    monkeypatch.setattr(launcher.Path, "home", classmethod(lambda cls: layout.home))
    assert launcher.uv_executable() == str(tool)
    monkeypatch.setattr(launcher, "run_command", lambda *_args, **_kwargs: b"[3,13,16]\n")
    assert launcher.python_identity(tool)["path"] == str(tool)


def test_child_environment_has_neutral_home_and_only_selected_settings(launcher, layout, monkeypatch):
    generation = layout.base / "generations" / ("a" * 64)
    monkeypatch.setenv("PREFECT_API_URL", "https://wrong.invalid")
    monkeypatch.setenv("PREFECT_API_KEY", "ambient-CANARY")
    monkeypatch.setenv("PREFECT_MCP_ENABLE_EXPERIMENTAL_TOOLS", "true")
    monkeypatch.setenv("LOGFIRE_TOKEN", "ambient-CANARY")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "ambient-CANARY")
    monkeypatch.setenv("UV_INDEX_URL", "https://wrong.invalid")
    env = launcher.child_environment(generation, "http://localhost/api", {})
    assert env["HOME"] == str(generation / "home")
    assert env["PREFECT_PROFILES_PATH"] == str(generation / "profiles.toml")
    assert env["PREFECT_API_URL"] == "http://localhost/api"
    assert env["PREFECT_SERVER_ALLOW_EPHEMERAL_MODE"] == "false"
    assert not any("CANARY" in value for value in env.values())
    assert not any(name.startswith(("UV_", "LOGFIRE_", "OTEL_")) for name in env)


@pytest.fixture
def fake_install(launcher, layout, monkeypatch):
    calls = []
    interpreter = Path(sys.executable).resolve()
    identity = {"path": str(interpreter), "sha256": hashlib.sha256(interpreter.read_bytes()).hexdigest(),
                "version": [3, 13, 16]}
    monkeypatch.setattr(launcher, "python_identity", lambda _: identity)
    monkeypatch.setattr(launcher, "uv_executable", lambda: "/synthetic/uv")
    monkeypatch.setattr(launcher, "distribution_identity", lambda *_: {
        "fixture": {"version": "1", "direct_url_sha256": None}})

    def run(argv, *, cwd, env, timeout=60):
        calls.append((argv, Path(cwd), dict(env)))
        if argv[1:3] == ["python", "find"]:
            return str(interpreter).encode() + b"\n"
        if "sync" in argv:
            binary = Path(cwd) / ".venv/bin/python"
            binary.parent.mkdir(parents=True)
            binary.symlink_to(interpreter)
            return b""
        assert argv[-1] == "--check-runtime"
        return b'{"qualified": true}\n'

    monkeypatch.setattr(launcher, "run_command", run)
    return calls


def test_install_is_frozen_snapshotted_and_idempotent(launcher, layout, fake_install):
    launcher.install(layout)
    generation, python = launcher.resolve_runtime(layout)
    assert generation.name == launcher.input_identity(layout.base)[0]
    assert (generation / "server.py").read_bytes() == (layout.base / "server.py").read_bytes()
    assert python == generation / ".venv/bin/python"
    sync = next(call for call in fake_install if "sync" in call[0])
    assert "--frozen" in sync[0] and "--no-python-downloads" in sync[0]
    assert sync[2]["UV_PROJECT_ENVIRONMENT"] == str(generation / ".venv")
    launcher.install(layout)
    assert sum("sync" in call[0] for call in fake_install) == 1


def test_failed_install_retains_generation_and_refuses_retry(launcher, layout, fake_install, monkeypatch):
    original = launcher.run_command

    def failed(argv, **kwargs):
        if "sync" in argv:
            raise launcher.Unavailable("installation_failed", 23)
        return original(argv, **kwargs)

    monkeypatch.setattr(launcher, "run_command", failed)
    assert launcher.main(["install"], layout=layout) == 23
    generation = layout.base / "generations" / launcher.input_identity(layout.base)[0]
    assert generation.is_dir() and not (generation / ".complete.json").exists()
    monkeypatch.setattr(launcher, "run_command", original)
    with pytest.raises(launcher.Unavailable):
        launcher.install(layout)


def test_concurrent_install_refuses_existing_lock(launcher, layout, fake_install):
    (layout.base / "install.lock").mkdir(mode=0o700)
    with pytest.raises(launcher.Unavailable):
        launcher.install(layout)
    assert fake_install == []


def test_changed_or_unsafe_generation_refuses_serve(launcher, layout, fake_install):
    launcher.install(layout)
    generation, _ = launcher.resolve_runtime(layout)
    (generation / "server.py").write_text("# altered bootstrap\n")
    with pytest.raises(launcher.Unavailable):
        launcher.resolve_runtime(layout)


def test_serve_validates_target_then_executes_without_sync(launcher, layout, fake_install, monkeypatch):
    launcher.install(layout)
    count = len(fake_install)
    generation, python = launcher.resolve_runtime(layout)
    writes = {}
    monkeypatch.setattr(launcher.os, "chdir", lambda path: writes.update(cwd=path))
    monkeypatch.setattr(launcher.os, "execve", lambda path, args, env: writes.update(path=path, args=args, env=env))
    assert launcher.main(["serve"], layout=layout) == 0
    assert len(fake_install) == count
    assert writes["cwd"] == generation / "work"
    assert writes["path"] == str(python) and writes["args"] == [str(python), "-I", str(generation / "server.py")]
    assert writes["env"]["PREFECT_API_URL"] == "http://127.0.0.1:4200/api"


def test_disabled_install_has_no_subprocess_or_generation_effect(launcher, layout, fake_install):
    write_config(layout, enabled=False)
    with pytest.raises(launcher.Unavailable):
        launcher.install(layout)
    assert fake_install == [] and not (layout.base / "generations").exists()


@pytest.mark.parametrize("changed", [
    {},
    {"fixture": {"version": "2", "direct_url_sha256": None}},
    {"fixture": {"version": "1", "direct_url_sha256": "a" * 64}},
    {"fixture": {"version": "1", "direct_url_sha256": None},
     "extra": {"version": "1", "direct_url_sha256": None}},
])
def test_dependency_drift_refuses_reuse_before_serve(launcher, layout, fake_install, monkeypatch, changed):
    launcher.install(layout)
    monkeypatch.setattr(launcher, "distribution_identity", lambda *_: changed)
    with pytest.raises(launcher.Unavailable, match="runtime_dependency_drift"):
        launcher.resolve_runtime(layout)


def test_unverified_subprocess_cleanup_retains_install_lock(launcher, layout, fake_install, monkeypatch):
    original = launcher.run_command

    def uncertain(argv, **kwargs):
        if "sync" in argv:
            raise launcher.Unavailable("command_cleanup_unverified", 124, retain_lock=True)
        return original(argv, **kwargs)

    monkeypatch.setattr(launcher, "run_command", uncertain)
    assert launcher.main(["install"], layout=layout) == 124
    assert (layout.base / "install.lock").is_dir()
    assert not list((layout.base / "generations").glob("*/.complete.json"))


def test_subprocess_failure_preserves_exit_without_raw_diagnostics(launcher, tmp_path):
    with pytest.raises(launcher.Unavailable) as failure:
        launcher.run_command([sys.executable, "-I", "-c",
                              "import sys; print('secret-CANARY',file=sys.stderr); sys.exit(23)"],
                             cwd=tmp_path, env={"PATH": os.defpath})
    assert failure.value.code == 23
    assert "CANARY" not in str(failure.value)


def test_timeout_stops_owned_session_and_keeps_timeout_status(launcher, tmp_path, monkeypatch):
    events = []

    class Process:
        pid = 45678
        returncode = None

        def wait(self, *, timeout):
            events.append(("wait", timeout))
            if len(events) == 1:
                raise launcher.subprocess.TimeoutExpired(["fixture"], timeout)
            self.returncode = -9
            return -9

    def popen(argv, **kwargs):
        assert kwargs["start_new_session"] is True
        return Process()

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, sig: events.append(("killpg", pid, sig)))
    with pytest.raises(launcher.Unavailable) as failure:
        launcher.run_command(["fixture"], cwd=tmp_path, env={}, timeout=1)
    assert failure.value.code == 124 and failure.value.retain_lock is False
    assert events == [("wait", 1), ("killpg", Process.pid, launcher.signal.SIGKILL), ("wait", 5)]


def test_group_permission_denial_never_proves_cleanup(launcher, monkeypatch):
    events = []

    class Process:
        pid = 45678

        def kill(self):
            events.append("direct-kill")

        def wait(self, *, timeout):
            events.append("wait")
            return -9

    def denied(*_):
        raise PermissionError("untrusted-CANARY")

    monkeypatch.setattr(launcher.os, "killpg", denied)
    assert launcher.stop_owned(Process()) is False
    assert events == ["direct-kill", "wait"]


def test_changed_lock_selects_new_generation_without_destroying_old(launcher, layout, fake_install):
    launcher.install(layout)
    generation, _ = launcher.resolve_runtime(layout)
    (layout.base / "uv.lock").write_text("version=2\n")
    with pytest.raises(launcher.Unavailable):
        launcher.resolve_runtime(layout)
    assert (generation / ".complete.json").is_file()
