"""The CLI composes only owner-managed Initiative operations."""
from contextlib import nullcontext
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from test_initiative_local_launch import launch


def test_missing_managed_recipe_refuses_before_provider_credentials(launch, monkeypatch):
    helper, _, _ = launch

    def forbidden(*_args):
        pytest.fail("Unenrolled Start reached provider authentication")

    monkeypatch.setattr(helper, "github_environment", forbidden)
    args = helper.parser().parse_args(["initiative-auto", "start", "--slice", "slice-a",
                                      "--expires-at", "2026-12-23T01:00:00Z", "--preview"])
    with pytest.raises(RuntimeError, match="managed Initiative runtime is unavailable"):
        helper.command_initiative_auto(args)


def test_start_prints_exact_confirmation_before_private_grant_write(launch, monkeypatch, capsys):
    helper, _, _ = launch
    grant_id = "a" * 64
    approved = "b" * 64
    preview = SimpleNamespace(approval_digest=approved, grant_digest=grant_id,
                              confirmation=f"START test {approved}",
                              review={"initiative_id": "test", "approval_digest": approved})
    applied = []

    class Service:
        def preview(self, selected, *, operator_id, expires_at):
            assert selected == ("slice-a",)
            assert (operator_id, expires_at) == ("github-actor-1", "2026-12-23T01:00:00Z")
            return preview

        def confirm(self, subject, line):
            applied.append((subject, line))
            return grant_id

    monkeypatch.setattr(helper, "initiative_managed_service",
                        lambda root: (Service(), lambda: "github-actor-1"), raising=False)
    args = ["initiative-auto", "start", "--slice", "slice-a", "--expires-at", "2026-12-23T01:00:00Z"]
    helper.command_initiative_auto(helper.parser().parse_args([*args, "--preview"]))
    assert approved in capsys.readouterr().out
    assert not applied

    class Interactive:
        def isatty(self):
            return True

        def readline(self, _size):
            assert approved in capsys.readouterr().err
            return preview.confirmation + "\n"

    monkeypatch.setattr(helper.sys, "stdin", Interactive())
    helper.command_initiative_auto(helper.parser().parse_args(args))
    assert applied == [(preview, preview.confirmation)]
    assert grant_id in capsys.readouterr().out


def test_resume_uses_only_persisted_grant_and_rejects_caller_session(launch, monkeypatch, capsys):
    helper, _, _ = launch
    target = "a" * 64
    results = []

    class Service:
        def resume(self, grant_id):
            results.append(grant_id)
            return SimpleNamespace(state="held", slice_id="slice-a", activation_id="b" * 64, reason=None)

    monkeypatch.setattr(helper, "initiative_managed_service",
                        lambda root: (Service(), lambda: "unused"), raising=False)
    parser = helper.parser()
    helper.command_initiative_auto(parser.parse_args(["initiative-auto", "resume", target]))
    assert results == [target]
    assert "held" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        parser.parse_args(["initiative-auto", "resume", target, "--session", "ses_untrusted"])


def test_load_private_installed_writer_witness(launch):
    helper, fixture, _ = launch
    managed = helper.ManagedInitiativeRuntime(fixture.native_task)
    driver, writer = managed.running_identities()
    value = {"schema_version": 1, "origin": "http://127.0.0.1:8400", "pid": 4321, "version": "2.3.2",
             "writer_digest": writer, "controller_digest": driver, "evidence_digest": "c" * 64}
    managed.custody._write(managed.custody.directory / "initiative-native-qualification.json",
                           json.dumps(value).encode())
    _, actual = managed._witness()
    assert (actual.origin, actual.pid, actual.version, actual.writer_digest) == (
        value["origin"], value["pid"], value["version"], value["writer_digest"])


@pytest.mark.parametrize("mode", [None, "draft_pr", "admin"])
def test_managed_publication_cannot_fall_back_to_an_unbound_mode(launch, mode):
    helper, fixture, _ = launch
    auto = {"initiative_approval": {"method": "initiative_auto"}}
    with pytest.raises(RuntimeError, match="ordinary birth enrollment"):
        with helper.initiative_publication_fence(fixture.native_task, auto, mode):
            pytest.fail("Unenrolled Auto reached the publication effect")
    with helper.initiative_publication_fence(fixture.native_task, {}, mode):
        pass


