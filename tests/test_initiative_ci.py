"""Control the observation clock and prove that only exact evidence changes CI telemetry."""

from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, forgejo, forgejo_ci, github, initiative_ci as ci, runtime


TARGET = "refs/heads/main"
NOW = 1_800_000_000
BASE, HEAD, TREE = (letter * 40 for letter in "abc")
POLICY = ci.Policy(60, 10, 40, 300)
CANDIDATE = ci.Candidate(1, BASE, HEAD, HEAD, "d" * 64)


def observe(state, offset, **kwargs):
    return ci.Observation(CANDIDATE, state, "native_" + state, NOW + offset, **kwargs)


@pytest.mark.parametrize("state", ["queued", "running"])
def test_repeated_reads_preserve_progress_and_stall_needs_a_current_observation(state):
    first = ci.advance(None, observe(state, 0, run_id=10, attempt=1, native_progress_at=NOW-10), POLICY)
    assert first.last_success_at == NOW
    assert first.last_progress_at == first.progress_since == NOW-10
    assert ci.stall(first, POLICY, NOW + 60) is None
    assert ci.advance(first, first.observation, POLICY) is first
    current = ci.advance(first, observe(state, 50, run_id=10, attempt=1, native_progress_at=NOW-10), POLICY)
    assert current.last_success_at == NOW+50
    assert current.last_progress_at == first.last_progress_at
    assert ci.stall(current, POLICY, NOW+50) == ci.Stall(state, NOW-10, NOW-10, NOW+60)
    assert ci.stall(current, POLICY, NOW+61) is None


def test_unknown_progress_time_requires_repeated_observation_and_is_never_invented():
    first = ci.advance(None, observe("queued", 0, run_id=10, attempt=1), POLICY)
    later = ci.advance(first, observe("queued", 60, run_id=10, attempt=1), POLICY)
    assert later.last_progress_at is None and later.progress_since == NOW
    assert ci.stall(later, POLICY, NOW+60) == ci.Stall("queued", NOW, None, NOW+70)
    running = ci.advance(later, observe("running", 61, run_id=10, attempt=1, native_progress_at=NOW+61), POLICY)
    assert running.last_progress_at == running.progress_since == NOW+61
    retry = ci.advance(running, observe("queued", 62, run_id=10, attempt=2), POLICY)
    assert retry.progress_since == NOW+62 and ci.stall(retry, POLICY, NOW+62) is None
    fresh = replace(retry.observation, candidate=replace(CANDIDATE, generation=2, digest="e"*64), read_at=NOW+65)
    state = ci.advance(retry, fresh, POLICY)
    assert state.progress_since == NOW+65 and state.last_progress_at is None


@pytest.mark.parametrize(("state", "outcome"), [("missing", "verified"), ("pending", "verified"),
    ("stale", "stale"), ("unavailable", "untrusted"), ("unavailable", "unavailable"), ("failed", "verified")])
def test_missing_pending_stale_and_untrusted_evidence_is_not_a_stall_or_repair(state, outcome):
    earlier = ci.advance(None, observe("running", 0, native_progress_at=NOW-100), POLICY)
    telemetry = ci.advance(earlier, observe(state, 100, read_outcome=outcome), POLICY)
    assert ci.stall(telemetry, POLICY, NOW+100) is None
    assert telemetry.observation.failure_digest is None
    assert telemetry.progress_since is None
    assert telemetry.last_progress_at == NOW-100
    assert telemetry.last_success_at == (NOW+100 if outcome=="verified" else NOW)


