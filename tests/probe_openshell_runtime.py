"""Internal fail-fast probes for the credential-free OpenShell qualification.

This module is never installed. A probe result cannot qualify unperformed rows
of the runtime matrix. Preparation and retained-state retirement are separate.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import argparse
import errno
import hashlib
import importlib
import json
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import uuid


class Refusal(Exception):
    """A stable, public-safe refusal reason without paths or command output."""

    def __init__(self, reason: str, *, output_limit_bytes: int | None = None):
        super().__init__(reason)
        self.output_limit_bytes = output_limit_bytes


@dataclass(frozen=True)
class Selection:
    root: Path
    lima_sha256: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def parse_selection(raw: bytes) -> Selection:
    """Validate the closed private selection without executing commands."""
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise Refusal("invalid_selection")
    value = decode_object(raw)
    if set(value) != {"schema_version", "run_root", "lima_sha256"}:
        raise Refusal("invalid_selection")
    root, digest = value["run_root"], value["lima_sha256"]
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(root, str) or "\x00" in root or len(root) > 4096
            or not root.startswith("/") or str(Path(root)) != root
            or any(part in {".", "..", ""} for part in root.split("/")[1:])
            or re.fullmatch(r"openshell-q-[a-f0-9]{12}", Path(root).name) is None
            or not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None):
        raise Refusal("invalid_selection")
    return Selection(Path(root), digest)


def decode_object(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("duplicate_field")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal("invalid_selection") from None
    if not isinstance(value, dict):
        raise Refusal("invalid_selection")
    return value


def private_directory(path: Path) -> os.stat_result:
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or path.resolve(strict=True) != path):
        raise Refusal("unsafe_directory")
    return info


def private_file(path: Path, limit: int = 65536) -> bytes:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or info.st_size > limit):
            raise Refusal("unsafe_file")
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise Refusal("unsafe_file")
        return data


def validate_root(selection: Selection) -> None:
    """Check private owner-controlled, alias-free prepared fixture ownership."""
    try:
        # Revalidate even when an internal caller constructs the dataclass.
        parse_selection(json.dumps({"schema_version": 1, "run_root": str(selection.root),
                                    "lima_sha256": selection.lima_sha256}).encode())
        for relative in ("", "fixture", "fixture/main", "fixture/task", "evidence", "lima"):
            private_directory(selection.root / relative)
        value = decode_object(private_file(selection.root / "owner.json"))
        if (set(value) != {"schema_version", "run_id"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["run_id"] != selection.root.name):
            raise Refusal("owner_mismatch")
    except (OSError, ValueError, RuntimeError):
        raise Refusal("invalid_root") from None


@contextmanager
def _storage_guard_for_command(argv: list[str], cwd: Path, env: dict[str, str]):
    """Gate trusted Lima operations; this does not mediate arbitrary host tools."""
    if Path(argv[0]).name != "limactl":
        yield
        return
    # Closed recovery/inventory forms. Unknown verbs and global-option variants
    # cannot evade the storage gate as the upstream command surface grows.
    if tuple(argv[1:]) in {
        ("list",), ("list", "q"), ("list", "--json"), ("list", "q", "--json"),
        ("stop", "q"), ("delete", "q"), ("--yes", "delete", "q"), ("--version",),
    }:
        yield
        return
    lima_home = Path(env.get("LIMA_HOME", ""))
    run_root = lima_home.parent
    if (not lima_home.is_absolute() or str(lima_home) != env.get("LIMA_HOME")
            or ".." in lima_home.parts or lima_home.name != "lima"
            or not re.fullmatch(r"openshell-q-[a-f0-9]{12}", run_root.name)
            or run_root.parent.name != "qualification" or cwd != run_root
            or env.get("HOME") != str(run_root / "controller")
            or env.get("TMPDIR") != str(run_root / "controller/tmp")):
        raise Refusal("storage_route_unqualified")
    try:
        storage = importlib.import_module("probe_openshell_storage")
    except ImportError:
        raise Refusal("storage_enforcement_unavailable") from None
    try:
        with storage.allocation_guard(run_root.parent.parent):
            yield
    except storage.Refusal as error:
        raise Refusal(str(error)) from None


def run_command(argv: list[str], *, cwd: Path, env: dict[str, str],
                timeout: float = 60, limit: int = 1024 * 1024) -> CommandResult:
    """Bound owned child groups and both streams; retain nonzero exit status."""
    if (not isinstance(argv, list) or not argv or not all(isinstance(x, str) and "\x00" not in x for x in argv)
            or isinstance(timeout, bool) or not 0 < timeout <= 1800
            or type(limit) is not int or not 0 < limit <= 10 * 1024 * 1024):
        raise Refusal("invalid_command")
    with _storage_guard_for_command(argv, cwd, env):
        return _run_bounded_command(argv, cwd=cwd, env=env, timeout=timeout, limit=limit)


def _run_bounded_command(argv: list[str], *, cwd: Path, env: dict[str, str],
                         timeout: float, limit: int) -> CommandResult:
    """Run only after argument validation and applicable storage admission."""
    try:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except OSError:
        raise Refusal("spawn_failed") from None
    deadline = time.monotonic() + timeout
    stdout, stderr = bytearray(), bytearray()
    failure = None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, stdout)
            selector.register(process.stderr, selectors.EVENT_READ, stderr)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise Refusal("timeout")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, min(65536, limit + 1 - len(stdout) - len(stderr)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    key.data.extend(chunk)
                    if len(stdout) + len(stderr) > limit:
                        raise Refusal("output_limit", output_limit_bytes=limit)
            process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        failure = Refusal("timeout")
    except OSError:
        failure = Refusal("command_io_failed")
    except BaseException as error:
        failure = error
    finally:
        # Do not reap before draining: a dead parent may leave descendant pipes
        # open. Its unreaped PID keeps this owned process-group identity stable.
        if process.returncode is None:
            try:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                failure = failure or Refusal("termination_uncertain")
        process.stdout.close()
        process.stderr.close()
    if failure:
        raise failure
    return CommandResult(process.returncode, bytes(stdout), bytes(stderr))


_POINTER_OPERATIONS = ("write_open", "append", "truncate", "unlink", "rename", "replace", "hardlink")
_POINTER_SPELLINGS = (".git", ".GIT", ".GiT")
_POSITIVE_NAME = ".openshell-positive-control"
_POSITIVE_BYTES = b"openshell-pointer-positive-control\n"
_DENIAL_ERRNOS = {errno.EACCES, errno.EPERM, errno.EROFS, errno.EBUSY, errno.EXDEV}
_GUARD_OPERATIONS = ("setflags_clear", "fssetxattr_clear", "xattr_set", "chmod")
_GUARD_DENIAL_ERRNOS = {errno.EACCES, errno.EPERM, errno.EROFS}
# Probe results contain Linux guest errno values, not macOS controller values.
_GUARD_UNSUPPORTED_ERRNOS = {25, 95, 38}  # ENOTTY, EOPNOTSUPP, ENOSYS on Linux aarch64.


def _guard_stat(info: os.stat_result) -> dict:
    flags = getattr(info, "st_flags", None)
    if type(flags) is not int or flags < 0:
        raise Refusal("guard_flags_unavailable")
    return {"device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid,
            "link_count": info.st_nlink, "size": info.st_size, "mode": info.st_mode,
            "mtime_ns": info.st_mtime_ns, "flags": flags}


def _guard_snapshot(pointer: Path) -> dict:
    """Observe native file flags and bytes without following or changing links."""
    with os.fdopen(os.open(pointer, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        before = _guard_stat(os.fstat(stream.fileno()))
        if (not stat.S_ISREG(before["mode"]) or before["uid"] != os.getuid()
                or before["link_count"] != 1 or not 1 <= before["size"] <= 4096):
            raise Refusal("unsafe_guard_pointer")
        raw = stream.read(4097)
        after = _guard_stat(os.fstat(stream.fileno()))
        if before != after or len(raw) != before["size"]:
            raise Refusal("guard_observation_changed")
    return before | {"sha256": hashlib.sha256(raw).hexdigest()}


def _validate_guard(root: Path) -> dict:
    value = decode_object(private_file(root / "guard.json"))
    integer_fields = {"schema_version", "device", "inode", "uid", "link_count", "size",
                      "mode", "mtime_ns", "original_flags", "protected_flags"}
    if (set(value) != integer_fields | {"sha256"}
            or any(type(value[key]) is not int for key in integer_fields)
            or value["schema_version"] != 1 or value["device"] < 0 or value["inode"] <= 0
            or value["uid"] != os.getuid() or value["link_count"] != 1
            or not 1 <= value["size"] <= 4096 or not 0 <= value["mode"] <= 0o177777
            or not stat.S_ISREG(value["mode"]) or value["mtime_ns"] <= 0
            or value["original_flags"] != 0 or value["protected_flags"] != 2
            or not isinstance(value["sha256"], str)
            or re.fullmatch(r"[a-f0-9]{64}", value["sha256"]) is None):
        raise Refusal("invalid_guard")
    expected = {key: item for key, item in value.items()
                if key not in {"schema_version", "original_flags", "protected_flags"}}
    expected["flags"] = value["protected_flags"]
    if _guard_snapshot(root / "fixture/task/.git") != expected:
        raise Refusal("guard_mismatch")
    return expected


def _regular_identity(path: Path, limit: int) -> tuple:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_size > limit):
            raise Refusal("unsafe_fixture_file")
        digest, consumed = hashlib.sha256(), 0
        while chunk := stream.read(min(65536, limit + 1 - consumed)):
            consumed += len(chunk)
            if consumed > limit:
                raise Refusal("fixture_limit")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        if ((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                or consumed != info.st_size):
            raise Refusal("fixture_changed")
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, digest.hexdigest()


def _metadata_snapshot(root: Path) -> dict:
    """Observe bounded native metadata without following links or opening hooks."""
    found = {}
    count, total = 0, 0
    pending = [root]
    while pending:
        path = pending.pop()
        info = path.lstat()
        count += 1
        if count > 4096 or info.st_uid != os.getuid():
            raise Refusal("fixture_limit")
        relative = path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):
            found[relative] = (info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns)
            with os.scandir(path) as entries:
                for entry in entries:
                    if count + len(pending) >= 4096:
                        raise Refusal("fixture_limit")
                    pending.append(path / entry.name)
        elif stat.S_ISREG(info.st_mode):
            total += info.st_size
            if total > 64 * 1024 * 1024:
                raise Refusal("fixture_limit")
            found[relative] = _regular_identity(path, 64 * 1024 * 1024)
        else:
            raise Refusal("fixture_alias")
    return found


def _controller_environment(root: Path) -> dict[str, str]:
    private_directory(root / "controller")
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(root / "controller"),
           "LIMA_HOME": str(root / "lima"), "LC_ALL": "C", "TERM": "dumb", "NO_COLOR": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0"}
    for name, relative in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                           ("XDG_STATE_HOME", "state"), ("XDG_CACHE_HOME", "cache"),
                           ("TMPDIR", "tmp")):
        path = root / "controller" / relative
        private_directory(path)
        env[name] = str(path)
    return env


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Refusal("timeout")
    return min(60, remaining)


def _prepared_deadline(root: Path) -> float:
    private_file(root / "prepared.json")
    age = time.time() - (root / "prepared.json").lstat().st_mtime
    if not 0 <= age < 900:
        raise Refusal("experiment_deadline")
    return time.monotonic() + 900 - age


_GENERATION_FIELDS = ("sandbox_id", "main_process_instance_id", "main_process_started_at_ms",
                      "container_id", "pid", "container_started_at", "policy_hash", "policy_version",
                      "config_revision", "provider_env_revision", "current_policy_version")


def _validate_generation(root: Path) -> tuple[tuple, str]:
    private_directory(root.parent)
    prepared = decode_object(private_file(root / "prepared.json"))
    value = decode_object(private_file(root / "generation.json"))
    if (set(prepared) != {"schema_version", "sandbox_id", "container_id"}
            or type(prepared["schema_version"]) is not int or prepared["schema_version"] != 1
            or set(value) != {"schema_version", "identity"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["identity"], dict) or set(value["identity"]) != set(_GENERATION_FIELDS)):
        raise Refusal("invalid_generation")
    identity = value["identity"]
    for key in ("main_process_started_at_ms", "pid", "policy_version", "config_revision",
                "provider_env_revision", "current_policy_version"):
        if type(identity[key]) is not int or identity[key] <= 0:
            raise Refusal("invalid_generation")
    for key in ("main_process_instance_id", "container_started_at"):
        if not isinstance(identity[key], str) or not 1 <= len(identity[key]) <= 256 or not identity[key].isprintable():
            raise Refusal("invalid_generation")
    for key in ("container_id", "policy_hash"):
        if not isinstance(identity[key], str) or re.fullmatch(r"[0-9a-f]{64}", identity[key]) is None:
            raise Refusal("invalid_generation")
    try:
        if not isinstance(identity["sandbox_id"], str) or str(uuid.UUID(identity["sandbox_id"])) != identity["sandbox_id"]:
            raise ValueError
    except ValueError:
        raise Refusal("invalid_generation") from None
    if (identity["sandbox_id"] != prepared["sandbox_id"] or identity["container_id"] != prepared["container_id"]
            or identity["current_policy_version"] != identity["policy_version"]):
        raise Refusal("invalid_generation")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return tuple(identity[key] for key in _GENERATION_FIELDS), hashlib.sha256(canonical).hexdigest()


def _record_truncation(report: dict, error: Refusal) -> None:
    if str(error) == "output_limit":
        report["truncation"] = {"transport_output": True, "limit_bytes": error.output_limit_bytes}


def _host_git_fixture(root: Path, env: dict[str, str], deadline: float) -> tuple[Path, Path]:
    main, task = root / "fixture/main", root / "fixture/task"
    common = main / ".git"
    if not common.is_dir() or common.resolve(strict=True) != common:
        raise Refusal("fixture_membership")
    pointer = task / ".git"
    _regular_identity(pointer, 4096)
    with pointer.open("rb") as stream:
        pointer_bytes = stream.read(4097)
    if len(pointer_bytes) > 4096:
        raise Refusal("fixture_limit")
    if not pointer_bytes.startswith(b"gitdir: ") or not pointer_bytes.endswith(b"\n"):
        raise Refusal("fixture_membership")
    try:
        admin = Path(pointer_bytes[8:-1].decode("utf-8"))
    except UnicodeError:
        raise Refusal("fixture_membership") from None
    if (not admin.is_absolute() or admin.resolve(strict=True) != admin
            or admin.parent != common / "worktrees" or not admin.is_dir()):
        raise Refusal("fixture_membership")
    for option, expected in (("--git-common-dir", common), ("--git-dir", admin)):
        result = run_command(["/usr/bin/git", "-C", str(task), "rev-parse", "--path-format=absolute", option],
                             cwd=root, env=env, timeout=_remaining(deadline), limit=16384)
        if result.returncode or result.stdout.rstrip(b"\n") != os.fsencode(expected):
            raise Refusal("fixture_membership")
    result = run_command(["/usr/bin/git", "-C", str(main), "worktree", "list", "--porcelain", "-z"],
                         cwd=root, env=env, timeout=_remaining(deadline), limit=65536)
    records = result.stdout.split(b"\0\0")
    registered = [x.split(b"\0", 1)[0][9:] for x in records if x.startswith(b"worktree ")]
    if result.returncode or registered.count(os.fsencode(task)) != 1 or registered.count(os.fsencode(main)) != 1:
        raise Refusal("fixture_membership")
    return common, pointer


class _PointerController:
    """Only fixed native commands for an already prepared, exact enrollment."""

    def __init__(self, selection: Selection, deadline: float):
        self.root, self.deadline = selection.root, deadline
        self.sandbox_name = self.root.name.removeprefix("openshell-")
        self.env = _controller_environment(self.root)
        self.binary = Path("/opt/homebrew/bin/limactl").resolve(strict=True)
        self.binary_identity = _regular_identity(self.binary, 256 * 1024 * 1024)
        if self.binary_identity[-1] != selection.lima_sha256:
            raise Refusal("lima_identity")
        if not self.binary_identity[2] & 0o111:
            raise Refusal("lima_identity")
        private_directory(self.root / "lima/q")
        self.prepared = decode_object(private_file(self.root / "prepared.json"))
        p = self.prepared
        if (set(p) != {"schema_version", "sandbox_id", "container_id"}
                or type(p["schema_version"]) is not int or p["schema_version"] != 1
                or not isinstance(p["sandbox_id"], str)
                or not isinstance(p["container_id"], str)
                or re.fullmatch(r"[0-9a-f]{64}", p["container_id"]) is None):
            raise Refusal("invalid_preparation")
        try:
            if str(uuid.UUID(p["sandbox_id"])) != p["sandbox_id"]:
                raise ValueError
        except ValueError:
            raise Refusal("invalid_preparation") from None
        home = self._lima(["/usr/bin/printenv", "HOME"], deadline).stdout.strip()
        uid = self._lima(["/usr/bin/id", "-u"], deadline).stdout.strip()
        if not re.fullmatch(rb"/home/[A-Za-z0-9_.-]+", home) or not re.fullmatch(rb"[1-9][0-9]{0,9}", uid):
            raise Refusal("guest_identity")
        self.guest_home, self.guest_uid = home.decode(), int(uid)
        self.guest_env = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin",
                          "HOME=" + home.decode(), "XDG_CONFIG_HOME=" + home.decode() + "/.config",
                          "XDG_DATA_HOME=" + home.decode() + "/.local/share",
                          "XDG_STATE_HOME=" + home.decode() + "/.local/state",
                          "XDG_CACHE_HOME=" + home.decode() + "/.cache",
                          "XDG_RUNTIME_DIR=/run/user/" + uid.decode(), "LC_ALL=C", "TERM=dumb",
                          "NO_COLOR=1", "OPENSHELL_TELEMETRY_ENABLED=false"]

    def _lima(self, args: list[str], deadline: float) -> CommandResult:
        if _regular_identity(self.binary, 256 * 1024 * 1024) != self.binary_identity:
            raise Refusal("lima_identity")
        result = run_command([str(self.binary), "shell", "--workdir", "/", "q", "--", *args],
                             cwd=self.root, env=self.env,
                             timeout=_remaining(min(deadline, self.deadline)), limit=1024 * 1024)
        if result.returncode:
            raise Refusal("native_command_failed")
        return result

    def guest(self, args: list[str], deadline: float) -> CommandResult:
        return self._lima([*self.guest_env, *args], deadline)

    def identity(self, deadline: float) -> tuple:
        # Pinned CLI source run.rs:sandbox_detail_to_json emits a flat object.
        sandbox = decode_object(self.guest(["/usr/bin/openshell", "sandbox", "get",
                                           self.sandbox_name, "-o", "json"], deadline).stdout)
        if (sandbox.get("id") != self.prepared["sandbox_id"] or sandbox.get("name") != self.sandbox_name
                or sandbox.get("phase") != "Ready" or sandbox.get("restart_policy") != "never"
                or not isinstance(sandbox.get("main_process_instance_id"), str)
                or not sandbox["main_process_instance_id"]
                or type(sandbox.get("main_process_started_at_ms")) is not int
                or sandbox["main_process_started_at_ms"] <= 0
                or type(sandbox.get("restart_count")) is not int or sandbox["restart_count"] != 0):
            raise Refusal("sandbox_identity")
        admission = sandbox.get("configuration_admission")
        if (not isinstance(admission, dict) or admission.get("state") != "accepted"
                or not isinstance(admission.get("policy_hash"), str)
                or re.fullmatch(r"[0-9a-f]{64}", admission["policy_hash"]) is None
                or any(type(admission.get(key)) is not int or admission[key] <= 0
                       for key in ("policy_version", "config_revision", "provider_env_revision"))
                or type(sandbox.get("current_policy_version")) is not int
                or sandbox["current_policy_version"] != admission["policy_version"]):
            raise Refusal("sandbox_identity")
        result = self.guest(["/usr/bin/podman", "inspect", "--type", "container",
                             self.prepared["container_id"]], deadline)
        try:
            items = json.loads(result.stdout)
            if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
                raise ValueError
            item = items[0]
            state, labels = item["State"], item["Config"]["Labels"]
            if (item.get("Id") != self.prepared["container_id"] or state.get("Running") is not True
                    or state.get("Paused") is not False or type(state.get("Pid")) is not int
                    or state["Pid"] <= 0 or not isinstance(state.get("StartedAt"), str)
                    or not state["StartedAt"] or labels.get("openshell.managed") != "true"
                    or labels.get("openshell.ai/isolation-role") != "sandbox"
                    or labels.get("openshell.ai/sandbox-id") != self.prepared["sandbox_id"]):
                raise ValueError
        except (ValueError, TypeError, KeyError, UnicodeError, AttributeError):
            raise Refusal("container_identity") from None
        return (sandbox["id"], sandbox["main_process_instance_id"], sandbox["main_process_started_at_ms"],
                item["Id"], state["Pid"], state["StartedAt"], admission["policy_hash"],
                admission["policy_version"], admission["config_revision"],
                admission["provider_env_revision"], sandbox["current_policy_version"])

    def execute(self, program: str, deadline: float) -> dict:
        result = self.guest(["/usr/bin/openshell", "sandbox", "exec", "--name", self.sandbox_name,
                             "--workdir", "/work", "--no-tty", "--no-login-shell", "--timeout", "50", "--",
                             "python3", "-I", "-B", "-c", program], deadline)
        if len(result.stdout) > 4096:
            raise Refusal("invalid_probe_output")
        try:
            return decode_object(result.stdout)
        except Refusal:
            raise Refusal("invalid_probe_output") from None


def _pointer_program(operation: str, spelling: str) -> str:
    if operation not in _POINTER_OPERATIONS or spelling not in _POINTER_SPELLINGS:
        raise Refusal("invalid_probe")
    # Numeric ordinals keep retained destinations distinct on case-insensitive hosts.
    extra = f"/work/.openshell-{operation}-{_POINTER_SPELLINGS.index(spelling)}"
    # Only these compile-time operation/spelling enums enter the program.
    return """import errno,json,os,stat
