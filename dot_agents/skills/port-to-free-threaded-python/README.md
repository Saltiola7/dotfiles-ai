# Free-threaded Python compatibility guidance

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

**Experimental porting workflow.** Use [SKILL.md](SKILL.md) for an actual selected
free-threaded target or compatibility assessment. Preserve supported runtimes,
binding versions and tooling. Runtime detection, native declarations and actual
thread safety are separate claims; none implies a measured workload speedup.

- [Project boundaries](GUARDRAILS.md): task authority and existing lifecycle owners.
- [Background](reference/background.md): CPython runtime versus ABI decisions.
- [Declarations](reference/declaring-support.md): native support markers.
- [Thread safety](reference/thread-safety.md): ownership and synchronization hazards.
- [Build and test](reference/build-and-test.md): artifacts and bounded evidence.
- [Provenance](UPSTREAM.md): immutable source and reversible adaptations.

Acknowledgments retained: Quansight and the free-threading community's porting
guides/pytest-run-parallel; CPython developers; Sam Gross (PEP 703); Petr Viktorin
and Nathan Goldbaum (PEP 803); Hugo van Kemenade's adoption tracking; NumPy,
SciPy and PyO3 teams. The optional upstream
[grounding list](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/reference-repos.md)
and [limited-API workflow](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/port-to-python-limited-api/SKILL.md)
are external sources; this bundle has no implicit sibling dependency.
