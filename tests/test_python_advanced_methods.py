"""Original advanced methods retain a complete bounded distribution closure."""

import json
import subprocess
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import DATA, ROOT
from test_python_specialists import inventory, markdown_destinations

SKILLS = ROOT / "dot_agents/skills"
LOCAL_METHODS = {
    "python-process-parallelism", "python-data-contracts",
    "python-arrow-interchange", "python-mutation-testing", "python-durable-jobs",
}


def test_advanced_bundles_are_complete_and_normally_discoverable():
    for name in LOCAL_METHODS:
        files = inventory(SKILLS / name)
        assert {"SKILL.md", "agents/openai.yaml"} <= files.keys()
        assert "allow_implicit_invocation: false" not in (SKILLS / name / "agents/openai.yaml").read_text()
        for document in (SKILLS / name).rglob("*.md"):
            for link in markdown_destinations(document.read_text()):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(SKILLS) and target.is_file(), (document, link)


def test_advanced_projection_preserves_source_modes_and_unrelated_files(tmp_path):
    destination = tmp_path / "destination"
    live = destination / ".agents/skills"
    sentinel = live / "unrelated/local.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Keep operator edits.\n")
    targets = [live / name for name in sorted(LOCAL_METHODS)]
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination),
               "--config", "/dev/null", "--config-format", "toml",
               "--override-data", json.dumps(DATA), "--cache", str(tmp_path / "cache"),
               "--persistent-state", str(tmp_path / "state"), "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)], check=True, capture_output=True)
        for name in LOCAL_METHODS:
            assert inventory(live / name) == inventory(SKILLS / name)
            for relative in inventory(SKILLS / name):
                assert (live / name / relative).stat().st_mode & 0o777 == (SKILLS / name / relative).stat().st_mode & 0o777
        assert sentinel.read_text() == "Keep operator edits.\n"
    assert subprocess.run([*command, "diff", "--recursive", *map(str, targets)], check=True, capture_output=True).stdout == b""
    expected = {sentinel.relative_to(destination)}
    for target in targets:
        expected.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected


def test_advanced_methods_have_shared_and_audit_selection_paths():
    module = (SKILLS / "dbsctr/modules/python.md").read_text()
    data = (SKILLS / "dbsctr/modules/data.md").read_text()
    methods = (SKILLS / "dbsctr/references/python-stack-specialists.md").read_text()
    audit = (SKILLS / "python-audit/references/stack-specialists.md").read_text()
    for name in LOCAL_METHODS:
        assert f"`{name}`" in module and name in methods and name in audit
    for name in {"python-data-contracts", "python-arrow-interchange"}:
        assert f"`{name}`" in data
