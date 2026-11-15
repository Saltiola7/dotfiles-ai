"""Privileged coordinator entrypoints retain their default-off trust boundary."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_default_repository_policy_is_disabled_without_enrollment_or_credentials() -> None:
    policy = ROOT / ".github/dbsctr-integration.json"
    assert json.loads(policy.read_text()) == {"schema_version": 2, "enabled": False}
    result = subprocess.run([sys.executable, str(ROOT / "dot_local/bin/executable_dbsctr-integration"),
                             "advance", "--policy", str(policy)], input="untrusted payload\n",
                            capture_output=True, text=True, cwd=ROOT, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "disabled"


def test_shared_action_uses_its_pinned_source_and_keeps_data_out_of_shell_source() -> None:
    action = (ROOT / ".github/actions/integration-coordinator/action.yml").read_text()
    run = action.split("run:", 1)[1]
    assert "${{" not in run
    assert '"$GITHUB_ACTION_PATH/../../../dot_local/bin/executable_dbsctr-integration"' in run
    assert 'advance --policy "$DBSCTR_POLICY_PATH"' in run
    assert "DBSCTR_COORDINATOR_IMPLEMENTATION_REF:" in action
    assert "github.action_ref" in action
    assert "DBSCTR_COORDINATOR_TOKEN:" in action
    assert "persist-credentials" not in action and "actions/cache" not in action


def test_worker_is_a_separate_short_trusted_wakeup_with_no_pr_code_checkout() -> None:
    text = (ROOT / ".github/workflows/dbsctr-integration.yml").read_text()
    assert "workflow_dispatch:" in text and "workflow_run:" in text and "schedule:" in text
    assert "pull_request_target:" not in text and "pull_request:" not in text
    assert "cancel-in-progress: false" in text
    assert "environment: dbsctr-integration" in text
    assert "vars.DBSCTR_COORDINATOR_ENABLED == 'true'" in text
    assert "ref: ${{ github.sha }}" in text and "persist-credentials: false" in text
    assert "runs-on: ubuntu-24.04" in text and "timeout-minutes: 15" in text
    assert "contents: write" not in text and "id-token:" not in text
    assert "DBSCTR_COORDINATOR_TOKEN" in text
    assert "pull_request.head" not in text and "workflow_run.head" not in text
    assert "actions/cache" not in text and "DAGGER" not in text
