"""Default-off advisory validation against private immutable source snapshots.

Repository adapters own check semantics. This controller owns enrollment,
source identity, shared admission, bounded execution and private observations.
Nothing in this module grants a DBSCTR or forge gate result.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

VERSION = "1"
MAX_JSON = 1024 * 1024
MAX_LOG = 4 * 1024 * 1024
MAX_FILES = 20000
MAX_SOURCE = 256 * 1024 * 1024
MAX_RECORDS = 200
MAX_PRIVATE_RECORD = 8 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
ENROLLMENT_FIELDS = {
    "schema_version", "enabled", "mode", "worktree", "adapter", "adapter_digest",
    "adapter_python", "adapter_config", "repository_id", "session_id", "cycle_id",
    "base", "state_dir", "feedback_enabled", "feedback_qualification", "feedback_qualification_receipt", "max_running",
    "max_expensive", "debounce_seconds", "max_debounce_seconds", "load_limit",
    "admission_timeout_seconds",
}
CHECK_FIELDS = {"id", "class", "backend", "lane", "timeout_seconds", "cacheable", "configuration"}
LANE_FIELDS = {"os", "architecture", "python", "tools", "dependencies"}
RESERVED = {".git", ".venv", ".dbsctr", "__pycache__", "node_modules"}


class ValidationError(ValueError):
    """A bounded machine-readable refusal; never include raw command output."""


class Interrupted(ValidationError):
    pass


class Deferred(ValidationError):
    pass


class UncertainTermination(ValidationError):
    pass


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError):
        raise ValidationError("non_json_value") from None


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def closed(value, required, allowed):
    if not isinstance(value, dict) or set(value) - allowed or not required <= set(value):
        raise ValidationError("invalid_schema")
    if "schema_version" in value and (type(value["schema_version"]) is not int or value["schema_version"] != 1):
        raise ValidationError("unsupported_schema")
    if len(canonical(value)) > MAX_JSON:
        raise ValidationError("record_limit")
    return value


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValidationError("invalid_identifier")
    return value


def text(value, limit=4096):
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        raise ValidationError("invalid_text")
    return value


def relative(value):
    text(value)
    parts = PurePosixPath(value)
    if parts.is_absolute() or ".." in parts.parts or value in {".", ""}:
        raise ValidationError("invalid_relative_path")
    return value


def no_alias(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise ValidationError("invalid_private_path")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValidationError("private_path_alias")
    return path


def git_environment(environment=None):
    # A caller's GIT_DIR/INDEX/OBJECT redirection must never retarget snapshot
    # mutations. Explicit synthetic identity is the only accepted Git override.
    supplied = environment or os.environ
    clean = {key: value for key, value in supplied.items() if not key.startswith("GIT_")}
    identity = {"GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
                "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE"}
    if environment is not None:
        clean.update({key: value for key, value in environment.items() if key in identity})
    return {**clean, "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1"}


def git(root, *args, input_data=None, environment=None):
    try:
        result = subprocess.run(["git", "-C", str(root), *args], input=input_data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
                                env=git_environment(environment))
    except (OSError, subprocess.SubprocessError):
        raise ValidationError("git_unavailable") from None
    if result.returncode:
        raise ValidationError("git_command_failed")
    return result.stdout


def outside_git(path):
    current = path
    while not current.exists():
        current = current.parent
    result = subprocess.run(["git", "-C", str(current), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, timeout=3, env=git_environment())
    if result.returncode == 0 and result.stdout.strip() == b"true":
        raise ValidationError("private_state_inside_repository")


def private_dir(path):
    path = no_alias(path)
    outside_git(path)
    existing = path
    while not existing.exists():
        existing = existing.parent
    for parent in (existing, *existing.parents):
        item = parent.stat()
        if item.st_uid not in {0, os.getuid()} or item.st_mode & 0o022 and not item.st_mode & stat.S_ISVTX:
            raise ValidationError("unsafe_private_parent")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    item = path.stat()
    if not path.is_dir() or item.st_uid != os.getuid() or item.st_mode & 0o077:
        raise ValidationError("unsafe_private_directory")
    return path


def read_private(path):
    path = no_alias(path)
    item = path.lstat()
    if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid()
            or item.st_nlink != 1 or item.st_mode & 0o077 or item.st_size > MAX_PRIVATE_RECORD):
        raise ValidationError("unsafe_private_record")
    try:
        value = json.loads(path.read_text())
    except (ValueError, UnicodeError):
        raise ValidationError("invalid_json") from None
    return value


def write_private(path, value):
    path = no_alias(path)
    private_dir(path.parent)
    if path.exists():
        read_private(path)
    descriptor, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def repository_id(worktree):
    common = git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    return hashlib.sha256(os.fsencode(Path(common).resolve())).hexdigest()


def cycle_open(enrollment):
    try:
        result = subprocess.run(["dbsctrctl", "status"], cwd=enrollment["worktree"],
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    words = result.stdout.split()
    return result.returncode == 0 and len(words) >= 2 and words[0] == enrollment["cycle_id"] and words[1] in {"active", "finalizing"}


def validate_feedback_receipt(value, *, stored=False):
    fields = {"schema_version", "transport", "codex_version", "active_delivery", "idle_wake"}
    if stored:
        fields.add("assertion")
    closed(value, fields, fields)
    if (value["transport"] != "codex-queue" or value["codex_version"] != "0.163.0"
            or value["active_delivery"] is not True or value["idle_wake"] is not True
            or stored and value["assertion"] != "operator_supplied"):
        raise ValidationError("invalid_feedback_receipt")
    return {**value, "assertion": "operator_supplied"}


def validate_enrollment(value):
    closed(value, {"schema_version", "enabled"}, ENROLLMENT_FIELDS)
    if type(value["enabled"]) is not bool:
        raise ValidationError("invalid_feature_flag")
    if not value["enabled"]:
        return dict(value)
    required = {"worktree", "adapter", "adapter_digest", "repository_id", "session_id", "cycle_id", "base", "state_dir"}
    if not required <= set(value) or value.get("mode", "shadow") != "shadow":
        raise ValidationError("invalid_enrollment")
    value = dict(value)
    value.setdefault("mode", "shadow")
    try:
        session = str(uuid.UUID(value["session_id"]))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("invalid_session") from None
    if session != value["session_id"]:
        raise ValidationError("invalid_session")
    identifier(value["cycle_id"])
    root = no_alias(Path(value["worktree"]))
    if not root.is_dir() or Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root.resolve():
        raise ValidationError("invalid_worktree")
    admin = git(root, "rev-parse", "--path-format=absolute", "--git-dir").decode().strip()
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    if Path(admin).resolve() == Path(common).resolve():
        raise ValidationError("linked_worktree_required")
    branch = git(root, "symbolic-ref", "--short", "HEAD").decode().strip()
    if branch in {"main", "master"}:
        raise ValidationError("task_branch_required")
    if value["repository_id"] != repository_id(root):
        raise ValidationError("repository_identity_changed")
    relative(value["adapter"])
    adapter = root / value["adapter"]
    if adapter.is_symlink() or not adapter.is_file() or adapter.resolve().is_relative_to(root.resolve()) is False:
        raise ValidationError("invalid_adapter")
    if not isinstance(value["adapter_digest"], str) or not DIGEST.fullmatch(value["adapter_digest"]) or hashlib.sha256(adapter.read_bytes()).hexdigest() != value["adapter_digest"]:
        raise ValidationError("adapter_identity_changed")
    value.setdefault("adapter_python", sys.executable)
    interpreter = Path(text(value["adapter_python"]))
    if not interpreter.is_absolute() or not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise ValidationError("adapter_python_unavailable")
    state = no_alias(Path(value["state_dir"]))
    outside_git(state)
    git(root, "rev-parse", "--verify", text(value["base"]) + "^{commit}")
    config = value.setdefault("adapter_config", {})
    if not isinstance(config, dict) or len(canonical(config)) > 64 * 1024:
        raise ValidationError("invalid_adapter_config")
    for name, default, maximum in (("max_running", 2, 8), ("max_expensive", 1, 4)):
        value.setdefault(name, default)
        if type(value[name]) is not int or not 1 <= value[name] <= maximum:
            raise ValidationError("invalid_budget")
    if value["max_expensive"] > value["max_running"]:
        raise ValidationError("invalid_budget")
    for name, default, maximum in (("debounce_seconds", 1.0, 60), ("max_debounce_seconds", 5.0, 120), ("admission_timeout_seconds", 30.0, 600)):
        value.setdefault(name, default)
        if type(value[name]) not in {int, float} or not 0 <= value[name] <= maximum:
            raise ValidationError("invalid_timing")
    if value["max_debounce_seconds"] < value["debounce_seconds"]:
        raise ValidationError("invalid_timing")
    value.setdefault("feedback_enabled", False)
    if type(value["feedback_enabled"]) is not bool:
        raise ValidationError("invalid_feedback_flag")
    qualification = value.get("feedback_qualification")
    if qualification is not None:
        closed(qualification, {"transport", "codex_version", "qualified"}, {"transport", "codex_version", "qualified"})
        if qualification["transport"] != "codex-queue" or type(qualification["qualified"]) is not bool:
            raise ValidationError("invalid_feedback_qualification")
        text(qualification["codex_version"], 128)
    receipt = value.get("feedback_qualification_receipt")
    if receipt is not None:
        validate_feedback_receipt(receipt, stored=True)
    if value["feedback_enabled"] and (receipt is None or qualification is None
            or qualification != {"transport": receipt["transport"], "codex_version": receipt["codex_version"], "qualified": True}):
        raise ValidationError("invalid_feedback_receipt")
    if value.get("load_limit") is not None and (type(value["load_limit"]) not in {int, float} or value["load_limit"] <= 0):
        raise ValidationError("invalid_load_limit")
    return value


def load_enrollment(path):
    return validate_enrollment(read_private(path))


def default_state_root():
    return Path.home() / ".local/state/dotfiles-ai/continuous-validation"


def budget_root():
    # All enrollments use one host/user admission authority, even when their
    # artifact directories differ. Native permissions, not this budget, isolate users.
    return default_state_root() / "admission"


def validate_input_patterns(patterns):
    if not isinstance(patterns, list) or not 1 <= len(patterns) <= 128:
        raise ValidationError("invalid_input_patterns")
    for pattern in patterns:
        text(pattern)
        relative(pattern[1:] if pattern.startswith("!") else pattern)
    if not any(not pattern.startswith("!") for pattern in patterns):
        raise ValidationError("positive_input_pattern_required")
    return patterns


def matches(path, patterns):
    def matched(pattern):
        return pattern == "**" or fnmatch.fnmatchcase(path, pattern) or PurePosixPath(path).match(pattern)
    return (any(matched(pattern) for pattern in patterns if not pattern.startswith("!"))
            and not any(matched(pattern[1:]) for pattern in patterns if pattern.startswith("!")))


def selected_name(name, patterns):
    parts = PurePosixPath(name).parts
    return (not any(part in RESERVED for part in parts)
            and parts[-1] != ".env" and not parts[-1].startswith(".env.")
            and matches(name, patterns))


def inventory(worktree, patterns, *, content=True):
    paths = git(worktree, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")
    entries = {}
    total = 0
    for raw in sorted(set(paths)):
        if not raw:
            continue
        try:
            name = raw.decode("utf-8")
        except UnicodeError:
            raise ValidationError("unsupported_filename") from None
        relative(name)
        if not selected_name(name, patterns):
            continue
        source = worktree / name
        if not os.path.lexists(source):
            continue
        item = source.lstat()
        if source.is_symlink():
            raise ValidationError("source_symlink_unsupported")
        if not stat.S_ISREG(item.st_mode) or not source.resolve().is_relative_to(worktree.resolve()):
            raise ValidationError("source_kind_unsupported")
        total += item.st_size
        if len(entries) >= MAX_FILES or total > MAX_SOURCE:
            raise ValidationError("source_limit")
        entries[name] = {"size": item.st_size, "executable": bool(item.st_mode & 0o111)}
        if content:
            entries[name]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        else:
            entries[name].update(mtime=item.st_mtime_ns, inode=item.st_ino)
    return entries


def historical_inputs(worktree, revisions, patterns, live_size):
    """Resolve only selected historical blobs; never transfer original Git trees."""
    trees = {}
    objects = set()
    for revision in set(revisions):
        entries = []
        raw_tree = git(worktree, "ls-tree", "-r", "-z", revision)
        if len(raw_tree) > MAX_JSON * 8:
            raise ValidationError("snapshot_tree_limit")
        for raw in raw_tree.split(b"\0"):
            if not raw:
                continue
            header, raw_name = raw.split(b"\t", 1)
            try:
                name = raw_name.decode("utf-8")
            except UnicodeError:
                raise ValidationError("unsupported_filename") from None
            relative(name)
            if not selected_name(name, patterns):
                continue
            mode, kind, object_id = header.decode().split()
            if mode not in {"100644", "100755"} or kind != "blob":
                raise ValidationError("source_kind_unsupported")
            entries.append((mode, object_id, name))
            objects.add(object_id)
            if len(entries) > MAX_FILES or len(objects) > MAX_FILES * 3:
                raise ValidationError("snapshot_history_limit")
        trees[revision] = entries
    ordered = sorted(objects)
    sizes = {}
    if ordered:
        checked = git(worktree, "cat-file", "--batch-check", input_data=("\n".join(ordered) + "\n").encode())
        for line in checked.decode().splitlines():
            object_id, kind, size = line.split()
            if kind != "blob":
                raise ValidationError("historical_object_invalid")
            sizes[object_id] = int(size)
    if set(sizes) != objects or live_size + sum(sizes.values()) > MAX_SOURCE:
        raise ValidationError("source_history_limit")
    payload = git(worktree, "cat-file", "--batch", input_data=("\n".join(ordered) + "\n").encode()) if ordered else b""
    blobs = {}
    position = 0
    for object_id in ordered:
        ending = payload.index(b"\n", position)
        header = payload[position:ending].decode().split()
        if header != [object_id, "blob", str(sizes[object_id])]:
            raise ValidationError("historical_object_invalid")
        position = ending + 1
        blobs[object_id] = payload[position:position + sizes[object_id]]
        position += sizes[object_id] + 1
    return trees, blobs


def deterministic_commit(path, tree, parents, label):
    environment = {**os.environ, "GIT_AUTHOR_NAME": "Validation Snapshot",
                   "GIT_AUTHOR_EMAIL": "snapshot@invalid", "GIT_COMMITTER_NAME": "Validation Snapshot",
                   "GIT_COMMITTER_EMAIL": "snapshot@invalid", "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
                   "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000"}
    arguments = ["commit-tree", tree]
    for parent in parents:
        arguments.extend(["-p", parent])
    return git(path, *arguments, input_data=(label + "\n").encode(), environment=environment).decode().strip()


def filtered_git(path, trees, blobs, ancestor, head, base):
    """Retain selector topology with bounded selected trees and fixed metadata."""
    git(path, "init", "-q")
    git(path, "config", "user.name", "Validation Snapshot")
    git(path, "config", "user.email", "snapshot@invalid")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.logAllRefUpdates", "false")
    if blobs:
        data = bytearray()
        for content in blobs.values():
            data.extend(b"blob\ndata " + str(len(content)).encode() + b"\n" + content + b"\n")
        data.extend(b"done\n")
        git(path, "fast-import", "--quiet", input_data=bytes(data))
    mapped = {}
    for original in (ancestor, head, base):
        if original in mapped:
            continue
        git(path, "read-tree", "--empty")
        entries = trees[original]
        if entries:
            data = b"".join((mode + " " + object_id + "\t" + name).encode() + b"\0" for mode, object_id, name in entries)
            git(path, "update-index", "-z", "--index-info", input_data=data)
        tree = git(path, "write-tree").decode().strip()
        parents = [] if original == ancestor else [mapped[ancestor]]
        mapped[original] = deterministic_commit(path, tree, parents, "Filtered source " + original)
    git(path, "read-tree", mapped[head])
    git(path, "add", "--all")
    tree = git(path, "write-tree").decode().strip()
    commit = deterministic_commit(path, tree, [mapped[head]], "Advisory immutable snapshot")
    git(path, "update-ref", "refs/heads/snapshot", commit)
    git(path, "update-ref", "refs/heads/base", mapped[base])
    git(path, "symbolic-ref", "HEAD", "refs/heads/snapshot")
    # Rebuild index records without capture-specific inode/stat fields. Optional
    # index refresh is disabled in adapter children so selection stays stable.
    final_entries = git(path, "ls-tree", "-r", "-z", commit)
    git(path, "read-tree", "--empty")
    if final_entries:
        index = b"".join(raw.replace(b" blob ", b" ", 1) + b"\0" for raw in final_entries.split(b"\0") if raw)
        git(path, "update-index", "-z", "--index-info", input_data=index)
    git_bytes = sum(item.stat().st_size for item in (path / ".git").rglob("*") if item.is_file())
    if git_bytes > MAX_SOURCE + 16 * 1024 * 1024:
        raise ValidationError("snapshot_git_limit")
    return commit, mapped[base]


def capture_snapshot(worktree, patterns, state_dir, base):
    worktree = no_alias(Path(worktree)).resolve()
    validate_input_patterns(patterns)
    state = private_dir(Path(state_dir))
    snapshots = private_dir(state / "snapshots")
    if len(list(snapshots.iterdir())) >= MAX_RECORDS:
        raise ValidationError("snapshot_retention_limit")
    head = git(worktree, "rev-parse", "HEAD").decode().strip()
    base = git(worktree, "rev-parse", "--verify", str(base) + "^{commit}").decode().strip()
    ancestor = git(worktree, "merge-base", base, head).decode().strip()
    original_changes = git(worktree, "diff", "--name-only", "-z", base + "...HEAD").split(b"\0")
    dirty_changes = git(worktree, "diff", "--name-only", "-z", "HEAD").split(b"\0")
    if any(not selected_name(raw.decode(), patterns) for raw in original_changes + dirty_changes if raw):
        raise ValidationError("excluded_changed_input")
    for attempt in range(3):
        before = inventory(worktree, patterns)
        trees, blobs = historical_inputs(worktree, (ancestor, head, base), patterns,
                                         sum(entry["size"] for entry in before.values()))
        path = Path(tempfile.mkdtemp(prefix="source-", dir=snapshots))
        try:
            for name, metadata in before.items():
                target = path / name
                target.parent.mkdir(parents=True, exist_ok=True)
                data = (worktree / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != metadata["sha256"]:
                    raise Interrupted("source_changed")
                target.write_bytes(data)
                target.chmod(0o555 if metadata["executable"] else 0o444)
            if inventory(worktree, patterns) != before or git(worktree, "rev-parse", "HEAD").decode().strip() != head:
                raise Interrupted("source_changed")
            commit, mapped_base = filtered_git(path, trees, blobs, ancestor, head, base)
            changed = git(path, "diff", "--name-only", "-z", mapped_base + "...HEAD").split(b"\0")
            result = {"id": digest({"repository": repository_id(worktree), "head": head, "base": base, "files": before}),
                      "path": str(path), "head": head, "base": mapped_base, "original_base": base,
                      "commit": commit, "files": before, "changed_paths": [raw.decode() for raw in changed if raw]}
            write_private(state / ("snapshot-" + path.name + ".json"), result)
            return result
        except Interrupted:
            shutil.rmtree(path)
            if attempt == 2:
                raise ValidationError("source_unstable") from None
        except Exception:
            shutil.rmtree(path)
            raise
    raise ValidationError("source_unstable")


@contextmanager
def locked(path):
    path = no_alias(path)
    private_dir(path.parent)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        item = os.fstat(descriptor)
        if item.st_uid != os.getuid() or item.st_nlink != 1 or item.st_mode & 0o077:
            raise ValidationError("unsafe_lock")
        deadline = time.monotonic() + 3
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValidationError("admission_lock_unavailable") from None
                time.sleep(0.02)
        yield
    finally:
        os.close(descriptor)


class Budget:
    """Cross-process leases use kernel locks, never PID reuse as ownership proof."""

    def __init__(self, root, max_running=2, max_expensive=1):
        self.root = private_dir(Path(root))
        self.max_running = max_running
        self.max_expensive = max_expensive
        self.index = self.root / "index.json"

    def _read(self):
        value = read_private(self.index) if self.index.exists() else {
            "schema_version": 1, "entries": [],
            "limits": {"max_running": self.max_running, "max_expensive": self.max_expensive}}
        closed(value, {"schema_version", "entries", "limits"}, {"schema_version", "entries", "limits"})
        limits = value["limits"]
        if (not isinstance(limits, dict) or set(limits) != {"max_running", "max_expensive"}
                or any(type(item) is not int or item < 1 for item in limits.values())
                or limits["max_expensive"] > limits["max_running"]):
            raise ValidationError("admission_limits_invalid")
        if not isinstance(value["entries"], list) or len(value["entries"]) > 256:
            raise ValidationError("admission_inventory_invalid")
        active = []
        for entry in value["entries"]:
            closed(entry, {"token", "class", "state", "created"}, {"token", "class", "state", "created"})
            identifier(entry["token"])
            if entry["class"] not in {"cheap", "expensive"} or entry["state"] not in {"queued", "running", "unknown"} or type(entry["created"]) not in {int, float}:
                raise ValidationError("admission_inventory_invalid")
            if entry["state"] == "unknown":
                raise ValidationError("admission_completion_unknown")
            lease = self.root / (entry["token"] + ".lease")
            if not lease.exists():
                raise ValidationError("admission_lease_missing")
            descriptor = os.open(lease, os.O_RDWR | os.O_NOFOLLOW)
            try:
                details = os.fstat(descriptor)
                if details.st_uid != os.getuid() or details.st_nlink != 1 or details.st_mode & 0o077:
                    raise ValidationError("unsafe_admission_lease")
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    active.append(entry)
                else:
                    # A released controller lock does not prove its admitted
                    # subprocess or engine work stopped after a crash.
                    if entry["state"] == "running":
                        raise ValidationError("admission_completion_unknown")
            finally:
                os.close(descriptor)
        value["entries"] = active
        return value

    @contextmanager
    def slot(self, kind, cancel=lambda: False, timeout=30, pressure=lambda: False):
        if kind not in {"cheap", "expensive"}:
            raise ValidationError("invalid_check_class")
        token = uuid.uuid4().hex
        lease = self.root / (token + ".lease")
        descriptor = os.open(lease, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        started = time.monotonic()
        retain_unknown = False
        try:
            with locked(self.root / "index.lock"):
                value = self._read()
                value["entries"].append({"token": token, "class": kind, "state": "queued", "created": started})
                write_private(self.index, value)
            while True:
                if cancel():
                    raise Interrupted("superseded")
                if time.monotonic() - started > timeout:
                    raise Deferred("admission_deferred")
                with locked(self.root / "index.lock"):
                    value = self._read()
                    running = [entry for entry in value["entries"] if entry["state"] == "running"]
                    queued = [entry for entry in value["entries"] if entry["state"] == "queued"]
                    # Cheap work normally wins; aging retains progress for checkpoints.
                    queued.sort(key=lambda entry: (0 if entry["class"] == "cheap" or time.monotonic() - entry["created"] > 5 else 1, entry["created"]))
                    total_limit = min(self.max_running, value["limits"]["max_running"])
                    expensive_limit = min(self.max_expensive, value["limits"]["max_expensive"])
                    eligible = [entry for entry in queued if entry["class"] != "expensive" or sum(item["class"] == "expensive" for item in running) < expensive_limit]
                    if (len(running) < total_limit and eligible and eligible[0]["token"] == token
                            and not (kind == "expensive" and pressure())):
                        for entry in value["entries"]:
                            if entry["token"] == token:
                                entry["state"] = "running"
                        write_private(self.index, value)
                        break
                    write_private(self.index, value)
                time.sleep(0.05)
            try:
                yield time.monotonic() - started
            except UncertainTermination:
                with locked(self.root / "index.lock"):
                    value = self._read()
                    for entry in value["entries"]:
                        if entry["token"] == token:
                            entry["state"] = "unknown"
                    write_private(self.index, value)
                    retain_unknown = True
                raise
        finally:
            try:
                if not retain_unknown:
                    with locked(self.root / "index.lock"):
                        value = self._read()
                        value["entries"] = [entry for entry in value["entries"] if entry["token"] != token]
                        write_private(self.index, value)
            finally:
                os.close(descriptor)
                if not retain_unknown:
                    lease.unlink(missing_ok=True)


def pressure(enrollment):
    try:
        limit = enrollment.get("load_limit") or max(1, (os.cpu_count() or 1) * 0.75)
        return os.getloadavg()[0] > limit
    except (AttributeError, OSError):
        return True


def process(argv, payload, cwd, log_path, timeout, cancel=lambda: False):
    """JSON stdout is bounded; raw stderr and owned descendants stay private."""
    private_dir(log_path.parent)
    descriptor = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    child = None
    selector = selectors.DefaultSelector()
    output = bytearray()
    started = time.monotonic()
    try:
        details = os.fstat(descriptor)
        if details.st_uid != os.getuid() or details.st_nlink != 1 or details.st_mode & 0o077:
            os.close(descriptor)
            raise ValidationError("unsafe_log")
        with os.fdopen(descriptor, "ab", buffering=0) as log:
            child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, start_new_session=True,
                                     env={**git_environment(), "PYTHONDONTWRITEBYTECODE": "1"})
            try:
                os.setpriority(os.PRIO_PROCESS, child.pid, 10)
            except (AttributeError, OSError):
                pass
            pending_input = canonical(payload)
            input_offset = 0
            os.set_blocking(child.stdin.fileno(), False)
            selector.register(child.stdin, selectors.EVENT_WRITE, "input")
            selector.register(child.stdout, selectors.EVENT_READ, "output")
            selector.register(child.stderr, selectors.EVENT_READ, "stderr")
            while True:
                if cancel():
                    raise Interrupted("superseded")
                if time.monotonic() - started > timeout:
                    raise Interrupted("execution_timeout")
                check_log = Path(payload["log_path"]) if payload.get("log_path") else log_path
                if log_path.stat().st_size > MAX_LOG or check_log.exists() and check_log.stat().st_size > MAX_LOG:
                    raise Interrupted("log_limit")
                for key, _ in selector.select(0.1):
                    if key.data == "input":
                        try:
                            input_offset += os.write(key.fileobj.fileno(), pending_input[input_offset:input_offset + 65536])
                        except BrokenPipeError:
                            input_offset = len(pending_input)
                        if input_offset == len(pending_input):
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                    else:
                        data = os.read(key.fileobj.fileno(), 65536)
                        if data:
                            if key.data == "stderr":
                                remaining = max(0, MAX_LOG - log.tell())
                                log.write(data[:remaining])
                                if len(data) > remaining:
                                    raise Interrupted("log_limit")
                            else:
                                output.extend(data)
                                if len(output) > MAX_JSON:
                                    raise Interrupted("adapter_output_limit")
                        else:
                            selector.unregister(key.fileobj)
                if child.poll() is not None and not selector.get_map():
                    break
            if check_log.exists() and check_log.stat().st_size > MAX_LOG:
                raise Interrupted("log_limit")
            if child.returncode:
                raise ValidationError("adapter_command_failed")
            try:
                return json.loads(output)
            except (ValueError, UnicodeError):
                raise ValidationError("adapter_json_invalid") from None
    except OSError:
        raise ValidationError("adapter_unavailable") from None
    finally:
        selector.close()
        if child is not None:
            uncertain = False
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError:
                uncertain = True
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                uncertain = True
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                uncertain = True
            if child.stdout:
                child.stdout.close()
            if child.stderr:
                child.stderr.close()
            if child.stdin and not child.stdin.closed:
                child.stdin.close()
            if uncertain:
                raise UncertainTermination("termination_unconfirmed")


def validate_manifest(value):
    closed(value, {"schema_version", "adapter_id", "input_patterns", "checks"}, {"schema_version", "adapter_id", "input_patterns", "checks"})
    identifier(value["adapter_id"])
    validate_input_patterns(value["input_patterns"])
    if not isinstance(value["checks"], list) or not 1 <= len(value["checks"]) <= 256:
        raise ValidationError("invalid_checks")
    seen = set()
    for check in value["checks"]:
        closed(check, CHECK_FIELDS, CHECK_FIELDS)
        identifier(check["id"])
        if check["id"] in seen or check["class"] not in {"cheap", "expensive"} or check["backend"] not in {"native", "dagger"}:
            raise ValidationError("invalid_check")
        seen.add(check["id"])
        closed(check["lane"], LANE_FIELDS, LANE_FIELDS)
        if type(check["timeout_seconds"]) is not int or not 1 <= check["timeout_seconds"] <= 3600 or type(check["cacheable"]) is not bool or not isinstance(check["configuration"], dict):
            raise ValidationError("invalid_check")
    return value


def adapter_call(enrollment, action, payload, root, state, cancel=lambda: False, timeout=60):
    payload = {**payload, "config": enrollment["adapter_config"]}
    return process([enrollment["adapter_python"], str(root / enrollment["adapter"]), action],
                   payload, root, state / "logs" / (uuid.uuid4().hex + ".log"), timeout, cancel)


def event(state, value):
    folder = private_dir(state / "events")
    if len(list(folder.iterdir())) >= MAX_RECORDS * 16:
        raise ValidationError("event_retention_limit")
    write_private(folder / (uuid.uuid4().hex + ".json"), {"schema_version": 1, "at": now(), **value})


def summarize(observations, pending):
    statuses = {item["status"] for item in observations}
    if "failed" in statuses:
        return "failed"
    if pending:
        return "pending"
    if statuses - {"passed"}:
        return "unavailable"
    return "passed" if observations else "not_selected"


def _run_request(request):
    closed(request, {"schema_version", "enrollment", "trigger"}, {"schema_version", "enrollment", "trigger", "request_id"})
    if request["trigger"] not in {"edit", "checkpoint", "manual"}:
        raise ValidationError("invalid_trigger")
    request_id = identifier(request.get("request_id", uuid.uuid4().hex))
    enrollment_path = no_alias(Path(request["enrollment"]))
    enrollment_source_digest = digest(read_private(enrollment_path))
    enrollment = load_enrollment(enrollment_path)
    if not enrollment["enabled"]:
        return {"schema_version": 1, "request_id": request_id, "status": "disabled", "observations": [], "pending_checks": []}
    if not cycle_open(enrollment):
        raise ValidationError("enrolled_task_closed")
    state = private_dir(Path(enrollment["state_dir"]))
    records = private_dir(state / "observations")
    if len(list(records.iterdir())) >= MAX_RECORDS:
        raise ValidationError("observation_retention_limit")
    started = time.monotonic()
    root = Path(enrollment["worktree"])
    budget = Budget(budget_root(), enrollment["max_running"], enrollment["max_expensive"])
    event(state, {"type": "requested", "request_id": request_id, "trigger": request["trigger"]})
    def preparation_canceled():
        return digest(read_private(enrollment_path)) != enrollment_source_digest
    with budget.slot("cheap", preparation_canceled, enrollment["admission_timeout_seconds"]) as preparation_queue_seconds:
        preparation_started = time.monotonic()
        manifest = validate_manifest(adapter_call(enrollment, "describe", {"schema_version": 1}, root, state))
        patterns = list(dict.fromkeys([*manifest["input_patterns"], enrollment["adapter"]]))
        snapshot = capture_snapshot(root, patterns, state, enrollment["base"])
        if inventory(root, patterns) != snapshot["files"]:
            raise Interrupted("superseded")
        source_signature = inventory(root, patterns, content=False)
    preparation_seconds = time.monotonic() - preparation_started
    current = state / ("current-" + digest({"repository": enrollment["repository_id"], "worktree": str(root)}) + ".json")
    with locked(current.with_suffix(".lock")):
        previous_generation = read_private(current).get("generation", 0) if current.exists() else 0
        if type(previous_generation) is not int or previous_generation < 0:
            raise ValidationError("invalid_generation")
        generation = previous_generation + 1
        write_private(current, {"request_id": request_id, "snapshot_id": snapshot["id"], "generation": generation})
    cancel_state = {"checked": 0.0, "cycle_checked": time.monotonic(), "canceled": False}
    def cancel():
        if cancel_state["canceled"]:
            return True
        if time.monotonic() - cancel_state["checked"] < 0.5:
            return False
        cancel_state["checked"] = time.monotonic()
        try:
            latest = read_private(enrollment_path)
            canceled = (digest(latest) != enrollment_source_digest
                        or read_private(current)["request_id"] != request_id
                        or inventory(root, patterns, content=False) != source_signature
                        or git(root, "rev-parse", "HEAD").decode().strip() != snapshot["head"])
            if time.monotonic() - cancel_state["cycle_checked"] >= 5:
                cancel_state["cycle_checked"] = time.monotonic()
                canceled = canceled or not cycle_open(enrollment)
            cancel_state["canceled"] = canceled
            return canceled
        except (OSError, ValidationError):
            cancel_state["canceled"] = True
            return True
    selection = adapter_call(enrollment, "select", {"schema_version": 1, "snapshot": snapshot["path"], "base": snapshot["base"], "trigger": request["trigger"], "changed_paths": snapshot["changed_paths"]}, Path(snapshot["path"]), state, cancel)
    closed(selection, {"schema_version", "checks", "reason", "complete"}, {"schema_version", "checks", "reason", "complete"})
    checks = {check["id"]: check for check in manifest["checks"]}
    if (not isinstance(selection["checks"], list) or any(not isinstance(item, str) for item in selection["checks"])
            or len(set(selection["checks"])) != len(selection["checks"])
            or any(identifier(item) not in checks for item in selection["checks"])
            or type(selection["complete"]) is not bool):
        raise ValidationError("invalid_selection")
    text(selection["reason"], 4096)
    event(state, {"type": "selected", "request_id": request_id, "snapshot_id": snapshot["id"], "checks": selection["checks"], "complete": selection["complete"]})
    observations = []
    pending = [] if selection["complete"] else ["selection_incomplete"]
    for check_id in selection["checks"]:
        check = checks[check_id]
        if check["class"] == "expensive" and request["trigger"] == "edit":
            pending.append(check_id)
            continue
        observation_id = uuid.uuid4().hex
        log_path = state / "logs" / (observation_id + ".log")
        private_dir(log_path.parent)
        os.close(os.open(log_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600))
        key = digest({"runner": VERSION, "snapshot": snapshot["id"], "selection": selection,
                      "manifest": manifest, "adapter": enrollment["adapter_digest"], "config": enrollment["adapter_config"],
                      "check": check, "runner_bytes": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "python": enrollment["adapter_python"],
                      "python_resolved": str(Path(enrollment["adapter_python"]).resolve()),
                      "python_bytes": hashlib.sha256(Path(enrollment["adapter_python"]).read_bytes()).hexdigest()})
        cache = state / "cache" / (key + ".json")
        reuse = check["cacheable"] and check["backend"] == "native" and check["configuration"].get("hermetic") is True
        result = None
        queued = 0.0
        executed = False
        execution_seconds = 0.0
        check_started = time.monotonic()
        try:
            if cancel():
                raise Interrupted("superseded")
            if reuse and cache.exists():
                result = read_private(cache)
                result["reused_from"] = result["id"]
                result["original_elapsed_seconds"] = result["elapsed_seconds"]
                result["original_at"] = result["at"]
            else:
                with budget.slot(check["class"], cancel, enrollment["admission_timeout_seconds"], lambda: pressure(enrollment)) as queued:
                    executed = True
                    execution_started = time.monotonic()
                    try:
                        result = adapter_call(enrollment, "execute", {"schema_version": 1, "snapshot": snapshot["path"], "base": snapshot["base"], "trigger": request["trigger"], "check": check, "log_path": str(log_path)}, Path(snapshot["path"]), state, cancel, check["timeout_seconds"])
                    finally:
                        execution_seconds = time.monotonic() - execution_started
                closed(result, {"schema_version", "check_id", "status", "exit_code", "runtime", "test_ids", "diagnostic_codes"}, {"schema_version", "check_id", "status", "exit_code", "runtime", "test_ids", "diagnostic_codes"})
                if result["check_id"] != check_id or result["status"] not in {"passed", "failed", "unavailable", "interrupted"} or not isinstance(result["runtime"], dict):
                    raise ValidationError("invalid_check_result")
                if result["exit_code"] is not None and (type(result["exit_code"]) is not int or not 0 <= result["exit_code"] <= 255):
                    raise ValidationError("invalid_exit_code")
                if result["status"] == "passed" and result["exit_code"] != 0:
                    raise ValidationError("invalid_pass")
                for field in ("test_ids", "diagnostic_codes"):
                    if not isinstance(result[field], list) or len(result[field]) > 10000:
                        raise ValidationError("invalid_diagnostics")
                    for item in result[field]:
                        text(item, 1024)
                if any(not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", item) for item in result["diagnostic_codes"]):
                    raise ValidationError("invalid_diagnostic_code")
            if inventory(Path(snapshot["path"]), patterns) != snapshot["files"]:
                raise ValidationError("snapshot_modified_by_check")
            if (cancel() or not cycle_open(enrollment) or inventory(root, patterns) != snapshot["files"]
                    or git(root, "rev-parse", "HEAD").decode().strip() != snapshot["head"]):
                raise Interrupted("superseded")
        except Deferred as error:
            pending.append(check_id)
            result = {"status": "pending", "exit_code": None, "runtime": {}, "test_ids": [], "diagnostic_codes": [str(error)]}
        except (ValidationError, OSError) as error:
            code = str(error) if isinstance(error, ValidationError) else "execution_io_unavailable"
            result = {"status": "interrupted" if isinstance(error, Interrupted) else "unavailable", "exit_code": None, "runtime": {}, "test_ids": [], "diagnostic_codes": [code]}
        result = {**result, "schema_version": 1, "id": observation_id, "request_id": request_id,
                  "snapshot_id": snapshot["id"], "generation": generation, "check_id": check_id, "lane": check["lane"],
                  "manifest_digest": digest(manifest), "selection_digest": digest(selection), "cache_key": key,
                  "executed": executed, "cache_reused": bool(result.get("reused_from")), "queue_seconds": queued,
                  "elapsed_seconds": time.monotonic() - check_started, "execution_seconds": execution_seconds,
                  "at": now(), "log_path": str(log_path),
                  "advisory": True, "resource_metrics": "unavailable", "dagger_cache_metrics": "unavailable"}
        write_private(records / (observation_id + ".json"), result)
        if reuse and result["status"] == "passed" and not result["cache_reused"]:
            write_private(cache, result)
        if (result["status"] in {"failed", "unavailable"} and not cancel() and cycle_open(enrollment)
                and digest(read_private(enrollment_path)) == enrollment_source_digest
                and read_private(current)["request_id"] == request_id
                and inventory(root, patterns) == snapshot["files"]
                and git(root, "rev-parse", "HEAD").decode().strip() == snapshot["head"]):
            try:
                from . import feedback
                result["feedback"] = feedback.deliver(enrollment, result, current_snapshot_id=snapshot["id"], state_dir=state,
                    eligible=lambda: (not cancel() and cycle_open(enrollment)
                        and digest(read_private(enrollment_path)) == enrollment_source_digest
                        and read_private(current)["request_id"] == request_id
                        and inventory(root, patterns) == snapshot["files"]
                        and git(root, "rev-parse", "HEAD").decode().strip() == snapshot["head"]))
            except (ImportError, OSError, ValueError):
                result["feedback"] = {"status": "unavailable", "reason": "feedback_unavailable"}
            write_private(records / (observation_id + ".json"), result)
        observations.append(result)
    result = {"schema_version": 1, "request_id": request_id, "snapshot_id": snapshot["id"], "generation": generation,
              "status": summarize(observations, pending), "observations": observations, "pending_checks": pending,
              "selection_complete": selection["complete"], "preparation_seconds": preparation_seconds,
              "preparation_queue_seconds": preparation_queue_seconds,
              "elapsed_seconds": time.monotonic() - started, "advisory": True, "new_execution": True}
    write_private(state / "requests" / (request_id + ".json"), {
        "schema_version": 1, "request_digest": digest(request), "enrollment_digest": enrollment_source_digest,
        "patterns": patterns, "files": snapshot["files"], "head": snapshot["head"], "result": result})
    event(state, {"type": "finished", "request_id": request_id, "snapshot_id": snapshot["id"], "status": result["status"]})
    return result


def run_request(request):
    """A repeated request ID is an idempotent query, never another execution."""
    closed(request, {"schema_version", "enrollment", "trigger"}, {"schema_version", "enrollment", "trigger", "request_id"})
    request = {**request, "request_id": identifier(request.get("request_id", uuid.uuid4().hex))}
    enrollment = load_enrollment(Path(request["enrollment"]))
    if not enrollment["enabled"]:
        return _run_request(request)
    if not cycle_open(enrollment):
        raise ValidationError("enrolled_task_closed")
    state = private_dir(Path(enrollment["state_dir"]))
    requests = private_dir(state / "requests")
    if len(list(requests.glob("*.json"))) >= MAX_RECORDS and not (requests / (request["request_id"] + ".json")).exists():
        raise ValidationError("request_retention_limit")
    record = requests / (request["request_id"] + ".json")
    lease = requests / (request["request_id"] + ".lock")
    descriptor = os.open(lease, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        details = os.fstat(descriptor)
        if details.st_uid != os.getuid() or details.st_nlink != 1 or details.st_mode & 0o077:
            raise ValidationError("unsafe_request_lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            prior = read_private(record) if record.exists() else None
            if prior is not None and prior.get("request_digest") != digest(request):
                raise ValidationError("request_identity_reused") from None
            return {"schema_version": 1, "request_id": request["request_id"], "status": "pending",
                    "coalesced_with": request["request_id"], "new_execution": False, "advisory": True}
        if record.exists():
            prior = read_private(record)
            if prior.get("request_digest") != digest(request) or prior.get("enrollment_digest") != digest(read_private(Path(request["enrollment"]))):
                raise ValidationError("request_identity_reused")
            if "result" in prior:
                if (inventory(Path(enrollment["worktree"]), prior["patterns"]) != prior["files"]
                        or prior.get("head") is not None and git(Path(enrollment["worktree"]), "rev-parse", "HEAD").decode().strip() != prior["head"]):
                    raise ValidationError("request_source_changed")
                return {**prior["result"], "coalesced_with": request["request_id"], "new_execution": False}
            return {"schema_version": 1, "request_id": request["request_id"], "status": "unavailable",
                    "error_code": "previous_execution_interrupted", "observations": [],
                    "pending_checks": ["previous_execution_interrupted"], "new_execution": False, "advisory": True}
        write_private(record, {"schema_version": 1, "request_digest": digest(request),
                               "enrollment_digest": digest(read_private(Path(request["enrollment"])))})
        try:
            return _run_request(request)
        except (ValidationError, OSError) as error:
            code = str(error) if isinstance(error, ValidationError) else "execution_io_unavailable"
            result = {"schema_version": 1, "request_id": request["request_id"],
                      "status": "interrupted" if isinstance(error, Interrupted) else "pending" if isinstance(error, Deferred) else "unavailable",
                      "error_code": code, "observations": [], "pending_checks": ["selection_or_execution_incomplete"],
                      "selection_complete": False, "advisory": True, "new_execution": False}
            write_private(record, {"schema_version": 1, "request_digest": digest(request),
                                   "enrollment_digest": digest(read_private(Path(request["enrollment"]))),
                                   "patterns": [], "files": {}, "result": result})
            event(state, {"type": "interrupted_or_unavailable", "request_id": request["request_id"], "status": result["status"], "code": code})
            return result
    finally:
        os.close(descriptor)


def inspect_status(enrollment_path):
    enrollment = load_enrollment(enrollment_path)
    if not enrollment["enabled"]:
        return {"schema_version": 1, "status": "disabled", "enabled": False}
    state = no_alias(Path(enrollment["state_dir"]))
    latest = []
    if (state / "observations").is_dir():
        for path in sorted((state / "observations").glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:20]:
            item = read_private(path)
            latest.append({key: item.get(key) for key in ("id", "request_id", "snapshot_id", "check_id", "status", "executed", "cache_reused", "at")})
    index = budget_root() / "index.json"
    admission = read_private(index) if index.exists() else {"entries": [], "limits": None}
    return {"schema_version": 1, "status": "enrolled", "enabled": True,
            "task_open": cycle_open(enrollment), "latest_observations": latest,
            "admission_metadata": admission, "live_lease_ownership": "not_probed",
            "capabilities": {"native_adapter": Path(enrollment["adapter_python"]).is_file(),
                             "feedback_qualified": bool(enrollment.get("feedback_qualification", {}).get("qualified")),
                             "dagger_runtime": "adapter_owned_not_probed", "resource_enforcement": "admission_only"}}


def enroll(args):
    if not args.enable_shadow:
        return {"schema_version": 1, "status": "disabled", "enabled": False}
    root = no_alias(Path(args.worktree)).resolve()
    adapter = relative(args.adapter)
    state = no_alias(Path(args.state_dir)).resolve()
    if args.adapter_config:
        configuration_path = no_alias(Path(args.adapter_config))
        outside_git(configuration_path.parent)
        config = read_private(configuration_path)
    else:
        config = {}
    value = {"schema_version": 1, "enabled": True, "mode": "shadow", "worktree": str(root), "adapter": adapter,
             "adapter_digest": hashlib.sha256((root / adapter).read_bytes()).hexdigest(), "adapter_python": str(Path(args.python).expanduser().absolute()),
             "adapter_config": config, "repository_id": repository_id(root), "session_id": args.session_id,
             "cycle_id": args.cycle_id, "base": git(root, "rev-parse", args.base + "^{commit}").decode().strip(),
             "state_dir": str(state), "feedback_enabled": False}
    if args.feedback_qualification:
        qualification_path = no_alias(Path(args.feedback_qualification))
        outside_git(qualification_path.parent)
        receipt = validate_feedback_receipt(read_private(qualification_path))
        value["feedback_qualification_receipt"] = receipt
        value["feedback_qualification"] = {"transport": receipt["transport"],
            "codex_version": receipt["codex_version"], "qualified": True}
        value["feedback_enabled"] = True
    value = validate_enrollment(value)
    if not cycle_open(value):
        raise ValidationError("enrolled_task_closed")
    write_private(no_alias(Path(args.enrollment)), value)
    return {"schema_version": 1, "status": "enrolled", "enabled": True, "feedback_enabled": value["feedback_enabled"]}


def watch(enrollment_path, once=False):
    enrollment = load_enrollment(enrollment_path)
    if not enrollment["enabled"]:
        return {"schema_version": 1, "status": "disabled"}
    state = private_dir(Path(enrollment["state_dir"]))
    manifest = validate_manifest(adapter_call(enrollment, "describe", {"schema_version": 1}, Path(enrollment["worktree"]), state))
    patterns = [*manifest["input_patterns"], enrollment["adapter"]]
    previous = None
    first_change = last_change = None
    while True:
        current = load_enrollment(enrollment_path)
        if not current["enabled"] or not cycle_open(current):
            return {"schema_version": 1, "status": "stopped"}
        value = digest(inventory(Path(enrollment["worktree"]), patterns, content=False))
        if value != previous:
            previous = value
            last_change = time.monotonic()
            first_change = first_change or last_change
        if first_change is not None and (time.monotonic() - last_change >= enrollment["debounce_seconds"] or time.monotonic() - first_change >= enrollment["max_debounce_seconds"]):
            result = run_request({"schema_version": 1, "enrollment": str(enrollment_path), "trigger": "edit"})
            first_change = last_change = None
            if once:
                return result
            print(json.dumps(result), flush=True)
        time.sleep(0.5)


def validate_observation(value):
    """Accept complete controller records, never sparse backend receipts."""
    required = {"schema_version", "id", "request_id", "snapshot_id", "generation", "check_id", "lane",
                "manifest_digest", "selection_digest", "cache_key", "status", "exit_code", "runtime", "test_ids",
                "diagnostic_codes", "executed", "cache_reused", "queue_seconds", "elapsed_seconds",
                "execution_seconds", "at", "log_path", "advisory", "resource_metrics", "dagger_cache_metrics"}
    reuse_fields = {"reused_from", "original_elapsed_seconds", "original_at"}
    closed(value, required, required | reuse_fields | {"feedback"})
    for name in ("id", "request_id", "check_id"):
        identifier(value[name])
    for name in ("snapshot_id", "manifest_digest", "selection_digest", "cache_key"):
        if not isinstance(value[name], str) or not DIGEST.fullmatch(value[name]):
            raise ValidationError("invalid_observation_identity")
    if type(value["generation"]) is not int or value["generation"] < 1:
        raise ValidationError("invalid_observation_generation")
    closed(value["lane"], LANE_FIELDS, LANE_FIELDS)
    for name in ("os", "architecture", "python"):
        text(value["lane"][name], 256)
    if any(not isinstance(value["lane"][name], dict) for name in ("tools", "dependencies")):
        raise ValidationError("invalid_observation_lane")
    if not isinstance(value["status"], str) or value["status"] not in {"passed", "failed", "unavailable", "interrupted", "pending"}:
        raise ValidationError("invalid_observation_status")
    code = value["exit_code"]
    if code is not None and (type(code) is not int or not 0 <= code <= 255):
        raise ValidationError("invalid_observation_exit_code")
    if value["status"] == "passed" and code != 0:
        raise ValidationError("invalid_observation_pass")
    if not isinstance(value["runtime"], dict):
        raise ValidationError("invalid_observation_runtime")
    for name in ("os", "architecture", "python", "platform", "adapter_python", "backend", "execution",
                 "sdk_version", "engine_version", "uv", "image_digest"):
        if name in value["runtime"]:
            text(value["runtime"][name], 4096)
    if "tools" in value["runtime"] and not isinstance(value["runtime"]["tools"], dict):
        raise ValidationError("invalid_observation_runtime")
    for name in ("test_ids", "diagnostic_codes"):
        if not isinstance(value[name], list) or len(value[name]) > 10000:
            raise ValidationError("invalid_observation_diagnostics")
        for item in value[name]:
            text(item, 1024)
    if any(not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", item) for item in value["diagnostic_codes"]):
        raise ValidationError("invalid_observation_diagnostics")
    if any(type(value[name]) is not bool for name in ("executed", "cache_reused")) or value["advisory"] is not True:
        raise ValidationError("invalid_observation_flag")
    if value["executed"] and value["cache_reused"]:
        raise ValidationError("invalid_observation_reuse")
    if value["status"] in {"passed", "failed"} and not (value["executed"] or value["cache_reused"]):
        raise ValidationError("invalid_observation_execution")
    if value["cache_reused"]:
        if not reuse_fields <= value.keys() or value["status"] != "passed":
            raise ValidationError("invalid_observation_reuse")
        identifier(value["reused_from"])
    elif reuse_fields & value.keys():
        raise ValidationError("invalid_observation_reuse")
    for name in ("queue_seconds", "elapsed_seconds", "execution_seconds", "original_elapsed_seconds"):
        if name in value and (type(value[name]) not in {int, float} or value[name] < 0
                              or type(value[name]) is float and not math.isfinite(value[name])):
            raise ValidationError("invalid_observation_timing")
    for name in ("at", "original_at"):
        if name in value:
            try:
                if datetime.fromisoformat(text(value[name], 128)).tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise ValidationError("invalid_observation_timestamp") from None
    if not Path(text(value["log_path"])).is_absolute():
        raise ValidationError("invalid_observation_log")
    for name in ("resource_metrics", "dagger_cache_metrics"):
        if value[name] != "unavailable" and not isinstance(value[name], dict):
            raise ValidationError("invalid_observation_metrics")
    if "feedback" in value and not isinstance(value["feedback"], dict):
        raise ValidationError("invalid_observation_feedback")
    return value


RUNTIME_MEASUREMENTS = {"cache", "cache_metrics", "cache_counters", "metrics", "resource_metrics",
                        "dagger_cache_metrics", "artifacts", "termination_signal"}


def comparison_runtime(observation):
    """Project measured runtime identity without treating cache hits as inputs."""
    identity = {key: value for key, value in observation["runtime"].items() if key not in RUNTIME_MEASUREMENTS}
    def unresolved(value):
        if value is None:
            return True
        if isinstance(value, str):
            return not value or bool(re.search(r"(?:^|[ _-])(unknown|unresolved|unavailable|unconfigured|not_probed)(?:$|[ _-])", value, re.I))
        if isinstance(value, dict):
            return any(unresolved(item) for item in value.values())
        if isinstance(value, list):
            return any(unresolved(item) for item in value)
        return False
    architectures = {"arm64": "arm64", "aarch64": "arm64", "amd64": "amd64", "x86_64": "amd64"}
    if isinstance(identity.get("platform"), str) and identity["platform"] in {"linux/arm64", "linux/amd64"}:
        os_name, architecture = identity["platform"].split("/")
    else:
        os_name = identity.get("os", "")
        architecture = identity.get("architecture", "")
    architecture = architectures.get(architecture) if isinstance(architecture, str) else None
    python = identity.get("python")
    complete = (os_name in {"linux", "darwin"} and architecture is not None
                and isinstance(python, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python) is not None)
    lane = observation["lane"]
    agrees_with_lane = (os_name == lane["os"] and architecture == architectures.get(lane["architecture"])
                        and isinstance(python, str) and (python == lane["python"] or python.startswith(lane["python"] + ".")))
    qualified = complete and agrees_with_lane and not unresolved(identity) and not unresolved(lane)
    return identity, bool(qualified)


def metric_availability(value):
    if not isinstance(value, dict) or not value or value.get("available") is False:
        return "unavailable"
    if isinstance(value.get("availability"), str) and value["availability"] in {"unavailable", "unknown", "unsupported"}:
        return "unavailable"
    return "available"


def compare(value):
    closed(value, {"schema_version", "observations"}, {"schema_version", "observations"})
    if not isinstance(value["observations"], list) or len(value["observations"]) != 2:
        raise ValidationError("comparison_requires_pair")
    observations = [validate_observation(read_private(Path(text(path)))) for path in value["observations"]]
    left, right = observations
    runtimes = [comparison_runtime(item) for item in observations]
    duplicate_sample = left["id"] == right["id"] or left["request_id"] == right["request_id"]
    qualified = all(item[1] for item in runtimes) and not duplicate_sample
    qualification_reasons = [([] if item[1] else ["runtime_identity_unresolved"])
                             + (["duplicate_sample"] if duplicate_sample else []) for item in runtimes]
    fields = ("snapshot_id", "check_id", "lane", "manifest_digest", "selection_digest", "cache_key", "test_ids")
    differences = [field for field in fields if left[field] != right[field]]
    if runtimes[0][0] != runtimes[1][0]:
        differences.append("runtime")
    matched = qualified and not differences
    return {"schema_version": 1, "status": "unqualified" if not qualified else "matched" if matched else "unmatched",
            "qualified": qualified, "matched": matched, "differences": differences,
            "qualification_reasons": qualification_reasons,
            "statuses": [item["status"] for item in observations],
            "elapsed_seconds": [item["elapsed_seconds"] for item in observations],
            "execution_seconds": [item["execution_seconds"] for item in observations],
            "queue_seconds": [item["queue_seconds"] for item in observations],
            "executed": [item["executed"] for item in observations],
            "cache_reused": [item["cache_reused"] for item in observations],
            "metric_availability": [{name: metric_availability(item[name])
                                     for name in ("resource_metrics", "dagger_cache_metrics")} for item in observations],
            "runtime_cache_reports": [item["runtime"].get("cache", "unavailable") for item in observations],
            "advisory": True}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "engine":
        from . import local_engine
        return local_engine.main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="continuous-validation " + VERSION)
    commands = parser.add_subparsers(dest="operation", required=True)
    add = commands.add_parser("enroll")
    for name in ("worktree", "adapter", "session-id", "cycle-id", "base", "enrollment"):
        add.add_argument("--" + name, required=True)
    add.add_argument("--enable-shadow", action="store_true")
    add.add_argument("--json", action="store_true")
    add.add_argument("--state-dir", default=str(default_state_root() / "artifacts"))
    add.add_argument("--python", default=sys.executable)
    add.add_argument("--adapter-config")
    add.add_argument("--feedback-qualification")
    for name in ("run", "checkpoint"):
        command = commands.add_parser(name)
        command.add_argument("--request", required=True)
        command.add_argument("--json", action="store_true")
    command = commands.add_parser("watch")
    command.add_argument("--enrollment", required=True)
    command.add_argument("--once", action="store_true")
    command.add_argument("--json", action="store_true")
    for name in ("status", "stop"):
        command = commands.add_parser(name)
        command.add_argument("--enrollment")
        command.add_argument("--json", action="store_true")
    command = commands.add_parser("compare")
    command.add_argument("--experiment", required=True)
    command.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "enroll":
            result = enroll(args)
        elif args.operation in {"run", "checkpoint"}:
            request = read_private(Path(args.request))
            if args.operation == "checkpoint":
                request["trigger"] = "checkpoint"
            result = run_request(request)
        elif args.operation == "watch":
            result = watch(Path(args.enrollment), args.once)
        elif args.operation == "compare":
            result = compare(read_private(Path(args.experiment)))
        elif not args.enrollment:
            result = {"schema_version": 1, "status": "disabled", "enabled": False}
        elif args.operation == "status":
            result = inspect_status(Path(args.enrollment))
        else:
            value = read_private(Path(args.enrollment))
            closed(value, {"schema_version", "enabled"}, ENROLLMENT_FIELDS)
            if type(value["enabled"]) is not bool:
                raise ValidationError("invalid_feature_flag")
            value["enabled"] = False
            write_private(Path(args.enrollment), value)
            result = {"schema_version": 1, "status": "disabled", "enabled": False, "cancellation_requested": True}
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") in {"disabled", "stopped", "enrolled", "passed", "not_selected"} or args.operation == "compare" else 1 if result.get("status") == "failed" else 2
    except (ValidationError, OSError, ValueError) as error:
        code = str(error) if isinstance(error, ValidationError) else "input_unavailable"
        print(json.dumps({"schema_version": 1, "status": "unavailable", "error_code": code, "advisory": True}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
