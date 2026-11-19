"""Native ARM Try Omarchy reuses AI owners without host state or hardware files."""

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib

import pytest

from test_portable_distribution import ROOT


HOOK = "run_onchange_after_install-linux-herdr-desktop.sh.tmpl"


def configured(arch="arm64", desktop=True):
    return {
        "chezmoi": {"os": "linux", "arch": arch},
        "dotfiles_ai": {
            "linux_workstation": {"enabled": True},
            "herdr_linux_desktop": {"enabled": desktop},
            "remote_user_environment": {"enabled": False},
            "sandbox": {"enabled": False},
            "herdr": {"launchagent": False, "host_enabled": False},
            "state": {"root": "/var/lib/dotfiles-ai/example"},
        },
    }


def chezmoi(*args, data=None, template=None):
    return subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(data or configured()), *args],
        input=template, capture_output=True, text=True, check=True,
    ).stdout


def render(path, data=None):
    result = chezmoi("execute-template", data=data, template=(ROOT / path).read_text())
    subprocess.run(["bash", "-n"], input=result, text=True, check=True)
    return result


@pytest.mark.parametrize("arch", ["arm64", "amd64"])
def test_native_profile_owns_ai_only_and_installs_worktrunk_before_consumers(arch):
    managed = set(chezmoi("managed", data=configured(arch)).splitlines())
    assert "config.omarchy-try.example.toml" not in managed
    assert "install-00-workstation-tools.sh" in managed
    assert "install-workstation-tools.sh" not in managed
    assert "install-linux-herdr-desktop.sh" in managed
    assert ".config/herdr-app/settings.json" in managed
    assert ".config/herdr-app/themes/catppuccin-mocha.json" in managed
    assert not any(p.startswith(("Library/", ".config/hypr/")) for p in managed)
    assert not {".bashrc", ".local/bin/docker", ".local/bin/sandbox-vm"} & managed
    for source in ("run_onchange_after_install-00-remote-herdr.sh.tmpl",
                   "run_onchange_after_install-00-workstation-tools.sh.tmpl", HOOK):
        render(source, configured(arch))


def test_bootstrap_validates_state_before_mutation_and_exports_private_paths():
    source = (ROOT / "dot_local/bin/executable_dotfiles-ai-omarchy-setup").read_text()
    assert source.index('[[ $root == ') < source.index("omarchy pkg add")
    assert source.index('export DOTFILES_AI_STATE_ROOT=') < source.index('chezmoi -c "$config" apply')
    assert source.index('export XDG_DATA_HOME=') < source.index('chezmoi -c "$config" apply')
    assert source.index('export XDG_STATE_HOME=') < source.index('chezmoi -c "$config" apply')


def test_arm_tui_pin_matches_published_release():
    defaults = tomllib.loads((ROOT / ".chezmoidata.toml").read_text())["dotfiles_ai"]["herdr"]
    assert defaults["linux_arm64_asset_url"].endswith("/v0.9.5/herdr-linux-aarch64")
    assert defaults["linux_arm64_asset_sha256"] == "17d7536f2da50859523680ef279dffcac8e4a235f4e46fe8da6c2ec44141897c"