def test_unavailable_read_backoff_and_wakeup_adjust_only_the_next_read():
    first = ci.advance(None, observe("failed", 0, check="build", run_id=9, attempt=1, failure_digest="e"*64), POLICY)
    assert not ci.due(first, NOW+9)
    assert ci.due(first, NOW+9, wakeup=True)
    assert ci.due(first, NOW+10)
    for offset, interval in [(10,10), (20,20), (40,40), (80,40), (120,40)]:
        outage = ci.unavailable(first, NOW+offset, "native_ci_read_unavailable")
        assert outage.candidate == CANDIDATE and outage.failure_digest is None
        first = ci.advance(first, outage, POLICY)
        assert first.next_recheck_at == NOW+offset+interval
        assert first.last_success_at == NOW
    initial = ci.advance(None, ci.unavailable(None, NOW, "native_ci_read_unavailable"), POLICY)
    assert initial.observation.candidate is None and initial.next_recheck_at == NOW+10
    assert ci.Telemetry.load(initial.to_record()) == initial
    with pytest.raises(core.Invalid, match="candidate_unbound"):
        ci.Observation(None,"unavailable","native_ci_read_unavailable",NOW,"unavailable",check="build")
    latest = ci.advance(first, observe("pending", 145), POLICY)
    assert latest.unavailable_reads == 0 and latest.next_recheck_at == NOW+155
    assert not ci.diagnostic_expired(latest, POLICY, NOW+444)
    assert ci.diagnostic_expired(latest, POLICY, NOW+445)


def test_storage_shape_and_out_of_order_reads():
    state = ci.advance(None, observe("queued", 30), POLICY)
    assert ci.Telemetry.load(state.to_record()) == state
    assert ci.Telemetry.load(json.dumps(state.to_record())) == state
    with pytest.raises(core.Conflict, match="out_of_order"):
        ci.advance(state, observe("queued", 29), POLICY)
    with pytest.raises(core.Invalid, match="telemetry_duplicate"):
        ci.Telemetry.load('{"observation":{},"observation":{}}')
    with pytest.raises(core.Invalid, match="telemetry_invalid"):
        ci.Telemetry.load("not json")
    with pytest.raises(core.Invalid, match="failure_unproved"):
        observe("running", 0, run_id=1, attempt=1, check="build", failure_digest="e"*64)


@pytest.mark.parametrize("link", ["file:///etc/passwd", "https://owner@forge.example/pull/1",
    "https://forge.example/a/../secrets", "https://forge.example/a%2fsecrets", "https://forge.example/run?s=private"])
def test_untrusted_links_are_rejected_by_retained_schema(link):
    with pytest.raises(core.Invalid, match="diagnostic_url"):
        observe("queued", 0, diagnostic_url=link)


@pytest.mark.parametrize("values", [(0,10,20,30), (-1,10,20,30), (60,False,40,300), (60,30,10,300)])
def test_policy_requires_finite_positive_values_and_bounded_backoff(values):
    with pytest.raises(core.Invalid):
        ci.Policy(*values)


def forge_candidate():
    binding = forgejo.Binding("https://forge.example.invalid:8443","fixture/reference",42,"reader","writer")
    check = forgejo_ci.RequiredCheck("build",8,"4"*64,"5"*64)
    plan = forgejo_ci.CheckPlan(binding,TARGET,"6"*64,(check,))
    candidate = runtime.Candidate(1,"7"*64,"8"*64,HEAD,BASE,HEAD,(BASE,),TREE,core.identity(plan),plan.policy_digest)
    return forgejo_ci.Subject(binding,TARGET,19,candidate),check,plan


def test_forgejo_qualified_red_binds_independent_current_attempt_and_wrong_producer_is_diagnostic():
    subject,check,plan = forge_candidate()
    now = datetime.fromtimestamp(NOW,UTC)
    invocation = runtime.Invocation(12,2,"9"*32,check.definition_digest)
    receipt = forgejo_ci.ExecutionReceipt(subject,check.context,20,check.producer_digest,invocation,True,"failure",now)
    execution = forgejo_ci.Execution(subject,check.context,check.producer_digest,invocation,"completed",(receipt,),now)
    class Ports:
        binding = subject.binding
        creator = check.creator_id
        def request(self, method, path, body=None):
            assert method=="GET" and HEAD in path
            native = {"id":20,"creator":{"id":self.creator},"status":"failure","context":check.context,
                      "target_url":f"{self.binding.origin}/{self.binding.repository}/actions/runs/12"}
            return forgejo.Response(200,[native],{"X-Total-Count":"1"})
        def current_execution(self, wanted, required):
            assert (wanted,required)==(subject,check)
            return execution
    ports = Ports()
    red = forgejo_ci.initiative_observation(forgejo_ci.assess_ci(subject,plan,ports,ports,observed_at=now),read_at=NOW)
    assert red.state=="failed" and red.failure_digest is not None and red.candidate.digest==core.identity(subject.candidate)
    assert (red.check,red.run_id,red.attempt,red.native_state)==("build",12,2,"failure")
    ports.creator = 9
    untrusted = forgejo_ci.initiative_observation(forgejo_ci.assess_ci(subject,plan,ports,ports,observed_at=now),
                                                   read_at=NOW+1)
    assert untrusted.state=="unavailable" and untrusted.read_outcome=="untrusted"
    assert untrusted.native_state=="failure" and untrusted.failure_digest is None and untrusted.attempt is None


