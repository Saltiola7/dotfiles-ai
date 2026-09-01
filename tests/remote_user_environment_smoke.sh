#!/bin/bash
set -euo pipefail

source_root=$(cd "$(dirname "$0")/.." && pwd)
export HOME=/home/you
export PATH="/tmp/dotfiles-ai-test-bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export DOTFILES_AI_SYSTEMCTL=/tmp/dotfiles-ai-test-bin/systemctl
install -d -m 0700 "$HOME" "$HOME/.config/dotfiles-ai"
install -d -m 0755 /tmp/dotfiles-ai-test-bin /usr/local/bin
printf '#!/bin/sh\nexit 0\n' >"$DOTFILES_AI_SYSTEMCTL"
chmod 0755 "$DOTFILES_AI_SYSTEMCTL"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL --retry 3 --retry-all-errors \
  https://github.com/twpayne/chezmoi/releases/download/v2.69.4/chezmoi_2.69.4_linux_amd64.tar.gz \
  -o "$tmp/chezmoi.tgz"
printf '%s  %s\n' 5054cf09cb2993725f525c8bb6ec3ff8625489ecfc061e019c17e737e7c7057b "$tmp/chezmoi.tgz" | sha256sum -c -
tar -xzf "$tmp/chezmoi.tgz" -C "$tmp" chezmoi
install -m 0755 "$tmp/chezmoi" /usr/local/bin/chezmoi
install -m 0600 "$source_root/config.remote-user.example.toml" "$HOME/.config/dotfiles-ai/chezmoi.toml"

apply() {
  chezmoi -S "$source_root" -D "$HOME" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" apply
}
apply
apply
test -z "$(chezmoi -S "$source_root" -D "$HOME" -c "$HOME/.config/dotfiles-ai/chezmoi.toml" status)"

"$HOME/.local/bin/starship" --version
"$HOME/.local/bin/atuin" --version
"$HOME/.local/bin/op" --version
"$HOME/.local/bin/gcloud" version --format=json >/dev/null
"$HOME/.local/bin/codex" --version
"$HOME/.local/bin/opencode" --version
"$HOME/.local/bin/herdr" --version
"$HOME/.local/bin/remote-user-foundation" status

set +e
readiness=$("$HOME/.local/bin/remote-agent-readiness")
readiness_status=$?
set -e
test "$readiness_status" -eq 1
test "$readiness" = '{"codex":"failure","onepassword":"failure","openai":"failure","state":"auth_pending","vertex":"failure"}'
