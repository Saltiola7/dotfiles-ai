"""Fixture-only checks of the original Initiative boundary at protected effects."""

from contextlib import contextmanager
from dataclasses import replace
from typing import Never

import pytest

from test_integration_client import Remote
from test_integration_controller import FakeAdapter, FakeHost, config, digest, handle, oid, requested
from test_integration_github import ControlGitHub, MutationGitHub, admission_append, reserved_state
from integration_coordinator import client, controller as h, core as c, github as g, runtime as r


def local_config() -> h.HostedConfig:
    selected = replace(config(), initiative_local=True)
    assert selected.enrollment is not None
    return replace(selected, enrollment=replace(selected.enrollment, policy_digest=h.policy_identity(selected)))


def test_local_enrollment_is_digest_bound_and_old_shape_stays_unchanged() -> None:
    legacy = config()
    local = local_config()
    assert "initiative_local" not in h._config_data(legacy)
    assert h._config_data(local)["initiative_local"] is True
    assert h.policy_identity(local) != h.policy_identity(legacy)
    assert h.parse_config(c._canonical(h._config_data(local))) == local
    changed = h._config_data(local)
    del changed["initiative_local"]
    with pytest.raises(c.Invalid):
        h.parse_config(c._canonical(changed))


def test_hosted_run_refuses_before_reading_context_dispatch_or_credentials() -> None:
    def forbidden() -> Never:
        raise AssertionError("local-only repository must not start a hosted worker")

    with pytest.raises(c.Unavailable, match="initiative_private_authority_required"):
        h.run(local_config(), forbidden, forbidden, forbidden, forbidden)


def test_default_client_does_not_dispatch_to_hosted_local_only_enrollment() -> None:
    remote = Remote()
    remote.config = local_config()
    remote.payload = c._canonical(h._config_data(remote.config))
    with pytest.raises(c.Unavailable, match="initiative_private_authority_required"):
        client.LocalClient(remote, remote.local_policy()).submit(remote.source_request())
    assert all(method == "GET" for method, _, _ in remote.calls)


def test_current_policy_reads_local_only_bit_from_native_default() -> None:
    remote = Remote()
    remote.config = local_config()
    remote.payload = c._canonical(h._config_data(remote.config))
    _, adapter = client.LocalClient(remote, remote.local_policy()).configuration()
    assert adapter._current_enrollment() is True
    assert all(method == "GET" for method, _, _ in remote.calls)


class Guard:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.inside = False
        self.calls: list[tuple[str, r.Ticket, r.Obligation, r.NativeReservation | None]] = []

    @contextmanager
    def __call__(self, operation, ticket, obligation, reservation):
        self.calls.append((operation, ticket, obligation, reservation))
        if not self.allowed:
            raise c.Unavailable("initiative_grant_stopped")
        self.inside = True
        try:
            yield
        finally:
            self.inside = False


class LocalControlGitHub(ControlGitHub):
    def _current_enrollment(self):
        return True


@pytest.mark.parametrize("allowed", [None, False, True])
def test_exact_admission_rechecks_under_lock_at_native_cas(allowed, monkeypatch) -> None:
    request = admission_append()
    api = LocalControlGitHub(request)
    guard = None if allowed is None else Guard(allowed)
    api.initiative_guard = guard
    original_request = api.transport.request

    def requires_lock(*args):
        assert guard is not None and guard.inside
        return original_request(*args)

    monkeypatch.setattr(api.transport, "request", requires_lock)
    if allowed is not True:
        with pytest.raises(c.Unavailable):
            api.append(request)
        assert api.tip == oid(901)
    else:
        assert api.append(request) == oid(902)
    if guard is not None:
        assert len(guard.calls) == 1
        operation, ticket, obligation, reservation = guard.calls[0]
        assert (operation, ticket.handle, obligation.handle, reservation) == ("admit", "6" * 32, "7" * 32, None)
        assert ticket.state is r.State.REQUESTED


class LocalMutationGitHub(MutationGitHub):
    def _current_enrollment(self):
        return True

    def file_at(self, head, path):
        if not path.startswith("integration/v2/obligations/"):
            return super().file_at(head, path)
        native_head, files = self.read_control()
        assert head == native_head
        return files.get(path)


@pytest.mark.parametrize("allowed", [None, False, True])
def test_exact_merge_rechecks_under_lock_at_native_put(allowed, monkeypatch) -> None:
    state = reserved_state(operator=True)
    ticket = state.ticket("1" * 32)
    reservation = ticket.reservation
    assert reservation is not None
    api = LocalMutationGitHub(state)
    guard = None if allowed is None else Guard(allowed)
    api.initiative_guard = guard
    original_write = api._write

    def requires_lock(*args):
        assert guard is not None and guard.inside
        return original_write(*args)

    monkeypatch.setattr(api, "_write", requires_lock)
    if allowed is not True:
        with pytest.raises((c.Unavailable, g.NativeRejection)):
            api.merge(ticket, reservation)
        assert not api.writes
    else:
        assert api.merge(ticket, reservation).merge_oid == oid(30)
        assert len(api.writes) == 1
        guard.allowed = False
        assert api.reconcile(ticket, reservation).merge_oid == oid(30)
    if guard is not None:
        assert guard.calls == [("merge", ticket, state.obligation(ticket.obligation_handle), reservation)]


