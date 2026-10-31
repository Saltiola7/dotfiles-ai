# Ruff Configuration Reference

Use only the portions selected by the current task and project policy. Examples
below do not authorize tool installation, dependency changes, hook activation,
CI changes or publication. Preserve supported runtimes, dependency constraints,
existing tools and acceptance criteria unless their change is explicitly in scope.

Ruff is a Python linter and formatter written in Rust. It can replace selected checks from other tools after compatibility and project requirements are verified.

## Basic Setup

Example for a project selecting Ruff. Match `target-version`, source discovery, selected rules and formatting to the project's requirements:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src"]

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "D",        # pydocstyle
    "COM812",   # trailing comma (formatter conflict)
    "ISC001",   # string concat (formatter conflict)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

## Running Ruff

```bash
# Lint
uv run ruff check .
uv run ruff check --fix .        # Auto-fix
uv run ruff check --fix --unsafe-fixes .  # Including unsafe fixes

# Format
uv run ruff format .
uv run ruff format --check .     # Check only
uv run ruff format --diff .      # Show diff
```

## Rule Categories

Using `select = ["ALL"]` enables all rules. Common categories:

| Code | Category | Description |
|------|----------|-------------|
| `E`, `W` | pycodestyle | Style errors and warnings |
| `F` | Pyflakes | Logical errors |
| `I` | isort | Import sorting |
| `N` | pep8-naming | Naming conventions |
| `D` | pydocstyle | Docstring conventions |
| `UP` | pyupgrade | Python upgrade suggestions |
| `B` | flake8-bugbear | Bug detection |
| `S` | flake8-bandit | Security issues |
| `A` | flake8-builtins | Built-in shadowing |
| `C4` | flake8-comprehensions | Comprehension improvements |
| `DTZ` | flake8-datetimez | Timezone-aware datetime |
| `T10` | flake8-debugger | Debugger statements |
| `T20` | flake8-print | Print statements |
| `PT` | flake8-pytest-style | Pytest style |
| `Q` | flake8-quotes | Quote consistency |
| `SIM` | flake8-simplify | Simplification suggestions |
| `TID` | flake8-tidy-imports | Import hygiene |
| `ARG` | flake8-unused-arguments | Unused arguments |
| `ERA` | eradicate | Commented-out code |
| `PL` | Pylint | Pylint rules |
| `RUF` | Ruff-specific | Ruff's own rules |
| `ANN` | flake8-annotations | Type annotation checks |

## Recommended Ignores

### Consider Formatter-Conflict Ignores for the Selected Ruff Version

```toml
ignore = [
    "COM812",   # missing-trailing-comma
    "ISC001",   # single-line-implicit-string-concatenation
]
```

### Common Ignores

```toml
ignore = [
    "D",        # Docstrings (enable selectively)
    "ANN401",   # Dynamically typed Any
    "TD002",    # Missing TODO author
    "TD003",    # Missing TODO link
    "FIX002",   # Line contains TODO
]
```

## Per-File Ignores

```toml
[tool.ruff.lint.per-file-ignores]
# Tests
"tests/**/*.py" = [
    "S101",     # assert usage
    "PLR2004",  # magic values
    "ANN",      # type annotations
    "D",        # docstrings
]

# Scripts
"scripts/**/*.py" = [
    "T20",      # print statements
    "INP001",   # implicit namespace package
]

# __init__.py
"__init__.py" = [
    "F401",     # unused imports (re-exports)
]

# Migrations
"**/migrations/*.py" = [
    "ALL",      # ignore all
]
```

## Import Sorting (isort)

```toml
[tool.ruff.lint.isort]
force-single-line = false
known-first-party = ["myproject"]
required-imports = ["from __future__ import annotations"]
section-order = [
    "future",
    "standard-library",
    "third-party",
    "first-party",
    "local-folder",
]
```

## Docstring Style (pydocstyle)

If enabling docstring checks:

```toml
[tool.ruff.lint]
select = ["D"]
ignore = [
    "D100",     # Missing module docstring
    "D104",     # Missing public package docstring
    "D203",     # 1 blank line before class docstring (conflicts D211)
    "D213",     # Multi-line summary second line (conflicts D212)
]

[tool.ruff.lint.pydocstyle]
convention = "google"  # or "numpy", "pep257"
```

## Formatter Configuration

```toml
[tool.ruff.format]
quote-style = "double"           # or "single"
indent-style = "space"           # or "tab"
skip-magic-trailing-comma = false
line-ending = "auto"             # or "lf", "crlf"
docstring-code-format = true
docstring-code-line-length = 80
```

## Type Checking

Ruff does NOT do type checking. Keep the project's selected checker. Example only when ty was selected:

```bash
# Add ty to dev dependencies
uv add --group dev ty

# Run type checking
uv run ty check src/
```

Evaluate checker capability and project integrations as well as speed before any migration from mypy or Pyright.

## CI Configuration

```yaml
# GitHub Actions
- name: Lint
  run: uv run ruff check --output-format=github .

- name: Format check
  run: uv run ruff format --check .
```

## Migration from Other Tools

Apply only an explicitly selected migration. Verify equivalent required checks,
configuration consumers and CI before retiring superseded packages or settings.

### From flake8

After verifying coverage for the selected flake8 migration, possible superseded artifacts include:
- flake8
- flake8-* plugins
- .flake8 config file

### From black

If replacing Black is selected and formatting changes are accepted, possible superseded artifacts include:
- black
- [tool.black] config

### From isort

If replacing isort is selected and import-order behavior is verified, possible superseded artifacts include:
- isort
- [tool.isort] config

Use `[tool.ruff.lint.isort]` for isort settings.

## Code Modernization

Use pyupgrade rules for compatible syntax changes within scope. Set the target to the minimum supported runtime; preview before applying fixes:

```bash
uv run ruff check --select=UP .        # Preview only
uv run ruff check --select=UP --fix .  # Apply reviewed compatible fixes
```

Common modernizations include:
- `typing.Optional[X]` → `X | None`
- `typing.List[X]` → `list[X]`
- `super(ClassName, self)` → `super()`
- Format strings and other syntax upgrades

## Line Length Migration

If migrating from 120 to 100 char lines, expect manual fixes.
For less churn during initial migration, keep existing:

```toml
line-length = 120  # Match existing; tighten later
```
