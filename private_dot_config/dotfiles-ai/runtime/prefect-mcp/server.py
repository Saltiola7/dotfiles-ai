"""Pinned Prefect inspection adapter; package installation belongs to the launcher."""

import asyncio
import json
import os
import sys
from importlib import metadata
from urllib.parse import urlsplit


UPSTREAM_COMMIT = "48efd289bdb2b94a78e35b1331fbefc4fa3f6411"
READ_ONLY_TOOLS = frozenset({
    "orientation", "get_identity", "get_dashboard", "get_deployments", "get_flows",
    "get_flow_runs", "get_flow_run_logs", "get_task_runs", "get_work_pools",
    "read_events", "get_automations", "get_object_schema",
})
EXPERIMENTAL_TOOLS = frozenset({
    "execution_plans_get_schema", "execution_plans_validate", "execution_plans_get",
    "execution_plans_publish",
})
SELECTED_ENVIRONMENT = frozenset({
    "PREFECT_API_URL", "PREFECT_API_AUTH_STRING", "PREFECT_API_KEY",
    "PREFECT_HOME", "PREFECT_PROFILES_PATH",
})


class BootstrapError(Exception):
    """A qualification or selection boundary could not be established."""


class OfflineNetworkDenied(BootstrapError):
    """An offline qualification attempted a socket or subprocess effect."""


def prepare_environment(*, check_runtime=False):
    """Discard ambient project/telemetry settings before importing Prefect."""
    for name in tuple(os.environ):
        if (name.startswith(("PREFECT_", "LOGFIRE_", "OTEL_")) or name == "LOGFIRE") and name not in SELECTED_ENVIRONMENT:
            os.environ.pop(name, None)
    os.environ.update({
        "PREFECT_SERVER_EPHEMERAL_ENABLED": "false",
        "PREFECT_SERVER_ALLOW_EPHEMERAL_MODE": "false",
        "PREFECT_MCP_CLOUD_ENABLED": "false",
        "PREFECT_MCP_EXPERIMENTAL_EXECUTION_PLANS_ENABLED": "false",
        # The upstream wrapper accepts None, but not the SDK's boolean False.
        # Explicit nested None lets the SDK read its own false environment value.
        "LOGFIRE": '{"send_to_logfire":null,"token":null}',
        "LOGFIRE_SEND_TO_LOGFIRE": "false",
        "LOGFIRE_CONSOLE": "false",
        "OTEL_SDK_DISABLED": "true",
    })
    if check_runtime:
        os.environ["PREFECT_API_URL"] = "http://127.0.0.1:9/api"
        os.environ.pop("PREFECT_API_AUTH_STRING", None)
        os.environ.pop("PREFECT_API_KEY", None)


def validate_target(target):
    """Require explicit HTTP target without credential-bearing URL components."""
    try:
        if not target or any(character.isspace() or ord(character) < 32 for character in target):
            raise ValueError
        parsed = urlsplit(target)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise ValueError
        parsed.port  # Validate port syntax before SDK import.
        if os.environ.get("PREFECT_API_AUTH_STRING") and os.environ.get("PREFECT_API_KEY"):
            raise ValueError
    except (TypeError, ValueError):
        raise BootstrapError("target_unavailable") from None


def build_server():
    """Use the exact upstream factory and public server-side visibility controls."""
    from prefect_mcp_server.server import build_prefect_mcp_server

    server = build_prefect_mcp_server(
        name="Local Prefect inspection",
        auth_provider=None,
        include_docs_proxy=False,
        include_cloud_tools=False,
        include_cloud_oauth_tools=False,
    )
    server.enable(keys={"tool:" + name + "@" for name in READ_ONLY_TOOLS}, only=True)
    return server


def runtime_versions():
    versions = {"python": ".".join(map(str, sys.version_info[:3]))}
    for name in ("prefect-mcp", "prefect", "fastmcp", "mcp", "pydantic", "logfire",
                 "logfire-sdk", "opentelemetry-api", "opentelemetry-sdk"):
        value = metadata.version(name)
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise BootstrapError("version_unavailable")
        versions[name] = value
    return versions


def installed_upstream_commit():
    raw = metadata.distribution("prefect-mcp").read_text("direct_url.json")
    if not isinstance(raw, str) or len(raw) > 16384:
        raise BootstrapError("source_unverified")
    try:
        document = json.loads(raw)
        commit = document["vcs_info"]["commit_id"]
    except (TypeError, ValueError, KeyError):
        raise BootstrapError("source_unverified") from None
    if commit != UPSTREAM_COMMIT:
        raise BootstrapError("source_unverified")
    return commit


