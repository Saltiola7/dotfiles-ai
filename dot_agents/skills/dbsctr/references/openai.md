# OpenAI GPT-6.1 Execution

- State each instruction once and require observable outcomes and evidence.
- Delegate only cleanly independent work whose benefit exceeds orchestration cost.
- Use `reviewer-openai` only for explicit review or critical work with a bounded
  evidence brief; routine work uses normal integration evidence.
- Keep configured helper models when the primary changes to another OpenAI
  model. Report an unavailable route; the primary may handle the work directly,
   without automatic helper model or provider substitution.

- GPT-6 Astra prompting observations are hypotheses for GPT-6.1 Sol; evaluate
  workload-specific deltas rather than copying a provider prompt wholesale.
- GPT-6.1 Sol tool calling requires Responses; `none`/`minimal` reasoning is
  unsupported. Public API guidance does not qualify the configured harness or
  authorize a model, effort or route change. Preserve native gates and exact approval.

Authority (verified 2026-10-16): <https://developers.openai.com/api/docs/guides/model-guidance>
