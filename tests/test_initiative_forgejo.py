"""Fixture-only Forgejo continuation uses the managed journal and source proof."""
from dataclasses import asdict
from hashlib import sha256
import json

import pytest

from test_integration_forgejo_merge import (
    ACTOR, BASE, HEAD, MERGED, PREVIOUS, PULL, PULL_ID, REVIEWER, SOURCE, TARGET, TREE, Fixture,
)
from integration_coordinator import core, forgejo, initiative_controller as controller, initiative_service, lifecycle


def fixture_document(native):
    return {
        "binding": asdict(native.transport.binding),
        "target_ref": TARGET,
        "root_oid": BASE,
        "actor_id": ACTOR,
        "operator_id": REVIEWER,
        "guard_digest": native.intent.target.guard_digest,
        "dispatcher_digest": native.intent.target.dispatcher_digest,
        "policy_digest": native.plan.policy_digest,
        "checks": [asdict(check) for check in native.plan.checks],
        "bridge_digest": sha256(b"private fixture owner").hexdigest(),
        "draft_prefixes": ["WIP:", "Draft:"],
    }


@pytest.fixture
def custody(tmp_path):
    git = tmp_path / ".git"
    git.mkdir()
    return lifecycle.Custody(git)


def test_managed_recipe_accepts_only_explicit_typed_forgejo_fixture(custody, tmp_path):
    value = {
        "schema_version": 2, "authority_checkout": str(tmp_path.resolve()),
        "manifest_path": "docs/initiatives/test/MANIFEST.json", "writer_agent": "build",
        "forgejo": fixture_document(Fixture()),
        "slices": {"slice-a": {"branch": "topic", "cycle_id": "LOCAL-A", "context": "fixture",
            "risk": "critical", "plan_path": "docs/initiatives/test/A.plan.json", "plan_digest": "c" * 64}},
    }
    custody._write(custody.directory / "initiative-runtime.json", lifecycle.canonical(value))
    recipe = initiative_service.read_recipe(custody)
    assert recipe.forgejo.binding == Fixture().transport.binding
    assert recipe.github_account is None
    assert recipe.forgejo.target_ref == TARGET
    assert recipe.digest == lifecycle.digest({
        **{key: value[key] for key in ("schema_version", "authority_checkout", "manifest_path", "writer_agent")},
        "forgejo": recipe.forgejo.digest, "slices": [asdict(recipe.slice("slice-a"))],
    })


