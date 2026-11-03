"""Inspect owned APFS image bindings without admitting any allocating operation.

This internal collector runs only bounded, fixed native read commands. Selection
metadata supplies comparison identities, never a quota receipt or an override.
The existing runtime allocation guard remains independently fail-closed. This
increment does not qualify aggregate external retention or retained VM inventory.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields, replace
import json
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import time
from xml.parsers.expat import ExpatError

from probe_openshell_runtime import CommandResult, Refusal as CommandRefusal, run_command
from probe_openshell_storage import REQUIRED_FREE_BYTES, Refusal


MIB = 1024**2
GIB = 1024**3
NATIVE_LIMIT = 1024**2
_UUID = re.compile(r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\Z")
_DEVICE = re.compile(r"disk[0-9]{1,5}(?:s[0-9]{1,5})?\Z")
_HINTS = {
    "GUID_partition_scheme": "whole",
    "Apple_APFS": "store", "7C3457EF-0000-11AA-AA11-00306543ECAC": "store",
    "Apple_APFS_Container": "container", "EF57347C-0000-11AA-AA11-00306543ECAC": "container",
    "Apple_APFS_Volume": "volume", "41504653-0000-11AA-AA11-00306543ECAC": "volume",
}


@dataclass(frozen=True)
class NativeStorageSelection:
    profile: str
    pilot_root: Path
    run_root: Path
    image_path: Path
    image_device: int
    image_inode: int
    container_uuid: str
    runtime_uuid: str
    cache_uuid: str

    @property
    def image_bytes(self) -> int:
        return 768 * MIB if self.profile == "mechanism" else 24 * GIB

    @property
    def cache_bytes(self) -> int:
        return 32 * MIB if self.profile == "mechanism" else 2 * GIB

    @property
    def runtime_path(self) -> Path:
        return self.run_root / ("runtime" if self.profile == "mechanism" else "lima")

    @property
    def home_path(self) -> Path:
        return self.runtime_path / ("controller" if self.profile == "mechanism" else "_controller")

    @property
    def cache_path(self) -> Path:
        return self.home_path / "Library/Caches/lima"


@dataclass(frozen=True)
class FileIdentity:
    path: Path
    device: int
    inode: int
    mode: int
    uid: int
    links: int
    size: int
    allocated: int


@dataclass(frozen=True)
class Attachment:
    image_path: str
    owner_uid: int
    owner_mode: int
    writable: bool
    image_bytes: int
    whole_device: str
    physical_store: str
    container_device: str
    volume_devices: tuple[str, ...]


@dataclass(frozen=True)
class Volume:
    uuid: str
    device: str
    quota: int
    reserve: int
    in_use: int


@dataclass(frozen=True)
class Container:
    uuid: str
    device: str
    physical_store: str
    physical_uuid: str
    physical_size: int
    capacity: int
    free: int
    runtime: Volume
    cache: Volume


@dataclass(frozen=True)
class Mount:
    volume_uuid: str
    device: str
    container_device: str
    physical_store: str
    mountpoint: str
    writable: bool
    capacity: int


@dataclass(frozen=True)
class NativeSnapshot:
    attachment: Attachment
    container: Container
    runtime: Mount
    cache: Mount


@dataclass(frozen=True)
class NativeStorageObservation:
    owner_uid: int
    before: tuple[FileIdentity, ...]
    after: tuple[FileIdentity, ...]
    native_before: NativeSnapshot
    native_after: NativeSnapshot
    free_bytes: int


@dataclass(frozen=True)
class StorageAdmission:
    blockers: tuple[str, ...]
    topology_verified: bool = False
    required_free_bytes: int = REQUIRED_FREE_BYTES
    inventory_qualification: str = "not_run"

    @property
    def allocation_enabled(self) -> bool:
        return False

    @property
    def admitted(self) -> bool:
        return False


class _UniqueDict(dict[str, object]):
    def __setitem__(self, key: str, value: object) -> None:
        if key in self:
            raise Refusal("duplicate_field")
        super().__setitem__(key, value)


def _unique_json(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("duplicate_field")
        result[key] = value
    return result


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise Refusal("native_schema")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list) or len(value) > 256:
        raise Refusal("native_schema")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or len(value) > 4096 or "\x00" in value:
        raise Refusal("native_schema")
    return value


def _number(value: object) -> int:
    if type(value) is not int or not 0 <= value < 2**63:
        raise Refusal("native_schema")
    return value


def _mode(value: object) -> int:
    value = _number(value)
    if value > 0xffff:
        raise Refusal("native_schema")
    return value


def _deadline_timeout(deadline: float | None) -> float:
    """Check an absolute monotonic deadline and bound the next native call."""
    if deadline is None:
        return 10.0
    if type(deadline) is not float or not math.isfinite(deadline):
        raise Refusal("invalid_deadline")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Refusal("storage_deadline")
    return min(10.0, remaining)


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise Refusal("native_schema")
    return value


def _uuid(value: object) -> str:
    value = _text(value)
    if _UUID.fullmatch(value) is None:
        raise Refusal("native_schema")
    return value


def normalize_device(value: object) -> str:
    """Accept the two native spellings, never arbitrary command arguments."""
    value = _text(value)
    device = value.removeprefix("/dev/")
    if _DEVICE.fullmatch(device) is None:
        raise Refusal("native_device")
    return device


def _path(value: object) -> Path:
    value = _text(value)
    try:
        os.fsencode(value)
    except UnicodeError:
        raise Refusal("invalid_selection") from None
    path = Path(value)
    if (not path.is_absolute() or str(path) != value
            or any(part in {"", ".", ".."} for part in value.split("/")[1:])):
        raise Refusal("invalid_selection")
    return path


def parse_selection(raw: bytes) -> NativeStorageSelection:
    """Parse the closed comparison-only selection, without reading the image."""
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise Refusal("invalid_selection")
    try:
        value = _object(json.loads(raw, object_pairs_hook=_unique_json))
        keys = {field.name for field in fields(NativeStorageSelection)} | {"schema_version"}
        if (set(value) != keys or type(value["schema_version"]) is not int
                or value["schema_version"] != 1):
            raise Refusal("invalid_selection")
        selected = NativeStorageSelection(
            _text(value["profile"]), _path(value["pilot_root"]), _path(value["run_root"]),
            _path(value["image_path"]), _number(value["image_device"]), _number(value["image_inode"]),
            _uuid(value["container_uuid"]), _uuid(value["runtime_uuid"]), _uuid(value["cache_uuid"]))
        if selected.profile not in {"mechanism", "pilot"}:
            raise Refusal("invalid_selection")
        mechanism = selected.profile == "mechanism"
        parent = "storage-qualification" if mechanism else "qualification"
        prefix = "s" if mechanism else "q"
        filename = "quota-test.raw" if mechanism else "runtime.raw"
        if (selected.run_root.parent != selected.pilot_root / parent
                or re.fullmatch(r"openshell-" + prefix + r"-[a-f0-9]{12}", selected.run_root.name) is None
                or selected.image_path != selected.run_root / filename
                or selected.image_device == 0 or selected.image_inode == 0
                or len({selected.container_uuid, selected.runtime_uuid, selected.cache_uuid}) != 3):
            raise Refusal("invalid_selection")
        return selected
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal("invalid_selection") from None


def _check_selection(selection: NativeStorageSelection) -> None:
    if type(selection) is not NativeStorageSelection:
        raise Refusal("invalid_selection")
    values = {field.name: getattr(selection, field.name) for field in fields(selection)}
    for name in ("pilot_root", "run_root", "image_path"):
        if not isinstance(values[name], Path):
            raise Refusal("invalid_selection")
        values[name] = str(values[name])
    for name in ("profile", "container_uuid", "runtime_uuid", "cache_uuid"):
        if type(values[name]) is not str:
            raise Refusal("invalid_selection")
    for name in ("image_device", "image_inode"):
        if type(values[name]) is not int:
            raise Refusal("invalid_selection")
    parse_selection(json.dumps({"schema_version": 1, **values}).encode())


def _paths(selection: NativeStorageSelection) -> tuple[Path, ...]:
    home = selection.home_path
    return (selection.pilot_root, selection.run_root.parent, selection.run_root,
            selection.image_path, selection.runtime_path, home, home / "Library", home / "Library/Caches",
            *(home / name for name in ("tmp", "config", "data", "state", "cache")), selection.cache_path)


def _observe_paths(selection: NativeStorageSelection, *, deadline: float | None = None) -> tuple[FileIdentity, ...]:
    result = []
    try:
        for path in _paths(selection):
            _deadline_timeout(deadline)
            info = path.lstat()
            _deadline_timeout(deadline)
            image = path == selection.image_path
            expected_mode = 0o600 if image else 0o700
            if (path.resolve(strict=True) != path or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != expected_mode
                    or not (stat.S_ISREG(info.st_mode) if image else stat.S_ISDIR(info.st_mode))
                    or (image and (info.st_nlink != 1 or info.st_size != selection.image_bytes
                                   or (info.st_dev, info.st_ino) != (selection.image_device, selection.image_inode)))):
                raise Refusal("storage_identity")
            _deadline_timeout(deadline)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (0 if image else os.O_DIRECTORY))
            try:
                _deadline_timeout(deadline)
                opened = os.fstat(fd)
                if (opened.st_dev, opened.st_ino, opened.st_mode) != (info.st_dev, info.st_ino, info.st_mode):
                    raise Refusal("storage_identity")
            finally:
                os.close(fd)
            _deadline_timeout(deadline)
            result.append(FileIdentity(path, info.st_dev, info.st_ino, info.st_mode, info.st_uid,
                                       info.st_nlink, info.st_size, _number(info.st_blocks) * 512))
    except (OSError, RuntimeError):
        raise Refusal("storage_unavailable") from None
    return tuple(result)


def _host_free(root: Path, *, deadline: float | None = None) -> int:
    _deadline_timeout(deadline)
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _deadline_timeout(deadline)
            space = os.fstatvfs(fd)
            available = _number(space.f_bavail) * _number(space.f_frsize)
        finally:
            os.close(fd)
    except OSError:
        raise Refusal("storage_unavailable") from None
    _deadline_timeout(deadline)
    return available


def _query(selection: NativeStorageSelection, argv: list[str], *, deadline: float | None = None) -> dict[str, object]:
    timeout = _deadline_timeout(deadline)
    try:
        result = run_command(argv, cwd=selection.run_root,
                             env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C", "HOME": "/"},
                             timeout=timeout, limit=NATIVE_LIMIT)
    except CommandRefusal as error:
        reason = str(error)
        raise Refusal("native_" + reason if reason in {"timeout", "output_limit"} else "native_unavailable") from None
    _deadline_timeout(deadline)
    if result.returncode != 0:
        raise Refusal("native_unavailable")
    if len(result.stdout) + len(result.stderr) > NATIVE_LIMIT:
        raise Refusal("native_output_limit")
    try:
        parsed = _object(plistlib.loads(result.stdout, dict_type=_UniqueDict))
    except (ValueError, TypeError, OverflowError, RecursionError, ExpatError):
        raise Refusal("native_schema") from None
    _deadline_timeout(deadline)
    return parsed


def _attachment(value: dict[str, object], selection: NativeStorageSelection) -> Attachment:
    images = [_object(item) for item in _list(value.get("images"))]
    matches = [item for item in images if item.get("image-path") == str(selection.image_path)]
    if len(matches) != 1:
        raise Refusal("native_attachment")
    image = matches[0]
    if (any("shadow" in key.lower() for key in image)
            or image.get("image-type") != "read/write disk image" or image.get("image-encrypted") is not False):
        raise Refusal("native_attachment")
    devices: dict[str, list[str]] = {name: [] for name in ("whole", "store", "container", "volume")}
    entities = [_object(item) for item in _list(image.get("system-entities"))]
    for entity in entities:
        hint = _text(entity.get("content-hint"))
        if hint not in _HINTS or any("shadow" in key.lower() for key in entity):
            raise Refusal("native_attachment")
        devices[_HINTS[hint]].append(normalize_device(entity.get("dev-entry")))
    if (any(len(devices[name]) != 1 for name in ("whole", "store", "container"))
            or len(devices["volume"]) != 2):
        raise Refusal("native_attachment")
    all_devices = [device for group in devices.values() for device in group]
    if len(set(all_devices)) != len(all_devices):
        raise Refusal("native_attachment")
    # Another attachment sharing any selected device makes ownership ambiguous.
    for other in images:
        if other is image:
            continue
        for item in _list(other.get("system-entities")):
            device = normalize_device(_object(item).get("dev-entry"))
            if device in all_devices:
                raise Refusal("native_attachment")
    return Attachment(str(selection.image_path), _number(image.get("owner-uid")),
                      _number(image.get("owner-mode")), _boolean(image.get("writeable")),
                      _number(image.get("blockcount")) * _number(image.get("blocksize")),
                      devices["whole"][0], devices["store"][0], devices["container"][0],
                      tuple(sorted(devices["volume"])))


def _volume(value: dict[str, object]) -> Volume:
    return Volume(_uuid(value.get("APFSVolumeUUID")), normalize_device(value.get("DeviceIdentifier")),
                  _number(value.get("CapacityQuota")), _number(value.get("CapacityReserve")),
                  _number(value.get("CapacityInUse")))


def _container(value: dict[str, object], selection: NativeStorageSelection) -> Container:
    containers = _list(value.get("Containers"))
    if len(containers) != 1:
        raise Refusal("native_container")
    container = _object(containers[0])
    stores = _list(container.get("PhysicalStores"))
    volumes = [_volume(_object(item)) for item in _list(container.get("Volumes"))]
    if len(stores) != 1 or len(volumes) != 2 or {item.uuid for item in volumes} != {selection.runtime_uuid, selection.cache_uuid}:
        raise Refusal("native_container")
    store = _object(stores[0])
    device = normalize_device(store.get("DeviceIdentifier"))
    if normalize_device(container.get("DesignatedPhysicalStore")) != device:
        raise Refusal("native_container")
    return Container(_uuid(container.get("APFSContainerUUID")), normalize_device(container.get("ContainerReference")),
                     device, _uuid(store.get("DiskUUID")), _number(store.get("Size")),
                     _number(container.get("CapacityCeiling")), _number(container.get("CapacityFree")),
                     next(item for item in volumes if item.uuid == selection.runtime_uuid),
                     next(item for item in volumes if item.uuid == selection.cache_uuid))


def _mount(value: dict[str, object]) -> Mount:
    stores = _list(value.get("APFSPhysicalStores"))
    device = normalize_device(value.get("DeviceIdentifier"))
    if (len(stores) != 1 or value.get("FilesystemType") != "apfs"
            or value.get("DeviceNode") != "/dev/" + device):
        raise Refusal("native_mount")
    return Mount(_uuid(value.get("VolumeUUID")), device, normalize_device(value.get("APFSContainerReference")),
                 normalize_device(_object(stores[0]).get("APFSPhysicalStore")), _text(value.get("MountPoint")),
                 _boolean(value.get("WritableVolume")), _number(value.get("APFSContainerSize")))


def _native_snapshot(selection: NativeStorageSelection, *, deadline: float | None = None) -> NativeSnapshot:
    attachment = _attachment(_query(selection, ["/usr/bin/hdiutil", "info", "-plist"], deadline=deadline), selection)
    container = _container(_query(selection, ["/usr/sbin/diskutil", "apfs", "list", "-plist",
                                            attachment.container_device], deadline=deadline), selection)
    runtime = _mount(_query(selection, ["/usr/sbin/diskutil", "info", "-plist", str(selection.runtime_path)], deadline=deadline))
    cache = _mount(_query(selection, ["/usr/sbin/diskutil", "info", "-plist", str(selection.cache_path)], deadline=deadline))
    _deadline_timeout(deadline)
    return NativeSnapshot(attachment, container, runtime, cache)


def collect_native_storage(selection: NativeStorageSelection, *, deadline: float | None = None) -> NativeStorageObservation:
    """Collect fresh state without writes, using an optional shared deadline.

    Checks between filesystem steps cannot interrupt a blocking kernel call.
    Native subprocesses additionally receive the remaining execution budget.
    """
    _deadline_timeout(deadline)
    _check_selection(selection)
    before = _observe_paths(selection, deadline=deadline)
    free_before = _host_free(selection.pilot_root, deadline=deadline)
    first = _native_snapshot(selection, deadline=deadline)
    second = _native_snapshot(selection, deadline=deadline)
    after = _observe_paths(selection, deadline=deadline)
    observation = NativeStorageObservation(os.getuid(), before, after, first, second,
                                           min(free_before, _host_free(selection.pilot_root, deadline=deadline)))
    _deadline_timeout(deadline)
    return observation


def collect_running_native_storage(selection: NativeStorageSelection, *, deadline: float | None = None) -> NativeStorageObservation:
    """Collect live usage without relaxing identity or native capacity bindings.

    Usage pressure is reported for admission and cannot suppress an identity
    observation needed to stop the exact worker safely.
    """
    observation = collect_native_storage(selection, deadline=deadline)
    report = validate_running_native_storage_identity(selection, observation)
    if not report.topology_verified:
        raise Refusal(report.blockers[0])
    _deadline_timeout(deadline)
    return observation


def _typed(value: object, expected: type) -> None:
    """Do not accept dictionaries or truthy scalar substitutions as evidence."""
    if type(value) is not expected:
        raise Refusal("native_observation")


def _validate_snapshot(selection: NativeStorageSelection, snapshot: NativeSnapshot, uid: int, *, check_usage: bool = True) -> None:
    _typed(snapshot, NativeSnapshot)
    image, container = snapshot.attachment, snapshot.container
    _typed(image, Attachment)
    _typed(container, Container)
    for volume in (container.runtime, container.cache):
        _typed(volume, Volume)
        _uuid(volume.uuid)
        normalize_device(volume.device)
        for amount in (volume.quota, volume.reserve, volume.in_use):
            _number(amount)
    for amount in (image.owner_uid, image.owner_mode, image.image_bytes,
                   container.physical_size, container.capacity, container.free):
        _number(amount)
    for device in (image.whole_device, image.physical_store, image.container_device,
                   container.device, container.physical_store):
        normalize_device(device)
    _uuid(container.uuid)
    _uuid(container.physical_uuid)
    _typed(image.volume_devices, tuple)
    if (image.image_path != str(selection.image_path) or image.owner_uid != uid or image.owner_mode != 0o600
            or image.writable is not True or image.image_bytes != selection.image_bytes
            or re.fullmatch(r"disk[0-9]+", image.whole_device) is None
            or re.fullmatch(re.escape(image.whole_device) + r"s[0-9]+", image.physical_store) is None
            or image.container_device == image.whole_device
            or container.uuid != selection.container_uuid or container.device != image.container_device
            or container.physical_store != image.physical_store
            or not 0 < container.capacity == container.physical_size < image.image_bytes
            or container.free > container.capacity
            or container.runtime.uuid != selection.runtime_uuid or container.cache.uuid != selection.cache_uuid
            or container.runtime.device == container.cache.device
            or tuple(sorted((container.runtime.device, container.cache.device))) != image.volume_devices
            or container.runtime.quota != 0 or container.cache.quota != selection.cache_bytes
            or any(volume.reserve != 0 for volume in (container.runtime, container.cache))):
        raise Refusal("native_binding")
    if check_usage and (container.runtime.in_use > container.capacity or container.cache.in_use > container.cache.quota):
        raise Refusal("native_binding")
    for volume, mount, path in ((container.runtime, snapshot.runtime, selection.runtime_path),
                                (container.cache, snapshot.cache, selection.cache_path)):
        _typed(mount, Mount)
        if (re.fullmatch(re.escape(container.device) + r"s[0-9]+", volume.device) is None
                or mount.volume_uuid != volume.uuid or mount.device != volume.device
                or mount.container_device != container.device or mount.physical_store != container.physical_store
                or mount.mountpoint != str(path) or mount.writable is not True
                or _number(mount.capacity) != container.capacity):
            raise Refusal("native_mount")


def _stable_file_identity(item: FileIdentity) -> FileIdentity:
    """Project comparison identity only; original observations retain all usage."""
    _typed(item, FileIdentity)
    _mode(item.mode)
    return replace(item, allocated=0, size=0 if stat.S_ISDIR(item.mode) else item.size)


def _stable_native_identity(snapshot: NativeSnapshot) -> NativeSnapshot:
    _typed(snapshot, NativeSnapshot)
    _typed(snapshot.container, Container)
    _typed(snapshot.container.runtime, Volume)
    _typed(snapshot.container.cache, Volume)
    return replace(snapshot, container=replace(snapshot.container, free=0,
                   runtime=replace(snapshot.container.runtime, in_use=0), cache=replace(snapshot.container.cache, in_use=0)))


def assert_same_running_binding(before: NativeStorageObservation, after: NativeStorageObservation) -> None:
    """Compare already validated observations across calls, retaining all caps."""
    _typed(before, NativeStorageObservation)
    _typed(after, NativeStorageObservation)
    _typed(before.after, tuple)
    _typed(after.before, tuple)
    if (before.owner_uid != after.owner_uid
            or tuple(map(_stable_file_identity, before.after)) != tuple(map(_stable_file_identity, after.before))
            or _stable_native_identity(before.native_after) != _stable_native_identity(after.native_before)):
        raise Refusal("storage_changed")


def _validate_paths(selection: NativeStorageSelection, observation: NativeStorageObservation, *, running: bool = False) -> None:
    _typed(observation.before, tuple)
    _typed(observation.after, tuple)
    for records in (observation.before, observation.after):
        if len(records) != len(_paths(selection)):
            raise Refusal("storage_identity")
        for item, path in zip(records, _paths(selection), strict=True):
            _typed(item, FileIdentity)
            for number in (item.device, item.inode, item.mode, item.uid, item.links, item.size, item.allocated):
                _number(number)
            _mode(item.mode)
            image = path == selection.image_path
            if (item.path != path or item.uid != observation.owner_uid
                    or stat.S_IMODE(item.mode) != (0o600 if image else 0o700)
                    or not (stat.S_ISREG(item.mode) if image else stat.S_ISDIR(item.mode))
                    or item.inode == 0 or item.device == 0
                    or (image and (item.links != 1 or item.size != selection.image_bytes
                                   or (item.device, item.inode) != (selection.image_device, selection.image_inode)))):
                raise Refusal("storage_identity")
        by_path = {item.path: item for item in records}
        host, runtime, cache = (by_path[path].device for path in
                                (selection.pilot_root, selection.runtime_path, selection.cache_path))
        if len({host, runtime, cache}) != 3:
            raise Refusal("storage_mount")
        for item in records:
            expected = (cache if item.path == selection.cache_path else runtime
                        if item.path == selection.runtime_path or selection.runtime_path in item.path.parents else host)
            if item.device != expected:
                raise Refusal("storage_mount")
    before = tuple(map(_stable_file_identity, observation.before)) if running else observation.before
    after = tuple(map(_stable_file_identity, observation.after)) if running else observation.after
    if before != after:
        raise Refusal("storage_identity")


def _validate_native_storage(selection: NativeStorageSelection, observation: NativeStorageObservation,
                             *, running: bool, check_usage: bool) -> StorageAdmission:
    try:
        _check_selection(selection)
        _typed(observation, NativeStorageObservation)
        _number(observation.owner_uid)
        _number(observation.free_bytes)
        _validate_paths(selection, observation, running=running)
        for snapshot in (observation.native_before, observation.native_after):
            _validate_snapshot(selection, snapshot, observation.owner_uid, check_usage=check_usage)
        before = _stable_native_identity(observation.native_before) if running else observation.native_before
        after = _stable_native_identity(observation.native_after) if running else observation.native_after
        if before != after:
            raise Refusal("native_changed")
        if check_usage and observation.free_bytes < REQUIRED_FREE_BYTES:
            raise Refusal("host_free_space")
    except Refusal as error:
        return StorageAdmission((str(error),))
    return StorageAdmission((), topology_verified=True)


def validate_native_storage(selection: NativeStorageSelection, observation: NativeStorageObservation,
                            operation: str) -> StorageAdmission:
    """Preserve strict stopped-state validation; no inspection can allocate."""
    if type(operation) is not str or operation != "inspect":
        return StorageAdmission(("unsupported_operation",))
    return _validate_native_storage(selection, observation, running=False, check_usage=True)


def validate_running_native_storage(selection: NativeStorageSelection, observation: NativeStorageObservation) -> StorageAdmission:
    return _validate_native_storage(selection, observation, running=True, check_usage=True)


def validate_running_native_storage_identity(selection: NativeStorageSelection, observation: NativeStorageObservation) -> StorageAdmission:
    """Check identities and fixed ceilings for exact recovery, ignoring usage pressure."""
    return _validate_native_storage(selection, observation, running=True, check_usage=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--operation", choices=("inspect",), default="inspect")
    args = parser.parse_args()
    report = StorageAdmission(("selection_unavailable",))
    try:
        from probe_openshell_runtime import private_file
        selection = parse_selection(private_file(args.selection))
        report = validate_native_storage(selection, collect_native_storage(selection), args.operation)
    except Refusal as error:
        report = StorageAdmission((str(error),))
    except (OSError, CommandRefusal):
        report = StorageAdmission(("selection_unavailable",))
    print(json.dumps({"schema_version": 1, **asdict(report),
                      "allocation_enabled": False, "runtime_qualification": "not_run"}, sort_keys=True))
    return 0 if report.topology_verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
