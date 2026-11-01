# PM Kernel Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Explicitly invoked local PM/Jira reporting workflow, CLI, and optional PostgreSQL projection |
| Owner | dotfiles-ai maintainer |
| Languages/frameworks | Python, Markdown, SQL, Bash, and Go templates |
| Runtime/platform support | Python 3.12+, Git, OpenCode; optional rootless Podman and PostgreSQL 19 on macOS and configured Fedora Lima workspaces |
| Compatibility | Existing PM rows migrate without loss; lifecycle consumers remain ticket-blind; Jira remains optional and explicitly invoked |
| Trust/data | Local PM files may contain private project context; Jira payloads and generated reports are private |
| Delivery | Feature branch and draft pull request; local deployment only after affected gates pass |
| Authorities | `pytest`, Git fixed-commit inspection, chezmoi dry-run/apply, and configured runtime smokes |

The context README remains authoritative for ticket behavior and historical cycle
overrides. New cycles use this file as their Engineering Profile.

## Python policy-boundary slice

The approved [policy-boundary feature](features/python-policy-boundaries.md) is
elevated risk because it reorganizes private-data validation without changing its
accepted inputs, errors, serialization, or authority. Python and Security modules
apply. Keep the standalone standard-library-only `pmctl` layout; no companion
runtime module, schema migration, external operation, or runtime-floor increase.
Existing [Product Intent](PRODUCT.md) remains authoritative and unchanged.

### Selected typing and property authorities

Implementation selects `ty==0.0.95` and `hypothesis==6.170.14` in the existing root
`test` dependency group, with `uv.lock` as the resolved environment authority.
These are test/checker dependencies only. No dependency or environment is changed
by this Discovery specification. ty is a pinned beta checker; upgrades require
a new diagnostic/compatibility census rather than assuming stable diagnostics.

The affected Python population is the complete extensionless
`dot_local/bin/executable_pmctl`, `tests/test_pm_kernel.py`, proposed
`tests/test_pm_kernel_policies.py`, and every additional changed Python fixture
or helper. Establish that independent inventory before implementation and expand
it with new files. No other context or repository-wide analysis is claimed.
All selected files reach analysis; annotation precision, dynamic loader behavior,
unknown types and suppressions are reported separately from file coverage.

In the root uv environment, the planned authoritative typing command is:

```sh
uv run --locked --group test ty check --python .venv --python-version 3.12 --error-on-warning dot_local/bin/executable_pmctl tests/test_pm_kernel.py tests/test_pm_kernel_policies.py
```

Pass any additional affected Python path explicitly. Explicit selection includes
the extensionless executable; checking only its dynamic import tests is
insufficient. The selected rule policy is documented defaults with warnings
treated as failure and the Python 3.12 target explicitly supplied. The CLI can
merge project/user configuration: before qualification, record effective project,
ancestor, user and environment configuration inputs, including `TY_CONFIG_FILE`.
Undeclared rule overrides or exclusions block setup acceptance; do not edit
global user configuration or claim that CLI flags isolate it. Resolve execution
in an explicitly qualified environment and retain its effective rule census
privately.
No invented strict mode, blanket exclusions, unchecked casts, broad `Any`, or
diagnostic disabling may manufacture acceptance. Setup may establish a complete
conflict census with failures; required typing evidence must subsequently pass
or retain an explicit lifecycle exception. Invalid configuration, missing inputs,
incomplete analysis, and checker internal errors remain gaps or failures.

The planned affected behavior command is:

```sh
uv run --locked --group test pytest tests/test_pm_kernel.py tests/test_pm_kernel_policies.py -q
```

New properties use explicit per-property settings: `max_examples=100`,
`derandomize=True`, `database=None`, `deadline=None`, `print_blob=True`, and
`suppress_health_check=()`. Use bounded strategies. Existing CI supplies a
90-minute overall job timeout; the bare pytest command supplies none locally.
Local qualification must supervise the selected command with a hard 5,400-second
limit, terminate/reap its process group on timeout, and record the actual launcher
and bound in evidence. This requires no new tracked runner or dependency.
Example count is not a bound on shrinking, total calls, or wall time. Retain
minimized synthetic counterexamples as explicit examples and
record the exact Python/Hypothesis versions for replay. Do not change unrelated
tests through a global profile. Property acceptance and runtime example tests
remain separate from typing acceptance.

The root Python `>=3.12` support and existing CI remain unchanged: PR checks use
3.14; weekly/manual compatibility includes 3.12, 3.13, and 3.14. Type-model target
evidence is not execution on each interpreter/platform. Qualification uses the
root environment only; optional Dagger, model and other runtime environments
are outside this slice. Private check evidence stays in existing lifecycle
evidence; public specifications contain only synthetic examples and summaries.

### Delivery applicability

Kernel, Review/Integrate and Maintain/Retire gates are required. Release, Deploy
and Operate are not applicable to the source-only draft PR: it publishes no
independent artifact, installs no command/configuration, and activates no live
PM, Jira or database workflow. Managed installation and any operational proof
require a later explicit scope and their existing gates. Discovery's manifest,
publication and launch checks do not pass implementation gates.
