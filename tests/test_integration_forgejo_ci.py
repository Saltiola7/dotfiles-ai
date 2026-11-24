"""Fixture-only Forgejo status and independently supplied CI execution facts."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, forgejo, forgejo_ci as ci, runtime


ORIGIN = "https://forge.example.invalid:8443"
REPOSITORY = "fixture/reference"
TARGET = "refs/heads/main"
TESTED = "c" * 40
POLICY = "d" * 64
OBSERVED = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
STARTED = OBSERVED - timedelta(seconds=60)
ENDED = OBSERVED - timedelta(seconds=5)
RUN_URL = f"{ORIGIN}/{REPOSITORY}/actions/runs/101"
ENDPOINT = f"/api/v1/repos/{REPOSITORY}/statuses/{TESTED}"


@pytest.fixture
def planned():
    binding = forgejo.Binding(ORIGIN, REPOSITORY, 42, "git-actor", "api-actor")
    checks = (
        ci.RequiredCheck("build", 71, "7" * 64, "a" * 64),
        ci.RequiredCheck("verify", 72, "8" * 64, "b" * 64),
    )
    plan = ci.CheckPlan(binding, TARGET, POLICY, checks)
    base, head = "a" * 40, "b" * 40
    candidate = runtime.Candidate(
        3, "5" * 64, "6" * 64, head, base, TESTED, (base, head), "e" * 40,
        core.identity(plan), POLICY,
    )
    return ci.Subject(binding, TARGET, 7, candidate), plan


def path(page):
    return f"{ENDPOINT}?page={page}&limit=50"


def status_for(check, status_id, *, native_state="success", creator_id=None, url=RUN_URL):
    return {
        "id": status_id,
        "status": native_state,
        "context": check.context,
        "creator": {"id": check.creator_id if creator_id is None else creator_id},
        "created_at": STARTED.isoformat(),
        "target_url": url,
    }


def page(rows, *, total=None, headers=None):
    count = str(len(rows) if total is None else total)
    return forgejo.Response(200, rows, {"X-Total-Count": count, **(headers or {})})


def completed(subject, check, status_id, *, conclusion="success", run=101):
    invocation = runtime.Invocation(run, 2, "1" * 32, check.definition_digest)
    receipt = ci.ExecutionReceipt(subject, check.context, status_id, check.producer_digest,
                                  invocation, True, conclusion, completed_at=ENDED)
    return ci.Execution(subject, check.context, check.producer_digest, invocation,
                        "completed", (receipt,), started_at=STARTED)


class Transport:
    def __init__(self, binding, *pages):
        self.binding = binding
        self.pages = list(pages)
        self.calls = []

    def request(self, method, requested_path, body=None):
        self.calls.append((method, requested_path))
        assert method == "GET" and body is None
        assert requested_path == path(len(self.calls))
        assert self.pages, f"unexpected request for {requested_path}"
        response = self.pages.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class Reader:
    def __init__(self, executions):
        self.executions = executions
        self.calls = []

    def current_execution(self, subject, check):
        self.calls.append((subject, check))
        observed = self.executions.get(check.context)
        if isinstance(observed, Exception):
            raise observed
        return observed


def assess(subject, plan, transport, reader):
    return ci.assess_ci(subject, plan, transport, reader, observed_at=OBSERVED)


def test_all_required_executions_match_exact_candidate_and_produce_forgejo_evidence(planned):
    subject, plan = planned
    build, verify = plan.checks
    build_execution = completed(subject, build, 11)
    verify_execution = completed(subject, verify, 12, run=102)
    reader = Reader({"build": build_execution, "verify": verify_execution})
    transport = Transport(subject.binding, page([status_for(build, 11), status_for(verify, 12)]))

    result = assess(subject, plan, transport, reader)

    assert result.subject == subject
    assert result.state == "passed"
    assert result.observed_at == OBSERVED
    assert transport.calls == [("GET", path(1))]
    assert reader.calls == [(subject, build), (subject, verify)]
    checks = {check.context: check for check in result.checks}
    for execution in (build_execution, verify_execution):
        check = checks[execution.context]
        receipt = execution.receipts[0]
        assert (check.state, check.native_state, check.status_id) == ("passed", "success", receipt.status_id)
        assert (check.run_id, check.attempt) == (execution.invocation.run_id, execution.invocation.attempt)
        assert check.receipt == receipt
        assert check.receipt.provider == "forgejo"
        assert check.created_at == STARTED
        assert check.diagnostic_url == RUN_URL


def test_later_required_failure_wins_despite_first_successful_clamped_page(planned):
    subject, plan = planned
    build, verify = plan.checks
    link = f'<{ORIGIN}{path(2)}>; rel="next", <{ORIGIN}{path(2)}>; rel="last"'
    transport = Transport(
        subject.binding,
        page([status_for(build, 11)], total=2, headers={"Link": link}),
        page([status_for(verify, 12, native_state="failure")], total=2),
    )
    reader = Reader({"build": completed(subject, build, 11),
                     "verify": completed(subject, verify, 12, conclusion="failure", run=102)})

    result = assess(subject, plan, transport, reader)

    assert result.state == "failed"
    assert transport.calls == [("GET", path(1)), ("GET", path(2))]
    assert {check.context: check.state for check in result.checks} == {"build": "passed", "verify": "failed"}


@pytest.mark.parametrize("problem", ["missing_next", "foreign_next", "contradictory_last", "duplicate_id"])
def test_incomplete_or_untrusted_pagination_never_qualifies_first_page(planned, problem):
    subject, plan = planned
    build, verify = plan.checks
    first = [status_for(build, 11), status_for(verify, 12)]
    total = len(first) + 1
    headers = {}
    pages = []
    if problem == "foreign_next":
        headers["Link"] = f'<https://other.example.invalid{path(2)}>; rel="next"'
    elif problem == "contradictory_last":
        total = len(first)
        headers["Link"] = f'<{ORIGIN}{path(2)}>; rel="last"'
    elif problem == "duplicate_id":
        headers["Link"] = f'<{ORIGIN}{path(2)}>; rel="next"'
        pages = [page([status_for(build, 11)], total=total)]
    transport = Transport(subject.binding, page(first, total=total, headers=headers), *pages)
    reader = Reader({"build": completed(subject, build, 11), "verify": completed(subject, verify, 12)})

    result = assess(subject, plan, transport, reader)

    assert result.state == "unavailable"
    assert reader.calls == []


@pytest.mark.parametrize("problem", ["binding", "target", "plan", "policy"])
def test_stale_subject_or_scope_short_circuits_native_and_receipt_reads(planned, problem):
    subject, plan = planned
    binding = subject.binding
    if problem == "binding":
        binding = replace(binding, repository_id=43)
    elif problem == "target":
        subject = replace(subject, target_ref="refs/heads/other")
    elif problem == "plan":
        subject = replace(subject, candidate=replace(subject.candidate, plan_digest="0" * 64))
    else:
        subject = replace(subject, candidate=replace(subject.candidate, policy_digest="0" * 64))
    transport = Transport(binding)
    reader = Reader({})

    result = assess(subject, plan, transport, reader)

    assert result.state == "stale"
    assert transport.calls == []
    assert reader.calls == []


@pytest.mark.parametrize("duplicate", [False, True])
def test_plan_cannot_qualify_an_empty_or_ambiguous_required_set(planned, duplicate):
    _, plan = planned
    checks = (plan.checks[0], plan.checks[0]) if duplicate else ()
    with pytest.raises(core.Invalid):
        replace(plan, checks=checks)


@pytest.mark.parametrize("problem", [
    "candidate", "repository", "target", "pull_number", "context", "status_id", "producer", "definition",
    "earlier_attempt", "duplicate_receipt", "not_executed", "skipped", "neutral", "cancelled", "timed_out",
    "wrong_provider",
])
def test_success_status_without_exact_trusted_execution_is_never_green(planned, problem):
    subject, plan = planned
    build, verify = plan.checks
    execution = completed(subject, build, 11)
    receipt = execution.receipts[0]
    if problem == "candidate":
        changed = replace(subject, candidate=replace(subject.candidate, tree="f" * 40))
        receipt = replace(receipt, subject=changed)
    elif problem == "repository":
        changed = replace(subject, binding=replace(subject.binding, repository_id=43))
        receipt = replace(receipt, subject=changed)
    elif problem == "target":
        receipt = replace(receipt, subject=replace(subject, target_ref="refs/heads/other"))
    elif problem == "pull_number":
        receipt = replace(receipt, subject=replace(subject, pull_number=8))
    elif problem == "context":
        receipt = replace(receipt, context="different")
    elif problem == "status_id":
        receipt = replace(receipt, status_id=10)
    elif problem == "producer":
        receipt = replace(receipt, producer_digest="9" * 64)
    elif problem == "definition":
        other_definition = replace(execution.invocation, workflow_digest="9" * 64)
        execution = replace(execution, invocation=other_definition)
        receipt = replace(receipt, invocation=other_definition)
    elif problem == "earlier_attempt":
        receipt = replace(receipt, invocation=replace(execution.invocation, attempt=1))
    elif problem == "not_executed":
        receipt = replace(receipt, executed=False)
    elif problem in {"skipped", "neutral", "cancelled", "timed_out"}:
        receipt = replace(receipt, conclusion=problem)
    elif problem == "wrong_provider":
        receipt = replace(receipt, provider="github")
    receipt_set = (receipt, receipt) if problem == "duplicate_receipt" else (receipt,)
    execution = replace(execution, receipts=receipt_set)
    transport = Transport(subject.binding, page([status_for(build, 11), status_for(verify, 12)]))
    reader = Reader({"build": execution, "verify": completed(subject, verify, 12)})

    result = assess(subject, plan, transport, reader)

    assert result.state != "passed"
    build_result = next(check for check in result.checks if check.context == "build")
    assert build_result.state != "passed"
    assert build_result.receipt is None


def test_receipt_cannot_complete_before_the_qualified_execution_started(planned):
    subject, plan = planned
    build, verify = plan.checks
    execution = completed(subject, build, 11)
    receipt = replace(execution.receipts[0], completed_at=STARTED - timedelta(seconds=1))
    reader = Reader({"build": replace(execution, receipts=(receipt,)),
                     "verify": completed(subject, verify, 12)})
    transport = Transport(subject.binding, page([status_for(build, 11), status_for(verify, 12)]))

    result = assess(subject, plan, transport, reader)

    assert result.state == "unavailable"
    assert next(check for check in result.checks if check.context == "build").receipt is None


@pytest.mark.parametrize("creator_missing", [False, True])
def test_newest_status_with_untrusted_creator_cannot_expose_older_green(planned, creator_missing):
    subject, plan = planned
    build, verify = plan.checks
    newest = status_for(build, 31, creator_id=99)
    if creator_missing:
        newest.pop("creator")
    transport = Transport(subject.binding, page([
        newest,
        status_for(verify, 12),
        status_for(build, 11),
    ]))
    reader = Reader({"build": completed(subject, build, 11), "verify": completed(subject, verify, 12)})

    result = assess(subject, plan, transport, reader)

    assert result.state != "passed"
    check = next(check for check in result.checks if check.context == "build")
    assert check.status_id == 31
    assert check.native_state == "success"
    assert check.receipt is None


def test_missing_native_required_context_cannot_be_filled_by_receipt_alone(planned):
    subject, plan = planned
    build, verify = plan.checks
    reader = Reader({"build": completed(subject, build, 11), "verify": completed(subject, verify, 12)})
    transport = Transport(subject.binding, page([status_for(verify, 12)]))

    result = assess(subject, plan, transport, reader)

    assert result.state == "waiting"
    check = next(check for check in result.checks if check.context == "build")
    assert (check.state, check.status_id, check.receipt) == ("waiting", None, None)


@pytest.mark.parametrize("native_state", ["success", "failure"])
def test_native_response_cannot_supply_a_trusted_execution_receipt(planned, native_state):
    subject, plan = planned
    build, verify = plan.checks
    raw = status_for(build, 11, native_state=native_state)
    raw["execution_receipt"] = {"provider": "forgejo", "executed": True, "conclusion": native_state}
    transport = Transport(subject.binding, page([raw, status_for(verify, 12)]))
    reader = Reader({"verify": completed(subject, verify, 12)})

    result = assess(subject, plan, transport, reader)

    assert result.state not in {"passed", "failed"}
    check = next(check for check in result.checks if check.context == "build")
    assert check.native_state == native_state
    assert check.receipt is None


@pytest.mark.parametrize("phase, expected", [(None, "waiting"), ("queued", "queued"), ("running", "running")])
def test_pending_status_uses_current_qualified_phase_and_safe_timing(planned, phase, expected):
    subject, plan = planned
    build, verify = plan.checks
    invocation = runtime.Invocation(101, 2, "1" * 32, build.definition_digest)
    execution = None if phase is None else ci.Execution(
        subject, build.context, build.producer_digest, invocation, phase, started_at=STARTED,
    )
    transport = Transport(subject.binding, page([
        status_for(build, 11, native_state="pending"), status_for(verify, 12),
    ]))
    reader = Reader({"build": execution, "verify": completed(subject, verify, 12)})

    result = assess(subject, plan, transport, reader)

    assert result.state == expected
    check = next(check for check in result.checks if check.context == "build")
    assert (check.native_state, check.state, check.status_id) == ("pending", expected, 11)
    assert check.created_at == STARTED
    assert check.elapsed_seconds == 60
    assert check.receipt is None
    if phase is not None:
        assert (check.run_id, check.attempt) == (101, 2)


def test_read_timeout_returns_unavailable_without_touching_receipt_reader(planned):
    subject, plan = planned
    transport = Transport(subject.binding, TimeoutError())
    reader = Reader({})

    result = assess(subject, plan, transport, reader)

    assert result.state == "unavailable"
    assert transport.calls == [("GET", path(1))]
    assert reader.calls == []
