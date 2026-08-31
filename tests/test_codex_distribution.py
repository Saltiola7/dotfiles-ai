import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).parents[1]
PROJECTOR = ROOT / "dot_local/bin/executable_codex-project"
ARCHIVE = ROOT / "dot_local/bin/executable_codex-archive"
ROLLBACK = ROOT / "dot_local/bin/executable_codex-rollback"


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


def test_projector_validates_homebrew_executable_record(tmp_path: Path) -> None:
    helper = load_projector()
    executable = tmp_path / "prefix/Caskroom/codex/0.151.0/bin/codex"
    executable.parent.mkdir(parents=True)
    executable.write_text("binary")
    executable.chmod(0o755)
    record = tmp_path / "record"
    record.write_text(str(executable) + "\n")
    record.chmod(0o600)

    assert helper.resolve_homebrew(record, "0.151.0") == executable

    record.write_text(str(tmp_path / "outside/codex") + "\n")
    record.chmod(0o600)
    with pytest.raises((ValueError, FileNotFoundError)):
        helper.resolve_homebrew(record, "0.151.0")


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

    token = helper.snapshot(home)
    (source / "version").write_text("new")
    subprocess.run(["git", "add", "version"], cwd=source, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-m", "new"], cwd=source, check=True, capture_output=True)
    managed.write_text("new managed")
    binary.write_text("new binary")
    guest_config.write_text("new config")
    added = home / ".local/bin/codex-project"
    added.parent.mkdir(parents=True)
    added.write_text("new helper")

    helper.restore(token, home)

    assert subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True,
        capture_output=True).stdout.strip() == old_revision
    assert managed.read_text() == "old managed"
    assert binary.read_text() == "old binary"
    assert guest_config.read_text() == "old config"
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
