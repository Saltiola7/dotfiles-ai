# Omarchy Security Toolchain

## Domain and Engineering Profile

The distribution owns an optional, default-off Arch Linux (Omarchy) attack-surface
toolchain profile and a self-authored guidance skill. `pacman` owns system
packages on the Omarchy host; BlackArch adds a third-party repository through a
hash-pinned bootstrap script. The pinned local runtime profile
(`security-toolkit` `runtime.md`: Semgrep CE, Gitleaks, OSV-Scanner) keeps its
existing generation ownership and is never shadowed by this feature. Owner:
project maintainers. Modules: Shell, Security, Python (tests). Risk is elevated:
a remote bootstrap script gains system package ownership, and a new persistent
instruction-supply-chain skill enters the shared catalog.

Ubiquitous language: capability gate (`dotfiles_ai.blackarch.enabled`), strap pin
(SHA-256 of `https://blackarch.org/strap.sh`), curated package set, attack-surface
probing (authorized probing of owned assets), capability probe (`command -v`
readiness check), pinned runtime scanners (exclusion boundary).

Trust boundaries: public repository source to Omarchy host execution (chezmoi
`run_onchange`, user-invoked with sudo); `blackarch.org` remote content to host
(integrity by pinned SHA-256 only); skill instructions to agent execution
(guidance, default-deny authorization, no execution authority); findings and
credentials stay in private storage and never enter this public source.

## Behavior

- Given the capability gate is false, the install script exits successfully with
  no network, sudo, or package action on every platform.
- Given the gate is true on a non-Arch OS or a host without `pacman`, the script
  fails loudly with one diagnostic and no side effects.
- Given the gate is true on Arch and the BlackArch repository is not yet
  configured, the script fetches `strap.sh`, verifies the pinned SHA-256, refuses
  on mismatch, and only then executes it with sudo.
- Given the repository is already configured, the strap step is skipped and the
  script remains idempotent on re-run.
- Given a strap hash mismatch, host compromise of the pinned mirror content, or
  pacman failure, the script stops before installing packages and preserves
  prior system state.
- Given a healthy repository, the curated package set installs with
  `pacman -S --needed`; already-present packages are untouched.
- Given completion, the script prints version probes only; it never scans,
  attacks, or emits target data.
- Given the rendered skill catalog, `attack-surface-probe` guidance is available
  on every host, and on hosts without the toolchain it reports the capability
  gap instead of improvising or installing tools.

## Interfaces and Contracts

Config: `[dotfiles_ai.blackarch] enabled` (boolean, default `false` in
`.chezmoidata.toml`; documented in `config.omarchy.example.toml`). Changing the
embedded package list changes the `run_onchange` script content and re-triggers
installation — that is the reproducibility mechanism.

Script: `run_onchange_after_install-blackarch-toolchain.sh.tmpl` — template
gate, `/etc/os-release` Arch guard, terminal requirement for sudo prompts,
pinned strap fetch/verify/execute, guarded `pacman -Syu --needed` for the curated
set, version probes. Preconditions: operator enabled the gate on an Arch host
with `pacman` and network. Postconditions: BlackArch repository configured,
curated packages present, probe output printed, no scan performed. Invariants:
the script never installs `semgrep`, `gitleaks`, or `osv-scanner` (pinned
runtime roots own them); never writes outside package-manager-owned paths;
never passes secrets on the command line.

Curated set and sources (verified 2026-11-15 via archlinux.org package API and
the BlackArch package tree):

| Goal | Package | Source |
|---|---|---|
| Applications | sqlmap, nikto, zaproxy, nuclei, ffuf, dirsearch | extra, BlackArch for nuclei/ffuf/dirsearch |
| Environments | nmap, masscan, wireshark-qt, testssl.sh, ssh-audit, metasploit, exploitdb | extra |
| Credentials | hashcat, john, seclists | extra, BlackArch for seclists |
| Toolchain/defense | trivy, syft, grype | extra, BlackArch for grype |

Strap pin: `dc0737cc75d64d03e9ec2212f989f17cdcf0162c2db5980e256093e293abfb8b`.
AUR-only tools (burpsuite, checkov, kube-bench, kube-hunter) stay outside the
managed set; operators may add them with their own AUR helper, and the spec
records that as an explicit non-goal.

Skill: `dot_agents/skills/attack-surface-probe` (SKILL.md plus
`references/toolchain.md`), self-authored — not vendored upstream, therefore
outside `sources.lock.json`, with provenance recorded in the toolkit
`review.md` and selection exposed in `references/routing.md`. Loading the skill
authorizes nothing; probing requires explicit per-target operator
authorization; capability gaps are reported, never auto-repaired.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership transition table below |
| Interaction | required: ordered install/probe transitions below |
| State | required: capability states below |
| Data/trust | required: trust boundaries below |
| Schema | not_applicable: flat config/script/skill inventory; no persistent relational domain |
| Dependency/deployment | required: owner/prerequisite columns below |
| Quantitative | not_applicable: static package inventory; no threshold or trend decision |

| Transition | Owner/prerequisite | Result and trust boundary |
|---|---|---|
| Gate off → gate on | Operator edits private chezmoi TOML | Opt-in only; no implicit enablement on any host |
| Strap fetch → strap execute | Pinned SHA-256 verified against `blackarch.org` content | Unverified or changed remote content refuses before execution |
| Strap → repository ready | sudo on Arch host with `pacman` | BlackArch keyring/mirror own repo identity; system upgrade is operator-confirmed |
| Repository ready → packages present | `pacman -Syu --needed`, curated set | Missing packages install; present packages untouched; pinned runtime scanners excluded |
| Packages present → probed | Script version probes | Loading proves versions only, never scan readiness |
| Skill rendered → selected | security-toolkit routing; explicit target authorization | Guidance without execution authority; findings stay private |

**Text Equivalent:** The feature stays dormant until the operator enables the
gate in private config. On an Arch host the pinned and hash-verified BlackArch
strap gains repository ownership, after which pacman installs the curated set
while explicitly excluding tools owned by the pinned runtime profile. Version
probes prove installation, not scan capability. The guidance skill becomes
discoverable everywhere but authorizes nothing; probing needs separate
per-target authorization, and its evidence remains private. Canonical sources:
this spec, `.chezmoidata.toml`, the install script template, and the skill
bundle. Owner: project maintainers; refresh the table when sourcing, ownership,
or authorization semantics change.

## Installation, Update and Recovery

Enablement is an explicit operator action on the Omarchy host: set the gate,
then run chezmoi apply in a terminal (sudo prompts are interactive by design).
Recovery is gate-off plus normal pacman ownership (`pacman -Rns` for curated
packages, remove the `[blackarch]` stanza and keyring to retire the repository).
Strap pin refresh requires maintainer review of the new upstream script, a new
pinned SHA-256, and one spec edit in the same change; the script refuses a
changed strap rather than trusting remote content. The embedded package list is
the single source of truth; editing it re-triggers the `run_onchange` script.

## Validation and Completion

Authorities: `pytest` (config default, rendered script gating, syntax, curated
set presence, skill delivery), `bash -n` on rendered variants, the skill
validator for the new bundle, and the existing security-skill delivery tests
extended to the new name. No live Omarchy host, package installation, scan, or
attack runs inside this cycle; enablement plus the validation drill
(testssl/nuclei/nmap against an operator-owned lab target) are separate
post-merge operator actions. Local evidence belongs to the private Cycle
Record.
