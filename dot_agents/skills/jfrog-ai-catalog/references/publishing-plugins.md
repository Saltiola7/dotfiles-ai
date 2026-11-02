# Publish a selected plugin artifact

Use only the explicitly selected JFrog catalog/platform/project and existing
native source/install owner. Cover the base JFrog guards once; retain actual
errors, requested versions and project-required scan/provenance gates. Agent
Guard is a separate reviewed runtime: examples use a qualified owner-selected
executable/pin, never floating npx installation. Listing can execute downloaded
code; no tool installation or authentication follows from loading this file.

Reuse concrete existing publication authority. Resolve root `plugin.json`, the
complete reviewed bundle, license/source provenance, intended slug/version,
selected platform and explicit target repository. Do not auto-provision a repo,
widen to another project/server or invent a version to make publication possible.
Repository creation and overwrite/deletion need their own concrete scoped action.

Review actual plugin hooks/runtime/configuration effects, compatibility, required
scans/signatures/attestations and lifecycle release controls. Use the selected
CLI's supported `jf agent plugins publish --help`; explicit version overrides the
manifest only when selected. Ordinary native-owner shape:

```bash
jf agent plugins publish "<reviewed-plugin-path>" \
  --server-id "<SID>" --repo "<REPOSITORY>"
```

Signing belongs to the existing credential owner. Retain required signer identity
and explicit/inherited key precedence; never expose a private key, create/trust a
replacement, silently clear policy or equate a signature with malware scanning.
A noninteractive flag follows concrete existing write authority, not a blanket
new repeated-confirmation requirement.

Preserve project scan/provenance gates. Uploaded, indexed, scanned, approved and
available to clients are separate facts. Report pending/failed/absent evidence
and actual residual uploads, including partial failure. Do not remove a conflicting
version, retry elsewhere, bypass evidence or generate an unsigned substitute as
automatic recovery. Use actual authorized native-owner status/cleanup operations
with private preimages and bounded sanitized errors.
