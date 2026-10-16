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
"$source_root/dot_local/bin/executable_remote-user-bootstrap" bootstrap "$revision"
native_before=$(sha256sum "$HOME/.opencode/bin/opencode")
config_before=$(sha256sum "$HOME/.config/opencode/opencode.json")
remote-user-bootstrap bootstrap "$revision"

remote-user-foundation apply "$revision"
test "$(sha256sum "$HOME/.opencode/bin/opencode")" = "$native_before"
test "$(sha256sum "$HOME/.config/opencode/opencode.json")" = "$config_before"
expected_status=$(printf ' R update-codex.sh\n R update-opencode.sh')
test "$(chezmoi -S "$source_root" -D "$HOME" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" status)" = "$expected_status"

"$HOME/.local/bin/starship" --version
"$HOME/.local/bin/atuin" --version
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
