"""Read-only aggregate inventory for the independently bound pilot image.

Only the two selected native mounts may be crossed. All qualification runs are
counted, including partially created workers. No result enables allocation,
qualifies disk format, or proves compatibility with a running worker.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields, replace
import fcntl
import json
import os
from pathlib import Path
import re
import stat

import probe_openshell_storage as legacy
import probe_openshell_storage_native as native
from probe_openshell_storage import Refusal


MAX_ENTRIES = legacy.MAX_ENTRIES
MAX_DEPTH = legacy.MAX_DEPTH
_RUN = re.compile(r"openshell-q-[a-f0-9]{12}\Z")
_EXCLUSIONS = {"_controller", "_config", "_networks"}
_DISKS = {"disk", "image", "basedisk", "diffdisk"}
_RUNNING_SOCKETS = {"ha.sock", "default_ep.sock", "default_fd.sock", "ssh.sock"}
_IMAGE_SUFFIXES = {".raw", ".qcow", ".qcow2", ".asif", ".dmg", ".sparseimage", ".sparsebundle", ".vmdk", ".vdi", ".vhd", ".vhdx"}


@dataclass(frozen=True)
class RetainedWorker:
    run_id: str
    name: str
    device: int
    inode: int
    has_config: bool
    disks: tuple[native.FileIdentity, ...]


@dataclass(frozen=True)
class NativeInventory:
    native_before: native.NativeStorageObservation
    native_after: native.NativeStorageObservation
    workers: tuple[RetainedWorker, ...]
    external_allocated_bytes: int
    image_allocated_bytes: int
    runtime_used_bytes: int
    cache_used_bytes: int
    maximum_vm_disk_logical_bytes: int
    entry_count: int
    socket_count: int
    fixture_alias_count: int
    free_bytes: int


@dataclass(frozen=True)
class StorageAdmission:
    blockers: tuple[str, ...]
    inventory_verified: bool = False
    required_free_bytes: int = legacy.REQUIRED_FREE_BYTES
    disk_format_qualification: str = "not_run"
    running_worker_qualification: str = "not_run"

    @property
    def allocation_enabled(self) -> bool:
        return False

    @property
    def admitted(self) -> bool:
        return False


@dataclass(frozen=True)
class _Scan:
    entries: tuple[native.FileIdentity, ...]
    workers: tuple[RetainedWorker, ...]
    external: int
    image: int
    maximum_disk: int
    aliases: int


def _stat(fd: int, name: str | None = None) -> os.stat_result:
    return os.fstat(fd) if name is None else os.stat(name, dir_fd=fd, follow_symlinks=False)


def _identity(path: Path, info: os.stat_result) -> native.FileIdentity:
    numbers = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink, info.st_size, info.st_blocks)
    if any(type(value) is not int or value < 0 for value in numbers):
        raise Refusal("storage_accounting")
    native._mode(info.st_mode)
    return native.FileIdentity(path, *numbers[:-1], numbers[-1] * 512)


def _check_selection(selection: native.NativeStorageSelection) -> None:
    native._check_selection(selection)
    if selection.profile != "pilot":
        raise Refusal("inventory_profile")


def _check_root_fd(selection: native.NativeStorageSelection, root_fd: int) -> None:
    if type(root_fd) is not int or root_fd < 0:
        raise Refusal("storage_identity")
    try:
        opened = _stat(root_fd)
        current = selection.pilot_root.lstat()
        if (not stat.S_ISDIR(opened.st_mode) or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o700
                or selection.pilot_root.resolve(strict=True) != selection.pilot_root
                or (opened.st_dev, opened.st_ino, opened.st_mode) != (current.st_dev, current.st_ino, current.st_mode)):
            raise Refusal("storage_identity")
    except (OSError, RuntimeError):
        raise Refusal("storage_unavailable") from None


def _check_native(selection: native.NativeStorageSelection, observation: native.NativeStorageObservation,
                  *, running: bool = False, identity_only: bool = False) -> None:
    if running:
        validator = (native.validate_running_native_storage_identity if identity_only
                     else native.validate_running_native_storage)
        report = validator(selection, observation)
    else:
        report = native.validate_native_storage(selection, observation, "inspect")
    if not report.topology_verified:
        raise Refusal(report.blockers[0])


def _same_binding(before: native.NativeStorageObservation, after: native.NativeStorageObservation, *, running: bool = False) -> None:
    # Deliberately conservative until the running-worker contract is qualified.
    # Host free space is sampled separately; unrelated host writes are not an
    # image identity change. Native image usage changes still refuse this phase.
    if running:
        native.assert_same_running_binding(before, after)
    elif before.after != after.before or before.native_after != after.native_before:
        raise Refusal("storage_changed")


def _unused_cache_route(selection: native.NativeStorageSelection, parts: tuple[str, ...]) -> bool:
    path = selection.pilot_root.joinpath(*parts)
    if path in {selection.home_path / "cache", selection.home_path / "tmp"}:
        return True
    return (len(parts) >= 4 and parts[0] == "qualification" and _RUN.fullmatch(parts[1]) is not None
            and parts[2:] in {("controller", "cache"), ("controller", "tmp"),
                              ("controller", "Library", "Caches", "lima")})


def _scan(selection: native.NativeStorageSelection, root_fd: int,
          observation: native.NativeStorageObservation, *, deadline: float | None = None, running: bool = False) -> _Scan:
    native._deadline_timeout(deadline)
    records: list[native.FileIdentity] = []
    workers: dict[tuple[str, str], RetainedWorker] = {}
    external = image = maximum_disk = aliases = 0
    root = selection.pilot_root
    bound = {item.path: item for item in observation.before}
    mounts = {path: bound[path] for path in (selection.runtime_path, selection.cache_path)}
    routes = {selection.cache_path / "_xdg", selection.cache_path / "_tmp"}
    seen_routes: set[Path] = set()
    seen_mounts: set[Path] = set()

    def walk(fd: int, parent: tuple[str, ...]) -> None:
        nonlocal external, image, maximum_disk, aliases
        native._deadline_timeout(deadline)
        if len(parent) > MAX_DEPTH:
            raise Refusal("storage_inventory_limit")
        original = _stat(fd)
        native._deadline_timeout(deadline)
        names = []
        unused_cache = _unused_cache_route(selection, parent)
        with os.scandir(fd) as entries:
            for entry in entries:
                native._deadline_timeout(deadline)
                if unused_cache:
                    raise Refusal("cache_route_retained")
                if len(records) + len(names) >= MAX_ENTRIES:
                    raise Refusal("storage_inventory_limit")
                names.append(entry.name)
        names.sort()
        for name in names:
            native._deadline_timeout(deadline)
            if len(records) >= MAX_ENTRIES:
                raise Refusal("storage_inventory_limit")
            parts = (*parent, name)
            path = root.joinpath(*parts)
            info = _stat(fd, name)
            native._deadline_timeout(deadline)
            item = _identity(path, info)
            records.append(item)
            if item.uid != observation.owner_uid:
                raise Refusal("storage_owner")
            if _unused_cache_route(selection, parts) and not stat.S_ISDIR(item.mode):
                raise Refusal("cache_route_unqualified")
            if path in mounts:
                expected = mounts[path]
                if (item.device, item.inode, item.mode) != (expected.device, expected.inode, expected.mode):
                    raise Refusal("storage_mount_unqualified")
                seen_mounts.add(path)
            elif item.device != original.st_dev:
                raise Refusal("storage_mount_unqualified")
            if path in routes:
                if (not stat.S_ISDIR(item.mode) or stat.S_IMODE(item.mode) != 0o700
                        or item.device != mounts[selection.cache_path].device):
                    raise Refusal("cache_route_unqualified")
                seen_routes.add(path)
            inside_image = path == selection.runtime_path or selection.runtime_path in path.parents
            inside_cache = path == selection.cache_path or selection.cache_path in path.parents
            if path == selection.image_path:
                same = (native._stable_file_identity(item) == native._stable_file_identity(bound[path])
                        if running else item == bound[path])
                if not same:
                    raise Refusal("storage_identity")
                image = item.allocated
            elif not inside_image:
                external += item.allocated
            if path != selection.image_path and not inside_cache and path.suffix.lower() in _IMAGE_SUFFIXES:
                raise Refusal("additional_image")
            qualification_run = len(parts) >= 2 and parts[0] == "qualification"
            finder_metadata = parts == ("qualification", ".DS_Store")
            if finder_metadata and (not stat.S_ISREG(item.mode) or item.links != 1 or item.size > 64 * 1024):
                raise Refusal("storage_owner")
            run_root = qualification_run and len(parts) == 2 and not finder_metadata
            if run_root and (_RUN.fullmatch(name) is None or not stat.S_ISDIR(item.mode)):
                raise Refusal("storage_owner")
            in_lima = qualification_run and len(parts) >= 3 and parts[2] == "lima"
            if in_lima and len(parts) == 3 and not stat.S_ISDIR(item.mode):
                raise Refusal("unexpected_lima_state")
            worker_root = in_lima and len(parts) == 4
            if worker_root:
                if (not stat.S_ISDIR(item.mode)
                        or (name.startswith(("_", ".")) and name not in _EXCLUSIONS)):
                    raise Refusal("unexpected_lima_state")
                if name not in _EXCLUSIONS:
                    workers[(parts[1], name)] = RetainedWorker(parts[1], name, item.device, item.inode, False, ())
            worker_key = (parts[1], parts[3]) if in_lima and len(parts) >= 5 else None
            if stat.S_ISDIR(item.mode):
                native._deadline_timeout(deadline)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    native._deadline_timeout(deadline)
                    if _identity(path, _stat(child)) != item:
                        raise Refusal("storage_identity")
                    if run_root:
                        legacy._run_marker(child, name)
                    walk(child, parts)
                finally:
                    os.close(child)
            elif stat.S_ISREG(item.mode):
                fixture_alias = legacy._fixture_alias(parts, item.size)
                if item.links != 1:
                    if not fixture_alias:
                        raise Refusal("storage_alias")
                    aliases += 1
                if worker_key in workers and len(parts) == 5:
                    worker = workers[worker_key]
                    if name == "lima.yaml":
                        workers[worker_key] = RetainedWorker(worker.run_id, worker.name, worker.device,
                                                             worker.inode, True, worker.disks)
                    elif name in _DISKS:
                        workers[worker_key] = RetainedWorker(worker.run_id, worker.name, worker.device,
                                                             worker.inode, worker.has_config, (*worker.disks, item))
                        maximum_disk = max(maximum_disk, item.size)
            elif stat.S_ISLNK(item.mode) and legacy._fixture_alias(parts, item.size):
                aliases += 1
            elif stat.S_ISSOCK(item.mode):
                if (not running or path.parent != selection.runtime_path / "q"
                        or name not in _RUNNING_SOCKETS or item.links != 1):
                    raise Refusal("inventory_socket_unqualified")
            else:
                raise Refusal("storage_alias")
        current = _stat(fd)
        native._deadline_timeout(deadline)
        if any(getattr(original, name) != getattr(current, name) for name in
               ("st_dev", "st_ino", "st_mode", "st_uid", "st_mtime_ns", "st_ctime_ns")):
            raise Refusal("storage_changed")

    walk(root_fd, ())
    native._deadline_timeout(deadline)
    if seen_mounts != set(mounts) or seen_routes != routes:
        raise Refusal("cache_route_unqualified")
    return _Scan(tuple(records), tuple(workers[key] for key in sorted(workers)), external, image, maximum_disk, aliases)


def _same_running_scans(selection: native.NativeStorageSelection, before: _Scan, after: _Scan) -> None:
    anchors = {selection.image_path, selection.runtime_path / "q/disk", selection.runtime_path / "q/lima.yaml"}

    def identity(item: native.FileIdentity) -> native.FileIdentity:
        stable = native._stable_file_identity(item)
        if (stat.S_ISREG(item.mode) and selection.runtime_path in item.path.parents
                and item.path not in anchors):
            stable = replace(stable, size=0)
        return stable

    if tuple(map(identity, before.entries)) != tuple(map(identity, after.entries)):
        raise Refusal("storage_changed")


def _collect_inventory(selection: native.NativeStorageSelection, root_fd: int, *, deadline: float | None,
                       running: bool) -> NativeInventory:
    native._deadline_timeout(deadline)
    _check_selection(selection)
    _check_root_fd(selection, root_fd)
    native._deadline_timeout(deadline)
    collector = native.collect_running_native_storage if running else native.collect_native_storage
    before = collector(selection, deadline=deadline)
    native._deadline_timeout(deadline)
    _check_native(selection, before, running=running, identity_only=running)
    try:
        first = _scan(selection, root_fd, before, deadline=deadline, running=running)
        second = _scan(selection, root_fd, before, deadline=deadline, running=running)
        native._deadline_timeout(deadline)
        if running:
            _same_running_scans(selection, first, second)
        elif first != second:
            raise Refusal("storage_changed")
        after = collector(selection, deadline=deadline)
        native._deadline_timeout(deadline)
        _check_native(selection, after, running=running, identity_only=running)
        _same_binding(before, after, running=running)
        _check_root_fd(selection, root_fd)
    except (OSError, RuntimeError):
        raise Refusal("storage_unavailable") from None
    snapshots = (before.native_before, before.native_after, after.native_before, after.native_after)
    image_allocation = max(item.allocated for observation in (before, after)
                           for records in (observation.before, observation.after)
                           for item in records if item.path == selection.image_path)
    external_allocation = sum(max(left.allocated, right.allocated)
                              for left, right in zip(first.entries, second.entries, strict=True)
                              if left.path not in {selection.image_path, selection.runtime_path}
                              and selection.runtime_path not in left.path.parents)
    result = NativeInventory(before, after, second.workers, external_allocation,
                           max(first.image, second.image, image_allocation),
                           max(s.container.capacity - s.container.free for s in snapshots),
                           max(s.container.cache.in_use for s in snapshots), first.maximum_disk,
                           len(second.entries), sum(stat.S_ISSOCK(item.mode) for item in second.entries),
                           max(first.aliases, second.aliases), min(before.free_bytes, after.free_bytes))
    if running:
        report = validate_running_inventory_identity(selection, result)
        if not report.inventory_verified:
            raise Refusal(report.blockers[0])
    native._deadline_timeout(deadline)
    return result


def _collect_locked(selection: native.NativeStorageSelection, root_fd: int, *, deadline: float | None = None) -> NativeInventory:
    """Borrow the caller's lock while retaining strict stopped-state behavior."""
    return _collect_inventory(selection, root_fd, deadline=deadline, running=False)


