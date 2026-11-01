import base64
import importlib.machinery
import importlib.util
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import stat
import sys
import subprocess
import threading

import pytest


ROOT = Path(__file__).parents[1]
COMMAND = ROOT / "dot_local/bin/executable_remote-user-foundation"
BOOTSTRAP = ROOT / "dot_local/bin/executable_remote-user-bootstrap"


def _render(path: str) -> str:
    data = {
        "chezmoi": {"os": "linux", "arch": "amd64"},
        "dotfiles_ai": {
            "remote_user_environment": {"enabled": True},
            "state": {"root": "/shared/state"},
            "codex": {"channel": "stable"},
            "opencode": {
                "version": "1.18.25",
                "vertex_project": "local-project",
                "vertex_location": "global",
                "vertex_credentials": "/shared/credentials.json",
                "vertex_account": "",
            },
            "herdr": {"host_enabled": False},
        }
    }
    return subprocess.run(
        [
            "chezmoi", "-S", str(ROOT), "--config", "/dev/null",
            "--config-format", "toml", "--override-data", json.dumps(data),
            "execute-template",
        ],
        input=(ROOT / path).read_text(), text=True, capture_output=True, check=True,
    ).stdout


def test_remote_user_environment_has_distinct_pinned_assets() -> None:
    defaults = (ROOT / ".chezmoidata.toml").read_text()
    example = (ROOT / "config.example.toml").read_text()
    remote_example = (ROOT / "config.remote-user.example.toml").read_text()
    ignore = (ROOT / ".chezmoiignore").read_text()
    tools = (ROOT / "run_onchange_after_install-guest-development-tools.sh.tmpl").read_text()
    starship = (ROOT / "run_onchange_after_install-starship.sh.tmpl").read_text()
    atuin = (ROOT / "run_onchange_after_install-atuin.sh.tmpl").read_text()
    codex = (ROOT / "dot_local/bin/executable_codex-update-all").read_text()
    opencode = (ROOT / "dot_local/bin/executable_opencode-install.tmpl").read_text()
    assert "opencode-package/release-lock.json" in opencode
    assert "managed OpenCode release lock is unsafe" in opencode
    herdr = (ROOT / "run_onchange_after_install-00-remote-herdr.sh.tmpl").read_text()

    assert "[dotfiles_ai.remote_user_environment]" in defaults
    assert "[data.dotfiles_ai.remote_user_environment]" in example
    assert "[data.dotfiles_ai.remote_user_environment]" in remote_example
    assert 'enabled = true' in remote_example
    assert "role =" not in remote_example
    for forbidden in ("password =", "token =", "api_key =", "secret ="):
        assert forbidden not in remote_example.lower()
    assert "remote_user_environment.enabled" in ignore
    assert "remote_workspace.enabled" in ignore
    assert "docker-compose-linux-x86_64" in tools
    assert "dba9d98e1ba5bfe11d88c99b9bd32fc4a0624a30fafe68eea34d61a3e42fd372" in tools
    assert "op_linux_amd64_v2.39.0.zip" in tools
    assert "6fba7f376b6c6dec49f41b06408930a43ad064cce103c6a2ce5b3d0413a86434" in tools
    assert "google-cloud-cli-580.0.0-linux-x86_64.tar.gz" in tools
    assert "e580c04b45dfa2e537b8dc0cf7c828e46a65bc77ef61de69161e1f3a124d7480" in tools
    assert "asset=starship-x86_64-unknown-linux-musl.tar.gz" in starship
    assert "b7c232b0e8249d8e55a40beb79c5c43a7d370f3f9408bd215deb0170daeaadf3" in starship
    assert "asset=atuin-x86_64-unknown-linux-musl.tar.gz" in atuin
    assert "5772df4121174a9f0b71c17260727794fde22a71b5a3ee5ac07b227eebcbfa9a" in atuin
    assert "codex-x86_64-unknown-linux-musl" in codex
    assert "api.github.com/repos/openai/codex/releases/latest" in codex
    assert 'channel = "stable"' in defaults
    assert "opencode-linux-x64.tar.gz" in defaults
    assert "linux_amd64_asset_url" in opencode
    assert "58a3729a6f3432dd6d2917fcc4a949788891a035818646ad480e12c947f56e78" in defaults
    assert "herdr-linux-x86_64" in defaults
    assert "linux_amd64_asset_url" in herdr
    assert "14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d" in defaults
    for source in (tools, starship, atuin, opencode, herdr):
        assert "remote_user_environment.enabled" in source
        assert "uname -m" in source
    assert "DOTFILES_AI_REMOTE_USER_ENVIRONMENT" in codex
    assert "platform.machine" in codex
    rendered_tools = _render("run_onchange_after_install-guest-development-tools.sh.tmpl")
    assert 'exec "$HOME/.local/share/google-cloud-sdk-580.0.0/bin/gcloud" "$@"' in rendered_tools
    assert 'ln -sfn "$destination/bin/gcloud"' not in rendered_tools
    assert "DOTFILES_AI_SYSTEMCTL" in tools
    assert "install-00-remote-herdr.sh" in ignore
    assert "install-01-remote-opencode.sh" in ignore
    wrapper = (ROOT / "dot_local/bin/executable_opencode.tmpl").read_text()
    assert 'herdr-opencode-restore' not in wrapper
    assert 'herdr_host' not in wrapper
    assert 'exec "$HOME/.local/bin/opencode-update-all" exec-managed "$@"' in wrapper


