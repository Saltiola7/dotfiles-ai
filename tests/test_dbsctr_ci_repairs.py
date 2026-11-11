"""Supervised accounting never executes a repair or authorizes delivery."""

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"


def load_core():
    loader = importlib.machinery.SourceFileLoader("ci_repair_test_core", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    core = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = core
    loader.exec_module(core)
    return core


@pytest.fixture
def case(tmp_path, monkeypatch):
    core = load_core()
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-c", "commit.gpgsign=false", *args],
                                       cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()

    git("init", "-b", "main")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/test.yml").write_text("name: test\n")
    (repo / "contract.md").write_text("Preserve rollback assertions.\n")
    (repo / "smoke.sh").write_text("cmp before after\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    head = git("rev-parse", "HEAD")
    git("remote", "add", "origin", "https://github.com/example/project.git")
    git("update-ref", "refs/remotes/origin/main", head)
    git("switch", "-c", "feature")
    git("branch", "--set-upstream-to=origin/main")
    data = {
        "pulls/7": {"number": 7, "state": "open", "head": {"sha": head, "ref": "feature",
                      "repo": {"full_name": "example/project"}},
                    "base": {"sha": head, "ref": "main", "repo": {"full_name": "example/project"}}},
        "actions/jobs/11": {"id": 11, "run_id": 10, "run_attempt": 1, "head_sha": head, "name": "smoke",
                            "status": "completed", "conclusion": "failure"},
        "actions/runs/10": {"id": 10, "run_attempt": 1, "pull_requests": [{"number": 7,
                            "head": {"sha": head}, "base": {"sha": head}}],
                            "head_sha": head, "event": "pull_request",
                            "path": ".github/workflows/test.yml", "repository": {"full_name": "example/project"}},
    }
    calls = []

    def request(account, method, endpoint, fields, timeout):
        calls.append((account, method, endpoint, fields, timeout))
        return {"status": "success", "value": data[endpoint.removeprefix("repos/example/project/")]}

    monkeypatch.setattr(core, "root_dir", lambda: repo)
    monkeypatch.setattr(core, "workflow_github", request)
    args = SimpleNamespace(pull_request=7, job_id=11, github_account="fixture",
                           signature="cmp command not found", specification="contract.md",
                           paths=["smoke.sh"], preflight=True, approval=None, expected_repair_digest=None)
    return SimpleNamespace(core=core, repo=repo, git=git, data=data, calls=calls, request=request, args=args)


def preview(case, capsys):
    case.args.preflight = True
    case.args.approval = case.args.expected_repair_digest = None
    case.core.command_ci_repair(case.args)
    return json.loads(capsys.readouterr().out)


def reserve(case, digest):
    case.args.preflight = False
    case.args.approval = "agent-confirmed"
    case.args.expected_repair_digest = digest
    case.core.command_ci_repair(case.args)


def test_real_cli_requires_explicit_supervised_inputs():
    core = load_core()
    args = core.parser().parse_args([
        "ci-repair", "--pull-request", "7", "--job-id", "11", "--github-account", "fixture",
        "--signature", "cmp command not found", "--specification", "contract.md",
        "--paths", "smoke.sh", "--preflight",
    ])
    assert args.func is core.command_ci_repair


@pytest.mark.parametrize("account", ["fixture", "123456_example", "a" * 39])
def test_account_selector_accepts_managed_users_without_changing_authority(case, capsys, account):
    case.args.github_account = account
    plan = preview(case, capsys)
    assert plan["plan"]["github_account"] == account
    assert all(call[0] == account for call in case.calls)
    reserve(case, plan["repair_digest"])
    result = json.loads(capsys.readouterr().out)
    assert result["attempt"] == 1 and result["merge_authority"] is False
    with pytest.raises(RuntimeError, match="plan_changed"):
        reserve(case, plan["repair_digest"])


@pytest.mark.parametrize("account", ["", "_managed", "-option", "a" * 40,
                                      "user name", "user\nname", "user/name", "usér", None])
def test_invalid_account_selector_refuses_before_native_reads(case, account):
    case.args.github_account = account
    with pytest.raises(RuntimeError, match="ci_repair_account_invalid"):
        case.core.ci_repair_plan(case.repo, case.args, request=case.request)
    assert not case.calls


def test_preflight_does_not_consume_and_exact_approval_consumes(case, capsys):
    first = preview(case, capsys)
    assert first == preview(case, capsys)
    assert first["plan"]["attempt"] == 1
    assert all(account == "fixture" and method == "GET" and not fields and 0 < timeout <= 30
               for account, method, _, fields, timeout in case.calls)
    reserve(case, first["repair_digest"])
    result = json.loads(capsys.readouterr().out)
    assert result["attempt"] == 1 and result["merge_authority"] is False
    assert (case.repo / "smoke.sh").read_text() == "cmp before after\n"
    with pytest.raises(RuntimeError, match="plan_changed"):
        reserve(case, first["repair_digest"])


def test_budget_survives_module_restart_and_changed_head(case, capsys, monkeypatch):
    for number in range(1, 4):
        plan = preview(case, capsys)
        assert plan["plan"]["attempt"] == number
        reserve(case, plan["repair_digest"])
        capsys.readouterr()
        case.git("commit", "--allow-empty", "-m", f"repair {number}")
        head = case.git("rev-parse", "HEAD")
        case.data["pulls/7"]["head"]["sha"] = head
        case.data["actions/jobs/11"]["head_sha"] = head
        case.data["actions/runs/10"]["head_sha"] = head
        case.data["actions/runs/10"]["pull_requests"][0]["head"]["sha"] = head
        case.core = load_core()
        monkeypatch.setattr(case.core, "root_dir", lambda: case.repo)
        monkeypatch.setattr(case.core, "workflow_github", case.request)
    with pytest.raises(RuntimeError, match="attempts_exhausted"):
        preview(case, capsys)


@pytest.mark.parametrize("field,value", [("conclusion", "success"), ("conclusion", "cancelled"),
                                         ("status", "in_progress"), ("head_sha", "0" * 40)])
def test_nonfailure_or_wrong_head_never_authorizes(case, field, value, capsys):
    case.data["actions/jobs/11"][field] = value
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        preview(case, capsys)


def test_denied_api_and_changed_scope_fail_closed(case, monkeypatch, capsys):
    first = preview(case, capsys)
    (case.repo / "smoke.sh").write_text("changed without approval\n")
    with pytest.raises(RuntimeError, match="plan_changed|identity_mismatch"):
        reserve(case, first["repair_digest"])
    monkeypatch.setattr(case.core, "workflow_github", lambda *args: {"status": "blocked"})
    with pytest.raises(RuntimeError, match="native_evidence_unavailable"):
        preview(case, capsys)


def test_missing_established_ledger_never_resets_budget(case, capsys):
    first = preview(case, capsys)
    reserve(case, first["repair_digest"])
    capsys.readouterr()
    ledger = case.core.cycle_dir(case.repo) / "qualifications/ci-repairs.json"
    ledger.unlink()
    with pytest.raises(RuntimeError):
        preview(case, capsys)


def test_symlink_scope_is_not_writable_authority(case, capsys):
    outside = case.repo.parent / "outside"
    outside.write_text("preserve\n")
    (case.repo / "smoke.sh").unlink()
    (case.repo / "smoke.sh").symlink_to(outside)
    with pytest.raises(RuntimeError, match="scope_unsafe"):
        preview(case, capsys)
    assert outside.read_text() == "preserve\n"


@pytest.mark.parametrize("digest", [None, "not-a-digest", "a" * 63])
def test_reservation_without_exact_digest_is_rejected(case, digest):
    case.args.preflight = False
    case.args.approval = "agent-confirmed"
    case.args.expected_repair_digest = digest
    with pytest.raises(RuntimeError, match="exact_approval_required"):
        case.core.command_ci_repair(case.args)


@pytest.mark.parametrize("field,value", [("id", 99), ("event", "push"),
                                        ("pull_requests", []), ("run_attempt", 2)])
def test_unbound_or_stale_run_is_rejected(case, field, value, capsys):
    case.data["actions/runs/10"][field] = value
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        preview(case, capsys)


def test_account_and_target_are_part_of_approved_plan(case, capsys):
    first = preview(case, capsys)
    assert first["plan"]["github_account"] == "fixture"
    assert first["plan"]["target_ref"] == "refs/heads/main"
    case.args.github_account = "other"
    with pytest.raises(RuntimeError, match="plan_changed"):
        reserve(case, first["repair_digest"])


def test_corrupt_ledger_blocks_instead_of_resetting(case, capsys):
    first = preview(case, capsys)
    reserve(case, first["repair_digest"])
    capsys.readouterr()
    ledger = case.core.cycle_dir(case.repo) / "qualifications/ci-repairs.json"
    ledger.write_text('{"schema_version":1,"entries":{"bad":[]}}')
    with pytest.raises(RuntimeError, match="accounting_invalid"):
        preview(case, capsys)


def test_common_git_accounting_is_shared_by_linked_worktrees(case, capsys):
    plan = preview(case, capsys)
    reserve(case, plan["repair_digest"])
    capsys.readouterr()
    linked = case.repo.parent / "linked"
    case.git("worktree", "add", "-b", "linked", str(linked), "HEAD")
    assert case.core.cycle_dir(linked) == case.core.cycle_dir(case.repo)
    _, _, _, ledger = case.core.ci_repair_ledger(linked, "example/project")
    assert [len(attempts) for attempts in ledger["entries"].values()] == [1]


def test_concurrent_same_plan_reservations_cannot_both_succeed(case, capsys):
    first = preview(case, capsys)
    repository, fingerprint, plan = case.core.ci_repair_plan(case.repo, case.args)
    arguments = vars(case.args) | {"preflight": False, "approval": "agent-confirmed",
                                  "expected_repair_digest": first["repair_digest"]}
    program = """
import json, runpy, sys
from pathlib import Path
from types import SimpleNamespace
core = runpy.run_path(sys.argv[1])
scope = core['command_ci_repair'].__globals__
scope['root_dir'] = lambda: Path(sys.argv[2])
scope['ci_repair_plan'] = lambda *a: tuple(json.loads(sys.argv[3]))
core['command_ci_repair'](SimpleNamespace(**json.loads(sys.argv[4])))
"""
    command = [sys.executable, "-c", program, str(SCRIPT), str(case.repo),
               json.dumps([repository, fingerprint, plan]), json.dumps(arguments)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: subprocess.run(command, capture_output=True, text=True, timeout=30), range(2)))
    assert sorted(result.returncode for result in results) == [0, 1]
    assert any("plan_changed" in result.stderr or "evidence is busy" in result.stderr for result in results)
    _, _, _, ledger = case.core.ci_repair_ledger(case.repo, repository)
    assert len(ledger["entries"][fingerprint]) == 1


def test_supervised_instruction_and_contract_keep_automatic_repairs_blocked():
    root = SCRIPT.parents[2]
    skill = (root / "dot_agents/skills/dbsctr-pr-review/SKILL.md").read_text()
    contract = (root / "docs/specs/dbsctr_v3_lifecycle/features/supervised-ci-repairs.md").read_text()
    for phrase in ("--expected-repair-digest", "explicit", "three", "activation"):
        assert phrase in skill and phrase in contract
    assert "separate activation after merge" in skill
    assert "this entry point blocks every automatic repair" in skill
    assert "reopens no completed cycle" in skill


def test_base_drift_and_foreign_pr_block_reservation(case, capsys):
    first = preview(case, capsys)
    case.data["pulls/7"]["base"]["sha"] = "0" * 40
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        reserve(case, first["repair_digest"])
    case.data["pulls/7"]["head"]["repo"]["full_name"] = "other/project"
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        preview(case, capsys)


def test_interrupted_initialization_does_not_refund_or_reinitialize(case, capsys, monkeypatch):
    first = preview(case, capsys)
    original = case.core.private_json

    def fail_ledger(path, value, **kwargs):
        if path.name == "ci-repairs.json":
            raise OSError("interrupted")
        return original(path, value, **kwargs)

    monkeypatch.setattr(case.core, "private_json", fail_ledger)
    with pytest.raises(RuntimeError, match="evidence_unavailable"):
        reserve(case, first["repair_digest"])
    with pytest.raises(RuntimeError):
        preview(case, capsys)


def test_ledger_symlink_is_rejected_without_touching_target(case, capsys):
    first = preview(case, capsys)
    reserve(case, first["repair_digest"])
    capsys.readouterr()
    ledger = case.core.cycle_dir(case.repo) / "qualifications/ci-repairs.json"
    outside = case.repo.parent / "private"
    outside.write_text("preserve")
    ledger.unlink()
    ledger.symlink_to(outside)
    with pytest.raises(RuntimeError):
        preview(case, capsys)
    assert outside.read_text() == "preserve"


def test_failure_from_old_tested_base_is_not_current_evidence(case, capsys):
    case.data["actions/runs/10"]["pull_requests"][0]["base"]["sha"] = "0" * 40
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        preview(case, capsys)


def test_replacing_a_pr_does_not_reset_same_problem_budget(case, capsys):
    first = preview(case, capsys)
    reserve(case, first["repair_digest"])
    capsys.readouterr()
    case.args.pull_request = 8
    case.data["pulls/8"] = case.data.pop("pulls/7")
    case.data["pulls/8"]["number"] = 8
    case.data["actions/runs/10"]["pull_requests"][0]["number"] = 8
    assert preview(case, capsys)["plan"]["attempt"] == 2
