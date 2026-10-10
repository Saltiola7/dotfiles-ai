import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import zipfile

import pytest


ROOT = Path(__file__).parents[1]
UPDATER = ROOT / "dot_local/bin/executable_opencode-update-all"


def native_host_fixture(tmp_path):
    from test_portable_distribution import chezmoi

    home = Path(os.environ['HOME'])
    state = tmp_path / 'state'
    state.mkdir()
    (state / '.dotfiles-ai-state').touch()
    registration = state / 'xdg/state/opencode/service.json'
    registration.parent.mkdir(parents=True)
    registration.write_text(json.dumps({'url': 'http://127.0.0.1:12345', 'pid': 123,
                                        'password': 'synthetic-private'}))
    registration.chmod(0o600)
    native = home / '.opencode/bin/opencode'
    native.parent.mkdir(parents=True)
    native.write_text(f'''#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
if args == ["--version"]:
    print("opencode v2.0.24")
elif args == ["service", "status"]:
    print(os.environ.get("TEST_NATIVE_STATUS", "http://127.0.0.1:12345"))
elif args == ["debug", "paths", "state"]:
    print(os.environ["XDG_STATE_HOME"] + "/opencode")
elif args == ["api", "--server", "http://127.0.0.1:12345", "get", "/api/info"]:
    assert os.environ.get("OPENCODE_PASSWORD") == "synthetic-private"
    print(json.dumps({{"version": os.environ.get("TEST_NATIVE_SERVER_VERSION", "2.0.24"), "pid": 123}}))
else:
    print(sys.stdin.read() if os.environ.get("TEST_NATIVE_STDIN") else json.dumps(args))
''')
    native.chmod(0o700)
    pacing = home / '.local/bin/herdr-opencode-restore'
    pacing.write_text('#!/bin/sh\n[ "$1" = --pace-start ] || exit 91\n'
                      'touch "$HOME/paced"\nshift\nexec "$@"\n')
    pacing.chmod(0o700)
    scripts = {}
    for name in ['opencode', 'opencode-install']:
        template = (ROOT / f'dot_local/bin/executable_{name}.tmpl').read_text()
        template = template.replace('.chezmoi.os', '"darwin"').replace('.chezmoi.arch', '"arm64"')
        # Never let a regression execute the real Homebrew installation.
        template = template.replace('/opt/homebrew/bin/opencode', str(tmp_path / 'forbidden-brew'))
        script = tmp_path / name
        script.write_text(chezmoi('execute-template', state_root=str(state), template=template).stdout)
        scripts[name] = script
    return native, state, scripts


