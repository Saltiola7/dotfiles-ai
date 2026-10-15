"""Bind current V2 routes and retained V1 aliases to strict provider admission."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_dbsctrctl"


@pytest.mark.parametrize("suffix", ["claude", "gpt"])
@pytest.mark.parametrize("version", [1, 2])
def test_committed_primary_route_is_admitted(tmp_path, suffix, version):
    primary = f"build-{suffix}"
    control = ROOT / "private_dot_config/opencode"
    agent = (control / f"agents/{primary}.md").read_text()
    command = (control / f"commands/dbsctr-{suffix}.md").read_text()
    route = next(line.removeprefix("model: ") for line in agent.splitlines() if line.startswith("model: "))
    assert f"model: {route}" in command.splitlines()
    provider, model = route.split("/", 1)
    if version == 1:
        provider = {"google-vertex": "google-vertex-anthropic"}.get(provider, provider)
    database = tmp_path / "opencode.db"
    with sqlite3.connect(database) as connection:
        if version == 2:
            connection.executescript("""
                create table session_v2 (id text primary key, parent_id text, agent text);
                create table session_message (id text primary key, session_id text, type text, seq integer, data text);
            """)
            connection.execute("insert into session_v2 values (?, ?, ?)", ("session", None, primary))
            body = {"agent": primary, "model": {"providerID": provider, "id": model}}
            connection.execute("insert into session_message values (?, ?, ?, ?, ?)", (
                "message", "session", "assistant", 1, json.dumps(body)))
        else:
            connection.executescript("""
                create table session (id text primary key, agent text);
                create table message (id text primary key, session_id text, data text);
            """)
            connection.execute("insert into session values (?, ?)", ("session", primary))
            body = {"providerID": provider, "modelID": model}
            connection.execute("insert into message values (?, ?, ?)", (
                "message", "session", json.dumps(body)))
    loader = importlib.machinery.SourceFileLoader("route_helper", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    activation = json.dumps({"schema_version": 1, "core_revision": "3.29", "overlays": {
        "build": "neutral", "build-gpt": "openai", "build-claude": "anthropic"}})
    value = module.harness_activation_for_message(str(database), "message", activation)
    assert (value["agent_id"], value["provider_id"], value["model_id"]) == (primary, provider, model)
    assert module.validate_stored_harness_activation(value) == value

    # Reject foreign providers and the other schema's Vertex namespace.
    identity = body["model"] if version == 2 else body
    vertex = "google-vertex" if version == 2 else "google-vertex-anthropic"
    rejected = ["openai", "google-vertex-anthropic" if version == 2 else "google-vertex"] if suffix == "claude" else [vertex]
    table = "session_message" if version == 2 else "message"
    for denied_provider in rejected:
        identity["providerID"] = denied_provider
        with sqlite3.connect(database) as connection:
            connection.execute(f"update {table} set data=? where id=?", (json.dumps(body), "message"))
        with pytest.raises(RuntimeError, match="provider does not match its primary agent"):
            module.harness_activation_for_message(str(database), "message", activation)
