# Skill activation

- Automatically use `caveman-commit` when preparing a commit message.
- For other skills, suggest activation when it would materially help and wait
  for the operator's decision. Task relevance alone is not approval.
- An explicit request to use a skill, including its slash command, activates it
  for the conversation. Reuse loaded guidance rather than reloading it unchanged.
- When DBSCTR is active, its router may activate its dependencies and applicable
  specialists without separate approval for each skill.
- If a suggestion is declined, continue normally and do not repeat it unless
  circumstances materially change.
