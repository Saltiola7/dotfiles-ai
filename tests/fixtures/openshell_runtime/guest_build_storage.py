"""Closed root controller for the optional Linux guest build storage experiment.

Only source-defined callers may use run_unit; there is no command, path, or script
CLI. Native errors preserve partial state. Receipts are comparisons, not authority.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import uuid

ROOT = Path("/var/lib/dotfiles-ai-openshell-build")
WORK = ROOT / "store/work"
OTHER_SOCKET = Path("/opt/.dotfiles-ai-openshell-build-probe.sock")
IMAGE_BYTES = 8 * 1024**3
FIXTURE_BYTES = 64 * 1024**2
REQUIRED_FREE = 12 * 1024**3
PREPARE_SECONDS = 420
CLEANUP_RESERVE = 60
MAX_OUTPUT = 512 * 1024
ENV = {"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C", "LANG": "C"}
_active = None
_end = _work_end = None


class Refusal(Exception):
    """A fixed reason; native output and arbitrary exception messages stay private."""

    def __init__(self, reason: str, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int | None = None):
        super().__init__(reason)
        self.stdout = stdout[:MAX_OUTPUT]
        self.stderr = stderr[:MAX_OUTPUT - len(self.stdout)]
        self.returncode = returncode


@dataclass(frozen=True)
class Store:
    root: Path
    image: Path
    mount: Path
    work: Path
    uuid: str
    device: str
    mount_id: int
    image_identity: tuple[int, ...]
    size: int


@dataclass(frozen=True)
class Resolver:
    path: Path
    destination: Path
    identity: tuple[int, ...]


def _remaining(deadline: float, maximum: float = 30) -> float:
    if type(deadline) is not float or not math.isfinite(deadline):
        raise Refusal("deadline")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Refusal("deadline")
    return min(remaining, maximum)


def _command(argv: list[str], deadline: float, *, maximum: float = 30, check: bool = True) -> dict:
    """Bound both streams and the child process group; never invoke a shell."""
    end = min(deadline, time.monotonic() + _remaining(deadline, maximum))
    process = None
    streams = [bytearray(), bytearray()]
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=ENV, start_new_session=True, close_fds=True)
        with selectors.DefaultSelector() as poll:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                poll.register(stream, selectors.EVENT_READ, index)
            while poll.get_map():
                for key, _ in poll.select(_remaining(end, 0.2)):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        poll.unregister(key.fileobj)
                    else:
                        streams[key.data].extend(block)
                        if sum(map(len, streams)) > MAX_OUTPUT:
                            raise Refusal("command_output_limit")
            process.wait(timeout=_remaining(end))
        _remaining(end)
        if check and process.returncode:
            raise Refusal("native_command_failed", stdout=bytes(streams[0]), stderr=bytes(streams[1]),
                          returncode=process.returncode)
        return {"returncode": process.returncode, "stdout": bytes(streams[0]), "stderr": bytes(streams[1])}
    except (OSError, subprocess.TimeoutExpired):
        raise Refusal("native_command_unavailable", stdout=bytes(streams[0]), stderr=bytes(streams[1])) from None
    except Refusal as error:
        if not error.stdout and not error.stderr:
            error.stdout = bytes(streams[0])[:MAX_OUTPUT]
            error.stderr = bytes(streams[1])[:MAX_OUTPUT - len(error.stdout)]
        raise
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()


def _read(path: Path, limit: int = 65536) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Refusal("metadata_type")
        result = bytearray()
        while True:
            if _end is not None:
                _remaining(_end)
            block = os.read(fd, min(65536, limit + 1 - len(result)))
            if not block:
                return bytes(result)
            result.extend(block)
            if len(result) > limit:
                raise Refusal("metadata_limit")
    finally:
        os.close(fd)


def _private(path: Path, *, directory: bool = False, size: int | None = None) -> tuple[int, ...]:
    info = path.lstat()
    expected_mode = 0o711 if path == ROOT else 0o700 if directory else 0o600
    if (path.resolve(strict=True) != path or info.st_uid != 0 or info.st_gid != 0
            or stat.S_IMODE(info.st_mode) != expected_mode
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and (info.st_nlink != 1 or (size is not None and info.st_size != size)))):
        raise Refusal("resource_identity")
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink, info.st_size)


def _image_changed(recorded: tuple[int, ...], observed: tuple[int, ...]) -> Refusal:
    """Bounded metadata diagnostics only; never rebind or repair a receipt."""
    report = {"reason": "image_changed",
              "fields": ["device", "inode", "mode", "uid", "gid", "links", "size"],
              "recorded": list(recorded), "observed": list(observed), "paths": [],
              "mounts": [], "mount_status": "unavailable"}
    for path in (Path("/"), ROOT.parent, ROOT):
        entry = {"path": str(path)[:256]}
        try:
            if _end is not None:
                _remaining(_end)
            info = path.lstat()
            entry["identity"] = [info.st_dev, info.st_ino, info.st_mode, info.st_uid,
                                 info.st_gid, info.st_nlink, info.st_size]
        except (OSError, Refusal):
            entry["status"] = "unavailable"
        report["paths"].append(entry)
    try:
        selected = {str(path) for path in (ROOT / "image.raw", ROOT, *ROOT.parents)}
        mounts = []
        for line in _mounts().decode("ascii").splitlines():
            if _end is not None:
                _remaining(_end)
            row = line.split()
            if len(row) <= 6 or row[4] not in selected:
                continue
            split = row.index("-")
            if len(mounts) == 4:
                raise Refusal("diagnostic_limit")
            mounts.append({key: value[:128] for key, value in zip(
                ("mount_id", "parent_id", "device", "root", "mount_point", "options", "filesystem_type", "source"),
                (*row[:6], row[split + 1], row[split + 2]))})
        report["mounts"], report["mount_status"] = mounts, "observed"
    except (OSError, Refusal, ValueError, UnicodeError, IndexError):
        pass
    raw = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    if len(raw) > 8192:
        report.update(paths=[], mounts=[], mount_status="output_limit")
        raw = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    return Refusal("image_changed", stderr=raw)


def _write_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)


def _root() -> int:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise Refusal("linux_root_required")
    _private(ROOT, directory=True)
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (os.fstat(fd).st_dev, os.fstat(fd).st_ino) != (ROOT.stat().st_dev, ROOT.stat().st_ino):
            raise Refusal("resource_identity")
    except (OSError, Refusal):
        os.close(fd)
        raise Refusal("storage_busy") from None
    return fd


def _parse_receipt(raw: bytes) -> dict:
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal("receipt")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise Refusal("receipt") from None
    if (type(value) is not dict or set(value) != {"schema_version", "uuid", "image_identity", "fixture_verified"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["fixture_verified"] is not True
            or type(value["image_identity"]) is not list or len(value["image_identity"]) != 7
            or any(type(number) is not int or number < 0 for number in value["image_identity"])
            or not isinstance(value["uuid"], str)
            or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value["uuid"]) is None):
        raise Refusal("receipt")
    return value


def _binding_host(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Refusal("binding_host")


def _binding_uuid(value) -> bool:
    try:
        parsed = uuid.UUID(value) if type(value) is str else None
        return parsed is not None and parsed.int != 0 and str(parsed) == value
    except ValueError:
        return False


def _binding_parse(raw: bytes) -> dict:
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal("binding_record")
            result[key] = value
        return result
    if not 0 < len(raw) <= 8192:
        raise Refusal("binding_record")
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise Refusal("binding_record") from None
    expected = {"schema_version", "host_binding_sha256", "legacy_receipt_sha256", "inner_uuid", "btrfs",
                "image_identity", "receipt_identity", "root_identity", "parent_identity"}
    if (type(value) is not dict or set(value) != expected or type(value["schema_version"]) is not int
            or value["schema_version"] != 1 or not _binding_uuid(value["inner_uuid"])):
        raise Refusal("binding_record")
    for field in ("host_binding_sha256", "legacy_receipt_sha256"):
        _binding_host(value[field])
    native = value["btrfs"]
    if (type(native) is not dict or set(native) != {"fsid", "tree_id", "subvolume_uuid"}
            or not _binding_uuid(native["fsid"]) or not _binding_uuid(native["subvolume_uuid"])
            or type(native["tree_id"]) is not int or not 0 < native["tree_id"] < 2**64):
        raise Refusal("binding_record")
    for field, length in (("image_identity", 6), ("receipt_identity", 6), ("root_identity", 4), ("parent_identity", 4)):
        identity = value[field]
        if (type(identity) is not list or len(identity) != length
                or any(type(number) is not int or not 0 <= number < 2**64 for number in identity)
                or identity[0] == 0 or identity[1] > 0xffff or identity[2:4] != [0, 0]):
            raise Refusal("binding_record")
    if (value["image_identity"][1:] != [stat.S_IFREG | 0o600, 0, 0, 1, IMAGE_BYTES]
            or value["receipt_identity"][1:5] != [stat.S_IFREG | 0o600, 0, 0, 1]
            or not 0 < value["receipt_identity"][5] <= 4096
            or value["root_identity"][1] != stat.S_IFDIR | 0o711
            or not stat.S_ISDIR(value["parent_identity"][1]) or value["parent_identity"][1] & 0o022):
        raise Refusal("binding_record")
    return value


def _binding_btrfs(fd: int) -> dict:
    if sys.byteorder != "little":
        raise Refusal("binding_platform")
    try:
        filesystem = fcntl.ioctl(fd, 0x8400941f, bytes(1024))
        subvolume = fcntl.ioctl(fd, 0x81f8943c, bytes(504))
    except OSError:
        raise Refusal("binding_ioctl") from None
    if type(filesystem) is not bytes or len(filesystem) != 1024 or type(subvolume) is not bytes or len(subvolume) != 504:
        raise Refusal("binding_ioctl")
    result = {"fsid": str(uuid.UUID(bytes=filesystem[16:32])),
              "tree_id": struct.unpack_from("=Q", subvolume)[0],
              "subvolume_uuid": str(uuid.UUID(bytes=subvolume[296:312]))}
    if not _binding_uuid(result["fsid"]) or not _binding_uuid(result["subvolume_uuid"]) or result["tree_id"] == 0:
        raise Refusal("binding_ioctl")
    return result


@contextmanager
def _binding_fds(root_fd: int, *, sidecar: bool):
    fds = {"root": root_fd}
    try:
        for role, path in (("parent", ROOT.parent), ("receipt", ROOT / "receipt.json"), ("image", ROOT / "image.raw"),
                           *((("binding", ROOT / "binding.json"),) if sidecar else ())):
            _remaining(_work_end)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            fds[role] = os.open(path, flags | (os.O_DIRECTORY if role == "parent" else 0))
        yield fds
    except OSError:
        raise Refusal("binding_io") from None
    finally:
        primary = sys.exc_info()[1]
        close_failed = False
        for role, fd in fds.items():
            if role != "root":
                try:
                    os.close(fd)
                except OSError:
                    close_failed = True
        if close_failed:
            if primary is None:
                raise Refusal("binding_close")
            if isinstance(primary, Refusal):
                primary.stderr = (primary.stderr + b"\nbinding_fd_close_failed")[:MAX_OUTPUT - len(primary.stdout)]


def _binding_read(fd: int, limit: int, deadline: float) -> bytes:
    result = bytearray()
    while True:
        _remaining(deadline)
        block = os.pread(fd, min(4096, limit + 1 - len(result)), len(result))
        if not block:
            return bytes(result)
        result.extend(block)
        if len(result) > limit:
            raise Refusal("binding_record_limit")


def _binding_observe(fds: dict, deadline: float) -> dict:
    paths = {"root": ROOT, "parent": ROOT.parent, "image": ROOT / "image.raw",
             "receipt": ROOT / "receipt.json", "binding": ROOT / "binding.json"}
    try:
        rows = [line.split() for line in _mounts().decode("ascii").splitlines()]
        result = {}
        for role, fd in fds.items():
            _remaining(deadline)
            info = os.fstat(fd)
            identity = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink, info.st_size)
            path = paths[role]
            native = path.lstat()
            path_identity = (native.st_dev, native.st_ino, native.st_mode, native.st_uid, native.st_gid, native.st_nlink, native.st_size)
            directory = role in {"root", "parent"}
            if (path.resolve(strict=True) != path or identity != path_identity or info.st_uid != 0 or info.st_gid != 0
                    or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                    or (directory and info.st_mode & 0o022)
                    or (role == "root" and stat.S_IMODE(info.st_mode) != 0o711)
                    or (not directory and (stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1))
                    or (role == "image" and info.st_size != IMAGE_BYTES)
                    or (role in {"receipt", "binding"} and not 0 < info.st_size <= (4096 if role == "receipt" else 8192))):
                raise Refusal("binding_path")
            raw = _read(Path(f"/proc/self/fdinfo/{fd}"), 4096).decode("ascii")
            mount_ids = re.findall(r"^mnt_id:\s*([0-9]+)$", raw, re.MULTILINE)
            inodes = re.findall(r"^ino:\s*([0-9]+)$", raw, re.MULTILINE)
            if len(mount_ids) != 1 or len(inodes) != 1 or int(inodes[0]) != info.st_ino:
                raise Refusal("binding_mount")
            matches = [row for row in rows if len(row) > 6 and row[0] == mount_ids[0]]
            if len(matches) != 1:
                raise Refusal("binding_mount")
            row = matches[0]
            if row[row.index("-") + 1] != "btrfs" or not path.is_relative_to(Path(row[4])):
                raise Refusal("binding_mount")
            result[role] = {"identity": identity, "mount": tuple(row), "btrfs": _binding_btrfs(fd)}
        if any(value["btrfs"] != result["root"]["btrfs"] for value in result.values()):
            raise Refusal("binding_filesystem")
        return result
    except (OSError, ValueError, UnicodeError, IndexError):
        raise Refusal("binding_observation") from None


def _binding_check(before: dict, after: dict, *, publication: bool = False) -> None:
    for role, initial in before.items():
        current = after[role]
        left, right = initial["identity"], current["identity"]
        if publication and role == "root":
            left, right = left[:-1], right[:-1]
        if left != right or initial["mount"] != current["mount"] or initial["btrfs"] != current["btrfs"]:
            raise Refusal("binding_changed")


def _binding_unmounted(deadline: float) -> None:
    _remaining(deadline)
    _private(ROOT / "store", directory=True)
    if _active is not None or _is_mounted(ROOT / "store") or _associated(ROOT / "image.raw", deadline):
        raise Refusal("binding_attached")


def _binding_value(fds: dict, observed: dict, host: str, deadline: float) -> tuple[dict, bytes]:
    raw = _binding_read(fds["receipt"], 4096, deadline)
    receipt = _parse_receipt(raw)
    if observed["image"]["identity"][1:] != tuple(receipt["image_identity"][1:]):
        raise Refusal("binding_legacy_image")
    procfd = f"/proc/{os.getpid()}/fd/{fds['image']}"
    for field, expected in (("TYPE", "ext4"), ("UUID", receipt["uuid"])):
        answer = _command(["/usr/sbin/blkid", "-p", "-s", field, "-o", "value", procfd], deadline)["stdout"]
        if answer.strip() != expected.encode():
            raise Refusal("binding_inner_filesystem")
    value = {"schema_version": 1, "host_binding_sha256": host,
             "legacy_receipt_sha256": hashlib.sha256(raw).hexdigest(), "inner_uuid": receipt["uuid"],
             "btrfs": observed["root"]["btrfs"],
             "image_identity": list(observed["image"]["identity"][1:]),
             "receipt_identity": list(observed["receipt"]["identity"][1:]),
             "root_identity": list(observed["root"]["identity"][1:5]),
             "parent_identity": list(observed["parent"]["identity"][1:5])}
    _binding_parse(json.dumps(value).encode())
    return value, raw


def record_stable_binding(*, host_binding_sha256: str, deadline: float) -> dict:
    """Explicitly record current identity; preserve the historical receipt."""
    global _end, _work_end
    _binding_host(host_binding_sha256)
    _remaining(deadline)
    if _end is not None:
        raise Refusal("nested_operation")
    root_fd = _root()
    _end, _work_end = deadline, deadline - CLEANUP_RESERVE
    try:
        if _root_names() != {"image.raw", "store", "receipt.json"}:
            raise Refusal("binding_retained_state")
        _binding_unmounted(_work_end)
        with _binding_fds(root_fd, sidecar=False) as fds:
            before = _binding_observe(fds, _work_end)
            value, receipt_raw = _binding_value(fds, before, host_binding_sha256, _work_end)
            raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            _binding_check(before, _binding_observe(fds, _work_end))
            if _binding_read(fds["receipt"], 4096, _work_end) != receipt_raw:
                raise Refusal("binding_receipt_changed")
            _binding_unmounted(_work_end)
            if _root_names() != {"image.raw", "store", "receipt.json"}:
                raise Refusal("binding_retained_state")
            fds["binding"] = os.open(ROOT / "binding.json",
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
            pending = memoryview(raw)
            while pending:
                _remaining(_work_end)
                written = os.write(fds["binding"], pending)
                if written <= 0:
                    raise Refusal("binding_write")
                pending = pending[written:]
            os.fsync(fds["binding"])
            os.fsync(root_fd)
            if _root_names() != {"image.raw", "store", "receipt.json", "binding.json"}:
                raise Refusal("binding_retained_state")
            after = _binding_observe(fds, _work_end)
            _binding_check(before, after, publication=True)
            if (_binding_read(fds["binding"], 8192, _work_end) != raw
                    or _binding_read(fds["receipt"], 4096, _work_end) != receipt_raw):
                raise Refusal("binding_record_changed")
            _binding_unmounted(_work_end)
            _binding_check(after, _binding_observe(fds, _work_end))
            return {"schema_version": 1, "status": "storage_bound", "host_binding_sha256": host_binding_sha256,
                    "legacy_receipt_sha256": value["legacy_receipt_sha256"], "binding_sha256": hashlib.sha256(raw).hexdigest(),
                    "image_bytes": IMAGE_BYTES, "unmounted_verified": True, "session_enabled": False,
                    "historical_outer_identity_verified": False}
    finally:
        _end = _work_end = None
        os.close(root_fd)


@contextmanager
def _bound_store(root_fd: int, host: str, deadline: float):
    _binding_host(host)
    _binding_unmounted(deadline)
    with _binding_fds(root_fd, sidecar=True) as fds:
        before = _binding_observe(fds, deadline)
        raw = _binding_read(fds["binding"], 8192, deadline)
        saved = _binding_parse(raw)
        current, receipt_raw = _binding_value(fds, before, host, deadline)
        if saved != current:
            raise Refusal("binding_mismatch")
        _binding_check(before, _binding_observe(fds, deadline))
        if (_binding_read(fds["receipt"], 4096, deadline) != receipt_raw
                or _binding_read(fds["binding"], 8192, deadline) != raw):
            raise Refusal("binding_record_changed")
        if _root_names() != {"image.raw", "store", "receipt.json", "binding.json"}:
            raise Refusal("binding_retained_state")
        with _mounted(ROOT / "image.raw", IMAGE_BYTES, current["inner_uuid"], before["image"]["identity"],
                      deadline, initialize=False) as store:
            yield store
        _binding_check(before, _binding_observe(fds, deadline))
        if (_binding_read(fds["receipt"], 4096, deadline) != receipt_raw
                or _binding_read(fds["binding"], 8192, deadline) != raw):
            raise Refusal("binding_record_changed")
        if _root_names() != {"image.raw", "store", "receipt.json", "binding.json"}:
            raise Refusal("binding_retained_state")
        _binding_unmounted(deadline)


def _parse_pending(raw: bytes) -> dict:
    def unique(items):
        value = {}
        for key, item in items:
            if key in value:
                raise Refusal("pending_record")
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise Refusal("pending_record") from None
    if (type(value) is not dict or set(value) != {"schema_version", "phase", "uuid", "image_identity", "fill_inode", "fixture_written_bytes"}
            or type(value["phase"]) is not str or value["phase"] not in {"fixture", "image"}
            or type(value["fill_inode"]) is not int or value["fill_inode"] < 0
            or type(value["fixture_written_bytes"]) is not int or value["fixture_written_bytes"] < 0):
        raise Refusal("pending_record")
    _parse_receipt(json.dumps({key: value[key] for key in ("schema_version", "uuid", "image_identity")}
                             | {"fixture_verified": True}).encode())
    identity = value["image_identity"]
    expected = FIXTURE_BYTES if value["phase"] == "fixture" else IMAGE_BYTES
    if (identity[0] == 0 or identity[1] == 0 or identity[2:] != [stat.S_IFREG | 0o600, 0, 0, 1, expected]
            or (value["phase"] == "fixture" and value["fixture_written_bytes"] != 0)
            or (value["phase"] == "image" and (value["fill_inode"] != 0
                or not 0 < value["fixture_written_bytes"] <= 65 * 1024**2))):
        raise Refusal("pending_record")
    return value


def _save_pending(value: dict) -> None:
    raw = json.dumps(value, sort_keys=True).encode()
    _parse_pending(raw)
    temporary = ROOT / "pending.next"
    target = ROOT / "pending.json"
    if target.exists():
        _private(target)
        _parse_pending(_read(target, 4096))
    _write_new(temporary, raw)
    temporary.replace(target)


def _validate_fill(info, inode: int, device: int) -> None:
    if (info.st_ino != inode or info.st_dev != device or info.st_uid != 65534 or info.st_gid != 65534
            or info.st_mode != stat.S_IFREG | 0o600 or info.st_nlink != 1 or not 0 <= info.st_size <= FIXTURE_BYTES):
        raise Refusal("fixture_fill_identity")


def _reset_fill(pending: dict) -> None:
    """Reset only the receipt-bound synthetic fixture file, never its image."""
    if _active is None or _active.size != FIXTURE_BYTES or pending["phase"] != "fixture":
        raise Refusal("fixture_fill_identity")
    path = WORK / "fill"
    if pending["fill_inode"] == 0:
        _write_new(path, b"")
        os.chown(path, 65534, 65534)
        pending["fill_inode"] = path.lstat().st_ino
        _save_pending(pending)
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        _validate_fill(os.fstat(fd), pending["fill_inode"], WORK.stat().st_dev)
        os.ftruncate(fd, 0)
        os.fsync(fd)
    finally:
        os.close(fd)


def _root_names() -> set[str]:
    names = set()
    with os.scandir(ROOT) as entries:
        for entry in entries:
            if len(names) >= 4:
                raise Refusal("retained_state")
            names.add(entry.name)
    return names


def _mount_record(raw: bytes, mount: Path, device: str, mount_id: int, major: int, minor: int) -> dict:
    try:
        rows = [line.split() for line in raw.decode("ascii").splitlines()]
        rows = [row for row in rows if len(row) > 6 and row[4] == str(mount)]
        if len(rows) != 1:
            raise Refusal("mount_identity")
        row = rows[0]
        split = row.index("-")
        if (int(row[0]) != mount_id or row[2] != f"{major}:{minor}" or row[3] != "/"
                or not {"rw", "nosuid", "nodev"} <= set(row[5].split(","))
                or row[split + 1:split + 3] != ["ext4", device]):
            raise Refusal("mount_identity")
        return {"mount_id": mount_id}
    except (ValueError, UnicodeError, IndexError):
        raise Refusal("mount_identity") from None


def _mounts() -> bytes:
    return _read(Path("/proc/self/mountinfo"), 1024 * 1024)


def _is_mounted(mount: Path) -> bool:
    return any(len(row) > 4 and row[4] == str(mount).encode() for row in (line.split() for line in _mounts().splitlines()))


def _associated(image: Path, deadline: float) -> list[str]:
    raw = _command(["/usr/sbin/losetup", "--associated", str(image), "--output", "NAME", "--noheadings"], deadline)["stdout"]
    try:
        devices = raw.decode("ascii").split()
    except UnicodeError:
        raise Refusal("loop_identity") from None
    if len(devices) > 1 or any(re.fullmatch(r"/dev/loop[0-9]+", device) is None for device in devices):
        raise Refusal("loop_identity")
    return devices


def _loop_identity(image: Path, identity: tuple[int, ...], device: str, size: int, deadline: float) -> None:
    if (_private(image, size=size) != identity or re.fullmatch(r"/dev/loop[0-9]+", device) is None
            or _associated(image, deadline) != [device]):
        raise Refusal("loop_identity")
    fd = os.open(device, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISBLK(info.st_mode) or os.major(info.st_rdev) != 7:
            raise Refusal("loop_identity")
        native = struct.unpack("=QQQQQIIII64s64s32sQQ", fcntl.ioctl(fd, 0x4C05, bytes(232)))
        if (native[1] != identity[1] or native[3] != 0 or native[4] != size
                or native[5] != int(device.removeprefix("/dev/loop")) or native[6] != 0 or native[8] & 1
                or native[9].split(b"\0", 1)[0] != os.fsencode(image)):
            raise Refusal("loop_identity")
    finally:
        os.close(fd)
    raw = _command(["/usr/sbin/blockdev", "--getsize64", device], deadline)["stdout"]
    if raw.strip() != str(size).encode():
        raise Refusal("loop_capacity")


def _verify(store: Store, deadline: float, *, work: bool = True) -> None:
    _remaining(deadline)
    _private(ROOT, directory=True)
    _loop_identity(store.image, store.image_identity, store.device, store.size, deadline)
    for field, expected in (("TYPE", "ext4"), ("UUID", store.uuid)):
        raw = _command(["/usr/sbin/blkid", "-p", "-s", field, "-o", "value", store.device], deadline)["stdout"]
        if raw.strip() != expected.encode():
            raise Refusal("filesystem_identity")
    fd = os.open(store.mount, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        fields = dict(line.split(":", 1) for line in _read(Path(f"/proc/self/fdinfo/{fd}"), 4096).decode("ascii").splitlines())
        mount_id = int(fields["mnt_id"].strip())
        if int(fields["ino"].strip()) != info.st_ino or (store.mount_id and mount_id != store.mount_id):
            raise Refusal("mount_identity")
        _mount_record(_mounts(), store.mount, store.device, mount_id, os.major(info.st_dev), os.minor(info.st_dev))
        capacity = os.fstatvfs(fd)
        if (not store.size * 3 // 4 < capacity.f_blocks * capacity.f_frsize <= store.size
                or info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o755
                or (store.mount.stat().st_dev, store.mount.stat().st_ino) != (info.st_dev, info.st_ino)):
            raise Refusal("filesystem_capacity")
        if work:
            for path in (store.work, *(store.work / name for name in ("home", "tmp", "cargo", "rustup", "cache", "target"))):
                child = path.lstat()
                if (not stat.S_ISDIR(child.st_mode) or child.st_uid != 65534 or child.st_gid != 65534
                        or stat.S_IMODE(child.st_mode) != 0o700 or child.st_dev != info.st_dev
                        or path.resolve(strict=True) != path):
                    raise Refusal("work_identity")
    except (ValueError, KeyError, UnicodeError):
        raise Refusal("mount_identity") from None
    finally:
        os.close(fd)
    _remaining(deadline)


def _mount_id(mount: Path) -> int:
    rows = [line.split() for line in _mounts().decode("ascii").splitlines()]
    found = [int(row[0]) for row in rows if len(row) > 4 and row[4] == str(mount)]
    if len(found) != 1:
        raise Refusal("mount_identity")
    return found[0]


def _make_image(image: Path, size: int, filesystem_uuid: str, deadline: float) -> tuple[int, ...]:
    _remaining(deadline)
    fd = os.open(image, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.ftruncate(fd, size)
        os.fsync(fd)
    finally:
        os.close(fd)
    identity = _private(image, size=size)
    _command(["/usr/sbin/mkfs.ext4", "-q", "-F", "-m", "0", "-U", filesystem_uuid, str(image)], deadline)
    if _private(image, size=size) != identity:
        raise Refusal("image_changed")
    return identity


@contextmanager
def _mounted(image: Path, size: int, filesystem_uuid: str, identity: tuple[int, ...], deadline: float, *, initialize: bool):
    global _active
    mount = ROOT / "store"
    _private(mount, directory=True)
    if _active is not None or _is_mounted(mount) or _associated(image, deadline):
        raise Refusal("retained_mount")
    mount_identity = mount.stat()
    device = None
    store = None
    try:
        raw = _command(["/usr/sbin/losetup", "--find", "--show", "--nooverlap", "--sizelimit", str(size), str(image)], deadline)["stdout"]
        try:
            device = raw.decode("ascii").strip()
        except UnicodeError:
            raise Refusal("loop_identity") from None
        _loop_identity(image, identity, device, size, deadline)
        _command(["/usr/bin/mount", "-t", "ext4", "-o", "rw,nosuid,nodev", device, str(mount)], deadline)
        store = Store(ROOT, image, mount, WORK, filesystem_uuid, device, _mount_id(mount), identity, size)
        _verify(store, deadline, work=False)
        if initialize and not WORK.exists():
            for path in (WORK, *(WORK / name for name in ("home", "tmp", "cargo", "rustup", "cache", "target"))):
                path.mkdir(mode=0o700)
                os.chown(path, 65534, 65534)
        _verify(store, deadline)
        _active = store
        yield store
        _verify(store, deadline)
    finally:
        _active = None
        cleanup_deadline = _end if _end is not None else deadline
        # Reobserve exact backing and mount identities before either cleanup effect.
        # Unknown or changed resources remain in place, including timed-out attaches.
        if device is not None:
            _loop_identity(image, identity, device, size, cleanup_deadline)
            if _is_mounted(mount):
                if store is None:
                    store = Store(ROOT, image, mount, WORK, filesystem_uuid, device, _mount_id(mount), identity, size)
                _verify(store, cleanup_deadline, work=False)
                _command(["/usr/bin/umount", str(mount)], cleanup_deadline)
            if _is_mounted(mount) or (mount.stat().st_dev, mount.stat().st_ino) != (mount_identity.st_dev, mount_identity.st_ino):
                raise Refusal("unmount_unverified")
            _loop_identity(image, identity, device, size, cleanup_deadline)
            _command(["/usr/sbin/losetup", "--detach", device], cleanup_deadline)
            if _associated(image, cleanup_deadline):
                raise Refusal("loop_release_unverified")


def _system_refusal(reason: str, path: Path | str | None, info=None) -> Refusal:
    metadata = {"path": str(path)[:512] if path is not None else None,
                "uid": getattr(info, "st_uid", None), "gid": getattr(info, "st_gid", None),
                "mode": oct(info.st_mode) if info is not None else None}
    return Refusal(reason, stderr=json.dumps(metadata, sort_keys=True).encode()[:4096])


def _safe_system_entry(info, *, path: Path | None = None) -> None:
    if (info.st_uid != 0 or stat.S_ISSOCK(info.st_mode)
            or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode))
            or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022)):
        raise _system_refusal("visible_system_mutable_or_socket", path, info)


def _visible_system(deadline: float) -> None:
    """Admit immutable visible guest trees; guest root is the trusted controller.

    No privileged concurrent system-tree mutation is permitted during this closed
    experiment. The unprivileged build cannot create sockets in admitted trees.
    Unknown roots, special files, nested mounts, or scan limits fail closed.
    """
    allowed = {"usr", "etc", "dev", "proc", "sys", "run", "var", "tmp", "home", "root",
               "opt", "srv", "mnt", "media", "boot", "efi", "lost+found", "afs"}
    aliases = {"bin": "usr/bin", "sbin": "usr/sbin", "lib": "usr/lib", "lib64": "usr/lib64"}
    with os.scandir("/") as entries:
        for number, entry in enumerate(entries):
            _remaining(deadline)
            if number >= 64:
                raise Refusal("system_scan_limit")
            info = entry.stat(follow_symlinks=False)
            path = Path("/") / entry.name
            if entry.name in aliases:
                if not stat.S_ISLNK(info.st_mode) or os.readlink(entry.path) not in {aliases[entry.name], "/" + aliases[entry.name]}:
                    raise _system_refusal("system_alias", path, info)
            elif stat.S_ISDIR(info.st_mode):
                if entry.name not in allowed or info.st_uid != 0:
                    raise _system_refusal("system_root", path, info)
            else:
                _safe_system_entry(info, path=path)
                if stat.S_ISLNK(info.st_mode):
                    raise _system_refusal("system_alias", path, info)
    mounts = [line.split() for line in _mounts().splitlines()]
    if any(len(row) > 4 and (row[4].startswith(b"/usr/") or row[4].startswith(b"/etc/")) for row in mounts):
        raise Refusal("system_mount")
    count = 0
    def walk(path: Path, depth: int) -> None:
        nonlocal count
        _remaining(deadline)
        if depth > 32:
            raise Refusal("system_scan_limit")
        _safe_system_entry(path.lstat(), path=path)
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            _safe_system_entry(os.fstat(fd), path=path)
            with os.scandir(fd) as entries:
                for entry in entries:
                    _remaining(deadline)
                    count += 1
                    if count > 200000:
                        raise Refusal("system_scan_limit")
                    info = entry.stat(follow_symlinks=False)
                    _safe_system_entry(info, path=path / entry.name)
                    if stat.S_ISDIR(info.st_mode):
                        walk(path / entry.name, depth + 1)
        finally:
            os.close(fd)
    for path in (Path("/usr"), Path("/etc")):
        walk(path, 0)


_RESOLVER_TARGETS = {Path("/etc/resolv.conf"), Path("/run/systemd/resolve/stub-resolv.conf"),
                     Path("/run/systemd/resolve/resolv.conf"), Path("/run/NetworkManager/resolv.conf")}


def _resolver_identity(info) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _resolver_principals() -> set[tuple[int, int]]:
    # Use bounded local account files, never an unbounded NSS/network lookup.
    users = [row.split(":") for row in _read(Path("/etc/passwd"), 65536).decode().splitlines()
             if row.startswith("systemd-resolve:")]
    groups = [row.split(":") for row in _read(Path("/etc/group"), 65536).decode().splitlines()
              if row.startswith("systemd-resolve:")]
    if not users and not groups:
        return {(0, 0)}
    try:
        if len(users) != 1 or len(groups) != 1 or len(users[0]) != 7 or len(groups[0]) != 4:
            raise Refusal("resolver_identity")
        uid, gid, group = int(users[0][2]), int(users[0][3]), int(groups[0][2])
        if gid != group or not 0 < uid < 2**32 - 1 or not 0 < gid < 2**32 - 1 or 65534 in (uid, gid):
            raise Refusal("resolver_identity")
    except ValueError:
        raise Refusal("resolver_identity") from None
    return {(0, 0), (uid, gid)}


def _validate_resolver_info(info, principals: set[tuple[int, int]]) -> None:
    if (info.st_mode != stat.S_IFREG | 0o644 or (info.st_uid, info.st_gid) not in principals
            or info.st_nlink != 1 or not 0 < info.st_size <= 65536):
        raise Refusal("resolver_identity")


def _validate_resolver_data(raw: bytes) -> None:
    if not 0 < len(raw) <= 65536 or b"\0" in raw:
        raise Refusal("resolver_data")
    servers = 0
    try:
        for line in raw.decode("ascii").splitlines():
            if len(line) > 1024:
                raise Refusal("resolver_data")
            fields = line.split("#", 1)[0].split(";", 1)[0].split()
            if not fields:
                continue
            if fields[0] == "nameserver" and len(fields) == 2:
                ipaddress.ip_address(fields[1])
                servers += 1
            elif fields[0] in {"search", "domain", "options"} and 1 < len(fields) <= 16:
                if any(re.fullmatch(r"[A-Za-z0-9_.:-]{1,253}", value) is None for value in fields[1:]):
                    raise Refusal("resolver_data")
            else:
                raise Refusal("resolver_data")
    except (ValueError, UnicodeError):
        raise Refusal("resolver_data") from None
    if not 1 <= servers <= 3:
        raise Refusal("resolver_data")


def _open_resolver(target: Path, principals: set[tuple[int, int]]) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open("/", flags)
    try:
        for component in target.parts[1:-1]:
            opened = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = opened
            info = os.fstat(directory)
            if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022
                    or (info.st_uid, info.st_gid) not in principals):
                raise Refusal("resolver_identity")
        return os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def _resolver_source(deadline: float) -> tuple[Path, bytes]:
    path = Path("/etc/resolv.conf")
    selected = _resolver_identity(path.lstat())
    if selected[3:5] != (0, 0):
        raise Refusal("resolver_identity")
    target = path.resolve(strict=True)
    if target not in _RESOLVER_TARGETS:
        raise Refusal("resolver_identity")
    principals = _resolver_principals() if str(target).startswith("/run/systemd/resolve/") else {(0, 0)}
    fd = _open_resolver(target, principals)
    try:
        info = os.fstat(fd)
        _validate_resolver_info(info, principals)
        identity = _resolver_identity(info)
        raw = bytearray()
        while True:
            _remaining(deadline)
            block = os.read(fd, min(65536, 65537 - len(raw)))
            if not block:
                break
            raw.extend(block)
            if len(raw) > 65536:
                raise Refusal("resolver_data")
        if (len(raw) != info.st_size or _resolver_identity(os.fstat(fd)) != identity
                or _resolver_identity(target.lstat()) != identity
                or _resolver_identity(path.lstat()) != selected or path.resolve(strict=True) != target):
            raise Refusal("resolver_changed")
    finally:
        os.close(fd)
    _validate_resolver_data(bytes(raw))
    return target, bytes(raw)


def _resolver(deadline: float) -> Resolver:
    if _active is None:
        raise Refusal("store_not_mounted")
    target, raw = _resolver_source(deadline)
    directory = _active.mount / "runtime-config"
    if not directory.exists():
        directory.mkdir(mode=0o700)
    _private(directory, directory=True)
    if directory.stat().st_dev != _active.mount.stat().st_dev:
        raise Refusal("resolver_identity")
    with os.scandir(directory) as entries:
        if next(entries, None) is not None:
            raise Refusal("resolver_retained_snapshot")
    snapshot = directory / ("resolver-" + uuid.uuid4().hex + ".conf")
    _write_new(snapshot, raw)
    snapshot.chmod(0o444)
    info = snapshot.lstat()
    if (info.st_mode != stat.S_IFREG | 0o444 or info.st_uid or info.st_gid or info.st_nlink != 1
            or info.st_dev != directory.stat().st_dev or _read(snapshot, 65536) != raw):
        raise Refusal("resolver_identity")
    return Resolver(snapshot, target, _resolver_identity(info))


def _retire_resolver(resolver: Resolver) -> None:
    try:
        if _resolver_identity(resolver.path.lstat()) != resolver.identity:
            raise Refusal("resolver_retirement_identity")
        resolver.path.unlink()
    except OSError:
        raise Refusal("resolver_retirement_identity") from None


def _properties(network: bool, seconds: int, *, resolver: Resolver | None = None) -> list[str]:
    if type(network) is not bool or type(seconds) is not int or not 1 <= seconds <= 1500:
        raise Refusal("unit_contract")
    properties = ["Type=exec", "User=65534", "Group=65534", "SupplementaryGroups=", "UMask=0077",
            "ProtectSystem=strict", "ProtectHome=yes", "PrivateDevices=yes", "PrivatePIDs=yes", "PrivateTmp=no",
            "BindLogSockets=no", "NoNewPrivileges=yes", "CapabilityBoundingSet=", "AmbientCapabilities=",
            "RestrictNamespaces=yes", "ProtectKernelTunables=yes", "ProtectControlGroups=yes",
            "CPUQuota=200%", "MemoryMax=6G", "MemorySwapMax=0", "TasksMax=512", "LimitCORE=0",
            "KillMode=control-group", "Restart=no", "TimeoutStartSec=20", "TimeoutStopSec=10",
            f"RuntimeMaxSec={seconds}", f"PrivateNetwork={'no' if network else 'yes'}",
            "RestrictAddressFamilies=AF_INET AF_INET6" + ("" if network else " AF_UNIX"),
            "TemporaryFileSystem=/var:ro" + (" /run:ro" if network else ""),
            "InaccessiblePaths=" + ("" if network else "/run ") + "/dev/shm -/opt -/srv -/mnt -/media -/boot -/efi -/lost+found -/afs",
            f"BindPaths={WORK}:{WORK}:norbind {WORK}/tmp:/tmp:norbind {WORK}/tmp:/var/tmp:norbind",
            f"WorkingDirectory={WORK}", "ProtectClock=yes"]
    if resolver is not None:
        if (not network or type(resolver) is not Resolver or resolver.destination not in _RESOLVER_TARGETS
                or resolver.path.parent != ROOT / "store/runtime-config"
                or re.fullmatch(r"resolver-[0-9a-f]{32}\.conf", resolver.path.name) is None):
            raise Refusal("resolver_identity")
        properties.append(f"BindReadOnlyPaths={resolver.path}:{resolver.destination}:norbind")
    return properties


def _unit_stopped(unit: str, deadline: float) -> None:
    if re.fullmatch(r"dotfiles-ai-openshell-build-[0-9a-f]{32}\.service", unit) is None:
        raise Refusal("unit_shutdown_unverified")
    observed = _command(["/usr/bin/systemctl", "show", "--all", unit,
                         "--property=LoadState,ActiveState,SubState,ControlGroup"], deadline, check=False)
    raw = observed["stdout"]
    try:
        rows = [line.split("=", 1) for line in raw.decode("ascii").splitlines()]
        fields = dict(rows)
    except (ValueError, UnicodeError):
        raise Refusal("unit_shutdown_unverified") from None
    # systemd v259 show-properties returns zero even for an absent unit. Do not
    # treat status(1)'s broader exit-code set as successful show observations.
    if (type(observed.get("returncode")) is not int or observed["returncode"] != 0
            or len(rows) != 4 or set(fields) != {"LoadState", "ActiveState", "SubState", "ControlGroup"}):
        raise Refusal("unit_shutdown_unverified")
    state = (fields["LoadState"], fields["ActiveState"], fields["SubState"])
    if state not in {("not-found", "inactive", "dead"), ("loaded", "inactive", "dead"), ("loaded", "failed", "failed")}:
        raise Refusal("unit_shutdown_unverified")
    group = fields["ControlGroup"]
    if group not in {"", f"/system.slice/{unit}"} or (state[0] == "not-found" and group):
        raise Refusal("unit_shutdown_unverified")
    path = Path("/sys/fs/cgroup/system.slice") / unit
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        raise Refusal("unit_shutdown_unverified") from None
    if state[0] == "not-found" or not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        raise Refusal("unit_shutdown_unverified")
    try:
        if _read(path / "cgroup.procs", 4096).strip():
            raise Refusal("unit_shutdown_unverified")
    except OSError:
        raise Refusal("unit_shutdown_unverified") from None


def run_unit(script: str, *, network: bool = False, seconds: int = 300) -> dict:
    """Execute a trusted source-defined script within the current verified store.

    This internal Python interface is not an authorization boundary or a CLI.
    Callers must never pass user, downloaded, environment, or JSON-supplied code.
    """
    if _active is None or _end is None or _work_end is None:
        raise Refusal("store_not_mounted")
    properties = _properties(network, seconds)
    if type(script) is not str or not script or len(script.encode("utf-8")) > 65536:
        raise Refusal("unit_script")
    deadline = min(_work_end, time.monotonic() + seconds)
    _verify(_active, deadline)
    _visible_system(deadline)
    resolver = _resolver(deadline) if network else None
    properties = _properties(network, seconds, resolver=resolver)
    unit = "dotfiles-ai-openshell-build-" + uuid.uuid4().hex + ".service"
    environment = {"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C", "LANG": "C", "HOME": str(WORK / "home"),
                   "CARGO_HOME": str(WORK / "cargo"), "RUSTUP_HOME": str(WORK / "rustup"), "TMPDIR": str(WORK / "tmp"),
                   "XDG_CACHE_HOME": str(WORK / "cache"), "CARGO_TARGET_DIR": str(WORK / "target")}
    argv = ["/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", f"--unit={unit}"]
    argv += [f"--property={item}" for item in properties]
    argv += [f"--setenv={key}={value}" for key, value in environment.items()]
    argv += ["--", "/usr/bin/env", "-i", *(f"{key}={value}" for key, value in environment.items()),
             "/usr/bin/python3", "-I", "-c", script]
    primary = None
    result = None
    try:
        try:
            result = _command(argv, deadline, maximum=seconds, check=False)
            if result["returncode"]:
                primary = Refusal("unit_failed", **result)
        except Refusal as error:
            primary = error
    finally:
        stop_error = None
        try:
            stopped = _command(["/usr/bin/systemctl", "stop", unit], _end, maximum=15, check=False)
            if stopped["returncode"]:
                stop_error = Refusal("unit_stop_failed", **stopped)
        except Refusal as error:
            stop_error = error
        try:
            _unit_stopped(unit, _end)
        except Refusal as error:
            original = primary if primary is not None else Refusal("unit_result", **result) if result is not None else error
            detail = original.stderr + b"\nshutdown verification failed\n"
            if stop_error is not None:
                detail += stop_error.stderr + b"\n"
            detail += error.stderr
            raise Refusal("unit_shutdown_unverified", stdout=original.stdout, stderr=detail,
                          returncode=original.returncode) from None
        if resolver is not None:
            try:
                _retire_resolver(resolver)
            except Refusal as error:
                if primary is not None:
                    raise Refusal(str(error), stdout=primary.stdout,
                                  stderr=primary.stderr + b"\nresolver retirement failed\n" + error.stderr,
                                  returncode=primary.returncode) from None
                raise
    if primary is not None:
        raise primary
    _verify(_active, _work_end)
    _visible_system(_work_end)
    return result


_PROBE = r'''
import errno,json,os,resource,socket,stat
p=PARAMETERS
w=p["work"]
assert os.getuid()==os.getgid()==65534 and set(os.getgroups()) <= {65534}
assert stat.S_ISFIFO(os.fstat(1).st_mode) and stat.S_ISFIFO(os.fstat(2).st_mode)
assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
status=dict(line.split(":",1) for line in open("/proc/self/status") if ":" in line)
assert status["NoNewPrivs"].strip()=="1"
assert all(int(status[key].strip(),16)==0 for key in ("CapEff","CapPrm","CapBnd","CapAmb"))
assert all(os.stat("/proc/self/ns/"+name).st_ino != p[name] for name in ("pid","mnt","net"))
for entry in os.listdir("/proc/self/fd"):
    if int(entry)>2:
        try: os.fstat(int(entry))
        except OSError as error: assert error.errno==errno.EBADF
        else: raise AssertionError("inherited descriptor")
cgroup=open("/proc/self/cgroup").read().strip()
assert cgroup.startswith("0::/system.slice/dotfiles-ai-openshell-build-") and "\n" not in cgroup
cgroup="/sys/fs/cgroup"+cgroup[3:]
quota,period=map(int,open(cgroup+"/cpu.max").read().split())
assert quota==2*period and period>0
for name,expected in (("memory.max",6*1024**3),("memory.swap.max",0),("pids.max",512)):
    assert int(open(cgroup+"/"+name).read())==expected
device=os.stat(w).st_dev
for path in (w,"/tmp","/var/tmp",os.environ["HOME"],os.environ["CARGO_HOME"],os.environ["RUSTUP_HOME"],os.environ["TMPDIR"],os.environ["XDG_CACHE_HOME"],os.environ["CARGO_TARGET_DIR"]):
    assert os.stat(path).st_dev==device
    target=path+"/positive-"+str(os.getpid())
    with open(target,"xb") as stream: stream.write(b"inside")
    os.unlink(target)
for path in (p["outside"],"/run/openshell-escape","/dev/shm/openshell-escape","/etc/openshell-escape","/var/cache/openshell-escape","/var/log/openshell-escape","/openshell-escape"):
    try: fd=os.open(path,os.O_WRONLY|os.O_CREAT,0o600)
    except OSError as error: assert error.errno in (errno.EACCES,errno.EROFS,errno.ENOENT)
    else: os.close(fd); raise AssertionError("outside write")
try: os.stat("/proc/"+str(p["outside_pid"])+"/root")
except OSError as error: assert error.errno in (errno.EACCES,errno.ENOENT,errno.ESRCH)
else: raise AssertionError("outside process")
for address in (p["pathname"],p["other_pathname"],"\0"+p["abstract"]):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(1)
        try: client.connect(address)
        except OSError as error: assert error.errno in (errno.EACCES,errno.ENOENT,errno.ECONNREFUSED)
        else: raise AssertionError("outside socket")
for address in (w+"/tmp/positive.sock","\0openshell-positive-"+str(os.getpid())):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server, socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        server.bind(address); server.listen(1); client.connect(address)
        connection,_=server.accept(); connection.close()
    if not address.startswith("\0"): os.unlink(address)
for endpoint in socket.socketpair(): endpoint.close()
with socket.socket(socket.AF_INET,socket.SOCK_STREAM): pass
written=0
if p["fill"]:
    fd=os.open(w+"/fill",os.O_WRONLY|os.O_NOFOLLOW)
    info=os.fstat(fd)
    assert info.st_ino==p["fill_inode"] and info.st_dev==device and info.st_nlink==1 and info.st_size==0
    block=os.urandom(1024*1024)
    try:
        while written < 65*1024*1024:
            written += os.write(fd,block[:min(len(block),65*1024*1024-written)])
        os.fsync(fd)
    except OSError as error: assert error.errno==errno.ENOSPC
    else: raise AssertionError("missing ENOSPC")
    finally: os.close(fd)
assert (0 < written <= 65*1024*1024) if p["fill"] else written==0
print(json.dumps({"schema_version":1,"escape_verified":True,"enospc_verified":p["fill"],"written_bytes":written}))
'''


def _probe(*, fill: bool, deadline: float, fill_inode: int = 0) -> dict:
    pathname = ROOT / "outside.sock"
    outside = ROOT / "outside-writable"
    abstract = "dotfiles-openshell-outside-" + uuid.uuid4().hex
    servers = []
    owned = {}
    pid = None
    ready_read = ready_write = None
    def remember(path):
        info = path.lstat()
        owned[path] = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink)
    try:
        if OTHER_SOCKET.exists() or OTHER_SOCKET.is_symlink() or not OTHER_SOCKET.parent.is_dir():
            raise Refusal("probe_listener_unavailable")
        _write_new(outside, b"unchanged")
        remember(outside)
        os.chown(outside, 65534, 65534)
        remember(outside)
        for address in (str(pathname), str(OTHER_SOCKET), "\0" + abstract):
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            servers.append(server)
            server.bind(address)
            if not address.startswith("\0"):
                remember(Path(address))
                os.chmod(address, 0o777)
                remember(Path(address))
            server.listen(4)
            server.setblocking(False)
        def positive_listeners():
            for address, server in zip((str(pathname), str(OTHER_SOCKET), "\0" + abstract), servers, strict=True):
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(_remaining(deadline, 1))
                    client.connect(address)
                    connection, _ = server.accept()
                    connection.close()
        positive_listeners()
        # This trusted child owns no writable external descriptors. Its UID makes
        # the proc-namespace negative control distinct from ordinary UID denial.
        ready_read, ready_write = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(ready_read)
                for server in servers:
                    server.close()
                os.setgroups([])
                os.setgid(65534)
                os.setuid(65534)
                import ctypes
                if ctypes.CDLL(None).prctl(4, 1, 0, 0, 0) != 0:
                    os._exit(2)
                # Prove the same-UID fixture is writable outside the unit before
                # treating the confined failure as a namespace/readonly proof.
                with outside.open("r+b") as stream:
                    if stream.read() != b"unchanged":
                        os._exit(2)
                    stream.seek(0)
                    stream.write(b"unchanged")
                os.write(ready_write, b"ready")
                os.close(ready_write)
                time.sleep(120)
            finally:
                os._exit(0)
        os.close(ready_write)
        ready_write = None
        with selectors.DefaultSelector() as poll:
            poll.register(ready_read, selectors.EVENT_READ)
            if not poll.select(_remaining(deadline, 5)) or os.read(ready_read, 6) != b"ready":
                raise Refusal("probe_listener_unavailable")
        os.close(ready_read)
        ready_read = None
        parameters = {"work": str(WORK), "outside": str(outside), "outside_pid": pid,
                      "pathname": str(pathname), "other_pathname": str(OTHER_SOCKET), "abstract": abstract,
                      "fill": fill, "fill_inode": fill_inode,
                      **{name: os.stat(f"/proc/self/ns/{name}").st_ino for name in ("pid", "mnt", "net")}}
        result = run_unit(_PROBE.replace("PARAMETERS", repr(parameters), 1), seconds=min(100, int(_remaining(deadline, 100))))
        for server in servers:
            try:
                connection, _ = server.accept()
            except BlockingIOError:
                pass
            else:
                connection.close()
                raise Refusal("socket_escape")
        if _read(outside, 32) != b"unchanged":
            raise Refusal("write_escape")
        positive_listeners()
        try:
            report = json.loads(result["stdout"])
        except (ValueError, UnicodeError):
            raise Refusal("probe_report") from None
        if (type(report) is not dict or set(report) != {"schema_version", "escape_verified", "enospc_verified", "written_bytes"}
                or type(report["schema_version"]) is not int or report["schema_version"] != 1
                or report["escape_verified"] is not True or report["enospc_verified"] is not fill
                or type(report["written_bytes"]) is not int
                or not (0 < report["written_bytes"] <= 65 * 1024**2 if fill else report["written_bytes"] == 0)):
            raise Refusal("probe_report")
        return report
    finally:
        for fd in (ready_read, ready_write):
            if fd is not None:
                os.close(fd)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            stop_end = min(_end, time.monotonic() + 2)
            while os.waitpid(pid, os.WNOHANG) == (0, 0):
                if time.monotonic() >= stop_end:
                    os.kill(pid, signal.SIGKILL)
                    if os.waitpid(pid, os.WNOHANG) == (0, 0):
                        raise Refusal("probe_process_shutdown_unverified")
                    break
                time.sleep(0.01)
        for server in servers:
            server.close()
        # Only exact freshly created synthetic fixtures are retired.
        for path, identity in owned.items():
            info = path.lstat()
            if identity != (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink):
                raise Refusal("probe_retirement_identity")
            path.unlink()


@contextmanager
def mounted_store(*, deadline: float | None = None, host_binding_sha256: str | None = None):
    """Rebind the retained area and always release its exact mount and loop."""
    global _end, _work_end
    if _end is not None:
        raise Refusal("nested_operation")
    end = time.monotonic() + PREPARE_SECONDS if deadline is None else deadline
    _remaining(end)
    fd = _root()
    _end, _work_end = end, end - CLEANUP_RESERVE
    try:
        _remaining(_work_end)
        names = _root_names()
        if names == {"image.raw", "store", "receipt.json", "binding.json"}:
            with _bound_store(fd, host_binding_sha256, _work_end) as store:
                yield store
            return
        if names != {"image.raw", "store", "receipt.json"}:
            raise Refusal("retained_state")
        receipt_path = ROOT / "receipt.json"
        _private(receipt_path)
        receipt = _parse_receipt(_read(receipt_path, 4096))
        image = ROOT / "image.raw"
        identity = _private(image, size=IMAGE_BYTES)
        if identity != tuple(receipt["image_identity"]):
            raise _image_changed(tuple(receipt["image_identity"]), identity)
        with _mounted(image, IMAGE_BYTES, receipt["uuid"], identity, _work_end, initialize=False) as store:
            yield store
    finally:
        _end = _work_end = None
        os.close(fd)


def prepare() -> dict:
    """Prepare once, or explicitly resume an exactly recorded formatted image.

    A new invocation is required after failure. Resume never formats, enlarges,
    or recreates retained images; unknown partial state remains untouched.
    """
    global _end, _work_end
    if sys.platform != "linux" or os.geteuid() != 0:
        raise Refusal("linux_root_required")
    retained = ROOT.exists()
    if ROOT.is_symlink() or (retained and not (ROOT / "pending.json").is_file()):
        raise Refusal("retained_state")
    if _end is not None:
        raise Refusal("nested_operation")
    end = time.monotonic() + PREPARE_SECONDS
    parent = ROOT.parent
    if parent.resolve(strict=True) != parent or parent.stat().st_uid != 0:
        raise Refusal("parent_identity")
    capacity = os.statvfs(parent)
    if capacity.f_bavail * capacity.f_frsize < (4 * 1024**3 if retained else REQUIRED_FREE):
        raise Refusal("guest_free_space")
    if not retained:
        ROOT.mkdir(mode=0o711)
        ROOT.chmod(0o711)
        (ROOT / "store").mkdir(mode=0o700)
    fd = _root()
    _end, _work_end = end, end - CLEANUP_RESERVE
    try:
        fixture = ROOT / "fixture.raw"
        image = ROOT / "image.raw"
        if retained:
            _private(ROOT / "pending.json")
            pending = _parse_pending(_read(ROOT / "pending.json", 4096))
            expected_file = "fixture.raw" if pending["phase"] == "fixture" else "image.raw"
            if _root_names() != {"pending.json", "store", expected_file}:
                raise Refusal("retained_state")
        else:
            fixture_uuid = str(uuid.uuid4())
            identity = _make_image(fixture, FIXTURE_BYTES, fixture_uuid, _work_end)
            pending = {"schema_version": 1, "phase": "fixture", "uuid": fixture_uuid,
                       "image_identity": list(identity), "fill_inode": 0, "fixture_written_bytes": 0}
            _save_pending(pending)
        if pending["phase"] == "fixture":
            identity = tuple(pending["image_identity"])
            with _mounted(fixture, FIXTURE_BYTES, pending["uuid"], identity, _work_end, initialize=True):
                _reset_fill(pending)
                proof = _probe(fill=True, deadline=_work_end, fill_inode=pending["fill_inode"])
            if _private(fixture, size=FIXTURE_BYTES) != identity or _associated(fixture, _work_end):
                raise Refusal("fixture_retirement")
            fixture.unlink()
            (ROOT / "pending.json").unlink()
            marker = ROOT / "parent-writable"
            _write_new(marker, b"parent remains writable after fixture ENOSPC")
            marker.unlink()
            capacity = os.statvfs(parent)
            if capacity.f_bavail * capacity.f_frsize < REQUIRED_FREE:
                raise Refusal("guest_free_space")
            filesystem_uuid = str(uuid.uuid4())
            identity = _make_image(image, IMAGE_BYTES, filesystem_uuid, _work_end)
            pending = {"schema_version": 1, "phase": "image", "uuid": filesystem_uuid,
                       "image_identity": list(identity), "fill_inode": 0, "fixture_written_bytes": proof["written_bytes"]}
            _save_pending(pending)
        identity = tuple(pending["image_identity"])
        with _mounted(image, IMAGE_BYTES, pending["uuid"], identity, _work_end, initialize=True):
            _probe(fill=False, deadline=_work_end)
        receipt = {"schema_version": 1, "uuid": pending["uuid"], "image_identity": list(identity), "fixture_verified": True}
        _write_new(ROOT / "receipt.json", json.dumps(receipt, sort_keys=True).encode())
        (ROOT / "pending.json").unlink()
        _remaining(end)
        return {"schema_version": 1, "status": "prepared", "image_bytes": IMAGE_BYTES,
                "fixture_bytes": FIXTURE_BYTES, "fixture_written_bytes": pending["fixture_written_bytes"],
                "escape_verified": True, "enospc_verified": True, "unmounted_verified": True,
                "work": str(WORK), "allocation_enabled": False}
    except (OSError, ValueError, UnicodeError):
        raise Refusal("guest_storage_unavailable") from None
    finally:
        _end = _work_end = None
        os.close(fd)
