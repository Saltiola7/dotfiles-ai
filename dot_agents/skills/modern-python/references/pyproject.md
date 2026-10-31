# pyproject.toml Configuration Reference

Use only the portions selected by the current task and project policy. Examples
below do not authorize tool installation, dependency changes, hook activation,
CI changes or publication. Preserve supported runtimes, dependency constraints,
existing tools and acceptance criteria unless their change is explicitly in scope.

Complete reference for configuring `pyproject.toml` for modern Python projects.

For uv-managed projects, prefer `uv add` and `uv remove` so metadata and locks stay consistent. Other projects retain their selected dependency authority.

## Complete Example

Illustrative uv/Ruff/ty/pytest setup. Retain the project's runtime floor, backend,
layout, metadata and checks rather than copying all sections verbatim.

```toml
[project]
name = "myproject"
version = "0.1.0"
description = "A modern Python project"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "requests",
    "rich",
]

[project.optional-dependencies]
# Use for optional features users can install
cli = ["typer"]

[project.scripts]
myproject = "myproject.cli:main"

[project.urls]
Homepage = "https://github.com/org/myproject"
Documentation = "https://myproject.readthedocs.io"
Repository = "https://github.com/org/myproject"

[build-system]
requires = ["uv_build>=0.9,<1"]  # Use latest 0.x; check https://pypi.org/project/uv-build/
build-backend = "uv_build"

[dependency-groups]
dev = ["ruff", "ty"]
test = ["pytest", "pytest-cov", "hypothesis"]
docs = ["sphinx", "myst-parser"]

[tool.uv]
default-groups = ["dev", "test"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src"]

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "D",        # pydocstyle (enable selectively)
    "COM812",   # trailing comma (conflicts with formatter)
    "ISC001",   # implicit string concat (conflicts with formatter)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",     # assert allowed in tests
    "PLR2004",  # magic values allowed in tests
    "ANN",      # annotations optional in tests
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

[tool.pytest]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "--cov=myproject",
    "--cov-report=term-missing",
]

[tool.coverage.run]
branch = true
source = ["src/myproject"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

## Section Reference

### [project]

Core project metadata following PEP 621.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Package name (lowercase, hyphens) |
| `version` | Yes | Semantic version |
| `description` | No | One-line description |
| `readme` | No | Path to README file |
| `license` | No | SPDX license identifier |
| `requires-python` | Recommended | Python version constraint |
| `authors` | No | List of author dicts |
| `dependencies` | No | Runtime dependencies |

### [project.optional-dependencies]

**Rarely needed.** Only use for optional *runtime* features that end users install:

```toml
[project.optional-dependencies]
# User installs with: uv add myproject[postgres]
postgres = ["psycopg2"]
```

For new setups whose tooling supports PEP 735, prefer `[dependency-groups]` for development tools. Preserve existing extras when consumers still rely on them.

### [project.scripts]

Console entry points:

```toml
[project.scripts]
myproject = "myproject.cli:main"
myproject-serve = "myproject.server:run"
```

### [build-system]

Build backend configuration. Example when the project selected `uv_build`:

```toml
[build-system]
requires = ["uv_build>=0.9,<1"]  # Use latest 0.x; check https://pypi.org/project/uv-build/
build-backend = "uv_build"
```

Check the selected backend against required packaging capabilities. Preserve the project's static or dynamic versioning strategy.

For flat layout (no `src/` directory), configure the module root:

```toml
[tool.uv.build-backend]
module-root = ""
```

> **Note:** Preserve project-selected version ranges and locks. Change constraints only as part of the selected dependency work.

### [dependency-groups]

Development dependencies (PEP 735). Unlike optional-dependencies, these are NOT installed by users:

```toml
[dependency-groups]
dev = [{include-group = "lint"}, {include-group = "test"}, {include-group = "audit"}]
lint = ["ruff", "ty"]
test = ["pytest", "pytest-cov"]
audit = ["pip-audit"]
docs = ["sphinx", "myst-parser"]
```

Install with: `uv sync --group dev --group test`

### [tool.uv]

uv-specific configuration:

```toml
[tool.uv]
# Default groups to install with `uv sync`
default-groups = ["dev", "test"]

# Python version management
python-preference = "managed"
```

## Version Specifiers

| Specifier | Meaning |
|-----------|---------|
| `>=1.0` | At least version 1.0 |
| `>=1.0,<2.0` | Version 1.x only |
| `~=1.4` | Compatible release (>=1.4, <2.0) |
| `==1.4.*` | Any 1.4.x version |

## uv.lock Handling

| Project Type | uv.lock in Git? | Why |
|--------------|-----------------|-----|
| Application | Project policy; commonly commit | Reproducible deployment environments |
| Library | Project policy; often commit development lock | Consumers resolve runtime ranges; development can still be locked |

## Common Patterns

### Library Package

```toml
[project]
dependencies = []  # Minimal runtime deps

[project.optional-dependencies]
# Optional runtime features (user installs with mylib[async])
async = ["httpx"]

[dependency-groups]
dev = ["ruff", "ty"]
test = ["pytest", "pytest-cov"]
```

### Application Package

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
]

[project.scripts]
myapp = "myapp.main:run"

[dependency-groups]
dev = ["ruff", "ty", "pytest"]
```

### CLI Tool

```toml
[project]
dependencies = [
    "typer",
    "rich",
]

[project.scripts]
mytool = "mytool.cli:app"

[dependency-groups]
dev = ["ruff", "ty", "pytest"]
```
