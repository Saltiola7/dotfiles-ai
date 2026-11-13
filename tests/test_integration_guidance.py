"""Managed lifecycle guidance must use the enrolled route without widening legacy authority."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lifecycle_routes_enrolled_delivery_and_retains_existing_shadow_guidance() -> None:
    entry = (ROOT / "dot_agents/skills/dbsctr/SKILL.md").read_text()
    guide = ROOT / "dot_agents/skills/dbsctr/references/integration-coordinator.md"
    assert "references/integration-coordinator.md" in entry
    body = guide.read_text()
    for term in ("--integration-mode", "draft_pr", "ordinary", "admin", "unadmitted",
                 "integration-submit", "integration-status", "--integration-authorization",
                 "--expected-generation", "original task", "Dagger", "shadow",
                 "material", "unchanged", "retention", "worktree"):
        assert term.lower() in body.lower()
    assert "Never force-push automatically" in entry
    assert "At evidence checkpoints" in entry


def test_pr_review_does_not_silently_bypass_enrolled_coordination() -> None:
    body = (ROOT / "dot_agents/skills/dbsctr-pr-review/SKILL.md").read_text()
    assert "enrolled coordinator" in body
    assert "explicit outside override" in body
    assert "integration-coordinator.md" in body
    assert "Operator-approved single PR" in body


def test_current_method_is_qualified_as_one_generation() -> None:
    assert 'CURRENT_METHOD_REVISION = "3.30"' in (ROOT / "dot_local/bin/executable_dbsctrctl").read_text()
    for path in ("dot_agents/skills/dbsctr/SKILL.md", "docs/specs/dbsctr_v3_lifecycle/PROFILE.md"):
        assert "Method Revision `3.30`" in (ROOT / path).read_text()
