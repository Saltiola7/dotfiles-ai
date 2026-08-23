import hashlib
import json
import os
import plistlib
import runpy
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _render_herdr_script(name: str, values: dict) -> str:
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(values),
            "cat", str(Path.home() / name),
        ],
        text=True, capture_output=True, check=True,
    ).stdout


def _run_native_installer(
    tmp_path: Path,
    *,
    handoff_fails: bool = False,
    seed_previous: bool = False,
    seed_native: bool = False,
    compatible_old: bool = True,
    interrupt_handoff: bool = False,
    old_version: str = "0.7.5",
    old_protocol: int = 17,
    pane_count: int = 1,
    server_pid: int | None = None,
    pane_pid: int | None = None,
    recheck_fails: bool = False,
) -> tuple[subprocess.CompletedProcess, bytes, bytes]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    home.mkdir()
    bin_dir.mkdir()
    target = home / ".local/bin/herdr"
    state = tmp_path / "state"
    calls = tmp_path / "calls"
    asset = tmp_path / "herdr-asset"
    asset.write_text(
        "#!/bin/bash\n"
        "case \"$*\" in\n"
        "  --version) printf 'herdr 0.8.2\\n' ;;\n"
        "  'status server --json')\n"
        "    if [[ -f \"$STATE\" ]]; then printf '{\"running\":true,\"version\":\"0.8.2\",\"protocol\":20,\"capabilities\":{\"live_handoff\":true}}\\n';\n"
        "    else printf '{\"running\":true,\"version\":\"%s\",\"protocol\":%s,\"capabilities\":{\"live_handoff\":true},\"compatible\":false}\\n' \"$OLD_VERSION\" \"$OLD_PROTOCOL\"; fi ;;\n"
        "  server\\ live-handoff*)\n"
        "    printf '%s\\n' \"$*\" >> \"$CALLS\"\n"
        "    [[ \"${INTERRUPT_HANDOFF:-0}\" == 1 ]] && { kill -TERM \"$PPID\"; sleep 0.1; exit 1; }\n"
        "    [[ \"${HANDOFF_FAIL:-0}\" == 1 ]] && exit 1\n"
        "    touch \"$STATE\" ;;\n"
        "esac\n"
    )
    asset.chmod(0o755)
    checksum = hashlib.sha256(asset.read_bytes()).hexdigest()

    old = bin_dir / "herdr"
    old.write_text(
        "#!/bin/bash\n"
        "case \"$*\" in\n"
        "  --version) printf 'herdr %s\\n' \"${OLD_VERSION:-0.7.5}\" ;;\n"
        "  'status server --json') printf '{\"running\":true,\"version\":\"%s\",\"protocol\":%s,\"capabilities\":{\"live_handoff\":true},\"compatible\":%s}\\n' \"$OLD_VERSION\" \"$OLD_PROTOCOL\" \"$COMPATIBLE_OLD\" ;;\n"
        "  'pane list') if [[ \"${RECHECK_FAIL:-0}\" == 1 && -f \"$PANE_CALLS\" ]]; then exit 1; fi; touch \"$PANE_CALLS\"; printf '{\"result\":{\"panes\":['; for ((i=0; i<PANE_COUNT; i++)); do ((i)) && printf ','; printf '{\"pane_id\":\"w1:p%s\"}' \"$i\"; done; printf ']}}\\n' ;;\n"
        "  'server stop') kill \"$SERVER_PID\" \"$PANE_PID\" ;;\n"
        "esac\n"
    )
    old.chmod(0o755)
    previous_bytes = old.read_bytes()
    if seed_native:
        target.parent.mkdir(parents=True)
        target.write_bytes(asset.read_bytes())
        target.chmod(0o755)
    elif seed_previous:
        target.parent.mkdir(parents=True)
        target.write_bytes(previous_bytes)
        target.chmod(0o755)
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/bin/bash\n"
        "while [[ $# -gt 0 ]]; do [[ $1 == -o ]] && { /bin/cp \"$ASSET\" \"$2\"; exit; }; shift; done\n"
    )
    curl.chmod(0o755)
    uname = bin_dir / "uname"
    uname.write_text("#!/bin/bash\n[[ ${1:-} == -m ]] && printf 'arm64\\n' || printf 'Darwin\\n'\n")
    uname.chmod(0o755)
    sha256sum = bin_dir / "sha256sum"
    sha256sum.write_text("#!/bin/bash\nprintf '%064d  -\\n' 0\n")
    sha256sum.chmod(0o755)

    values = {
        "dotfiles_ai": {
            "herdr": {
                "theme": "nord", "launchagent": True,
                "executable": str(target), "version": "0.8.2", "protocol": 20,
                "asset_url": "https://example.invalid/herdr-macos-aarch64",
                "asset_sha256": checksum,
            }
        }
    }
    script = _render_herdr_script("install-herdr.sh", values)
    result = subprocess.run(
        ["bash"], input=script, text=True, capture_output=True,
        env={
            "HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin",
            "ASSET": str(asset), "STATE": str(state), "CALLS": str(calls),
            "HANDOFF_FAIL": "1" if handoff_fails else "0",
            "INTERRUPT_HANDOFF": "1" if interrupt_handoff else "0",
            "OLD_VERSION": old_version, "OLD_PROTOCOL": str(old_protocol),
            "COMPATIBLE_OLD": "true" if compatible_old else "false",
            "PANE_COUNT": str(pane_count),
            "SERVER_PID": str(server_pid or ""), "PANE_PID": str(pane_pid or ""),
            "RECHECK_FAIL": "1" if recheck_fails else "0",
            "PANE_CALLS": str(tmp_path / "pane-calls"),
        },
    )
    return result, asset.read_bytes(), previous_bytes


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
    assert "active server preserved" in loader
    assert "status server" in loader
    assert "managed server did not stop" not in loader
    assert "kickstart" not in loader
    assert "com" + ".tis" not in plist + loader


