"""Cross-client instruction projection and activation migration contracts."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

from test_codex_distribution import load_projector, managed_source
from test_portable_distribution import chezmoi


ROOT = Path(__file__).parents[1]
CANONICAL = ROOT / ".chezmoitemplates/agent-activation.md"


def test_private_analysis_inputs_are_not_chezmoi_targets(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in (".chezmoiignore", ".chezmoidata.toml"):
        shutil.copyfile(ROOT / name, source / name)
    for directory in (".dbsctr", ".venv", ".pytest_cache"):
        private = source / directory
        private.mkdir()
        (private / "private-fixture").write_text("synthetic private input\n")
    (source / ".dbsctr/dangling").symlink_to(source / "absent")
    (source / "dot_visible").write_text("visible\n")
    result = subprocess.run(
        ["chezmoi", "--source", str(source), "--destination", str(tmp_path / "dest"),
         "--config", "/dev/null", "--config-format", "toml", "managed"],
        text=True, capture_output=True, check=True,
    )
    assert result.stdout.splitlines() == [".visible"]


@pytest.mark.parametrize("remote", [False, True])
def test_native_global_projections_have_one_content_source(remote):
    expected = CANONICAL.read_text()
    for relative in (
        ".config/opencode/AGENTS.md",
        ".config/dotfiles-ai/codex-managed/AGENTS.md",
    ):
        actual = chezmoi(
            "cat", str(Path.home() / relative), remote_user_environment=remote
        ).stdout
        assert actual == expected


@pytest.mark.parametrize("retired", [
    "@dietrichgebert/ponytail@4.10.3", "@dietrichgebert/ponytail",
])
def test_plugin_migration_preserves_other_plugins_and_is_idempotent(retired):
    script = chezmoi(
        "execute-template",
        template=(ROOT / "private_dot_config/opencode/modify_private_opencode.json.tmpl").read_text(),
    ).stdout
    retained = ["unrelated-plugin@1.2.3", "file:///fixture/local-plugin.mjs"]
    local = {"plugin": [retained[0], retired, retained[1]], "fixture": {"keep": True}}
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", script], input=json.dumps(local),
            capture_output=True, text=True, check=True,
        )
        local = json.loads(result.stdout)
        assert local["plugin"] == retained
        assert local["fixture"] == {"keep": True}


def test_fresh_configuration_does_not_install_a_prompt_injector():
    config = json.loads(chezmoi(
        "cat", str(Path.home() / ".config/opencode/opencode.json")
    ).stdout)
    assert not any("@dietrichgebert/ponytail" in item for item in config.get("plugin", []))


def test_rendered_instructions_use_existing_codex_projection_guards(tmp_path):
    source = managed_source(tmp_path)
    expected = chezmoi(
        "cat", str(Path.home() / ".config/dotfiles-ai/codex-managed/AGENTS.md")
    ).stdout
    (source / "AGENTS.md").write_text(expected)
    target = tmp_path / "codex-home"
    projector = load_projector()
    projector.project(source, target)
    before = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    projector.project(source, target)
    assert (target / "AGENTS.md").read_text() == CANONICAL.read_text()
    assert before == {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    (target / "AGENTS.md").write_text("unreviewed local edit\n")
    with pytest.raises(ValueError):
        projector.project(source, target)
    assert (target / "AGENTS.md").read_text() == "unreviewed local edit\n"


def test_style_skill_bundles_match_reviewed_inventory():
    inventory = json.loads((ROOT / "dot_agents/skills/dbsctr/references/workflow-skills.lock.json").read_text())
    assert set(inventory["skills"]) == {"caveman", "caveman-commit", "ponytail"}
    for name, entry in inventory["skills"].items():
        root = ROOT / "dot_agents/skills" / name
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        assert actual == set(entry["files"])
        assert {"SKILL.md", "LICENSE.upstream", "UPSTREAM.md"} <= actual
        assert entry["upstream"]["repository"].startswith("https://github.com/")
        for relative, expected in entry["files"].items():
            path = root / relative
            assert not path.is_symlink()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
