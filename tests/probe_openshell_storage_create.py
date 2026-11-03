"""Create one source-bound Linux worker under native storage caps; never boot it.

Selection hashes are comparison targets. Fresh native inventory, executable and
recipe identities are required for every invocation. No stored observation can
admit an operation. Legacy runtime allocation routes remain independently closed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import time
from xml.parsers.expat import ExpatError

import probe_openshell_storage as legacy
import probe_openshell_storage_inventory as inventory
import probe_openshell_storage_native as native
from probe_openshell_runtime import CommandResult, Refusal as CommandRefusal, _run_bounded_command, private_file
from probe_openshell_storage import Refusal


LIMA = Path("/opt/homebrew/bin/limactl")
QEMU = Path("/opt/homebrew/bin/qemu-img")
RECIPE = Path(__file__).resolve().parent / "fixtures/openshell_runtime/lima.yaml"
RECIPE_SHA256 = "c4db40652e23becb65df58a70c65a98ae8ad1c42260db576011beb70287bd750"
IMAGE_URL = "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/aarch64/images/Fedora-Cloud-Base-Generic-44-1.7.aarch64.qcow2"
IMAGE_DIGEST = "sha256:55c60a3b80d3616a08705afd0459e75fe9f03c54aba7a46e4002a41a72fa0d5b"
PROVISION = ("#!/bin/bash\nset -euo pipefail\n"
             "dnf -y install podman fuse-overlayfs passt shadow-utils shadow-utils-subid python3\n"
             "# OpenShell installation, private configuration and service activation are\n"
             "# separate reviewed preparation steps. No runtime starts from this recipe.\n")
LIMIT = 1024**2
DISK_BYTES = 20 * 1024**3
PREPARATION_SECONDS = 1800
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class CreateSelection:
    storage: native.NativeStorageSelection
    lima_sha256: str
    qemu_sha256: str
    source_recipe_sha256: str


@dataclass(frozen=True)
class FileEvidence:
    identity: native.FileIdentity
    modified_ns: int
    changed_ns: int
    sha256: str | None


@dataclass(frozen=True)
class PreparedWorkerObservation:
    name: str
    status: str
    worker_device: int
    worker_inode: int
    config_sha256: str
    source_recipe_sha256: str
    lima_sha256: str
    qemu_sha256: str
    disk: FileEvidence
    disk_format: str
    virtual_bytes: int
    inventory: inventory.NativeInventory
    vm_start_requested: bool = False
    start_enabled: bool = False


def selection_json(selection: CreateSelection) -> bytes:
    """Encode comparison data; the decoder remains the closed authority."""
    if type(selection) is not CreateSelection:
        raise Refusal("invalid_selection")
    native._check_selection(selection.storage)
    value = {field.name: getattr(selection.storage, field.name) for field in fields(selection.storage)}
    for name in ("pilot_root", "run_root", "image_path"):
        value[name] = str(value[name])
    value.update(schema_version=1, lima_sha256=selection.lima_sha256,
                 qemu_sha256=selection.qemu_sha256, source_recipe_sha256=selection.source_recipe_sha256)
    try:
        return json.dumps(value).encode()
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise Refusal("invalid_selection") from None


def parse_selection(raw: bytes) -> CreateSelection:
    if type(raw) is not bytes or len(raw) > 65536:
        raise Refusal("invalid_selection")
    try:
        value = native._object(json.loads(raw, object_pairs_hook=native._unique_json))
        digests = []
        for name in ("lima_sha256", "qemu_sha256", "source_recipe_sha256"):
            digest = value.pop(name, None)
            if type(digest) is not str or _DIGEST.fullmatch(digest) is None:
                raise Refusal("invalid_selection")
            digests.append(digest)
        storage = native.parse_selection(json.dumps(value).encode())
        if storage.profile != "pilot" or digests[2] != RECIPE_SHA256:
            raise Refusal("invalid_selection")
        return CreateSelection(storage, *digests)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise Refusal("invalid_selection") from None


def _remaining(deadline: float, maximum: float = PREPARATION_SECONDS) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Refusal("preparation_timeout")
    return min(maximum, remaining)


def _file(path: Path, limit: int, *, content: bool = True,
          mode: int | None = None, executable: bool = False, deadline: float | None = None) -> tuple[FileEvidence, bytes]:
    """Own one no-follow descriptor and bind both path observations to it."""
    try:
        before = path.lstat()
        if path.resolve(strict=True) != path:
            raise Refusal("file_identity")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            opened = inventory._stat(fd)
            actual = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_mode) != (actual.st_dev, actual.st_ino, actual.st_mode)
                    or not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
                    or actual.st_uid not in ({0, os.getuid()} if executable else {os.getuid()})
                    or actual.st_size > limit or stat.S_IMODE(actual.st_mode) & 0o022
                    or (mode is not None and stat.S_IMODE(actual.st_mode) != mode)
                    or (executable and not stat.S_IMODE(actual.st_mode) & 0o111)):
                raise Refusal("file_identity")
            digest = hashlib.sha256()
            data = bytearray()
            if content:
                total = 0
                while True:
                    if deadline is not None:
                        _remaining(deadline)
                    chunk = os.read(fd, min(65536, limit + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit:
                        raise Refusal("file_identity")
                    if not executable:
                        data.extend(chunk)
                    digest.update(chunk)
            after = os.fstat(fd)
            current = path.lstat()
            attrs = ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(actual, key) != getattr(item, key) for item in (after, current) for key in attrs):
                raise Refusal("file_identity")
            identity = inventory._identity(path, opened)
            return FileEvidence(identity, actual.st_mtime_ns, actual.st_ctime_ns,
                                digest.hexdigest() if content else None), bytes(data)
        finally:
            os.close(fd)
    except (OSError, RuntimeError, UnicodeError):
        raise Refusal("file_unavailable") from None


def _sources(selection: CreateSelection, deadline: float) -> tuple[FileEvidence, ...]:
    try:
        lima = LIMA.resolve(strict=True)
        qemu = QEMU.resolve(strict=True)
        evidence = [_file(path, 256 * LIMIT, executable=True, deadline=deadline)[0] for path in (lima, qemu)]
        source, source_bytes = _file(RECIPE, LIMIT, deadline=deadline)
        parent = selection.storage.run_root / "input"
        info = parent.lstat()
        if (parent.resolve(strict=True) != parent or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
            raise Refusal("recipe_identity")
        copied, copied_bytes = _file(parent / "lima.yaml", LIMIT, mode=0o600, deadline=deadline)
        if (evidence[0].sha256 != selection.lima_sha256 or evidence[1].sha256 != selection.qemu_sha256
                or source.sha256 != RECIPE_SHA256 or copied.sha256 != RECIPE_SHA256
                or source_bytes != copied_bytes):
            raise Refusal("source_identity")
        return (*evidence, source, copied)
    except (OSError, RuntimeError):
        raise Refusal("source_unavailable") from None


def _environment(selection: CreateSelection) -> dict[str, str]:
    storage = selection.storage
    return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C", "TERM": "dumb", "NO_COLOR": "1",
            "HOME": str(storage.home_path), "LIMA_HOME": str(storage.runtime_path),
            "XDG_CONFIG_HOME": str(storage.home_path / "config"),
            "XDG_DATA_HOME": str(storage.home_path / "data"), "XDG_STATE_HOME": str(storage.home_path / "state"),
            "XDG_CACHE_HOME": str(storage.cache_path / "_xdg"), "TMPDIR": str(storage.cache_path / "_tmp")}


def _command(selection: CreateSelection, argv: list[str], deadline: float, phase: str,
             maximum: float = 10) -> bytes:
    try:
        result = _run_bounded_command(argv, cwd=selection.storage.run_root, env=_environment(selection),
                                      timeout=_remaining(deadline, maximum), limit=LIMIT)
    except CommandRefusal as error:
        reason = str(error)
        raise Refusal(phase + "_" + (reason if reason in {"timeout", "output_limit"} else "unavailable")) from None
    if result.returncode != 0:
        raise Refusal(phase + "_failed")
    if len(result.stdout) + len(result.stderr) > LIMIT:
        raise Refusal(phase + "_output_limit")
    _remaining(deadline)
    return result.stdout


def _inventory(selection: CreateSelection, root_fd: int, deadline: float) -> inventory.NativeInventory:
    _remaining(deadline)
    result = inventory._collect_locked(selection.storage, root_fd, deadline=deadline)
    report = inventory.validate_native_inventory(selection.storage, result)
    if not report.inventory_verified:
        raise Refusal(report.blockers[0])
    _remaining(deadline)
    for name in ("default.yaml", "override.yaml", "base.yaml"):
        if os.path.lexists(selection.storage.runtime_path / "_config" / name):
            raise Refusal("global_configuration")
    return result


def _json(raw: bytes) -> dict[str, object]:
    try:
        return native._object(json.loads(raw, object_pairs_hook=native._unique_json))
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal("worker_schema") from None


def _worker_config(value: dict[str, object], selection: CreateSelection) -> None:
    storage = selection.storage
    if (value.get("name") != "q" or value.get("dir") != str(storage.runtime_path / "q")
            or value.get("status") != "Stopped" or value.get("vmType") != "vz" or value.get("arch") != "aarch64"
            or value.get("limaVersion") != "2.2.1" or value.get("errors") not in (None, [])
            or value.get("additionalDisks") not in (None, []) or value.get("autoStartedIdentifier") not in (None, "")):
        raise Refusal("worker_identity")
    for key, expected in (("disk", DISK_BYTES), ("cpus", 4), ("memory", 8 * 1024**3),
                          ("hostAgentPID", 0), ("driverPID", 0)):
        actual = value.get(key, 0)
        if type(actual) is not int or actual != expected:
            raise Refusal("worker_identity")
    config = native._object(value.get("config"))
    for key, expected in (("os", "Linux"), ("vmType", "vz"), ("arch", "aarch64"),
                          ("cpus", 4), ("memory", "8GiB"), ("disk", "20GiB"), ("mountType", "virtiofs")):
        if type(config.get(key)) is not type(expected) or config.get(key) != expected:
            raise Refusal("worker_configuration")
    for key in ("mounts", "additionalDisks", "networks", "probes", "copyToHost"):
        if config.get(key) not in (None, []):
            raise Refusal("worker_configuration")
    vz = native._object(native._object(config.get("vmOpts")).get("vz"))
    if vz.get("diskImageFormat") != "raw":
        raise Refusal("worker_configuration")
    rosetta = native._object(vz.get("rosetta", {}))
    if any(rosetta.get(key) is not None and rosetta.get(key) is not False for key in ("enabled", "binfmt")):
        raise Refusal("worker_configuration")
    for group, keys in (("containerd", ("system", "user")),
                        ("ssh", ("loadDotSSHPubKeys", "forwardAgent", "forwardX11"))):
        values = native._object(config.get(group))
        if any(values.get(key) is not False for key in keys):
            raise Refusal("worker_configuration")
    if config.get("propagateProxyEnv") is not False:
        raise Refusal("worker_configuration")
    images = native._list(config.get("images"))
    if len(images) != 1 or any(native._object(images[0]).get(key) != value for key, value in
                             (("location", IMAGE_URL), ("arch", "aarch64"), ("digest", IMAGE_DIGEST))):
        raise Refusal("worker_configuration")
    provision = native._list(config.get("provision"))
    if len(provision) != 1 or native._object(provision[0]).get("mode") != "system" or native._object(provision[0]).get("script") != PROVISION:
        raise Refusal("worker_configuration")
    forwards = native._list(config.get("portForwards"))
    if (len(forwards) != 1 or native._object(forwards[0]).get("ignore") is not True
            or native._object(forwards[0]).get("guestIP") != "0.0.0.0" or native._object(forwards[0]).get("proto") != "any"):
        raise Refusal("worker_configuration")


def _disk_format(apple_raw: bytes, qemu_raw: bytes, disk: FileEvidence) -> None:
    try:
        apple = native._object(plistlib.loads(apple_raw, dict_type=native._UniqueDict))
    except (ValueError, TypeError, OverflowError, RecursionError, ExpatError):
        raise Refusal("disk_schema") from None
    encrypted = native._object(apple.get("Encryption Info")).get("Is Encrypted")
    capacity = native._object(apple.get("Size Info")).get("Total Bytes")
    if (apple.get("Image Format") != "RAW" or type(encrypted) is not int or encrypted != 0
            or type(capacity) is not int or capacity != DISK_BYTES or disk.identity.size != DISK_BYTES):
        raise Refusal("disk_format")
    qemu = _json(qemu_raw)
    keys = {"children", "virtual-size", "filename", "format", "actual-size", "dirty-flag"}
    if set(qemu) != keys:
        raise Refusal("disk_schema")
    children = native._list(qemu.get("children"))
    if len(children) != 1 or set(native._object(children[0])) != {"name", "info"} or native._object(children[0]).get("name") != "file":
        raise Refusal("disk_schema")
    child = native._object(native._object(children[0]).get("info"))
    if (set(child) != keys | {"format-specific"} or child.get("children") != []
            or child.get("format-specific") != {"type": "file", "data": {}}):
        raise Refusal("disk_schema")
    for value, format_name in ((qemu, "raw"), (child, "file")):
        if (value.get("format") != format_name or value.get("filename") != str(disk.identity.path)
                or type(value.get("virtual-size")) is not int or value.get("virtual-size") != DISK_BYTES
                or type(value.get("actual-size")) is not int or value.get("actual-size") != disk.identity.allocated
                or value.get("dirty-flag") is not False):
            raise Refusal("disk_format")


def create_worker(selection: CreateSelection) -> PreparedWorkerObservation:
    """Allocate only a stopped worker; retain every partial result on failure."""
    deadline = time.monotonic() + PREPARATION_SECONDS
    selection = parse_selection(selection_json(selection))
    fd = legacy._open_root(selection.storage.pilot_root)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("storage_busy") from None
        before = _inventory(selection, fd, deadline)
        if before.workers:
            raise Refusal("worker_already_retained")
        sources = _sources(selection, deadline)
        lima, qemu = (str(item.identity.path) for item in sources[:2])
        if _command(selection, [lima, "--version"], deadline, "lima_version").strip() != b"limactl version 2.2.1":
            raise Refusal("lima_version")
        qemu_version = _command(selection, [qemu, "--version"], deadline, "qemu_version").splitlines()
        if not qemu_version or qemu_version[0] != b"qemu-img version 11.1.2":
            raise Refusal("qemu_version")
        if _inventory(selection, fd, deadline).workers:
            raise Refusal("worker_already_retained")
        if _sources(selection, deadline) != sources:
            raise Refusal("source_changed")
        # No user arguments or command descriptors reach this sole effect.
        _command(selection, [lima, "create", "--tty=false", "--name=q",
                             str(selection.storage.run_root / "input/lima.yaml")],
                 deadline, "create", PREPARATION_SECONDS)
        after = _inventory(selection, fd, deadline)
        if (len(after.workers) != 1 or after.workers[0].run_id != selection.storage.run_root.name
                or after.workers[0].name != "q" or not after.workers[0].has_config
                or len(after.workers[0].disks) != 1 or after.workers[0].disks[0].path.name != "disk"):
            raise Refusal("worker_identity")
        worker = after.workers[0]
        config, _ = _file(selection.storage.runtime_path / "q/lima.yaml", LIMIT)
        disk, _ = _file(selection.storage.runtime_path / "q/disk", DISK_BYTES, content=False)
        if disk.identity != worker.disks[0] or config.identity.device != worker.device:
            raise Refusal("worker_identity")
        _worker_config(_json(_command(selection, [lima, "list", "q", "--json"], deadline, "worker")), selection)
        apple = _command(selection, ["/usr/sbin/diskutil", "image", "info", "--plist", str(disk.identity.path)], deadline, "disk")
        qemu_info = _command(selection, [qemu, "info", "--output=json", str(disk.identity.path)], deadline, "disk")
        _disk_format(apple, qemu_info, disk)
        if (_file(config.identity.path, LIMIT)[0] != config
                or _file(disk.identity.path, DISK_BYTES, content=False)[0] != disk or _sources(selection, deadline) != sources):
            raise Refusal("worker_changed")
        final = _inventory(selection, fd, deadline)
        if final.workers != after.workers:
            raise Refusal("worker_changed")
        if _sources(selection, deadline) != sources:
            raise Refusal("source_changed")
        if config.sha256 is None:
            raise Refusal("worker_configuration")
        _remaining(deadline)
        return PreparedWorkerObservation("q", "Stopped", worker.device, worker.inode, config.sha256,
                                         selection.source_recipe_sha256, selection.lima_sha256, selection.qemu_sha256,
                                         disk, "RAW", DISK_BYTES, final)
    except (OSError, RuntimeError, UnicodeError):
        raise Refusal("preparation_unavailable") from None
    finally:
        os.close(fd)


def start_worker(selection: CreateSelection) -> None:
    """No selection or prior observation enables VM boot in this increment."""
    raise Refusal("start_unqualified")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--operation", choices=("create",), default="create")
    args = parser.parse_args()
    try:
        observed = create_worker(parse_selection(private_file(args.selection)))
        report = {"schema_version": 1, "status": "prepared", "worker_status": observed.status,
                  "disk_format": observed.disk_format, "virtual_bytes": observed.virtual_bytes,
                  "vm_start_requested": False, "start_enabled": False}
    except Refusal as error:
        report = {"schema_version": 1, "status": "refused", "blockers": [str(error)],
                  "vm_start_requested": False, "start_enabled": False}
    except (OSError, CommandRefusal):
        report = {"schema_version": 1, "status": "refused", "blockers": ["selection_unavailable"],
                  "vm_start_requested": False, "start_enabled": False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "prepared" else 1


if __name__ == "__main__":
    raise SystemExit(main())
