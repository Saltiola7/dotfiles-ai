"""Qualified local original-task recovery over the shared coordinator scheduler.

TaskBinding is output from the paired lifecycle helper's live record, physical
checkout and operator-role validation. It is never accepted from a JSON file or
used as human authentication. Credentials remain owned by the supplied LocalClient.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import hashlib
import os
import secrets
import subprocess
import sys
import uuid
from typing import Protocol

from . import core as c, runtime as r, lifecycle as l, github as g, controller as h
from .client import Status


@dataclass(frozen=True, slots=True)
class TaskBinding:
    obligation_handle: str
    original_task_digest: str
    cycle_custody_digest: str

    def __post_init__(self) -> None:
        c._handle(self.obligation_handle)
        c._digest(self.original_task_digest)
        c._digest(self.cycle_custody_digest)


class OperatorClient(Protocol):
    @property
    def transport(self) -> g.Transport: ...
    @property
    def repository(self) -> str: ...
    def configuration(self) -> tuple[h.HostedConfig, h.Adapter]: ...
    def status(self, ticket_handle: str, obligation_handle: str) -> Status | None: ...


def _hash(value: object) -> str:
    return hashlib.sha256(c._canonical(value)).hexdigest()


def _process_context() -> str:
    """Bind liveness queries to the same boot and PID namespace, or refuse.

    A PID absent in a different host/container namespace is not proof that the
    original process ended. Only a digest enters private custody; no raw boot ID
    or process namespace is published in the ledger.
    """
    try:
        if sys.platform == "linux":
            with open("/proc/sys/kernel/random/boot_id", "rb") as stream:
                raw = stream.read(128)
            boot = uuid.UUID(raw.decode("ascii").strip()).hex
            namespace = os.stat("/proc/self/ns/pid")
            return _hash({"system": "linux", "boot": boot, "namespace_device": namespace.st_dev,
                          "namespace_inode": namespace.st_ino})
        if sys.platform == "darwin":
            result = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"],
                capture_output=True, text=True, timeout=5,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"})
            if result.returncode or result.stderr or len(result.stdout) > 128:
                raise c.Unavailable("operator_process_authority_unavailable")
            return _hash({"system": "darwin", "boot": uuid.UUID(result.stdout.strip()).hex})
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        raise c.Unavailable("operator_process_authority_unavailable") from None
    raise c.Unavailable("operator_process_authority_unavailable")


def _task_custody(binding: TaskBinding) -> str:
    return _hash({"cycle_custody": binding.cycle_custody_digest, "process_context": _process_context()})


def _pid_dead(pid: int) -> bool:
    c._integer(pid)
    try:
        os.kill(pid, 0)
    except OSError as error:
        return error.errno == errno.ESRCH
    return False


def _scope(record: Mapping[str, object]) -> str:
    keys = ("repository", "root_oid", "policy_digest", "obligation_handle", "ticket_handle", "generation",
            "source_digest", "grant_digest", "obligation_digest", "original_task_digest", "task_custody_digest", "requester_id")
    return _hash({key: record[key] for key in keys})


def _human(client: OperatorClient, config: h.HostedConfig) -> int:
    try:
        user = g._object(client.transport.request("GET", "user"))
    except g.ApiFailure:
        raise c.Unavailable("operator_identity_unavailable") from None
    actor = g._integer(user.get("id"))
    if (user.get("type") != "User" or config.enrollment is None
            or actor not in config.enrollment.mutator_user_ids or actor not in config.requester_ids):
        raise c.Unavailable("operator_human_not_enrolled")
    return actor


def _private_scope(store: l.Custody, binding: TaskBinding, status: Status) -> tuple[str, dict[str, object]]:
    grant_digest = status.obligation.grant_digest
    try:
        grant = store.read("grant", grant_digest)
        obligation_digest = l.hex_value(grant["obligation_digest"])
        obligation = store.read("obligation", obligation_digest)
        if (obligation["handle"] != binding.obligation_handle
                or status.ticket.obligation_handle != binding.obligation_handle
                or obligation["original_task_digest"] != binding.original_task_digest
                or grant["scope_digest"] != obligation["scope_digest"]
                or grant["record_digest"] != obligation["record_digest"]):
            raise c.Unavailable("operator_original_task_mismatch")
        if "operator_resume" not in l.string_list(grant["allowed_operations"]):
            raise c.Unavailable("operator_not_granted")
        if store.revoked(grant_digest):
            raise c.Unavailable("operator_grant_revoked")
        link = store.linked("revision_link", status.ticket.handle)
        revision = store.read("revision", l.hex_value(link["revision_digest"]))
        source_value = store.read("source", l.hex_value(link["source_custody_digest"]))
        source = r.decode("source", l.canonical(source_value["descriptor"]))
        if (link["ticket_handle"] != status.ticket.handle or revision["grant_digest"] != grant_digest
                or revision["obligation_digest"] != obligation_digest or source != status.ticket.source
                or source_value["record_digest"] != revision["child_record_digest"]):
            raise c.Unavailable("operator_revision_custody_changed")
        if revision["authorization_digest"] is not None:
            authorization_digest = l.hex_value(revision["authorization_digest"])
            authorization = store.read("authorization", authorization_digest)
            if authorization["grant_digest"] != grant_digest or authorization["obligation_digest"] != obligation_digest:
                raise c.Unavailable("operator_revision_authority_changed")
            store.verify_approval({"schema_version": 2, "method": "integration_grant",
                "launch_digest": authorization["launch_digest"], "authorization_digest": authorization_digest,
                "authorized_at": authorization["authorized_at"]}, l.text(revision["child_cycle_id"]))
        return obligation_digest, grant
    except (OSError, ValueError):
        raise c.Unavailable("operator_private_custody_unavailable") from None


class OperationCustody:
    """Read-only old-invocation proof; neither age nor unchanged refs is no-effect."""

    def __init__(self, client: OperatorClient, store: l.Custody, binding: TaskBinding,
                 config: h.HostedConfig, status: Status) -> None:
        self.store, self.binding, self.config, self.status = store, binding, config, status
        self.hosted = h.NativeHost.for_reconciliation(client.transport, config)

    def quiescent(self, invocation: r.InvocationIdentity) -> bool:
        if isinstance(invocation, r.Invocation):
            return self.hosted.quiescent(invocation)
        try:
            record = self.store.read("operator", invocation.custody_digest)
            enrollment = self.config.enrollment
            assert enrollment is not None
            if (record["requester_id"] != invocation.requester_id or record["invocation_id"] != invocation.invocation_id
                    or record["scope_digest"] != invocation.scope_digest or _scope(record) != invocation.scope_digest
                    or record["repository"] != enrollment.repository or record["root_oid"] != enrollment.root_oid
                    or record["policy_digest"] != enrollment.policy_digest
                    or record["obligation_handle"] != self.binding.obligation_handle
                    or record["original_task_digest"] != self.binding.original_task_digest
                    or record["ticket_handle"] != self.status.ticket.handle
                    or record["grant_digest"] != self.status.obligation.grant_digest
                    or record["source_digest"] != c.identity(self.status.ticket.source)
                    or record["task_custody_digest"] != _task_custody(self.binding)):
                raise c.Unavailable("operator_prior_custody_unbound")
            generation = record["generation"]
            pid = record["pid"]
            if type(generation) is not int or not 0 < generation <= self.status.ticket.generation or type(pid) is not int:
                raise c.Unavailable("operator_prior_process_unbound")
            if self.store.revoked(self.status.obligation.grant_digest):
                raise c.Unavailable("operator_grant_revoked")
            return _pid_dead(pid)
        except (OSError, ValueError):
            raise c.Unavailable("operator_prior_custody_unavailable") from None


def resume(client: OperatorClient, store: l.Custody, binding: TaskBinding,
           expected_handle: str, expected_generation: int) -> h.Report:
    """Use helper-qualified original task and the existing native client only."""
    c._require(type(binding) is TaskBinding, "operator_task_binding")
    c._handle(expected_handle)
    c._integer(expected_generation)
    config, native = client.configuration()
    if not config.enabled or config.enrollment is None or client.repository != config.enrollment.repository:
        raise c.Unavailable("operator_coordinator_not_enrolled")
    if h.policy_identity(config) != config.enrollment.policy_digest:
        raise c.Unavailable("operator_policy_changed")
    actor = _human(client, config)
    status = client.status(expected_handle, binding.obligation_handle)
    if (status is None or status.ticket.handle != expected_handle or status.ticket.generation != expected_generation
            or status.ticket.state not in r.ACTIVE):
        raise c.Conflict("operator_subject_not_active")
    obligation_digest, _grant = _private_scope(store, binding, status)
    if (native.enrollment != config.enrollment or native.plan != config.check_plan
            or native.observe_policy().digest != config.enrollment.native_guard_digest):
        raise c.Unavailable("operator_native_policy_changed")
    head, files = native.read_control((expected_handle,))
    view = r.load_snapshot(files)
    ticket = view.ticket(expected_handle)
    enrollment = config.enrollment
    if ((view.target.repository, view.target.default_branch, view.target.root_oid, view.target.policy_digest)
            != (enrollment.repository, enrollment.default_branch, enrollment.root_oid, enrollment.policy_digest)
            or view.target.active != expected_handle or view.target.generation != expected_generation
            or ticket.source != status.ticket.source or view.obligation(binding.obligation_handle) != status.obligation):
        raise c.Conflict("operator_slot_changed")
    if store.revoked(status.obligation.grant_digest):
        raise c.Unavailable("operator_grant_revoked")
    record: dict[str, object] = {"obligation_digest": obligation_digest, "grant_digest": status.obligation.grant_digest,
        "original_task_digest": binding.original_task_digest, "task_custody_digest": _task_custody(binding),
        "repository": enrollment.repository, "root_oid": enrollment.root_oid, "policy_digest": enrollment.policy_digest,
        "obligation_handle": binding.obligation_handle, "ticket_handle": expected_handle, "generation": expected_generation,
        "source_digest": c.identity(ticket.source), "requester_id": actor, "invocation_id": secrets.token_hex(16),
        "pid": os.getpid(), "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    record["scope_digest"] = _scope(record)
    custody_digest = store.write("operator", record)
    invocation = r.OperatorInvocation(actor, l.hex_value(record["invocation_id"], tuple(range(16, 65))),
                                      custody_digest, l.hex_value(record["scope_digest"]))
    authority = h.OperatorAuthority(invocation, _hash({"custody": custody_digest, "ledger_head": head}),
                                    expected_handle, expected_generation)
    current = Status(head, ticket, view.obligation(binding.obligation_handle))
    return h.advance(config, authority, OperationCustody(client, store, binding, config, current), native,
                     (expected_handle, binding.obligation_handle))