operation,spelling = %r,%r
target='/work/'+spelling
extra=%r
out={'schema_version':1,'operation':operation,'spelling':spelling,'outcome':'unavailable','errno':0}
attempted=False
try:
    if not stat.S_ISREG(os.lstat(target).st_mode):
        raise RuntimeError('not_pointer')
    if operation=='write_open':
        attempted=True
        fd=os.open(target,os.O_WRONLY);os.close(fd)
    elif operation=='append':
        attempted=True
        fd=os.open(target,os.O_WRONLY|os.O_APPEND);os.write(fd,b'probe');os.close(fd)
    elif operation=='truncate':
        attempted=True
        fd=os.open(target,os.O_WRONLY|os.O_TRUNC);os.close(fd)
    elif operation=='unlink':
        attempted=True
        os.unlink(target)
    elif operation=='rename':
        if os.path.lexists(extra):raise RuntimeError('collision')
        attempted=True
        os.rename(target,extra)
    elif operation=='replace':
        fd=os.open(extra,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,b'probe');os.close(fd)
        attempted=True
        os.replace(extra,target)
    elif operation=='hardlink':
        attempted=True
        os.link(target,extra)
    out['outcome']='succeeded'
except OSError as error:
    out['errno']=error.errno
    if attempted and error.errno in (errno.EACCES,errno.EPERM,errno.EROFS,errno.EBUSY,errno.EXDEV):out['outcome']='denied'
