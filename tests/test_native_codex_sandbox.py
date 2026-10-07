"""Native sandbox primitive smoke; no provider, conversation or live HOME access.

Select an already installed native executable with CODEX_NATIVE_BINARY. This
does not qualify interactive approvals, native session migration or fleet rollout.
Permission profile names come from Codex rust-v0.155.1 protocol/models.rs.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.skipif(not os.environ.get("CODEX_NATIVE_BINARY"), reason="native Codex authority not selected")
def test_native_read_only_and_workspace_profiles_preserve_sibling_checkout(tmp_path):
    executable = Path(os.environ["CODEX_NATIVE_BINARY"]).resolve(strict=True)
    home = tmp_path / "home"
    codex_home = home / "codex"
    codex_home.mkdir(parents=True, mode=0o700)
    (codex_home / "config.toml").write_text("# Synthetic qualification; no credentials or history.\n")
    environment = {"HOME": str(home), "CODEX_HOME": str(codex_home),
                   "PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    version = subprocess.run([str(executable), "--version"], env=environment,
                             text=True, capture_output=True, check=True, timeout=10)
    assert version.stdout.startswith("codex-cli ")
    # Keep the workspace outside OS temp roots that native policies may allow.
    base = ROOT / ".dbsctr"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex-sandbox-", dir=base) as directory:
        primary = Path(directory) / "primary"
        primary.mkdir()

        def git(cwd, *arguments):
            return subprocess.run(["git", *arguments], cwd=cwd, env=environment, text=True,
                                  capture_output=True, check=True, timeout=10).stdout.strip()

        git(primary, "init", "-b", "main")
        git(primary, "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
            "commit", "--allow-empty", "-m", "native sandbox fixture")
        task = Path(directory) / "task"
        git(primary, "worktree", "add", "-b", "task", str(task))
        source = task / "fixture.txt"
        source.write_text("synthetic readable input")
        sibling_before = git(primary, "rev-parse", "HEAD"), git(primary, "branch", "--show-current")

        def native(profile, program, *arguments):
            return subprocess.run(
                [str(executable), "sandbox", "--permission-profile", profile, "-C", str(task), "--",
                 sys.executable, "-B", "-c", program, *map(str, arguments)],
                env=environment, text=True, capture_output=True, timeout=20,
            )

        read = native(":read-only", "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())", source)
        assert read.returncode == 0 and read.stdout.strip() == "synthetic readable input", read.stderr
        write_program = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('synthetic write')"
        denied = task / "read-only-denied.txt"
        result = native(":read-only", write_program, denied)
        assert result.returncode != 0 and not denied.exists()
        permitted = task / "workspace-allowed.txt"
        result = native(":workspace", write_program, permitted)
        assert result.returncode == 0 and permitted.read_text() == "synthetic write", result.stderr
        outside = primary / "sibling-denied.txt"
        result = native(":workspace", write_program, outside)
        assert result.returncode != 0 and not outside.exists()
        assert sibling_before == (git(primary, "rev-parse", "HEAD"), git(primary, "branch", "--show-current"))
