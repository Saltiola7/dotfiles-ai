import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "dot_agents/skills"
COMMANDS = ROOT / "private_dot_config/opencode/commands"


def text(path: Path | str) -> str:
    return (ROOT / path).read_text() if isinstance(path, str) else path.read_text()


def test_public_lifecycle_commands_are_unversioned_and_thin():
    expected = {"discovery": "discovery", "dbsctr": "dbsctr", "qa": "qa",
                "dbsctr-review": "dbsctr-review", "incident": "dbsctr-incident"}
    for command, skill in expected.items():
        body = text(COMMANDS / f"{command}.md")
        assert f"skill tool to load `{skill}`" in body
        assert "Do not answer from memory" in body
        if command == "discovery":
            assert "\nagent: discovery-coordinator\n" in body
        else:
            assert "\nagent:" not in body

    assert not (COMMANDS / "discovery2.md").exists()
    assert not (COMMANDS / "dbsctr2.md").exists()


def test_v3_skills_use_unversioned_names_and_full_lifecycle():
    discovery = text(SKILLS / "discovery/SKILL.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")

    assert "name: discovery" in discovery
    assert "trigger: /discovery" in discovery
    assert "Engineering Profile" in discovery
    assert "Gate Ledger" in discovery
    assert "V3.2 applicability plan" not in discovery
    assert "DBSCTR V3 applicability plan" in discovery
    for term in ("Initiative", "MANIFEST.json", "PROFILE.md", "initiative-check",
                 "initiative-receipt", "exact user approval"):
        assert term in discovery

    coordinator = text("private_dot_config/opencode/agents/discovery-coordinator.md")
    assert "mode: primary" in coordinator
    assert '"docs/**": allow' in coordinator
    assert '"*": deny' in coordinator
    assert "bash: allow" in coordinator
    assert "native CLI, API, or notebook kernel" in coordinator
    assert "shell proxy when a direct interface exists" in coordinator
    assert "keep governed private result bodies local" in coordinator
    assert "dbsctr_initiative_launch: ask" in coordinator
    assert "explore-openai: allow" in coordinator
    assert "scout-openai: allow" in coordinator
    for agent in ("explore-openai", "scout-openai"):
        assert "bash: deny" in text(f"private_dot_config/opencode/agents/{agent}.md")

    assert "name: dbsctr" in dbsctr
    assert "trigger: /dbsctr" in dbsctr
    for term in (
        "Development Kernel",
        "Review/Integrate",
        "Release",
        "Deploy",
        "Operate",
        "Maintain/Retire",
        "accepted_risk",
    ):
        assert term in dbsctr


def test_v311_review_skill_is_private_bounded_and_approval_only():
    review = text(SKILLS / "dbsctr-review/SKILL.md")
    for term in (
        "dbsctr_review", "dbsctr_review_complete", "blocked", "abandoned", "dormant", "snapshot", "unknown",
        "raw transcript", "sanitized", "separate DBSCTR cycle", "review marker", "90 days", "tombstones",
    ):
        assert term.lower() in review.lower()
    assert "same snapshot and both row ceilings" in review.lower()
    assert "digest, snapshot" in review.lower()
    assert "without a matched" in review.lower() and "record are unknown" in review.lower()
    assert "never perform automatic remediation" in review.lower()

    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    assert "DVC-relevant" in dbsctr
    assert "original checkout" in dbsctr
    assert "explicit project policy" in dbsctr.lower()


def test_v339_incident_skill_is_fork_bounded_and_separately_remediated():
    incident = text(SKILLS / "dbsctr-incident/SKILL.md")
    review = text(SKILLS / "dbsctr-review/SKILL.md")
    for term in ("dbsctr_incident_scan", "dbsctr_incident_register", "INCIDENT:",
                 "defect", "friction", "behavior_gap", "capability_idea",
                 "root-cause", "separate DBSCTR cycle", "verified activation"):
        assert term.lower() in incident.lower()
    assert review.lower().index("registered incidents") < review.lower().index("incident signals")
    assert review.lower().index("incident signals") < review.lower().index("review candidates")
    assert "never perform automatic remediation" in review.lower()


