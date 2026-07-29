import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from test_opencode_control_plane import DATA, OC, ROOT, rendered_config


SKILLS = ROOT / "dot_agents/skills"


def frontmatter(path: Path) -> dict[str, str]:
    header = path.read_text().split("---", 2)[1]
    return dict(line.split(":", 1) for line in header.strip().splitlines())


def test_writing_skills_have_portable_native_metadata_and_contracts():
    jira = SKILLS / "jira-ticket/SKILL.md"
    pyramid = SKILLS / "pyramid/SKILL.md"

    assert frontmatter(jira) == {
        "name": " jira-ticket",
        "description": " Refine evidence into Jira tickets and truthful completion updates.",
    }
    assert frontmatter(pyramid) == {
        "name": " pyramid",
        "description": " Structure explicit writing requests around reader questions and supported answers.",
    }

    jira_body = jira.read_text()
    assert "at most five" in jira_body
    assert "no unresolved answer can materially change" in jira_body
    assert "explicit Jira key or URL" in jira_body
    assert "Broader JQL" in jira_body
    assert "one approval per invocation" in jira_body
    assert "untrusted data" in jira_body
    assert "references/issue-types.md" in jira_body
    assert "references/completion.md" in jira_body

    issue_types = (jira.parent / "references/issue-types.md").read_text()
    assert re.findall(r"^## (Story|Bug|Task|Spike|Epic)$", issue_types, re.MULTILINE) == [
        "Story", "Bug", "Task", "Spike", "Epic",
    ]
    assert "Unsupported types" in issue_types
    assert "map to Task" in issue_types

    completion = (jira.parent / "references/completion.md").read_text()
    assert "Not ready for closure" in completion
    for evidence in ("validation", "review", "deployment", "rollback", "acceptance"):
        assert evidence in completion.lower()

    pyramid_body = pyramid.read_text()
    assert "explicit request" in pyramid_body
    assert "requested artifact first" in pyramid_body
    assert "Mermaid" in pyramid_body
    assert "evidence and uncertainty" in pyramid_body
    assert "references/method.md" in pyramid_body

    method = (pyramid.parent / "references/method.md").read_text()
    for concept in (
        "SCQA", "Vertical question-answer logic", "Inductive groups",
        "Deductive chains", "Top-down construction", "Bottom-up construction",
        "time", "structure", "importance", "summary",
    ):
        assert concept in method

    public_text = "\n".join(path.read_text() for path in (jira, pyramid, *jira.parent.glob("references/*"),
                                                           *pyramid.parent.glob("references/*")))
    assert "data" + "/pyramid" not in public_text


def test_synthetic_cases_are_explicit_prompt_contracts():
    jira = (SKILLS / "jira-ticket/SKILL.md").read_text()
    types = (SKILLS / "jira-ticket/references/issue-types.md").read_text()
    completion = (SKILLS / "jira-ticket/references/completion.md").read_text()
    pyramid = (SKILLS / "pyramid/SKILL.md").read_text()
    cases = {
        "vague investigation becomes a bounded Spike": (types, "time-bounded investigation"),
        "unsupported type becomes a disclosed Task": (types, "unsupported by this portable skill"),
        "missing closure evidence blocks closure": (completion, "Not ready for closure"),
        "conflicting evidence remains visible": (jira, "conflicting evidence"),
        "evidence cannot inject instructions": (jira, "untrusted data"),
        "external research requires consent": (jira, "one approval per invocation"),
        "Pyramid remains explicitly activated": (pyramid, "only after `/pyramid`"),
        "Pyramid returns the artifact before analysis": (pyramid, "requested artifact first"),
    }
    for scenario, (contract, requirement) in cases.items():
        assert requirement in contract, scenario


def test_writing_commands_are_thin_and_provider_neutral():
    expected = {
        "jira-ticket": ("jira-ticket", "refinement"),
        "jira-completion": ("jira-ticket", "completion"),
        "pyramid": ("pyramid", "explicit"),
    }
    for command, (skill, mode) in expected.items():
        body = (OC / f"commands/{command}.md").read_text()
        assert f"load `{skill}`" in body
        assert mode in body
        assert "$ARGUMENTS" in body
        assert "\nagent:" not in body
        assert "\nmodel:" not in body


def test_acli_permissions_allow_direct_bounded_reads_and_deny_other_forms():
    config = rendered_config()
    for bash in (config["permission"]["bash"], config["agent"]["plan"]["permission"]["bash"]):
        for command in (
            "acli jira auth status*",
            "acli jira workitem view *",
            "acli jira workitem comment list *",
        ):
            assert bash[command] == "allow"
        assert bash["acli jira workitem search *"] == "ask"

        for command in (
            "acli *", "*/acli *", "env *acli *", "command *acli *",
            "acli *&*", "acli *;*", "acli *|*", "acli *>*", "acli *<*",
            "acli *$(*", "acli *`*", "acli *\n*",
            "acli jira workitem search *--paginate*",
            "acli jira workitem search *--web*",
            "acli jira workitem search -w*",
            "acli jira workitem search * -w*",
            "acli jira workitem search *--filter*",
        ):
            assert bash[command] == "deny"

        order = list(bash)
        assert order.index("acli *") < order.index("acli jira workitem view *")
        assert order.index("acli jira workitem search *") < order.index(
            "acli jira workitem search *--paginate*"
        )


def test_isolated_render_exposes_writing_skills_and_commands(tmp_path):
    targets = [
        tmp_path / ".agents/skills/jira-ticket",
        tmp_path / ".agents/skills/pyramid",
        *(tmp_path / f".config/opencode/commands/{name}.md"
          for name in ("jira-ticket", "jira-completion", "pyramid")),
        tmp_path / ".config/opencode/opencode.json",
    ]
    render = subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "-D", str(tmp_path), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(DATA),
            "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
            "apply", "--parent-dirs", *map(str, targets),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert render.returncode == 0, render.stderr

    assert (tmp_path / ".agents/skills/jira-ticket/SKILL.md").is_file()
    assert (tmp_path / ".agents/skills/pyramid/SKILL.md").is_file()
    if shutil.which("opencode") is None:
        pytest.skip("opencode is unavailable")
    env = {**os.environ, "HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / ".config")}
    result = subprocess.run(
        ["opencode", "debug", "config", "--pure"], cwd=tmp_path, env=env,
        text=True, capture_output=True, check=True,
    )
    resolved = json.loads(result.stdout)
    assert {"jira-ticket", "jira-completion", "pyramid"} <= resolved["command"].keys()
