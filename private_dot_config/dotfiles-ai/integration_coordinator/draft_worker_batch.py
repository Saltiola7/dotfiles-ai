"""One reviewed launch-only grant, one durable dispatch cursor per worker."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import PurePosixPath
import re

from . import core, initiative_authority as authority, initiative_controller as controller, lifecycle as l
from .initiative_service import open_execution


class RoutedTransport:
    """Apply the approved route to creation and require explicit session readback."""
    def __init__(self, transport, agent, model, variant):
        provider, identifier = model.split("/", 1)
        self.transport = transport
        self.agent = agent
        self.model = {"providerID": provider, "id": identifier, "variant": variant}

    def qualification(self):
        return self.transport.qualification()

    def request(self, method, path, payload=None):
        create = (method, path) == ("POST", "/api/session")
        if create:
            if payload.get("agent") != self.agent:
                raise core.Conflict("draft_worker_native_agent_changed")
            payload = {**payload, "model": self.model}
        response = self.transport.request(method, path, payload)
        if response.status == 200 and (create or method == "GET" and re.fullmatch(r"/api/session/ses_[^/]+", path)):
            data = response.value.get("data") if isinstance(response.value, dict) else None
            if not isinstance(data, dict) or data.get("agent") != self.agent or data.get("model") != self.model:
                raise core.Ambiguous("draft_worker_native_model_unproved")
        return response


def claims(value):
    if not isinstance(value, dict) or not 1 <= len(value) <= 64:
        raise ValueError("draft batch requires 1-64 selected slices")
    paths = []
    resources = set()
    for identifier, item in value.items():
        l.initiative_slice_id(identifier)
        if not isinstance(item, dict) or set(item) != {"write_set", "shared_resources", "agent", "model", "variant"}:
            raise ValueError("invalid draft slice claims")
        if item["agent"] not in ("build", "build-gpt", "build-claude") or item["variant"] != "medium":
            raise ValueError("expected an exact approved Build agent and medium variant")
        if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9.@_-]+", l.text(item["model"])):
            raise ValueError("expected provider/model route")
        writes, shared = item["write_set"], item["shared_resources"]
        if not isinstance(writes, list) or not 1 <= len(writes) <= 256 or not isinstance(shared, list):
            raise ValueError("invalid draft write set")
        for raw in writes:
            path = PurePosixPath(l.text(raw, 1024))
            if (not re.fullmatch(r"[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)*", raw)
                    or path.as_posix() != raw or not path.parts or ".." in path.parts
                    or ".git" in (p.casefold() for p in path.parts)):
                raise ValueError("invalid draft claim path")
            path = PurePosixPath(raw.casefold())
            if any(p == path or p in path.parents or path in p.parents for p in paths):
                raise ValueError("overlapping draft write sets")
            paths.append(path)
        for resource in shared:
            if not re.fullmatch(r"[a-z0-9][a-z0-9._:-]{0,127}", l.text(resource)) or resource in resources:
                raise ValueError("invalid or overlapping shared resource")
            resources.add(resource)
    return value


def binding(runtime, recipe, graph):
    result = dict(runtime.binding(recipe))
    result["qualification_digest"] = l.digest({"draft_worker_batch": graph, "native": result["qualification_digest"]})
    return result


def prepare(runtime, selection, approved_at, expires_at):
    recipe = runtime.recipe()
    if recipe.forgejo is not None:
        raise ValueError("draft batch requires GitHub draft delivery")
    chosen = tuple(sorted(claims(selection)))
    scope = runtime.committed_scope(recipe, chosen)
    graph = {"schema_version": 2, "intent": "draft_pr", "integration_mode": "draft_pr",
             "source": str(recipe.authority_checkout), "workers": {}}
    for key in chosen:
        checkout, plan = runtime.preview_slice(recipe, key)
        if selection[key]["agent"] != recipe.writer_agent:
            raise ValueError("draft worker agent differs from enrolled recipe")
        graph["workers"][key] = {**selection[key], "checkout": str(checkout), "plan": plan,
                                 "depends_on": scope["slices"][key]["depends_on"]}
    proposal = authority.grant_proposal(scope, binding=binding(runtime, recipe, graph),
                                        operator_id=runtime.operator_identity(), approved_at=approved_at,
                                        expires_at=expires_at, allowed_operations=("launch",), repair_limit=0)
    return {"graph": graph, "scope": scope, "proposal": proposal, "approval_digest": l.digest(proposal)}


def _directory(custody, identity, create=False):
    path = custody.directory / ("draft-batch-" + l.hex_value(identity))
    custody._directory(path, create)
    return path


class _Journal:
    """Namespace the existing inode-anchored ExecutionStore by grant and slice."""
    def __init__(self, custody, grant, key, create):
        self.directory = _directory(custody, grant, create) / l.digest({"slice": key})
        custody._directory(self.directory, create)
        self._read, self._write = custody._read, custody._write


def journal(custody, grant, key, create=False):
    return open_execution(_Journal(custody, grant, key, create), create=create)


def accept(runtime, selection, approved_at, expires_at, expected, now, *, approval="interactive"):
    custody = runtime.custody
    if approval not in {"interactive", "agent-confirmed"}:
        raise ValueError("unknown draft approval method")
    with authority.initiative_effect_lock(custody, l.digest("draft-batch-acceptance")):
        review = prepare(runtime, selection, approved_at, expires_at)
        if (l.hex_value(expected) != review["approval_digest"]
                or not l.initiative_time(approved_at) <= l.initiative_time(now()) < l.initiative_time(expires_at)):
            raise ValueError("draft batch approval changed or expired")
        grant = l.digest({"schema_version": 1, "kind": "initiative_grant", "value": review["proposal"]})
        for prior in custody.directory.glob("draft-batch-*"):
            if prior.name == "draft-batch-" + grant:
                continue
            previous = json.loads(custody._read(prior / "graph.json"), object_pairs_hook=l.no_duplicates)
            old = prior.name.removeprefix("draft-batch-")
            prior_grant, prior_scope = authority.read_grant(custody, old)
            native = json.loads(custody._read(prior / "native.json"))
            if (prior_grant["binding"]["qualification_digest"] != l.digest({"draft_worker_batch": previous,
                    "native": native}) or set(previous["workers"]) != set(prior_scope["selected"])):
                raise ValueError("retained draft claims changed")
            for item in review["graph"]["workers"].values():
                for key, other in previous["workers"].items():
                    if item["plan"]["cycle_id"] == other["plan"]["cycle_id"]:
                        raise ValueError("draft batch cycle identity already retained")
                    overlap = set(item["shared_resources"]) & set(other["shared_resources"])
                    same_worker = (item["checkout"] == other["checkout"]
                                   or item["plan"]["checkout"]["branch"] == other["plan"]["checkout"]["branch"])
                    if same_worker or overlap or any(
                        a == b or a in b.parents or b in a.parents
                        for a in map(PurePosixPath, (p.casefold() for p in item["write_set"]))
                        for b in map(PurePosixPath, (p.casefold() for p in other["write_set"]))
                    ):
                        state = journal(custody, old, key).execution(old, key)
                        if (state is None or state.state != "dispatched"
                                or runtime.terminal_delivery(state.activation, other) is not True):
                            raise ValueError("draft batch conflicts with retained worker claims")
        native = runtime.binding(runtime.recipe())["qualification_digest"]
        if (review["proposal"]["binding"]["qualification_digest"] != l.digest({"draft_worker_batch": review["graph"],
                "native": native}) or l.initiative_time(now()) >= l.initiative_time(expires_at)):
            raise ValueError("draft approval changed before acceptance")
        path = _directory(custody, grant, True)
        custody._write(path / "graph.json", l.canonical(review["graph"]))
        custody._write(path / "native.json", l.canonical(native))
        custody._write(path / "confirmation.json", l.canonical({"method": approval, "approval_digest": expected}))
        # The append-only graph is the claim inventory. Never replace an old
        # cycle identity or infer that expiration/revocation ended a worker.
        for key in review["graph"]["workers"]:
            journal(custody, grant, key, True)
        return authority.store_grant(custody, review["scope"], review["proposal"], expected_approval_digest=expected)


def read_graph(runtime, grant):
    proposal, scope = authority.read_grant(runtime.custody, grant)
    graph = json.loads(runtime.custody._read(_directory(runtime.custody, grant) / "graph.json"),
                       object_pairs_hook=l.no_duplicates)
    if (graph["schema_version"] != 2 or proposal["allowed_operations"] != ["launch"] or graph["intent"] != "draft_pr"
            or set(scope["selected"]) != set(graph["workers"])
            or proposal["binding"] != binding(runtime, runtime.recipe(), graph)):
        raise ValueError("draft batch binding changed")
    return graph


def authorize(runtime, grant, graph, key, now):
    recipe = runtime.recipe()
    current = runtime.committed_scope(recipe, (key,))
    if current["source_commit"] != graph["workers"][key]["plan"]["source_commit"]:
        raise ValueError("draft batch source changed")
    return authority.require_grant(runtime.custody, grant, binding=binding(runtime, recipe, graph),
                                   current=current, slice_id=key, operation="launch", now=now())


class DraftController(controller.InitiativeController):
    def _dependency_delivered(self, approval, selected, dependency):
        # A dispatched draft never unlocks its consumers. Re-read a
        # separately protected delivery receipt even for an in-batch producer.
        return self.verified_dependency(approval, dependency)


def build(runtime, grant, now):
    """Round-robin dispatch. Native workers run concurrently after release.

    Begin owns process-wide cwd; never register checkouts on Python threads.
    Re-entering after any claimed effect only observes the same native ID.
    """
    graph = read_graph(runtime, grant)
    recipe = runtime.recipe()
    workers = graph["workers"]
    reports = {}
    for key in workers:
        authorize(runtime, grant, graph, key, now)
    for _ in range(8):
        changed = False
        for key, item in workers.items():
            authorize(runtime, grant, graph, key, now)
            store = journal(runtime.custody, grant, key)
            port = authority.CustodyAuthority(runtime.custody,
                current_binding=lambda: binding(runtime, runtime.recipe(), graph),
                current_scope=lambda k: runtime.committed_scope(recipe, (k,)),
                plan=lambda k: runtime.launch(grant, graph, k),
                prior_delivery=lambda ap, k, scope: runtime.prior_delivery(recipe, ap, k, scope), clock=now)
            ctl = DraftController(store, port, runtime.worker_writer(item), runtime.provider, registration=runtime)
            def verified_dependency(approval, dep):
                _, scope = authority.read_grant(runtime.custody, grant)
                try:
                    return runtime.prior_delivery(recipe, approval, dep, scope["slices"][dep]) is True
                except FileNotFoundError:
                    # No prior protected delivery journal: keep the consumer
                    # waiting without preventing independent workers starting.
                    return False
            ctl.verified_dependency = verified_dependency
            approval = ctl._approval(grant)
            if approval.mutation_stop:
                raise ValueError(approval.mutation_stop)
            execution = store.execution(grant, key)
            if execution is None:
                if not all(ctl._dependency_delivered(approval, set(workers), dep) for dep in item["depends_on"]):
                    reports[key] = {"state": "waiting", "depends_on": item["depends_on"]}
                    continue
                launch = port.preflight(approval, key)
                if launch is None:
                    raise ValueError("draft batch launch scope changed")
                activation = controller.Activation.from_launch(approval, key, launch, managed=True)
                if not store._reserve(activation):
                    raise ValueError("draft batch reservation changed")
                execution = store.execution(grant, key)
            activation = execution.activation
            if execution.state == "dispatched":
                released = ctl.writer.observe_release(activation)
                if released is None or not released.delivered or runtime.observed(activation) is None:
                    raise ValueError("draft batch reattachment unverified")
                reports[key] = {"state": "dispatched", "session_id": activation.session_id}
                continue
            if execution.state in {"reserved", "session_ready"}:
                with authority.initiative_effect_lock(runtime.custody, grant):
                    report = ctl._advance_active(execution)
            else:
                report = ctl._advance_active(execution)
            reports[key] = {**asdict(report), "session_id": activation.session_id}
            if report.state in {"uncertain", "blocked", "discovery_reopened", "reprepare"}:
                return reports
            changed |= report.state != execution.state
        if not changed:
            break
    return reports
