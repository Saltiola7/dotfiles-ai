---
name: chezmoi-operations
description: Manage chezmoi source and destination state, templates, conflicts and scoped applies. Use for actual chezmoi changes or diagnosis; preserve the repository's deployment owner.
---

# Chezmoi Operations

Use the project's existing source, configuration and deployment runbook. This
method supplies chezmoi semantics; it does not replace repository policy or grant
authority to install tools, synchronize Git or apply additional targets.

## Establish the state and requested effect

- Identify the installed version, selected configuration, source directory,
  destination directory and exact requested targets. Use local command help for
  version-sensitive flags; do not assume default paths or change the setup.
- Distinguish edits to managed source from edits to deployed files. Inspect both
  when drift or conflicts matter, preserving unrelated live changes and recoverable
  preimages before a write. Do not import the whole home directory to resolve one
  target's divergence.
- Check applicable source naming, template data, ignore/removal rules and file
  types. Rendering a file correctly on one host does not qualify other platform
  branches, secret-dependent content or script effects.

## Preview and apply within scope

- Preview the selected targets and account for template evaluation, hooks, managed
  scripts and external content. Dry-run is not an effects sandbox. Read
  [state and effects](references/state-and-effects.md) when preview guarantees,
  external refresh, scripts, conflicts or recovery affect the decision.
- Keep secret values out of previews and transcripts. Inspect relevant non-secret
  configuration or status rather than dumping all configuration, data or rendered
  encrypted content. Report any resulting verification gap.
- Use the narrowest target selection for the authorized change. Resolve a conflict
  deliberately; do not add unconditional force or refresh flags, run a broad
  update, or discard destination edits to avoid a prompt.
- Applying reviewed guidance does not authorize its scripts, package installation,
  remote publication or host changes outside the actual task. Reuse existing
  authorization when those effects are already part of the requested work.

## Verify the result

Check the selected destination bytes, modes and file types against the reviewed
target state. Inspect a fresh scoped diff or verify result; a successful diff
command with visible changes does not establish equality. For repeatability work,
check the second application and its remaining diff. Report actual scope, effects,
conflicts, skipped content and unavailable checks to the existing primary and QA.
