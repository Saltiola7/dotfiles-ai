---
name: linux-host-diagnostics
description: Diagnose Linux host services, packages, permissions, storage and networking, with focused RHEL/Fedora and systemd guidance. Use for actual host failures or bounded operational changes.
---

# Linux Host Diagnostics

Establish what failed, on which host and under which identity, before proposing a
change. Preserve the current task, project policy and existing lifecycle owner.

## Establish the target

Use project inventory and existing evidence first. Record OS/distribution/release,
architecture, service manager, current user, relevant unit/package/process and the
expected versus observed behavior. Distinguish a host from a container, VM or
remote Podman service. A Linux client does not identify the target environment.

Read bounded facts such as `/etc/os-release`, the selected tool's version and an
exact service's status. Resolve user versus system service scope explicitly.
Avoid whole-machine environment dumps or collecting unrelated logs/secrets.

## Investigate the affected boundary

| Symptom | Useful evidence |
|---|---|
| Service will not start | Exact unit, effective drop-ins, executable/working directory, identity, exit result and bounded journal interval |
| Permission denied | Path ownership/mode, traversal permissions, mount options, identity mapping and security labels |
| RPM-family package issue | Installed package/version, repository ownership, dependency result and relevant transaction history |
| Network failure | Listener/bind address, route/DNS, selected firewall zone and the actual client/server path |
| Storage failure | Affected filesystem, capacity/inodes, mount/read-only state and relevant device/kernel evidence |

For RHEL/Fedora package, SELinux and service details, read
[RPM-family diagnosis](references/rpm-family.md). Load `podman-quadlet` only when
container/user-namespace or Quadlet behavior is involved. Do not infer a container
issue merely because Podman is installed.

Keep competing hypotheses until evidence distinguishes them. Missing privileged
logs or access remains a limitation; do not manufacture a root cause or escalate
through another identity to fill it.

## Bounded remediation and verification

Tie each proposed change to the observed failure, its owner and a recovery path.
Proceed within existing task authorization and native permissions; unresolved
material scope or destructive/data-impacting work needs its actual authority.
Do not turn diagnosis into a host upgrade, broad audit or security-policy rewrite.

Preserve SELinux, firewall and ownership constraints. A temporary workaround is
not acceptance evidence for the intended configuration. After an authorized fix,
verify the original failing operation under its real identity, relevant health
and persistence/restart behavior, plus any affected downstream contract.

Return target identity, observed facts, hypotheses and confidence, proposed or
actual changes, verification and remaining gaps to the existing primary/QA.
