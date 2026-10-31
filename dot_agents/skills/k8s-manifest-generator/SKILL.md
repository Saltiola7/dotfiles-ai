---
name: k8s-manifest-generator
description: Design and review Kubernetes manifests for workloads, services, configuration and storage. Use for concrete manifest changes; preserve the project's target cluster/version, resource policy and deployment authority.
---

# Kubernetes Manifest Design

Use for manifests and their workload contracts. Resolve existing project facts
before asking about missing requirements. The current primary owns scope and
lifecycle; this skill supplies design and validation techniques.

## Establish the target

Identify the supported Kubernetes version/distribution, resource owner, intended
cluster/context and namespace, deployment mechanism, image identity, availability
needs, configuration/secret authority, persistent data and network exposure.
Do not silently infer a production target from active kubeconfig or example names.
Preserve existing Helm, Kustomize, GitOps and project validation choices.

## Design the affected resources

- Match selectors and template labels, named ports and Service targets. Separate
  startup, readiness and liveness behavior; a restart cannot repair every failure.
- Size requests, limits, replicas and rollout bounds from workload evidence and
  policy. CPU limits and every probe type are not universal requirements.
- Preserve immutable image/provenance policy. Examples use placeholders and
  illustrative versions; they do not select a release, provider or namespace.
- Keep non-sensitive configuration in ConfigMaps. Use the selected secret
  authority; never put real credentials or token values in committed examples.
- Define storage class, access mode, retention and recovery with the data owner.
  Changing a PVC or image is not proof that application data remains compatible.
- Apply relevant security context, service-account, network and admission policy.
  Do not weaken controls or expose a service solely to make an example work.

Read [worked patterns](references/details.md) for resource composition;
[Deployment fields](references/deployment-spec.md) or
[Service fields](references/service-spec.md) for the specific affected resource.
The [Deployment](assets/deployment-template.yaml),
[Service](assets/service-template.yaml) and
[ConfigMap](assets/configmap-template.yaml) assets are examples to adapt, not
ready-to-apply production configurations.

## Validate the claim being made

Use project-selected local syntax/schema checks first. Rendering or client-side
dry-run does not prove server admission, permissions, storage behavior, image
availability or rollout health. Server dry-run contacts a real API server and
needs the intended context/namespace and existing access authority.

Live commands require explicit target selection and task authorization. Prefer
bounded existing evidence before executing inside a workload or creating a debug
Pod. Such execution/creation is not read-only metadata inspection. Do not install
tools or fetch charts just because this guidance was loaded. Preserve failures and
missing target capability in the existing gate evidence.

Return a scoped manifest/design proposal, compatibility concerns, actual checks
and remaining uncertainty. The primary decides implementation and delivery;
loading this skill does not create commits, PRs, deployments or a new gate.

## Related guidance

Use installed `helm-chart-scaffolding` for actual chart work. Optional upstream
[GitOps](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/kubernetes-operations/skills/gitops-workflow)
and [security-policy](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/kubernetes-operations/skills/k8s-security-policies)
resources are not bundled dependencies or authority to change project workflow.
