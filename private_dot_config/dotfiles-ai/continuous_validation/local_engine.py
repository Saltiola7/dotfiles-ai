"""Explicit optional local-engine bootstrap owned by dotfiles-ai distribution.

Only setup with --enable-shadow installs the private pinned CLI/SDK environment
and starts the dedicated worker. Run/watch/check execution never calls setup.
Existing agent workers, their rootless runtime policy and host services remain
outside this bootstrap's ownership.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


INSTANCE = "continuous-validation-shadow"
OWNER = "dotfiles-ai.continuous-validation.local-engine"
VERSION = "0.21.10"
CLI_URL = "https://github.com/dagger/dagger/releases/download/v0.21.10/dagger_v0.21.10_darwin_arm64.tar.gz"
CLI_ARCHIVE_SHA256 = "4c9412e6f05c9ff2645dec2018f302dd9ba144badf9ea762d8ff3c0b1dd1259c"
ENGINE_IMAGE = "registry.dagger.io/engine:v0.21.10@sha256:2a7c054e0864e297671c24a0726ebf1c9747d70291b8843b1726daaff200a334"
WORKLOAD_IMAGE = "ghcr.io/astral-sh/uv:0.9.2-python3.14-bookworm@sha256:65708f023da472345b7de3bc7dffdca083e7634d01f6fbc9299b622e0023fad4"
TEMPLATE = Path(__file__).resolve().parent / "engine/lima.yaml"
_CURRENT_LOG = None


class EngineError(Exception):
    """A bounded disposition; subprocess output is retained only in private logs."""


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_directory(path):
    path = Path(path).absolute()
    if any(item.is_symlink() for item in [path, *path.parents]):
        raise EngineError("local_engine_private_path_invalid")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    details = path.stat()
    if details.st_uid != os.geteuid() or details.st_mode & 0o077:
        raise EngineError("local_engine_private_path_invalid")
    return path


def _read_private(path):
    if path.is_symlink():
        raise EngineError("local_engine_ownership_unavailable")
    details = path.stat()
    if not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid() or details.st_mode & 0o077 or details.st_nlink != 1:
        raise EngineError("local_engine_ownership_unavailable")
    if details.st_size > 65536:
        raise EngineError("local_engine_ownership_unavailable")
    return json.loads(path.read_text())


def _write_private(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=".engine-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _environment(lima_home):
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith(("DAGGER_", "_EXPERIMENTAL_DAGGER_", "OTEL_")) or key in {"TRACEPARENT", "TRACESTATE", "SSH_AUTH_SOCK", "SSH_AGENT_PID"}:
            del environment[key]
    environment.update({"LIMA_HOME": str(lima_home), "DAGGER_NO_UPDATE_CHECK": "1", "UV_PYTHON_DOWNLOADS": "never"})
    return environment


def _command(argv, *, timeout=30, env=None):
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        raise EngineError("local_engine_command_unavailable") from None
    if _CURRENT_LOG is not None:
        with _CURRENT_LOG.open("a") as stream:
            stream.write((result.stdout + "\n" + result.stderr)[-256 * 1024:])
    if result.returncode:
        raise EngineError("local_engine_command_failed")
    if len(result.stdout) > 8 * 1024 * 1024:
        raise EngineError("local_engine_output_exceeds_bound")
    return result


def _dagger_command(argv, *, executable=None, engine=None, timeout=30):
    # Share the backend's credential and analytics boundary for owner-only
    # qualification too. Loading this stdlib-only module never installs an SDK.
    source = Path(__file__).resolve().with_name("dagger_backend.py")
    spec = importlib.util.spec_from_file_location("continuous_validation_dagger_environment", source)
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    with backend._cli_environment(executable, engine) as environment:
        return _command(argv, timeout=timeout, env=environment)


def plan():
    return {
        "schema_version": 1, "status": "planned", "owner": OWNER, "instance": INSTANCE,
        "resources": {"cpus": 2, "memory_gib": 4, "disk_gib": 40},
        "mounts": [], "ssh_agent_forwarding": False,
        "dagger_version": VERSION, "engine_transport": "private_unix_socket",
        "cli_archive_sha256": CLI_ARCHIVE_SHA256, "engine_image": ENGINE_IMAGE,
        "workload_image": WORKLOAD_IMAGE, "template_sha256": _digest(TEMPLATE),
        "existing_workers": "untouched", "activation": "explicit_setup_only",
    }


def _inventory(lima_home):
    result = _command(["limactl", "list", "--json"], env=_environment(lima_home))
    rows = {}
    for line in result.stdout.splitlines():
        row = json.loads(line)
        name = row.get("name")
        if not isinstance(name, str) or name in rows:
            raise EngineError("local_engine_inventory_invalid")
        rows[name] = row
    return rows


def _download(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        if not response.url.startswith("https://"):
            raise EngineError("local_engine_download_invalid")
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise EngineError("local_engine_download_exceeds_bound")
    return data


def _install_cli(state_root):
    binary_dir = _private_directory(state_root / "bin")
    executable = binary_dir / "dagger"
    receipt_path = state_root / "cli.json"
    if executable.exists() or executable.is_symlink():
        receipt = _read_private(receipt_path)
        details = executable.lstat()
        if (not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
                or details.st_mode & 0o022 or details.st_nlink != 1
                or receipt.get("archive_sha256") != CLI_ARCHIVE_SHA256
                or receipt.get("binary_sha256") != _digest(executable)):
            raise EngineError("local_engine_cli_identity_mismatch")
    else:
        data = _download(CLI_URL)
        if hashlib.sha256(data).hexdigest() != CLI_ARCHIVE_SHA256:
            raise EngineError("local_engine_cli_checksum_mismatch")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = [entry for entry in archive.getmembers() if entry.name in {"dagger", "./dagger"}]
            if len(members) != 1 or not members[0].isfile() or members[0].size > 128 * 1024 * 1024:
                raise EngineError("local_engine_cli_archive_invalid")
            binary = archive.extractfile(members[0]).read(128 * 1024 * 1024 + 1)
        descriptor, temporary = tempfile.mkstemp(prefix=".dagger-", dir=binary_dir)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(binary)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o700)
            os.replace(temporary, executable)
        finally:
            Path(temporary).unlink(missing_ok=True)
        _write_private(receipt_path, {"schema_version": 1, "version": VERSION,
                                     "archive_sha256": CLI_ARCHIVE_SHA256,
                                     "binary_sha256": _digest(executable)})
    reply = _dagger_command([str(executable), "version"]).stdout
    if not re.search(r"\bdagger v0\.21\.10\b", reply[:4096]):
        raise EngineError("local_engine_cli_version_mismatch")
    return {"cli": str(executable), "cli_sha256": _digest(executable)}


def _host_capability():
    if sys.platform != "darwin" or platform.machine() not in {"arm64", "aarch64"}:
        raise EngineError("local_engine_host_unsupported")
    if not shutil.which("limactl") or not shutil.which("uv"):
        raise EngineError("local_engine_prerequisite_unavailable")
    reply = _command(["limactl", "--version"]).stdout.strip()
    if reply != "limactl version 2.2.1":
        raise EngineError("local_engine_lima_version_unqualified")
    return {"lima_version": "2.2.1"}


def _prepare_sdk(state_root, lima_home):
    project = Path(__file__).resolve().parent / "dagger_runtime"
    if not (project / "uv.lock").is_file():
        raise EngineError("local_engine_sdk_lock_unavailable")
    environment = _environment(lima_home)
    environment["UV_PROJECT_ENVIRONMENT"] = str(state_root / "sdk")
    _command(["uv", "sync", "--project", str(project), "--frozen", "--no-dev", "--python", "3.13"],
             timeout=300, env=environment)


def _validate_instance(lima_home, row, record=None):
    directory = Path(row.get("dir", ""))
    if (directory != lima_home / INSTANCE or directory.is_symlink()
            or row.get("name") != INSTANCE or row.get("vmType") != "vz"
            or row.get("arch") != "aarch64" or row.get("cpus") != 2
            or row.get("memory") != 4 * 1024**3 or row.get("disk") != 40 * 1024**3):
        raise EngineError("local_engine_instance_mismatch")
    config = row.get("config", {})
    # Lima 2.2.1 omits a nil mounts slice in list JSON, while template yq emits
    # null. Both mean no mounts; nonempty arrays remain a hard mismatch.
    if (config.get("mounts") not in (None, []) or config.get("ssh", {}).get("forwardAgent") is not False
            or config.get("ssh", {}).get("loadDotSSHPubKeys") is not False):
        raise EngineError("local_engine_instance_mismatch")
    configuration = directory / "lima.yaml"
    if not configuration.is_file() or configuration.is_symlink():
        raise EngineError("local_engine_instance_mismatch")
    if record is not None and record.get("instance_config_sha256") != _digest(configuration):
        raise EngineError("local_engine_instance_mismatch")
    return directory


def _canonical_configuration(path, lima_home):
    """Use the selected Lima's own parser to compare formatting-only rewrites."""
    result = _command(["limactl", "template", "yq", str(path), "to_json"],
                      env=_environment(lima_home))
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise EngineError("local_engine_configuration_unavailable")
    return value


