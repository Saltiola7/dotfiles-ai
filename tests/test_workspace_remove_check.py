"""Worktrunk eligibility is read-only and never treats missing evidence as safe."""
import importlib.machinery
import importlib.util
import json
import hashlib
import shutil
import subprocess
import sys
import os
import fcntl
import uuid
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
    observed = subprocess.run([sys.executable, str(harness.SCRIPT), "workspace-remove-check", "--json"],
        cwd=target, env=harness.isolated_env(), text=True, capture_output=True, timeout=90)
    result = json.loads(observed.stdout)
    if observed.returncode == 1 and result.get("reasons") == ["process_inventory_unavailable"]:
        # Binary presence is not process-visibility qualification. The guard still
        # refuses removal; unavailable live capability is not a positive smoke.
        assert result["eligible"] is False and target.is_dir()
        pytest.skip("native process visibility unavailable; checker correctly retained target")
    assert observed.returncode == 0, result
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


def removal_reservation(core, target):
    admin = core.git_dir(target).resolve()
    common = core.common_git_dir(target).resolve()
    directory = common / "agent-worktree-locks"
    directory.mkdir(exist_ok=True, mode=0o700)
    path = directory / (hashlib.sha256(str(admin).encode()).hexdigest() + ".lock")
    body = {"schema_version": 1, "operation": "remove", "attempt_id": str(uuid.uuid4()),
            "worktree": str(target.resolve()), "common_git_dir": str(common), "git_dir": str(admin),
            "branch": "refs/heads/" + core.branch(target),
            "head": git(target, "rev-parse", "HEAD").strip(),
            "expected_state_digest": None, "outcome": "preflight"}
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    os.fchmod(fd, 0o600)
    os.write(fd, json.dumps(body).encode())
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd, path, body


def test_strict_inherited_reservation_is_not_actor_authority(removal, monkeypatch):
    core, _, target = removal
    fd, path, body = removal_reservation(core, target)
    try:
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", str(fd))
        assert core.removal_reservation(target) == body
        result = core.workspace_remove_check(target)
        assert result["schema_version"] == 2
        assert result["eligible"] is False
        assert result["reservation_id"] == body["attempt_id"]
        assert "cycle_records_unknown" in result["reasons"]
        assert "native_handoff_unavailable" in result["reasons"]
        assert "ownership_unavailable" in result["reasons"]
        assert "git_default_unavailable" in result["reasons"]
        assert "native_removal_coordination_unavailable" in result["reasons"]
        assert len(result["state_digest"]) == 64
        # Verifying an inherited lock must never release the parent's reservation.
        with path.open("rb") as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)


@pytest.mark.parametrize("problem", ["version", "target", "mode", "inode", "unlocked", "separate", "uid", "oversized"])
def test_strict_reservation_rejects_untrusted_descriptor(removal, monkeypatch, problem):
    core, _, target = removal
    fd, path, body = removal_reservation(core, target)
    other = None
    try:
        if problem in {"version", "target", "oversized"}:
            body["schema_version" if problem == "version" else "worktree"] = 2 if problem == "version" else "/wrong"
            os.ftruncate(fd, 0)
            os.pwrite(fd, b"x" * 8193 if problem == "oversized" else json.dumps(body).encode(), 0)
        elif problem == "mode":
            path.chmod(0o644)
        elif problem == "inode":
            path.unlink()
            path.write_text(json.dumps(body))
            path.chmod(0o600)
        elif problem == "unlocked":
            fcntl.flock(fd, fcntl.LOCK_UN)
        elif problem == "separate":
            other = os.open(path, os.O_RDWR)
        elif problem == "uid":
            monkeypatch.setattr(core.os, "getuid", lambda: -1)
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", str(other if other is not None else fd))
        result = core.workspace_remove_check(target)
        assert result["schema_version"] == 2
        assert result["eligible"] is False
        assert "removal_reservation_unavailable" in result["reasons"]
        assert result["state_digest"] is None
    finally:
        if other is not None:
            os.close(other)
        os.close(fd)


def test_strict_source_guard_binds_preview_digest(removal, monkeypatch):
    core, _, target = removal
    fd, _, body = removal_reservation(core, target)
    try:
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", str(fd))
        first = core.workspace_remove_check(target)
        body.update(expected_state_digest=first["state_digest"], outcome="started")
        os.ftruncate(fd, 0)
        os.pwrite(fd, json.dumps(body).encode(), 0)
        assert "removal_state_changed" not in core.workspace_remove_check(target)["reasons"]
        (target / "tracked.txt").write_text("changed\n")
        assert "removal_state_changed" in core.workspace_remove_check(target)["reasons"]
    finally:
        os.close(fd)


