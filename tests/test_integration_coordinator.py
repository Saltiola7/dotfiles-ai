"""Offline model contracts; fixtures do not establish native forge authority."""
from dataclasses import FrozenInstanceError, asdict, replace
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from hypothesis import given, settings, strategies as st
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as c


def oid(n: int) -> str:
    return f"{n:040x}"


def digest(n: int) -> str:
    return f"{n:064x}"


def handle(n: int) -> str:
    return f"{n:032x}"


def source(n: int = 1) -> c.SourceSeries:
    return c.SourceSeries("example/repo", n, oid(n * 10 + 2),
                          (oid(n * 10 + 1), oid(n * 10 + 2)), (), digest(1))


def empty() -> c.Snapshot:
    return c.Snapshot(c.Target("example/repo", "main", oid(900), digest(2)), ())


def requested(n: int = 1) -> c.Ticket:
    return c.Ticket(handle(n), source(n), digest(3))


def queued(count: int = 1) -> c.Snapshot:
    state = empty()
    for n in range(1, count + 1):
        ticket = requested(n)
        state = c.request(state, ticket)
        binding = c.Admission(c.identity(ticket.source), ticket.requester_digest,
                              state.target.policy_digest, digest(4))
        state = c.admit(state, ticket.handle, binding)
    return state


def candidate(state: c.Snapshot, n: int = 1) -> c.Candidate:
    ticket = state.ticket(handle(n))
    return c.Candidate(state.target.generation + 1, c.identity(ticket.source),
                       ticket.source.head, oid(900), oid(901), (oid(900), ticket.source.head),
                       oid(902), digest(5), state.target.policy_digest)


def claimed(count: int = 1) -> c.Snapshot:
    state = queued(count)
    return c.claim(state, handle(1), candidate(state))


def qualification(state: c.Snapshot) -> c.Qualification:
    ticket = state.ticket(handle(1))
    assert ticket.candidate is not None
    native = c.Evidence("check", 7, 8, 1, ticket.candidate.tested_oid, digest(6))
    return c.Qualification(c.identity(ticket.candidate), ticket.candidate.plan_digest,
                           ticket.candidate.policy_digest, digest(7), (native,))


def reserved() -> c.Snapshot:
    state = claimed(2)
    return c.reserve_merge(state, handle(1), 1, qualification(state), handle(501), handle(601))


def test_twelve_tasks_remain_concurrent_but_only_one_candidate_can_claim() -> None:
    state = queued(12)
    assert state.target.queue == tuple(handle(i) for i in range(1, 13))
    assert [t.sequence for t in state.tickets] == list(range(1, 13))
    active = c.claim(state, handle(1), candidate(state))
    assert len(active.target.queue) == 11
    assert state.target.active is None
    with pytest.raises(c.Conflict):
        c.claim(active, handle(2), candidate(active, 2))
    with pytest.raises(c.Conflict):
        c.claim(state, handle(2), candidate(state, 2))


def test_duplicate_request_is_idempotent_after_admission_and_rejects_new_identity() -> None:
    state = queued()
    assert c.request(state, requested()) == state
    assert c.admit(state, handle(1), c.Admission(c.identity(source()), digest(3), digest(2), digest(4))) == state
    with pytest.raises(c.Conflict):
        c.request(state, replace(requested(), requester_digest=digest(99)))


def test_wrong_admission_binding_does_not_modify_requested_state() -> None:
    state = c.request(empty(), requested())
    with pytest.raises(c.Conflict):
        c.admit(state, handle(1), c.Admission(digest(99), digest(3), digest(2), digest(4)))
    assert state.target.queue == ()
    assert state.ticket(handle(1)).state == c.State.REQUESTED


def test_failure_releases_only_known_unreserved_candidate_and_retains_evidence() -> None:
    state = claimed(2)
    repaired = c.record_failure(state, handle(1), 1, digest(99))
    assert repaired.target.active is None
    assert repaired.ticket(handle(1)).failure_digest == digest(99)
    assert repaired.ticket(handle(1)).state == c.State.REPAIR_PENDING
    following = c.claim(repaired, handle(2), candidate(repaired, 2))
    assert following.target.generation == 2
    assert state.target.active == handle(1)


def test_invalidation_discards_qualification_and_monotonically_advances_generation() -> None:
    first = claimed()
    invalid = c.invalidate(first, handle(1), 1)
    second = c.claim(invalid, handle(1), candidate(invalid))
    assert second.target.generation == 2
    with pytest.raises(c.Conflict):
        c.reserve_merge(second, handle(1), 2, qualification(first), handle(501), handle(601))
    with pytest.raises(c.Conflict):
        c.record_failure(second, handle(1), 1, digest(99))


