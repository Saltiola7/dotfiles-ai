"""Boot the selected worker for one fixed read-only guest inventory, then stop.

This is build-preflight evidence only. It cannot install packages, download
artifacts, mount build storage, compile, or enable an agent session.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import stat

import probe_openshell_storage_boot as boot
import probe_openshell_storage_create as create
import probe_openshell_storage_native as native
from probe_openshell_storage import Refusal


REPORT_LIMIT = 64 * 1024
TOOLS = (
    "/usr/bin/python3", "/usr/bin/rpm", "/usr/bin/dnf", "/usr/bin/git", "/usr/bin/gcc",
    "/usr/bin/musl-gcc", "/usr/bin/ar", "/usr/sbin/mkfs.ext4", "/usr/sbin/losetup",
    "/usr/bin/losetup", "/usr/bin/systemd-run", "/usr/bin/setpriv", "/usr/bin/findmnt",
)
PACKAGES = (
    "python3", "podman", "gcc", "musl-gcc", "musl-devel", "musl-libc-static", "git",
    "e2fsprogs", "util-linux", "systemd",
)

# Fixed source, not a selected script path or a user-supplied command. Imports and
# queries are standard-library/native reads in the already verified guest.
GUEST_SCRIPT = r'''
import json, os, selectors, shlex, signal, stat, subprocess, time

TOOLS = __TOOLS__
PACKAGES = __PACKAGES__
DEADLINE = time.monotonic() + 20

def remaining(maximum=2):
    value = DEADLINE - time.monotonic()
    if value <= 0:
        raise RuntimeError("guest_deadline")
    return min(value, maximum)

def read_file(path, limit):
    remaining()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("guest_file_type")
        data = bytearray()
        while len(data) <= limit:
            remaining()
            chunk = os.read(fd, min(4096, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > limit:
            raise RuntimeError("guest_file_limit")
        return bytes(data).decode("utf-8")
    finally:
        os.close(fd)

def query(package):
    args = ["/usr/bin/rpm", "-q", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\n", package]
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "HOME": "/nonexistent"}
    end = time.monotonic() + remaining()
    out, err = bytearray(), bytearray()
    process = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, out)
            selector.register(process.stderr, selectors.EVENT_READ, err)
            while selector.get_map():
                wait = min(end - time.monotonic(), remaining())
                if wait <= 0:
                    raise RuntimeError("guest_package_timeout")
                for key, _ in selector.select(wait):
                    chunk = os.read(key.fd, min(4096, 8193 - len(out) - len(err)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        key.data.extend(chunk)
                    if len(out) + len(err) > 8192:
                        raise RuntimeError("guest_package_output")
            process.wait(timeout=max(0.001, min(end - time.monotonic(), remaining())))
    finally:
        try:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=1)
        finally:
            process.stdout.close()
            process.stderr.close()
    if process.returncode == 1 and not err and out == ("package " + package + " is not installed\n").encode():
        return {"name": package, "installed": False, "version": None, "arch": None}
    if process.returncode != 0 or err:
        raise RuntimeError("guest_package_query")
    fields = out.decode("utf-8").rstrip("\n").split("\t")
    if len(fields) != 3 or fields[0] != package or any("\n" in value for value in fields):
        raise RuntimeError("guest_package_schema")
    return {"name": package, "installed": True, "version": fields[1], "arch": fields[2]}

def collect():
    release = {}
    for line in read_file("/usr/lib/os-release", 65536).splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, raw = line.partition("=")
        if not separator or key in release:
            raise RuntimeError("guest_release_schema")
        values = shlex.split(raw)
        if len(values) != 1:
            raise RuntimeError("guest_release_schema")
        release[key] = values[0]
    mounts = []
    for line in read_file("/proc/self/mountinfo", 262144).splitlines():
        left, separator, right = line.partition(" - ")
        fields = left.split()
        after = right.split()
        if not separator or len(fields) < 6 or len(after) < 3:
            raise RuntimeError("guest_mount_schema")
        if fields[4] in ("/", "/var", "/var/lib"):
            major, minor = fields[2].split(":")
            mounts.append((fields[4], os.makedev(int(major), int(minor)), after[0]))
    if sum(item[0] == "/" for item in mounts) != 1:
        raise RuntimeError("guest_mount_schema")
    filesystems = []
    for path in ("/", "/var/lib"):
        remaining()
        info = os.lstat(path)
        if not stat.S_ISDIR(info.st_mode) or os.path.realpath(path) != path:
            raise RuntimeError("guest_path_identity")
        candidates = [item for item in mounts if item[0] == "/" or path == item[0] or path.startswith(item[0] + "/")]
        longest = max(len(item[0]) for item in candidates)
        candidates = [item for item in candidates if len(item[0]) == longest]
        if len(candidates) != 1:
            raise RuntimeError("guest_mount_schema")
        mount_point, mount_device, filesystem_type = candidates[0]
        if mount_device != info.st_dev:
            raise RuntimeError("guest_mount_identity " + json.dumps({
                "path": path, "device": info.st_dev, "mount_point": mount_point,
                "mount_device": mount_device, "filesystem_type": filesystem_type}))
        space = os.statvfs(path)
        filesystems.append({"path": path, "device": info.st_dev, "inode": info.st_ino,
                            "mode": info.st_mode, "filesystem_type": filesystem_type,
                            "mount_point": mount_point, "mount_device": mount_device,
                            "bytes_total": space.f_blocks * space.f_frsize,
                            "bytes_free": space.f_bfree * space.f_frsize,
                            "bytes_available": space.f_bavail * space.f_frsize,
                            "block_size": space.f_frsize})
    uname = os.uname()
    result = {"schema_version": 2, "os": uname.sysname, "arch": uname.machine,
              "kernel": uname.release, "uid": os.getuid(),
              "release": {"id": release.get("ID"), "version_id": release.get("VERSION_ID")},
              "filesystems": filesystems,
              "tools": {path: os.path.isfile(path) and os.access(path, os.X_OK) for path in TOOLS},
              "packages": [query(package) for package in PACKAGES]}
    remaining()
    return result

if __name__ == "__main__":
    print(json.dumps(collect(), sort_keys=True))
'''.replace("__TOOLS__", repr(TOOLS)).replace("__PACKAGES__", repr(PACKAGES))
SCRIPT_SHA256 = hashlib.sha256(GUEST_SCRIPT.encode()).hexdigest()


@dataclass(frozen=True)
class GuestFilesystem:
    path: str
    device: int
    inode: int
    mode: int
    filesystem_type: str
    mount_point: str
    mount_device: int
    bytes_total: int
    bytes_free: int
    bytes_available: int
    block_size: int


@dataclass(frozen=True)
class GuestPackage:
    name: str
    installed: bool
    version: str | None
    arch: str | None


@dataclass(frozen=True)
class GuestInventory:
    kernel: str
    uid: int
    filesystems: tuple[GuestFilesystem, ...]
    available_tools: tuple[str, ...]
    packages: tuple[GuestPackage, ...]
    build_enabled: bool = False

    @property
    def free_bytes(self) -> int:
        return min(item.bytes_available for item in self.filesystems)

    @property
    def missing_packages(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.packages if not item.installed)


@dataclass(frozen=True)
class GuestInventoryObservation:
    lifecycle: boot.BootObservation
    guest: GuestInventory
    script_sha256: str


def parse_inventory(raw: bytes) -> GuestInventory:
    """Validate a bounded closed report; never treat availability as admission."""
    try:
        if type(raw) is not bytes or len(raw) > REPORT_LIMIT:
            raise Refusal("guest_inventory_schema")
        value = native._object(json.loads(raw, object_pairs_hook=native._unique_json))
        keys = {"schema_version", "os", "arch", "kernel", "uid", "release", "filesystems", "tools", "packages"}
        if (set(value) != keys or type(value["schema_version"]) is not int or value["schema_version"] != 2
                or value["os"] != "Linux" or value["arch"] != "aarch64"
                or value["release"] != {"id": "fedora", "version_id": "44"}
                or type(value["uid"]) is not int or not 0 < value["uid"] < 2**31
                or type(value["kernel"]) is not str or re.fullmatch(r"[A-Za-z0-9._+\-]{1,128}", value["kernel"]) is None):
            raise Refusal("guest_inventory_schema")
        filesystems = []
        data = native._list(value["filesystems"])
        if len(data) != 2:
            raise Refusal("guest_inventory_schema")
        for path, item in zip(("/", "/var/lib"), data, strict=True):
            item = native._object(item)
            if set(item) != set(GuestFilesystem.__dataclass_fields__) or item["path"] != path:
                raise Refusal("guest_inventory_schema")
            for key in ("device", "inode", "mode", "mount_device", "bytes_total", "bytes_free", "bytes_available", "block_size"):
                native._number(item[key])
            native._mode(item["mode"])
            if (not item["device"] or not item["inode"] or not stat.S_ISDIR(item["mode"])
                    or item["mount_device"] != item["device"]
                    or item["mount_point"] not in (("/",) if path == "/" else ("/", "/var", "/var/lib"))
                    or item["filesystem_type"] not in {"btrfs", "ext4", "xfs"}
                    or not 0 < item["bytes_total"] <= create.DISK_BYTES
                    or not 0 <= item["bytes_available"] <= item["bytes_free"] <= item["bytes_total"]
                    or not 512 <= item["block_size"] <= 1024**2
                    or item["block_size"] & (item["block_size"] - 1)):
                raise Refusal("guest_inventory_schema")
            filesystems.append(GuestFilesystem(**item))
        tools = native._object(value["tools"])
        if set(tools) != set(TOOLS) or any(type(flag) is not bool for flag in tools.values()):
            raise Refusal("guest_inventory_schema")
        data = native._list(value["packages"])
        if len(data) != len(PACKAGES):
            raise Refusal("guest_inventory_schema")
        packages = []
        for name, item in zip(PACKAGES, data, strict=True):
            item = native._object(item)
            if (set(item) != set(GuestPackage.__dataclass_fields__) or item["name"] != name
                    or type(item["installed"]) is not bool):
                raise Refusal("guest_inventory_schema")
            if item["installed"]:
                if (type(item["version"]) is not str or re.fullmatch(r"[A-Za-z0-9._+~^\-]{1,128}", item["version"]) is None
                        or item["arch"] not in {"aarch64", "noarch"}):
                    raise Refusal("guest_inventory_schema")
            elif item["version"] is not None or item["arch"] is not None:
                raise Refusal("guest_inventory_schema")
            packages.append(GuestPackage(**item))
        return GuestInventory(value["kernel"], value["uid"], tuple(filesystems),
                              tuple(path for path in TOOLS if tools[path]), tuple(packages))
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise Refusal("guest_inventory_schema") from None


def _inspect_guest(selection: create.CreateSelection, anchor: boot._Anchors, deadline: float) -> GuestInventory:
    argv = [str(anchor.sources[0].identity.path), "shell", "--tty=false", "--start=false",
            "--workdir", "/", "q", "--", "/usr/bin/python3", "-I", "-c", GUEST_SCRIPT]
    return parse_inventory(create._command(selection, argv, deadline, "guest_inventory", 30))


def qualify_guest_inventory(selection: create.CreateSelection) -> GuestInventoryObservation:
    """Run the one compiled read-only inventory inside verified worker lifetime."""
    lifecycle, guest = boot._qualify_with_inspection(selection, _inspect_guest)
    if type(guest) is not GuestInventory:
        raise boot.BootRefusal("guest_inventory_unavailable", start_requested=True,
                               stop_requested=True, stopped_verified=lifecycle.stopped_verified)
    return GuestInventoryObservation(lifecycle, guest, SCRIPT_SHA256)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    args = parser.parse_args()
    try:
        selected = create.parse_selection(create.private_file(args.selection))
        observed = qualify_guest_inventory(selected)
        report = {"schema_version": 1, "status": "guest_inventory_stopped",
                  "guest": asdict(observed.guest), "script_sha256": observed.script_sha256,
                  "vm_start_requested": True, "stop_requested": True, "stopped_verified": True,
                  "shutdown_uncertain": False, "build_enabled": False, "session_enabled": False}
    except boot.BootRefusal as error:
        report = {"schema_version": 1, "status": "refused", "blockers": [str(error)],
                  "vm_start_requested": error.start_requested, "stop_requested": error.stop_requested,
                  "stopped_verified": error.stopped_verified, "shutdown_uncertain": error.shutdown_uncertain,
                  "build_enabled": False, "session_enabled": False}
    except (Refusal, OSError, create.CommandRefusal):
        report = {"schema_version": 1, "status": "refused", "blockers": ["selection_unavailable"],
                  "vm_start_requested": False, "stop_requested": False, "stopped_verified": False,
                  "shutdown_uncertain": False, "build_enabled": False, "session_enabled": False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "guest_inventory_stopped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