def strict_cycle(core, target):
    head = git(target, "rev-parse", "HEAD").strip()
    policy = {"schema_version": 1, "repository": str(core.common_git_dir(target).resolve()),
              "policy_digest": "a" * 64, "consent": {"schema_version": 1, "automatic_remove": True}}
    record = {"schema_version": 5, "cycle_id": "strict-cycle", "state": "completed",
              "initiative": {"initiative_id": "dbsctr-workflow-convergence"},
              "completed_at": core.now(), "runtime": {"adapters": {}},
              "execution": {"schema_version": 1, "mode": "native_workspace", "origin": "registered",
                            "attribution": {"status": "unavailable", "reason": "native_identity_not_collected"},
                            "adoption": None},
              "worktree": {"id": core.worktree_id(target), "branch": core.branch(target),
                           "locator": {"root": "cycle_worktree", "path": "."}, "base_commit": head,
                           "git_dir": core.git_dir(target).resolve().relative_to(core.common_git_dir(target).resolve()).as_posix()},
              "preservation_policy": policy, "commits": [{"id": head, "gates": list(core.GATES)}],
              "gates": {name: {"applicability": "required", "result": "passed", "evidence": name}
                        for name in core.GATES},
              "evidence": {"items": {name: {"gate": name, "result": "passed", "commit": head,
                                            "content": {"status": "no_content"}} for name in core.GATES}},
              "git": {"head": head, "upstream": "origin/task", "remote": {}, "pre_cycle_ahead_commits": []},
              "delivery": {"remote": "origin", "branch": "task", "base_branch": "main",
                           "github": {"repository": "owner/repo"},
                           "pull_request": {"number": 1, "url": "https://github.com/owner/repo/pull/1"}},
              "artifact_reviews": {name: {"result": "changed", "reviewed_at": core.now(),
                                         "path": name, "reason": None} for name in core.ARTIFACTS}}
    directory = core.cycle_dir(target) / "cycles"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "strict-cycle.json"
    path.write_text(json.dumps(record))
    path.chmod(0o600)
    return path, record, policy


@pytest.mark.parametrize("problem,expected", [
    ("active", "cycle_not_completed"), ("unknown", "cycle_evidence_unavailable"),
    ("old", "birth_policy_unavailable_or_changed"), ("changed", "birth_policy_unavailable_or_changed"),
    ("exception", "incomplete_cycle_evidence"), ("backup", "removal_evidence_unavailable"),
])
def test_strict_cycle_sources_never_infer_completion_or_upgrade_consent(removal, monkeypatch, problem, expected):
    core, _, target = removal
    path, record, policy = strict_cycle(core, target)
    fd, _, _ = removal_reservation(core, target)
    try:
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", str(fd))
        monkeypatch.setattr(core, "preservation_policy_snapshot", lambda root: policy)
        if problem == "active":
            record["state"] = "active"
        elif problem == "unknown":
            record["state"] = "unknown"
        elif problem == "old":
            record["preservation_policy"] = None
        elif problem == "changed":
            record["preservation_policy"] = {**policy, "policy_digest": "b" * 64}
        elif problem == "exception":
            record["gates"]["domain"].update(result="failed", exception={"kind": "operator"})
        elif problem == "backup":
            def unavailable(*args):
                raise RuntimeError("backup unavailable")
            monkeypatch.setattr(core, "verify_native_workspace_backup", unavailable)
        path.write_text(json.dumps(record))
        result = core.workspace_remove_check(target)
        assert result["eligible"] is False
        assert expected in result["reasons"]
    finally:
        os.close(fd)


def test_new_opted_cycle_without_parent_cannot_use_legacy_manual_eligibility(removal, monkeypatch):
    core, _, target = removal
    strict_cycle(core, target)
    monkeypatch.delenv("DBSCTR_REMOVAL_FD", raising=False)
    result = core.workspace_remove_check(target)
    assert result == {"schema_version": 2, "eligible": False,
                      "reasons": ["removal_reservation_unavailable"],
                       "reservation_id": None, "state_digest": None}


