# Agent entry point: port-to-free-threaded-python

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

Read [SKILL.md](SKILL.md) for an actual selected no-GIL compatibility task.
**Experimental porting workflow:** supported CPython runtime status does not make
these recipes fully qualified. Preserve project-selected versions and the existing
primary/QA/lifecycle ownership described in [project boundaries](GUARDRAILS.md).

Load only relevant detail: [background](reference/background.md),
[declarations](reference/declaring-support.md),
[thread safety](reference/thread-safety.md), or
[build and test](reference/build-and-test.md). No sibling skill is required.
Attribution, exact original identities and local adaptations are in
[UPSTREAM.md](UPSTREAM.md) and [LICENSE.upstream](LICENSE.upstream).
