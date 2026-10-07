# Host packages, interpreters and shell resolution

Home: dotfiles, host_tool_maintenance. Owner: dotfiles maintainer.
Scope: every installed managed formula, cask, App Store app, declared Go/uv tool,
mise runtime and integration; latest available stable within explicit existing
constraints. Production consumers and enterprise-seo-tools remain excluded.
Risk: elevated for service/runtime changes, routine for isolated leaf tools.

## Sources and discovered conflicts

Current bounded inventory and completed CLI upgrades:
[maintenance follow-up](findings/maintenance-follow-up.md).

The owning source is dotfiles/Brewfile, dot_common_profile.tmpl, installer templates
and machine-local chezmoi values. Its configured test authority is pytest via
pyproject.toml; tests/test_terminal_environment.py and test_ai_config_ownership.py
cover environment and ownership behavior. The terminal test currently requires
OpenCode wrapper selection despite later PATH changes: native-updater migration
must revise executable selection while retaining state routing, not simply delete it.

Brewfile still declares colima, docker, docker-buildx, docker-compose and
docker-credential-helper, and a Colima/Atuin bootstrap script remains in the source.
dotfiles-ai's distribution CHANGELOG records their retirement in DAI-033-1.
Resolve that source/deployment conflict before a full bundle apply; upgrades must
not resurrect intentionally retired services. Inspect existing user changes first.
The source also has one-time recovery hooks; promote durable behavior into the
proper owner rather than relying on one machine's already-executed hook state.

## Domain and behavior

Package owner means the one installer selecting an executable; runtime consumer
means any environment/service referencing its binary, shared library or prefix.

| Given | When | Required outcome |
|---|---|---|
| Outdated managed package with classified consumers | Upgrade is applied | Latest eligible stable selected and affected runtime smoke passes |
| Conflicting or retired declaration | Inventory runs | Resolve ownership before installation; no silent reintroduction |
| Multiple uv/mise/Python roots | Fresh shells resolve tools | Interactive, login and noninteractive paths use the declared owner consistently |
| Python minor pin | New patch exists | Minor pin unchanged; dependent environments remain executable |
| Package-manager lag or upstream constraint | Latest cannot be installed | Record installed/candidate version and concrete reason, not a false current result |
| Shared binary needed by production | Candidate would affect that consumer | Hold that package and report coupling; production is not upgraded indirectly |

## Implementation boundary and validation

Native OpenCode/Codex installation declarations are owned by native-tool-updates;
this lane records their package-manager status but must not install duplicate copies.
Dotfiles owns shell environment defaults; changes shared with native-tool-updates
are serialized. Do not upgrade project environments from this lane.

Inventory with native package/mise/uv commands, mapping installed and declared
packages, executable resolution and service consumers. Separate already-completed
upgrades from currently available releases. No blanket brew cleanup or interpreter
removal; referenced old kegs stay until consumer checks pass.

Validation: targeted chezmoi render/diff/apply, bash/zsh syntax where affected,
pytest tests/test_terminal_environment.py tests/test_ai_config_ownership.py,
fresh login/interactive/noninteractive resolution, per-package functional smoke,
and a second empty targeted apply. Check services separately from binary versions.
MAS login, GUI restart or unavailable release metadata is an explicit blocker.

Before Build, create or select the host profile in the owning repository, with
Bash/Zsh/Go templates and package managers, supported machine roles, consumer
boundaries, pytest/rendering authorities and managed deployment obligations.
Kernel/review/deploy/operate/maintain gates required; separate release not applicable.
Remaining qualification: exhaustive installed/declared inventory, retired-source
conflict resolution and complete interpreter consumer map. No profile-ready claim.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: package owner/consumer and lane ownership are explicit |
| Interaction | not_applicable: inventory-before-upgrade order is explicit |
| State | required: behavior table above |
| Data/trust | not_applicable: no credentials or state transfer introduced |
| Schema | not_applicable: native package metadata reused |
| Dependency/deployment | required: WORKSTREAMS.md activation table |
| Quantitative | not_applicable: no comparative measurements claimed |

**Text Equivalent:** upgrade only classified active packages; conflicting ownership
and protected consumers block activation. Fresh shells and affected services must
resolve the intended runtime after repeat apply. Owner: host maintainer. Canonical
source: this contract; update when package scope, ownership or consumer policy changes.