@pytest.mark.parametrize("change", ["source_digest", "head", "policy_digest", "generation"])
def test_wrong_candidate_binding_is_rejected(change: str) -> None:
    state = queued()
    proposed = candidate(state)
    value = 99 if change == "generation" else oid(99) if change == "head" else digest(99)
    with pytest.raises((c.Invalid, c.Conflict)):
        c.claim(state, handle(1), replace(proposed, **{change: value}))


def test_operator_wait_retains_same_slot_and_requires_fresh_qualification() -> None:
    state = c.wait_for_operator(claimed(2), handle(1), 1)
    assert state.target.active == handle(1)
    assert state.ticket(handle(1)).state == c.State.AWAITING_OPERATOR
    result = c.reserve_merge(state, handle(1), 1, qualification(state), handle(501), handle(601))
    assert result.ticket(handle(1)).reservation is not None


def test_uncertain_mutation_has_no_age_based_takeover_or_failure_release() -> None:
    state = c.mark_uncertain(reserved(), handle(1), 1, handle(501))
    assert state.ticket(handle(1)).state == c.State.MERGE_UNCERTAIN
    for action in (lambda: c.invalidate(state, handle(1), 1),
                   lambda: c.record_failure(state, handle(1), 1, digest(99)),
                   lambda: c.claim(state, handle(2), candidate(state, 2)),
                   lambda: c.reserve_merge(state, handle(1), 1, qualification(state), handle(502), handle(602))):
        with pytest.raises(c.Conflict):
            action()
    assert c.decode("ticket", c.encode(state.ticket(handle(1)))) == state.ticket(handle(1))


def test_no_effect_reconciliation_requires_exact_operation_invocation_and_candidate() -> None:
    state = c.mark_uncertain(reserved(), handle(1), 1, handle(501))
    ticket = state.ticket(handle(1))
    assert ticket.candidate is not None
    proof = c.NoEffect(handle(501), handle(601), c.identity(ticket.candidate), digest(8))
    with pytest.raises(c.Conflict):
        c.resolve_no_effect(state, handle(1), 1, replace(proof, invocation_id=handle(602)))
    cleared = c.resolve_no_effect(state, handle(1), 1, proof)
    assert cleared.target.active == handle(1)
    assert cleared.ticket(handle(1)).reservation is None
    assert cleared.ticket(handle(1)).qualification is None


def delivery(state: c.Snapshot) -> c.Delivery:
    ticket = state.ticket(handle(1))
    assert ticket.candidate is not None
    mapping = tuple(c.CommitPair(old, oid(800 + i)) for i, old in enumerate(ticket.source.phase_commits))
    return c.Delivery(c.identity(ticket.candidate), 1, oid(801), mapping, digest(8), handle(501), handle(601))


def test_delivery_preserves_each_phase_and_claims_no_local_cleanup() -> None:
    state = reserved()
    proof = delivery(state)
    result = c.record_delivery(state, handle(1), 1, proof)
    ticket = result.ticket(handle(1))
    assert ticket.state == c.State.DELIVERED
    assert ticket.source == source()
    assert ticket.delivery == proof
    assert result.target.active is None
    assert "cleanup" not in json.dumps(asdict(ticket))
    assert state.target.active == handle(1)
    with pytest.raises(c.Conflict):
        c.record_delivery(state, handle(1), 1, replace(proof, phase_map=tuple(reversed(proof.phase_map))))
    with pytest.raises(c.Conflict):
        c.record_delivery(state, handle(1), 1, replace(proof, pr_number=2))


def test_phase_ids_and_wrappers_are_disjoint_and_keep_original_order() -> None:
    original = source()
    wrapped = replace(original, head=oid(50), wrappers=(oid(40), oid(50)))
    assert wrapped.phase_commits == original.phase_commits
    with pytest.raises(c.Invalid):
        replace(original, wrappers=(original.phase_commits[0],))
    with pytest.raises(c.Invalid):
        replace(original, phase_commits=(original.head, original.head))
    with pytest.raises(c.Invalid):
        replace(original, phase_commits=())