def test_v2_is_archived_and_not_deployable():
    archive = ROOT / "docs/_archive/opencode/skills/v2"
    assert (archive / "discovery2/SKILL.md").exists()
    assert (archive / "dbsctr2/SKILL.md").exists()
    assert {
        path.name for path in (archive / "dbsctr2/modules").glob("*.md")
    } == {"data.md", "cloud.md", "ml.md", "analytics_references.md"}
    assert not any(path.is_file() for path in (SKILLS / "discovery2").rglob("*"))
    assert not any(path.is_file() for path in (SKILLS / "dbsctr2").rglob("*"))

    removals = [line for line in text(".chezmoiremove").splitlines() if not line.startswith("#")]
    assert not [path for path in removals if "discovery2" in path or "dbsctr2" in path]


def test_current_distribution_profile_names_hermes_orchestration():
    spec = text("docs/specs/dotfiles_ai_distribution/README.md")
    assert "opt-in Hermes R&D orchestration" in spec
    assert "opt-in native R&D scheduling" not in spec


def test_v3_module_registry_is_extensible_and_normalized():
    modules = SKILLS / "dbsctr/modules"
    references = SKILLS / "dbsctr/references"
    expected = {"python.md", "security.md", "data.md", "cloud.md", "ml.md", "analytics.md", "web.md"}
    assert {path.name for path in modules.glob("*.md")} == expected
    assert {path.name for path in references.glob("*.md")} == {
        "data.md",
        "cloud.md",
        "ml.md",
        "analytics.md",
        "python.md",
            "semantic-audit.md",
            "spec-visuals.md",
            "web.md",
            "openai.md",
            "anthropic.md",
        }

    for path in modules.glob("*.md"):
        body = path.read_text()
        for heading in (
            "## Applicability",
            "## Engineering Profile Extensions",
            "## Required Outcomes",
            "## Conditional Controls",
            "## Validation Capabilities",
            "## Lifecycle Obligations",
        ):
            assert heading in body, f"{path}: missing {heading}"
        for label in ("REQUIRED", "CONDITIONAL", "PROJECT POLICY", "EXAMPLE"):
            assert label in body, f"{path}: missing {label} guidance"


def test_project_specific_module_rules_are_not_normative():
    module_text = "\n".join(
        path.read_text() for path in (SKILLS / "dbsctr/modules").glob("*.md")
    )
    for banned in (
        "Every IaC component returns a typed dataclass",
        "All three layers required",
        "Typer CLI alongside Prefect",
        "F1 (macro) | ≥ 0.68",
        "+6% accuracy",
    ):
        assert banned not in module_text


def test_qa_accepts_v3_capabilities_without_breaking_scoped_mode():
    qa = text(SKILLS / "qa/SKILL.md")
    for term in (
        "Engineering Profile",
        "Capability Requirement",
        "capability gap",
        "accepted_risk",
        "scoped",
        "full",
    ):
        assert term in qa
    assert "do not install tools" in qa


def test_global_routing_defaults_to_unversioned_v3():
    agents = text("private_dot_config/opencode/AGENTS.md")
    assert "Use `dbsctr`" in agents
    assert "`discovery` until no unresolved question can materially change implementation" in agents
    assert "dbsctr2" not in agents.lower()
    assert "discovery2" not in agents.lower()
    assert "Keep `/dbsctr` and `/discovery` unchanged" not in agents


def test_ci_and_specs_cover_lifecycle_sources():
    workflow = text(".github/workflows/test.yml")
    assert 'python-version: ["3.12", "3.13", "3.14"]' in workflow
    assert "push:\n    branches: [main]" in workflow
    assert "pull_request:\n\n" in workflow
    assert "uv run --group test pytest" in workflow

    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    for term in ("Engineering Profile", "Gate Ledger", "MethodWeave", "RigorWeave"):
        assert term in spec