def test_forgejo_progress_and_transport_outage_are_separate():
    subject,check,plan = forge_candidate()
    now = datetime.fromtimestamp(NOW,UTC)
    start = datetime.fromtimestamp(NOW-70,UTC)
    class Ports:
        binding = subject.binding
        outage = False
        def request(self, method, path, body=None):
            if self.outage:
                raise TimeoutError("hidden diagnostic")
            return forgejo.Response(200,[{"id":1,"status":"pending","context":"build","creator":{"id":8}}],
                                     {"X-Total-Count":"1"})
        def current_execution(self, wanted, required):
            return forgejo_ci.Execution(wanted,required.context,required.producer_digest,
                runtime.Invocation(20,1,"1"*32,required.definition_digest),"running",started_at=start)
    ports = Ports()
    observation = forgejo_ci.initiative_observation(
        forgejo_ci.assess_ci(subject,plan,ports,ports,observed_at=now),read_at=NOW)
    assert observation.state=="running" and observation.native_progress_at==NOW-70
    assert ci.stall(ci.advance(None,observation,POLICY),POLICY,NOW) is not None
    ports.outage = True
    unavailable = forgejo_ci.initiative_observation(
        forgejo_ci.assess_ci(subject,plan,ports,ports,observed_at=now),read_at=NOW+1)
    assert unavailable.read_outcome=="unavailable" and unavailable.native_progress_at is None


@pytest.mark.parametrize(("native","mapped"), [("queued","queued"), ("in_progress","running"), ("pending","pending")])
def test_github_required_run_projection_uses_actual_attempt_and_safe_run_link(native,mapped):
    candidate = forge_candidate()[0].candidate
    class Diagnostic:
        class enrollment:
            repository = "fixture/reference"
        def qualify(self, incoming, pr):
            assert (incoming,pr)==(candidate,9)
            raise github._RequiredRunPending({"status":native,"id":20,"run_attempt":2,
                "run_started_at":datetime.fromtimestamp(NOW-70,UTC).isoformat(),
                "created_at":datetime.fromtimestamp(NOW-900,UTC).isoformat()}, "build")
    result = github.GitHub.observe_ci(Diagnostic(),candidate,9,NOW)
    assert (result.state,result.run_id,result.attempt,result.check)==(mapped,20,2,"build")
    assert result.diagnostic_url=="https://github.com/fixture/reference/actions/runs/20"
    assert result.native_progress_at==(NOW-70 if mapped=="running" else None)
    assert (ci.stall(ci.advance(None,result,POLICY),POLICY,NOW) is not None)==(mapped=="running")


@pytest.mark.parametrize(("error","state","outcome"), [
    (github.FailedChecks("9"*64),"unavailable","untrusted"),
    (core.Unavailable("native_candidate_changed"),"stale","stale"),
    (core.Unavailable("native_read_unavailable"),"unavailable","unavailable"),
    (core.Unavailable("native_run_missing"),"missing","verified"),
    (core.Unavailable("native_required_producer_not_enrolled"),"unavailable","untrusted")])
def test_github_diagnostics_never_promote_unqualified_red(error,state,outcome):
    candidate = forge_candidate()[0].candidate
    class Diagnostic:
        class enrollment:
            repository = "fixture/reference"
        def qualify(self, incoming, pr):
            raise error
    result = github.GitHub.observe_ci(Diagnostic(),candidate,9,NOW)
    assert result.state==state and result.read_outcome==outcome and result.failure_digest is None