def test_append_is_expected_tip_guarded_and_durably_records_operation_identity() -> None:
    before = empty()
    after = c.request(before, requested())
    request = c.build_append(before, after, oid(950), "dbsctr/integration-state", handle(701))
    payload = request.graphql()
    assert payload["expectedHeadOid"] == oid(950)
    assert payload["branch"] == {"repositoryNameWithOwner": "example/repo", "branchName": "dbsctr/integration-state"}
    changes = payload["fileChanges"]
    assert isinstance(changes, dict)
    additions = changes["additions"]
    assert isinstance(additions, list)
    assert {a["path"] for a in additions} == {"integration/v1/target.json", f"integration/v1/tickets/{handle(1)}.json"}
    target = next(a for a in additions if a["path"].endswith("target.json"))
    stored = c.decode("target", base64.b64decode(target["contents"]))
    assert isinstance(stored, c.Target)
    assert stored.last_operation == handle(701)
    assert request.state.target.last_operation == handle(701)
    assert before.target.last_operation is None


def test_contending_appends_share_guard_and_recomputed_loser_retains_winner() -> None:
    before = empty()
    first = c.build_append(before, c.request(before, requested()), oid(950), "state", handle(701))
    second = c.build_append(before, c.request(before, requested(2)), oid(950), "state", handle(702))
    current_tip = oid(951)
    committed = first.state
    # Construction binds both writers; only the later native store can prove CAS.
    assert first.expected_head == second.expected_head == oid(950)
    assert second.expected_head != current_tip
    reloaded = c.request(committed, requested(2))
    retry = c.build_append(committed, reloaded, current_tip, "state", handle(703))
    assert {t.handle for t in retry.state.tickets} == {handle(1), handle(2)}
    assert len(second.state.tickets) == 1


@pytest.mark.parametrize("raw", [b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}',
                                 b'{"x":Infinity}', b'\xff', b'[' * 2000])
def test_bad_json_is_bounded_refusal(raw: bytes) -> None:
    with pytest.raises(c.Invalid):
        c.decode("target", raw)


def test_unknown_fields_boolean_integers_raw_and_canonical_limits() -> None:
    record = asdict(source())
    record["enabled"] = True
    with pytest.raises(c.Invalid):
        c.decode("source", json.dumps(record).encode())
    with pytest.raises(c.Invalid):
        replace(source(), pr_number=True)
    with pytest.raises(c.Invalid):
        c.decode("target", b" " * (64 * 1024 + 1))
    with pytest.raises(c.Invalid):
        replace(empty().target, queue=tuple(handle(n) for n in range(1, 258)))
    with pytest.raises(c.Invalid):
        replace(empty().target, default_branch="../escape")
    with pytest.raises(c.Invalid):
        replace(source(), wrappers=[oid(20)])


def test_snapshot_refuses_missing_ticket_duplicate_queue_and_false_counts() -> None:
    state = queued()
    with pytest.raises(c.Invalid):
        c.Snapshot(state.target, ())
    with pytest.raises(c.Invalid):
        replace(state.target, queue=(handle(1), handle(1)))
    with pytest.raises(c.Invalid):
        c.Snapshot(replace(state.target, retained_count=2), state.tickets)
    with pytest.raises(FrozenInstanceError):
        setattr(state.target, "generation", 12)


@given(st.lists(st.integers(min_value=1, max_value=2**64), min_size=1, max_size=30, unique=True))
def test_source_roundtrip_and_identity_do_not_depend_on_input_key_order(values: list[int]) -> None:
    phases = tuple(oid(n) for n in values)
    value = c.SourceSeries("example/repo", 1, phases[-1], phases, (), digest(1))
    encoded = c.encode(value)
    assert c.decode("source", encoded) == value
    reverse_keys = dict(reversed(list(asdict(value).items())))
    assert c.decode("source", json.dumps(reverse_keys).encode()) == value
    assert hashlib.sha256(encoded).hexdigest() == c.identity(value)


def run_cli(*args: str, data: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, str(ROOT / "dot_local/bin/executable_dbsctr-integration"), *args],
                          input=data, capture_output=True, timeout=10, env=os.environ.copy())


def test_offline_cli_reports_structural_status_and_refuses_live_before_input() -> None:
    result = run_cli("validate", "--kind", "source", data=c.encode(source()))
    assert result.returncode == 0
    assert json.loads(result.stdout)["authority"] == "structural_only"
    status = run_cli("status", data=c.encode(queued(2).target))
    assert status.returncode == 0
    assert json.loads(status.stdout)["authority"] == "unverified"
    assert json.loads(status.stdout)["queued"] == 2
    for operation in ("submit", "adopt", "advance", "reconcile", "operator-resume"):
        result = run_cli(operation, data=b"PRIVATE_SENTINEL\xff")
        assert result.returncode == 78
        assert result.stdout == b""
        assert result.stderr == b"dbsctr-integration: live_adapters_unavailable\n"
    invalid = run_cli("validate", "--kind", "source", data=b"PRIVATE_SENTINEL")
    assert invalid.returncode == 2
    assert b"PRIVATE_SENTINEL" not in invalid.stderr


