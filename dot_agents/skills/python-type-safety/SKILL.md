---
name: python-type-safety
license: MIT
description: Design Python typed interfaces, generics, protocols and narrowing when type-bearing code changes. Preserve the project-selected checker and existing lifecycle coverage policy.
---

# Python Type Safety

## Project and workflow boundaries

Apply this guidance within the current task and project Engineering Profile.
Project-selected runtimes, dependencies, tools, error contracts and acceptance
criteria control examples. Loading this skill does not install tools or authorize
external operations. Existing authorization persists; ask only about unresolved
material decisions. DBSCTR retains phase and gate ownership; QA retains configured
validation and evidence ownership. Return scoped findings, affected artifacts,
supporting evidence and limitations. See [UPSTREAM.md](UPSTREAM.md) for provenance.

Use types to describe contracts at component and data boundaries. Keep type
precision separate from runtime validation: annotations do not validate untrusted
JSON, rows or API responses. Parse external objects into checked domain values
before relying on their types.

This lens owns type-design technique, not checker selection or lifecycle coverage.
Use the project's selected checker (including ty where selected), target runtimes,
configuration, environments and existing migration policy. DBSCTR and QA retain
inventory, completed-analysis and diagnostic reporting. Do not create a parallel
checker policy, force mypy/pyright, add blanket ignores, or use casts/Any to hide
unresolved contracts. Use `python-modernization-review` for support-floor changes.

## When to Use This Skill

- Adding type hints to existing code
- Creating generic, reusable classes
- Defining structural interfaces with protocols
- Refining interfaces under the project-selected checker and typing policy
- Understanding type narrowing and guards
- Building type-safe APIs and libraries

## Core Concepts

### 1. Type Annotations

Declare expected types for function parameters, return values, and variables.

### 2. Generics

Write reusable code that preserves type information across different types.

### 3. Protocols

Define structural interfaces without inheritance (duck typing with type safety).

### 4. Type Narrowing

Use guards and conditionals to narrow types within code blocks.

## Quick Start

```python
def get_user(user_id: str) -> User | None:
    """Return type makes 'might not exist' explicit."""
    ...

# Type checker enforces handling None case
user = get_user("123")
if user is None:
    raise UserNotFoundError("123")
print(user.name)  # Type checker knows user is User here
```

## Fundamental Patterns

### Pattern 1: Annotate All Public Signatures

Prioritize public signatures and consequential boundaries within the agreed
scope. Preserve existing annotation conventions and compatibility; do not expand
an implementation task into whole-repository typing remediation.

```python
def get_user(user_id: str) -> User:
    """Retrieve user by ID."""
    ...

def process_batch(
    items: list[Item],
    max_workers: int = 4,
) -> BatchResult[ProcessedItem]:
    """Process items concurrently."""
    ...

class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def find_by_id(self, user_id: str) -> User | None:
        """Return User if found, None otherwise."""
        ...

    async def find_by_email(self, email: str) -> User | None:
        ...

    async def save(self, user: User) -> User:
        """Save and return user with generated ID."""
        ...
```

Run the project's configured checker for changed types and affected consumers.
A stricter mode or checker migration is a separate project decision; preserve
findings and known limitations rather than changing authority to obtain green.

### Pattern 2: Use Modern Union Syntax

Python 3.10+ provides cleaner union syntax.

```python
# Preferred (3.10+)
def find_user(user_id: str) -> User | None:
    ...

def parse_value(v: str) -> int | float | str:
    ...

# Older style (still valid, needed for 3.9)
from typing import Optional, Union

def find_user(user_id: str) -> Optional[User]:
    ...
```

### Pattern 3: Type Narrowing with Guards

Use conditionals to narrow types for the type checker.

```python
def process_user(user_id: str) -> UserData:
    user = find_user(user_id)

    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    # Type checker knows user is User here, not User | None
    return UserData(
        name=user.name,
        email=user.email,
    )

def process_items(items: list[Item | None]) -> list[ProcessedItem]:
    # Filter and narrow types
    valid_items = [item for item in items if item is not None]
    # valid_items is now list[Item]
    return [process(item) for item in valid_items]
```

### Pattern 4: Generic Classes

Preserve payload types without conflating a valid `None` with a missing value.
This optional tagged-outcome example permits successful `None`, and narrowing
selects the correct branch without ignored returns or unchecked casts. Prefer the
project's existing exception/result convention rather than introducing a new one.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure(Generic[E]):
    error: E

def unwrap(result: Success[T] | Failure[E]) -> T:
    if isinstance(result, Failure):
        raise result.error
    return result.value

successful_none: Success[None] = Success(None)
assert unwrap(successful_none) is None
```

## Detailed worked examples and patterns

Detailed sections (starting with `## Advanced Patterns`) live in `references/details.md`. Read that file when the navigation summary above is insufficient.

## Best Practices Summary

1. **Annotate all public APIs** - Functions, methods, class attributes
2. **Use `T | None`** - Modern union syntax over `Optional[T]`
3. **Honor the selected checker** - Use the project configuration and acceptance criteria
4. **Use generics** - Preserve type info in reusable code
5. **Define protocols** - Structural typing for interfaces
6. **Narrow types** - Use guards to help the type checker
7. **Bound type vars** - Restrict generics to meaningful types
8. **Create type aliases** - Meaningful names for complex types
9. **Expose dynamic boundaries** - Narrow unknown inputs through runtime checks; document justified dynamic types and limitations
10. **Separate static and runtime contracts** - Neither annotations nor clean diagnostics prove input validation
