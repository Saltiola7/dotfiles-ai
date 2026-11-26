"""Recover a three-worker handoff using actual private grants and SQLite journals."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from test_integration_initiative_authority import APPROVED_AT, NOW, EXPIRES, SELECTED, binding, manifest, oid, selected_snapshot, l
from test_initiative_managed_registration import HeldWriter, Registration, ic, Provider
from test_initiative_local_launch import launch
from integration_coordinator import draft_worker_batch as batch, initiative_opencode as native


def selection():
    return {key: {"write_set": ["src/" + key], "agent": "build", "model": "fixture/model", "variant": "medium",
                  "shared_resources": [key]} for key in SELECTED}


@pytest.mark.parametrize("path", ("src", "src/first/file", "SRC/FIRST", ".git/config", "a/../other"))
def test_rejects_ambiguous_authority(path):
    spec = selection()
    spec["second"]["write_set"] = [path]
    with pytest.raises(ValueError):
        batch.claims(spec)


class Fixture:
    def __init__(self, directory):
        self.custody = l.Custody(directory)
        self.raw = manifest()
        for row in self.raw["slices"]:
            row["depends_on"] = []
        self.recipe_value = SimpleNamespace(authority_checkout=directory, writer_agent="build", forgejo=None)
        self.provider = Provider()
        self.workers = {}
        self.registrars = {}

    def recipe(self):
        return self.recipe_value

    def operator_identity(self):
        return "fixture"

    def binding(self, _recipe):
        return binding()

    def committed_scope(self, _recipe, keys):
        return selected_snapshot(self.raw, selected=keys)

    def preview_slice(self, recipe, key):
        return recipe.authority_checkout / key, {"source_commit": oid("approved"), "cycle_id": key,
                                                "checkout": {"branch": key}}

    def launch(self, grant, graph, key):
        worker = graph["workers"][key]
        return ic.Launch(l.digest(worker), oid("base"), worker["checkout"], key, "build")

    def worker_writer(self, item):
        key = item["plan"]["cycle_id"]
        if key not in self.workers:
            store = batch.journal(self.custody, self.grant, key)
            self.workers[key] = HeldWriter(store)
            self.registrars[key] = Registration(self.workers[key])
        return self.workers[key]

    def register(self, activation, controller):
        self.registrars[activation.slice_id].register(activation, controller)

    def observed(self, activation):
        return self.registrars[activation.slice_id].observed(activation)

    @contextmanager
    def require_release(self, activation):
        with self.registrars[activation.slice_id].require_release(activation) as receipt:
            yield receipt

    def prior_delivery(self, *unused):
        return False


def test_one_receipt_recovers_three_distinct_sessions_then_refuses_revocation(tmp_path):
    fixture, spec = Fixture(tmp_path), selection()
    review = batch.prepare(fixture, spec, APPROVED_AT, EXPIRES)
    assert not fixture.custody.directory.exists()
    assert review["proposal"]["allowed_operations"] == ["launch"]
    changed = selection()
    changed["second"]["model"] = "fixture/other"
    with pytest.raises(ValueError, match="approval changed"):
        batch.accept(fixture, changed, APPROVED_AT, EXPIRES, review["approval_digest"], lambda: NOW)
    grant = fixture.grant = batch.accept(fixture, spec, APPROVED_AT, EXPIRES, review["approval_digest"], lambda: NOW)
    first = batch.build(fixture, grant, lambda: NOW)
    assert {item["state"] for item in first.values()} == {"release_accepted"}
    assert len({item["session_id"] for item in first.values()}) == 3
    for writer in fixture.workers.values():
        writer.release_receipt = replace(writer.release_receipt, delivered=True)
    for _ in range(2):
        result = batch.build(fixture, grant, lambda: NOW)
        assert {item["state"] for item in result.values()} == {"dispatched"}
    assert all(len(writer.created) == len(writer.release_calls) == 1 for writer in fixture.workers.values())
    batch.authority.revoke_grant(fixture.custody, grant, reason_digest="f" * 64, revoked_at=NOW)
    with pytest.raises(ValueError, match="revoked"):
        batch.build(fixture, grant, lambda: NOW)


def test_model_readback_mismatch_stops_before_dispatch():
    class Transport:
        def request(self, method, path, payload):
            return native.Response(200, {"data": {"model": {"providerID": "fixture", "id": "wrong"}}})
    with pytest.raises(batch.core.Ambiguous, match="native_model_unproved"):
        batch.RoutedTransport(Transport(), "build", "fixture/expected", "medium").request("GET", "/api/session/ses_abc")


@pytest.mark.parametrize("wrong", ("agent", "variant", "absent"))
def test_create_and_resume_require_exact_agent_and_model_ref(wrong):
    class Transport:
        def request(self, method, path, payload):
            if method == "POST":
                assert payload["agent"] == "build-claude"
                assert payload["model"] == {"providerID": "vertex", "id": "opus", "variant": "medium"}
                self.session = payload
            return native.Response(200, {"data": self.session})
    transport = Transport()
    writer = batch.RoutedTransport(transport, "build-claude", "vertex/opus", "medium")
    writer.request("POST", "/api/session", {"agent": "build-claude"})
    writer.request("GET", "/api/session/ses_exact")
    transport.session = {**transport.session, "model": dict(transport.session["model"])}
    if wrong == "agent":
        transport.session["agent"] = "plan"
    elif wrong == "variant":
        transport.session["model"]["variant"] = "low"
    else:
        del transport.session["model"]["variant"]
    with pytest.raises(batch.core.Ambiguous):
        writer.request("GET", "/api/session/ses_exact")


def test_overlap_retained_until_terminal_delivery(tmp_path):
    fixture, spec = Fixture(tmp_path), selection()
    first = {"first": spec["first"]}
    second = {"second": spec["first"]}
    def accept(s):
        digest = batch.prepare(fixture, s, APPROVED_AT, EXPIRES)["approval_digest"]
        return batch.accept(fixture, s, APPROVED_AT, EXPIRES, digest, lambda: NOW)
    fixture.grant = accept(first)
    batch.build(fixture, fixture.grant, lambda: NOW)
    with pytest.raises(ValueError, match="retained worker claims"):
        accept(second)
    writer = fixture.workers["first"]
    writer.release_receipt = replace(writer.release_receipt, delivered=True)
    batch.build(fixture, fixture.grant, lambda: NOW)
    fixture.terminal_delivery = lambda act, worker: False
    with pytest.raises(ValueError, match="retained worker claims"):
        accept(second)
    fixture.terminal_delivery = lambda act, worker: act == writer.created[0] and worker["plan"]["cycle_id"] == "first"
    assert accept(second) != fixture.grant


def test_cli_chat_confirmation_binds_exact_preview_without_reading_stdin(launch, tmp_path, monkeypatch, capsys):
    helper, _, _ = launch
    fixture = Fixture(tmp_path)
    monkeypatch.setattr(helper, "DraftWorkerRuntime", lambda root: fixture)
    monkeypatch.setattr(helper, "now", lambda: NOW)
    monkeypatch.setattr(helper.sys, "stdin", None)
    spec = tmp_path / "claims.json"
    spec.write_text(json.dumps(selection()))
    parser = helper.parser()
    opts = ["--claims", str(spec), "--approved-at", APPROVED_AT, "--expires-at", EXPIRES]
    helper.command_draft_worker_batch(parser.parse_args(["draft-worker-batch", "preview", *opts]))
    digest = json.loads(capsys.readouterr().out)["approval_digest"]
    accept = parser.parse_args(["draft-worker-batch", "accept", *opts, "--approval", "agent-confirmed",
                                "--approval-digest", digest])
    helper.command_draft_worker_batch(accept)
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["approval_method"] == "agent-confirmed"
    assert len(receipt["grant_digest"]) == 64
    changed = selection()
    changed["second"]["model"] = "fixture/another"
    spec.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="approval changed"):
        helper.command_draft_worker_batch(accept)


def test_lost_registration_response_stops_batch_and_only_observes_claim_on_resume(tmp_path):
    fixture, spec = Fixture(tmp_path), selection()
    fixture.raw["slices"][2]["depends_on"] = ["first"]
    review = batch.prepare(fixture, spec, APPROVED_AT, EXPIRES)
    grant = fixture.grant = batch.accept(fixture, spec, APPROVED_AT, EXPIRES, review["approval_digest"], lambda: NOW)
    fixture.worker_writer(review["graph"]["workers"]["first"])
    fixture.registrars["first"].lost = True
    result = batch.build(fixture, grant, lambda: NOW)
    assert result["first"]["state"] == "uncertain"
    assert not any(w.release_calls for w in fixture.workers.values())
    result = batch.build(fixture, grant, lambda: NOW)
    assert result["second"]["state"] == "waiting"
    assert result["first"]["state"] == result["independent"]["state"] == "release_accepted"
    assert len(fixture.registrars["first"].calls) == 1


def test_runtime_registers_reviewed_projection_in_real_git_checkout(launch, monkeypatch):
    helper, fixture, args = launch
    runtime = helper.DraftWorkerRuntime(fixture.native_task)
    recipe = {"schema_version": 1, "authority_checkout": str(fixture.repo), "manifest_path": args.initiative_manifest,
              "github_account": args.github_account, "writer_agent": "build", "slices": {}}
    plan = Path(args.initiative_manifest).parent / "cycle.plan.json"
    (fixture.repo / plan).write_bytes(Path(args.plan).read_bytes())
    sibling = plan.parent / "unrelated.md"
    (fixture.repo / sibling).write_text("outside this slice\n")
    helper.git(fixture.repo, "add", str(plan), str(sibling))
    helper.git(fixture.repo, "commit", "-m", "fixture plan and sibling evidence")
    original = helper.git(fixture.repo, "rev-parse", "HEAD").stdout
    key = args.initiative_slice
    recipe["slices"][key] = {"branch": "native-task", "cycle_id": args.cycle_id, "context": args.context,
                             "risk": args.risk, "plan_path": str(plan), "plan_digest": args.expected_plan_digest}
    runtime.custody._write(runtime.custody.directory / "initiative-runtime.json", l.canonical(recipe))
    live = {**binding(), "repository": {"provider": "github", "origin": "https://github.com", "repository": "example/test"}}
    monkeypatch.setattr(runtime, "live_binding", lambda _: live)
    monkeypatch.setattr(runtime, "operator_identity", lambda: "fixture")
    monkeypatch.setattr(runtime, "_selected", lambda: {"coordinator": {"target_ref": live["target_ref"],
                                                                       "remote_repository": "example/test"}})
    monkeypatch.setattr(helper, "github_remote_head", lambda root, url, ref, env:
        [helper.git(root, "rev-parse", "origin/main").stdout.strip(), ref] if ref == "refs/heads/main" else [])
    monkeypatch.setattr(helper, "now", lambda: NOW)
    monkeypatch.setattr(helper, "integration_birth_enrollment", lambda *a, **kw: None)
    spec = {key: {"write_set": ["tests/owned"], "agent": "build", "variant": "medium",
                  "model": "fixture/model", "shared_resources": []}}
    review = batch.prepare(runtime, spec, APPROVED_AT, EXPIRES)
    grant = batch.accept(runtime, spec, APPROVED_AT, EXPIRES, review["approval_digest"], lambda: NOW)
    store = batch.journal(runtime.custody, grant, key)
    writer = HeldWriter(store)
    writer.release_locked = True
    monkeypatch.setattr(runtime, "worker_writer", lambda _: writer)
    report = batch.build(runtime, grant, lambda: NOW)
    assert report[key]["state"] == "release_accepted", report
    assert not (fixture.native_task / sibling).exists()
    assert (fixture.native_task / plan).read_bytes() == (fixture.repo / plan).read_bytes()
    assert helper.git(fixture.repo, "rev-parse", "HEAD").stdout == original
    assert helper.branch(fixture.repo) == "discovery/local"
    assert runtime.observed(store.execution(grant, key).activation).cycle_id == args.cycle_id


def test_disposable_install_exposes_batch_and_both_skill_entries(tmp_path):
    import subprocess
    from test_opencode_control_plane import DATA, ROOT

    cli = tmp_path / '.local/bin/dbsctrctl'
    modules = [tmp_path / '.config/dotfiles-ai/integration_coordinator' / name for name in
               ('draft_worker_batch.py', 'draft_slice_projection.py')]
    skills = [tmp_path / '.agents/skills' / name / 'SKILL.md' for name in ('discovery', 'dbsctr')]
    subprocess.run(['chezmoi', '-S', ROOT, '-D', tmp_path, '--config', '/dev/null', '--config-format', 'toml',
                    '--override-data', json.dumps(DATA), '--cache', tmp_path / 'cache', '--persistent-state',
                    tmp_path / 'state', 'apply', '--parent-dirs', '--exclude', 'scripts', cli, *modules, *skills],
                   check=True, timeout=30)
    help_text = subprocess.check_output([cli, 'draft-worker-batch', 'accept', '--help'], text=True)
    assert 'agent-confirmed' in help_text and '--approval-digest' in help_text
    assert all(p.is_file() for p in modules) and all('draft-worker-batch' in p.read_text() for p in skills)
