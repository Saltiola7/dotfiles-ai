"""Trusted pinned-image review strategy; never installs or starts an engine.

The normal entry point requires separately activated real inference. Explicit
qualification is a different CLI operation and never reads Vertex credentials.
Only a bounded patch and the trusted worker enter the tool container.
"""

import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

from . import dagger_backend


CHECK_ID = "pr-agent-review"
RELEASE = "0.49.0"
SOURCE_COMMIT = "efdde4afe14aa401a3889012c7f3e9ef3081a430"
IMAGE = "pragent/pr-agent:0.49.0@sha256:10a8893d5e081be1a5ae825843d9fc14f8e8d59d8a4f61d67c1775415156079f"
NATIVE_DIGESTS = {
    "linux/arm64": "sha256:72bf20078583aadb63f4cdb6cf350668d6f622a79ed00cba2d30643ec802d4a4",
    "linux/amd64": "sha256:e47e1108778407cd85882cd035f9217f69daae08c8a826617ccb2eb2373b4071",
}
PYTHON_VERSION = "3.14.9"
PACKAGE_VERSION = "0.49.0"  # Observed installed metadata in the digest-pinned image.
LITELLM_VERSION = "1.105.1"
MAX_PATCH = 256 * 1024
MAX_ARTIFACT = 1024 * 1024
MAX_ADC = 64 * 1024
MAX_REPLY = 8192
MAX_REQUEST = 1024 * 1024
_CONFIG = {"schema_version", "provider", "model", "project", "location", "adc_file", "source_patterns", "real_inference_enabled", "dagger"}
_DAGGER = {"platform", "engine", "cli", "cli_sha256", "sdk_python"}
_CODES = {"pr_agent_reauth_required", "pr_agent_access_denied", "pr_agent_execution_failed", "pr_agent_output_invalid", "pr_agent_patch_unavailable"}