def test_opencode_bootstrap_ignores_legacy_lock_and_preserves_native_binary(tmp_path: Path) -> None:
    home = tmp_path / "home"
    binary = home / ".opencode/bin/opencode"
    lock = home / ".local/state/dotfiles-ai/opencode-package/release-lock.json"
    binary.parent.mkdir(parents=True)
    lock.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nprintf "opencode v2.0.99\\n"\n')
    binary.chmod(0o700)
    before = binary.read_bytes()
    script = tmp_path / "opencode-install"
    script.write_text(_render("dot_local/bin/executable_opencode-install.tmpl"))
    script.chmod(0o755)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl = fake_bin / "curl"
    curl.write_text('#!/bin/sh\nexit 93\n')
    curl.chmod(0o755)
    environment = {**os.environ, "HOME": str(home),
                   "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    lock.write_text("{}")

    result = subprocess.run([script], text=True, capture_output=True,
                            env=environment)
    assert result.returncode == 0
    assert binary.read_bytes() == before

    lock.unlink()
    lock.symlink_to(tmp_path / "missing")
    result = subprocess.run([script], text=True, capture_output=True,
                            env=environment)
    assert result.returncode == 0, result.stderr
    assert binary.read_bytes() == before
    lock.unlink()
    lock.mkdir()
    result = subprocess.run([script], text=True, capture_output=True,
                            env=environment)
    assert result.returncode == 0, result.stderr
    assert binary.read_bytes() == before
    assert not (home / '.local/state/opencode').exists()


def test_remote_smoke_expects_both_always_run_updaters() -> None:
    smoke = (ROOT / "tests/remote_user_environment_smoke.sh").read_text()
    foundation = (ROOT / "dot_local/bin/executable_remote-user-foundation").read_text()
    assert "R update-codex.sh\\n R update-opencode.sh" in smoke
    assert 'sorted(status) != [" R update-codex.sh", " R update-opencode.sh"]' in foundation
    assert 'binaries / "opencode"), "--version"' in foundation
    assert 'data["opencode"]["version"]' not in foundation


def test_remote_agent_wrappers_force_per_user_state_and_adc() -> None:
    opencode = _render("dot_local/bin/executable_opencode.tmpl")
    codex = _render("dot_local/bin/executable_codex.tmpl")
    vertex = _render("dot_local/bin/executable_vertex-reauth.tmpl")
    config = json.loads(_render(".chezmoitemplates/opencode.json.tmpl"))

    assert 'export XDG_CONFIG_HOME="$HOME/.config"' in opencode
    assert 'export XDG_DATA_HOME="$HOME/.local/share"' in opencode
    assert 'export XDG_STATE_HOME="$HOME/.local/state"' in opencode
    assert 'export XDG_CACHE_HOME="$HOME/.cache"' in opencode
    installer = _render('dot_local/bin/executable_opencode-install.tmpl')
    assert '/shared/state' not in installer
    assert 'export XDG_STATE_HOME="$HOME/.local/state"' in installer
    assert 'target="$HOME/.opencode/bin/opencode"' in opencode + installer
    assert 'exec-managed' not in opencode
    assert "/shared/state" not in opencode + codex
    assert 'export CODEX_HOME="$HOME/.local/state/dotfiles-ai/codex"' in codex
    assert 'ADC="$HOME/.config/gcloud/application_default_credentials.json"' in vertex
    assert "/shared/credentials.json" not in vertex
    assert config["provider"]["google-vertex-anthropic"]["options"] == {
        "project": "local-project", "location": "global",
    }


@pytest.fixture
def local_readiness(tmp_path):
    script = tmp_path / "remote-agent-readiness"
    script.write_text(_render("dot_local/bin/executable_remote-agent-readiness.tmpl"))
    script.chmod(0o755)
    paths = [".config/opencode/opencode.json", ".local/state/dotfiles-ai/codex/config.toml",
             ".local/state/dotfiles-ai/codex/auth.json", ".config/gcloud/application_default_credentials.json",
             ".config/op/config"]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
        path.chmod(0o600)
    binary = tmp_path / "bin"
    binary.mkdir()
    private = "private-account private-token private-path private-session private-content"
    for name in ("opencode", "codex", "vertex-reauth", "op"):
        path = binary / name
        path.write_text('#!/bin/sh\n'
                        + ('[ "$1" = --version ] && { echo "opencode v2.0.99"; exit; }\n'
                           if name == "opencode" else "")
                        + f'touch "{tmp_path}/unexpected-command"\necho "{private}"\nexit 99\n')
        path.chmod(0o755)
    state = {"connections": [{"type": "credential", "id": "synthetic"}], "pid": 123,
             "version": "2.0.99", "requests": [], "fault": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"].append(self.path)
            expected = "Basic " + base64.b64encode(b"opencode:synthetic-private").decode()
            if self.headers.get("Authorization") != expected:
                self.send_error(401)
                return
            payload = ({"pid": state["pid"], "version": state["version"]}
                       if self.path == "/api/info" else
                       {"data": [{"id": "openai", "connections": state["connections"]}]})
            body = json.dumps(payload).encode()
            if state["fault"] == "bad-json":
                body = b"private-token invalid json"
            elif state["fault"] == "overflow":
                body = b" " * 65537
            self.send_response(302 if state["fault"] == "redirect" else 200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    registration = tmp_path / ".local/state/opencode/service.json"
    registration.parent.mkdir(parents=True)
    registration.write_text(json.dumps({"url": f"http://127.0.0.1:{server.server_port}",
                                        "pid": 123, "password": "synthetic-private"}))
    registration.chmod(0o600)
    try:
        yield tmp_path, script, binary, registration, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("failed", [None, "opencode", "codex", "vertex-reauth", "op"])
def test_remote_agent_readiness_is_content_free(local_readiness, failed):
    tmp_path, script, binary, _, state = local_readiness
    if failed == "opencode":
        state["connections"] = []
    elif failed:
        path = {"codex": ".local/state/dotfiles-ai/codex/auth.json",
                "vertex-reauth": ".config/gcloud/application_default_credentials.json",
                "op": ".config/op/config"}[failed]
        (tmp_path / path).unlink()

    result = subprocess.run(
        [str(script)], text=True, capture_output=True,
        env={"HOME": str(tmp_path), "PATH": f"{binary}:{os.environ['PATH']}"},
    )

    expected_state = "ready" if failed is None else "auth_pending"
    expected = {
        "codex": "failure" if failed == "codex" else "success",
        "onepassword": "failure" if failed == "op" else "success",
        "openai": "failure" if failed == "opencode" else "success",
        "state": expected_state,
        "vertex": "failure" if failed == "vertex-reauth" else "success",
    }
    assert json.loads(result.stdout) == expected
    assert result.returncode == (0 if failed is None else 1)
    assert result.stderr == ""
    assert "private-" not in result.stdout
    assert not (tmp_path / "unexpected-command").exists()
    assert len(state["requests"]) == 2


@pytest.mark.parametrize("fault", ["missing", "public", "symlink", "remote-url", "password", "pid", "version",
                                   "bad-json", "overflow", "redirect"])
def test_readiness_never_starts_or_repairs_unavailable_native_service(local_readiness, fault):
    home, script, binary, registration, state = local_readiness
    if fault == "missing":
        registration.unlink()
    elif fault == "public":
        registration.chmod(0o644)
    elif fault == "symlink":
        saved = home / "saved-registration"
        registration.rename(saved)
        registration.symlink_to(saved)
    elif fault in {"remote-url", "password"}:
        value = json.loads(registration.read_text())
        value["url" if fault == "remote-url" else "password"] = (
            "https://example.invalid" if fault == "remote-url" else "wrong-password")
        registration.write_text(json.dumps(value))
    elif fault in {"pid", "version"}:
        state[fault] = 999 if fault == "pid" else "2.0.22"
    else:
        state["fault"] = fault
    result = subprocess.run([script], text=True, capture_output=True,
                            env={"HOME": str(home), "PATH": f"{binary}:{os.environ['PATH']}"})
    assert result.returncode == 1
    assert json.loads(result.stdout)["state"] == "auth_pending"
    assert result.stderr == ""
    assert "private" not in result.stdout
    assert not (home / "unexpected-command").exists()
    assert all(path == "/api/info" for path in state["requests"])


@pytest.mark.parametrize("connections,ready", [
    (["invalid"], False), ({"type": "credential"}, False),
    ([{"type": "unknown", "id": "synthetic"}], False),
    ([{"type": "env", "name": "OPENAI_API_KEY"}], True),
])
def test_readiness_validates_local_connection_metadata(local_readiness, connections, ready):
    home, script, binary, _, state = local_readiness
    state["connections"] = connections
    result = subprocess.run([script], text=True, capture_output=True,
                            env={"HOME": str(home), "PATH": f"{binary}:{os.environ['PATH']}"})
    assert result.returncode == (0 if ready else 1)
    assert json.loads(result.stdout)["openai"] == ("success" if ready else "failure")
    assert result.stderr == ""


def _commit(repository: Path, content: str) -> str:
    (repository / "managed.txt").write_text(content)
    subprocess.run(["git", "add", "managed.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", content], cwd=repository, check=True,
                   capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
        text=True, capture_output=True,
    ).stdout.strip()


def _foundation(tmp_path: Path, *arguments: str, fail: bool = False) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    source = home / ".local/share/chezmoi-dotfiles-ai"
    state = home / ".local/state/dotfiles-ai/remote-user-foundation.json"
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    chezmoi = binary / "chezmoi"
    chezmoi.write_text(
        "#!/bin/sh\n"
        "case \" $* \" in\n"
        "  *' managed '*) printf '%s\\n' '.bashrc' '.config/opencode/opencode.json' ;;\n"
        "  *' status '*) test -f \"$HOME/.bashrc\" && test ! -L \"$HOME/.bashrc\" && "
        "printf '%s\\n' ' R update-codex.sh' ' R update-opencode.sh' ;;\n"
        "  *' apply '*) test \"${FAIL_APPLY:-0}\" != 1 ;;\n"
        "  *) exit 2 ;;\n"
        "esac\n"
    )
    chezmoi.chmod(0o755)
    environment = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{binary}:{home / '.local/bin'}:{os.environ['PATH']}",
        "DOTFILES_AI_SOURCE": str(source),
        "DOTFILES_AI_CONFIG": str(config),
        "DOTFILES_AI_FOUNDATION_STATE": str(state),
        "FAIL_APPLY": "1" if fail else "0",
    }
    return subprocess.run(
        [str(COMMAND), *arguments], text=True, capture_output=True,
        env=environment,
    )


def _install_foundation_targets(tmp_path: Path, state: str = "auth_pending") -> Path:
    home = tmp_path / "home"
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("\n")
    config.chmod(0o600)
    (home / ".config/opencode").mkdir(parents=True, exist_ok=True)
    (home / ".config/opencode/opencode.json").write_text("{}\n")
    (home / ".bashrc").write_text("\n")
    binary = home / ".local/bin"
    binary.mkdir(parents=True, exist_ok=True)
    versions = {
        "codex": "codex-cli 0.151.0",
        "gcloud": "Google Cloud SDK 580.0.0",
        "herdr": "herdr 0.8.2",
        "op": "2.39.0",
        "opencode": "1.18.25",
        "wt": "wt v0.80.0",
    }
    for name, version in versions.items():
        path = binary / name
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
        path.chmod(0o755)
    marker = tmp_path / "readiness-called"
    readiness = binary / "remote-agent-readiness"
    failed = state == "auth_pending"
    readiness.write_text(
        "#!/bin/sh\n"
        f"touch '{marker}'\n"
        f"printf '%s\\n' '{{\"codex\":\"{'failure' if failed else 'success'}\","
        f"\"onepassword\":\"{'failure' if failed else 'success'}\","
        f"\"openai\":\"{'failure' if failed else 'success'}\","
        f"\"state\":\"{state}\",\"vertex\":\"{'failure' if failed else 'success'}\"}}'\n"
        f"exit {1 if failed else 0}\n"
    )
    readiness.chmod(0o755)
    return marker


@pytest.fixture
def bootstrap_case(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    source = home / ".local/share/chezmoi-dotfiles-ai"
    seed = tmp_path / "seed"
    seed.mkdir()
    real_git = shutil.which("git")
    assert real_git
    subprocess.run([real_git, "init", "-q", "-b", "main"], cwd=seed, check=True)
    for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                       ("commit.gpgsign", "false"), ("core.hooksPath", "/dev/null")):
        subprocess.run([real_git, "config", key, value], cwd=seed, check=True)
    (seed / "config.remote-user.example.toml").write_text(
        'sourceDir = "/home/you/.local/share/chezmoi-dotfiles-ai"\n'
    )
    foundation = seed / "dot_local/bin/executable_remote-user-foundation"
    foundation.parent.mkdir(parents=True)
    foundation.write_text(
        '#!/bin/sh\n[ "${PY01_FAULT:-}" != apply ] || exit 1\n'
        f'printf "%s\\n" "$*" > {str(tmp_path / "apply-args")!r}\n'
    )
    foundation.chmod(0o755)
    subprocess.run([real_git, "add", "."], cwd=seed, check=True)
    _commit(seed, "initial")
    initial = tmp_path / "initial"
    subprocess.run([real_git, "clone", "-q", "--no-hardlinks", str(seed), str(initial)], check=True)
    revision = _commit(seed, "requested")
    binary = home / ".local/bin"
    binary.mkdir(parents=True)
    (binary / "python3").symlink_to(sys.executable)
    chezmoi = binary / "chezmoi"
    chezmoi.write_text(
        f'#!/bin/sh\ntouch {str(tmp_path / "chezmoi-called")!r}\n'
        "echo 'chezmoi version 2.69.4'\n"
    )
    chezmoi.chmod(0o755)
    shim = binary / "git"
    shim.write_text(f'''#!{sys.executable}
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
real_git = {real_git!r}
source = {str(source)!r}
with open({str(tmp_path / "git-calls")!r}, "a") as stream:
    stream.write(json.dumps(args) + "\\n")
operation = args[2] if args[:1] == ["-C"] else args[0]
fault = os.environ.get("PY01_FAULT")
if operation == "clone":
    assert args[-2] == "https://github.com/Saltiola7/dotfiles-ai.git"
    if fault == "clone":
        destination = pathlib.Path(args[-1])
        destination.mkdir(exist_ok=True)
        (destination / "partial-clone").write_text("partial")
        sys.exit(1)
    result = subprocess.run([real_git, *args[:-2], {str(initial)!r}, args[-1]])
    if result.returncode == 0:
        subprocess.run([real_git, "-C", args[-1], "remote", "set-url", "origin",
                        "https://github.com/Saltiola7/dotfiles-ai.git"], check=True)
    sys.exit(result.returncode)
if operation == "fetch":
    if fault == "fetch":
        sys.exit(1)
    assert args[4:] == ["origin", "main"]
    args[4] = {str(seed)!r}
if operation == "checkout" and fault in {{"replaced", "symlink"}}:
    original = pathlib.Path(source)
    original.rename(original.with_name("retained-original"))
    if fault == "symlink":
        original.symlink_to({str(tmp_path / "replacement")!r}, target_is_directory=True)
    else:
        original.mkdir()
        (original / "user-marker").write_text("preserve")
    sys.exit(1)
if operation == "checkout" and fault == "checkout":
    pathlib.Path(source, "managed.txt").write_text("partial checkout")
    sys.exit(1)
sys.exit(subprocess.run([real_git, *args]).returncode)
''')
    shim.chmod(0o755)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment.update({"HOME": str(home), "PATH": f"{binary}:{os.environ['PATH']}",
                        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                        "DOTFILES_AI_SOURCE": str(source),
                        "DOTFILES_AI_CONFIG": str(home / ".config/dotfiles-ai/chezmoi.toml"),
                        "DOTFILES_AI_FOUNDATION_STATE": str(home / ".local/state/foundation.json")})

    def run(*, fault: str = "", requested: str = revision):
        return subprocess.run([str(BOOTSTRAP), "bootstrap", requested], text=True,
                              capture_output=True, env={**environment, "PY01_FAULT": fault}, timeout=20)

    return source, seed, revision, run


def test_remote_user_bootstrap_clones_absent_source_and_reuses_exact_revision(tmp_path, bootstrap_case):
    source, _seed, revision, run = bootstrap_case
    assert not source.exists()
    first = run()
    assert first.returncode == 0, first.stderr
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == revision
    assert subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"]) == b""
    assert subprocess.run(["git", "-C", str(source), "symbolic-ref", "-q", "HEAD"]).returncode == 1
    config = tmp_path / "home/.config/dotfiles-ai/chezmoi.toml"
    assert str(tmp_path / "home") in config.read_text()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert (tmp_path / "apply-args").read_text().strip() == f"apply {revision}"
    second = run()
    assert second.returncode == 0, second.stderr
    calls = [json.loads(line) for line in (tmp_path / "git-calls").read_text().splitlines()]
    assert sum(args[0] == "clone" for args in calls) == 1


@pytest.mark.parametrize("fault", ["clone", "fetch", "checkout"])
def test_remote_user_bootstrap_new_source_failure_is_retryable(tmp_path, bootstrap_case, fault):
    source, _seed, revision, run = bootstrap_case
    failed = run(fault=fault)
    assert failed.returncode != 0
    assert failed.stderr == "remote user bootstrap failed\n"
    assert not source.exists()
    assert not (tmp_path / "home/.config/dotfiles-ai/chezmoi.toml").exists()
    assert not (tmp_path / "chezmoi-called").exists()
    assert not (tmp_path / "apply-args").exists()
    state = tmp_path / "home/.local/state/foundation.json"
    previous = state.read_bytes()
    assert json.loads(previous)["desired_revision"] == revision
    assert json.loads(previous)["state"] == "failed_retryable"
    assert run(fault=fault).returncode != 0
    assert state.read_bytes() == previous
    retried = run()
    assert retried.returncode == 0, retried.stderr
    assert (tmp_path / "apply-args").read_text().strip() == f"apply {revision}"


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked", "legacy", "origin"])
def test_remote_user_bootstrap_preserves_existing_source_on_refusal(tmp_path, bootstrap_case, kind):
    source, seed, _revision, run = bootstrap_case
    source.parent.mkdir(parents=True)
    command = ["git", "clone", "-q", *(["--no-checkout"] if kind == "legacy" else []), str(seed), str(source)]
    subprocess.run(command, check=True)
    if kind != "origin":
        subprocess.run(["git", "-C", str(source), "remote", "set-url", "origin",
                        "https://github.com/Saltiola7/dotfiles-ai.git"], check=True)
    if kind in {"tracked", "staged"}:
        (source / "managed.txt").write_text("user changes")
        if kind == "staged":
            subprocess.run(["git", "-C", str(source), "add", "managed.txt"], check=True)
    if kind == "untracked":
        (source / "user.txt").write_text("user changes")
    before = {path.relative_to(source): path.read_bytes() for path in source.rglob("*")
              if path.is_file() and ".git" not in path.relative_to(source).parts}
    index = subprocess.check_output(["git", "-C", str(source), "ls-files", "--stage"])
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"])
    failed = run()
    assert failed.returncode != 0
    assert failed.stderr == ("bootstrap source is invalid\n" if kind == "origin"
                             else "bootstrap source is not clean\n")
    assert source.is_dir()
    assert before == {path.relative_to(source): path.read_bytes() for path in source.rglob("*")
                      if path.is_file() and ".git" not in path.relative_to(source).parts}
    assert index == subprocess.check_output(["git", "-C", str(source), "ls-files", "--stage"])
    assert head == subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"])
    assert not (tmp_path / "chezmoi-called").exists()
    assert not (tmp_path / "apply-args").exists()


def test_remote_user_bootstrap_reuses_source_after_apply_failure(tmp_path, bootstrap_case):
    source, _seed, _revision, run = bootstrap_case
    failed = run(fault="apply")
    assert failed.returncode != 0
    assert source.is_dir()
    assert subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"]) == b""
    assert run().returncode == 0
    calls = [json.loads(line) for line in (tmp_path / "git-calls").read_text().splitlines()]
    assert sum(args[0] == "clone" for args in calls) == 1


@pytest.mark.parametrize("fault", ["replaced", "symlink"])
def test_remote_user_bootstrap_cleanup_preserves_replaced_source(tmp_path, bootstrap_case, fault):
    source, _seed, _revision, run = bootstrap_case
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    (replacement / "user-marker").write_text("preserve")
    failed = run(fault=fault)
    assert failed.returncode != 0
    assert (replacement / "user-marker").read_text() == "preserve"
    assert source.with_name("retained-original").is_dir()
    if fault == "replaced":
        assert (source / "user-marker").read_text() == "preserve"
    else:
        assert source.is_symlink()
    assert not (tmp_path / "apply-args").exists()


@pytest.mark.parametrize("kind", ["missing", "blob"])
def test_remote_user_bootstrap_rejects_invalid_commit_before_downstream(tmp_path, bootstrap_case, kind):
    source, seed, _revision, run = bootstrap_case
    requested = ("f" * 40 if kind == "missing" else subprocess.check_output(
        ["git", "-C", str(seed), "rev-parse", "HEAD:managed.txt"], text=True).strip())
    failed = run(requested=requested)
    assert failed.returncode != 0
    assert failed.stderr == "remote user bootstrap failed\n"
    assert not source.exists()
    assert not (tmp_path / "chezmoi-called").exists()
    assert not (tmp_path / "apply-args").exists()


def test_remote_user_bootstrap_rejects_annotated_tag_identity(tmp_path, bootstrap_case):
    source, seed, _revision, run = bootstrap_case
    subprocess.run(["git", "-C", str(seed), "-c", "tag.gpgsign=false", "tag", "-a",
                    "-m", "annotated", "v1"], check=True)
    tag = subprocess.check_output(["git", "-C", str(seed), "rev-parse", "v1"], text=True).strip()
    source.parent.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", str(seed), str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "remote", "set-url", "origin",
                    "https://github.com/Saltiola7/dotfiles-ai.git"], check=True)
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"])
    failed = run(requested=tag)
    assert failed.returncode != 0
    assert failed.stderr == "bootstrap revision is invalid\n"
    assert head == subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"])
    assert not (tmp_path / "chezmoi-called").exists()
    assert not (tmp_path / "apply-args").exists()


