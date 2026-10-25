"""Pinned Dagger SDK backend, invoked in an isolated process by an enrolled adapter.

The caller owns snapshot capture, admission, cancellation and enrollment. This
module never installs a CLI or runtime, provisions an engine, submits agent
messages, or accepts its observations as formal gate evidence.
"""

import argparse
import asyncio
from contextlib import contextmanager
import fnmatch
from functools import lru_cache
import hashlib
import importlib
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlsplit


DAGGER_VERSION = "0.21.10"
_MAX_INPUT = 1024 * 1024
_MAX_LOG = 256 * 1024
_SESSION_LOCK = threading.Lock()
_GENERATED_SOURCE_EXCLUDES = (".venv", "**/.venv", "__pycache__", "**/__pycache__", "node_modules", "**/node_modules")


class _Unavailable(Exception):
    """A fixed, non-secret capability or input disposition."""


def _result(check_id, status, code, *, exit_code=None, runtime=None):
    return {
        "schema_version": 1,
        "check_id": check_id,
        "status": status,
        "exit_code": exit_code,
        "runtime": runtime or {},
        "test_ids": [],
        "diagnostic_codes": [code] if code else [],
    }


def _relative(value, *, allow_dot=False):
    if not isinstance(value, str) or not value or len(value) > 4096 or "\\" in value or "\0" in value:
        raise _Unavailable("dagger_configuration_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or (str(path) == "." and not allow_dot):
        raise _Unavailable("dagger_configuration_invalid")
    return str(path)


def _local_engine(value):
    if not isinstance(value, str) or len(value) > 4096 or any(char.isspace() for char in value):
        return False
    parsed = urlsplit(value)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return False
    if parsed.scheme == "unix":
        return not parsed.netloc and parsed.path.startswith("/")
    if parsed.scheme == "docker-container":
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", parsed.netloc)) and not parsed.path
    if parsed.scheme == "tcp":
        try:
            return parsed.hostname in {"localhost", "127.0.0.1", "::1"} and 0 < parsed.port < 65536 and not parsed.path
        except (ValueError, TypeError):
            return False
    return False


def _source_excludes(value):
    if not isinstance(value, list) or len(value) > 32:
        raise _Unavailable("dagger_configuration_invalid")
    excludes = list(_GENERATED_SOURCE_EXCLUDES)
    for pattern in value:
        pattern = _relative(pattern)
        if pattern.startswith("!"):
            raise _Unavailable("dagger_configuration_invalid")
        # An explicit generated subtree must exclude its directory too, so
        # validation prunes it before looking at platform-specific symlinks.
        if pattern.endswith("/**"):
            excludes.append(pattern[:-3])
        excludes.append(pattern)
    return list(dict.fromkeys(excludes))


def _excluded_source(name, excludes):
    # Match rooted path components, never suffixes or '*' across separators.
    # Otherwise validation could prune a path that Dagger would still import.
    parts = PurePosixPath(name).parts
    for pattern in excludes:
        tokens = PurePosixPath(pattern).parts
        @lru_cache(maxsize=None)
        def matched(position, token):
            if token == len(tokens):
                return position == len(parts)
            if tokens[token] == "**":
                return matched(position, token + 1) or (position < len(parts) and matched(position + 1, token))
            return position < len(parts) and fnmatch.fnmatchcase(parts[position], tokens[token]) and matched(position + 1, token + 1)
        if matched(0, 0):
            return True
    return False


def _validate_source_links(snapshot, excludes):
    def failed(error):
        raise error
    for directory, names, files in os.walk(snapshot, followlinks=False, onerror=failed):
        root = Path(directory)
        names[:] = [name for name in names if not _excluded_source(str((root / name).relative_to(snapshot)), excludes)]
        for name in [*names, *files]:
            target = root / name
            if _excluded_source(str(target.relative_to(snapshot)), excludes):
                continue
            if target.is_symlink():
                target.resolve(strict=True).relative_to(snapshot)


def _validated(request):
    if not isinstance(request, dict) or type(request.get("schema_version")) is not int or request["schema_version"] != 1:
        raise _Unavailable("dagger_configuration_invalid")
    check = request.get("check")
    if not isinstance(check, dict) or check.get("backend") != "dagger":
        raise _Unavailable("dagger_configuration_invalid")
    if not isinstance(check.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", check["id"]):
        raise _Unavailable("dagger_configuration_invalid")
    config = check.get("configuration")
    if not isinstance(config, dict):
        raise _Unavailable("dagger_configuration_invalid")
    if not config.get("engine"):
        raise _Unavailable("dagger_engine_unconfigured")
    required = {"argv", "platform", "image", "python_version", "uv_version", "engine"}
    if not required <= config.keys() or config.keys() - required - {"groups", "project_path", "artifacts", "cli", "cli_sha256", "source_excludes"}:
        raise _Unavailable("dagger_configuration_invalid")
    if ("cli" in config) != ("cli_sha256" in config):
        raise _Unavailable("dagger_configuration_invalid")
    if "cli" in config and (not isinstance(config["cli"], str) or not Path(config["cli"]).is_absolute()
                            or not isinstance(config["cli_sha256"], str)
                            or not re.fullmatch(r"[0-9a-f]{64}", config["cli_sha256"])):
        raise _Unavailable("dagger_configuration_invalid")
    config = dict(config)
    lane = check.get("lane")
    architectures = {"arm64": "arm64", "aarch64": "arm64", "amd64": "amd64", "x86_64": "amd64"}
    if not isinstance(lane, dict) or lane.get("os") != "linux":
        raise _Unavailable("dagger_configuration_invalid")
    if config["platform"] not in {"linux/arm64", "linux/amd64"} or config["platform"] != "linux/" + architectures.get(lane.get("architecture"), "unknown"):
        raise _Unavailable("dagger_configuration_invalid")
    if not isinstance(config["image"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", config["image"]):
        raise _Unavailable("dagger_configuration_invalid")
    for key in ("python_version", "uv_version"):
        if not isinstance(config[key], str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", config[key]):
            raise _Unavailable("dagger_configuration_invalid")
    if lane.get("python") not in {config["python_version"], config["python_version"].rsplit(".", 1)[0]}:
        raise _Unavailable("dagger_configuration_invalid")
    if not _local_engine(config["engine"]):
        raise _Unavailable("dagger_configuration_invalid")
    argv = config["argv"]
    if not isinstance(argv, list) or not 1 <= len(argv) <= 256 or not all(isinstance(value, str) and value and "\0" not in value for value in argv) or sum(map(len, argv)) > 32768:
        raise _Unavailable("dagger_configuration_invalid")
    config["groups"] = config.get("groups", [])
    if not isinstance(config["groups"], list) or not all(isinstance(group, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", group) for group in config["groups"]) or len(set(config["groups"])) != len(config["groups"]):
        raise _Unavailable("dagger_configuration_invalid")
    config["project_path"] = _relative(config.get("project_path", "."), allow_dot=True)
    config["source_excludes"] = _source_excludes(config.get("source_excludes", []))
    artifacts = config.get("artifacts", [])
    if not isinstance(artifacts, list) or len(artifacts) > 32:
        raise _Unavailable("dagger_configuration_invalid")
    config["artifacts"] = [_relative(value) for value in artifacts]
    if len(set(config["artifacts"])) != len(config["artifacts"]):
        raise _Unavailable("dagger_configuration_invalid")
    timeout = check.get("timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 21600:
        raise _Unavailable("dagger_configuration_invalid")
    try:
        snapshot = Path(request["snapshot"])
        if not snapshot.is_absolute() or snapshot.is_symlink() or not snapshot.is_dir():
            raise _Unavailable("dagger_snapshot_unavailable")
        snapshot = snapshot.resolve(strict=True)
        project = (snapshot / config["project_path"]).resolve(strict=True)
        project.relative_to(snapshot)
        for name in ("pyproject.toml", "uv.lock"):
            target = project / name
            if not target.is_file() or target.is_symlink():
                raise _Unavailable("dagger_frozen_dependencies_unavailable")
        _validate_source_links(snapshot, config["source_excludes"])
        log_path = Path(request["log_path"])
        if not log_path.is_absolute() or log_path.is_symlink():
            raise _Unavailable("dagger_log_unavailable")
    except (KeyError, OSError, ValueError, TypeError):
        raise _Unavailable("dagger_snapshot_unavailable") from None
    return config, snapshot, log_path, float(timeout)


def _load_sdk():
    """Use only the already installed isolated SDK; do not install dependencies."""
    if metadata.version("dagger-io") != DAGGER_VERSION:
        raise _Unavailable("dagger_sdk_version_mismatch")
    return importlib.import_module("dagger")


def _probe_cli():
    """Probe an existing CLI with update checks disabled, without provisioning."""
    executable = shutil.which("dagger")
    if not executable:
        return None
    return _probe_binary(executable)


def _probe_binary(executable):
    with _cli_environment() as environment:
        process = subprocess.run(
            [executable, "version"], stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=5, env=environment,
        )
    match = re.search(r"\bdagger v([0-9]+\.[0-9]+\.[0-9]+)\b", process.stdout[:4096])
    return (executable, match[1]) if process.returncode == 0 and match else None


def _configured_cli(config):
    """Verify the explicit private installation before allowing its version probe."""
    path = Path(config["cli"])
    try:
        if any(item.is_symlink() for item in [path, *path.parents]):
            raise _Unavailable("dagger_cli_identity_mismatch")
        details = path.stat()
        parent = path.parent.stat()
        if (not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
                or details.st_nlink != 1 or details.st_mode & 0o022 or not details.st_mode & stat.S_IXUSR
                or parent.st_uid != os.geteuid() or parent.st_mode & 0o022
                or details.st_size > 128 * 1024 * 1024):
            raise _Unavailable("dagger_cli_identity_mismatch")
        if hashlib.sha256(path.read_bytes()).hexdigest() != config["cli_sha256"]:
            raise _Unavailable("dagger_cli_identity_mismatch")
    except OSError:
        raise _Unavailable("dagger_cli_identity_mismatch") from None
    return _probe_binary(str(path))


@contextmanager
def _cli_environment(executable=None, engine=None):
    """Isolate registry and saved Cloud auth; disable pinned CLI analytics."""
    # Public images only. Never read, copy, or alter host credential files.
    # Dagger 0.21.10 analytics checks DO_NOT_TRACK=1; its separate Cloud trace
    # exporter falls back to XDG_CONFIG_HOME/dagger/credentials.json.
    with tempfile.TemporaryDirectory(prefix="continuous-validation-cli-") as directory:
        private = Path(directory)
        private.chmod(0o700)
        configuration = private / "configuration"
        configuration.mkdir(mode=0o700)
        registry = private / "registry"
        registry.mkdir(mode=0o700)
        descriptor = os.open(registry / "config.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"auths": {}}, stream)
        environment = dict(os.environ)
        for key in list(environment):
            if key.startswith(("DAGGER_", "_EXPERIMENTAL_DAGGER_", "OTEL_", "DOCKER_",
                               "REGISTRY_", "CONTAINERS_", "BUILDKIT_", "BUILDX_")) or key in {"TRACEPARENT", "TRACESTATE", "SSH_AUTH_SOCK", "SSH_AGENT_PID"}:
                del environment[key]
        environment.update({
            "DAGGER_NO_UPDATE_CHECK": "1", "DO_NOT_TRACK": "1",
            "XDG_CONFIG_HOME": str(configuration), "DOCKER_CONFIG": str(registry),
        })
        if executable is not None:
            environment["_EXPERIMENTAL_DAGGER_CLI_BIN"] = executable
        if engine is not None:
            environment["_EXPERIMENTAL_DAGGER_RUNNER_HOST"] = engine
        yield environment


@contextmanager
def _connection_environment(executable, engine):
    # The command is process-isolated. Refuse concurrent in-process executions
    # rather than racing the SDK's process-environment session configuration.
    previous = dict(os.environ)
    try:
        with _cli_environment(executable, engine) as environment:
            os.environ.clear()
            os.environ.update(environment)
            yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def _ensure_directory(path, code):
    # Check existing ancestors before mkdir(parents=True), which would otherwise
    # follow a symlink and create directories outside the output boundary.
    if any(item.is_symlink() for item in [path, *path.parents]):
        raise _Unavailable(code)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.resolve() != path:
        raise _Unavailable(code)


class _PrivateLog:
    """A bounded private stream; SDK progress and command output stay off stdout."""

    def __init__(self, path):
        _ensure_directory(path.parent, "dagger_log_unavailable")
        if path.parent != path.parent.resolve() or path.parent.stat().st_mode & 0o077:
            raise _Unavailable("dagger_log_unavailable")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or details.st_uid != os.geteuid():
            os.close(descriptor)
            raise _Unavailable("dagger_log_unavailable")
        try:
            os.fchmod(descriptor, 0o600)
            os.ftruncate(descriptor, 0)
        except OSError:
            os.close(descriptor)
            raise
        self.stream = os.fdopen(descriptor, "w")
        self.remaining = _MAX_LOG
        self.lock = threading.Lock()

    def write(self, value):
        with self.lock:
            bounded = str(value).encode("utf-8")[:self.remaining].decode("utf-8", errors="ignore")
            self.stream.write(bounded)
            self.remaining -= len(bounded.encode("utf-8"))
        return len(value)

    def writelines(self, values):
        for value in values:
            self.write(value)

    def isatty(self):
        return False

    def flush(self):
        with self.lock:
            self.stream.flush()

    def close(self):
        with self.lock:
            self.stream.close()


async def _export_artifacts(container, config, log_path):
    exported = []
    for relative in config["artifacts"]:
        destination = log_path.parent / relative
        if destination == log_path or destination.is_symlink():
            raise _Unavailable("dagger_artifact_unavailable")
        if destination.exists():
            details = destination.stat()
            if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or details.st_uid != os.geteuid():
                raise _Unavailable("dagger_artifact_unavailable")
        _ensure_directory(destination.parent, "dagger_artifact_unavailable")
        for item in [destination, *destination.parents]:
            if item == log_path.parent.parent:
                break
            if item.is_symlink():
                raise _Unavailable("dagger_artifact_unavailable")
        source = str(PurePosixPath("/workspace") / config["project_path"] / relative)
        await container.file(source).export(str(destination))
        if not destination.is_file() or destination.is_symlink():
            raise _Unavailable("dagger_artifact_unavailable")
        destination.chmod(0o600)
        exported.append(relative)
    return exported


def _uv_cache_key(config, snapshot):
    """Namespace the package cache without sharing a source tree or environment."""
    project = snapshot / config["project_path"]
    policy = {}
    for directory in dict.fromkeys((snapshot, project)):
        for name in ("pyproject.toml", "uv.lock", "uv.toml"):
            path = directory / name
            if path.is_file():
                policy[str(path.relative_to(snapshot))] = hashlib.sha256(path.read_bytes()).hexdigest()
    identity = {
        "schema_version": 1, "sdk": DAGGER_VERSION, "image": config["image"],
        "platform": config["platform"], "python": config["python_version"],
        "uv": config["uv_version"], "project": config["project_path"],
        "groups": sorted(config["groups"]), "policy": policy,
        "source_excludes": config["source_excludes"],
        "frozen": True, "link_mode": "copy", "python_downloads": "never",
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return "continuous-validation-uv-v1-" + hashlib.sha256(encoded).hexdigest()


async def _pipeline(sdk, config, snapshot, log_path, timeout, executable):
    runtime = {"backend": "dagger", "sdk_version": DAGGER_VERSION, "cache": "unavailable"}
    log = _PrivateLog(log_path)
    stage = "connection"
    try:
        with _connection_environment(executable, config["engine"]):
            async with sdk.Connection(sdk.Config(
                log_output=log, load_workspace_modules=False,
                timeout=sdk.Timeout(timeout, connect=min(timeout, 10)),
                retry=sdk.Retry(connect=False, execute=False),
            )) as client:
                engine_version = (await client.version()).removeprefix("v")
                if engine_version != DAGGER_VERSION:
                    raise _Unavailable("dagger_engine_version_mismatch")
                runtime["engine_version"] = engine_version
                engine_platform = str(await client.default_platform())
                if engine_platform != config["platform"]:
                    raise _Unavailable("dagger_native_platform_unavailable")
                runtime["platform"] = engine_platform
                source = client.host().directory(str(snapshot), gitignore=False, exclude=config["source_excludes"])
                container = client.container(platform=sdk.Platform(config["platform"])).from_(config["image"])
                python_version = (await container.with_exec(["python", "-c", "import platform; print(platform.python_version())"]).stdout()).strip()
                if python_version != config["python_version"]:
                    raise _Unavailable("dagger_python_version_mismatch")
                uv_reply = (await container.with_exec(["uv", "--version"]).stdout()).strip()
                if not re.fullmatch(r"uv " + re.escape(config["uv_version"]) + r"(?: \([^\n]*\))?", uv_reply):
                    raise _Unavailable("dagger_uv_version_mismatch")
                runtime.update({"python": python_version, "uv": config["uv_version"], "image_digest": config["image"].split("@", 1)[1]})
                # Dagger persists only uv's package cache between snapshots.
                # Frozen sync and tests still execute against their own source
                # and .venv; this mount is not evidence of a cache hit or pass.
                package_cache = client.cache_volume(_uv_cache_key(config, snapshot))
                container = (container.with_directory("/workspace", source)
                             .with_workdir(str(PurePosixPath("/workspace") / config["project_path"]))
                             .with_mounted_cache("/root/.cache/uv", package_cache)
                             .with_env_variable("UV_CACHE_DIR", "/root/.cache/uv")
                             .with_env_variable("UV_LINK_MODE", "copy")
                             .with_env_variable("UV_PYTHON_DOWNLOADS", "never")
                             .with_env_variable("UV_NO_PROGRESS", "1"))
                sync = ["uv", "sync", "--frozen"]
                for group in config["groups"]:
                    sync += ["--group", group]
                stage = "setup"
                container = await container.with_exec(sync).sync()
                stage = "check"
                container = container.with_exec(config["argv"], expect=sdk.ReturnType.ANY)
                exit_code = await container.exit_code()
                if isinstance(exit_code, bool) or not isinstance(exit_code, int) or not 0 <= exit_code <= 255:
                    raise _Unavailable("dagger_check_completion_unconfirmed")
                log.write(await container.stdout())
                log.write(await container.stderr())
                result = _result("", "passed" if exit_code == 0 else "failed", None if exit_code == 0 else "dagger_check_failed", exit_code=exit_code, runtime=runtime)
                try:
                    runtime["artifacts"] = await _export_artifacts(container, config, log_path)
                except Exception:
                    result["diagnostic_codes"].append("dagger_artifact_unavailable")
                    if exit_code == 0:
                        result.update({"status": "unavailable", "exit_code": None})
                return result
    except sdk.ExecError as error:
        if stage != "check":
            return _result("", "unavailable", "dagger_dependency_setup_failed" if stage == "setup" else "dagger_capability_probe_failed", runtime=runtime)
        code = getattr(error, "exit_code", None)
        if isinstance(code, bool) or not isinstance(code, int) or not 1 <= code <= 255:
            return _result("", "unavailable", "dagger_check_completion_unconfirmed", runtime=runtime)
        return _result("", "failed", "dagger_check_failed", exit_code=code, runtime=runtime)
    finally:
        log.close()


async def execute(request: dict, *, enabled: bool = False) -> dict:
    """Evaluate one immutable snapshot, or return a bounded unavailable result."""
    check = request.get("check", {}) if isinstance(request, dict) else {}
    candidate_id = check.get("id") if isinstance(check, dict) else None
    check_id = candidate_id if isinstance(candidate_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", candidate_id) else "unknown"
    if enabled is not True:
        return _result(check_id, "unavailable", "shadow_disabled")
    acquired = False
    try:
        config, snapshot, log_path, timeout = _validated(request)
        cli = _configured_cli(config) if "cli" in config else _probe_cli()
        if cli is None:
            raise _Unavailable("dagger_cli_unavailable")
        executable, version = cli
        if version != DAGGER_VERSION:
            raise _Unavailable("dagger_cli_version_mismatch")
        try:
            sdk = _load_sdk()
        except (ImportError, metadata.PackageNotFoundError):
            raise _Unavailable("dagger_sdk_unavailable") from None
        acquired = _SESSION_LOCK.acquire(blocking=False)
        if not acquired:
            raise _Unavailable("dagger_session_busy")
        async with asyncio.timeout(timeout):
            result = await _pipeline(sdk, config, snapshot, log_path, timeout, executable)
        result["check_id"] = check_id
        return result
    except _Unavailable as error:
        return _result(check_id, "unavailable", str(error))
    except (TimeoutError, subprocess.TimeoutExpired):
        return _result(check_id, "unavailable", "dagger_execution_timeout")
    except Exception:
        return _result(check_id, "unavailable", "dagger_engine_unavailable")
    finally:
        if acquired:
            _SESSION_LOCK.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Execute an enrolled advisory check with a pinned local Dagger engine")
    parser.add_argument("--enabled", action="store_true")
    args = parser.parse_args(argv)
    if not args.enabled:
        print(json.dumps(_result("unknown", "unavailable", "shadow_disabled"), sort_keys=True))
        return 2
    try:
        payload = sys.stdin.buffer.read(_MAX_INPUT + 1)
        if len(payload) > _MAX_INPUT:
            raise ValueError("request exceeds bound")
        request = json.loads(payload)
        result = asyncio.run(execute(request, enabled=args.enabled))
    except Exception:
        result = _result("unknown", "unavailable", "dagger_request_invalid")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1 if result["status"] == "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