def test_dbsctr_commits_gate_increments_and_pushes_completed_cycles():
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    for term in (
        "Gate Commit",
        "Final Push",
        "At cycle start",
        "pre-cycle ahead commits",
        "without another confirmation",
        "Never force-push automatically",
        "dvc push",
        "worktree is clean",
    ):
        assert term in dbsctr

    agents = text("private_dot_config/opencode/AGENTS.md")
    assert "coherent Gate Commits" in agents
    assert "one Final Push" in agents


def test_v31_separates_gate_dimensions_and_scales_artifacts():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    discovery = text(SKILLS / "discovery/SKILL.md")
    qa = text(SKILLS / "qa/SKILL.md")

    for term in ("Gate Applicability", "Gate Result", "Gate Exception", "Cycle Record", "Method Revision"):
        assert term in spec
        assert term in dbsctr
    assert "Git common directory" in dbsctr
    assert "Every cycle reviews README and CHANGELOG" in dbsctr
    assert "ticket" not in dbsctr.lower()
    assert "never creates, reads, updates, or requires PM Kernel tickets" in discovery
    assert "no unresolved question can materially change" in discovery
    assert "95%" not in discovery
    assert "structured" in qa.lower() and "Gate Result" in qa


def test_v31_templates_match_artifact_and_gate_contracts():
    spec_template = text("docs/specs/_template_spec.md")
    changelog_template = text("docs/specs/_template_changelog.md")
    assert "Applicability | Result" in spec_template
    assert "Artifact Review" in spec_template
    assert "Gate commits" in changelog_template


