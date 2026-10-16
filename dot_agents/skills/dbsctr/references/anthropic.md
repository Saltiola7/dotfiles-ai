# Vertex Claude Opus 5.5 Execution

- Rely on native self-correction; do not request generic final verification,
  repeated double-checking, or a subagent used only to verify the primary.
- Delegate only genuinely independent, parallelizable work and keep fanout small.
- Integrate delegated output through executable evidence without adding a human or
  reviewer requirement.
- Keep helpers on configured Vertex Sonnet 5.5. Report an unavailable route;
  the primary may handle the work directly, without automatic helper model or
  provider substitution. Never cross provider families.

- Existing Opus 5 prompts remain a starting point; calibrate effort only against
  authorized workload evaluations and actual harness support. Do not switch global
  settings based on upstream comparisons. Report progress, but progress is not completion;
  preserve risky-action confirmation, required gates and exact approval.

Authority (verified 2026-10-16): <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5>
