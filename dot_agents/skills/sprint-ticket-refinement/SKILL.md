---
name: sprint-ticket-refinement
description: Refine all-status Jira sprint tickets using GitHub evidence, focused interviews, and jira-ticket templates, then publish approved edits. Use for current-sprint or retrospective refinement, and the Needs Refinement sprint when requested.
---

# Sprint Ticket Refinement

Turn sprint tickets into accurate, useful records of intent, business value, scope, acceptance, and delivered work. Support both forward-looking refinement and retrospective refinement near sprint end. Research first, interview for missing meaning, present concrete drafts, then publish only after approval.

## Dependency and scope

Load the available `jira-ticket` skill and its issue-type reference. For retrospective work also read its completion reference. Discover its location from the skill catalog; do not hardcode a user's home directory. If unavailable, search installed skill locations; if still missing, explain the dependency and stop template drafting rather than inventing its contracts.

Use jira-ticket for framing, type selection, templates, and evidence discipline. This workflow expressly supports authorized Jira sprint searches and post-review publishing through available Jira connectors or authenticated CLIs. Its publishing stage is an intentional exception to jira-ticket's draft-only/no-mutation guidance, activated only by the user's approval of concrete edits. Do not change the dependency skill itself. Use completion guidance to assess delivered work inside the description; do not post status comments or transition tickets.

The workflow is universal: do not assume a particular organization, project, person, repository, account ID, or sprint number.

## Resolve selection

Reuse scope already established in the conversation. Otherwise resolve:

- **Project and board:** use supplied context or discover accessible candidates. Ask when more than one is plausible.
- **Sprint:** default to the current active sprint on that board. Use authoritative sprint metadata, not the largest ID, newest creation date, or issue rows. If multiple sprints are active, ask which one. If none is active, present relevant recent/upcoming choices instead of silently selecting one. An explicitly named historical sprint is valid for retrospective work.
- **Needs Refinement:** include the sprint with this exact name only when requested. Resolve it on the selected board, including inactive/future states; ask if ambiguous. Clarify whether the request replaces or adds to current-sprint scope when wording does not establish that. Do not infer a status or label with this name is the sprint.
- **Whose tickets:** when unspecified, ask whether to select the user's own tickets, named individuals, or the whole team. “My tickets” means the authenticated Jira user/current user, never a saved author's identity. Resolve names unambiguously. Whole-team scope includes unassigned tickets unless excluded. Explain if the connected identity is unavailable or inconsistent with the request.
- **Repositories:** use linked development evidence and project context to identify relevant GitHub repositories. Ask if their identity or coverage is unclear. Never assume the repositories used in a previous unrelated project apply.

Show the resolved sprint name, dates/state, ownership selection, and ticket count. Include **all statuses**, including closed/completed carryovers. Fetch every page of the scoped result; deduplicate tickets if multiple selected sprints overlap. Do not expand ownership or add tickets outside the agreed selection without direction. Respect explicit exclusions and requests to leave particular tickets unchanged.

## Retrieve and reconcile

Read current titles, descriptions, types, statuses, assignees, relevant comments, parent context, and linked work. Inspect GitHub history, PRs, delivery records, tests, release/deployment evidence, and relevant specifications using available connectors, authenticated gh CLI, or local Git. Follow repository instructions for local reads. Use Confluence context when linked or when needed to resolve business rationale or stakeholder decisions.

Use older history to establish the baseline and follow-up relationship. Attribute sprint delivery only to the supported period; do not silently backdate later changes. A ticket's sprint membership, closure date, and a PR's merge date describe different events. Check actual delivery evidence when those disagree.

Map each material change to the best-fitting ticket. Do not count the same work twice across specific tickets and general rollups. Miscellaneous work may fit an existing Platform Updates or equivalent ticket when its scope supports that; do not invent a rollup, widen an unrelated ticket, or create tickets automatically.

For each candidate, retain a compact working record of intended outcome, why it matters, baseline, actual delivered changes, validation/maturity, remaining work, sources, conflicts, and open questions. Distinguish merged software, deployment, user adoption, and measured business results. GitHub cannot establish private stakeholder acceptance or meetings that are not recorded. Missing evidence is not proof of success or failure.

Preserve useful technical history and original intent. Explain material deviations instead of rewriting the plan as if the final result had always been intended. When a closed ticket lacks completion evidence, identify that gap in the proposed record without changing its status. When a follow-up ticket continues earlier work, separate inherited capabilities from this sprint's intended or actual increment.

## Interview

Research before asking users to supply information already accessible. Ask a small number of focused questions, grouped by related work, that can change the ticket boundary, rationale, type, acceptance criteria, completion claims, or attribution.

Typical uncertainties:

- What problem or decision prompted this work, and who benefits?
- What is new in this sprint versus the previous delivery?
- Is this an investigation, bounded task, bug, or stakeholder outcome?
- What was actually delivered, validated, deployed, or accepted?
- What counts as completion, and what remains future work?
- What important collaboration, business nuance, or non-code work is absent from the repositories?

Challenge consequential ambiguity with a concrete recommendation. Do not assume the interviewer can attest to every teammate's acceptance or outcomes; retain unknowns where needed. Reuse answers and do not interview merely to fill fields. Do not require timeboxes or story points; preserve supplied values and treat estimation as a separate request.

For “95% confidence,” stop when no unresolved answer would materially change the proposed edits. Do not fabricate a percentage. Clearly evidenced tickets can be drafted while other material questions remain, but unresolved claims must not be presented as verified.

## Draft for review

Select the smallest appropriate type using jira-ticket's contracts and available project types. Recommend a title that captures the complete bounded work and a description using the matching template. Preserve project-required structure and meaningful links, tables, attachments, and embedded media.

For retrospective tickets, combine appropriate context/scope with delivered outcomes, validation, deviations, and follow-up evidence. Keep business value and technical history together without turning the description into a commit dump. Include enough source references to support consequential claims.

Present reviewable per-ticket proposed titles, types, and full descriptions, or a linked artifact containing them. Summarize material changes and explicitly identify unchanged or blocked tickets. Do not apply edits at this stage. Ask for approval of this concrete set; approval may cover all or a named subset. Approval of this skill's creation is not approval to update future Jira tickets.

Allowed publication fields are **summary/title, description, and explicitly approved issue type only**. Keep status, assignee, sprint, estimates/points, issue links, labels, and other fields unchanged unless separately requested. Type changes that require wider Jira migrations are outside this default operation; explain the limitation instead of broadening the mutation.

## Publish and verify

After approval, apply only approved tickets and fields without asking again for the same approval. Re-read affected fields first to detect concurrent edits; preserve unrelated changes. If concurrent changes materially invalidate the approved draft, reconcile and return the changed proposal for review.

Use a representation that preserves existing rich content and media. Never replace a rich description with a lossy version merely for convenience. If faithful preservation is unavailable, explain the affected ticket and leave it unchanged while continuing independent approved edits.

Read back updated fields and verify they match the approved content, accounting for harmless formatting normalization. Verify status, assignee, and sprint stayed unchanged. Report successes, failures, and skipped tickets accurately. On uncertain write outcomes, read before retrying. If a repair requires different content, wider fields, or unsupported migration, stop that ticket and present the concrete issue rather than repeating blind writes.

Finish with a concise summary and Jira links. Do not claim successful publication based solely on preparing an artifact.
