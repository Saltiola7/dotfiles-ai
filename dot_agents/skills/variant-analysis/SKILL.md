---
name: variant-analysis
description: Hunts for the other instances of a bug already found — the variants of one root cause across a codebase. Use immediately after a vulnerability, logic bug, or bad pattern turns up in a specific file and the question becomes where else it occurs, including the bare conversational form ("are there others like this?", "is this the same bug?"). Also for generalizing one known instance into a CodeQL or Semgrep query for its whole pattern family, and for triaging a set of look-alike candidates against a known root cause. Not for initial discovery with no bug in hand.
---

<!-- Adapted by dotfiles-ai, 2026-10-28; see UPSTREAM.md and security-toolkit provenance. -->
# Variant Analysis

Find the other instances of a bug you have already found. One root cause usually has several
manifestations, and they are rarely in the module where you found the first one.

## When to Use

- A vulnerability has been found and you need to search for similar instances
- Building or refining CodeQL/Semgrep queries for security patterns
- Performing systematic code audits after an initial issue discovery
- Analyzing how a single root cause manifests in different code paths

## When NOT to Use

- Initial vulnerability discovery — use the selected primary security workflow
- General code review with no known pattern to search for
- Writing fix recommendations — use the selected primary reporting workflow
- Understanding unfamiliar code — build bounded source context first

## The Five Steps

Read the reference for a step when you reach it.

**1. Understand the original issue.** Extract the root cause — why the code is wrong, not
what it does — and enumerate the directions a variant could hide in: related identifiers,
other manifestations of the same mistake, data-type edge cases.
→ [references/root-cause.md](references/root-cause.md)

**2. Create an exact match.** Write a pattern matching ONLY the known instance and confirm
it hits. A pattern that matches nothing means you have misunderstood the bug, and every
search built on it is calibrated against the wrong code.

**3–4. Generalize one element at a time.** Climb from the exact match toward the pattern
family, running and reading all matches after each single change. Stop when more than half
the matches are noise.
→ [references/searching.md](references/searching.md) — abstraction ladder, tool selection,
false-positive filters

**5. Triage.** Confirm actual boundary violations under the primary evidence policy.
Assign severity only to confirmed findings; unresolved candidates have no severity.
→ [references/triage.md](references/triage.md)

**Then write it up**, including the patterns that failed and a CI rule to prevent regression.
→ [references/reporting.md](references/reporting.md)

## Portable workflow

Use the five steps directly within the approved target and scope. The upstream
plugin slash command and named agents are not part of this portable bundle.
Delegate bounded searches through native tools only when available and authorized.
Use existing approved tools; this skill does not install scanners, fetch rules,
or authorize target-code execution. Keep incomplete traces as needs-validation;
only confirmed boundary violations receive severity under the primary workflow.

## What Makes Hunts Fail

1. **Narrow scope** — searching only the module the original bug was in
2. **Pattern too specific** — searching one attribute and missing the family around it
3. **One vulnerability class** — chasing a single manifestation of the root cause
4. **Happy-path testing** — never trying the null, empty, and boundary cases
5. **Generalizing too fast** — abstracting several elements at once, so noise cannot be
   attributed to any one of them

The first three are covered in root-cause.md and searching.md, the fourth in triage.md.

## Resources

Scanner query templates are intentionally not bundled. Write and validate any
new rule against positive and negative fixtures before proposing CI use; missing
CodeQL packs, build requirements, or private-code license eligibility are gaps.

**Report**: `resources/variant-report-template.md`
