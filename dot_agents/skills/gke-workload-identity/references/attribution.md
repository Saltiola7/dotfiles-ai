# Optional request attribution

The upstream skill describes request tags for measuring skill usage. This managed
adaptation retains source attribution in UPSTREAM.md and LICENSE.upstream. Loading
the skill does not enable request tracking, add metrics environment variables,
rewrite User-Agent headers or change provider/client configuration.

Only apply request attribution when the user or project policy explicitly selects
it for the concrete environment. Respect existing opt-outs and provider/header
ownership. Tags identify software usage, not an authenticated actor or permission.
Do not add tracking to generated user code or shared artifacts incidentally.
