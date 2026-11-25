"""Native ARM Try Omarchy reuses AI owners without host state or hardware files."""

import hashlib
import io
import json
import os
from pathlib import Path
import pty
import pwd
import stat
import subprocess
import sys
import tarfile
import tomllib

import pytest

from test_portable_distribution import ROOT


HOOK = "run_onchange_after_install-linux-herdr-desktop.sh.tmpl"
WORKTRUNK = "run_onchange_after_install-00-workstation-tools.sh.tmpl"
# Upstream's published v0.83.0 Linux musl assets and SHA-256 checksums.
WORKTRUNK_PINS = {
    "aarch64": ("worktrunk-aarch64-unknown-linux-musl",
                "92c68827a18b037c608b7728bcf7ce1d594771ac814bec7412a35129f276d4ae"),
    "x86_64": ("worktrunk-x86_64-unknown-linux-musl",
               "e0dd5e5eb365890ddc7b255183c227e441fbb7da04cab5b72e54fa80fd21818b"),
}


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


@pytest.mark.parametrize("os_name,distro,workstation,remote,expected", [
    ("linux", "omarchy", True, False, True),
    ("linux", "fedora", True, False, False),
    ("linux", "omarchy", False, False, False),
    ("linux", "omarchy", True, True, False),
    ("darwin", "", True, False, False),
])
def test_chatgpt_package_is_only_managed_on_omarchy_workstations(os_name, distro, workstation, remote, expected):
    data = configured()
    data["chezmoi"].update(os=os_name, osRelease={"id": distro})
    data["dotfiles_ai"]["linux_workstation"]["enabled"] = workstation
    data["dotfiles_ai"]["remote_user_environment"]["enabled"] = remote
    scripts = chezmoi("managed", "--include=scripts", data=data).splitlines()
    assert ("install-omarchy-chatgpt-desktop.sh" in scripts) == expected


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
    # The owned default directories exist before the apply renders the policy.
    assert (source.index('[[ -e $root/.dotfiles-ai-state ]]') < source.rindex('provision_worktree_policy_roots')
            < source.index('chezmoi -c "$config" apply'))


SETUP = ".local/bin/dotfiles-ai-omarchy-setup"
ROOT_DIR = ".local/state/worktrees"
CACHE_DIR = ".cache/dotfiles-ai/dvc"


def install_setup(tmp_path):
    """Install only the setup command: the first documented Try Omarchy step."""
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("GIT_", "WORKTRUNK_", "XDG_"))}
    environment.update(HOME=str(home))
    subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(configured()), "--cache", str(tmp_path / "cache"),
         "--persistent-state", str(tmp_path / "state.boltdb"), "apply", "--exclude", "scripts",
         str(home / SETUP)],
        env=environment, text=True, capture_output=True, check=True, timeout=120)
    return home, environment


def run_setup(tmp_path, home, environment, *, declared, cache="", foreign=None):
    """Run the installed command as the runbook does; script every other effect."""
    tools, calls = tmp_path / "tools", tmp_path / "calls"
    tools.mkdir()
    account = pwd.getpwuid(os.getuid()).pw_name
    for name in ("sudo", "omarchy", "touch", "herdr", "opencode", "codex"):
        executable(tools / name, f'#!/bin/sh\nprintf \'%s %s\\n\' {name} "$*" >>"{calls}"\n')
    executable(tools / "chezmoi", f'''#!/bin/sh
printf 'chezmoi %s\\n' "$3" >>"{calls}"
case "$3" in
  execute-template)
    case "$4" in
      *state.root*) echo "/var/lib/dotfiles-ai/{account}" ;;
      *cache_root*) echo "$DECLARED_CACHE" ;;
      *) echo "$DECLARED_ROOT" ;;
    esac ;;
  apply)
    for directory in {ROOT_DIR} {CACHE_DIR}; do
      [ -d "$HOME/$directory" ] && echo "present $directory" >>"{calls}" || echo "absent $directory" >>"{calls}"
    done ;;
esac
''')
    if foreign is not None:
        executable(tools / "stat", f'#!/bin/sh\n[ "$3" = "{foreign}" ] && echo {os.getuid() + 1} '
                                    '|| exec /usr/bin/stat "$@"\n')
    master, slave = pty.openpty()
    try:
        result = subprocess.run(
            [str(home / SETUP)], stdin=slave, text=True, capture_output=True, timeout=60,
            env={**environment, "PATH": f"{tools}:/usr/bin:/bin", "CALLS": str(calls),
                 "ACCOUNT": account, "DECLARED_ROOT": declared, "DECLARED_CACHE": cache,
                 "DOTFILES_AI_CHEZMOI_CONFIG": str(tmp_path / "chezmoi.toml")})
    finally:
        os.close(master)
        os.close(slave)
    return result, calls.read_text().splitlines()


