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

**Validation:** Focused inference behavior tests and affected lifecycle/control
plane suites passed. Final independent review and Gate Commit are pending.

**Gate exceptions:** None.

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
