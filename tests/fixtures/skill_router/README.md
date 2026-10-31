# Native skill-router maintenance qualification

`tests/skill_router_eval.py` is an opt-in maintenance experiment, not a production
dispatcher. Normal pytest validates its contracts offline and never calls a model.
The native client selects skills from names/descriptions; DBSCTR modules provide
conditional task triggers. Selected entrypoints and resources remain lazy-loaded.
The Python module owns its single trigger/checkpoint table. Consult the common
selection reference only for an unresolved selection, discovery or handoff issue.

## Inputs and private evidence

`cases.json` contains synthetic task inputs. `oracle.json` holds expected selected
sets and decision checks outside the model fixture. `output.schema.json` is the
common answer contract. Do not put expected skill names or scores in model input.
The fixed original plan has 46 calls: eight diagnostic development calls,
32 held-out calls (eight tasks, two arms, two repetitions in balanced order),
four explicit DBSCTR navigation calls and two unregistered-sibling controls.
Explicit controls do not establish implicit selection accuracy.

Use an existing project-compatible Python interpreter. Prepare immutable baseline
and candidate snapshots outside public source; a baseline can use `prepare --ref`.
The CLI's `prepare --help` and `run-one --help` describe required arguments.
`run-one` requires `--allow-native`, an exact declared slot and an observed private
runtime identity containing client/model/provider labels plus SHA-256 bindings
for existing configuration and executable files. Do not copy credentials or
change the chosen model, provider, authentication, home or normal hooks to run it.

Each call performs a no-model native catalog preflight, checks exact physical
bundle revisions and invocation-only exclusions of replaced global copies, then
captures bounded native JSONL. Unregistered controls omit a registration symlink
while retaining its physical sibling; this does not simulate cache staleness.
Store prompts, raw events, configuration identities, snapshots and receipts in
private Cycle Record evidence. Never commit raw sessions or machine identities.

Inspect actual successful returned method content, not path mentions, metadata or
self-reported loading. This observes returned content, not OS file-access or
semantic compliance. Review task decisions independently. Keep failed, unavailable
and missing attempts in the denominator. A known native web-search duplicate-ID
shape retains both opaque IDs and a warning; other duplicate keys are rejected.
Record nonfatal hook diagnostics separately from failures. Do not rerun a model
silently to replace an instrumentation or selection failure.

## Initial observed comparison

All 46 native processes completed. The original baseline and frozen metadata/
deduplication candidate each selected required guidance in 16/16 held-out runs,
4/4 diagnostic development runs and 2/2 explicit navigation runs. Both failed
their one unregistered GPU-sibling control. Independent decision review found
41 passes and five partial results: three Helm answers omitted the explicit
local-render versus cluster-acceptance boundary, and both omission answers
overstated absence. No paired candidate-specific quality regression was found;
these absolute omissions remain visible.

| Original split | Runs per arm | Baseline input / cached input / output | Candidate input / cached input / output |
|---|---:|---:|---:|
| Diagnostic development | 4 | 352,076 / 247,424 / 3,239 | 400,856 / 302,336 / 3,544 |
| Implicit held-out | 16 | 1,278,021 / 963,968 / 12,174 | 1,356,103 / 1,042,048 / 12,396 |
| Explicit navigation | 2 | 300,885 / 260,736 / 2,196 | 264,196 / 214,144 / 1,978 |
| Unregistered sibling | 1 | 100,806 / 83,328 / 685 | 99,799 / 83,456 / 666 |

Native usage fields include cached input within input; do not add them or infer
billing. Held-out input increased 6.1%; the two navigation calls per arm used
12.2% less input. Small noisy samples and different task splits support no general
token-saving or automatic-trigger reliability claim. The two tuned descriptions
shrank from 1,495 to 348 characters; character reduction is not measured tokens.
The actual CLI catalog exposed their full original descriptions, so truncation
is not a demonstrated cause of misses. Some task families were familiar from
earlier planning checks; held-out wording/rubrics were withheld until freezing.

## Follow-up resolver repair

The omission failure motivated `dbsctr/scripts/resolve_specialist.py`: follow the
physical DBSCTR directory before selecting one exact permitted sibling and
verify its declared name. Invalid names refuse before lookup. No scan, download,
installation or policy override occurs; the caller must respect disablement.

The original comparison snapshots and failures stay unchanged. Freeze repaired
guidance separately and predeclare four targeted checks: two permitted recovery
cases, explicit project disablement and an incidental-language negative. These
post-failure checks are repair smoke, not fresh held-out evidence or repetitions
of the original comparison. Report their outcomes separately and retain all
50 calls. Deployment still requires complete source/provenance/distribution
checks, exact-target application and installed-byte/file-set verification.

The four declared repair calls all completed and passed independent decision and
read-proof review. Both positive cases recovered the physical GPU sibling and
read its method; neither negative looked up or read GPU guidance. Repair-only
usage was 682,972 input, 594,944 cached input and 3,539 output tokens. Its ambient
catalog differed from the first comparison, so these counts remain separate and
support no comparative saving claim. Original 46 captures remain unchanged.
