# OpenAI GPT-6.1 Execution

- State each instruction once and require observable outcomes and evidence.
- Delegate only cleanly independent work whose benefit exceeds orchestration cost.
- Use `reviewer-openai` only for explicit review or critical work with a bounded
  evidence brief; routine work uses normal integration evidence.
- Keep configured helper models when the primary changes to another OpenAI
  model. Report an unavailable route; the primary may handle the work directly,
  without automatic helper model or provider substitution.

Authority: <https://developers.openai.com/api/docs/guides/latest-model>
