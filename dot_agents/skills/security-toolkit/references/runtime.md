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

OSV databases are not installed. Select ecosystem databases separately, document
their age and exact identity, and populate the documented offline cache before
claiming scan readiness. Missing databases or commit-level offline limitations
remain gaps. No database bootstrap or scan is performed in this setup.

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