def test_v334_normative_specs_require_accessible_visual_evidence():
    policy = text(SKILLS / "dbsctr/references/spec-visuals.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    discovery = text(SKILLS / "discovery/SKILL.md")
    template = text("docs/specs/_template_spec.md")
    excluded = {"CHANGELOG.md", "ROADMAP.md", "PROFILE.md", "_template_changelog.md"}
    specs = sorted(path for path in (ROOT / "docs/specs").rglob("*.md") if path.name not in excluded)

    for term in ("Visual Evidence Plan", "Text Equivalent", "quantitative", "not_applicable"):
        assert term in policy
        assert term in template
    assert "references/spec-visuals.md" in dbsctr
    assert "../dbsctr/references/spec-visuals.md" in discovery

    for path in specs:
        body = text(path)
        assert "## Visual Evidence" in body, path.relative_to(ROOT)
        assert "Quantitative" in body, path.relative_to(ROOT)
        for diagram in re.findall(r"```mermaid\n(.*?)```", body, re.DOTALL):
            assert "accTitle:" in diagram, path.relative_to(ROOT)
            assert "accDescr:" in diagram, path.relative_to(ROOT)


def test_v31_helper_and_reviewer_surfaces_exist():
    helper = ROOT / "dot_local/bin/executable_dbsctrctl"
    reviewer = ROOT / "private_dot_config/opencode/agents/reviewer-openai.md"
    assert helper.exists()
    assert reviewer.exists()
    assert "mode: subagent" in reviewer.read_text()
    assert "edit: deny" in reviewer.read_text()


def test_v32_requires_planned_ordered_monotonic_cycles():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    discovery = text(SKILLS / "discovery/SKILL.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    roadmap = text("docs/specs/dbsctr_v3_lifecycle/ROADMAP.md")

    for term in ("Method Revision `3.28`", "applicability plan", "predecessor", "V3.1"):
        assert term in dbsctr
    assert "schema version `1`" in spec
    assert "dbsctrctl start --plan PATH" in discovery
    assert ".dbsctr/plans/" in discovery and ".dbsctr/plans/" in dbsctr
    assert "schema_version" in helper and "raise-risk" in helper
    for milestone in ("V3.2", "V3.3", "V3.4", "V3.5", "V3.6"):
        assert milestone in roadmap


def test_v33_uses_common_worktree_registry_and_delivery_lock():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    for term in ("<git-common-dir>/dbsctr/cycles/", "worktrees/<worktree-id>/active", "Delivery Target Lock"):
        assert term in spec
    assert "--git-common-dir" in helper
    assert "LOCK_EX | fcntl.LOCK_NB" in helper


def test_v34_automates_isolation_and_safe_cleanup():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    for term in ("dbsctrctl begin", "24 hours", "unknown ahead commits"):
        assert term in spec
    assert "commands.add_parser(\"begin\")" in helper
    assert "commands.add_parser(\"cleanup\")" in helper
    assert "dbsctrctl begin --plan" in dbsctr


def test_v35_keeps_opencode_and_herdr_as_adapters():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    for term in ("dbsctr_status", "dbsctr_begin", "execution/visibility plane", "pane history disabled"):
        assert term in spec
    assert "Typed OpenCode tools are argument-safe adapters" in dbsctr


def test_v36_audit_is_fixed_commit_report_only_and_distinct_from_qa():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    agents = text("private_dot_config/opencode/AGENTS.md")
    for term in ("report-only", "one Git commit", "dbsctr_audit", "does not duplicate `/qa`"):
        assert term in spec
    assert "Lifecycle Reconciliation Audit" in dbsctr
    assert "Never infer" in dbsctr
    assert 'Treat "DBSCTR audit" as a report-only' in agents


def test_v362_uses_validated_build_begin_authorization_and_method_revision_compatibility():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    tools = text("private_dot_config/opencode/tools/dbsctr.ts")
    assert "CURRENT_METHOD_REVISION = \"3.28\"" in helper
    assert '"method_revision": CURRENT_METHOD_REVISION' in helper
    begin = tools.partition("export const begin = tool({")[2].partition("export const initiative_launch = tool({")[0]
    assert "context.ask" not in begin
    assert "before any `beginCycle`" in spec
    assert "schema-less/schema-1/schema-2" in spec
    assert "standing authorization for validated Build-primary" in dbsctr
    assert "explicit Initiative mode" in text("private_dot_config/opencode/AGENTS.md")


def test_v326_inventory_and_batch_cleanup_remain_explicit_and_dvc_efficient():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    for term in ("Worktree Inventory", "Cleanup Candidate", "cleanup --completed", "reflink,copy"):
        assert term in spec
    assert 'commands.add_parser("worktree-list")' in helper
    assert 'cleanup_target.add_argument("--completed"' in helper


def test_stale_cycle_retirement_is_explicit_and_preserves_dirty_work():
    helper = (ROOT / "dot_local/bin/executable_dbsctrctl").read_text()
    spec = (ROOT / "docs/specs/dbsctr_v3_lifecycle/STALE_CYCLE_RETIREMENT.md").read_text()
    assert 'commands.add_parser("cycle-retire")' in helper
    assert 'commands.add_parser("cycle-retire-worktree")' in helper
    assert "refusing to retire a dirty cycle worktree" in helper
    assert "preserves the cycle record" in spec.lower() or "preserve the cycle record" in spec.lower()


def test_v324_profiles_explicit_spans_and_keeps_dispatch_primary_mediated():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    tools = text("private_dot_config/opencode/tools/dbsctr.ts")
    for term in ("Phase Span", "Execution DAG", "90 days", "partial", "10 percent"):
        assert term in spec
    for term in ("dbsctr_phase_span", "dbsctr_execution_dag", "primary", "serial"):
        assert term in dbsctr
    assert "does not dispatch" in dbsctr
    assert 'commands.add_parser("phase-span")' in helper
    assert 'commands.add_parser("phase-report")' in helper
    assert 'commands.add_parser("execution-dag")' in helper
    assert 'commands.add_parser("execution-benchmark")' in helper
    assert "export const phase_span" in tools
    assert "export const execution_dag" in tools


def test_v316_review_skill_has_separate_private_history_and_replay_modes():
    review = text(SKILLS / "dbsctr-review/SKILL.md").lower()
    for term in ("inbox", "history", "replay", "standing", "privacy", "raw transcript", "tombstone"):
        assert term in review
    assert "dbsctr_review_history" in review
    assert "dbsctr_review_history_save" in review
    assert "builder" in review and "denied" in review


def test_v310_product_intent_and_web_ui_are_conditional_and_accessible():
    discovery = text(SKILLS / "discovery/SKILL.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    web = text(SKILLS / "dbsctr/modules/web.md")
    references = text(SKILLS / "dbsctr/references/web.md")
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")

    assert "docs/specs/<context>/PRODUCT.md" in discovery
    assert "Do not create synthetic Product Intent" in discovery
    assert "Only create or" in discovery and "when no existing artifact satisfies" in discovery
    assert "Never duplicate an existing authoritative product artifact" in discovery
    assert "selected authoritative artifact records" in spec
    assert "creates `PRODUCT.md` only when no existing artifact satisfies it" in spec
    assert "modules/web.md" in dbsctr
    assert "WCAG 2.2 AA" in web
    for outcome in ("keyboard", "focus", "semantics", "contrast", "zoom", "reflow", "target size", "reduced-motion"):
        assert outcome in web
    assert "standard-defined exception" in web
    assert "Automated checks and screenshots are supporting evidence only" in web
    assert "Playwright" in references and "Flowbite Pro" in references
    assert "Playwright" not in web and "Flowbite Pro" not in web
    assert "Configure an MCP server only" in references and "within that project" in references
    assert "Never create or modify user-global" in references
    assert "MCP output is a tool hint, not source authority or gate evidence" in references


def test_v37_inspection_is_fixed_commit_bounded_and_read_only():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    tools = text("private_dot_config/opencode/tools/dbsctr.ts")
    for term in ("Fixed-Commit Inspection Contract", "`read`, `tree`", "`search`, and", "`object` actions", "dirty overlay"):
        assert term in spec
    assert 'commands.add_parser("inspect")' in helper
    assert "INSPECT_RESPONSE_HARD" in helper
    assert "export const inspect = tool({" in tools


def test_v38_retains_secret_safe_evidence_and_conditional_python_reference():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    helper = text("dot_local/bin/executable_dbsctrctl")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    python = text(SKILLS / "dbsctr/references/python.md")
    for term in ("schema version `3`", "record-evidence", "withheld", "no_content", "256 KiB"):
        assert term in spec
    assert 'commands.add_parser("record-evidence")' in helper
    for term in ("op://", "op run", "Pydantic Settings", "SecretStr", "fake environment"):
        assert term in python
    assert "record-evidence GATE" in dbsctr


def test_v39_semantic_reconciliation_is_fixed_commit_report_only_and_authority_ordered():
    spec = text("docs/specs/dbsctr_v3_lifecycle/README.md")
    dbsctr = text(SKILLS / "dbsctr/SKILL.md")
    protocol = text(SKILLS / "dbsctr/references/semantic-audit.md")
    classifications = ("consistent", "confirmed_drift", "stale_evidence", "missing_artifact",
                       "authority_conflict", "historical_unlabelled", "unverified_claim", "out_of_scope")
    for term in classifications:
        assert term in protocol
        assert protocol.count(f"- `{term}`:") == 1
    for term in ("report-only", "resolved commit", "Absence of contradiction", "private machine paths",
                 "inventory_findings", "public=false", "authoritative=false"):
        assert term in spec
    assert "references/semantic-audit.md" in dbsctr
    assert "Graph paths never prove a claim" in protocol
    assert "never project authority" in protocol and "publishable source" in protocol
    assert "first matching rule" in protocol
    assert "dbsctrctl inspect" in protocol and "never read its filesystem" in protocol
    assert "never read withheld content" in protocol
    assert "Keep `/qa full` separate" in protocol
    for boundary in ("never changes files", "lifecycle state", "without explicit approval"):
        assert boundary in protocol


def test_dbsctr_backlog_is_report_only_priority_queue():
    backlog = text(SKILLS / "dbsctr-backlog/SKILL.md")
    assert "P2/P3" in backlog and "state is `claimed`" in backlog
    assert "This skill is report-only" in backlog
    for term in ("Do not reprioritize", "advance", "recover", "abandon", "launch", "merge"):
        assert term in backlog
