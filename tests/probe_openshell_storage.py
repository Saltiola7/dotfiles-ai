"""Read-only storage inventory and fail-closed pilot allocation admission.

This internal module installs no quota and starts no runtime. The native bounded
image/cache topology remains unqualified, so allocation is always refused.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import fcntl
import json
import os
from pathlib import Path
import re
import stat
from typing import Iterator


GIB = 1024**3
RETAINED_VM_LIMIT = 1
VIRTUAL_DISK_LIMIT = 20 * GIB
RUNTIME_STORAGE_LIMIT = 24 * GIB
CACHE_LIMIT = 2 * GIB
HOST_RESERVE = 20 * GIB
IMAGE_OVERHEAD_LIMIT = GIB
EXTERNAL_RETENTION_LIMIT = GIB
REQUIRED_FREE_BYTES = RUNTIME_STORAGE_LIMIT + IMAGE_OVERHEAD_LIMIT + EXTERNAL_RETENTION_LIMIT + HOST_RESERVE
MAX_ENTRIES = 20000
MAX_DEPTH = 32
_RUN_NAME = re.compile(r"openshell-q-[a-f0-9]{12}\Z")


class Refusal(Exception):
    """A path-free reason; no caller-owned receipt can override it."""


@dataclass(frozen=True)
class StorageInventory:
    allocated_bytes: int = 0
    logical_bytes: int = 0
    runtime_allocated_bytes: int = 0
    external_allocated_bytes: int = 0
    lima_cache_allocated_bytes: int = 0
    other_cache_allocated_bytes: int = 0
    maximum_vm_disk_logical_bytes: int = 0
    retained_vm_count: int = 0
    entry_count: int = 0
    symlink_count: int = 0
    free_bytes: int = 0


@dataclass(frozen=True)
class StorageAdmission:
    blockers: tuple[str, ...]
    required_free_bytes: int = REQUIRED_FREE_BYTES

    @property
    def admitted(self) -> bool:
        # Native image/quota proof has no implementation in this increment.
        return False


def _open_root(root: Path) -> int:
    if not isinstance(root, Path) or not root.is_absolute():
        raise Refusal("storage_owner")
    try:
        info = root.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700 or root.resolve(strict=True) != root):
            raise Refusal("storage_owner")
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            actual = os.fstat(fd)
            if (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino):
                raise Refusal("storage_identity")
        except BaseException:
            os.close(fd)
            raise
        return fd
    except OSError:
        raise Refusal("storage_unavailable") from None


def _run_marker(fd: int, name: str) -> None:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise Refusal("storage_owner")
            value[key] = item
        return value

    try:
        marker = os.open("owner.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            stream = os.fdopen(marker, "rb")
        except BaseException:
            os.close(marker)
            raise
        with stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 4096):
                raise Refusal("storage_owner")
            raw = stream.read(4097)
            if len(raw) > 4096:
                raise Refusal("storage_owner")
        value = json.loads(raw, object_pairs_hook=unique)
        if (not isinstance(value, dict) or set(value) != {"schema_version", "run_id"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["run_id"] != name):
            raise Refusal("storage_owner")
    except (OSError, ValueError, RecursionError):
        raise Refusal("storage_owner") from None


def _run_parts(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 2 and parts[0] == "qualification" and _RUN_NAME.fullmatch(parts[1]) is not None


def _fixture_alias(parts: tuple[str, ...], size: int) -> bool:
    return _run_parts(parts) and len(parts) >= 4 and parts[2] in {"fixture", "input"} and size <= 4096


def _inspect_fd(root: Path, root_fd: int) -> StorageInventory:
    root_info = os.fstat(root_fd)
    counts = {field.name: 0 for field in fields(StorageInventory)}

    def scan(fd: int, parent: tuple[str, ...]) -> None:
        if len(parent) > MAX_DEPTH:
            raise Refusal("storage_inventory_limit")
        with os.scandir(fd) as entries:
            for entry in entries:
                counts["entry_count"] += 1
                if counts["entry_count"] > MAX_ENTRIES:
                    raise Refusal("storage_inventory_limit")
                parts = (*parent, entry.name)
                info = entry.stat(follow_symlinks=False)
                if info.st_uid != os.getuid():
                    raise Refusal("storage_owner")
                if info.st_dev != root_info.st_dev:
                    raise Refusal("storage_mount_unqualified")
                blocks = getattr(info, "st_blocks", None)
                if type(blocks) is not int or blocks < 0 or info.st_size < 0:
                    raise Refusal("storage_accounting")
                allocated = blocks * 512
                counts["allocated_bytes"] += allocated
                runtime = _run_parts(parts) and len(parts) >= 3 and parts[2] in {"controller", "lima"}
                counts["runtime_allocated_bytes" if runtime else "external_allocated_bytes"] += allocated
                if _run_parts(parts) and parts[2:6] == ("controller", "Library", "Caches", "lima"):
                    counts["lima_cache_allocated_bytes"] += allocated
                elif _run_parts(parts) and parts[2:4] == ("controller", "cache"):
                    counts["other_cache_allocated_bytes"] += allocated
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                            raise Refusal("storage_identity")
                        if len(parts) == 2 and parts[0] == "qualification":
                            if _RUN_NAME.fullmatch(parts[1]) is None:
                                raise Refusal("storage_owner")
                            _run_marker(child, parts[1])
                        if (_run_parts(parts) and len(parts) == 4 and parts[2] == "lima"
                                and parts[3] not in {"_config", "_networks"}):
                            counts["retained_vm_count"] += 1
                        scan(child, parts)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_nlink != 1 and not _fixture_alias(parts, info.st_size):
                        raise Refusal("storage_alias")
                    counts["logical_bytes"] += info.st_size
                    if (_run_parts(parts) and len(parts) == 5 and parts[2] == "lima"
                            and parts[4] in {"disk", "basedisk", "diffdisk"}):
                        counts["maximum_vm_disk_logical_bytes"] = max(
                            counts["maximum_vm_disk_logical_bytes"], info.st_size)
                elif stat.S_ISLNK(info.st_mode) and _fixture_alias(parts, info.st_size):
                    counts["symlink_count"] += 1
                else:
                    raise Refusal("storage_alias")

    try:
        scan(root_fd, ())
        capacity = os.fstatvfs(root_fd)
        if (type(capacity.f_bavail) is not int or capacity.f_bavail < 0
                or type(capacity.f_frsize) is not int or capacity.f_frsize <= 0):
            raise Refusal("storage_accounting")
        counts["free_bytes"] = capacity.f_bavail * capacity.f_frsize
        after = root.lstat()
        if (after.st_dev, after.st_ino) != (root_info.st_dev, root_info.st_ino):
            raise Refusal("storage_identity")
        return StorageInventory(**counts)
    except OSError:
        raise Refusal("storage_unavailable") from None


def inspect_storage(root: Path) -> StorageInventory:
    """Count the private store without following aliases or creating anything.

    Allocated blocks are conservative: hard-linked fixture entries can be counted
    twice, and APFS clone sharing never becomes credit for future growth.
    """
    fd = _open_root(root)
    try:
        return _inspect_fd(root, fd)
    finally:
        os.close(fd)


def admit_storage(inventory: StorageInventory) -> StorageAdmission:
    """Report all blockers; portable accounting is never native quota proof."""
    if (not isinstance(inventory, StorageInventory)
            or any(type(getattr(inventory, field.name)) is not int or getattr(inventory, field.name) < 0
                   for field in fields(StorageInventory))):
        raise Refusal("storage_accounting")
    blockers = []
    for exceeded, reason in (
        (inventory.free_bytes < REQUIRED_FREE_BYTES, "host_free_space"),
        (inventory.retained_vm_count > RETAINED_VM_LIMIT, "retained_vm_limit"),
        (inventory.maximum_vm_disk_logical_bytes > VIRTUAL_DISK_LIMIT, "virtual_disk_limit"),
        (inventory.runtime_allocated_bytes > RUNTIME_STORAGE_LIMIT, "runtime_storage_limit"),
        (inventory.lima_cache_allocated_bytes + inventory.other_cache_allocated_bytes > CACHE_LIMIT, "cache_limit"),
        (inventory.external_allocated_bytes > EXTERNAL_RETENTION_LIMIT, "external_retention_limit"),
    ):
        if exceeded:
            blockers.append(reason)
    blockers.append("storage_enforcement_unqualified")
    return StorageAdmission(tuple(blockers))


@contextmanager
def allocation_guard(root: Path) -> Iterator[None]:
    """Hold the real directory lock through admission and any future operation."""
    fd = _open_root(root)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("storage_busy") from None
        except OSError:
            raise Refusal("storage_lock_unavailable") from None
        admission = admit_storage(_inspect_fd(root, fd))
        if not admission.admitted:
            raise Refusal(admission.blockers[0])
        yield
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    report = {"schema_version": 1, "status": "refused", "hard_limits": "unqualified",
              "runtime_qualification": "not_run", "required_free_bytes": REQUIRED_FREE_BYTES}
    try:
        inventory = inspect_storage(args.root)
        admission = admit_storage(inventory)
        report.update({"inventory": asdict(inventory), "blockers": admission.blockers})
    except Refusal as error:
        report["blockers"] = [str(error)]
    print(json.dumps(report, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
