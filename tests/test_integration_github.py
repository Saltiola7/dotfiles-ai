"""Native facts are untrusted data; fixtures never establish live enrollment."""
from __future__ import annotations

import hashlib
import datetime as dt
from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core as c
from integration_coordinator import github as g
from integration_coordinator import runtime as r
from integration_coordinator import controller as h


def oid(n: int) -> str:
    return f"{n:040x}"


def classic() -> dict[str, object]:
    return {
        "enforce_admins": {"enabled": True},
        "required_status_checks": {"strict": True, "checks": [{"context": "gate", "app_id": 15368}]},
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }


def ruleset(kind: str, bypass: str = "never") -> dict[str, object]:
    params: dict[str, object] = {}
    if kind == "required_status_checks":
        params = {"strict_required_status_checks_policy": True,
                  "required_status_checks": [{"context": "gate", "integration_id": 15368}]}
    if kind == "pull_request":
        params = {"required_approving_review_count": 1}
    if kind == "code_scanning":
        params = {"code_scanning_tools": [{"tool": "CodeQL", "security_alerts_threshold": "high_or_higher", "alerts_threshold": "none"}]}
    return {"id": 21, "enforcement": "active", "current_user_can_bypass": bypass,
            "bypass_actors": [], "rules": [{"type": kind, "parameters": params}]}


def test_strict_classic_and_layered_review_exception_preserve_ci_guard() -> None:
    facts = g.verify_target_policy(classic(), ())
    assert facts.checks == (g.CheckRequirement("gate", 15368),)
    layered = g.verify_target_policy(None, (ruleset("pull_request", "always"),
        ruleset("required_status_checks"), ruleset("code_scanning")), review_exception=True)
    assert layered.code_scanning
    assert layered.checks == facts.checks


@pytest.mark.parametrize("defect", ["loose", "admin_bypass", "any_app", "boolean_app", "empty_checks"])
def test_classic_policy_never_claims_nonbypassable_fresh_ci_for_unsafe_policy(defect: str) -> None:
    value = classic()
    if defect == "admin_bypass":
        value["enforce_admins"] = {"enabled": False}
    else:
        checks: list[dict[str, object]] = [{"context": "gate", "app_id": 15368}]
        if defect == "any_app": checks = [{"context": "gate", "app_id": None}]
        if defect == "boolean_app": checks = [{"context": "gate", "app_id": True}]
        if defect == "empty_checks": checks = []
        value["required_status_checks"] = {"strict": defect != "loose", "checks": checks}
    with pytest.raises((c.Invalid, c.Unavailable)):
        g.verify_target_policy(value, ())


@pytest.mark.parametrize("kind", ["required_status_checks", "code_scanning"])
def test_admin_review_exception_cannot_bypass_independent_ci_or_scanning(kind: str) -> None:
    with pytest.raises(c.Unavailable):
        g.verify_target_policy(None, (ruleset("required_status_checks"), ruleset(kind, "always")), review_exception=True)


def test_unrecognized_effective_native_policy_is_unavailable() -> None:
    with pytest.raises(c.Unavailable):
        g.verify_target_policy(None, (ruleset("required_status_checks"), ruleset("merge_queue")))


