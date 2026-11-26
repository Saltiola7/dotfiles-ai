"""Offline tests of the Linux service's read-only Forgejo credential boundary."""

import base64
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import time

import pytest


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
IDENTITY = {
    "provider": "forgejo",
    "origin": "https://forge.example.invalid:8443",
    "repository": "example/private-config",
}
ACCOUNT = "fixture-user"
TOKEN = "INERT_FIXTURE_TOKEN"
CREDENTIAL_NAME = "dbsctr-forgejo"
REQUEST = (
    "capability[]=authtype\nauthtype=basic\nprotocol=https\nhost=forge.example.invalid:8443\n"
    "path=example/private-config.git\nusername=fixture-user\n\n"
)


@pytest.fixture
def helper():
    loader = importlib.machinery.SourceFileLoader("fixture_forgejo_systemd", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    helper = importlib.util.module_from_spec(spec)
    loader.exec_module(helper)
    return helper


@pytest.fixture
def credential(helper, monkeypatch, tmp_path):
    monkeypatch.setattr(helper, "_forgejo_systemd_directory", lambda: tmp_path)
    path = tmp_path / CREDENTIAL_NAME
    envelope = {
        "schema_version": 1,
        "origin": IDENTITY["origin"],
        "repository": IDENTITY["repository"],
        "account": ACCOUNT,
        "role": "read",
        "expires_at": int(time.time()) + 3600,
        "token": TOKEN,
    }
    return path, envelope


def write(path, payload, mode=0o400):
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
    path.write_bytes(payload)
    path.chmod(mode)


def write_get_request(helper, monkeypatch, request=REQUEST):
    monkeypatch.setattr(helper.sys, "stdin", io.StringIO(request))


def unexpected_lookup(*_args, **_kwargs):
    pytest.fail("unexpected credential lookup")


def assert_redacted_refusal(helper, capsys):
    with pytest.raises(RuntimeError) as error:
        helper._forgejo_systemd_password(IDENTITY, ACCOUNT)
    captured = capsys.readouterr()
    assert TOKEN not in str(error.value)
    assert "PRIVATE_PATH_SENTINEL" not in str(error.value)
    assert captured.out == captured.err == ""


def test_systemd_get_only_emits_exact_ephemeral_basic_match(helper, credential, monkeypatch, capsys):
    path, envelope = credential
    write(path, envelope)
    monkeypatch.setattr(helper, "_forgejo_security_lookup", unexpected_lookup)
    write_get_request(helper, monkeypatch)
    helper.forgejo_credential_helper("get", IDENTITY, ACCOUNT, credential_source="systemd")
    output = capsys.readouterr()
    encoded = base64.b64encode(f"{ACCOUNT}:{TOKEN}".encode()).decode("ascii")
    assert output.out == f"capability[]=authtype\nauthtype=basic\ncredential={encoded}\nephemeral=true\n\n"
    assert output.err == ""
    assert json.loads(path.read_bytes()) == envelope


@pytest.mark.parametrize("change", [
    {"schema_version": True},
    {"schema_version": 2},
    {"origin": "https://another.example.invalid"},
    {"repository": "example/another-repo"},
    {"account": "another-user"},
    {"role": "write"},
    {"expires_at": 1},
    {"expires_at": True},
    {"expires_at": 4_000_000_000.5},
    {"token": "INERT_FIXTURE_TOKEN\nextra"},
    {"unexpected": True},
], ids=[
    "bool-version", "other-version", "other-origin", "other-repo", "other-account", "write-role",
    "expired", "bool-expiry", "noninteger-expiry", "malformed-token", "extra-field",
])
def test_systemd_envelope_must_match_identity_and_expiry(helper, credential, capsys, change):
    path, envelope = credential
    write(path, envelope | change)
    assert_redacted_refusal(helper, capsys)


@pytest.mark.parametrize("problem", ["missing-field", "duplicate", "invalid-json", "oversized"])
def test_systemd_bounded_envelope_rejects_incomplete_or_ambiguous_input(helper, credential, capsys, problem):
    path, envelope = credential
    if problem == "missing-field":
        del envelope["token"]
        write(path, envelope)
    elif problem == "duplicate":
        raw = json.dumps(envelope)[:-1] + ",\"token\":" + json.dumps(TOKEN) + "}"
        write(path, raw.encode())
    elif problem == "invalid-json":
        write(path, b'{"token":"INERT_FIXTURE_TOKEN"')
    else:
        write(path, b" " * (16 * 1024 + 1))
    assert_redacted_refusal(helper, capsys)


@pytest.mark.parametrize("problem", ["missing", "mode", "symlink", "hardlink", "directory"])
def test_systemd_named_credential_requires_private_regular_single_link(helper, credential, capsys, problem):
    path, envelope = credential
    if problem == "mode":
        write(path, envelope, mode=0o600)
    elif problem == "symlink":
        other = path.with_name("PRIVATE_PATH_SENTINEL")
        write(other, envelope)
        path.symlink_to(other)
    elif problem == "hardlink":
        write(path, envelope)
        os.link(path, path.with_name("PRIVATE_PATH_SENTINEL"))
    elif problem == "directory":
        path.mkdir(mode=0o700)
    assert_redacted_refusal(helper, capsys)


def test_systemd_file_must_belong_to_current_user(helper, credential, monkeypatch, capsys):
    path, envelope = credential
    write(path, envelope)
    monkeypatch.setattr(helper.os, "getuid", lambda: path.stat().st_uid + 1)
    assert_redacted_refusal(helper, capsys)



def test_systemd_open_errors_are_redacted(helper, credential, monkeypatch, capsys):
    path, envelope = credential
    write(path, envelope)

    def denied(*_args, **_kwargs):
        raise OSError(f"PRIVATE_PATH_SENTINEL {TOKEN}")

    with monkeypatch.context() as scoped:
        scoped.setattr(helper.os, "open", denied)
        assert_redacted_refusal(helper, capsys)


@pytest.mark.parametrize("directory", [
    None, "relative/PRIVATE_PATH_SENTINEL", "/tmp/PRIVATE_PATH_SENTINEL", "/run/credentials/../PRIVATE_PATH_SENTINEL",
])
def test_systemd_directory_refuses_missing_or_unbound_service_location(helper, monkeypatch, directory):
    if directory is None:
        monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    else:
        monkeypatch.setenv("CREDENTIALS_DIRECTORY", directory)
    with pytest.raises(RuntimeError) as error:
        helper._forgejo_systemd_directory()
    assert "PRIVATE_PATH_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("request_text", [
    REQUEST.replace("protocol=https", "protocol=http"),
    REQUEST.replace("host=forge.example.invalid:8443", "host=forge.example.invalid"),
    REQUEST.replace("path=example/private-config.git", "path=example/other.git"),
    REQUEST.replace("username=fixture-user", "username=someone-else"),
    REQUEST.replace("authtype=basic", "authtype=bearer"),
    REQUEST.replace("capability[]=authtype\n", ""),
])
def test_systemd_get_checks_git_request_before_selecting_credential(helper, monkeypatch, capsys, request_text):
    monkeypatch.setattr(helper, "_forgejo_systemd_password", unexpected_lookup)
    monkeypatch.setattr(helper, "_forgejo_security_lookup", unexpected_lookup)
    write_get_request(helper, monkeypatch, request_text)
    with pytest.raises(RuntimeError):
        helper.forgejo_credential_helper("get", IDENTITY, ACCOUNT, credential_source="systemd")
    output = capsys.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("operation", ["store", "erase", "unknown"])
