# Bounded independent readiness checks

Batch only independent, relevant read-only checks after their actual effects are
reviewed. Keep target/configuration identity fixed and retain individual exit
codes. Do not treat a batch's aggregate green as proof of each capability.

Do not run `jfrog-detect-all.mjs` as a harmless shortcut: it can write setup state
and invokes helpers with network/configuration effects. Likewise, broad MCP
resolution may write Kiro/Junie entries. Use the actual native owners and bounded
per-capability checks described in [the workflow](upstream-workflow.md).
Failed/unavailable checks remain visible. Do not loop, mask statuses, perform
repairs, log in or change global defaults merely to finish a walk.
