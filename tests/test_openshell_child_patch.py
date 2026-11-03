"""Offline patch provenance/application checks; these do not execute Linux seccomp."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).parent / "fixtures/openshell_runtime/patches"
REPOSITORY = "https://github.com/NVIDIA/OpenShell"
COMMIT = "ac7f615cd12d5cc49cb16eb1f5f10ffeb1e90f47"
TARGET = "crates/openshell-sandbox/src/linux/child_seccomp.rs"
SOURCE_BLOB = "6fc9f67f73ebda29d3dccadf8ea0ee74b898e1f5"
LICENSE_BLOB = "f13d24c3fa482d61605d600e5ac1248799bd4107"
SOURCE_BUDGET = 1024 * 1024


def metadata() -> dict:
    return json.loads((ROOT / "source.json").read_text(encoding="utf-8"))


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def git_apply(directory: Path, patch: bytes, *options: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/usr/bin/git", "apply", *options, "-"], cwd=directory, input=patch,
        capture_output=True, timeout=10, check=False,
    )


def stage_preimage(directory: Path, raw: bytes | None = None) -> Path:
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(raw if raw is not None else (ROOT / "upstream/child_seccomp.rs").read_bytes())
    return target


def test_patch_metadata_matches_pinned_source():
    record = metadata()
    assert record["schema_version"] == 1
    upstream = record["upstream"]
    assert upstream["repository"] == REPOSITORY
    assert upstream["tag"] == "v0.1.6"
    assert upstream["commit"] == COMMIT
    expected = {
        "source": (TARGET, "upstream/child_seccomp.rs", SOURCE_BLOB),
        "license": ("LICENSE", "upstream/LICENSE", LICENSE_BLOB),
    }
    for key, (path, fixture, blob) in expected.items():
        entry = upstream[key]
        assert entry["path"] == path and entry["fixture"] == fixture
        raw = (ROOT / fixture).read_bytes()
        assert entry["size_bytes"] == len(raw)
        assert entry["git_blob"] == blob == git_blob(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        assert entry["url"] == f"{REPOSITORY}/blob/{COMMIT}/{path}"
    assert upstream["license_spdx"] == "Apache-2.0"
    patch = record["patch"]
    assert patch["path"] == "child-unix-sockets.patch"
    assert patch["target"] == TARGET
    assert patch["sha256"] == hashlib.sha256((ROOT / patch["path"]).read_bytes()).hexdigest()
    assert record["experimental_identity"] == {
        "name": "openshell-v0.1.6+dotfiles-ai.child-unix-deny.1",
        "artifact_kind": "source-only-patch",
        "unchanged_upstream_release": False,
    }


def test_only_bounded_attributed_upstream_files_are_vendored():
    files = sorted(path for path in (ROOT / "upstream").rglob("*") if path.is_file())
    assert [path.name for path in files] == ["LICENSE", "child_seccomp.rs"]
    assert all(not path.is_symlink() for path in files)
    assert sum(path.stat().st_size for path in files) <= SOURCE_BUDGET
    source = (ROOT / "upstream/child_seccomp.rs").read_text(encoding="utf-8")
    assert source.startswith("// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA")
    assert "// SPDX-License-Identifier: Apache-2.0" in source.splitlines()[:3]


def test_patch_changes_only_declared_upstream_target(tmp_path):
    patch = (ROOT / "child-unix-sockets.patch").read_bytes()
    assert all(line == line.rstrip(b" \t") for line in patch.splitlines()), (
        "Patch artifact must pass repository trailing-whitespace checks"
    )
    result = git_apply(tmp_path, patch, "--numstat")
    assert result.returncode == 0, result.stderr.decode()
    added, removed, path = result.stdout.decode().strip().split("\t")
    assert int(added) > 0 and int(removed) > 0
    assert path == TARGET


def test_patch_applies_exact_preimage_and_reverses_without_drift(tmp_path):
    record = metadata()
    original = (ROOT / "upstream/child_seccomp.rs").read_bytes()
    target = stage_preimage(tmp_path, original)
    patch = (ROOT / record["patch"]["path"]).read_bytes()
    check = git_apply(tmp_path, patch, "--check", "--whitespace=error-all")
    assert check.returncode == 0, check.stderr.decode()
    assert target.read_bytes() == original, "check must not apply the patch"
    applied = git_apply(tmp_path, patch, "--whitespace=error-all")
    assert applied.returncode == 0, applied.stderr.decode()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == record["patch"]["patched_sha256"]
    assert [path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()] == [TARGET]
    duplicate = git_apply(tmp_path, patch, "--check")
    assert duplicate.returncode != 0, "already-applied patch must not be admitted twice"
    reversed_patch = git_apply(tmp_path, patch, "--reverse")
    assert reversed_patch.returncode == 0, reversed_patch.stderr.decode()
    assert target.read_bytes() == original


@pytest.mark.parametrize("missing", [False, True])
def test_patch_check_refuses_missing_or_changed_context_without_writing(tmp_path, missing):
    original = (ROOT / "upstream/child_seccomp.rs").read_bytes()
    changed = original.replace(
        b"//! not allocate while installing and deliberately leaves mediated networking",
        b"//! Unexpected upstream filter contract.", 1,
    )
    assert changed != original
    target = stage_preimage(tmp_path, changed)
    if missing:
        target.unlink()
    result = git_apply(tmp_path, (ROOT / "child-unix-sockets.patch").read_bytes(), "--check")
    assert result.returncode != 0
    if missing:
        assert not target.exists()
    else:
        assert target.read_bytes() == changed
