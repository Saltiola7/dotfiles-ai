"""Physical sibling lookup stays narrow across native registration symlinks."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_opencode_control_plane import ROOT


SCRIPT = ROOT / "dot_agents/skills/dbsctr/scripts/resolve_specialist.py"
spec = importlib.util.spec_from_file_location("managed_skill_discovery", SCRIPT)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


@pytest.fixture
def managed(tmp_path):
    skills = tmp_path / "physical skills"
    script = skills / "dbsctr/scripts/resolve_specialist.py"
    script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script)
    entry = skills / "mojo-gpu-fundamentals/SKILL.md"
    entry.parent.mkdir()
    entry.write_text("---\nname: mojo-gpu-fundamentals\ndescription: Device methods.\n---\n# Method\n")
    return skills, script, entry


def test_exact_physical_sibling_is_available(managed):
    _, script, entry = managed
    assert discovery.resolve_specialist("mojo-gpu-fundamentals", script_path=script) == entry.resolve()


def test_directory_symlink_registration_uses_physical_sibling(managed, tmp_path):
    skills, _, entry = managed
    registered = tmp_path / "registration/skills/dbsctr"
    registered.parent.mkdir(parents=True)
    registered.symlink_to(skills / "dbsctr", target_is_directory=True)
    assert not (registered.parent / "mojo-gpu-fundamentals/SKILL.md").exists()
    assert discovery.resolve_specialist(
        "mojo-gpu-fundamentals", script_path=registered / "scripts/resolve_specialist.py"
    ) == entry.resolve()


@pytest.mark.parametrize("name", ["", "../outside", "/tmp/outside", "nested/name", "-option", "x" * 65])
def test_invalid_names_refuse_before_lookup(name, managed):
    _, script, _ = managed
    with pytest.raises(ValueError):
        discovery.resolve_specialist(name, script_path=script)


def test_absence_does_not_search_other_skill_roots(managed, tmp_path):
    _, script, entry = managed
    entry.unlink()
    other = tmp_path / "unrelated/skills/mojo-gpu-fundamentals/SKILL.md"
    other.parent.mkdir(parents=True)
    other.write_text("---\nname: mojo-gpu-fundamentals\n---\n")
    with pytest.raises(FileNotFoundError):
        discovery.resolve_specialist("mojo-gpu-fundamentals", script_path=script)


@pytest.mark.parametrize("content", ["name: mojo-gpu-fundamentals\n", "---\nname: other\n---\n", "---\nname: mojo-gpu-fundamentals\nname: other\n---\n"])
def test_unverified_metadata_is_not_available(content, managed):
    _, script, entry = managed
    entry.write_text(content)
    with pytest.raises(LookupError):
        discovery.resolve_specialist("mojo-gpu-fundamentals", script_path=script)


def test_cli_reports_scoped_availability_and_missing_status(managed):
    _, script, entry = managed
    result = subprocess.run([sys.executable, str(script), "mojo-gpu-fundamentals"], capture_output=True, text=True)
    assert result.returncode == 0 and json.loads(result.stdout)["path"] == str(entry.resolve())
    entry.unlink()
    result = subprocess.run([sys.executable, str(script), "mojo-gpu-fundamentals"], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "unavailable"
    assert result.stderr == ""
