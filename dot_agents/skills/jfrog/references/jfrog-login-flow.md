# Server Login Flow

Add or authenticate an explicitly selected JFrog Platform server only when that
setup/recovery task is authorized. Installation or an ordinary failed query does
not authorize starting login. Existing native credential/configuration ownership
and [local execution boundaries](local-ownership.md) govern the retained helpers.
They create sessions, exchange tokens and write credentials; review their actual
code, collisions and selected CLI version before use.

Requires Artifactory 7.64.0+ and JFrog CLI (`jf`).

## Security rules

- Never print, echo, or display access tokens in terminal output or chat.
- Confirm auth: "authenticated as user X" — never show the token.
- Preserve the selected existing native credential owner. Do not migrate or copy
  secrets into another store, shell profile, project or MCP connection.
- Validate URLs with ping endpoint before shell use.

## Resolve the active environment

```bash
jf config show 2>/dev/null
```

- **Command errors** (nonzero exit / config unreadable) — stop and report; do **not** treat empty output as 0 servers.
- **0 servers** (success, empty) — resolve the intended URL from authorized task
  evidence; request the missing target only if setup is actually requested.
- **1 server** — verify it matches the task and pass `--server-id <server-id>`
  explicitly. Do not change the global default.
- **2+ servers** — user named specific server → use it. Else current default.
  No default → list server IDs/URLs, ask user. **Never iterate servers or
  fallback on error** — see SKILL.md **Server selection rules**.

## Web login (preferred)

### 1. Verify server and register session

```bash
bash <skill_path>/scripts/jfrog-login-register-session.sh "https://mycompany.jfrog.io"
```

Pings server, generates session UUID, registers with Access API. On success:

```
SESSION_UUID=<uuid>
VERIFY_CODE=<last 4 chars>
```

Exit codes: 0 = success, 2 = server unreachable, 3 = registration failed.

### 2. Open the login link and show the verification code

Build login URL:

```
${JFROG_PLATFORM_URL}/ui/login?jfClientSession=${SESSION_UUID}&jfClientName=JFrog-Skills&jfClientCode=1
```

Within an authorized interactive login, use the available supported browser or
provide the URL. Never open a browser merely because this resource was loaded.
OS opener examples, when suitable for that selected environment:

```bash
open "<login-url>"          # macOS
xdg-open "<login-url>"      # Linux
start "" "<login-url>"      # Windows (cmd) / `Start-Process "<login-url>"` in PowerShell
```

Opener fails or unavailable (headless/remote, no `$DISPLAY`) → fall back
to showing the link as text; not a hard failure.

Show verification code prominently, then confirm the link was opened
(or provide it, on fallback):

> ## Verification code: `<last 4 chars of SESSION_UUID>`
>
> I've opened the login page in your browser — enter the code above.
>
> Let me know when you're done.

Wait for user confirmation. Do not poll automatically.

### 3. Retrieve token, save credentials, verify

```bash
bash <skill_path>/scripts/jfrog-login-save-credentials.sh \
  "https://mycompany.jfrog.io" \
  "<SESSION_UUID from step 1>"
```

Substitute literal platform URL and session UUID from step 1 output.

Retrieves one-time token, derives server ID from URL, saves via `jf config add`,
verifies with Artifactory version check. Leaves default `jf` server unchanged —
pass `--server-id=<id>` on subsequent calls (SKILL.md "Server selection rules").
On success:

```
SERVER_ID=<derived-id>
--- Verifying authentication ---
{ "version" : "7.x.x", ... }
```

Exit codes: 0 = success, 2 = token retrieval failed (user may not have
completed browser login — HTTP 400), 3 = empty token, 4 = config save or
verification failed. The token is one-time-use — see Gotchas below.

## Post-login target handoff

Keep using the explicitly selected server ID and leave the global default
unchanged. Changing the global default is separate task scope; do it only when
requested or already authorized, not as a mandatory post-login question.
Verify authentication through bounded non-secret metadata and a task-relevant
same-server operation. Login success alone is not full platform readiness.

## Fallback: manual token setup

Web login fails (old server, network restrictions):

1. Ask user to generate token in JFrog UI:
  **Administration > Identity and Access > Access Tokens > Generate Token**
2. Ask user to run in **their own terminal** (not via your shell tool, no `!`
  prefix), pick **Access Token**, and paste the token at jf's hidden prompt
  (add `--overwrite` if `<server-id>` already exists):

```bash
jf config add <server-id> --url=https://<jfrog-url> --interactive
```

3. After the user confirms, verify with
  `jf api --server-id=<server-id> /artifactory/api/system/version`, then run
  the same-server target handoff above.

Never ask for the token in chat or put it in a command — a command-line
token is visible to other local users in process listings.

## Gotchas

- Token endpoint (`/token/{uuid}`) **one-time-use**. Consumed (even failed save)
  → session UUID invalidated → restart step 1. save-credentials script handles
  cleanup; non-zero exit after token consumed → restart step 1.
- Server ID from hostname: `https://mycompany.jfrog.io` → `mycompany`.
  Self-hosted slugified: `https://artifactory.internal.corp` → `artifactory-internal-corp`.
- `**jf**`, `**uuidgen**` (register-session), and `**jq**` (save-credentials) must be on PATH.
