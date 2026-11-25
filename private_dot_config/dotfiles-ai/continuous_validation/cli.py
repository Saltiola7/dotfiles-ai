"""Managed owner for lifecycle-requested validation. Every action is advisory.

The lifecycle helper selects this module and calls ``managed_action`` after its
own policy admission. This module adds no scheduler, watcher, enrollment writer
or gate authority: it resolves the one enrollment explicitly bound to the task
and delegates to the ordinary request owner.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import uuid

from . import checkpoints, runner

UNSUPPORTED = "owner_action_unsupported"
LEGACY_STATUS = {"enroll": "not_enrolled", "checkpoint": "legacy_enrolled"}
MAX_CHANGED_PATHS = 256
MAX_FAILED_TEST_IDS = 200
MAX_DIAGNOSTIC_CODES = 200
MAX_RECEIPT_PROJECTION = 8192


def _admitted(policy_path):
    """Recheck the private feature flag; a missing or disabled policy admits nothing."""
    try:
        value = runner.read_private(Path(policy_path))
    except (runner.ValidationError, OSError, TypeError):
        return False
    return isinstance(value, dict) and value.get("enabled") is True


def _unavailable(code):
    return {"schema_version": 1, "status": "unavailable", "error_code": code, "observations": [], "advisory": True}


def _bound(worktree, cycle):
    """The enabled checkpoint enrollment explicitly bound to this exact worktree and task."""
    return checkpoints._load_bound(runner.no_alias(Path(worktree)), cycle)


def _retained(directory, prefix):
    """Bounded read of retained private records; an unreadable record is skipped, never trusted."""
    if not directory.is_dir():
        return []
    values = []
    for path in sorted(directory.glob(prefix + "*.json"))[:runner.MAX_RECORDS]:
        try:
            value = runner.read_private(path)
        except (runner.ValidationError, OSError):
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def _selection(worktree, cycle):
    bound = _bound(worktree, cycle)
    if bound is None:
        return _unavailable("enrollment_inactive")
    binding, stored = bound
    return {"schema_version": 1, "status": "completed", "advisory": True,
            **runner.preview_selection(binding["enrollment"], stored)}


def _observation(item, context):
    identity = item["runtime"].get("test_identity")
    result = {name: item[name] for name in ("id", "check_id", "status", "snapshot_id", "executed", "cache_reused",
                                            "request_id", "generation")}
    result["failed_test_ids"] = identity.get("failed_test_ids", [])[:MAX_FAILED_TEST_IDS] if identity else []
    result["diagnostic_codes"] = item["diagnostic_codes"][:MAX_DIAGNOSTIC_CODES]
    if (context is not None and "started_at" in item
            and len(runner.canonical(item["lane"])) <= MAX_RECEIPT_PROJECTION
            and len(runner.canonical(identity)) <= MAX_RECEIPT_PROJECTION):
        result["receipt"] = {**context, "manifest_digest": item["manifest_digest"],
                             "lane": item["lane"], "test_identity": identity, "started_at": item["started_at"],
                             "finished_at": item["at"], "elapsed_seconds": item["execution_seconds"]}
    return result


def _validate(worktree, cycle, check_ids, request_id, selection_pin):
    bound = _bound(worktree, cycle)
    if bound is None:
        return _unavailable("enrollment_inactive")
    binding, stored = bound
    enrollment = runner.validate_enrollment(dict(stored))
    if not runner.cycle_open(enrollment):
        return _unavailable("enrolled_task_closed")
    if check_ids is not None and not isinstance(check_ids, list):
        return _unavailable("invalid_checks")
    request = {"schema_version": 1, "enrollment": binding["enrollment"], "trigger": "affected",
               "request_id": request_id or uuid.uuid4().hex}
    if check_ids is not None:
        request["checks"] = list(check_ids)
    if selection_pin is not None:
        request["selection_pin"] = selection_pin
    result = runner.run_request(request)
    if "snapshot_id" not in result and result["status"] != "pending":
        return {**_unavailable(result.get("error_code", "enrollment_inactive")), "request_id": result["request_id"]}
    if "snapshot_id" not in result:
        return {**_unavailable(result.get("error_code", "request_pending")), "status": "pending",
                "request_id": result["request_id"], "new_execution": False}
    pending = result["pending_checks"]
    if check_ids is not None and not result["selection_complete"] and pending[:1] == ["selection_incomplete"]:
        # The runner puts the selection sentinel first; preserve real pending checks.
        pending = pending[1:]
    return {
        "schema_version": 1,
        "status": "pending" if "error_code" in result or any(item["status"] == "pending" for item in result["observations"]) else "completed",
        "request_id": result["request_id"], "snapshot_id": result["snapshot_id"], "generation": result["generation"],
        "selection_complete": result["selection_complete"], "pending_checks": pending,
        "new_execution": result["new_execution"],
        "observations": [_observation(item, result.get("receipt_context")) for item in result["observations"]],
        **({"error_code": result["error_code"]} if "error_code" in result else {}),
        "advisory": True,
    }


def _paths_in_scope(paths, files):
    if not isinstance(paths, list) or len(paths) > MAX_CHANGED_PATHS or not isinstance(files, dict):
        return False
    for path in paths:
        try:
            runner.relative(path)
        except runner.ValidationError:
            return False
        if path != PurePosixPath(path).as_posix() or "\\" in path or path not in files:
            return False
    return True


def _applicability(worktree, cycle, snapshot_id, paths):
    """A receipt is evidence about captured content; a newer request alone does not retire it."""
    refused = {"schema_version": 1, "applicable": False, "changed_paths": []}
    if paths is not None:
        refused["paths_in_scope"] = False
    try:
        bound = _bound(worktree, cycle)
        if bound is None:
            return {**refused, "reason": "enrollment_inactive"}
        enrollment = runner.validate_enrollment(dict(bound[1]))
        if not runner.cycle_open(enrollment):
            return {**refused, "reason": "enrollment_inactive"}
    except runner.ValidationError as error:
        return {**refused, "reason": "enrollment_inactive", "error_code": str(error)}
    if not isinstance(snapshot_id, str) or not runner.DIGEST.fullmatch(snapshot_id):
        return {**refused, "reason": "snapshot_unknown"}
    root = Path(enrollment["worktree"])
    state = runner.no_alias(Path(enrollment["state_dir"]))
    record = next((item for item in _retained(state / "requests", "")
                   if item.get("kind") == "completed" and item.get("observation_refs")
                   and isinstance(item.get("result"), dict) and item["result"].get("snapshot_id") == snapshot_id), None)
    if record is None:
        return {**refused, "reason": "snapshot_unknown"}
    try:
        files_digest = record.get("files_digest")
        files = next((item["files"] for item in _retained(state, "snapshot-") if item.get("id") == snapshot_id
                      and isinstance(item.get("files"), dict) and runner.digest(item["files"]) == files_digest), None)
        current = runner.inventory(root, runner.validate_input_patterns(record.get("patterns")))
    except runner.ValidationError as error:
        # Content that cannot be inventoried is not demonstrably unchanged.
        return {**refused, "reason": "source_changed", "changed_paths_complete": False, "error_code": str(error)}
    scope = {"paths_in_scope": _paths_in_scope(paths, files)} if paths is not None else {}
    if runner.digest(current) != files_digest:
        changed = None if not isinstance(files, dict) else sorted(
            name for name in set(current) | set(files) if current.get(name) != files.get(name))
        return {**refused, **scope, "reason": "source_changed", "changed_paths": (changed or [])[:MAX_CHANGED_PATHS],
                "changed_paths_complete": changed is not None and len(changed) <= MAX_CHANGED_PATHS}
    try:
        # A generation record that cannot be read is not a lineage this owner will vouch for.
        token = runner.generation_token(runner.generation_path(enrollment))
    except (runner.ValidationError, OSError) as error:
        return {**refused, "reason": "generation_changed",
                "error_code": str(error) if isinstance(error, runner.ValidationError) else "execution_io_unavailable"}
    return {"schema_version": 1, "applicable": True, "reason": "current", "changed_paths": [],
             "head_advanced": runner.git(root, "rev-parse", "HEAD").decode().strip() != record["head"],
             "generation_current": token is None or token["snapshot_id"] == snapshot_id, **scope}


def managed_action(action, *, worktree, cycle, policy_path, check_ids=None, snapshot_id=None, request_id=None,
                   selection_pin=None, paths=None, **_):
    """The lifecycle's only entry point; every result is advisory and bounded."""
    if not _admitted(policy_path):
        return {"status": "disabled", "advisory": True}
    try:
        if action == "validate":
            return _validate(worktree, cycle, check_ids, request_id, selection_pin)
        if action == "selection":
            return _selection(worktree, cycle)
        if action == "applicability":
            return _applicability(worktree, cycle, snapshot_id, paths)
        if action in LEGACY_STATUS:
            # This owner enrolls nothing and queues nothing; the lifecycle keeps its legacy route.
            bound = LEGACY_STATUS[action] == "legacy_enrolled" and _bound(worktree, cycle) is not None
            return {"schema_version": 1, "status": "legacy_enrolled" if bound else "not_enrolled",
                    "error_code": UNSUPPORTED, "advisory": True}
        return _unavailable(UNSUPPORTED)
    except runner.ValidationError as error:
        return _unavailable(str(error))
    except OSError:
        return _unavailable("execution_io_unavailable")
