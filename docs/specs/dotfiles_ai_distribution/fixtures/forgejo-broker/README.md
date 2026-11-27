# Forgejo comparison broker: administrator handoff

These source templates are not installed by chezmoi. Do not enroll a real
token until the candidate has passed the disposable systemd fixture and
review required by the [controller isolation contract](../../features/forgejo-controller-isolation.md).

For each authorized teammate, use one distinct non-login controller UID,
with no administrative access. Both account creation and filesystem
installation are host-administrator operations. Install the reviewed
`dbsctrctl` as a root-owned executable at `/usr/local/libexec/dbsctrctl`; keep
its parent directories and the systemd units administrator-writable only.
Install the matching client under the normal managed DBSCTR owner.

For each repository, configure one instance:

1. Compute the instance name from the caller UID, canonical origin,
   repository, read account and full comparison ref using the canonical
   tuple in the contract. The ref for branch `main` is `refs/heads/main`.
2. In `/etc/dbsctr-forgejo`, create root-owned `<instance>.json`, readable
   only by root and the dedicated controller group. Required keys are `uid`,
   `controller_uid`, `origin`, `repository`, `account`, `branch`, and
   `object_format` (`sha1` or `sha256`). `branch` contains the branch name,
   not the full ref. Both UIDs are integers. The directory itself must be
   root-owned, not group/world-writable, and traversable by service users.
3. In the service instance drop-in set `User=` and `Group=` to the dedicated
   controller. In the socket instance drop-in set `SocketGroup=` to a group
   granting the enrolled teammate socket access. The controller still checks
   the connecting UID even when socket file permissions permit connection.
4. Use `systemd-creds encrypt --name=dbsctr-forgejo --with-key=host - OUTPUT`
   with the existing Forgejo envelope provided privately on stdin. `OUTPUT`
   is a temporary file in a root-only staging directory. Keep input out of
   scripts, shell history, logs, environment variables and Git. Install the
   ciphertext atomically as root-owned mode `0600` at
   `/etc/dbsctr-forgejo/<instance>.cred`. The selected Forgejo account and
   token must be read-only and limited to the enrolled repository.
5. Verify the exact systemd instance and groups, reload the system manager,
   and start only the reviewed socket. Run the existing checkout preflight
   with `--forge-credential-source systemd-broker`. A digest is evidence of a
   successful check, not approval to register. No worker may act as root or
   as the controller account.

Rotate by stopping the socket and settling or stopping the service, replacing
the encrypted credential atomically, then starting the socket and verifying a
fresh preflight before retiring the old token. If a token is suspected exposed,
revoke it immediately instead. To withdraw enrollment, stop the socket and
service, revoke the token, and remove only that instance's configuration and
credential. Do not remove the teammate's checkout or DBSCTR records.
