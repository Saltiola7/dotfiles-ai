"""Portable shared maintenance guidance: installation and reference integrity."""
import json
from pathlib import Path
import re
import subprocess

from test_portable_distribution import ROOT, data


def test_shared_update_skill_renders_exactly_and_reapplies_without_changes(tmp_path):
    source = ROOT / "dot_agents/skills/dotfiles-ai-update"
    assert (source / "SKILL.md").is_file()
    destination = tmp_path / ".agents/skills/dotfiles-ai-update"
    command = ["chezmoi", "-S", str(ROOT), "-D", str(tmp_path), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(data()),
               "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state")]
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}
    expected = files(source)
    for _ in range(2):
        subprocess.run([*command, "apply", "--exclude", "scripts", "--parent-dirs", str(destination)],
                       check=True, text=True, capture_output=True)
        assert files(destination) == expected
    diff = subprocess.run([*command, "diff", "--exclude", "scripts", str(destination)],
                          check=True, text=True, capture_output=True)
    assert not diff.stdout


def test_update_runbook_local_links_resolve():
    runbook = ROOT / "docs/UPDATES.md"
    links = re.findall(r"\]\(([^)]+)\)", runbook.read_text())
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        assert (runbook.parent / link.split("#", 1)[0]).exists(), link