def test_idle_writer_can_be_composed_without_touching_opencode(launch, monkeypatch):
    helper, fixture, _ = launch
    managed = helper.ManagedInitiativeRuntime(fixture.native_task)

    def forbidden():
        pytest.fail("Provider-only reconciliation touched the writer")

    monkeypatch.setattr(managed, "_witness", forbidden)
    assert callable(managed.writer(None).observe_release)


def test_refresh_prepared_dependent_to_verified_new_base(launch):
    helper, fixture, args = launch
    target = fixture.native_task
    original = helper.git(target, "rev-parse", "HEAD").stdout.strip()
    tree = helper.git(target, "rev-parse", "HEAD^{tree}").stdout.strip()
    newer = helper.git(fixture.repo, "commit-tree", tree, "-p", original, "-m", "delivered prerequisite").stdout.strip()
    helper.git(fixture.repo, "push", "origin", newer + ":refs/heads/main")
    scope = SimpleNamespace(verify_scope=lambda *_args: None)
    managed = helper.ManagedInitiativeRuntime(target)
    managed._refresh_task_base(target, args, scope)
    assert helper.git(target, "rev-parse", "HEAD").stdout.strip() == newer
    assert helper.git(target, "status", "--porcelain").stdout == ""
    unique = helper.git(target, "commit", "--allow-empty", "-m", "independent task work")
    assert unique.returncode == 0
    retained = helper.git(target, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(RuntimeError, match="unique local history"):
        managed._refresh_task_base(target, args, scope)
    assert helper.git(target, "rev-parse", "HEAD").stdout.strip() == retained


@pytest.mark.parametrize("changed", [None, "root_oid", "policy_digest", "default_branch", "repository"])
def test_managed_enrollment_reads_native_control_before_launch(launch, monkeypatch, changed):
    helper, fixture, _ = launch
    managed = helper.ManagedInitiativeRuntime(fixture.native_task)
    from integration_coordinator import core, runtime
    from test_initiative_protected_delivery import local_config

    config = local_config()
    enrollment = config.enrollment
    assert enrollment is not None
    values = {"root_oid": "9" * 40, "policy_digest": "9" * 64,
              "default_branch": "unapproved", "repository": "elsewhere/project"}
    ledger = runtime.Target(enrollment.repository, enrollment.default_branch, enrollment.root_oid,
                            enrollment.policy_digest)
    if changed is not None:
        ledger = replace(ledger, **{changed: values[changed]})
    observations = []

    def read_control(handles):
        observations.append(handles)
        return "f" * 40, {"integration/v2/target.json": runtime.encode(ledger)}

    native = SimpleNamespace(enrollment=enrollment, plan=config.check_plan, read_control=read_control,
        observe_policy=lambda: SimpleNamespace(digest=enrollment.native_guard_digest))
    actor = config.requester_ids[0]
    transport = SimpleNamespace(request=lambda method, path: {"id": actor, "type": "User"})
    target_ref = "refs/heads/" + enrollment.default_branch
    client = SimpleNamespace(configuration=lambda: (config, native), transport=transport, target_ref=target_ref)
    monkeypatch.setattr(helper, "require_repository_home", lambda *_args: None)
    monkeypatch.setattr(helper, "integration_native_client", lambda *_args: nullcontext(client))
    selected = {"coordinator": {"remote_repository": enrollment.repository, "target_ref": target_ref}}
    recipe = SimpleNamespace(github_account="fixture")
    if changed is None:
        identity, root, requester, policy = managed._native_enrollment(recipe, selected)
        assert (identity["repository"], root, requester, policy) == (
            enrollment.repository, enrollment.root_oid, actor, enrollment.policy_digest)
    else:
        with pytest.raises(core.Unavailable, match="native_ledger_authority_changed"):
            managed._native_enrollment(recipe, selected)
    assert observations == [()]
