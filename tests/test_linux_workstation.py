import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_native_workstation_manages_agents_without_desktop_or_vms():
    data = {
        "chezmoi": {"os": "linux", "arch": "amd64"},
        "dotfiles_ai": {
            "linux_workstation": {"enabled": True},
            "remote_user_environment": {"enabled": False},
            "sandbox": {"enabled": False},
            "herdr": {"host_enabled": False, "launchagent": False},
            "state": {"root": "/var/lib/dotfiles-ai/example"},
        },
    }
    command = ["chezmoi", "-S", str(ROOT), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(data)]
    managed = subprocess.run(command + ["managed"], check=True, capture_output=True, text=True).stdout.splitlines()
    for path in (".local/bin/codex", ".local/bin/opencode", ".local/bin/opencode-install",
                 ".local/bin/dotfiles-ai-omarchy-setup"):
        assert path in managed
    for path in (".bashrc", ".common_profile", ".local/bin/docker", ".local/bin/sandbox-vm"):
        assert path not in managed
    assert not any(path.startswith("Library/") for path in managed)
    for source in ("dot_local/bin/executable_codex.tmpl", "dot_local/bin/executable_opencode.tmpl"):
        rendered = subprocess.run(command + ["execute-template"], input=(ROOT / source).read_text(),
                                  check=True, capture_output=True, text=True).stdout
        assert "/var/lib/dotfiles-ai/example" in rendered
        assert "--resolve-native" not in rendered
        assert "codex-native" not in rendered
        subprocess.run(["bash", "-n"], input=rendered, text=True, check=True)
