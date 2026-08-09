import json
import plistlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_herdr_server_runs_in_aqua_without_secrets() -> None:
    plist = (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist.tmpl").read_text()
    loader = (ROOT / "run_onchange_load-herdr-launchagent.sh.tmpl").read_text()

    assert "<key>LimitLoadToSessionType</key>\n    <string>Aqua</string>" in plist
    assert "<key>KeepAlive</key>" in plist
    assert "<key>SuccessfulExit</key>" in plist
    assert "<key>LANG</key>\n        <string>en_US.UTF-8</string>" in plist
    assert '{{ .chezmoi.homeDir | html }}/.local/bin:/opt/homebrew/bin' in plist
    assert "OP_SERVICE_ACCOUNT_TOKEN" not in plist + loader
    assert "launchctl bootstrap" in loader
    assert '"$HERDR" server stop' not in loader
    assert "unmanaged server owns the socket" in loader
    assert "status server" in loader
    assert "for _ in {1..50}" in loader
    assert "managed server did not stop within 5 seconds" in loader
    assert "kickstart" not in loader
    assert "com" + ".tis" not in plist + loader


def test_herdr_launchagent_renders_valid_plist_and_disable_transition(tmp_path) -> None:
    values = {
        "dotfiles_ai": {
            "opencode": {
                "vertex_project": "", "vertex_location": "global", "vertex_credentials": "",
                "default_model": "openai/gpt-5.6-sol",
                "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://localhost:1234/v1",
            },
            "herdr": {
                "theme": "nord", "launchagent": True,
                "executable": "/tmp/a&b/herdr",
            },
            "onepassword": {
                "enabled": False, "account": "", "user_uuid": "",
                "keychain_service": "op-service-account-token",
            },
        }
    }
    base = [
        "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
        "--config-format", "toml", "--override-data", json.dumps(values),
    ]
    target = str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist")
    rendered = subprocess.run([*base, "cat", target], text=True, capture_output=True, check=True)
    plist = tmp_path / "herdr.plist"
    plist.write_text(rendered.stdout)
    subprocess.run(["plutil", "-lint", str(plist)], check=True, capture_output=True)
    assert "/.local/bin/herdr-server-owner" in rendered.stdout
    wrapper = subprocess.run(
        [*base, "cat", str(Path.home() / ".local/bin/herdr-server-owner")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert '/tmp/a&b/herdr' in wrapper
    assert "status server" in wrapper
    assert '"running":true' in wrapper

    values["dotfiles_ai"]["herdr"]["launchagent"] = False
    disabled = subprocess.run(
        [*base[:-1], json.dumps(values), "cat", str(Path.home() / "load-herdr-launchagent.sh")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert 'launchctl bootout "$DOMAIN/$LABEL"' in disabled
    assert "PlistBuddy -c 'Print :Label'" in disabled
    assert '[[ "$PLIST_LABEL" == "$LABEL" ]]' in disabled
    assert 'rm -f "$PLIST"' in disabled


def test_unmanaged_server_keeps_launchagent_handoff_pending(tmp_path) -> None:
    calls = tmp_path / "calls"
    launchctl = tmp_path / "launchctl"
    herdr = tmp_path / "herdr"
    launchctl.write_text(
        '#!/bin/bash\nprintf "launchctl %s\\n" "$1" >> "$CALLS"\n[[ "$1" == print ]] && exit 1\nexit 99\n'
    )
    herdr.write_text(
        '#!/bin/bash\nprintf "herdr %s\\n" "$*" >> "$CALLS"\n'
        '[[ "$*" == "status server --json" ]] && printf \'{"running":true}\\n\'\n'
    )
    launchctl.chmod(0o755)
    herdr.chmod(0o755)

    values = {
        "dotfiles_ai": {
            "opencode": {
                "vertex_project": "", "vertex_location": "global", "vertex_credentials": "",
                "default_model": "openai/gpt-5.6-sol",
                "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://localhost:1234/v1",
            },
            "herdr": {"theme": "nord", "launchagent": True, "executable": str(herdr)},
            "onepassword": {
                "enabled": False, "account": "", "user_uuid": "",
                "keychain_service": "op-service-account-token",
            },
        }
    }
    loader = subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(values),
            "cat", str(Path.home() / "load-herdr-launchagent.sh"),
        ],
        text=True, capture_output=True, check=True,
    ).stdout.replace("/bin/launchctl", str(launchctl))
    home = tmp_path / "home"
    plist = home / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist"
    plist.parent.mkdir(parents=True)
    plist.touch()

    result = subprocess.run(
        ["bash"], input=loader, text=True, capture_output=True,
        env={"HOME": str(home), "CALLS": str(calls), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 1
    assert "run 'herdr server stop', then rerun chezmoi apply" in result.stderr
    assert calls.read_text().splitlines() == ["launchctl print", "herdr status server --json"]


def test_centralized_state_renders_herdr_and_launchagent_environment() -> None:
    values = {"dotfiles_ai": {"state": {"root": "/Volumes/ext/state"}}}
    base = [
        "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
        "--config-format", "toml", "--override-data", json.dumps(values),
    ]
    config = subprocess.run(
        [*base, "cat", str(Path.home() / ".config/herdr/config.toml")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert '[worktrees]\ndirectory = "/Volumes/ext/state/herdr/worktrees"' in config

    expected = {
        "DOTFILES_AI_STATE_ROOT": "/Volumes/ext/state",
        "XDG_DATA_HOME": "/Volumes/ext/state/xdg/data",
        "XDG_STATE_HOME": "/Volumes/ext/state/xdg/state",
        "DBSCTR_STATE_ROOT": "/Volumes/ext/state/dbsctr",
        "DBSCTR_WORKTREE_ROOT": "/Volumes/ext/state/dbsctr/worktrees",
        "DBSCTR_RND_STATE": "/Volumes/ext/state/dbsctr/rnd/dbsctr-rnd.sqlite3",
        "DBSCTR_RND_RECEIPTS": "/Volumes/ext/state/dbsctr/rnd/receipts",
        "HERMES_HOME": "/Volumes/ext/state/hermes",
    }
    for name in ("herdr-server", "dbsctr-spawner", "dbsctr-watchdog"):
        rendered = subprocess.run(
            [*base, "execute-template", "--file",
             str(ROOT / f"private_Library/LaunchAgents/dev.dotfiles-ai.{name}.plist.tmpl")],
            text=True, capture_output=True, check=True,
        ).stdout
        assert plistlib.loads(rendered.encode())["EnvironmentVariables"].items() >= expected.items()


def test_native_state_does_not_render_centralized_environment() -> None:
    plist = (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist.tmpl").read_text()
    config = (ROOT / "private_dot_config/herdr/config.toml.tmpl").read_text()
    assert "DOTFILES_AI_STATE_ROOT" not in subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml", "cat",
         str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert "[worktrees]" not in subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml", "cat",
         str(Path.home() / ".config/herdr/config.toml")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert "DOTFILES_AI_STATE_ROOT" in plist and "[worktrees]" in config


def test_centralized_state_scopes_opencode_runtime_environment() -> None:
    values = {"dotfiles_ai": {"state": {"root": "/Volumes/ext/state"}}}
    rendered = subprocess.run(
        ["chezmoi", "-S", str(ROOT), "--config", "/dev/null", "--config-format", "toml",
         "--override-data", json.dumps(values), "cat", str(Path.home() / ".local/bin/opencode")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert 'export HERMES_HOME="/Volumes/ext/state/hermes"' in rendered
    assert 'export DBSCTR_WORKTREE_ROOT="/Volumes/ext/state/dbsctr/worktrees"' in rendered
    assert 'export XDG_DATA_HOME="/Volumes/ext/state/xdg/data"' in rendered
    assert "exec /opt/homebrew/bin/opencode" in rendered