@pytest.mark.parametrize("condition", ["green", "stale_target", "foreign_pr_head", "outage"])
def test_forgejo_admitted_observation_reads_exact_native_subject_without_authorizing_effects(tmp_path, condition):
    from dataclasses import asdict

    from integration_coordinator import initiative_controller as controller, initiative_forgejo, lifecycle
    from test_initiative_forgejo import fixture_document
    from test_integration_forgejo_merge import ACTOR, BASE, HEAD, PREVIOUS, PULL, PULL_ID, SOURCE, TARGET, TREE, Fixture

    native = Fixture()
    fixture = initiative_forgejo.parse_fixture(fixture_document(native))
    common = tmp_path / ".git"
    common.mkdir()
    custody = lifecycle.Custody(common)
    target = controller.Target(fixture.binding.origin, fixture.binding.repository, TARGET)
    grant = controller.Approval("a"*64,target,"b"*64,"c"*64,(controller.Slice("slice-a"),))
    launch = controller.Launch("d"*64,BASE,str(tmp_path),"CYCLE-A","build")
    activation = controller.Activation.from_launch(grant,"slice-a",launch,managed=True)
    source = initiative_forgejo.Source(SOURCE,BASE,HEAD,TREE,(
        runtime.SourceEntry(PREVIOUS,"discovery_import"),
        runtime.SourceEntry(HEAD,"phase",("refactor",)),
    ),"e"*64)

    class Ports:
        binding = fixture.binding
        def ref(self, binding, ref):
            if condition == "outage":
                raise TimeoutError("private provider detail")
            return native.objects.ref(binding,ref)
        def commit(self,binding,oid):
            return native.objects.commit(binding,oid)
        def request(self,method,path,body=None):
            assert method=="GET"
            if path == PULL:
                row = native.transport.pull()
                row.update(title=initiative_forgejo.publication_title(source),user={"id":ACTOR})
                if condition=="foreign_pr_head":
                    row["head"]["repo"]["full_name"]="foreign/repo"
                return forgejo.Response(200,row)
            return native.transport.request(method,path,body)
        def current_execution(self, subject, check):
            old = native.reader.execution
            return replace(old,subject=subject,receipts=(replace(old.receipts[0],subject=subject),))

    def forbidden(*args):
        pytest.fail("observation must never authorize a protected effect or look up local writer source")

    delivery = initiative_forgejo.FixtureDelivery(custody,fixture,Ports(),forbidden,forbidden)
    delivery._write(activation,"source",asdict(source))
    delivery._write(activation,"admission",{"source":core.identity(source),"number":7,"pull_id":PULL_ID})
    recorded = delivery.observe_admission(activation)
    if condition=="stale_target":
        native.objects.refs[TARGET]="7"*40
    assert recorded is not None
    observation = delivery.observe_ci(activation,recorded,NOW)
    assert observation is not None
    assert observation.candidate == ci.Candidate.exact(delivery._expected_candidate(source,7,PULL_ID).subject.candidate)
    assert observation.state == {"green":"passed","stale_target":"stale","foreign_pr_head":"stale","outage":"unavailable"}[condition]
    assert observation.failure_digest is None
    if condition == "green":
        assert observation.diagnostic_url == f"{fixture.binding.origin}/{fixture.binding.repository}/pulls/7"
    assert native.transport.writes == []
    with pytest.raises(core.Conflict, match="admission_changed"):
        delivery.observe_ci(activation,replace(recorded,receipt_digest="8"*64),NOW)


def test_github_read_only_pending_and_aggregate_red_reuse_native_qualification():
    from test_integration_github import QualifiedGitHub, ready_candidate

    api = QualifiedGitHub()
    candidate = ready_candidate(api)
    assert api.observe_ci(candidate,5,NOW).state == "passed"
    api.run["status"] = "in_progress"
    api.run["conclusion"] = None
    api.run["run_started_at"] = datetime.fromtimestamp(NOW-70,UTC).isoformat()
    running = api.observe_ci(candidate,5,NOW)
    assert (running.state,running.check,running.run_id,running.attempt,running.native_progress_at)==(
        "running","gate",71,2,NOW-70)
    api.run.update(status="completed",conclusion="failure")
    with pytest.raises(github.FailedChecks):
        api.qualify(candidate,5)
    result = api.observe_ci(candidate,5,NOW)
    assert (result.state,result.read_outcome,result.native_state,result.failure_digest) == (
        "unavailable","untrusted","failure",None)
