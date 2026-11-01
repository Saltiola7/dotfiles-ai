---
name: python-design-patterns
license: MIT
description: "Design or refactor Python component responsibilities, dependency direction and abstractions, including entangled I/O and business logic. Use for structural changes."
---

# Python Design Patterns

## Project and workflow boundaries

Apply this guidance within the current task and project Engineering Profile.
Project-selected runtimes, tools, dependencies, compatibility and acceptance
criteria control examples and heuristics. Loading the skill does not install
tools or expand scope. Existing authorization persists; ask only about unresolved
material decisions or required permissions. When used by DBSCTR, the primary owns
phase order and gate decisions; QA supplies configured validation evidence.
Return scoped findings, affected artifacts, supporting evidence and limitations.
See [UPSTREAM.md](UPSTREAM.md) for upstream attribution and local adaptations.

Write maintainable Python code using fundamental design principles. These patterns help you build systems that are easy to understand, test, and modify.

## When to Use This Skill

- Designing new components or services
- Refactoring complex or tangled code
- Deciding whether to create an abstraction
- Choosing between inheritance and composition
- Evaluating code complexity and coupling
- Planning modular architectures

## Core Concepts

### 1. KISS (Keep It Simple)

Choose the simplest solution that works. Complexity must be justified by concrete requirements.

### 2. Single Responsibility (SRP)

Each unit should have one reason to change. Separate concerns into focused components.

### 3. Composition Over Inheritance

Build behavior by combining objects, not extending classes.

### 4. Rule of Three

Treat three occurrences as a useful signal, not a threshold. Abstract earlier when demonstrated divergence or contract risk justifies it; otherwise prefer clarity over premature abstraction.

## Quick Start

```python
# Simple beats clever
# Instead of a factory/registry pattern:
FORMATTERS = {"json": JsonFormatter, "csv": CsvFormatter}

def get_formatter(name: str) -> Formatter:
    return FORMATTERS[name]()
```

## Detailed patterns and worked examples

Detailed pattern documentation lives in `references/details.md`. Read that file when the navigation tier above is insufficient.

## Best Practices Summary

1. **Keep it simple** - Choose the simplest solution that works
2. **Single responsibility** - Each unit has one reason to change
3. **Separate concerns** - Distinct layers with clear purposes
4. **Compose, don't inherit** - Combine objects for flexibility
5. **Rule of three** - Wait before abstracting
6. **Keep functions focused** - Size is a review signal, not a line-count gate
7. **Inject dependencies** - Constructor injection for testability
8. **Delete before abstracting** - Remove dead code, then consider patterns
9. **Validate affected behavior** - Use the project's configured test strategy and appropriate seams
10. **Explicit over clever** - Readable code beats elegant code

## Troubleshooting

**A class is growing and seems to have multiple responsibilities, but splitting it feels wrong.**
Apply the "reason to change" test: list every change that could require editing this class. If the list has items from different domains (e.g., HTTP parsing AND business rules AND formatting), split it. If all changes stem from the same domain concern, the class may be appropriately sized.

**Injecting all dependencies through the constructor is producing constructors with 7+ parameters.**
Review whether the dependencies represent distinct responsibilities. Parameter count alone does not prove a design problem; split only when cohesion, testability or change patterns justify it.

**Composition is producing deeply nested wrapper objects that are hard to trace.**
Review whether each wrapper earns its complexity. Nesting depth is a signal, not a fixed limit; consider whether a Protocol-based approach or simple function composition would make the behavior easier to trace.

**The rule of three says not to abstract yet, but the duplication is causing bugs when one copy is updated but not the other.**
Duplication that diverges in dangerous ways should be abstracted sooner. The rule of three is a heuristic, not a law. If the copies are already diverging incorrectly, extract immediately and add a test that exercises the shared behavior.

**A service layer is importing from the API layer, breaking the dependency direction.**
This is a layering violation. The service layer must not import from handlers. Introduce a shared types/models layer that both can import from, keeping the dependency arrow pointing downward (API → Service → Repository).

## Related Skills

Optional upstream reading; these sibling skills are not required or bundled:

- [python-testing-patterns](https://github.com/wshobson/agents/blob/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/python-development/skills/python-testing-patterns/SKILL.md) — Testing techniques
- [python-project-structure](https://github.com/wshobson/agents/blob/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/python-development/skills/python-project-structure/SKILL.md) — Module organization
