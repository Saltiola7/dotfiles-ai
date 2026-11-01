# Platform Specialist Guidance

Use the [common selection contract](specialist-selection.md), then only the
specialist relevant to the current platform concern. Existing Cloud obligations,
project target policy and QA remain authoritative.

| Evidence | Preferred specialist and boundary |
|---|---|
| Linux host/service/package/permission failure | `linux-host-diagnostics`; read RPM-family detail only for the actual distribution |
| macOS launchd, launch environment, TCC or Keychain failure | `macos-operations`; app design/build/signing can use the corresponding installed macOS app skill |
| Actual Podman/container or Quadlet lifecycle | `podman-quadlet`; resolve runtime host, account and user/system ownership |
| Generic Kubernetes resource authoring | `k8s-manifest-generator`; keep platform-specific defaults out of generic manifests |
| Helm templates/values/package work | `helm-chart-scaffolding`; local lint/render does not prove cluster acceptance |
| Actual gcloud command work | `gcloud`; preserve explicit project/location and native authorization |
| GCP authentication/identity choice | `google-cloud-recipe-auth`; reuse known decisions and existing identity authority |
| GKE workload failure | `gke-workload-troubleshooting`; bounded diagnostics and evidence-backed hypotheses |
| GKE workload authentication to GCP | `gke-workload-identity`; distinguish IAM/RBAC and use non-secret verification |
| Actual Pulumi program, Output/Input, configuration or resource refactor | `pulumi-best-practices`; preserve language, provider, backend and stack authority |
| Pulumi ComponentResource interface/ownership | `pulumi-component`; type tokens, parenting/providers and registered outputs |
| One identified failed Pulumi operation | `pulumi-debug-failed-operation`; bounded actual records and hypotheses, without implicit state change/retry |
| Hetzner Cloud or hcloud resource/action work | `hetzner-operations`; effective identity/configuration, persistent data and recovery |
| Actual Dagger module or CI execution graph | `dagger-pipelines`; selected SDK/engine, terminal evaluation, caches, secrets and capabilities |
| Actual Chezmoi source, templates, destination drift or scoped apply | `chezmoi-operations`; identify hook/script/external effects and preserve repository deployment ownership |
| Actual PyInfra inventory, deploy code or host operation | `pyinfra-deployments`; distinguish preparation facts, execution-time conditions and verified host results |
| Prefect run, deployment, log or orchestration-state diagnosis | `prefect-operations`; verify the selected API identity and available tools, with self-hosted operation independent of Cloud; project SDK/CLI remains sufficient for flow authoring |
| JFrog Artifactory artifacts/repos, builds, Xray findings or platform API work | `jfrog`; use the selected server and relevant references; configured QA authority remains unchanged |
| Explicit Artifactory package-manager binding | `jfrog-setup-package-managers`; preserve selected repository, runtime and workspace configuration owner |
| JFrog Curation package-policy check/download or blocked-resolution diagnosis | `jfrog-package-curation`; CLI check/download differs from MCP-only historical troubleshooting |
| JFrog topology, sizing, HA, recovery or hosting design | `jfrog-reference-architecture`; preserve selected hosting target; planning needs no configured CLI |
| Selected JFrog AI Catalog skill/plugin lifecycle | `jfrog-ai-catalog`; preserve managed source and required scan/provenance gates |
| Explicit JFrog installation/readiness diagnosis | `jfrog-init`; manual invocation policy and native installer/client owners remain authoritative |
| Explicit JFrog Agent Guard or governed MCP catalog work | `jfrog-mcp-management`; no takeover of unrelated MCP setup or automatic global governance |

Resolve target facts from existing project/configuration evidence before asking.
Record material ambiguity rather than silently using an ambient cluster,
namespace, account or project. Loading multiple relevant techniques is valid;
the platform's presence alone does not select every row.

Keep current task authorization. Do not automatically install clients, enable
APIs, fetch credentials, change IAM, apply manifests, start services or publish
resources because a recipe includes such a command. An authorized task can
proceed without repeated permission questions; missing material authority remains
a real boundary. Read-only output can contain secrets: select/redact fields and
avoid token/environment dumps.

Existing plugin-owned macOS app skills stay externally owned and are resolved by
available catalog name/capability. Do not duplicate that plugin merely to provide
host-service diagnosis. Unavailable preferred guidance remains a limitation;
required execution/validation evidence keeps its existing gate semantics.

## Sources and delivery

The shared [source inventory](specialist-sources/sources.lock.json), including
reviewed Pulumi and Django bundles, records immutable
upstream roots/commits, original blobs/hashes, complete packaged bytes/modes,
licenses and reversible patches for this expansion, including shell/async and
Modular bundles. Each bundle's `UPSTREAM.md` records its adaptations. Existing
Python bundles retain their current separate source inventory. Original local
Hetzner/Dagger guidance links official selected-version sources; it does not
redistribute the considered community trees or imply an installed Dang dependency.
Source modes and declared chezmoi installed modes are distinct. The retained Helm
helper projects as a readable resource and is invoked through Bash; installation
does not execute it or promise a preserved executable bit.

Maintain full resource trees; review helpers before execution. Updates deliberately
review the selected revision and all local patches, including supporting examples.
Preserve exact upstream license notices and original Git identities. Installing
guidance does not install upstream plugins/hooks or target-project runtimes.

The marimo notebook, Jupyter conversion and WASM bundles share this inventory and
retain their official complete resource trees. Original Chezmoi, PyInfra and
Python/Rust methods link official documentation; they do not redistribute the
considered community candidates. The Python module owns notebook/interop routing.

The official Prefect workflow bundle shares this inventory as
`prefect-operations`. It is adapted for capability-aware self-hosted inspection;
installing guidance does not require the optional local MCP runtime. Runtime,
private API selection and native client registration retain separate owners.

Use the existing distribution owner: isolated exact-target projection, prior-live
comparison, reviewed preview, application with scripts excluded, then complete
file/mode verification and repeated-apply/diff evidence. Preserve unrelated
installed edits. A disjoint reconciled entrypoint overlay is verified separately
from canonical source bytes and retained privately with its preimages; unresolved
overlap blocks that target. Rollback restores reviewed source/inventory plus the
relevant prior installed state without removing unrelated skills.

Filesystem installation, native discovery, actual target-tool availability and
demonstrated task behavior are separate claims. Report only observed evidence.

The complete seven-root official JFrog collection shares this inventory. Its
compact entrypoints route into full lazy resources, with scoped adaptations for
native configuration, tool ownership, requested package versions and scan gates.
The optional CLI installer is default-off and missing-only; skills need no plugin,
Agent Guard, login or MCP connection. CLI/API operations and MCP tools overlap,
but Curation's historical troubleshooting requires actual `jfs_curation_*` tools.
Legacy upstream helper/config writers remain inert until task-specific review and
version-qualified owner selection. Preserve existing native MCP owners.