class _Unavailable(ValueError):
    """Fixed diagnostic; never wrap raw provider, credential or SDK messages."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _result(status, code=None, *, runtime=None):
    return {"schema_version": 1, "check_id": CHECK_ID, "status": status,
            "exit_code": 0 if status == "passed" else None, "runtime": runtime or {},
            "test_ids": [], "diagnostic_codes": [code] if code else []}


def _closed(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise _Unavailable("pr_agent_configuration_invalid")


def _absolute(value):
    if (not isinstance(value, str) or not value or len(value) > 4096
            or not Path(value).is_absolute() or any(ord(char) < 32 for char in value)):
        raise _Unavailable("pr_agent_configuration_invalid")
    return Path(value)


def _private_bytes(path, maximum, code):
    """Read one opened nonblocking owned file, rejecting aliases and special files."""
    try:
        path = Path(path)
        if not path.is_absolute() or any(item.is_symlink() for item in [path, *path.parents]):
            raise _Unavailable(code)
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            item = os.fstat(stream.fileno())
            if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.geteuid()
                    or item.st_nlink != 1 or item.st_mode & 0o077 or item.st_size > maximum):
                raise _Unavailable(code)
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise _Unavailable(code)
        return raw
    except OSError:
        raise _Unavailable(code) from None


def _read_adc(path):
    raw = _private_bytes(path, MAX_ADC, "pr_agent_credentials_unavailable")
    try:
        if any((parent / ".git").exists() for parent in Path(path).parents):
            raise ValueError()
        value = json.loads(raw)
        if (not isinstance(value, dict) or value.get("type") != "authorized_user"
                or any(not isinstance(value.get(key), str) or not value[key] for key in ("client_id", "client_secret", "refresh_token"))
                or value.get("token_uri", "https://oauth2.googleapis.com/token") != "https://oauth2.googleapis.com/token"
                or value.get("universe_domain", "googleapis.com") != "googleapis.com"):
            raise ValueError()
    except (ValueError, UnicodeError, TypeError):
        raise _Unavailable("pr_agent_credentials_unavailable") from None
    return raw.decode("utf-8")


def _validated(request):
    _closed(request, {"schema_version", "check", "log_path", "patch_path", "config"})
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise _Unavailable("pr_agent_configuration_invalid")
    config = request["config"]
    _closed(config, _CONFIG)
    _closed(config["dagger"], _DAGGER)
    if (type(config["schema_version"]) is not int or config["schema_version"] != 1
            or config["provider"] != "vertex" or type(config["real_inference_enabled"]) is not bool
            or not isinstance(config["model"], str) or not re.fullmatch(r"vertex_ai/[A-Za-z0-9][A-Za-z0-9_.@/-]{0,190}", config["model"])
            or not isinstance(config["project"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", config["project"])
            or not isinstance(config["location"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", config["location"])
            or not isinstance(config["source_patterns"], list) or not config["source_patterns"]
            or any(not isinstance(item, str) or not item or len(item) > 4096 or item.startswith(("/", "!")) or ".." in Path(item).parts for item in config["source_patterns"])):
        raise _Unavailable("pr_agent_configuration_invalid")
    for name in ("adc_file",):
        _absolute(config[name])
    for name in ("cli", "sdk_python"):
        _absolute(config["dagger"][name])
    engine = config["dagger"]
    if (engine["platform"] not in NATIVE_DIGESTS or not dagger_backend._local_engine(engine["engine"])
            or not isinstance(engine["cli_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", engine["cli_sha256"])):
        raise _Unavailable("pr_agent_configuration_invalid")
    check = request["check"]
    _closed(check, {"id", "class", "backend", "lane", "timeout_seconds", "cacheable", "configuration"})
    lane = check["lane"]
    _closed(lane, {"os", "architecture", "python", "tools", "dependencies"})
    configuration = check["configuration"]
    _closed(configuration, {"strategy", "test_identity", "config_digest"})
    if (check["id"] != CHECK_ID or check["class"] != "expensive" or check["backend"] != "dagger"
            or check["cacheable"] is not False or type(check["timeout_seconds"]) is not int or not 1 <= check["timeout_seconds"] <= 300
            or lane["os"] != "linux" or lane["python"] != PYTHON_VERSION
            or engine["platform"] != "linux/" + str(lane["architecture"])
            or not isinstance(lane["tools"], dict) or not isinstance(lane["dependencies"], dict)
            or configuration != {"strategy": "pr-agent-review-v1", "test_identity": "not_applicable", "config_digest": hashlib.sha256(_canonical(config)).hexdigest()}):
        raise _Unavailable("pr_agent_configuration_invalid")
    return config, _absolute(request["patch_path"]), _absolute(request["log_path"]), check["timeout_seconds"]


@contextmanager
def _connection_environment(executable, engine):
    previous = dict(os.environ)
    allowed = {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"}
    try:
        os.environ.clear()
        os.environ.update({name: value for name, value in previous.items() if name in allowed})
        with dagger_backend._connection_environment(executable, engine):
            yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


async def _exports(container, log_path):
    directory = log_path.with_suffix(".artifacts")
    dagger_backend._ensure_directory(directory, "pr_agent_artifact_unavailable")
    item = directory.stat()
    if item.st_uid != os.geteuid() or item.st_mode & 0o077:
        raise _Unavailable("pr_agent_artifact_unavailable")
    for name in ("review.md", "review.json"):
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            raise _Unavailable("pr_agent_artifact_unavailable")
        source = container.file("/output/" + name)
        size = await source.size()
        if type(size) is not int or not 0 < size <= MAX_ARTIFACT:
            raise _Unavailable("pr_agent_artifact_unavailable")
        temporary = directory / (".export-" + uuid.uuid4().hex)
        await source.export(str(temporary))
        # Export creates a new path; verify it before setting private permissions.
        descriptor = os.open(temporary, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            item = os.fstat(stream.fileno())
            if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.geteuid() or item.st_nlink != 1
                    or item.st_size != size or item.st_size > MAX_ARTIFACT):
                raise _Unavailable("pr_agent_artifact_unavailable")
            os.fchmod(stream.fileno(), 0o600)
        os.rename(temporary, destination)
    return ["review.md", "review.json"]


async def _pipeline(sdk, config, patch, log_path, timeout, executable, adc, mode):
    engine = config["dagger"]
    runtime = {"backend": "dagger", "sdk_version": dagger_backend.DAGGER_VERSION, "pr_agent_release": RELEASE,
               "upstream_source": SOURCE_COMMIT, "image_digest": NATIVE_DIGESTS[engine["platform"]],
               "image_index_digest": IMAGE.split("@", 1)[1], "cache": "not_reused",
               "configuration_digest": hashlib.sha256(_canonical(config)).hexdigest(),
               "model": config["model"], "provider": "vertex",
               "test_identity": {"schema_version": 1, "kind": "not_applicable"}}
    if mode != "review":
        runtime["qualification"] = mode
    log = dagger_backend._PrivateLog(log_path)
    try:
        with _connection_environment(executable, engine["engine"]):
            async with sdk.Connection(sdk.Config(log_output=None, load_workspace_modules=False,
                    timeout=sdk.Timeout(timeout, connect=min(timeout, 10)), retry=sdk.Retry(connect=False, execute=False))) as client:
                if (await client.version()).removeprefix("v") != dagger_backend.DAGGER_VERSION:
                    raise _Unavailable("dagger_engine_version_mismatch")
                if str(await client.default_platform()) != engine["platform"]:
                    raise _Unavailable("dagger_native_platform_unavailable")
                runtime.update({"engine_version": dagger_backend.DAGGER_VERSION, "platform": engine["platform"]})
                worker = Path(__file__).with_name("pr_agent_worker.py").read_text()
                runtime["wrapper_sha256"] = hashlib.sha256(worker.encode()).hexdigest()
                container = (client.container(platform=sdk.Platform(engine["platform"]))
                    .from_("pragent/pr-agent:0.49.0@" + NATIVE_DIGESTS[engine["platform"]])
                    .with_exec(["mkdir", "-p", "/work/home", "/input", "/output"])
                    .with_exec(["chown", "10001:10001", "/work", "/work/home", "/input", "/output"])
                    .with_user("10001:10001")
                    .with_workdir("/work")
                    .with_new_file("/runner/pr_agent_worker.py", worker)
                    .with_env_variable("HOME", "/work/home")
                    .with_env_variable("XDG_CONFIG_HOME", "/work/config")
                    .with_env_variable("DO_NOT_TRACK", "1")
                    .with_env_variable("LITELLM_LOCAL_MODEL_COST_MAP", "true")
                    .with_env_variable("PYTHONDONTWRITEBYTECODE", "1"))
                probe = container.with_exec(["python", "/runner/pr_agent_worker.py", "--probe"])
                raw = await probe.stdout()
                if len(raw.encode()) > MAX_REPLY:
                    raise _Unavailable("pr_agent_runtime_identity_unavailable")
                try:
                    identity = json.loads(raw)
                except (ValueError, TypeError):
                    raise _Unavailable("pr_agent_runtime_identity_unavailable") from None
                if identity != {"python": PYTHON_VERSION, "package_version": PACKAGE_VERSION, "litellm": LITELLM_VERSION, "uid": 10001}:
                    raise _Unavailable("pr_agent_runtime_version_mismatch")
                runtime.update(identity)
                settings = {"schema_version": 1, "model": config["model"], "project": config["project"], "location": config["location"]}
                container = (container.with_new_file("/input/changes.diff", patch, owner="10001:10001", permissions=0o600)
                    .with_new_file("/input/settings.json", _canonical(settings).decode(), owner="10001:10001", permissions=0o600)
                    .with_env_variable("PR_AGENT_EXECUTION_NONCE", uuid.uuid4().hex))
                if mode == "review":
                    secret = client.set_secret("pr-agent-vertex-adc-" + uuid.uuid4().hex, adc)
                    container = container.with_mounted_secret("/run/secrets/vertex-adc.json", secret, owner="10001:10001", mode=0o400)
                container = container.with_exec(["python", "/runner/pr_agent_worker.py", "--mode", mode], expect=sdk.ReturnType.ANY)
                code = await container.exit_code()
                raw = await container.stdout()
                if type(code) is not int or not 0 <= code <= 255 or len(raw.encode()) > MAX_REPLY:
                    raise _Unavailable("pr_agent_completion_unconfirmed")
                try:
                    reply = json.loads(raw)
                    if (not isinstance(reply, dict) or set(reply) != {"schema_version", "status", "diagnostic_code"}
                            or reply["schema_version"] != 1 or type(reply["schema_version"]) is not int
                            or reply["status"] not in {"passed", "unavailable"}
                            or reply["diagnostic_code"] not in _CODES | {None}):
                        raise ValueError()
                except (ValueError, TypeError):
                    raise _Unavailable("pr_agent_completion_unconfirmed") from None
                if code != 0 or reply["status"] != "passed" or reply["diagnostic_code"] is not None:
                    return _result("unavailable", reply["diagnostic_code"] or "pr_agent_execution_failed", runtime=runtime)
                if mode != "help":
                    runtime["artifacts"] = await _exports(container, log_path)
                log.write("pr-agent " + mode + " completed; private artifacts retain advisory output\n")
                return _result("passed", runtime=runtime)
    finally:
        log.close()


async def _execute(request, *, enabled=False, qualification=None):
    if enabled is not True:
        return _result("unavailable", "shadow_disabled")
    acquired = False
    try:
        config, patch_path, log_path, timeout = _validated(request)
        if qualification is None and config["real_inference_enabled"] is not True:
            raise _Unavailable("pr_agent_inference_not_activated")
        patch = _private_bytes(patch_path, MAX_PATCH, "pr_agent_patch_unavailable").decode("utf-8")
        if not patch.strip() or "\0" in patch or len(re.findall(r"^diff --git ", patch, re.M)) > 32:
            raise _Unavailable("pr_agent_patch_unavailable")
        adc = _read_adc(Path(config["adc_file"])) if qualification is None else None
        if adc is not None and json.loads(adc).get("quota_project_id") != config["project"]:
            raise _Unavailable("pr_agent_credentials_unavailable")
        cli = dagger_backend._configured_cli(config["dagger"])
        if cli is None or cli[1] != dagger_backend.DAGGER_VERSION:
            raise _Unavailable("dagger_cli_version_mismatch")
        sdk = dagger_backend._load_sdk()
        acquired = dagger_backend._SESSION_LOCK.acquire(blocking=False)
        if not acquired:
            raise _Unavailable("dagger_session_busy")
        async with asyncio.timeout(timeout):
            return await _pipeline(sdk, config, patch, log_path, timeout, cli[0], adc, qualification or "review")
    except (ValueError, UnicodeError) as error:
        code = str(error) if isinstance(error, _Unavailable) else "pr_agent_configuration_invalid"
        return _result("unavailable", code)
    except dagger_backend._Unavailable as error:
        return _result("unavailable", str(error))
    except (TimeoutError, subprocess.TimeoutExpired):
        return _result("unavailable", "pr_agent_execution_timeout")
    except Exception:
        return _result("unavailable", "pr_agent_runtime_unavailable")
    finally:
        if acquired:
            dagger_backend._SESSION_LOCK.release()


async def execute(request: dict, *, enabled=False) -> dict:
    """Execute only an explicitly activated trusted-controller review request."""
    return await _execute(request, enabled=enabled)


async def qualify(request: dict, *, mode: str, enabled=False) -> dict:
    """Explicit operator qualification; never reachable through enrollment config."""
    if mode not in {"help", "synthetic"}:
        return _result("unavailable", "pr_agent_qualification_invalid")
    return await _execute(request, enabled=enabled, qualification=mode)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--qualify", choices=("help", "synthetic"))
    args = parser.parse_args(argv)
    if not args.enabled:
        result = _result("unavailable", "shadow_disabled")
    else:
        try:
            raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
            if len(raw) > MAX_REQUEST:
                raise ValueError()
            request = json.loads(raw)
            result = asyncio.run(qualify(request, mode=args.qualify, enabled=True) if args.qualify else execute(request, enabled=True))
        except Exception:
            result = _result("unavailable", "pr_agent_request_invalid")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