@pytest.mark.parametrize('argv,interactive,paced', [
    (['api', 'get', '/api/info'], False, False),
    (['upgrade', '2.0.24'], False, False),
    (['service', 'status'], False, False),
    (['--standalone', 'api', 'get', '/api/info'], False, False),
    (['--server', 'http://localhost:1234', 'service', 'status'], False, False),
    (['mini', '--help'], False, False),
    (['--version'], False, False),
    (['--session', 'ses_test', '--help'], False, False),
    (['--session', 'ses_test'], True, False),
    (['--session=ses_test'], True, False),
    (['-s', 'ses_test'], True, False),
    (['-c'], True, False),
    (['mini', '--session', 'ses_test', '--auto'], True, False),
    (['run', 'a prompt'], True, False),
    ([], True, False),
])
def test_native_host_routes_without_implicit_recovery_pacing(tmp_path, argv, interactive, paced):
    _, _, scripts = native_host_fixture(tmp_path)
    result = subprocess.run(['/bin/bash', str(scripts['opencode']), *argv],
                            env={**os.environ, 'HERDR_ENV':'1'}, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    expected = argv + ['--auto'] if interactive and '--auto' not in argv else argv
    if interactive:
        if argv and argv[0] in ['run', 'mini']:
            expected = [expected[0], '--server', 'http://127.0.0.1:12345', *expected[1:]]
        else:
            expected = ['--server', 'http://127.0.0.1:12345', *expected]
    if argv == ['--version']:
        assert result.stdout.strip() == 'opencode v2.0.24'
    elif argv == ['service', 'status']:
        assert result.stdout.strip() == 'http://127.0.0.1:12345'
    else:
        assert json.loads(result.stdout) == expected
    assert (Path(os.environ['HOME']) / 'paced').exists() == paced


def test_native_bootstrap_preserves_existing_release_and_refuses_unsafe_state(tmp_path):
    native, state, scripts = native_host_fixture(tmp_path)
    before = native.read_bytes()
    for _ in range(2):
        result = subprocess.run(['/bin/bash', str(scripts['opencode-install'])], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert native.read_bytes() == before
    native.chmod(0o777)
    assert subprocess.run(['/bin/bash', str(scripts['opencode-install'])], capture_output=True).returncode != 0
    assert subprocess.run(['/bin/bash', str(scripts['opencode'])], capture_output=True).returncode != 0
    native.chmod(0o700)
    (state / '.dotfiles-ai-state').unlink()
    for script in scripts.values():
        assert subprocess.run(['/bin/bash', str(script)], capture_output=True).returncode != 0


def test_native_host_default_updater_cannot_mutate_fleet(monkeypatch):
    helper = load_updater()
    monkeypatch.setattr(helper.sys, 'platform', 'darwin')
    monkeypatch.setattr(helper.platform, 'machine', lambda: 'arm64')
    monkeypatch.setattr(helper, 'host_update', lambda: pytest.fail('legacy host/fleet mutation'))
    assert helper.main([]) == 75


@pytest.mark.parametrize('setting,value', [('TEST_NATIVE_SERVER_VERSION', '2.0.22'),
                                          ('TEST_NATIVE_STATUS', 'stopped')])
def test_native_launch_refuses_uncoordinated_server_replacement(tmp_path, monkeypatch, setting, value):
    _, _, scripts = native_host_fixture(tmp_path)
    monkeypatch.setenv(setting, value)
    monkeypatch.delenv('HERDR_ENV', raising=False)
    result = subprocess.run(['/bin/bash', str(scripts['opencode']), '--session', 'ses_test'],
                            text=True, capture_output=True)
    assert result.returncode == 75
    assert 'coordinated' in result.stderr
    assert not result.stdout


@pytest.mark.parametrize('args', [['--standalone'], ['--server', 'https://example.invalid'],
                                 ['--server=https://example.invalid']])
def test_native_explicit_server_modes_do_not_probe_or_replace_local_server(tmp_path, monkeypatch, args):
    _, _, scripts = native_host_fixture(tmp_path)
    monkeypatch.setenv('TEST_NATIVE_STATUS', 'stopped')
    monkeypatch.delenv('HERDR_ENV', raising=False)
    result = subprocess.run(['/bin/bash', str(scripts['opencode']), *args, '--session', 'ses_test'],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [*args, '--session', 'ses_test']


@pytest.mark.parametrize('fault', ['public-mode', 'symlink', 'invalid-json', 'wrong-pid'])
def test_native_service_credentials_fail_closed_without_disclosure(tmp_path, fault):
    _, state, scripts = native_host_fixture(tmp_path)
    registration = state / 'xdg/state/opencode/service.json'
    if fault == 'public-mode':
        registration.chmod(0o644)
    elif fault == 'symlink':
        saved = tmp_path / 'saved-registration'
        registration.rename(saved)
        registration.symlink_to(saved)
    elif fault == 'invalid-json':
        registration.write_text('synthetic-private')
    else:
        value = json.loads(registration.read_text())
        value['pid'] = 456
        registration.write_text(json.dumps(value))
    result = subprocess.run(['/bin/bash', str(scripts['opencode']), '--session', 'ses_test'],
                            text=True, capture_output=True)
    assert result.returncode == 75
    assert not result.stdout
    assert 'synthetic-private' not in result.stderr


def test_native_guard_preserves_client_standard_input(tmp_path, monkeypatch):
    _, _, scripts = native_host_fixture(tmp_path)
    monkeypatch.setenv('TEST_NATIVE_STDIN', '1')
    result = subprocess.run(['/bin/bash', str(scripts['opencode']), 'run'],
                            input='synthetic piped input', text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'synthetic piped input'


def test_native_bootstrap_installs_only_when_missing(tmp_path, monkeypatch):
    native, _, scripts = native_host_fixture(tmp_path)
    saved = tmp_path / 'candidate'
    native.rename(saved)
    curl = Path(os.environ['HOME']) / '.local/bin/curl'
    curl.write_text(f'''#!{sys.executable}
import os, pathlib, sys
assert "https://opencode.ai/v2/install" in sys.argv
pathlib.Path(sys.argv[sys.argv.index("-o") + 1]).write_text(
    '#!/bin/bash\\n[ "$1" = --no-modify-path ] || exit 91\\n'
    '[ -z "${{VERSION:-}}" ] || exit 92\\n'
    'cp "{saved}" "$HOME/.opencode/bin/opencode"\\n')
''')
    curl.chmod(0o700)
    monkeypatch.setenv('VERSION', '1.0.0')
    result = subprocess.run(['/bin/bash', str(scripts['opencode-install'])], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert native.read_bytes() == saved.read_bytes()
    curl.write_text('#!/bin/sh\nexit 93\n')
    assert subprocess.run(['/bin/bash', str(scripts['opencode-install'])], capture_output=True).returncode == 0
    native.unlink()
    assert subprocess.run(['/bin/bash', str(scripts['opencode-install'])], capture_output=True).returncode != 0
    assert not native.exists()


@pytest.mark.parametrize('unsafe', ['symlink', 'parent-writable', 'non-executable'])
def test_native_host_refuses_unsafe_existing_install(tmp_path, unsafe):
    native, _, scripts = native_host_fixture(tmp_path)
    if unsafe == 'symlink':
        native.rename(tmp_path / 'saved')
        native.symlink_to(tmp_path / 'saved')
    elif unsafe == 'parent-writable':
        native.parent.chmod(0o777)
    else:
        native.chmod(0o600)
    for script in scripts.values():
        assert subprocess.run(['/bin/bash', str(script)], capture_output=True).returncode != 0


@pytest.mark.parametrize('platform,arch,remote,managed', [
    ('darwin', 'arm64', False, True),
    ('darwin', 'amd64', False, False),
    ('linux', 'arm64', False, False),
    ('linux', 'amd64', True, True),
])
def test_native_bootstrap_managed_inventory_and_update_hook(platform, arch, remote, managed):
    from test_portable_distribution import data

    values = data(remote_user_environment=remote)
    values['chezmoi'] = {'os': platform, 'arch': arch}
    command = ['chezmoi', '-S', str(ROOT), '--config', '/dev/null', '--config-format', 'toml',
               '--override-data', json.dumps(values)]
    result = subprocess.run([*command, 'managed'], text=True, capture_output=True, check=True)
    assert ('.local/bin/opencode-install' in result.stdout.splitlines()) == managed
    hook = subprocess.run([*command, 'execute-template'],
                          input=(ROOT / 'run_after_update-opencode.sh.tmpl').read_text(),
                          text=True, capture_output=True, check=True).stdout
    owner = 'opencode-install' if (platform, arch) == ('darwin', 'arm64') else 'opencode-update-all'
    assert f'exec "$HOME/.local/bin/{owner}"' in hook
    subprocess.run(['/bin/bash', '-n'], input=hook, text=True, check=True)


@pytest.fixture(autouse=True)
def isolate_native_configuration(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    bin_dir = home / ".local/bin"
    bin_dir.mkdir(parents=True)
    for name, output in {
        "dbsctrctl": "workspace-adopt workspace-remove-check record-evidence final-push",
        "wt": "wt v0.80.0",
    }.items():
        executable = bin_dir / name
        executable.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
        executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir) + ":" + os.environ.get("PATH", "/usr/bin:/bin"))


def load_updater():
    loader = importlib.machinery.SourceFileLoader("opencode_update", str(UPDATER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def release_payload(version="1.18.29"):
    assets = []
    for name in (
        "opencode-darwin-arm64.zip",
        "opencode-linux-arm64.tar.gz",
        "opencode-linux-x64.tar.gz",
    ):
        assets.append({
            "name": name,
            "size": 6,
            "digest": "sha256:" + "a" * 64,
            "browser_download_url":
                f"https://github.com/anomalyco/opencode/releases/download/v{version}/{name}",
        })
    return {"name": f"v{version}", "tag_name": f"v{version}", "draft": False,
            "prerelease": False, "assets": assets}


def fake_binary(path: Path, version="1.18.29", valid=True, tool_valid=True, minimal=False):
    config = ({"agent": {"build": {}, "plan": {}} if minimal else {"build": {}, "build-rnd": {}, "plan": {}},
               "permission": {"bash": "ask", "dks_context": "allow"}} if valid else {})
    tool = {} if not tool_valid else {"bash": True}
    path.write_text(
        "#!/bin/sh\n"
        f"case \"$1\" in --version) printf '{version}\\n';; --help) printf 'help\\n' >&2;; "
        "agent) printf 'build primary\\nbuild-rnd primary\\nplan primary\\n';; "
        "session) printf 'opencode session list\\n' >&2;; "
        f"debug) if [ \"$2\" = agent ]; then printf '%s\\n' "
        f"'{json.dumps({'name': 'build', 'tools': tool})}'; else "
        f"printf '%s\\n' '{json.dumps(config)}'; fi;; esac\n"
    )
    path.chmod(0o700)


def test_release_metadata_accepts_official_name_and_complete_assets() -> None:
    helper = load_updater()
    value = helper.validate_release(release_payload())

    assert value["release"] == "1.18.29"
    assert set(value["assets"]) == {"darwin-aarch64", "linux-aarch64", "linux-x86_64"}
    broken = release_payload()
    broken["assets"].pop()
    with pytest.raises(helper.UpdateError):
        helper.validate_release(broken)
    with pytest.raises(helper.UpdateError):
        helper.validate_release({**release_payload(), "tag_name": "1.18.29"})
    with pytest.raises(helper.UpdateError, match="metadata_unavailable"):
        helper.MetadataRedirectHandler().redirect_request(None, None, 302, "", {}, "https://example.com")


def test_extract_accepts_one_regular_zip_or_tar_member(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    archive = tmp_path / "candidate"
    destination = tmp_path / "opencode"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("opencode", b"zip")
    helper.extract(archive, destination, "opencode")
    assert destination.read_bytes() == b"zip"

    archive.unlink()
    destination.unlink()
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo("opencode")
        info.size = 3
        bundle.addfile(info, io.BytesIO(b"tar"))
    helper.extract(archive, destination, "opencode")
    assert destination.read_bytes() == b"tar"

    class Encrypted:
        filename = "opencode"
        file_size = 3

    class Bundle:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def infolist(self):
            return [Encrypted()]

        def open(self, _member):
            raise RuntimeError("encrypted")

    monkeypatch.setattr(helper.zipfile, "is_zipfile", lambda _path: True)
    monkeypatch.setattr(helper.zipfile, "ZipFile", lambda _path: Bundle())
    with pytest.raises(helper.UpdateError):
        helper.extract(archive, destination, "opencode")


def test_semantic_validator_requires_managed_roles_and_permissions(tmp_path: Path) -> None:
    helper = load_updater()
    binary = tmp_path / "opencode"
    fake_binary(binary)
    helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, valid=False)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, tool_valid=False)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")

    fake_binary(binary, minimal=True)
    helper.validate_binary(binary, "1.18.29")

    helper = load_updater()
    helper.run = lambda *_args, **_kwargs: b"\xff"
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")


def test_bounded_runner_drains_large_output_and_rejects_overflow() -> None:
    helper = load_updater()
    payload = b'{"value":"' + b"x" * 40_000 + b'"}'
    command = [sys.executable, "-c", f"import sys;sys.stdout.buffer.write({payload!r})"]
    assert helper.run(command, maximum=len(payload)) == payload
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.run(command, maximum=len(payload) - 1)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.run([sys.executable, "-c", "import time;time.sleep(1)"], timeout=.01)


@pytest.mark.parametrize("still_running", [False, True])
def test_bounded_runner_preserves_validation_error_when_group_signal_is_denied(monkeypatch, still_running):
    helper = load_updater()

    class Child:
        pid = 123
        polls = 0
        killed = False

        def poll(self):
            self.polls += 1
            return None if still_running or self.polls < 3 else 0

        def kill(self):
            self.killed = True

        def wait(self):
            assert self.killed or not still_running

    child = Child()
    monkeypatch.setattr(helper.subprocess, "Popen", lambda *args, **kwargs: child)

    def denied(*args):
        raise PermissionError("process group exited during cleanup")

    monkeypatch.setattr(helper.os, "killpg", denied)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.run(["fixture"], timeout=0)
    assert child.killed is still_running


@pytest.mark.parametrize("retired", ["plugins/continuation.ts", "lib/continuation.ts", "tools/dbsctr.ts"])
def test_native_validator_refuses_stale_deployed_adapters_without_removing_them(tmp_path, retired):
    helper = load_updater()
    plugin = Path.home() / ".config/opencode" / retired
    plugin.parent.mkdir(parents=True)
    plugin.write_text("fixture")
    binary = tmp_path / "binary"
    fake_binary(binary)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")
    assert plugin.read_text() == "fixture"
    plugin.unlink()
    helper.validate_binary(binary, "1.18.29")


def test_native_validator_requires_the_lifecycle_cli_surface(tmp_path):
    helper = load_updater()
    binary = tmp_path / "binary"
    fake_binary(binary)
    (Path.home() / ".local/bin/dbsctrctl").write_text("#!/bin/sh\nprintf 'legacy help\\n'\n")
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.validate_binary(binary, "1.18.29")
    assert not (ROOT / "dot_local/share/opencode-continuation/native_probe.py").exists()


def test_stage_lock_binds_binary_and_activates(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    monkeypatch.setattr(helper, "download", lambda _asset, path: path.write_bytes(b"archive"))
    monkeypatch.setattr(helper, "extract", lambda _archive, path, _member: fake_binary(path))
    candidate = helper.validate_release(release_payload())

    assert helper.stage(candidate) == "staged"
    lock = json.loads((root / "candidate-lock.json").read_text())
    assert lock["binary_sha256"] == hashlib.sha256(
        (root / "candidate-opencode").read_bytes()).hexdigest()
    assert helper.activate() == "updated"
    assert helper.healthy(helper.read_lock())
    assert stat.S_IMODE(binary.stat().st_mode) == 0o700


def test_same_release_asset_mutation_is_rejected(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    lock = helper.generation(candidate, "darwin-aarch64", "b" * 64)
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    mutated = json.loads(json.dumps(candidate))
    mutated["assets"]["darwin-aarch64"]["sha256"] = "c" * 64

    with pytest.raises(helper.UpdateError, match="candidate_invalid"):
        helper.stage(mutated, root, binary)


def test_validator_revision_retries_rejection_and_upgrades_live_lock(
        tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    fake_binary(binary)
    monkeypatch.setattr(helper, "platform_id", lambda: "darwin-aarch64")
    candidate = helper.validate_release(release_payload())
    old_revision = "opencode-release-validator-1"
    helper.atomic_json(root / "rejected-candidate.json", {
        "schema_version": 1, "release": candidate["release"],
        "candidate_digest": hashlib.sha256(helper.canonical(candidate)).hexdigest(),
        "validator_revision": old_revision, "reason": "validation_failed",
    })
    assert helper.rejected_candidate(candidate, root) is False

    lock = helper.generation(candidate, "darwin-aarch64", helper.file_digest(binary))
    lock["validator_revision"] = old_revision
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    old_lock = helper.read_lock(root)
    assert helper.healthy(old_lock, binary) is False
    upgraded = helper.upgrade_validator_lock(root, binary, old_lock)
    assert upgraded["validator_revision"] == helper.VALIDATOR_REVISION
    assert helper.read_lock(root)["validator_revision"] == helper.VALIDATOR_REVISION


def test_legacy_guest_is_verified_before_migration_marker(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    assert helper.LEGACY_LINUX_AARCH64_BINARY_SHA256 == (
        "896c9c9b1942d4d74576868af24bbcbfa3f267d7eeb17aa6b8dff70810800084"
    )
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    legacy = tmp_path / "legacy-opencode"
    fake_binary(legacy, helper.LEGACY_RELEASE)
    legacy.chmod(0o755)
    monkeypatch.setattr(helper, "LEGACY_ROOT", str(legacy))
    monkeypatch.setattr(helper, "LEGACY_LINUX_AARCH64_BINARY_SHA256", helper.file_digest(legacy))
    helper.validate_legacy(legacy, os.getuid())
    monkeypatch.setattr(helper, "validate_legacy", lambda _path: None)
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-aarch64")
    monkeypatch.setattr(helper, "binary_path", lambda: tmp_path / "missing")

    helper.verify_legacy(root)

    marker = json.loads((root / "legacy-migration.json").read_text())
    assert marker == {"schema_version": 1, "release": helper.LEGACY_RELEASE,
                      "binary_sha256": helper.LEGACY_LINUX_AARCH64_BINARY_SHA256}


def test_remote_bootstrap_binary_is_adopted_before_update(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    assert helper.LEGACY_LINUX_X86_64_BINARY_SHA256 == (
        "d91e0d33676d0839f7cde87924cd4127ea88c9d6784eea9f009a7d08bdc60eeb"
    )
    assert helper.LEGACY_ASSETS["linux-x86_64"] == {
        "url": "https://github.com/anomalyco/opencode/releases/download/v1.18.25/opencode-linux-x64.tar.gz",
        "sha256": "58a3729a6f3432dd6d2917fcc4a949788891a035818646ad480e12c947f56e78",
        "size": 60534407,
    }
    root = tmp_path / "state"
    binary = tmp_path / "opencode"
    root.mkdir(mode=0o700)
    fake_binary(binary, helper.LEGACY_RELEASE)
    binary.chmod(0o755)
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-x86_64")
    monkeypatch.setattr(helper, "LEGACY_LINUX_X86_64_BINARY_SHA256", helper.file_digest(binary))

    helper.adopt_remote_legacy(root, binary)

    lock = helper.read_lock(root)
    assert lock["release"] == helper.LEGACY_RELEASE
    assert lock["assets"] == helper.LEGACY_ASSETS
    assert lock["binary_sha256"] == helper.file_digest(binary)
    assert lock["validator_revision"] == helper.VALIDATOR_REVISION
    assert stat.S_IMODE(binary.stat().st_mode) == 0o700


def test_remote_bootstrap_rejects_bad_digest_before_execution(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state"
    binary = tmp_path / "opencode"
    root.mkdir(mode=0o700)
    fake_binary(binary, helper.LEGACY_RELEASE)
    binary.chmod(0o755)
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-x86_64")
    monkeypatch.setattr(helper, "validate_binary", lambda *_args: pytest.fail(
        "unverified bootstrap binary executed"))

    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.adopt_remote_legacy(root, binary)


def test_remote_bootstrap_is_retained_when_metadata_is_unavailable(
        tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state"
    binary = tmp_path / "libexec/opencode"
    binary.parent.mkdir(parents=True, mode=0o700)
    fake_binary(binary, helper.LEGACY_RELEASE)
    binary.chmod(0o755)
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "platform_id", lambda: "linux-x86_64")
    monkeypatch.setattr(helper, "LEGACY_LINUX_X86_64_BINARY_SHA256", helper.file_digest(binary))
    monkeypatch.setattr(helper, "fetch_release", lambda: (_ for _ in ()).throw(
        helper.UpdateError("metadata_unavailable")))

    assert helper.local_update() == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"schema_version": 1, "status": "retained", "release": "1.18.25",
                      "target_count": 1, "reason": "metadata_unavailable"}


def test_host_update_stages_every_guest_before_activation(tmp_path: Path, monkeypatch, capsys) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    candidate = helper.validate_release(release_payload())
    calls = []
    monkeypatch.setattr(helper, "fetch_release", lambda: candidate)
    monkeypatch.setattr(helper, "read_lock", lambda *_args: None)
    health = iter((False, True))
    monkeypatch.setattr(helper, "healthy", lambda *_args: next(health))
    monkeypatch.setattr(helper, "rejected_candidate", lambda *_args: False)
    monkeypatch.setattr(helper, "sandbox_config", lambda: ["workspace-a", "workspace-b"])

    def stage(candidate, root, _binary, target_count, targets_digest):
        calls.append("stage-host")
        lock = helper.generation(candidate, "darwin-aarch64", "b" * 64,
                                 target_count, targets_digest)
        lock["previous"] = None
        helper.atomic_json(root / "candidate-lock.json", lock)
        return "staged"

    stages = {}

    def guest(action, workspace, candidate=None, **_kwargs):
        calls.append(f"{action}-{workspace}")
        if action == "stage":
            stages[workspace] = stages.get(workspace, 0) + 1
            return "staged" if stages[workspace] == 1 else "current"
        return "current"

    monkeypatch.setattr(helper, "stage", stage)
    monkeypatch.setattr(helper, "guest_call", guest)
    monkeypatch.setattr(helper, "activate", lambda *_args, **_kwargs:
                        calls.append("activate-host") or "updated")

    assert helper.host_update() == 0
    assert calls[:5] == ["stage-host", "stage-workspace-a", "stage-workspace-b",
                         "activate-workspace-a", "activate-workspace-b"]
    assert calls.index("activate-host") > calls.index("activate-workspace-b")
    assert json.loads(capsys.readouterr().out)["target_count"] == 3


def test_exec_managed_recovers_and_execs_verified_path(tmp_path: Path, monkeypatch) -> None:
    helper = load_updater()
    root = tmp_path / "state/opencode-package"
    binary = tmp_path / "libexec/opencode"
    root.mkdir(parents=True, mode=0o700)
    binary.parent.mkdir(parents=True, mode=0o700)
    fake_binary(binary)
    candidate = helper.validate_release(release_payload())
    lock = helper.generation(candidate, helper.platform_id(), helper.file_digest(binary))
    lock["previous"] = None
    helper.atomic_json(root / "release-lock.json", lock)
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_PACKAGE_ROOT", str(root))
    monkeypatch.setenv("DOTFILES_AI_OPENCODE_BINARY", str(binary))
    monkeypatch.setattr(helper, "recover_host", lambda *_args: None)
    called = {}

    class ExecCalled(Exception):
        pass

    def execute(path, argv, environment):
        called.update(path=path, argv=argv, environment=environment)
        raise ExecCalled

    monkeypatch.setattr(helper.os, "execve", execute)
    with pytest.raises(ExecCalled):
        helper.exec_managed(["--version"])
    assert called["path"] == binary
    assert called["argv"] == [str(binary), "--version"]

    binary.write_text("tampered")
    binary.chmod(0o700)
    with pytest.raises(helper.UpdateError, match="validation_failed"):
        helper.exec_managed(["--version"])
