"""Prefect registration changes only its opted-in native OpenCode entry."""

import json
from pathlib import Path
import subprocess

import pytest

from test_portable_distribution import ROOT, data


def configured(home: Path, *, enabled: bool = False, platform: str = "darwin") -> dict:
    values = data()
    values["chezmoi"] = {"homeDir": str(home), "os": platform, "arch": "arm64"}
    values["dotfiles_ai"]["prefect_mcp"] = {
        "enabled": enabled,
        "api_url": "https://private-target.invalid/api",
        "profile": "private-profile-canary",
        "api_key_env": "PRIVATE_AUTH_SELECTOR_CANARY",
    }
    return values


def render_config(values: dict) -> dict:
    result = subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(values), "execute-template"],
        input=(ROOT / ".chezmoitemplates/opencode.json.tmpl").read_text(),
        text=True, capture_output=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)


def project(home: Path, values: dict, original: dict) -> tuple[subprocess.CompletedProcess, Path]:
    target = home / ".config/opencode/opencode.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(original, indent=2) + "\n")
    result = subprocess.run(
        ["chezmoi", "-S", str(ROOT), "-D", str(home), "--config", "/dev/null",
         "--config-format", "toml", "--override-data", json.dumps(values),
         "--cache", str(home / "chezmoi-cache"), "--persistent-state", str(home / "chezmoi-state"),
         "--exclude", "scripts", "apply", str(target)],
        text=True, capture_output=True, timeout=30,
    )
    return result, target


def expected_entry(home: Path) -> dict:
    return {"type": "local", "command": [str(home / ".local/bin/prefect-mcp"), "serve"],
            "disabled": False}


@pytest.mark.parametrize("platform", ["darwin", "linux"])
def test_prefect_registration_is_optional_and_contains_only_local_launcher(tmp_path, platform):
    home = tmp_path / "home with spaces"
    disabled = render_config(configured(home, platform=platform))
    assert "prefect_local" not in disabled["mcp"]["servers"]
    implicit = data()
    implicit["chezmoi"] = {"homeDir": str(home), "os": platform, "arch": "arm64"}
    assert "prefect_local" not in render_config(implicit)["mcp"]["servers"]

    enabled = render_config(configured(home, enabled=True, platform=platform))
    assert enabled["mcp"]["servers"].pop("prefect_local") == expected_entry(home)
    assert enabled == disabled


def test_prefect_projection_adds_only_its_entry_and_repeats_without_change(tmp_path):
    home = tmp_path / "home with spaces"
    original = {
        "mcp": {"servers": {"operator": {"type": "local", "command": ["operator-server"],
                                        "environment": {"OPERATOR": "preserve"}}},
                "timeout": {"startup": 45000}},
        "plugin": ["operator-local-plugin"],
        "operator_preferences": {"keep": [1, 2]},
    }
    off, target = project(home, configured(home), original)
    assert off.returncode == 0, off.stderr
    without_prefect = json.loads(target.read_text())
    on, target = project(home, configured(home, enabled=True), original)
    assert on.returncode == 0, on.stderr
    projected = json.loads(target.read_text())
    assert projected["mcp"]["servers"]["prefect_local"] == expected_entry(home)
    assert projected["mcp"]["servers"]["operator"] == original["mcp"]["servers"]["operator"]
    assert projected["mcp"]["timeout"] == original["mcp"]["timeout"]
    assert projected["operator_preferences"] == original["operator_preferences"]
    without_entry = json.loads(target.read_text())
    del without_entry["mcp"]["servers"]["prefect_local"]
    assert without_entry == without_prefect

    previous = target.read_bytes()
    repeated, target = project(home, configured(home, enabled=True), projected)
    assert repeated.returncode == 0, repeated.stderr
    assert json.loads(target.read_text()) == projected
    assert target.read_bytes() == previous


@pytest.mark.parametrize("difference", [
    {"type": "remote", "url": "https://private-server-canary.invalid/mcp"},
    {"command": ["different-command", "private-command-canary"]},
    {"environment": {"PREFECT_API_KEY": "private-auth-canary"}},
    {"disabled": True},
    {"disabled": 0},
    {"codemode": False},
])
def test_prefect_conflict_retains_original_without_disclosing_entry(tmp_path, difference):
    home = tmp_path / "home"
    original = {"mcp": {"servers": {"prefect_local": {**expected_entry(home), **difference}}},
                "operator_preferences": {"keep": True}}
    before = json.dumps(original, indent=2) + "\n"
    result, target = project(home, configured(home, enabled=True), original)
    assert result.returncode != 0
    assert "prefect_local conflicts with managed entry; original left unchanged" in result.stderr
    assert "private-" not in result.stdout + result.stderr
    assert target.read_text() == before


def test_disabled_prefect_preserves_existing_same_name_entry(tmp_path):
    home = tmp_path / "home"
    original = {"mcp": {"servers": {"prefect_local": {
        "type": "remote", "url": "https://operator-owned.invalid/mcp", "codemode": False}}}}
    result, target = project(home, configured(home), original)
    assert result.returncode == 0, result.stderr
    assert json.loads(target.read_text())["mcp"]["servers"]["prefect_local"] == original["mcp"]["servers"]["prefect_local"]
