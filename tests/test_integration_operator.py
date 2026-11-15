"""Qualified local fallback fixtures never use real credentials or native writes."""
from dataclasses import asdict, replace
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as c, runtime as r, lifecycle as l, controller as h
from integration_coordinator.client import Status
from integration_coordinator import operator as o
from test_integration_controller import FakeAdapter, config, requested, oid, digest, handle


class Identity:
    def __init__(self) -> None:
        self.user: dict[str, object] = {"id": 5, "type": "User", "login": "human"}
        self.calls: list[str] = []

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        assert method == "GET" and path == "user" and body is None
        self.calls.append(path)
        return self.user

    def archive(self, path: str) -> bytes:
        raise AssertionError("operator identity must not download artifacts")


class Local:
    def __init__(self, adapter: FakeAdapter, identity: Identity) -> None:
        self.adapter = adapter
        self.transport = identity
        self.repository = "example/repo"

    def configuration(self) -> tuple[h.HostedConfig, h.Adapter]:
        return config(), self.adapter

    def status(self, ticket_handle: str, obligation_handle: str) -> Status | None:
        ticket = self.adapter.state.lookup_ticket(ticket_handle)
        return Status(self.adapter.tip, ticket, self.adapter.state.obligation(obligation_handle))


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Local, l.Custody, o.TaskBinding]:
    common = tmp_path / "common"
    common.mkdir()
    store = l.Custody(common)
    adapter = FakeAdapter()
    ticket = requested()
    source_object = store.write("source", {"record_digest": digest(11), "descriptor": asdict(ticket.source)})
    obligation_body: dict[str, object] = {"handle": ticket.obligation_handle, "cycle_id": "root-cycle",
        "record_digest": digest(11), "source_digest": c.identity(ticket.source), "source_custody_digest": source_object,
        "original_task_digest": digest(12), "scope_digest": digest(13), "context": "fixture", "risk": "critical",
        "target_ref": "refs/heads/main", "policy_digest": digest(14)}
    obligation_digest = store.write("obligation", obligation_body)
    grant_digest = store.write("grant", {"obligation_digest": obligation_digest, "record_digest": digest(11),
        "context": "fixture", "risk": "critical", "scope_digest": digest(13), "profile_blob": oid(70),
        "plan_digest": digest(15), "policy_digest": digest(14), "enrollment_digest": digest(16),
        "approval_digest": digest(17), "allowed_operations": ["submit", "repair", "accept_outcome", "operator_resume"],
        "authorized_at": "2026-11-13T00:00:00Z"})
    revision_digest = store.write("revision", {"grant_digest": grant_digest, "obligation_digest": obligation_digest,
        "prior_revision_digest": None, "prior_source_custody_digest": source_object, "qualified_projection_digest": None,
        "child_cycle_id": "root-cycle", "child_record_digest": digest(11), "authorization_digest": None, "adoption_digest": None})
    link = store.write("revision_link", {"revision_digest": revision_digest, "source_custody_digest": source_object,
                                        "ticket_handle": ticket.handle})
    store.link("revision_link", ticket.handle, link)
    cfg = config()
    assert cfg.enrollment is not None
    admission = c.Admission(c.identity(ticket.source), ticket.requester_digest, cfg.enrollment.policy_digest, digest(4))
    state = r.admit_authenticated(adapter.state, ticket, r.Obligation(ticket.obligation_handle, ticket.handle, grant_digest), admission)
    state = r.claim(state, ticket.handle, oid(900), adapter.plan.digest)
    adapter.state = r.bind_projection(state, ticket.handle, 1, adapter.projection(ticket.source, ticket.source.head, oid(900)))
    monkeypatch.setattr(o, "_process_context", lambda: digest(99))
    return Local(adapter, Identity()), store, o.TaskBinding(ticket.obligation_handle, digest(12), digest(18))


def test_local_operator_authenticates_human_and_uses_actual_private_pid_before_same_advance(setup: tuple[Local, l.Custody, o.TaskBinding]) -> None:
    client, store, binding = setup
    result = o.resume(client, store, binding, handle(1), 1)
    assert result.status == "delivered" and client.adapter.merges == 1
    delivered = client.adapter.state.lookup_ticket(handle(1))
    assert delivered.delivery is not None
    invocation = delivered.delivery.invocation
    assert isinstance(invocation, r.OperatorInvocation)
    record = store.read("operator", invocation.custody_digest)
    assert record["pid"] == os.getpid()
    assert record["requester_id"] == 5 and record["invocation_id"] == invocation.invocation_id
    assert record["ticket_handle"] == handle(1) and record["generation"] == 1
    assert "run_id" not in record and "token" not in record and "chat_id" not in record
    assert store.object_path(invocation.custody_digest).stat().st_mode & 0o777 == 0o600
    assert client.transport.calls == ["user"]


