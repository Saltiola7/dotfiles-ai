"""Complete Python audit composition and bounded shared-skill projection."""

import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

from test_opencode_control_plane import DATA, ROOT
from test_python_specialists import NAMES, inventory, markdown_destinations
from test_python_data_specialists import PYTHON, ENGINES, DATABRICKS, AUTHORED

SKILLS = ROOT / "dot_agents/skills"
BUNDLES = {"pydantic", "polars", "typer", "fastapi", "atheris", "secure-python-release-pipeline", "port-to-free-threaded-python", "architecture-patterns", "python-project-structure", "python-architecture-fitness", *PYTHON, *ENGINES, *DATABRICKS, *AUTHORED, *NAMES, "async-python-patterns", "python-modernization-review", "python-audit", "qa"}


def test_audit_composition_installs_complete_dependencies_and_preserves_unrelated_state(tmp_path):
    destination = tmp_path / "destination"
    live = destination / ".agents/skills"
    sentinel = live / "unrelated/keep.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve unrelated local edits.\n")
    targets = [live / name for name in sorted(BUNDLES)]
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(DATA),
               "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
               "--exclude", "scripts"]
    for _ in range(2):
        result = subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)],
                                capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
        for name in BUNDLES:
            assert inventory(live / name) == inventory(SKILLS / name), name
        assert sentinel.read_text() == "Preserve unrelated local edits.\n"
    expected = {Path(".agents/skills/unrelated/keep.md")}
    for target in targets:
        expected.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected
    assert subprocess.run([*command, "diff", "--recursive", *map(str, targets)],
                          check=True, capture_output=True).stdout == b""


def test_audit_local_links_resolve_with_only_its_declared_bundles(tmp_path):
    for name in BUNDLES:
        shutil.copytree(SKILLS / name, tmp_path / name)
    for document in (tmp_path / "python-audit").rglob("*.md"):
        for destination in markdown_destinations(document.read_text()):
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(tmp_path)
            assert target.is_file(), f"missing audit resource: {document}: {destination}"
