# Install or update a selected catalog skill

Use only the explicitly selected JFrog catalog/platform/project and existing
native source/install owner. Cover the base JFrog guards once; retain actual
errors, requested versions and project-required scan/provenance gates. Agent
Guard is a separate reviewed runtime: examples use a qualified owner-selected
executable/pin, never floating npx installation. Listing can execute downloaded
code; no tool installation or authentication follows from loading this file.

Resolve the exact slug, requested version and repository from explicit task
selection or verified scoped catalog evidence. A mutable latest alias is used
only when actually selected and must resolve to concrete bytes/version before
claiming provenance. Do not silently widen to another project/repository or
create a repo to make installation succeed.

Check root `SKILL.md`, complete resources, license/provenance and the target's
existing same-name owner. Native CLI install/update is appropriate only when that
CLI owns the selected installation. For dotfiles-ai managed skills, adapt source,
review the complete bundle and deploy exact files through that owner instead.
Retain preimages and native explicit/implicit invocation policy.

When native JFrog CLI owns the target, inspect its actual supported help and pass
explicit `--repo`, `--version` and `--server-id` for `jf skills install/update` as
appropriate. Update does not itself establish the original repository identity;
resolve it rather than guessing. Preserve true exit status and bounded output.
Verify installed file set/bytes and native discovery separately after execution.

## Evidence verification failure

Missing signed evidence is an unmet provenance control, not proof of a safe skill.
Do not set `JFROG_SKILLS_DISABLE_QUIET_FAILURE=true` merely because installation
fails or an ordinary install request was authorized. Preserve project-required
attestation/signature/scan gates. An actual exception requires that project's
explicit qualified exception process and still cannot bypass immutable controls.
Report what evidence is absent and the selected owner's recovery path.

## Blocked or pending download

A 403 can indicate access denial or Xray gating; do not infer one cause from the
HTTP status alone. For a concrete selected skill/archive and authorized diagnostic,
inspect supported status at
`/artifactory/api/skills/<repo>/xrayStatus?path=<encoded-archive-path>` with the
selected server, preserving actual response and escaping path data. Pending scan,
blocked/malicious verdict, absent evidence, inaccessible resource and transport
failure are separate states. Do not retry tightly, skip scans, switch targets,
delete/re-publish or override attestation to obtain success. A partial local install
is not ready until its actual files, policy and discovery are qualified.
