#!/bin/bash
# Hosted disposable container only. No PAM login, journals or native output.
set -euo pipefail
umask 077
stage=initialization
fail() { echo "F07: shell-invariant-failed-$stage" >&2; exit 1; }
[[ $EUID == 0 && $(cat /proc/1/comm) == systemd ]] || fail
[[ $(uname -m) == x86_64 ]] || fail
[[ $(systemd-detect-virt --container) == docker ]] || fail
uid=$(id -u fixture)
as_user() {
    setpriv --reuid "$uid" --regid "$(id -g fixture)" --init-groups \
        env -i HOME=/home/fixture USER=fixture LOGNAME=fixture TERM=xterm-256color LANG=C.UTF-8 \
        PATH=/home/fixture/.local/bin:/usr/local/bin:/usr/bin:/bin \
        XDG_CONFIG_HOME=/home/fixture/.config XDG_DATA_HOME=/home/fixture/.local/share \
        XDG_STATE_HOME=/home/fixture/.local/state XDG_CACHE_HOME=/home/fixture/.cache \
        XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
        "$@"
}
wait_user() {
    local attempt
    for ((attempt = 0; attempt < 90; attempt++)); do
        if [[ -S /run/user/$uid/bus ]] && as_user timeout 5 systemctl --user is-active --quiet default.target >/dev/null 2>&1; then return; fi
        sleep 1
    done
    # Only fixed systemd state properties from this disposable fixture account;
    # never journals, environment, unit contents, registrations or native output.
    systemctl show "user@$uid.service" --property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus --no-pager || true
    fail
}
no_login() {
    local sessions session manager class service owner leader
    sessions=$(timeout 5 loginctl show-user fixture -p Sessions --value 2>/dev/null) || fail
    manager=$(timeout 5 systemctl show "user@$uid.service" -p MainPID --value 2>/dev/null) || fail
    [[ $manager =~ ^[0-9]+$ && $manager -gt 1 ]] || fail
    for session in $sessions; do
        [[ $session =~ ^[a-zA-Z0-9_-]+$ ]] || fail
        class=$(timeout 5 loginctl show-session "$session" -p Class --value 2>/dev/null) || fail
        service=$(timeout 5 loginctl show-session "$session" -p Service --value 2>/dev/null) || fail
        owner=$(timeout 5 loginctl show-session "$session" -p User --value 2>/dev/null) || fail
        leader=$(timeout 5 loginctl show-session "$session" -p Leader --value 2>/dev/null) || fail
        [[ $class == manager && $service == systemd-user && $owner == "$uid" && $leader == "$manager" ]] || fail
    done
}
case ${1:-} in
    prepare)
        stage=prepare-precondition
        [[ ! -e /var/lib/f07/prepared ]] || fail
        for ((attempt = 0; attempt < 90; attempt++)); do
            if timeout 5 systemctl is-active --quiet systemd-logind.service dbus.service >/dev/null 2>&1; then break; fi
            sleep 1
        done
        stage=enable-linger
        timeout 10 loginctl enable-linger fixture >/dev/null 2>&1 || fail
        stage=wait-user
        wait_user
        stage=copy-source
        install -d -o fixture -g fixture -m 0700 /home/fixture/.local/share
        cp -R /opt/f01/source /home/fixture/.local/share/chezmoi-dotfiles-ai
        chown -R fixture:fixture /home/fixture/.local
        as_user timeout 900 python3 /opt/f07/verify-user.py prepare
        touch /var/lib/f07/prepared /run/f07-core
        ;;
    verify-core)
        stage=verify-core-precondition
        [[ -f /var/lib/f07/prepared && ! -e /run/f07-core && ! -e /var/lib/f07/core-verified ]] || fail
        wait_user
        [[ $(timeout 5 loginctl show-user fixture -p Linger --value 2>/dev/null) == yes ]] || fail
        no_login
        as_user timeout 600 python3 /opt/f07/verify-user.py verify-core
        touch /var/lib/f07/core-verified /run/f07-tui
        ;;
    verify-tui)
        stage=verify-tui-precondition
        [[ -f /var/lib/f07/core-verified && ! -e /run/f07-tui && ! -e /var/lib/f07/qualified ]] || fail
        wait_user
        no_login
        as_user timeout 600 python3 /opt/f07/verify-user.py verify-tui
        touch /var/lib/f07/qualified
        echo 'F07: native-layout-and-inflight-turn-qualification-complete'
        ;;
    *) fail ;;
esac
