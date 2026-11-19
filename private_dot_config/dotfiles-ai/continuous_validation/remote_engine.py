"""A parent-owned permission and lifetime guard for native remote Dagger RPC.

The installed consumer helper owns IAP, host quotas, relay and expiry. This
module never stages source or implements a remote job service.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time
from typing import Never
from urllib.parse import urlsplit
import uuid

from . import runner

LIMIT = 65536
CONFIG_FIELDS = {"schema_version", "endpoint_id", "endpoint_digest", "activation_receipt",
                 "activation_sha256", "control_helper", "control_helper_sha256"}
RUNTIME_FIELDS = {"endpoint_digest", "installation_digest", "runtime_digest",
                  "resource_profile_digest", "owner_digest"}
RECEIPT_FIELDS = {"schema_version", "kind", "repository_id", "endpoint_id", *RUNTIME_FIELDS,
                  "budget_id", "budget_permission_digest", "engine_uri", "max_execution_seconds"}
EXECUTION_FIELDS = {"execution_id", "repository_id", "request_id", "snapshot_id",
                    "manifest_digest", "selection_digest", "check_digest", "check_id"}
BUDGET_FIELDS = {"boot_id", "clock_id", "original_started_monotonic",
                 "original_work_deadline_monotonic", "original_cleanup_deadline_monotonic",
                 "work_deadline_monotonic", "cleanup_deadline_monotonic", "observed_monotonic"}
ORIGINAL_CLOCK = {"boot_id", "clock_id", "original_started_monotonic",
                  "original_work_deadline_monotonic", "original_cleanup_deadline_monotonic"}
TERMINAL_FIELDS = {"execution_completion", "unit_inactive", "container_absent",
                   "cgroup_empty", "relay_absent", "idle_lease_absent"}
RESPONSE_FIELDS = {"schema_version", "request_sha256", "status", "lease_id", "runtime",
                   "budget", "engine_instance", "terminal", "diagnostic_codes"}


def _fail(code: str) -> Never:
    raise runner.ValidationError("remote_engine_" + code)


def _closed(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        _fail("schema_invalid")
    if "schema_version" in value and (type(value["schema_version"]) is not int or value["schema_version"] != 1):
        _fail("schema_invalid")
    if len(runner.canonical(value)) > LIMIT:
        _fail("metadata_limit")
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _json(raw):
    if len(raw) > LIMIT:
        _fail("metadata_limit")
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: _fail("non_finite_json"))
    except (ValueError, UnicodeError, RecursionError):
        _fail("json_invalid")


def _file(path, *, executable=False):
    if not isinstance(path, (str, Path)):
        _fail("file_path_invalid")
    if not Path(path).is_absolute():
        _fail("file_path_invalid")
    path = runner.no_alias(Path(path))
    if executable:
        for parent in path.parents:
            item = parent.lstat()
            if (not stat.S_ISDIR(item.st_mode) or item.st_uid not in {0, os.getuid()}
                    or item.st_mode & 0o022 and not item.st_mode & stat.S_ISVTX):
                _fail("helper_parent_invalid")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        allowed = {0, os.getuid()} if executable else {os.getuid()}
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in allowed or before.st_nlink != 1
                or before.st_mode & (0o022 if executable else 0o077)
                or executable and not before.st_mode & 0o111):
            _fail("file_ownership_invalid")
        maximum = 4 * 1024 * 1024 if executable else LIMIT
        if before.st_size > maximum:
            _fail("file_limit")
        raw = bytearray()
        while len(raw) <= maximum:
            block = os.read(descriptor, min(65536, maximum + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        after = os.fstat(descriptor)
        current = path.lstat()
        keys = ("st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        if len(raw) > maximum or any(getattr(before, key) != getattr(after, key) or getattr(after, key) != getattr(current, key) for key in keys):
            _fail("file_changed")
        return bytes(raw)
    finally:
        os.close(descriptor)


def _digest(value):
    if not isinstance(value, str) or runner.DIGEST.fullmatch(value) is None:
        _fail("digest_invalid")
    return value


def _socket_path(uri):
    if not isinstance(uri, str) or any(char.isspace() for char in uri) or "%" in uri:
        _fail("uri_invalid")
    runner.text(uri)
    parsed = urlsplit(uri)
    if (parsed.scheme != "unix" or parsed.netloc or parsed.query or parsed.fragment
            or not parsed.path.startswith("/") or uri != "unix://" + parsed.path):
        _fail("uri_invalid")
    path = runner.no_alias(Path(parsed.path))
    if len(os.fsencode(path)) >= 104 or path.name in {"", ".", ".."}:
        _fail("socket_path_invalid")
    return str(path)


@dataclass(frozen=True)
class RemoteEngineConfig:
    carrier: dict
    receipt: dict
    receipt_raw: bytes
    socket_path: str
    worktree: Path | None


def validate_config(adapter_config, *, repository_id, worktree=None):
    """Read local authority only; never connect, allocate or invoke a helper."""
    if not isinstance(adapter_config, dict) or len(runner.canonical(adapter_config)) > LIMIT:
        _fail("configuration_invalid")
    if "remote_engine" not in adapter_config:
        return None
    carrier = dict(_closed(adapter_config["remote_engine"], CONFIG_FIELDS))
    for key in ("activation_receipt", "control_helper"):
        runner.text(carrier[key])
    runner.identifier(carrier["endpoint_id"])
    for key in ("endpoint_digest", "activation_sha256", "control_helper_sha256"):
        _digest(carrier[key])
    raw = _file(carrier["activation_receipt"])
    if hashlib.sha256(raw).hexdigest() != carrier["activation_sha256"]:
        _fail("activation_changed")
    receipt = _closed(_json(raw), RECEIPT_FIELDS)
    if receipt["kind"] != "cv-native-remote-engine-v1" or receipt["repository_id"] != repository_id:
        _fail("activation_binding_invalid")
    runner.text(receipt["repository_id"])
    for key in ("endpoint_id", "budget_id"):
        runner.identifier(receipt[key])
    for key in (*RUNTIME_FIELDS, "budget_permission_digest"):
        _digest(receipt[key])
    if any(receipt[key] != carrier[key] for key in ("endpoint_id", "endpoint_digest")):
        _fail("endpoint_changed")
    maximum = receipt["max_execution_seconds"]
    if type(maximum) is not int or not 1 <= maximum <= 7500:
        _fail("execution_limit_invalid")
    path = _socket_path(receipt["engine_uri"])
    pins = adapter_config.get("dagger")
    if not isinstance(pins, dict) or pins.get("engine") != receipt["engine_uri"]:
        _fail("uri_changed")
    helper = runner.no_alias(Path(carrier["control_helper"]))
    root = Path(worktree).resolve() if worktree is not None else None
    if root is not None and helper.is_relative_to(root):
        _fail("repository_helper_forbidden")
    runner.outside_git(helper.parent)
    if hashlib.sha256(_file(helper, executable=True)).hexdigest() != carrier["control_helper_sha256"]:
        _fail("helper_changed")
    return RemoteEngineConfig(carrier, dict(receipt), raw, path, root)


def runtime_identity(config):
    return {key: config.receipt[key] for key in RUNTIME_FIELDS}


def timeout_limit(config, check):
    if config is None or check.get("backend") != "dagger":
        return 3600
    if check.get("configuration", {}).get("engine") != config.receipt["engine_uri"]:
        _fail("descriptor_uri_changed")
    return min(7500, config.receipt["max_execution_seconds"])


def _recheck(config):
    if _file(config.carrier["activation_receipt"]) != config.receipt_raw:
        _fail("activation_changed")
    if hashlib.sha256(_file(config.carrier["control_helper"], executable=True)).hexdigest() != config.carrier["control_helper_sha256"]:
        _fail("helper_changed")
    runner.outside_git(Path(config.carrier["control_helper"]).parent)


def _parent(path):
    parent = runner.no_alias(Path(path).parent)
    item = parent.lstat()
    if not stat.S_ISDIR(item.st_mode) or item.st_uid != os.getuid() or item.st_mode & 0o077:
        _fail("socket_parent_invalid")
    return item.st_dev, item.st_ino


def _socket_identity(path):
    item = Path(path).lstat()
    if not stat.S_ISSOCK(item.st_mode) or item.st_uid != os.getuid():
        _fail("socket_identity_invalid")
    return item.st_dev, item.st_ino


def _finite(number):
    try:
        return type(number) in {int, float} and math.isfinite(number) and number >= 0
    except OverflowError:
        return False


def _response(value, request, config, *, statuses, previous=None):
    _closed(value, RESPONSE_FIELDS)
    if (value["request_sha256"] != runner.digest(request) or value["lease_id"] != request["lease_id"]
            or not isinstance(value["status"], str) or value["status"] not in statuses
            or value["runtime"] != runtime_identity(config)):
        _fail("control_binding_changed")
    if (not isinstance(value["diagnostic_codes"], list) or len(value["diagnostic_codes"]) > 32
            or any(not isinstance(code, str) or runner.ID.fullmatch(code) is None for code in value["diagnostic_codes"])):
        _fail("diagnostics_invalid")
    engine = value["engine_instance"]
    if engine is not None:
        runner.identifier(engine)
    if value["status"] == "active" and engine is None:
        _fail("engine_identity_missing")
    budget = _closed(value["budget"], BUDGET_FIELDS)
    runner.identifier(budget["boot_id"])
    if budget["clock_id"] != "linux-monotonic-v1":
        _fail("clock_unqualified")
    for key in BUDGET_FIELDS - {"boot_id", "clock_id"}:
        number = budget[key]
        if not _finite(number):
            _fail("clock_invalid")
    start, observed = budget["original_started_monotonic"], budget["observed_monotonic"]
    work, cleanup = budget["work_deadline_monotonic"], budget["cleanup_deadline_monotonic"]
    if (not start <= observed or not start <= work <= cleanup <= budget["original_cleanup_deadline_monotonic"]
            or work > budget["original_work_deadline_monotonic"]
            or budget["original_work_deadline_monotonic"] > budget["original_cleanup_deadline_monotonic"]
            or cleanup - work > request["cleanup_seconds"] + 0.001):
        _fail("deadline_invalid")
    if previous is not None:
        old = previous["budget"]
        if (any(budget[key] != old[key] for key in ORIGINAL_CLOCK)
                or observed < old["observed_monotonic"]
                or previous["status"] == "active" and (work > old["work_deadline_monotonic"] or cleanup > old["cleanup_deadline_monotonic"])):
            _fail("deadline_changed")
        if previous["status"] == "active" and engine != previous["engine_instance"]:
            _fail("engine_identity_changed")
    if value["status"] in {"ready", "active"}:
        if not observed < work or work - observed > request["work_seconds"] + 0.001:
            _fail("budget_expired")
    if value["status"] == "terminal":
        terminal = _closed(value["terminal"], TERMINAL_FIELDS)
        if terminal["execution_completion"] != "confirmed_terminal" or any(terminal[key] is not True for key in TERMINAL_FIELDS - {"execution_completion"}):
            _fail("cleanup_unconfirmed")
    elif value["terminal"] is not None:
        _fail("terminal_invalid")
    return value


class OwnerControl:
    """One pinned installed helper; only metadata crosses its fixed operations."""

    def __init__(self, config, proof_dir):
        self.config = config
        self.proof_dir = runner.private_dir(Path(proof_dir))
        self.process = None
        self.log_bytes = 0
        self.pending_inputs = {}
        self.children = []

    def _spawn(self, operation, request):
        _recheck(self.config)
        if operation not in {"status", "open", "stop"}:
            _fail("operation_invalid")
        raw = runner.canonical(request) + b"\n"
        if len(raw) > LIMIT:
            _fail("metadata_limit")
        environment = {key: value for key, value in os.environ.items()
                       if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "CLOUDSDK_CONFIG"}}
        child = subprocess.Popen([self.config.carrier["control_helper"], operation],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 env=environment, start_new_session=True)
        self.children.append(child)
        try:
            if child.stdin is None or child.stdout is None or child.stderr is None:
                _fail("control_pipes_unavailable")
            os.set_blocking(child.stdin.fileno(), False)
            os.set_blocking(child.stdout.fileno(), False)
            os.set_blocking(child.stderr.fileno(), False)
            self.pending_inputs[child.pid] = raw
        except BaseException:
            self._close_child(child)
            raise
        return child

    def _read(self, child, *, timeout, cancel, foreground):
        started, output = time.monotonic(), bytearray()
        if child.stdin is None or child.stdout is None or child.stderr is None:
            _fail("control_pipes_unavailable")
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ, "stdout")
        selector.register(child.stderr, selectors.EVENT_READ, "stderr")
        selector.register(child.stdin, selectors.EVENT_WRITE, "stdin")
        try:
            while True:
                if cancel():
                    raise runner.Interrupted("remote_engine_canceled")
                if time.monotonic() - started >= timeout:
                    _fail("control_timeout")
                for key, _ in selector.select(0.05):
                    if key.data == "stdin":
                        pending = self.pending_inputs[child.pid]
                        try:
                            written = os.write(key.fd, pending[:8192])
                        except BrokenPipeError:
                            _fail("control_input_closed")
                        self.pending_inputs[child.pid] = pending[written:]
                        if not self.pending_inputs[child.pid]:
                            selector.unregister(key.fileobj)
                            child.stdin.close()
                        continue
                    block = os.read(key.fd, LIMIT + 1)
                    if not block:
                        selector.unregister(key.fileobj)
                    elif key.data == "stderr":
                        self.log_bytes += len(block)
                        if self.log_bytes > LIMIT:
                            _fail("control_log_limit")
                        self._log(block)
                    else:
                        output.extend(block)
                        if len(output) > LIMIT:
                            _fail("metadata_limit")
                if foreground and b"\n" in output:
                    line, rest = output.split(b"\n", 1)
                    if rest.strip() or self.pending_inputs[child.pid] or child.poll() is not None:
                        _fail("foreground_unavailable")
                    return _json(line)
                if child.poll() is not None and not selector.get_map():
                    if child.returncode:
                        _fail("control_unavailable")
                    return _json(output)
        finally:
            self.pending_inputs.pop(child.pid, None)
            selector.close()

    def _log(self, raw):
        path = self.proof_dir / "control.log"
        descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            item = os.fstat(descriptor)
            if not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid() or item.st_nlink != 1 or item.st_mode & 0o077 or item.st_size + len(raw) > LIMIT:
                _fail("control_log_invalid")
            os.write(descriptor, raw)
        finally:
            os.close(descriptor)

    def _call(self, operation, request, *, cancel=lambda: False, timeout):
        child = self._spawn(operation, request)
        try:
            return self._read(child, timeout=timeout, cancel=cancel, foreground=False)
        finally:
            if not self._close_child(child):
                raise runner.UncertainTermination("remote_engine_control_termination_unknown")

    def status(self, request, *, cancel, timeout):
        return self._call("status", request, cancel=cancel, timeout=timeout)

    def open(self, request, *, cancel, timeout):
        self.process = self._spawn("open", request)
        return self._read(self.process, timeout=timeout, cancel=cancel, foreground=True)

    def stop(self, request, *, timeout):
        return self._call("stop", request, timeout=timeout)

    def alive(self):
        child = self.process
        if child is None or child.poll() is not None:
            return False
        for stream in (child.stdout, child.stderr):
            if stream is None:
                _fail("control_pipes_unavailable")
            try:
                block = os.read(stream.fileno(), LIMIT + 1)
            except BlockingIOError:
                continue
            if block:
                if stream is child.stdout:
                    _fail("unexpected_foreground_output")
                self.log_bytes += len(block)
                if self.log_bytes > LIMIT:
                    _fail("control_log_limit")
                self._log(block)
        return True

    @staticmethod
    def _kill(child):
        certain = True
        for sig, wait in ((signal.SIGTERM, 0.5), (signal.SIGKILL, 2)):
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
            except OSError:
                certain = False
            try:
                child.wait(timeout=wait)
            except subprocess.TimeoutExpired:
                pass
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            pass
        except OSError:
            certain = False
        else:
            certain = False
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream and not stream.closed:
                stream.close()
        return certain and child.poll() is not None

    def close(self):
        outcomes = [self._close_child(child) for child in list(self.children)]
        return all(outcomes)

    def _close_child(self, child):
        certain = self._kill(child)
        if certain:
            self.children.remove(child)
            if self.process is child:
                self.process = None
        return certain

    def record(self, request, proof):
        payload = {"schema_version": 1, "request": request, "proof": proof}
        path = self.proof_dir / (request["lease_id"] + ".json")
        runner.write_private(path, payload)
        return {"path": str(path), "sha256": hashlib.sha256(_file(path)).hexdigest()}


@dataclass
class RemoteSession:
    work_timeout: float
    runtime: dict = field(default_factory=dict)
    cancel: object = None


@contextmanager
def remote_engine_session(config, check, *, execution, owner, cancel, remaining_seconds):
    """Keep exact remote cleanup inside the caller's existing admission lease."""
    ceiling = timeout_limit(config, check)
    _closed(execution, EXECUTION_FIELDS)
    if execution["repository_id"] != config.receipt["repository_id"] or execution["check_id"] != check["id"] or execution["check_digest"] != runner.digest(check):
        _fail("execution_binding_invalid")
    for key in ("execution_id", "request_id", "check_id"):
        runner.identifier(execution[key])
    for key in ("snapshot_id", "manifest_digest", "selection_digest", "check_digest"):
        _digest(execution[key])
    if not _finite(remaining_seconds):
        _fail("remaining_time_invalid")
    if type(check.get("timeout_seconds")) is not int or not 1 <= check["timeout_seconds"] <= ceiling:
        _fail("execution_limit_invalid")
    total = math.floor(min(check["timeout_seconds"], ceiling, remaining_seconds))
    cleanup_seconds = min(300, max(1, total // 10))
    work_seconds = min(7200, total - cleanup_seconds)
    if work_seconds < 1 or cancel():
        raise runner.Interrupted("remote_engine_canceled_or_expired")
    _recheck(config)
    parent = _parent(config.socket_path)
    if os.path.lexists(config.socket_path):
        _fail("socket_already_exists")
    request = {"schema_version": 1, "activation_receipt": config.receipt,
               "activation_sha256": config.carrier["activation_sha256"], "execution": dict(execution),
               "lease_id": uuid.uuid4().hex, "work_seconds": work_seconds, "cleanup_seconds": cleanup_seconds}
    session = RemoteSession(float(work_seconds))
    started = time.monotonic()
    opened = False
    ready = None
    validated_status = None
    validated_ready = None
    socket_identity = None
    proof = {"cleanup_confirmed": False, "open_attempted": False, "diagnostic_codes": []}
    def effective_cancel():
        try:
            return (cancel() or time.monotonic() - started >= total - cleanup_seconds or not owner.alive()
                    or _parent(config.socket_path) != parent
                    or socket_identity is not None and _socket_identity(config.socket_path) != socket_identity)
        except (runner.ValidationError, OSError):
            return True
    session.cancel = effective_cancel
    try:
        status = owner.status(request, cancel=cancel, timeout=min(30, work_seconds))
        _response(status, request, config, statuses={"ready"})
        validated_status = status
        proof["status"] = status
        if cancel() or _parent(config.socket_path) != parent or os.path.lexists(config.socket_path):
            _fail("socket_or_authority_changed")
        opened = True
        proof["open_attempted"] = True
        ready = owner.open(request, cancel=cancel, timeout=min(30, max(1, work_seconds - (time.monotonic() - started))))
        _response(ready, request, config, statuses={"active"}, previous=status)
        validated_ready = ready
        proof["ready"] = ready
        if _parent(config.socket_path) != parent:
            _fail("socket_parent_changed")
        socket_identity = _socket_identity(config.socket_path)
        if effective_cancel():
            raise runner.Interrupted("remote_engine_canceled")
        session.work_timeout = min(work_seconds - (time.monotonic() - started),
                                   ready["budget"]["work_deadline_monotonic"] - ready["budget"]["observed_monotonic"])
        if session.work_timeout <= 0:
            raise runner.Interrupted("remote_engine_budget_expired")
        yield session
        if effective_cancel():
            raise runner.Interrupted("remote_engine_forward_lost_or_expired")
        if _parent(config.socket_path) != parent or _socket_identity(config.socket_path) != socket_identity:
            _fail("socket_replaced")
    finally:
        stop = None
        try:
            if opened:
                stop = owner.stop(request, timeout=max(0.1, min(cleanup_seconds, total - (time.monotonic() - started))))
                _response(stop, request, config, statuses={"terminal"}, previous=validated_ready or validated_status)
                proof["terminal"] = stop
        except BaseException as error:
            proof["diagnostic_codes"].append(str(error) if isinstance(error, runner.ValidationError) else "remote_engine_cleanup_unavailable")
        try:
            local_closed = owner.close()
            if local_closed is not True:
                _fail("local_forward_termination_unknown")
            if _parent(config.socket_path) != parent:
                _fail("socket_parent_changed")
            if opened and os.path.lexists(config.socket_path):
                _fail("socket_cleanup_unconfirmed")
            proof["local_forward_closed"] = True
            proof["cleanup_confirmed"] = not opened or stop is not None and not proof["diagnostic_codes"]
        except BaseException as error:
            proof["diagnostic_codes"].append(str(error) if isinstance(error, runner.ValidationError) else "remote_engine_local_cleanup_unavailable")
        try:
            reference = owner.record(request, proof)
            session.runtime = {"remote_engine": runtime_identity(config), "remote_execution": {
                "lease_id": request["lease_id"], "engine_instance": stop.get("engine_instance") if stop else None,
                "budget_id": config.receipt["budget_id"], "engine_uri": config.receipt["engine_uri"],
                "cleanup_confirmed": proof["cleanup_confirmed"], "proof": reference,
                "elapsed_seconds": time.monotonic() - started}}
        except BaseException:
            proof["cleanup_confirmed"] = False
        if not proof["cleanup_confirmed"]:
            raise runner.UncertainTermination("remote_engine_cleanup_unknown")