@pytest.mark.parametrize("failure", [None, "lost_merge", "no_ci", "stale_base", "revoked", "lost_pr", "expiry_after_lookup"])
def test_forgejo_handoff_uses_exact_proof_and_never_repeats_native_writes(custody, failure, monkeypatch):
    from integration_coordinator import initiative_forgejo as auto
    from integration_coordinator.initiative_forgejo_bridge import Bridge
    from integration_coordinator.runtime import SourceEntry

    native = Fixture()
    config = auto.parse_fixture(fixture_document(native))
    bridge = Bridge(custody, config)
    ancestry = []

    def observe_ancestry(operation, *, ancestor, descendant):
        assert operation == "ancestor"
        ancestry.append((ancestor, descendant))
        return native.objects.is_ancestor(config.binding, ancestor, descendant)

    monkeypatch.setattr(bridge, "_call", observe_ancestry)
    bound = controller.Target(config.binding.origin, config.binding.repository, TARGET)
    approval = controller.Approval("a" * 64, bound, "b" * 64, "c" * 64, (controller.Slice("slice-a"),))
    launch = controller.Launch("d" * 64, BASE, str(custody.common.parent), "LOCAL-A", "build")
    activation = controller.Activation.from_launch(approval, "slice-a", launch, managed=True)
    proof = auto.Source(SOURCE, BASE, HEAD, TREE, (
        SourceEntry(PREVIOUS, "discovery_import"), SourceEntry(HEAD, "phase", ("refactor",)),
    ), "e" * 64)
    native.objects.refs[SOURCE] = None
    underlying = native.transport

    class Ports:
        binding = config.binding

        def __init__(self):
            self.pr_exists = False
            self.pushes = []
            self.creates = 0

        def ref(self, binding, ref):
            return native.objects.ref(binding, ref)

        def commit(self, binding, oid):
            return native.objects.commit(binding, oid)

        def is_ancestor(self, binding, older, newer):
            return bridge.is_ancestor(binding, older, newer)

        def current_execution(self, subject, check):
            if failure == "no_ci":
                return None
            from dataclasses import replace
            old = native.reader.execution
            return replace(old, subject=subject, receipts=(replace(old.receipts[0], subject=subject),))

        def preconditions(self, intent, reservation, subject, expires_at):
            assert subject == activation and expires_at == 4_000_000_000
            assert intent.pull_request_id == PULL_ID and intent.subject.candidate.tree == TREE
            return native.authority.preconditions

        def push(self, checkout, ref, oid, expires_at):
            assert expires_at == 4_000_000_000
            assert checkout == launch.checkout and ref == SOURCE and oid == HEAD
            self.pushes.append((ref, oid))
            native.objects.refs[ref] = oid

        def request(self, method, path, body=None, *, expires_at=None, expected_base=None, expected_head=None):
            nonlocal stopped
            if method == "POST":
                assert (expected_base, expected_head) == (BASE, HEAD)
                assert expires_at == (native.authority.preconditions.grant.expires_at
                                      if path == PULL + "/merge" else 4_000_000_000)
            if path == PULL.rsplit("/", 1)[0] + "?state=all&page=1&limit=50":
                assert method == "GET"
                if failure == "expiry_after_lookup":
                    stopped = True
                return forgejo.Response(200, [self.pull()] if self.pr_exists else [],
                                        {"X-Total-Count": str(int(self.pr_exists))})
            if path == PULL.rsplit("/", 1)[0] and method == "POST":
                self.creates += 1
                assert body["head"] == "topic" and body["base"] == "main"
                self.pr_exists = True
                if failure == "lost_pr":
                    raise TimeoutError("native PR accepted before reply was lost")
                return forgejo.Response(201, self.pull())
            if path == PULL and method == "GET":
                return forgejo.Response(200, self.pull())
            if path == PULL + "/merge" and method == "POST":
                underlying.authority.claimed = True
            return underlying.request(method, path, body)

        def pull(self):
            return {**underlying.pull(), "title": auto.publication_title(proof), "user": {"id": ACTOR}}

    ports = Ports()
    if failure == "lost_merge":
        underlying.mode = "lost_after_effect"
    if failure == "stale_base":
        native.objects.refs[TARGET] = "9" * 40
    stopped = failure == "revoked"

    def authorize(subject, operation):
        assert subject == activation and operation in {"admit", "merge"}
        if stopped:
            raise core.Unavailable("fixture grant revoked")
        return 4_000_000_000

    delivery = auto.FixtureDelivery(custody, config, ports, lambda current: proof, authorize)
    if failure in {"stale_base", "revoked"}:
        with pytest.raises((core.Unavailable, core.Conflict)):
            delivery.advance(activation)
        assert ports.pushes == [] and ports.creates == 0 and underlying.writes == []
        return
    if failure == "expiry_after_lookup":
        with pytest.raises(core.Unavailable, match="revoked"):
            delivery.advance(activation)
        assert ports.pushes == [(SOURCE, HEAD)] and ports.creates == 0 and underlying.writes == []
        return
    delivery.advance(activation)
    admission = delivery.observe_admission(activation)
    assert admission is not None and ports.pushes == [(SOURCE, HEAD)] and ports.creates == 1
    if failure == "no_ci":
        delivery.advance(activation)
        assert delivery.observe_delivery(activation, admission) is None and not underlying.writes
        return
    if failure == "lost_merge":
        with pytest.raises(core.Ambiguous):
            delivery.advance(activation)
    else:
        delivery.advance(activation)
    stopped = True
    restarted = auto.FixtureDelivery(custody, config, ports, lambda _: pytest.fail("reused checkout"), authorize)
    outcome = restarted.observe_delivery(activation, admission)
    assert outcome is not None and outcome.merge_oid == MERGED
    assert ancestry[-1] == (MERGED, MERGED)
    assert ports.creates == len(underlying.writes) == 1
    assert underlying.writes[0][2]["force_merge"] is False
    assert underlying.writes[0][2]["delete_branch_after_merge"] is False


def test_owner_ancestry_checks_equal_revisions_without_assuming_inclusion(custody, monkeypatch):
    from integration_coordinator import initiative_forgejo as auto
    from integration_coordinator.initiative_forgejo_bridge import Bridge

    config = auto.parse_fixture(fixture_document(Fixture()))
    bridge = Bridge(custody, config)
    calls = []

    def observe_absence(operation, **facts):
        calls.append((operation, facts))
        return False

    monkeypatch.setattr(bridge, "_call", observe_absence)
    assert bridge.is_ancestor(config.binding, BASE, BASE) is False
    with pytest.raises(core.Invalid, match="mixed_oid_formats"):
        bridge.is_ancestor(config.binding, BASE, "a" * 64)
    with pytest.raises(core.Invalid, match="invalid_oid"):
        bridge.is_ancestor(config.binding, "0" * 40, BASE)
    assert calls == [("ancestor", {"ancestor": BASE, "descendant": BASE})]


