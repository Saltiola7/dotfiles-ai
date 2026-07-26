import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def data(onepassword: bool = False) -> dict:
    return {
        "dotfiles_ai": {
            "distribution": {"repository": "https://github.com/example/dotfiles-ai.git"},
            "opencode": {
                "bedrock_region": "eu-west-1",
                "bedrock_profile": "local-profile",
                "default_model": "openai/gpt-5.6-sol",
                "small_model": "openai/gpt-5.6-terra",
                "lmstudio_base_url": "http://localhost:1234/v1",
                "theme": "catppuccin",
            },
            "herdr": {
                "theme": "nord",
                "launchagent": True,
                "executable": "/usr/local/bin/herdr",
            },
            "sandbox": {
                "enabled": True,
                "build_workspace": "workspace1",
                "cpus": 4,
                "memory_gib": 8,
                "disk_gib": 60,
                "workspaces": [
                    {
                        "name": "workspace1", "instance": "workspace1-sandbox", "shell_alias": "workspace1sh", "federate": True,
                        "mounts": [{
                            "host": "/workspace/projects", "guest": "/workspace/projects", "writable": True,
                            "protect_git_submodules": False, "reference_name": "", "reference_description": "", "reference_subpath": "",
                        }],
                    },
                    {
                        "name": "workspace2", "instance": "workspace2-sandbox", "shell_alias": "workspace2sh", "federate": False,
                        "mounts": [{
                            "host": "/workspace/reference", "guest": "/workspace/reference", "writable": False,
                            "protect_git_submodules": False, "reference_name": "project-reference",
                            "reference_description": "Project reference.", "reference_subpath": "",
                        }],
                    },
                ],
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
    assert config["theme"] == "catppuccin"

    herdr = chezmoi("cat", str(Path.home() / ".config/herdr/config.toml")).stdout
    plist = chezmoi(
        "cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist")
    ).stdout
    assert 'name = "nord"' in herdr
    assert "/usr/local/bin/herdr" in plist


def test_portable_terminal_config_is_guest_only() -> None:
    host = set(chezmoi("managed").stdout.splitlines())
    targets = {".bashrc", ".bash_profile", ".common_profile", ".config/starship.toml"}

    assert targets.isdisjoint(host)
    assert (ROOT / "dot_bashrc").read_text().count('eval "$(starship init bash)"') == 1
    assert (ROOT / "dot_bash_profile").exists()
    assert (ROOT / "dot_common_profile.tmpl").exists()
    assert (ROOT / "private_dot_config/starship.toml").exists()
    ignore = (ROOT / ".chezmoiignore").read_text()
    assert '{{ if eq .chezmoi.os "darwin" }}' in ignore
    assert all(target in ignore for target in targets)


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


def test_dynamic_workspace_registry_and_template_render() -> None:
    registry = json.loads(chezmoi(
        "cat", str(Path.home() / ".config/dotfiles-ai/sandbox.json")
    ).stdout)
    assert registry["enabled"] is True
    assert registry["schema_version"] == 3
    assert registry["build_workspace"] == "workspace1"
    assert [workspace["name"] for workspace in registry["workspaces"]] == ["workspace1", "workspace2"]
    assert [workspace["shell_alias"] for workspace in registry["workspaces"]] == ["workspace1sh", "workspace2sh"]
    assert registry["workspaces"][1]["mounts"][0]["writable"] is False
    template = chezmoi("cat", str(Path.home() / ".config/dotfiles-ai/lima/workspace.yaml")).stdout
    assert 'disk: "60GiB"' in template
    assert "@@MOUNTS@@" in template
    assert "@@WORKSPACE_JSON@@" in template


def test_shell_alias_reconciler_refuses_unmanaged_command(tmp_path: Path) -> None:
    script = chezmoi(
        "execute-template", "--file",
        str(ROOT / "run_onchange_after_reconcile-sandbox-shell-aliases.sh.tmpl"),
    ).stdout
    command = tmp_path / ".local/bin/workspace1sh"
    command.parent.mkdir(parents=True)
    command.write_text("unmanaged\n")
    controller = command.parent / "sandbox-vm"
    controller.write_text("#!/bin/sh\n")
    controller.chmod(0o755)

    result = subprocess.run(
        ["sh"], input=script, text=True, capture_output=True,
        env={**os.environ, "HOME": str(tmp_path)},
    )

    assert result.returncode != 0
    assert "refusing to replace unmanaged command" in result.stderr
    assert command.read_text() == "unmanaged\n"


def test_shell_alias_reconciler_replaces_managed_alias_set(tmp_path: Path) -> None:
    script = chezmoi(
        "execute-template", "--file",
        str(ROOT / "run_onchange_after_reconcile-sandbox-shell-aliases.sh.tmpl"),
    ).stdout
    bin_dir = tmp_path / ".local/bin"
    state = tmp_path / ".config/dotfiles-ai/sandbox-shell-aliases"
    bin_dir.mkdir(parents=True)
    state.parent.mkdir(parents=True)
    controller = bin_dir / "sandbox-vm"
    controller.write_text("#!/bin/sh\n")
    controller.chmod(0o755)
    (bin_dir / "oldsh").symlink_to(controller)
    state.write_text("oldsh\n")

    subprocess.run(
        ["sh"], input=script, text=True, check=True,
        env={**os.environ, "HOME": str(tmp_path)},
    )

    assert not (bin_dir / "oldsh").exists()
    assert (bin_dir / "workspace1sh").resolve() == controller
    assert (bin_dir / "workspace2sh").resolve() == controller
    assert state.read_text().splitlines() == ["workspace1sh", "workspace2sh"]


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
        for value in (
            "m" + "gm",
            "personal" + "-sandbox",
            "personal" + "_instance",
            "personal" + "_root",
            "seo" + "_data_science_path",
            "seo" + "-data-science",
            "seo" + "-code-analysis",
        ):
            assert value not in body.lower(), f"legacy identifier in {path.relative_to(ROOT)}"