except RuntimeError:
    pass
print(json.dumps(out,sort_keys=True))
""" % (operation, spelling, extra)


def _guard_program(operation: str, spelling: str) -> str:
    if operation not in _GUARD_OPERATIONS or spelling not in _POINTER_SPELLINGS:
        raise Refusal("invalid_probe")
    # These Linux aarch64 ioctl requests are fixed; no caller controls a payload.
    return """import errno,fcntl,json,os,stat
operation,spelling = %r,%r
target='/work/'+spelling
out={'schema_version':1,'operation':operation,'spelling':spelling,'outcome':'unavailable','errno':0}
attempted=False
fd=None
try:
    if not stat.S_ISREG(os.lstat(target).st_mode):
        raise RuntimeError('not_pointer')
    if operation in ('setflags_clear','fssetxattr_clear'):
        fd=os.open(target,os.O_RDONLY|os.O_NOFOLLOW)
        request,payload=(0x40086602,bytes(8)) if operation=='setflags_clear' else (0x401c5820,bytes(28))
        attempted=True
        fcntl.ioctl(fd,request,payload)
    elif operation=='xattr_set':
        attempted=True
        os.setxattr(target,'user.openshell_qualification',b'probe',follow_symlinks=False)
    elif operation=='chmod':
        attempted=True
        os.chmod(target,0o600,follow_symlinks=False)
    out['outcome']='succeeded'
