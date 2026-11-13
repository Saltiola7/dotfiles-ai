"""Local submissions use an injected credential owner and honest admission status."""
from __future__ import annotations

import base64
from dataclasses import replace
import json

import pytest

from test_integration_controller import config, envelope, oid
from integration_coordinator import controller as h, core as c, runtime as r
from integration_coordinator import github as g
from integration_coordinator.client import LocalClient
from test_integration_runtime import queued


class Remote:
    def __init__(self) -> None:
        selected = config()
        assert selected.enrollment is not None
        self.config = replace(selected, enrollment=replace(selected.enrollment,
                                                           policy_digest=h.policy_identity(selected)))
        self.payload = c._canonical(h._config_data(self.config))
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []
        self.symlink = False
        self.actor = 5

    def request(self, method: str, path: str, body: dict[str, object] | None = None) -> object:
        self.calls.append((method, path, body))
        if path == "user": return {"id": self.actor, "login": "fixture"}
        if path == "repos/example/repo": return {"id": 1, "full_name": "example/repo", "default_branch": "main"}
        if path == "repos/example/repo/contents/.github/integration.json?ref=main":
            return {"type": "file", "encoding": "base64", "size": len(self.payload),
                    "content": base64.b64encode(self.payload).decode()}
        if path.endswith("/git/ref/heads/main"):
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": oid(10)}}
        if path.endswith("/git/commits/" + oid(10)):
            return {"sha": oid(10), "tree": {"sha": oid(11)}, "parents": []}
        if path.endswith("/git/trees/" + oid(11)):
            return {"sha": oid(11), "truncated": False, "tree": [
                {"path": ".github", "mode": "040000", "type": "tree", "sha": oid(12)}]}
        if path.endswith("/git/trees/" + oid(12)):
            return {"sha": oid(12), "truncated": False, "tree": [
                {"path": "integration.json", "mode": "120000" if self.symlink else "100644",
                 "type": "blob", "sha": oid(13)}]}
        if path.endswith("/git/blobs/" + oid(13)):
            return {"sha": oid(13), "encoding": "base64", "size": len(self.payload),
                    "content": base64.b64encode(self.payload).decode()}
        if path == "repos/example/repo/actions/workflows/80/dispatches" and method == "POST":
            return None
        raise AssertionError((method, path))

    def archive(self, path: str) -> bytes:
        raise AssertionError("No artifact is needed for submission")

    def local_policy(self) -> dict[str, object]:
        assert self.config.enrollment is not None
        return {"schema_version": 1, "protocol_version": 2, "enabled": True, "strategy": "rebase",
                "remote_repository": "example/repo", "target_ref": "refs/heads/main",
                "control_ref": "refs/heads/control", "policy_path": ".github/integration.json",
                "policy_digest": self.config.enrollment.policy_digest, "guarded_refresh": True}

    def source_request(self) -> dict[str, object]:
        value = json.loads(envelope())
        assert self.config.enrollment is not None
        value["policy_digest"] = self.config.enrollment.policy_digest
        return value


def test_dispatch_acceptance_is_unadmitted_until_durable_ledger_acknowledges() -> None:
    remote = Remote()
    result = LocalClient(remote, remote.local_policy()).submit(remote.source_request())
    assert result["status"] == "unadmitted" and result["dispatch"] == "accepted"
    writes = [item for item in remote.calls if item[0] != "GET"]
    assert len(writes) == 1 and writes[0][1].endswith("/dispatches")
    assert writes[0][2] is not None and writes[0][2]["ref"] == "main"


@pytest.mark.parametrize("defect", ["remote_pin", "request_pin", "actor", "symlink", "foreign_target", "refresh_permission"])
def test_unqualified_submission_never_dispatches(defect: str) -> None:
    remote = Remote()
    policy = remote.local_policy()
    request = remote.source_request()
    if defect == "remote_pin": policy["policy_digest"] = "e" * 64
    if defect == "request_pin": request["policy_digest"] = "e" * 64
    if defect == "actor": remote.actor = 99
    if defect == "symlink": remote.symlink = True
    if defect == "foreign_target": policy["target_ref"] = "refs/heads/other"
    if defect == "refresh_permission": policy["guarded_refresh"] = False
    with pytest.raises((c.Invalid, c.Unavailable, c.Conflict)):
        LocalClient(remote, policy).submit(request)
    assert all(method == "GET" for method, _, _ in remote.calls)