def test_systemd_non_get_does_not_lookup_or_modify_credentials(helper, credential, monkeypatch, capsys, operation):
    path, envelope = credential
    write(path, envelope)
    before = path.read_bytes()
    monkeypatch.setattr(helper, "_forgejo_systemd_password", unexpected_lookup)
    monkeypatch.setattr(helper, "_forgejo_security_lookup", unexpected_lookup)
    write_get_request(helper, monkeypatch, REQUEST + "password=" + TOKEN)
    helper.forgejo_credential_helper(operation, IDENTITY, ACCOUNT, credential_source="systemd")
    output = capsys.readouterr()
    assert output.out == output.err == ""
    assert path.read_bytes() == before


def test_internal_systemd_get_refuses_without_exposing_credential_or_os_home(helper, credential, monkeypatch, capsys):
    import pwd

    path, envelope = credential
    write(path, envelope | {"role": "write"})
    write_get_request(helper, monkeypatch)
    monkeypatch.setattr(pwd, "getpwuid", unexpected_lookup)
    monkeypatch.setattr(helper, "_forgejo_security_lookup", unexpected_lookup)
    assert helper.forgejo_internal_main([
        "_forgejo-credential", "--identity-json", json.dumps(IDENTITY), "--account", ACCOUNT,
        "--credential-source", "systemd", "get",
    ])
    output = capsys.readouterr()
    assert output.out == "quit=true\n\n"
    assert output.err == ""


