"""Managed owner for lifecycle-requested validation. Every action is advisory.

The lifecycle helper selects this module and calls ``managed_action`` after its
own policy admission. This module adds no scheduler, watcher, enrollment writer
or gate authority: it resolves the one enrollment explicitly bound to the task
and delegates to the ordinary request owner.
"""
from __future__ import annotations

from pathlib import Path
import uuid

from . import checkpoints, runner

UNSUPPORTED = "owner_action_unsupported"
LEGACY_STATUS = {"enroll": "not_enrolled", "checkpoint": "legacy_enrolled"}
MAX_CHANGED_PATHS = 256
MAX_FAILED_TEST_IDS = 200


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


def _validate(worktree, cycle, check_ids, request_id):
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
    if check_ids:
        request["checks"] = list(check_ids)
    result = runner.run_request(request)
    if result["status"] in {"unavailable", "interrupted", "disabled"}:
        return {**_unavailable(result.get("error_code", "enrollment_inactive")), "request_id": result["request_id"]}
    return {
        "schema_version": 1,
        "status": "pending" if "error_code" in result or any(item["status"] == "pending" for item in result["observations"]) else "completed",
        "request_id": result["request_id"], "snapshot_id": result["snapshot_id"], "generation": result["generation"],
        "selection_complete": result["selection_complete"], "pending_checks": result["pending_checks"],
        "new_execution": result["new_execution"],
        "observations": [{"id": item["id"], "check_id": item["check_id"], "status": item["status"],
                          "snapshot_id": item["snapshot_id"], "executed": item["executed"],
                          "failed_test_ids": item["runtime"].get("test_identity", {}).get("failed_test_ids", [])[:MAX_FAILED_TEST_IDS],
                          "diagnostic_codes": item["diagnostic_codes"]} for item in result["observations"]],
        **({"error_code": result["error_code"]} if "error_code" in result else {}),
        "advisory": True,
    }


def _applicability(worktree, cycle, snapshot_id):
    """A receipt is evidence about captured content; a newer request alone does not retire it."""
    refused = {"schema_version": 1, "applicable": False, "changed_paths": []}
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
                   if item.get("kind") == "completed" and item.get("result", {}).get("snapshot_id") == snapshot_id), None)
    if record is None:
        return {**refused, "reason": "snapshot_unknown"}
    try:
        files = next((item.get("files") for item in _retained(state, "snapshot-") if item.get("id") == snapshot_id), None)
        current = runner.inventory(root, record["patterns"])
    except runner.ValidationError as error:
        # Content that cannot be inventoried is not demonstrably unchanged.
        return {**refused, "reason": "source_changed", "changed_paths_complete": False, "error_code": str(error)}
    if runner.digest(current) != record["files_digest"]:
        changed = None if not isinstance(files, dict) else sorted(
            name for name in set(current) | set(files) if current.get(name) != files.get(name))
        return {**refused, "reason": "source_changed", "changed_paths": (changed or [])[:MAX_CHANGED_PATHS],
                "changed_paths_complete": changed is not None and len(changed) <= MAX_CHANGED_PATHS}
    try:
        # A generation record that cannot be read is not a lineage this owner will vouch for.
        token = runner.generation_token(state / ("current-" + runner.digest({
            "repository": enrollment["repository_id"], "worktree": str(root)}) + ".json"))
    except runner.ValidationError as error:
        return {**refused, "reason": "generation_changed", "error_code": str(error)}
    return {"schema_version": 1, "applicable": True, "reason": "current", "changed_paths": [],
            "head_advanced": runner.git(root, "rev-parse", "HEAD").decode().strip() != record["head"],
            "generation_current": token is None or token["snapshot_id"] == snapshot_id}


def managed_action(action, *, worktree, cycle, policy_path, check_ids=None, snapshot_id=None, request_id=None, **_):
    """The lifecycle's only entry point; every result is advisory and bounded."""
    if not _admitted(policy_path):
        return {"status": "disabled", "advisory": True}
    try:
        if action == "validate":
            return _validate(worktree, cycle, check_ids, request_id)
        if action == "applicability":
            return _applicability(worktree, cycle, snapshot_id)
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
