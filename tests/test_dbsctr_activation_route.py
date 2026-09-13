"""Bind lifecycle admission to the committed primary and entry command routes."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "dot_local/bin/executable_dbsctrctl"


@pytest.mark.parametrize("suffix", ["claude", "gpt"])
def test_committed_primary_route_is_admitted(tmp_path, suffix):
    primary = f"build-{suffix}"
    control = ROOT / "private_dot_config/opencode"
    agent = (control / f"agents/{primary}.md").read_text()
    command = (control / f"commands/dbsctr-{suffix}.md").read_text()
    route = next(line.removeprefix("model: ") for line in agent.splitlines() if line.startswith("model: "))
    assert f"model: {route}" in command.splitlines()
    provider, model = route.split("/", 1)
    database = tmp_path / "opencode.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            create table session (id text primary key, agent text);
            create table message (id text primary key, session_id text, data text);
        """)
        connection.execute("insert into session values (?, ?)", ("session", primary))
        connection.execute("insert into message values (?, ?, ?)", (
            "message", "session", json.dumps({"providerID": provider, "modelID": model})))
    loader = importlib.machinery.SourceFileLoader("route_helper", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    activation = json.dumps({"schema_version": 1, "core_revision": "3.29", "overlays": {
        "build": "neutral", "build-gpt": "openai", "build-claude": "anthropic"}})
    value = module.harness_activation_for_message(str(database), "message", activation)
    assert (value["agent_id"], value["provider_id"], value["model_id"]) == (primary, provider, model)
    assert module.validate_stored_harness_activation(value) == value