def _validate_container(container):
    expected_digest = ENGINE_IMAGE.split("@", 1)[1]
    normalized = "registry.dagger.io/engine@" + expected_digest
    references = {ENGINE_IMAGE, normalized}
    if (not isinstance(container, list) or len(container) != 1
            or container[0].get("Config", {}).get("Image") not in references
            or container[0].get("ImageName") not in references
            or container[0].get("ImageDigest") != expected_digest
            or container[0].get("State", {}).get("Running") is not True):
        raise EngineError("local_engine_container_mismatch")


def _probe_worker(lima_home, row, cli, state_root):
    environment = _environment(lima_home)
    container = json.loads(_command([
        "limactl", "shell", "--workdir=/tmp", INSTANCE, "--", "sudo", "-n", "podman",
        "inspect", "--type", "container", "continuous-validation-dagger",
    ], timeout=60, env=environment).stdout)
    _validate_container(container)
    socket = Path(row["dir"]) / "sock/cvs-dagger.sock"
    if socket.is_symlink() or not socket.is_socket() or socket.stat().st_uid != os.geteuid():
        raise EngineError("local_engine_socket_unavailable")
    socket.chmod(0o600)
    probe = (
        "import json,platform,subprocess; "
        "print(json.dumps({'python_version':platform.python_version(),"
        "'uv_version':subprocess.check_output(['uv','--version'],text=True).split()[1],"
        "'git_version':subprocess.check_output(['git','--version'],text=True).strip()}))"
    )
    versions = json.loads(_command([
        "limactl", "shell", "--workdir=/tmp", INSTANCE, "--", "sudo", "-n", "podman",
        "run", "--rm", "--pull=missing", WORKLOAD_IMAGE, "python", "-c", probe,
    ], timeout=900, env=environment).stdout)
    if versions.get("python_version") != "3.14.0" or versions.get("uv_version") != "0.9.2" or not versions.get("git_version", "").startswith("git version "):
        raise EngineError("local_engine_workload_version_mismatch")
    podman = _command(["limactl", "shell", "--workdir=/tmp", INSTANCE, "--", "sudo", "-n", "podman", "--version"], env=environment).stdout.strip()
    if not re.fullmatch(r"podman version [0-9]+\.[0-9]+\.[0-9]+", podman):
        raise EngineError("local_engine_podman_version_unavailable")
    versions["podman_version"] = podman.removeprefix("podman version ")
    sdk_probe = (
        "import asyncio,json,sys,dagger; "
        "exec('async def probe():\\n async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:"
        "\\n  print(json.dumps({\"version\":await client.version(),\"platform\":await client.default_platform()}))'); "
        "asyncio.run(probe())"
    )
    identity = json.loads(_dagger_command([str(state_root / "sdk/bin/python"), "-c", sdk_probe],
                                          executable=cli["cli"], engine="unix://" + str(socket),
                                          timeout=90).stdout)
    if identity.get("version", "").removeprefix("v") != VERSION or identity.get("platform") != "linux/arm64":
        raise EngineError("local_engine_sdk_identity_mismatch")
    return versions


