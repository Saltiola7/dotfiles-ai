"""Offline v1 compatibility and explicit v2/live command selection."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "private_dot_config/dotfiles-ai"))
from integration_coordinator import core, runtime
from integration_coordinator import cli


def call(args: list[str], body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ROOT / "dot_local/bin/executable_dbsctr-integration"), *args],
                          input=body, text=True, capture_output=True, cwd=ROOT, timeout=15)


def test_runtime_source_validation_never_claims_native_authority() -> None:
    value = runtime.SourceSeries("example/repo", 1, "1" * 40, "2" * 40,
        (runtime.SourceEntry("2" * 40, "phase", ("domain", "behavior")),), "3" * 64)
    result = call(["validate", "--kind", "source"], runtime.encode(value).decode())
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "valid", "authority": "structural_only",
                                       "kind": "source", "sha256": core.identity(value)}


def test_runtime_target_status_stays_offline_and_versioned() -> None:
    target = runtime.Target("example/repo", "main", "1" * 40, "2" * 64)
    result = call(["status"], runtime.encode(target).decode())
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "offline", "authority": "unverified",
                                       "queued": 0, "active": False, "generation": 0}


def test_unselected_live_commands_do_not_consume_the_input_or_change_old_default() -> None:
    for command in ("submit", "adopt", "advance", "reconcile", "operator-resume"):
        result = call([command], '{"schema_version":2,"enabled":true,"credential":"fixture"}')
        assert result.returncode == 78 and result.stdout == ""
        assert result.stderr.strip() == "dbsctr-integration: live_adapters_unavailable"


def test_selected_adoption_forwards_the_explicit_mode_to_the_paired_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    def local(action: str, arguments: list[str]) -> int:
        calls.append((action, arguments))
        return 0
    monkeypatch.setattr(cli, "_local_action", local)
    assert cli.main(["adopt", "--cycle-id", "retained", "--pr", "12", "--integration-mode", "admin"]) == 0
    assert calls == [("adopt", ["--cycle-id", "retained", "--pr", "12", "--integration-mode", "admin"])]
