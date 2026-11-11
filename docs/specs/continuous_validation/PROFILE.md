# Continuous Validation Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Portable standalone Python runner and versioned repository-adapter protocol for opt-in advisory validation during development |
| Accountable owner | Dotfiles owner; repository maintainers own check definitions and validation authorities |
| Languages/frameworks | Python `>=3.12`, Python Dagger SDK for Linux checks, native subprocess backend for required macOS checks, JSON requests/results/events |
| Applicable modules | Python, Security, and Cloud for the optional dedicated local VM/runtime bootstrap; GCP remains a later slice |
| Runtime/platform support | Local Apple Silicon macOS controller, optional dedicated ARM64 Lima VM with pinned Linux Dagger execution, and native macOS validation; amd64 and additional platforms require independent qualification |
| Compatibility | Versioned closed runner/adapter protocol; explicit snapshot/check/lane identities; preserve repository-owned test, affected-selection, coverage, and vulnerability authorities |
| Configuration | Default-off feature flag plus private per-worktree enrollment; distribution owns concrete settings, managed installation, and service configuration |
| Trust/data | Check definitions execute repository code only after enrollment. Source snapshots, logs, credentials, absolute paths, runtime/session identities, and observation storage remain private. Published documents and summaries are generic and sanitized |
| Agent boundary | Optional exact-session feedback through the owning control-plane adapter; check output is untrusted diagnostic data; native permissions and approvals remain authoritative |
| Gate boundary | Observations are advisory. No automatic Gate Ledger mutation, required-check acceptance, merge, delivery, or production authority |
| Release | Initial source slice creates no independently published package or image; later releasable artifacts require the Release gate |
| Deployment | Source/draft delivery and targeted optional setup are separate; explicit setup owns pinned local runtime resources, and per-worktree enrollment remains default-off |
| Operations | One host-wide admission budget, local worker bounded to 2 CPUs/4 GiB RAM/40 GiB disk, foreground observations, cancellation/recovery, bounded private retention, and separate enrollment/VM stop controls |
| Maintenance/retirement | Exact supported-version pins and capability reprobes, dependency/EOL intake through existing owners, safe disable/uninstall, and explicit private evidence retention/removal policy |
| Quality/security authorities | Repository-selected affected pytest, Python compilation, publication/instruction checks, declared coverage and vulnerability authorities, plus real Dagger/native/feedback runtime smokes for activation |
| Product Intent | Internal developer infrastructure; no separate product-facing document required for the initial slice |

The current slice is elevated risk because it runs repository-defined checks and
may submit diagnostic input to an existing agent session. The runner owns neither
DBSCTR lifecycle semantics nor native session transport nor managed installation.
Those integrations remain with their existing contexts.

Version pins must identify the Python runtime, runner, adapter, Dagger CLI, engine,
SDK, selected images/tools, and session transport capabilities. A documented CLI
surface is not end-to-end activation evidence. Missing or incompatible components
report unavailable; ordinary checks never install or upgrade components, and
explicit setup uses reviewed pins. Beta-feature assumptions are not permitted.

## Local Runtime Platform Contract

| Concern | Current authority and boundary |
|---|---|
| Purpose and owner | Disposable optional advisory worker; distribution owns bootstrap and its operator owns activation, cost review, recovery, and disposal |
| Topology | Mac controller and private immutable snapshots; local ARM64 Lima VM; privileged Dagger engine inside that VM; private Unix socket; native host checks remain separate |
| Declarative input and state | Reviewed [Lima template](../../../private_dot_config/dotfiles-ai/continuous_validation/engine/lima.yaml), pinned bootstrap constants and SDK lock; private host ownership/configuration receipts, CLI/SDK installation, observations and journals; guest named volume retains Dagger cache |
| Plan and drift | Read-only `continuous-validation engine plan`; only explicit `engine setup --enable-shadow` creates/starts owned resources. Setup compares owner, resource shape, template/configuration digests, socket, runtime versions and image pins; drift is unavailable rather than silently repaired |
| Identity and secrets | Exact session UUID is a caller binding; actor/native-session association remains unavailable absent independent proof. No host mounts, host SSH keys, SSH-agent forwarding or implicit project credentials. Runtime artifacts stay under private host permissions; disk-encryption posture is not attested by this source slice |
| Network | No public host listener or forwarded guest TCP ingress. Private Unix engine socket and Lima control transport have local ownership; outbound HTTPS/package access is used for explicit provisioning and workload dependency resolution |
| Resource and cost bound | Local VM uses 2 CPUs, 4 GiB RAM and 40 GiB disk; controller/native checks have admission and priority, not hard CPU/RAM quotas. No GCP resource or metered cloud spend is created |
| Resilience and recovery | Best-effort developer feedback, no availability SLA. Disposable caches need no backup promise; preserve host observations and journals under the retention policy. Unknown process completion blocks admission. Explicit setup validates an owned stopped worker before restarting it |
| Rollout and health | Default-off source installation, explicit engine setup, one worktree opt-in and bounded `watch --once`/checkpoint smokes precede a two-worktree experiment. Ready engine and synthetic transport evidence do not establish an entire repository or foreground-responsiveness pass |
| Rollback and retirement | Disable each enrollment, confirm owned work termination, then separately stop the exact owned VM. Preserve private state; wipe/delete requires an authorized retention/disposal decision |
| Supply chain and maintenance | Dagger CLI/engine/SDK 0.21.10, CLI archive checksum, image digests, SDK lock, selected workload Python/uv versions and supported Lima version are current source authorities. Package/runtime drift requires reviewed requalification; no automatic upgrade during checks |

