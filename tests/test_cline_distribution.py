"""Opt-in Cline installation and isolated Vertex provider configuration."""

import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tomllib

import pytest

from test_portable_distribution import ROOT, data


def test_cline_features_default_off():
    defaults = tomllib.loads((ROOT / ".chezmoidata.toml").read_text())["dotfiles_ai"]
    for feature in ("cline_desktop", "cline_cli", "cline_vertex"):
        assert defaults[feature]["enabled"] is False


def chezmoi(*args, cli=False, desktop=False, vertex=False, platform="darwin", template=None,
            remote=False, check=True):
    configured = data(remote_user_environment=remote)
    configured["chezmoi"] = {"os": platform, "arch": "arm64"}
    configured["dotfiles_ai"].update({
        "cline_cli": {"enabled": cli},
        "cline_desktop": {"enabled": desktop},
        "cline_vertex": {"enabled": vertex, "model": "claude-sonnet-5-5@default"},
    })
    return subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(configured), *args],
        input=template, capture_output=True, text=True, check=check,
    )


@pytest.mark.parametrize("cli,desktop,vertex,platform", [
    (False, False, False, "darwin"),
    (True, False, False, "darwin"),
    (False, True, False, "darwin"),
    (True, True, True, "darwin"),
    (True, False, True, "linux"),
    (False, True, True, "linux"),
    (False, False, True, "darwin"),
])
def test_cline_managed_targets_follow_independent_flags(cli, desktop, vertex, platform):
    managed = set(chezmoi("managed", cli=cli, desktop=desktop, vertex=vertex,
                          platform=platform).stdout.splitlines())
    assert ("install-cline-cli.sh" in managed) is cli
    assert ("install-cline-desktop.sh" in managed) is (desktop and platform == "darwin")
    active_vertex = vertex and (cli or desktop and platform == "darwin")
    assert (".config/dotfiles-ai/cline-vertex.json" in managed) is active_vertex
    assert (".local/bin/cline-vertex" in managed) is active_vertex
    assert (".local/bin/cline-desktop" in managed) is (
        vertex and desktop and platform == "darwin"
    )


@pytest.mark.parametrize("flag", ["cli", "desktop", "vertex"])
def test_cline_flags_reject_string_false(flag):
    result = chezmoi("managed", **{flag: "false"}, check=False)
    assert result.returncode != 0


def render_script(name, **options):
    script = chezmoi("execute-template", template=(ROOT / name).read_text(), **options).stdout
    subprocess.run(["/bin/bash", "-n"], input=script, text=True, check=True)
    return script


def executable(path, body):
    path.write_text(body)
    path.chmod(0o755)
    return path


def shell_environment(tmp_path):
    home, bin_dir = tmp_path / "home", tmp_path / "bin"
    home.mkdir(mode=0o700)
    bin_dir.mkdir()
    return home, bin_dir, {
        "HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin",
        "TEST_LOG": str(tmp_path / "calls"),
    }


@pytest.mark.parametrize("name", [
    "run_onchange_after_install-cline-cli.sh.tmpl",
    "run_onchange_after_install-cline-desktop.sh.tmpl",
])
def test_disabled_cline_hook_never_invokes_installers(tmp_path, name):
    script = render_script(name)
    result = subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True,
                            env={"HOME": str(tmp_path), "PATH": "/not-present"})
    assert result.returncode == 0


def test_cli_installs_reviewed_package_only_when_missing(tmp_path):
    _, bin_dir, env = shell_environment(tmp_path)
    executable(bin_dir / "node", "#!/bin/sh\necho v26.12.1\n")
    executable(bin_dir / "npm", "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$TEST_LOG\"\n"
               "printf '#!/bin/sh\\necho 3.0.73\\n' > \"${PATH%%:*}/cline\"\n"
               "chmod +x \"${PATH%%:*}/cline\"\n")
    script = render_script("run_onchange_after_install-cline-cli.sh.tmpl", cli=True)
    for _ in range(2):
        result = subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True, env=env)
        assert result.returncode == 0, result.stderr
    assert Path(env["TEST_LOG"]).read_text().splitlines() == ["install --global cline@3.0.73"]


