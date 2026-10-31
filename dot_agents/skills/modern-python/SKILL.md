---
name: modern-python
description: Guides new Python packaging/tooling setup and explicitly selected tooling migrations, respecting project-selected runtimes, tools, dependency constraints, and acceptance criteria. Use for setup or migration decisions, not routine Python edits.
license: CC-BY-SA-4.0
---

# Modern Python

## Managed use

Project instructions and the Engineering Profile own runtimes, tooling, dependency
constraints, layout, CI schedules, lock strategy and acceptance criteria. Existing
choices remain valid without an explicit request to keep them. Use the recipes
below only for tools and migrations selected within the current task; they are
examples, not automatic replacements or universal gates. Loading this skill does
not install tools, add dependencies, activate hooks or authorize publication.
Existing task authorization persists; ask only about unresolved material choices.
When used by DBSCTR, return setup/migration decisions, affected artifacts,
validation evidence and limitations to the primary; DBSCTR and QA retain lifecycle
and evidence ownership. See [UPSTREAM.md](UPSTREAM.md) for provenance and changes.

Guide for modern Python tooling and best practices, based on [trailofbits/cookiecutter-python](https://github.com/trailofbits/cookiecutter-python).

## When to Use This Skill

- Creating a new Python project or package
- Setting up `pyproject.toml` configuration
- Configuring development tools (linting, formatting, testing)
- Writing Python scripts with external dependencies
- Migrating from legacy tools (when user requests it)

## When NOT to Use This Skill

- **Routine Python code changes**: Use this skill only when setup or tooling is affected
- **Unsupported recipe**: Check each selected tool against the project's supported runtimes; do not raise the runtime floor to fit an example
- **Unrelated tooling**: In mixed codebases, limit the guidance to the affected Python component

## Tool-specific options

| Selected context | Recipe |
|------------------|--------|
| ty configuration | Put `python-version` under `[tool.ty.environment]` |
| uv-managed project | Use `uv add` / `uv remove` for dependency metadata and `uv sync` for its environment |
| Authorized build-backend evaluation | Compare `uv_build` with the existing backend's capabilities before changing it |
| Authorized package-manager migration | uv is an option; Poetry and other project-selected managers remain valid |
| Selected standalone-script packaging | Consider PEP 723; preserve existing requirements and constraints when still authoritative |
| Authorized type-checker evaluation | Compare ty with the project's current mypy/Pyright coverage and integrations |
| Tooling supporting PEP 735 | Consider `[dependency-groups]` for development dependencies |
| uv-managed execution | Prefer `uv run <cmd>` within that project |
| Authorized hook-runner migration | Consider prek after checking existing hooks and project requirements |

**Key principles:**
- Follow the selected package manager and preserve dependency constraints
- Keep environment ownership explicit; uv recipes apply only to uv-managed environments
- Preserve project-selected dependency groups, extras and lock authority unless their migration is in scope

## Decision Tree

```
After confirming the selected tools, what are you doing?
│
├─ Single-file script with dependencies?
│   └─ Use PEP 723 inline metadata (./references/pep723-scripts.md)
│
├─ New multi-file project (not distributed)?
│   └─ Minimal uv setup (see Quick Start below)
│
├─ New reusable package/library?
│   └─ Full project setup (see Full Setup below)
│
└─ Migrating existing project?
    └─ See Migration Guide below
```

## Tool Overview

| Tool | Purpose | Replaces |
|------|---------|----------|
| **uv** | Package/dependency management | pip, virtualenv, pip-tools, pipx, pyenv |
| **ruff** | Linting AND formatting | flake8, black, isort, pyupgrade, pydocstyle |
| **ty** | Type checking | mypy, pyright (faster alternative) |
| **pytest** | Testing with coverage | unittest |
| **prek** | Pre-commit hooks ([setup](./references/prek.md)) | pre-commit (faster, Rust-native) |

### Security Tools

| Tool | Purpose | When It Runs |
|------|---------|--------------|
| **shellcheck** | Shell script linting | pre-commit |
| **detect-secrets** | Secret detection | pre-commit |
| **actionlint** | Workflow syntax validation | pre-commit, CI |
| **zizmor** | Workflow security audit | pre-commit, CI |
| **pip-audit** | Dependency vulnerability scanning | CI, manual |
| **Dependabot** | Automated dependency updates | scheduled |

See [security-setup.md](./references/security-setup.md) for configuration and usage.

## Quick Start: Minimal Project

For an authorized new uv-managed project not intended for distribution. Select only dependencies needed by the project:

```bash
# Create project with uv
uv init myproject
cd myproject

# Add dependencies
uv add requests rich

# Add dev dependencies
uv add --group dev pytest ruff ty

# Run code
uv run python src/myproject/main.py

# Run tools
uv run pytest
uv run ruff check .
```

## Full Project Setup
For a new project, the Trail of Bits cookiecutter is an optional bootstrap when its tool choices fit the agreed setup. Do not fetch or execute it merely because this skill was loaded; use existing setup decisions or resolve an otherwise material choice.

```bash
uvx cookiecutter gh:trailofbits/cookiecutter-python
```

### 1. Create Project Structure

```bash
uv init --package myproject
cd myproject
```

This creates:
```
myproject/
├── pyproject.toml
├── README.md
├── src/
│   └── myproject/
│       └── __init__.py
└── .python-version
```

### 2. Configure pyproject.toml

See [pyproject.md](./references/pyproject.md) for complete configuration reference.

Example sections for a project that selected these tools. Match runtime versions, layout, lint rules and test configuration to project policy:
```toml
[project]
name = "myproject"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = [{include-group = "lint"}, {include-group = "test"}, {include-group = "audit"}]
lint = ["ruff", "ty"]
test = ["pytest", "pytest-cov"]
audit = ["pip-audit"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["ALL"]
ignore = ["D", "COM812", "ISC001"]

[tool.pytest]
addopts = ["--cov=myproject"]  # Only when project policy selects coverage

[tool.ty.terminal]
error-on-warning = true

[tool.ty.environment]
python-version = "3.11"

[tool.ty.rules]
# Strict from day 1 for new projects
possibly-unresolved-reference = "error"
unused-ignore-comment = "warn"
```

### 3. Install Dependencies

```bash
# Install all dependency groups
uv sync --all-groups

# Or install specific groups
uv sync --group dev
```

### 4. Add Makefile

```makefile
.PHONY: dev lint format test build

dev:
	uv sync --all-groups

lint:
	uv run ruff format --check && uv run ruff check && uv run ty check src/

format:
	uv run ruff format .

test:
	uv run pytest

build:
	uv build
```

## Migration Guide

Apply only the explicitly selected migration below. Inspect consumers first, preserve dependency constraints and supported runtimes, and validate replacement behavior before retiring any artifact.

### From requirements.txt + pip

First, determine the nature of the code:

**For standalone scripts**: Convert to PEP 723 inline metadata (see [pep723-scripts.md](./references/pep723-scripts.md))

**For projects**:
```bash
# Initialize uv in existing project
uv init --bare

# Add dependencies using uv (not by editing pyproject.toml)
uv add requests rich  # add each package

# Or import from requirements.txt (review each package before adding)
# Note: Complex version specifiers may need manual handling
grep -v '^#' requirements.txt | grep -v '^-' | grep -v '^\s*$' | while read -r pkg; do
    uv add "$pkg" || echo "Failed to add: $pkg"
done

uv sync
```

Then:
1. Retire requirements files only after every affected consumer uses the verified replacement
2. Recreate an environment only when needed within migration scope; do not delete unrelated environments or caches
3. Apply the project's lockfile version-control policy

### From setup.py / setup.cfg

1. Run `uv init --bare` to create pyproject.toml
2. Use `uv add` to add each dependency from `install_requires`
3. Use `uv add --group dev` for dev dependencies
4. Copy non-dependency metadata (name, version, description, etc.) to `[project]`
5. Retire only superseded setup files after verifying metadata, package contents and all affected consumers

### From flake8 + black + isort

1. Map existing rules, suppressions, format expectations and CI consumers
2. Add Ruff through the selected package manager and configure equivalent checks (see [ruff-config.md](./references/ruff-config.md))
3. Preview changes, then apply the agreed affected-scope fixes and formatting
4. Validate the replacement before removing superseded tools or configuration

### Selected migration from mypy / Pyright to ty

Keep the existing checker unless this migration is explicitly selected. Compare
supported annotations, plugins, stubs, strictness and diagnostics before choosing ty.
If selected, add it through the project's dependency authority, run both against
representative code and validate required coverage. Retire the former checker and
its configuration only after the replacement meets the project's requirements.

## Quick Reference: uv Commands

| Command | Description |
|---------|-------------|
| `uv init` | Create new project |
| `uv init --package` | Create distributable package |
| `uv add <pkg>` | Add dependency |
| `uv add --group dev <pkg>` | Add to dependency group |
| `uv remove <pkg>` | Remove dependency |
| `uv sync` | Install dependencies |
| `uv sync --all-groups` | Install all dependency groups |
| `uv run <cmd>` | Run command in venv |
| `uv run --with <pkg> <cmd>` | Run with temporary dependency |
| `uv build` | Build package |
| `uv publish` | Publish to PyPI |

### Ad-hoc Dependencies with `--with`

For authorized one-off dependency use in a uv-selected workflow, `uv run --with` can run packages not in project metadata. It may download/install packages and is not a permission bypass:

```bash
# Run Python with a temporary package
uv run --with requests python -c "import requests; print(requests.get('https://httpbin.org/ip').json())"

# Run a module with temporary deps
uv run --with rich python -m rich.progress

# Multiple packages
uv run --with requests --with rich python script.py

# Combine with project deps (adds to existing venv)
uv run --with httpx pytest  # project deps + httpx
```

**When to use `--with` vs `uv add`:**
- `uv add`: Package is a project dependency (goes in pyproject.toml/uv.lock)
- `--with`: One-off usage, testing, or scripts outside a project context

See [uv-commands.md](./references/uv-commands.md) for complete reference.

## Quick Reference: Dependency Groups

```toml
[dependency-groups]
dev = ["ruff", "ty"]
test = ["pytest", "pytest-cov", "hypothesis"]
docs = ["sphinx", "myst-parser"]
```

Install with: `uv sync --group dev --group test`

## Project-aligned Checklist

- [ ] Preserve or select a layout appropriate to the deliverable
- [ ] Match `requires-python` and tool targets to supported runtimes
- [ ] Use project-selected linting, formatting and type-checking authorities
- [ ] Apply the project's test strategy and coverage policy; no universal percentage
- [ ] Keep dependency metadata, constraints and lock authority consistent
- [ ] Validate any selected migration before retiring old consumers or artifacts
- [ ] Preserve scheduled CI and unrelated tooling
- [ ] Use PEP 723 only where standalone-script packaging fits the project

## Read Next

- [migration-checklist.md](./references/migration-checklist.md) - Step-by-step migration cleanup
- [pyproject.md](./references/pyproject.md) - Complete pyproject.toml reference
- [uv-commands.md](./references/uv-commands.md) - uv command reference
- [ruff-config.md](./references/ruff-config.md) - Ruff linting/formatting configuration
- [testing.md](./references/testing.md) - pytest and coverage setup
- [pep723-scripts.md](./references/pep723-scripts.md) - PEP 723 inline script metadata
- [prek.md](./references/prek.md) - Fast pre-commit hooks with prek
- [security-setup.md](./references/security-setup.md) - Security hooks and dependency scanning
- [dependabot.md](./references/dependabot.md) - Automated dependency updates
