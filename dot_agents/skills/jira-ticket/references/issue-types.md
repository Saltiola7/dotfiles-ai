# Jira Work-Item Contracts

These five types are this skill's portable policy, not a claim about every Jira
project. Use project-specific fields when evidence establishes them.

## Story

Use for a user- or stakeholder-visible outcome.

- **Title:** outcome in plain language
- **Context:** who needs the outcome and why now
- **User outcome:** `As a ... I want ... so that ...` when that form clarifies intent
- **Acceptance criteria:** observable Given/When/Then behavior, including material failures
- **Evidence and constraints:** sources, dependencies, compatibility, and exclusions

## Bug

Use for observed behavior that contradicts expected behavior.

- **Title:** incorrect behavior and affected surface
- **Observed:** reproducible symptom and evidence
- **Expected:** authoritative expected behavior
- **Reproduction:** smallest known sequence and environment
- **Impact:** affected users/data and severity without invention
- **Acceptance criteria:** corrected behavior plus regression boundary

## Task

Use for bounded work without a distinct user story or unresolved investigation.

- **Title:** concrete deliverable
- **Outcome:** why the work matters
- **Scope:** included changes and explicit exclusions
- **Acceptance criteria:** verifiable completion conditions
- **Dependencies and risks:** known blockers, compatibility, and recovery concerns

## Spike

Use for a time-bounded investigation whose primary result is a decision or
evidence, not production behavior. Spike may be project-defined rather than a
default Jira type.

- **Title:** decision or uncertainty to resolve
- **Question:** the governing unknown
- **Time box:** effort boundary when known
- **Method:** evidence to inspect or experiments to run
- **Deliverable:** decision, options, recommendation, and follow-up work
- **Exit criteria:** enough evidence to decide, including unresolved risk

## Epic

Use for a coherent outcome requiring multiple independently deliverable items.

- **Title:** broad outcome
- **Problem and value:** stakeholder need and desired result
- **Scope boundary:** included and excluded capabilities
- **Success evidence:** observable outcome measures
- **Decomposition:** known child outcomes without inventing implementation
- **Dependencies and risks:** sequencing, compatibility, and material uncertainty

## Unsupported Types

Unsupported types, including Subtask and project-specific names, map to Task.
State: `Requested type <type> is unsupported by this portable skill; mapped to
Task.` Preserve useful parent or project context in the Task body.