@pytest.mark.parametrize("link", ["source", "ancestor"])
def test_remote_user_bootstrap_refuses_symlinked_source_admission(tmp_path, bootstrap_case, link):
    source, _seed, _revision, run = bootstrap_case
    target = tmp_path / "retained-target"
    target.mkdir()
    (target / "user-marker").write_text("preserve")
    if link == "source":
        source.parent.mkdir(parents=True)
        source.symlink_to(target, target_is_directory=True)
    else:
        source.parent.parent.mkdir(parents=True, exist_ok=True)
        source.parent.symlink_to(target, target_is_directory=True)
    failed = run()
    assert failed.returncode != 0
    assert failed.stderr == "bootstrap path is unsafe\n"
    assert (target / "user-marker").read_text() == "preserve"
    assert not (tmp_path / "chezmoi-called").exists()
    assert not (tmp_path / "apply-args").exists()


def test_remote_user_bootstrap_refuses_foreign_source_owner(tmp_path, monkeypatch):
    loader = importlib.machinery.SourceFileLoader("bootstrap_owner_under_test", str(BOOTSTRAP))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    home = tmp_path / "home"
    source = home / "source"
    source.mkdir(parents=True)
    (source / "user-marker").write_text("preserve")
    for name, path in (("HOME", home), ("SOURCE", source),
                       ("CONFIG", home / "config"), ("STATE", home / "state")):
        monkeypatch.setattr(module, name, path)
    original_lstat = Path.lstat

    def foreign_owner(path, *args, **kwargs):
        value = original_lstat(path, *args, **kwargs)
        if path == source:
            fields = list(value)
            fields[4] = os.getuid() + 1
            return os.stat_result(fields)
        return value

    def forbidden(*args, **kwargs):
        pytest.fail("unsafe source reached downstream work")

    monkeypatch.setattr(Path, "lstat", foreign_owner)
    for name in ("run", "prepare_config", "install_chezmoi"):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(module.BootstrapError, match="bootstrap path is unsafe"):
        module.bootstrap("a" * 40)
    assert (source / "user-marker").read_text() == "preserve"
    assert not (home / "config").exists()