except OSError as error:
    out['errno']=error.errno
    if attempted and error.errno in (errno.EACCES,errno.EPERM,errno.EROFS):
        out['outcome']='denied'
    elif attempted and operation!='chmod' and error.errno in (errno.ENOTTY,errno.EOPNOTSUPP,errno.ENOSYS):
        out['outcome']='unsupported'
except RuntimeError:
    pass
finally:
    if fd is not None:
        os.close(fd)
print(json.dumps(out,sort_keys=True))
""" % (operation, spelling)


def _check_pointer_evidence(root: Path, allowance: int, entries: int) -> Path:
    private_directory(root.parent)
    total, current, found = 0, 0, False
    for root_count, candidate in enumerate(root.parent.iterdir()):
        if root_count >= 4096:
            raise Refusal("evidence_limit")
        if re.fullmatch(r"openshell-q-[a-f0-9]{12}", candidate.name) is None:
            continue
        private_directory(candidate)
        owner = decode_object(private_file(candidate / "owner.json"))
        if (set(owner) != {"schema_version", "run_id"}
                or type(owner["schema_version"]) is not int or owner["schema_version"] != 1
                or owner["run_id"] != candidate.name):
            raise Refusal("owner_mismatch")
        directory = candidate / "evidence"
        private_directory(directory)
        retained = 0
        for count, path in enumerate(directory.iterdir()):
            if count + (entries if candidate == root else 0) >= 4096:
                raise Refusal("evidence_limit")
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise Refusal("unsafe_evidence")
            retained += info.st_size
        total += retained
        if candidate == root:
            current, found = retained, True
    if not found or current + allowance > 10 * 1024 * 1024 or total + allowance > 100 * 1024 * 1024:
        raise Refusal("evidence_limit")
    return root / "evidence"


def _write_pointer_evidence(root: Path, report: dict) -> None:
    raw = (json.dumps(report, sort_keys=True) + "\n").encode()
    if len(raw) > 64 * 1024:
        raise Refusal("evidence_limit")
    directory = _check_pointer_evidence(root, len(raw), 1)
    fd = os.open(directory / ("pointer-" + uuid.uuid4().hex + ".json"),
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _run_pointer_probe(selection: Selection, immutable: bool) -> dict:
    """Run fixed observations; immutable admission never changes native flags."""
    report = {"schema_version": 1, "probe": "immutable_git_pointer" if immutable else "git_pointer",
              "status": "unavailable", "reason": None,
              "runtime_qualification": "not_run", "checks": [], "retained": False,
              "generation_sha256": None, "truncation": {"transport_output": False, "limit_bytes": None}}
    admitted, active = False, None
    try:
        validate_root(selection)
        deadline = _prepared_deadline(selection.root)
        generation, report["generation_sha256"] = _validate_generation(selection.root)
        admitted = True
        guard = _validate_guard(selection.root) if immutable else None
        # Reserve the complete bounded probe budget before any workload effect.
        _check_pointer_evidence(selection.root, 256 * 1024, 48 if immutable else 32)
        controller = _PointerController(selection, deadline)
        common, pointer = _host_git_fixture(selection.root, controller.env, deadline)
        baseline = (_regular_identity(pointer, 4096), _metadata_snapshot(common))
        if controller.identity(min(deadline, time.monotonic() + 60)) != generation:
            raise Refusal("sandbox_identity")
        task = selection.root / "fixture/task"
        # Reject pre-existing probe outputs and source aliases before effects.
        _metadata_snapshot(task)
        for entry in task.iterdir():
            if entry.name.startswith(".openshell-"):
                raise Refusal("probe_collision")
        aliases = []
        for spelling in _POINTER_SPELLINGS:
            path = task / spelling
            try:
                info = path.lstat()
            except FileNotFoundError:
                report["checks"].append({"spelling": spelling, "status": "not_alias"})
                continue
            if (info.st_dev, info.st_ino) != baseline[0][:2]:
                raise Refusal("fixture_alias")
            aliases.append(spelling)

        def unchanged() -> None:
            try:
                validate_root(selection)
                current = (_regular_identity(pointer, 4096), _metadata_snapshot(common))
                if current != baseline or (guard is not None and _guard_snapshot(pointer) != guard):
                    raise Refusal("protected_state_changed")
            except (OSError, Refusal):
                raise Refusal("protected_state_changed") from None

        step_deadline = min(deadline, time.monotonic() + 60)
        active = {"operation": "source_write"}
        unchanged()
        if controller.identity(step_deadline) != generation:
            raise Refusal("sandbox_identity")
        try:
            positive = controller.execute("import json,os\n"
                                          "p='/work/.openshell-positive-control'\n"
                                          "fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n"
                                          "os.write(fd,b'openshell-pointer-positive-control\\n');os.fsync(fd);os.close(fd)\n"
                                          "print(json.dumps({'schema_version':1,'positive':'written'}))", step_deadline)
        finally:
            # Remote failures cannot suppress an authoritative host observation.
            unchanged()
            if controller.identity(step_deadline) != generation:
                raise Refusal("sandbox_identity")
        if (type(positive.get("schema_version")) is not int
                or positive != {"schema_version": 1, "positive": "written"}
                or _regular_identity(task / _POSITIVE_NAME, 4096)[3] != len(_POSITIVE_BYTES)
                or (task / _POSITIVE_NAME).read_bytes() != _POSITIVE_BYTES):
            raise Refusal("positive_control_failed")
        report["checks"].append({"operation": "source_write", "status": "passed"})
        active = None
        _write_pointer_evidence(selection.root, report)
        groups = [(_GUARD_OPERATIONS, True)] if immutable else []
        groups.append((_POINTER_OPERATIONS, False))
        for operations, is_guard in groups:
            for spelling, operation in ((spelling, operation) for spelling in aliases for operation in operations):
                step_deadline = min(deadline, time.monotonic() + 60)
                unchanged()
                if controller.identity(step_deadline) != generation:
                    raise Refusal("sandbox_identity")
                active = {"operation": operation, "spelling": spelling}
                try:
                    program = _guard_program(operation, spelling) if is_guard else _pointer_program(operation, spelling)
                    result = controller.execute(program, step_deadline)
                finally:
                    unchanged()
                    if controller.identity(step_deadline) != generation:
                        raise Refusal("sandbox_identity")
                if (set(result) != {"schema_version", "operation", "spelling", "outcome", "errno"}
                        or type(result["schema_version"]) is not int or result["schema_version"] != 1
                        or result["operation"] != operation or result["spelling"] != spelling
                        or type(result["errno"]) is not int or result["errno"] < 0
                        or result["outcome"] not in ({"denied", "succeeded", "unavailable", "unsupported"}
                                                     if is_guard else {"denied", "succeeded", "unavailable"})
                        or (result["outcome"] == "denied" and result["errno"] not in
                            (_GUARD_DENIAL_ERRNOS if is_guard else _DENIAL_ERRNOS))
                        or (result["outcome"] == "unsupported" and
                            (operation == "chmod" or result["errno"] not in _GUARD_UNSUPPORTED_ERRNOS))
                        or (result["outcome"] == "succeeded" and result["errno"] != 0)):
                    raise Refusal("invalid_probe_output")
                outcome = ("succeeded_guard_intact" if is_guard and result["outcome"] == "succeeded"
                           else result["outcome"])
                report["checks"].append({"operation": operation, "spelling": spelling,
                                          "status": outcome, "errno": result["errno"]})
                active = None
                _write_pointer_evidence(selection.root, report)
                if not is_guard and result["outcome"] == "succeeded":
                    raise Refusal("pointer_operation_allowed")
                if result["outcome"] == "unavailable":
                    raise Refusal("pointer_operation_unobserved")
        report["status"] = "passed"
    except Refusal as error:
        _record_truncation(report, error)
        report["reason"] = str(error)
        if str(error) in {"pointer_operation_allowed", "protected_state_changed", "positive_control_failed"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "native_observation_unavailable"
    if active is not None:
        report["checks"].append({**active, "status": report["status"], "reason": report["reason"]})
    if admitted:
        try:
            report["retained"] = True
            _write_pointer_evidence(selection.root, report)
        except (OSError, Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"] = "unavailable"
                report["reason"] = "evidence_retention_failed"
    return report


def pointer_probe(selection: Selection) -> dict:
    """Observe the original bind-mounted pointer candidate without rollout claims."""
    return _run_pointer_probe(selection, immutable=False)


def immutable_pointer_probe(selection: Selection) -> dict:
    """Observe a separately prepared immutable guard without applying or repairing it."""
    return _run_pointer_probe(selection, immutable=True)


_CONTAINMENT_TEXT = b"OpenShell containment text: caf\xc3\xa9\n"
_CONTAINMENT_BINARY = bytes(range(256))
_CONTAINMENT_EXECUTABLE = b"#!/bin/sh\nexit 0\n"
_CONTAINMENT_MARKER = b"openshell-nonfunctional-host-marker\n"
_CONTAINMENT_TARGETS = ("host_sentinel", "controller_home", "podman_socket", "environment",
                        "internal_control", "bootstrap")


def _validate_containment(root: Path) -> None:
    private_directory(root / "input")
    value = decode_object(private_file(root / "containment.json"))
    if (set(value) != {"schema_version", "marker_sha256"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["marker_sha256"] != hashlib.sha256(_CONTAINMENT_MARKER).hexdigest()
            or private_file(root / "input/host-sentinel", 1024) != _CONTAINMENT_MARKER):
        raise Refusal("invalid_containment")


def _validate_containment_resources(value: dict) -> dict:
    integers = {"cpu_quota", "cpu_period", "memory_max", "pids_max", "pids_current", "scratch_size"}
    if (not isinstance(value, dict) or set(value) != integers | {"scratch_rw"}
            or any(type(value[key]) is not int for key in integers)
            or value["scratch_rw"] is not True):
        raise Refusal("invalid_resource_observation")
    if (not 0 < value["cpu_quota"] <= 2 * value["cpu_period"]
            or not 0 < value["memory_max"] <= 2147483648
            or not 0 < value["pids_max"] <= 256
            or not 0 <= value["pids_current"] <= value["pids_max"]
            or not 0 < value["scratch_size"] <= 268435456):
        raise Refusal("resource_limits")
    return value


def _native_containment_observation(controller, deadline: float) -> dict:
    identity = controller.identity(deadline)
    pid = identity[4]
    if type(pid) is not int or pid <= 0:
        raise Refusal("container_identity")
    program = """import json,os,pathlib,re,stat,sys
