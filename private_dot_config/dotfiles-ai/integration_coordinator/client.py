"""Local enrolled client; the existing lifecycle owner supplies authentication.

Dispatch is a wakeup. Only an observed durable ledger ticket acknowledges admission.
This module never selects, exports, installs or reads a credential.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
import urllib.parse

from . import core as c
from . import runtime as r
from . import github as g
from . import controller as h


@dataclass(frozen=True, slots=True)
class Status:
    ledger_head: str
    ticket: r.Ticket
    obligation: r.Obligation

    def report(self) -> dict[str, object]:
        return {"status": self.ticket.state.value, "ticket_handle": self.ticket.handle,
                "obligation_handle": self.obligation.handle, "generation": self.ticket.generation,
                "repository": self.ticket.source.repository, "pr_number": self.ticket.source.pr_number,
                "head": self.ticket.current_head, "base": self.ticket.base,
                "tested_oid": None if self.ticket.candidate is None else self.ticket.candidate.tested_oid,
                "repair_count": self.obligation.repair_count,
                "failure_digest": self.ticket.failure_digest,
                "merge_oid": None if self.ticket.delivery is None else self.ticket.delivery.merge_oid}


@dataclass(frozen=True, slots=True)
class VerifiedOutcome:
    ledger_head: str
    ticket: r.Ticket
    obligation: r.Obligation
    mapping: tuple[c.CommitPair, ...]
    merge_oid: str
    landed_base: str
    target_head: str
    merged_at: str
    verification_digest: str


class LocalClient:
    """Consume the existing validated coordinator table and the shared wire policy."""

    def __init__(self, transport: g.Transport, coordinator: Mapping[str, object],
                 proof: g.ProofPort | None = None) -> None:
        allowed = {"schema_version", "enabled", "protocol_version", "strategy", "remote_repository",
                   "target_ref", "control_ref", "policy_path", "policy_digest", "guarded_refresh"}
        required = allowed - {"strategy", "guarded_refresh"}
        if (not required <= coordinator.keys() or set(coordinator) - allowed
                or type(coordinator["schema_version"]) is not int or coordinator["schema_version"] != 1
                or type(coordinator["protocol_version"]) is not int or coordinator["protocol_version"] != 2
                or coordinator["enabled"] is not True or coordinator.get("strategy", "rebase") != "rebase"
                or type(coordinator.get("guarded_refresh", False)) is not bool):
            raise c.Unavailable("local_coordinator_not_enrolled")
        self.transport = transport
        self.proof = proof
        self.repository = g._text(coordinator["remote_repository"], 201)
        c._repository(self.repository)
        self.target_ref = g._text(coordinator["target_ref"], 260)
        self.control_ref = g._text(coordinator["control_ref"], 260)
        self.policy_path = g._text(coordinator["policy_path"], 512)
        parts = PurePosixPath(self.policy_path).parts
        if (not parts or self.policy_path.startswith("/") or any(part in {".", "..", ".dbsctr"} for part in parts)
                or not self.policy_path.endswith(".json") or str(PurePosixPath(self.policy_path)) != self.policy_path):
            raise c.Invalid("local_policy_path")
        self.policy_digest = g._digest(coordinator["policy_digest"])
        self.guarded_refresh = coordinator.get("guarded_refresh", False) is True
        self._loaded: tuple[h.HostedConfig, g.GitHub] | None = None

    def _get(self, path: str) -> object:
        try:
            return self.transport.request("GET", "repos/" + self.repository + ("/" + path if path else ""))
        except g.ApiFailure:
            raise c.Unavailable("local_native_read_unavailable") from None

    def configuration(self) -> tuple[h.HostedConfig, g.GitHub]:
        if self._loaded is not None:
            return self._loaded
        repository = g._object(self._get(""))
        default = g._text(repository.get("default_branch"), 256)
        if (repository.get("full_name") != self.repository or self.target_ref != "refs/heads/" + default
                or self.control_ref in {self.target_ref, "refs/heads/main", "refs/heads/master"}):
            raise c.Unavailable("local_native_target_changed")
        path = urllib.parse.quote(self.policy_path, safe="/")
        response = g._object(self._get("contents/" + path + "?ref=" + urllib.parse.quote(default, safe="")))
        size = response.get("size")
        if (response.get("type") != "file" or response.get("encoding") != "base64"
                or type(size) is not int or not 0 < size <= h.POLICY_LIMIT):
            raise c.Unavailable("local_policy_unqualified")
        content = response.get("content")
        if not isinstance(content, str) or len(content) > 2 * h.POLICY_LIMIT:
            raise c.Invalid("local_policy_size")
        try:
            raw = base64.b64decode("".join(content.split()), validate=True)
        except (ValueError, binascii.Error):
            raise c.Invalid("local_policy_encoding") from None
        if len(raw) != size:
            raise c.Unavailable("local_policy_size_changed")
        config = h.parse_config(raw)
        if not config.enabled or config.enrollment is None or config.check_plan is None:
            raise c.Unavailable("remote_coordinator_not_enrolled")
        enrollment = config.enrollment
        if (enrollment.repository != self.repository or enrollment.repository_id != repository.get("id")
                or enrollment.default_branch != default
                or self.control_ref != "refs/heads/" + enrollment.control_branch
                or enrollment.policy_digest != self.policy_digest or h.policy_identity(config) != self.policy_digest):
            raise c.Unavailable("local_remote_policy_mismatch")
        native = g.GitHub(self.transport, enrollment, self.proof, config.check_plan,
                          policy_path=self.policy_path)
        # Contents API can follow repository symlinks. Independently require the
        # exact regular Git blob at one actual default-branch commit.
        head = native.ref(default)
        if native.file_at(head, self.policy_path) != raw:
            raise c.Unavailable("local_policy_source_changed")
        self._loaded = config, native
        return self._loaded

    def submit(self, request: dict[str, object]) -> dict[str, object]:
        if set(request) != {"schema_version", "policy_digest", "ticket", "obligation"}:
            raise c.Invalid("source_request_fields")
        raw = c._canonical(request)
        if len(raw) > h.DISPATCH_LIMIT or request.get("schema_version") != 2 or type(request.get("schema_version")) is not int:
            raise c.Invalid("source_request_limit")
        ticket = r.decode("ticket", c._canonical(request["ticket"]))
        obligation = r.decode("obligation", c._canonical(request["obligation"]))
        if not isinstance(ticket, r.Ticket) or not isinstance(obligation, r.Obligation):
            raise c.Invalid("source_request_types")
        config, _native = self.configuration()
        assert config.enrollment is not None and config.workflow_id is not None
        if (request["policy_digest"] != self.policy_digest or ticket.source.repository != self.repository
                or ticket.obligation_handle != obligation.handle or ticket.state != r.State.REQUESTED
                or ticket.guarded_refresh and not self.guarded_refresh
                or ticket.delivery_mode == "admin" and not config.enrollment.review_exception):
            raise c.Conflict("source_request_binding")
        try:
            actor = g._integer(g._object(self.transport.request("GET", "user")).get("id"))
        except g.ApiFailure:
            raise c.Unavailable("local_requester_unavailable") from None
        if actor not in config.requester_ids or ticket.requester_digest != r.requester_digest(self.repository, actor):
            raise c.Unavailable("local_requester_not_enrolled")
        try:
            self.transport.request("POST", f"repos/{self.repository}/actions/workflows/{config.workflow_id}/dispatches",
                {"ref": config.enrollment.default_branch, "inputs": {"request": raw.decode("utf-8")}})
        except g.ApiFailure:
            raise c.Unavailable("local_dispatch_rejected") from None
        return {"status": "unadmitted", "dispatch": "accepted", "ticket_handle": ticket.handle,
                "obligation_handle": obligation.handle}

    def status(self, ticket_handle: str, obligation_handle: str) -> Status | None:
        c._handle(ticket_handle)
        c._handle(obligation_handle)
        _config, native = self.configuration()
        native.observe_policy()
        first = native.ref(native.enrollment.control_branch)
        payload = native.file_at(first, "integration/v2/obligations/" + obligation_handle + ".json")
        if payload is None:
            return None
        obligation = r.decode("obligation", payload)
        assert isinstance(obligation, r.Obligation)
        if obligation.handle != obligation_handle:
            raise c.Unavailable("local_obligation_identity")
        head, files = native.read_control(tuple(dict.fromkeys((ticket_handle, obligation.current_ticket))))
        if head != first:
            raise c.Conflict("local_ledger_moved")
        view = r.load_snapshot(files)
        if (view.target.repository != native.enrollment.repository
                or view.target.default_branch != native.enrollment.default_branch
                or view.target.root_oid != native.enrollment.root_oid
                or view.target.policy_digest != native.enrollment.policy_digest):
            raise c.Unavailable("local_ledger_enrollment_changed")
        selected = view.obligation(obligation_handle)
        if selected != obligation:
            raise c.Unavailable("local_obligation_changed")
        original = view.lookup_ticket(ticket_handle)
        current = view.lookup_ticket(obligation.current_ticket)
        if original.obligation_handle != obligation_handle or current.obligation_handle != obligation_handle:
            raise c.Unavailable("local_ticket_obligation_mismatch")
        return Status(head, current, selected)

    def verify_delivered(self, ticket_handle: str, obligation_handle: str) -> VerifiedOutcome:
        status = self.status(ticket_handle, obligation_handle)
        if status is None or status.ticket.state != r.State.DELIVERED:
            raise c.Unavailable("local_delivery_pending")
        ticket = status.ticket
        if ticket.delivery is None or ticket.projection is None or ticket.candidate is None or self.proof is None:
            raise c.Unavailable("local_delivery_proof_missing")
        _config, native = self.configuration()
        observed = native.observe_pr(ticket.source.pr_number)
        if (not observed.merged or observed.merge_oid != ticket.delivery.merge_oid
                or observed.head != ticket.projection.head or observed.merged_at is None):
            raise c.Unavailable("local_native_delivery_changed")
        target = native.ref(native.enrollment.default_branch)
        if self.proof.excludes_root(ticket.delivery.merge_oid, (target,)):
            raise c.Unavailable("local_delivery_not_contained")
        mapping = self.proof.prove_delivery(ticket.source, ticket.projection, ticket.delivery.merge_oid)
        if mapping != ticket.delivery.mapping:
            raise c.Unavailable("local_delivery_correspondence_changed")
        prior = ticket.candidate.base
        introductions: list[str] = []
        for pair in mapping:
            commit = native.git_commit(pair.landed)
            if commit.parents != (prior,):
                raise c.Unavailable("local_landed_interval_changed")
            introductions.append(g.verify_introduction(native.pages("commits/" + pair.landed + "/pulls", limit=100),
                                                       self.repository, ticket.source.pr_number, observed.merged_at))
            prior = pair.landed
        if native.observe_pr(ticket.source.pr_number) != observed:
            raise c.Unavailable("local_native_delivery_changed")
        evidence = hashlib.sha256(c._canonical({"ledger_head": status.ledger_head,
            "delivery": c.identity(ticket.delivery), "target": target, "introductions": introductions,
            "mapping": [c._data(pair) for pair in mapping]})).hexdigest()
        return VerifiedOutcome(status.ledger_head, ticket, status.obligation, r.original_to_landed(ticket),
                               ticket.delivery.merge_oid, ticket.candidate.base, target, observed.merged_at, evidence)
