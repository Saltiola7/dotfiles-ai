"""The managed Auto route reuses exact preflight and existing cycle custody."""
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest

from test_initiative_local_launch import launch


def test_waiting_approval_cannot_change_manual_receipt(launch):
    helper, fixture, _ = launch
    manifest = fixture.repo / "docs/initiatives/test/MANIFEST.json"
    original = json.loads(manifest.read_text())
    waiting = deepcopy(original["slices"][0])
    waiting.update(id="waiting-slice", depends_on=["slice-a"])
    original["slices"].append(waiting)
    group = next(group for group in original["release_groups"] if group["id"] == waiting["release_group"])
    group["members"].append("waiting-slice")
    manifest.write_text(json.dumps(original))

    with pytest.raises(RuntimeError, match="dependency is not delivered"):
        helper.read_initiative_manifest(manifest)
    _, _, _, slices, _, _ = helper.read_initiative_manifest(manifest, auto_waiting=True)
    assert slices["waiting-slice"]["depends_on"] == ["slice-a"]
    with pytest.raises(RuntimeError, match="dependency is not delivered"):
        helper.initiative_receipt(manifest, "waiting-slice")


def test_auto_preflight_is_bound_and_does_not_consume_confirmation(launch, capsys):
    helper, fixture, _ = launch
    seen = []

    class Scope:
        grant_digest = "a" * 64

        def verify_scope(self, source, authority, manifest, receipt, base_branch):
            seen.append((source, authority, manifest, receipt["slice_id"], base_branch))

    argv = [*fixture.launch_argv, "--preflight"]
    helper.command_begin(helper.parser().parse_args(argv), auto_launch=Scope())
    auto = json.loads(capsys.readouterr().out)
    helper.command_begin(helper.parser().parse_args(argv))
    draft = json.loads(capsys.readouterr().out)
    assert auto["plan"]["initiative_grant_digest"] == Scope.grant_digest
    assert auto["launch_digest"] != draft["launch_digest"]
    assert seen == [(fixture.native_task.resolve(), fixture.repo.resolve(),
                     "docs/initiatives/test/MANIFEST.json", "slice-a", "main")]
    assert not (helper.cycle_dir(fixture.native_task) / "cycles/local-1.json").exists()


def test_auto_scope_failure_precedes_provider_authentication(launch, monkeypatch):
    helper, fixture, _ = launch

    class RevokedScope:
        grant_digest = "b" * 64

        def verify_scope(self, *_args):
            raise ValueError("initiative_grant_revoked")

    def unexpected_fetch(*_args):
        pytest.fail("A revoked grant reached provider authentication")

    monkeypatch.setattr(helper, "github_environment", unexpected_fetch)
    with pytest.raises(ValueError, match="initiative_grant_revoked"):
        helper.command_begin(helper.parser().parse_args([*fixture.launch_argv, "--preflight"]),
                             auto_launch=RevokedScope())

    argv = list(fixture.launch_argv)
    argv[argv.index("--delivery-intent") + 1] = "local"
    with pytest.raises(RuntimeError, match="approved source delivery intent"):
        helper.command_begin(helper.parser().parse_args([*argv, "--preflight"]),
                             auto_launch=RevokedScope())


