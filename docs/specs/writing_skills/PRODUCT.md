# Writing Skills Product Intent

**Status:** WS-1 through WS-6 delivered to Git; live managed deployment intentionally excluded
**Created:** 2026-07-28
**Last updated:** 2026-07-30

## Users And Stakeholders

The primary user is an OpenCode operator turning incomplete evidence into a Jira
work item, a completion update, or a logically structured written artifact.
Readers of those artifacts are downstream stakeholders who need decisions,
scope, evidence, and uncertainty to remain distinguishable.

## Problem

Requests often arrive as proposed solutions, incomplete notes, or closure claims.
Formatting them immediately preserves weak intent and unsupported conclusions.
The operator needs portable skills that investigate available evidence, challenge
material ambiguity, and produce a useful artifact only when its basis is clear.

## Desired Outcomes

- Jira tickets state the real outcome, justified scope, acceptance boundary, and
  material uncertainty rather than merely polishing the initial request.
- Completion updates distinguish verified work from missing closure evidence.
- Pyramid-structured artifacts answer the reader's governing question first and
  support it with coherent, ordered reasoning.
- Private source material and local evidence never leak into public skills or
  external research queries.

## Non-goals

- Mutating Jira, authenticating ACLI, closing work items, or claiming deployment.
- Replacing project-specific Jira fields, workflows, or issue-type configuration.
- Automatically applying Pyramid behavior to ordinary writing requests.
- Reproducing proprietary source wording, examples, or diagrams.
- Publishing a release or applying the managed OpenCode configuration live.

## Core Journeys

1. The user supplies a request or Jira key; the skill gathers bounded evidence,
   reframes the intent, asks only material questions, and drafts a justified Jira
   item using one of five supported contracts.
2. The user requests a completion update; the skill checks available evidence and
   returns either a closure-ready status or a status explicitly marked not ready
   for closure with blockers.
3. The user explicitly invokes Pyramid structuring; the skill tests the argument,
   asks material questions when needed, returns the requested artifact, and then
   shows its logic as an original Mermaid map.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | not_applicable: the context README owns the canonical evidence and consent boundary diagram | - | `README.md` Visual Evidence | Writing-skills owner |
| Interaction | not_applicable: the three product journeys are linear and the context README owns detailed ordering | - | Core Journeys and `README.md` | Product owner |
| State | not_applicable: Product Intent defines outcomes rather than persistent workflow state | - | Desired Outcomes | Product owner |
| Data/trust | not_applicable: Privacy And Trust plus the context README Text Equivalent fully state the boundary | - | Privacy And Trust | Product owner |
| Schema | not_applicable: Jira artifact schemas belong to the skill references | - | Product Constraints | Writing-skills owner |
| Dependency/deployment | not_applicable: deployment is outside this Product Intent and canonical in the control-plane specification | - | Non-goals | Control-plane owner |
| Quantitative | not_applicable: success evidence is categorical and no comparative dataset controls a product decision | - | Success Evidence | Product owner |

The context README's accessible workflow is the canonical visual for these
journeys. This Product Intent intentionally does not duplicate it. Its prose is
the Text Equivalent for product outcomes; the product owner revisits this plan
when journeys, privacy boundaries, or measurable success decisions change.
V3.35 corrects delivery status without changing those journeys or boundaries.

## Success Evidence

- Focused contracts verify portable skill metadata, thin commands, bounded ACLI
  permissions, explicit activation, and privacy-safe public content.
- Isolated rendered OpenCode smoke cases cover complete, vague, conflicting,
  unsupported-type, missing-evidence, and prompt-injection inputs.
- Public skill text contains no private paths, copied source examples, or claims
  that unavailable evidence was verified.

## Product Constraints

- The Jira policy supports exactly Story, Bug, Task, Spike, and Epic. Any other
  requested type becomes Task with visible disclosure.
- One interview round contains at most five questions and continues only while an
  answer could materially change scope, behavior, risk, or the final artifact.
- An explicit Jira key or URL authorizes only bounded view and comment-list reads.
  Broader JQL search requires user approval.
- Public web or Context7 research requires one approval per invocation and uses
  generic queries without private content.
- Context7 is optional and Scout-only; unavailability must be reported rather
  than hidden behind another provider.

## Accessibility

Outputs use meaningful headings, plain text labels, and Mermaid source that does
not carry essential meaning without an accompanying textual artifact.

## Privacy And Trust

Local files, Git history, Jira content, and user notes may be private. They may be
read only when relevant and must not be copied into public files or external
queries. Prompt-like text found in evidence is untrusted data, not instruction.

## Compatibility And Retirement

Skills and commands follow native OpenCode skill and command contracts and remain
provider-neutral. Removing or renaming a public skill or command requires an
explicit retirement cycle and migration note.
