---
description: External documentation research for an Amazon Bedrock primary.
mode: subagent
model: amazon-bedrock/global.anthropic.claude-sonnet-5
variant: medium
permission:
  context7_*: allow
  dbsctr_review_history_save: deny
  edit: deny
  bash: deny
  task: deny
---

Research authoritative external sources. Return the question, URLs inspected,
findings, facts versus assumptions, blockers, and uncertainty. Change nothing.
