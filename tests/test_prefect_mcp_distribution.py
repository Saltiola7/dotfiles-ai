"""Optional Prefect installation keeps package, target and client owners distinct."""

import json
import subprocess
import tomllib

from test_portable_distribution import ROOT, chezmoi, data


RUNTIME = ROOT / "private_dot_config/dotfiles-ai/runtime/prefect-mcp"


def test_prefect_defaults_and_private_config_have_no_ambient_target():
    defaults = tomllib.loads((ROOT / ".chezmoidata.toml").read_text())["dotfiles_ai"]["prefect_mcp"]
    assert defaults["enabled"] is False
    assert not any(value for key, value in defaults.items() if key != "enabled")
    template = ROOT / "private_dot_config/dotfiles-ai/private_prefect-mcp.toml.tmpl"
    rendered = chezmoi("execute-template", template=template.read_text()).stdout
    config = tomllib.loads(rendered)
    assert config == {"schema_version": 1, **defaults}


def test_prefect_disabled_installer_has_no_command_or_filesystem_effects(tmp_path):
    source = ROOT / "run_onchange_after_install-prefect-mcp.sh.tmpl"
    rendered = chezmoi("execute-template", template=source.read_text()).stdout
    subprocess.run(["/bin/bash", "-n"], input=rendered, text=True, check=True)
    result = subprocess.run(["/bin/bash"], input=rendered, text=True, capture_output=True,
                            env={"PATH": "/unavailable", "HOME": str(tmp_path)}, timeout=5)
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


def test_prefect_installer_only_calls_explicit_owner(tmp_path):
    configured = data()
    configured["dotfiles_ai"]["prefect_mcp"] = {"enabled": True}
    source = ROOT / "run_onchange_after_install-prefect-mcp.sh.tmpl"
    command = ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
               "--override-data", json.dumps(configured), "execute-template"]
    rendered = subprocess.run(command, input=source.read_text(), text=True, capture_output=True, check=True).stdout
    executable = tmp_path / ".local/bin/prefect-mcp"
    executable.parent.mkdir(parents=True)
    executable.write_text('#!/bin/sh\n[ "$#" = 1 ] && [ "$1" = install ] || exit 88\nexit 37\n')
    executable.chmod(0o700)
    result = subprocess.run(["/bin/bash"], input=rendered, text=True, capture_output=True,
                            env={"PATH": "/unavailable", "HOME": str(tmp_path)}, timeout=5)
    assert result.returncode == 37


def test_prefect_runtime_pins_source_api_and_isolated_build_closure():
    project = tomllib.loads((RUNTIME / "pyproject.toml").read_text())
    assert project["project"]["requires-python"] == ">=3.13,<3.14"
    assert project["tool"]["uv"]["package"] is False
    assert project["tool"]["uv"]["require-build-hashes"] is True
    source = project["tool"]["uv"]["sources"]["prefect-mcp"]
    assert source == {"git": "https://github.com/PrefectHQ/prefect-mcp-server.git",
                      "rev": "48efd289bdb2b94a78e35b1331fbefc4fa3f6411"}
    constraints = project["tool"]["uv"]["build-constraint-dependencies"]
    assert {item["requirement"].split("==")[0] for item in constraints} >= {
        "hatchling", "hatch-vcs", "setuptools-scm", "setuptools", "vcs-versioning",
        "packaging", "pathspec", "pluggy", "trove-classifiers", "tomlkit"}
    assert all("==" in item["requirement"] and item["hashes"] for item in constraints)
    lock = tomllib.loads((RUNTIME / "uv.lock").read_text())
    packages = {item["name"]: item for item in lock["package"]}
    assert packages["fastmcp"]["version"] == "3.4.11"
    assert packages["mcp"]["version"] == "1.30.0"
    assert packages["prefect"]["version"] == "3.7.1"
    assert source["rev"] in packages["prefect-mcp"]["source"]["git"]
    assert "docs-mcp-server" not in packages and "ingestion-pipeline" not in packages


def test_prefect_mcp_does_not_expand_codex_managed_config_ownership():
    config = tomllib.loads((ROOT / "private_dot_config/dotfiles-ai/codex-managed/config.toml").read_text())
    assert set(config) == {"hooks"}
