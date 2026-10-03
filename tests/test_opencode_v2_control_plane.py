"""Exact-candidate synthetic qualification; never use operator config or history."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import socket
import subprocess
import sys
import threading
import time

import pytest

import probe_opencode_v2 as probe
from test_opencode_control_plane import DATA, OC, ROOT


def project(root, name):
    target = root / ".config/opencode" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text("{}\n")
    result = subprocess.run([
        "chezmoi", "-S", str(ROOT), "-D", str(root), "--config", "/dev/null",
        "--config-format", "toml", "--override-data", json.dumps(DATA),
        "--cache", str(root / "chezmoi-cache"), "--persistent-state", str(root / "chezmoi-state"),
        "apply", str(target),
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(target.read_text())


def test_native_preferences_preserve_local_fields_and_are_idempotent(tmp_path):
    target = tmp_path / ".config/opencode/cli.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"theme": {"name": "old", "mode": "light", "local": 1},
                                  "keybinds": {"agent_cycle": "shift+tab"}, "local": [1, 2]}))
    result = project(tmp_path, "cli.json")
    assert result == {"$schema": "https://opencode.ai/v2/cli.json",
                      "theme": {"name": "catppuccin", "mode": "dark", "local": 1},
                      "keybinds": {"agent_cycle": "shift+tab"}, "local": [1, 2]}
    assert project(tmp_path, "cli.json") == result
    assert target.stat().st_mode & 0o777 == 0o600


def test_configuration_modifier_refuses_invalid_input_without_overwriting(tmp_path):
    target = tmp_path / ".config/opencode/opencode.json"
    target.parent.mkdir(parents=True)
    for invalid in ("{invalid-private-value", "[]", "null"):
        target.write_text(invalid)
        with pytest.raises(AssertionError, match="original left unchanged"):
            project(tmp_path, "opencode.json")
        assert target.read_text() == invalid


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        assert size <= 16 * 1024 * 1024
        request = json.loads(self.rfile.read(size))
        self.server.requests.append(request)
        completed = sum(item.get("role") == "tool" for item in request.get("messages", []))
        if completed < len(self.server.steps):
            name, args = self.server.steps[completed]
            delta = {"tool_calls": [{"index": 0, "id": f"fixture_{completed}", "type": "function",
                                    "function": {"name": name, "arguments": json.dumps(args)}}]}
            reason = "tool_calls"
        else:
            delta, reason = {"content": "Fixture complete."}, "stop"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for part, finish in (({"role": "assistant"}, None), (delta, None), ({}, reason)):
            self.wfile.write(("data: " + json.dumps({"id": "fixture", "object": "chat.completion.chunk",
                "created": 1, "model": "mock", "choices": [{"index": 0, "delta": part,
                "finish_reason": finish}]}) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")


@pytest.mark.skipif(not os.environ.get("OPENCODE_V2_BINARY"), reason="exact V2 candidate not selected")
def test_exact_v2_roles_plugins_instructions_and_permissions(tmp_path, monkeypatch):
    binary = Path(os.environ["OPENCODE_V2_BINARY"])
    original = probe.identity(binary)
    assert original[-1] == "af29b0b1b0291dbf2471c66c89d2e055b6afa9c41a950e052fa609c3295e2a75"
    package = Path(os.environ["OPENCODE_PONYTAIL_PACKAGE"]).resolve(strict=True)
    assert json.loads((package / "package.json").read_text())["version"] == "4.10.3"
    config = project(tmp_path, "opencode.json")
    assert config["plugin"] == ["@dietrichgebert/ponytail@4.10.3"]
    config_dir = tmp_path / ".config/opencode"
    shutil.copytree(OC / "agents", config_dir / "agents")
    shutil.copytree(OC / "commands", config_dir / "commands")
    shutil.copyfile(OC / "AGENTS.md", config_dir / "AGENTS.md")
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin", "SHELL": "/bin/bash",
           "TERM": "dumb", "NO_COLOR": "1"}
    for key, name in {"HOME": "home", "OPENCODE_TEST_HOME": "home", "XDG_CONFIG_HOME": ".config",
                      "OPENCODE_CONFIG_DIR": ".config/opencode", "XDG_DATA_HOME": "data",
                      "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache", "TMPDIR": "tmp"}.items():
        directory = tmp_path / name
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        env[key] = str(directory)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    server.steps, server.requests = [], []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    # Native local directories resolve index/server, whereas npm resolves exports.
    # Exercise the verified package entrypoint without installing into native cache.
    plugin = tmp_path / "staged-plugin"
    plugin.mkdir()
    (plugin / "index.js").write_text("export { default } from " +
        json.dumps(str(package / ".opencode/plugins/ponytail.mjs")) + ";\n")
    config.pop("references", None)
    # Preserve server identities and managed permissions, replace transports only.
    config["mcp"] = {name: {"type": "local", "enabled": True,
        "command": [sys.executable, str(ROOT / "tests/fixtures/opencode_v2_mcp.py"),
                    str(tmp_path / f"{name}-calls")]}
        for name in config["mcp"]}
    config.update({"plugin": [str(plugin)], "update": "disable", "model": "probe/mock",
        "small_model": "probe/mock", "enabled_providers": ["probe"], "provider": {"probe": {
            "npm": "@ai-sdk/openai-compatible", "options": {"baseURL": f"http://127.0.0.1:{server.server_port}/v1"},
            "models": {"mock": {"limit": {"context": 32000, "output": 1000}}}}}})
    (config_dir / "opencode.json").write_text(json.dumps(config))
    monkeypatch.setattr(probe, "OUTPUT_LIMIT", 1024 * 1024)
    monkeypatch.setattr(probe, "TIMEOUT_SECONDS", 90)

    def run(*args, timeout=90):
        previous = probe.TIMEOUT_SECONDS
        probe.TIMEOUT_SECONDS = timeout
        try:
            return probe.run(binary, args, tmp_path, env)
        finally:
            probe.TIMEOUT_SECONDS = previous

    try:
        assert run("--version") == "opencode v2.0.22"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        run("service", "set", "port", str(port))
        roles = {path.stem for path in (OC / "agents").glob("*.md")} | set(config["agent"]) | {"plan", "build"}
        deadline = time.monotonic() + 30
        for role in sorted(roles):
            while True:
                remaining = deadline - time.monotonic()
                assert remaining > 0, "managed role readiness deadline exceeded"
                try:
                    result = json.loads(run("api", "agent.get", "--param", f"agentID={role}",
                                            "--param", f"location[directory]={tmp_path}", timeout=min(5, remaining)))
                    assert result["data"]["id"] == role
                    assert Path(result["location"]["directory"]).resolve() == tmp_path.resolve()
                    source = OC / "agents" / f"{role}.md"
                    if source.exists():
                        model = re.search(r"^model: (.+)$", source.read_text(), re.MULTILINE)
                        if model:
                            provider, identifier = model[1].split("/", 1)
                            provider = "google-vertex" if provider == "google-vertex-anthropic" else provider
                            assert result["data"]["model"]["providerID"] == provider
                            assert result["data"]["model"]["id"] == identifier
                    break
                except probe.Failure:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.25)
        for namespace in ("skill", "command"):
            entries = json.loads(run("api", f"{namespace}.list", "--param",
                                     f"location[directory]={tmp_path}"))["data"]
            assert any(item.get("id", item.get("name")) == "ponytail" for item in entries)
        for role in ("plan", "build"):
            target = tmp_path / f"{role}-fixture.txt"
            server.steps = [("write", {"path": str(target), "content": "synthetic fixture"})]
            run("run", "--agent", role, "--model", "probe/mock", "--format", "json", "Run synthetic fixture.")
            assert target.exists() == (role == "build")
            if role == "build":
                assert target.read_text() == "synthetic fixture"
        prompt = json.dumps(server.requests[-1]["messages"])
        assert "PONYTAIL MODE ACTIVE" in prompt
        assert "Re-read and validate" in prompt and "initiative-receipt" in prompt
        for role, tool, allowed in (("scout-openai", "context7_guarded", True),
                                    ("build", "context7_guarded", False),
                                    ("plan", "1password_guarded", False),
                                    ("build", "1password_guarded", False)):
            marker = tmp_path / f"{tool.split('_')[0]}-calls"
            before = marker.read_text() if marker.exists() else ""
            server.steps = [("execute", {"code": "return await tools[" +
                json.dumps(tool.split("_")[0]) + "].guarded({})"})]
            output = run("run", "--agent", role, "--model", "probe/mock", "--format", "json", "Run synthetic fixture.")
            after = marker.read_text() if marker.exists() else ""
            if (after != before) != allowed:
                pytest.fail(json.dumps({"role": role, "tool": tool, "output": output,
                    "catalog": [item.get("function", item).get("name")
                                for item in server.requests[-1].get("tools", [])],
                    "mcp_signatures": [line for message in server.requests[-1]["messages"]
                        if message["role"] == "system" and isinstance(message.get("content"), str)
                        for line in message["content"].splitlines() if "guarded" in line]}))
            if role == "build" and tool == "1password_guarded":
                assert "reject" in output.lower() or "denied" in output.lower()
        shell_marker = tmp_path / "shell-executed"
        helper = tmp_path / "dbsctrctl"
        helper.write_text("#!/bin/sh\ntouch " + shlex.quote(str(shell_marker)) + "\n")
        helper.chmod(0o700)
        for role in ("build", "plan"):
            server.steps = [("shell", {"command": f"{shlex.quote(str(helper))} start --cycle-id fixture",
                                       "workdir": str(tmp_path)})]
            run("run", "--agent", role, "--model", "probe/mock", "--format", "json", "Run synthetic fixture.")
            assert shell_marker.exists() == (role == "build")
            if shell_marker.exists():
                shell_marker.unlink()
        wt = tmp_path / "wt"
        wt.write_text(helper.read_text())
        wt.chmod(0o700)
        for role, command in (("build", f"{shlex.quote(str(wt))} remove fixture --force"),
                              ("plan", f"printf readonly; {shlex.quote(str(helper))} start --cycle-id fixture")):
            server.steps = [("shell", {"command": command, "workdir": str(tmp_path)})]
            output = run("run", "--agent", role, "--model", "probe/mock", "--format", "json", "Run synthetic fixture.")
            assert not shell_marker.exists()
            assert "denied" in output.lower() or "not allowed" in output.lower()
        assert probe.identity(binary) == original
    finally:
        try:
            run("service", "stop")
        finally:
            server.shutdown()
            server.server_close()
