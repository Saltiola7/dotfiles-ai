---
name: django-expert
description: Implement or review Django and DRF models, ORM queries, serializers, views, permissions, migrations and framework tests. Use for concrete Django behavior with project-selected versions and ownership.
license: MIT
metadata:
  author: https://github.com/Jeffallan
  upstream-version: "1.1.0"
---

<!-- Adapted by dotfiles-ai; see UPSTREAM.md for the immutable source and changes. -->
# Django and Django REST Framework

Use the existing project's Django/DRF versions, database, user model,
authentication, test tools and delivery process. Read its settings, model/service
contracts and selected dependencies before proposing changes; examples below are
illustrative fragments, not a runnable application or a framework upgrade.

Establish access and ownership rules before exposing or changing an endpoint.
Keep query scoping, object checks, writable fields and server-owned values
consistent. Authentication identifies a caller; it does not grant object access.

Load only the reference needed for the affected behavior:

| Concern | Reference |
|---|---|
| Models, chainable queries, query cost and bulk behavior | [Models and ORM](references/models-orm.md) |
| Fields, partial updates and nested write contracts | [DRF serializers](references/drf-serializers.md) |
| ViewSets, custom actions, stock concurrency and async boundaries | [Views](references/viewsets-views.md) |
| Selected authentication, permissions and account boundaries | [Authentication](references/authentication.md) |
| API, constraint, transaction and authentication tests | [Testing](references/testing-django.md) |

Distinguish migration authoring, plan review, local compatibility tests and
application to a selected environment. Loading this guidance does not authorize
database changes, dependency installation, JWT adoption, a user-model replacement
or a new CI workflow. Reuse already resolved task authority.

Validate changed behavior through the project's existing authorities. Cover
denied cross-owner writes, invalid input, partial/nested updates and concurrent
database behavior when affected. Measure queries before changing eager loading
or indexes. Keep framework/database test results separate from source inspection
and report unavailable environments without claiming integration success.

See [UPSTREAM.md](UPSTREAM.md) for attribution, corrections and reference versions.
