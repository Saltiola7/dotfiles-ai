---
name: new-modular-project
description: Set up an explicitly requested Mojo project or selected Modular development environment while preserving the chosen SDK channel, version pins and environment manager. Use for setup decisions and manifests, not ordinary source edits or automatic MAX model workflows.
---

# Set up a Mojo project

Confirm the requested project scope and existing choices before creating files or
resolving packages. Read project instructions, manifests, locks, CI and compatible
nearby projects. Preserve selected environment manager, Python runtime where
applicable, SDK version/channel, package constraints and target architecture.

Infer settled choices from that evidence. Ask only for missing choices that
materially change setup or compatibility, using the available conversation/UI;
no particular interactive tool is required. A default channel or manager in an
upstream recipe does not override a project choice.

## Bounded setup

1. Identify project path, Mojo purpose, platform, CPU/GPU targets, SDK/channel,
   manager and Python interop needs. Existing manifests/locks take precedence.
2. Check selected-version primary installation/support documentation and available
   local tools. Diagnose missing compiler/linker/runtime prerequisites without
   automatically installing system packages, SDKs, managers or drivers.
3. Read [setup choices](references/setup-choices.md) for the selected manager only.
   Choose the smallest supported dependency set. A Mojo project does not imply MAX
   packages, optional extras or model-lifecycle skills.
4. Within current authorization, create or adjust the project-local manifest,
   compatible constraints/lock and minimal source/test task. Keep selected pins;
   record any requested pin/channel change separately and verify compatibility.
5. Use the chosen environment's project commands for version/build/test evidence.
   Inspect whether an environment wrapper resolves or installs dependencies before
   running it. Report missing capability rather than installing tools implicitly.

Do not fetch and execute shell installers, change global shell configuration,
activate a different manager, remove locks or drop pins to follow an example.
Installation or host changes require their own actual task authorization; merely
loading this skill supplies none. Retain existing credentials and provider settings.

## Verify and hand back

Use [Mojo syntax](../mojo-syntax/SKILL.md) for generated source. Add
[Python interop](../mojo-python-interop/SKILL.md) or
[GPU fundamentals](../mojo-gpu-fundamentals/SKILL.md) only for actual boundaries.
Validate the selected compiler version and applicable build/test/import behavior
in the existing authorized environment. GPU support requires real selected-target
evidence; a manifest, package resolution or CPU build does not establish it.

Return selected manager, SDK/channel/constraints, files and commands, actual
results and missing prerequisites. No compilation, installation or target-support
claim follows from a recipe alone. The existing primary and QA own lifecycle,
acceptance and any later deployment.

Provenance and exact license terms: [UPSTREAM.md](UPSTREAM.md).
