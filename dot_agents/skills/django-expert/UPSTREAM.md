# Upstream and adaptation

This complete selected bundle derives from
[Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills/tree/078a25cc5bfd8011459be7b91d004e900c1d02d3/skills/django-expert)
at immutable commit `078a25cc5bfd8011459be7b91d004e900c1d02d3`,
path `skills/django-expert`, tree `aa8f42dbf2f8f5d12fdb32200494399a37b40197`.
The upstream entrypoint identifies version 1.1.0 and author Jeff Allan.
The exact repository MIT notice is retained as
[LICENSE.upstream](LICENSE.upstream), Git blob
`b77bf2ab726c6e7cb5a81a9d3b7dc38266ebfd3d`.

All seven selected original paths remain in this package: SKILL.md, the five
references below, and the license. Adapted instructions use normal automatic
discovery and on-demand references. The shared DBSCTR specialist source inventory
records the original blobs/modes, packaged hashes and reversible adaptation;
this document does not claim that current framework or database execution passed.

## Original SHA-256 identities

All original files have Git mode `100644`; their packaged modes remain 0644.
The license bytes are unchanged.

| Packaged path | Original SHA-256 |
|---|---|
| LICENSE.upstream | 06dcddbb6908a0c6dd4a9e8ec822eea41d5a460a53089fecccc8a68049e99241 |
| SKILL.md | 0107de33b8bfbf91ba64e09be529c9bf176883cfd89c534065eefba17cd631ae |
| references/authentication.md | 1c8cb67744898fadca804fb262e25bf0fc3ee4e094ff920b00ae0be9ee5925a8 |
| references/drf-serializers.md | 0642b28b45e28c367f3b897c565abc1a9dd743a67bc0330a9acbd1a3bf6ee5ff |
| references/models-orm.md | 82169cfe80c42aaa0a90d5ec0fc3813ba4c6e2db181eaa84562a53e4e9de17f9 |
| references/testing-django.md | ef2d0d2cb45d868131a47b3e8ac217630d32d1ce9852ee9d0f49fc2147f67084 |
| references/viewsets-views.md | 48ce90f17330f60b58a8f948cfcd7323f67dd446d0cc16cbce3c1313748574e7 |

## Reviewed adaptations

- Compact discovery/entrypoint; preserve project-selected Django/DRF, database,
  tests, user/authentication model and task authorization. Remove automatic
  migrations, JWT/tool adoption and authentication-after-exposure ordering.
- Preserve model relations through AUTH_USER_MODEL. Put chainable methods on a
  QuerySet and expose its manager correctly. Qualify indexes, lazy queries,
  bulk writes and model-validation/signal behavior.
- Retain owner checks for updates/custom writes when selecting permissions,
  explicitly identify the example's destroy policy and remove the unsafe
  missing-key equality permission. Avoid assumed user fields or blanket 401/403.
- Validate positive request quantities and replace read/decrement/save with a
  conditional database-side stock update; preserve object access and qualify
  the selected database, concurrency and larger transaction boundaries.
- Repair imports and remove assumed to_dict methods. Keep async work inside its
  selected framework/serving and sync/async transaction boundaries.
- Exclude the current instance from optional name checks; distinguish those
  checks from database uniqueness. Resolve cross-field partial updates against
  existing state. Replace incomplete generic nested writes with an explicit
  read representation and project-owned atomic write/ownership/price contract,
  avoiding invented order semantics.
- Keep owner, stock, line-price and total inputs under server authority. Test
  exact IntegrityError inside a recoverable atomic boundary, cross-owner denial,
  invalid quantity and selected partial/nested behavior. Separate forced
  authentication from actual credential tests.

The illustrative snippets depend on the project's actual models, app layout,
fixtures and service contracts; they do not form a runnable application.
No Django/DRF upgrade, SDK/tool installation, user-model replacement, migration,
database operation or new delivery coordinator is implied.

## Primary method references

Patterns were reviewed against Django 5.2 documentation for
[managers](https://docs.djangoproject.com/en/5.2/topics/db/managers/),
[transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/),
[database routing](https://docs.djangoproject.com/en/5.2/topics/db/multi-db/),
[QuerySets](https://docs.djangoproject.com/en/5.2/ref/models/querysets/),
[configured users](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
and [async support](https://docs.djangoproject.com/en/5.2/topics/async/), plus DRF
[permissions](https://www.django-rest-framework.org/api-guide/permissions/),
[authentication](https://www.django-rest-framework.org/api-guide/authentication/),
[serializers](https://www.django-rest-framework.org/api-guide/serializers/) and
[testing](https://www.django-rest-framework.org/api-guide/testing/).
These document versions verify the adaptation; they do not select or upgrade the
consumer project's runtime. Resolve the actual installed versions before use.
