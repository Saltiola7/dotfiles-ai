---
name: pulumi-component
description: Design or repair Pulumi ComponentResource interfaces, parenting, provider inheritance and registered outputs. Use for actual component changes or explicitly selected package distribution, preserving the project's language and SDK.
---

# Pulumi Components

Keep the selected language, CLI/SDK/provider versions, backend, stack, package
manager and task authority. A component or cross-language package is an option
for a useful abstraction; it is not required for every set of resources.

- `myorg:index:StaticSite` is a resource type token, not a full resource URN.
  Type, logical name, parent and aliases affect resource identity.
- Pass supported options to the base component; parent actual owned children and
  preserve explicit provider selection. Resolve any deliberate provider override
  against the target account/region rather than silently falling back.
- Accept `Input` for properties that can depend on Outputs. Use known plain
  configuration for synchronous topology choices; an Output object is not its
  resolved boolean/string. Prefer resource declarations outside `apply`.
- Expose the useful typed outputs and register them with `registerOutputs` /
  `register_outputs` when registration is complete. Keep secret outputs marked.
- Refactors preserve prior identity, data protection and compatibility; inspect
  the selected preview evidence before claiming a non-destructive change.

For interface examples, conditional creation, composition or provider forwarding,
read those sections of [component details](references/details.md). Read its
multi-language/distribution sections only when packaging or publication is part
of the task. They include version-sensitive examples, not permission to install
SDKs/plugins, generate packages, publish, change credentials or deploy.

Use project-selected tests and validation. Component mocks do not establish cloud
provider behavior, and a preview executes program/provider work. Return actual
coverage and remaining gaps to the current workflow; keep its delivery gates.
