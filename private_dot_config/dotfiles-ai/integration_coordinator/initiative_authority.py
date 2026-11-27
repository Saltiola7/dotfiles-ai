"""Immutable Initiative scope and the local approval boundary for Auto.

Callers supply a validated committed manifest and native policy/writer binding.
Review confirmation and live capability observation belong to those callers.
"""
from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
from functools import cache
import os
import stat
import time
from typing import TYPE_CHECKING

from . import core, initiative_controller as controller, lifecycle as l

if TYPE_CHECKING:
    from .initiative_ci import Policy


_WITHDRAWN = {"deferred", "rejected"}


def _repository(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = {"provider": "github", "origin": "https://github.com", "repository": value}
    return l.initiative_repository(value)


def material_snapshot(manifest: dict, selected: tuple[str, ...], blob: Callable[[str], str], *, commit: str,
                      manifest_path: str | None = None) -> dict:
    """Fingerprint each selected slice and its transitive material dependencies."""
    if not 1 <= len(selected) <= 256 or len(set(selected)) != len(selected):
        raise ValueError("initiative_population_invalid")
    statements = {item["id"]: item for item in manifest["statements"]}
    contexts = {item["id"]: item for item in manifest["contexts"]}
    slices = {item["id"]: item for item in manifest["slices"]}
    groups = {item["id"]: item for item in manifest["release_groups"]}
    if len(contexts) > 256 or len(slices) > 256:
        raise ValueError("initiative_population_invalid")
    if not set(selected) <= slices.keys():
        raise ValueError("initiative_slice_missing")
    coordinator = _repository(manifest["coordinator_repository"])
    material: dict[str, dict] = {}

    @cache
    def context_scope(identifier: str) -> tuple[str, bool]:
        context = contexts[identifier]
        dependencies = [context_scope(key) for key in context["depends_on"]]
        scope = {"id": identifier, "repository": _repository(context["repository"]),
                 "depends_on": context["depends_on"], "dependencies": [digest for digest, _ in dependencies]}
        clear = context["status"] not in _WITHDRAWN and all(clear for _, clear in dependencies)
        return l.digest(scope), clear

    @cache
    def artifact_blob(path: str) -> str | None:
        try:
            identity = blob(path)
        except FileNotFoundError:
            return None
        core._oid(identity)
        return identity

    @cache
    def slice_scope(identifier: str) -> dict:
        item = slices[identifier]
        dependencies = [slice_scope(key) for key in item["depends_on"]]
        source_statements = [statements[key] for key in item["requirements"]]
        requirements = [statement | {"disposition": "ready"} if statement["disposition"] == "delivered"
                        else statement for statement in source_statements]
        paths = set(item["artifacts"])
        for statement in requirements:
            paths.update(statement["artifacts"])
        artifacts = {path: artifact_blob(path) for path in sorted(paths)}
        context_digest, context_clear = context_scope(item["context"])
        release = groups[item["release_group"]]
        owner = item.get("execution_owner", "build")
        scope = {"id": identifier, "coordinator": coordinator, "context_digest": context_digest,
                 "requirements": requirements, "slice_artifacts": item["artifacts"], "artifacts": artifacts,
                 "owner": owner, "depends_on": item["depends_on"],
                 "dependencies": [dependency["scope_digest"] for dependency in dependencies],
                 "release_group": {"id": release["id"], "members": release["members"]}}
        clear = (manifest["state"] not in _WITHDRAWN and context_clear and item["state"] not in _WITHDRAWN
                 and release["state"] not in _WITHDRAWN
                 and bool(requirements) and bool(item["artifacts"])
                 and all(statement["disposition"] not in {"open", "blocked"} for statement in requirements)
                 and all(artifacts.values()) and all(dependency["clear"] for dependency in dependencies))
        entry = {"scope_digest": l.digest(scope), "depends_on": item["depends_on"].copy(),
                 "repository": _repository(contexts[item["context"]]["repository"]),
                 "clear": clear and (identifier not in selected or owner == "build")}
        material[identifier] = entry
        return entry

    for identifier in selected:
        slice_scope(identifier)
    if manifest_path is None:
        manifest_path = f"docs/initiatives/{manifest['id']}/MANIFEST.json"
    snapshot = {"schema_version": 1, "initiative_id": manifest["id"], "manifest_path": manifest_path, "source_commit": commit,
                "selected": list(selected), "slices": material}
    l.validate("initiative_snapshot", snapshot)
    return snapshot


def same_material(approved: dict, current: dict, slice_id: str) -> bool:
    """Allow unrelated revisions and progress while binding the full scope."""
    l.validate("initiative_snapshot", approved)
    l.validate("initiative_snapshot", current)
    before = approved["slices"].get(slice_id)
    after = current["slices"].get(slice_id)
    return (approved["initiative_id"] == current["initiative_id"] and approved["manifest_path"] == current["manifest_path"]
            and slice_id in approved["selected"]
            and before is not None and after is not None and before["clear"] and before == after)


def _snapshot_digest(snapshot: dict) -> str:
    return l.digest({"schema_version": 1, "kind": "initiative_snapshot", "value": snapshot})


def _reviewed_scope(snapshot: dict, binding: Mapping[str, object]) -> None:
    l.validate("initiative_snapshot", snapshot)
    for identifier in snapshot["selected"]:
        item = snapshot["slices"][identifier]
        if not item["clear"] or item["repository"] != binding["repository"]:
            raise ValueError("initiative_selected_scope_unavailable")


def _reviewed_repair_scope(snapshot: dict, proposal: dict) -> None:
    policy = proposal.get("repair_policy")
    if policy is not None and policy["writable_paths"].keys() - set(snapshot["selected"]):
        raise ValueError("initiative_repair_slice_scope_unapproved")


def grant_proposal(snapshot: dict, *, binding: dict, operator_id: str, approved_at: str, expires_at: str,
                   allowed_operations: tuple[str, ...], repair_limit: int, ci_policy: Policy | None = None,
                   repair_policy: l.InitiativeRepairPolicy | None = None) -> dict:
    """Prepare the complete scope for review by the authenticated operator."""
    binding = l.initiative_binding(binding)
    _reviewed_scope(snapshot, binding)
    proposal = {"schema_version": 1, "snapshot_digest": _snapshot_digest(snapshot), "binding": binding,
                "operator_id": operator_id, "approved_at": approved_at, "expires_at": expires_at,
                "allowed_operations": list(allowed_operations), "repair_limit": repair_limit}
    if ci_policy is None:
        if repair_policy is not None or repair_limit != 0:
            raise ValueError("initiative_repair_policy_required")
    else:
        from .initiative_ci import Policy

        if type(ci_policy) is not Policy:
            raise ValueError("initiative_ci_policy_invalid")
        proposal.update(schema_version=2, ci_policy=asdict(ci_policy),
                        repair_policy=l.initiative_repair_policy(repair_policy) if repair_policy is not None else None)
    l.validate("initiative_grant", proposal)
    _reviewed_repair_scope(snapshot, proposal)
    return proposal


def store_grant(custody: l.Custody, snapshot: dict, proposal: dict, *, expected_approval_digest: str) -> str:
    """Accept the exact proposal digest provided by the operator approval path."""
    l.validate("initiative_grant", proposal)
    _reviewed_scope(snapshot, proposal["binding"])
    _reviewed_repair_scope(snapshot, proposal)
    if (l.digest(proposal) != l.hex_value(expected_approval_digest)
            or _snapshot_digest(snapshot) != proposal["snapshot_digest"]):
        raise ValueError("initiative_approval_changed")
    if proposal["schema_version"] == 1 and proposal["repair_limit"] != 0:
        identity = l.digest({"schema_version": 1, "kind": "initiative_grant", "value": proposal})
        try:
            read_grant(custody, identity)
        except FileNotFoundError:
            raise ValueError("initiative_repair_policy_required") from None
        return identity
    custody.write("initiative_snapshot", snapshot)
    return custody.write("initiative_grant", proposal)


def read_grant(custody: l.Custody, identity: str) -> tuple[dict, dict]:
    proposal = custody.read("initiative_grant", identity)
    snapshot = custody.read("initiative_snapshot", l.hex_value(proposal["snapshot_digest"]))
    _reviewed_scope(snapshot, l.initiative_binding(proposal["binding"]))
    _reviewed_repair_scope(snapshot, proposal)
    return proposal, snapshot


def _mutation_stop(custody: l.Custody, identity: str, proposal: dict, binding: dict, now: str) -> str | None:
    if custody.optional_link("initiative_revocation", identity) is not None:
        return "initiative_grant_revoked"
    if not l.initiative_time(proposal["approved_at"]) <= l.initiative_time(now) < l.initiative_time(proposal["expires_at"]):
        return "initiative_grant_inactive"
    if proposal["binding"] != l.initiative_binding(binding):
        return "initiative_qualification_changed"
    return None


def _require_repair(proposal: dict, slice_id: str, attempt: int | None, repair_class: str | None,
                    qualification_digest: str | None, paths: tuple[str, ...]) -> None:
    if type(attempt) is not int or not 1 <= attempt <= proposal["repair_limit"]:
        raise ValueError("initiative_repair_limit_reached")
    policy = proposal.get("repair_policy")
    if policy is None:
        if repair_class is not None or qualification_digest is not None or paths:
            raise ValueError("initiative_repair_policy_unavailable")
        return
    if type(repair_class) is not str or repair_class not in policy["class_qualifications"]:
        raise ValueError("initiative_repair_class_unapproved")
    if qualification_digest != policy["class_qualifications"][repair_class]:
        raise ValueError("initiative_repair_qualification_changed")
    if type(paths) is not tuple:
        raise ValueError("initiative_repair_paths_unapproved")
    if repair_class == "source_fix":
        approved_paths = policy["writable_paths"].get(slice_id, ())
        if (not 1 <= len(paths) <= len(approved_paths)
                or any(type(path) is not str or path not in approved_paths for path in paths)
                or len(set(paths)) != len(paths)):
            raise ValueError("initiative_repair_paths_unapproved")
    elif paths:
        raise ValueError("initiative_repair_paths_unapproved")


def require_grant(custody: l.Custody, identity: str, *, binding: dict, current: dict, slice_id: str,
                  operation: str, now: str, repair_attempt: int | None = None,
                  repair_class: str | None = None, repair_qualification_digest: str | None = None,
                  repair_paths: tuple[str, ...] = ()) -> dict:
    """Recheck the exact live binding and material scope before an authorized effect."""
    proposal, approved = read_grant(custody, identity)
    stopped = _mutation_stop(custody, identity, proposal, binding, now)
    if stopped is not None:
        raise ValueError(stopped)
    if operation not in proposal["allowed_operations"]:
        raise ValueError("initiative_operation_unapproved")
    if operation == "repair":
        _require_repair(proposal, slice_id, repair_attempt, repair_class, repair_qualification_digest, repair_paths)
    if not same_material(approved, current, slice_id):
        raise ValueError("initiative_material_changed")
    return proposal


@contextmanager
def initiative_effect_lock(custody: l.Custody, grant_id: str, *, timeout: float = 2.0) -> Generator[None]:
    """Serialize the final bounded native effect and local revocation."""
    identity = l.hex_value(grant_id)
    if not 0 <= timeout <= 2.0:
        raise core.Invalid("initiative_effect_lock_timeout_invalid")
    directory = custody.directory / "initiative-locks"
    custody._directory(directory, True)
    name = l.digest({"kind": "initiative-effect-lock", "grant_digest": identity})
    path = directory / name
    descriptor = os.open(path, os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_RDWR, 0o600)
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.getuid() or opened.st_nlink != 1
                or stat.S_IMODE(opened.st_mode) != 0o600):
            raise core.Unavailable("initiative_effect_lock_invalid")
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise core.Unavailable("initiative_effect_lock_busy") from None
                time.sleep(0.01)
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise core.Unavailable("initiative_effect_lock_changed")
        yield
    finally:
        os.close(descriptor)


