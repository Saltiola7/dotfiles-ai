"""Retired admission controls cannot mutate or reactivate retained evidence.

Native actor/terminal historical reads remain in test_opencode_v2_authority;
native checkout identity, adoption and uncertain operations are covered by
test_native_checkout_identity, test_workspace_adoption and
test_native_workspace_execution. No new-work caller uses the old writer engine.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"


@pytest.mark.parametrize("command", [
    "continuation-check", "continuation-enroll", "continuation-attach", "continuation-admit",
    "continuation-finish", "continuation-handover", "continuation-recover", "continuation-v2",
    "continuation-storage-check", "continuation-storage-recover",
])
def test_retired_control_refuses_before_reading_or_mutating_evidence(tmp_path, command):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    retained = state / "retained-evidence.json"
    before = b'{"state":"uncertain","gate":"failed"}\n'
    retained.write_bytes(before)
    result = subprocess.run(
        [sys.executable, str(SOURCE), command, "--request-json", "-"],
        input=json.dumps({"session_id": "forged-owner", "message_id": "forged-message",
                          "state": "owned", "generation": 1}),
        cwd=tmp_path, text=True, capture_output=True, timeout=10,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "DBSCTR_STATE_ROOT": str(state),
             "XDG_DATA_HOME": str(tmp_path / "data"), "XDG_STATE_HOME": str(state)},
    )
    assert result.returncode == 1
    assert "commands are retired" in result.stderr and not result.stdout
    assert retained.read_bytes() == before
    assert sorted(path.name for path in state.iterdir()) == ["retained-evidence.json"]