def test_native_herdr_release_is_pinned_and_handed_off(tmp_path) -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    installer = (ROOT / "run_onchange_before_install-herdr.sh.tmpl").read_text()

    assert 'executable = "~/.local/bin/herdr"' in defaults
    assert 'version = "0.8.2"' in defaults
    assert "protocol = 20" in defaults
    assert "a5d4f4d504d8b309c91f811050559300faba31258425f53c50852fc96f6ae574" in defaults
    assert "server live-handoff" in installer
    assert "server stop" not in installer

    result, _, _ = _run_native_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    target = tmp_path / "home/.local/bin/herdr"
    assert target.exists()
    assert subprocess.run([target, "--version"], text=True, capture_output=True).stdout == "herdr 0.8.2\n"
    assert (tmp_path / "calls").read_text().strip() == (
        f"server live-handoff --import-exe {target} --expected-protocol 20 --expected-version 0.8.2"
    )


def test_failed_native_handoff_restores_previous_path_and_keeps_processes(tmp_path) -> None:
    pane_pid_file = tmp_path / "pane.pid"
    server = subprocess.Popen([
        "bash", "-c", f"sleep 30 & printf '%s' $! > {pane_pid_file}; wait"
    ])
    while not pane_pid_file.exists():
        pass
    pane_pid = int(pane_pid_file.read_text())
    try:
        result, _, previous = _run_native_installer(
            tmp_path / "install", handoff_fails=True, seed_previous=True,
            server_pid=server.pid, pane_pid=pane_pid,
        )

        assert result.returncode != 0
        target = tmp_path / "install/home/.local/bin/herdr"
        assert target.read_bytes() == previous
        assert target.stat().st_mode & 0o777 == 0o755
        assert server.poll() is None
        os.kill(pane_pid, 0)
        assert "live handoff failed; old server left running" in result.stderr
    finally:
        server.terminate()
        server.wait()


def test_interrupted_native_handoff_restores_previous_path(tmp_path) -> None:
    result, _, previous = _run_native_installer(
        tmp_path, seed_previous=True, interrupt_handoff=True
    )

    assert result.returncode != 0
    assert (tmp_path / "home/.local/bin/herdr").read_bytes() == previous


