# Failed-operation diagnosis details

Locally modified adaptation of the pinned official skill; see
[upstream attribution](../UPSTREAM.md). This method diagnoses one operation from
recorded evidence without rerunning it just to reproduce the error.

## Resolve the exact record

Reuse the user-provided backend, organization/project/stack, operation kind and
update version or preview ID. A stack name may be ambiguous across projects or
backends. Project files, existing links, bounded history and current task facts can
fill missing fields; avoid dumping configuration or credentials. Do not assume the
locally selected stack is the intended one when it conflicts with the request.

When an immutable operation is already identified, state that identity and proceed
under existing read authority. Do not force a second confirmation. If identity is
materially ambiguous, inspect bounded candidate metadata or ask one focused
question. A missing version does not mean latest unless the user actually selected
latest. Actor login, including `requestedBy.githubLogin`, is evidence about a run,
not proof that it is the operation the user means.

Prefer records available in the project's selected backend, CI artifact or local
event log. Cloud REST examples below are conditional on an existing Pulumi Cloud
backend, compatible CLI/API and authorized access; they do not require Cloud login
or a new account for a DIY backend. Displayed update versions and backend operation
IDs may differ. Resolve the identifier required by the actual endpoint from its
record rather than substituting an arbitrary version into an ID field.

## Retrieve bounded events and preserve failures

With a compatible Cloud API, the event path has the following shape. `event_path`
must already contain the resolved kind and operation identifier; `record_file` and
`diagnostic_file` are approved private evidence paths because raw messages can
contain sensitive data. Use protected storage under the project's evidence policy.
The response schema and flags must match the selected CLI/API. No tool installation
is implied by the example.

```sh
# Example shape: /api/stacks/ORG/PROJECT/STACK/update/OPERATION_ID/events
# Preview uses the corresponding preview/OPERATION_ID/events path when supported.
if pulumi api "$event_path" > "$record_file"; then
    : # Fetch succeeded; now inspect/validate the response before extracting fields.
else
    fetch_status=$?
    printf 'Operation-event fetch failed (status %s)\n' "$fetch_status" >&2
    exit "$fetch_status"
fi

# If jq is already available, validate expected events before formatting locally.
if jq -e '(.events | type) == "array"' "$record_file" > /dev/null; then
    if jq -r '.events[].diagnosticEvent | select(. != null) |
        "[\(.severity)] \(.message)"' "$record_file" > "$diagnostic_file"; then
        : # Inspect privately; publish only a bounded, reviewed non-secret subset.
    else
        parse_status=$?
        printf 'Diagnostic extraction failed (status %s)\n' "$parse_status" >&2
        exit "$parse_status"
    fi
else
    printf 'Unexpected event response; record coverage is unavailable\n' >&2
    exit 1
fi
```

Do not interpret that one page as complete. Follow the endpoint's opaque
`continuationToken` with correct URL encoding and the same operation identity;
retain event ordering/coverage, page errors and a bounded stopping condition. A
still-running operation can return the same continuation token without new events.
Stop bounded polling and report partial coverage rather than loop forever. A
completed record with no continuation and the expected terminal status provides
stronger completeness evidence than an empty diagnostic filter alone. History
list pagination and event continuation can use different schemes; follow the
selected endpoint documentation. If size limits or permissions prevent full
coverage, retain that gap.

Keep stderr and the true exit status of fetch and parsing steps. Piping a failed
`pulumi api` into a successful formatter must not turn it into a successful fetch.
Do not infer success from an empty output file or assume a 404 means no failure.
Review the approved private messages before quoting a minimal redacted subset;
never publish tokens, secret outputs, full state exports or unreviewed raw logs.

Read relevant diagnostics beyond `severity == "error"`. Program stderr can be
reported as `info#err`; provider, policy, warning and cancellation messages can
explain a failure chain. Correlate resource URN/type and operation metadata with
the actual program revision, provider versions and input/config identities.
Terminal color markers such as `<{%reset%}>` can be removed for readability after
successful parsing; keep the underlying evidence unchanged.

## Locate the cause

An operation can have several independent errors. Start with relevant root errors
and dependencies; do not treat every trailing failure as a separate root cause.
Tie claims to specific evidence and distinguish hypothesis from confirmation.

- **Program:** Invalid references/types, rejected inputs or lost Output dependencies
  can require a code fix. A preview can also fail from permissions, providers or
  network access; do not assume every failed preview is a program defect.
- **State/resource reality:** A partial update may already have changed resources.
  Compare the relevant recorded/current metadata through available read authorities.
  Drift or unmanaged resources may justify a separately selected refresh/import
  plan; they do not authorize it automatically, and an arbitrary retry can worsen
  partial changes. Preserve data, deletion protection and recovery obligations.
- **Environment:** Credentials, IAM/OIDC, quota, connectivity, runtime or provider
  availability can be causal. Diagnose the actual selected identity and rejected
  operation; do not switch accounts, broaden permissions, edit ESC or upgrade a
  provider merely because an error mentions them.

When the recorded diagnostic is thin, inspect a bounded relevant subprocess,
provider or CI log if available within existing authority. State missing access,
coverage, tool support or source revision precisely. Do not manufacture credentials,
install a CLI/SDK or declare success from unavailable evidence.

## Fix and verify through the current workflow

Make the smallest authorized change at the actual cause. Preserve the current
primary, project tests and delivery gates; this skill does not create a PR flow or
new coordinator. Reuse the selected runtime/dependency/backend/stack contracts.

Separate evidence claims: a source/type/unit check supports that scope; a preview
executes program/provider work; an update mutates infrastructure; operation
completion and workload health are separate. Refresh/import, state/config/IAM/ESC
changes, retries and deployment need appropriate existing task authorization and
exact target/recovery evidence. Resolve missing material authority immediately
before the action rather than repeatedly asking about authorized reads.

Report the immutable operation, evidence and coverage, confirmed cause or
remaining hypotheses, fix location, validation actually run, partial changes and
next bounded step. Do not state that a proposed fix recovered the environment.

## Official references

- https://www.pulumi.com/docs/reference/cloud-rest-api/stack-updates/
- https://www.pulumi.com/docs/iac/cli/commands/pulumi_api/
- https://www.pulumi.com/docs/iac/concepts/state-and-backends/
- https://www.pulumi.com/docs/iac/concepts/inputs-outputs/apply/
