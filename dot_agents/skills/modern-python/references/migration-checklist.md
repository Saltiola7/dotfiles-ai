# Migration Checklist

Use only the portions selected by the current task and project policy. Examples
below do not authorize tool installation, dependency changes, hook activation,
CI changes or publication. Preserve supported runtimes, dependency constraints,
existing tools and acceptance criteria unless their change is explicitly in scope.

Comprehensive checklist for migrating Python projects to modern tooling.

## Before Migration

- [ ] **Determine layout**: `src/` or flat? Configure `[tool.uv.build-backend]` if flat
- [ ] **Confirm lock strategy**: follow project policy for applications and libraries; preserve development reproducibility
- [ ] **Backup current state**: Create a branch or tag before starting

## Cleanup Old Artifacts

Find legacy linter comments; remove only those made obsolete by the selected, validated replacement:

```bash
# Find files with old linter pragmas
rg "# pylint:|# noqa:|# type: ignore" --files-with-matches

# Find missing __init__.py files
uv run ruff check --select=INP001 .
```

Review these candidates after migration. Remove only confirmed superseded artifacts whose consumers have moved; retained tools and delivery paths keep their files:
- [ ] `requirements.txt`, `requirements-dev.txt`
- [ ] `setup.py`, `setup.cfg`, `MANIFEST.in`
- [ ] `.flake8`, `mypy.ini`, `pyrightconfig.json`
- [ ] `tox.ini` (if not needed)
- [ ] `Pipfile`, `Pipfile.lock`
- [ ] Old virtual environments (`venv/`, `.venv/`)

## .gitignore Updates

Add these entries:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/

# Tools
.ruff_cache/
.ty/

# uv.lock tracking follows the project's lock policy
```

## pyproject.toml Sections to Review for Superseded Tools

- [ ] `[tool.black]`
- [ ] `[tool.isort]`
- [ ] `[tool.mypy]`
- [ ] `[tool.pyright]`
- [ ] `[tool.pylint]`
- [ ] `[tool.flake8]` (if present)

## Post-Migration Easy Wins

Preview relevant checks first and apply only reviewed affected-scope fixes. Configure the minimum supported Python version; an upgrade suggestion does not justify raising it:

```bash
# Pyupgrade modernization (typing, syntax)
uv run ruff check --select=UP --fix .

# Unnecessary variable assignments before return
uv run ruff check --select=RET504 --fix .

# Simplifications (conditionals, comprehensions)
uv run ruff check --select=SIM --fix .

# Remove commented-out code
uv run ruff check --select=ERA --fix .
```

## CI Cleanup

- [ ] Preserve scheduled CI, compatibility coverage and unrelated jobs
- [ ] Update affected commands only when the selected migration changes them
- [ ] Preserve the project's GitHub Actions pinning policy
- [ ] Reuse selected security authorities; introduce tooling only within authorized setup (see [security-setup.md](./security-setup.md))

## Gradual ty Adoption

Only when ty adoption is selected, establish an independent inventory of the
approved Python population and its environment bindings before broad cleanup.
Include tests, scripts and notebooks when selected; a convenient `src/` target
does not establish full coverage. Use the project's checker command, configuration
and runtime targets in every required environment.

Retain original diagnostics and the actual exit status. Build a conflict census
that distinguishes code defects, annotation/stub problems, missing dependencies,
checker limitations and notebook structure. Report completed analysis separately
from diagnostic cleanliness and remaining coverage gaps; do not substitute a
count of matching output lines for either result.

Setup can finish once inventory, environments, execution and the census satisfy
their contract. That does not pass a required typing gate with failing findings.
Keep remediation bounded by runtime contracts and project acceptance criteria.
Do not manufacture a green baseline by disabling diagnostic classes or masking
exit codes. Narrow suppressions require a reason, owner, precise scope and review
condition; suppressed concerns are not evidence of a pass.

## Supply Chain Security

- [ ] Use the project's selected vulnerability-scanning authority
- [ ] Preserve or explicitly select update automation and cadence
- [ ] Follow the project's runtime ranges and deployment-lock policy

See [security-setup.md](./security-setup.md) for pip-audit and Dependabot configuration.

## Verification

After migration, run the project-selected affected checks. The following uv/Ruff/ty/pytest commands are examples for projects that selected those tools; do not install missing tools simply to run this list:

```bash
# Install all dependencies
uv sync --all-groups

# Run linting
uv run ruff check .
uv run ruff format --check .

# Run type checking
uv run ty check src/

# Run tests
uv run pytest

# Security audit
uv run pip-audit

# Build package (if distributable)
uv build
```
