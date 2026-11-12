---
name: python-project-structure
license: MIT
description: Review Python package cohesion, module ownership and public import surfaces when layout or import boundaries change. Preserve project packaging, import conventions and consumer compatibility.
---

# Python Project Structure & Module Architecture

Group code by coherent responsibility and change patterns, and make supported
import surfaces clear to consumers. Inspect existing callers, package metadata,
test discovery, import side effects and project decisions before proposing moves.
Preserve selected tools, runtimes, layout and compatibility. The current primary
owns the task; this guidance does not install tools, scaffold a replacement or
start another audit/lifecycle. See [UPSTREAM.md](UPSTREAM.md) for attribution.

A structural assessment is report-only unless remediation is already authorized.
Offer an incremental change and a retain alternative, with concrete import/caller
costs and validation. Missing `src/`, `__all__` or a particular folder name is not
by itself debt. Examples below are choices, not universal requirements.

## When to Use This Skill

- Starting a new Python project from scratch
- Reorganizing an existing codebase for clarity
- Defining module public APIs with `__all__`
- Deciding between flat and nested directory structures
- Determining test file placement strategies
- Creating reusable library packages

## Core Concepts

### 1. Module Cohesion

Group related code that changes together. A module should have a single, clear purpose.

### 2. Explicit Interfaces

Define supported imports through documentation, naming and deliberate re-exports.
`__all__` optionally controls `from module import *`; it does not make other
attributes inaccessible or establish an enforcement boundary.

### 3. Flat Hierarchies

Choose nesting from coherent ownership and consumer navigation needs. Flat and
nested structures can both be appropriate; neither depth nor file count is a gate.

### 4. Consistent Conventions

Use established project conventions unless evidence justifies a bounded change.

## Example layout

Use this only when the project selects a `src/` package layout. Preserve a working
flat layout unless a concrete isolation/packaging need justifies migration; moving
files also affects package data, entrypoints, test discovery, CI and consumers.


```
myproject/
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── services/
│       ├── models/
│       └── api/
├── tests/
├── pyproject.toml
└── README.md
```

## Fundamental Patterns

### Pattern 1: Cohesive modules

Keep related behavior and invariants together. Consider a split when unrelated
responsibilities change independently or an interface isolates a real ownership
boundary. Consider consolidation when callers must navigate many pass-through
modules to understand one behavior. File length and one-class-per-file conventions
are signals, not thresholds or proof of debt.

```python
# Example: separate responsibilities when that separation earns its cost
# user_service.py - User business logic
# user_repository.py - User data access
# user_models.py - User data structures

# A cohesive user.py can also be appropriate; inspect actual coupling first.
```

### Pattern 2: Explicit Public APIs with `__all__`

Use `__all__` when controlled star-import behavior or documented export enumeration
is useful. It is not required for every module and does not hide unlisted members.
Explicit imports and attribute access still work. Test supported imports and
consumer compatibility rather than treating this list as access control.

```python
# mypackage/services/__init__.py
from .user_service import UserService
from .order_service import OrderService
from .exceptions import ServiceError, ValidationError

__all__ = [
    "UserService",
    "OrderService",
    "ServiceError",
    "ValidationError",
]

# Omission changes star imports, not direct access. Underscore naming and
# documented contracts communicate internal status; enforcement is separate.
```

### Pattern 3: Flat Directory Structure

Avoid nesting that adds navigation without useful ownership. Keep subpackages
when they express real domains or isolation; do not flatten a stable package
solely to shorten paths.

```
# Option: flat technical groups
project/
├── api/
│   ├── routes.py
│   └── middleware.py
├── services/
│   ├── user_service.py
│   └── order_service.py
├── models/
│   ├── user.py
│   └── order.py
└── utils/
    └── validation.py

# Review whether each nested level expresses a real responsibility
project/core/internal/services/impl/user/
```

Add or retain subpackages when their cohesion, public surface or ownership earns the boundary.

### Pattern 4: Test File Organization

Retain the configured runner/discovery authority. Colocated and parallel test
layouts are both valid; verify collection and package artifacts after moving
files. A matching directory tree does not prove behavioral coverage.

**Option A: Colocated Tests**

```
src/
├── user_service.py
├── test_user_service.py
├── order_service.py
└── test_order_service.py
```

