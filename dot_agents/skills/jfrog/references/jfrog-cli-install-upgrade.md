# JFrog CLI prerequisite and installer ownership

The base `jf api` capability needs CLI 2.100.0 or later; the complete collection's
setup workflow needs 2.106.0. A lower or missing CLI is an unmet prerequisite,
not consent to replace the user's selected owner or install another runtime.

For this distribution, use its optional default-off missing-only CLI installer
when explicitly selected. It pins official 2.129.0 platform assets and hashes,
qualifies in a private isolated CLI home and preserves existing installations.
For another environment, first identify its actual installer and supported update
workflow. An existing Homebrew/Mise/package-managed CLI stays with that owner.
Do not add a second npm installation, alter global PATH or run a floating
`curl | sh` installer from copied upstream instructions.

Updates are separate reviewed work: inspect release notes, exact asset integrity,
compatibility, native owner and recovery before replacing anything. Do not issue
a mandatory upgrade offer at the end of unrelated tasks or run network/cache
version helpers on every skill load. Compatible existing versions need not match
the distribution's bootstrap version.

When version qualification is the task, use the selected installer's supported
metadata or a bounded isolated probe so normal CLI configuration/plugins and
telemetry cannot execute as an unnoticed diagnostic side effect. CLI availability,
server identity, authentication and a successful platform operation remain
separate observations. See [local ownership](local-ownership.md).