def setup(state_root: Path, lima_home: Path, *, enable_shadow=False):
    global _CURRENT_LOG
    if enable_shadow is not True:
        return {"schema_version": 1, "status": "unavailable", "diagnostic_codes": ["shadow_opt_in_required"]}
    try:
        host = _host_capability()
        state_root = _private_directory(state_root)
        lima_home = Path(lima_home).resolve(strict=True)
        descriptor = os.open(state_root / "setup.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = _inventory(lima_home)
            row = rows.get(INSTANCE)
            record_path = state_root / "ownership.json"
            record = _read_private(record_path) if record_path.exists() else None
            if row is not None and record is None:
                raise EngineError("local_engine_ownership_unavailable")
            if record is not None:
                if (record.get("owner") != OWNER or record.get("instance") != INSTANCE
                        or record.get("lima_home") != str(lima_home)
                        or record.get("template_sha256") != _digest(TEMPLATE)
                        or record.get("lima_version") != host["lima_version"]
                        or record.get("status") not in {"creating", "created", "ready"}):
                    raise EngineError("local_engine_ownership_unavailable")
                if row is None:
                    raise EngineError("local_engine_owned_instance_missing")
                if record["status"] == "creating" and not record.get("instance_config_sha256"):
                    directory = _validate_instance(lima_home, row)
                    expected = _canonical_configuration(TEMPLATE, lima_home)
                    actual = _canonical_configuration(directory / "lima.yaml", lima_home)
                    if actual != expected:
                        raise EngineError("local_engine_instance_mismatch")
                    record.update({"instance_config_sha256": _digest(directory / "lima.yaml"), "status": "created"})
                    _write_private(record_path, record)
                else:
                    _validate_instance(lima_home, row, record)
            log = state_root / "setup.log"
            if log.is_symlink() or (log.exists() and log.stat().st_nlink != 1):
                raise EngineError("local_engine_private_path_invalid")
            log.touch(mode=0o600)
            log.chmod(0o600)
            _CURRENT_LOG = log
            cli = _install_cli(state_root)
            _prepare_sdk(state_root, lima_home)
            environment = _environment(lima_home)
            if row is None:
                record = {"schema_version": 1, "owner": OWNER, "instance": INSTANCE,
                          "lima_home": str(lima_home), "template_sha256": _digest(TEMPLATE),
                          "lima_version": host["lima_version"], "status": "creating"}
                _write_private(record_path, record)
                _command(["limactl", "create", "--name=" + INSTANCE, "--mount-none", "--tty=false", str(TEMPLATE)],
                         timeout=900, env=environment)
                row = _inventory(lima_home).get(INSTANCE)
                if row is None:
                    raise EngineError("local_engine_created_instance_unavailable")
                directory = _validate_instance(lima_home, row)
                record.update({"instance_config_sha256": _digest(directory / "lima.yaml"), "status": "created"})
                _write_private(record_path, record)
            if row["status"] == "Stopped":
                _command(["limactl", "start", "--tty=false", INSTANCE], timeout=1800, env=environment)
                row = _inventory(lima_home).get(INSTANCE)
            if row is None or row.get("status") != "Running":
                raise EngineError("local_engine_not_running")
            _validate_instance(lima_home, row, record)
            versions = _probe_worker(lima_home, row, cli, state_root)
            if record.get("podman_version") and record["podman_version"] != versions["podman_version"]:
                raise EngineError("local_engine_podman_version_changed")
            record.update({"status": "ready", "podman_version": versions["podman_version"], **cli})
            _write_private(record_path, record)
            return {"schema_version": 1, "status": "ready", "diagnostic_codes": [],
                    "runtime": {**host, **versions, "dagger_version": VERSION, "platform": "linux/arm64"},
                    "dagger_helper_argv": [str(state_root / "sdk/bin/python"), str(Path(__file__).resolve().with_name("dagger_backend.py"))],
                    "backend_configuration": {"engine": "unix://" + str(Path(row["dir"]) / "sock/cvs-dagger.sock"),
                                              **cli, "image": WORKLOAD_IMAGE,
                                              "python_version": versions["python_version"], "uv_version": versions["uv_version"]}}
    except EngineError as error:
        return {"schema_version": 1, "status": "unavailable", "diagnostic_codes": [str(error)]}
    except Exception:
        return {"schema_version": 1, "status": "unavailable", "diagnostic_codes": ["local_engine_setup_unavailable"]}
    finally:
        _CURRENT_LOG = None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit optional local shadow engine")
    parser.add_argument("action", choices=("plan", "setup"))
    parser.add_argument("--enable-shadow", action="store_true")
    parser.add_argument("--state-root", type=Path, default=Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "dotfiles-ai/continuous-validation/engine")
    parser.add_argument("--lima-home", type=Path, default=Path(os.environ.get("LIMA_HOME", Path.home() / ".lima")))
    args = parser.parse_args(argv)
    result = plan() if args.action == "plan" else setup(args.state_root, args.lima_home, enable_shadow=args.enable_shadow)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"ready", "planned"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
