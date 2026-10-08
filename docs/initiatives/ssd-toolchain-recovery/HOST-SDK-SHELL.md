# Host SDK shell-selection slice

Delivered: dotfiles PR #18 merged at d5aa8ff72294ab3a3fb88a5f199317f08955b9d5.
Implementation 00a6f0d and deployment record 5163a5e passed affected tests and all
four host login-shell checks. Second targeted apply had no drift. Final Push
completed after separately approved delivery-helper repair; historical failures
remain in the Cycle Record.

Home: Saltiola7/dotfiles, host_tool_maintenance. Requirements: INT-003, INT-012,
INT-022. Independent prerequisite toward SDK duplicate retirement; bootstrap and
retirement remain in host-tools. No guest activation or package update belongs here.

Normative contract and committed profile live in the host repository under
docs/specs/host_tool_maintenance/{README.md,PROFILE.md}; applicability plan is
SDK-SHELL.plan.json in that directory. Prepared Discovery commit: 5ca9d03.
Build must verify those Git artifacts before launch. Risk elevated; draft PR into
main and targeted managed host deployment. Method revision 3.29.

Writable scope: dot_common_profile.tmpl, dot_zprofile.tmpl, affected terminal tests
and host_tool_maintenance documentation. Preserve the primary's dirty profile,
Brewfile and recovery hooks. Do not import or overwrite unrelated primary changes.

Observed failure: Bash login (both interactive and noninteractive) and Zsh
noninteractive login select Homebrew despite a healthy standalone SDK. Native Bash
SDK path helper skips reprioritization when its bin directory already exists later
in PATH. Interactive Zsh alone selects the intended SDK.

Acceptance: healthy standalone SDK wins in both login-shell modes, including
inherited later PATH entries; missing SDK preserves existing selection; repeated
initialization is stable; guarded AI launchers and external-state variables remain
correct. No cloud calls, installer, credentials or project-environment changes.

Qualification: isolated shell-resolution regression; existing terminal and AI
ownership tests; rendered Bash/Zsh syntax; targeted chezmoi preview/apply twice;
fresh host command-resolution checks. Preserve target preimages and newer user
edits. Kernel/review/deploy/operate/maintain required; release not applicable.

Readiness: no unresolved behavioral question for this slice. Implementation and
deployment evidence remain required Build gates, not claimed by Discovery.

## Visual Evidence

All concerns: not_applicable here; the owning host README contains the canonical
behavior transition table and Text Equivalent. This coordination record does not
duplicate that visual or define a new interface.
