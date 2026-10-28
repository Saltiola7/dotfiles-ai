"""Private default-off Gate Commit requests, separate from formal gate evidence.

The lifecycle only enqueues. An explicitly started worker claims an event before
calling the ordinary request owner. An uncertain attempt is never replayed.
"""

from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import time

from . import runner


MAX_BINDINGS = 4096
MAX_EVENTS = 128
MAX_RECORD = 32 * 1024
GATES = frozenset({"domain", "behavior", "spec", "contract", "test_driven_implementation",
    "refactor", "review_integrate", "release", "deploy", "operate", "maintain_retire"})
OID = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")
BINDING_FIELDS = {"schema_version", "enrollment", "enrollment_digest", "repository_id", "worktree", "cycle_id"}
EVENT_FIELDS = BINDING_FIELDS | {"event_id", "head", "gates", "created_at", "state"}
RESULTS = {"passed", "failed", "pending", "unavailable", "interrupted", "not_selected", "disabled"}


def _root():
    return runner.default_state_root() / "checkpoint-bindings"


def _enabled(enrollment):
    runner.closed(enrollment, {"schema_version", "enabled"}, runner.ENROLLMENT_FIELDS)
    if type(enrollment["enabled"]) is not bool:
        raise runner.ValidationError("invalid_checkpoint_flag")
    if not enrollment["enabled"]:
        return False
    flag = enrollment.get("checkpoints_enabled", False)
    if type(flag) is not bool:
        raise runner.ValidationError("invalid_checkpoint_flag")
    return flag


def _identity(worktree):
    root = runner.no_alias(Path(worktree))
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir", "--show-toplevel"], capture_output=True,
                                timeout=1, env=runner.git_environment())
        lines = result.stdout.decode().splitlines()
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        raise runner.ValidationError("checkpoint_repository_unavailable") from None
    if result.returncode or len(lines) != 2 or Path(lines[1]).resolve() != root:
        raise runner.ValidationError("checkpoint_repository_mismatch")
    repository = hashlib.sha256(os.fsencode(Path(lines[0]).resolve())).hexdigest()
    return repository, hashlib.sha256(os.fsencode(root)).hexdigest()


def _head(worktree):
    try:
        result = subprocess.run(["git", "-C", str(worktree), "rev-parse", "HEAD"], capture_output=True,
                                timeout=1, env=runner.git_environment())
        head = result.stdout.decode().strip()
    except (OSError, UnicodeError, subprocess.SubprocessError):
        raise runner.ValidationError("checkpoint_repository_unavailable") from None
    if result.returncode or not OID.fullmatch(head):
        raise runner.ValidationError("checkpoint_repository_unavailable")
    return head


def _binding_path(worktree, cycle):
    runner.identifier(cycle)
    repository, worktree_id = _identity(worktree)
    return _root() / repository / worktree_id / (cycle + ".json"), repository


def _safe_parents(path):
    runner.no_alias(path)
    for parent in path.parents:
        if not parent.exists():
            continue
        item = parent.stat()
        if (not stat.S_ISDIR(item.st_mode) or item.st_uid not in {0, os.getuid()}
                or item.st_mode & 0o022 and not item.st_mode & stat.S_ISVTX):
            raise runner.ValidationError("unsafe_checkpoint_parent")


def _read(path, limit=MAX_RECORD):
    _safe_parents(path)
    item = path.lstat()
    if item.st_size > limit:
        raise runner.ValidationError("checkpoint_record_limit")
    return runner.read_private(path)


def _write(path, value):
    if len(runner.canonical(value)) > MAX_RECORD:
        raise runner.ValidationError("checkpoint_record_limit")
    runner.write_private(path, value)


@contextmanager
def _lock(path):
    _safe_parents(path)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        item = os.fstat(descriptor)
        if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
                or item.st_nlink != 1 or item.st_mode & 0o077):
            raise runner.ValidationError("unsafe_checkpoint_lock")
        deadline = time.monotonic() + 1
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise runner.ValidationError("checkpoint_lock_timeout") from None
                time.sleep(0.01)
        yield
    finally:
        os.close(descriptor)


def _binding(value):
    runner.closed(value, BINDING_FIELDS, BINDING_FIELDS)
    if (not isinstance(value["repository_id"], str) or not runner.DIGEST.fullmatch(value["repository_id"])
            or not isinstance(value["enrollment_digest"], str) or not runner.DIGEST.fullmatch(value["enrollment_digest"])):
        raise runner.ValidationError("invalid_checkpoint_binding")
    runner.identifier(value["cycle_id"])
    if any(not isinstance(value[key], str) for key in ("enrollment", "worktree")):
        raise runner.ValidationError("invalid_checkpoint_binding")
    runner.no_alias(Path(value["enrollment"]))
    runner.no_alias(Path(value["worktree"]))
    return value


