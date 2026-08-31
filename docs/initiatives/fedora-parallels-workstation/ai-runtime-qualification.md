# AI Runtime Qualification

OpenCode and Codex CLI qualify independently after AI distribution is deployed.
Both require exact executable/configuration identity, guest-local authenticated
operation, isolated private state, and no host credential or session copy.

OpenCode qualification runs the managed configuration parser, provider/auth
status, one bounded disposable session, Herdr integration, and DBSCTR tool smoke.
Codex qualification repeats the frozen-release identity matrix on the Parallels
Fedora platform through supported hooks, CLI JSONL, and app-server methods. It
retains only bounded content-free relation and digest evidence. Ambiguous,
unavailable, mismatched, or copied identity blocks qualification without
fallback to another runtime.

Upgrading either frozen runtime invalidates only that runtime's qualification
and requires its version-specific probes again.