def test_remote_user_bootstrap_validates_revision_and_creates_private_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/Saltiola7/dotfiles-ai.git"],
        cwd=source, check=True,
    )
    (source / "config.remote-user.example.toml").write_text(
        'sourceDir = "/home/you/.local/share/chezmoi-dotfiles-ai"\n'
        'persistentState = "/home/you/.local/state/dotfiles-ai/chezmoi.boltdb"\n'
    )
    foundation = source / "dot_local/bin/executable_remote-user-foundation"
    foundation.parent.mkdir(parents=True)
    foundation.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >'{tmp_path / 'apply-args'}'\n")
    foundation.chmod(0o755)
    subprocess.run(
        ["git", "add", "config.remote-user.example.toml", "dot_local/bin/executable_remote-user-foundation"],
        cwd=source, check=True,
    )
    revision = _commit(source, "bootstrap")
    local_bin = home / ".local/bin"
    local_bin.mkdir(parents=True)
    chezmoi = local_bin / "chezmoi"
    chezmoi.write_text("#!/bin/sh\necho 'chezmoi version 2.69.4'\n")
    chezmoi.chmod(0o755)

    result = subprocess.run(
        [str(BOOTSTRAP), "bootstrap", revision], text=True, capture_output=True,
        env={
            **os.environ,
            "HOME": str(home),
            "DOTFILES_AI_SOURCE": str(source),
            "DOTFILES_AI_CONFIG": str(home / ".config/dotfiles-ai/chezmoi.toml"),
        },
    )

    assert result.returncode == 0, result.stderr
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    assert str(home) in config.read_text()
    assert "/home/you" not in config.read_text()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert (tmp_path / "apply-args").read_text().strip() == f"apply {revision}"


