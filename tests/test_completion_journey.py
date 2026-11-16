"""Primary guidance consumes existing public completion proof, not a new engine.

Instruction assertions and synthetic CLI fixtures do not measure model quality
or claim installed primary behavior. Provider routes and permissions stay owned
by the existing control-plane tests.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_completion_segments import segments
from test_dbsctr_external_completion import arguments, cycle, ready, snapshot


AGENTS = Path(__file__).resolve().parents[1] / "private_dot_config/opencode/agents"


@pytest.mark.parametrize("role", ["build-gpt", "build-claude"])
def test_primary_completion_guidance_preserves_classified_boundaries(role: str) -> None:
    text = (AGENTS / f"{role}.md").read_text()
    _, header, body = text.split("---", 2)
    assert "mode: primary" in header
    assert "## Completion reporting" in body
    normalized = " ".join(body.split())
    for clause in (
        "`dbsctrctl complete-external --help`",
        "`dbsctrctl complete-external --preview`",
        "verified cycle/PR/head/merge pins",
        "`--delivery-segment`",
        "`completion_preview` schema 1",
        "`passed`, `blocked`, `unavailable`, `not_evaluated`",
        "A preview is not completion",
        "Unknown versions mean `capability_unavailable`",
        "Writer denial means `capability_gap`",
        "original execution identity",
        "actual exit code and recorded result",
        "supported next action",
        "Do not switch identity or repeat a denied operation",
        "no private helpers or manual ledger edits",
        "completed; cleanup retained",
        "Source delivery, deployment, acceptance, logical completion and cleanup",
        "Uniquely proved bookkeeping needs no extra confirmation",
        "Fresh merge, installation, cloud and destructive actions retain separate approval",
        "raw errors, credentials, transcripts and private custody",
    ):
        assert clause in normalized, (role, clause)
    assert normalized.index("complete-external --help") < normalized.index("complete-external --preview")


@pytest.mark.parametrize("cycle", ["source-only"], indirect=True)
def test_journey_uses_public_preview_then_retained_historical_proof(
        ready: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    selector, transport = segments(ready)
    monkeypatch.setattr(ready.core, "github_json", transport)
    before = json.loads(ready.path.read_text())
    initial = snapshot(ready)
    capsys.readouterr()
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--preview")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 1 and report["kind"] == "completion_preview"
    assert report["status"] == "passed" and report["verification"] == "current"
    assert all(stage["status"] in {"passed", "blocked", "unavailable", "not_evaluated"}
               for stage in report["stages"].values())
    assert report["stages"]["cleanup"] == {
        "status": "not_evaluated", "reason_codes": ["cleanup_independent"]}
    assert {name: value["evidence"] for name, value in report["evidence_dispositions"].items()} == {
        name: gate["evidence"] for name, gate in before["gates"].items()
        if gate["applicability"] == "required"}
    assert snapshot(ready) == initial

    assert ready.invoke(*arguments(ready, "--delivery-segment", selector)) == 0
    receipt = json.loads(capsys.readouterr().out)
    after = ready.core.read_cycle_record(ready.root, ready.path, historical=True)
    assert after["state"] == "completed"
    assert after["evidence"] == before["evidence"] and after["gates"] == before["gates"]
    assert ready.root.is_dir()
    completed = snapshot(ready)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector, "--cycle-id", "cycle-1")) == 0
    capsys.readouterr()
    assert snapshot(ready) == completed

    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Historical preview must not acquire credentials or probe runtime")

    monkeypatch.setattr(ready.core, "github_environment", unavailable)
    monkeypatch.setattr(ready.core, "evidence_runtime_probe", unavailable)
    assert ready.invoke(*arguments(ready, "--delivery-segment", selector,
                                  "--cycle-id", "cycle-1", "--preview")) == 0
    historical = json.loads(capsys.readouterr().out)
    assert historical["schema_version"] == 1 and historical["verification"] == "historical"
    assert historical["receipt"] == receipt
    assert historical["stages"]["runtime"]["status"] == "not_evaluated"
    assert historical["stages"]["delivery"]["status"] == "not_evaluated"
    assert snapshot(ready) == completed