def revoke_grant(custody: l.Custody, identity: str, *, reason_digest: str, revoked_at: str) -> None:
    with initiative_effect_lock(custody, identity):
        proposal, _ = read_grant(custody, identity)
        if l.initiative_time(revoked_at) < l.initiative_time(proposal["approved_at"]):
            raise ValueError("initiative_revocation_time_invalid")
        record = custody.write("initiative_revocation", {"grant_digest": identity, "reason_digest": reason_digest,
                                                           "revoked_at": revoked_at})
        custody.link("initiative_revocation", identity, record)


class CustodyAuthority:
    """Supply controller authority from retained approval and fresh native observations."""

    def __init__(self, custody: l.Custody, *, current_binding: Callable[[], dict], current_scope: Callable[[str], dict],
                 plan: Callable[[str], controller.Launch], prior_delivery: Callable[[controller.Approval, str, dict], bool],
                 clock: Callable[[], str]) -> None:
        self.custody, self.current_binding, self.current_scope = custody, current_binding, current_scope
        self.plan, self.prior_delivery, self.clock = plan, prior_delivery, clock

    def _stored(self, identity: str) -> tuple[dict, dict]:
        try:
            return read_grant(self.custody, identity)
        except ValueError:
            raise core.Invalid("initiative_approval_custody_invalid") from None

    @staticmethod
    def _review(identity: str, proposal: dict, snapshot: dict, stop: str | None) -> controller.Approval:
        binding = proposal["binding"]
        repository = binding["repository"]
        target = controller.Target(repository["origin"], repository["repository"], binding["target_ref"])
        slices = tuple(controller.Slice(key, tuple(snapshot["slices"][key]["depends_on"])) for key in snapshot["selected"])
        return controller.Approval(identity, target, binding["controller_digest"], binding["writer_digest"], slices, stop)

    def _live_stop(self, identity: str, proposal: dict) -> str | None:
        try:
            stop = _mutation_stop(self.custody, identity, proposal, self.current_binding(), self.clock())
        except (ValueError, OSError, core.Unavailable, core.Ambiguous, core.Conflict):
            return "initiative_authority_unavailable"
        if stop is None and "launch" not in proposal["allowed_operations"]:
            return "initiative_operation_unapproved"
        return stop

    def approval(self, grant_id: str) -> controller.Approval:
        proposal, snapshot = self._stored(grant_id)
        return self._review(grant_id, proposal, snapshot, self._live_stop(grant_id, proposal))

    def _reviewed(self, approval: controller.Approval) -> tuple[dict, dict]:
        proposal, snapshot = self._stored(approval.grant_id)
        if approval != self._review(approval.grant_id, proposal, snapshot, approval.mutation_stop):
            raise core.Conflict("initiative_approval_subject_changed")
        return proposal, snapshot

    def preflight(self, approval: controller.Approval, slice_id: str) -> controller.Launch | None:
        proposal, snapshot = self._reviewed(approval)
        if self._live_stop(approval.grant_id, proposal) is not None:
            raise core.Unavailable("initiative_execution_authority_stopped")
        if slice_id not in snapshot["selected"]:
            raise core.Conflict("initiative_launch_slice_unapproved")
        try:
            current = self.current_scope(slice_id)
            matches = same_material(snapshot, current, slice_id)
        except FileNotFoundError:
            return None
        except ValueError:
            raise core.Unavailable("initiative_current_scope_unavailable") from None
        return self.plan(slice_id) if matches else None

    def dependency_delivered(self, approval: controller.Approval, slice_id: str) -> bool:
        _, snapshot = self._reviewed(approval)
        scope = snapshot["slices"].get(slice_id)
        return (scope is not None and slice_id not in snapshot["selected"]
                and self.prior_delivery(approval, slice_id, scope) is True)