@pytest.mark.parametrize("spelling", ["tilde", "absolute"])
def test_setup_creates_the_missing_default_directories_before_its_apply(tmp_path, spelling):
    home, environment = install_setup(tmp_path)
    declared, cache = "~/.local/state/worktrees", ""
    if spelling == "absolute":
        declared, cache = f"{home}/{ROOT_DIR}", f"{home}/{CACHE_DIR}"
    result, calls = run_setup(tmp_path, home, environment, declared=declared, cache=cache)
    assert result.returncode == 0, result.stderr
    for relative in (ROOT_DIR, CACHE_DIR):
        assert stat.S_IMODE((home / relative).stat().st_mode) == 0o700
        # Recorded by the scripted apply: both directories exist when it runs.
        assert f"present {relative}" in calls


def test_setup_leaves_an_existing_private_root_and_its_mode_alone(tmp_path):
    home, environment = install_setup(tmp_path)
    existing = home / ROOT_DIR
    existing.mkdir(parents=True)
    existing.chmod(0o750)
    result, calls = run_setup(tmp_path, home, environment, declared="~/.local/state/worktrees")
    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(existing.stat().st_mode) == 0o750
    assert stat.S_IMODE((home / CACHE_DIR).stat().st_mode) == 0o700


@pytest.mark.parametrize("declared,cache,absent", [
    ("~/Worktrees", "", (ROOT_DIR, CACHE_DIR)),
    ("", "", (ROOT_DIR, CACHE_DIR)),
    ("~/.local/state/worktrees", "/external/dvc", (CACHE_DIR,)),
])
def test_setup_creates_only_the_declared_default_directories(tmp_path, declared, cache, absent):
    home, environment = install_setup(tmp_path)
    result, calls = run_setup(tmp_path, home, environment, declared=declared, cache=cache)
    assert result.returncode == 0, result.stderr
    assert "chezmoi apply" in calls
    for relative in absent:
        assert not os.path.lexists(home / relative)
        assert f"absent {relative}" in calls


