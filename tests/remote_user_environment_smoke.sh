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

revision=$(git -C "$source_root" rev-parse HEAD)
"$source_root/dot_local/bin/executable_remote-user-bootstrap" bootstrap "$revision"
remote-user-bootstrap bootstrap "$revision"

remote-user-foundation apply "$revision"
test -z "$(chezmoi -S "$source_root" -D "$HOME" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" status)"

"$HOME/.local/bin/starship" --version
"$HOME/.local/bin/atuin" --version
"$HOME/.local/bin/op" --version
"$HOME/.local/bin/gcloud" version --format=json >/dev/null
"$HOME/.local/bin/codex" --version
"$HOME/.local/bin/opencode" --version
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
test "${1:-}" != --version || { echo 1.18.25; exit; }
echo OpenAI
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
PATH="$ready_bin:$PATH" remote-user-foundation refresh-auth
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = ready

mv "$HOME/.bashrc" "$HOME/.bashrc.saved"
set +e
remote-user-foundation refresh-auth
damage_status=$?
set -e
test "$damage_status" -ne 0
test "$(remote-user-foundation status | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = failed_retryable
rm -f "$HOME/.bashrc.saved"
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
