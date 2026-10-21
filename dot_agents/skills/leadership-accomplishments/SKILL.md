---
name: leadership-accomplishments
description: Draft management accomplishment bullets from GitHub, Jira, and Confluence, then interview for business rationale, adoption, and missing nuance. Use for weekly leadership wins and capability reporting, rather than ticket inventories or sprint dashboards.
---

# Leadership Accomplishments

Produce a small set of management-ready bullets explaining why work mattered, what meaningfully changed, and what value was enabled or demonstrated. Research before interviewing; use the interview to resolve missing business context rather than asking the user to repeat accessible records.

## What qualifies

An accomplishment is a meaningful result achieved during the reporting period that creates durable business value, enables an important business capability, reduces material risk, or demonstrates a measurable win.

A completed intermediate milestone can qualify when it enables a concrete next step, resolves consequential uncertainty, or removes a meaningful blocker. A validated finding, consequential design decision, adopted process, or completed system scaffold may qualify without production adoption. State its actual maturity.

Group related features into business capabilities. Meetings, ticket closures, pull-request counts, research activity, and maintenance are evidence of activity, not accomplishments by themselves. Identify their result and significance. High development velocity is not a reason to report more bullets.

## Establish scope and retrieve evidence

Reuse audience, team, cadence, sources, and preferences already established. Read a team profile when the user supplies its path or a previous report identifies it. Otherwise, look for a matching profile in `${XDG_CONFIG_HOME:-$HOME/.config}/leadership-accomplishments/profiles/`; inspect filenames first and read only the profile relevant to the requested team. If the match is ambiguous, ask which profile to use. If none exists, establish the missing context through the available sources and a focused interview.

Team profiles are private inputs, separate from this portable skill. Keep employer identities, account details, internal links, stakeholder notes, and historical business examples outside public source and the installed skill bundle. A local profile directory should be accessible only to its owner (`0700`), with profile files readable and writable only by that owner (`0600`). Preserve the user's existing profile and sharing boundaries; do not publish or synchronize it with the skill. Local file permissions do not prevent the selected report agent or model from reading a profile when it is used.

Resolve the reporting interval from the previous report's cutoff through the current evidence cutoff, using the user's timezone. A weekly Friday report does not imply a calendar-week window or permission to schedule an automation. Read the previous report when available to avoid repeating the same achievement. If unavailable, ask once; if drafting continues, disclose the deduplication limitation without inventing a baseline. Include only the new material advance of an ongoing initiative.

Retrieve relevant evidence from all three available sources:

- **Confluence:** previous weekly report, sprint review, strategy/initiative context, accomplishment notes, and relevant stakeholder decisions. Personal/private notes may inform drafting, but do not expose private details or change sharing. Prefer audience-accessible supporting links in the final report.
- **Jira:** completed work, parent initiatives, acceptance results, and relevant comments. Include the team's work, not only the requester's tickets, when the report is team-wide. Sprint membership or Closed status alone does not establish when delivery occurred or its business impact.
- **GitHub:** relevant repositories, merged PRs, delivery records, specifications, and operational evidence. GitHub connectors, authenticated gh CLI, or local Git history are appropriate. Follow repository instructions for local reads. Review enough detail to distinguish scaffold, tests, merged implementation, deployment, and actual use.

Use targeted searches and linked evidence; expand when a material claim needs verification. Follow current tool discovery and pagination contracts rather than hardcoding connector schemas. If a source is inaccessible, name the gap and use available evidence; never imply it was reviewed.

Maintain a compact working record per candidate: reporting-period change, original problem/goal, beneficiary, delivered result, maturity/adoption, demonstrated versus expected value, evidence/date, prior-report overlap, and unresolved questions. Keep this working detail out of the leadership bullets.

## Interview for meaning

After research, summarize the strongest candidate accomplishments and ask a few focused questions whose answers can change selection or wording. Reuse prior answers. Relevant questions include:

- Why was this worth doing? What business problem or constraint prompted it?
- What can the team or business now do that it could not do before?
- Who actually uses it, and who benefits? Are those different groups?
- What milestone was completed, and what testing, adoption, or implementation remains?
- What decision, commitment, prioritized work, or changed practice resulted?
- Is the claimed revenue, savings, time reduction, adoption, or risk reduction measured? What evidence supports it?
- What changed since the last report, rather than earlier in the initiative?

Do not ask every question for every candidate. Ask when the why is unknown rather than substituting generic benefits such as efficiency or scalability. Label an inferred rationale as tentative until supported or confirmed. User-confirmed business intent is valid context; do not present it as independently measured impact.

For a request to interview until “95% confidence,” use a qualitative stopping condition: no unresolved question would materially change which accomplishments qualify, their rationale, scope, attribution, or maturity. Do not fabricate confidence percentages. Drop weak candidates rather than prolonging an interview to fill a quota.

## Select and write

Rank by durable value, capability, consequential learning/decisions, material risk reduction, revenue generation, and measurable business results. Keep security/vulnerability accomplishments separate when the report has that section. Routine engineering detail belongs in source links, not executive prose.

Write normal professional prose in the report, even if conversation uses compressed language. Prefer roughly 3–7 bullets when warranted; fewer strong bullets are better than filler. Follow the user's existing format when supplied.

Each bullet should connect the business reason with the concrete result and its significance, typically in one or two sentences:

> Completed [meaningful result] to address [business need], enabling [specific capability or demonstrated outcome].

Vary wording naturally. Preserve material boundaries inside the claim: “ready for internal testing,” “added prioritized remediation targets,” or “canceled unused subscription.” Do not append long technical caveat lists that overwhelm the result.

Do not equate:

- system scaffolding with a validated model, adoption, or realized savings;
- a visibility audit/backlog with deployed rendering fixes or recovered traffic;
- a decision to pursue agent-operated workflows with implementation of those workflows;
- source dependency fixes with verified deployment or closure of all vulnerabilities;
- subscription cancellation with reconciled invoices or quantified savings.

Use concise source links when appropriate. Deduplicate across Jira, GitHub, and Confluence; these often describe the same result. Do not double-count overlapping metrics or use implementation counts as a proxy for value.

Before delivery, check each bullet for reporting-period eligibility, supported rationale, business relevance, accurate attribution, and truthful maturity. Deliver the requested bullets in chat by default. Creating/updating a report elsewhere, sending it, altering source records, or scheduling recurring runs requires authorization for that action; existing authorization need not be requested again.
