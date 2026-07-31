---
name: dbsctr-lens-audit
description: Audit prior autonomous review sessions and propose source-controlled R&D lens improvements.
---

# DBSCTR Lens Audit

Use only when `dbsctr-rnd lens-plan` assigns `review_session_governance`.

1. Review only candidates whose validated `review_session` value is true. The
   active worker family remains excluded by federation.
2. Compare lens versions using pass telemetry: pages, sources, selected sessions,
   excluded review sessions, yield/no-yield outcome, cadence, duplicate claims,
   blocked work, and draft-PR outcomes. Missing telemetry is unavailable, not zero.
3. Propose a lens change only for concrete missed defects, repeated duplicates,
   avoidable cost, unsafe overlap, or operator friction. Never create novelty to
   avoid a truthful no-yield result.
4. Lens definitions remain source-controlled. A useful change follows ordinary
   Discovery and DBSCTR delivery to a draft pull request; it never mutates the
   active runtime registry, merges, or deploys itself.
5. Audit prior lens-audit sessions with one-pass delay. Never inspect or evaluate
   the active session family.

Return bounded sanitized findings, telemetry caveats, and either one distinct
proposal or `no_yield`.