def test_local_policy_refuses_a_hosted_reservation_even_under_green_checks() -> None:
    state = reserved_state()
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = LocalMutationGitHub(state)
    guard = Guard(True)
    api.initiative_guard = guard
    with pytest.raises(g.NativeRejection):
        api.merge(ticket, ticket.reservation)
    assert not api.writes and not guard.calls


def test_authority_can_stop_after_final_native_candidate_observation(monkeypatch) -> None:
    state = reserved_state(operator=True)
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = LocalMutationGitHub(state)
    guard = Guard(True)
    api.initiative_guard = guard
    original = api._candidate_facts

    def changed(*args):
        result = original(*args)
        guard.allowed = False
        return result

    monkeypatch.setattr(api, "_candidate_facts", changed)
    with pytest.raises(g.NativeRejection):
        api.merge(ticket, ticket.reservation)
    assert not api.writes
    assert len(guard.calls) == 1


def local_subject() -> tuple[h.HostedConfig, FakeAdapter, h.OperatorAuthority, r.Ticket, r.Obligation]:
    selected = local_config()
    assert selected.enrollment is not None
    adapter = FakeAdapter()
    adapter.enrollment = selected.enrollment
    adapter.state = replace(adapter.state, target=replace(adapter.state.target,
                                                          policy_digest=selected.enrollment.policy_digest))
    ticket = replace(requested(), guarded_refresh=False)
    obligation = r.Obligation(ticket.obligation_handle, ticket.handle, digest(77))
    authority = h.OperatorAuthority(r.OperatorInvocation(5, handle(900), digest(81), digest(82)),
                                    digest(83), ticket.handle, 1)
    return selected, adapter, authority, ticket, obligation


def test_local_admission_and_scoped_advance_share_protected_scheduler() -> None:
    selected, adapter, authority, ticket, obligation = local_subject()
    assert h.admit_initiative(selected, authority, adapter, ticket, obligation).status == "accepted"
    assert adapter.state.ticket(ticket.handle).state is r.State.QUEUED
    assert h.admit_initiative(selected, authority, adapter, ticket, obligation).status == "accepted"
    assert len(adapter.writes) == 1
    with pytest.raises(c.Unavailable, match="initiative_private_authority_required"):
        h.advance(selected, authority, FakeHost(), adapter)
    report = h.advance_initiative(selected, authority, FakeHost(), adapter, obligation.handle)
    assert report.status == "delivered"
    assert adapter.merges == 1 and adapter.refreshes == 0


def test_local_advance_cannot_claim_or_merge_another_queued_ticket() -> None:
    selected, adapter, authority, first, obligation = local_subject()
    assert h.admit_initiative(selected, authority, adapter, first, obligation).status == "accepted"
    second = replace(first, handle=handle(2), obligation_handle=handle(102),
                     source=replace(first.source, pr_number=2))
    subject = replace(authority, expected_handle=second.handle)
    second_obligation = r.Obligation(second.obligation_handle, second.handle, digest(88))
    assert h.admit_initiative(selected, subject, adapter, second, second_obligation).status == "accepted"
    report = h.advance_initiative(selected, subject, FakeHost(), adapter, second_obligation.handle)
    assert (report.status, report.detail) == ("waiting", "initiative_candidate_slot_busy")
    assert len(adapter.writes) == 2 and not adapter.merges


@pytest.mark.parametrize("problem", ["admin", "refresh", "repair", "actor", "generation", "ticket"])
def test_local_admission_refuses_out_of_scope_authority_without_cas(problem) -> None:
    selected, adapter, authority, ticket, obligation = local_subject()
    if problem == "admin":
        ticket = replace(ticket, delivery_mode="admin")
    if problem == "refresh":
        ticket = replace(ticket, guarded_refresh=True)
    if problem == "repair":
        obligation = replace(obligation, repair_count=1)
    if problem == "actor":
        authority = replace(authority, invocation=replace(authority.invocation, requester_id=9))
    if problem == "generation":
        authority = replace(authority, expected_generation=2)
    if problem == "ticket":
        authority = replace(authority, expected_handle=handle(78))
    with pytest.raises((c.Unavailable, c.Conflict, c.Invalid)):
        h.admit_initiative(selected, authority, adapter, ticket, obligation)
    assert adapter.writes == []
