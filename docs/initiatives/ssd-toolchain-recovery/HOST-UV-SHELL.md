# Host uv shell selection

Delivered: dotfiles PR #20 merged at 6750fc855fa5b4e7e5c9c4df50ce9135470f9e8c.
Implementation 22fe571 and deployment record 189f559 passed 40 scoped tests and
Python 3.12/3.13/3.14 CI. All four host login modes select installed uv 0.12.23
and uvx with minimal inherited PATH; unrelated command resolution matches each
mode's saved baseline. Repeated targeted apply is clean; preimages retained.

Home: Saltiola7/dotfiles, host_tool_maintenance. Engineering Profile:
docs/specs/host_tool_maintenance/PROFILE.md. Requirements INT-003, INT-006,
INT-012, INT-026 (bounded refinement of INT-004). Elevated risk; targeted managed deployment and draft PR into
main. Guest work stays deferred. No package or project-environment upgrade.

## Evidence and boundary

Fresh Bash noninteractive login selects local uv 0.8.15; interactive Bash selects
mise-owned uv 0.12.23. Bash sources common configuration before its interactive-only
return, but activates mise after that return. Zsh login currently inherits the
new uv path; that result does not establish clean-environment initialization.
The active external mise store contains uv 0.12.23 and 0.12.3. The existing global
mise configuration selects 0.12.23 and is not owned by this chezmoi source.
Keep that operator configuration unchanged. Local uv/uvx binaries remain retained.

Whole-mise shim activation could change Python, Node and protected project runtime
selection. This slice therefore changes only uv/uvx selection, respecting the
existing mise selection and requiring an already-installed executable. Do not
evaluate mise environment output or run installers at shell startup.

## Contract

Scope is the mac-mini machine role. Share the small portable selection fragment
through the repository's native template mechanism if both common and Zsh login
profiles need it. Preserve SDK selection, AI launch guards and credential behavior.

| Given | When shell initializes | Required outcome |
|---|---|---|
| External-state marker, mise and installed selected uv/uvx | Bash/Zsh login starts, interactive or not | Selected mise uv/uvx wins over retained local copies |
| PATH without inherited mise entries | Same startup | Same selected uv/uvx; do not rely on parent activation |
| Different installed uv selected by existing mise configuration | New shell starts | Follow selection without a version hardcode or config rewrite |
| Missing marker, mise, selected executable, or failed lookup | Startup | No installation, authentication or fabricated path; retain existing selection |
| Existing Python/Node/AI guards/SDK path | uv selection changes | Do not alter their resolution through broad runtime activation |
| Repeat initialization or HOME containing spaces | Startup | Stable effective selection and correctly quoted paths |
| Other machine role | Templates render | Existing behavior unchanged |

Set the external mise data root only when its existing external-state marker is
present. Promote the already-deployed MISE_DATA_DIR source hunk into tracked source
as part of this slice; remove an exactly matching inherited variable when the marker
is absent rather than introducing a missing-volume local state store. No deletion
or migration of local tools, no rewrite of project pins, no new PATH directory
containing unrelated tool shims. A bare non-login shell inherits its caller; no
BASH_ENV or new global Zsh hooks.

Writable scope: dot_common_profile.tmpl, dot_zprofile.tmpl, one optional shared
chezmoi template, focused shell tests and context completion docs. Preserve all
other dirty primary changes. Serialization with native runtime migration remains
required; that slice has not entered Build.

## Validation and delivery

Use isolated shell fixtures with fake mise and uv/uvx to cover clean/inherited PATH,
failed lookup, missing tools/marker, repeat startup, quoted paths and unchanged
sentinel Python/Node/AI commands. Render both supported shell profiles, syntax-check
them, and run affected terminal, SDK-selection and AI-ownership tests. No test
contacts cloud services or executes protected project tasks.

Review targeted chezmoi diff; retain source/target preimages; apply only the changed
shell profiles. Check all four host login modes and repeat apply. Compare unrelated
tool resolution before/after in each mode rather than requiring every shell to
select one Python. Preserve newer user edits on rollback. Kernel, review, deploy,
operate and maintain/retire gates required; package release not applicable.

Readiness: no unresolved scope or behavior decision. Build must still establish
regression and host evidence; installed uv version alone is not shell qualification.

## Visual Evidence

State: required; canonical transition table above. Boundary, interaction, data/trust,
schema, dependency/deployment and quantitative: not_applicable; this is bounded
shell selection without new data transport, topology, schema or performance claims.

**Text Equivalent:** select only installed mise uv/uvx when external state is
available; otherwise retain current behavior without provisioning. Leave unrelated
runtime resolution intact. Canonical source: this table. Owner: dotfiles maintainer;
update when shell scope, tool ownership or fallback policy changes.
