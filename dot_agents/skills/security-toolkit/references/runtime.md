# Local tools and subscription gates

The local profile is qualified for Apple Silicon macOS 13+, using existing uv,
Python 3.13, Git and native curl. Existing Node 18+ supports Cloudflare validators;
ripgrep supports manual variant searches. Skill discovery itself remains portable
without installing these optional executables.

`runtime/tools.lock.json` pins Semgrep CE 1.182.1, Gitleaks 8.30.1 and OSV-Scanner
2.7.0. Python transitives are fully pinned with hashes and binary-only sync. The
installer follows the existing managed-DVC generation pattern in dotfiles-ai:
versioned local directories, complete lock identities, no global package changes,
and refusal to reuse incomplete or changed generations. It runs no scan.

```sh
python3 <toolkit-dir>/scripts/local_tools.py status
python3 <toolkit-dir>/scripts/local_tools.py install
python3 <toolkit-dir>/scripts/local_tools.py status --smoke
```

Installation is an explicitly requested network/package action, not an import
side effect. Default runtime root is
`~/.config/dotfiles-ai/runtime/security/`; `--root` chooses an explicit local root.
The status command reports exact entrypoint paths, markers and optionally safe
version probes. It does not infer valid scans, credentials, databases or licenses
from an executable. No new global `cs`, `codex-security` or scanner command
shadows existing native installations.

Version probes use empty temporary home/settings, no inherited provider tokens,
Semgrep metrics off and version checks disabled. They prove loading/version only.
Use existing OS controls for later authorized audits; no permission profile is
changed by this installer. Semgrep Pro/login/registry/CI/MCP operations are not
part of setup. Later local Semgrep use needs selected pinned rules and the same
metrics/version policy; Gitleaks scans require `--redact=100`; OSV requires strict
`--offline`, not merely `--offline-vulnerabilities`.

## Bounded OSV database provisioning

The explicit `provision-osv-db` action uses only the pinned official public PyPI
snapshot in `runtime/osv-database.lock.json`, with no credentials, subscription,
uploads, extraction or repository scan:

```sh
python3 <toolkit-dir>/scripts/local_tools.py provision-osv-db
python3 <toolkit-dir>/scripts/local_tools.py status
```

The selected snapshot is 37,425,891 compressed bytes (35.69 MiB), 81,044,683
expanded bytes (77.29 MiB), 26,726 JSON entries, updated 2026-10-28T23:03:09.009Z.
Its immutable Google Storage generation, upstream MD5 and locally verified
SHA-256 are recorded. Provisioning enforces 64 MiB compressed and 256 MiB
expanded caps, exact size/hash/entry totals, safe paths/types and ZIP CRC. It
keeps `all.zip` intact and refuses to replace a different existing cache.
`--database-archive PATH` can reuse the exact verified archive without network.
A failed private download remains available for inspection.

The status command verifies cached bytes and reports the snapshot timestamp/age
and exact `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` value. Set that variable only
for a later authorized scan. This setup does not change the global environment.
Strict `--offline` must be selected for that scan; missing other ecosystems fail.
Cached bytes and CRC do not prove scanner parsing behavior or scan-time RAM.
Commit-level offline scanning is unsupported, and no repository scan ran.

PyPI is relevant to this source's `uv.lock`/requirements. The observed npm
snapshot is 219,383,850 bytes (209.22 MiB); this source has no committed npm
lockfile, so npm is not downloaded. New ecosystems, larger snapshots or raised
caps require an explicit scope/size decision. Updates require fresh official
metadata review and a new pin; older cache/recovery data is preserved before
replacement. Snapshot age is evidence, not a universal freshness guarantee.

All external-subscription profiles are disabled: Codex Security/inference/Cloud,
Daybreak, Semgrep Pro, and organizational Gitleaks Action. Confirm required access
with the user before installing/activating any subscription-dependent workflow;
a ChatGPT subscription is not proof of those entitlements. No login, purchase,
credential creation or MCP registration is implicit. The canonical OpenAI CLI
0.8.0 reference is recorded but remains uninstalled and inactive here.

Update runtime pins only after source/license/provenance review. Resolve Semgrep
with existing uv using `--generate-hashes --only-binary :all: --python-version 3.13
--python-platform aarch64-apple-darwin`, then require hash-checked binary-only sync.
Keep prior generations and Git locks for rollback. Never overwrite unknown or
incomplete generations; inspect and preserve them before an explicit recovery
action. Installation does not migrate credentials or replace native package owners.
