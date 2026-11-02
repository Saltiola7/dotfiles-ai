# AI Catalog reachability and entitlement

Check this only for a selected authorized catalog-readiness task. Retained helpers
use the platform path `/ml/core/api/v1/mcp-registry/ml-projects?pageSize=1`; verify
current product/version support rather than assuming every deployment serves it.
CLI/artifact work does not require this optional feature.

| Observation | Honest conclusion |
|---|---|
| Successful authenticated read | That selected operation worked; do not infer unrelated permissions. |
| 401 | Authentication rejected; native auth owner handles recovery. |
| 403 | Request denied; distinguish known entitlement and authorization evidence without granting roles. |
| 404 | Endpoint/resource unavailable at this target/version; do not invent a catalog or switch platforms. |
| Connection failure/5xx | Actual transport/service gap; no successful readiness claim. |
| No selected target or runtime | Capability untested/unavailable, not disabled or passed. |

Never expose exported credentials or auth headers. Do not automatically create
projects, install Agent Guard, enable a registry or write `setup.json` after a
check. [Summary](final-summary-rendering.md) records independent capability gaps.