@pytest.mark.parametrize("source", ["systemd", "osxkeychain"])
def test_only_selected_network_fetch_inherits_systemd_credential_directory(source, request, monkeypatch, tmp_path):
    import subprocess
    import test_dbsctr_forgejo_transport as transport

    fixture = transport.ForgejoTransportTest()
    request.addfinalizer(fixture.doCleanups)
    fixture.setUp()
    original = fixture.core._forgejo_run
    directory = tmp_path / "PRIVATE_PATH_SENTINEL"
    directory.mkdir()
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(directory))
    selected = directory if source == "systemd" else None
    monkeypatch.setattr(fixture.core, "_forgejo_systemd_directory",
                        (lambda: directory) if selected is not None else unexpected_lookup)
    observations = []

    def offline(command, **kwargs):
        environment = kwargs["env"]
        if "fetch" not in command:
            assert "CREDENTIALS_DIRECTORY" not in environment
            return original(command, **kwargs)
        observations.append(environment.get("CREDENTIALS_DIRECTORY"))
        assert kwargs["cwd"].name == "control.git"
        assert environment["GIT_ALLOW_PROTOCOL"] == "https"
        assert str(directory) not in repr(command)
        if source == "systemd":
            assert any("--credential-source systemd" in item for item in command)
        clean = {key: value for key, value in environment.items() if key != "CREDENTIALS_DIRECTORY"}
        ref = command[-1].split(":", 1)[1]
        original([fixture.git, "update-ref", ref, fixture.head], cwd=kwargs["cwd"], env=clean, timeout=5)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(fixture.core, "_forgejo_run", offline)
    assert fixture.core.fetch_forgejo_branch(
        fixture.root, "origin", IDENTITY, "main", ACCOUNT, credential_source=source,
    ) == fixture.head
    assert observations == [str(selected) if selected is not None else None]


def test_managed_entrypoint_keeps_locator_out_of_ordinary_children(helper, monkeypatch):
    import subprocess

    locator = "/run/user/1000/credentials/example.service"
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", locator)
    for environment in (helper.GIT_REPOSITORY_ENV, helper.INSPECT_ENV):
        monkeypatch.setitem(environment, "CREDENTIALS_DIRECTORY", locator)
    monkeypatch.setattr(helper.sys, "argv", ["dbsctrctl", "initiative-auto", "resume", "a" * 64])

    def managed_command(_args):
        assert helper.FORGEJO_SYSTEMD_LOCATOR.get() == locator
        for environment in (os.environ, helper.GIT_REPOSITORY_ENV, helper.INSPECT_ENV):
            assert "CREDENTIALS_DIRECTORY" not in environment
        result = subprocess.run(
            [helper.sys.executable, "-I", "-c", "import os; assert 'CREDENTIALS_DIRECTORY' not in os.environ"],
            capture_output=True, timeout=5, check=False,
        )
        assert result.returncode == 0

    monkeypatch.setattr(helper, "command_initiative_auto", managed_command)
    assert helper.main() == 0
    assert helper.FORGEJO_SYSTEMD_LOCATOR.get() is None
    for environment in (os.environ, helper.GIT_REPOSITORY_ENV, helper.INSPECT_ENV):
        assert environment["CREDENTIALS_DIRECTORY"] == locator
