# Scoped ASVS review workflow

Local adaptation of TarkinLarson/asvs-auditor's interactive methodology. Read
only the selected requirement chapters; [the index](../reference/README.md)
links their exact text. The current coordinator owns integration and reporting.

## Establish scope and reference

Record the target revision and dirty state, approved source paths and exclusions,
ASVS version, selected level and chapter/requirement set. Derive the selected
requirement IDs and their levels from the bundled tables, not from memory or
approximate counts. A chapter-limited review selects only that chapter's agreed
requirements; do not imply an application-wide assessment. Resolve a missing
level before a full assessment. Requirements above the selected level may be
reported separately as additional guidance without changing its denominator.

Identify actual frameworks, identities, entry points, data stores, infrastructure
and deployment assumptions. Exclude generated or third-party implementation
from first-party code review where appropriate, but retain in-scope dependency
identities, versions and trust sources. Verify whether directories such as
`packages/` contain first-party code. Test fixtures, migrations and seed data may
matter when they ship or weaken deployed controls; their directory names alone
do not decide applicability.

Use only authorized source and existing tools. Read-only source review does not
authorize executing target code, testing credentials, probing a service or
installing a scanner. Respect current source-disclosure and private-evidence
policy. Recheck the revision and relevant dirty files before finalizing; if the
source changed, re-read affected evidence or report the unresolved drift.

## Gather control evidence

Map the selected attack surface before searching for dangerous patterns. For web
applications, enumerate relevant routes, methods, handlers and inherited middleware.
For another target, identify the relevant queue, IPC, socket or privileged CLI
entry points. Check controls at their actual application sites: authentication,
operation/resource authorization, state-changing request protection and relevant
abuse defenses. A framework offering a control does not prove this handler uses
it; inherited/global controls count when their application is traceable.

Use independent searches together where useful, then follow actual call chains.
For input-to-sink concerns, record the lower-trust input, transformations, defensive
controls, sink and resulting impact. Validation appropriate to one context may
not protect another. A suspicious sink alone is a candidate; missing runtime
wiring or a plausible path is not a confirmed exploit. Separate observed code
behavior from assumptions about external reachability and deployment.

For configuration and absence concerns, examine the actual control owner, loaded
configuration and relevant deployment artifacts. Cite the existing construct
where the control belongs and describe the search that supports absence. Do not
invent a filename or line for a missing document. An exhaustive search within a
bounded scope may establish absence there; it does not establish absence outside
that scope. A missing prerequisite can make a dependent requirement inconclusive
instead of creating several findings for one unknown.

Controls may live at a proxy, identity provider, gateway or in separately owned
documentation. If their effect cannot be established from authorized evidence,
record `UNVERIFIABLE` and the specific owner/evidence needed. Judge a partial
in-repository policy against the actual requirement text rather than declaring
all documentation missing. Platform defaults are assessed for the selected
runtime and effective configuration; an unset option is not automatically wrong.

Do not treat implementation preferences as ASVS text. For example, 15.1.2 asks
for a component inventory and trusted sources; 15.2.4 concerns expected repositories
and dependency-confusion defenses. Neither by itself mandates a particular
lockfile, update bot or version-range policy. Such mechanisms can be relevant
evidence or project requirements, but a violation needs its actual authority.
ASVS is one verification standard, not an exhaustive catalog of security issues;
retain a valid concern outside it under the coordinator's normal process.

## Handle credential candidates

A filename ending in `.example`, `.template` or `.sample` does not exempt real
credential material. Distinguish an obvious synthetic placeholder or variable
reference from a plausible secret using context and authorized existing redacted
scanner evidence. A high-entropy string alone does not establish a live credential.
Never authenticate with a candidate, print its literal value, copy it into a
report, or expose it through source snippets, command arguments or tool output.
Use a redacted location and nonsecret description. Treat sensitive input under
existing approved handling; do not sweep unrelated private files because the
methodology mentions secrets. Exposure response remains with its current owner.

## Reconcile each selected requirement

Build one ledger row for every selected ID, including single-requirement N/A
and unreviewed rows. Record its level, status, evidence location or bounded
search, coverage, reasoning and any linked defect ID. Use these states:

| Status | Evidence needed |
|---|---|
| `PASS` | Located control satisfies the exact requirement within the stated scope, or an appropriate exhaustive search establishes that a forbidden construct is absent |
| `FAIL` | Evidence establishes a violation of the requirement; link its defect and failed control |
| `UNVERIFIABLE` | Required deployment, external-control or documentation evidence is outside what was available; name the missing authority |
| `INCONCLUSIVE` | Review occurred but evidence cannot establish either satisfaction or violation; name the uncertainty or missing prerequisite |
| `N/A` | Evidence shows the requirement's governing functionality/technology is absent; state the reason |
| `NOT_CHECKED` | The selected requirement was not evaluated; retain the row and explain the limit |

For site-specific controls, record `full` or `sampled n of N`, the site inventory
and sampling method. Examine high-risk sites first, then spread any remaining
sample across relevant modules. A clean sample supports only the sites examined;
unexamined sites remain a coverage limit. A sampled violation remains a violation.
Do not call sampled evidence exhaustive or silently shrink N to the inspected set.

Reconcile the selected denominator against the distinct ledger IDs. Resolve
unknown IDs, wrong levels, duplicates and missing rows from the reference before
summarizing. Count each requirement once, even when several defects affect it.
Report all six status totals, the number of sampled rows and the inspected/total
sites where relevant. The six status counts must sum to the selected denominator.
For summaries, distinguish evaluated requirements (`PASS`, `FAIL`, `UNVERIFIABLE`,
`INCONCLUSIVE`) from `N/A` and `NOT_CHECKED`; state that evaluated does not mean
satisfied. An unresolved or sampled row cannot establish full verification.

Never infer compliance from zero findings, model-generated arithmetic, a report
schema, a scanner exit code or a high checked percentage. This is an evidence
ledger, not a new CI pass/fail interface. Its counts cannot establish the truth
of the underlying observations or production detection effectiveness.

## Findings and final report

Confirm cited files/locations exist in the reviewed revision. Separate confirmed
control violations from candidates requiring validation. Each defect includes
its root cause, affected boundary/sites, evidence, assumptions, confidence and
all exact ASVS requirements it actually violates. Use one defect for one shared
root cause; independent weaknesses remain separate. Each mapped ledger row links
the same defect ID where appropriate. Keep unique-defect counts separate from
requirement/status totals. Repeated code patterns or matching CWEs alone do not
prove a shared cause.

Apply the project's current severity and risk policy where evidence supports it.
ASVS L1/L2/L3 is the selected verification target and does not mechanically decide
severity or remediation order. Where deployment context materially changes risk,
state the open question and responsible assessor instead of guessing. Useful
attack paths relate existing findings through supported links; they create no
extra requirement violation or independent finding merely by combining them.

Return a concise scope/revision statement, the requirement coverage ledger,
confirmed defects and separate candidates, external evidence requests and
coverage limits. Group remediation by root cause while retaining every verified
requirement mapping. Keep repository-specific findings and credentials out of
this public skill bundle. The coordinator decides further validation, accepted
risk, remediation, publication and any later CI qualification under existing
authority.