def test_oversized_or_untrusted_shape_is_refused_without_a_network_write() -> None:
    remote = Remote()
    request = remote.source_request()
    request["private_path"] = "x" * 50000
    with pytest.raises(c.Invalid):
        LocalClient(remote, remote.local_policy()).submit(request)
    assert all(method == "GET" for method, _, _ in remote.calls)


class StatusNative(g.GitHub):
    def __init__(self, remote: Remote, wrong_policy: bool = False) -> None:
        assert remote.config.enrollment is not None and remote.config.check_plan is not None
        super().__init__(remote, remote.config.enrollment, plan=remote.config.check_plan)
        view = queued()
        self.state = replace(view, target=replace(view.target,
            policy_digest="e" * 64 if wrong_policy else self.enrollment.policy_digest))

    def observe_policy(self) -> g.TargetGuards:
        return g.TargetGuards((), False, "a" * 64)

    def ref(self, branch: str) -> str:
        assert branch == self.enrollment.control_branch
        return oid(1000)

    def file_at(self, head: str, path: str) -> bytes | None:
        assert head == oid(1000)
        for value in self.state.obligations:
            if path == f"integration/v2/obligations/{value.handle}.json":
                return r.encode(value)
        return None

    def read_control(self, lookup_handles: tuple[str, ...] = ()) -> tuple[str, dict[str, bytes]]:
        rows = {"integration/v2/target.json": r.encode(self.state.target)}
        rows.update({f"integration/v2/tickets/{v.handle}.json": r.encode(v) for v in self.state.tickets})
        rows.update({f"integration/v2/obligations/{v.handle}.json": r.encode(v) for v in self.state.obligations})
        return oid(1000), rows


def test_status_rejects_target_policy_drift_even_with_a_valid_root_and_schema() -> None:
    remote = Remote()
    client = LocalClient(remote, remote.local_policy())
    native = StatusNative(remote, wrong_policy=True)
    client._loaded = remote.config, native
    ticket = native.state.tickets[0]
    with pytest.raises(c.Unavailable):
        client.status(ticket.handle, ticket.obligation_handle)


def test_status_reports_only_the_pinned_obligation_and_current_ticket() -> None:
    remote = Remote()
    client = LocalClient(remote, remote.local_policy())
    native = StatusNative(remote)
    client._loaded = remote.config, native
    ticket = native.state.tickets[0]
    status = client.status(ticket.handle, ticket.obligation_handle)
    assert status is not None and status.report()["status"] == "queued"
    assert status.ticket == ticket
    assert status.report()["repository"] == ticket.source.repository
    assert status.report()["pr_number"] == ticket.source.pr_number
    assert status.report()["head"] == ticket.current_head
    assert status.report()["tested_oid"] is None


def delivered(remote: Remote) -> r.RuntimeSnapshot:
    assert remote.config.enrollment is not None and remote.config.check_plan is not None
    selected = remote.config.enrollment
    source = r.SourceSeries("example/repo", 1, oid(1), oid(10),
                            (r.SourceEntry(oid(10), "phase", ("domain",)),), "a" * 64)
    ticket = r.Ticket("1" * 32, "2" * 32, source, r.requester_digest("example/repo", 5))
    state = r.RuntimeSnapshot(r.Target("example/repo", "main", selected.root_oid, selected.policy_digest), (), ())
    state = r.admit_authenticated(state, ticket, r.Obligation(ticket.obligation_handle, ticket.handle, "b" * 64),
        c.Admission(c.identity(source), ticket.requester_digest, selected.policy_digest, "c" * 64))
    state = r.claim(state, ticket.handle, oid(1), remote.config.check_plan.digest)
    projection = r.Projection(c.identity(source), oid(1), oid(10), (c.CommitPair(oid(10), oid(10)),), "d" * 64)
    state = r.bind_projection(state, ticket.handle, 1, projection)
    candidate = r.Candidate(1, c.identity(source), c.identity(projection), oid(10), oid(1), oid(11),
                            (oid(1), oid(10)), oid(20), remote.config.check_plan.digest, selected.policy_digest)
    state = r.bind_candidate(state, ticket.handle, 1, candidate)
    qualified = c.Qualification(c.identity(candidate), candidate.plan_digest, selected.policy_digest, "e" * 64,
                                 (c.Evidence("check", 15368, 70, 1, oid(11), "f" * 64),))
    invocation = r.Invocation(71, 1, "3" * 32, "a" * 64)
    state = r.reserve_native(state, ticket.handle, 1, "merge", "4" * 32, invocation, qualification=qualified)
    outcome = r.Delivery("4" * 32, invocation, c.identity(candidate), c.identity(projection), 1, oid(30),
                         (c.CommitPair(oid(10), oid(30)),), "b" * 64)
    return r.record_delivery(state, ticket.handle, 1, outcome)


