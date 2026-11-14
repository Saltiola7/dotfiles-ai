"""Explicit qualified-Git protocol tests, separate from offline lifecycle tests.

Run: uv run --frozen --group test pytest tests/forgejo_native_transport.py -q -s
Requires the production selector to find Git >=2.56 with authtype capability.
No skip/fallback, installer, network request, Keychain lookup or real credential.
This is native Git/credential-protocol evidence, not live Forgejo qualification.
"""
import base64
import json
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from test_dbsctr_forgejo_transport import IDENTITY, SCRIPT, load_core, native_git_metadata


@pytest.fixture
def qualified_git():
    core = load_core()
    report = native_git_metadata(core)
    print(json.dumps(report, sort_keys=True))
    assert report["tools"] is not None, (
        "Native transport requires qualified Git; production guard is unchanged",
        report["error"],
    )
    return core, report["tools"]


def test_native_selected_git_meets_production_capability_guard(qualified_git):
    core, (executable, exec_path) = qualified_git
    assert Path(executable).is_absolute() and Path(exec_path).is_absolute()
    assert core._forgejo_tools() == (executable, exec_path)


def test_native_git_basic_protocol_uses_only_synthetic_credentials(qualified_git, tmp_path):
    core, (executable, exec_path) = qualified_git
    helper = tmp_path / "credential_fixture.py"
    helper.write_text(
        "import importlib.machinery, importlib.util, json, sys\n"
        "loader = importlib.machinery.SourceFileLoader('credential_fixture', sys.argv[1])\n"
        "spec = importlib.util.spec_from_loader(loader.name, loader)\n"
        "core = importlib.util.module_from_spec(spec)\n"
        "loader.exec_module(core)\n"
        "identity = json.loads(sys.argv[2])\n"
        "def synthetic_lookup(query):\n"
        "    assert query['server'] == 'forge.example.invalid'\n"
        "    assert query['port'] == 8443\n"
        "    assert query['account'] == 'fixture-user'\n"
        "    assert query['path'] == 'example/private-config.git'\n"
        "    return [{**query, 'password': 'SYNTHETIC_PROTOCOL_TOKEN'}]\n"
        "core._forgejo_security_lookup = synthetic_lookup\n"
        "core.forgejo_credential_helper(sys.argv[3], identity, 'fixture-user')\n"
    )
    command = "!" + shlex.join([
        sys.executable, "-I", "-S", "-B", str(helper), str(SCRIPT), json.dumps(IDENTITY),
    ])
    home = tmp_path / "home"
    home.mkdir()
    environment = {**core._forgejo_environment(home), "GIT_EXEC_PATH": exec_path}
    result = subprocess.run([
        executable, "-c", "credential.helper=", "-c", "credential.helper=" + command,
        "-c", "credential.useHttpPath=true", "-c", "credential.username=fixture-user",
        "credential", "fill",
    ], input="capability[]=authtype\nprotocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\n\n",
        text=True, capture_output=True, env=environment, cwd=tmp_path, timeout=15)
    assert result.returncode == 0, result.stderr
    expected = base64.b64encode(b"fixture-user:SYNTHETIC_PROTOCOL_TOKEN").decode("ascii")
    assert "authtype=basic\n" in result.stdout
    assert "credential=" + expected + "\n" in result.stdout
    assert "SYNTHETIC_PROTOCOL_TOKEN" not in result.stderr