def test_same_version_with_wrong_digest_is_replaced(tmp_path) -> None:
    result, asset, previous = _run_native_installer(
        tmp_path, seed_previous=True, old_version="0.8.2", old_protocol=20
    )

    assert result.returncode == 0, result.stderr
    assert previous != asset
    assert (tmp_path / "home/.local/bin/herdr").read_bytes() == asset


def test_installed_native_client_skips_incompatible_old_server(tmp_path) -> None:
    result, _, _ = _run_native_installer(tmp_path, seed_native=True)

    assert result.returncode == 0, result.stderr
    assert "server live-handoff" in (tmp_path / "calls").read_text()


def test_installer_fails_when_no_compatible_live_server_client_exists(tmp_path) -> None:
    result, _, _ = _run_native_installer(
        tmp_path, seed_native=True, compatible_old=False
    )

    assert result.returncode != 0
    assert "no compatible client for safe handoff" in result.stderr


def test_protocol_match_is_exact_and_handoff_refuses_more_than_64_panes(tmp_path) -> None:
    result, _, _ = _run_native_installer(
        tmp_path / "protocol", old_version="0.8.2", old_protocol=200
    )
    assert result.returncode == 0, result.stderr
    assert "server live-handoff" in (tmp_path / "protocol/calls").read_text()

    result, _, _ = _run_native_installer(tmp_path / "limit", pane_count=65)
    assert result.returncode != 0
    assert "supports at most 64 panes; found 65" in result.stderr
    assert not (tmp_path / "limit/home/.local/bin/herdr").exists()


def test_failed_pane_recheck_restores_previous_native_path(tmp_path) -> None:
    result, _, previous = _run_native_installer(
        tmp_path, seed_previous=True, recheck_fails=True
    )

    assert result.returncode != 0
    assert (tmp_path / "home/.local/bin/herdr").read_bytes() == previous
    assert "could not recheck live pane count" in result.stderr


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