def environment(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env = {**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin"}
    return home, bin_dir, env


def executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


def archive(path, files):
    with tarfile.open(path, "w:gz") as tar:
        for name, contents in files.items():
            payload = contents.encode()
            info = tarfile.TarInfo(name)
            info.mode = 0o755 if name.endswith(("herdr-core", "herdr-app")) else 0o644
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_existing_desktop_and_core_keep_their_installer(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    for command in ("herdr-app", "herdr-core"):
        executable(bin_dir / command, "#!/bin/sh\nexit 99\n")
    result = subprocess.run(["bash"], input=render(HOOK), env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not (home / ".local").exists()


def test_verified_native_archives_install_once_without_starting_a_core(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    app_archive = tmp_path / "app.tar.gz"
    core_archive = tmp_path / "core.tar.gz"
    app_sha = archive(app_archive, {"herdr-app/herdr-app": "#!/bin/sh\nexit 0\n", "herdr-app/herdr-app.svg": "<svg/>"})
    core_sha = archive(core_archive, {"herdr-core": "#!/bin/sh\necho hc 0.1.21\n"})
    config = configured()
    config["dotfiles_ai"]["herdr_linux_desktop"].update(app_arm64_sha256=app_sha, core_arm64_sha256=core_sha)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    if sys.platform == "darwin":
        # macOS hosts lack GNU sha256sum; Linux runs the real one unshimmed.
        executable(bin_dir / "sha256sum", '#!/bin/sh\nexec shasum -a 256 "$@"\n')
    executable(bin_dir / "curl", '''#!/bin/sh
case "$*" in *'/core/'*) source="$CORE_ARCHIVE" ;; *) source="$APP_ARCHIVE" ;; esac
while [ "$1" != -o ]; do shift; done
cp "$source" "$2"
''')
    env.update(APP_ARCHIVE=str(app_archive), CORE_ARCHIVE=str(core_archive))
    script = render(HOOK, config)
    for _ in range(2):
        result = subprocess.run(["bash"], input=script, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert (home / ".local/bin/herdr-app").is_symlink()
    assert (home / ".local/bin/herdr-core").is_file()
    assert (home / ".local/share/applications/herdr-app.desktop").is_file()


def test_checksum_failure_leaves_install_destinations_untouched(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    executable(bin_dir / "sha256sum", '#!/bin/sh\nexit 1\n')
    executable(bin_dir / "curl", '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\nprintf bad > "$2"\n')
    result = subprocess.run(["bash"], input=render(HOOK), env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert not (home / ".local").exists()


@pytest.mark.parametrize("name,hook,version", [
    ("herdr", "run_onchange_after_install-00-remote-herdr.sh.tmpl", "herdr 0.10.0"),
    ("wt", "run_onchange_after_install-00-workstation-tools.sh.tmpl", "wt v0.81.0"),
])
def test_newer_native_path_provider_is_never_shadowed(tmp_path, name, hook, version):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    provider = bin_dir / name
    executable(provider, f'#!/bin/sh\n[ "$1" = --version ] && echo "{version}"; exit 0\n')
    original = provider.read_bytes()
    executable(bin_dir / "curl", '#!/bin/sh\necho download-attempted >&2; exit 99\n')
    data = configured()
    data["dotfiles_ai"]["herdr"]["executable"] = "~/.local/bin/herdr"
    result = subprocess.run(["bash"], input=render(hook, data), env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "ownership review required" in result.stderr
    assert "download-attempted" not in result.stderr
    assert provider.read_bytes() == original
    assert not (home / ".local").exists()


def test_active_native_herdr_server_is_guarded_before_any_download(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    log = tmp_path / "calls"
    env["PROVIDER_LOG"] = str(log)
    provider = bin_dir / "herdr"
    executable(provider, """#!/bin/sh
printf '%s\n' "$*" >> "$PROVIDER_LOG"
[ "$1" != --version ] || { echo 'herdr 0.10.0'; exit 0; }
printf '{"running": true}\n'
""")
    original = provider.read_bytes()
    executable(bin_dir / "curl", '#!/bin/sh\necho download-attempted >&2; exit 99\n')
    data = configured()
    data["dotfiles_ai"]["herdr"]["executable"] = "~/.local/bin/herdr"
    result = subprocess.run(["bash"], input=render("run_onchange_after_install-00-remote-herdr.sh.tmpl", data), env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "active native server" in result.stderr
    assert log.read_text().splitlines() == ["status server --json"]
    assert provider.read_bytes() == original
    assert "download-attempted" not in result.stderr
    assert not (home / ".local").exists()


def test_qualified_native_worktrunk_is_reused_without_local_shadow(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    executable(bin_dir / "wt", '#!/bin/sh\necho "wt v0.80.0"\n')
    result = subprocess.run(["bash"], input=render("run_onchange_after_install-00-workstation-tools.sh.tmpl"), env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not (home / ".local").exists()