def test_reserved_operation_identity_cannot_be_reused_after_no_effect() -> None:
    state = reserved()
    ticket = state.ticket(handle(1))
    assert ticket.candidate is not None
    proof = c.NoEffect(handle(501), handle(601), c.identity(ticket.candidate), digest(8))
    cleared = c.resolve_no_effect(state, handle(1), 1, proof)
    assert cleared.ticket(handle(1)).reconciliations == (proof,)
    with pytest.raises(c.Conflict):
        c.reserve_merge(cleared, handle(1), 1, qualification(cleared), handle(501), handle(602))


def test_stale_delivery_callback_cannot_finish_a_new_operation_in_same_generation() -> None:
    first = reserved()
    ticket = first.ticket(handle(1))
    assert ticket.candidate is not None
    no_effect = c.NoEffect(handle(501), handle(601), c.identity(ticket.candidate), digest(8))
    cleared = c.resolve_no_effect(first, handle(1), 1, no_effect)
    second = c.reserve_merge(cleared, handle(1), 1, qualification(cleared), handle(502), handle(602))
    with pytest.raises(c.Conflict):
        c.record_delivery(second, handle(1), 1, delivery(first))


def test_cas_constructor_rejects_a_forged_snapshot_that_drops_mutation_custody() -> None:
    before = reserved()
    first = before.ticket(handle(1))
    forged_ticket = replace(first, state=c.State.QUEUED, candidate=None, qualification=None, reservation=None)
    forged = c.Snapshot(replace(before.target, active=None, queue=(handle(1), handle(2))),
                        (forged_ticket, before.ticket(handle(2))))
    with pytest.raises(c.Conflict):
        c.build_append(before, forged, oid(950), "state", handle(701))
    assert before.ticket(handle(1)).reservation is not None


def test_append_cannot_target_default_branch_or_generate_arbitrary_files() -> None:
    before = empty()
    after = c.request(before, requested())
    for branch in ("main", "refs/heads/main", "../escape", "state.lock"):
        with pytest.raises((c.Conflict, c.Invalid)):
            c.build_append(before, after, oid(950), branch, handle(701))
    request = c.build_append(before, after, oid(950), "state", handle(701))
    with pytest.raises((c.Invalid, TypeError)):
        replace(request, additions=((".github/workflows/execute.yaml", "eA=="),))


def test_closed_receipt_fields_roundtrip_and_admission_proof_is_retained() -> None:
    state = queued()
    assert state.ticket(handle(1)).admission_digest == digest(4)
    for state in (queued(), claimed(), reserved(), c.record_delivery(reserved(), handle(1), 1, delivery(reserved()))):
        ticket = state.ticket(handle(1))
        assert c.decode("ticket", c.encode(ticket)) == ticket
    rejected = c.reject(c.request(empty(), requested()), handle(1), digest(99))
    assert rejected.ticket(handle(1)).state == c.State.REJECTED
    assert rejected.target.retained_count == 1


def test_boolean_generation_is_not_a_freshness_guard() -> None:
    with pytest.raises(c.Invalid):
        c.record_failure(claimed(), handle(1), True, digest(99))


