import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def data(
    onepassword: bool = False,
    vertex: bool = True,
    vertex_account: str = "user@example.com",
    vertex_credentials: str = "/tmp/application_default_credentials.json",
    pm_image: str = "",
    pm_backup_dir: str = "/Volumes/ext/state/pm-kernel/backups",
    state_root: str = "/Volumes/ext/state",
) -> dict:
    return {
        "dotfiles_ai": {
            "distribution": {"repository": "https://github.com/example/dotfiles-ai.git"},
            "state": {"root": state_root},
            "opencode": {
                "vertex_project": "example-project" if vertex else "",
                "vertex_location": "global",
                "vertex_credentials": vertex_credentials,
                "vertex_account": vertex_account,
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
            "hermes": {
                "enabled": True, "executable": "~/.local/bin/hermes", "profile": "system",
                "provider": "openai-codex", "backlog_roots": ["/workspace/projects"],
                "project_profiles": False,
            },
            "atuin": {"sync_address": "https://atuin.example.com", "server_enabled": False},
            "tailscale": {"enabled": False, "ssh": False},
            "sandbox": {
                "enabled": True,
                "build_workspace": "workspace1",
                "atuin_workspace": "workspace1",
                "lima_home": "/Volumes/ext/state/lima",
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
            "pm_kernel": {
                "enabled": bool(pm_image),
                "workspace": "workspace1" if pm_image else "",
                "postgres_enabled": bool(pm_image),
                "postgres_image": pm_image,
                "postgres_password_ref": "op://Private/PM Kernel/password" if pm_image else "",
                "postgres_backup_dir": pm_backup_dir if pm_image else "",
                "jira_adapter": "fake",
                "jira_project": "",
                "jira_issue_types": [],
            },
        }
    }


def chezmoi(
    *args: str,
    onepassword: bool = False,
    vertex: bool = True,
    vertex_account: str = "user@example.com",
    vertex_credentials: str = "/tmp/application_default_credentials.json",
    pm_image: str = "",
    pm_backup_dir: str = "/Volumes/ext/state/pm-kernel/backups",
    state_root: str = "/Volumes/ext/state",
    template: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data",
            json.dumps(data(onepassword, vertex, vertex_account, vertex_credentials,
                            pm_image, pm_backup_dir, state_root)),
            *args,
        ],
        input=template,
        text=True,
        capture_output=True,
        check=True,
    )


def test_local_data_renders_complete_configs() -> None:
    config = json.loads(
        chezmoi("cat", str(Path.home() / ".config/opencode/opencode.json")).stdout
    )
    assert config["provider"]["google-vertex-anthropic"]["options"] == {
        "project": "example-project",
        "location": "global",
        "googleAuthOptions": {
            "keyFilename": "/tmp/application_default_credentials.json"
        },
    }

    sandbox = json.loads(
        chezmoi("cat", str(Path.home() / ".config/dotfiles-ai/sandbox.json")).stdout
    )
    assert sandbox["lima_home"] == "/Volumes/ext/state/lima"
    assert sandbox["state_root"] == "/Volumes/ext/state"
    assert sandbox["schema_version"] == 6
    assert sandbox["atuin_workspace"] == "workspace1"
    assert config["provider"]["lmstudio"]["options"]["baseURL"] == "http://localhost:1234/v1"
    assert "theme" not in config

    tui = json.loads(
        chezmoi("cat", str(Path.home() / ".config/opencode/tui.json")).stdout
    )
    assert tui == {
        "$schema": "https://opencode.ai/tui.json",
        "theme": "catppuccin",
    }

    herdr = chezmoi("cat", str(Path.home() / ".config/herdr/config.toml")).stdout
    plist = chezmoi(
        "cat", str(Path.home() / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist")
    ).stdout
    assert 'name = "nord"' in herdr
    assert "/.local/bin/herdr-server-owner" in plist
    wrapper = chezmoi("cat", str(Path.home() / ".local/bin/herdr-server-owner")).stdout
    assert '/usr/local/bin/herdr' in wrapper

    sandbox = json.loads(
        chezmoi("cat", str(Path.home() / ".config/dotfiles-ai/sandbox.json")).stdout
    )
    assert sandbox["guest"]["atuin_sync_address"] == "https://atuin.example.com"
    assert sandbox["guest"]["hermes_enabled"] is True
    assert sandbox["guest"]["rnd_backend"] == "native"
    assert sandbox["tailscale"] == {"enabled": False, "ssh": False}


def test_tailscale_defaults_and_local_state_stay_out_of_git() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    ignore = (ROOT / ".gitignore").read_text().splitlines()

    assert "[dotfiles_ai.tailscale]" in defaults
    assert "[data.dotfiles_ai.tailscale]" in example
    assert defaults.count("enabled = false") >= 3
    assert 'small_model = "openai/gpt-5.6-luna"' in defaults
    assert 'small_model = "openai/gpt-5.6-luna"' in example
    assert "auth_key" not in defaults + example
    assert "/config.local.toml" in ignore
    assert "/.tailscale/" in ignore


def test_portable_terminal_config_is_guest_only() -> None:
    host = set(chezmoi("managed").stdout.splitlines())
    targets = {
        ".bashrc", ".bash_profile", ".common_profile", ".config/starship.toml",
        ".config/atuin/config.toml",
    }

    assert targets.isdisjoint(host)
    assert "install-starship.sh" not in host
    assert "install-atuin.sh" not in host
    assert "install-bash-preexec.sh" not in host
    assert "install-guest-development-tools.sh" not in host
    assert ".local/bin/docker" not in host
    assert (ROOT / "dot_bashrc").read_text().count('eval "$(starship init bash)"') == 1
    assert (ROOT / "dot_bashrc").read_text().count('eval "$(atuin init bash)"') == 1
    assert (ROOT / "dot_bash_profile").exists()
    assert (ROOT / "dot_common_profile.tmpl").exists()
    assert (ROOT / "private_dot_config/starship.toml").exists()
    atuin = (ROOT / "private_dot_config/atuin/private_config.toml.tmpl").read_text()
    assert "{{ .dotfiles_ai.atuin.sync_address | quote }}" in atuin
    assert "auto_sync = true" in atuin
    assert "sync_frequency = \"10m\"" in atuin
    ignore = (ROOT / ".chezmoiignore").read_text()
    assert '{{ if eq .chezmoi.os "darwin" }}' in ignore
    assert all(target in ignore for target in targets)
    assert "install-starship.sh" in ignore
    assert "install-atuin.sh" in ignore
    assert "install-bash-preexec.sh" in ignore
    assert "install-guest-development-tools.sh" in ignore
    assert ".local/bin/docker" in ignore
    assert "reconcile-sandbox-shell-aliases.sh" in ignore
    assert "run_onchange_after_reconcile-sandbox-shell-aliases.sh" not in ignore
    installer = (ROOT / "run_onchange_after_install-starship.sh.tmpl").read_text()
    assert "command -v starship" not in installer
    assert 'mv -f "$HOME/.local/bin/.starship.new"' in installer
    atuin_installer = (ROOT / "run_onchange_after_install-atuin.sh.tmpl").read_text()
    assert "atuin-aarch64-unknown-linux-musl.tar.gz" in atuin_installer
    assert "13fc31e9f40fcc97b28c626adf4015eed080b5d8d8df31bb23e8ddf504d19d59" in atuin_installer
    assert 'mv -f "$HOME/.local/bin/.atuin.new"' in atuin_installer
    preexec_installer = (ROOT / "run_onchange_after_install-bash-preexec.sh.tmpl").read_text()
    assert "b73ed5f7f953207b958f15b1773721dded697ac3" in preexec_installer
    assert "998f4d5e9dd82e254463228cc6caa4d40125ae79b31d5a16a2a2f49357f0c160" in preexec_installer
    bashrc = (ROOT / "dot_bashrc").read_text()
    assert 'source "$HOME/.local/share/bash-preexec/bash-preexec.sh"' in bashrc
    assert bashrc.index('eval "$(starship init bash)"') < bashrc.index("bash-preexec.sh")


def test_guest_development_tools_are_pinned_and_podman_backed() -> None:
    installer = (ROOT / "run_onchange_after_install-guest-development-tools.sh.tmpl").read_text()
    shim = (ROOT / "dot_local/bin/executable_docker").read_text()

    assert "docker-compose-linux-aarch64" in installer
    assert "systemctl --user enable --now podman.socket" in installer
    assert "d26373b19e89160546d15407516cc59f453030d9bc5b43ba7faf16f7b4980137" in installer
    assert "op_linux_arm64_v2.39.0.zip" in installer
    assert "829baeff1c07e055cfa132031b1d9f2282ccdf5076258e482caf2fda70aea5d0" in installer
    assert "google-cloud-cli-580.0.0-linux-arm.tar.gz" in installer
    assert "a02b7c478f94c070d7cb1ec1c595d3a0c9ae84601c17d93946b89a33d3155d71" in installer
    assert 'PODMAN_COMPOSE_PROVIDER="$HOME/.docker/cli-plugins/docker-compose"' in shim
    assert 'exec podman compose "$@"' in shim


def test_atuin_server_uses_rootless_quadlet_without_project_mounts() -> None:
    container = (ROOT / "private_dot_config/containers/systemd/atuin.container").read_text()
    volume = (ROOT / "private_dot_config/containers/systemd/atuin-data.volume").read_text()
    installer = (ROOT / "run_onchange_after_enable-atuin-server.sh.tmpl").read_text()

    assert "ghcr.io/atuinsh/atuin:18.17.1" in container
    assert "ATUIN_DB_URI=sqlite:///config/atuin.db" in container
    assert "ATUIN_OPEN_REGISTRATION=false" in container
    assert "PublishPort=127.0.0.1:8888:8888" in container
    assert "Volume=atuin-data.volume:/config" in container
    assert "/workspace" not in container
    assert "VolumeName=atuin-data" in volume
    assert "systemctl --user restart atuin.service" in installer
    assert "systemctl --user stop atuin.service" in installer
    assert 'include "private_dot_config/containers/systemd/atuin.container" | sha256sum' in installer
    assert '/bin/rm -f "$HOME/.config/containers/systemd/atuin.container"' in installer
    plist = (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.atuin-workspace.plist.tmpl").read_text()
    assert "state-root-exec" in plist
    assert "LIMA_HOME" in plist
    assert "--foreground" in plist
    assert "start-atuin-workspace" not in plist
    template = (ROOT / "private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl").read_text()
    assert "NOPASSWD: /usr/bin/cat /mnt/lima-cidata/param.env" in template
    assert "sudo -n /usr/bin/id" in template
    loader = (ROOT / "run_onchange_after_load-atuin-workspace-launchagent.sh.tmpl").read_text()
    assert 'configure-atuin --remove' in loader
    assert '/bin/rm -f "$plist"' in loader
    assert loader.index('sandbox-vm" validate') < loader.index("launchctl bootstrap")


def test_pm_postgres_is_default_off_and_requires_exact_image() -> None:
    data = (ROOT / ".chezmoidata.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()
    container = (ROOT / "private_dot_config/containers/systemd/pm-postgres.container.tmpl").read_text()
    schema = (ROOT / "dot_local/share/pm-kernel/schema.sql").read_text()

    assert "[dotfiles_ai.pm_kernel]" in data
    assert "postgres_enabled = false" in data
    assert ".dotfiles_ai.pm_kernel.postgres_enabled" in ignore
    assert "enable-pm-postgres.sh" not in ignore
    assert "docker" in container
    assert "library/postgres:19beta3" in container
    assert "postgres_image must be an exact PostgreSQL 19 image digest" in container
    assert "PublishPort=127.0.0.1:55432:5432" in container
    assert "HealthCmd=/bin/sh /usr/local/bin/pm-kernel-health" in container
    assert "ExecStartPost=%h/.local/bin/pm-postgres-migrate" in container
    assert "docker-entrypoint-initdb.d/001-pm-kernel.sql" in container
    assert "001-pm-kernel.sql:ro,Z" in container
    assert "pm-kernel-health:ro,Z" in container
    assert "Secret=pm-postgres-password" in container
    assert "POSTGRES_PASSWORD_FILE=/run/secrets/pm-postgres-password" in container
    assert "EnvironmentFile=" not in container
    assert "DROP PROPERTY GRAPH IF EXISTS context.context_graph" in schema
    assert "CREATE PROPERTY GRAPH context.context_graph" in schema
    assert "CREATE PROPERTY GRAPH IF NOT EXISTS" not in schema
    assert "REFERENCES tickets (id)" in schema
    assert "SOURCE KEY (source_id) REFERENCES context.tickets" not in schema
    assert "DESTINATION KEY (target_id) REFERENCES context.tickets" not in schema
    assert "context.source_envelopes" in schema

    image = "docker.io/library/postgres:19beta3@sha256:" + "a" * 64
    rendered = chezmoi("execute-template", pm_image=image, template=container).stdout
    assert f"Image={image}" in rendered
    for invalid in (
        "postgres:19beta3@sha256:" + "a" * 64,
        "docker.io/library/postgres:19beta4@sha256:" + "a" * 64,
        "docker.io/library/postgres:19beta3",
        "docker.io/library/postgres:19beta3@sha256:invalid",
    ):
        with pytest.raises(subprocess.CalledProcessError):
            chezmoi("execute-template", pm_image=invalid, template=container)

    psql = (ROOT / "dot_local/bin/executable_pm-psql.tmpl").read_text()
    backup = (ROOT / "dot_local/bin/executable_pm-postgres-backup.tmpl").read_text()
    loader = (ROOT / "run_onchange_after_configure-pm-postgres.sh.tmpl").read_text()
    guest_loader = (ROOT / "run_onchange_after_enable-pm-postgres.sh.tmpl").read_text()
    plist = (ROOT / "private_Library/LaunchAgents/dev.dotfiles-ai.pm-postgres-backup.plist.tmpl").read_text()
    assert "op read" in psql and "127.0.0.1" in psql and "55432" in psql
    assert "pg_dump" in backup and "pg_restore" in backup and "retain=7" in backup
    assert "configure-pm-postgres --remove" in loader
    assert loader.index("provision-pm-postgres") < loader.index('sandbox-vm" update')
    assert loader.index('sandbox-vm" update') < loader.index("configure-pm-postgres")
    assert "systemctl --user start pm-postgres.service" in guest_loader
    assert "systemctl --user stop pm-postgres.service" in guest_loader
    assert "enable --now pm-postgres.service" not in guest_loader
    assert "podman secret rm pm-postgres-password" in guest_loader
    assert "podman volume rm" not in guest_loader
    assert "StartCalendarInterval" in plist and "pm-postgres-backup" in plist
    sandbox_template = (ROOT / "private_dot_config/dotfiles-ai/sandbox.json.tmpl").read_text()
    with pytest.raises(subprocess.CalledProcessError):
        chezmoi("execute-template", onepassword=True, pm_image=image,
                pm_backup_dir="/Volumes/ext/state-foreign/backups", template=sandbox_template)
    with pytest.raises(subprocess.CalledProcessError):
        chezmoi("execute-template", onepassword=True, pm_image=image,
                pm_backup_dir="/Volumes/ext/state/../outside", template=sandbox_template)


def test_pm_postgres_backup_verifies_restore_retains_seven_and_preserves_collisions(tmp_path) -> None:
    image = "docker.io/library/postgres:19beta3@sha256:" + "a" * 64
    source = (ROOT / "dot_local/bin/executable_pm-postgres-backup.tmpl").read_text()
    rendered = chezmoi("execute-template", onepassword=True, pm_image=image,
                       pm_backup_dir=str(tmp_path / "backups"), state_root=str(tmp_path),
                       template=source).stdout
    script = tmp_path / "pm-postgres-backup"
    script.write_text(rendered)
    script.chmod(0o755)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "sandbox.log"
    sandbox = fake_bin / "sandbox-vm"
    sandbox.write_text(f"""#!/bin/sh
printf '%s\\n' "$*" >> {log}
case "$*" in
  *createdb*) test -z "$FAIL_CREATE" ;;
  *'pg_dump '*) printf 'private-dump' ;;
  *'pg_restore --list'*) cat >/dev/null ;;
  *'pg_restore '*) cat >/dev/null ;;
  *' psql '*) printf '1\\n' ;;
esac
""")
    sandbox.chmod(0o755)
    backups = tmp_path / "backups"
    backups.mkdir()
    for day in range(1, 9):
        (backups / f"pm-kernel-202601{day:02d}T000000Z.dump").write_text("old")
        (backups / f"pm-kernel-202601{day:02d}T000000Z.dump.sha256").write_text("sum")
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}", "FAIL_CREATE": ""}
    subprocess.run([str(script)], check=True, text=True, capture_output=True, env=env)
    assert len(list(backups.glob("pm-kernel-*.dump"))) == 7
    assert json.loads((backups / "last-verified.json").read_text())["restore_verified"] is True

    collision_dir = tmp_path / "collision"
    collision_source = chezmoi("execute-template", onepassword=True, pm_image=image,
                               pm_backup_dir=str(collision_dir), state_root=str(tmp_path),
                               template=source).stdout
    script.write_text(collision_source)
    log.write_text("")
    failed = subprocess.run([str(script)], text=True, capture_output=True,
                            env={**env, "FAIL_CREATE": "1"})
    assert failed.returncode == 1
    assert "dropdb" not in log.read_text()


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


def test_vertex_reauth_helper_is_gated_and_localized() -> None:
    disabled = chezmoi("managed", vertex=False).stdout.splitlines()
    assert ".local/bin/vertex-reauth" not in disabled
    assert ".local/bin/vertex-reauth-browser" not in disabled

    enabled = chezmoi("managed").stdout.splitlines()
    assert ".local/bin/vertex-reauth" in enabled
    assert ".local/bin/vertex-reauth-browser" in enabled

    helper = chezmoi("cat", str(Path.home() / ".local/bin/vertex-reauth")).stdout
    assert 'ADC="/tmp/application_default_credentials.json"' in helper
    assert 'PROJECT="example-project"' in helper
    assert 'ACCOUNT="user@example.com"' in helper
    # Every gcloud call must route through the isolating wrapper, never bare.
    assert "\ngcloud " not in helper

    browser = chezmoi(
        "cat", str(Path.home() / ".local/bin/vertex-reauth-browser")
    ).stdout
    assert "exec vertex-reauth --browser" in browser


def test_vertex_reauth_isolates_gcloud_from_ambient_credentials(tmp_path: Path) -> None:
    script = tmp_path / "vertex-reauth"
    script.write_text(chezmoi("cat", str(Path.home() / ".local/bin/vertex-reauth")).stdout)
    script.chmod(0o755)

    log = tmp_path / "gcloud.log"
    fake = tmp_path / "gcloud"
    fake.write_text(
        "#!/bin/bash\n"
        "{\n"
        '  echo "ARGV: $*"\n'
        '  echo "CLOUDSDK_CONFIG=${CLOUDSDK_CONFIG-<unset>}"\n'
        '  echo "GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS-<unset>}"\n'
        '  echo "OVERRIDE=${CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE-<unset>}"\n'
        '  echo "ACTIVE_CONFIG=${CLOUDSDK_ACTIVE_CONFIG_NAME-<unset>}"\n'
        f"}} >> {log}\n"
    )
    fake.chmod(0o755)

    # Exactly what the 1Password `secret` loader exports into a shell.
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "GOOGLE_APPLICATION_CREDENTIALS": "/ambient/wrong-sa.json",
        "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE": "/ambient/wrong-sa.json",
        "CLOUDSDK_ACTIVE_CONFIG_NAME": "wrong-config",
    }
    subprocess.run([str(script)], check=True, capture_output=True, text=True, env=env)

    recorded = log.read_text()
    # The isolated config directory is the ADC file's parent, never the default.
    assert "CLOUDSDK_CONFIG=/tmp\n" in recorded
    assert "/ambient/wrong-sa.json" not in recorded
    assert "GOOGLE_APPLICATION_CREDENTIALS=<unset>" in recorded
    assert "OVERRIDE=<unset>" in recorded
    assert "ACTIVE_CONFIG=<unset>" in recorded
    assert (
        "auth application-default login user@example.com --no-launch-browser "
        "--scopes=openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/cloud-platform,"
        "https://www.googleapis.com/auth/sqlservice.login"
        in recorded
    )
    assert "auth application-default set-quota-project example-project" in recorded

    script.write_text(
        chezmoi(
            "cat",
            str(Path.home() / ".local/bin/vertex-reauth"),
            vertex_account="",
        ).stdout
    )
    log.write_text("")
    subprocess.run([str(script)], check=True, capture_output=True, text=True, env=env)
    assert (
        "ARGV: auth application-default login --no-launch-browser "
        "--scopes=openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/cloud-platform,"
        "https://www.googleapis.com/auth/sqlservice.login\n"
        in log.read_text()
    )

    script.write_text(chezmoi("cat", str(Path.home() / ".local/bin/vertex-reauth")).stdout)
    log.write_text("")
    subprocess.run(
        [str(script), "--browser"], check=True, capture_output=True, text=True, env=env
    )
    assert (
        "ARGV: auth application-default login user@example.com "
        "--scopes=openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/cloud-platform,"
        "https://www.googleapis.com/auth/sqlservice.login\n"
        in log.read_text()
    )

    wrapper = tmp_path / "vertex-reauth-browser"
    wrapper.write_text(
        chezmoi("cat", str(Path.home() / ".local/bin/vertex-reauth-browser")).stdout
    )
    wrapper.chmod(0o755)
    log.write_text("")
    subprocess.run([str(wrapper)], check=True, capture_output=True, text=True, env=env)
    assert (
        "ARGV: auth application-default login user@example.com "
        "--scopes=openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/cloud-platform,"
        "https://www.googleapis.com/auth/sqlservice.login\n"
        in log.read_text()
    )

    invalid_args = subprocess.run(
        [str(script), "--browser", "extra"], capture_output=True, text=True, env=env
    )
    assert invalid_args.returncode == 2

    script.write_text(
        chezmoi(
            "cat",
            str(Path.home() / ".local/bin/vertex-reauth"),
            vertex_account="--quiet",
        ).stdout
    )
    invalid_account = subprocess.run(
        [str(script)], capture_output=True, text=True, env=env
    )
    assert invalid_account.returncode == 2
    assert "invalid vertex_account" in invalid_account.stderr

    script.write_text(chezmoi("cat", str(Path.home() / ".local/bin/vertex-reauth")).stdout)
    check = subprocess.run(
        [str(script), "--check"], capture_output=True, text=True, env=env
    )
    assert check.returncode == 0
    assert "credentials valid" in check.stdout

    script.write_text(
        chezmoi(
            "cat",
            str(Path.home() / ".local/bin/vertex-reauth"),
            vertex_credentials="/tmp/custom.json",
        ).stdout
    )
    invalid = subprocess.run(
        [str(script)], capture_output=True, text=True, env=env
    )
    assert invalid.returncode == 2
    assert "must end with application_default_credentials.json" in invalid.stderr


def test_dynamic_workspace_registry_and_template_render() -> None:
    registry = json.loads(chezmoi(
        "cat", str(Path.home() / ".config/dotfiles-ai/sandbox.json")
    ).stdout)
    assert registry["enabled"] is True
    assert registry["schema_version"] == 6
    assert registry["build_workspace"] == "workspace1"
    assert registry["atuin_workspace"] == "workspace1"
    assert [workspace["name"] for workspace in registry["workspaces"]] == ["workspace1", "workspace2"]
    assert [workspace["shell_alias"] for workspace in registry["workspaces"]] == ["workspace1sh", "workspace2sh"]
    assert registry["workspaces"][1]["mounts"][0]["writable"] is False
    template = chezmoi("cat", str(Path.home() / ".config/dotfiles-ai/lima/workspace.yaml")).stdout
    assert 'disk: "60GiB"' in template
    assert "@@MOUNTS@@" in template
    assert "@@WORKSPACE_JSON@@" in template
    assert "@@PORT_FORWARDS@@" in template


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
            # The helper must mint the token from the mocked keychain. A real
            # ambient token (exported by `secret`) would shadow it and fail the
            # mock, making this test pass or fail on shell history alone.
            **{k: v for k, v in os.environ.items() if k != "OP_SERVICE_ACCOUNT_TOKEN"},
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
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.split(b"\0")
    files = [ROOT / name.decode() for name in tracked if name and (ROOT / name.decode()).is_file()]
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
