"""Complete specialist provenance, bounded helper behavior and exact delivery."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from test_opencode_control_plane import DATA, ROOT
from test_python_specialists import assert_bundles, digest, inventory, markdown_destinations, portable_path


SKILLS = ROOT / "dot_agents/skills"
PROVENANCE = SKILLS / "dbsctr/references/specialist-sources"
VENDORED = {
    "bash-defensive-patterns", "bats-testing-patterns", "async-python-patterns",
    "k8s-manifest-generator", "helm-chart-scaffolding", "gcloud",
    "google-cloud-recipe-auth", "gke-workload-troubleshooting", "gke-workload-identity",
    "mojo-syntax", "mojo-gpu-fundamentals", "mojo-python-interop", "new-modular-project",
}
AUTHORED = {"linux-host-diagnostics", "macos-operations", "podman-quadlet", "python-modernization-review"}
SHARED = (
    "dbsctr/SKILL.md", "dbsctr/modules/python.md", "dbsctr/modules/cloud.md",
    "dbsctr/modules/shell.md", "dbsctr/modules/mojo.md",
    "dbsctr/references/python-specialists.md", "dbsctr/references/platform-specialists.md",
    "dbsctr/references/specialist-selection.md",
)


def packages():
    result = json.loads((PROVENANCE / "sources.lock.json").read_text())
    assert result["schema_version"] == 1
    assert {p["name"] for p in result["packages"]} == VENDORED
    return result["packages"]


def test_complete_specialists_retain_immutable_origins_and_modes():
    selected = packages()
    for package in selected:
        assert package["state"] == "vendored"
        assert len(package["commit"]) == 40 and int(package["commit"], 16)
        assert package["license"] in {"MIT", "Apache-2.0", "Apache-2.0 WITH LLVM-exception"}
        assert package["changes"].strip()
        portable_path(package["upstream_path"])
        assert package["upstream_files"].keys() == package["git_blobs"].keys()
        assert {"SKILL.md", "LICENSE.upstream"} <= package["upstream_files"].keys()
        assert package["upstream_files"].keys() <= package["files"].keys()
        assert "UPSTREAM.md" in package["files"]
        assert package["modes"].keys() == package["installed_modes"].keys() == package["files"].keys()
        assert set(package["modes"].values()) <= {"100644", "100755"}
        assert set(package["installed_modes"].values()) <= {"100644", "100755"}
        attribution = (SKILLS / package["name"] / "UPSTREAM.md").read_text()
        assert package["commit"] in attribution and package["upstream_url"] in attribution
        for relative, mode in package["modes"].items():
            path = SKILLS / package["name"] / portable_path(relative)
            assert bool(path.stat().st_mode & 0o111) == (mode == "100755"), path
    assert_bundles(SKILLS, selected)


def test_adaptations_reconstruct_complete_original_blobs(tmp_path):
    for package in packages():
        target = tmp_path / package["name"]
        shutil.copytree(SKILLS / package["name"], target)
        patches = []
        for relative, expected in package["patches"].items():
            patch = PROVENANCE / portable_path(relative)
            assert digest(patch.read_bytes()) == expected
            patches.append(patch)
        for patch in reversed(patches):
            subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-i", str(patch)],
                           cwd=target, check=True, capture_output=True)
        for relative, expected in package["upstream_files"].items():
            data = (target / portable_path(relative)).read_bytes()
            assert digest(data) == expected, (package["name"], relative)
            assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == package["git_blobs"][relative]
        for patch in patches:
            subprocess.run(["patch", "--batch", "--fuzz=0", "--forward", "-p1", "-i", str(patch)],
                           cwd=target, check=True, capture_output=True)
        assert_bundles(tmp_path, [package])


def copy_scope(destination):
    for name in VENDORED | AUTHORED:
        shutil.copytree(SKILLS / name, destination / name)
    for name in SHARED:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILLS / name, target)
    for name in ("specialist-sources", "python-specialists"):
        shutil.copytree(SKILLS / "dbsctr/references" / name, destination / "dbsctr/references" / name)


def test_selected_bundles_have_closed_local_resources(tmp_path):
    copy_scope(tmp_path)
    documents = [p for name in VENDORED | AUTHORED for p in (tmp_path / name).rglob("*.md")]
    documents.extend(tmp_path / name for name in SHARED)
    for document in documents:
        for destination in markdown_destinations(document.read_text()):
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(tmp_path), (document, destination)
            assert target.exists(), (document, destination)


def test_declared_specialists_are_reachable_from_relevant_routing_surfaces():
    surfaces = [SKILLS / name for name in (
        "dbsctr/modules/shell.md", "dbsctr/modules/mojo.md", "dbsctr/modules/python.md",
        "dbsctr/references/platform-specialists.md",
    )]
    routing = "\n".join(path.read_text() for path in surfaces)
    for name in VENDORED | AUTHORED:
        assert f"`{name}`" in routing, name
        entrypoint = (SKILLS / name / "SKILL.md").read_text()
        assert entrypoint.startswith("---\n") and f"name: {name}\n" in entrypoint
    core = (SKILLS / "dbsctr/SKILL.md").read_text()
    assert "modules/shell.md" in core and "modules/mojo.md" in core


@pytest.mark.parametrize("lint_status,template_status", [(0, 0), (23, 0), (0, 29)])
def test_helm_helper_only_lints_and_renders_with_truthful_status(tmp_path, lint_status, template_status):
    chart = tmp_path / "application chart"
    chart.mkdir()
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: example\nversion: 1.0.0\ntype: application\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    calls = tmp_path / "calls"
    helm = binary / "helm"
    helm.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$HELM_CALLS"
case "$1" in
  lint) exit "$LINT_STATUS" ;;
  template) exit "$TEMPLATE_STATUS" ;;
  *) exit 91 ;;
esac
''')
    helm.chmod(0o755)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.defpath,
               HELM_CALLS=str(calls), LINT_STATUS=str(lint_status), TEMPLATE_STATUS=str(template_status))
    script = SKILLS / "helm-chart-scaffolding/scripts/validate-chart.sh"
    result = subprocess.run(["/bin/bash", str(script), str(chart)], env=env, text=True, capture_output=True)
    assert result.returncode == (lint_status or template_status), result.stdout + result.stderr
    commands = calls.read_text().splitlines()
    assert len(commands) == (1 if lint_status else 2)
    assert commands[0].startswith("lint ") and str(chart) in commands[0]
    if not lint_status:
        assert commands[1].startswith("template ") and str(chart) in commands[1]
    if result.returncode:
        assert "All validations passed" not in result.stdout



@pytest.mark.parametrize("lint_status", [0, 23])
def test_helm_library_lint_only_never_attempts_direct_render(tmp_path, lint_status):
    chart = tmp_path / "library chart"
    chart.mkdir()
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: helpers\nversion: 1.0.0\ntype: library\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    calls = tmp_path / "calls"
    helm = binary / "helm"
    helm.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$HELM_CALLS"
case "$1" in
  lint) exit "$LINT_STATUS" ;;
  template) exit 91 ;;
  *) exit 92 ;;
esac
''')
    helm.chmod(0o755)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.defpath,
               HELM_CALLS=str(calls), LINT_STATUS=str(lint_status))
    script = SKILLS / "helm-chart-scaffolding/scripts/validate-chart.sh"
    result = subprocess.run(["/bin/bash", str(script), "--lint-only", str(chart)],
                            env=env, text=True, capture_output=True)
    assert result.returncode == lint_status, result.stdout + result.stderr
    assert calls.read_text().splitlines() == [f"lint {chart}"]
    if not lint_status:
        assert "rendering remains unverified" in result.stdout
        assert "lint/render checks passed" not in result.stdout


def test_exact_delivery_preserves_unrelated_state_and_resource_modes(tmp_path):
    selected = packages()
    destination = tmp_path / "destination"
    target_root = destination / ".agents/skills"
    sentinel = target_root / "unrelated/local.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve unrelated local instructions.\n")
    targets = [target_root / n for n in sorted(VENDORED | AUTHORED)]
    targets.extend(target_root / n for n in SHARED)
    targets.append(target_root / "dbsctr/references/specialist-sources")
    targets.append(target_root / "dbsctr/references/python-specialists")
    command = ["chezmoi", "-S", str(ROOT), "-D", str(destination), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(DATA),
               "--cache", str(tmp_path / "cache"), "--persistent-state", str(tmp_path / "state"),
               "--exclude", "scripts"]
    for _ in range(2):
        subprocess.run([*command, "apply", "--parent-dirs", *map(str, targets)], check=True, capture_output=True)
        assert_bundles(target_root, selected)
        for name in AUTHORED:
            assert inventory(target_root / name) == inventory(SKILLS / name)
        for name in SHARED:
            assert (target_root / name).read_bytes() == (SKILLS / name).read_bytes()
        for package in selected:
            for name, mode in package["installed_modes"].items():
                assert bool((target_root / package["name"] / name).stat().st_mode & 0o111) == (mode == "100755")
        assert inventory(target_root / "dbsctr/references/specialist-sources") == inventory(PROVENANCE)
        assert sentinel.read_text() == "Preserve unrelated local instructions.\n"
    result = subprocess.run([*command, "diff", "--recursive", *map(str, targets)], check=True, capture_output=True)
    assert result.stdout == b""
    rendered_helper = target_root / "helm-chart-scaffolding/scripts/validate-chart.sh"
    subprocess.run(["/bin/bash", "-n", str(rendered_helper)], check=True, capture_output=True)
    expected = {sentinel.relative_to(destination)}
    for target in targets:
        if target.is_file():
            expected.add(target.relative_to(destination))
        else:
            expected.update(p.relative_to(destination) for p in target.rglob("*") if p.is_file())
    assert {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()} == expected
