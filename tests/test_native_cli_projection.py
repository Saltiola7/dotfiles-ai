"""Private analytics retain the retired adapter's bounded output boundary."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def core():
    source = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
    loader = importlib.machinery.SourceFileLoader("cli_projection", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_safe_metadata_reaches_stdout(core, capsys):
    core.agent_analytics_output(lambda: print(json.dumps({"schema_version": 1, "count": 2})))
    assert json.loads(capsys.readouterr().out)["count"] == 2


@pytest.mark.parametrize("payload", [
    '{"extra":"/Users/private/history"}', '{"extra":"https://private.invalid/body"}',
    '{"extra":"-----BEGIN PRIVATE KEY-----"}', '{"extra":"\\u002fUsers/private/history"}',
    '{"a":1,"a":2}', '[]', 'not JSON', '{"extra":"' + "x" * (256 * 1024) + '"}',
    '{"body":"PRIVATE_BODY_SENTINEL"}', '{"nested":{"messages":["PRIVATE_BODY_SENTINEL"]}}',
    '{"extra":"Bearer SYNTHETIC_CREDENTIAL"}', '{"extra":"api_key=SYNTHETIC_CREDENTIAL"}',
    '{"extra":"\\u0042earer SYNTHETIC_CREDENTIAL"}',
    '{"nested":{"credentials":"SYNTHETIC_CREDENTIAL"}}',
    '{"Body":"PRIVATE_BODY_SENTINEL"}', '{"nested":{"Credentials":"SYNTHETIC_CREDENTIAL"}}',
    '{"count":NaN}', '{"count":Infinity}', '{"count":1e309}',
])
def test_unsafe_or_unbounded_analytics_are_withheld(core, capsys, payload):
    with pytest.raises(RuntimeError, match="analytics projection"):
        core.agent_analytics_output(lambda: print(payload))
    assert capsys.readouterr().out == ""


def test_partial_output_and_exception_body_are_withheld(core, capsys):
    def broken():
        print('{"partial":')
        raise RuntimeError("PRIVATE_FAILURE_SENTINEL")
    with pytest.raises(RuntimeError) as error:
        core.agent_analytics_output(broken)
    assert "PRIVATE_FAILURE_SENTINEL" not in str(error.value)
    assert capsys.readouterr().out == ""


def test_private_stderr_is_not_forwarded(core, capsys):
    def broken():
        print("PRIVATE_STDERR_SENTINEL", file=core.sys.stderr)
        print('{"count": 1}')
    with pytest.raises(RuntimeError, match="analytics projection"):
        core.agent_analytics_output(broken)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("arguments", [
    ["incident-scan", "--session-id", "forged-fork"],
    ["incident-register", "--session-id", "forged-fork", "--message-id", "forged-message",
     "--kind", "defect", "--title", "INCIDENT: fixture", "--summary", "fixture"],
    ["incident-update", "--session-id", "forged-fork", "--message-id", "forged-message",
     "--incident-id", "incident-fixture", "--state", "investigating"],
    ["incident-forget", "--session-id", "forged-fork", "--message-id", "forged-message",
     "--incident-id", "incident-fixture"],
])
def test_native_incident_cli_refuses_identity_claims_before_private_access(core, tmp_path, arguments):
    database = tmp_path / "history.db"
    database.write_bytes(b"SYNTHETIC_PRIVATE_HISTORY")
    state = tmp_path / "state"
    result = core.subprocess.run(
        [core.sys.executable, core.__file__, *arguments, "--database", str(database), "--state-root", str(state)],
        cwd=tmp_path, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 1
    assert "native_incident_invocation_unavailable" in result.stderr
    assert not result.stdout and "SYNTHETIC_PRIVATE_HISTORY" not in result.stderr
    assert database.read_bytes() == b"SYNTHETIC_PRIVATE_HISTORY"
    assert not state.exists()


@pytest.mark.parametrize("arguments", [
    ["improvement-register", "--worker-id", "worker-fixture", "--session-id", "forged-session"],
    ["improvement-claim", "--worker-id", "worker-fixture", "--session-id", "forged-session", "--summary", "fixture"],
    ["improvement-update", "--worker-id", "worker-fixture", "--state", "blocked"],
    ["improvement-recover", "--worker-id", "worker-fixture", "--action", "retry"],
])
def test_worker_cli_cannot_authenticate_caller_supplied_identity(core, tmp_path, arguments):
    state = tmp_path / "state"
    result = core.subprocess.run(
        [core.sys.executable, core.__file__, *arguments, "--state-root", str(state)],
        cwd=tmp_path, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 1
    assert "native_automation_identity_unavailable" in result.stderr
    assert not result.stdout and not state.exists()


def test_federated_save_requires_qualified_capture_authority(core, tmp_path):
    state = tmp_path / "state"
    result = core.subprocess.run(
        [core.sys.executable, core.__file__, "provider-evaluation-save", "--receipt-json", "-",
         "--report-json", "{}", "--state-root", str(state)],
        input="SYNTHETIC_UNTRUSTED_RECEIPT", cwd=tmp_path, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 1 and "native_capture_authority_unavailable" in result.stderr
    assert not result.stdout and "SYNTHETIC_UNTRUSTED_RECEIPT" not in result.stderr
    assert not state.exists()


def test_inventory_errors_and_cursor_input_do_not_disclose_paths(core, tmp_path):
    root = tmp_path / "PRIVATE_PROJECT_SENTINEL"
    root.mkdir()
    core.subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    for arguments in (["--cursor", "PRIVATE_CURSOR_SENTINEL"],
                      ["--repository", "PRIVATE_RELATIVE_SENTINEL"]):
        result = core.subprocess.run(
            [core.sys.executable, core.__file__, "worktree-list", "--json", *arguments],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert result.stderr.strip() == "dbsctrctl: inventory_unavailable"
        assert not result.stdout


def test_inventory_subprocess_budget_withholds_untrusted_git_output(core, tmp_path, monkeypatch):
    fake = tmp_path / "git"
    fake.write_text("#!/bin/sh\nprintf 'PRIVATE_ERROR_SENTINEL' >&2\nexit 1\n")
    fake.chmod(0o700)
    monkeypatch.setattr(core, "INSPECT_ENV", {**core.INSPECT_ENV, "PATH": str(tmp_path)})
    with pytest.raises(RuntimeError, match="inventory_git_unavailable") as error:
        core.inventory_git(tmp_path, "rev-parse", "HEAD")
    assert "PRIVATE" not in str(error.value)


def test_inventory_timeout_terminates_only_its_spawned_collector(core, tmp_path):
    child = core.subprocess.Popen(
        [core.sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=core.subprocess.PIPE, stderr=core.subprocess.PIPE, start_new_session=True,
    )
    with pytest.raises(RuntimeError, match="preservation evidence unavailable"):
        core.preservation_output(child, limit=1024, timeout=0.01)
    assert child.poll() is not None
    assert child.stdout.closed and child.stderr.closed
