---
name: attack-surface-probe
description: Probe explicitly authorized own applications, hosts, and environments with the installed Omarchy attack-surface toolchain; report capability gaps without installing tools or scanning by default.
---

# Attack-Surface Probe

Default deny. Probing runs only against targets the operator explicitly named
for this request, in writing, with scope and time window. Ownership must be
verifiable (your accounts, your hosts, your lab). Loading this skill or the
toolchain's presence authorizes nothing.

1. **Probe capability first.** Check `command -v` for each selected tool in
   [references/toolchain.md](references/toolchain.md). A missing tool is an
   explicit capability gap: report it; never install, never substitute an
   unvetted tool, and never run a partial probe whose reduced coverage you
   cannot state.
2. **Smallest sufficient technique.** Match the tool to the question (service
   inventory, TLS or SSH configuration audit, web surface, dependency and
   credential strength). State target identity, revision, scope, exclusions and
   coverage limits before running anything.
3. **Guard execution.** Bound rates and threads. No credential testing against
   third-party services. Wordlist and cracking work only against your own
   extracted test hashes. Wireless or radio work stays on hardware you own.
4. **Keep evidence private.** Findings, target names, addresses and raw output
   go to the operator's private storage (DBSCTR Cycle Record or an approved
   store), never into a public repository. Redact credentials even in private
   notes.
5. **Report honestly.** A clean probe is absence of findings within stated
   coverage, not proof of security. Separate verified facts from hypotheses and
   name the next missing check.

The pinned runtime scanners (Semgrep CE, Gitleaks, OSV-Scanner) stay under
`security-toolkit` `runtime.md` ownership with their own selected policies; do
not reinstall or reroute them through this toolchain. On hosts without the
Omarchy toolchain profile enabled, report the gap and stay in static review.
