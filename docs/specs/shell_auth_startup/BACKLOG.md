# Shell Auth Startup Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| AUTH-011 | Keep blocked Herdr LaunchAgent handoff retryable | P1 | active | AUTH-008 | loader, owner wrapper, shell auth spec, regression test | Herdr runtime contract | no | One deployment path and one runtime owner | S | focused pytest, rendered shell syntax, managed runtime smoke test |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| AUTH-009 | Support Keychain token loading with shell `noclobber` enabled | 2026-07-15 | `0d0be5f` |
| AUTH-008 | Run persistent Herdr server in the Aqua security context | 2026-07-13 | `ea9eaeb` |
| AUTH-007 | Preserve safe Keychain failure diagnostics and repair guidance | 2026-07-13 | `ea9eaeb` |
| AUTH-006 | Avoid stale shell command lookup for `op-session` | 2026-07-02 | `ea9eaeb` |
| AUTH-005 | Use Keychain-backed 1Password service account token in Herdr | 2026-07-02 | `ea9eaeb` |
| AUTH-004 | Remove template-time 1Password reads from Databricks config | 2026-06-22 | `ea9eaeb` |
| AUTH-003 | Stop Clockify poll loop from calling `op` | 2026-06-22 | `ea9eaeb` |
| AUTH-002 | Make `secret` fail fast when `op` hangs | 2026-06-22 | `ea9eaeb` |
| AUTH-001 | Remove blocking auth from Herdr shell startup | 2026-06-22 | `ea9eaeb` |