Benefits: Tests live next to the code they verify. Easy to see coverage gaps.

**Option B: Parallel Test Directory**

```
src/
├── services/
│   ├── user_service.py
│   └── order_service.py
tests/
├── services/
│   ├── test_user_service.py
│   └── test_order_service.py
```

Benefits: Clean separation between production and test code. Standard for larger projects.

## Advanced Patterns

### Pattern 5: Package Initialization

Deliberate `__init__.py` re-exports can provide a stable consumer surface. Trace
import-time work, optional dependencies and cycles first: importing a package
executes initialization, and broad eager re-exports can make unrelated features
unavailable. Keep expensive I/O and owned resource acquisition out of imports.
A namespace package need not gain `__init__.py` merely to follow this example.

```python
# mypackage/__init__.py
"""MyPackage - A library for doing useful things."""

from .core import MainClass, HelperClass
from .exceptions import PackageError, ConfigError
from .config import Settings

__all__ = [
    "MainClass",
    "HelperClass",
    "PackageError",
    "ConfigError",
    "Settings",
]

__version__ = "1.0.0"
```

The version literal is illustrative: retain the project's authoritative version
source rather than adding a competing one. Consumers can use deliberate re-exports:

```python
from mypackage import MainClass, Settings
```

### Pattern 6: Layered Architecture

If the project selects technical layers, express their actual dependency rules.
The names below are examples; Pydantic, repositories and duplicated data models
are not required merely by this directory structure.

```
myapp/
├── api/           # HTTP handlers, request/response
│   ├── routes/
│   └── middleware/
├── services/      # Business logic
├── repositories/  # Data access
├── models/        # Domain entities
├── schemas/       # API schemas (Pydantic)
└── config/        # Configuration
```

Validate the chosen dependency direction against actual imports and call paths.
A directory name alone does not establish isolation. Pure dependencies and
composition-root wiring follow the selected architecture, not visual tree order.

### Pattern 7: Domain-Driven Structure

Domain-oriented packages can keep related changes together when business models
or owners differ. Compare them with the existing structure; a domain package is
not automatically a separately deployed service, and a shared module needs an
explicit cohesive owner rather than becoming a dumping ground.

```
ecommerce/
├── users/
│   ├── models.py
│   ├── services.py
│   ├── repository.py
│   └── api.py
├── orders/
│   ├── models.py
│   ├── services.py
│   ├── repository.py
│   └── api.py
└── shared/
    ├── database.py
    └── exceptions.py
```

## File and Module Naming

### Conventions

- Use `snake_case` for all file and module names: `user_repository.py`
- Avoid abbreviations that obscure meaning: `user_repository.py` not `usr_repo.py`
- Follow existing naming policy; a cohesive module may contain multiple related classes or functions

### Import style and compatibility

Both absolute and explicit relative imports are valid Python package mechanisms.
Follow project conventions, execution mode and public/internal boundary intent.
For example:

```python
from myproject.services import UserService  # An absolute package import
from . import models                        # A relative sibling import
```

Either form can require changes when modules move. Verify supported package
imports, module execution/CLI entrypoints, import-time side effects and affected
consumers. Public path changes may need re-export shims and a documented
migration window; do not conceal a cycle with local imports without explaining
why that execution-time dependency is appropriate.

## Best Practices Summary

1. **Keep modules cohesive** - Split or consolidate for actual responsibility and change cost
2. **Define supported imports** - Use documentation/re-exports and optional `__all__` deliberately
3. **Justify structure** - Retain useful flat or nested package ownership
4. **Preserve import semantics** - Honor selected relative/absolute conventions and execution modes
5. **Preserve project policy** - Change conventions only with concrete reasons
6. **Match names to content** - File names should describe their purpose
7. **Check boundaries** - Verify selected dependency rules with actual evidence
8. **Document useful decisions** - Reuse existing architecture/API records rather than inventing another required document


For repeatable accepted import rules, consult the project's existing checks or
`python-architecture-fitness` if available. Guidance availability is not authority
to install a checker. Static import checks complement consumer and behavior tests.

Primary semantics: [Python import statement](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement)
and [packages](https://docs.python.org/3/tutorial/modules.html#packages). Match
version-specific changes to the actual supported runtime.
