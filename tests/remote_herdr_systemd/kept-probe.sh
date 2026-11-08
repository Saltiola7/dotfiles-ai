#!/bin/bash
# Run ONLY inside the explicitly approved disposable hosted Docker fixture.
# Primary workflow owns image wiring; this entrypoint never applies dotfiles.
set -euo pipefail
umask 077
fail() { echo 'kept-probe: boot-precondition-failed' >&2; exit 1; }
[[ ${1:-} == approved-disposable-container && $# == 1 ]] || fail
[[ $EUID == 0 && $(cat /proc/1/comm) == systemd ]] || fail
[[ $(systemd-detect-virt --container) == docker && $(uname -m) == x86_64 ]] || fail
[[ $(id -u fixture) == 1000 && $(id -g fixture) == 1000 ]] || fail
[[ ! -e /home/fixture/kept-probe.json && ! -L /home/fixture/kept-probe.json ]] || fail
as_user() {
    setpriv --reuid 1000 --regid 1000 --init-groups env -i \
        HOME=/home/fixture PATH=/home/fixture/.local/bin:/usr/bin:/bin LANG=C.UTF-8 \
        XDG_CONFIG_HOME=/home/fixture/.config XDG_DATA_HOME=/home/fixture/.local/share \
        XDG_STATE_HOME=/home/fixture/.local/state XDG_CACHE_HOME=/home/fixture/.cache \
        XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
        "$@"
}
for ((attempt=0; attempt<90; attempt++)); do
    if timeout 5 systemctl is-active --quiet systemd-logind.service dbus.service >/dev/null 2>&1; then break; fi
    sleep 1
done
timeout 10 loginctl enable-linger fixture >/dev/null 2>&1 || fail
ready=false
for ((attempt=0; attempt<90; attempt++)); do
    if [[ -S /run/user/1000/bus ]] && as_user timeout 5 systemctl --user is-active --quiet default.target >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
[[ $ready == true ]] || fail
# No PAM/session creation; reject pre-existing human login sessions as well.
sessions=$(timeout 5 loginctl show-user fixture -p Sessions --value 2>/dev/null) || fail
for session in $sessions; do
    [[ $session =~ ^[a-zA-Z0-9_-]+$ ]] || fail
    [[ $(timeout 5 loginctl show-session "$session" -p Class --value 2>/dev/null) == manager ]] || fail
    [[ $(timeout 5 loginctl show-session "$session" -p Service --value 2>/dev/null) == systemd-user ]] || fail
done
chmod 0700 /home/fixture
install -d -o fixture -g fixture -m 0700 /home/fixture/.local/bin
[[ ! -e /home/fixture/.local/bin/remote-herdr-core ]] || fail
install -o fixture -g fixture -m 0755 /opt/f01/source/dot_local/bin/executable_remote-herdr-core /home/fixture/.local/bin/remote-herdr-core
as_user timeout 600 /usr/bin/python3 -I /opt/f07/kept-probe.py