def _count_bindings(root):
    """Bound directory traversal as well as the number of retained records."""
    count, visited = 0, 0
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        _safe_parents(directory / "entry")
        with os.scandir(directory) as entries:
            for entry in entries:
                if depth == 0 and entry.name == "register.lock":
                    continue
                visited += 1
                if visited > MAX_BINDINGS * 3:
                    raise runner.ValidationError("checkpoint_binding_limit")
                if depth < 2:
                    if not runner.DIGEST.fullmatch(entry.name) or not entry.is_dir(follow_symlinks=False):
                        raise runner.ValidationError("unsafe_checkpoint_registry")
                    pending.append((Path(entry.path), depth + 1))
                else:
                    if not entry.name.endswith(".json") or not runner.ID.fullmatch(entry.name[:-5]):
                        raise runner.ValidationError("unsafe_checkpoint_registry")
                    _binding(_read(Path(entry.path)))
                    count += 1
                    if count > MAX_BINDINGS:
                        raise runner.ValidationError("checkpoint_binding_limit")
    return count


def register(enrollment_path, enrollment):
    """Bind an explicit checkpoint opt-in; disabled configuration has no effects."""
    if not _enabled(enrollment):
        return None
    path = runner.no_alias(Path(enrollment_path))
    runner.outside_git(path.parent)
    stored = _read(path, runner.MAX_PRIVATE_RECORD)
    if runner.digest(stored) != runner.digest(enrollment):
        raise runner.ValidationError("checkpoint_enrollment_changed")
    runner.validate_enrollment(stored)
    if not runner.cycle_open(stored):
        raise runner.ValidationError("enrolled_task_closed")
    target, repository = _binding_path(stored["worktree"], stored["cycle_id"])
    if stored["repository_id"] != repository:
        raise runner.ValidationError("checkpoint_repository_mismatch")
    value = {"schema_version": 1, "enrollment": str(path), "enrollment_digest": runner.digest(stored),
             "repository_id": repository, "worktree": stored["worktree"], "cycle_id": stored["cycle_id"]}
    root = runner.private_dir(_root())
    with _lock(root / "register.lock"):
        count = _count_bindings(root)
        if not os.path.lexists(target) and count >= MAX_BINDINGS:
            raise runner.ValidationError("checkpoint_binding_limit")
        runner.private_dir(target.parent)
        _write(target, value)
    return None


def _load_bound(worktree, cycle):
    if not os.path.lexists(_root()):
        return None
    target, repository = _binding_path(worktree, cycle)
    if not os.path.lexists(target):
        return None
    binding = _binding(_read(target))
    if (binding["repository_id"] != repository or binding["worktree"] != str(worktree)
            or binding["cycle_id"] != cycle):
        raise runner.ValidationError("checkpoint_binding_mismatch")
    enrollment = _read(Path(binding["enrollment"]), runner.MAX_PRIVATE_RECORD)
    if not _enabled(enrollment):
        return None
    if runner.digest(enrollment) != binding["enrollment_digest"]:
        return None
    if any(enrollment.get(key) != binding[key] for key in ("repository_id", "worktree", "cycle_id")):
        raise runner.ValidationError("checkpoint_binding_mismatch")
    return binding, enrollment


def _gates(values):
    if (not isinstance(values, list) or not 1 <= len(values) <= len(GATES)
            or any(not isinstance(item, str) or item not in GATES for item in values)
            or len(values) != len(set(values))):
        raise runner.ValidationError("invalid_checkpoint_gates")
    return sorted(values)


def _event_identity(binding, head, gates):
    return runner.digest({**binding, "head": head, "gates": gates})


def _event(value):
    optional = {"attempted_at", "finished_at", "outcome"}
    runner.closed(value, EVENT_FIELDS, EVENT_FIELDS | optional)
    binding = _binding({key: value[key] for key in BINDING_FIELDS})
    gates = _gates(value["gates"])
    if (not isinstance(value["head"], str) or not OID.fullmatch(value["head"])
            or gates != value["gates"] or value["event_id"] != _event_identity(binding, value["head"], gates)
            or value["state"] not in {"queued", "attempting", "terminal"}):
        raise runner.ValidationError("invalid_checkpoint_event")
    needed = set() if value["state"] == "queued" else {"attempted_at"} if value["state"] == "attempting" else optional
    if (set(value) - EVENT_FIELDS != needed or value.get("outcome", "passed") not in RESULTS):
        raise runner.ValidationError("invalid_checkpoint_event")
    try:
        for key in ("created_at", "attempted_at", "finished_at"):
            if key in value:
                stamp = value[key]
                if not isinstance(stamp, str) or len(stamp) > 64 or datetime.fromisoformat(stamp).utcoffset() is None:
                    raise ValueError
    except (ValueError, TypeError):
        raise runner.ValidationError("invalid_checkpoint_event") from None
    return value


