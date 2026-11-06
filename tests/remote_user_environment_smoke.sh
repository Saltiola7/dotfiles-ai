#!/bin/bash
set -euo pipefail

source_root=$(cd "$(dirname "$0")/.." && pwd)
export HOME=/home/you
export PATH="/tmp/dotfiles-ai-test-bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export DOTFILES_AI_SYSTEMCTL=/tmp/dotfiles-ai-test-bin/systemctl
export DOTFILES_AI_SOURCE="$source_root"
install -d -m 0700 "$HOME"
install -d -m 0755 /tmp/dotfiles-ai-test-bin
printf '#!/bin/sh\nexit 0\n' >"$DOTFILES_AI_SYSTEMCTL"
chmod 0755 "$DOTFILES_AI_SYSTEMCTL"
install -d -m 0700 "$HOME/.local/libexec/dotfiles-ai" "$HOME/.local/state/dotfiles-ai/codex-package"
cat >"$HOME/.local/libexec/dotfiles-ai/codex" <<'EOF'
#!/bin/sh
test "${1:-}" != --version || { echo 'codex-cli 0.153.4'; exit; }
exit 0
EOF
chmod 0700 "$HOME/.local/libexec/dotfiles-ai/codex"
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
home = Path(os.environ["HOME"])
binary = home / ".local/libexec/dotfiles-ai/codex"
version = "0.153.4"
names = {
    "darwin-aarch64": "codex-aarch64-apple-darwin.tar.gz",
    "linux-aarch64": "codex-aarch64-unknown-linux-musl.tar.gz",
    "linux-x86_64": "codex-x86_64-unknown-linux-musl.tar.gz",
}
lock = {
    "schema_version": 1, "channel": "stable", "release": version,
    "tag": f"rust-v{version}", "platform": "linux-x86_64",
    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "target_count": 1,
    "targets_digest": hashlib.sha256(b'["local"]').hexdigest(),
    "assets": {platform: {
        "url": f"https://github.com/openai/codex/releases/download/rust-v{version}/{name}",
        "sha256": "a" * 64, "size": 1,
    } for platform, name in names.items()},
    "validator_revision": "codex-release-validator-1", "previous": None,
}
path = home / ".local/state/dotfiles-ai/codex-package/release-lock.json"
path.write_text(json.dumps(lock, sort_keys=True, separators=(",", ":")) + "\n")
path.chmod(0o600)
PY

revision=$(git -C "$source_root" rev-parse HEAD)
bootstrap_with_fixture_diagnostics() {
  if "$source_root/dot_local/bin/executable_remote-user-bootstrap" bootstrap "$revision"; then
    return 0
  fi
  # This fixture starts credential-free with public config only. Replay here,
  # never in the production bootstrap, to expose the hidden apply failure.
  echo 'UBI fixture bootstrap failed; replaying apply for diagnostics' >&2
  "$HOME/.local/bin/chezmoi" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" \
    -S "$source_root" apply --verbose || true
  return 1
}
bootstrap_with_fixture_diagnostics
native_before=$(sha256sum "$HOME/.opencode/bin/opencode")
config_before=$(sha256sum "$HOME/.config/opencode/opencode.json")
remote-user-bootstrap bootstrap "$revision"

remote-user-foundation apply "$revision"
test "$(sha256sum "$HOME/.opencode/bin/opencode")" = "$native_before"
test "$(sha256sum "$HOME/.config/opencode/opencode.json")" = "$config_before"
expected_status=$(printf ' R install-02-remote-tools.sh\n R install-03-remote-mise.sh\n R update-codex.sh\n R update-opencode.sh')
test "$(chezmoi -S "$source_root" -D "$HOME" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" status)" = "$expected_status"

"$HOME/.local/bin/starship" --version
"$HOME/.local/bin/atuin" --version
"$HOME/.local/bin/mise" --version
"$HOME/.local/bin/gh" --version
test -s "$HOME/.agents/skills/herdr/SKILL.md"
grep -q '^name: herdr$' "$HOME/.agents/skills/herdr/SKILL.md"
herdr integration status | grep -E '^opencode: current'
python3 - <<'PY'
import hashlib, os, tomllib
from pathlib import Path
home = Path.home()
source = Path(os.environ['DOTFILES_AI_SOURCE'])
pins = tomllib.loads((source / '.chezmoidata.toml').read_text())['dotfiles_ai']['remote_user_environment']
for name, key in [('mise', 'mise_sha256'), ('gh', 'gh_binary_sha256')]:
    assert hashlib.sha256((home / '.local/bin' / name).read_bytes()).hexdigest() == pins[key]
