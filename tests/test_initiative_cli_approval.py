"""Exact operator confirmation is independent of native permission enforcement."""
import hashlib
import importlib.machinery
import importlib.util
import io
import json

import pytest
import test_dbsctrctl as harness
from test_worktrunk_registration import fixture, git, task


class Operator(io.StringIO):
    def isatty(self):
        return True


@pytest.fixture
def initiative(fixture, monkeypatch, capsys):
    manifest = fixture.write_initiative()
    git(fixture.repo, "add", str(manifest.relative_to(fixture.repo)))
    git(fixture.repo, "commit", "-m", "initiative")
    remote = fixture.repo.parent / "remote.git"
    git(fixture.repo, "init", "--bare", str(remote))
    git(fixture.repo, "remote", "add", "origin", "https://github.com/example/test.git")
    git(fixture.repo, "remote", "add", "upstream", str(remote))
    git(fixture.repo, "push", "upstream", "HEAD:refs/heads/base")
    target = task(fixture)
    git(target, "branch", "--set-upstream-to", "upstream/base")
    plan = fixture.plan_path()
    checked = json.loads(harness.run(target, "initiative-check", "--manifest",
                                   "docs/initiatives/test/MANIFEST.json", "--json").stdout)
    argv = ["begin", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
            "--delivery-intent", "local", "--base-branch", "protected", "--plan", str(plan),
            "--initiative-manifest", "docs/initiatives/test/MANIFEST.json", "--initiative-slice", "slice-a",
            "--initiative-digest", checked["manifest_digest"], "--expected-repository", "example/test",
            "--expected-plan-digest", hashlib.sha256(plan.read_bytes()).hexdigest()]
    loader = importlib.machinery.SourceFileLoader("initiative_cli_approval", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.chdir(target)
    core.command_begin(core.parser().parse_args([*argv, "--preflight"]))
    prepared = json.loads(capsys.readouterr().out)
    assert not fixture.record_path().exists()
    argv += ["--expected-launch-digest", prepared["launch_digest"]]
    return core, target, fixture.record_path(), argv, prepared, plan


@pytest.mark.parametrize("input_kind", ["noninteractive", "wrong", "eof", "resume_missing"])
def test_unconfirmed_initiative_refuses_without_mutation(initiative, monkeypatch, input_kind):
    core, target, path, argv, prepared, _ = initiative
    before = git(target, "status", "--porcelain")
    line = f"BEGIN cycle-1 {prepared['launch_digest']}\n"
    stream = io.StringIO(line) if input_kind in {"noninteractive", "resume_missing"} else Operator(
        "WRONG\n" if input_kind == "wrong" else "")
    monkeypatch.setattr(core.sys, "stdin", stream)
    if input_kind == "resume_missing":
        argv = [*argv, "--resume-existing"]
    with pytest.raises(RuntimeError, match="confirmation|interactive"):
        core.command_begin(core.parser().parse_args(argv))
    assert not path.exists()
    assert git(target, "status", "--porcelain") == before


def test_confirmed_registration_records_truthful_provenance(initiative, monkeypatch):
    core, _, path, argv, prepared, _ = initiative
    monkeypatch.setattr(core.sys, "stdin", Operator(f"BEGIN cycle-1 {prepared['launch_digest']}\n"))
    core.command_begin(core.parser().parse_args(argv))
    record = json.loads(path.read_text())
    assert record["initiative_approval"]["method"] == "interactive_cli"
    assert record["initiative_approval"]["launch_digest"] == prepared["launch_digest"]
    assert record["execution"]["attribution"]["status"] == "unavailable"
    assert record["runtime"] == {"adapters": {}}


def test_changed_plan_during_confirmation_refuses(initiative, monkeypatch):
    core, _, path, argv, prepared, plan = initiative

    class Changed(Operator):
        def readline(self, *_):
            plan.write_text(plan.read_text() + "\n")
            return f"BEGIN cycle-1 {prepared['launch_digest']}\n"

    monkeypatch.setattr(core.sys, "stdin", Changed())
    with pytest.raises(RuntimeError, match="changed"):
        core.command_begin(core.parser().parse_args(argv))
    assert not path.exists()


@pytest.mark.parametrize("change", ["branch", "head", "target"])
def test_changed_git_state_during_confirmation_refuses(initiative, fixture, monkeypatch, change):
    core, target, path, argv, prepared, _ = initiative

    class Changed(Operator):
        def readline(self, *_):
            if change == "branch":
                git(target, "switch", "-c", "other-task")
                git(target, "branch", "--set-upstream-to", "upstream/base")
            elif change == "head":
                git(target, "commit", "--allow-empty", "-m", "intervening commit")
            else:
                git(fixture.repo, "commit", "--allow-empty", "-m", "target advance")
                git(fixture.repo, "push", "upstream", "HEAD:refs/heads/base")
            return f"BEGIN cycle-1 {prepared['launch_digest']}\n"

    monkeypatch.setattr(core.sys, "stdin", Changed())
    with pytest.raises(RuntimeError, match="changed"):
        core.command_begin(core.parser().parse_args(argv))
    assert not path.exists()


def test_stale_digest_is_rejected_before_prompt(initiative, monkeypatch):
    core, _, path, argv, _, _ = initiative

    class Unreadable(Operator):
        def readline(self, *_):
            raise AssertionError("stale plan must not request confirmation")

    monkeypatch.setattr(core.sys, "stdin", Unreadable())
    with pytest.raises(RuntimeError, match="changed"):
        core.command_begin(core.parser().parse_args([*argv[:-1], "0" * 64]))
    assert not path.exists()


def test_concurrent_registration_is_blocked_while_operator_confirms(initiative, monkeypatch):
    core, target, path, argv, prepared, plan = initiative

    class Contended(Operator):
        def readline(self, *_):
            result = harness.run(target, "start", "--cycle-id", "other-cycle", "--context", "test",
                                 "--risk", "routine", "--delivery-intent", "local", "--plan", str(plan), ok=False)
            assert "busy" in result.stderr
            return f"BEGIN cycle-1 {prepared['launch_digest']}\n"

    monkeypatch.setattr(core.sys, "stdin", Contended())
    core.command_begin(core.parser().parse_args(argv))
    assert path.exists()
    assert not path.with_name("other-cycle.json").exists()


def test_exact_existing_cycle_resumes_without_rewriting_approval(initiative, monkeypatch, capsys):
    core, _, path, argv, prepared, _ = initiative
    monkeypatch.setattr(core.sys, "stdin", Operator(f"BEGIN cycle-1 {prepared['launch_digest']}\n"))
    core.command_begin(core.parser().parse_args(argv))
    capsys.readouterr()
    before = path.read_bytes()
    monkeypatch.setattr(core.sys, "stdin", io.StringIO(""))
    core.command_begin(core.parser().parse_args([*argv, "--resume-existing"]))
    assert json.loads(capsys.readouterr().out)["resumed"] is True
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("schema_version", True), ("method", "caller_assertion"),
                                         ("launch_digest", "bad"), ("confirmed_at", "2026-10-02")])
def test_malformed_approval_provenance_refuses(initiative, monkeypatch, field, value):
    core, target, path, argv, prepared, _ = initiative
    monkeypatch.setattr(core.sys, "stdin", Operator(f"BEGIN cycle-1 {prepared['launch_digest']}\n"))
    core.command_begin(core.parser().parse_args(argv))
    record = json.loads(path.read_text())
    record["initiative_approval"][field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="Initiative confirmation"):
        core.read_cycle_record(target, path)
