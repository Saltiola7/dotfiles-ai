# Selection and evidence

| Request | Select | Boundary |
|---|---|---|
| Implement or review a security-sensitive change | `codeguard` selected guidance | Fourteen topics; project controls and affected tests govern. No audit claim. |
| Security scan, diff/deep scan, triage or finding validation | Matching native Codex Security workflow, if actually available | Provider plugin/runtime is separate. The dotfiles bundle does not install it. Missing tools stay unavailable. |
| Independent source audit or explicit second opinion | Cloudflare `security-audit` | One coordinator, explicit full-audit request, coverage ledger and independent validation. Guidance mode otherwise. |
| Look for variants of a known bug | `variant-analysis` | Start from established root cause; stay in approved scope; new candidates need their own trace. |
| Credential object leakage | `secret-serialization` | Actual unauthorized holder-to-sink exposure; dummy evidence only. |
| GitHub Actions exploitation review | `gha-security-review` | External-contributor technique, effective permissions and downstream sinks; not complete CI assurance. |
| Review a new skill/source before adoption | This toolkit's review criteria | Read the complete proposed bundle and executable dependencies; no automatic installer or scanner. |

Select Codex Security as primary when it is available and chosen. A separately
requested Cloudflare run is an independent opinion, not a competing nested
coordinator. Specialists return bounded evidence to the current primary. Do not
replace an unavailable or denied provider workflow with another route to bypass
its boundary. Report unavailable capabilities without inventing readiness.

## DBSCTR and QA

The DBSCTR Engineering Profile selects authorities. These skills inform the
affected security outcomes; they do not make every change an audit or replace
QA's configured scanner/test gates. Retain one authoritative result per concern.
Record target identity, revision/dirty state, scope/exclusions, chosen technique
and version, validation state, and coverage limits in private cycle evidence.
Keep proprietary source and findings out of this public skill bundle.

Deduplicate by root cause and affected boundary. A confirmed finding needs a
lower-trust principal, controlled input, source-to-sink trace, failed control and
concrete impact. Only confirmed findings receive severity. Needs-validation
items name the exact missing fact and safe next check; rejected candidates keep
the disproof. A structural validator pass is not an audit or security-gate pass.
Remediation, publishing and deployment need their own applicable authorization.

## Execution and data flow

Source review uses the approved provider and current permissions. Model context
may disclose selected source to that provider even when subprocess networking is
disabled. Do not introduce a provider or upload destination silently.

For audit and vulnerability-reproduction workflows that execute untrusted target
code, require every isolation control of the selected workflow:
OS-enforced network isolation, sanitized allowlisted environment, read-only
source/toolchain, scratch-only writes, no ambient credentials/sockets, and
resource limits. Without them, remain in static review and report the missing
validation capability. Skill installation supplies none of those controls.
Ordinary implementation/testing follows the project/DBSCTR authorities and
native permissions; loading CodeGuard does not impose a full audit sandbox.
Cloudflare validators use existing Node.js on trusted parent-owned input paths;
they do not reject every ancestor-link/hardlink condition or enforce isolation.

Deterministic tools are separate project authorities: existing Semgrep CI is not
modified by installing these skills. Explicit local-tool setup is a separate requested action; use `runtime.md` and
`local_tools.py status --smoke` to distinguish installed executables from scan
readiness. Keep all subscription integrations disabled until the user confirms
entitlement; a ChatGPT subscription or executable presence is not entitlement.
Select pinned
rules and metrics policy for Semgrep, redacted output for secrets tools, and
offline database freshness for OSV only when that separately configured layer
is requested and available. CodeQL needs license/build/pack review first.
