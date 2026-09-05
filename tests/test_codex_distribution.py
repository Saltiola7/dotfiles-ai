import importlib.machinery
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import tarfile

import pytest


ROOT = Path(__file__).parents[1]
PROJECTOR = ROOT / "dot_local/bin/executable_codex-project"
ARCHIVE = ROOT / "dot_local/bin/executable_codex-archive"
ROLLBACK = ROOT / "dot_local/bin/executable_codex-rollback"
UPDATER = ROOT / "dot_local/bin/executable_codex-update-all"


def load_projector():
    loader = importlib.machinery.SourceFileLoader("codex_project", str(PROJECTOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_archive():
    loader = importlib.machinery.SourceFileLoader("codex_archive", str(ARCHIVE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_rollback():
    loader = importlib.machinery.SourceFileLoader("codex_rollback", str(ROLLBACK))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_updater():
    loader = importlib.machinery.SourceFileLoader("codex_update", str(UPDATER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def managed_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "agents/nested").mkdir(parents=True)
    (source / "config.toml").write_text("model = 'managed'\n")
    (source / "AGENTS.md").write_text("managed instructions\n")
    (source / "agents/build.toml").write_text("name = 'build'\n")
    (source / "agents/nested/review.toml").write_text("name = 'review'\n")
    return source


def test_projector_publishes_only_digest_owned_files(tmp_path: Path) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    target.mkdir(parents=True, mode=0o700)
    private = target / "auth.json"
    private.write_text("private")

    helper.project(source, target)

    manifest = json.loads((target / ".dotfiles-ai-managed.json").read_text())
    assert sorted(manifest["files"]) == [
        "AGENTS.md", "agents/build.toml", "agents/nested/review.toml", "config.toml",
    ]
    assert private.read_text() == "private"
    assert not (target / ".dotfiles-ai-journal.json").exists()
    assert not (target / ".dotfiles-ai-staging").exists()


def test_projector_rejects_unmanaged_changes_and_symlinks(tmp_path: Path) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    target.mkdir(parents=True, mode=0o700)
    (target / "config.toml").write_text("unmanaged")
    (target / "config.toml").chmod(0o600)

    with pytest.raises(ValueError, match="unmanaged target"):
        helper.project(source, target)

    (target / "config.toml").unlink()
    (target / "config.toml").symlink_to(source / "config.toml")
    with pytest.raises(ValueError, match="symlink"):
        helper.project(source, target)


def test_projector_rejects_modified_owned_file(tmp_path: Path) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    (target / "config.toml").write_text("local change")

    with pytest.raises(ValueError, match="managed target changed"):
        helper.project(source, target)

    (target / "config.toml").write_text("model = 'managed'\n")
    (target / "config.toml").chmod(0o644)
    with pytest.raises(ValueError, match="unsafe managed target"):
        helper.project(source, target)


def test_projector_recovers_interrupted_transaction(tmp_path: Path, monkeypatch) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    (source / "config.toml").write_text("model = 'updated'\n")
    original = helper.publish_entry
    calls = 0

    def interrupted(*args):
        nonlocal calls
        calls += 1
        original(*args)
        if calls == 1:
            raise RuntimeError("interrupted")

    monkeypatch.setattr(helper, "publish_entry", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        helper.project(source, target)
    monkeypatch.setattr(helper, "publish_entry", original)

    helper.project(source, target)

    assert (target / "config.toml").read_text() == "model = 'updated'\n"
    assert not (target / ".dotfiles-ai-journal.json").exists()


def test_projector_rejects_git_and_symlinked_state_roots(tmp_path: Path) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    repository = tmp_path / "repository"
    (repository / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="Git worktree"):
        helper.project(source, repository / "state/codex")

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        helper.project(source, link / "codex")


def test_projector_rejects_unsafe_metadata_and_home_modes(tmp_path: Path) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    manifest = target / ".dotfiles-ai-managed.json"
    manifest.unlink()
    manifest.symlink_to(target / "missing")
    with pytest.raises(ValueError, match="ownership manifest"):
        helper.project(source, target)

    manifest.unlink()
    target.chmod(0o755)
    with pytest.raises(ValueError, match="CODEX_HOME"):
        helper.validate_home(target)


def test_projector_validates_private_release_lock(tmp_path: Path) -> None:
    helper = load_projector()
    executable = tmp_path / "libexec/codex"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nprintf 'codex-cli 0.153.3\\n'\n")
    executable.chmod(0o700)
    lock = tmp_path / "release-lock.json"
    lock.write_text(json.dumps({
        "schema_version": 1, "channel": "stable", "release": "0.153.3",
        "tag": "rust-v0.153.3", "platform": "darwin-aarch64",
        "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "target_count": 1, "targets_digest": hashlib.sha256(b"targets").hexdigest(),
        "assets": load_updater().validate_release(release_payload())["assets"],
        "validator_revision": "codex-release-validator-1", "previous": None,
    }))
    lock.chmod(0o600)

    assert helper.resolve_managed(lock, executable) == executable

    executable.write_text("changed")
    with pytest.raises(ValueError, match="executable"):
        helper.resolve_managed(lock, executable)


def release_payload(version="0.153.3"):
    assets = []
    for name in (
        "codex-aarch64-apple-darwin.tar.gz",
        "codex-aarch64-unknown-linux-musl.tar.gz",
        "codex-x86_64-unknown-linux-musl.tar.gz",
    ):
        assets.append({
            "name": name, "size": 6, "digest": "sha256:" + "a" * 64,
            "browser_download_url":
                f"https://github.com/openai/codex/releases/download/rust-v{version}/{name}",
        })
    return {"name": version, "tag_name": f"rust-v{version}", "draft": False,
            "prerelease": False, "assets": assets}


def test_rolling_release_metadata_is_closed_and_platform_complete() -> None:
    helper = load_updater()
    value = helper.validate_release(release_payload())

    assert value["release"] == "0.153.3"
    assert set(value["assets"]) == {"darwin-aarch64", "linux-aarch64", "linux-x86_64"}
    broken = release_payload()
    broken["assets"].pop()
    with pytest.raises(helper.UpdateError):
        helper.validate_release(broken)
    with pytest.raises(helper.UpdateError):
        helper.validate_release({**release_payload(), "prerelease": True})


def test_rolling_stage_lock_binds_extracted_binary_and_activates(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    monkeypatch.setattr(helper, "download", lambda _asset, path: path.write_bytes(b"archive"))

    def extract(_archive, destination, _expected):
        destination.write_text("#!/bin/sh\nprintf 'codex-cli 0.153.3\\n'\n")
        destination.chmod(0o700)

    monkeypatch.setattr(helper, "extract", extract)
    monkeypatch.setattr(helper, "validate_binary", lambda *_args: None)
    candidate = helper.validate_release(release_payload())

    assert helper.stage(candidate) == "staged"
    staged_lock = json.loads((root / "candidate-lock.json").read_text())
    assert staged_lock["binary_sha256"] == hashlib.sha256(
        (root / "candidate-codex").read_bytes()).hexdigest()
    assert staged_lock["platform"] == "darwin-aarch64"
    assert stat.S_IMODE((root / "candidate-lock.json").stat().st_mode) == 0o600
    assert helper.activate() == "updated"
    assert helper.read_lock()["release"] == "0.153.3"
    assert helper.healthy(helper.read_lock())


def test_same_release_restages_when_fleet_attestation_changes(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    candidate = helper.validate_release(release_payload())
    current = helper.generation(candidate, "darwin-aarch64", "b" * 64)
    current["previous"] = None
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    monkeypatch.setattr(helper, "read_lock", lambda *_args: current)
    monkeypatch.setattr(helper, "healthy", lambda *_args: True)
    monkeypatch.setattr(helper, "download", lambda _asset, path: path.write_bytes(b"archive"))

    def extract(_archive, destination, _expected):
        destination.write_bytes(b"candidate")
        destination.chmod(0o700)

    monkeypatch.setattr(helper, "extract", extract)
    monkeypatch.setattr(helper, "validate_binary", lambda *_args: None)
    digest = hashlib.sha256(helper.canonical(["host", "workspace-a"])).hexdigest()

    assert helper.stage(candidate, root, binary, 2, digest) == "staged"
    lock = json.loads((root / "candidate-lock.json").read_text())
    assert lock["target_count"] == 2
    assert lock["targets_digest"] == digest


def test_rolling_update_soft_fails_only_with_healthy_active_release(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    binary.write_text("#!/bin/sh\nprintf 'codex-cli 0.153.3\\n'\n")
    binary.chmod(0o700)
    generation = {
        "schema_version": 1, "channel": "stable", "release": "0.153.3",
        "tag": "rust-v0.153.3", "platform": "darwin-aarch64",
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "target_count": 1,
        "targets_digest": hashlib.sha256(helper.canonical(["local"])).hexdigest(),
        "assets": helper.validate_release(release_payload())["assets"],
        "validator_revision": helper.VALIDATOR_REVISION, "previous": None,
    }
    helper.atomic_json(root / "release-lock.json", generation)
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    monkeypatch.setattr(helper, "fetch_release", lambda: (_ for _ in ()).throw(
        helper.UpdateError("metadata_unavailable")))

    assert helper.local_update() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "retained"
    binary.unlink()
    assert helper.local_update() == 1


def test_host_rolling_update_stages_all_guests_before_activation(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls = []
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    health = iter((False, True))
    monkeypatch.setattr(helper, "healthy", lambda *_args: next(health))
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])
    def staged(candidate, root, _binary, target_count, targets_digest):
        calls.append("stage-host")
        value = helper.generation(
            candidate, "darwin-aarch64", "b" * 64, target_count, targets_digest,
        )
        value["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", value)
        return "staged"

    monkeypatch.setattr(helper, "stage", staged)
    stages = {}
    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append(f"{action}-{workspace}")
        if action == "stage":
            stages[workspace] = stages.get(workspace, 0) + 1
            return "staged" if stages[workspace] == 1 else "current"
        return "current"
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs:
                        calls.append("activate-host") or "updated")

    assert helper.host_update() == 0

    assert calls == [
        "stage-host", "stage-workspace-a", "stage-workspace-b",
        "activate-workspace-a", "activate-workspace-b", "activate-host",
        "stage-workspace-a", "stage-workspace-b",
        "activate-workspace-a", "activate-workspace-b",
    ]
    assert json.loads(capsys.readouterr().out)["target_count"] == 3


def test_host_activation_oserror_rolls_back_every_attempted_guest(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls = []
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    monkeypatch.setattr(helper, "healthy", lambda *_args: False)
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])

    def staged(candidate, root, _binary, target_count, targets_digest):
        value = helper.generation(candidate, "darwin-aarch64", "b" * 64,
                                  target_count, targets_digest)
        value["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", value)
        return "staged"

    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append((action, workspace))
        if action == "stage":
            return "staged"
        if action == "activate" and workspace == "workspace-b":
            raise OSError("lost VM response")
        return "current"

    monkeypatch.setattr(helper, "stage", staged)
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs: "updated")
    monkeypatch.setattr(helper, "rollback", lambda *_args: None)

    assert helper.host_update() == 1
    assert calls[-2:] == [("rollback", "workspace-b"), ("rollback", "workspace-a")]
    assert json.loads(capsys.readouterr().out)["reason"] == "rollback_completed"


def test_late_guest_verification_failure_rolls_back_all_activated_guests(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls, stage_counts = [], {}
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    monkeypatch.setattr(helper, "healthy", lambda *_args: False)
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])

    def staged(candidate, root, _binary, target_count, targets_digest):
        value = helper.generation(candidate, "darwin-aarch64", "b" * 64,
                                  target_count, targets_digest)
        value["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", value)
        return "staged"

    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append((action, workspace))
        if action == "stage":
            stage_counts[workspace] = stage_counts.get(workspace, 0) + 1
            if workspace == "workspace-b" and stage_counts[workspace] == 2:
                raise helper.UpdateError("activation_failed")
            return "staged" if stage_counts[workspace] == 1 else "current"
        return "current"

    monkeypatch.setattr(helper, "stage", staged)
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs: "updated")
    monkeypatch.setattr(helper, "rollback", lambda *_args: None)

    assert helper.host_update() == 1
    assert calls[-2:] == [("rollback", "workspace-b"), ("rollback", "workspace-a")]
    assert json.loads(capsys.readouterr().out)["reason"] == "rollback_completed"


def test_lost_finalize_response_retains_commit_journal_without_rollback(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls, activations, stages = [], {}, {}
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    health = iter((False, True))
    monkeypatch.setattr(helper, "healthy", lambda *_args: next(health))
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])

    def staged(candidate, root, _binary, target_count, targets_digest):
        value = helper.generation(candidate, "darwin-aarch64", "b" * 64,
                                  target_count, targets_digest)
        value["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", value)
        return "staged"

    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append((action, workspace))
        if action == "stage":
            stages[workspace] = stages.get(workspace, 0) + 1
            return "staged" if stages[workspace] == 1 else "current"
        if action == "activate":
            activations[workspace] = activations.get(workspace, 0) + 1
            if workspace == "workspace-b" and activations[workspace] == 2:
                raise OSError("response lost after finalize")
        return "current"

    monkeypatch.setattr(helper, "stage", staged)
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs: "updated")
    monkeypatch.setattr(helper, "rollback", lambda *_args: calls.append(("rollback", "host")))

    assert helper.host_update() == 1
    assert not any(action == "rollback" for action, _ in calls)
    journal = json.loads((root / "transaction").read_text())
    assert journal["phase"] == "verifying"
    assert json.loads(capsys.readouterr().out)["status"] == "updated"


def test_interrupted_local_activation_recovers_previous_generation(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    monkeypatch.setenv("DOTFILES_AI_CODEX_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_CODEX_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    assets = helper.validate_release(release_payload())["assets"]

    def executable(path, version):
        path.write_text(f"#!/bin/sh\nprintf 'codex-cli {version}\\n'\n")
        path.chmod(0o700)

    executable(binary, "0.152.0")
    old = {
        "schema_version": 1, "channel": "stable", "release": "0.152.0",
        "tag": "rust-v0.152.0", "platform": "darwin-aarch64",
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "target_count": 1, "targets_digest": hashlib.sha256(
            helper.canonical(["local"])).hexdigest(),
        "assets": {name: {**asset, "url": asset["url"].replace("0.153.3", "0.152.0")}
                   for name, asset in assets.items()},
        "validator_revision": helper.VALIDATOR_REVISION, "previous": None,
    }
    helper.atomic_json(root / "release-lock.json", old)
    candidate_binary = root / "candidate-codex"
    executable(candidate_binary, "0.153.3")
    new = helper.generation(
        {"release": "0.153.3", "tag": "rust-v0.153.3", "assets": assets},
        "darwin-aarch64", hashlib.sha256(candidate_binary.read_bytes()).hexdigest(),
    )
    new["previous"] = {key: value for key, value in old.items() if key != "previous"}
    helper.atomic_json(root / "candidate-lock.json", new)
    helper.transaction(root, "prepared", True, True, new)
    os.replace(binary, root / "previous-codex")
    helper.atomic_json(root / "previous-lock.json", old)
    helper.transaction(root, "backed_up", True, True, new)
    os.replace(candidate_binary, binary)

    helper.recover(root, binary)

    assert helper.read_lock(root)["release"] == "0.152.0"
    assert helper.healthy(helper.read_lock(root), binary)
    assert not (root / "transaction").exists()


def test_bootstrap_activation_failure_restores_absent_state(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    candidate_binary = root / "candidate-codex"
    candidate_binary.write_text("candidate")
    candidate_binary.chmod(0o700)
    candidate = helper.validate_release(release_payload())
    lock = helper.generation(candidate, "darwin-aarch64",
                             hashlib.sha256(candidate_binary.read_bytes()).hexdigest())
    lock["previous"] = None
    helper.atomic_json(root / "candidate-lock.json", lock)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    monkeypatch.setattr(helper, "healthy", lambda *_args: False)

    with pytest.raises(helper.UpdateError):
        helper.activate(root, binary)

    assert not binary.exists()
    assert not (root / "release-lock.json").exists()
    assert not (root / "transaction").exists()


def test_guest_activation_failure_retains_unchanged_healthy_host(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    binary.write_text("#!/bin/sh\nprintf 'codex-cli 0.153.3\\n'\n")
    binary.chmod(0o700)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    count, targets_digest = helper.target_identity(["workspace-a", "workspace-b"])
    current = helper.generation(
        candidate, "darwin-aarch64", hashlib.sha256(binary.read_bytes()).hexdigest(),
        count, targets_digest,
    )
    current["previous"] = None
    helper.atomic_json(root / "release-lock.json", current)
    (root / "candidate-codex").write_text("staged")
    (root / "candidate-codex").chmod(0o700)
    helper.atomic_json(root / "candidate-lock.json", current)
    helper.transaction(root, "activating_guests", True, True, current, 1)

    helper.rollback(root, binary)

    assert helper.healthy(helper.read_lock(root), binary)
    assert not (root / "candidate-codex").exists()
    assert not (root / "transaction").exists()


def test_rejected_release_detects_full_authority_mutation(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    root.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    helper.reject_candidate(candidate, "validation_failed", root)

    assert helper.rejected_candidate(candidate, root) is True
    changed = json.loads(json.dumps(candidate))
    changed["assets"]["linux-x86_64"]["size"] += 1
    with pytest.raises(helper.UpdateError):
        helper.rejected_candidate(changed, root)


def test_known_lockless_fedora_binary_is_adopted_for_rollback(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    binary.write_text("#!/bin/sh\nprintf 'codex-cli 0.151.0\\n'\n")
    binary.chmod(0o755)
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-aarch64")
    monkeypatch.setattr(helper, "validate_binary", lambda *_args: None)
    monkeypatch.setattr(helper, "LEGACY_LINUX_AARCH64_BINARY_SHA256",
                        hashlib.sha256(binary.read_bytes()).hexdigest())
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))

    helper.adopt_legacy(root, binary)

    lock = helper.read_lock(root)
    assert lock["release"] == "0.151.0"
    assert lock["assets"]["linux-aarch64"]["sha256"] == \
        "c1cf2baf375e261c1469381a52dc2c8fd05b6fb45cfff83fed0988fd6c5369b6"
    assert stat.S_IMODE(binary.stat().st_mode) == 0o700


def test_persisted_candidate_symlink_and_unsafe_process_lock_fail_closed(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/codex-package"
    binary = tmp_path / "libexec/codex"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    outside = tmp_path / "outside"
    outside.write_text("private")
    (root / "candidate-lock.json").symlink_to(outside)
    (root / "candidate-codex").write_text("candidate")
    (root / "candidate-codex").chmod(0o700)
    with pytest.raises(helper.UpdateError):
        helper.activate(root, binary)
    assert outside.read_text() == "private"

    (root / ".lock").write_text("")
    (root / ".lock").chmod(0o644)
    with pytest.raises(helper.UpdateError):
        helper.process_lock(root)


def test_projector_validates_centralized_state_sentinel(tmp_path: Path) -> None:
    helper = load_projector()
    root = tmp_path / "state"
    target = root / "codex"
    target.mkdir(parents=True, mode=0o700)
    sentinel = root / ".dotfiles-ai-state"
    sentinel.write_text("")
    sentinel.chmod(0o644)
    assert helper.validate_home(target, root) == target

    sentinel.chmod(0o666)
    with pytest.raises(ValueError, match="sentinel"):
        helper.validate_home(target, root)
    sentinel.unlink()
    sentinel.mkdir()
    with pytest.raises(ValueError, match="sentinel"):
        helper.validate_home(target, root)


def test_projector_recovers_cleanup_interruptions(tmp_path: Path, monkeypatch) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    (source / "config.toml").write_text("model = 'updated'\n")
    atomic_json = helper.atomic_json

    def interrupt_manifest(path, value):
        atomic_json(path, value)
        if path.name == helper.MANIFEST:
            raise RuntimeError("manifest interruption")

    monkeypatch.setattr(helper, "atomic_json", interrupt_manifest)
    with pytest.raises(RuntimeError, match="manifest interruption"):
        helper.project(source, target)
    monkeypatch.setattr(helper, "atomic_json", atomic_json)
    helper.project(source, target)

    (source / "config.toml").write_text("model = 'again'\n")
    remove_tree = helper.shutil.rmtree

    def interrupt_cleanup(path):
        remove_tree(path)
        raise RuntimeError("cleanup interruption")

    monkeypatch.setattr(helper.shutil, "rmtree", interrupt_cleanup)
    with pytest.raises(RuntimeError, match="cleanup interruption"):
        helper.project(source, target)
    monkeypatch.setattr(helper.shutil, "rmtree", remove_tree)
    helper.project(source, target)
    assert (target / "config.toml").read_text() == "model = 'again'\n"


@pytest.mark.parametrize("kind", ["mode", "directory", "fifo"])
def test_projector_recovery_rejects_unsafe_old_targets(
        tmp_path: Path, monkeypatch, kind: str) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    (source / "config.toml").write_text("model = 'updated'\n")

    monkeypatch.setattr(helper, "publish_entry", lambda *_args: (_ for _ in ()).throw(
        RuntimeError("interrupted")))
    with pytest.raises(RuntimeError, match="interrupted"):
        helper.project(source, target)
    monkeypatch.undo()

    current = target / "config.toml"
    if kind == "mode":
        current.chmod(0o644)
    else:
        current.unlink()
        if kind == "directory":
            current.mkdir()
        else:
            os.mkfifo(current)
    with pytest.raises(ValueError, match="unsafe managed recovery target"):
        helper.project(source, target)


def test_projector_recovery_rejects_unsafe_completed_target(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    helper.project(source, target)
    (source / "config.toml").write_text("model = 'updated'\n")
    publish = helper.publish_entry

    def interrupt(staged, current):
        publish(staged, current)
        raise RuntimeError("interrupted")

    monkeypatch.setattr(helper, "publish_entry", interrupt)
    with pytest.raises(RuntimeError, match="interrupted"):
        helper.project(source, target)
    monkeypatch.setattr(helper, "publish_entry", publish)
    (target / "config.toml").chmod(0o644)
    with pytest.raises(ValueError, match="unsafe managed recovery target"):
        helper.project(source, target)


def test_projector_rejects_traversal_and_target_replacement(tmp_path: Path, monkeypatch) -> None:
    helper = load_projector()
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    with pytest.raises(ValueError, match="not normalized"):
        helper.project(source, tmp_path / "state/../escape")

    helper.project(source, target)
    files = helper.source_files

    def replace_target(path):
        result = files(path)
        target.rename(tmp_path / "moved-codex")
        target.mkdir(mode=0o700)
        return result

    monkeypatch.setattr(helper, "source_files", replace_target)
    with pytest.raises(ValueError, match="changed while locked"):
        helper.project(source, target)
    assert not (target / "config.toml").exists()


def test_projector_serializes_concurrent_processes(tmp_path: Path) -> None:
    source = managed_source(tmp_path)
    target = tmp_path / "state/codex"
    processes = [subprocess.Popen(
        [sys.executable, str(PROJECTOR), str(source), str(target)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) for _ in range(4)]

    results = [process.communicate(timeout=10) for process in processes]

    assert all(process.returncode == 0 for process in processes), results
    manifest = json.loads((target / ".dotfiles-ai-managed.json").read_text())
    assert len(manifest["files"]) == 4
    assert not (target / ".dotfiles-ai-journal.json").exists()


def test_archive_extracts_only_the_exact_regular_executable(tmp_path: Path) -> None:
    helper = load_archive()
    archive = tmp_path / "codex.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo(helper.EXPECTED)
        member.mode = 0o755
        member.size = 6
        bundle.addfile(member, io.BytesIO(b"codex\n"))

    destination = tmp_path / "codex"
    helper.extract(archive, destination)

    assert destination.read_bytes() == b"codex\n"


def test_archive_accepts_an_explicit_x86_64_executable(tmp_path: Path) -> None:
    helper = load_archive()
    assert helper.MAX_SIZE >= 270_815_680
    expected = "codex-x86_64-unknown-linux-musl"
    archive = tmp_path / "codex.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo(expected)
        member.mode = 0o755
        member.size = 6
        bundle.addfile(member, io.BytesIO(b"codex\n"))

    destination = tmp_path / "codex"
    helper.extract(archive, destination, expected)

    assert destination.read_bytes() == b"codex\n"


@pytest.mark.parametrize("name,kind", [
    ("../escape", tarfile.REGTYPE),
    ("/absolute", tarfile.REGTYPE),
    ("codex-aarch64-unknown-linux-musl", tarfile.SYMTYPE),
    ("codex-aarch64-unknown-linux-musl", tarfile.LNKTYPE),
])
def test_archive_rejects_unsafe_members(tmp_path: Path, name: str, kind: bytes) -> None:
    helper = load_archive()
    archive = tmp_path / "codex.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = "../escape"
        member.size = 1 if kind == tarfile.REGTYPE else 0
        bundle.addfile(member, io.BytesIO(b"x") if member.size else None)

    with pytest.raises(ValueError, match="unsafe member set"):
        helper.extract(archive, tmp_path / "codex")


def test_archive_rejects_duplicate_members(tmp_path: Path) -> None:
    helper = load_archive()
    archive = tmp_path / "codex.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for _ in range(2):
            member = tarfile.TarInfo(helper.EXPECTED)
            member.size = 1
            bundle.addfile(member, io.BytesIO(b"x"))

    with pytest.raises(ValueError, match="unsafe member set"):
        helper.extract(archive, tmp_path / "codex")


@pytest.mark.parametrize("kind", ["directory", "fifo", "symlink"])
def test_archive_rejects_unsafe_install_targets(tmp_path: Path, kind: str) -> None:
    helper = load_archive()
    target = tmp_path / "codex"
    if kind == "directory":
        target.mkdir()
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        target.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="unsafe type"):
        helper.validate_target(target)

    target.unlink() if not target.is_dir() else target.rmdir()
    target.write_text("existing")
    helper.validate_target(target)


def test_guest_rollback_restores_source_and_managed_state_only(tmp_path: Path) -> None:
    helper = load_rollback()
    home = tmp_path / "home"
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    (source / "version").write_text("old")
    for command in (
        ["git", "init", "-b", "main"],
        ["git", "add", "version"],
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "old"],
    ):
        subprocess.run(command, cwd=source, check=True, capture_output=True)
    old_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True,
        capture_output=True).stdout.strip()
    managed = home / ".local/state/dotfiles-ai/codex/config.toml"
    managed.parent.mkdir(parents=True, mode=0o700)
    managed.write_text("old managed")
    managed.chmod(0o600)
    auth = managed.parent / "auth.json"
    auth.write_text("private")
    binary = home / ".local/libexec/dotfiles-ai/codex"
    binary.parent.mkdir(parents=True)
    binary.write_text("old binary")
    guest_config = home / ".config/dotfiles-ai/chezmoi.toml"
    guest_config.parent.mkdir(parents=True)
    guest_config.write_text("old config")
    lifecycle = home / ".local/bin/dbsctrctl"
    lifecycle.parent.mkdir(parents=True)
    lifecycle.write_text("old lifecycle")

    token = helper.snapshot(home)
    (source / "version").write_text("new")
    subprocess.run(["git", "add", "version"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-m", "new"], cwd=source, check=True, capture_output=True)
    managed.write_text("new managed")
    binary.write_text("new binary")
    guest_config.write_text("new config")
    lifecycle.write_text("new lifecycle")
    added = home / ".local/bin/codex-project"
    added.parent.mkdir(parents=True, exist_ok=True)
    added.write_text("new helper")

    helper.restore(token, home)

    assert subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True,
        capture_output=True).stdout.strip() == old_revision
    assert managed.read_text() == "old managed"
    assert binary.read_text() == "old binary"
    assert guest_config.read_text() == "old config"
    assert lifecycle.read_text() == "old lifecycle"
    assert not added.exists()
    assert auth.read_text() == "private"
    helper.discard(token, home)

    binary.unlink()
    guest_config.unlink()
    token = helper.snapshot(home)
    binary.write_text("new binary")
    guest_config.write_text("new config")
    helper.restore(token, home)
    assert not binary.exists()
    assert not guest_config.exists()
    helper.discard(token, home)


def test_guest_rollback_rejects_symlinked_ancestor_without_external_deletion(tmp_path: Path) -> None:
    helper = load_rollback()
    home = tmp_path / "home"
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    (source / "version").write_text("old")
    for command in (
        ["git", "init", "-b", "main"],
        ["git", "add", "version"],
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "old"],
    ):
        subprocess.run(command, cwd=source, check=True, capture_output=True)
    token = helper.snapshot(home)
    original = home / ".local"
    retained = home / ".local-retained"
    original.rename(retained)
    outside = tmp_path / "outside"
    victim = outside / "bin/codex"
    victim.parent.mkdir(parents=True)
    victim.write_text("external")
    original.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked ancestor"):
        helper.restore(token, home)

    assert victim.read_text() == "external"


def test_guest_rollback_preflights_config_before_source_reset(tmp_path: Path) -> None:
    helper = load_rollback()
    home = tmp_path / "home"
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    (source / "version").write_text("old")
    for command in (
        ["git", "init", "-b", "main"],
        ["git", "add", "version"],
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "old"],
    ):
        subprocess.run(command, cwd=source, check=True, capture_output=True)
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    config.parent.mkdir(parents=True)
    config.write_text("old config")
    token = helper.snapshot(home)
    (source / "version").write_text("new")
    subprocess.run(["git", "add", "version"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-m", "new"], cwd=source, check=True, capture_output=True)
    new_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True,
        capture_output=True).stdout.strip()
    retained = home / ".config-retained"
    (home / ".config").rename(retained)
    outside = tmp_path / "outside"
    victim = outside / "dotfiles-ai/chezmoi.toml"
    victim.parent.mkdir(parents=True)
    victim.write_text("external")
    (home / ".config").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked ancestor"):
        helper.restore(token, home)

    assert subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True,
        capture_output=True).stdout.strip() == new_revision
    assert victim.read_text() == "external"
