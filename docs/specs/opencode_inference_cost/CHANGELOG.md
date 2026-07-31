# Changelog - OpenCode Inference Cost Reporting

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