herdr = tomllib.loads((home / '.config/herdr/config.toml').read_text())
assert herdr['session']['resume_agents_on_restore'] is True
worktrunk = tomllib.loads((home / '.config/worktrunk/config.toml').read_text())
assert worktrunk['worktree-path'].startswith(str(home / '.local/state/worktrees') + '/')
assert '{{ repo_path | hash }}' in worktrunk['worktree-path']
assert worktrunk['pre-switch'] and worktrunk['pre-remove']
PY
# A tampered foundation tool must fail integrity before any auth observation.
printf '#!/bin/sh\nexit 42\n' >"$HOME/.local/bin/mise"
if remote-user-foundation refresh-auth; then
  echo 'tampered mise unexpectedly passed integrity' >&2
  exit 1
fi
remote-user-foundation retry
python3 - <<'PY'
import hashlib, os, tomllib
from pathlib import Path
pins = tomllib.loads((Path(os.environ['DOTFILES_AI_SOURCE']) / '.chezmoidata.toml').read_text())['dotfiles_ai']['remote_user_environment']
assert hashlib.sha256((Path.home() / '.local/bin/mise').read_bytes()).hexdigest() == pins['mise_sha256']
PY
remote-user-foundation supported-flags | python3 -c \
  'import json,sys;v=json.load(sys.stdin);assert set(v)=={"onepassword","prefect_mcp","pm_kernel","jfrog_cli","history_projection","opencode.vertex_project"}'
python3 - <<'PY'
import tomllib
from pathlib import Path
config = tomllib.loads((Path.home() / ".config/atuin/config.toml").read_text())
assert config["auto_sync"] is False
assert config["sync_address"] == ""
assert config["daemon"]["enabled"] is False
PY
"$HOME/.local/bin/op" --version
"$HOME/.local/bin/gcloud" version --format=json >/dev/null
"$HOME/.local/bin/codex" --version
"$HOME/.local/bin/opencode" --version
test "$("$HOME/.local/bin/wt" --version)" = 'wt v0.80.0'
"$HOME/.local/bin/herdr" --version
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')" = "$revision"

set +e
remote-user-foundation refresh-auth
refresh_status=$?
set -e
test "$refresh_status" -eq 1
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = auth_pending

ready_bin=/tmp/dotfiles-ai-ready-bin
install -d -m 0755 "$ready_bin"
cat >"$ready_bin/opencode" <<'EOF'
#!/bin/sh
test "${1:-}" != --version || { echo 'opencode v2.0.99'; exit; }
exit 99
EOF
cat >"$ready_bin/codex" <<'EOF'
#!/bin/sh
test "${1:-}" != --version || { echo 'codex-cli 0.151.0'; exit; }
exit 0
EOF
for command in vertex-reauth op; do
  printf '#!/bin/sh\nexit 0\n' >"$ready_bin/$command"
