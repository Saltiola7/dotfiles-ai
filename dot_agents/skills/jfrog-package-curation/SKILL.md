---
name: jfrog-package-curation
description: >-
  Check selected package versions against JFrog Curation or diagnose an actual
  Artifactory package-resolution/download block. Use for concrete JFrog package
  policy work; pure CVE lookup and generic package installation use other guidance.
metadata:
  role: workflow
---

# JFrog package Curation

Use the base [JFrog guards](../jfrog/SKILL.md) once for actual target, available
tools and current task authority. Do not install a CLI, connect MCP or change
authentication merely to load this workflow.

## Select one path

| Evidence | Read |
|---|---|
| Proactive policy check or authorized download of a selected package | [Check/download workflow](references/upstream-workflow.md#check--download) and the specific OneModel schema/query guidance it needs |
| Actual `ETARGET`, missing-version, `403`, Curation-policy or ineffective-waiver failure | [Historical RCA procedure](references/rca-procedure.md); its tool preflight is required |

Preserve the exact requested or locked version. Use a latest-version branch only
when latest is the requested selection; do not silently change a failing pin or
pick a different repository to bypass a policy block.

Repository/cache presence, current Curation allowance, available catalog security
signals and a completed project-required security assessment are separate facts.
A cached artifact is not thereby safe, compliant or approved. Apply the selected
project's policy/scan requirements even when a stored location is available.
Without Curation entitlement/capability, report the missing evaluation; do not
label an unassessed download as allowed or bypass a required gate.

The proactive CLI path and historical MCP audit path are distinct capabilities.
RCA requires actual registered `jfs_curation_*` tools on the failing tenant;
missing tools, denied access or an uncertain tenant are gaps. Do not invent a
CLI-equivalent historical audit, connect a different tenant or install MCP to make
this diagnosis appear complete. Live compliance checks/downloads can create audit
or cache records and are not interchangeable with reading historical failures.

Report package type/name/version, selected target/repository, observed evidence,
policy decision and remaining uncertainty. Recommend approved remediation without
silently changing policy, raising/approving waivers, reindexing or clearing caches.
Those mutations retain their existing task and policy owners. Full upstream
resources remain installed and lazy; no helper executes during skill deployment.
