# Project selection and verification branches

| Evidence | Outcome |
|---|---|
| Known selected server/project key | Reuse it for the current task; do not ask again. |
| Server ambiguous | Resolve server identity first through [server selection](server-picker.md). |
| Project missing and required by requested operation | Ask for the actual key; do not invent `default` or a platform-wide mode. |
| User supplies a project key | Record selection only; existence and privileges remain unverified until a relevant authorized operation proves them. |
| Project list fails with 403 | Enumeration unavailable; do not claim missing project or silently grant roles. |
| Credential or transport failure | Report the actual bounded failure; do not retry against another server. |
| Optional catalog/project feature irrelevant to requested artifact operation | Leave it untested; do not block independent work or claim a pass. |

Some retained upstream helpers accept typed input without validation. Their green
result is not platform verification. Matching/caching mechanics are described in
[project matching](project-matching.md); use actual selected-version behavior.
