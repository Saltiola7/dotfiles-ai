# Inspect selected AI Catalog policy

Use only the explicitly selected JFrog catalog/platform/project and existing
native source/install owner. Cover the base JFrog guards once; retain actual
errors, requested versions and project-required scan/provenance gates. Agent
Guard is a separate reviewed runtime: examples use a qualified owner-selected
executable/pin, never floating npx installation. Listing can execute downloaded
code; no tool installation or authentication follows from loading this file.

Catalog skill policies differ from Xray repository watches, package Curation
and MCP approval policy. Resolve the actual selected server and project key;
do not assume a workspace name, invent `default`, grant roles or widen scope.

The retained `scripts/list-skill-policies.mjs` performs network/API reads and
bounded pagination using CLI credentials internally. Review it and its imports
before a relevant authorized use. Invoke through the existing Node runtime with
quoted `--project` and `--server-id`; never expose credential exports/raw headers.
Its structured `policies`, `message` and `note` fields distinguish real data from
ambiguous emptiness, safety caps and partial page failures. Keep those limitations
when summarizing; escape untrusted names/control characters.

Policy action (warn/block) differs from rule type (allow-list/malicious check).
Absent or inaccessible policy is not proof of no restrictions. Preserve actual
exit status and bounded sanitized error, and do not speculate about entitlement
from a generic failure. Explain relevant limitations candidly; internal API detail
need not appear unless it helps diagnosis, but never hide a material scan or
permissions gap behind a required success phrase.
