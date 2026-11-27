#!/usr/bin/env bash
# Disposable container only. Creates two test users and a controller.
set -euo pipefail
trap 'printf "Fixture failed at line %s\n" "$LINENO" >&2' ERR
[[ $(cat /run/systemd/container) == podman && -f /opt/inputs/dbsctrctl ]]
format=${1:-sha1}
[[ $format == sha1 || $format == sha256 ]]
umask 022
systemctl start dbus.socket
systemd-creds setup
install -d /usr/local/bin /usr/local/libexec /etc/dbsctr-forgejo /opt/git-fixture/example /etc/ssl/certs
install -m 0755 /usr/bin/git /usr/local/bin/git
install -m 0755 /usr/bin/python3 /usr/local/bin/python3
install -m 0755 /opt/inputs/dbsctrctl /usr/local/libexec/dbsctrctl
install -m 0644 /opt/inputs/*.socket /opt/inputs/*.service /etc/systemd/system/
for pair in teammate:2101 controller:3101 other:2102; do
    user=${pair%:*}
    uid=${pair#*:}
    printf '%s:x:%s:%s:Fixture:/nonexistent:/usr/bin/nologin\n' "$user" "$uid" "$uid" >> /etc/passwd
    printf '%s:x:%s:\n' "$user" "$uid" >> /etc/group
done
git init -qb main --object-format="$format" /opt/git-fixture/seed
git -C /opt/git-fixture/seed -c user.name=Fixture -c user.email=fixture@example.invalid \
    commit -qm baseline --allow-empty
git clone -q --bare /opt/git-fixture/seed /opt/git-fixture/example/repo.git
git -C /opt/git-fixture/seed -c user.name=Fixture -c user.email=fixture@example.invalid \
    commit -qm next --allow-empty
git -C /opt/git-fixture/seed push -q /opt/git-fixture/example/repo.git main
openssl req -config /dev/null -x509 -nodes -days 1 -newkey rsa:2048 \
    -subj /CN=127.0.0.1 -addext subjectAltName=IP:127.0.0.1 \
    -keyout /opt/git-fixture/key.pem -out /opt/git-fixture/cert.pem >/dev/null 2>&1
install -m 0644 /opt/git-fixture/cert.pem /etc/ssl/certs/ca-certificates.crt
install -m 0644 /opt/git-fixture/cert.pem /etc/ssl/cert.pem
systemd-run --unit=forgejo-https-fixture --quiet /usr/local/bin/python3 /opt/inputs/https.py
for attempt in 1 2 3 4 5; do
    if test -f /opt/git-fixture/ready; then break; fi
    sleep 1
done
test -f /opt/git-fixture/ready
instance=$(printf '%s' '[2101,"https://127.0.0.1:18443","example/repo","reader","refs/heads/main"]' | sha256sum | cut -d ' ' -f1)
prefix="dbsctr-forgejo@$instance"
install -d "/etc/systemd/system/$prefix.service.d" "/etc/systemd/system/$prefix.socket.d"
# /usr/local is a throwaway tmpfs in the runner. Use its root-owned native
# interpreter copy rather than the unprivileged read-only host bind.
printf '[Service]\nUser=controller\nGroup=controller\nStandardError=journal\nExecStart=\nExecStart=/usr/local/bin/python3 -I -B /usr/local/libexec/dbsctrctl _forgejo-broker-serve %%i\n' > "/etc/systemd/system/$prefix.service.d/fixture.conf"
printf '[Socket]\nSocketGroup=teammate\n' > "/etc/systemd/system/$prefix.socket.d/fixture.conf"
printf '{"uid":2101,"controller_uid":3101,"origin":"https://127.0.0.1:18443","repository":"example/repo","account":"reader","branch":"main","object_format":"%s"}\n' "$format" > "/etc/dbsctr-forgejo/$instance.json"
chown root:controller "/etc/dbsctr-forgejo/$instance.json"
chmod 0640 "/etc/dbsctr-forgejo/$instance.json"
printf '{"schema_version":1,"origin":"https://127.0.0.1:18443","repository":"example/repo","account":"reader","role":"read","expires_at":%s,"token":"dummy-native-fixture"}\n' "$(($(date +%s) + 300))" |
    systemd-creds --with-key=host --name=dbsctr-forgejo encrypt - "/etc/dbsctr-forgejo/$instance.cred"
chmod 0600 "/etc/dbsctr-forgejo/$instance.cred"
systemctl daemon-reload
systemctl start "$prefix.socket"
install -d -o teammate -g teammate -m 0700 /opt/teammate
runuser -u teammate -- git -C /opt/teammate init -qb main --object-format="$format"
runuser -u teammate -- git -C /opt/teammate remote add origin https://127.0.0.1:18443/example/repo.git
if runuser -u controller -- test -x /opt/teammate; then exit 2; fi
if runuser -u other -- test -r "/etc/dbsctr-forgejo/$instance.cred"; then exit 2; fi
compare() {
    runuser -u teammate -- /usr/local/bin/python3 -IB -c '
import pathlib, runpy
helper = runpy.run_path("/usr/local/libexec/dbsctrctl")
try:
    helper["fetch_forgejo_branch"](
        pathlib.Path("/opt/teammate"), "origin",
        {"provider": "forgejo", "origin": "https://127.0.0.1:18443", "repository": "example/repo"},
        "main", "reader", "systemd-broker")
except RuntimeError as error:
    raise SystemExit(str(error))
'
}
compare
expected=$(git -C /opt/git-fixture/seed rev-parse HEAD)
test "$(runuser -u teammate -- git -C /opt/teammate rev-parse refs/remotes/origin/main)" = "$expected"
endpoint="/run/dbsctr-forgejo/$instance.sock"
if runuser -u other -- test -w "$endpoint"; then exit 2; fi
# Give the second fixture user only socket access, then test the broker's
# independent peer-UID check. No live credentials or accounts are involved.
chmod 0666 "$endpoint"
runuser -u other -- /usr/local/bin/python3 -IB -c '
import socket, sys
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
    peer.settimeout(5)
    peer.connect(sys.argv[1])
    try:
        peer.sendall(b"DBSCTR FORGEJO 1\n")
        peer.shutdown(socket.SHUT_WR)
        assert peer.recv(1) == b""
    except ConnectionResetError:
        pass
' "$endpoint"
chmod 0660 "$endpoint"
test "$(runuser -u teammate -- git -C /opt/teammate rev-parse refs/remotes/origin/main)" = "$expected"
systemctl stop "$prefix.socket" "$prefix.service"
printf '%s\n' '{"schema_version":1,"origin":"https://127.0.0.1:18443","repository":"example/repo","account":"reader","role":"read","expires_at":1,"token":"dummy-native-fixture"}' |
    systemd-creds --with-key=host --name=dbsctr-forgejo encrypt - "/etc/dbsctr-forgejo/$instance.expired"
chmod 0600 "/etc/dbsctr-forgejo/$instance.expired"
cp -p "/etc/dbsctr-forgejo/$instance.cred" "/etc/dbsctr-forgejo/$instance.valid"
mv "/etc/dbsctr-forgejo/$instance.expired" "/etc/dbsctr-forgejo/$instance.cred"
systemctl start "$prefix.socket"
if compare >/run/fixture-expired.log 2>&1; then exit 2; fi
grep -Fxq 'Forgejo broker response unavailable' /run/fixture-expired.log
test "$(runuser -u teammate -- git -C /opt/teammate rev-parse refs/remotes/origin/main)" = "$expected"
systemctl stop "$prefix.socket" "$prefix.service"
mv "/etc/dbsctr-forgejo/$instance.valid" "/etc/dbsctr-forgejo/$instance.cred"
systemctl start "$prefix.socket"
compare
printf '%s\n' 'Native system manager, socket activation, encrypted dummy credential, authenticated HTTPS and ref import: passed.'
printf '%s\n' 'Socket access and broker independently refused the other fixture UID.'
printf '%s\n' 'Expired credential refused without ref mutation; valid replacement restored comparison.'
