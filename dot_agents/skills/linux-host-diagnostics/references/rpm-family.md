# RHEL/Fedora Host Boundaries

Use the actual distribution/release and installed tool help. RHEL and Fedora have
different support/update policies and may expose different DNF implementations;
do not substitute Fedora upgrade procedures for a RHEL maintenance task.

## Packages and transactions

Use the exact installed package name/version and configured repository authority.
`rpm -q PACKAGE` and relevant DNF history can establish state without installing
updates. Verify the installed command's subcommands/options before constructing a
transaction. Package rollback depends on available versions, data migrations and
support policy; a history entry alone does not prove reversibility.

Use the existing package/repository owner for a repair. Do not add repositories,
perform a distribution upgrade or remove dependent packages as an incidental fix.

## SELinux and filesystem access

Distinguish discretionary permissions, mount options, user namespaces and SELinux.
Inspect the selected path's label, enforcing state and relevant AVC denials when
authorized log access is available. Correlate the denial with the actual process,
path and operation; redact sensitive output and retain only relevant evidence.

Prefer a policy-consistent correction, such as an appropriate persistent file
context, over disabling enforcement. Review any proposed label change against
the installed policy and affected consumers; recursive relabeling of shared or
system directories can affect unrelated services. Generating a policy module
from every denial without understanding it can authorize the wrong access.

## systemd and networking

Keep user units and system units separate. Inspect the exact unit/drop-ins and
its bounded journal, not every service. A unit's configured environment, home,
working directory and access can differ from an interactive login shell.

For firewalld, establish the active interface/zone and the required source,
destination and port. Runtime and permanent configuration have different
persistence. A local listener, an open firewall rule and successful remote access
are separate claims. Configuration reload/restart and firewall/package changes
are operations under existing authorization, not read-only diagnostic steps.

## Primary references

- [Red Hat SELinux documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_selinux/index)
- [Fedora system administration documentation](https://docs.fedoraproject.org/en-US/quick-docs/)
- [systemd unit semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)

Select documentation matching the target release. An unavailable documentation
site or privileged log is an evidence limitation, not a successful check.