@pytest.mark.parametrize("delivery_mode", ["draft_pr", "ordinary"])
def test_managed_registration_records_exact_grant_and_session(launch, monkeypatch, capsys, delivery_mode):
    helper, fixture, _ = launch
    lifecycle = helper.integration_lifecycle_owner()
    from integration_coordinator import initiative_authority as authority
    from integration_coordinator import initiative_controller as controller

    checkout = fixture.native_task.resolve()
    manifest = "docs/initiatives/test/MANIFEST.json"
    snapshot = helper.initiative_committed_snapshot(fixture.repo, manifest, ("slice-a",))
    root = helper.git(checkout, "rev-list", "--max-parents=0", "HEAD").stdout.strip()
    operations = ("launch",)
    if delivery_mode == "ordinary":
        tree = helper.git(checkout, "rev-parse", "HEAD^{tree}").stdout.strip()
        root = helper.git(checkout, "commit-tree", tree, "-m", "Orphan control root").stdout.strip()
        assert helper.git(checkout, "merge-base", "--is-ancestor", root, "HEAD", check=False).returncode == 1
        operations = ("launch", "admit", "merge")
    repository = {"provider": "github", "origin": "https://github.com", "repository": "example/test"}
    binding = {"repository": repository, "root_oid": root, "target_ref": "refs/heads/main",
               "policy_digest": "a" * 64, "enrollment_digest": "b" * 64, "controller_digest": "c" * 64,
               "writer_digest": "d" * 64, "qualification_digest": "e" * 64}
    clock = datetime.now(timezone.utc).replace(microsecond=0)
    proposal = authority.grant_proposal(snapshot, binding=binding, operator_id="owner",
        approved_at=(clock - timedelta(minutes=1)).isoformat(),
        expires_at=(clock + timedelta(hours=1)).isoformat(), allowed_operations=operations, repair_limit=0)
    custody = lifecycle.Custody(helper.common_git_dir(checkout).resolve())
    identity = authority.store_grant(custody, snapshot, proposal, expected_approval_digest=lifecycle.digest(proposal))
    policy = {"policy_digest": binding["policy_digest"], "enrollment_digest": binding["enrollment_digest"],
              "delivery": {"role": "operator", "mode": delivery_mode},
              "coordinator": {"target_ref": binding["target_ref"], "remote_repository": repository["repository"]}}
    monkeypatch.setattr(helper, "integration_policy_snapshot", lambda _: policy)
    monkeypatch.setattr(helper, "initiative_delivery_preference", lambda _: "auto")
    monkeypatch.setattr(helper, "integration_birth_enrollment", lambda *_args, **_kwargs: None)
    build = helper.ManagedInitiativeLaunch(identity, lambda: binding, delivery_mode=delivery_mode)
    policy["coordinator"]["target_ref"] = "refs/heads/unapproved"
    with pytest.raises(RuntimeError, match="enrollment is unavailable or changed"):
        helper.command_begin(helper.parser().parse_args([*fixture.launch_argv, "--preflight"]), auto_launch=build)
    policy["coordinator"]["target_ref"] = binding["target_ref"]
    if delivery_mode == "ordinary":
        draft = helper.ManagedInitiativeLaunch(identity, lambda: binding)
        with pytest.raises(RuntimeError, match="repository binding changed"):
            helper.command_begin(helper.parser().parse_args([*fixture.launch_argv, "--preflight"]), auto_launch=draft)
    helper.command_begin(helper.parser().parse_args([*fixture.launch_argv, "--preflight"]), auto_launch=build)
    preflight = json.loads(capsys.readouterr().out)
    assert preflight["plan"]["integration_mode"] == delivery_mode
    target = controller.Target("https://github.com", "example/test", "refs/heads/main")
    approval = controller.Approval(identity, target, binding["controller_digest"], binding["writer_digest"],
                                   (controller.Slice("slice-a"),))
    selected = controller.Launch(preflight["launch_digest"], preflight["plan"]["base_head"],
                                 str(checkout), "local-1", "build")
    activation = controller.Activation.from_launch(approval, "slice-a", selected)

    class Controller:
        def authorize_begin(self, grant_id, activation_id, session_id, launch_digest):
            assert (grant_id, activation_id, session_id, launch_digest) == (
                identity, activation.activation_id, activation.session_id, selected.launch_digest)
            return activation

    argv = [*fixture.launch_argv, "--expected-launch-digest", preflight["launch_digest"]]
    record_path = helper.cycle_dir(checkout) / "cycles/local-1.json"
    with pytest.raises(RuntimeError, match="proven native writer dispatch"):
        helper.command_begin(helper.parser().parse_args(argv), auto_launch=build)
    assert not record_path.exists()
    build = helper.ManagedInitiativeLaunch(identity, lambda: binding, Controller(),
        activation_id=activation.activation_id, session_id=activation.session_id, delivery_mode=delivery_mode)
    fetches = []
    fetch = helper.fetch_github_branch

    def observe_fetch(*args):
        fetches.append(args[3])
        return fetch(*args)

    monkeypatch.setattr(helper, "fetch_github_branch", observe_fetch)
    helper.command_begin(helper.parser().parse_args(argv), auto_launch=build)
    assert fetches == ["main", "main"]
    record = helper.read_cycle_record(checkout, record_path)
    assert record["initiative_approval"]["method"] == "initiative_auto"
    proof = custody.read("initiative_begin", record["initiative_approval"]["authorization_digest"])
    assert (proof["grant_digest"], proof["activation_digest"], proof["launch_digest"]) == (
        identity, activation.activation_id, selected.launch_digest)
    assert proof["session_digest"] == helper.continuation_digest(activation.session_id)