def test_existing_cli_keeps_its_installer_and_version(tmp_path):
    _, bin_dir, env = shell_environment(tmp_path)
    native = executable(bin_dir / "cline", "#!/bin/sh\necho 4.0.0\n")
    original = native.read_bytes()
    script = render_script("run_onchange_after_install-cline-cli.sh.tmpl", cli=True)
    result = subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True, env=env)
    assert result.returncode == 0, result.stderr
    assert native.read_bytes() == original
    assert not Path(env["TEST_LOG"]).exists()


def test_cli_installer_failure_propagates_without_fallback(tmp_path):
    _, bin_dir, env = shell_environment(tmp_path)
    executable(bin_dir / "node", "#!/bin/sh\necho v26.12.1\n")
    executable(bin_dir / "npm", "#!/bin/sh\necho npm-refused >&2\nexit 7\n")
    script = render_script("run_onchange_after_install-cline-cli.sh.tmpl", cli=True)
    result = subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True, env=env)
    assert result.returncode != 0
    assert "npm-refused" in result.stderr
    assert not (bin_dir / "cline").exists()


def test_existing_desktop_preserves_unmanaged_app(tmp_path):
    home, _, env = shell_environment(tmp_path)
    app = home / "Applications/Cline.app"
    app.mkdir(parents=True)
    marker = app / "retain"
    marker.write_text("existing application")
    script = render_script("run_onchange_after_install-cline-desktop.sh.tmpl", desktop=True)
    result = subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True, env=env)
    assert result.returncode == 0, result.stderr
    assert marker.read_text() == "existing application"


def test_vertex_template_reuses_existing_adc_selection():
    template = (ROOT / "private_dot_config/dotfiles-ai/private_cline-vertex.json.tmpl").read_text()
    configured = json.loads(chezmoi("execute-template", cli=True, vertex=True,
                                  template=template).stdout)
    inherited = data()["dotfiles_ai"]["opencode"]
    assert configured["project"] == inherited["vertex_project"]
    assert configured["region"] == inherited["vertex_location"]
    assert configured["credentials"] == inherited["vertex_credentials"]
    assert configured["cli_enabled"] is True
    assert configured["desktop_enabled"] is False
    assert configured["model"] == "claude-sonnet-5-5@default"
    assert configured["hub_port"] == 25464
    remote = json.loads(chezmoi("execute-template", cli=True, vertex=True, remote=True,
                               template=template).stdout)
    assert remote["credentials"].endswith("/.config/gcloud/application_default_credentials.json")
    assert remote["credentials"] != inherited["vertex_credentials"]


@pytest.fixture
def vertex_home(tmp_path):
    home, bin_dir, env = shell_environment(tmp_path)
    # All paths and credential content are synthetic and remain in the fixture.
    adc = home / "vertex/application_default_credentials.json"
    adc.parent.mkdir(mode=0o700)
    adc.write_text("{}\n")
    configuration = home / ".config/dotfiles-ai/cline-vertex.json"
    configuration.parent.mkdir(parents=True, mode=0o700)
    configuration.write_text(json.dumps({
        "project": "example-project", "region": "global", "credentials": str(adc),
        "model": "claude-sonnet-5-5@default", "cli_enabled": True, "desktop_enabled": False,
        "hub_port": 25464,
    }))
    configuration.chmod(0o600)
    settings = home / ".cline-vertex/data/settings/providers.json"
    settings.parent.mkdir(parents=True, mode=0o700)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    return home, bin_dir, env, configuration, settings, adc


def helper(env, *args, source=None):
    return subprocess.run([sys.executable, str(source or ROOT / "dot_local/bin/executable_cline-vertex"),
                           *args], capture_output=True, text=True, env=env)


