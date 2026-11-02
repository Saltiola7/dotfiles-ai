# Runtime access boundaries

| Operation | Material capability and effects |
|---|---|
| Guard check | Can execute selected CLI, access its credential store internally and request selected platform HTTPS endpoints. |
| Catalog list/inspect through npx | Can fetch/execute npm code, write npm caches and request registry/platform networks; requires a reviewed selected pin/runtime owner. |
| OAuth/login or enable-tools action | Can open a browser and persist tokens; separate concrete authentication scope and native owner. |
| Native entry change | Writes selected effective configuration through its existing owner; preserve other entries, hooks and trust. |
| OAuth cache retirement | Secret-bearing shared state and potentially surviving callers; explicit exact-key retirement scope, no raw values or whole-directory removal. |

Skill frontmatter, examples and helper names do not grant access or authenticate
an actor. Honor the actual harness permission model. A denial, unavailable network
or failed guard remains a gap, not a false disabled/pass result. Do not broadly
escalate permissions, switch clients, change an allowlist or retry outside native
controls merely to make a check succeed. Concrete existing task authority persists
without repetitive questions; genuinely missing material authority must be resolved.