class DeliveryProof:
    def __init__(self, state: r.RuntimeSnapshot, defect: str = "") -> None:
        self.ticket = state.tickets[0]
        self.defect = defect

    def prove_refresh(self, source: r.SourceSeries, head: str, base: str) -> r.Projection:
        assert self.ticket.projection is not None and source == self.ticket.source
        return self.ticket.projection

    def prove_delivery(self, source: r.SourceSeries, projection: r.Projection,
                       merge_oid: str) -> tuple[c.CommitPair, ...]:
        assert source == self.ticket.source and self.ticket.delivery is not None
        if self.defect == "mapping": return (c.CommitPair(oid(10), oid(40)),)
        return self.ticket.delivery.mapping

    def excludes_root(self, root: str, heads: tuple[str, ...]) -> bool:
        assert root == oid(30) and heads == (oid(31),)
        return self.defect == "containment"


class DeliveredNative(StatusNative):
    def __init__(self, remote: Remote, defect: str = "") -> None:
        super().__init__(remote)
        self.state = delivered(remote)
        self.defect = defect

    def ref(self, branch: str) -> str:
        return oid(31) if branch == "main" else oid(1000)

    def observe_pr(self, number: int) -> g.PullFacts:
        return g.PullFacts(number, "PR_fixture", oid(10), oid(31), "task", "main",
                           oid(40) if self.defect == "merge" else oid(30), True, "2026-01-01T00:00:00Z")

    def git_commit(self, oid: str) -> g.GitCommit:
        ticket = self.state.tickets[0]
        assert ticket.delivery is not None and ticket.candidate is not None
        assert oid == ticket.delivery.merge_oid
        parent = f"{9:040x}" if self.defect == "parent" else ticket.candidate.base
        return g.GitCommit(oid, ticket.candidate.tree, (parent,))

    def pages(self, path: str, key: str | None = None, *, limit: int = 4096) -> list[object]:
        assert path == "commits/" + oid(30) + "/pulls"
        return [{"number": 999 if self.defect == "introduction" else 1, "state": "closed",
                 "merged_at": "2026-01-01T00:00:00Z", "html_url": "https://github.com/example/repo/pull/1",
                 "base": {"repo": {"full_name": "example/repo"}}}]


@pytest.mark.parametrize("defect", ["", "mapping", "containment", "merge", "parent", "introduction"])
def test_delivered_outcome_requires_every_native_and_correspondence_link(defect: str) -> None:
    remote = Remote()
    native = DeliveredNative(remote, defect)
    proof = DeliveryProof(native.state, defect)
    client = LocalClient(remote, remote.local_policy(), proof)
    client._loaded = remote.config, native
    if defect:
        with pytest.raises(c.Unavailable):
            client.verify_delivered("1" * 32, "2" * 32)
    else:
        outcome = client.verify_delivered("1" * 32, "2" * 32)
        assert outcome.mapping == (c.CommitPair(oid(10), oid(30)),)
        assert outcome.landed_base == oid(1) and outcome.target_head == oid(31)
        assert len(outcome.verification_digest) == 64