def test_live_refusal_does_not_access_stdin_or_activation_environment(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from integration_coordinator import cli

    class ForbiddenInput:
        @property
        def buffer(self) -> object:
            raise AssertionError("stdin touched before unavailable")

    monkeypatch.setattr(cli.sys, "stdin", ForbiddenInput())
    monkeypatch.setenv("DBSCTR_INTEGRATION_ENABLED", "true")
    assert cli.main(["advance"]) == 78
    assert "live_adapters_unavailable" in capsys.readouterr().err


def test_incomplete_source_owner_refuses_before_installed_fallback(tmp_path: Path) -> None:
    root = tmp_path / "source"
    executable = root / "dot_local/bin/executable_dbsctr-integration"
    executable.parent.mkdir(parents=True)
    executable.write_bytes((ROOT / "dot_local/bin/executable_dbsctr-integration").read_bytes())
    incomplete = root / "private_dot_config/dotfiles-ai/integration_coordinator"
    incomplete.mkdir(parents=True)
    (incomplete / "__init__.py").write_text("")
    installed = tmp_path / "home/.config/dotfiles-ai/integration_coordinator"
    installed.mkdir(parents=True)
    for name in ("__init__.py", "core.py", "cli.py"):
        (installed / name).write_text('raise AssertionError("installed owner executed")\n')
    result = subprocess.run([sys.executable, str(executable), "status"],
        input=b"", capture_output=True, timeout=10, env={**os.environ, "HOME": str(tmp_path / "home")})
    assert result.returncode == 78
    assert result.stderr == b"dbsctr-integration: module_unavailable\n"


def test_append_cannot_omit_required_ticket_write() -> None:
    request = c.build_append(empty(), c.request(empty(), requested()), oid(950), "state", handle(701))
    target_only = tuple(pair for pair in request.additions if pair[0].endswith("target.json"))
    with pytest.raises((c.Invalid, TypeError)):
        replace(request, additions=target_only)


def test_target_requires_unqualified_default_branch_name() -> None:
    with pytest.raises(c.Invalid):
        replace(empty().target, default_branch="refs/heads/main")


def test_large_phase_series_cannot_reserve_unrepresentable_delivery() -> None:
    phases = tuple(oid(n) for n in range(10000, 11024))
    big = c.SourceSeries("example/repo", 1, phases[-1], phases, (), digest(1))
    ticket = c.Ticket(handle(1), big, digest(3))
    state = c.request(empty(), ticket)
    state = c.admit(state, handle(1), c.Admission(c.identity(big), digest(3), digest(2), digest(4)))
    state = c.claim(state, handle(1), candidate(state))
    with pytest.raises(c.Conflict):
        c.reserve_merge(state, handle(1), 1, qualification(state), handle(501), handle(601))
    assert state.ticket(handle(1)).reservation is None
    assert state.ticket(handle(1)).source.phase_commits == phases


def test_reservation_retains_room_for_another_no_effect_receipt() -> None:
    state = claimed()
    original = state.ticket(handle(1))
    assert original.candidate is not None
    receipts = tuple(c.NoEffect(f"{n:016x}", "0000000000000001", c.identity(original.candidate), digest(8))
                     for n in range(10000, 10512))
    ticket = replace(original, reconciliations=receipts)
    state = c.Snapshot(state.target, (ticket,))
    with pytest.raises(c.Conflict):
        c.reserve_merge(state, handle(1), 1, qualification(state), handle(501), handle(601))
    assert state.ticket(handle(1)).reconciliations == receipts


@given(st.integers(min_value=1, max_value=1024), st.integers(min_value=16, max_value=64))
@settings(max_examples=40, deadline=None)
def test_every_reserved_series_can_represent_each_native_outcome(count: int, width: int) -> None:
    phases = tuple(oid(n) for n in range(10000, 10000 + count))
    series = c.SourceSeries("example/repo", 1, phases[-1], phases, (), digest(1))
    state = c.request(empty(), c.Ticket(handle(1), series, digest(3)))
    state = c.admit(state, handle(1), c.Admission(c.identity(series), digest(3), digest(2), digest(4)))
    state = c.claim(state, handle(1), candidate(state))
    operation = f"{501:0{width}x}"
    invocation = f"{601:0{width}x}"
    try:
        active = c.reserve_merge(state, handle(1), 1, qualification(state), operation, invocation)
    except c.Conflict as error:
        assert str(error) == "outcome_capacity"
        assert state.ticket(handle(1)).reservation is None
        return
    uncertain = c.mark_uncertain(active, handle(1), 1, operation)
    current = active.ticket(handle(1)).candidate
    assert current is not None
    no_effect = c.NoEffect(operation, invocation, c.identity(current), digest(8))
    reconciled = c.resolve_no_effect(uncertain, handle(1), 1, no_effect)
    mapping = tuple(c.CommitPair(old, oid(100000 + i)) for i, old in enumerate(phases))
    proof = c.Delivery(c.identity(current), 1, mapping[-1].landed, mapping, digest(8), operation, invocation)
    delivered = c.record_delivery(uncertain, handle(1), 1, proof)
    for result in (uncertain, reconciled, delivered):
        ticket = result.ticket(handle(1))
        assert len(c.encode(ticket)) <= c.RECORD_LIMIT
        assert c.decode("ticket", c.encode(ticket)) == ticket
