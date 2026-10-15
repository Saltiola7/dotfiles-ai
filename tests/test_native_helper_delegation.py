"""Native helper routing, role boundaries, and instruction agreement."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

import pytest

from test_opencode_control_plane import OC, ROOT, rendered_config


def task_permissions(name):
    body = (OC / "agents" / f"{name}.md").read_text()
    block = body.split("  task:\n", 1)[1].split("---", 1)[0]
    return {
        (wildcard or agent): effect
        for wildcard, agent, effect in re.findall(
            r'^    (?:"([*])"|([\w-]+)): (allow|deny)$', block, re.M)
    }


def test_native_controls_inherit_models_and_plan_cannot_delegate_writes():
    agents = rendered_config()["agent"]
    assert agents["build"]["permission"]["task"] == {
        "*": "deny", "general": "allow", "explore": "allow", "scout": "allow", "discovery-writer": "allow"}
    assert agents["plan"]["permission"]["task"] == {
        "*": "deny", "explore": "allow", "scout": "allow"}
    assert agents["plan"]["model"] == "openai/gpt-6.1-sol-fast"
    for name in ("general", "explore"):
        assert "model" not in agents.get(name, {})
    for name in ("scout", "discovery-writer"):
        assert "\nmodel:" not in (OC / "agents" / f"{name}.md").read_text()


def test_fixed_primaries_allow_only_their_provider_helpers():
    for primary, family, model in (
        ("build-claude", "vertex", "google-vertex/claude-opus-5-5@default"),
        ("build-gpt", "openai", "openai/gpt-6.1-sol-fast"),
    ):
        body = (OC / "agents" / f"{primary}.md").read_text()
        assert f"model: {model}\n" in body
        rules = task_permissions(primary)
        assert rules.pop("*") == "deny"
        assert {f"{role}-{family}" for role in ("builder", "explore", "scout", "discovery-writer")} <= rules.keys()
        assert all(name.endswith(f"-{family}") and effect == "allow" for name, effect in rules.items())
        assert "no automatic cross-provider fallback" in body
    for role in ("builder", "explore", "scout", "discovery-writer"):
        assert "model: google-vertex/claude-sonnet-5-5@default\n" in (OC / "agents" / f"{role}-vertex.md").read_text()
    for role, model in (("builder", "gpt-6.1-sol"), ("scout", "gpt-6.1-sol"),
                        ("discovery-writer", "gpt-6.1-sol"), ("explore", "gpt-5.6-terra")):
        assert f"model: openai/{model}\n" in (OC / "agents" / f"{role}-openai.md").read_text()


def test_discovery_delegates_docs_not_implementation():
    assert task_permissions("discovery-coordinator") == {
        "*": "deny", "explore": "allow", "scout": "allow", "discovery-writer": "allow"}
    for name in ("discovery-writer", "discovery-writer-openai", "discovery-writer-vertex"):
        body = (OC / "agents" / f"{name}.md").read_text()
        for boundary in ('"*": deny', '"docs/**": allow', "bash: deny", "task: deny", "external_directory: deny"):
            assert boundary in body
    ignored = (ROOT / ".chezmoiignore").read_text().split('{{ if not .dotfiles_ai.opencode.vertex_project }}', 1)[1].split('{{ end }}', 1)[0]
    assert '.config/opencode/agents/discovery-writer-vertex.md' in ignored


def test_shared_instructions_allow_helpers_but_keep_primary_cycle_ownership():
    for path in ("private_dot_config/opencode/AGENTS.md", "dot_agents/skills/discovery/SKILL.md",
                 "dot_agents/skills/dbsctr/SKILL.md"):
        body = (ROOT / path).read_text()
        assert "without Task or child sessions" not in body
        assert "bounded helpers" in body and "primary" in body
        assert "independent" in body and "slice" in body
    assert "never Task delegation in an ordinary session" not in (ROOT / "dot_agents/skills/dbsctr/SKILL.md").read_text()
    contract = (ROOT / "docs/specs/opencode_control_plane/features/native-helper-delegation.md").read_text()
    for term in ("## Domain", "## Behavior", "## Native configuration", "## Validation",
                 "## Visual Evidence", "accTitle:", "accDescr:", "**Text Equivalent:**"):
        assert term in contract
    assert "features/native-helper-delegation.md" in (ROOT / "docs/specs/opencode_control_plane/README.md").read_text()


@pytest.mark.skipif(os.environ.get("OPENCODE_HELPER_LIVE") != "1", reason="host deployment smoke not selected")
def test_deployed_host_helper_configuration_matches_source():
    home = Path.home()
    installed = json.loads((home / '.config/opencode/opencode.json').read_text())
    expected = rendered_config()["agent"]
    for name in ("build", "build-rnd", "plan", "general"):
        assert installed["agent"][name]["permission"]["task"] == expected[name]["permission"]["task"]
    assert installed["agent"]["plan"]["model"] == "openai/gpt-6.1-sol-fast"
    sources = [OC / 'AGENTS.md', *[OC / 'agents' / f'{name}.md' for name in (
        'build-claude', 'build-gpt', 'builder-openai', 'builder-vertex', 'explore-openai', 'explore-vertex',
        'scout-openai', 'scout-vertex', 'discovery-coordinator', 'discovery-writer',
        'discovery-writer-openai', 'discovery-writer-vertex')]]
    sources += [OC / 'commands' / f'dbsctr-{family}.md' for family in ('gpt', 'claude')]
    for source in sources:
        assert (home / '.config/opencode' / source.relative_to(OC)).read_bytes() == source.read_bytes()
    for name in ('discovery', 'dbsctr'):
        assert (home / '.agents/skills' / name / 'SKILL.md').read_bytes() == (ROOT / 'dot_agents/skills' / name / 'SKILL.md').read_bytes()


@pytest.mark.skipif(not os.environ.get("OPENCODE_HELPER_BINARY"), reason="native helper resolution authority not selected")
def test_native_v2_resolves_helper_permissions_and_model_inheritance(tmp_path):
    """Resolve native roles in isolated state; no inference or child launch."""
    binary = Path(os.environ["OPENCODE_HELPER_BINARY"]).resolve(strict=True)
    env = {"PATH": os.defpath, "TERM": "dumb", "NO_COLOR": "1"}
    for key, name in {"HOME": "home", "OPENCODE_TEST_HOME": "home", "XDG_CONFIG_HOME": "config",
                      "OPENCODE_CONFIG_DIR": "config/opencode", "XDG_DATA_HOME": "data",
                      "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache", "TMPDIR": "tmp"}.items():
        directory = tmp_path / name
        directory.mkdir(parents=True, exist_ok=True)
        env[key] = str(directory)
    config_dir = tmp_path / "config/opencode"
    config = rendered_config()
    # Keep exact role configuration; disable external integrations in this fixture.
    config.update({"plugin": [], "mcp": {"servers": {}}, "update": "disable"})
    config.pop("references", None)
    (config_dir / "opencode.json").write_text(json.dumps(config))
    shutil.copytree(OC / "agents", config_dir / "agents")

    def run(*args):
        result = subprocess.run([str(binary), *args], cwd=tmp_path, env=env,
                                text=True, capture_output=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout

    def agent(name):
        deadline = time.monotonic() + 20
        while True:
            try:
                return json.loads(run("api", "agent.get", "--param", f"agentID={name}",
                                      "--param", f"location[directory]={tmp_path}"))["data"]
            except AssertionError as error:
                if "404" not in str(error) or time.monotonic() >= deadline:
                    raise
                time.sleep(.25)

    def rules(role, action):
        return {rule["resource"]: rule["effect"] for rule in role["permissions"] if rule["action"] == action}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    run("service", "set", "port", str(port))
    try:
        for name, model in (("build-gpt", ("openai", "gpt-6.1-sol-fast")),
                            ("build-claude", ("google-vertex", "claude-opus-5-5@default"))):
            role = agent(name)
            assert (role["model"]["providerID"], role["model"]["id"]) == model
            assert rules(role, "subagent") == task_permissions(name)
        for name in ("general", "explore", "scout", "discovery-writer"):
            assert not agent(name).get("model"), name
        assert rules(agent("plan"), "subagent") == {"*": "deny", "explore": "allow", "scout": "allow"}
        assert rules(agent("build"), "subagent")["general"] == "allow"
        for name in ("discovery-writer", "discovery-writer-openai", "discovery-writer-vertex"):
            role = agent(name)
            assert rules(role, "edit") == {"*": "deny", "docs/**": "allow"}
            assert rules(role, "shell")["*"] == "deny"
            assert rules(role, "subagent")["*"] == "deny"
        for name in ("builder-openai", "builder-vertex"):
            assert rules(agent(name), "subagent")["*"] == "deny"
        for family, provider, models in (
            ("openai", "openai", {"builder": "gpt-6.1-sol", "scout": "gpt-6.1-sol",
                                    "explore": "gpt-5.6-terra", "discovery-writer": "gpt-6.1-sol"}),
            ("vertex", "google-vertex", {role: "claude-sonnet-5-5@default" for role in
                                         ("builder", "explore", "scout", "discovery-writer")}),
        ):
            for name, model in models.items():
                resolved = agent(f"{name}-{family}")["model"]
                assert (resolved["providerID"], resolved["id"]) == (provider, model)
    finally:
        run("service", "stop")
