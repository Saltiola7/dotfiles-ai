# DBSCTR Module: Mojo

## Applicability

- **REQUIRED:** Load when affected `.mojo` source, project metadata or explicit requirements identify Mojo work.
- **CONDITIONAL:** Load for actual Mojo/Python interop, Mojo GPU work or explicitly selected Modular project setup.
- **PROJECT POLICY:** SDK/channel, targets, environment manager and validation commands remain project-selected.
- **EXAMPLE:** A Python-only project mentioning Mojo does not automatically select a new language, SDK or model platform.

## Engineering Profile Extensions

- **REQUIRED:** Record Mojo/Modular SDK version/channel, OS/architecture/device targets, deliverable and dependency/environment authority.
- **CONDITIONAL:** Record Python ABI/interoperability boundaries, GPU/runtime prerequisites and benchmark workload where affected.
- **PROJECT POLICY:** Preserve supported stable/nightly commitments and existing pins; current upstream syntax examples may target a different SDK.

## Required Outcomes

- **REQUIRED:** Match syntax, ownership/lifetime and library APIs to the selected compiler rather than pretrained Python or another Mojo release.
- **REQUIRED:** Preserve declared interfaces, memory/resource lifetimes, errors and data contracts; validate with the configured compiler/tests when required.
- **CONDITIONAL:** Verify interop conversion, ownership, exceptions and ABI on relevant targets; keep untrusted values out of dynamically assembled executable code.
- **CONDITIONAL:** GPU work needs actual target support, synchronization, correctness and representative measurement before a performance claim.
- **PROJECT POLICY:** Installed guidance is not evidence that an SDK, GPU, driver or target environment exists.

## Conditional Controls

Use [specialist selection](../references/specialist-selection.md) at first relevant
selection. Load only the official bundle matching the concrete concern.

| Current evidence | Preferred specialist |
|---|---|
| Writing/reviewing changed Mojo source | `mojo-syntax` |
| Actual GPU kernel/device behavior | `mojo-gpu-fundamentals` alongside relevant syntax |
| Python/Mojo calls or extension ABI | `mojo-python-interop` alongside relevant syntax |
| Explicit new Modular project/setup | `new-modular-project` |

- **CONDITIONAL:** Load Python or ML/AI modules when their real interfaces or model behavior are affected; Mojo alone does not select MAX model-lifecycle work.
- **REQUIRED:** Missing required target/compiler evidence follows the existing Gate Ledger; equivalent guidance cannot manufacture a pass.
- **EXAMPLE:** Existing Pixi/uv choices and SDK pins remain authoritative when reading setup examples.

## Validation Capabilities

- **REQUIRED:** Name compiler/build/test authorities and target identities for affected claims; record unavailable execution honestly.
- **CONDITIONAL:** Check relevant Python ABI and GPU devices separately from syntax/static review. Compare equivalent synchronized workloads for performance claims.
- **PROJECT POLICY:** Use installed/project-selected tools and existing authorization; skill selection does not install an SDK or provision compute.

## Lifecycle Obligations

- **REQUIRED:** Carry version/channel compatibility, target capabilities, ownership and boundary evidence through existing phases.
- **CONDITIONAL:** Evaluate build/release/deployment, operations and support/deprecation where the actual deliverable requires them.
- **PROJECT POLICY:** DBSCTR owns lifecycle, QA owns validation and the project owns platform/tool policy.
