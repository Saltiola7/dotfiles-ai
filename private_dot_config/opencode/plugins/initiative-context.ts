import type { Plugin } from "@opencode-ai/plugin"

async function initiativeContext(worktree: string) {
  const manifests = [...new Bun.Glob("docs/initiatives/*/MANIFEST.json").scanSync({ cwd: worktree })]
    .sort()
  if (manifests.length === 0) return undefined
  if (manifests.length > 16) return `## Durable Initiative Authority
Found ${manifests.length} Initiative manifests; the bounded context limit is 16. Readiness and launch are blocked until the active Initiative is selected explicitly.`
  const anchors: string[] = []
  for (const manifest of manifests) {
    const child = Bun.spawn(["dbsctrctl", "initiative-check", "--manifest", manifest, "--json"], {
      cwd: worktree, stdout: "pipe", stderr: "ignore",
    })
    const [stdout, exitCode] = await Promise.all([new Response(child.stdout).text(), child.exited])
    if (exitCode !== 0) {
      anchors.push(`- manifest: ${manifest}\n  status: invalid; readiness and launch are blocked`)
      continue
    }
    try {
      const value = JSON.parse(stdout)
      if (typeof value.initiative_id !== "string" || !/^[0-9a-f]{64}$/.test(value.manifest_digest)
          || !Array.isArray(value.ready_slices) || value.ready_slices.some((item: unknown) => typeof item !== "string"))
        throw new Error("invalid summary")
      anchors.push(`- manifest: ${manifest}\n  initiative: ${value.initiative_id}\n  digest: ${value.manifest_digest}\n  ready_slices: ${value.ready_slices.join(", ") || "none"}`)
    } catch {
      anchors.push(`- manifest: ${manifest}\n  status: invalid; readiness and launch are blocked`)
    }
  }
  return `## Durable Initiative Authority
Re-read and validate these Git artifacts before planning, editing, readiness, or launch. Do not rely on compressed prose alone.
${anchors.join("\n")}
Issue a fresh digest-bound handoff with \`dbsctrctl initiative-receipt --manifest PATH --slice ID --json\` immediately before any launch.`
}

export const InitiativeContext: Plugin = async ({ worktree }) => ({
  "experimental.chat.system.transform": async (_input, output) => {
    const context = await initiativeContext(worktree)
    if (context !== undefined) output.system.push(context)
  },
  "experimental.session.compacting": async (_input, output) => {
    const context = await initiativeContext(worktree)
    if (context !== undefined) output.context.push(context)
  },
})
