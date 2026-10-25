"""Dagger execution preserves pinned inputs and reports capability gaps honestly."""

import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).parents[1] / "private_dot_config/dotfiles-ai/continuous_validation/dagger_backend.py"
IMAGE = "ghcr.io/astral-sh/uv:0.12.23-python3.12-bookworm-slim@sha256:" + "a" * 64


@pytest.fixture
def backend():
    spec = importlib.util.spec_from_file_location("continuous_validation_dagger", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def job(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.1'\n")
    (snapshot / "uv.lock").write_text("version = 1\n")
    return {
        "schema_version": 1,
        "snapshot": str(snapshot),
        "base": "a" * 40,
        "trigger": "checkpoint",
        "check": {
            "id": "pytest",
            "class": "expensive",
            "backend": "dagger",
            "lane": {"os": "linux", "architecture": "arm64", "python": "3.12", "tools": {}, "dependencies": {}},
            "timeout_seconds": 30,
            "cacheable": False,
            "configuration": {
                "argv": ["uv", "run", "--frozen", "--no-sync", "pytest", "-q"],
                "platform": "linux/arm64",
                "image": IMAGE,
                "python_version": "3.12.12",
                "uv_version": "0.12.23",
                "groups": ["test"],
                "engine": "unix:///tmp/fixture-dagger.sock",
            },
        },
        "log_path": str(tmp_path / "logs" / "pytest.log"),
    }


class FakeExecError(Exception):
    exit_code = 17
    stdout = "PRIVATE_COMMAND_OUTPUT"
    stderr = "Bearer PRIVATE_SECRET"


class FakeContainer:
    def __init__(self, client):
        self.client = client
        self.command = None

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.client.calls.append((name, args, kwargs))
            if name == "with_exec":
                self.command = args[0]
            return self
        return call

    async def stdout(self):
        if self.command == ["python", "-c", "import platform; print(platform.python_version())"]:
            return self.client.python_version
        if self.command == ["uv", "--version"]:
            return "uv " + self.client.uv_version
        return "PRIVATE_TEST_OUTPUT"

    async def stderr(self):
        return "PRIVATE_TEST_STDERR"

    async def sync(self):
        if self.client.setup_failure and self.command[:2] == ["uv", "sync"]:
            raise FakeExecError("PRIVATE_SETUP_ERROR")
        return self

    async def exit_code(self):
        if self.client.execution_error:
            raise FakeExecError("PRIVATE_EXEC_ERROR")
        return self.client.code


class FakeClient:
    def __init__(self):
        self.calls = []
        self.python_version = "3.12.12"
        self.uv_version = "0.12.23"
        self.engine_version = "v0.21.10"
        self.engine_platform = "linux/arm64"
        self.code = 0
        self.setup_failure = False
        self.execution_error = False

    async def version(self):
        return self.engine_version

    async def default_platform(self):
        return self.engine_platform

    def host(self):
        client = self
        class Host:
            def directory(self, path, **kwargs):
                client.calls.append(("host.directory", (path,), kwargs))
                return object()
        return Host()

    def container(self, **kwargs):
        self.calls.append(("container", (), kwargs))
        return FakeContainer(self)

    def cache_volume(self, key):
        cache = object()
        self.calls.append(("cache_volume", (key,), {"cache": cache}))
        return cache


@pytest.fixture
def sdk(backend, monkeypatch):
    client = FakeClient()
    environments = []

    class Connection:
        def __init__(self, config):
            environments.append(dict(backend.os.environ))
        async def __aenter__(self):
            return client
        async def __aexit__(self, *_):
            return None

    fake = SimpleNamespace(
        Connection=Connection,
        Config=lambda **kwargs: kwargs,
        Timeout=lambda *args, **kwargs: (args, kwargs),
        Retry=lambda **kwargs: kwargs,
        Platform=str,
        ReturnType=SimpleNamespace(ANY="ANY"),
        ExecError=FakeExecError,
    )
    monkeypatch.setattr(backend, "_load_sdk", lambda: fake)
    monkeypatch.setattr(backend, "_probe_cli", lambda: ("/fixture/dagger", "0.21.10"))
    return client, environments


def run(backend, job, **kwargs):
    return asyncio.run(backend.execute(job, **kwargs))


def test_disabled_backend_does_not_probe_or_load(backend, job, monkeypatch):
    def forbidden():
        raise AssertionError("disabled shadow must not touch execution capabilities")
    monkeypatch.setattr(backend, "_probe_cli", forbidden)
    monkeypatch.setattr(backend, "_load_sdk", forbidden)
    result = run(backend, job)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["shadow_disabled"]


def test_missing_cli_reports_unavailable_without_sdk(backend, job, monkeypatch):
    monkeypatch.setattr(backend, "_probe_cli", lambda: None)
    monkeypatch.setattr(backend, "_load_sdk", lambda: pytest.fail("must not load SDK"))
    assert run(backend, job, enabled=True)["diagnostic_codes"] == ["dagger_cli_unavailable"]


def test_cli_probe_timeout_does_not_expose_output(backend, job, monkeypatch):
    def broken():
        raise backend.subprocess.TimeoutExpired("PRIVATE_COMMAND", 5, "PRIVATE_OUTPUT")
    monkeypatch.setattr(backend, "_probe_cli", broken)
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("field,value", [("platform", "darwin/arm64"), ("image", "python:latest"),
    ("python_version", "3.12"), ("uv_version", "latest"), ("project_path", "../outside"),
    ("engine", "tcp://remote.invalid:1234"), ("engine", "docker-image://registry/engine"),
    ("argv", "pytest -q"), ("artifacts", ["../private"]), ("unknown", True)])
def test_unpinned_or_unsafe_configuration_never_connects(backend, job, monkeypatch, field, value):
    job["check"]["configuration"][field] = value
    monkeypatch.setattr(backend, "_probe_cli", lambda: pytest.fail("invalid inputs must fail first"))
    assert run(backend, job, enabled=True)["diagnostic_codes"] == ["dagger_configuration_invalid"]


def test_native_macos_check_cannot_enter_linux_backend(backend, job, monkeypatch):
    job["check"]["lane"]["os"] = "darwin"
    monkeypatch.setattr(backend, "_probe_cli", lambda: pytest.fail("native lane must fail first"))
    assert run(backend, job, enabled=True)["diagnostic_codes"] == ["dagger_configuration_invalid"]


def test_sdk_pipeline_uses_snapshot_platform_pins_and_frozen_sync(backend, job, sdk):
    client, _ = sdk
    result = run(backend, job, enabled=True)
    assert result["status"] == "passed" and result["exit_code"] == 0
    assert ("container", (), {"platform": "linux/arm64"}) in client.calls
    assert ("from_", (IMAGE,), {}) in client.calls
    assert any(name == "host.directory" and args == (job["snapshot"],) for name, args, _ in client.calls)
    commands = [args[0] for name, args, _ in client.calls if name == "with_exec"]
    assert commands[-2:] == [["uv", "sync", "--frozen", "--group", "test"], job["check"]["configuration"]["argv"]]
    assert result["runtime"]["python"] == "3.12.12"
    assert result["runtime"]["engine_version"] == "0.21.10"
    assert result["runtime"]["cache"] == "unavailable"
    assert "PRIVATE_TEST_OUTPUT" not in json.dumps(result)
    assert Path(job["log_path"]).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("change", ["source", "lock", "project_policy", "uv_policy", "image", "python", "uv", "platform", "groups", "project_path"])
def test_uv_package_cache_identity_binds_dependency_runtime_policy(backend, job, sdk, change):
    client, _ = sdk
    assert run(backend, job, enabled=True)["status"] == "passed"
    cache_calls = [args[0] for name, args, _ in client.calls if name == "cache_volume"]
    assert len(cache_calls) == 1
    original_key = cache_calls[0]
    snapshot = Path(job["snapshot"])
    config = job["check"]["configuration"]
    if change == "source":
        (snapshot / "changed_source.py").write_text("value = 2\n")
    elif change == "lock":
        (snapshot / "uv.lock").write_text("version = 1\nrevision = 1\n")
    elif change == "project_policy":
        (snapshot / "pyproject.toml").write_text("[project]\nname='different-project'\nversion='0.1'\n")
    elif change == "uv_policy":
        (snapshot / "uv.toml").write_text("compile-bytecode = true\n")
    elif change == "image":
        config["image"] = IMAGE.rsplit("@", 1)[0] + "@sha256:" + "b" * 64
    elif change == "python":
        client.python_version = config["python_version"] = "3.12.13"
    elif change == "uv":
        client.uv_version = config["uv_version"] = "0.12.24"
    elif change == "platform":
        client.engine_platform = config["platform"] = "linux/amd64"
        job["check"]["lane"]["architecture"] = "amd64"
    elif change == "groups":
        config["groups"] = ["another-group"]
    else:
        project = snapshot / "subproject"
        project.mkdir()
        for name in ("pyproject.toml", "uv.lock"):
            (project / name).write_bytes((snapshot / name).read_bytes())
        config["project_path"] = "subproject"
    client.calls.clear()
    result = run(backend, job, enabled=True)
    assert result["status"] == "passed"
    current_key = next(args[0] for name, args, _ in client.calls if name == "cache_volume")
    assert (current_key == original_key) is (change == "source")
    assert result["runtime"]["cache"] == "unavailable"


def test_uv_cache_mount_does_not_share_source_or_project_environment(backend, job, sdk):
    client, _ = sdk
    assert run(backend, job, enabled=True)["status"] == "passed"
    mounts = [(args, kwargs) for name, args, kwargs in client.calls if name == "with_mounted_cache"]
    assert len(mounts) == 1 and mounts[0][0][0] == "/root/.cache/uv"
    cache = next(kwargs["cache"] for name, _, kwargs in client.calls if name == "cache_volume")
    assert mounts[0][0][1] is cache
    assert ("with_env_variable", ("UV_CACHE_DIR", "/root/.cache/uv"), {}) in client.calls
    assert ("with_env_variable", ("UV_LINK_MODE", "copy"), {}) in client.calls
    sync_index = next(i for i, (name, args, _) in enumerate(client.calls) if name == "with_exec" and args[0][:2] == ["uv", "sync"])
    mount_index = next(i for i, (name, _, _) in enumerate(client.calls) if name == "with_mounted_cache")
    assert mount_index < sync_index


@pytest.mark.parametrize("generated", [".venv", "package/.venv", "package/__pycache__", "package/node_modules", "lib/src/fixture.egg-info"])
def test_generated_host_runtime_is_excluded_from_symlink_validation_and_import(backend, job, sdk, tmp_path, generated):
    client, _ = sdk
    snapshot = Path(job["snapshot"])
    outside = tmp_path / "host-runtime"
    outside.mkdir()
    (outside / "python").write_text("host platform executable\n")
    directory = snapshot / generated
    directory.mkdir(parents=True)
    (directory / "host-python").symlink_to(outside / "python")
    if generated.endswith("fixture.egg-info"):
        job["check"]["configuration"]["source_excludes"] = [generated + "/**"]
    result = run(backend, job, enabled=True)
    assert result["status"] == "passed"
    options = next(kwargs for name, _, kwargs in client.calls if name == "host.directory")
    assert options["gitignore"] is False
    assert generated in options["exclude"] or "**/" + directory.name in options["exclude"]
    assert ".git" not in options["exclude"]


def test_ordinary_source_symlink_escape_still_refuses_before_sdk_import(backend, job, sdk, tmp_path):
    client, _ = sdk
    outside = tmp_path / "private-source.py"
    outside.write_text("must never import\n")
    (Path(job["snapshot"]) / "source.py").symlink_to(outside)
    result = run(backend, job, enabled=True)
    assert result["diagnostic_codes"] == ["dagger_snapshot_unavailable"]
    assert not any(name == "host.directory" for name, _, _ in client.calls)


@pytest.mark.parametrize("pattern,directory", [
    ("lib/src/fixture.egg-info/**", "unrelated/lib/src/fixture.egg-info"),
    ("lib/*/fixture.egg-info/**", "lib/deeper/nested/fixture.egg-info"),
])
def test_source_exclusion_cannot_prune_unrelated_suffix_or_cross_components(backend, job, sdk, tmp_path, pattern, directory):
    client, _ = sdk
    outside = tmp_path / "host-python"
    outside.write_text("host runtime must not import\n")
    target = Path(job["snapshot"]) / directory
    target.mkdir(parents=True)
    (target / "python").symlink_to(outside)
    job["check"]["configuration"]["source_excludes"] = [pattern]
    result = run(backend, job, enabled=True)
    assert result["diagnostic_codes"] == ["dagger_snapshot_unavailable"]
    assert not any(name == "host.directory" for name, _, _ in client.calls)


@pytest.mark.parametrize("excludes", [["../source"], ["/absolute"], ["!source/**"], [""], ["source\\escape"], "source/**"])
def test_source_exclusions_require_safe_explicit_relative_globs(backend, job, monkeypatch, excludes):
    job["check"]["configuration"]["source_excludes"] = excludes
    monkeypatch.setattr(backend, "_probe_cli", lambda: pytest.fail("invalid policy must fail before CLI"))
    assert run(backend, job, enabled=True)["diagnostic_codes"] == ["dagger_configuration_invalid"]


@pytest.mark.parametrize("attribute,value,code", [
    ("engine_version", "v0.21.9", "dagger_engine_version_mismatch"),
    ("engine_platform", "linux/amd64", "dagger_native_platform_unavailable"),
    ("python_version", "3.12.11", "dagger_python_version_mismatch"),
    ("uv_version", "0.12.22", "dagger_uv_version_mismatch"),
])
def test_runtime_mismatch_never_runs_test_command(backend, job, sdk, attribute, value, code):
    client, _ = sdk
    setattr(client, attribute, value)
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable" and result["diagnostic_codes"] == [code]
    assert not any(name == "with_exec" and args[0] == job["check"]["configuration"]["argv"] for name, args, _ in client.calls)


def test_failed_check_keeps_failure_and_hides_raw_logs(backend, job, sdk):
    client, _ = sdk
    client.code = 5
    result = run(backend, job, enabled=True)
    assert result["status"] == "failed" and result["exit_code"] == 5
    assert result["diagnostic_codes"] == ["dagger_check_failed"]
    assert "PRIVATE" not in json.dumps(result)


def test_dependency_setup_error_is_not_a_failed_test_or_pass(backend, job, sdk):
    client, _ = sdk
    client.setup_failure = True
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["dagger_dependency_setup_failed"]
    assert "PRIVATE" not in json.dumps(result)


def test_sdk_execution_error_preserves_exit_code_without_exception_body(backend, job, sdk):
    client, _ = sdk
    client.execution_error = True
    result = run(backend, job, enabled=True)
    assert result["status"] == "failed" and result["exit_code"] == 17
    assert "PRIVATE" not in json.dumps(result)


def test_connection_environment_cannot_reuse_session_or_cloud_credentials(backend, job, sdk, monkeypatch):
    _, environments = sdk
    for key in ("DAGGER_CLOUD_TOKEN", "DAGGER_SESSION_PORT", "DAGGER_SESSION_TOKEN", "OTEL_EXPORTER_OTLP_ENDPOINT"):
        monkeypatch.setenv(key, "PRIVATE_SENTINEL")
    assert run(backend, job, enabled=True)["status"] == "passed"
    assert environments[0]["_EXPERIMENTAL_DAGGER_CLI_BIN"] == "/fixture/dagger"
    assert environments[0]["_EXPERIMENTAL_DAGGER_RUNNER_HOST"] == job["check"]["configuration"]["engine"]
    assert "PRIVATE_SENTINEL" not in json.dumps(environments)
    assert backend.os.environ["DAGGER_CLOUD_TOKEN"] == "PRIVATE_SENTINEL"


def test_connection_environment_uses_private_empty_registry_config_and_restores(backend, tmp_path, monkeypatch):
    host_config = tmp_path / "host-docker"
    host_config.mkdir()
    (host_config / "config.json").write_text('{"credsStore":"PRIVATE_HELPER"}')
    inherited = {
        "DOCKER_CONFIG": str(host_config), "DOCKER_AUTH_CONFIG": "PRIVATE_AUTH",
        "DOCKER_CONTEXT": "PRIVATE_CONTEXT", "DOCKER_HOST": "PRIVATE_HOST",
        "REGISTRY_AUTH_FILE": "PRIVATE_FILE", "REGISTRY_TOKEN": "PRIVATE_TOKEN",
        "CONTAINERS_AUTH_FILE": "PRIVATE_CONTAINER_FILE",
        "BUILDKIT_HOST": "PRIVATE_BUILDKIT", "BUILDX_CONFIG": "PRIVATE_BUILDX",
        "XDG_CONFIG_HOME": str(tmp_path / "host-configuration"),
        "DO_NOT_TRACK": "0",
        "SSH_AUTH_SOCK": "PRIVATE_AGENT", "SSH_AGENT_PID": "PRIVATE_PID",
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    previous = dict(backend.os.environ)
    with backend._connection_environment("/fixture/dagger", "unix:///fixture.sock"):
        private = Path(backend.os.environ["DOCKER_CONFIG"])
        assert private != host_config
        assert private.is_dir() and private.stat().st_mode & 0o777 == 0o700
        config = private / "config.json"
        assert config.stat().st_mode & 0o777 == 0o600
        assert json.loads(config.read_text()) == {"auths": {}}
        assert all(key not in backend.os.environ for key in inherited if key not in {"DOCKER_CONFIG", "XDG_CONFIG_HOME", "DO_NOT_TRACK"})
        configuration = Path(backend.os.environ["XDG_CONFIG_HOME"])
        assert configuration != Path(inherited["XDG_CONFIG_HOME"])
        assert configuration.is_dir() and configuration.stat().st_mode & 0o777 == 0o700
        assert not list(configuration.iterdir())
        assert backend.os.environ["DO_NOT_TRACK"] == "1"
        assert "PRIVATE_" not in json.dumps(dict(backend.os.environ))
    assert dict(backend.os.environ) == previous
    assert not private.exists()
    assert not configuration.exists()
    assert (host_config / "config.json").read_text() == '{"credsStore":"PRIVATE_HELPER"}'


def test_connection_environment_restores_and_removes_private_config_on_exception(backend, monkeypatch):
    monkeypatch.setenv("DOCKER_CONFIG", "/original/docker")
    previous = dict(backend.os.environ)
    with pytest.raises(RuntimeError, match="fixture failure"):
        with backend._connection_environment("/fixture/dagger", "unix:///fixture.sock"):
            private = Path(backend.os.environ["DOCKER_CONFIG"])
            raise RuntimeError("fixture failure")
    assert dict(backend.os.environ) == previous
    assert not private.exists()


def test_cli_version_probe_uses_same_private_auth_and_analytics_boundary(backend, monkeypatch):
    monkeypatch.setenv("DAGGER_CLOUD_TOKEN", "PRIVATE_TOKEN")
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", "PRIVATE_DOCKER")
    previous = dict(backend.os.environ)
    def probe(_argv, **kwargs):
        environment = kwargs["env"]
        assert environment["DO_NOT_TRACK"] == "1"
        assert "DAGGER_CLOUD_TOKEN" not in environment
        assert "DOCKER_AUTH_CONFIG" not in environment
        assert Path(environment["XDG_CONFIG_HOME"]).is_dir()
        assert json.loads((Path(environment["DOCKER_CONFIG"]) / "config.json").read_text()) == {"auths": {}}
        return SimpleNamespace(stdout="dagger v0.21.10", returncode=0)
    monkeypatch.setattr(backend.subprocess, "run", probe)
    assert backend._probe_binary("/fixture/dagger") == ("/fixture/dagger", "0.21.10")
    assert dict(backend.os.environ) == previous


def test_sdk_stderr_line_forwarding_uses_bounded_private_stream(backend, job, sdk, monkeypatch):
    def config(**kwargs):
        # The pinned SDK forwards CLI stderr through TextIO.writelines.
        kwargs["log_output"].writelines(["PRIVATE_STARTUP\n", "x" * (1024 * 1024)])
        return kwargs
    fake = backend._load_sdk()
    fake.Config = config
    monkeypatch.setattr(backend, "_load_sdk", lambda: fake)
    result = run(backend, job, enabled=True)
    assert result["status"] == "passed"
    assert Path(job["log_path"]).stat().st_size <= 256 * 1024
    assert "PRIVATE_STARTUP" not in json.dumps(result)


def test_log_hardlink_cannot_truncate_another_file(backend, job, sdk, tmp_path):
    original = tmp_path / "preserve.txt"
    original.write_text("preserve original bytes\n")
    log = Path(job["log_path"])
    log.parent.mkdir(mode=0o700)
    backend.os.link(original, log)
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert original.read_text() == "preserve original bytes\n"


def test_disabled_cli_does_not_read_stdin(backend, monkeypatch, capsys):
    class NoInput:
        @property
        def buffer(self):
            raise AssertionError("disabled backend must not read input")
    monkeypatch.setattr(backend.sys, "stdin", NoInput())
    assert backend.main([]) == 2
    assert json.loads(capsys.readouterr().out)["diagnostic_codes"] == ["shadow_disabled"]


def test_artifact_symlink_parent_does_not_create_outside_directories(backend, job, sdk, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    log = Path(job["log_path"])
    log.parent.mkdir(mode=0o700)
    (log.parent / "linked").symlink_to(outside, target_is_directory=True)
    job["check"]["configuration"]["artifacts"] = ["linked/new/junit.xml"]
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    assert list(outside.iterdir()) == []


def test_failed_check_remains_failed_when_artifact_is_unavailable(backend, job, sdk):
    client, _ = sdk
    client.code = 1
    job["check"]["configuration"]["artifacts"] = [".ci-select/junit.xml"]
    result = run(backend, job, enabled=True)
    assert result["status"] == "failed" and result["exit_code"] == 1
    assert "dagger_artifact_unavailable" in result["diagnostic_codes"]


def test_private_checksum_pinned_cli_does_not_depend_on_path(backend, job, sdk, tmp_path, monkeypatch):
    executable = tmp_path / "private-dagger"
    executable.write_bytes(b"fixture executable bytes")
    executable.chmod(0o700)
    job["check"]["configuration"].update({"cli": str(executable), "cli_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()})
    calls = []
    def version(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(stdout="dagger v0.21.10 darwin/arm64\n", returncode=0)
    monkeypatch.setattr(backend.subprocess, "run", version)
    monkeypatch.setattr(backend, "_probe_cli", lambda: pytest.fail("configured CLI must not use PATH"))
    assert run(backend, job, enabled=True)["status"] == "passed"
    assert calls == [[str(executable), "version"]]


@pytest.mark.parametrize("problem", ["hash", "writable", "symlink", "missing_hash"])
def test_private_cli_identity_failure_never_executes(backend, job, tmp_path, monkeypatch, problem):
    executable = tmp_path / "private-dagger"
    executable.write_bytes(b"fixture executable bytes")
    executable.chmod(0o700)
    checksum = hashlib.sha256(executable.read_bytes()).hexdigest()
    if problem == "hash":
        checksum = "0" * 64
    elif problem == "writable":
        executable.chmod(0o777)
    elif problem == "symlink":
        target = executable
        executable = tmp_path / "linked-dagger"
        executable.symlink_to(target)
    job["check"]["configuration"].update({"cli": str(executable), "cli_sha256": checksum})
    if problem == "missing_hash":
        del job["check"]["configuration"]["cli_sha256"]
    monkeypatch.setattr(backend.subprocess, "run", lambda *_a, **_k: pytest.fail("unverified CLI must not execute"))
    result = run(backend, job, enabled=True)
    assert result["status"] == "unavailable"
    if problem != "missing_hash":
        assert result["diagnostic_codes"] == ["dagger_cli_identity_mismatch"]
