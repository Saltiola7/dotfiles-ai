"""Headless native bootstrap preserves executable and private runtime ownership."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from test_portable_distribution import ROOT, data


def headless_values():
    values = data(state_root="", remote_user_environment=False)
    values["chezmoi"] = {"os": "linux", "arch": "arm64"}
    values["dotfiles_ai"]["headless_server"] = {"enabled": True}
    return values


def render(path, values=None):
    return subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(values or headless_values()), "execute-template"],
        input=(ROOT / path).read_text(), capture_output=True, text=True, check=True,
    ).stdout


def fixture(tmp_path):
    user = tmp_path / "user"
    bin_dir = user / ".local/bin"
    bin_dir.mkdir(parents=True)
    home = user / ".codex"
    home.mkdir(mode=0o700)
    release = home / "packages/standalone/releases/99.0.0-aarch64-unknown-linux-musl"
    (release / "bin").mkdir(parents=True)
    executable = release / "bin/codex"
    executable.write_text('#!/bin/sh\nprintf "codex-cli 99.0.0\\n"\n')
    executable.chmod(0o755)
    (home / "packages/standalone/current").symlink_to(release)
    (bin_dir / "codex").symlink_to(home / "packages/standalone/current/bin/codex")
    for name in ["codex-project"]:
        shutil.copyfile(ROOT / f"dot_local/bin/executable_{name}", bin_dir / name)
        (bin_dir / name).chmod(0o700)
    script = bin_dir / "codex-install"
    script.write_text(render("dot_local/bin/executable_codex-install.tmpl"))
    script.chmod(0o700)
    (bin_dir / "curl").write_text('#!/bin/sh\necho unexpected-download >&2\nexit 99\n')
    (bin_dir / "curl").chmod(0o700)
    (bin_dir / "uname").write_text('#!/bin/sh\ncase "$1" in -s) echo Linux;; -m) echo aarch64;; esac\n')
    (bin_dir / "uname").chmod(0o700)
    env = {**os.environ, "HOME": str(user), "PATH": f"{bin_dir}:" + os.environ["PATH"]}
    env.pop("CODEX_HOME", None)
    return home, bin_dir, script, executable, env


def test_headless_reapply_keeps_newer_native_release_auth_and_sessions(tmp_path):
    home, bin_dir, script, executable, env = fixture(tmp_path)
    auth = home / "auth.json"
    auth.write_text('{"fixture":"not-a-real-credential"}')
    auth.chmod(0o600)
    (home / "sessions").mkdir()
    (home / "sessions/fixture").write_text("preserve-session")
    before = (executable.read_bytes(), auth.read_bytes(), (home / "sessions/fixture").read_bytes())
    for _ in range(2):
        result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert (executable.read_bytes(), auth.read_bytes(), (home / "sessions/fixture").read_bytes()) == before
    settings = json.loads((home / "app-server-daemon/settings.json").read_text())
    assert settings["updater"]["autoUpdateEnabled"] is False
    assert (bin_dir / "codex").is_symlink()


def test_headless_refuses_unknown_executable_without_executing(tmp_path):
    home, bin_dir, script, _, env = fixture(tmp_path)
    (bin_dir / "codex").unlink()
    unknown = bin_dir / "codex"
    unknown.write_text('#!/bin/sh\ntouch "$HOME/unsafe-executed"\n')
    unknown.chmod(0o700)
    before = unknown.read_bytes()
    result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert unknown.read_bytes() == before
    assert not (home.parent / "unsafe-executed").exists()


def test_headless_does_not_manage_upstream_binary_shell_or_credentials():
    result = subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(headless_values()), "managed"],
        capture_output=True, text=True, check=True,
    )
    files = set(result.stdout.splitlines())
    assert ".local/bin/codex-install" in files
    assert ".local/bin/codex-project" in files
    assert not ({".local/bin/codex", ".bash_profile", ".bashrc", ".common_profile", ".codex/auth.json"} & files)
    assert not any("opencode" in p or "LaunchAgents" in p or "codex-update-all" in p for p in files)


def test_headless_bootstrap_uses_existing_policy_guard_and_official_installer():
    script = render("dot_local/bin/executable_codex-install.tmpl")
    assert 'CODEX_HOME="$HOME/.codex"' in script
    assert "--prepare-native" in script and "--resolve-native" in script
    assert "https://chatgpt.com/codex/install.sh" in script
    assert "curl" in script and "| sh" not in script


def test_headless_refuses_conflicting_inherited_home(tmp_path):
    home, _, script, _, env = fixture(tmp_path)
    env["CODEX_HOME"] = str(home.parent / "unrelated")
    result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 75
    assert not (home / "app-server-daemon").exists()


def test_headless_refuses_symlinked_home_before_policy_write(tmp_path):
    home, _, script, _, env = fixture(tmp_path)
    other = home.with_name("private-original")
    home.rename(other)
    home.symlink_to(other, target_is_directory=True)
    result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 75
    assert not (other / "app-server-daemon").exists()


def test_headless_missing_install_uses_official_installer_then_validates(tmp_path):
    home, bin_dir, script, executable, env = fixture(tmp_path)
    (bin_dir / "codex").unlink()
    installer = tmp_path / "upstream-installer"
    installer.write_text('#!/bin/sh\nln -s "$CODEX_HOME/packages/standalone/current/bin/codex" "$CODEX_INSTALL_DIR/codex"\n')
    curl = bin_dir / "curl"
    curl.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then cp "' + str(installer) + '" "$2"; exit 0; fi; shift; done; exit 1\n')
    for _ in range(2):
        result = subprocess.run([str(script)], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert (bin_dir / "codex").resolve() == executable
    assert json.loads((home / "app-server-daemon/settings.json").read_text())["updater"]["autoUpdateEnabled"] is False


def test_headless_role_rejects_other_platforms_and_overlapping_owners():
    for change in ("platform", "workstation", "remote", "state"):
        values = headless_values()
        if change == "platform":
            values["chezmoi"]["os"] = "darwin"
        elif change == "workstation":
            values["dotfiles_ai"]["linux_workstation"] = {"enabled": True}
        elif change == "remote":
            values["dotfiles_ai"]["remote_user_environment"]["enabled"] = True
        else:
            values["dotfiles_ai"]["state"]["root"] = "/other"
        result = subprocess.run(
            ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
             "--override-data", json.dumps(values), "execute-template"],
            input=(ROOT / "dot_local/bin/executable_codex-install.tmpl").read_text(),
            capture_output=True, text=True,
        )
        assert result.returncode != 0
