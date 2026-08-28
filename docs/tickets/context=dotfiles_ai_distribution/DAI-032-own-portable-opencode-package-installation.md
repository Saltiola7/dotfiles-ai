---
schema_version: 1
id: DAI-032
slug: own-portable-opencode-package-installation
context: dotfiles_ai_distribution
title: Own portable OpenCode package installation
kind: story
state: ready
priority: high
points: 3
depends_on: []
relations: []
owns:
  - Brewfile
  - run_onchange_before_install-opencode.sh.tmpl
  - README.md
  - .chezmoiignore
  - tests/test_portable_distribution.py
  - docs/specs/dotfiles_ai_distribution
reads:
  - /Volumes/ext/git/Personal/dotfiles/Brewfile
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_portable_distribution.py -q
  - rendered macOS and Linux installer checks
  - live Homebrew OpenCode version check
created: 2026-08-27
updated: 2026-08-27
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Make `dotfiles-ai` the portable OpenCode package owner while preserving the
existing native binary, configuration, and update behavior.

## Context

The public source promises a working OpenCode environment but previously
required users to install OpenCode separately. The maintainer's personal
Brewfile filled that gap only for one installation and created duplicate package
ownership.

## Scope

Install the official Homebrew formula before managed OpenCode configuration,
document Homebrew as the prerequisite, and retire the duplicate personal
formula in a separate repository commit.

## Non-Goals

Do not install Homebrew, Herdr, provider credentials, or unrelated workstation
tools. Do not change guest OpenCode provisioning.

## Acceptance Criteria

- A macOS apply installs `anomalyco/tap/opencode` through a hash-triggered
  Brewfile before managed configuration.
- Linux rendering exits without invoking Homebrew.
- Missing Homebrew fails with actionable guidance.
- `Personal/dotfiles` no longer declares OpenCode after migration.

## Evidence

Record red-first tests, rendered installer checks, the live OpenCode version,
and the personal ownership cleanup commit.

## Risks

Homebrew availability remains an explicit macOS prerequisite. Package updates
follow Homebrew and rerun only when the managed Brewfile changes.

## Review

Confirm ordering, idempotency, platform boundaries, and single ownership.