@pytest.mark.parametrize("kind", ["disabled", "upload-only", "historical"])
def test_unrelated_preservation_policy_retains_legacy_inspection(removal, monkeypatch, kind):
    core, _, target = removal
    path, record, policy = strict_cycle(core, target)
    record.pop("initiative")
    if kind == "disabled":
        record["preservation_policy"]["consent"]["automatic_remove"] = False
    elif kind == "upload-only":
        record["preservation_policy"]["consent"] = {"schema_version": 1, "uploads": []}
    path.write_text(json.dumps(record))
    monkeypatch.delenv("DBSCTR_REMOVAL_FD", raising=False)
    expected = core.legacy_workspace_remove_check(target)
    assert core.workspace_remove_check(target) == expected
    assert expected["schema_version"] == 1
    assert "retained_24_hours" in expected["reasons"]


def test_satisfied_synthetic_oracle_cannot_remove_permanent_runtime_blockers(removal, monkeypatch):
    core, _, target = removal
    _, _, policy = strict_cycle(core, target)
    fd, _, _ = removal_reservation(core, target)
    try:
        monkeypatch.setenv("DBSCTR_REMOVAL_FD", str(fd))
        monkeypatch.setattr(core, "preservation_policy_snapshot", lambda _: policy)
        monkeypatch.setattr(core, "removal_default_predicates", lambda *args: [])
        result = core.workspace_remove_check(target)
        assert result["eligible"] is False
        assert {"ownership_unavailable", "native_handoff_unavailable", "git_default_unavailable",
                "native_removal_coordination_unavailable"} <= set(result["reasons"])
    finally:
        os.close(fd)


@pytest.mark.parametrize("problem,expected", [
    (None, []), ("default_drift", ["git_default_changed"]),
    ("stale_head", ["git_default_changed"]), ("dirty_primary", ["primary_not_synchronized"]),
    ("temp_integration", ["ultimate_default_ancestry_unverified"]),
    ("gate_ancestor", ["ultimate_default_ancestry_unverified"]),
    ("wrong_pr_head", ["pr_delivery_unverified"]), ("unavailable", ["git_default_unavailable"]),
])
def test_strict_default_source_oracle_never_accepts_feature_only_preservation(removal, monkeypatch, problem, expected):
    core, primary, target = removal
    _, record, _ = strict_cycle(core, target)
    default = core.branch(primary)
    head = git(primary, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(core, "upstream", lambda root: "origin/" + default)
    monkeypatch.setattr(core, "remote_destination", lambda *args: {})
    pull = {"number": 1, "url": record["delivery"]["pull_request"]["url"], "repository": "owner/repo",
            "state": "MERGED", "baseRefName": "main", "headRefName": "task", "headRefOid": head,
            "mergeCommit": {"oid": head}}
    observation = {"repository": "owner/repo", "repository_after": "owner/repo", "remote": "origin",
                   "default": default, "default_after": default, "head": head, "head_after": head,
                   "fetched_head": head, "pull_requests": {"1": pull}}
    if problem == "default_drift":
        observation["default_after"] = "another-default"
    elif problem == "stale_head":
        observation["head_after"] = "b" * 40
    elif problem == "dirty_primary":
        (primary / "tracked.txt").write_text("retain\n")
    elif problem in {"temp_integration", "gate_ancestor"}:
        git(target, "commit", "--allow-empty", "-m", "feature-only obligation")
        feature = git(target, "rev-parse", "HEAD").strip()
        if problem == "gate_ancestor":
            record["commits"].insert(0, {"id": feature, "gates": ["domain"]})
    elif problem == "wrong_pr_head":
        pull["headRefOid"] = "b" * 40
    elif problem == "unavailable":
        observation = {}
    assert core.removal_default_predicates(target, [record], observation) == expected


def test_strict_standalone_dvc_and_ignored_plans_remain_unpreserved(removal, monkeypatch):
    core, primary, target = removal
    (target / "file.dvc").write_text("outs:\n- md5: " + "a" * 32 + "\n  size: 1\n  hash: md5\n  path: data\n")
    (target / ".gitignore").write_text(".dbsctr/\n")
    git(target, "add", "file.dvc", ".gitignore")
    git(target, "commit", "-m", "standalone metadata")
    git(primary, "merge", "--ff-only", "task")
    (target / ".dbsctr").mkdir()
    (target / ".dbsctr/plan.json").write_text('{"unique": true}')
    calls = []
    original = core.removal_run
    def native(root, argv, **kwargs):
        calls.append(argv)
        if argv[0] == "dvc":
            return "{}"  # Clean local status is not remote object disposition.
        return original(root, argv, **kwargs)
    monkeypatch.setattr(core, "removal_run", native)
    result = core.legacy_workspace_remove_check(target, strict=True)
    assert "data_disposition_required" in result["reasons"]
    assert ["dvc", "data", "status", "--unchanged", "--json"] in calls
    assert (target / ".dbsctr/plan.json").exists()
