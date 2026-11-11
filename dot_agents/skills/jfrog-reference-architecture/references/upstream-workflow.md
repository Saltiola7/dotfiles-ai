# Local scope for the retained workflow

The active [skill](../SKILL.md) governs this complete retained planning workflow. Preserve the selected host, Podman, Kubernetes or other deployment target. Read only relevant current official pages; a full reference dump and a Kubernetes migration are not prerequisites. These instructions do not authorize infrastructure changes. Skill-root-relative backtick paths still refer to the enclosing skill root.

# JFrog Reference Architecture

Planning skill for topology, sizing, and deployment. Answers must come from
**live fetches** of the [JFrog Platform Reference Architecture](https://jfrog.com/reference-architecture/) — not from training data or duplicated tables in this repo.

## Prerequisites

- Read `../../jfrog/SKILL.md` only if actual platform operations also need its
  target/tool guards. Planning alone uses this reference and current official docs.
- **No `jf` CLI required** for planning-only questions (no live instance needed).

## Source of truth

| Allowed in this skill | Not allowed |
|-----------------------|-------------|
| Fetch procedures, workflows, output templates | Sizing RPM tables, use-case narratives, deployment checklists copied from the site |
| Selected-target deployment workflow (Helm when Kubernetes is chosen) | Hardcoded slug lists, criteria or an imposed runtime migration |

**Every factual claim** (numbers, template names, limitations, infrastructure guidance) must come from a **`WebFetch` in the current session**. If a fetch fails, use an available documented public alternative or report the
evidence gap. Respect native permissions; do not loop or guess from memory.

**Citations:** Use the `URL:` line from the relevant section in the fetched content (public HTML URL). You may note content was read from `llms-full.txt`.

For fetch URLs, size thresholds, and the fallback ladder, see [references/doc-access.md](../references/doc-access.md).

## Gotchas

| Symptom | Mitigation |
|---------|------------|
| Sizing numbers or use-case names not on the official site | `WebFetch` ref-arch first; cite `URL:` from the fetch — not training data |
| `small` template recommended for production | Re-read production warnings in the fetched Artifactory/Xray sizing sections |
| SaaS section missing or 404 | SaaS paths use prefix **`jfrog-saas`**, not `saas` |
| HA storage guidance wrong | Per ref arch: **`cluster-file-system`** or object storage — not `file-system` for HA |
| Documentation blocked, truncated, or over size limits | Respect native access; fetch a targeted page if available, or report the gap per [references/doc-access.md](../references/doc-access.md) |

## Session bootstrap

Before answering a reference-architecture question:

1. Resolve the specific planning question and selected hosting/runtime from task evidence.
2. Fetch the relevant official page; use `llms.txt` or the sitemap only when the
   page is not already known. See [documentation access](doc-access.md).
3. Retain only relevant bounded content for follow-ups. Use `llms-full.txt` only
   when an actual broad/cross-site question requires it and limits permit.
4. Refresh the affected page when source freshness becomes uncertain. Failed
   access is an evidence gap, not permission to change runtime security settings.

### Parsing llms-full.txt

Sections are separated by `---` and typically include:

- `# <Title>`
- `URL: https://jfrog.com/reference-architecture/...`
- Optional `> <summary>`
- Body text (may be condensed vs the HTML page)

Use only text from the fetch. For recommendations, cite the section’s `URL:` line.

## Intent routing

| User intent | Where to look in llms-full | Fallback |
|-------------|---------------------------|----------|
| Sizing | `# Sizing`, `# AWS Sizing`, Azure, GCP sections | `.../self-managed/deployment/sizing/index.md` |
| Topology / use case | Matching title + `URL:` for SaaS (`jfrog-saas`) or self-managed | That path’s `index.md` |
| List use cases | All `URL:` lines containing `/use-cases/` | `sitemap.xml` |
| Deployment / install | Deployment and considerations sections | `.../deployment/index.md` |
| Disaster recovery | DR playbook / tiers sections | Matching `index.md` |

SaaS paths use prefix **`jfrog-saas`**, not `saas`.

## Workflow: Sizing

1. Fetch the official sizing page for the selected hosting/product/version; do
   not bootstrap unrelated reference sections.
2. Find the **Sizing** section. Build follow-up questions from **Artifactory Sizing Templates Criteria** in the fetch (peak **Requests Per Minute** and **Concurrent Connections** per template).
3. Use **`AskQuestion`** when available; otherwise numbered options using labels from the fetched table only.
4. If the user mentions Xray or production, use **Xray Sizing Templates Criteria** and production warnings from the same fetch (e.g. small is not for production).
5. If the user names a cloud, use **AWS Sizing** / **Azure** / **GCP** sections from the fetch.
6. Recommend a template (`small` through `2xlarge`) and cite the sizing page `URL:` from the relevant fetched pages.
7. **Helm (when selected):** Verify the current [jfrog-platform](https://github.com/jfrog/charts/tree/master/stable/jfrog-platform) chart, matching product/version and sizing values before proposing exact commands. For a different runtime, use its supported official deployment guidance instead.

### Sizing output template

```markdown
## Recommended sizing

- **Template**: <from fetched table>
- **Artifactory**: <RPM and concurrent connections from fetched table>
- **Xray** (if applicable): <from fetched Xray table>
- **Source**: <URL: line from Sizing section>
- **Selected runtime**: <existing supported hosting/deployment target; Helm values only when Kubernetes is chosen>
- **Caveats**: <Notes / additional factors from fetched Sizing section>
```

## Workflow: Topology and use cases

1. Fetch the official pages relevant to the selected hosting model and question.
2. Ask **1–2 follow-ups per turn** until hosting model and site count are clear:
   - SaaS vs self-managed (if unsure, fetch home/overview from the relevant fetched pages and mention SaaS value proposition from site text).
   - Single site vs multi site.
   - For multi-site: DR/failover, geo performance, CI/CD separation, edges, hybrid variants, IoT, subsidiaries/vendors, air-gapped (self-managed only), archiving.
3. **List documented use cases:** For a requested broad listing, use the official
   sitemap or index and group applicable **JFrog SaaS**/**Self-managed** pages.
   Do not fetch every use case for a narrow single-topology question.
4. **Recommend a use case:** Match the user’s answers to sections in the relevant fetched pages; cite each `URL:`. If the dump is insufficient for one page, `WebFetch` `https://jfrog.com/reference-architecture/<path>/index.md` for that `URL:` path.
5. **No exact match:** Suggest combining documented patterns (e.g. active-passive for DR + main-site-with-edges); fetch each component section before describing how they combine. Remind that the ref arch is a starting point for emerging cases.

## Workflow: Deployment

1. Fetch the official pages relevant to the selected hosting model and question.
2. Use deployment, considerations, HA, database, storage, and cloud sections from the fetch.
3. **Selected-target policy:** Preserve the chosen SaaS/self-managed and runtime
   route. Verify official support for its exact version/platform; do not migrate
   a host or Podman requirement to Kubernetes by default. When Kubernetes is
   selected, verify the current appropriate chart and product values from official
   documentation before proposing installation.
4. Production reminders from fetched content where applicable: external managed PostgreSQL (not bundled chart DB for production), object storage / `cluster-file-system` for HA, Enterprise license for `replicaCount > 1`.
5. `WebFetch` the [chart README](https://github.com/jfrog/charts/tree/master/stable/jfrog-platform) when the user needs install snippets, OpenShift (`openshift-values.yaml` last), or RabbitMQ quorum files.

### Deployment output template

```markdown
## Deployment recommendation

- **Runtime**: <selected supported runtime and version; no automatic migration>
- **Reference**: <URL: from deployment-related sections>
- **Key considerations**: <bullets from fetched considerations sections>
- **Helm** (if requested): <commands from chart README fetch>
```

## When to read reference files

- **Fetch ladder, Markdown URL rule, size governance:** [references/doc-access.md](../references/doc-access.md)

## Examples

**Sizing:** User asks what sizing to set for Artifactory → fetch relevant official sizing/topology pages → ask peak RPM using fetched table options → recommend supported template and selected-runtime configuration.

**List use cases:** User asks for all documented use cases → fetch relevant official sizing/topology pages → list grouped by SaaS vs self-managed from `URL:` lines in dump.

**Topology:** User needs DR across two regions → clarify SaaS vs self-managed → recommend active-passive (or related) section from the relevant fetched pages with `URL:` citations.

**Deploy:** User wants Artifactory on EKS → deployment + AWS sizing sections from the relevant fetched pages → jfrog-platform chart with external DB and sizing values file.
