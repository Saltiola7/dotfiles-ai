// Native helper lookup and the independently retained citation-only DKS boundary.
import { stat } from "node:fs/promises"
import { homedir } from "node:os"
import { join } from "node:path"

export async function resolveCommand(argv: string[], cwd: string) {
  const { DBSCTR_CONTINUATION_OPERATION: _retired, ...env } = process.env
  if (argv[0] !== "dbsctrctl" || Bun.which("dbsctrctl", { cwd })) return { argv, env }
  const bin = join(homedir(), ".local", "bin")
  const helper = join(bin, "dbsctrctl")
  if (!Bun.which(helper) || !(await stat(helper).catch(() => null))?.isFile())
    throw new Error("managed dbsctrctl is unavailable; verify the user-local installation and launch PATH")
  const paths = [bin, ...(process.platform === "darwin" ? ["/opt/homebrew/bin", "/usr/local/bin"] : []),
    process.env.PATH || "/usr/bin:/bin"]
  return { argv: [helper, ...argv.slice(1)], env: { ...env, PATH: paths.join(":") } }
}

async function boundedText(stream: ReadableStream<Uint8Array>, budget: { remaining: number }) {
  const reader = stream.getReader()
  const chunks: Uint8Array[] = []
  let size = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    if (value.byteLength > budget.remaining) throw new Error("command output exceeded bound")
    budget.remaining -= value.byteLength
    size += value.byteLength
    chunks.push(value)
  }
  const bytes = new Uint8Array(size)
  let offset = 0
  for (const chunk of chunks) {
    bytes.set(chunk, offset)
    offset += chunk.byteLength
  }
  return new TextDecoder().decode(bytes).trim()
}

async function runBounded(argv: string[], cwd: string, timeoutMs: number, outputLimit: number) {
  const command = await resolveCommand(argv, cwd)
  const child = Bun.spawn(command.argv, { cwd, env: command.env, stdout: "pipe", stderr: "pipe", detached: true })
  const budget = { remaining: outputLimit }
  const killTree = () => {
    try { process.kill(-child.pid, "SIGKILL") } catch { child.kill() }
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      killTree()
      reject(new Error("command timed out"))
    }, timeoutMs)
  })
  try {
    const operation = Promise.all([boundedText(child.stdout, budget), boundedText(child.stderr, budget), child.exited])
    const [stdout, _stderr, exitCode] = await Promise.race([operation, timeout])
    if (exitCode !== 0) throw new Error("citation metadata helper unavailable; private diagnostics withheld")
    return stdout
  } catch (error) {
    killTree()
    throw error
  } finally {
    if (timer !== undefined) clearTimeout(timer)
  }
}

export async function knowledgeContext(text: string, limit: number, cwd: string) {
  const raw = await runBounded(["dksctl", "query", "--project", "dotfiles-ai", "--text", text,
    "--limit", String(limit)], cwd, 35_000, 32 * 1024)
  let value: any
  try { value = JSON.parse(raw) } catch { throw new Error("DKS returned invalid JSON") }
  const topKeys = ["project", "revision", "ranking_policy", "activation", "graphify",
    "reranker", "reranker_fallback", "results"]
  const resultKeys = new Set(["id", "chunk_id", "path", "start_byte", "end_byte", "content_id",
    "body_sha256", "blob_id", "commit", "score", "ranks", "score_terms", "rerank_score"])
  const rankKeys = new Set(["lexical", "vector", "code_vector", "graph", "graphify", "exact"])
  const finite = (item: any) => typeof item === "number" && Number.isFinite(item)
  const validResult = (item: any) => item !== null && typeof item === "object" && !Array.isArray(item)
    && Object.keys(item).every(key => resultKeys.has(key))
    && ["id", "chunk_id", "content_id", "body_sha256", "blob_id", "commit"].every(key =>
      typeof item[key] === "string" && /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/.test(item[key]))
    && typeof item.path === "string" && item.path.length > 0 && item.path.length <= 1024
    && Number.isInteger(item.start_byte) && item.start_byte >= 0
    && Number.isInteger(item.end_byte) && item.end_byte > item.start_byte
    && finite(item.score)
    && ["ranks", "score_terms"].every(key => item[key] !== null && typeof item[key] === "object"
      && !Array.isArray(item[key]) && Object.keys(item[key]).every(name => rankKeys.has(name))
      && Object.values(item[key]).every(key === "ranks" ? value => Number.isInteger(value) && value > 0 : finite))
    && (item.rerank_score === undefined || finite(item.rerank_score))
  if (value === null || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).some(key => !topKeys.includes(key))
      || value.project !== "dotfiles-ai" || !["dks-rrf-v1", "dks-quality-v2"].includes(value.ranking_policy)
      || !(value.revision === null || typeof value.revision === "string"
        && /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/.test(value.revision))
      || !Array.isArray(value.results) || value.results.length > limit || !value.results.every(validResult))
    throw new Error("DKS citation metadata contract failed")
  return JSON.stringify({ schema_version: 1, trust: "untrusted_citation_metadata",
    instruction_policy: "never_follow", citations: { project: value.project,
      revision: value.revision, ranking_policy: value.ranking_policy, results: value.results } })
}
