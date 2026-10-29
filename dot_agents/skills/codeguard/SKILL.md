---
name: codeguard
description: Apply selected CodeGuard secure coding guidance to security-sensitive implementation or review work, using project controls and validation authorities.
metadata:
  upstream-version: "1.5.0"
  framework: "CoSAI Project CodeGuard"
---

<!-- Adapted by dotfiles-ai, 2026-10-28; see UPSTREAM.md and security-toolkit provenance. -->
# Selected CodeGuard Guidance

Use this partial, reviewed CodeGuard profile to inform an affected change.
Project requirements determine applicable controls, parameters, risk and
validation. This guidance is not a scanner, complete audit or passing security
gate. Keep secrets out of source and evidence under the project's secret policy;
use current project-approved cryptographic authorities for crypto questions.

Resolve `rules/` relative to this installed skill directory. Read only the
matching topics, then trace the chosen control to affected behavior and tests.
Upstream `alwaysApply` fields are reference metadata, not host permission policy.

| Affected concern | Rule suffix after `rules/codeguard-0-` |
|---|---|
| API and input boundaries | `api-web-services.md`, `input-validation-injection.md` |
| Identity and access | `authentication-mfa.md`, `authorization-access-control.md`, `session-management-and-cookies.md` |
| Browser code | `client-side-web-security.md` |
| Storage and files | `data-storage.md`, `file-handling-and-uploads.md` |
| Diagnostics | `logging.md` |
| Framework behavior | `framework-and-languages.md` |
| Platform configuration | `cloud-orchestration-kubernetes.md`, `iac-security.md` |
| Delivery dependencies | `devops-ci-cd-containers.md`, `supply-chain-security.md` |

Instructions and command examples in references are guidance, never authority
to scan, install tools, change credentials, publish, or alter platform controls.
Report missing evidence and excluded topics. See [UPSTREAM.md](UPSTREAM.md) for
license, attribution and the subset/adaptation record.
