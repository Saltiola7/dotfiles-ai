# Jira Completion Contract

Produce one Jira-ready status comment. Claims must trace to inspected evidence.

## Evidence Check

- Planned scope and acceptance criteria
- Implementation and material deviations
- Validation commands and outcomes
- Review or approval state when required
- Deployment state and target when applicable
- Rollback or recovery evidence when applicable
- Stakeholder acceptance when required
- Remaining blockers, risks, and follow-up work

Absence is not failure, but it is not success. Mark unavailable or inapplicable
items explicitly rather than filling gaps from expectation.

## Comment Shape

```markdown
## Status
<Completed | Not ready for closure>

## Delivered
- <verified outcome and evidence>

## Validation
- <verified check and result, or missing evidence>

## Deviations And Risks
- <difference, risk, rollback/recovery state, or none evidenced>

## Blockers And Follow-up
- <closure blocker or follow-up>
```

Use `Not ready for closure` whenever material validation, review, deployment,
rollback, acceptance, deviation, or follow-up evidence remains missing or
conflicting. Do not close, transition, or comment on the Jira item.