def test_vertex_merge_preserves_native_settings_and_private_preimage(vertex_home):
    home, _, env, _, settings, _ = vertex_home
    before = {
        "version": 1, "lastUsedProvider": "anthropic",
        "modes": {"voiceInput": {"providerId": "openai", "modelId": "whisper-1"}},
        "nativePreference": "retain",
        "providers": {
            "anthropic": {"settings": {"provider": "anthropic", "apiKey": "synthetic-secret",
                                       "model": "claude-sonnet-5-5"},
                          "updatedAt": "2026-10-24T00:00:00.000Z", "tokenSource": "manual"},
            "vertex": {"settings": {"provider": "vertex", "model": "prior-model",
                                     "gcp": {"projectId": "prior-project", "region": "us-east5",
                                             "futureField": "retain"},
                                     "futureSetting": True}, "futureProviderField": "retain",
                       "updatedAt": "2026-10-24T00:00:00.000Z", "tokenSource": "manual"},
        },
    }
    original = json.dumps(before, indent=2).encode()
    settings.write_bytes(original)
    result = helper(env, "--configure")
    assert result.returncode == 0, result.stderr
    after = json.loads(settings.read_text())
    assert after["lastUsedProvider"] == "vertex"
    assert after["modes"] == before["modes"]
    assert after["nativePreference"] == "retain"
    assert after["providers"]["anthropic"] == before["providers"]["anthropic"]
    vertex = after["providers"]["vertex"]
    assert vertex["settings"] == {
        "provider": "vertex", "model": "claude-sonnet-5-5@default",
        "gcp": {"projectId": "example-project", "region": "global", "futureField": "retain"},
        "futureSetting": True,
    }
    assert vertex["futureProviderField"] == "retain"
    backup = home / ".config/dotfiles-ai/backups/cline" / (hashlib.sha256(original).hexdigest() + ".json")
    assert backup.read_bytes() == original
    assert backup.stat().st_mode & 0o777 == 0o600
    assert settings.stat().st_mode & 0o777 == 0o600
    assert "synthetic-secret" not in result.stdout + result.stderr
    recorded = (settings.read_bytes(), settings.stat().st_mtime_ns)
    assert helper(env, "--configure").returncode == 0
    assert (settings.read_bytes(), settings.stat().st_mtime_ns) == recorded


@pytest.mark.parametrize("content", [
    "not JSON", "[]", '{"version": 2, "providers": {}}',
    '{"version": 1, "providers": []}',
    '{"version": 1, "providers": {"vertex": {"settings": []}}}',
    '{"version": 1, "providers": {"vertex": {"settings": {"gcp": []}}}}',
])
def test_vertex_refuses_unknown_or_malformed_native_settings(vertex_home, content):
    _, _, env, _, settings, _ = vertex_home
    settings.write_text(content)
    result = helper(env, "--configure")
    assert result.returncode != 0
    assert settings.read_text() == content


@pytest.mark.parametrize("case", [
    "unrelated-provider-null", "settings-list", "missing-updated-at", "invalid-updated-at",
    "invalid-token-source", "invalid-provider-id", "invalid-routing-provider", "voice-input-list",
    "voice-input-missing-provider", "voice-input-invalid-model",
])
def test_vertex_refuses_malformed_native_entries_and_voice_preferences(vertex_home, case):
    _, _, env, _, settings, _ = vertex_home
    stored = {"version": 1, "providers": {"anthropic": {
        "settings": {"provider": "anthropic", "model": "claude-sonnet-5-5"},
        "updatedAt": "2026-10-24T00:00:00.000Z", "tokenSource": "manual",
    }}, "modes": {"voiceInput": {"providerId": "openai", "modelId": "whisper-1"}}}
    provider = stored["providers"]["anthropic"]
    if case == "unrelated-provider-null":
        stored["providers"]["anthropic"] = None
    elif case == "settings-list":
        provider["settings"] = []
    elif case == "missing-updated-at":
        provider.pop("updatedAt")
    elif case == "invalid-updated-at":
        provider["updatedAt"] = "not-a-datetime"
    elif case == "invalid-token-source":
        provider["tokenSource"] = "unsupported-source"
    elif case == "invalid-provider-id":
        provider["settings"]["provider"] = 12
    elif case == "invalid-routing-provider":
        provider["settings"]["routingProviderId"] = "invalid/provider"
    elif case == "voice-input-list":
        stored["modes"]["voiceInput"] = []
    elif case == "voice-input-missing-provider":
        stored["modes"]["voiceInput"].pop("providerId")
    elif case == "voice-input-invalid-model":
        stored["modes"]["voiceInput"]["modelId"] = 12
    original = json.dumps(stored)
    settings.write_text(original)
    assert helper(env, "--configure").returncode != 0
    assert settings.read_text() == original


def test_vertex_configuration_leaves_default_native_cline_state_untouched(vertex_home):
    home, _, env, _, settings, _ = vertex_home
    native = home / ".cline/data/settings/providers.json"
    native.parent.mkdir(parents=True)
    native.write_text("native-default-state-is-not-managed")
    before = (native.read_bytes(), native.stat().st_mtime_ns)
    assert helper(env, "--configure").returncode == 0
    assert settings.exists()
    assert (native.read_bytes(), native.stat().st_mtime_ns) == before


