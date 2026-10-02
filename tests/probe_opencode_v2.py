"""Qualify only V2 CLI surfaces; never assert migration or deployment readiness."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time

TIMEOUT_SECONDS = 30
OUTPUT_LIMIT = 128 * 1024
COMMANDS = (
    ("version", ("--version",), ()),
    ("root_help", ("--help",), ("--standalone", "--server", "--auto", "--session")),
    ("debug_help", ("debug", "--help"), ("agents", "config", "paths")),
    ("session_help", ("session", "--help"), ("list", "export", "import")),
    ("service_help", ("service", "--help"), ("start", "stop", "restart", "status")),
    ("isolated_database_path", ("debug", "paths", "db"), ()),
)


class Failure(Exception):
    """An allowlisted public reason, never a raw subprocess/filesystem error."""


def result() -> dict:
    return {"schema_version": 1, "candidate": None, "status": "failed",
            "checks": {key: "not_run" for key in ("identity", *(item[0] for item in COMMANDS))},
            "continuation": "unavailable", "migration": "unavailable",
            "deployment": "unavailable", "reason": None}


def identity(path: Path) -> tuple:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o111:
            raise Failure("invalid_input")
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, digest


def directory_identity(info: os.stat_result) -> tuple[int, int]:
    if not stat.S_ISDIR(info.st_mode):
        raise Failure("cleanup_failed")
    return info.st_dev, info.st_ino


def run(binary: Path, args: tuple[str, ...], root: Path, env: dict[str, str]) -> str:
    try:
        process = subprocess.Popen([str(binary), *args], cwd=root, env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
    except OSError:
        raise Failure("spawn_failed") from None
    output = bytearray()
    deadline = time.monotonic() + TIMEOUT_SECONDS
    failure = None
    try:
        with selectors.DefaultSelector() as selector:
            for stream in (process.stdout, process.stderr):
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise Failure("timeout")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, min(65536, OUTPUT_LIMIT + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output.extend(chunk)
                    if len(output) > OUTPUT_LIMIT:
                        raise Failure("output_limit")
        if process.wait(timeout=max(0, deadline - time.monotonic())):
            raise Failure("command_failed")
    except subprocess.TimeoutExpired:
        failure = Failure("timeout")
    except Failure as error:
        failure = error
    except OSError:
        failure = Failure("command_failed")
    finally:
        # Until wait succeeds the child has not been reaped; its PID cannot be
        # recycled into an unrelated process group while cleanup signals it.
        if process.returncode is None:
            try:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                failure = failure or Failure("cleanup_failed")
        process.stdout.close()
        process.stderr.close()
    if failure:
        raise failure
    return output.decode("utf-8", errors="replace").strip()


def probe(*, binary: Path, sha256: str, expected_version: str, scratch: Path) -> dict:
    report = result()
    check = "identity"
    parent_fd = None
    root = None
    root_identity = None
    try:
        if (not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
                or not isinstance(expected_version, str) or len(expected_version) > 64
                or re.fullmatch(r"2\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", expected_version) is None):
            raise Failure("invalid_input")
        binary, scratch = Path(binary).absolute(), Path(scratch).absolute()
        if binary.is_symlink() or scratch.is_symlink():
            raise Failure("invalid_input")
        parent_fd = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parent_info = os.fstat(parent_fd)
        if parent_info.st_uid != os.getuid() or parent_info.st_mode & 0o022:
            raise Failure("invalid_input")
        parent_identity = directory_identity(parent_info)
        original = identity(binary)
        report["candidate"] = {"version": expected_version, "sha256": sha256}
        if original[-1] != sha256:
            raise Failure("candidate_mismatch")
        report["checks"][check] = "passed"
        root = Path(tempfile.mkdtemp(prefix="opencode-v2-", dir=scratch))
        root_identity = directory_identity(os.stat(root.name, dir_fd=parent_fd, follow_symlinks=False))
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "SHELL": "/bin/sh",
               "TERM": "dumb", "NO_COLOR": "1"}
        for key, relative in {
            "HOME": "home", "OPENCODE_TEST_HOME": "home",
            "OPENCODE_CONFIG_DIR": "config/opencode", "XDG_CONFIG_HOME": "config",
            "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state",
            "XDG_CACHE_HOME": "cache", "TMPDIR": "tmp",
        }.items():
            path = root / relative
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            env[key] = str(path)
        database = root / "data/opencode/opencode.db"
        for check, args, required in COMMANDS:
            if (directory_identity(scratch.lstat()) != parent_identity
                    or directory_identity(root.lstat()) != root_identity):
                raise Failure("cleanup_failed")
            output = run(binary, args, root, env)
            if check == "version" and output != f"opencode v{expected_version}":
                raise Failure("version_mismatch")
            if required and not set(required) <= set(re.findall(r"[^\s,]+", output)):
                raise Failure("help_contract")
            if check == "isolated_database_path" and (output != str(database) or os.path.lexists(database)):
                raise Failure("database_path")
            report["checks"][check] = "passed"
        check = "identity"
        try:
            if identity(binary) != original:
                raise Failure("candidate_mismatch")
        except (OSError, Failure):
            raise Failure("candidate_mismatch") from None
        report["status"] = "passed"
    except (Failure, OSError, ValueError, TypeError) as error:
        report["reason"] = str(error) if isinstance(error, Failure) else "invalid_input"
        report["checks"][check] = "failed"
        if report["reason"] == "invalid_input":
            report["candidate"] = None
    finally:
        if root is not None:
            try:
                if directory_identity(os.stat(root.name, dir_fd=parent_fd, follow_symlinks=False)) != root_identity:
                    raise Failure("cleanup_failed")
                # An anchored directory descriptor and stdlib's fd-safe removal
                # prevent cleanup from following a substituted scratch path.
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise Failure("cleanup_failed")
                shutil.rmtree(root.name, dir_fd=parent_fd)
            except (OSError, Failure):
                report["status"] = "failed"
                report["reason"] = report["reason"] or "cleanup_failed"
        if parent_fd is not None:
            os.close(parent_fd)
    return report


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Failure("invalid_input")


def main() -> int:
    parser = Parser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    try:
        report = probe(**vars(parser.parse_args()))
    except Failure:
        report = result()
        report["reason"] = "invalid_input"
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
