# jf setup command semantics

Preserve the selected manager/runtime and native configuration owner. Inspect the
actual installed CLI's `jf setup --help`; supported managers/flags can change.
Do not install/upgrade the CLI or replace package managers as a prerequisite.

Review affected native configuration paths and retain private preimages. Resolve
one explicit server/repository and any required project key, validating values
as data with the reviewed `scripts/check-repo-key.sh`. Quote accepted outputs;
never interpolate raw task/cache text into executable shell source.

```bash
jf setup "<SELECTED_PACKAGE_MANAGER>" --server-id "$SID" --repo "$REPO"
```

Always use explicit selected `--server-id` and `--repo`; do not force the CLI's
global default or arbitrary repo discovery over the task's existing selection.
Maven/Gradle wrappers and `gradle` package-type ownership remain distinct. Preserve
actual Yarn/Poetry/uv/Podman selection instead of guessing from an incidental file.

| Observation | Outcome |
|---|---|
| Actual zero status and qualified resulting config | Record non-secret binding through its reviewed owner. |
| Nonzero status | Report bounded sanitized failure; do not update binding, continue another manager or mask status. |
| 401/403 | Authentication/authorization gap; native owner handles separately authorized recovery, no auto-login. |
| Missing repo/type/404 | Verify selected identity and actual evidence; do not iterate other servers or invent a repo. |

`jf setup` may overwrite native config and write credentials; configuration is
not a harmless read. Docker/Podman configuration does not rewrite image names;
use the selected Artifactory host/repository prefix. Actual resolution requires
its own authorized bounded verification; a successful config write alone is not
platform/package availability proof.