def test_vertex_refuses_symlinked_provider_ancestor(vertex_home, tmp_path):
    _, _, env, _, settings, _ = vertex_home
    real = tmp_path / "outside-settings"
    settings.parent.rmdir()
    real.mkdir()
    settings.parent.symlink_to(real, target_is_directory=True)
    original = '{"version":1,"providers":{}}'
    settings.write_text(original)
    result = helper(env, "--configure")
    assert result.returncode != 0
    assert settings.read_text() == original


@pytest.mark.parametrize("field,value", [
    ("project", ""), ("region", ""), ("model", ""),
    ("credentials", "relative/application_default_credentials.json"),
    ("hub_port", 0), ("hub_port", 65536), ("hub_port", True), ("hub_port", "25464"),
])
def test_vertex_refuses_incomplete_configuration_before_native_write(vertex_home, field, value):
    _, _, env, configuration, settings, _ = vertex_home
    selected = json.loads(configuration.read_text())
    selected[field] = value
    configuration.write_text(json.dumps(selected))
    assert helper(env, "--configure").returncode != 0
    assert not settings.exists()


def test_vertex_launch_overrides_ambient_credentials_and_forwards_arguments(vertex_home):
    home, bin_dir, env, _, settings, adc = vertex_home
    executable(bin_dir / "cline", f"#!{sys.executable}\n"
               "import json, os, sys\n"
               "if sys.argv[1:] == ['--version']: print('3.0.73')\n"
               "else: print(json.dumps({'args': sys.argv[1:], 'adc': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),"
               " 'config': os.environ.get('CLOUDSDK_CONFIG'), 'override': os.environ.get('CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE'),"
               " 'active': os.environ.get('CLOUDSDK_ACTIVE_CONFIG_NAME'),"
               " 'cline_dir': os.environ.get('CLINE_DIR'), 'cline_data': os.environ.get('CLINE_DATA_DIR'),"
               " 'cline_providers': os.environ.get('CLINE_PROVIDER_SETTINGS_PATH'),"
               " 'hub_host': os.environ.get('CLINE_HUB_HOST'), 'hub_port': os.environ.get('CLINE_HUB_PORT'),"
               " 'session_data': os.environ.get('CLINE_SESSION_DATA_DIR'), 'db_data': os.environ.get('CLINE_DB_DATA_DIR')}))\n")
    env.update({"GOOGLE_APPLICATION_CREDENTIALS": "/incorrect/adc.json",
                "CLOUDSDK_CONFIG": "/incorrect/config",
                "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE": "/incorrect/override.json",
                "CLOUDSDK_ACTIVE_CONFIG_NAME": "incorrect",
                "CLINE_DIR": "/incorrect/cline", "CLINE_DATA_DIR": "/incorrect/data",
                "CLINE_PROVIDER_SETTINGS_PATH": "/incorrect/providers.json",
                "CLINE_HUB_HOST": "incorrect.example", "CLINE_HUB_PORT": "1",
                "CLINE_SESSION_DATA_DIR": "/incorrect/sessions", "CLINE_DB_DATA_DIR": "/incorrect/db"})
    assert helper(env, "--configure").returncode == 0
    result = helper(env, "--", "--plan", "synthetic prompt with spaces")
    assert result.returncode == 0, result.stderr
    received = json.loads(result.stdout)
    assert received == {"args": ["--plan", "synthetic prompt with spaces"],
                        "adc": str(adc), "config": str(adc.parent),
                        "override": None, "active": None,
                        "cline_dir": str(home / ".cline-vertex"),
                        "cline_data": str(home / ".cline-vertex/data"),
                        "cline_providers": str(settings),
                        "hub_host": "127.0.0.1", "hub_port": "25464",
                        "session_data": None, "db_data": None}
    assert env["GOOGLE_APPLICATION_CREDENTIALS"] == "/incorrect/adc.json"
    assert env["CLINE_DIR"] == "/incorrect/cline"


def test_vertex_launch_refuses_cli_2_without_starting_task(vertex_home):
    _, bin_dir, env, _, _, _ = vertex_home
    executable(bin_dir / "cline", "#!/bin/sh\n"
               "if [ \"$1\" = --version ]; then echo 2.13.0; else echo task-started; fi\n")
    assert helper(env, "--configure").returncode == 0
    result = helper(env, "--", "synthetic task")
    assert result.returncode != 0
    assert "task-started" not in result.stdout


