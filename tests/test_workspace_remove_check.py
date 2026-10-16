"""Worktrunk eligibility is read-only and never treats missing evidence as safe."""
import importlib.machinery
import importlib.util
import json
import hashlib
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import test_dbsctrctl as harness
from test_worktrunk_registration import fixture, git, task


@pytest.fixture
def removal(fixture, monkeypatch):
    target = task(fixture)
    loader = importlib.machinery.SourceFileLoader("workspace_removal", str(harness.SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    core = importlib.util.module_from_spec(spec)
    loader.exec_module(core)
    monkeypatch.setattr(core, "workspace_processes", lambda _root: [])
    return core, fixture.repo, target


def test_clean_code_only_checkout_can_be_removed_without_a_cycle(removal):
    core, primary, target = removal
    before = git(primary, "worktree", "list", "--porcelain")
    assert core.workspace_remove_check(target)["eligible"] is True
    assert git(primary, "worktree", "list", "--porcelain") == before
    assert target.is_dir()


@pytest.mark.parametrize("problem", ["primary", "dirty", "ignored", "undelivered", "process"])
def test_preservation_blockers_refuse_without_removing_files(removal, monkeypatch, problem):
    core, primary, target = removal
    if problem == "primary":
        target = primary
    elif problem == "dirty":
        (target / "tracked.txt").write_text("retain dirty work\n")
    elif problem == "ignored":
        (target / ".gitignore").write_text("private-data\n")
        git(target, "add", ".gitignore")
        git(target, "commit", "-m", "ignore data")
        git(primary, "merge", "--ff-only", "task")
        (target / "private-data").write_bytes(b"unique data")
    elif problem == "undelivered":
        git(target, "commit", "--allow-empty", "-m", "unmerged task")
    else:
        monkeypatch.setattr(core, "workspace_processes", lambda _root: [123])
    result = core.workspace_remove_check(target)
    assert result["eligible"] is False
    assert result["reasons"]
    assert target.is_dir()
    if problem == "ignored":
        assert (target / "private-data").read_bytes() == b"unique data"


def test_unavailable_process_inventory_is_not_an_empty_inventory(removal, monkeypatch):
    core, _, target = removal

    def unavailable(_root):
        raise RuntimeError("process inventory unavailable")

    monkeypatch.setattr(core, "workspace_processes", unavailable)
    result = core.workspace_remove_check(target)
    assert result["eligible"] is False
    assert "process_inventory_unavailable" in result["reasons"]


def test_active_cycle_blocks_removal_even_when_git_is_clean(removal, fixture):
    core, _, target = removal
    harness.run(target, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
                "--delivery-intent", "local", "--plan", str(fixture.plan_path()))
    before = fixture.record_path().read_bytes()
    assert "active_cycle" in core.workspace_remove_check(target)["reasons"]
    assert fixture.record_path().read_bytes() == before


def test_new_cycle_records_no_implicit_preservation_consent(removal, fixture):
    _, _, target = removal
    harness.run(target, "start", "--cycle-id", "cycle-1", "--context", "test", "--risk", "routine",
                "--delivery-intent", "local", "--plan", str(fixture.plan_path()))
    record = json.loads(fixture.record_path().read_text())
    assert "preservation_policy" in record
    assert record["preservation_policy"] is None


def test_declared_push_interface_is_explicit_and_legacy_recording_stays_distinct(fixture):
    result = harness.run(fixture.repo, "record-dvc-push", "--help")
    for flag in ("--declaration", "--remote", "--upload", "--head", "--evidence"):
        assert flag in result.stdout


def test_committed_output_declaration_binds_exact_metadata(removal):
    core, _, target = removal
    declaration = {"schema_version": 1, "targets": ["result.dvc"]}
    (target / "outputs.json").write_text(json.dumps(declaration))
    (target / "result.dvc").write_text("outs:\n- md5: " + "a" * 32 + "\n  size: 10\n  hash: md5\n  path: result.txt\n")
    git(target, "add", "outputs.json", "result.dvc")
    git(target, "commit", "-m", "declare output")
    head = git(target, "rev-parse", "HEAD").strip()
    digest, outputs = core.preservation_declaration(target, head, "outputs.json")
    assert len(digest) == 64 and outputs[0]["path"] == "result.txt"
    assert outputs[0]["object_id"] == "a" * 32 and outputs[0]["kind"] == "file"
    (target / "result.dvc").write_text("changed metadata")
    with pytest.raises(RuntimeError, match="metadata_changed"):
        core.preservation_declaration(target, head, "outputs.json")


@pytest.mark.parametrize("declaration", [{"schema_version": True, "targets": ["x.dvc"]},
    {"schema_version": 1, "targets": []}, {"schema_version": 1, "targets": ["x.dvc", "x.dvc"]},
    {"schema_version": 1, "targets": ["../escape.dvc"]},
    {"schema_version": 1, "targets": ["dvc.yaml:stage"]},
    {"schema_version": 1, "targets": ["x.dvc"], "upload": True}])
def test_output_declaration_never_grants_consent_or_guesses_scope(removal, declaration):
    core, _, target = removal
    (target / "outputs.json").write_text(json.dumps(declaration))
    (target / "x.dvc").write_text("outs:\n- md5: " + "a" * 32 + "\n  size: 1\n  hash: md5\n  path: x\n")
    git(target, "add", "outputs.json", "x.dvc")
    git(target, "commit", "-m", "fixture")
    with pytest.raises(RuntimeError):
        core.preservation_declaration(target, git(target, "rev-parse", "HEAD").strip(), "outputs.json")


def test_policy_cannot_retroactively_authorize_an_existing_cycle(removal, monkeypatch):
    core, _, target = removal
    policy = {"schema_version": 1, "policy_digest": "a" * 64, "consent": {"uploads": []}}
    monkeypatch.setattr(core, "preservation_policy_snapshot", lambda root: policy)
    def forbidden(*a, **kw):
        pytest.fail("native upload/query must not run before birth-bound consent")
    monkeypatch.setattr(core, "removal_run", forbidden)
    with pytest.raises(RuntimeError, match="consent_absent_or_changed"):
        core.record_declared_dvc_preservation(target, None, {}, SimpleNamespace(
            declaration="outputs.json", remote="backup", upload=True))


def test_policy_replacement_during_validation_refuses_unvalidated_bytes(removal, monkeypatch):
    core, primary, target = removal
    home = primary.parent / "home"
    config = home / ".config"
    path = config / "dotfiles-ai/workflow-policy.json"
    path.parent.mkdir(parents=True)
    helper = home / ".local/bin/workflow-policy"
    helper.parent.mkdir(parents=True)
    helper.write_text("synthetic validator adapter")
    helper.chmod(0o700)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    def policy(enabled):
        value = {"schema_version": 1, "repositories": [{"repository": str(primary),
            "preservation": {"schema_version": 1, "automatic_remove": enabled, "uploads": []}}]}
        value["policy_digest"] = hashlib.sha256(json.dumps(value, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        return value
    path.write_text(json.dumps(policy(False)))
    path.chmod(0o600)
    def validator(root, argv):
        assert argv == [str(helper), "check"]
        path.write_text(json.dumps(policy(True)))
        return '{"status":"passed"}'
    monkeypatch.setattr(core, "removal_run", validator)
    with pytest.raises(RuntimeError, match="policy"):
        core.preservation_policy_snapshot(target)


@pytest.mark.parametrize("boundary", ["destination", "policy", "command"])
def test_private_filesystem_failures_have_sanitized_preservation_diagnostics(removal, monkeypatch, boundary):
    core, primary, target = removal
    sentinel = "PRIVATE_PATH_SENTINEL"
    private = primary.parent / sentinel
    if boundary == "destination":
        monkeypatch.setattr(core, "removal_run", lambda *a, **kw: str(private))
        operation = lambda: core.preservation_destination(target, "backup")
    elif boundary == "policy":
        path = private / ".config/dotfiles-ai/workflow-policy.json"
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        path.chmod(0o600)
        monkeypatch.setenv("HOME", str(private))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(private / ".config"))
        operation = lambda: core.preservation_policy_snapshot(target)
    else:
        (target / ".dvc").mkdir()
        head = git(target, "rev-parse", "HEAD").strip()
        monkeypatch.setattr(core, "root_dir", lambda: target)
        monkeypatch.setattr(core, "load", lambda root: (None, {"state": "active"}))
        def unavailable(*a, **kw):
            raise FileNotFoundError(2, "synthetic missing endpoint", str(private))
        monkeypatch.setattr(core, "record_declared_dvc_preservation", unavailable)
        operation = lambda: core.command_record_dvc_push(SimpleNamespace(
            head=head, evidence="fixture", declaration="outputs.json", remote="backup", upload=True))
    with pytest.raises(RuntimeError) as error:
        operation()
    assert sentinel not in str(error.value)


def test_directory_closure_is_unavailable_even_when_cloud_status_would_be_empty(removal, monkeypatch):
    core, _, target = removal
    monkeypatch.setattr(core, "removal_run", lambda *a, **kw: pytest.fail("directory query is not proof"))
    value = core.preservation_remote_observation(target, [{"kind": "directory"}], "backup")
    assert value["status"] == "unavailable"
    assert value["reasons"] == ["remote_directory_closure_unverified"]


@pytest.mark.parametrize("cloud,expected", [("{}", "verified"), ('{"result.txt":"missing"}', "unavailable"),
                                           ("[]", "unavailable"), ("broken", "unavailable")])
def test_file_presence_query_is_exact_and_nonempty_or_malformed_status_never_passes(removal, monkeypatch, cloud, expected):
    core, _, target = removal
    calls = []
    def native(root, argv):
        calls.append(argv)
        return cloud
    monkeypatch.setattr(core, "removal_run", native)
    value = core.preservation_remote_observation(target, [{"kind": "file", "target": "file.dvc",
        "algorithm": "md5", "object_id": "a" * 32}], "backup")
    assert value["status"] == expected
    assert calls == [["dvc", "status", "--cloud", "--json", "-r", "backup", "file.dvc"]]


def test_native_dvc_status_distinguishes_absence_from_modified_data(removal):
    core, _, target = removal
    assert core.removal_dvc_paths(target, {"uncommitted": {"deleted": ["dataset/"]}}) == []
    assert core.removal_dvc_paths(target, {"unchanged": ["dataset/"]}) == ["dataset/"]
    for status in ({"uncommitted": {"modified": ["dataset/"]}}, {"committed": {"added": ["data"]}},
                   {"unknown": []}, {"unchanged": ["../escape"]}):
        with pytest.raises(RuntimeError):
            core.removal_dvc_paths(target, status)
    (target / "dataset").mkdir()
    with pytest.raises(RuntimeError):
        core.removal_dvc_paths(target, {"not_in_cache": ["dataset/"]})


@pytest.mark.skipif(shutil.which("lsof") is None, reason="native process inventory is unavailable")
def test_cli_eligibility_does_not_remove_checkout(fixture):
    target = task(fixture)
    result = json.loads(harness.run(target, "workspace-remove-check", "--json").stdout)
    assert result["eligible"] is True
    assert target.is_dir()


@pytest.mark.skipif(shutil.which("lsof") is None, reason="native process inventory is unavailable")
def test_open_file_process_blocks_even_when_its_cwd_is_elsewhere(fixture):
    target = task(fixture)
    code = "import sys,signal; f=open(sys.argv[1]); print('ready',flush=True); signal.pause()"
    with subprocess.Popen([sys.executable, "-c", code, str(target / "tracked.txt")], cwd=fixture.repo,
                          stdout=subprocess.PIPE, text=True) as child:
        try:
            assert child.stdout.readline().strip() == "ready"
            result = json.loads(harness.run(target, "workspace-remove-check", "--json", ok=False).stdout)
            assert "running_processes" in result["reasons"]
            assert target.is_dir()
        finally:
            child.terminate()
            child.wait(timeout=5)


@pytest.mark.parametrize("payload", [b"", b"unclassified inventory\0", b"p123\0xunknown\0"])
def test_empty_or_malformed_native_inventory_cannot_authorize_removal(fixture, tmp_path, payload):
    target = task(fixture)
    program = tmp_path / "lsof"
    program.write_text(f"#!{sys.executable}\nimport os\nos.write(1, {payload!r})\n")
    program.chmod(0o700)
    environment = harness.isolated_env()
    environment["PATH"] = str(tmp_path) + ":" + environment.get("PATH", "/usr/bin:/bin")
    response = harness.run(target, "workspace-remove-check", "--json", ok=False, env=environment)
    assert "process_inventory_unavailable" in json.loads(response.stdout)["reasons"]
    assert target.is_dir()


def test_native_evidence_overflow_stops_before_child_finishes(removal, tmp_path):
    core, _, target = removal
    marker = tmp_path / "should-not-finish"
    code = "import os,sys; from pathlib import Path; os.write(1,b'x'*(2*1024*1024)); Path(sys.argv[1]).touch()"
    with pytest.raises(RuntimeError, match="preservation evidence"):
        core.removal_run(target, [sys.executable, "-c", code, str(marker)])
    assert not marker.exists(), "output must be bounded while reading, not after communicate buffers everything"
