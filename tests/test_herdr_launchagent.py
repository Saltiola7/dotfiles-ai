import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_herdr_server_runs_in_aqua_without_secrets() -> None:
    plist = (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist.tmpl").read_text()
    loader = (ROOT / "run_onchange_load-herdr-launchagent.sh.tmpl").read_text()

    assert "<key>LimitLoadToSessionType</key>\n    <string>Aqua</string>" in plist
    assert "<key>KeepAlive</key>" in plist
    assert "<key>LANG</key>\n        <string>en_US.UTF-8</string>" in plist
    assert "OP_SERVICE_ACCOUNT_TOKEN" not in plist + loader
    assert "launchctl bootstrap" in loader
    assert "herdr server stop" not in loader
    assert "unmanaged server owns the socket" in loader
    assert "status server" in loader
    assert "kickstart" not in loader
    assert "com" + ".tis" not in plist + loader


def test_herdr_launchagent_renders_valid_plist_and_disable_transition(tmp_path) -> None:
    values = {
        "dotfiles_ai": {
            "opencode": {
                "bedrock_region": "us-west-2", "bedrock_profile": "",
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
    assert "/tmp/a&amp;b/herdr" in rendered.stdout

    values["dotfiles_ai"]["herdr"]["launchagent"] = False
    disabled = subprocess.run(
        [*base[:-1], json.dumps(values), "cat", str(Path.home() / "load-herdr-launchagent.sh")],
        text=True, capture_output=True, check=True,
    ).stdout
    assert 'launchctl bootout "$DOMAIN/$LABEL"' in disabled
    assert "PlistBuddy -c 'Print :Label'" in disabled
    assert '[[ "$PLIST_LABEL" == "$LABEL" ]]' in disabled
    assert 'rm -f "$PLIST"' in disabled