def collect_running_inventory_locked(selection: native.NativeStorageSelection, root_fd: int,
                                     *, deadline: float | None = None) -> NativeInventory:
    """Observe exact live resources; usage pressure alone cannot block safe stop."""
    return _collect_inventory(selection, root_fd, deadline=deadline, running=True)


def collect_native_inventory(selection: native.NativeStorageSelection, *, deadline: float | None = None) -> NativeInventory:
    """Collect fresh state under the exclusive root lock without writing files."""
    native._deadline_timeout(deadline)
    _check_selection(selection)
    native._deadline_timeout(deadline)
    fd = legacy._open_root(selection.pilot_root)
    try:
        native._deadline_timeout(deadline)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("storage_busy") from None
        except OSError:
            raise Refusal("storage_lock_unavailable") from None
        return _collect_locked(selection, fd, deadline=deadline)
    finally:
        os.close(fd)


def _validate_inventory(selection: native.NativeStorageSelection, inventory: NativeInventory,
                        *, running: bool, identity_only: bool) -> StorageAdmission:
    try:
        _check_selection(selection)
        if type(inventory) is not NativeInventory or type(inventory.workers) is not tuple:
            raise Refusal("invalid_inventory")
        for field in fields(NativeInventory):
            if field.name not in {"native_before", "native_after", "workers"}:
                native._number(getattr(inventory, field.name))
        _check_native(selection, inventory.native_before, running=running, identity_only=identity_only)
        _check_native(selection, inventory.native_after, running=running, identity_only=identity_only)
        _same_binding(inventory.native_before, inventory.native_after, running=running)
        identities: set[tuple[str, str]] = set()
        disks = []
        for worker in inventory.workers:
            if (type(worker) is not RetainedWorker or not isinstance(worker.run_id, str)
                    or _RUN.fullmatch(worker.run_id) is None or not isinstance(worker.name, str)
                    or not worker.name or "/" in worker.name or "\x00" in worker.name
                    or worker.name.startswith(("_", ".")) or type(worker.has_config) is not bool
                    or type(worker.disks) is not tuple):
                raise Refusal("invalid_inventory")
            for number in (worker.device, worker.inode):
                if native._number(number) == 0:
                    raise Refusal("invalid_inventory")
            identity = (worker.run_id, worker.name)
            if identity in identities:
                raise Refusal("invalid_inventory")
            identities.add(identity)
            names = set()
            for disk in worker.disks:
                if type(disk) is not native.FileIdentity:
                    raise Refusal("invalid_inventory")
                for number in (disk.device, disk.inode, disk.mode, disk.uid, disk.links, disk.size, disk.allocated):
                    native._number(number)
                native._mode(disk.mode)
                if (not isinstance(disk.path, Path)
                        or disk.path.parent != selection.pilot_root / "qualification" / worker.run_id / "lima" / worker.name
                        or disk.path.name not in _DISKS or disk.path.name in names
                        or not stat.S_ISREG(disk.mode) or disk.links != 1
                        or disk.device != worker.device or disk.uid != inventory.native_before.owner_uid):
                    raise Refusal("invalid_inventory")
                disks.append(disk.size)
                names.add(disk.path.name)
        snapshots = (inventory.native_before.native_before, inventory.native_before.native_after,
                     inventory.native_after.native_before, inventory.native_after.native_after)
        image_allocation = max(item.allocated for observation in (inventory.native_before, inventory.native_after)
                               for records in (observation.before, observation.after)
                               for item in records if item.path == selection.image_path)
        if (inventory.maximum_vm_disk_logical_bytes != max(disks, default=0)
                or (inventory.image_allocated_bytes < image_allocation if running else inventory.image_allocated_bytes != image_allocation)
                or inventory.runtime_used_bytes != max(s.container.capacity - s.container.free for s in snapshots)
                or inventory.cache_used_bytes != max(s.container.cache.in_use for s in snapshots)
                or inventory.free_bytes != min(inventory.native_before.free_bytes, inventory.native_after.free_bytes)
                or inventory.entry_count > MAX_ENTRIES or inventory.fixture_alias_count > inventory.entry_count
                or inventory.socket_count > (len(_RUNNING_SOCKETS) if running else 0)):
            raise Refusal("invalid_inventory")
        if running and (len(inventory.workers) != 1 or inventory.workers[0].run_id != selection.run_root.name
                        or inventory.workers[0].name != "q" or not inventory.workers[0].has_config
                        or len(inventory.workers[0].disks) != 1 or inventory.workers[0].disks[0].path.name != "disk"):
            raise Refusal("worker_identity")
    except Refusal as error:
        return StorageAdmission((str(error),))
    if identity_only:
        return StorageAdmission((), inventory_verified=True)
    blockers = tuple(reason for exceeded, reason in (
        (len(inventory.workers) > legacy.RETAINED_VM_LIMIT, "retained_vm_limit"),
        (inventory.maximum_vm_disk_logical_bytes > legacy.VIRTUAL_DISK_LIMIT, "virtual_disk_limit"),
        (inventory.external_allocated_bytes > legacy.EXTERNAL_RETENTION_LIMIT, "external_retention_limit"),
        (inventory.image_allocated_bytes > legacy.RUNTIME_STORAGE_LIMIT + legacy.IMAGE_OVERHEAD_LIMIT, "image_allocation_limit"),
        (inventory.runtime_used_bytes > legacy.RUNTIME_STORAGE_LIMIT, "runtime_storage_limit"),
        (inventory.cache_used_bytes > legacy.CACHE_LIMIT, "cache_limit"),
        (inventory.free_bytes < legacy.REQUIRED_FREE_BYTES, "host_free_space"),
    ) if exceeded)
    return StorageAdmission(blockers, inventory_verified=not blockers)


