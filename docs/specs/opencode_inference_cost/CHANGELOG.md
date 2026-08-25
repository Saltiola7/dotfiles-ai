# Changelog - OpenCode Inference Cost Reporting

## 2026-08-25 - Canonical Completion Reconciliation

- Closed OIC-009 against merged Fast-rate evidence and verified that structured
  history already reports absent provider cost as `unavailable`, not zero. No
  rate card or report behavior changed.

## 2026-08-23 - Managed OpenAI Fast Estimates (v0.4)

**Outcome:** Added exact effective-dated list-price entries for managed Sol Fast,
Terra Fast, and Luna Fast usage. Priority-processing token-class rates are twice
the corresponding standard rates and start at `2026-08-23T00:00:00Z`; near
identities and complete usage intervals beginning before that boundary remain
unestimated.

**Provenance and validation:** Existing standard rates were reverified unchanged
before the card retrieval date advanced. The missing Fast entry produced the
intended red failure, then six focused inference-cost tests and Git whitespace
validation passed. Independent review findings on retrieval-date provenance and
boundary evidence were remediated; final review found no material issue.

**Gate exceptions:** None. **Gate Commit:** `48dd3a4`. **Deployment:** Not run.
Intended Final Push: feature branch and verified draft pull request into protected
`main`.

## 2026-08-18 - Canonical Ticket Migration

- Migrated active and completed inference-cost work records to independently
  validated PM Kernel tickets with original row provenance.

## 2026-07-31 - Message-level context attribution (v0.3)

**Outcome:** Replaced lossy session-grain model and context attribution with
allowlisted OpenCode `step-finish` metadata joined to parent assistant messages.
Each reconciled usage record is assigned through a half-open DBSCTR context
interval; non-DBSCTR, abandoned, and interval-less historical usage remains
`UNKNOWN`, while overlapping contexts remain `MULTI_CONTEXT`.

**Reconciliation:** Session aggregates remain authoritative controls. Exact
canonical parts receive message/model/context detail; eight legacy live sessions
with historical source inconsistencies were quarantined once into `UNKNOWN`.
The live report retained 99.9886% token reconciliation coverage without
fabricated allocation.

**Privacy and compatibility:** SQL projects only opaque IDs, timestamps,
provider/model/variant, cost, and token classes through explicit JSON paths.
Raw message/part JSON and content never enter persisted output. Schema v2 replaces
v1 in place; existing history without interval fields remains valid and is not
migrated.

**Validation:** Focused red/green behavior tests, Python compilation, and the
reconciled union suite passed `271 tests` with one optional Lima skip. Live
metadata-only dry-run and full report generation succeeded. Independent review
was unavailable because its sandbox could not read the isolated worktree; primary
diff review found no unresolved issue.

**Gate exceptions:** None. **Gate Commit:** `0315f15`. **Deployment:** Not run.
Intended Final Push: feature branch and verified draft pull request into protected
`main`.

## 2026-07-30 - MVP implemented (v0.2)

**Outcome:** Added the read-only `inference-cost-report` CLI, current OpenCode
session-schema capability adapter, sanitized DBSCTR context attribution, separate
recorded/list-price costs, deterministic descriptive statistics, and coherent
JSON/Markdown/manifest publication.

**Privacy:** Queries project only session ID, timestamp, provider/model metadata,
cost, and token counters. Synthetic sentinels prove title, path, metadata,
message, part, prompt, response, and tool arguments do not enter output.

**Rates:** Added effective-dated official OpenAI standard short-context prices.
Unsupported providers, long contexts, missing token-class rates, and ambiguous
zero recorded costs remain null and lower coverage.

**Validation:** `200 passed, 1 skipped` across focused inference,
`test_dbsctrctl`, lifecycle, and control-plane suites; metadata-only live dry run
and full local report generation succeeded; final independent review found no
remaining material issues.

**Review remediation:** Sanitized path-bearing input errors, exposed monetary
and attribution coverage in Markdown, retained attribution source/confidence,
clarified conservative session-grain pricing, and made interrupted publication
self-recovering. Re-review additionally hardened rate-source URLs and bound each
estimate to a rate entry covering the complete session lifetime.

**Gate exceptions:** None.

**Gate commits:** `1a5b8a9`, `ab46a73`, `85ab5b8`, `67056a2`.

**Deployment:** None. The command and rate card are delivered through the normal
dotfiles apply path; this cycle does not apply local configuration.

## 2026-07-30 - Specification created (v0.1)

**Outcome:** Defined a portable DBSCTR-ready MVP for reporting OpenCode token
usage, model mix, actual cost, list-price estimates, descriptive statistics,
and attribution coverage by bounded context.

**Key decisions:** OpenCode remains the usage authority; sanitized DBSCTR
telemetry supplies context evidence; actual and estimated cost remain separate;
ambiguous and unknown usage stay visible; prompt and response content is outside
the source contract.

**Evidence:** Sanitized DBSCTR history demonstrated available token totals but
ambiguous context and unavailable provider/model IDs in at least one archived
sample, so DBSCTR aggregates alone cannot satisfy model-level costing.

**Gate exceptions:** None.

**Implementation:** Pending transfer to and reconciliation with the owning
dotfiles/DBSCTR repository.

**Intended delivery:** Feature branch and verified draft pull request into the
target repository's protected base. No deployment or package publication.
