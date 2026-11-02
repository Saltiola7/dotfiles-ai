# Reference architecture documentation access

Fetch relevant current official content during the task; do not copy upstream
page bodies into this repository or load the whole manual for a narrow question.
Use available web tooling and actual native permissions. Failed access is an
evidence gap, not permission to bypass a denial or change runtime configuration.

## Targeted access first

| Need | Source and selection |
|---|---|
| Known topic/page | The relevant public page under https://jfrog.com/reference-architecture/; fetch its content directly |
| Topic navigation or Markdown URL pattern | https://jfrog.com/reference-architecture/llms.txt |
| Individual Markdown section | `https://jfrog.com/reference-architecture/<path>/index.md`; use the actual known page path |
| Broad documented-use-case inventory | https://jfrog.com/reference-architecture/sitemap.xml |
| Actual cross-domain/full-site comparison | https://jfrog.com/reference-architecture/llms-full.txt only when needed and within tool/context limits |
| Markdown unavailable | Fetch the corresponding public HTML page rather than guessing another deployment target |

The base path is `https://jfrog.com/reference-architecture/`. Known SaaS paths
use `jfrog-saas`, but resolve current URLs from the official index/sitemap rather
than constructing a speculative catalog of slugs.

## Scope and size

Retain only task-relevant page content for follow-ups. A truncated response does
not establish full-source coverage; fetch the required sections separately and
report any unverified claim. A large response is not a reason to load megabytes
of unrelated reference material. Refresh affected sources when version/support
or freshness uncertainty matters.

If a full dump is actually used, sections can contain `# <Title>` and
`URL: https://jfrog.com/reference-architecture/...`, separated by `---`. Cite the
specific public HTML URL supporting the claim rather than the dump URL alone.

## Runtime and chart details

Preserve the selected hosting/runtime; verify official support for its version.
For a selected Kubernetes route, current chart instructions are at
https://github.com/jfrog/charts/tree/master/stable/jfrog-platform . Fetch its
matching README and values before proposing exact install commands. Planning
never executes those commands or provisions a platform.
