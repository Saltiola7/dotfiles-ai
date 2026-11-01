---
name: pydantic
license: MIT
description: Define or review Pydantic validation and serialization at actual Python input/output boundaries, including constraints, coercion, model variants and settings. Use for selected Pydantic code, not general Python typing or unrelated internal models.
---

# Pydantic

Inspect the selected Python/Pydantic versions, existing models and their callers.
Preserve runtime support, dependency owners and the accepted data contract. This
technique supplements the current primary; it does not start another audit,
replace internal domain models or authorize configuration/service operations.
See [UPSTREAM.md](UPSTREAM.md) for immutable source and adaptations.

Establish which values are trusted, accepted and emitted. Preserve intentional
coercion, strictness, unknown-field handling, aliases, defaults and required/null
semantics. Prefer built-in constraints for simple rules; keep custom validators
pure and type-aware. Treat schema and serialization changes as public contracts.
Check declared versus runtime subclass output before broadening exposed fields.

Read only the reference needed:

- [Modeling and validation](references/modeling.md): constraints, validators,
  coercion, unions, annotations, serialization and focused contract checks.
- [Settings](references/settings.md): existing `pydantic-settings` boundaries,
  source precedence, deterministic validation and secret-safe diagnostics.

Use the project's existing tests to exercise invalid inputs and emitted values;
static types or generated JSON Schema do not prove runtime behavior. If a required
runtime is unavailable, report the unexecuted checks without installing a new one.
