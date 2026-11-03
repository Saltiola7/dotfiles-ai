"""Qualify one existing bounded worker by booting and stopping it exactly once.

No observation is an admission receipt. This runner checks storage immediately
before and after the bounded start; native hard caps apply throughout. It is not
continuous monitoring, a general launcher, or authority to start any workload.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time

import probe_openshell_storage_create as create
import probe_openshell_storage_inventory as inventory
import probe_openshell_storage_native as native
from probe_openshell_storage import Refusal


QUALIFICATION_SECONDS = 900
SHUTDOWN_RESERVE = 300
FINAL_VERIFICATION_RESERVE = 60
STOP_SECONDS = 190


class BootRefusal(Refusal):
    """Path-free failure facts, including whether shutdown remains uncertain."""

    def __init__(self, reason: str, *, start_requested: bool = False,
                 stop_requested: bool = False, stopped_verified: bool = False):
        super().__init__(reason)
        self.start_requested = start_requested
        self.stop_requested = stop_requested
        self.stopped_verified = stopped_verified
        self.shutdown_uncertain = start_requested and not stopped_verified


@dataclass(frozen=True)
class BootObservation:
    worker_status: str
    running_observed: bool
    stopped_verified: bool
    host_agent_pid: int
    driver_pid: int
    running_inventory: inventory.NativeInventory
    stopped_inventory: inventory.NativeInventory
    session_enabled: bool = False


@dataclass(frozen=True)
class _Anchors:
    inventory: inventory.NativeInventory
    worker: inventory.RetainedWorker
    config: create.FileEvidence
    disk: create.FileEvidence
    sources: tuple[create.FileEvidence, ...]


@dataclass(frozen=True)
class _Process:
    pid: int
    uid: int
    started: str
    executable: str
    arguments: str


@dataclass(frozen=True)
class _Processes:
    pids: tuple[int, int]
    files: tuple[create.FileEvidence | None, ...]
    processes: tuple[_Process, ...]


def _stable_file(item: native.FileIdentity) -> tuple[object, ...]:
    return (item.path, item.device, item.inode, item.mode, item.uid, item.links, item.size)


def _settings(selection: create.CreateSelection) -> None:
    for name in ("default.yaml", "override.yaml", "base.yaml"):
        if os.path.lexists(selection.storage.runtime_path / "_config" / name):
            raise Refusal("global_configuration")
    if os.path.lexists(selection.storage.home_path / "Library/LaunchAgents/io.lima-vm.autostart.q.plist"):
        raise Refusal("autostart_configuration")


def _collect(selection: create.CreateSelection, fd: int, deadline: float, *, identity_only: bool = False) -> inventory.NativeInventory:
    create._remaining(deadline)
    observed = inventory.collect_running_inventory_locked(selection.storage, fd, deadline=deadline)
    validator = inventory.validate_running_inventory_identity if identity_only else inventory.validate_running_inventory
    report = validator(selection.storage, observed)
    if not report.inventory_verified:
        raise Refusal(report.blockers[0])
    create._remaining(deadline)
    return observed


def _worker(selection: create.CreateSelection, observed: inventory.NativeInventory) -> inventory.RetainedWorker:
    if (len(observed.workers) != 1 or observed.workers[0].name != "q"
            or observed.workers[0].run_id != selection.storage.run_root.name
            or not observed.workers[0].has_config or len(observed.workers[0].disks) != 1
            or observed.workers[0].disks[0].path != selection.storage.runtime_path / "q/disk"):
        raise Refusal("worker_identity")
    return observed.workers[0]


def _live_disk(path: Path, deadline: float) -> create.FileEvidence:
    """Bind a live disk without demanding unchanged write timestamps or allocation."""
    create._remaining(deadline)
    try:
        before = path.lstat()
        if path.resolve(strict=True) != path:
            raise Refusal("disk_identity")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            opened = inventory._stat(fd)
            actual = os.fstat(fd)
            after = os.fstat(fd)
            current = path.lstat()
            stable = ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink", "st_size")
            if (any(getattr(actual, key) != getattr(item, key)
                    for item in (before, after, current) for key in stable)
                    or not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
                    or actual.st_uid != os.getuid() or stat.S_IMODE(actual.st_mode) & 0o022
                    or actual.st_size != create.DISK_BYTES):
                raise Refusal("disk_identity")
            identity = inventory._identity(path, opened)
            create._remaining(deadline)
            return create.FileEvidence(identity, after.st_mtime_ns, after.st_ctime_ns, None)
        finally:
            os.close(fd)
    except (OSError, RuntimeError, UnicodeError):
        raise Refusal("disk_unavailable") from None


def _files(selection: create.CreateSelection, observed: inventory.NativeInventory,
           deadline: float) -> tuple[create.FileEvidence, create.FileEvidence]:
    worker = _worker(selection, observed)
    config, _ = create._file(selection.storage.runtime_path / "q/lima.yaml", create.LIMIT, deadline=deadline)
    disk = _live_disk(selection.storage.runtime_path / "q/disk", deadline)
    if (_stable_file(disk.identity) != _stable_file(worker.disks[0])
            or config.identity.device != worker.device or disk.identity.size != create.DISK_BYTES):
        raise Refusal("worker_identity")
    return config, disk


def _guard(selection: create.CreateSelection, fd: int, anchor: _Anchors, deadline: float,
           *, identity_only: bool = False) -> inventory.NativeInventory:
    observed = _collect(selection, fd, deadline, identity_only=identity_only)
    native.assert_same_running_binding(anchor.inventory.native_after, observed.native_before)
    worker = _worker(selection, observed)
    if (worker.device, worker.inode) != (anchor.worker.device, anchor.worker.inode):
        raise Refusal("worker_changed")
    config, disk = _files(selection, observed, deadline)
    if config != anchor.config or _stable_file(disk.identity) != _stable_file(anchor.disk.identity):
        raise Refusal("worker_changed")
    if create._sources(selection, deadline) != anchor.sources:
        raise Refusal("source_changed")
    _settings(selection)
    return observed


def _status(selection: create.CreateSelection, anchor: _Anchors, deadline: float,
            expected: str | None = None) -> dict[str, object]:
    lima = str(anchor.sources[0].identity.path)
    value = create._json(create._command(selection, [lima, "list", "q", "--json"], deadline, "worker"))
    state = value.get("status")
    pids = tuple(value.get(key, 0) for key in ("hostAgentPID", "driverPID"))
    if (state not in {"Stopped", "Running", "Broken"} or (expected is not None and state != expected)
            or any(type(pid) is not int or pid < 0 or pid > 2**31 - 1 for pid in pids)
            or (state == "Stopped" and pids != (0, 0))
            or (state == "Running" and (not all(pids) or pids[0] != pids[1]))):
        raise Refusal("worker_status")
    # Reuse the full reviewed configuration validator without changing its strict
    # stopped-worker interface. Native PID/status checks remain separate above.
    normalized = value | {"status": "Stopped", "hostAgentPID": 0, "driverPID": 0}
    if expected is None:
        normalized["errors"] = []  # Runtime errors cannot prevent identity-safe shutdown.
    create._worker_config(normalized, selection)
    return value


def _format(selection: create.CreateSelection, anchor: _Anchors, deadline: float) -> None:
    disk, _ = create._file(anchor.disk.identity.path, create.DISK_BYTES, content=False, deadline=deadline)
    apple = create._command(selection, ["/usr/sbin/diskutil", "image", "info", "--plist", str(disk.identity.path)], deadline, "disk")
    qemu = create._command(selection, [str(anchor.sources[1].identity.path), "info", "--output=json", str(disk.identity.path)], deadline, "disk")
    create._disk_format(apple, qemu, disk)
    if create._file(disk.identity.path, create.DISK_BYTES, content=False, deadline=deadline)[0] != disk:
        raise Refusal("disk_changed")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        raise Refusal("process_unavailable") from None
    return True


def _process(selection: create.CreateSelection, anchor: _Anchors, pid: int,
             config: dict[str, object], deadline: float) -> _Process:
    def read(columns: str) -> str:
        raw = create._command(selection, ["/bin/ps", "-ww", "-p", str(pid), "-o", columns], deadline, "process")
        try:
            result = raw.decode("utf-8").strip()
        except UnicodeError:
            raise Refusal("process_schema") from None
        if not result or "\n" in result or "\x00" in result:
            raise Refusal("process_schema")
        return result

    stamp = read("pid=,uid=,lstart=")
    parts = stamp.split()
    if len(parts) != 7 or parts[:2] != [str(pid), str(os.getuid())]:
        raise Refusal("process_identity")
    started = " ".join(parts[2:])
    try:
        datetime.strptime(started, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        raise Refusal("process_schema") from None
    executable = read("comm=")
    arguments = read("args=")
    lima = anchor.sources[0].identity.path
    base = [str(lima), "hostagent", "--pidfile", str(selection.storage.runtime_path / "q/ha.pid"),
            "--socket", str(selection.storage.runtime_path / "q/ha.sock")]
    video = config.get("video", {})
    if type(video) is not dict:
        raise Refusal("worker_configuration")
    if video.get("display") in {"vz", "default"}:
        base.append("--run-gui")
    guest = lima.parent.parent / "share/lima/lima-guestagent.Linux-aarch64"
    expected = {" ".join([*base, "--guestagent", str(guest) + suffix, "q"]) for suffix in ("", ".gz")}
    if executable != str(lima) or arguments not in expected or read("pid=,uid=,lstart=") != stamp:
        raise Refusal("process_identity")
    return _Process(pid, os.getuid(), started, executable, arguments)


def _processes(selection: create.CreateSelection, anchor: _Anchors, status: dict[str, object],
               deadline: float) -> _Processes:
    pids = tuple(status.get(key, 0) for key in ("hostAgentPID", "driverPID"))
    files = []
    for name, pid in zip(("ha.pid", "vz.pid"), pids, strict=True):
        path = selection.storage.runtime_path / "q" / name
        if not pid:
            if os.path.lexists(path):
                raise Refusal("process_identity")
            files.append(None)
            continue
        evidence, raw = create._file(path, 32, deadline=deadline)
        if re.fullmatch(rb"[1-9][0-9]{0,9}\n?", raw) is None or int(raw) != pid:
            raise Refusal("process_identity")
        files.append(evidence)
    config = native._object(status.get("config"))
    processes = tuple(_process(selection, anchor, pid, config, deadline) for pid in sorted(set(pids) - {0}))
    return _Processes(pids, tuple(files), processes)


def _admit(selection: create.CreateSelection, fd: int, deadline: float) -> _Anchors:
    observed = _collect(selection, fd, deadline)
    worker = _worker(selection, observed)
    _settings(selection)
    sources = create._sources(selection, deadline)
    lima, qemu = (str(item.identity.path) for item in sources[:2])
    if create._command(selection, [lima, "--version"], deadline, "lima_version").strip() != b"limactl version 2.2.1":
        raise Refusal("lima_version")
    version = create._command(selection, [qemu, "--version"], deadline, "qemu_version").splitlines()
    if not version or version[0] != b"qemu-img version 11.1.2":
        raise Refusal("qemu_version")
    config, disk = _files(selection, observed, deadline)
    anchor = _Anchors(observed, worker, config, disk, sources)
    _processes(selection, anchor, _status(selection, anchor, deadline, "Stopped"), deadline)
    _format(selection, anchor, deadline)
    _guard(selection, fd, anchor, deadline)
    _processes(selection, anchor, _status(selection, anchor, deadline, "Stopped"), deadline)
    if create._sources(selection, deadline) != sources:
        raise Refusal("source_changed")
    _settings(selection)
    return anchor


def qualify_boot(selection: create.CreateSelection) -> BootObservation:
    """One closed start and exact stop; preserve partial state on every failure."""
    deadline = time.monotonic() + QUALIFICATION_SECONDS
    work_deadline = deadline - SHUTDOWN_RESERVE
    start_requested = stop_requested = stopped_verified = running_observed = False
    reason = None
    fd = None
    anchor = running = final = processes = None
    try:
        selection = create.parse_selection(create.selection_json(selection))
        fd = create.legacy._open_root(selection.storage.pilot_root)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("storage_busy") from None
        anchor = _admit(selection, fd, work_deadline)
        start_requested = True
        create._command(selection, [str(anchor.sources[0].identity.path), "start", "--tty=false", "--timeout", "10m", "q"],
                        work_deadline, "start", 600)
        running = _guard(selection, fd, anchor, work_deadline)
        processes = _processes(selection, anchor, _status(selection, anchor, work_deadline, "Running"), work_deadline)
        running_observed = True
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if isinstance(error, Refusal) else "qualification_unavailable"
    finally:
        if start_requested and anchor is not None and fd is not None:
            try:
                stop_deadline = deadline - FINAL_VERIFICATION_RESERVE
                identity_deadline = stop_deadline - STOP_SECONDS
                # Rebind safe stop independently of new-work budget admission.
                # Identity checks cannot consume the stop or final-proof reserve.
                _guard(selection, fd, anchor, identity_deadline, identity_only=True)
                status = _status(selection, anchor, identity_deadline)
                current = _processes(selection, anchor, status, identity_deadline)
                if processes is not None and current != processes:
                    raise Refusal("process_changed")
                processes = current
                _guard(selection, fd, anchor, identity_deadline, identity_only=True)
                if _processes(selection, anchor, _status(selection, anchor, identity_deadline), identity_deadline) != processes:
                    raise Refusal("process_changed")
                stop_requested = True
                try:
                    create._command(selection, [str(anchor.sources[0].identity.path), "stop", "--tty=false", "q"],
                                    stop_deadline, "stop", STOP_SECONDS)
                except (Exception, KeyboardInterrupt) as error:
                    reason = reason or (str(error) if isinstance(error, Refusal) else "stop_unavailable")
                # Command success does not prove process death; command failure
                # likewise does not prevent an independent stopped observation.
                final = _guard(selection, fd, anchor, deadline, identity_only=True)
                _processes(selection, anchor, _status(selection, anchor, deadline, "Stopped"), deadline)
                if any(_pid_alive(pid) for pid in set(processes.pids) - {0}):
                    raise Refusal("process_still_alive")
                stopped_verified = True
                _format(selection, anchor, deadline)
                final = _guard(selection, fd, anchor, deadline)
            except (Exception, KeyboardInterrupt) as error:
                reason = reason or (str(error) if isinstance(error, Refusal) else "shutdown_unavailable")
        if fd is not None:
            os.close(fd)
    if reason is not None:
        raise BootRefusal(reason, start_requested=start_requested, stop_requested=stop_requested,
                          stopped_verified=stopped_verified)
    if not running_observed or not stopped_verified or processes is None or running is None or final is None:
        raise BootRefusal("qualification_incomplete", start_requested=start_requested,
                          stop_requested=stop_requested, stopped_verified=stopped_verified)
    return BootObservation("Stopped", True, True, *processes.pids, running, final)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--operation", choices=("qualify-boot",), default="qualify-boot")
    args = parser.parse_args()
    try:
        result = qualify_boot(create.parse_selection(create.private_file(args.selection)))
        report = {"schema_version": 1, "status": "boot_stopped", "worker_status": result.worker_status,
                  "running_observed": result.running_observed, "vm_start_requested": True,
                  "stop_requested": True, "stopped_verified": True, "shutdown_uncertain": False,
                  "session_enabled": False}
    except BootRefusal as error:
        report = {"schema_version": 1, "status": "refused", "blockers": [str(error)],
                  "vm_start_requested": error.start_requested, "stop_requested": error.stop_requested,
                  "stopped_verified": error.stopped_verified, "shutdown_uncertain": error.shutdown_uncertain,
                  "session_enabled": False}
    except (Refusal, OSError, create.CommandRefusal):
        report = {"schema_version": 1, "status": "refused", "blockers": ["selection_unavailable"],
                  "vm_start_requested": False, "stop_requested": False, "stopped_verified": False,
                  "shutdown_uncertain": False, "session_enabled": False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "boot_stopped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
