"""Private immutable lifecycle custody; native authority belongs to validated ports.

These objects retain local attribution and never enter the public control ledger.
Content hashes bind evidence; they do not authenticate humans or prove CI execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import VerifiedOutcome

from . import core, runtime
from .gitproof import GitObjects, Proof, prove_series

MAX_PRIVATE_BYTES = 512 * 1024

_FIELDS = {
    "birth": "cycle_id launch_digest record_digest policy_digest enrollment_digest remote_repository target_ref control_ref guarded_refresh delivery_mode",
    "obligation": "handle cycle_id record_digest source_digest source_custody_digest original_task_digest scope_digest context risk target_ref policy_digest",
    "grant": "obligation_digest record_digest context risk scope_digest profile_blob plan_digest policy_digest enrollment_digest approval_digest allowed_operations authorized_at",
    "authorization": "grant_digest obligation_digest child_cycle_id launch_digest plan_digest profile_blob source_head base_head enrollment_digest assessment_digest authorized_at predecessor_ticket qualified_projection_digest prior_revision_digest delivery_mode guarded_refresh",
    "projection": "grant_digest obligation_digest prior_revision_digest prior_source_custody_digest ticket obligation projection native_receipt_digest verified_at",
    "revision": "grant_digest obligation_digest prior_revision_digest prior_source_custody_digest qualified_projection_digest child_cycle_id child_record_digest authorization_digest adoption_digest",
    "revision_link": "revision_digest source_custody_digest ticket_handle",
    "adoption": "grant_digest original_source_custody_digest record_digest projection native_receipt_digest delivery_mode guarded_refresh verified_at",
    "alignment_selection": "grant_digest qualified_projection_digest expected_head scope_digest",
    "outcome": "obligation_digest grant_digest source_digest revision_digest ticket_handle native_receipt_digest merge landed_base published_head published_base merged_at mapping record_digests verified_at",
    "outcome_check": "outcome_digest verification_digest ledger_head target_head checked_at",
    "operator": "obligation_digest grant_digest original_task_digest task_custody_digest repository root_oid policy_digest obligation_handle ticket_handle generation source_digest requester_id invocation_id pid created_at scope_digest",
    "source": "record_digest descriptor",
    "assessment": "grant_digest launch_digest predecessor_ticket statement assessed_at",
    "revocation": "grant_digest reason_digest revoked_at",
    "outbox": "cycle_id record_digest source_digest obligation_digest ticket_handle requester_digest request",
    "validation_correction": "grant_digest obligation_digest predecessor_ticket expected_generation failure_digest source_digest revision_digest source_custody_digest scope_digest policy_digest remote_policy_digest enrollment_digest ledger_head statement assessed_at",
    "validation_outbox": "correction_digest obligation_digest predecessor_ticket ticket_handle request",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode() + b"\n"


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def text(value: object, maximum: int = 256) -> str:
    if (not isinstance(value, str) or not 0 < len(value.encode()) <= maximum
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("integration_private_text_invalid")
    return value


def hex_value(value: object, lengths: tuple[int, ...] = (64,)) -> str:
    result = text(value)
    if len(result) not in lengths or re.fullmatch(r"[0-9a-f]+", result) is None:
        raise ValueError("integration_private_identity_invalid")
    return result


def timestamp(value: object) -> str:
    result = text(value)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("integration_private_timestamp_invalid") from None
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("integration_private_timestamp_invalid")
    return result


def string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise ValueError("integration_private_list_invalid")
    return tuple(text(item, 64) for item in value)


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError("integration_private_object_invalid")
    return {str(k): v for k, v in value.items()}


def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("integration_private_duplicate_key")
        result[key] = value
    return result


def validate(kind: str, value: Mapping[str, object]) -> None:
    if kind not in _FIELDS or set(value) != set(_FIELDS[kind].split()):
        raise ValueError("integration_private_fields_invalid")
    for key, item in value.items():
        if kind == "revision" and key in {"prior_revision_digest", "qualified_projection_digest", "authorization_digest", "adoption_digest"} and item is None:
            continue
        if key == "request":
            request = object_value(item)
            if (set(request) != {"schema_version", "policy_digest", "ticket", "obligation"}
                    or type(request["schema_version"]) is not int or request["schema_version"] != 2
                    or len(canonical(request)) > 48 * 1024):
                raise ValueError("integration_private_outbox_request_invalid")
            hex_value(request["policy_digest"])
            runtime.decode("validation_repair" if kind == "validation_outbox" else "ticket", canonical(request["ticket"]))
            runtime.decode("obligation", canonical(request["obligation"]))
        elif key in {"ticket", "obligation", "projection"}:
            runtime.decode(key, canonical(item))
        elif key == "predecessor_ticket":
            hex_value(item, tuple(range(16, 65)))
        elif key.endswith("_digest"):
            hex_value(item)
        elif key in {"profile_blob", "source_head", "base_head", "merge", "landed_base", "published_head", "ledger_head", "target_head", "expected_head", "root_oid", "published_base"}:
            hex_value(item, (40, 64))
        elif key in {"handle", "ticket_handle", "obligation_handle", "invocation_id"}:
            hex_value(item, tuple(range(16, 65)))
        elif key in {"authorized_at", "verified_at", "assessed_at", "revoked_at", "merged_at", "checked_at", "created_at"}:
            timestamp(item)
        elif kind == "validation_correction" and key == "expected_generation":
            if type(item) is not int or not 1 <= item <= 2**53 - 1:
                raise ValueError("integration_private_integer_invalid")
        elif kind == "operator" and key in {"generation", "requester_id", "pid"}:
            if type(item) is not int or not 1 <= item <= (2147483647 if key == "pid" else 2**53 - 1):
                raise ValueError("integration_private_integer_invalid")
        elif key == "repository":
            core._repository(item)
        elif key == "guarded_refresh":
            if type(item) is not bool:
                raise ValueError("integration_private_boolean_invalid")
        elif key == "delivery_mode":
            if item not in ("off", "draft_pr", "pr", "ordinary", "admin"):
                raise ValueError("integration_private_delivery_mode_invalid")
        elif key == "risk":
            if item not in ("routine", "elevated", "critical"):
                raise ValueError("integration_private_risk_invalid")
        elif key in {"allowed_operations", "landed_commits"}:
            if not isinstance(item, list) or not 1 <= len(item) <= 256:
                raise ValueError("integration_private_list_invalid")
            checked = [hex_value(x, (40, 64)) if key == "landed_commits" else text(x, 64)
                       for x in item]
            if len(set(checked)) != len(checked):
                raise ValueError("integration_private_list_invalid")
            if key == "allowed_operations" and set(checked) - {"submit", "repair", "accept_outcome", "operator_resume"}:
                raise ValueError("integration_private_operation_invalid")
        elif key == "mapping":
            if not isinstance(item, list) or not 1 <= len(item) <= 4096:
                raise ValueError("integration_private_mapping_invalid")
            originals: set[str] = set()
            for raw in item:
                pair = object_value(raw)
                if set(pair) != {"original", "landed"}:
                    raise ValueError("integration_private_mapping_invalid")
                original = hex_value(pair["original"], (40, 64)); hex_value(pair["landed"], (40, 64))
                if original in originals:
                    raise ValueError("integration_private_mapping_duplicate")
                originals.add(original)
        elif key == "record_digests":
            records = object_value(item)
            if not 1 <= len(records) <= 64:
                raise ValueError("integration_private_records_bound")
            for cycle, record_digest in records.items():
                if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", cycle) is None:
                    raise ValueError("integration_private_cycle_invalid")
                hex_value(record_digest)
        elif key == "descriptor":
            runtime.decode("source", canonical(item))
        else:
            result = text(item, 4096 if key == "statement" else 256)
            if key.endswith("cycle_id") and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", result) is None:
                raise ValueError("integration_private_cycle_invalid")
            if key.endswith("_ref") and (not result.startswith("refs/heads/") or any(
                    term in result for term in ("..", "//", "@{", "\\", " ", "~", "^", ":", "?", "*", "["))
                    or result.endswith(("/", ".", ".lock"))):
                raise ValueError("integration_private_ref_invalid")
    if kind == "birth" and value["target_ref"] == value["control_ref"]:
        raise ValueError("integration_private_control_invalid")


def qualify_projection(objects: GitObjects, source: runtime.SourceSeries,
                       projection: runtime.Projection) -> Proof:
    """Reprove every original delta; serialized projection claims are insufficient."""
    runtime._projection(source, projection)
    proof = prove_series(objects, source.base, tuple(entry.oid for entry in source.entries),
                         projection.head, projection.base)
    if proof.pairs != projection.mapping or projection.receipt_digest != core.identity(proof):
        raise ValueError("integration_projection_correspondence_changed")
    return proof


def compose_source(objects: GitObjects, prior: runtime.SourceSeries, projection: runtime.Projection,
                   additions: tuple[runtime.SourceEntry, ...], authority_digest: str) -> runtime.SourceSeries:
    """Map prior attribution through qualified replay, then append the owned child."""
    qualify_projection(objects, prior, projection)
    if not additions:
        raise ValueError("integration_revision_child_empty")
    prove_series(objects, projection.head, tuple(entry.oid for entry in additions),
                 additions[-1].oid, projection.head)
    projected = tuple(runtime.SourceEntry(pair.landed, entry.kind, entry.gates)
                      for pair, entry in zip(projection.mapping, prior.entries, strict=True))
    return runtime.SourceSeries(prior.repository, prior.pr_number, projection.base, additions[-1].oid,
                                (*projected, *additions), authority_digest)


class Custody:
    """One bounded immutable object store under the repository's common Git dir."""

    def __init__(self, common_git_dir: Path) -> None:
        common = common_git_dir.absolute()
        if common != common.resolve(strict=True) or not common.is_dir():
            raise ValueError("integration_private_root_invalid")
        for parent in (common, *common.parents):
            if parent.is_symlink():
                raise ValueError("integration_private_root_invalid")
        info = common.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError("integration_private_root_invalid")
        self.common = common
        self.directory = common / "dbsctr/integration"

    def object_path(self, identity: str) -> Path:
        return self.directory / "objects" / (hex_value(identity) + ".json")

    def _directory(self, directory: Path, create: bool) -> None:
        relative = directory.relative_to(self.common)
        current = self.common
        for part in relative.parts:
            current = current / part
            if create:
                try:
                    current.mkdir(mode=0o700)
                except FileExistsError:
                    pass
            info = current.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o022 or current.is_symlink()):
                raise ValueError("integration_private_directory_invalid")

    def _read(self, path: Path) -> bytes:
        self._directory(path.parent, False)
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_size > MAX_PRIVATE_BYTES):
                raise ValueError("integration_private_file_invalid")
            raw = stream.read(MAX_PRIVATE_BYTES + 1)
        if len(raw) > MAX_PRIVATE_BYTES:
            raise ValueError("integration_private_file_invalid")
        return raw

    def _write(self, path: Path, raw: bytes) -> None:
        if len(raw) > MAX_PRIVATE_BYTES:
            raise ValueError("integration_private_bound_exceeded")
        self._directory(path.parent, True)
        descriptor, name = tempfile.mkstemp(dir=path.parent)
        temporary = Path(name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if self._read(path) != raw:
                    raise ValueError("integration_private_immutable_conflict") from None
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def write(self, kind: str, value: Mapping[str, object]) -> str:
        validate(kind, value)
        raw = canonical({"schema_version": 1, "kind": kind, "value": dict(value)})
        identity = hashlib.sha256(raw).hexdigest()
        self._write(self.object_path(identity), raw)
        return identity

    def read(self, kind: str, identity: str) -> dict[str, object]:
        raw = self._read(self.object_path(identity))
        if hashlib.sha256(raw).hexdigest() != identity:
            raise ValueError("integration_private_digest_changed")
        envelope = object_value(json.loads(raw, object_pairs_hook=no_duplicates))
        if (set(envelope) != {"schema_version", "kind", "value"}
                or type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1
                or envelope["kind"] != kind):
            raise ValueError("integration_private_envelope_invalid")
        value = object_value(envelope["value"])
        validate(kind, value)
        return value

    def link(self, kind: str, key: str, identity: str) -> None:
        if kind not in {"birth", "grant", "outbox", "outcome", "authorization", "revocation", "projection", "revision_link", "outcome_check", "alignment_selection", "adoption", "validation_correction", "validation_outbox"} or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", key) is None:
            raise ValueError("integration_private_link_invalid")
        self.read(kind, identity)
        self._write(self.directory / "links" / kind / (key + ".json"), canonical({"digest": identity}))

    def linked(self, kind: str, key: str) -> dict[str, object]:
        if kind not in {"birth", "grant", "outbox", "outcome", "authorization", "revocation", "projection", "revision_link", "outcome_check", "alignment_selection", "adoption", "validation_correction", "validation_outbox"} or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", key) is None:
            raise ValueError("integration_private_link_invalid")
        value = object_value(json.loads(self._read(self.directory / "links" / kind / (key + ".json")),
                                       object_pairs_hook=no_duplicates))
        if set(value) != {"digest"}:
            raise ValueError("integration_private_link_invalid")
        return self.read(kind, hex_value(value["digest"]))

    def optional_link(self, kind: str, key: str) -> dict[str, object] | None:
        """Only genuine link absence is optional; dangling custody is an error."""
        if kind not in {"birth", "grant", "outbox", "outcome", "authorization", "revocation", "projection", "revision_link", "outcome_check", "alignment_selection", "adoption", "validation_correction", "validation_outbox"} or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", key) is None:
            raise ValueError("integration_private_link_invalid")
        path = self.directory / "links" / kind / (key + ".json")
        try:
            self._directory(path.parent, False)
        except FileNotFoundError:
            return None
        if not os.path.lexists(path):
            return None
        return self.linked(kind, key)

    def revoked(self, grant_digest: str) -> bool:
        grant_identity = hex_value(grant_digest)
        try:
            self._read(self.directory / "links" / "revocation" / (grant_identity + ".json"))
        except FileNotFoundError:
            return False
        # Only absence of the link means unrevoked. Once it exists, missing or
        # corrupt referenced custody must remain an error rather than revive a
        # grant. A second guarded read also refuses a link removed after probing.
        self.linked("revocation", grant_identity)
        return True

    def revoke(self, grant_digest: str, reason_digest: str, revoked_at: str) -> None:
        self.read("grant", grant_digest)
        identity = self.write("revocation", {"grant_digest": grant_digest,
            "reason_digest": reason_digest, "revoked_at": revoked_at})
        self.link("revocation", grant_digest, identity)

    def verify_approval(self, approval: Mapping[str, object], cycle_id: str) -> dict[str, object]:
        if (set(approval) != {"schema_version", "method", "launch_digest", "authorization_digest", "authorized_at"}
                or type(approval["schema_version"]) is not int or approval["schema_version"] != 2
                or approval["method"] != "integration_grant"):
            raise ValueError("integration_private_approval_invalid")
        auth = self.read("authorization", hex_value(approval["authorization_digest"]))
        grant = self.read("grant", hex_value(auth["grant_digest"]))
        obligation = self.read("obligation", hex_value(auth["obligation_digest"]))
        assessment = self.read("assessment", hex_value(auth["assessment_digest"]))
        source = self.read("source", hex_value(obligation["source_custody_digest"]))
        series = runtime.decode("source", canonical(source["descriptor"]))
        qualified = self.read("projection", hex_value(auth["qualified_projection_digest"]))
        predecessor = runtime.decode("ticket", canonical(qualified["ticket"]))
        projection = projection_record(qualified)
        if not isinstance(predecessor, runtime.Ticket):
            raise ValueError("integration_private_predecessor_invalid")
        live_mode = auth["delivery_mode"] in {"ordinary", "admin"}
        if (qualified["grant_digest"] != auth["grant_digest"]
                or qualified["obligation_digest"] != auth["obligation_digest"]
                or qualified["prior_revision_digest"] != auth["prior_revision_digest"]
                or predecessor.handle != auth["predecessor_ticket"]
                or auth["source_head"] != projection.head
                or assessment["predecessor_ticket"] != predecessor.handle
                or live_mode and (auth["delivery_mode"] != predecessor.delivery_mode
                                  or auth["guarded_refresh"] != predecessor.guarded_refresh)
                or not live_mode and auth["guarded_refresh"] is not False
                or source["record_digest"] != obligation["record_digest"]
                or core.identity(series) != obligation["source_digest"]
                or assessment["grant_digest"] != auth["grant_digest"]
                or assessment["launch_digest"] != auth["launch_digest"]
                or assessment["assessed_at"] != auth["authorized_at"]
                or auth["enrollment_digest"] != grant["enrollment_digest"]
                or auth["child_cycle_id"] != cycle_id or auth["launch_digest"] != approval["launch_digest"]
                or auth["authorized_at"] != approval["authorized_at"]
                or auth["obligation_digest"] != grant["obligation_digest"]
                or grant["record_digest"] != obligation["record_digest"]
                or grant["scope_digest"] != obligation["scope_digest"]
                or grant["context"] != obligation["context"] or grant["risk"] != obligation["risk"]
                or auth["profile_blob"] != grant["profile_blob"] or auth["plan_digest"] != grant["plan_digest"]
                or "repair" not in string_list(grant["allowed_operations"])):
            raise ValueError("integration_private_authorization_binding_changed")
        return auth


@dataclass(frozen=True, slots=True)
class RevisionChain:
    source: runtime.SourceSeries
    aliases: tuple[core.CommitPair, ...]
    records: tuple[tuple[str, str], ...]
    grant_digest: str
    obligation_digest: str
    revision_digest: str


def source_record(store: Custody, identity: str) -> runtime.SourceSeries:
    result = runtime.decode("source", canonical(store.read("source", identity)["descriptor"]))
    if not isinstance(result, runtime.SourceSeries):
        raise ValueError("integration_private_source_invalid")
    return result


def projection_record(value: Mapping[str, object]) -> runtime.Projection:
    result = runtime.decode("projection", canonical(value["projection"]))
    if not isinstance(result, runtime.Projection):
        raise ValueError("integration_private_projection_invalid")
    return result


def revision_chain(store: Custody, ticket_handle: str, objects: GitObjects,
                   record_entries: Callable[[str, str], tuple[runtime.SourceEntry, ...]]) -> RevisionChain:
    """Reprove the bounded retained chain; never infer old attribution from text."""
    link = store.linked("revision_link", ticket_handle)
    latest_revision = hex_value(link["revision_digest"])
    revision_id = latest_revision
    source_id = hex_value(link["source_custody_digest"])
    pending: list[tuple[str, dict[str, object], str]] = []
    seen: set[str] = set()
    while True:
        if revision_id in seen or len(pending) >= 64:
            raise ValueError("integration_revision_chain_bound")
        seen.add(revision_id)
        revision = store.read("revision", revision_id)
        pending.append((revision_id, revision, source_id))
        before = revision["prior_revision_digest"]
        if before is None:
            break
        revision_id = hex_value(before)
        source_id = hex_value(revision["prior_source_custody_digest"])
    aliases: dict[str, str] = {}
    records: list[tuple[str, str]] = []
    root_grant = hex_value(pending[-1][1]["grant_digest"])
    root_obligation = hex_value(pending[-1][1]["obligation_digest"])
    prior_source: runtime.SourceSeries | None = None
    prior_revision: str | None = None
    current: runtime.SourceSeries | None = None
    for identity, revision, source_identity in reversed(pending):
        if revision["grant_digest"] != root_grant or revision["obligation_digest"] != root_obligation:
            raise ValueError("integration_revision_root_changed")
        current = source_record(store, source_identity)
        cycle_id = text(revision["child_cycle_id"], 128)
        record_digest = hex_value(revision["child_record_digest"])
        actual = record_entries(cycle_id, record_digest)
        if store.read("source", source_identity)["record_digest"] != record_digest:
            raise ValueError("integration_revision_record_changed")
        if prior_source is None:
            obligation = store.read("obligation", root_obligation)
            original = source_record(store, hex_value(obligation["source_custody_digest"]))
            if (revision["prior_revision_digest"] is not None or revision["qualified_projection_digest"] is not None
                    or revision["authorization_digest"] is not None or original.entries != actual
                    or obligation["source_digest"] != core.identity(original)
                    or obligation["record_digest"] != record_digest):
                raise ValueError("integration_revision_root_invalid")
            adoption_id = revision["adoption_digest"]
            if adoption_id is None:
                if current != original:
                    raise ValueError("integration_revision_root_source_changed")
                aliases.update((entry.oid, entry.oid) for entry in current.entries)
            else:
                adoption = store.read("adoption", hex_value(adoption_id))
                projection = projection_record(adoption)
                qualify_projection(objects, original, projection)
                expected = runtime.SourceSeries(original.repository, original.pr_number, projection.base, projection.head,
                    tuple(runtime.SourceEntry(pair.landed, entry.kind, entry.gates)
                          for pair, entry in zip(projection.mapping, original.entries, strict=True)),
                    digest({"adoption_digest": adoption_id, "grant_digest": root_grant, "record_digest": record_digest}))
                if (adoption["grant_digest"] != root_grant or adoption["record_digest"] != record_digest
                        or adoption["original_source_custody_digest"] != obligation["source_custody_digest"]
                        or current != expected):
                    raise ValueError("integration_adoption_custody_changed")
                aliases.update((pair.original, pair.landed) for pair in projection.mapping)
                aliases.update((entry.oid, entry.oid) for entry in current.entries)
        else:
            qualified = store.read("projection", hex_value(revision["qualified_projection_digest"]))
            projection = projection_record(qualified)
            auth_id = hex_value(revision["authorization_digest"])
            auth = store.read("authorization", auth_id)
            if (revision["prior_revision_digest"] != prior_revision
                    or qualified["prior_revision_digest"] != prior_revision
                    or qualified["grant_digest"] != root_grant or qualified["obligation_digest"] != root_obligation
                    or qualified["prior_source_custody_digest"] != revision["prior_source_custody_digest"]
                    or source_record(store, hex_value(revision["prior_source_custody_digest"])) != prior_source
                    or auth["qualified_projection_digest"] != revision["qualified_projection_digest"]
                    or auth["prior_revision_digest"] != prior_revision or auth["grant_digest"] != root_grant
                    or auth["child_cycle_id"] != cycle_id):
                raise ValueError("integration_revision_link_changed")
            authority = digest({"revision_digest": identity, "authorization_digest": auth_id})
            if compose_source(objects, prior_source, projection, actual, authority) != current:
                raise ValueError("integration_revision_composition_changed")
            mapping = {pair.original: pair.landed for pair in projection.mapping}
            if any(value not in mapping for value in aliases.values()):
                raise ValueError("integration_revision_attribution_missing")
            aliases = {original: mapping[value] for original, value in aliases.items()}
            for pair in projection.mapping:
                existing = aliases.get(pair.landed)
                if existing is not None and existing != pair.landed:
                    raise ValueError("integration_revision_alias_ambiguous")
                aliases[pair.landed] = pair.landed
            for entry in actual:
                if entry.oid in aliases:
                    raise ValueError("integration_revision_child_duplicate")
                aliases[entry.oid] = entry.oid
        if len(aliases) > 4096:
            raise ValueError("integration_revision_alias_bound")
        records.append((cycle_id, record_digest))
        prior_source, prior_revision = current, identity
    if current is None:
        raise ValueError("integration_revision_chain_empty")
    return RevisionChain(current, tuple(core.CommitPair(k, v) for k, v in aliases.items()), tuple(records),
                         root_grant, root_obligation, latest_revision)


def accept_verified_outcome(store: Custody, verified: VerifiedOutcome, objects: GitObjects,
                            record_entries: Callable[[str, str], tuple[runtime.SourceEntry, ...]],
                            verified_at: str) -> str:
    """Join fresh native verification to independently re-proved private history.

    The supported helper invokes LocalClient.verify_delivered itself. A serialized
    receipt or a content hash is never accepted as a native verifier replacement.
    """
    from .client import VerifiedOutcome as NativeOutcome
    if type(verified) is not NativeOutcome:
        raise ValueError("integration_native_outcome_required")
    ticket = verified.ticket
    if (ticket.state != runtime.State.DELIVERED or ticket.delivery is None or ticket.projection is None
            or verified.obligation.current_ticket != ticket.handle
            or ticket.delivery.merge_oid != verified.merge_oid
            or verified.mapping != runtime.original_to_landed(ticket)):
        raise ValueError("integration_native_delivery_binding_changed")
    chain = revision_chain(store, ticket.handle, objects, record_entries)
    if (chain.source != ticket.source or chain.grant_digest != verified.obligation.grant_digest
            or store.read("obligation", chain.obligation_digest)["handle"] != verified.obligation.handle):
        raise ValueError("integration_native_outcome_source_changed")
    qualify_projection(objects, chain.source, ticket.projection)
    proof = prove_series(objects, ticket.projection.base, tuple(pair.landed for pair in ticket.projection.mapping),
                         verified.merge_oid, verified.landed_base)
    if proof.pairs != ticket.delivery.mapping or not objects.ancestor(verified.merge_oid, verified.target_head):
        raise ValueError("integration_native_outcome_proof_changed")
    final = {pair.original: pair.landed for pair in verified.mapping}
    if any(pair.landed not in final for pair in chain.aliases):
        raise ValueError("integration_native_outcome_phase_missing")
    mapping = [{"original": pair.original, "landed": final[pair.landed]} for pair in chain.aliases]
    value: dict[str, object] = {"obligation_digest": chain.obligation_digest, "grant_digest": chain.grant_digest,
        "source_digest": core.identity(chain.source), "revision_digest": chain.revision_digest,
        "ticket_handle": ticket.handle, "native_receipt_digest": ticket.delivery.receipt_digest,
        "merge": verified.merge_oid, "landed_base": verified.landed_base, "published_head": ticket.projection.head,
        "published_base": ticket.projection.base, "merged_at": verified.merged_at, "mapping": mapping, "record_digests": dict(chain.records),
        "verified_at": timestamp(verified_at)}
    prior_values: list[dict[str, object]] = []
    for cycle, _ in chain.records:
        try:
            prior_values.append(store.linked("outcome", cycle))
        except FileNotFoundError:
            pass
    if prior_values:
        prior = prior_values[0]
        if any(old != prior for old in prior_values) or any(prior[k] != value[k] for k in value if k != "verified_at"):
            raise ValueError("integration_native_outcome_immutable_conflict")
        value = prior
    identity = store.write("outcome", value)
    for cycle, _ in chain.records:
        store.link("outcome", cycle, identity)
    check: dict[str, object] = {"outcome_digest": identity, "verification_digest": verified.verification_digest,
        "ledger_head": verified.ledger_head, "target_head": verified.target_head, "checked_at": timestamp(verified_at)}
    try:
        existing_check = store.linked("outcome_check", verified.verification_digest)
    except FileNotFoundError:
        existing_check = None
    if existing_check is not None:
        if any(existing_check[k] != check[k] for k in check if k != "checked_at"):
            raise ValueError("integration_native_verification_changed")
        check = existing_check
    check_id = store.write("outcome_check", check)
    store.link("outcome_check", verified.verification_digest, check_id)
    return identity


def verify_outcome(store: Custody, outcome_identity: str, objects: GitObjects,
                   record_entries: Callable[[str, str], tuple[runtime.SourceEntry, ...]]) -> tuple[dict[str, object], tuple[core.CommitPair, ...]]:
    """Re-prove retained correspondence; this is never fresh native authority."""
    value = store.read("outcome", outcome_identity)
    chain = revision_chain(store, text(value["ticket_handle"]), objects, record_entries)
    if (value["grant_digest"] != chain.grant_digest or value["obligation_digest"] != chain.obligation_digest
            or value["source_digest"] != core.identity(chain.source) or value["revision_digest"] != chain.revision_digest
            or value["record_digests"] != dict(chain.records)):
        raise ValueError("integration_retained_outcome_custody_changed")
    refreshed = prove_series(objects, chain.source.base, tuple(e.oid for e in chain.source.entries),
        hex_value(value["published_head"], (40, 64)), hex_value(value["published_base"], (40, 64)))
    landed = prove_series(objects, refreshed.base, tuple(p.landed for p in refreshed.pairs),
        hex_value(value["merge"], (40, 64)), hex_value(value["landed_base"], (40, 64)))
    current_to_published = {p.original: p.landed for p in refreshed.pairs}
    published_to_landed = {p.original: p.landed for p in landed.pairs}
    mapping = tuple(core.CommitPair(pair.original, published_to_landed[current_to_published[pair.landed]])
                    for pair in chain.aliases)
    if value["mapping"] != [{"original": p.original, "landed": p.landed} for p in mapping]:
        raise ValueError("integration_retained_outcome_mapping_changed")
    return value, mapping