def test_github_evidence_requires_live_target_inclusion_not_just_a_delivered_ticket(launch, monkeypatch):
    helper, fixture, _ = launch
    helper.integration_lifecycle_owner()
    from integration_coordinator import initiative_controller as controller, runtime

    target = controller.Target("https://github.com", "example/test", "refs/heads/main")
    activation = SimpleNamespace(target=target, activation_id="a" * 64)
    obligation = runtime.Obligation("b" * 32, "c" * 32, "d" * 64)
    source = runtime.SourceSeries(target.repository, 3, "1" * 40, "2" * 40,
        (runtime.SourceEntry("2" * 40, "phase", ("contract",)),), "3" * 64)
    original = runtime.Ticket(obligation.current_ticket, obligation.handle, source, "4" * 64)
    packet = {"ticket_handle": obligation.current_ticket,
              "request": {"obligation": json.loads(runtime.encode(obligation)),
                          "ticket": json.loads(runtime.encode(original))}}
    enrollment_root = "e" * 40
    provider = helper.GitHubInitiativeEvidence()
    monkeypatch.setattr(provider, "_subject", lambda _: (fixture.native_task, {}, packet, {}, enrollment_root))

    class Client:
        state = runtime.State.QUEUED
        observed_root = enrollment_root
        observed_source = source
        verified = False

        def configuration(self):
            return None, SimpleNamespace(enrollment=SimpleNamespace(root_oid=self.observed_root))

        def status(self, ticket, obligation_handle):
            assert (ticket, obligation_handle) == (obligation.current_ticket, obligation.handle)
            value = SimpleNamespace(handle=ticket, state=self.state, admission_digest="f" * 64,
                source=self.observed_source, requester_digest=original.requester_digest,
                obligation_handle=obligation.handle, delivery_mode=original.delivery_mode)
            return SimpleNamespace(ticket=value, obligation=obligation)

        def verify_delivered(self, ticket, obligation_handle):
            if not self.verified:
                raise RuntimeError("current protected branch could not be verified")
            status = self.status(ticket, obligation_handle)
            return SimpleNamespace(ticket=status.ticket, obligation=status.obligation,
                                   merge_oid="f" * 40, verification_digest="0" * 64)

    native = Client()
    monkeypatch.setattr(helper, "integration_native_client", lambda *_args: nullcontext(native))
    admission = provider.observe_admission(activation)
    assert provider.observe_delivery(activation, admission) is None
    native.state = runtime.State.DELIVERED
    with pytest.raises(RuntimeError, match="initiative_native_outcome_unverified"):
        provider.observe_delivery(activation, admission)
    native.verified = True
    assert provider.observe_delivery(activation, admission).merge_oid == "f" * 40
    native.observed_source = replace(source, authority_digest="5" * 64)
    with pytest.raises(RuntimeError, match="initiative_native_outcome_unverified"):
        provider.observe_admission(activation)
    native.observed_source = source
    native.observed_root = "0" * 40
    with pytest.raises(RuntimeError, match="initiative_native_outcome_unverified"):
        provider.observe_admission(activation)