Codex CLI 0.163.0 active delivery and idle wake were exercised in a synthetic open
interactive fixture using exact computed nonces. Closed noninteractive execution
accepted queue input without consumption and is not qualified. Enrollment may
copy a strict operator-supplied qualification receipt, but the dispatcher still
checks version and freshness and never infers ordinary consumption from queue
acceptance. Desktop checkout work is supported independently of Desktop feedback.

The initial local-shadow activation did not include automatic lifecycle
checkpoint hooks. The follow-up below adds explicit per-task checkpoint
enrollment; installation still starts no login service or forever watcher. GCP topology, networking, spend and authoritative evidence
reuse require separately bounded delivery decisions. Current gate results and
runtime identities remain in private lifecycle/qualification evidence.

## Visual Evidence

The [context specification](README.md#visual-evidence) owns canonical visuals and
Text Equivalents. Boundary, Interaction, State, Data/trust, Schema, and
Dependency/deployment are required and represented there through an ownership
flowchart and contract tables. Quantitative is not_applicable because this profile
makes no measured performance claim. The context owner updates those representations
when profile boundaries, identity, feedback, platform, or activation contracts change.

## Checkpoint and CLI feedback follow-up

[SESSION-HOOKS.md](SESSION-HOOKS.md) selects Python, Security and ML/AI for typed
native agent feedback, plus the existing local-runtime Cloud controls for the
bounded pilot. The lifecycle owns post-success event production outside its
mutation guard; the executor owns private queue draining and freshness; native
control planes own existing-session lookup and delivery. Explicit enrollment
selects checkpoint and feedback capabilities independently. Installation remains
default-off, with no automatic worker/service start. Complete-identity receipts
are required for new parity qualification; older observations stay readable and
unqualified for that claim. Native credentials, transcripts and consumer identities
remain private; no paid provider evaluation is introduced.

## Optional Vertex review follow-up

[PR-AGENT.md](PR-AGENT.md) adds a separately default-off, controller-owned
advisory review capability. Python, Security, ML/AI and the existing local-runtime
Cloud controls apply. A pinned PR-Agent image reviews a bounded immutable patch
inside the existing local Dagger worker. Repository test adapters, selectors,
coverage and formal gates retain their existing authority.

Vertex uses the existing isolated credential owner and interactive authentication
on the operator's Mac. An explicitly selected authorized-user ADC may be passed
to the pinned review process as an ephemeral Dagger secret. This transfers a
refresh-capable credential into the isolated worker for that execution; it is not
a token-only or Mac-exclusive credential guarantee. No host credential directory,
implicit credential discovery or unattended interactive login is permitted.
Provider project, location, model and disclosure scope must be configured
explicitly before inference. The ordinary disabled path performs no credential
lookup, installation or provider call.

The source/install slice permits private runtime installation and bounded
offline or synthetic-provider qualification. It performs no live Vertex
inference, private-source upload or GCP provisioning. Real provider evaluation,
model quality and metered cost remain separately qualified activation concerns.
Existing exact-session transports may deliver explicitly opted-in advisory
completion references; successful review findings never become failed tests or
formal gate evidence. Local OpenCode is a feedback client, not an inference
proxy in this slice.

## Bounded storage repair

[STORAGE.md](STORAGE.md) defines the PY-03/PY-04 follow-up within this context:
readable bounded private journals, atomic observation-capacity reservation and
preserved request replay. Python and Security apply; runtime/provider topology,
dependency pins and feedback authority remain unchanged. The private format change
requires old writers to stop and makes enabled in-place downgrade unsupported.
Private deployment, operation and rollback qualification remain required before
delivery; Discovery documents do not establish those results.