def _event_file(path):
    value = _event(_read(path))
    if path.name != value["event_id"] + ".json":
        raise runner.ValidationError("checkpoint_event_filename")
    return value


def _events(directory):
    retained = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name == "queue.lock":
                continue
            if (not entry.name.endswith(".json") or not runner.DIGEST.fullmatch(entry.name[:-5])
                    or not entry.is_file(follow_symlinks=False)):
                raise runner.ValidationError("unsafe_checkpoint_queue")
            retained.append(Path(entry.path))
            if len(retained) > MAX_EVENTS:
                raise runner.ValidationError("checkpoint_queue_full")
    return retained


def enqueue_gate_commit(worktree, cycle, head, gates):
    """Enqueue one advisory event; never execute checks or start a worker here."""
    worktree = runner.no_alias(Path(worktree))
    bound = _load_bound(worktree, cycle)
    if bound is None:
        return {"status": "disabled"}
    binding, enrollment = bound
    gates = _gates(gates)
    if not isinstance(head, str) or not OID.fullmatch(head):
        raise runner.ValidationError("invalid_checkpoint_head")
    if _head(worktree) != head:
        return {"status": "stale"}
    event_id = _event_identity(binding, head, gates)
    directory = runner.private_dir(Path(runner.text(enrollment.get("state_dir"))) / "checkpoints")
    target = directory / (event_id + ".json")
    with _lock(directory / "queue.lock"):
        retained = _events(directory)
        if os.path.lexists(target):
            _event_file(target)
            return {"status": "duplicate", "event_id": event_id}
        if len(retained) >= MAX_EVENTS:
            raise runner.ValidationError("checkpoint_queue_full")
        value = {**binding, "event_id": event_id, "head": head, "gates": gates,
                 "created_at": runner.now(), "state": "queued"}
        _write(target, value)
    return {"status": "queued", "event_id": event_id}


def drain_one(enrollment_path, run_request):
    """Claim at most one current event before executing through the normal owner."""
    path = runner.no_alias(Path(enrollment_path))
    enrollment = _read(path, runner.MAX_PRIVATE_RECORD)
    if not _enabled(enrollment):
        return None
    directory = runner.no_alias(Path(runner.text(enrollment.get("state_dir"))) / "checkpoints")
    if not os.path.lexists(directory):
        return None
    runner.private_dir(directory)
    with _lock(directory / "queue.lock"):
        retained = [(target, _event_file(target)) for target in _events(directory)]
        if any(value["state"] == "attempting" for _, value in retained):
            return None
        pending = sorted(((target, value) for target, value in retained if value["state"] == "queued"),
                         key=lambda pair: (pair[1]["created_at"], pair[1]["event_id"]))
        if not pending:
            return None
        target, value = pending[0]
        value.update(state="attempting", attempted_at=runner.now())
        _write(target, value)
    # A native lifecycle/status process and Git reads never hold the queue lock.
    # Claiming first also prevents another worker from replaying uncertain work.
    try:
        bound = _load_bound(Path(value["worktree"]), value["cycle_id"])
        eligible = (bound is not None and bound[0] == {key: value[key] for key in BINDING_FIELDS}
                    and value["enrollment"] == str(path) and runner.digest(enrollment) == value["enrollment_digest"]
                    and runner.cycle_open(enrollment)
                    and _head(Path(enrollment["worktree"])) == value["head"])
    except (runner.ValidationError, OSError):
        eligible = False
    if not eligible:
        with _lock(directory / "queue.lock"):
            if _event_file(target) != value:
                raise runner.ValidationError("checkpoint_attempt_changed")
            value.update(state="terminal", finished_at=runner.now(), outcome="interrupted")
            _write(target, value)
        return None
    result = run_request({"schema_version": 1, "enrollment": str(path), "trigger": "checkpoint",
                          "request_id": "checkpoint-" + value["event_id"]})
    if not isinstance(result, dict) or result.get("status") not in RESULTS:
        raise runner.ValidationError("invalid_checkpoint_result")
    with _lock(directory / "queue.lock"):
        if _event_file(target) != value:
            raise runner.ValidationError("checkpoint_attempt_changed")
        value.update(state="terminal", finished_at=runner.now(), outcome=result["status"])
        _write(target, value)
    return result