done
chmod 0755 "$ready_bin"/*
install -d -m 0700 "$HOME/.local/state/opencode" "$HOME/.config/gcloud" "$HOME/.config/op"
printf '{}\n' >"$HOME/.local/state/dotfiles-ai/codex/auth.json"
printf '{}\n' >"$HOME/.config/gcloud/application_default_credentials.json"
printf '{}\n' >"$HOME/.config/op/config"
chmod 0600 "$HOME/.local/state/dotfiles-ai/codex/auth.json" \
  "$HOME/.config/gcloud/application_default_credentials.json" "$HOME/.config/op/config"
# Synthetic metadata only: never log in or send a provider/model request.
python3 - <<'PY' &
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

os.umask(0o077)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Authorization") != "Basic b3BlbmNvZGU6c3ludGhldGlj":
            self.send_error(401)
            return
        if self.path == "/api/info":
            value = {"pid": os.getpid(), "version": "2.0.99"}
        elif self.path.startswith("/api/integration?"):
            value = {"data": [{"id": "openai", "connections": [{"type": "credential", "id": "synthetic"}]}]}
        else:
            self.send_error(404)
            return
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass

server = HTTPServer(("127.0.0.1", 0), Handler)
path = Path.home() / ".local/state/opencode/service.json"
path.write_text(json.dumps({"url": f"http://127.0.0.1:{server.server_port}",
                            "pid": os.getpid(), "password": "synthetic"}))
path.chmod(0o600)
server.serve_forever()
PY
metadata_pid=$!
trap 'kill "$metadata_pid" 2>/dev/null || true; wait "$metadata_pid" 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do
  test -f "$HOME/.local/state/opencode/service.json" && break
  sleep 0.1
done
PATH="$ready_bin:$PATH" remote-user-foundation refresh-auth
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = ready

mv "$HOME/.bashrc" "$HOME/.bashrc.saved"
set +e
remote-user-foundation refresh-auth
damage_status=$?
set -e
test "$damage_status" -ne 0
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = failed_retryable
mv "$HOME/.bashrc.saved" "$HOME/.bashrc"
chezmoi -c "$HOME/.config/dotfiles-ai/chezmoi.toml" -S "$source_root" apply --force
remote-user-foundation retry

install -d -m 0700 "$HOME/.local/state/dotfiles-ai/codex" "$HOME/.local/share/atuin"
printf keep-auth >"$HOME/.local/state/dotfiles-ai/codex/auth.json"
printf keep-history >"$HOME/.local/share/atuin/history.db"
git -C "$source_root" config user.name Test
git -C "$source_root" config user.email test@example.com
git -C "$source_root" commit --allow-empty -m update >/dev/null
update_revision=$(git -C "$source_root" rev-parse HEAD)
remote-user-foundation apply "$update_revision"
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')" = "$update_revision"
remote-user-foundation rollback
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')" = "$revision"
test "$(cat "$HOME/.local/state/dotfiles-ai/codex/auth.json")" = keep-auth
test "$(cat "$HOME/.local/share/atuin/history.db")" = keep-history

git -C "$source_root" commit --allow-empty -m failure-retry >/dev/null
retry_revision=$(git -C "$source_root" rev-parse HEAD)
cp "$HOME/.config/dotfiles-ai/chezmoi.toml" /tmp/chezmoi.toml
printf invalid >"$HOME/.config/dotfiles-ai/chezmoi.toml"
set +e
remote-user-foundation apply "$retry_revision"
failure_status=$?
set -e
test "$failure_status" -ne 0
install -m 0600 /tmp/chezmoi.toml "$HOME/.config/dotfiles-ai/chezmoi.toml"
remote-user-foundation retry
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')" = "$retry_revision"
remote-user-foundation rollback
test "$(cat "$HOME/.local/state/dotfiles-ai/codex/auth.json")" = keep-auth
test "$(cat "$HOME/.local/share/atuin/history.db")" = keep-history
printf 'remote user environment smoke passed\n'

# Owner actions below exist only in this disposable qualification home. Applying
# the foundation must never create or replace workflow-policy activation itself.
python3 - <<'PY'
from pathlib import Path
import tomllib
home = Path.home()
config = tomllib.loads((home / '.config/dotfiles-ai/chezmoi.toml').read_text())
assert config['data']['dotfiles_ai']['workspaces'] == {
    'schema_version': 1, 'root': str(home / '.local/state/worktrees')}
PY
remote-user-foundation apply "$(git -C "$source_root" rev-parse HEAD)"
test -f "$HOME/.config/dotfiles-ai/workflow-policy.json"
test ! -e "$HOME/.config/dotfiles-ai/workflow-policy.activation.json"
# Explicit owner provisioning for the existing default cache, not hydration.
install -d -m 0700 "$HOME/.cache/dotfiles-ai/dvc" "$HOME/src/fixture-worktree"
git init -q "$HOME/src/fixture-worktree"
git -C "$HOME/src/fixture-worktree" -c user.name=Fixture -c user.email=fixture@example.invalid \
  -c commit.gpgsign=false commit --allow-empty -qm baseline
git init --bare -q "$HOME/fixture-remote.git"
git -C "$HOME/src/fixture-worktree" remote add origin "$HOME/fixture-remote.git"
git -C "$HOME/src/fixture-worktree" push -q origin HEAD:refs/heads/fixture/remote-work
git -C "$HOME/src/fixture-worktree" fetch -q origin
(
  cd "$HOME/src/fixture-worktree"
  before=$(git worktree list --porcelain)
  if wt switch fixture/remote-work --no-cd --yes; then
    echo 'unactivated Worktrunk allocation unexpectedly succeeded' >&2
    exit 1
  fi
  test "$(git worktree list --porcelain)" = "$before"
  proposal=$(mktemp "$HOME/.config/dotfiles-ai/workflow-policy.proposal.XXXXXX")
  workflow-policy snapshot >"$proposal"
  python3 - "$proposal" <<'PY'
import json, os, stat, sys
from pathlib import Path
home = Path.home()
proposal = json.loads(Path(sys.argv[1]).read_text())
policy = home / '.config/dotfiles-ai/workflow-policy.json'
assert stat.S_IMODE(policy.stat().st_mode) == 0o600
assert proposal['policy_digest'] == json.loads(policy.read_text())['policy_digest']
root = next(item for item in proposal['roots'] if item['canonical_path'] == str(home / '.local/state/worktrees'))
assert root['kind'] == 'owned_home' and Path(root['mountpoint']).is_absolute()
PY
  # Fixture owner has reviewed this exact proposal; no assistant live activation.
  install -m 0600 "$proposal" "$HOME/.config/dotfiles-ai/workflow-policy.activation.json"
  workflow-policy check
  wt switch fixture/remote-work --no-cd --yes
  python3 - <<'PY'
import re, subprocess
from pathlib import Path
blocks = subprocess.check_output(['git', 'worktree', 'list', '--porcelain'], text=True).split('\n\n')
selected = next(block for block in blocks if 'branch refs/heads/fixture/remote-work' in block.splitlines())
path = Path(selected.splitlines()[0].removeprefix('worktree '))
root = Path.home() / '.local/state/worktrees'
assert path.is_dir() and path.parent.parent == root
assert re.fullmatch(r'fixture-worktree-[a-z0-9]{3}', path.parent.name)
assert path.name == 'fixture-remote-work'
PY
)
activation_before=$(sha256sum "$HOME/.config/dotfiles-ai/workflow-policy.activation.json")
remote-user-foundation apply "$(git -C "$source_root" rev-parse HEAD)"
test "$(sha256sum "$HOME/.config/dotfiles-ai/workflow-policy.activation.json")" = "$activation_before"
printf 'remote Worktrunk policy and owner activation qualification passed\n'

# Enable the optional toolchain using only public fixture configuration. The
# frozen adapter is qualified locally without an API URL, credentials or calls.
python3 - <<'PY'
import re
from pathlib import Path
path = Path.home() / '.config/dotfiles-ai/chezmoi.toml'
assert not (Path.home() / '.local/share/mise/installs/python').exists()
previous = path.read_text()
updated, count = re.subn(r'(\[data\.dotfiles_ai\.prefect_mcp\]\n(?:#[^\n]*\n)*)enabled = false',
                         r'\1enabled = true', previous, count=1)
assert count == 1
path.write_text(updated)
PY
# Only this disposable public fixture exposes captured subprocess diagnostics.
# Keep the production command, locking, failure status and logging unchanged.
python3 - "$(git -C "$source_root" rev-parse HEAD)" "$HOME/.local/bin/remote-user-foundation" <<'PY'
# BEGIN optional-apply diagnostics
import runpy
import subprocess
import sys

revision, helper = sys.argv[1:]
module = runpy.run_path(helper, run_name='smoke_diagnostics')
original = module['command']

def diagnostic_command(*args, **kwargs):
    try:
        return original(*args, **kwargs)
    except subprocess.CalledProcessError as error:
        for output in (error.stdout, error.stderr):
            if output:
                print(output, file=sys.stderr)
        raise

module['main'].__globals__['command'] = diagnostic_command
sys.argv = [helper, 'apply', revision]
module['main']()
# END optional-apply diagnostics
PY
bash -lc 'cd "$HOME"; . "$HOME/.common_profile"; command -v python3.13; [[ $(python3.13 --version) == "Python 3.13.18" ]]'
# Native mise may serialize its lock again during normal use. Its exact bytes
# must already match chezmoi's template, not merely contain the same pin values.
lock_before=$(sha256sum "$HOME/.config/mise/mise.lock")
"$HOME/.local/bin/remote-mise" exec -- "$HOME/.local/bin/mise" lock --global --platform linux-x64
test "$(sha256sum "$HOME/.config/mise/mise.lock")" = "$lock_before"
remote-user-foundation apply "$(git -C "$source_root" rev-parse HEAD)"
test "$(sha256sum "$HOME/.config/mise/mise.lock")" = "$lock_before"
printf 'remote native mise lock and enabled Prefect reapply passed\n'
# Project idiomatic pins override the global baseline for normal shells only.
idiomatic_project="$HOME/fixture-python-project"
install -d -m 0700 "$idiomatic_project"
printf '3.14\n' >"$idiomatic_project/.python-version"
"$HOME/.local/bin/mise" --cd "$idiomatic_project" install python@3.14
bash -lc 'cd "$1"; . "$HOME/.common_profile"; [[ $(python3 --version) == Python\ 3.14.* ]]' bash "$idiomatic_project"
# Even a HOME-level idiomatic pin cannot redirect foundation installation/checks.
printf '3.14\n' >"$HOME/.python-version"
(
  cd "$idiomatic_project"
  test "$("$HOME/.local/bin/remote-mise" exec -- python --version)" = 'Python 3.13.18'
)
test "$(sha256sum "$HOME/.config/mise/mise.lock")" = "$lock_before"
printf 'remote idiomatic Python version file qualification passed\n'
python3 - <<'PY'
from pathlib import Path
# Deliberately invalid extra configs must not enter foundation tool installation.
home = Path.home()
extras = home / '.config/mise/conf.d'
extras.mkdir(parents=True, exist_ok=True)
for candidate in (home / 'mise.toml', home / '.config/mise/config.local.toml',
                  home / '.config/mise/config.override.toml', extras / 'unreviewed.toml',
                  home / '.miserc.toml', home / '.miserc.local.toml'):
    candidate.write_text('unreviewed = [\n')
PY
remote-user-foundation apply "$(git -C "$source_root" rev-parse HEAD)"
"$HOME/.local/bin/prefect-mcp" check-runtime | python3 -c \
  'import json,sys;v=json.load(sys.stdin);assert v=={"qualified":True,"backend_health":"not_checked"}'
python3 - <<'PY'
import hashlib, json, os, subprocess, tomllib
from pathlib import Path
home = Path.home()
pins = tomllib.loads((Path(os.environ['DOTFILES_AI_SOURCE']) / '.chezmoidata.toml').read_text())['dotfiles_ai']['remote_user_environment']
environment = {**os.environ, 'PATH': str(home / '.local/share/mise/shims') + ':' + os.environ['PATH'],
               'UV_PYTHON_DOWNLOADS': 'never'}
project = home / 'fixture-project'
project.mkdir(exist_ok=True)
(project / 'mise.toml').write_text('[tools]\npython = "3.13.17"\n')
(project / '.miserc.toml').write_text('unreviewed = [\n')
selected = Path(subprocess.check_output([str(home / '.local/bin/remote-mise'), 'exec', '--',
    str(home / '.local/bin/uv'), 'python', 'find',
    '--system', '--no-python-downloads', '3.13'], cwd=project, env=environment, text=True).strip()).resolve()
assert selected.is_relative_to(home / '.local/share/mise/installs/python' / pins['prefect_python_version'])
version = subprocess.check_output([str(selected), '-I', '-c',
    'import sys;print(".".join(map(str,sys.version_info[:3])))'], text=True).strip()
assert version == pins['prefect_python_version']
runtime = home / '.config/dotfiles-ai/runtime/prefect-mcp'
records = [json.loads(path.read_text()) for path in (runtime / 'generations').glob('*/.complete.json')]
assert any(record['python']['path'] == str(selected) and record['python']['version'] == [3, 13, 18]
           for record in records)
before = hashlib.sha256(selected.read_bytes()).hexdigest()
subprocess.run(['remote-user-foundation', 'apply', subprocess.check_output(
    ['git', '-C', os.environ['DOTFILES_AI_SOURCE'], 'rev-parse', 'HEAD'], text=True).strip()], check=True)
assert hashlib.sha256(selected.read_bytes()).hexdigest() == before
config = home / '.config/dotfiles-ai/chezmoi.toml'
contents = config.read_text()
disabled, count = __import__('re').subn(r'(\[data\.dotfiles_ai\.prefect_mcp\]\n(?:#[^\n]*\n)*)enabled = true',
                                      r'\1enabled = false', contents, count=1)
assert count == 1
config.write_text(disabled)
subprocess.run(['remote-user-foundation', 'apply', subprocess.check_output(
    ['git', '-C', os.environ['DOTFILES_AI_SOURCE'], 'rev-parse', 'HEAD'], text=True).strip()], check=True)
assert selected.exists() and hashlib.sha256(selected.read_bytes()).hexdigest() == before
assert tomllib.loads((home / '.config/mise/config.toml').read_text())['tools'] == {}
PY
printf 'remote mise and frozen Prefect qualification passed\n'