def validate_native_inventory(selection: native.NativeStorageSelection, inventory: NativeInventory) -> StorageAdmission:
    """Preserve strict stopped-state validation and its existing refusal rules."""
    return _validate_inventory(selection, inventory, running=False, identity_only=False)


def validate_running_inventory(selection: native.NativeStorageSelection, inventory: NativeInventory) -> StorageAdmission:
    """Validate live identities and all usage budgets without enabling an operation."""
    return _validate_inventory(selection, inventory, running=True, identity_only=False)


def validate_running_inventory_identity(selection: native.NativeStorageSelection, inventory: NativeInventory) -> StorageAdmission:
    """Verify exact recovery identities, independent of usage-pressure blockers.

    A verified result here permits no operation. The boot controller must still
    bind its original worker, configuration, disk, and source evidence for stop.
    """
    return _validate_inventory(selection, inventory, running=True, identity_only=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    args = parser.parse_args()
    report = StorageAdmission(("selection_unavailable",))
    counts: dict[str, int] = {}
    from probe_openshell_runtime import Refusal as CommandRefusal, private_file
    try:
        selection = native.parse_selection(private_file(args.selection))
        observed = collect_native_inventory(selection)
        report = validate_native_inventory(selection, observed)
        counts = {field.name: getattr(observed, field.name) for field in fields(NativeInventory)
                  if field.name not in {"native_before", "native_after", "workers"}}
        counts["retained_vm_count"] = len(observed.workers)
    except Refusal as error:
        report = StorageAdmission((str(error),))
    except (OSError, CommandRefusal):
        report = StorageAdmission(("selection_unavailable",))
    print(json.dumps({"schema_version": 1, **asdict(report), "inventory": counts,
                      "allocation_enabled": False}, sort_keys=True))
    return 0 if report.inventory_verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
