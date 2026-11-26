#!/usr/bin/env bash
set -euo pipefail
umask 077

output=${1:?new destination required}
url=${2:-https://ziglang.org/download/0.16.0/zig-x86_64-linux-0.16.0.tar.xz}
size=${3:-55478392}
digest=${4:-70e49664a74374b48b51e6f3fdfbf437f6395d42509050588bd49abe52ba3d00}
[[ ! -e "$output" && ! -L "$output" ]]
partial=$(mktemp -- "$output.part.XXXXXXXX")
trap 'rm -f -- "$partial"' EXIT
for ((attempt = 1; attempt <= 5; attempt++)); do
    offset=$(stat -c %s -- "$partial")
    status=0
    curl -q -fsSL --proto '=https' --proto-redir '=https' \
        --connect-timeout 15 --max-time 105 --continue-at "$offset" \
        --output "$partial" "$url" || status=$?
    case "$status" in
        0|18|28|56) ;;
        *) printf 'Pinned Zig download refused (curl %s).\n' "$status" >&2; exit "$status" ;;
    esac
    bytes=$(stat -c %s -- "$partial")
    if [[ "$bytes" == "$size" ]]; then
        printf '%s  %s\n' "$digest" "$partial" | sha256sum -c
        mv -T -- "$partial" "$output"
        exit 0
    fi
    if (( bytes < offset || bytes > size )); then
        echo 'Pinned Zig archive has unexpected size.' >&2
        exit 1
    fi
    printf 'Pinned Zig download incomplete after attempt %s (%s bytes).\n' "$attempt" "$bytes" >&2
done
exit 1
