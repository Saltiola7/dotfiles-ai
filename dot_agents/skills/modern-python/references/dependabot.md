# Dependabot: Automated Dependency Updates

Use only the portions selected by the current task and project policy. Examples
below do not authorize tool installation, dependency changes, hook activation,
CI changes or publication. Preserve supported runtimes, dependency constraints,
existing tools and acceptance criteria unless their change is explicitly in scope.

[Dependabot](https://docs.github.com/en/code-security/dependabot) automatically creates pull requests to keep your dependencies up to date. GitHub hosts it natively—no external service required.

## Why Use Dependabot?

- **Security**: Can propose dependency updates for known vulnerabilities; validation and merge remain project-owned
- **Freshness**: Keeps dependencies current without manual tracking
- **Visibility**: PRs show changelogs and compatibility notes

## Configuration

For a selected Dependabot setup, adapt [templates/dependabot.yml](../templates/dependabot.yml) to the existing configuration. Preserve required schedules and version constraints.

The template includes:
- Weekly update schedule for pip and GitHub Actions
- Illustrative 7-day cooldown; project policy selects cadence and exceptions
- Grouping to reduce PR noise

## Supply Chain Protection

The illustrated `cooldown.default-days: 7` delays updates for newly published versions. This may allow time for problems to be discovered, but it does not prove package safety; verify ecosystem/version support and project policy.

**Why this matters:**
- Attackers sometimes publish malicious versions of legitimate packages
- A 7-day delay allows time for detection and removal
- Combined with weekly schedules, this balances security with freshness

## Common Options

| Option | Description |
|--------|-------------|
| `interval` | `daily`, `weekly`, or `monthly` |
| `cooldown.default-days` | Days to wait before updating new releases |
| `ignore` | Skip specific dependencies or versions |
| `groups` | Group related updates into single PRs |
| `reviewers` | Auto-assign reviewers to PRs |

## See Also

- [GitHub Dependabot docs](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [security-setup.md](./security-setup.md) - Security tooling overview
- [prek.md](./prek.md) - Pre-commit hooks (complementary tool)