@pytest.mark.parametrize("hazard,message", [
    ("home symlink", "symbolic link"), ("symlinked parent", "symbolic link"),
    ("symlinked root", "symbolic link"), ("foreign owner", "owned by"),
    ("not a directory", "owned by"),
])
def test_setup_refuses_unsafe_paths_before_creating_anything(tmp_path, hazard, message):
    home, environment = install_setup(tmp_path)
    elsewhere, root, cache_parent = tmp_path / "elsewhere", home / ROOT_DIR, home / ".cache/dotfiles-ai"
    elsewhere.mkdir()
    foreign = None
    if hazard == "home symlink":
        alias = tmp_path / "home-alias"
        alias.symlink_to(home, target_is_directory=True)
        environment = {**environment, "HOME": str(alias)}
    elif hazard == "symlinked parent":
        home.joinpath(".cache").mkdir()
        cache_parent.symlink_to(elsewhere, target_is_directory=True)
    elif hazard == "symlinked root":
        root.parent.mkdir(parents=True)
        root.symlink_to(elsewhere, target_is_directory=True)
    elif hazard == "foreign owner":
        cache_parent.mkdir(parents=True)
        foreign = str(cache_parent)
    else:
        home.joinpath(".cache").mkdir()
        cache_parent.write_text("not a directory")
    result, calls = run_setup(tmp_path, home, environment, declared="~/.local/state/worktrees", foreign=foreign)
    assert result.returncode == 1
    assert message in result.stderr
    assert "chezmoi apply" not in calls
    assert list(elsewhere.iterdir()) == []
    if hazard != "symlinked root":
        assert not os.path.lexists(root)


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
    ("wt", "run_onchange_after_install-00-workstation-tools.sh.tmpl", "wt v0.84.0"),
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
    executable(bin_dir / "wt", '#!/bin/sh\necho "wt v0.83.0"\n')
    result = subprocess.run(["bash"], input=render(WORKTRUNK), env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not (home / ".local").exists()


def test_workstation_installer_pins_the_published_worktrunk_release():
    script = render(WORKTRUNK)
    assert "version=0.83.0\n" in script
    assert "0.80.0" not in script and "0.81.0" not in script
    for asset, digest in WORKTRUNK_PINS.values():
        assert f"asset={asset}\n" in script and f"sha256={digest}\n" in script
        assert f"/download/v$version/$asset.tar.xz" in script


def worktrunk_release(path, machine, version="0.83.0"):
    """A disposable xz release archive whose single member reports `version`."""
    asset = WORKTRUNK_PINS[machine][0]
    payload = f'#!/bin/sh\n[ "$1" = --version ] && echo "wt v{version}"\nexit 0\n'.encode()
    with tarfile.open(path, "w:xz") as tar:
        member = tarfile.TarInfo(f"{asset}/wt")
        member.size, member.mode = len(payload), 0o755
        tar.addfile(member, io.BytesIO(payload))
    return hashlib.sha256(path.read_bytes()).hexdigest(), payload


@pytest.mark.parametrize("machine", sorted(WORKTRUNK_PINS))
def test_verified_worktrunk_release_installs_once_and_reapplies_without_download(tmp_path, machine):
    home, bin_dir, env = environment(tmp_path)
    asset, published = WORKTRUNK_PINS[machine]
    executable(bin_dir / "uname", f'#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo {machine}\n')
    if sys.platform == "darwin":
        # macOS hosts lack GNU sha256sum; Linux runs the real one unshimmed.
        executable(bin_dir / "sha256sum", '#!/bin/sh\nexec shasum -a 256 "$@"\n')
    release, urls = tmp_path / "worktrunk.tar.xz", tmp_path / "urls"
    digest, payload = worktrunk_release(release, machine)
    executable(bin_dir / "curl", f'''#!/bin/sh
while [ "$1" != -o ]; do url=$1; shift; done
printf '%s\\n' "$url" >>"{urls}"
cp "{release}" "$2"
''')
    # Only the published checksum gives way to the disposable archive; the
    # published value itself is pinned by the test above.
    script = render(WORKTRUNK)
    assert script.count(published) == 1
    script = script.replace(published, digest)
    installed = home / ".local/bin/wt"
    url = f"https://github.com/max-sixty/worktrunk/releases/download/v0.83.0/{asset}.tar.xz"
    for _ in range(2):
        result = subprocess.run(["bash"], input=script, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert urls.read_text().splitlines() == [url]
        assert installed.read_bytes() == payload
        assert installed.stat().st_mode & 0o777 == 0o755
        assert installed.stat().st_uid == os.getuid()


@pytest.mark.parametrize("fault,message", [
    ("checksum", "FAILED"),  # Printed by sha256sum and by the shasum shim alike.
    ("version", "managed Worktrunk version mismatch"),
])
def test_unverified_worktrunk_release_never_installs(tmp_path, fault, message):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    if sys.platform == "darwin":
        executable(bin_dir / "sha256sum", '#!/bin/sh\nexec shasum -a 256 "$@"\n')
    release = tmp_path / "worktrunk.tar.xz"
    published = WORKTRUNK_PINS["aarch64"][1]
    script = render(WORKTRUNK)
    if fault == "version":
        # A checksum that matches cannot vouch for the binary's own version.
        digest, _ = worktrunk_release(release, "aarch64", "0.84.0")
        script = script.replace(published, digest)
    else:
        release.write_bytes(b"not the published release")
    executable(bin_dir / "curl", f'''#!/bin/sh
while [ "$1" != -o ]; do shift; done
cp "{release}" "$2"
''')
    result = subprocess.run(["bash"], input=script, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert message in result.stdout + result.stderr
    assert not (home / ".local").exists()


def test_previous_pin_at_the_install_destination_is_never_replaced(tmp_path):
    home, bin_dir, env = environment(tmp_path)
    executable(bin_dir / "uname", '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo aarch64\n')
    previous = home / ".local/bin/wt"
    previous.parent.mkdir(parents=True)
    executable(previous, '#!/bin/sh\n[ "$1" = --version ] && echo "wt v0.80.0"; exit 0\n')
    original = previous.read_bytes()
    executable(bin_dir / "curl", '#!/bin/sh\necho download-attempted >&2; exit 99\n')
    result = subprocess.run(["bash"], input=render(WORKTRUNK), env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "ownership review required" in result.stderr
    assert "download-attempted" not in result.stderr
    assert previous.read_bytes() == original
    assert [path.relative_to(home).as_posix() for path in home.rglob("*")] == [".local", ".local/bin", ".local/bin/wt"]


@pytest.mark.parametrize("name", ["config.omarchy.example.toml", "config.omarchy-try.example.toml"])
def test_workstation_examples_declare_the_default_home_worktree_root(name):
    example = tomllib.loads((ROOT / name).read_text())["data"]["dotfiles_ai"]
    assert example["linux_workstation"] == {"enabled": True}
    assert example["remote_user_environment"] == {"enabled": False}
    assert example["workspaces"] == {"schema_version": 1, "root": "~/.local/state/worktrees"}
