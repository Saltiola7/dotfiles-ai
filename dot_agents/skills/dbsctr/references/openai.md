# GPT-5.6 Execution

- State each instruction once and require observable outcomes and evidence.
- Delegate only cleanly independent work whose benefit exceeds orchestration cost.
- Use `reviewer-openai` only for explicit review or critical work with a bounded
  evidence brief; routine work uses normal integration evidence.
- Retry a failed optimized route once on the OpenAI flagship. Never cross provider
  families automatically.

Authority: <https://developers.openai.com/api/docs/guides/latest-model>
