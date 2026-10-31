---
name: helm-chart-scaffolding
description: Design and validate Helm chart templates, values and packaging for a project-selected Kubernetes target. Use for actual chart changes; distinguish local rendering from cluster acceptance and deployment.
---

# Helm Chart Design

Preserve the project's Helm version, dependency and lock authority, supported
Kubernetes versions, release identity, namespaces and deployment workflow. Resolve
existing facts before asking about a material missing decision. The current
primary owns lifecycle, authorization and delivery.

## Work at the chart boundary

- Separate chart version from application/image identity. Follow the existing
  version and provenance policy instead of changing pins to match an example.
- Keep values and helper templates understandable; quote rendered values for the
  Kubernetes field type. Test intended overrides and meaningful empty values.
- Preserve selectors, names, upgrade compatibility and state ownership. Hooks and
  chart tests can execute workloads, migrations or destructive operations.
- Support the actual chart type. A valid library chart need not have values.yaml,
  runnable workloads or the same files as an application chart.
- Keep credentials outside ordinary values and rendered evidence. Use the
  project's existing secret references or operator; never deploy sample passwords.
- Treat resource sizing, probes, ingress and security context as workload/policy
  decisions. A global string match is not evidence for every rendered resource.

Read [chart patterns](references/details.md) for templates, values and hooks, or
[chart structure](references/chart-structure.md) for packaging fields. The
[Chart metadata](assets/Chart.yaml.template) and
[values](assets/values.yaml.template) assets are illustrative inputs, not a
production deployment or provider selection.

## Local validation

Use the project's configured rendering and linting commands. The bundled helper:

```bash
bash scripts/validate-chart.sh "/path/to/chart"
```

checks Chart.yaml, runs `helm lint` and `helm template` locally, and preserves the
failing command's exit status. It accepts a chart path containing spaces. It does
not fetch/build dependencies, install a chart, contact a cluster intentionally or
prove server admission and rollout health. Missing Helm is a capability gap; the
helper does not install it. Review chart inputs and the helper before execution.

For library charts, use `bash scripts/validate-chart.sh --lint-only "/path/to/chart"`.
Helm cannot directly render a library chart as an application. Linting alone leaves
helper behavior unverified: render the project-selected consumer chart or fixture
that includes the library and exercises its named templates.

Dependency updates/builds can access registries and rewrite chart state. Perform
those only within selected dependency work. Preserve locks and report missing
artifacts rather than resolving them incidentally during validation.

Server-side validation, `lookup` behavior, hooks, installation and chart tests
need separate applicable target evidence and existing task authorization. Use
explicit cluster/context, release and namespace when live work is in scope.
Avoid `--debug` output containing rendered Secrets. Do not introduce another
repository/PR/deployment coordinator or ask again for authorization already given.

Return template/value decisions, actual local results, compatibility concerns and
required target checks to the primary and QA. A rendered chart is not a deployed
or healthy application.

Use installed `k8s-manifest-generator` for base resources when helpful. Optional
upstream [GitOps guidance](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/kubernetes-operations/skills/gitops-workflow)
is not an installed dependency or a new workflow requirement.