@pytest.mark.parametrize("change", ["bot", "foreign_user", "task", "handle", "generation", "revoked"])
def test_unqualified_operator_cannot_mutate_or_forge_a_new_task(setup: tuple[Local, l.Custody, o.TaskBinding], change: str) -> None:
    client, store, binding = setup
    selected, generation = handle(1), 1
    if change == "bot": client.transport.user["type"] = "Bot"
    elif change == "foreign_user": client.transport.user["id"] = 9
    elif change == "task": binding = replace(binding, original_task_digest=digest(90))
    elif change == "handle": selected = handle(2)
    elif change == "generation": generation = 2
    elif change == "revoked":
        grant = client.adapter.state.obligation(binding.obligation_handle).grant_digest
        store.revoke(grant, digest(91), "2026-11-13T01:00:00Z")
    count = len(client.adapter.writes)
    with pytest.raises((c.Invalid, c.Conflict, c.Unavailable, ValueError)):
        o.resume(client, store, binding, selected, generation)
    assert len(client.adapter.writes) == count and client.adapter.merges == client.adapter.refreshes == 0


def test_operator_custody_requires_dead_pid_same_task_and_process_authority(setup: tuple[Local, l.Custody, o.TaskBinding], monkeypatch: pytest.MonkeyPatch) -> None:
    client, store, binding = setup
    client.adapter.pending = True
    assert o.resume(client, store, binding, handle(1), 1).status == "waiting"
    # Each record was created by the real local process, not an invented GHA run.
    records = [store.read("operator", path.stem) for path in (store.directory / "objects").glob("*.json")
               if b'"kind":"operator"' in path.read_bytes()]
    assert len(records) == 1
    body = records[0]
    identity = next(path.stem for path in (store.directory / "objects").glob("*.json")
                    if b'"kind":"operator"' in path.read_bytes())
    invocation = r.OperatorInvocation(5, l.text(body["invocation_id"]), identity, l.hex_value(body["scope_digest"]))
    cfg, _ = client.configuration()
    status = client.status(handle(1), binding.obligation_handle)
    assert status is not None
    proof = o.OperationCustody(client, store, binding, cfg, status)
    monkeypatch.setattr(o, "_pid_dead", lambda pid: False)
    assert proof.quiescent(invocation) is False
    monkeypatch.setattr(o, "_pid_dead", lambda pid: True)
    assert proof.quiescent(invocation) is True
    monkeypatch.setattr(o, "_process_context", lambda: digest(98))
    with pytest.raises(c.Unavailable):
        proof.quiescent(invocation)
    with pytest.raises((c.Unavailable, ValueError)):
        proof.quiescent(replace(invocation, scope_digest=digest(97)))


def test_native_human_membership_does_not_invent_an_operator_grant(setup: tuple[Local, l.Custody, o.TaskBinding]) -> None:
    client, store, binding = setup
    original = client.adapter.state.obligation(binding.obligation_handle)
    grant = store.read("grant", original.grant_digest)
    without = store.write("grant", {**grant, "allowed_operations": ["submit", "repair", "accept_outcome"]})
    client.adapter.state = replace(client.adapter.state,
        obligations=(replace(original, grant_digest=without),))
    with pytest.raises(c.Unavailable):
        o.resume(client, store, binding, handle(1), 1)
    assert client.adapter.writes == [] and client.adapter.merges == 0


@pytest.mark.parametrize("error,dead", [(None, False), (3, True), (1, False), (5, False)])
def test_pid_probe_only_treats_native_esrch_as_dead(monkeypatch: pytest.MonkeyPatch, error: int | None, dead: bool) -> None:
    def probe(pid: int, signal: int) -> None:
        assert pid == 123 and signal == 0
        if error is not None:
            raise OSError(error, "fixture")
    monkeypatch.setattr(o.os, "kill", probe)
    assert o._pid_dead(123) is dead
    with pytest.raises(c.Invalid):
        o._pid_dead(0)
