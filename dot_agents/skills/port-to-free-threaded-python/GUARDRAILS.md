# Project boundaries

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

The selected project and existing task own tooling, supported runtimes, build
backends, CI, accepted architecture, validation and delivery. Read applicable
project instructions and existing implementation first. For substantial ports,
check relevant upstream issues and pull requests before duplicating work.

Use the project's existing isolated environment and selected package manager.
The uv commands in these bundles are examples for a uv-selected workflow;
Poetry, pip/build and other established authorities remain valid. Loading a
skill does not install tools, recreate environments or raise the runtime floor.
Keep downloads and builds bounded by the task's existing resource authority;
resolve a genuinely missing resource or scope decision before proceeding.

Preserve unrelated and pre-existing changes. Use the current reviewable task
checkout and scoped diffs; a dirty tree alone does not invalidate authorization
for independent work. Existing user authorization persists. The primary workflow
owns commits, reviews and delivery; this technique adds no commit/stash prompt,
branch restriction or lifecycle coordinator.

Guidance, static review, local artifact builds, credential changes and external
publication have different effects. Execute only the effects covered by the
current task. A release review does not itself authorize uploading to PyPI,
pushing tags, editing a publisher or changing CI. Follow already authorized
operations without asking again; report actual gaps to the current primary.

Match project conventions. Keep private context, tokens and raw diagnostic data
out of public artifacts. Report checks actually run and their limits; a recipe,
example, syntax check or successful import is not broader qualification.
