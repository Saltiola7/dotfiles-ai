import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def data(onepassword: bool = False) -> dict:
    return {
        "dotfiles_ai": {
            "opencode": {
                "bedrock_region": "eu-west-1",
                "bedrock_profile": "local-profile",
                "default_model": "openai/gpt-5.6-sol",
                "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://localhost:1234/v1",
            },
            "herdr": {
                "theme": "nord",
                "launchagent": True,
                "executable": "/usr/local/bin/herdr",
            },
            "onepassword": {
                "enabled": onepassword,
                "account": "local-account",
                "user_uuid": "LOCALUUID",
                "keychain_service": "local-service",
            },
        }
    }


def chezmoi(*args: str, onepassword: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data",
            json.dumps(data(onepassword)), *args,
        ],
        text=True,
        capture_output=True,
        check=True,
    )


def test_local_data_renders_complete_configs() -> None:
    config = json.loads(
        chezmoi("cat", str(Path.home() / ".config/opencode/opencode.json")).stdout
    )
    assert config["provider"]["amazon-bedrock"]["options"] == {
        "region": "eu-west-1",
        "profile": "local-profile",
    }
    assert config["provider"]["lmstudio"]["options"]["baseURL"] == "http://localhost:1234/v1"

    herdr = chezmoi("cat", str(Path.home() / ".config/herdr/config.toml")).stdout
    plist = chezmoi(
        "cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist")
    ).stdout
    assert 'name = "nord"' in herdr
    assert "/usr/local/bin/herdr" in plist


def test_onepassword_helper_is_opt_in_and_localized() -> None:
    disabled = chezmoi("managed").stdout.splitlines()
    assert ".local/bin/op-session" not in disabled

    enabled = chezmoi("managed", onepassword=True).stdout.splitlines()
    assert ".local/bin/op-session" in enabled
    helper = chezmoi(
        "cat", str(Path.home() / ".local/bin/op-session"), onepassword=True
    ).stdout
    assert '__OP_USER_UUID="LOCALUUID"' in helper
    assert '__OP_ACCOUNT="local-account"' in helper
    assert '__OP_KEYCHAIN_SERVICE="local-service"' in helper


def test_onepassword_helper_supports_noclobber(tmp_path: Path) -> None:
    helper = tmp_path / "op-session"
    helper.write_text(chezmoi(
        "cat", str(Path.home() / ".local/bin/op-session"), onepassword=True
    ).stdout)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    security = bin_dir / "security"
    security.write_text("#!/bin/bash\nprintf service-token\n")
    security.chmod(0o755)
    op = bin_dir / "op"
    op.write_text(
        '#!/bin/bash\n[ "$*" = "vault list" ] && '
        '[ "$OP_SERVICE_ACCOUNT_TOKEN" = "service-token" ]\n'
    )
    op.chmod(0o755)

    result = subprocess.run(
        ["bash", "-c", 'set -C; source "$1"', "bash", str(helper)],
        env={
            **os.environ,
            "HERDR_ENV": "1",
            "HOME": str(tmp_path),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_public_tree_has_no_maintainer_identifiers() -> None:
    banned = (
        "/Users/" + "tis",
        "302432" + "775606",
        "KZRNJU45" + "TFHCFMB22WI6VCJVDY",
        "Bedrock" + "DeveloperAccess",
        "com" + ".tis",
    )
    files = [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not {".git", ".venv", "__pycache__"}.intersection(path.parts)
        and path.suffix != ".pyc"
    ]
    for path in files:
        body = path.read_text(errors="ignore")
        for value in banned:
            assert value not in body, f"{value} in {path.relative_to(ROOT)}"