def test_remote_user_bootstrap_rejects_symlinked_home(tmp_path: Path) -> None:
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    home = tmp_path / "home"
    home.symlink_to(real_home, target_is_directory=True)

    result = subprocess.run(
        [str(BOOTSTRAP), "bootstrap", "a" * 40], text=True, capture_output=True,
        env={**os.environ, "HOME": str(home)},
    )

    assert result.returncode != 0
    assert result.stderr == "bootstrap home is unsafe\n"


def test_remote_user_bootstrap_rejects_abbreviated_revision(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    result = subprocess.run(
        [str(BOOTSTRAP), "bootstrap", "a" * 12], text=True, capture_output=True,
        env={**os.environ, "HOME": str(home)},
    )

    assert result.returncode != 0
    assert result.stderr == "bootstrap revision must be a full commit identity\n"


def _refreshable_foundation(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    home.mkdir()
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source, check=True)
    (source / ".chezmoidata.toml").write_text(
        '[dotfiles_ai.codex]\nchannel = "stable"\n'
        '[dotfiles_ai.opencode]\nversion = "1.18.25"\n'
        '[dotfiles_ai.herdr]\nversion = "0.8.2"\n'
    )
    subprocess.run(["git", "add", ".chezmoidata.toml"], cwd=source, check=True)
    revision = _commit(source, "first")
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    config.parent.mkdir(parents=True)
    config.write_text("\n")
    config.chmod(0o600)
    assert _foundation(tmp_path, "apply", revision).returncode == 0
    return home, home / ".local/state/dotfiles-ai/remote-user-foundation.json"


def test_foundation_refresh_auth_distinguishes_integrity_and_login_state(tmp_path: Path) -> None:
    home, state_path = _refreshable_foundation(tmp_path)
    marker = _install_foundation_targets(tmp_path)

    pending = _foundation(tmp_path, "refresh-auth")
    assert pending.returncode == 1
    assert json.loads(state_path.read_text())["state"] == "auth_pending"
    assert marker.exists()

    marker.unlink()
    _install_foundation_targets(tmp_path, "ready")
    ready = _foundation(tmp_path, "refresh-auth")
    assert ready.returncode == 0
    assert json.loads(state_path.read_text())["state"] == "ready"
    assert marker.exists()

    marker.unlink()
    bashrc = tmp_path / "home/.bashrc"
    bashrc.unlink()
    bashrc.symlink_to(tmp_path / "private-history")
    damaged = _foundation(tmp_path, "refresh-auth")
    assert damaged.returncode != 0
    assert json.loads(state_path.read_text())["state"] == "failed_retryable"
    assert not marker.exists()


@pytest.mark.parametrize("version", ["1.18.25", "opencode v2.0.30", "opencode v2.99.999"])
def test_foundation_accepts_native_updates_without_release_pin(tmp_path, version):
    home, state_path = _refreshable_foundation(tmp_path)
    marker = _install_foundation_targets(tmp_path, "ready")
    (home / ".local/bin/opencode").write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
    result = _foundation(tmp_path, "refresh-auth")
    assert result.returncode == 0, result.stderr
    assert json.loads(state_path.read_text())["state"] == "ready"
    assert marker.exists()


@pytest.mark.parametrize("body", [b"invalid", b"[]", b'"not-config"', b"\xff"])
def test_foundation_rejects_malformed_configuration_before_local_readiness(tmp_path, body):
    home, state_path = _refreshable_foundation(tmp_path)
    marker = _install_foundation_targets(tmp_path, "ready")
    (home / ".config/opencode/opencode.json").write_bytes(body)
    result = _foundation(tmp_path, "refresh-auth")
    assert result.returncode != 0
    assert json.loads(state_path.read_text())["state"] == "failed_retryable"
    assert not marker.exists()


def test_foundation_refresh_auth_rejects_malformed_runtime_version_before_probe(tmp_path: Path) -> None:
    home, state_path = _refreshable_foundation(tmp_path)
    marker = _install_foundation_targets(tmp_path)
    (home / ".local/bin/opencode").write_text("#!/bin/sh\necho invalid\n")
    (home / ".local/bin/opencode").chmod(0o755)

    result = _foundation(tmp_path, "refresh-auth")

    assert result.returncode != 0
    assert json.loads(state_path.read_text())["state"] == "failed_retryable"
    assert not marker.exists()


def test_foundation_requires_worktrunk_before_auth_readiness(tmp_path: Path) -> None:
    home, state_path = _refreshable_foundation(tmp_path)
    marker = _install_foundation_targets(tmp_path, "ready")
    (home / ".local/bin/wt").unlink()
    result = _foundation(tmp_path, "refresh-auth")
    assert result.returncode != 0
    assert json.loads(state_path.read_text())["state"] == "failed_retryable"
    assert not marker.exists()


def test_foundation_apply_retry_and_rollback_preserve_unrelated_state(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    source = home / ".local/share/chezmoi-dotfiles-ai"
    source.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source, check=True)
    first = _commit(source, "first")
    second = _commit(source, "second")
    unrelated = home / "unrelated"
    unrelated.write_text("keep")
    auth = home / ".local/state/dotfiles-ai/codex/auth.json"
    history = home / ".local/share/atuin/history.db"
    auth.parent.mkdir(parents=True)
    history.parent.mkdir(parents=True)
    auth.write_text("keep-auth")
    history.write_text("keep-history")
    config = home / ".config/dotfiles-ai/chezmoi.toml"
    config.parent.mkdir(parents=True)
    config.write_text("\n")
    config.chmod(0o600)

    result = _foundation(tmp_path, "apply", first)
    assert result.returncode == 0, result.stderr
    state_path = home / ".local/state/dotfiles-ai/remote-user-foundation.json"
    state = json.loads(state_path.read_text())
    assert state == {
        "attempt": 1,
        "desired_revision": first,
        "managed_targets": [".bashrc", ".config/opencode/opencode.json"],
        "previous_managed_targets": [],
        "previous_revision": None,
        "revision": first,
        "schema_version": 1,
        "state": "foundation_ready",
    }
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600

    failed = _foundation(tmp_path, "apply", second, fail=True)
    assert failed.returncode != 0
    state = json.loads(state_path.read_text())
    assert state["state"] == "failed_retryable"
    assert state["revision"] == first
    assert state["desired_revision"] == second
    assert state["previous_revision"] is None
    assert state["previous_managed_targets"] == []
    assert state["attempt"] == 2

    changed = _foundation(tmp_path, "apply", first)
    assert changed.returncode != 0
    assert "retry must use the recorded foundation revision" in changed.stderr

    retried = _foundation(tmp_path, "retry")
    assert retried.returncode == 0, retried.stderr
    state = json.loads(state_path.read_text())
    assert state["state"] == "foundation_ready"
    assert state["revision"] == second
    assert state["previous_revision"] == first
    assert state["previous_managed_targets"] == [
        ".bashrc", ".config/opencode/opencode.json",
    ]
    assert state["attempt"] == 3

    rolled_back = _foundation(tmp_path, "rollback")
    assert rolled_back.returncode == 0, rolled_back.stderr
    state = json.loads(state_path.read_text())
    assert state["revision"] == first
    assert state["previous_revision"] == second
    assert state["managed_targets"] == state["previous_managed_targets"]
    assert state["attempt"] == 4
    assert unrelated.read_text() == "keep"
    assert auth.read_text() == "keep-auth"
    assert history.read_text() == "keep-history"

    status_result = _foundation(tmp_path, "status")
    assert status_result.returncode == 0
    assert json.loads(status_result.stdout) == state