def test_control_guard_requires_restricted_actual_writers_separate_integrity_rules() -> None:
    integrity = {"id": 2, "enforcement": "active", "current_user_can_bypass": "never",
                 "bypass_actors": [], "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
    update = {"id": 3, "enforcement": "active", "current_user_can_bypass": "always",
              "bypass_actors": [{"actor_type": "Integration", "actor_id": 44, "bypass_mode": "always"}],
              "rules": [{"type": "update"}]}
    assert g.verify_control_policy((integrity, update), (g.ControlActor("Integration", 44),))
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((integrity,), (g.ControlActor("Integration", 44),))
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((integrity, update), (g.ControlActor("Integration", 99),))
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((update,), (g.ControlActor("Integration", 44),))


@pytest.mark.parametrize("rule_source", ["classic", "ruleset"])
def test_linear_control_history_cannot_qualify_source_retention_parents(rule_source: str) -> None:
    integrity = {"enforcement": "active", "current_user_can_bypass": "never", "bypass_actors": [],
                 "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
    update = {"enforcement": "active", "current_user_can_bypass": "always",
              "bypass_actors": [{"actor_type": "Integration", "actor_id": 44, "bypass_mode": "always"}],
              "rules": [{"type": "update"}]}
    if rule_source == "classic":
        value = classic()
        value["restrictions"] = {"users": [{"id": 7}], "apps": [], "teams": []}
        value["required_linear_history"] = {"enabled": True}
        with pytest.raises(c.Unavailable, match="control_linear_history_unsupported"):
            g.verify_control_policy((), (g.ControlActor("User", 7),), classic=value, admin_ids=(7,))
    else:
        with pytest.raises(c.Unavailable, match="control_linear_history_unsupported"):
            g.verify_control_policy((integrity, update, ruleset("required_linear_history")),
                                   (g.ControlActor("Integration", 44),))


def test_role_based_control_exceptions_require_complete_native_expansion() -> None:
    integrity = {"id": 2, "enforcement": "active", "current_user_can_bypass": "never",
                 "bypass_actors": [], "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
    update = {"id": 3, "enforcement": "active", "current_user_can_bypass": "always",
              "bypass_actors": [{"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"}],
              "rules": [{"type": "update"}]}
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((integrity, update), (g.ControlActor("User", 7),))
    assert g.verify_control_policy((integrity, update), (g.ControlActor("User", 7),), admin_ids=(7,))
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((integrity, update), (g.ControlActor("User", 7),), admin_ids=(7, 8))


def native_check() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    check = {"id": 81, "name": "gate", "app": {"id": 15368}, "status": "completed",
             "conclusion": "success", "head_sha": oid(10), "check_suite": {"id": 91}}
    job = {"id": 81, "name": "gate", "run_id": 71, "run_attempt": 2,
           "status": "completed", "conclusion": "success", "head_sha": oid(10), "check_run_url": "https://api.github.com/repos/example/repo/check-runs/81"}
    run = {"id": 71, "run_attempt": 2, "workflow_id": 61, "path": ".github/workflows/test.yml",
           "event": "pull_request", "head_sha": oid(10), "check_suite_id": 91,
           "status": "completed", "conclusion": "success", "pull_requests": [{"number": 5}]}
    return check, job, run


def test_check_evidence_binds_real_app_run_attempt_job_event_and_candidate() -> None:
    check, job, run = native_check()
    value = g.verify_check(check, job, run, g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
                           head=oid(10), tested_oid=oid(11), pr_number=5, producer_digest="a" * 64)
    assert value == c.Evidence("check", 15368, 81, 2, oid(11), "a" * 64)


@pytest.mark.parametrize("defect", ["wrong_app", "old_attempt", "different_job", "wrong_event", "wrong_workflow", "different_pr", "skipped", "pending", "foreign_head"])
def test_green_label_cannot_substitute_for_complete_native_check_binding(defect: str) -> None:
    check, job, run = native_check()
    if defect == "wrong_app": check["app"] = {"id": 99}
    if defect == "old_attempt": job["run_attempt"] = 1
    if defect == "different_job": job["check_run_url"] = "https://api.github.com/repos/example/repo/check-runs/82"
    if defect == "wrong_event": run["event"] = "workflow_dispatch"
    if defect == "wrong_workflow": run["path"] = ".github/workflows/unrelated.yml"
    if defect == "different_pr": run["pull_requests"] = [{"number": 6}]
    if defect == "skipped": check["conclusion"] = "skipped"
    if defect == "pending": run["status"] = "in_progress"
    if defect == "foreign_head": check["head_sha"] = oid(99)
    with pytest.raises((c.Invalid, c.Unavailable)):
        g.verify_check(check, job, run, g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
                       head=oid(10), tested_oid=oid(11), pr_number=5, producer_digest="a" * 64)


def archive(body: bytes, name: str = "execution-context.json") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        output.writestr(name, body)
    return stream.getvalue()


def artifact(archive_bytes: bytes) -> dict[str, object]:
    return {"id": 101, "name": "selection-attempt-2", "expired": False,
            "size_in_bytes": len(archive_bytes), "digest": "sha256:" + hashlib.sha256(archive_bytes).hexdigest(),
            "workflow_run": {"id": 71, "repository_id": 51, "head_sha": oid(10)}}


def test_artifact_reader_checks_native_digest_run_and_fixed_member_without_extraction() -> None:
    data = archive(b'{"schema_version":1,"tested_sha":"' + oid(11).encode() + b'"}')
    value = g.read_artifact(data, artifact(data), run_id=71, repository_id=51, source_head=oid(10), member="execution-context.json")
    assert value["tested_sha"] == oid(11)


@pytest.mark.parametrize("body", [b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff', b'[]'])
def test_malformed_native_artifact_remains_unqualified(body: bytes) -> None:
    data = archive(body)
    with pytest.raises((c.Invalid, c.Unavailable)):
        g.read_artifact(data, artifact(data), run_id=71, repository_id=51, source_head=oid(10), member="execution-context.json")


def test_artifact_native_identity_and_member_names_cannot_be_substituted() -> None:
    data = archive(b'{"x":1}')
    wrong = artifact(data); wrong["workflow_run"] = {"id": 72, "repository_id": 51, "head_sha": oid(10)}
    with pytest.raises(c.Unavailable):
        g.read_artifact(data, wrong, run_id=71, repository_id=51, source_head=oid(10), member="execution-context.json")
    wrong = artifact(data); wrong["digest"] = "sha256:" + "0" * 64
    with pytest.raises(c.Unavailable):
        g.read_artifact(data, wrong, run_id=71, repository_id=51, source_head=oid(10), member="execution-context.json")
    with pytest.raises(c.Invalid):
        g.read_artifact(data, artifact(data), run_id=71, repository_id=51, source_head=oid(10), member="../execution-context.json")


def test_codeql_requires_current_actual_categories_not_a_green_workflow() -> None:
    setup = {"state": "configured", "languages": ["actions", "javascript", "javascript-typescript", "typescript", "python"], "updated_at": "2026-11-10T00:00:00Z"}
    analyses: list[object] = [
        {"id": n, "ref": "refs/pull/5/merge", "commit_sha": oid(10), "category": category,
         "tool": {"name": "CodeQL"}, "error": "", "created_at": "2026-11-11T00:00:00Z", "rules_count": 10}
        for n, category in enumerate(("/language:actions", "/language:javascript-typescript", "/language:python"), 1)
    ]
    assert len(g.verify_codeql(setup, analyses, accepted_oids=(oid(10), oid(11)), accepted_refs=("refs/pull/5/merge",), attempt=2, started=dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc), finished=dt.datetime(2026, 11, 12, tzinfo=dt.timezone.utc))) == 3
    setup["languages"] = ["actions", "javascript-typescript", "python", "csharp"]
    with pytest.raises(c.Unavailable):
        g.verify_codeql(setup, analyses, accepted_oids=(oid(10), oid(11)), accepted_refs=("refs/pull/5/merge",), attempt=2, started=dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc), finished=dt.datetime(2026, 11, 12, tzinfo=dt.timezone.utc))


def test_codeql_rejects_latest_error_and_analysis_from_before_configuration_change() -> None:
    setup = {"state": "configured", "languages": ["python"], "updated_at": "2026-11-10T00:00:00Z"}
    good = {"id": 1, "ref": "refs/pull/5/merge", "commit_sha": oid(10), "category": "/language:python", "tool": {"name": "CodeQL"}, "error": "", "created_at": "2026-11-11T00:00:00Z", "rules_count": 10}
    stale = dict(good); stale["created_at"] = "2026-11-09T00:00:00Z"
    bad = dict(good); bad.update({"id": 2, "error": "failure", "created_at": "2026-11-12T00:00:00Z"})
    for analyses in ([stale], [good, bad]):
        with pytest.raises(c.Unavailable):
            g.verify_codeql(setup, analyses, accepted_oids=(oid(10),), accepted_refs=("refs/pull/5/merge",), attempt=2, started=dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc), finished=dt.datetime(2026, 11, 12, tzinfo=dt.timezone.utc))


@pytest.mark.parametrize("destination", ["https://results.blob.core.windows.net/container/a.zip?sig=opaque", "https://attacker.invalid/a.zip"])
def test_artifact_redirect_never_forwards_authentication(monkeypatch: pytest.MonkeyPatch, destination: str) -> None:
    import email.message
    import urllib.error
    import urllib.request
    seen: list[urllib.request.Request] = []

    class Response:
        def __enter__(self) -> Response:
            return self
        def __exit__(self, *_args: object) -> None:
            return None
        def read(self, _size: int) -> bytes:
            return b"artifact"

    class Opener:
        def __init__(self, protected: bool) -> None:
            self.protected = protected
        def open(self, request: urllib.request.Request, data: object = None, timeout: float = 30.0) -> Response:
            seen.append(request)
            if request.full_url.startswith("https://api.github.com/"):
                if self.protected:
                    headers = email.message.Message(); headers["Location"] = destination
                    raise urllib.error.HTTPError(request.full_url, 302, "redirect", headers, None)
                forwarded = urllib.request.Request(destination, headers=dict(request.header_items()))
                seen.append(forwarded)
            return Response()

    def opener(*handlers: object) -> Opener:
        return Opener(bool(handlers))
    monkeypatch.setattr(urllib.request, "_opener", None)
    monkeypatch.setattr(urllib.request, "build_opener", opener)
    transport = g.HttpTransport("fixture-secret")
    if "attacker" in destination:
        with pytest.raises(c.Unavailable):
            transport.archive("repos/example/repo/actions/artifacts/1/zip")
        assert len(seen) == 1
    else:
        assert transport.archive("repos/example/repo/actions/artifacts/1/zip") == b"artifact"
        assert len(seen) == 2
        assert all(key.lower() not in {"authorization", "cookie", "proxy-authorization"} for key, _ in seen[1].header_items())
    assert "fixture-secret" not in repr(transport)


def test_json_transport_refuses_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    import email.message
    import urllib.error
    import urllib.request
    seen: list[str] = []
    class Opener:
        def open(self, request: urllib.request.Request, data: object = None, timeout: float = 30.0) -> bytes:
            seen.append(request.full_url)
            headers = email.message.Message(); headers["Location"] = "https://attacker.invalid/"
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", headers, None)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: Opener())
    with pytest.raises(c.Unavailable):
        g.HttpTransport("fixture-secret").request("GET", "repos/example/repo")
    assert seen == ["https://api.github.com/repos/example/repo"]


class FakeTransport:
    def __init__(self, routes: dict[tuple[str, str], object] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []
    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        self.calls.append((method, path, body))
        if (method, path) not in self.routes:
            raise c.Unavailable("fixture_route_missing")
        return self.routes[(method, path)]
    def archive(self, path: str) -> bytes:
        raise c.Unavailable("fixture_archive_missing")


def enrollment(*, enabled: bool = False) -> g.Enrollment:
    return g.Enrollment("example/repo", 51, "main", "integration-state", oid(900), "d" * 64,
                        (7,), (44,), enabled=enabled)


def test_native_enrollment_parser_is_closed_and_never_implicitly_enabled() -> None:
    value: dict[str, object] = {"schema_version": 2, "repository": "example/repo", "repository_id": 51,
        "default_branch": "main", "control_branch": "integration-state", "root_oid": oid(900),
        "policy_digest": "d" * 64, "mutator_user_ids": [7], "mutator_app_ids": [44],
        "enabled": False, "review_exception": False}
    assert not g.parse_enrollment(value).enabled
    wrong = dict(value); wrong["repository_id"] = True
    with pytest.raises(c.Invalid): g.parse_enrollment(wrong)
    wrong = dict(value); wrong["unreviewed_bypass"] = True
    with pytest.raises(c.Invalid): g.parse_enrollment(wrong)


def test_partial_native_pagination_is_not_complete_evidence() -> None:
    fake = FakeTransport({("GET", "repos/example/repo/commits/" + oid(10) + "/check-runs?per_page=100&page=1"): {"total_count": 2, "check_runs": [{"id": 1}]}})
    with pytest.raises(c.Unavailable):
        g.GitHub(fake, enrollment()).pages("commits/" + oid(10) + "/check-runs", "check_runs")


def test_introducing_pr_proof_rejects_foreign_or_ambiguous_merged_attribution() -> None:
    expected = {"number": 5, "html_url": "https://github.com/example/repo/pull/5", "state": "closed", "merged_at": "2026-11-11T00:00:00Z", "base": {"repo": {"full_name": "example/repo"}}}
    assert g.verify_introduction([expected], "example/repo", 5, "2026-11-11T00:00:00Z")
    wrong = dict(expected); wrong["number"] = 6
    for values in ([wrong], [], [expected, wrong]):
        with pytest.raises(c.Unavailable):
            g.verify_introduction(values, "example/repo", 5, "2026-11-11T00:00:00Z")


def test_disabled_native_mutations_refuse_before_transport_access() -> None:
    from integration_coordinator import runtime as r
    state = r.RuntimeSnapshot(r.Target("example/repo", "main", oid(900), "d" * 64), (), ())
    source = r.SourceSeries("example/repo", 5, oid(1), oid(10), (r.SourceEntry(oid(10), "phase", ("domain",)),), "a" * 64)
    ticket = r.Ticket("1" * 32, "2" * 32, source, "b" * 64)
    after = r.admit_authenticated(state, ticket, r.Obligation("2" * 32, "1" * 32, "c" * 64),
        c.Admission(r.identity(source), "b" * 64, "d" * 64, "e" * 64))
    request = r.build_append(state, after, oid(901), "integration-state", "3" * 32)
    fake = FakeTransport()
    with pytest.raises(c.Unavailable):
        g.GitHub(fake, enrollment()).append(request)
    assert fake.calls == []



def test_actions_job_and_check_run_use_native_check_run_url_not_equal_ids() -> None:
    check, job, run = native_check()
    job["id"] = 888
    job["check_run_url"] = "https://api.github.com/repos/example/repo/check-runs/81"
    evidence = g.verify_check(check, job, run, g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
                              head=oid(10), tested_oid=oid(11), pr_number=5, producer_digest="a" * 64)
    assert evidence.native_id == 81
    job["check_run_url"] = "https://attacker.invalid/check-runs/81"
    with pytest.raises(c.Unavailable):
        g.verify_check(check, job, run, g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
                       head=oid(10), tested_oid=oid(11), pr_number=5, producer_digest="a" * 64)


def test_classic_control_writer_restriction_excludes_unenrolled_people_and_apps() -> None:
    value = classic()
    value["restrictions"] = {"users": [{"id": 7}], "teams": [], "apps": [{"id": 44}]}
    trusted = (g.ControlActor("User", 7), g.ControlActor("Integration", 44))
    assert g.verify_control_policy((), trusted, classic=value, admin_ids=(7,))
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((), (trusted[0],), classic=value, admin_ids=(7,))
    value["allow_force_pushes"] = {"enabled": True}
    with pytest.raises(c.Unavailable):
        g.verify_control_policy((), trusted, classic=value, admin_ids=(7,))


def test_live_enrollment_requires_separate_qualified_native_guard_pin() -> None:
    enabled = enrollment(enabled=True)
    api = g.GitHub(FakeTransport({}), enabled)
    with pytest.raises(c.Unavailable, match="native_guard_pin_missing"):
        api._live()


def source_series() -> r.SourceSeries:
    return r.SourceSeries("example/repo", 5, oid(1), oid(10),
        (r.SourceEntry(oid(10), "phase", ("domain",)),), "e" * 64)


class MemoryProof:
    def prove_refresh(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
        return r.Projection(c.identity(source), base, head, (c.CommitPair(source.head, head),), "f" * 64)

    def prove_delivery(self, source: r.SourceSeries, projection: r.Projection, merge_oid: str) -> tuple[c.CommitPair, ...]:
        return (c.CommitPair(projection.head, merge_oid),)

    def excludes_root(self, root: str, heads: tuple[str, ...]) -> bool:
        return root not in heads


def pull() -> dict[str, object]:
    repo = {"id": 51, "full_name": "example/repo"}
    return {"number": 5, "node_id": "PR_fixture", "head": {"sha": oid(10), "ref": "task", "repo": repo},
        "base": {"sha": oid(1), "ref": "main", "repo": repo}, "merge_commit_sha": oid(11),
        "merged": False, "merged_at": None, "state": "open", "draft": False}


class FactGitHub(g.GitHub):
    def __init__(self, value: dict[str, object] | None = None) -> None:
        super().__init__(FakeTransport({}), enrollment(), MemoryProof(), policy_path=".github/integration.json")
        self.pull_value = pull() if value is None else value
        self.commit_values = {oid(10): g.GitCommit(oid(10), oid(20), (oid(1),)),
                              oid(11): g.GitCommit(oid(11), oid(21), (oid(1), oid(10)))}

    def _repository(self) -> dict[str, object]:
        return {"id": 51, "full_name": "example/repo", "default_branch": "main"}

    def get(self, path: str) -> object:
        if path == "pulls/5": return self.pull_value
        if path == "compare/" + oid(1) + "..." + oid(10):
            return {"merge_base_commit": {"sha": oid(1)}}
        raise c.Unavailable("fixture_missing")

    def ref(self, branch: str) -> str:
        assert branch == "main"
        return oid(1)

    def git_commit(self, oid: str) -> g.GitCommit:
        return self.commit_values[oid]


def test_projection_requires_exact_complete_native_interval_and_proof_port() -> None:
    api = FactGitHub()
    assert api.projection(source_series(), oid(10), oid(1)).head == oid(10)
    api.commit_values[oid(10)] = g.GitCommit(oid(10), oid(20), (oid(2),))
    api.commit_values[oid(2)] = g.GitCommit(oid(2), oid(22), (oid(1),))
    with pytest.raises(c.Unavailable):
        api.projection(source_series(), oid(10), oid(1))
    api = FactGitHub(); api.proof = None
    with pytest.raises(c.Unavailable):
        api.projection(source_series(), oid(10), oid(1))


def test_candidate_binds_actual_native_merge_oid_and_never_equates_equal_trees() -> None:
    api = FactGitHub()
    api.plan = g.CheckPlan((g.Producer(g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
        "a" * 64, g.ReceiptBinding("evidence-{attempt}", "receipt.json",
            (g.IdentityField(("tested",), "tested_oid"), g.IdentityField(("run",), "run_id"), g.IdentityField(("attempt",), "attempt")))),))
    source = source_series()
    ticket = r.Ticket("1" * 32, "2" * 32, source, "3" * 64)
    projection = api.projection(source, oid(10), oid(1))
    candidate = api.candidate(ticket, 1, projection)
    assert candidate.tested_oid == oid(11)
    api.pull_value["merge_commit_sha"] = oid(12)
    api.commit_values[oid(12)] = g.GitCommit(oid(12), oid(21), (oid(1), oid(10)))
    with pytest.raises(c.Unavailable):
        api._candidate_facts(candidate, 5)


def test_native_pr_rejects_draft_foreign_or_default_source() -> None:
    for key, value in (("draft", True), ("merged", True)):
        item = pull(); item[key] = value
        with pytest.raises(c.Unavailable): FactGitHub(item).observe_pr(5)
    item = pull(); item["head"] = {"sha": oid(10), "ref": "main", "repo": {"id": 51, "full_name": "example/repo"}}
    with pytest.raises(c.Unavailable): FactGitHub(item).observe_pr(5)



def check_plan() -> g.CheckPlan:
    return g.CheckPlan((g.Producer(g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
        hashlib.sha256(b"trusted workflow").hexdigest(), g.ReceiptBinding("selection-attempt-{attempt}", "execution-context.json",
            (g.IdentityField(("tested",), "tested_oid"), g.IdentityField(("run",), "run_id"), g.IdentityField(("attempt",), "attempt")),
            (g.LiteralField(("complete",), True),))),))


class QualifiedGitHub(FactGitHub):
    def __init__(self) -> None:
        super().__init__(); self.plan = check_plan()
        self.check, self.job, self.run = native_check()
        self.run["repository"] = {"id": 51, "full_name": "example/repo"}
        self.job["id"] = 888
        self.run["created_at"] = "2026-11-11T00:00:00Z"
        self.data = archive(json.dumps({"tested": oid(11), "run": 71, "attempt": 2, "complete": True}).encode())
        self.transport = ArchiveTransport(self.data)

    def observe_policy(self) -> g.TargetGuards:
        return g.TargetGuards((g.CheckRequirement("gate", 15368),), False, "9" * 64)

    def codeql_setup(self) -> object:
        return None

    def file_at(self, head: str, path: str) -> bytes | None:
        assert path == ".github/workflows/test.yml"
        return b"trusted workflow"

    def get(self, path: str) -> object:
        if path == "actions/runs/71": return dict(self.run)
        return super().get(path)

    def pages(self, path: str, key: str | None = None, *, limit: int = 4096) -> list[object]:
        if path.startswith("actions/workflows/61/runs?"): return [dict(self.run)]
        if path == "actions/runs/71/attempts/2/jobs": return [dict(self.job)]
        if path in {"commits/" + oid(10) + "/check-runs?filter=latest", "commits/" + oid(11) + "/check-runs?filter=latest"}:
            return [dict(self.check)]
        if path == "actions/runs/71/artifacts": return [artifact(self.data)]
        raise c.Unavailable("fixture_missing")


class ArchiveTransport(FakeTransport):
    def __init__(self, data: bytes) -> None:
        super().__init__({}); self.data = data
        self.review_decision: str | None = None
        self.merge_state = "CLEAN"

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        if method == "POST" and path == "graphql" and body is not None and "reviewDecision" in str(body.get("query")):
            return {"data": {"repository": {"pullRequest": {"id": "PR_fixture", "headRefOid": oid(10), "baseRefOid": oid(1),
                "reviewDecision": self.review_decision, "mergeStateStatus": self.merge_state}}}}
        return super().request(method, path, body)

    def archive(self, path: str) -> bytes:
        assert path == "repos/example/repo/actions/artifacts/101/zip"
        return self.data


def ready_candidate(api: g.GitHub) -> r.Candidate:
    source = source_series(); projection = api.projection(source, oid(10), oid(1))
    return api.candidate(r.Ticket("1" * 32, "2" * 32, source, "3" * 64), 1, projection)


def test_qualification_requires_receipt_native_job_and_current_attempt() -> None:
    api = QualifiedGitHub(); candidate = ready_candidate(api)
    result = api.qualify(candidate, 5)
    assert result.candidate_digest == c.identity(candidate)
    assert result.evidence[0].subject_oid == candidate.tested_oid
    api.data = archive(json.dumps({"tested": oid(11), "run": 71, "attempt": 1, "complete": True}).encode())
    api.transport = ArchiveTransport(api.data)
    with pytest.raises(c.Unavailable): api.qualify(candidate, 5)


@pytest.mark.parametrize("state", ["in_progress", "failure", "cancelled"])
def test_pending_and_native_failed_checks_have_distinct_repair_meaning(state: str) -> None:
    api = QualifiedGitHub(); candidate = ready_candidate(api)
    api.run["status"] = "in_progress" if state == "in_progress" else "completed"
    api.run["conclusion"] = None if state == "in_progress" else state
    if state == "in_progress":
        with pytest.raises(c.Unavailable) as result: api.qualify(candidate, 5)
        assert not isinstance(result.value, g.FailedChecks)
    else:
        with pytest.raises(g.FailedChecks): api.qualify(candidate, 5)


def test_qualification_rejects_changed_producer_blob_and_false_literal() -> None:
    api = QualifiedGitHub(); candidate = ready_candidate(api)
    api.data = archive(json.dumps({"tested": oid(11), "run": 71, "attempt": 2, "complete": 1}).encode())
    api.transport = ArchiveTransport(api.data)
    with pytest.raises(c.Unavailable): api.qualify(candidate, 5)
    api = QualifiedGitHub(); candidate = ready_candidate(api)
    assert api.plan is not None
    api.plan = g.CheckPlan((g.Producer(api.plan.producers[0].binding, "0" * 64, api.plan.producers[0].receipt),))
    with pytest.raises(c.Unavailable): api.qualify(candidate, 5)



def reserved_state(kind: str = "merge", operator: bool = False) -> r.RuntimeSnapshot:
    api = QualifiedGitHub(); source = source_series()
    ticket = r.Ticket("1" * 32, "2" * 32, source, "3" * 64, guarded_refresh=kind == "refresh")
    state = r.RuntimeSnapshot(r.Target("example/repo", "main", oid(900), "d" * 64), (), ())
    state = r.admit_authenticated(state, ticket, r.Obligation(ticket.obligation_handle, ticket.handle, "4" * 64),
        c.Admission(c.identity(source), ticket.requester_digest, "d" * 64, "5" * 64))
    state = r.claim(state, ticket.handle, oid(1), "6" * 64)
    if kind == "merge":
        projection = api.projection(source, oid(10), oid(1))
        state = r.bind_projection(state, ticket.handle, 1, projection)
        candidate = api.candidate(state.ticket(ticket.handle), 1, projection)
        state = r.bind_candidate(state, ticket.handle, 1, candidate)
        qualification = api.qualify(candidate, 5)
    else:
        qualification = None
    invocation: r.InvocationIdentity = (r.OperatorInvocation(7, "7" * 32, "8" * 64, "9" * 64) if operator
        else r.Invocation(1001, 2, "7" * 32, "8" * 64))
    return r.reserve_native(state, ticket.handle, 1, kind, "a" * 32, invocation,
        qualification=qualification, retention_digest="b" * 64 if kind == "refresh" else None)


class MutationGitHub(QualifiedGitHub):
    def _current_enrollment(self) -> None:
        # Explicit synthetic enrollment authority; dedicated tests exercise the
        # actual current-default policy reader rather than this fixture seam.
        return None

    def __init__(self, state: r.RuntimeSnapshot) -> None:
        super().__init__(); self.state = state
        self.enrollment = replace(self.enrollment, enabled=True, native_guard_digest="9" * 64)
        self.writes: list[dict[str, object]] = []
        self.native_default = oid(1)
        self.requires_approval = False

    def _approval_required(self) -> bool:
        return self.requires_approval

    def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]:
        assert not lookup_handles
        files = {"integration/v2/target.json": r.encode(self.state.target)}
        files.update({"integration/v2/tickets/" + row.handle + ".json": r.encode(row) for row in self.state.tickets})
        files.update({"integration/v2/obligations/" + row.handle + ".json": r.encode(row) for row in self.state.obligations})
        return oid(901), files

    def ref(self, branch: str) -> str:
        assert branch == "main"
        return self.native_default

    def _ancestor(self, ancestor: str, descendant: str) -> bool:
        return ancestor == oid(10) and descendant == oid(901) or ancestor == oid(30) and descendant == oid(30)

    def _write(self, method: str, path: str, body: dict[str, object]) -> object:
        assert method == "PUT" and path == "pulls/5/merge"
        self.writes.append(body)
        self.pull_value.update({"merged": True, "state": "closed", "merged_at": "2026-11-11T02:00:00Z", "merge_commit_sha": oid(30)})
        self.native_default = oid(30)
        self.commit_values[oid(30)] = g.GitCommit(oid(30), oid(21), (oid(1),))
        return {"merged": True, "sha": oid(30)}

    def pages(self, path: str, key: str | None = None, *, limit: int = 4096) -> list[object]:
        if path == "commits/" + oid(30) + "/pulls":
            return [{"number": 5, "state": "closed", "merged_at": "2026-11-11T02:00:00Z",
                "html_url": "https://github.com/example/repo/pull/5", "base": {"repo": {"full_name": "example/repo"}}}]
        return super().pages(path, key, limit=limit)


def test_merge_rechecks_fence_exact_sha_and_positive_introducing_pr_proof() -> None:
    state = reserved_state(); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = MutationGitHub(state)
    proof = api.merge(ticket, ticket.reservation)
    assert proof.merge_oid == oid(30)
    assert proof.mapping == (c.CommitPair(oid(10), oid(30)),)
    assert api.writes == [{"sha": oid(10), "merge_method": "rebase"}]


def test_merge_reproves_original_projection_before_any_native_effect() -> None:
    class Unsupported(MemoryProof):
        def prove_refresh(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
            raise c.Invalid("git_proof_delta")

    state = reserved_state()
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = MutationGitHub(state)
    api.proof = Unsupported()
    with pytest.raises(g.NativeRejection):
        api.merge(ticket, ticket.reservation)
    assert api.writes == []


def test_uncertain_operator_unchanged_native_refs_are_never_no_effect() -> None:
    state = reserved_state(operator=True); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    state = r.mark_uncertain(state, ticket.handle, 1, ticket.reservation.operation_id)
    ticket = state.ticket(ticket.handle); assert ticket.reservation is not None
    api = MutationGitHub(state)
    with pytest.raises(c.Ambiguous): api.reconcile(ticket, ticket.reservation)
    assert api.writes == []


def test_preflight_rejection_proves_no_call_and_never_strands_false_uncertainty() -> None:
    state = reserved_state(); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = MutationGitHub(state); api.pull_value["merge_commit_sha"] = oid(12)
    api.commit_values[oid(12)] = g.GitCommit(oid(12), oid(21), (oid(1), oid(10)))
    with pytest.raises(g.NativeRejection): api.merge(ticket, ticket.reservation)
    assert api.writes == []



def test_codeql_evidence_cannot_assign_attempt_from_an_old_analysis_interval() -> None:
    setup = {"state": "configured", "languages": ["python"], "updated_at": "2026-11-10T00:00:00Z"}
    analysis = {"id": 11, "ref": "refs/pull/5/merge", "commit_sha": oid(10), "category": "/language:python",
        "tool": {"name": "CodeQL"}, "error": "", "created_at": "2026-11-11T01:00:00Z", "rules_count": 10}
    started = dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc)
    finished = dt.datetime(2026, 11, 12, tzinfo=dt.timezone.utc)
    assert g.verify_codeql(setup, [analysis], accepted_oids=(oid(10),), accepted_refs=("refs/pull/5/merge",),
        attempt=7, started=started, finished=finished)[0].attempt == 7
    with pytest.raises(c.Unavailable):
        g.verify_codeql(setup, [analysis], accepted_oids=(oid(10),), accepted_refs=("refs/pull/5/merge",),
            attempt=8, started=finished, finished=finished + dt.timedelta(hours=1))


class RefreshTransport(FakeTransport):
    def __init__(self, api: MutationGitHub) -> None:
        super().__init__({}); self.api = api

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        assert method == "POST" and path == "graphql" and body is not None
        self.calls.append((method, path, body))
        variables = g._object(body["variables"]); request = g._object(variables["input"])
        assert request["expectedHeadOid"] == oid(10) and request["updateMethod"] == "REBASE"
        self.api.pull_value["head"] = {"sha": oid(12), "ref": "task", "repo": {"id": 51, "full_name": "example/repo"}}
        self.api.commit_values[oid(12)] = g.GitCommit(oid(12), oid(21), (oid(1),))
        return {"data": {"updatePullRequestBranch": {"clientMutationId": request["clientMutationId"], "pullRequest": {"id": "PR_fixture", "headRefOid": oid(12)}}}}


class RefreshGitHub(MutationGitHub):
    def get(self, path: str) -> object:
        if path == "compare/" + oid(1) + "..." + oid(12): return {"merge_base_commit": {"sha": oid(1)}}
        return super().get(path)


def test_refresh_uses_exact_old_head_rebase_and_operator_identity_without_fake_job() -> None:
    state = reserved_state("refresh", operator=True); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = RefreshGitHub(state); transport = RefreshTransport(api); api.transport = transport
    proof = api.refresh(ticket, ticket.reservation)
    assert proof.invocation == ticket.reservation.invocation
    assert proof.projection.mapping == (c.CommitPair(oid(10), oid(12)),)
    assert len(transport.calls) == 1


def test_known_native_refresh_conflict_is_no_call_and_releases_initial_slot() -> None:
    state = reserved_state("refresh")
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None and ticket.projection is None
    api = RefreshGitHub(state)
    api.pull_value.update(mergeable=False, mergeable_state="dirty")
    transport = RefreshTransport(api)
    api.transport = transport
    with pytest.raises(g.NativeRejection) as rejected:
        api.refresh(ticket, ticket.reservation)
    assert transport.calls == [] and api.writes == []
    assert api.observe_pr(ticket.source.pr_number).head == ticket.current_head
    no_effect = r.NoEffect(ticket.reservation.operation_id, ticket.reservation.invocation,
        ticket.reservation.subject_digest, rejected.value.receipt_digest)
    parked = r.record_rejection(state, ticket.handle, ticket.generation, no_effect)
    blocked = parked.ticket(ticket.handle)
    assert parked.target.active is None and blocked.state == r.State.REPAIR_PENDING
    assert blocked.reservation is None and blocked.projection is None
    assert blocked.source == ticket.source and blocked.reconciliations == (no_effect,)


@pytest.mark.parametrize(("mergeable", "mergeable_state"), [
    (None, "dirty"), (True, "dirty"), (0, "dirty"), (False, "unknown"),
    (False, "blocked"), (False, "behind"), (False, None),
])
def test_unknown_native_conflict_facts_do_not_reject_refresh_as_known_conflict(
        mergeable: object, mergeable_state: object) -> None:
    state = reserved_state("refresh")
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = RefreshGitHub(state)
    api.pull_value.update(mergeable=mergeable, mergeable_state=mergeable_state)
    transport = RefreshTransport(api)
    api.transport = transport
    assert api.refresh(ticket, ticket.reservation).projection.head == oid(12)
    assert len(transport.calls) == 1


def test_known_conflict_never_resolves_an_already_uncertain_refresh_as_no_effect() -> None:
    state = reserved_state("refresh")
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    state = r.mark_uncertain(state, ticket.handle, ticket.generation, ticket.reservation.operation_id)
    ticket = state.ticket(ticket.handle)
    assert ticket.reservation is not None
    api = RefreshGitHub(state)
    api.pull_value.update(mergeable=False, mergeable_state="dirty")
    transport = RefreshTransport(api)
    api.transport = transport
    with pytest.raises(c.Ambiguous):
        api.refresh(ticket, ticket.reservation)
    with pytest.raises(c.Ambiguous):
        api.reconcile(ticket, ticket.reservation)
    assert transport.calls == [] and api.writes == []
    assert state.ticket(ticket.handle).reservation == ticket.reservation


def test_unsupported_source_is_proved_before_any_native_rewrite() -> None:
    class Unsupported(MemoryProof):
        def prove_refresh(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
            raise c.Invalid("git_proof_empty_phase")

    state = reserved_state("refresh")
    ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = RefreshGitHub(state)
    api.proof = Unsupported()
    transport = RefreshTransport(api)
    api.transport = transport
    with pytest.raises(g.NativeRejection):
        api.refresh(ticket, ticket.reservation)
    assert transport.calls == []


def test_refresh_reconciliation_of_unchanged_refs_keeps_reservation_uncertain() -> None:
    state = reserved_state("refresh"); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = MutationGitHub(state)
    with pytest.raises(c.Ambiguous): api.reconcile(ticket, ticket.reservation)
    assert not api.writes


def test_native_fence_rejects_stale_ticket_before_any_mutation() -> None:
    state = reserved_state(); ticket = state.ticket("1" * 32)
    assert ticket.reservation is not None
    api = MutationGitHub(r.mark_uncertain(state, ticket.handle, 1, ticket.reservation.operation_id))
    with pytest.raises(g.NativeRejection): api.merge(ticket, ticket.reservation)
    assert api.writes == []



class ScanGitHub(QualifiedGitHub):
    def __init__(self) -> None:
        super().__init__(); assert self.plan is not None
        self.plan = g.CheckPlan(self.plan.producers, g.CodeQLBinding(62))
        self.scan_run: dict[str, object] = {"id": 72, "run_attempt": 3, "workflow_id": 62,
            "path": "dynamic/github-code-scanning/codeql", "event": "dynamic", "head_sha": oid(10),
            "check_suite_id": 92, "repository": {"id": 51, "full_name": "example/repo"},
            "status": "completed", "conclusion": "success", "run_started_at": "2026-11-11T00:00:00Z",
            "updated_at": "2026-11-11T02:00:00Z"}
        self.scan_check: dict[str, object] = {"id": 82, "name": "Analyze (python)", "app": {"id": 15368},
            "status": "completed", "conclusion": "success", "head_sha": oid(10), "check_suite": {"id": 92}}

    def codeql_setup(self) -> object:
        return {"state": "configured", "languages": ["python"], "updated_at": "2026-11-10T00:00:00Z"}

    def get(self, path: str) -> object:
        if path == "actions/runs/72": return self.scan_run
        if path == "check-runs/82": return self.scan_check
        return super().get(path)

    def pages(self, path: str, key: str | None = None, *, limit: int = 4096) -> list[object]:
        if path.startswith("actions/workflows/62/runs?"): return [self.scan_run]
        if path == "actions/runs/72/attempts/3/jobs":
            return [{"id": 889, "name": "Analyze (python)", "run_id": 72, "run_attempt": 3, "head_sha": oid(10),
                "status": "completed", "conclusion": "success", "check_run_url": "https://api.github.com/repos/example/repo/check-runs/82"}]
        if path.startswith("code-scanning/analyses?"):
            return [{"id": 11, "ref": "refs/pull/5/merge", "commit_sha": oid(10), "category": "/language:python",
                "tool": {"name": "CodeQL"}, "error": "", "created_at": "2026-11-11T01:00:00Z", "rules_count": 10}]
        return super().pages(path, key, limit=limit)


def test_codeql_actual_current_run_job_and_app_bind_category_attempt() -> None:
    api = ScanGitHub(); candidate = ready_candidate(api)
    evidence = api.qualify(candidate, 5).evidence
    assert evidence[-1].kind == "scan" and evidence[-1].attempt == 3
    api.scan_check["app"] = {"id": 99}
    with pytest.raises(c.Unavailable): api.qualify(candidate, 5)



def admission_append() -> r.AppendRequest:
    before = r.RuntimeSnapshot(r.Target("example/repo", "main", oid(900), "d" * 64), (), ())
    first = r.Ticket("1" * 32, "2" * 32, source_series(), "3" * 64)
    before = r.admit_authenticated(before, first, r.Obligation(first.obligation_handle, first.handle, "4" * 64),
        c.Admission(c.identity(first.source), first.requester_digest, "d" * 64, "5" * 64))
    second = r.Ticket("6" * 32, "7" * 32, replace(source_series(), pr_number=6), "8" * 64)
    after = r.admit_authenticated(before, second, r.Obligation(second.obligation_handle, second.handle, "4" * 64),
        c.Admission(c.identity(second.source), second.requester_digest, "d" * 64, "5" * 64))
    return r.build_append(before, after, oid(901), "integration-state", "9" * 32)


class AppendTransport(FakeTransport):
    def __init__(self, api: ControlGitHub, request: r.AppendRequest) -> None:
        super().__init__({}); self.api = api; self.append = request

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        assert method == "POST" and path == "graphql" and body is not None
        self.calls.append((method, path, body))
        variables = g._object(body["variables"]); request = g._object(variables["input"])
        assert request["expectedHeadOid"] == oid(901)
        assert g._object(request["branch"])["branchName"] == "integration-state"
        self.api.tip = oid(902)
        self.api.records.update({path: g.base64.b64decode(raw) for path, raw in self.append.additions})
        for path in self.append.deletions: del self.api.records[path]
        return {"data": {"createCommitOnBranch": {"commit": {"oid": oid(902)}, "ref": {"target": {"oid": oid(902)}}}}}


class ControlGitHub(g.GitHub):
    def _current_enrollment(self) -> None:
        return None  # This store fixture supplies qualified policy independently.

    def __init__(self, request: r.AppendRequest) -> None:
        enrolled = replace(enrollment(), enabled=True, native_guard_digest="9" * 64)
        super().__init__(FakeTransport({}), enrolled, MemoryProof(), policy_path=".github/integration.json")
        self.tip = oid(901)
        self.records = {"integration/v2/target.json": r.encode(request.before.target)}
        self.records.update({"integration/v2/tickets/" + row.handle + ".json": r.encode(row) for row in request.before.tickets})
        self.records.update({"integration/v2/obligations/" + row.handle + ".json": r.encode(row) for row in request.before.obligations})
        self.transport = AppendTransport(self, request)

    def observe_policy(self) -> g.TargetGuards:
        return g.TargetGuards((g.CheckRequirement("gate", 15368),), False, "9" * 64)

    def _root(self, head: str) -> None:
        assert head == oid(901)

    def ref(self, branch: str) -> str:
        assert branch == "integration-state"
        return self.tip

    def git_commit(self, oid: str) -> g.GitCommit:
        return g.GitCommit(oid, "f" * 40, (f"{901:040x}",))

    def file_at(self, head: str, path: str) -> bytes | None:
        return self.records.get(path)


def test_control_append_uses_expected_tip_cas_and_preserves_uncached_archive_names() -> None:
    request = admission_append(); api = ControlGitHub(request)
    assert api.append(request) == oid(902)
    request = admission_append(); api = ControlGitHub(request)
    api.records["integration/v2/archive/tickets/" + "6" * 32 + ".json"] = b"old immutable archive"
    with pytest.raises(c.Conflict, match="ticket_handle_reused"): api.append(request)
    assert isinstance(api.transport, AppendTransport)
    assert api.transport.calls == []


def test_control_append_compares_unchanged_before_custody_not_only_changed_paths() -> None:
    request = admission_append(); api = ControlGitHub(request)
    api.records["integration/v2/tickets/" + "1" * 32 + ".json"] = b"different native before image"
    with pytest.raises(c.Conflict, match="control_before_image_changed"): api.append(request)
    assert isinstance(api.transport, AppendTransport)
    assert api.transport.calls == []



@pytest.mark.parametrize("defect", ["suite_missing", "head_object", "attempt_bool"])
def test_malformed_native_identity_cannot_pass_or_escape_typed_boundary(defect: str) -> None:
    check, job, run = native_check()
    if defect == "suite_missing": check["check_suite"] = {}; run.pop("check_suite_id")
    if defect == "head_object": check["head_sha"] = {}
    if defect == "attempt_bool": job["run_attempt"] = True; run["run_attempt"] = 1
    with pytest.raises((c.Invalid, c.Unavailable)):
        g.verify_check(check, job, run, g.CheckBinding("gate", 15368, 61, ".github/workflows/test.yml", "pull_request"),
            head=oid(10), tested_oid=oid(11), pr_number=5, producer_digest="a" * 64)


def test_artifact_template_rejects_unmatched_closing_token_lookalike() -> None:
    with pytest.raises(c.Invalid):
        g.ReceiptBinding("artifact-attempt}", "receipt.json",
            (g.IdentityField(("tested",), "tested_oid"), g.IdentityField(("run",), "run_id"), g.IdentityField(("attempt",), "attempt")))



def test_ordinary_mode_does_not_silently_use_enrolled_review_exception() -> None:
    state = reserved_state(); ticket = state.ticket("1" * 32); assert ticket.reservation is not None
    api = MutationGitHub(state); api.enrollment = replace(api.enrollment, review_exception=True)
    api.requires_approval = True
    assert isinstance(api.transport, ArchiveTransport)
    api.transport.review_decision = "REVIEW_REQUIRED"
    with pytest.raises(g.NativeRejection): api.merge(ticket, ticket.reservation)
    assert not api.writes


def test_admin_mode_requires_explicit_repo_review_exception() -> None:
    state = reserved_state(); old = state.ticket("1" * 32)
    ticket = replace(old, delivery_mode="admin")
    state = replace(state, tickets=(ticket,)); assert ticket.reservation is not None
    api = MutationGitHub(state)
    with pytest.raises(g.NativeRejection): api.merge(ticket, ticket.reservation)
    assert not api.writes


def test_native_refresh_independently_refuses_missing_task_authority() -> None:
    state = reserved_state("refresh"); old = state.ticket("1" * 32)
    ticket = replace(old, guarded_refresh=False)
    state = replace(state, tickets=(ticket,)); assert ticket.reservation is not None
    api = RefreshGitHub(state); transport = RefreshTransport(api); api.transport = transport
    with pytest.raises(g.NativeRejection): api.refresh(ticket, ticket.reservation)
    assert transport.calls == []



class BypassReviewGitHub(QualifiedGitHub):
    def _classic(self, branch: str) -> object:
        return None

    def _rules(self, branch: str) -> list[object]:
        return [ruleset("pull_request", "always")]


def test_ordinary_required_review_cannot_use_bypass_identity_even_after_approval() -> None:
    api = BypassReviewGitHub(); assert isinstance(api.transport, ArchiveTransport)
    api.enrollment = replace(api.enrollment, review_exception=True)
    api.transport.review_decision = "APPROVED"
    source = source_series(); ticket = r.Ticket("1" * 32, "2" * 32, source, "3" * 64)
    with pytest.raises(c.Unavailable, match="ordinary_review_guard_not_atomic"):
        api._delivery_authority(ticket, ready_candidate(api))



class RetentionGitHub(ControlGitHub):
    def __init__(self, request: r.AppendRequest) -> None:
        super().__init__(request); self.request = request
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def _write(self, method: str, path: str, body: dict[str, object]) -> object:
        self.calls.append((method, path, body))
        if path == "git/trees":
            assert body["base_tree"] == "f" * 40
            for raw in g._array(body["tree"]):
                assert g._text(g._object(raw)["path"]).startswith("integration/v2/")
            return {"sha": oid(903)}
        if path == "git/commits":
            assert body["tree"] == oid(903) and body["parents"] == list(self.request.parents)
            return {"sha": oid(904)}
        assert method == "PATCH" and path == "git/refs/heads/integration-state"
        assert body == {"sha": oid(904), "force": False}
        self.tip = oid(904)
        self.records.update({path: g.base64.b64decode(raw) for path, raw in self.request.additions})
        return {"object": {"sha": oid(904)}}

    def git_commit(self, oid: str) -> g.GitCommit:
        if oid == f"{904:040x}": return g.GitCommit(oid, f"{903:040x}", self.request.parents)
        return super().git_commit(oid)


def test_retention_append_has_control_first_parent_source_custody_and_data_only_tree() -> None:
    after = reserved_state(); ticket = after.ticket("1" * 32)
    before = replace(after, tickets=(replace(ticket, reservation=None, qualification=None),), action=None)
    request = r.build_append(before, after, oid(901), "integration-state", "c" * 32)
    assert request.parents == (oid(901), oid(10))
    api = RetentionGitHub(request)
    assert api.append(request) == oid(904)
    assert [(method, path) for method, path, _ in api.calls] == [
        ("POST", "git/trees"), ("POST", "git/commits"), ("PATCH", "git/refs/heads/integration-state")]


def user_control_rules(kind: str = "User", actor_id: object = 7) -> tuple[object, ...]:
    return (
        {"id": 2, "enforcement": "active", "current_user_can_bypass": "never", "bypass_actors": [],
         "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]},
        {"id": 3, "enforcement": "active", "current_user_can_bypass": "always",
         "bypass_actors": [{"actor_type": kind, "actor_id": actor_id, "bypass_mode": "always"}],
         "rules": [{"type": "update"}]},
    )


def test_narrow_user_control_bypass_requires_exact_enrolled_human_without_admin_expansion() -> None:
    observed = g.verify_control_policy(user_control_rules(), (g.ControlActor("User", 7),))
    assert len(observed) == 64
    with pytest.raises(c.Unavailable, match="control_writer_not_enrolled"):
        g.verify_control_policy(user_control_rules(actor_id=8), (g.ControlActor("User", 7),))


@pytest.mark.parametrize("kind,actor_id", [("Team", 7), ("OrganizationAdmin", 7), ("RepositoryRole", 4),
                                          ("User", True), ("User", None)])
def test_user_control_support_never_accepts_broad_or_malformed_actor_identity(kind: str, actor_id: object) -> None:
    with pytest.raises((c.Invalid, c.Unavailable)):
        g.verify_control_policy(user_control_rules(kind, actor_id), (g.ControlActor("User", 7),))


@pytest.mark.parametrize("kind", ["closed", "draft"])
def test_positive_same_pr_closure_or_draft_has_typed_source_failure(kind: str) -> None:
    value = pull()
    if kind == "closed": value["state"] = "closed"
    else: value["draft"] = True
    with pytest.raises(g.SourceChanged) as result:
        FactGitHub(value).observe_pr(5)
    assert len(result.value.failure_digest) == 64


@pytest.mark.parametrize("defect", ["foreign_repo", "wrong_number", "missing_node", "contradictory_merge"])
def test_closed_or_draft_label_cannot_spoof_source_failure_for_wrong_identity(defect: str) -> None:
    value = pull(); value["draft"] = True
    if defect == "foreign_repo": value["head"] = {"sha": oid(10), "ref": "task", "repo": {"id": 99, "full_name": "other/repo"}}
    if defect == "wrong_number": value["number"] = 99
    if defect == "missing_node": value.pop("node_id")
    if defect == "contradictory_merge": value["merged_at"] = "2026-11-11T00:00:00Z"
    with pytest.raises((c.Invalid, c.Unavailable)) as result:
        FactGitHub(value).observe_pr(5)
    assert not isinstance(result.value, g.SourceChanged)


@pytest.mark.parametrize("kind", ["refresh", "merge"])
def test_direct_uncertain_reservation_never_manufactures_no_effect_or_issues_rpc(kind: str) -> None:
    state = reserved_state(kind)
    ticket = state.ticket("1" * 32); assert ticket.reservation is not None
    state = r.mark_uncertain(state, ticket.handle, ticket.generation, ticket.reservation.operation_id)
    ticket = state.ticket(ticket.handle); assert ticket.reservation is not None
    api = MutationGitHub(state); transport = FakeTransport({}); api.transport = transport
    with pytest.raises(c.Ambiguous):
        if kind == "refresh": api.refresh(ticket, ticket.reservation)
        else: api.merge(ticket, ticket.reservation)
    assert api.writes == [] and transport.calls == []


def live_policy_config() -> h.HostedConfig:
    selected = h.HostedConfig(True, replace(enrollment(enabled=True), native_guard_digest="9" * 64), check_plan(),
        80, ".github/workflows/coordinator.yml", oid(500), oid(501), "example/shared", "coordinate", (7,))
    assert selected.enrollment is not None
    return replace(selected, enrollment=replace(selected.enrollment, policy_digest=h.policy_identity(selected)))


class CurrentPolicyGitHub(g.GitHub):
    def __init__(self, config: h.HostedConfig) -> None:
        assert config.enrollment is not None and config.check_plan is not None
        super().__init__(FakeTransport({}), config.enrollment, MemoryProof(), config.check_plan,
                         policy_path=".github/integration.json")
        self.current_default = oid(990)
        self.policy_raw: bytes | None = c._canonical(h._config_data(config))
        self.policy_reads: list[tuple[str, str]] = []

    def _repository(self) -> dict[str, object]:
        return {"id": 51, "full_name": "example/repo", "default_branch": "main"}

    def ref(self, branch: str) -> str:
        assert branch == "main"
        return self.current_default

    def file_at(self, head: str, path: str) -> bytes | None:
        self.policy_reads.append((head, path))
        assert head == self.current_default and path == ".github/integration.json"
        return self.policy_raw


def test_live_authority_rereads_current_default_enrollment_instead_of_run_snapshot() -> None:
    api = CurrentPolicyGitHub(live_policy_config())
    api._live()
    api.current_default = oid(991)
    api.policy_raw = b'{"schema_version":2,"enabled":false}'
    with pytest.raises(c.Unavailable, match="current_enrollment"):
        api._live()
    assert api.policy_reads == [(oid(990), ".github/integration.json"), (oid(991), ".github/integration.json")]
    assert isinstance(api.transport, FakeTransport) and not api.transport.calls


@pytest.mark.parametrize("kind", ["missing", "malformed", "replacement"])
def test_current_policy_loss_or_replacement_cannot_preserve_old_live_authority(kind: str) -> None:
    config = live_policy_config(); api = CurrentPolicyGitHub(config)
    if kind == "missing": api.policy_raw = None
    if kind == "malformed": api.policy_raw = b'{"enabled":true}'
    if kind == "replacement":
        assert config.enrollment is not None
        changed = replace(config, requester_ids=(7, 8))
        changed = replace(changed, enrollment=replace(config.enrollment, policy_digest=h.policy_identity(changed)))
        api.policy_raw = c._canonical(h._config_data(changed))
    with pytest.raises(c.Unavailable, match="current_enrollment"):
        api._live()


def test_missing_live_policy_binding_refuses_before_provider_access() -> None:
    selected = replace(enrollment(enabled=True), native_guard_digest="9" * 64)
    transport = FakeTransport({})
    with pytest.raises(c.Unavailable, match="current_enrollment_binding_missing"):
        g.GitHub(transport, selected)._live()
    assert not transport.calls


class RefusedProof(MemoryProof):
    def __init__(self, transient: bool = False) -> None:
        self.transient = transient

    def prove_refresh(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
        if self.transient: raise c.Unavailable("proof_transport_unavailable")
        raise c.Invalid("unsupported_source_phase")


def test_deterministic_projection_refusal_is_source_changed_but_transient_failure_is_not() -> None:
    api = FactGitHub(); api.proof = RefusedProof()
    with pytest.raises(g.SourceChanged): api.projection(source_series(), oid(10), oid(1))
    api.proof = RefusedProof(transient=True)
    with pytest.raises(c.Unavailable) as result: api.projection(source_series(), oid(10), oid(1))
    assert not isinstance(result.value, g.SourceChanged)
