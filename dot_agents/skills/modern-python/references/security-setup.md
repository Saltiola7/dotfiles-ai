# Security Setup

Use only the portions selected by the current task and project policy. Examples
below do not authorize tool installation, dependency changes, hook activation,
CI changes or publication. Preserve supported runtimes, dependency constraints,
existing tools and acceptance criteria unless their change is explicitly in scope.

Security tooling for Python projects: pre-commit hooks, CI auditing, and dependency scanning.

## Tool Installation

Use existing selected security tools. Install only missing tools that are part of authorized setup, using the project's installation authority; this reference does not create an installation requirement.

### prek (pre-commit runner)

```bash
# Homebrew (recommended)
brew install prek

# Cargo
cargo install prek

# Standalone installer
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/j178/prek/releases/latest/download/prek-installer.sh | sh
```

### Security tools

Selected hooks may download tools when run via prek; include that dependency execution in the setup decision. Manual installation examples, only when authorized:

```bash
# Homebrew (macOS/Linux)
brew install actionlint shellcheck

# Python tools via uv
uv tool install detect-secrets
uv tool install zizmor
```

Alternative installation methods:

- **actionlint**: `go install github.com/rhysd/actionlint/cmd/actionlint@latest`
- **zizmor**: `cargo install zizmor`
- **detect-secrets**: `pipx install detect-secrets`

## Quick Setup

Use only for selected security setup. Preserve existing hooks and baseline files;
review a new baseline before adopting it, rather than replacing one blindly.

```bash
# 1. Install security hooks
prek install

# 2. Initialize secrets baseline
detect-secrets scan > .secrets.baseline

# 3. Audit existing workflows
actionlint .github/workflows/
zizmor .github/workflows/
```

See [templates/pre-commit-config.yaml](../templates/pre-commit-config.yaml) for a complete hook configuration.

## Tool Matrix

| Tool | Runs | Catches |
|------|------|---------|
| **shellcheck** | pre-commit | Shell script bugs, quoting issues |
| **detect-secrets** | pre-commit | Leaked API keys, passwords, tokens |
| **actionlint** | pre-commit, CI | Workflow syntax errors, invalid refs |
| **zizmor** | pre-commit, CI | Workflow security issues, excessive permissions |
| **pip-audit** | CI, manual | Known CVEs in dependencies |
| **Dependabot** | scheduled | Outdated dependencies with vulnerabilities |

## Pre-commit Hooks

These run locally before each commit via prek.

### shellcheck - Shell Script Linting

Catches common shell scripting errors: unquoted variables, undefined variables, deprecated syntax.

```yaml
# In .pre-commit-config.yaml
- repo: https://github.com/koalaman/shellcheck-precommit
  rev: <latest>  # https://github.com/koalaman/shellcheck-precommit/tags
  hooks:
    - id: shellcheck
      args: [--severity=error]  # Start strict, adjust if needed
```

Common findings:
- `SC2086`: Unquoted variable expansion (word splitting risk)
- `SC2046`: Unquoted command substitution
- `SC2155`: Declare and assign separately to avoid masking return values

### detect-secrets - Secret Detection

Prevents accidentally committing API keys, passwords, and tokens.

```yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: <latest>  # https://github.com/Yelp/detect-secrets/releases
  hooks:
    - id: detect-secrets
      args: [--baseline, .secrets.baseline]
```

**First-time setup:**

```bash
# Generate baseline of existing "secrets" (false positives to ignore)
detect-secrets scan > .secrets.baseline

# Review the baseline - ensure no real secrets
cat .secrets.baseline

# Commit the baseline
git add .secrets.baseline
```

**When hook fails:**

```bash
# View the finding (non-interactive)
detect-secrets audit --report .secrets.baseline
```

If false positive: update baseline with `detect-secrets scan --update .secrets.baseline`
If real secret: report it without exposing its value and follow the project's incident/remediation authority. Credential rotation is not authorized by loading this skill.

## CI Security

These run in GitHub Actions on every push/PR.

### actionlint - Workflow Syntax Validation

Catches syntax errors, invalid action references, and type mismatches before they fail in CI.

```yaml
- repo: https://github.com/rhysd/actionlint
  rev: <latest>  # https://github.com/rhysd/actionlint/releases
  hooks:
    - id: actionlint
```

Run manually:

```bash
actionlint .github/workflows/
```

Common findings:
- Invalid event triggers
- Undefined workflow inputs
- Shell syntax errors in `run:` blocks
- Invalid action version references

### zizmor - Workflow Security Audit

Finds security issues in GitHub Actions workflows: excessive permissions, injection risks, untrusted inputs.

```yaml
- repo: https://github.com/zizmorcore/zizmor-pre-commit
  rev: <latest>  # https://github.com/zizmorcore/zizmor-pre-commit/releases
  hooks:
    - id: zizmor
      args: [--persona=regular, --min-severity=medium, --min-confidence=medium]
```

Run manually:

```bash
zizmor .github/workflows/
```

**Fixing `excessive-permissions`:**

Effective defaults depend on repository and organization policy. Inspect them and declare the least permissions required by each workflow:

```yaml
# Read-only workflows (lint, test, audit)
permissions:
  contents: read

# Workflows that push or create releases
permissions:
  contents: write

# Workflows that comment on PRs
permissions:
  contents: read
  pull-requests: write
```

Common findings:
- `excessive-permissions`: No `permissions:` block
- `template-injection`: Using `${{ github.event.* }}` unsafely
- `unpinned-action`: Actions not pinned to SHA
- `dangerous-triggers`: `pull_request_target` with checkout

## Dependency Security

### pip-audit - Vulnerability Scanning

Checks installed packages against the Python Advisory Database (PyPA) for known CVEs.

**Setup:**

```toml
# pyproject.toml
[dependency-groups]
audit = ["pip-audit"]
```

**Usage:**

```bash
# Audit current environment
uv run pip-audit

# Audit project dependencies using the selected resolution policy
# This form can resolve/install dependencies; inspect tool behavior before use
uv run pip-audit .

# Only for an authorized remediation; changes package versions
uv run pip-audit --fix
```

**In CI:**

```yaml
- name: Security audit
  run: uv run pip-audit .
```

**When vulnerabilities found:**

1. Assess the finding using the project's vulnerability-review authority
2. For authorized remediation, select a compatible fixed version and validate it through the dependency authority
3. If no fix is available, report residual risk and options; do not silently suppress the finding or accept risk on the project's behalf

### Dependabot - Automated Updates

Automatically creates PRs for outdated dependencies.

For an explicitly selected Dependabot setup, adapt [templates/dependabot.yml](../templates/dependabot.yml) to the existing configuration and project update policy.

**How pip-audit and Dependabot work together:**

| Tool | Trigger | Scope |
|------|---------|-------|
| pip-audit | Every CI run | Known CVEs in current deps |
| Dependabot | Weekly schedule | All outdated deps, security + non-security |

- **pip-audit** catches: "You have a vulnerable version right now"
- **Dependabot** prevents: "You'll fall behind and accumulate vulnerabilities"

The illustrated cooldown can allow time for newly published problems to be discovered; it does not establish package safety. Choose cadence and exceptions through project policy.

See [dependabot.md](./dependabot.md) for advanced configuration.

See [prek.md](./prek.md) for complete pre-commit hook configuration including security hooks.