def test_vertex_launch_refuses_missing_adc_without_authentication(vertex_home):
    _, _, env, _, _, adc = vertex_home
    assert helper(env, "--configure").returncode == 0
    adc.unlink()
    result = helper(env, "--check")
    assert result.returncode != 0
    assert "vertex-reauth" in result.stderr


@pytest.mark.parametrize("override", [
    ["--config", "/synthetic/alternate-config"],
    ["--config=/synthetic/alternate-config"],
    ["--data-dir", "/synthetic/alternate-state"],
    ["--data-dir=/synthetic/alternate-state"],
])
def test_vertex_refuses_native_path_arguments_before_write_or_launch(vertex_home, override):
    _, bin_dir, env, _, settings, _ = vertex_home
    executable(bin_dir / "cline", "#!/bin/sh\necho native-invoked >> \"$TEST_LOG\"\necho 3.0.73\n")
    result = helper(env, "--", *override, "synthetic task")
    assert result.returncode != 0
    assert not settings.exists()
    assert not Path(env["TEST_LOG"]).exists()
    assert helper(env, "--configure").returncode == 0
    before = (settings.read_bytes(), settings.stat().st_mtime_ns)
    result = helper(env, "--", *override, "synthetic task")
    assert result.returncode != 0
    assert (settings.read_bytes(), settings.stat().st_mtime_ns) == before
    assert not Path(env["TEST_LOG"]).exists()


def test_vertex_check_is_read_only_and_does_not_start_task(vertex_home):
    home, bin_dir, env, _, settings, _ = vertex_home
    executable(bin_dir / "cline", "#!/bin/sh\n"
               "if [ \"$1\" = --version ]; then echo 3.0.73; else echo task-started; fi\n")
    assert helper(env, "--configure").returncode == 0
    before = (settings.read_bytes(), settings.stat().st_mtime_ns)
    files = sorted(path.relative_to(home) for path in home.rglob("*"))
    result = helper(env, "--check")
    assert result.returncode == 0, result.stderr
    assert "task-started" not in result.stdout
    assert (settings.read_bytes(), settings.stat().st_mtime_ns) == before
    assert sorted(path.relative_to(home) for path in home.rglob("*")) == files


@pytest.mark.skipif(sys.platform != "darwin", reason="Desktop native launcher is macOS-only")
def test_desktop_launcher_reads_bundle_and_supplies_isolated_adc(vertex_home):
    home, _, env, configuration, _, adc = vertex_home
    selected = json.loads(configuration.read_text())
    selected.update(cli_enabled=False, desktop_enabled=True)
    configuration.write_text(json.dumps(selected))
    contents = home / "Applications/Cline.app/Contents"
    (contents / "MacOS").mkdir(parents=True)
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleExecutable": "cline-fixture"}, stream)
    executable(contents / "MacOS/cline-fixture", f"#!{sys.executable}\n"
               "import json, os, sys\n"
               "print(json.dumps({'args':sys.argv[1:], 'adc':os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),"
               " 'cline_dir':os.environ.get('CLINE_DIR'), 'hub_host':os.environ.get('CLINE_HUB_HOST'),"
               " 'hub_port':os.environ.get('CLINE_HUB_PORT')}))\n")
    # Redirect only the system installation locator: tests must never launch a
    # real Cline application if one is installed on the developer's host.
    original = (ROOT / "dot_local/bin/executable_cline-vertex").read_text()
    locator = 'Path("/Applications/Cline.app")'
    assert original.count(locator) == 1
    isolated = home.parent / "isolated-cline-vertex"
    isolated.write_text(original.replace(locator, f"Path({str(home.parent / 'absent-system-app')!r})"))
    assert helper(env, "--configure", source=isolated).returncode == 0
    checked = helper(env, "--desktop", "--check", source=isolated)
    assert checked.returncode == 0, checked.stderr
    assert not checked.stdout.startswith("{")
    env.update(CLINE_DIR="/incorrect/cline", CLINE_HUB_HOST="incorrect.example", CLINE_HUB_PORT="1")
    launched = helper(env, "--desktop", "--", "--new-window", "example workspace", source=isolated)
    assert launched.returncode == 0, launched.stderr
    assert json.loads(launched.stdout) == {
        "args": ["--new-window", "example workspace"], "adc": str(adc),
        "cline_dir": str(home / ".cline-vertex"), "hub_host": "127.0.0.1", "hub_port": "25464",
    }
