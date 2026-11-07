#!/bin/bash
# Disposable, privileged, isolated hosted runner ONLY. Never run on a live host.
# docker exec <container> bash /opt/f01/boot-smoke.sh prepare
# docker restart --time 40 <container>
# docker exec <container> bash /opt/f01/boot-smoke.sh verify
# No diagnostics dump: service journals/registrations may contain private data.
set -euo pipefail
umask 077
[[ $EUID == 0 && $(cat /proc/1/comm) == systemd ]]
[[ $(uname -m) == x86_64 ]]
uid=$(id -u fixture)
home=/home/fixture
as_user() {
    # setpriv has no PAM session side effect; env -i excludes runner credentials.
    setpriv --reuid "$uid" --regid "$(id -g fixture)" --init-groups \
        env -i HOME="$home" USER=fixture LOGNAME=fixture TERM=xterm-256color \
        PATH="$home/.local/bin:/usr/local/bin:/usr/bin:/bin" \
        XDG_CONFIG_HOME="$home/.config" XDG_DATA_HOME="$home/.local/share" \
        XDG_STATE_HOME="$home/.local/state" XDG_CACHE_HOME="$home/.cache" \
        XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
        "$@"
}
wait_system() {
    local attempt
    for ((attempt = 0; attempt < 60; attempt++)); do
        if systemctl is-active --quiet systemd-logind.service dbus.service; then return 0; fi
        sleep 1
    done
    echo 'F01: systemd-logind/system D-Bus unavailable' >&2
    return 1
}
wait_user() {
    local attempt
    for ((attempt = 0; attempt < 60; attempt++)); do
        if [[ -S /run/user/$uid/bus ]] && as_user timeout 5 systemctl --user is-active --quiet default.target; then
            return 0
        fi
        sleep 1
    done
    echo 'F01: lingering user manager/D-Bus unavailable' >&2
    return 1
}
wait_system
case ${1:-} in
    prepare)
        [[ ! -e /var/lib/f01/prepared ]]
        # This is the sole account setup step. It is not a login or a service start.
        loginctl enable-linger fixture
        wait_user
        install -d -o fixture -g fixture -m 0700 "$home/.local" "$home/.local/share"
        cp -R /opt/f01/source "$home/.local/share/chezmoi-dotfiles-ai"
        chown -R fixture:fixture "$home/.local/share/chezmoi-dotfiles-ai"
        as_user timeout 600 python3 /opt/f01/verify-user.py prepare
        touch /var/lib/f01/prepared /run/f01-prepared
        echo 'F01: prepared; restart the container before verify'
        ;;
    verify)
        [[ -f /var/lib/f01/prepared ]]
        # /run must be tmpfs; the kernel boot_id does NOT change on container restart.
        [[ ! -e /run/f01-prepared ]]
        wait_user
        [[ $(loginctl show-user fixture -p Linger --value) == yes ]]
        [[ -z $(loginctl show-user fixture -p Sessions --value) ]]
        as_user timeout 240 python3 /opt/f01/verify-user.py verify
        ;;
    *) echo 'usage: boot-smoke.sh prepare|verify' >&2; exit 64 ;;
esac
