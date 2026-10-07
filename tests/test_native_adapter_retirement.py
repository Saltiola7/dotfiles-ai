"""Retirement keeps history assets out of managed removal and blocks old hooks.

The retired test_codex_signed_updates suite exercised the continuation producer's
ChatGPT-app signature policy, rewritten smoke calls and receipt admission, not
the managed CLI updater. Managed binary/lock, candidate identity, staged update,
rollback and home-preservation coverage stays in test_codex_distribution.
Legacy uncertain-operation preservation stays in test_workspace_adoption.

The continuation-native/probe, requalification/recovery-refresh and Codex-core
bridge suites exercised the same removed receipt/admission transport. Their
current replacement contracts are explicit native registration, unavailable
actor attribution, in-place adoption and refusal of retired hooks/commands;
see test_worktrunk_registration, test_native_workspace_execution,
test_workspace_adoption, test_codex_distribution and test_native_cli_projection.
Independent Codex history hooks remain covered by test_codex_control_plane.
The OpenCode continuation/checkout-continuation suites used the removed plugin
and transparent routing protocol. CLI refusal is now test_dbsctr_continuation;
retained native V1/V2 evidence reads remain in test_opencode_v2_authority.
Historical source loss has a native-checkout regression in
test_native_checkout_identity instead of a writer-binding recovery test.
The retired test_continuation_deploy suite targeted the removed deployer;
owned-target refusal and machine-local configuration preservation are covered by
test_opencode_distribution and test_opencode_control_plane. Live cutover remains
separate qualification, not an assertion that the old deployer still exists.
"""
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("source,target", [
    ("dot_local/bin/executable_codex-continuation", ".local/bin/codex-continuation"),
    ("dot_local/bin/executable_codex-continuation-probe", ".local/bin/codex-continuation-probe"),
    ("dot_local/bin/executable_codex-requalify", ".local/bin/codex-requalify"),
    ("private_dot_config/opencode/tools/dbsctr.ts", ".config/opencode/tools/dbsctr.ts"),
    ("private_dot_config/opencode/plugins/continuation.ts", ".config/opencode/plugins/continuation.ts"),
    ("private_dot_config/opencode/plugins/initiative-context.ts", ".config/opencode/plugins/initiative-context.ts"),
    ("private_dot_config/opencode/lib/continuation.ts", ".config/opencode/lib/continuation.ts"),
    ("dot_local/bin/executable_opencode-continuation-deploy", ".local/bin/opencode-continuation-deploy"),
    ("dot_local/share/opencode-continuation/native_probe.py", ".local/share/opencode-continuation/native_probe.py"),
])
def test_retired_adapters_are_not_distributed(source, target):
    assert not (ROOT / source).exists()
    removals = (ROOT / ".chezmoiremove").read_text().splitlines()
    assert target in removals


def test_retirement_does_not_remove_private_history_or_independent_hooks():
    removals = [line for line in (ROOT / ".chezmoiremove").read_text().splitlines()
                if line and not line.startswith("#")]
    for target in removals:
        assert not any(part in {".codex", "state", "dbsctr", "history", "sessions"}
                       for part in Path(target).parts)
        assert not any(symbol in target for symbol in ("*", "?", "["))
    assert (ROOT / "dot_local/bin/executable_codex-control-plane").is_file()
    assert (ROOT / "dot_local/bin/executable_codex-update-all").is_file()
    assert (ROOT / "dot_local/bin/executable_codex-project").is_file()
