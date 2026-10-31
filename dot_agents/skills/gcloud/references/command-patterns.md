# Scoped CLI and operation evidence

These are patterns for a project-selected CLI version, not executable setup or
universal flags. Resolve required values from the authorized task, verify exact
leaf help when needed, and use safely quoted arguments or structured argv.

## Bounded resource discovery

Use explicit project and location where the resource supports them. A bounded
sample can reveal output shape, but an empty response does not establish schema
or prove no resource exists outside the query's permissions/filter/page.

```bash
gcloud compute instances list --project="$PROJECT_ID" \
  --filter="$INSTANCE_FILTER" --limit=20 \
  --format='json(name,zone,status)'
```

Filters and projections have separate documented syntax. Preserve shell quoting;
verify field paths and semantics for the actual resource. Relevant official help:
`gcloud topic filters`, `gcloud topic formats`, and `gcloud topic projections`.
A restricted projection alone does not bound the number of returned objects.
When completeness is required, account for pagination, time limits, filters and
visibility; do not label a sample as a complete inventory.

## Concrete commands versus plans

Check exact leaf help for unfamiliar/version-sensitive flags, such as
`gcloud help container clusters describe`. Use official documentation for the
applicable version when the local capability is unavailable, and disclose the
limit. A conceptual design can describe required outcomes before choosing flags.
Do not require a fixed plan length, additional approval or a CLI installation to
answer a conceptual question.

## Preview and asynchronous operations

Choose a supported preview or validation mode that addresses the affected risk.
Do not assume every command has `--dry-run`, `--validate-only`, `--async`, a generic
`operations describe` group, or identical project/location parameters. Local
syntax validation, service-side preview and actual resource health are distinct.

For an authorized asynchronous change, capture a non-secret operation identity
and its service-specific status authority. Poll within the task's finite policy,
handle terminal failure/cancellation honestly, and verify the required readiness
or recovery outcome. Exit zero can mean the request was merely accepted.

## Identity and sensitive output

Prefer project-selected short-lived identity and per-command context when it
suffices. Changing active configuration, impersonation, ADC or kubeconfig is a
state change. Do not echo access/identity tokens, credential files, request
headers or unredacted sensitive configuration into output or evidence.

Use a task-selected output format and preserve actual exit status. Non-empty
stderr may contain ordinary progress; do not relabel a nonzero exit as success or
a successful submission as a completed deployment. Constrain/redact evidence
before retaining it in shared artifacts.

## Sources

- [CLI scripting](https://cloud.google.com/sdk/docs/scripting-gcloud)
- [Filters](https://cloud.google.com/sdk/gcloud/reference/topic/filters)
- [Formats](https://cloud.google.com/sdk/gcloud/reference/topic/formats)
