#!/usr/bin/env bash
# Opt-in Arch Linux fixture. Reuses native tools from a read-only /usr mount;
# starts no host units and uses no external network or existing credentials.
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ $(podman info --format '{{.Host.Security.Rootless}}') != true ]]; then
    echo "Rootless Podman required" >&2
    exit 1
fi
inputs=$(mktemp -d "${TMPDIR:-/tmp}/dbsctr-forgejo-fixture.XXXXXX")
container=
cleanup() {
    if [[ -n $container ]]; then podman rm -f "$container" >/dev/null; fi
    rm -f -- "$inputs"/{machine-id,https.py,run.sh,dbsctrctl,dbsctr-forgejo@.socket,dbsctr-forgejo@.service}
    rmdir -- "$inputs"
}
trap cleanup EXIT
systemd-id128 new > "$inputs/machine-id"
install -m 0644 tests/forgejo_broker_systemd/https-fixture.py "$inputs/https.py"
install -m 0644 tests/forgejo_broker_systemd/in-container.sh "$inputs/run.sh"
install -m 0644 dot_local/bin/executable_dbsctrctl "$inputs/dbsctrctl"
install -m 0644 docs/specs/dotfiles_ai_distribution/fixtures/forgejo-broker/dbsctr-forgejo@.* "$inputs/"
container=$(podman run -d --pull=never --network=none --systemd=always --cap-add=SYS_ADMIN \
    --mount=type=bind,src=/usr,dst=/usr,ro=true --tmpfs /usr/local:rw,exec \
    --mount="type=bind,src=$inputs/machine-id,dst=/etc/machine-id,ro=true" \
    --mount="type=bind,src=$inputs,dst=/opt/inputs,ro=true" \
    docker.io/library/debian:bookworm-20261020-slim /usr/lib/systemd/systemd --unit=basic.target)
for attempt in 1 2 3 4 5; do
    if podman exec "$container" /usr/bin/test -S /run/systemd/private; then break; fi
    sleep 1
done
if ! podman exec "$container" /usr/bin/bash /opt/inputs/run.sh "${1:-sha1}"; then
    podman exec "$container" /usr/bin/journalctl --no-pager -u 'dbsctr-forgejo@*' -u forgejo-https-fixture -n 20
    exit 1
fi
