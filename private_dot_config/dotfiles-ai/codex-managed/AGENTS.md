# Managed Codex CLI

Use the repository instructions and shared DBSCTR lifecycle. Codex is a peer
runtime; it does not own lifecycle state, infer unavailable identity, or fall
back to another runtime.

Keep prompts, transcripts, credentials, account data, tool input and output,
URLs, environment data, and machine paths out of shared evidence. Use only the
explicit sandbox and approval policy supplied by the parent launch.

Worktrunk owns task checkout creation, navigation and removal. Keep primary
checkouts stable. Codex CLI and Desktop may retain the current conversation and
select a Worktrunk task checkout as the explicit operation target. Give every
repository command that working directory and edit files through absolute paths
under it. Desktop worktree attachment and conversation relocation are not DBSCTR
prerequisites. A shell directory change does not retarget or authenticate the
conversation. Invoke `dbsctrctl` through native tool permissions against that
explicit checkout; it preserves lifecycle gates, not transparent task routing.
If native tools cannot access the selected checkout, report that capability gap
and retain the work; do not invent session identity or bypass a denied operation.
Do not use retired continuation receipts, attachment or writer-transfer commands.
Unavailable native actor/message/call identity stays unavailable.
Use native template-based creation. Worktrunk `switch --path` is an explicit
operator exception, not an automatic agent route. Its custom creation destination
is unavailable to the 0.81.0 pre-switch hook; do not claim storage validation for it.

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