def verify_process_controls():
    """Observe SDK state instead of treating environment strings as proof."""
    import logfire
    from prefect.settings import get_current_settings
    from prefect_mcp_server import cloud_oauth
    from prefect_mcp_server.settings import settings

    current = get_current_settings()
    telemetry = logfire.DEFAULT_LOGFIRE_INSTANCE.config
    if not (
        current.server.ephemeral.enabled is False
        and current.api.url == "http://127.0.0.1:9/api"
        and current.api.key is None and current.api.auth_string is None
        and cloud_oauth.settings.enabled is False
        and cloud_oauth.settings.auth_token_key is None
        and settings.experimental.execution_plans_enabled is False
        and settings.logfire.send_to_logfire is None
        and telemetry.send_to_logfire is False and telemetry.console is False
    ):
        raise BootstrapError("process_controls_unverified")
    return {"ephemeral": False, "cloud_oauth": False, "experimental_writes": False,
            "telemetry_export": False, "telemetry_console": False,
            "target": "synthetic_without_credentials"}


async def qualify_server(server):
    """Inspect capabilities and deny experiments without calling an API tool."""
    from fastmcp.exceptions import NotFoundError
    from prefect_mcp_server.settings import settings

    controls = verify_process_controls()
    tools = await server.list_tools()
    names = [tool.name for tool in tools]
    if len(names) != len(READ_ONLY_TOOLS) or set(names) != READ_ONLY_TOOLS:
        raise BootstrapError("catalog_mismatch")
    if any(getattr(tool.annotations, "readOnlyHint", None) is not True for tool in tools):
        raise BootstrapError("catalog_not_read_only")
    for name in EXPERIMENTAL_TOOLS:
        if await server.get_tool(name) is not None:
            raise BootstrapError("experimental_visible")

    previous = settings.experimental.execution_plans_enabled
    try:
        # First qualify the upstream feature guard; then prove visibility still
        # denies execution if the feature state changes within this process.
        for enabled in (False, True):
            settings.experimental.execution_plans_enabled = enabled
            for name in sorted(EXPERIMENTAL_TOOLS):
                try:
                    result = await server.call_tool(name, {})
                except NotFoundError:
                    continue
                content = getattr(result, "structured_content", None)
                if enabled or not isinstance(content, dict) or not (
                    content.get("enabled") is False and content.get("success") is False
                    and content.get("namespace") == "execution_plans"
                ):
                    raise BootstrapError("experimental_callable")
    finally:
        settings.experimental.execution_plans_enabled = previous

    return {
        "schema_version": 1, "qualified": True,
        "upstream_commit": installed_upstream_commit(),
        "tools": sorted(names), "experimental_denied": sorted(EXPERIMENTAL_TOOLS),
        "versions": runtime_versions(), "controls": controls,
    }


def install_offline_guard():
    """Deny socket creation and subprocess escape after the event loop is ready."""
    attempts = []

    def audit(event, arguments):
        if (event.startswith("socket.") and event not in {"socket.gethostname"}) or event in {
            "subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec",
        }:
            if len(attempts) < 32:
                attempts.append(event)
            raise OfflineNetworkDenied("offline_effect_denied")

    sys.addaudithook(audit)
    return attempts


def check_runtime():
    # asyncio's own wakeup socket pair must exist before the process-wide guard.
    # Every later socket operation, including during upstream import, is denied.
    loop = asyncio.new_event_loop()
    try:
        attempts = install_offline_guard()
        server = build_server()
        # SDK imports can catch denied IPv6 or host-metadata capability probes.
        # Record only bounded audit event names; the guard still denied effects.
        import_probes = {event: attempts.count(event) for event in sorted(set(attempts))}
        attempts.clear()
        result = loop.run_until_complete(qualify_server(server))
        if attempts:
            raise BootstrapError("offline_effect_attempted")
        result["network"] = "blocked"
        result["blocked_import_probes"] = import_probes
        return result
    finally:
        loop.close()


def emit(document):
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 16384:
        raise BootstrapError("qualification_output_exceeded")
    print(encoded)


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments not in ([], ["--check-runtime"]):
        print("Prefect MCP bootstrap: invalid arguments.", file=sys.stderr)
        return 64
    checking = arguments == ["--check-runtime"]
    try:
        prepare_environment(check_runtime=checking)
        if checking:
            emit(check_runtime())
        else:
            validate_target(os.environ.get("PREFECT_API_URL", ""))
            build_server().run(transport="stdio")
        return 0
    except Exception:
        # SDK errors can include URLs, credentials or remote response bodies.
        if checking:
            emit({"schema_version": 1, "qualified": False, "reason": "runtime_check_failed"})
        else:
            # Serve stdout is reserved exclusively for framed MCP messages.
            print("Prefect MCP unavailable.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
