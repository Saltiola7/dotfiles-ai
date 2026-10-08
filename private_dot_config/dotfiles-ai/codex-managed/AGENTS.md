# Managed Codex CLI

Use the repository instructions and shared DBSCTR lifecycle. Codex is a peer
runtime; it does not own lifecycle state, infer unavailable identity, or fall
back to another runtime.

Keep prompts, transcripts, credentials, account data, tool input and output,
URLs, environment data, and machine paths out of shared evidence. Use only the
explicit sandbox and approval policy supplied by the parent launch.

Worktrunk owns task checkout creation, navigation and removal. Keep primary
checkouts stable; open native Codex sessions in the selected task checkout and
scope searches there. A shell directory change does not retarget a resumed
session. Invoke `dbsctrctl` through native shell permissions; it registers the
explicit checkout and preserves lifecycle gates, not transparent task routing.
Do not use retired continuation receipts, attachment or writer-transfer commands.
Unavailable native actor/message/call identity stays unavailable.

For Initiative registration, obtain fresh receipt/preflight and present scope,
risk, delivery target and launch digest. Ask for explicit chat approval of that
plan. After approval, Build may run `begin` with `--expected-launch-digest DIGEST
--approval agent-confirmed`. This is an agent assertion, not authenticated
operator identity. Changed plans require renewed approval; general continuation
or shell permission is insufficient. Interactive confirmation remains available;
never synthesize its `BEGIN` input or simulate an operator terminal.
Legacy-cycle adoption and busy override also require their own operator consent.
Keep independent control-plane history hooks and managed-home/release checks.

Start DVC worktrees code-only with explicit external-cache, reflink-only setup;
materialize requested targets only. Removal requires operator authorization and
the managed Worktrunk preservation hook. Never bypass it or collect shared caches.
