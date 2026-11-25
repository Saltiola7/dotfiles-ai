"""Affected-trigger, selection-basis and named-check contracts of the closed runner protocol."""

import hashlib
import json
from pathlib import Path
import sys
import uuid

import pytest

from test_continuous_validation import git, private_json, worktree  # noqa: F401 - shared fixtures


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from continuous_validation import runner


ADAPTER = r'''import json,platform,sys,time
from pathlib import Path
request=json.load(sys.stdin)
config=request.get('config',{})
action=sys.argv[1]
def check(name,kind):
    return {'id':name,'class':kind,'backend':'native','lane':{'os':sys.platform,'architecture':platform.machine(),'python':platform.python_version(),'tools':{},'dependencies':{}},'timeout_seconds':3,'cacheable':False,'configuration':{}}
if action=='describe':
    value={'schema_version':1,'adapter_id':'fixture','input_patterns':['**'],'checks':[check('quick','cheap'),check('slow','expensive')]}
elif action=='select':
    extra={'basis':config['basis']} if 'basis' in config else {}
    value={'schema_version':1,'checks':config.get('checks',['quick','slow']),'reason':'fixture scope','complete':not config.get('incomplete',False),**extra}
else:
    Path(request['log_path']).write_text('private fixture log\n')
    value={'schema_version':1,'check_id':request['check']['id'],'status':'passed','exit_code':0,'runtime':{'python':platform.python_version()},'test_ids':['fixture::case'],'diagnostic_codes':[]}
print(json.dumps(value))
'''


@pytest.fixture
def bound(worktree, tmp_path, monkeypatch):
    """An enrolled task whose adapter answers select with the optional basis."""
    adapter = worktree / ".ci/adapter.py"
    adapter.parent.mkdir()
    adapter.write_text(ADAPTER)
    git(worktree, "add", ".ci/adapter.py")
    git(worktree, "commit", "-m", "affected fixture adapter")
    value = {
        "schema_version": 1, "enabled": True, "mode": "shadow",
        "worktree": str(worktree), "adapter": ".ci/adapter.py",
        "adapter_digest": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "adapter_python": sys.executable, "adapter_config": {},
        "repository_id": runner.repository_id(worktree),
        "session_id": str(uuid.uuid4()), "cycle_id": "fixture-cycle",
        "base": git(worktree, "rev-parse", "HEAD"), "state_dir": str(tmp_path / "state"),
    }
    path = private_json(tmp_path / "enrollment.json", value)
    monkeypatch.setattr(runner, "cycle_open", lambda _: True)
    monkeypatch.setattr(runner, "budget_root", lambda: tmp_path / "shared-admission")
    monkeypatch.setattr(runner, "pressure", lambda _: False)
    return path, value


def request(path, trigger="affected", **extra):
    return {"schema_version": 1, "enrollment": str(path), "trigger": trigger, **extra}


def configure(path, value, **config):
    private_json(path, {**value, "adapter_config": config})


def executed(result):
    return [(item["check_id"], item["status"], item["executed"]) for item in result["observations"]]


def test_affected_trigger_runs_cheap_and_expensive_checks(bound):
    path, _ = bound
    result = runner.run_request(request(path))
    assert result["status"] == "passed" and result["pending_checks"] == []
    assert executed(result) == [("quick", "passed", True), ("slow", "passed", True)]
    assert result["selection_complete"] is True


def test_edit_still_defers_expensive_checks(bound):
    path, _ = bound
    result = runner.run_request(request(path, "edit"))
    assert result["status"] == "pending" and result["pending_checks"] == ["slow"]
    assert executed(result) == [("quick", "passed", True)]


@pytest.mark.parametrize("config, basis", [({}, None), ({"basis": "broad", "incomplete": True}, "broad"),
                                           ({"basis": "affected", "incomplete": True}, "affected")])
def test_selection_basis_is_accepted_and_bound_into_the_selection_identity(bound, config, basis):
    path, value = bound
    configure(path, value, **config)
    result = runner.run_request(request(path))
    assert result["observations"][0]["selection_digest"] == runner.digest({
        "schema_version": 1, "checks": ["quick", "slow"], "reason": "fixture scope",
        "complete": "incomplete" not in config, **({"basis": basis} if basis else {})})
    assert result["selection_complete"] is ("incomplete" not in config)


@pytest.mark.parametrize("basis", ["partial", "", "Affected", 1, None, ["affected"]])
def test_unknown_selection_basis_is_an_invalid_selection(bound, basis):
    path, value = bound
    configure(path, value, basis=basis)
    result = runner.run_request(request(path))
    assert result["status"] == "unavailable" and result["error_code"] == "invalid_selection"
    assert result["observations"] == []


def test_named_checks_narrow_execution_and_leave_admissibility_to_the_adapter(bound):
    path, value = bound
    result = runner.run_request(request(path, checks=["slow"]))
    # A named selection is not the complete obligation, so an all-passed run stays pending, not passed.
    assert result["status"] == "pending" and result["pending_checks"] == ["selection_incomplete"]
    assert result["selection_complete"] is False
    assert executed(result) == [("slow", "passed", True)]
    # The runner forwards the named checks even when the adapter's own selection omits them.
    configure(path, value, checks=["quick"])
    forwarded = runner.run_request(request(path, checks=["slow"]))
    assert executed(forwarded) == [("slow", "passed", True)]


def test_named_check_outside_the_manifest_is_an_invalid_selection(bound):
    path, _ = bound
    result = runner.run_request(request(path, checks=["missing"]))
    assert result["status"] == "unavailable" and result["error_code"] == "invalid_selection"


@pytest.mark.parametrize("trigger, checks, code", [
    ("edit", ["quick"], "invalid_checks"), ("checkpoint", ["quick"], "invalid_checks"),
    ("manual", ["quick"], "invalid_checks"),
    ("affected", [], "invalid_checks"), ("affected", "quick", "invalid_checks"),
    ("affected", ["quick", "quick"], "invalid_checks"), ("affected", ["quick", 1], "invalid_checks"),
    ("affected", ["../escape"], "invalid_checks"), ("affected", ["x" * 129], "invalid_checks"),
])
def test_invalid_named_checks_fail_before_any_state(bound, trigger, checks, code):
    path, value = bound
    with pytest.raises(runner.ValidationError, match=code):
        runner.run_request(request(path, trigger, checks=checks))
    assert not Path(value["state_dir"]).exists()


def test_checkpoint_head_is_not_accepted_for_affected(bound):
    path, value = bound
    head = git(Path(value["worktree"]), "rev-parse", "HEAD")
    with pytest.raises(runner.ValidationError, match="invalid_checkpoint_head"):
        runner.run_request({**request(path), "checkpoint_head": head})
    assert not Path(value["state_dir"]).exists()


def test_request_identity_includes_the_named_checks(bound):
    path, _ = bound
    payload = {**request(path, request_id="named"), "checks": ["quick"]}
    assert runner.run_request(payload)["new_execution"] is True
    with pytest.raises(runner.ValidationError, match="request_identity_reused"):
        runner.run_request({**payload, "checks": ["slow"]})
    assert runner.run_request(payload)["new_execution"] is False
