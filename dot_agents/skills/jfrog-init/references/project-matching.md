# Project selection and matching evidence

Use [resolution branches](project-resolution-branches.md) and the skill's helper
execution boundary. These legacy helpers are not automatic readiness probes;
credential-bearing exports must not reach output or public evidence.

## Current detector behavior

`jfrog-detect-project.mjs` has two different branches:

- With a typed project key, it accepts that selection and returns `resolvedKey`
  without matching, existence or access checks. A green selection result is not
  proof that the project exists or that the identity has permission.
- Without input, it enumerates accessible projects using
  `GET /access/api/v1/projects` ([GetProjectsList](https://docs.jfrog.com/projects/reference/getprojectslist))
  through the selected identity. Enumeration may require privileges unavailable
  to an otherwise valid project user; a 403 does not establish project absence.

Enumeration stays live whenever requested. The compatibility cache always misses
and retains neither credential-derived fingerprints nor project metadata. Legacy
cache files are ignored. API failures retain their existing error behavior; no
credential, server or project switch follows from a failed enumeration.

The retained implementation resolves credentials internally and fetches Access
rather than the Artifactory root. Review that version and its effects before use;
prefer the existing qualified native owner where appropriate. Selection,
configuration, authenticated access and a successful relevant operation remain
separate observations. Verify authorization through the actual requested operation.

## Supporting matching utilities

[The project library](../scripts/lib/projects.mjs) retains local utilities for
project normalization, display capping, matching and suggestions. Its resolver
tries exact case-insensitive key, exact display name, separator-stripped exact
match, unique literal substring and unique separator-stripped substring, in order.
Ambiguous local matches need disambiguation; punctuation is not compiled into a
user-supplied regular expression. These utility results do not prove live access.
The current detector's typed-input branch does not call this matching resolver.