def test_owner_program_is_required_and_byte_bound(custody):
    from dataclasses import replace
    from integration_coordinator import initiative_forgejo as auto
    from integration_coordinator.initiative_forgejo_bridge import Bridge

    program = b"""import json, sys
call = json.load(sys.stdin)
assert call["operation"] == "ref"
json.dump({"schema_version": 1, "fixture_digest": call["fixture_digest"],
           "result": "a" * 40}, sys.stdout)
"""
    config = replace(auto.parse_fixture(fixture_document(Fixture())),
                     bridge_digest=sha256(program).hexdigest())
    bridge = Bridge(custody, config)
    with pytest.raises(core.Unavailable, match="bridge_unavailable"):
        bridge.ref(config.binding, TARGET)
    custody._write(custody.directory / "forgejo-fixture-provider.py", program)
    assert bridge.ref(config.binding, TARGET) == BASE
    with pytest.raises(core.Conflict, match="bridge_changed"):
        Bridge(custody, replace(config, bridge_digest="8" * 64)).ref(config.binding, TARGET)
    with pytest.raises(core.Invalid, match="http_scope"):
        bridge.request("POST", "/api/v1/repos/another/project/pulls", {})


@pytest.mark.parametrize("credential_source", ["osxkeychain", "systemd"])
def test_managed_forgejo_begin_and_verified_local_completion_use_schema_six(
    monkeypatch, request, capsys, credential_source,
):
    import importlib.machinery
    import importlib.util
    from dataclasses import replace
    from types import SimpleNamespace

    import test_dbsctrctl as harness
    from test_dbsctr_forgejo_completion import evidence
    from test_dbsctr_forgejo_identity import IDENTITY, manifest, write_manifest
    from integration_coordinator import initiative_authority as authority

    fixture = harness.DbsctrctlTest()
    fixture.setUp()
    request.addfinalizer(fixture.tearDown)
    loader = importlib.machinery.SourceFileLoader("managed_forgejo_helper", str(harness.SCRIPT))
    imported = importlib.util.spec_from_loader(loader.name, loader)
    helper = importlib.util.module_from_spec(imported)
    loader.exec_module(helper)
    root = fixture.repo.resolve()
    doc = write_manifest(root, manifest())
    plan = doc.with_name("LOCAL.plan.json")
    plan.write_bytes(fixture.plan_path().read_bytes())
    helper.git(root, "add", str(doc), str(plan))
    helper.git(root, "commit", "-m", "Commit synthetic qualification scope")
    base = helper.git(root, "rev-parse", "HEAD").stdout.strip()
    helper.git(root, "remote", "add", "origin", IDENTITY["origin"] + "/" + IDENTITY["repository"] + ".git")
    helper.git(root, "update-ref", "refs/remotes/origin/main", base)
    fixture.prepare_native_checkout()
    worktree = fixture.repo.resolve()
    helper.git(worktree, "branch", "--set-upstream-to", "origin/main")
    monkeypatch.chdir(worktree)
    monkeypatch.setattr(helper, "root_dir", lambda: worktree)
    fetches = []

    def capture_fetch(_root, remote, identity, branch, account, source):
        assert (remote, identity, branch) == ("origin", IDENTITY, "main")
        fetches.append((account, source))
        return base

    monkeypatch.setattr(helper, "fetch_forgejo_branch", capture_fetch)
    monkeypatch.setattr(helper, "initiative_delivery_preference", lambda _: "auto")

    runtime = helper.ManagedInitiativeRuntime(worktree)
    doc_fields = fixture_document(Fixture())
    doc_fields["binding"].update({"origin": IDENTITY["origin"], "repository": IDENTITY["repository"]})
    doc_fields["root_oid"] = base
    recipe_version = {"schema_version": 2} if credential_source == "osxkeychain" else {
        "schema_version": 3, "credential_source": "systemd",
    }
    runtime.custody._write(runtime.custody.directory / "initiative-runtime.json", lifecycle.canonical({
        **recipe_version, "authority_checkout": str(root), "manifest_path": doc.relative_to(root).as_posix(),
        "writer_agent": "build", "forgejo": doc_fields, "slices": {"local": {
            "branch": helper.branch(worktree), "cycle_id": "local-managed", "risk": "critical", "context": "test",
            "plan_path": plan.relative_to(root).as_posix(), "plan_digest": sha256(plan.read_bytes()).hexdigest(),
        }},
    }))
    recipe = runtime.recipe()
    monkeypatch.setattr(runtime, "_forgejo_enrollment", lambda enrolled: enrolled == recipe.forgejo)
    driver, writer = runtime.running_identities()
    monkeypatch.setattr(runtime, "_witness", lambda: ({"controller_digest": driver, "writer_digest": writer}, None))
    monkeypatch.setattr(runtime, "_transport", lambda _: None)
    binding = runtime.binding(recipe)
    scope = runtime.committed_scope(recipe, ("local",))
    proposal = authority.grant_proposal(scope, binding=binding, operator_id="forgejo-actor-72",
        approved_at="2025-01-01T00:00:00Z", expires_at="2099-01-01T00:00:00Z",
        allowed_operations=("launch", "admit", "merge"), repair_limit=0)
    grant = authority.store_grant(runtime.custody, scope, proposal, expected_approval_digest=lifecycle.digest(proposal))
    launch = runtime.preflight(recipe, grant, "local")
    target = controller.Target(IDENTITY["origin"], IDENTITY["repository"], TARGET)
    approval = controller.Approval(grant, target, driver, writer, (controller.Slice("local"),))
    activation = controller.Activation.from_launch(approval, "local", launch, managed=True)

    def authorize_begin(grant_id, activation_id, session_id, digest):
        assert (grant_id, activation_id, session_id, digest) == (
            grant, activation.activation_id, activation.session_id, launch.launch_digest)
        return activation

    runtime.register(activation, SimpleNamespace(authorize_begin=authorize_begin))
    record_path, record = helper.load(worktree)
    assert record["schema_version"] == 6 and record["delivery_intent"] == "local"
    assert record["initiative_approval"]["method"] == "initiative_auto"
    assert record["delivery"]["forge"]["credential_source"] == credential_source
    assert fetches == [(recipe.forgejo.binding.git_account, credential_source)] * 4
    alternative = "systemd" if credential_source == "osxkeychain" else "osxkeychain"
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "recipe", lambda: replace(recipe, credential_source=alternative))
        with pytest.raises(RuntimeError, match="local registration changed"):
            runtime._forgejo_record(activation, recipe.forgejo)
    assert runtime._forgejo_source(activation, recipe.forgejo) is None
    assert runtime.custody.optional_link("birth", launch.cycle_id) is None
    with runtime.require_release(activation) as registration:
        assert registration.activation_id == activation.activation_id

    existing_git = helper.git

    def local_only(target, *args, **kwargs):
        assert not {"push", "fetch", "ls-remote"} & set(args)
        return existing_git(target, *args, **kwargs)

    monkeypatch.setattr(helper, "git", local_only)
    cycle = SimpleNamespace(core=helper)
    paths = ["tracked.txt", "docs/specs/test/CHANGELOG.md"]
    for filename in paths:
        (worktree / filename).write_text("Completed synthetic source.\n")
    evidence(cycle, "domain", paths=paths)
    helper.command_gate_commit(helper.parser().parse_args([
        "gate-commit", "--message", "Exercise managed Forgejo local completion", "--gates", "domain", "--paths", *paths,
    ]))
    for name, result in (("README", "unchanged"), ("BACKLOG", "unchanged"), ("CHANGELOG", "changed")):
        argv = ["review-artifact", name, "--result", result, "--reason", "Synthetic fixture artifact review."]
        if result == "changed":
            argv += ["--path", paths[1]]
        helper.command_review(helper.parser().parse_args(argv))
    for gate in helper.GATES:
        if gate not in {"domain", "release"}:
            evidence(cycle, gate)
    helper.command_complete_local(helper.parser().parse_args(["complete-local"]))
    capsys.readouterr()
    source = runtime._forgejo_source(activation, recipe.forgejo)
    completed = json.loads(record_path.read_text())
    assert source.head == completed["local_completion"]["head"]
    assert source.tree == completed["local_completion"]["tree"]
    assert source.record_digest == sha256(record_path.read_bytes()).hexdigest()
    assert runtime.observed(activation) == registration

    (worktree / paths[0]).write_text("Unapproved checkout change.\n")
    with pytest.raises(RuntimeError, match="worktree is not clean"):
        runtime._forgejo_source(activation, recipe.forgejo)
