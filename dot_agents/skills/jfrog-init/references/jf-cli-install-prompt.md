# Missing or broken JFrog CLI

First distinguish absent executable, incompatible version, failure, hang and PATH
shadowing. Record the selected executable/owner without printing credentials. Do
not claim a broken CLI is missing or replace it to make a diagnostic pass.

Use the existing native installation owner. For dotfiles-ai, the optional
missing-only CLI installer is independent from skill deployment; it never repairs
or overwrites a different existing installation. Preserve current bytes and report
unmet readiness if the executable is broken. A user-authorized repair needs its
concrete version/source, affected path, owner, integrity check and rollback.

The retained upstream installer uses global npm, fallback registries/direct
binary installation and shell startup edits. Do not execute it as an init branch.
See [mechanics](jf-cli-install-internals.md) and [helper boundaries](script-invocation.md).
