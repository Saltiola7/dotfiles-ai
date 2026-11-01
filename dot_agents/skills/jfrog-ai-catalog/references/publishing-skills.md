# Publish a selected skill artifact

Use only the explicitly selected JFrog catalog/platform/project and existing
native source/install owner. Cover the base JFrog guards once; retain actual
errors, requested versions and project-required scan/provenance gates. Agent
Guard is a separate reviewed runtime: examples use a qualified owner-selected
executable/pin, never floating npx installation. Listing can execute downloaded
code; no tool installation or authentication follows from loading this file.

## Resolve the concrete release

Reuse existing explicit publication authority for the selected exact artifact and
destination; resolve only material ambiguity. Identify root `SKILL.md`, complete
resource closure, license, source revision, intended slug/version, selected server
and explicit repository. A project key is not a repository key. Do not provision
a repository, widen to server-wide discovery or select another project's repo as
a fallback. Repository creation is a separately concrete authorized operation.

Review publication lifecycle, required security scanning, signature/attestation,
compatibility and rollback before writing. Preserve the selected release version;
do not invent a patch version or mutable latest selection. Use the selected CLI's
actual `jf skills publish --help` to verify supported flags. The ordinary shape is:

```bash
jf skills publish "<reviewed-bundle-path>" \
  --server-id "<SID>" --repo "<REPOSITORY>" --version "<SELECTED_VERSION>"
```

Only add supported noninteractive flags when the concrete write is already
authorized; do not turn native prompts into a new blanket permission ceremony.
Secrets/signing keys remain with the existing credential owner. An explicit
signing-key path/alias and inherited signing variables have different precedence;
inspect configured identity without printing the private key, generating/trusting
a replacement or silently clearing inherited signing policy. Signing is not scan
success. Do not expose key material in commands, logs or public artifacts.

## Preserve scanning and release gates

Do not pass `--skip-scan` or set `JFROG_CLI_SKIP_SKILLS_SCAN=true` by default.
Indexing delays can make a synchronous result pending/unavailable; they do not
prove the artifact clean or authorize bypass. If project policy selects asynchronous
scanning, retain that explicit contract and qualify the required final result
before release approval. Upload, indexing, policy, scan verdict and publication
approval are distinct states. Report actual missing/pending/failed evidence.

A version conflict does not authorize deletion/overwrite or another version.
Use the existing approved release policy or resolve that concrete choice; retain
the original failure and selected destination. Destructive cleanup, automatic
post-failure deletion and another publish are separate material operations.

## Report and recover

Report exact observed artifact/version/repository plus upload and applicable scan/
attestation status. Never suppress Xray/indexing limitations behind an unconditional
success template. A scan may fail after upload, so do not claim the artifact was
removed. If authorized, use the selected native storage/status operation to verify
actual residual state before any owner-approved recovery. Preserve bounded sanitized
errors and stop on auth/permission/target failure without switching servers.
