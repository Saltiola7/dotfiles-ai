---
name: jfrog
description: >-
  Operate or review actual JFrog Artifactory repositories/artifacts, build info,
  Xray findings and JFrog platform APIs. Use for concrete JFrog tasks; generic
  GraphQL, evidence, workers or MCP requests alone do not select this skill.
metadata:
  role: base
  version: "0.44.0"
---

# JFrog platform operations

Use the selected project's JFrog target, tools and validation. Installing this
skill supplies guidance and complete resources; it does not install a plugin,
execute helpers, enable MCP, log in or change configuration.

## Environment check

Use already available, task-appropriate capabilities. An existing JFrog MCP
connection can supply structured tools; the dedicated CLI or `jf api` can cover
many of the same operations. MCP is not a prerequisite for ordinary CLI/API work.
Discover actual tools and current CLI help rather than guessing names or flags.
The base `jf api` floor is 2.100.0; the complete collection's setup capability
needs 2.106.0. Report missing/incompatible prerequisites and preserve their owner.

Read [local ownership](references/local-ownership.md) before setup, login,
telemetry or helper use. Upstream environment/upgrade probes can contact networks
and write caches. They are not automatic checks, and model identity/telemetry
must not be invented or disclosed merely to run a recipe. The distribution's
optional CLI installer and existing native owners govern installation/upgrades.

## Server selection rules (mandatory)

Resolve one server from explicit task/project configuration or a configured
unambiguous default; ask only when a material target remains unresolved. Use
redacted supported metadata, never raw credential files or config exports.
Pass `--server-id <SID>` after the relevant CLI subcommand on network calls.
Keep global defaults unchanged. MCP and CLI authenticate independently: verify
that both address the same selected platform before combining their evidence.

Stop on denied access, target mismatch, timeout or a missing endpoint. Do not
switch accounts, servers or transports to bypass a denial or obtain an answer.
After separately authorized same-server credential recovery, at most one retry
may be justified. Empty or failed results do not authorize preparatory uploads,
repository creation, alternate credentials or repeated guessed endpoints.

## Execution and evidence

Stay within current task authority; authorized mutations need no repeated
permission question, but resource installation or a recipe is not authorization.
Read first where useful, verify selected operation/target, and distinguish planned,
executed and verified changes. Retain project-selected scan/release gates.

For CLI/API calls, check options with native help. `jf api` needs the product
prefix (`/artifactory`, `/xray`, `/access`, and so on); status is on stderr and body
on stdout. Save output privately before parsing rather than repeat network calls.
Do not send structured MCP results through shell parsing. Bound queries and
pagination (at most 20 advancing pages); redact credential-bearing output.

## Load relevant detail

| Task | Read only the relevant guidance |
|---|---|
| `jf api`, AQL or advanced CLI I/O | [CLI caveats](references/cli-gotchas.md), [API contract](references/jf-api.md), [output handling](references/preserving-command-output.md), [command discovery](references/cli-command-discovery.md) |
| Artifact, build, Xray, Catalog, OneModel or administration domain | [Reference index](references/INDEX.md), then the specific domain |
| Setup/login/helper behavior | [Local ownership](references/local-ownership.md), then the needed setup reference |
| Extended orchestration or upstream examples | [Retained workflow](references/upstream-workflow.md); local ownership and current task authority govern every procedure |

Related workflows are selected by their own task descriptions: package-manager
binding, Curation, reference architecture and AI Catalog. JFrog MCP management
applies only to selected JFrog Agent Guard/governed-catalog work; existing native
owners handle unrelated MCPs. Unavailable tools remain a capability gap, never a
reason to claim live platform readiness from installed files.
