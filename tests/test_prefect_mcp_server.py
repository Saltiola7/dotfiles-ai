"""Offline bootstrap boundaries; ordinary pytest never imports the Prefect SDK."""

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "private_dot_config/dotfiles-ai/runtime/prefect-mcp/server.py"


@pytest.fixture
def bootstrap(monkeypatch):
    spec = importlib.util.spec_from_file_location("prefect_bootstrap_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.os, "environ", dict(os.environ))
    return module


@pytest.fixture
def upstream(bootstrap, monkeypatch):
    class NotFoundError(Exception):
        pass

    experimental = types.SimpleNamespace(execution_plans_enabled=False)
    calls = []

    class Server:
        def __init__(self):
            self.allowed = None
            self.missing = set()
            self.writable = set()
            self.unsafe = False

        def enable(self, *, keys, only):
            assert only is True
            # FastMCP 3.4.11 includes the version separator for unversioned tools.
            available = set(bootstrap.READ_ONLY_TOOLS) | {"unexpected_write"} | set(bootstrap.EXPERIMENTAL_TOOLS)
            self.allowed = {name for name in available if "tool:" + name + "@" in keys}

        async def list_tools(self):
            names = (set(bootstrap.READ_ONLY_TOOLS) | {"unexpected_write"}) - self.missing
            return [types.SimpleNamespace(
                name=name,
                annotations=types.SimpleNamespace(readOnlyHint=name not in self.writable),
            ) for name in sorted(names & self.allowed)]

        async def get_tool(self, name):
            return object() if name in self.allowed else None

        async def call_tool(self, name, arguments):
            calls.append((name, experimental.execution_plans_enabled))
            if self.unsafe:
                return types.SimpleNamespace(structured_content={"success": True})
            if not experimental.execution_plans_enabled:
                return types.SimpleNamespace(structured_content={
                    "success": False, "enabled": False, "namespace": "execution_plans",
                })
            raise NotFoundError(name)

    server = Server()
    server.process_settings = types.SimpleNamespace(
        api=types.SimpleNamespace(url="http://127.0.0.1:9/api", key=None, auth_string=None),
        server=types.SimpleNamespace(ephemeral=types.SimpleNamespace(enabled=False)),
    )
    server.cloud_settings = types.SimpleNamespace(enabled=False, auth_token_key=None)
    server.telemetry_settings = types.SimpleNamespace(send_to_logfire=False, console=False)
    factory_calls = []

    def factory(**kwargs):
        factory_calls.append(kwargs)
        return server

    modules = {
        "prefect_mcp_server": types.ModuleType("prefect_mcp_server"),
        "prefect_mcp_server.server": types.ModuleType("prefect_mcp_server.server"),
        "prefect_mcp_server.settings": types.ModuleType("prefect_mcp_server.settings"),
        "prefect_mcp_server.cloud_oauth": types.ModuleType("prefect_mcp_server.cloud_oauth"),
        "prefect": types.ModuleType("prefect"),
        "prefect.settings": types.ModuleType("prefect.settings"),
        "logfire": types.ModuleType("logfire"),
        "fastmcp": types.ModuleType("fastmcp"),
        "fastmcp.exceptions": types.ModuleType("fastmcp.exceptions"),
    }
    modules["prefect_mcp_server.server"].build_prefect_mcp_server = factory
    modules["prefect_mcp_server.settings"].settings = types.SimpleNamespace(
        experimental=experimental, logfire=types.SimpleNamespace(send_to_logfire=None),
    )
    modules["prefect_mcp_server.cloud_oauth"].settings = server.cloud_settings
    modules["prefect_mcp_server"].cloud_oauth = modules["prefect_mcp_server.cloud_oauth"]
    modules["prefect.settings"].get_current_settings = lambda: server.process_settings
    modules["logfire"].DEFAULT_LOGFIRE_INSTANCE = types.SimpleNamespace(config=server.telemetry_settings)
    modules["fastmcp.exceptions"].NotFoundError = NotFoundError
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(bootstrap, "runtime_versions", lambda: {"python": "test", "prefect-mcp": "test"})
    monkeypatch.setattr(bootstrap, "installed_upstream_commit", lambda: bootstrap.UPSTREAM_COMMIT)
    return server, experimental, factory_calls, calls


def test_factory_has_no_docs_or_cloud_and_uses_server_allowlist(bootstrap, upstream):
    server, _, factory_calls, _ = upstream
    assert bootstrap.build_server() is server
    assert factory_calls == [{
        "name": "Local Prefect inspection", "auth_provider": None,
        "include_docs_proxy": False, "include_cloud_tools": False,
        "include_cloud_oauth_tools": False,
    }]
    assert server.allowed == set(bootstrap.READ_ONLY_TOOLS)
    assert len(server.allowed) == 12


def test_unversioned_component_key_requires_version_separator(bootstrap, upstream):
    server, _, _, _ = upstream
    bootstrap.build_server()
    server.enable(keys={"tool:orientation"}, only=True)
    assert asyncio.run(server.get_tool("orientation")) is None
    server.enable(keys={"tool:orientation@"}, only=True)
    assert asyncio.run(server.get_tool("orientation")) is not None


def test_qualification_checks_catalog_and_direct_denial_even_if_feature_changes(bootstrap, upstream):
    server, experimental, _, calls = upstream
    bootstrap.build_server()
    result = asyncio.run(bootstrap.qualify_server(server))
    assert result["qualified"] is True
    assert result["tools"] == sorted(bootstrap.READ_ONLY_TOOLS)
    assert result["experimental_denied"] == sorted(bootstrap.EXPERIMENTAL_TOOLS)
    assert set(calls) == {(name, enabled) for name in bootstrap.EXPERIMENTAL_TOOLS for enabled in (False, True)}
    assert experimental.execution_plans_enabled is False


def test_offline_check_records_denied_import_probes_without_arguments(bootstrap, upstream, monkeypatch):
    attempts = []
    monkeypatch.setattr(bootstrap, "install_offline_guard", lambda: attempts)
    original = bootstrap.build_server

    def build_with_caught_probes():
        # These events represent probes the guard denied and the SDK caught.
        attempts.extend(["socket.__new__", "subprocess.Popen", "subprocess.Popen"])
        return original()

    monkeypatch.setattr(bootstrap, "build_server", build_with_caught_probes)
    result = bootstrap.check_runtime()
    assert result["network"] == "blocked"
    assert result["blocked_import_probes"] == {"socket.__new__": 1, "subprocess.Popen": 2}
    assert attempts == []


def test_offline_check_rejects_caught_effect_during_qualification(bootstrap, upstream, monkeypatch):
    attempts = []
    monkeypatch.setattr(bootstrap, "install_offline_guard", lambda: attempts)
    original = bootstrap.qualify_server

    async def qualification_with_caught_effect(server):
        result = await original(server)
        attempts.append("socket.connect")
        return result

    monkeypatch.setattr(bootstrap, "qualify_server", qualification_with_caught_effect)
    with pytest.raises(bootstrap.BootstrapError, match="offline_effect_attempted"):
        bootstrap.check_runtime()


@pytest.mark.parametrize("defect", ["missing", "writable", "unsafe"])
def test_qualification_rejects_missing_writable_or_callable_write(bootstrap, upstream, defect):
    server, experimental, _, _ = upstream
    bootstrap.build_server()
    if defect == "missing":
        server.missing.add("get_identity")
    elif defect == "writable":
        server.writable.add("get_flow_runs")
    else:
        server.unsafe = True
    with pytest.raises(bootstrap.BootstrapError):
        asyncio.run(bootstrap.qualify_server(server))
    assert experimental.execution_plans_enabled is False


@pytest.mark.parametrize("defect", ["ephemeral", "telemetry", "cloud", "experimental", "auth", "target"])
def test_qualification_rejects_unsafe_actual_sdk_state(bootstrap, upstream, defect):
    server, experimental, _, _ = upstream
    bootstrap.build_server()
    if defect == "ephemeral":
        server.process_settings.server.ephemeral.enabled = True
    elif defect == "telemetry":
        server.telemetry_settings.send_to_logfire = True
    elif defect == "cloud":
        server.cloud_settings.enabled = True
    elif defect == "experimental":
        experimental.execution_plans_enabled = True
    elif defect == "auth":
        server.process_settings.api.key = "secret-canary"
    else:
        server.process_settings.api.url = "https://unrelated.invalid/api"
    with pytest.raises(bootstrap.BootstrapError):
        asyncio.run(bootstrap.qualify_server(server))


def test_child_controls_preserve_only_selected_target_and_private_paths(bootstrap, monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:4201/api")
    monkeypatch.setenv("PREFECT_API_AUTH_STRING", "selected:canary")
    monkeypatch.setenv("PREFECT_HOME", "/private/runtime/home/prefect")
    monkeypatch.setenv("PREFECT_PROFILES_PATH", "/private/runtime/profiles.toml")
    monkeypatch.setenv("PREFECT_PROFILE", "unrelated-cloud-profile")
    monkeypatch.setenv("PREFECT_MCP_CLOUD_AUTH_TOKEN_KEY", "unrelated-canary")
    monkeypatch.setenv("LOGFIRE_TOKEN", "unrelated-canary")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://unrelated.invalid")
    bootstrap.prepare_environment()
    assert os.environ["PREFECT_API_AUTH_STRING"] == "selected:canary"
    assert os.environ["PREFECT_HOME"] == "/private/runtime/home/prefect"
    assert os.environ["PREFECT_PROFILES_PATH"] == "/private/runtime/profiles.toml"
    assert "PREFECT_PROFILE" not in os.environ
    assert "PREFECT_MCP_CLOUD_AUTH_TOKEN_KEY" not in os.environ
    assert "LOGFIRE_TOKEN" not in os.environ
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in os.environ
    assert os.environ["PREFECT_MCP_EXPERIMENTAL_EXECUTION_PLANS_ENABLED"] == "false"
    assert os.environ["PREFECT_SERVER_EPHEMERAL_ENABLED"] == "false"
    assert json.loads(os.environ["LOGFIRE"])["send_to_logfire"] is None
    assert os.environ["LOGFIRE_SEND_TO_LOGFIRE"] == "false"
    assert os.environ["LOGFIRE_CONSOLE"] == "false"
    assert os.environ["OTEL_SDK_DISABLED"] == "true"


@pytest.mark.parametrize("target", ["", "file:///tmp/prefect", "http://user:secret@host/api", "http://host/api?secret=canary", "http://host/api#canary", "http://host\n.invalid/api"])
def test_invalid_target_refuses_before_upstream_import(bootstrap, monkeypatch, capsys, target):
    monkeypatch.setenv("PREFECT_API_URL", target)
    imported = []
    monkeypatch.setattr(bootstrap, "build_server", lambda: imported.append(True))
    assert bootstrap.main([]) == 1
    assert imported == []
    result = capsys.readouterr()
    assert result.out == ""
    assert result.err == "Prefect MCP unavailable.\n"


def test_serve_dependency_error_never_emits_unframed_stdout_or_secrets(bootstrap, monkeypatch, capsys):
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:4201/api")
    def fail():
        raise RuntimeError("secret-canary from dependency")
    monkeypatch.setattr(bootstrap, "build_server", fail)
    assert bootstrap.main([]) == 1
    result = capsys.readouterr()
    assert result.out == "" and result.err == "Prefect MCP unavailable.\n"


def test_check_runtime_failure_has_bounded_json_without_raw_errors(bootstrap, monkeypatch, capsys):
    def fail():
        raise RuntimeError("secret-canary from dependency")
    monkeypatch.setattr(bootstrap, "check_runtime", fail)
    assert bootstrap.main(["--check-runtime"]) == 1
    result = capsys.readouterr()
    assert json.loads(result.out) == {"schema_version": 1, "qualified": False, "reason": "runtime_check_failed"}
    assert result.err == ""


def test_distribution_provenance_requires_exact_git_commit(bootstrap, monkeypatch):
    monkeypatch.setattr(bootstrap.metadata, "distribution", lambda name: types.SimpleNamespace(
        read_text=lambda filename: json.dumps({"vcs_info": {"commit_id": "0" * 40}}),
    ))
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.installed_upstream_commit()


def test_offline_guard_blocks_socket_creation_in_separate_process():
    code = """
import asyncio, importlib.util, socket, sys
spec = importlib.util.spec_from_file_location('bootstrap', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
loop = asyncio.new_event_loop()
try:
    module.install_offline_guard()
    try:
        socket.socket()
    except module.OfflineNetworkDenied:
        print('socket denied')
    else:
        raise AssertionError('socket was allowed')
finally:
    loop.close()
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(SCRIPT)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "socket denied\n"


def test_unknown_cli_option_is_bounded_and_does_not_import_sdk():
    result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--unknown-canary"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 64
    assert result.stdout == "" and result.stderr == "Prefect MCP bootstrap: invalid arguments.\n"