pid,root,uid=sys.argv[1:]
def read(path,limit=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError()
        data=stream.read(limit+1)
    if len(data)>limit:raise ValueError()
    return data
try:
    if read(root+'/input/host-sentinel',1024)!=b'openshell-nonfunctional-host-marker\\n':raise ValueError()
    socket=os.lstat('/run/user/'+uid+'/podman/podman.sock')
    if not stat.S_ISSOCK(socket.st_mode) or socket.st_uid!=int(uid):raise ValueError()
    group=read('/proc/'+pid+'/cgroup',4096).decode().splitlines()
    if len(group)!=1 or not group[0].startswith('0::/'):raise ValueError()
    relative=group[0][3:]
    if '..' in relative.split('/'):raise ValueError()
    base=pathlib.Path('/sys/fs/cgroup'+relative).resolve(strict=True)
    if not base.is_relative_to('/sys/fs/cgroup'):raise ValueError()
    quota,period=map(int,read(base/'cpu.max',128).split())
    values={'cpu_quota':quota,'cpu_period':period}
    for name in ('memory.max','pids.max','pids.current'):
        values[name.replace('.','_')]=int(read(base/name,128))
    matches=[]
    for line in read('/proc/'+pid+'/mountinfo',262144).decode().splitlines():
        before,after=line.split(' - ',1);left,right=before.split(),after.split()
        if left[4]=='/scratch':matches.append((left,right))
    if len(matches)!=1:raise ValueError()
    left,right=matches[0]
    if right[0]!='tmpfs':raise ValueError()
    sizes=[x[5:] for x in right[2].split(',') if x.startswith('size=')]
    if len(sizes)!=1:raise ValueError()
    match=re.fullmatch(r'([0-9]+)([kKmMgG]?)',sizes[0])
    if match is None:raise ValueError()
    values['scratch_size']=int(match[1])*({'':1,'k':1024,'m':1048576,'g':1073741824}[match[2].lower()])
    values['scratch_rw']='rw' in left[5].split(',') and 'rw' in right[2].split(',')
    print(json.dumps(values,sort_keys=True))
except (OSError,ValueError,IndexError,UnicodeError):
    print(json.dumps({'error':'native_observation_unavailable'}))
"""
    result = controller.guest(["/usr/bin/python3", "-I", "-B", "-c", program, str(pid),
                               str(controller.root), str(controller.guest_uid)], deadline)
    return _validate_containment_resources(decode_object(result.stdout))


def _containment_program(operation: str, controller) -> str:
    if operation not in {"source_create", "source_delete", "exclusions", "scratch_write"}:
        raise Refusal("invalid_probe")
    head = "import errno,json,os,socket\noperation,spelling=%r,''\n" % operation
    if operation == "source_create":
        return head + """base='/work/.openshell-containment'
os.mkdir(base,0o700)
for name,data in %r:
    fd=os.open(base+'/'+name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.write(fd,data);os.fsync(fd);os.close(fd)
os.chmod(base+'/executable',0o755)
print(json.dumps({'schema_version':1,'operation':operation,'outcome':'succeeded'}))
""" % ((('text', _CONTAINMENT_TEXT), ('binary', _CONTAINMENT_BINARY),
          ('delete-me', b'delete-me\n'), ('executable', _CONTAINMENT_EXECUTABLE)),)
    if operation == "source_delete":
        return head + "os.unlink('/work/.openshell-containment/delete-me')\nprint(json.dumps({'schema_version':1,'operation':operation,'outcome':'succeeded'}))\n"
    if operation == "scratch_write":
        return head + """fd=os.open('/scratch/.openshell-containment',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
os.write(fd,b'scratch\\n');os.fsync(fd);os.lseek(fd,0,os.SEEK_SET)
if os.read(fd,32)!=b'scratch\\n':raise RuntimeError('scratch_mismatch')
os.close(fd)
print(json.dumps({'schema_version':1,'operation':operation,'outcome':'succeeded'}))
"""
    paths = (("host_sentinel", str(controller.root / "input/host-sentinel"), "file"),
             ("controller_home", controller.guest_home, "directory"),
             ("podman_socket", f"/run/user/{controller.guest_uid}/podman/podman.sock", "socket"),
             ("environment", "OPENSHELL_QUALIFICATION_SENTINEL", "environment"),
             ("internal_control", "/.openshell/channel/control", "directory"),
             ("bootstrap", "/.openshell/channel/sandbox/bootstrap.json", "file"))
    return head + """checks=[]
for target,path,kind in %r:
    item={'target':target,'outcome':'unavailable','errno':0}
    try:
        if kind=='environment':
            item['outcome']='absent' if path not in os.environ else 'exposed'
        else:
            if kind=='directory':
                with os.scandir(path) as entries:next(entries,None)
            elif kind=='socket':
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
                    stream.settimeout(1);stream.connect(path)
            else:
                fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                try:os.read(fd,1)
                finally:os.close(fd)
            item['outcome']='exposed'
    except OSError as error:
        item['errno']=error.errno or 0
        if error.errno in (errno.ENOENT,errno.EACCES,errno.EPERM):item['outcome']='inaccessible'
    checks.append(item)
print(json.dumps({'schema_version':1,'operation':operation,'checks':checks}))
""" % (paths,)


def _validate_containment_exclusions(value: dict) -> list:
    if (set(value) != {"schema_version", "operation", "checks"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["operation"] != "exclusions" or not isinstance(value["checks"], list)
            or len(value["checks"]) != len(_CONTAINMENT_TARGETS)):
        raise Refusal("invalid_exclusion_observation")
    for row, target in zip(value["checks"], _CONTAINMENT_TARGETS):
        if (not isinstance(row, dict) or set(row) != {"target", "outcome", "errno"}
                or row["target"] != target or type(row["errno"]) is not int):
            raise Refusal("invalid_exclusion_observation")
        if row["outcome"] == "exposed":
            raise Refusal("containment_access")
        if ((target == "environment" and (row["outcome"] != "absent" or row["errno"] != 0))
                or (target != "environment" and (row["outcome"] != "inaccessible" or row["errno"] not in {1, 2, 13}))):
            raise Refusal("exclusion_unavailable")
    return value["checks"]


def containment_probe(selection: Selection) -> dict:
    report = {"schema_version": 1, "probe": "containment", "status": "unavailable", "reason": None,
              "runtime_qualification": "not_run", "checks": [], "resources": {}, "retained": False,
              "generation_sha256": None, "truncation": {"transport_output": False, "limit_bytes": None}}
    admitted = False
    try:
        validate_root(selection)
        deadline = _prepared_deadline(selection.root)
        generation, report["generation_sha256"] = _validate_generation(selection.root)
        admitted = True
        guard = _validate_guard(selection.root)
        _validate_containment(selection.root)
        _check_pointer_evidence(selection.root, 256 * 1024, 16)
        output = selection.root / "fixture/task/.openshell-containment"
        if os.path.lexists(output):
            raise Refusal("probe_collision")
        controller = _PointerController(selection, deadline)
        common, pointer = _host_git_fixture(selection.root, controller.env, deadline)
        baseline = _metadata_snapshot(common)
        if controller.identity(min(deadline, time.monotonic() + 60)) != generation:
            raise Refusal("sandbox_identity")

        def unchanged():
            try:
                validate_root(selection)
                if _guard_snapshot(pointer) != guard or _metadata_snapshot(common) != baseline:
                    raise Refusal("protected_state_changed")
            except (OSError, Refusal):
                raise Refusal("protected_state_changed") from None

        def checked(call):
            _remaining(deadline)
            step = min(deadline, time.monotonic() + 60)
            unchanged()
            if controller.identity(step) != generation:
                raise Refusal("sandbox_identity")
            try:
                value = call(step)
            finally:
                unchanged()
                if controller.identity(step) != generation:
                    raise Refusal("sandbox_identity")
            return value

        report["resources"] = checked(lambda step: _native_containment_observation(controller, step))
        for operation in ("source_create", "source_delete", "exclusions", "scratch_write"):
            result = checked(lambda step: controller.execute(_containment_program(operation, controller), step))
            if operation == "exclusions":
                report["checks"].extend(_validate_containment_exclusions(result))
            else:
                if (type(result.get("schema_version")) is not int or result !=
                        {"schema_version": 1, "operation": operation, "outcome": "succeeded"}):
                    raise Refusal("invalid_probe_output")
                if operation == "source_create":
                    try:
                        private_directory(output)
                        for name, data in (("text", _CONTAINMENT_TEXT), ("binary", _CONTAINMENT_BINARY),
                                           ("delete-me", b"delete-me\n"), ("executable", _CONTAINMENT_EXECUTABLE)):
                            identity = _regular_identity(output / name, 1024)
                            expected_mode = 0o755 if name == "executable" else 0o600
                            if identity[-1] != hashlib.sha256(data).hexdigest() or stat.S_IMODE(identity[2]) != expected_mode:
                                raise Refusal("source_observation_failed")
                    except (OSError, Refusal):
                        raise Refusal("source_observation_failed") from None
                elif operation == "source_delete" and os.path.lexists(output / "delete-me"):
                    raise Refusal("source_observation_failed")
                report["checks"].append({"operation": operation, "status": "passed"})
            _write_pointer_evidence(selection.root, report)
        final_resources = checked(lambda step: _native_containment_observation(controller, step))
        if any(final_resources[key] != value for key, value in report["resources"].items() if key != "pids_current"):
            raise Refusal("resource_identity")
        report["resources"] = final_resources
        report["status"] = "passed"
    except Refusal as error:
        _record_truncation(report, error)
        report["reason"] = str(error)
        if str(error) in {"protected_state_changed", "source_observation_failed", "containment_access", "resource_limits"}:
            report["status"] = "failed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        report["reason"] = "native_observation_unavailable"
    if admitted:
        try:
            report["retained"] = True
            _write_pointer_evidence(selection.root, report)
        except (OSError, Refusal):
            report["retained"] = False
            if report["status"] != "failed":
                report["status"], report["reason"] = "unavailable", "evidence_retention_failed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    extensions = {
        "network": ("probe_openshell_network", "network_probe"),
        "pause-resume": ("probe_openshell_pause", "pause_resume_probe"),
        "boundaries": ("probe_openshell_boundaries", "protected_boundaries_probe"),
        "recovery": ("probe_openshell_recovery", "recovery_probe"),
    }
    parser.add_argument("--probe", choices=("pointer", "immutable-pointer", "containment", *extensions), default="pointer")
    args = parser.parse_args()
    try:
        selection = parse_selection(private_file(args.selection))
        if args.probe in extensions:
            module, function = extensions[args.probe]
            run_probe = getattr(importlib.import_module(module), function)
        else:
            run_probe = {"pointer": pointer_probe, "immutable-pointer": immutable_pointer_probe,
                         "containment": containment_probe}[args.probe]
        report = run_probe(selection)
    except (Refusal, OSError):
        report = {"schema_version": 1,
                  "probe": {"pointer": "git_pointer", "immutable-pointer": "immutable_git_pointer",
                            "containment": "containment", "network": "network", "pause-resume": "pause_resume",
                            "boundaries": "boundaries", "recovery": "recovery"}[args.probe],
                  "status": "unavailable",
                  "reason": "invalid_selection", "runtime_qualification": "not_run", "checks": [], "retained": False,
                  "generation_sha256": None, "truncation": {"transport_output": False, "limit_bytes": None}}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    # Extensions share the executed module's classes and controller state.
    sys.modules["probe_openshell_runtime"] = sys.modules[__name__]
    raise SystemExit(main())
