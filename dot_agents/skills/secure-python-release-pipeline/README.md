# Secure Python package release guidance

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

**Experimental:** adapted from Christian Heimes' consolidated release workflow,
which is a draft grounded in shipping projects and primary tooling documentation.
Use [SKILL.md](SKILL.md) when an actual GitHub Actions package release path is
selected. This bundle preserves build-from-sdist, built-artifact verification,
scoped PyPI Trusted Publishing and the distinction between signed origin and
functional correctness. It does not select a build backend or authorize publication.

- [Project boundaries](GUARDRAILS.md): tooling, task scope and lifecycle ownership.
- [Workflow examples](reference/templates.md): project-adapted release shapes.
- [Hardening rationale](reference/hardening.md): permissions and trust boundaries.
- [Provenance](UPSTREAM.md): original commit, complete resource set and adaptations.

Acknowledgments retained: Hynek Schlawack's build-and-inspect-python-package;
PyPA's gh-action-pypi-publish, cibuildwheel and Trusted Publishers; William
Woodruff/zizmorcore; OpenSSF Scorecard; Christian Heimes' zipwire, retread and
pycxxfilt release work. The upstream [grounding list](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/reference-repos.md)
is optional source context, not a required installed dependency.