def test_loaded_owner_defers_launchagent_reload_when_status_fails(tmp_path) -> None:
    calls = tmp_path / "calls"
    launchctl = tmp_path / "launchctl"
    herdr = tmp_path / "herdr"
    launchctl.write_text(
        '#!/bin/bash\nprintf "launchctl %s\\n" "$1" >> "$CALLS"\n'
        '[[ "$1" == print ]] && { printf "state = running\\n"; exit 0; }\nexit 99\n'
    )
    herdr.write_text(
        '#!/bin/bash\nprintf "herdr %s\\n" "$*" >> "$CALLS"\n'
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
    assert result.returncode == 0
    assert "active server preserved; LaunchAgent reload deferred" in result.stderr
    assert calls.read_text().splitlines() == [
        *["herdr status server --json"] * 5,
        "launchctl print",
    ]


def test_disabling_launchagent_does_not_boot_out_active_server(tmp_path) -> None:
    calls = tmp_path / "calls"
    launchctl = tmp_path / "launchctl"
    herdr = tmp_path / "herdr"
    launchctl.write_text('#!/bin/bash\nprintf "launchctl %s\\n" "$1" >> "$CALLS"\n')
    herdr.write_text(
        '#!/bin/bash\nprintf "herdr %s\\n" "$*" >> "$CALLS"\n'
        'printf \'{"running":true}\\n\'\n'
    )
    launchctl.chmod(0o755)
    herdr.chmod(0o755)
    values = {"dotfiles_ai": {"herdr": {
        "theme": "nord", "launchagent": False, "executable": str(herdr),
    }}}
    loader = _render_herdr_script("load-herdr-launchagent.sh", values).replace(
        "/bin/launchctl", str(launchctl)
    )
    home = tmp_path / "home"
    plist = home / "Library/LaunchAgents/dev.dotfiles-ai.herdr-server.plist"
    plist.parent.mkdir(parents=True)
    plist.touch()

    result = subprocess.run(
        ["bash"], input=loader, text=True, capture_output=True,
        env={"HOME": str(home), "CALLS": str(calls), "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert "LaunchAgent disable deferred" in result.stderr
    assert calls.read_text().splitlines() == ["herdr status server --json"]


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
    assert ".dotfiles-ai-state" in rendered


def test_opencode_wrapper_adds_auto_only_for_herdr(tmp_path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / ".dotfiles-ai-state").touch()
    target = tmp_path / "opencode"
    target.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
    target.chmod(0o755)
    rendered = _render_herdr_script(".local/bin/opencode", {
        "dotfiles_ai": {"state": {"root": str(state)}}
    }).replace("/opt/homebrew/bin/opencode", str(target))
    wrapper = tmp_path / "wrapper"
    wrapper.write_text(rendered)
    wrapper.chmod(0o755)

    plain = subprocess.run(
        [wrapper, "plain"], text=True, capture_output=True, check=True,
        env={key: value for key, value in os.environ.items() if key != "HERDR_ENV"},
    )
    herdr = subprocess.run(
        [wrapper, "herdr"], text=True, capture_output=True, check=True,
        env={**os.environ, "HERDR_ENV": "1"},
    )
    explicit = subprocess.run(
        [wrapper, "--auto"], text=True, capture_output=True, check=True,
        env={**os.environ, "HERDR_ENV": "1"},
    )

    assert plain.stdout.splitlines() == ["plain"]
    assert herdr.stdout.splitlines() == ["herdr", "--auto"]
    assert explicit.stdout.splitlines() == ["--auto"]

    startup_dir = state / "herdr"
    startup_dir.mkdir()
    (startup_dir / "opencode-startup.lock").write_text("999999\n")
    (startup_dir / "opencode-startup.timestamp").write_text(str(int(time.time()) + 3600))
    started = time.monotonic()
    subprocess.run(
        [wrapper, "--session", "ses_first"], capture_output=True, check=True,
        env={**os.environ, "HERDR_ENV": "1"},
    )
    assert time.monotonic() - started < 2
    started = time.monotonic()
    resumed = subprocess.run(
        [wrapper, "--session", "ses_second"], text=True, capture_output=True, check=True,
        env={**os.environ, "HERDR_ENV": "1"},
    )

    assert time.monotonic() - started >= 5
    assert resumed.stdout.splitlines() == ["--session", "ses_second", "--auto"]


def test_session_detection_ignores_unrelated_processes(monkeypatch) -> None:
    script = runpy.run_path(str(ROOT / "dot_local/bin/executable_herdr-opencode-restore"))
    monkeypatch.setitem(script["pane_state"].__globals__, "run", lambda *_: {
        "result": {"process_info": {"foreground_processes": [
            {"argv": ["other", "--session", "ses_wrong"]},
            {"argv": ["/tmp/opencode", "--session=ses_right", "--auto"]},
        ]}}
    })

    assert script["pane_state"]("w1:p1") == ("ses_right", True)


def test_session_watcher_survives_capture_failure(monkeypatch, capsys, tmp_path) -> None:
    script = runpy.run_path(str(ROOT / "dot_local/bin/executable_herdr-opencode-restore"))
    script_globals = script["main"].__globals__
    calls = 0

    def capture(_manifest) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        raise KeyboardInterrupt

    monkeypatch.setitem(script_globals, "capture", capture)
    monkeypatch.setattr(script["time"], "sleep", lambda _: None)
    monkeypatch.setattr(script["sys"], "argv", ["herdr-opencode-restore", "--watch"])
    monkeypatch.setenv("DOTFILES_AI_STATE_ROOT", str(tmp_path))
    try:
        script["main"]()
    except KeyboardInterrupt:
        pass

    assert calls == 2
    assert "OpenCode session capture failed: temporary failure" in capsys.readouterr().err


def test_centralized_state_guard_fails_closed() -> None:
    guard = ROOT / "dot_local/bin/executable_state-root-exec"
    result = subprocess.run(
        ["bash", str(guard), "true"], text=True, capture_output=True,
        env={"DOTFILES_AI_STATE_ROOT": "/definitely/missing/state"},
    )
    assert result.returncode == 75
    assert "state root is unavailable" in result.stderr


def test_herdr_owner_recovers_exact_sessions_after_server_start() -> None:
    owner = (ROOT / "dot_local/bin/executable_herdr-server-owner.tmpl").read_text()

    assert '"$HERDR" server' in owner
    assert '"$HOME/.local/bin/herdr-opencode-restore"' in owner
    assert 'while [[ $stopping == 0 && $failures -lt 5 ]]' in owner
    assert 'if [[ $stopping == 1 ]]; then status=0; else status=1; fi' in owner
    assert 'wait "$server_pid"\n    status=$?\n    server_pid=' in owner


def test_herdr_owner_stays_alive_after_handoff_child_exits(tmp_path) -> None:
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    state = tmp_path / "running"
    calls = tmp_path / "calls"
    herdr = tmp_path / "herdr"
    herdr.write_text(
        '#!/bin/bash\n'
        'case "$*" in\n'
        f'  server) touch "{state}"; sleep 0.1 ;;\n'
        '  "status server --json")\n'
        f'    calls=$(cat "{calls}" 2>/dev/null || printf 0); calls=$((calls + 1)); printf %s "$calls" > "{calls}"\n'
        f'    [[ -f "{state}" ]] && printf \'{{"running":true}}\\n\' ;;\n'
        'esac\n'
    )
    herdr.chmod(0o755)
    restore = home / ".local/bin/herdr-opencode-restore"
    watch = tmp_path / "watch"
    restore.write_text(
        '#!/bin/bash\n'
        '[[ ${1:-} == --watch ]] || exit 1\n'
        'touch "$WATCH"\n'
        'sleep 10\n'
    )
    restore.chmod(0o755)
    owner = _render_herdr_script(".local/bin/herdr-server-owner", {
        "dotfiles_ai": {"herdr": {"executable": str(herdr)}}
    })

    process = subprocess.Popen(["bash"], stdin=subprocess.PIPE, text=True, env={
        **os.environ, "HOME": str(home), "WATCH": str(watch),
    })
    process.stdin.write(owner)
    process.stdin.close()
    for _ in range(100):
        if state.exists():
            break
        time.sleep(0.01)
    time.sleep(1.2)
    assert process.poll() is None
    assert watch.exists()
    process.terminate()
    assert process.wait(timeout=3) == 0


def test_herdr_owner_tolerates_transient_monitor_probe_failure(tmp_path) -> None:
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    calls = tmp_path / "calls"
    herdr = tmp_path / "herdr"
    herdr.write_text(
        '#!/bin/bash\n'
        f'calls=$(cat "{calls}" 2>/dev/null || printf 0)\n'
        'calls=$((calls + 1))\n'
        f'printf %s "$calls" > "{calls}"\n'
        '[[ $calls == 3 ]] || printf \'{"running":true}\\n\'\n'
    )
    herdr.chmod(0o755)
    restore = home / ".local/bin/herdr-opencode-restore"
    restore.write_text("#!/bin/bash\nexit 1\n")
    restore.chmod(0o755)
    owner = _render_herdr_script(".local/bin/herdr-server-owner", {
        "dotfiles_ai": {"herdr": {"executable": str(herdr)}}
    })

    process = subprocess.Popen(["bash"], stdin=subprocess.PIPE, text=True, env={
        **os.environ, "HOME": str(home),
    })
    process.stdin.write(owner)
    process.stdin.close()
    time.sleep(0.5)
    assert process.poll() is None
    process.terminate()
    assert process.wait(timeout=3) == 0


def test_herdr_owner_exits_nonzero_after_five_monitor_failures(tmp_path) -> None:
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    calls = tmp_path / "calls"
    herdr = tmp_path / "herdr"
    herdr.write_text(
        '#!/bin/bash\n'
        f'calls=$(cat "{calls}" 2>/dev/null || printf 0)\n'
        'calls=$((calls + 1))\n'
        f'printf %s "$calls" > "{calls}"\n'
        '[[ $calls == 1 ]] && printf \'{"running":true}\\n\'\n'
    )
    herdr.chmod(0o755)
    restore = home / ".local/bin/herdr-opencode-restore"
    restore.write_text("#!/bin/bash\nexit 1\n")
    restore.chmod(0o755)
    owner = _render_herdr_script(".local/bin/herdr-server-owner", {
        "dotfiles_ai": {"herdr": {"executable": str(herdr)}}
    })

    result = subprocess.run(
        ["bash"], input=owner, text=True, timeout=8,
        env={**os.environ, "HOME": str(home)},
    )

    assert result.returncode != 0


def test_session_restore_uses_manifest_database_and_managed_wrapper() -> None:
    restore = (ROOT / "dot_local/bin/executable_herdr-opencode-restore").read_text()

    assert 'opencode-sessions.json' in restore
    assert 'opencode.db' in restore
    assert 'Path.home() / ".local/bin/opencode"' in restore
    assert '"pane", "run"' in restore
    assert '"--session"' in restore
    assert '"--check"' in restore
    assert '"--capture"' in restore
    assert '"--watch"' in restore
    assert "shlex.join" in restore


def test_session_restore_skips_running_and_restores_exact_identity(tmp_path) -> None:
    state = tmp_path / "state"
    data = state / "xdg/data/opencode"
    directory = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    for path in (data, state / "herdr", directory, bin_dir):
        path.mkdir(parents=True)
    database = data / "opencode.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE session (id TEXT PRIMARY KEY)")
    connection.executemany("INSERT INTO session VALUES (?)", [("ses_running",), ("ses_restore",)])
    connection.commit()
    connection.close()
    (state / "herdr/opencode-sessions.json").write_text(json.dumps({
        "schema_version": 1,
        "sessions": [
            {"pane_id": "w1:p1", "directory": str(directory), "session_id": "ses_running"},
            {"pane_id": "w1:p2", "directory": str(directory), "session_id": "ses_restore"},
        ],
    }))
    home = tmp_path / "home"
    wrapper = home / ".local/bin/opencode"
    wrapper.parent.mkdir(parents=True)
    wrapper.touch()
    herdr = bin_dir / "herdr"
    herdr.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$*" >> "$CALLS"\n'
        'case "$1 $2" in\n'
        '  "agent list") printf \'{"result":{"agents":[{"agent_session":{"value":"ses_running"}}]}}\\n\' ;;\n'
        '  "pane get") printf \'{"result":{"pane":{}}}\\n\' ;;\n'
        '  "pane run") sleep 0.2; touch "$STARTED" ;;\n'
        '  "pane process-info") if [ "$4" = w1:p1 ]; then printf \'{"result":{"process_info":{"foreground_processes":[{"argv":["opencode","--session","ses_running","--auto"]}]}}}\\n\'; elif [ -f "$STARTED" ]; then printf \'{"result":{"process_info":{"foreground_processes":[{"argv":["opencode","--session","ses_restore","--auto"]}]}}}\\n\'; else printf \'{"result":{"process_info":{"foreground_processes":[]}}}\\n\'; fi ;;\n'
        'esac\n'
    )
    herdr.chmod(0o755)

    command = [sys.executable, str(ROOT / "dot_local/bin/executable_herdr-opencode-restore")]
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CALLS": str(tmp_path / "calls"),
        "STARTED": str(tmp_path / "started"),
        "DOTFILES_AI_STATE_ROOT": str(state),
        "XDG_DATA_HOME": str(state / "xdg/data"),
    }
    processes = [subprocess.Popen(command, text=True, stderr=subprocess.PIPE, env=env) for _ in range(2)]
    results = [(process.wait(timeout=10), process.stderr.read()) for process in processes]
    assert results == [(0, ""), (0, "")]
    calls = (tmp_path / "calls").read_text()
    assert "ses_running" not in calls
    assert calls.count(f"pane run w1:p2 exec {wrapper} --session ses_restore --auto") == 1
