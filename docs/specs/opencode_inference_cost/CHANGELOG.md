# Changelog - OpenCode Inference Cost Reporting

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
