"""The byte-pinned, owner-private process that supplies live fixture evidence."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import cast

from . import core, forgejo, forgejo_ci as ci, forgejo_merge as merge, lifecycle as l, runtime as r
from .initiative_controller import Activation
from .initiative_forgejo import Fixture
from .initiative_repair import Failure, INFRASTRUCTURE, Request


_PROVIDER_TIMEOUT = 25
_MERGE_PRECONDITIONS_TIMEOUT = 180 + 2  # Owner broker budget plus relay overhead.


class Bridge:
    """Use an enrolled local fixture owner; repository bytes cannot select its program."""

    def __init__(self, custody: l.Custody, fixture: Fixture) -> None:
        self.custody, self.fixture = custody, fixture
        self.binding = fixture.binding

    def _call(self, operation: str, **request: object) -> object:
        try:
            program = self.custody._read(self.custody.directory / "forgejo-fixture-provider.py")
            if sha256(program).hexdigest() != self.fixture.bridge_digest:
                raise core.Conflict("initiative_forgejo_bridge_changed")
            invocation = l.canonical({"schema_version": 1, "fixture_digest": self.fixture.digest,
                                      "binding": asdict(self.binding), "target_ref": self.fixture.target_ref,
                                      "operation": operation, "request": request})
            if len(invocation) > l.MAX_PRIVATE_BYTES:
                raise core.Invalid("initiative_forgejo_bridge_request_unbounded")
            with tempfile.TemporaryDirectory(prefix="forgejo-fixture-") as temp, tempfile.TemporaryFile() as output:
                executable = Path(temp) / "provider.py"
                executable.write_bytes(program)
                timeout: float = _PROVIDER_TIMEOUT
                if operation == "merge_preconditions":
                    now = _active_expiry(request.get("expires_at"))
                    expires_at = cast(int, request["expires_at"])
                    timeout = min(expires_at, now + _MERGE_PRECONDITIONS_TIMEOUT) - now
                elif operation == "retry_submit":
                    expires_at = int(l.initiative_time(request.get("expires_at")).timestamp())
                    timeout = min(_PROVIDER_TIMEOUT, expires_at - _active_expiry(expires_at))
                result = subprocess.run([sys.executable, "-I", "-B", str(executable)], input=invocation,
                    cwd=self.custody.directory, env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
                                                     "LC_ALL": "C", "PYTHONIOENCODING": "utf-8"},
                    stdout=output, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
                output.seek(0)
                data = output.read(l.MAX_PRIVATE_BYTES + 1)
            if result.returncode or len(data) > l.MAX_PRIVATE_BYTES:
                raise core.Unavailable("initiative_forgejo_bridge_response_unavailable")
            value = l.object_value(json.loads(data, object_pairs_hook=l.no_duplicates))
            if (set(value) != {"schema_version", "fixture_digest", "result"}
                    or type(value["schema_version"]) is not int or value["schema_version"] != 1
                    or value["fixture_digest"] != self.fixture.digest):
                raise core.Invalid("initiative_forgejo_bridge_response_unbound")
            if operation == "merge_preconditions":
                _active_expiry(request.get("expires_at"))
            elif operation == "retry_submit":
                _active_expiry(int(l.initiative_time(request.get("expires_at")).timestamp()))
            return value["result"]
        except (OSError, ValueError, subprocess.SubprocessError):
            raise core.Unavailable("initiative_forgejo_bridge_unavailable") from None

    def attest(self) -> None:
        fixture = self.fixture
        expected = {"private": True, "actor_id": fixture.target.actor_id, "operator_id": fixture.operator_id,
                    "repository_id": self.binding.repository_id, "role": "ordinary",
                    "root_oid": fixture.root_oid, "guard_digest": fixture.target.guard_digest,
                    "dispatcher_digest": fixture.target.dispatcher_digest,
                    "policy_digest": fixture.plan.policy_digest, "check_plan_digest": core.identity(fixture.plan),
                    "version": self.binding.version}
        if l.canonical(self._call("attest")) != l.canonical(expected):
            raise core.Conflict("initiative_forgejo_native_enrollment_changed")
        target = self.ref(self.binding, fixture.target_ref)
        if target is None or self.is_ancestor(self.binding, fixture.root_oid, target) is not True:
            raise core.Conflict("initiative_forgejo_root_unproved")

    def _binding(self, binding: forgejo.Binding) -> None:
        if self.binding != binding:
            raise core.Conflict("initiative_forgejo_bridge_binding_changed")

    def ref(self, binding: forgejo.Binding, ref: str) -> str | None:
        self._binding(binding)
        forgejo._branch(ref)
        value = self._call("ref", ref=ref)
        if value is not None:
            core._oid(value)
        return value

    def commit(self, binding: forgejo.Binding, oid: str) -> merge.RawCommit:
        self._binding(binding)
        core._oid(oid)
        value = l.object_value(self._call("commit", oid=oid))
        if set(value) != {"oid", "parents", "tree"} or value["oid"] != oid:
            raise core.Conflict("initiative_forgejo_bridge_object_changed")
        parents = tuple(l.string_list(value["parents"]))
        core._oids(parents, 64)
        core._oid(value["tree"])
        return merge.RawCommit(oid, parents, value["tree"])

    def is_ancestor(self, binding: forgejo.Binding, ancestor: str, descendant: str) -> bool:
        self._binding(binding)
        core._oid(ancestor)
        core._oid(descendant)
        core._require(len(ancestor) == len(descendant), "mixed_oid_formats")
        value = self._call("ancestor", ancestor=ancestor, descendant=descendant)
        if type(value) is not bool:
            raise core.Invalid("initiative_forgejo_bridge_ancestry_unproved")
        return value

    def push(self, checkout: str, ref: str, oid: str, expires_at: int) -> None:
        forgejo._branch(ref)
        core._oid(oid)
        _active_expiry(expires_at)
        if ref == self.fixture.target_ref:
            raise core.Invalid("initiative_forgejo_bridge_push_scope")
        if self._call("push_feature", checkout=checkout, ref=ref, oid=oid,
                      expected_old=None, expires_at=expires_at) != oid:
            raise core.Ambiguous("initiative_forgejo_bridge_push_unproved")

    def request(self, method: str, path: str, body: dict[str, object] | None = None, *,
                expires_at: int | None = None, expected_base: str | None = None,
                expected_head: str | None = None) -> forgejo.Response:
        prefix = f"/api/v1/repos/{self.binding.repository}/"
        suffix = path.removeprefix(prefix)
        pull = r"pulls(?:/[1-9][0-9]{0,15})?"
        sha = r"(?:[a-f0-9]{40}|[a-f0-9]{64})"
        readable = re.fullmatch(pull + rf"|(?:pulls\?state=all|statuses/{sha}\?)(&?page=[0-9]+)&limit=50", suffix)
        writable = suffix == "pulls" or re.fullmatch(r"pulls/[1-9][0-9]{0,15}/merge", suffix)
        if (not path.startswith(prefix) or
                not ((method == "GET" and body is None and readable) or
                     (method == "POST" and isinstance(body, dict) and writable))):
            raise core.Invalid("initiative_forgejo_bridge_http_scope")
        request = {"method": method, "path": path, "body": body}
        if method == "POST":
            self._verify_post(suffix, body, expected_head)
            core._oids((expected_base, expected_head), 2, 2)
            _active_expiry(expires_at)
            request.update(expires_at=expires_at, expected_base=expected_base, expected_head=expected_head)
        elif any(item is not None for item in (expires_at, expected_base, expected_head)):
            raise core.Invalid("initiative_forgejo_bridge_http_read_scope")
        value = l.object_value(self._call("http", **request))
        if set(value) != {"status", "headers", "value"} or type(value["status"]) is not int:
            raise core.Invalid("initiative_forgejo_bridge_http_unproved")
        headers = l.object_value(value["headers"])
        if not all(isinstance(entry, str) for entry in headers.values()):
            raise core.Invalid("initiative_forgejo_bridge_http_unproved")
        return forgejo.Response(value["status"], value["value"], headers)

    def _verify_post(self, suffix: str, body: dict[str, object], expected_head: str | None) -> None:
        if suffix == "pulls":
            if set(body) != {"head", "base", "title", "body"} or body["base"] != forgejo._branch(
                    self.fixture.target_ref) or body["head"] == body["base"]:
                raise core.Invalid("initiative_forgejo_bridge_pull_scope")
            core._branch(body["head"])
            return
        if (set(body) != {"Do", "head_commit_id", "force_merge", "merge_when_checks_succeed",
                         "delete_branch_after_merge"} or body["Do"] != "merge" or body["head_commit_id"] != expected_head
                or any(body[key] is not False for key in (
                    "force_merge", "merge_when_checks_succeed", "delete_branch_after_merge"))):
            raise core.Invalid("initiative_forgejo_bridge_merge_scope")
        core._oid(body["head_commit_id"])

    def current_execution(self, subject: ci.Subject, check: ci.RequiredCheck) -> ci.Execution | None:
        self._binding(subject.binding)
        value = self._call("ci_execution", subject=asdict(subject), check=asdict(check))
        if value is None:
            return None
        row = l.object_value(value)
        try:
            if (set(row) != {"subject", "context", "producer_digest", "invocation", "phase", "receipts", "started_at"}
                    or l.canonical(row["subject"]) != l.canonical(asdict(subject)) or row["context"] != check.context
                    or row["producer_digest"] != check.producer_digest):
                raise core.Conflict("initiative_forgejo_bridge_ci_unbound")
            invocation = r.Invocation(**l.object_value(row["invocation"]))
            receipts = row["receipts"]
            if not isinstance(receipts, list) or len(receipts) > 512:
                raise core.Invalid("initiative_forgejo_bridge_ci_invalid")
            return ci.Execution(subject, row["context"], row["producer_digest"], invocation, row["phase"],
                tuple(self._receipt(subject, l.object_value(item)) for item in receipts), _time(row["started_at"]))
        except (TypeError, KeyError, ValueError):
            raise core.Invalid("initiative_forgejo_bridge_ci_invalid") from None

    @staticmethod
    def _receipt(subject: ci.Subject, row: dict) -> ci.ExecutionReceipt:
        if (set(row) != {"subject", "context", "producer_digest", "invocation", "status_id", "executed",
                        "conclusion", "completed_at", "provider"}
                or l.canonical(row["subject"]) != l.canonical(asdict(subject))):
            raise core.Conflict("initiative_forgejo_bridge_ci_unbound")
        return ci.ExecutionReceipt(subject, row["context"], row["status_id"], row["producer_digest"],
            r.Invocation(**l.object_value(row["invocation"])), row["executed"], row["conclusion"],
            _time(row["completed_at"]), row["provider"])

    def _retry_activation(self, activation: Activation) -> dict[str, str]:
        if (type(activation) is not Activation or not activation.managed
                or (activation.target.origin, activation.target.repository, activation.target.target_ref)
                != (self.binding.origin, self.binding.repository, self.fixture.target_ref)):
            raise core.Conflict("initiative_forgejo_retry_target_changed")
        return {"activation_id": activation.activation_id, "grant_id": activation.grant_id,
                "slice_id": activation.slice_id}

    def _retry_request(self, activation: Activation, request: Request) -> dict[str, object]:
        scope = self._retry_activation(activation)
        if (type(request) is not Request or scope != {
                "activation_id": request.activation_id, "grant_id": request.grant_id, "slice_id": request.slice_id}
                or request.correction.kind != INFRASTRUCTURE):
            raise core.Conflict("initiative_forgejo_retry_request_unbound")
        return {**scope, "request": asdict(request), "request_digest": core.identity(request)}

    def retry_qualification(self) -> str | None:
        value = self._call("retry_qualification")
        return None if value is None else l.hex_value(value)

    def retry_correction(self, activation: Activation, failure: Failure) -> str | None:
        scope = self._retry_activation(activation)
        if type(failure) is not Failure:
            raise core.Invalid("initiative_forgejo_retry_failure_invalid")
        value = self._call("retry_correction", **scope, failure=asdict(failure))
        return None if value is None else l.hex_value(value)

    def retry_verify(self, activation: Activation, request: Request) -> bool:
        value = self._call("retry_verify", **self._retry_request(activation, request))
        if type(value) is not bool:
            raise core.Invalid("initiative_forgejo_retry_verification_unproved")
        return value

    def retry_submit(self, activation: Activation, request: Request, expires_at: str) -> dict | None:
        fields = self._retry_request(activation, request)
        _active_expiry(int(l.initiative_time(expires_at).timestamp()))
        value = self._call("retry_submit", **fields, expires_at=expires_at)
        return None if value is None else l.object_value(value)

    def retry_readback(self, activation: Activation, request: Request) -> dict | None:
        value = self._call("retry_readback", **self._retry_request(activation, request))
        return None if value is None else l.object_value(value)

    def preconditions(self, intent: merge.MergeIntent, reservation: r.NativeReservation,
                      activation: Activation, expires_at: int) -> merge.MergePreconditions | None:
        self._binding(intent.target.binding)
        _active_expiry(expires_at)
        value = self._call("merge_preconditions", intent=asdict(intent), reservation=asdict(reservation),
                           activation_id=activation.activation_id, grant_id=activation.grant_id,
                           expires_at=expires_at)
        if value is None:
            return None
        row = l.object_value(value)
        if (set(row) != {"target", "policy_digest", "reviewer_id", "reviewed_head", "grant"}
                or l.canonical(row["target"]) != l.canonical(asdict(self.fixture.target))):
            raise core.Conflict("initiative_forgejo_bridge_guard_unbound")
        try:
            grant = merge.GuardGrant(**l.object_value(row["grant"]))
        except (TypeError, ValueError):
            raise core.Invalid("initiative_forgejo_bridge_guard_invalid") from None
        return merge.MergePreconditions(self.fixture.target, row["policy_digest"], row["reviewer_id"],
                                        row["reviewed_head"], grant)


def _time(value: object) -> datetime | None:
    return None if value is None else l.initiative_time(value)


def _active_expiry(expires_at: object) -> float:
    core._integer(expires_at)
    now = datetime.now(UTC).timestamp()
    if cast(int, expires_at) <= now:
        raise core.Unavailable("initiative_forgejo_bridge_approval_expired")
    return now
