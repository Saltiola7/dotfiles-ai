"""OST-001 optional Omarchy attack-surface toolchain gating and content."""
import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "run_onchange_after_install-blackarch-toolchain.sh.tmpl"
STRAP_URL = "https://blackarch.org/strap.sh"
STRAP_SHA = "dc0737cc75d64d03e9ec2212f989f17cdcf0162c2db5980e256093e293abfb8b"
CURATED = ("nmap", "masscan", "wireshark-qt", "testssl.sh", "ssh-audit",
           "sqlmap", "nikto", "zaproxy", "nuclei", "ffuf", "dirsearch",
           "metasploit", "exploitdb", "hashcat", "john", "seclists",
           "trivy", "syft", "grype")
RUNTIME_OWNED = ("semgrep", "gitleaks", "osv-scanner")


def render(data):
    command = ["chezmoi", "-S", str(ROOT), "--config", "/dev/null",
               "--config-format", "toml", "--override-data", json.dumps(data)]
    return subprocess.run(command + ["execute-template"], input=SCRIPT.read_text(),
                          check=True, capture_output=True, text=True).stdout


def test_gate_defaults_off_in_source_data():
    data = tomllib.loads((ROOT / ".chezmoidata.toml").read_text())
    assert data["dotfiles_ai"]["blackarch"]["enabled"] is False


def test_gate_off_render_exits_zero_without_side_effects():
    rendered = render({"dotfiles_ai": {"blackarch": {"enabled": False}}})
    assert "sudo" not in rendered and "pacman" not in rendered
    subprocess.run(["bash", "-n"], input=rendered, text=True, check=True)
    result = subprocess.run(["bash", "-c", rendered], capture_output=True, text=True)
    assert result.returncode == 0


def test_gate_on_render_pins_strap_and_curates_packages():
    rendered = render({"dotfiles_ai": {"blackarch": {"enabled": True}}})
    assert STRAP_URL in rendered and STRAP_SHA in rendered
    assert "sha256sum -c" in rendered
    for package in CURATED:
        assert package in rendered
    for owned in RUNTIME_OWNED:
        assert owned not in rendered
    assert "--needed" in rendered and "/etc/os-release" in rendered
    subprocess.run(["bash", "-n"], input=rendered, text=True, check=True)


def test_example_omarchy_config_documents_opt_in_gate():
    text = (ROOT / "config.omarchy.example.toml").read_text()
    assert "[data.dotfiles_ai.blackarch]" in text
    assert "enabled = false" in text.split("[data.dotfiles_ai.blackarch]")[1]
