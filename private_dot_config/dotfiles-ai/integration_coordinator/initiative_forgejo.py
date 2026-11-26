"""Managed delivery to one separately qualified, private Forgejo fixture."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from typing import Protocol

from . import core, forgejo, forgejo_ci as ci, forgejo_merge as merge
from . import initiative_controller as controller, lifecycle as l, runtime as r
from .initiative_authority import initiative_effect_lock


@dataclass(frozen=True, slots=True)
class Fixture:
    target: merge.MergeTarget
    operator_id: int
    root_oid: str
    plan: ci.CheckPlan
    bridge_digest: str
    draft_prefixes: tuple[str, ...]

    @property
    def binding(self) -> forgejo.Binding:
        return self.target.binding

    @property
    def target_ref(self) -> str:
        return self.target.target_ref

    @property
    def repository(self) -> dict[str, object]:
        return {"provider": "forgejo", "origin": self.binding.origin, "repository": self.binding.repository}

    @property
    def digest(self) -> str:
        return core.identity(self)


def parse_fixture(raw: object) -> Fixture:
    value = l.object_value(raw)
    fields = {"binding", "target_ref", "root_oid", "actor_id", "operator_id", "guard_digest",
              "dispatcher_digest", "policy_digest", "checks", "bridge_digest", "draft_prefixes"}
    if set(value) != fields:
        raise ValueError("initiative_forgejo_fixture_invalid")
    binding_doc = l.object_value(value["binding"])
    if set(binding_doc) != {"origin", "repository", "repository_id", "git_account", "api_account", "version"}:
        raise ValueError("initiative_forgejo_binding_invalid")
    binding = forgejo.Binding(**binding_doc)
    # The same native adapter validates the approved origin, repository, IDs and version.
    forgejo._validate_binding(binding)
    core._oid(value["root_oid"])
    for key in ("actor_id", "operator_id"):
        core._integer(value[key])
    for key in ("guard_digest", "dispatcher_digest", "policy_digest", "bridge_digest"):
        core._digest(value[key])
    target = merge.MergeTarget(binding, value["target_ref"], value["actor_id"],
                               value["guard_digest"], value["dispatcher_digest"])
    raw_checks = value["checks"]
    if not isinstance(raw_checks, list) or not 1 <= len(raw_checks) <= 512:
        raise ValueError("initiative_forgejo_checks_invalid")
    checks = tuple(ci.RequiredCheck(**l.object_value(check)) for check in raw_checks)
    plan = ci.CheckPlan(binding, target.target_ref, value["policy_digest"], checks)
    if {target.actor_id, value["operator_id"]} & {check.creator_id for check in checks}:
        raise ValueError("initiative_forgejo_producer_not_independent")
    prefixes = tuple(l.string_list(value["draft_prefixes"]))
    core._tuple(prefixes, str, 16, 1)
    if len({item.casefold() for item in prefixes}) != len(prefixes):
        raise ValueError("initiative_forgejo_draft_prefixes_invalid")
    for prefix in prefixes:
        forgejo._title(prefix, 64)
    return Fixture(target, value["operator_id"], value["root_oid"], plan, value["bridge_digest"], prefixes)



@dataclass(frozen=True, slots=True)
class Source:
    ref: str
    base: str
    head: str
    tree: str
    entries: tuple[r.SourceEntry, ...]
    record_digest: str

    def __post_init__(self) -> None:
        forgejo._branch(self.ref)
        core._oid(self.tree)
        core._digest(self.record_digest)
        core._tuple(self.entries, r.SourceEntry, 1024, 1)
        core._oids((self.base, *(entry.oid for entry in self.entries)), 1025, 2)
        core._require(self.head == self.entries[-1].oid and any(entry.gates for entry in self.entries),
                      "initiative_forgejo_source_interval_invalid")
        core._require(all(len(oid) == len(self.head) for oid in (self.tree, self.base, *(e.oid for e in self.entries))),
                      "mixed_oid_formats")

    @classmethod
    def load(cls, raw: dict) -> Source:
        return cls(raw["ref"], raw["base"], raw["head"], raw["tree"],
                   tuple(r.SourceEntry(row["oid"], row["kind"], tuple(row["gates"])) for row in raw["entries"]),
                   raw["record_digest"])


def publication_title(source: Source) -> str:
    return f"DBSCTR candidate {source.head[:12]}"


class Ports(forgejo.Transport, merge.Objects, ci.ReceiptReader, Protocol):
    def request(self, method: str, path: str, body: dict[str, object] | None = None, *,
                expires_at: int | None = None, expected_base: str | None = None,
                expected_head: str | None = None) -> forgejo.Response: ...

    def push(self, checkout: str, ref: str, oid: str, expires_at: int) -> None: ...

    def preconditions(self, intent: merge.MergeIntent, reservation: r.NativeReservation,
                      activation: controller.Activation, expires_at: int) -> merge.MergePreconditions | None: ...


class _FencedTransport:
    def __init__(self, ports: Ports, source: Source, deadline: Callable[[], int | None]) -> None:
        self.ports, self.source, self.deadline = ports, source, deadline
        self.binding = ports.binding

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> forgejo.Response:
        if method == "GET":
            return self.ports.request(method, path, body)
        until = self.deadline()
        if until is None or int(datetime.now(UTC).timestamp()) >= until:
            raise core.Unavailable("initiative_forgejo_write_expired")
        return self.ports.request(method, path, body, expires_at=until,
                                  expected_base=self.source.base, expected_head=self.source.head)


class FixtureDelivery:
    """Use private per-activation claims with the existing provider adapters."""

    def __init__(self, custody: l.Custody, fixture: Fixture, ports: Ports,
                 source: Callable[[controller.Activation], Source | None],
                 authorize: Callable[[controller.Activation, str], int]) -> None:
        self.custody, self.fixture, self.ports = custody, fixture, ports
        self.source, self.authorize = source, authorize

    def _path(self, activation: controller.Activation, kind: str):
        expected = controller.Target(self.fixture.binding.origin, self.fixture.binding.repository,
                                     self.fixture.target_ref)
        if not activation.managed or activation.target != expected:
            raise core.Conflict("initiative_forgejo_target_changed")
        return self.custody.directory / "forgejo-initiative" / activation.activation_id / f"{kind}.json"

    def _read(self, activation: controller.Activation, kind: str) -> dict | None:
        path = self._path(activation, kind)
        try:
            raw = self.custody._read(path)
        except FileNotFoundError:
            if path.is_symlink():
                raise core.Invalid("initiative_forgejo_custody_invalid") from None
            return None
        except (ValueError, OSError):
            raise core.Invalid("initiative_forgejo_custody_invalid") from None
        try:
            value = l.object_value(json.loads(raw, object_pairs_hook=l.no_duplicates))
            if set(value) != {"activation", "fixture", "value"} or (
                    value["activation"], value["fixture"]) != (activation.activation_id, self.fixture.digest):
                raise ValueError("initiative_forgejo_custody_changed")
            return l.object_value(value["value"])
        except (ValueError, KeyError):
            raise core.Invalid("initiative_forgejo_custody_invalid") from None

    def _write(self, activation: controller.Activation, kind: str, value: dict) -> None:
        try:
            self.custody._write(self._path(activation, kind), l.canonical({
                "activation": activation.activation_id, "fixture": self.fixture.digest, "value": value,
            }))
        except (ValueError, OSError):
            raise core.Unavailable("initiative_forgejo_custody_write_unavailable") from None

    def _read_source(self, activation: controller.Activation) -> Source | None:
        data = self._read(activation, "source")
        if data is None:
            return None
        try:
            source = Source.load(data)
        except (KeyError, TypeError, ValueError):
            raise core.Invalid("initiative_forgejo_source_invalid") from None
        if l.canonical(asdict(source)) != l.canonical(data):
            raise core.Invalid("initiative_forgejo_source_changed")
        return source

    def _admission_data(self, activation: controller.Activation) -> tuple[Source, int, int] | None:
        data = self._read(activation, "admission")
        if data is None:
            return None
        source = self._read_source(activation)
        if source is None or set(data) != {"source", "number", "pull_id"} or data["source"] != core.identity(source):
            raise core.Invalid("initiative_forgejo_admission_unbound")
        core._integer(data["number"])
        core._integer(data["pull_id"])
        return source, data["number"], data["pull_id"]

    def observe_admission(self, activation: controller.Activation) -> controller.Admission | None:
        data = self._admission_data(activation)
        if data is None:
            return None
        source, number, pull_id = data
        digest = l.digest({"activation": activation.activation_id, "fixture": self.fixture.digest,
                                "source": core.identity(source), "number": number, "pull_id": pull_id})
        return controller.Admission(activation.activation_id, activation.target, digest[:32],
                                    l.digest({"admission": digest})[:32], digest)

    def _candidate(self, source: Source, number: int, pull_id: int) -> merge.MergeIntent:
        binding = self.fixture.binding
        series = r.SourceSeries(binding.repository, number, source.base, source.head, source.entries,
                                source.record_digest)
        previous = source.base
        for entry in source.entries:
            commit = self.ports.commit(binding, entry.oid)
            if commit.oid != entry.oid or commit.parents != (previous,):
                raise core.Conflict("initiative_forgejo_source_not_linear")
            previous = entry.oid
        if commit.tree != source.tree:
            raise core.Conflict("initiative_forgejo_source_tree_changed")
        projection = r.Projection(core.identity(series), source.base, source.head,
            tuple(core.CommitPair(item.oid, item.oid) for item in source.entries), source.record_digest)
        candidate = r.Candidate(1, projection.source_digest, core.identity(projection), source.head,
                                source.base, source.head, commit.parents, source.tree,
                                core.identity(self.fixture.plan), self.fixture.plan.policy_digest)
        return merge.MergeIntent(self.fixture.target, ci.Subject(binding, self.fixture.target_ref, number, candidate),
                                 source.ref, projection, pull_id)

    def _reservation(self, admission: controller.Admission, intent: merge.MergeIntent) -> r.NativeReservation:
        candidate = intent.subject.candidate
        scope = l.digest({"admission": admission.receipt_digest, "intent": asdict(intent)})
        invocation = r.OperatorInvocation(self.fixture.operator_id, scope[:32], admission.receipt_digest, scope)
        return r.NativeReservation("merge", l.digest({"invocation": scope})[:32], invocation,
                                   candidate.generation, core.identity(candidate), candidate.head, candidate.base)

    def _publish(self, activation: controller.Activation, source: Source) -> None:
        binding = self.fixture.binding
        if (source.base != activation.launch.base_head or source.ref == self.fixture.target_ref
                or self.ports.ref(binding, self.fixture.target_ref) != source.base):
            raise core.Conflict("initiative_forgejo_base_changed")
        remote = self.ports.ref(binding, source.ref)
        if remote is not None and remote != source.head:
            raise core.Conflict("initiative_forgejo_feature_ref_changed")
        if remote is None:
            if self._read(activation, "push-claim") is not None:
                raise core.Ambiguous("initiative_forgejo_push_unresolved")
            until = self._authorize_source(activation, source, "admit")
            self._write(activation, "push-claim", {"source": core.identity(source)})
            self.ports.push(activation.launch.checkout, source.ref, source.head, until)
        if self.ports.ref(binding, source.ref) != source.head:
            raise core.Ambiguous("initiative_forgejo_push_unresolved")
        if self.ports.ref(binding, self.fixture.target_ref) != source.base:
            raise core.Conflict("initiative_forgejo_base_changed")
        publication = forgejo.Publication(binding, source.ref, self.fixture.target_ref, source.head,
                                         source.base, publication_title(source), False, self.fixture.draft_prefixes)
        deadline = None

        def before_create() -> None:
            nonlocal deadline
            if self.ports.ref(binding, self.fixture.target_ref) != source.base:
                raise core.Conflict("initiative_forgejo_base_changed")
            if self.ports.ref(binding, source.ref) != source.head:
                raise core.Conflict("initiative_forgejo_feature_ref_changed")
            deadline = self._authorize_source(activation, source, "admit")
            self._write(activation, "publication-claim", {"source": core.identity(source)})

        if self._read(activation, "publication-claim") is None:
            transport = _FencedTransport(self.ports, source, lambda: deadline)
            pull = forgejo.publish_pull_request(publication, transport, before_create=before_create)
        else:
            pull = forgejo.recover_pull_request(publication, self.ports)
        row = forgejo._object(forgejo._get(self.ports, f"{forgejo._endpoint(publication)}/{pull.number}").value)
        if (forgejo._readback_row(publication, row, pull.number) != pull
                or forgejo._object(row.get("user")).get("id") != self.fixture.target.actor_id):
            raise core.Conflict("initiative_forgejo_admission_changed")
        pull_id = row.get("id")
        core._integer(pull_id)
        self._write(activation, "admission", {"source": core.identity(source), "number": pull.number,
                                              "pull_id": pull_id})

    def _authorize_source(self, activation: controller.Activation, source: Source, operation: str) -> int:
        until = self.authorize(activation, operation)
        if self.source(activation) != source:
            raise core.Conflict("initiative_forgejo_source_changed")
        if int(datetime.now(UTC).timestamp()) >= until:
            raise core.Unavailable("initiative_forgejo_approval_expired")
        return until

    def advance(self, activation: controller.Activation) -> None:
        with initiative_effect_lock(self.custody, activation.grant_id):
            admission = self.observe_admission(activation)
            if admission is None:
                source = self._read_source(activation)
                if source is None:
                    source = self.source(activation)
                    if source is None:
                        return
                    if source.base != activation.launch.base_head or source.ref == self.fixture.target_ref:
                        raise core.Conflict("initiative_forgejo_source_unbound")
                    self.authorize(activation, "admit")
                    self._write(activation, "source", asdict(source))
                self._publish(activation, source)
                return
            if self._read(activation, "merge-claim") is not None:
                return
            source, number, pull_id = self._admission_data(activation)
            if self.ports.ref(self.fixture.binding, self.fixture.target_ref) != source.base:
                raise core.Conflict("initiative_forgejo_base_changed")
            intent = self._candidate(source, number, pull_id)
            assessment = ci.assess_ci(intent.subject, self.fixture.plan, self.ports, self.ports,
                                      observed_at=datetime.now(UTC))
            if assessment.state != "passed":
                return
            self._authorize_source(activation, source, "merge")
            reservation = self._reservation(admission, intent)
            self._write(activation, "reservation", asdict(reservation))
            authority = _MergeAuthority(self, activation, intent, reservation, source)
            transport = _FencedTransport(self.ports, source, lambda: authority.submission_deadline)
            merge.merge(intent, reservation, self.fixture.plan, transport, self.ports, authority, self.ports)

    def observe_delivery(self, activation: controller.Activation,
                         admission: controller.Admission) -> controller.Delivery | None:
        if self.observe_admission(activation) != admission:
            raise core.Conflict("initiative_forgejo_admission_changed")
        claim = self._read(activation, "merge-claim")
        if claim is None:
            return None
        source, number, pull_id = self._admission_data(activation)
        intent = self._candidate(source, number, pull_id)
        reservation = self._reservation(admission, intent)
        if claim != {"operation_id": reservation.operation_id, "intent": core.identity(intent)}:
            raise core.Conflict("initiative_forgejo_submission_unbound")
        authority = _MergeAuthority(self, activation, intent, reservation, source)
        verified = merge.reconcile(intent, reservation, self.ports, self.ports, authority)
        proof = asdict(verified)
        del proof["target_oid"]  # Current target inclusion is rechecked on every read.
        return controller.Delivery(activation.activation_id, activation.target, admission.ticket_handle,
                                   admission.obligation_handle, verified.merge_oid, l.digest(proof))


class _MergeAuthority:
    def __init__(self, delivery: FixtureDelivery, activation: controller.Activation,
                 intent: merge.MergeIntent, reservation: r.NativeReservation, source: Source) -> None:
        self.delivery, self.activation = delivery, activation
        self.intent, self.reservation, self.source = intent, reservation, source
        self.guard_expires = 0
        self.submission_deadline = None

    def verify_reservation(self, intent: merge.MergeIntent, reservation: r.NativeReservation) -> None:
        retained = self.delivery._read(self.activation, "reservation")
        if (intent, reservation) != (self.intent, self.reservation) or retained != asdict(reservation):
            raise core.Conflict("initiative_forgejo_reservation_changed")

    def observe_preconditions(self, intent: merge.MergeIntent,
                              reservation: r.NativeReservation) -> merge.MergePreconditions | None:
        self.verify_reservation(intent, reservation)
        until = self.delivery._authorize_source(self.activation, self.source, "merge")
        observed = self.delivery.ports.preconditions(intent, reservation, self.activation, until)
        if observed is not None:
            if type(observed) is not merge.MergePreconditions or type(observed.grant) is not merge.GuardGrant:
                raise core.Invalid("initiative_forgejo_guard_unproved")
            self.guard_expires = observed.grant.expires_at
            core._integer(self.guard_expires)
            if self.guard_expires > until:
                raise core.Conflict("initiative_forgejo_guard_outlives_approval")
        return observed

    def claim_submission(self, intent: merge.MergeIntent, reservation: r.NativeReservation) -> None:
        self.verify_reservation(intent, reservation)
        until = self.delivery._authorize_source(self.activation, self.source, "merge")
        if not int(datetime.now(UTC).timestamp()) < self.guard_expires <= until:
            raise core.Unavailable("initiative_forgejo_guard_inactive")
        if self.delivery._read(self.activation, "merge-claim") is not None:
            raise core.Conflict("initiative_forgejo_submission_already_claimed")
        self.delivery._write(self.activation, "merge-claim", {"operation_id": reservation.operation_id,
                                                               "intent": core.identity(intent)})
        self.submission_deadline = self.guard_expires
