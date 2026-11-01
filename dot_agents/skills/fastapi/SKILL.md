---
name: fastapi
license: MIT
description: Implement or review selected FastAPI routes, dependency/resource scope, response contracts and streaming. Use for actual FastAPI boundaries; preserve existing versions, tools and service ownership.
---

# FastAPI

Inspect installed FastAPI/Starlette/Pydantic versions and existing routes,
authorization, resource owners and wire contracts. Preserve selected tools and
runtime support. This technique supplements the current primary; loading it does
not select a framework, migrate dependencies or authorize service/DB operations.
See [UPSTREAM.md](UPSTREAM.md) for source and adaptations.

Choose `def` versus `async def` from actual blocking/awaited calls. A synchronous
helper called inside an async endpoint still blocks unless explicitly offloaded.
Keep request dependencies, app-lifetime clients and streaming producers under
clear owners. Check response filtering on the actual path, including custom
`Response` objects that bypass model processing.

Read only relevant references:

- [Dependencies](references/dependencies.md): cleanup scope and callable choices.
- [Responses](references/responses.md): public fields and serialization boundaries.
- [Streaming](references/streaming.md): supported JSON Lines/SSE/byte APIs and cleanup.
- [Lifecycle](references/lifecycle.md): lifespan ownership and focused offline checks.
- [Routing](references/path-operations.md) and [Pydantic](references/pydantic.md):
  compatible declarations and preserved request/schema behavior.
- [Framework patterns](references/framework-patterns.md): annotated examples,
  optional frontend/telemetry/CLI features; check installed support first.
- [Other tools](references/other-tools.md): existing tool and dependency choices.

Use the project's runner for request/response, invalid-input, cleanup and relevant
streaming tests. In-process clients do not prove proxy/deployment behavior. Report
unavailable runtime coverage without installing or contacting services implicitly.
