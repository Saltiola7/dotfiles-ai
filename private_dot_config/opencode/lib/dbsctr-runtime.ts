import { readFile, realpath } from "node:fs/promises"
import { createHash } from "node:crypto"
import { homedir } from "node:os"
import { join } from "node:path"

const harnessActivation = {
  schema_version: 1,
  core_revision: "3.29",
  overlays: { build: "neutral-2026-07-26", "build-gpt": "openai-2026-07-26", "build-claude": "anthropic-2026-07-26" },
}

const evaluationPages = new Map<string, { source_id: string, capture_id: string, pages: Map<number, any> }>()
const evaluationReceipts = new Map<string, any>()

function discardEvaluationReceipt(manifestDigest: string) {
  const receipt = evaluationReceipts.get(manifestDigest)
  if (receipt !== undefined) for (const source of receipt.sources)
    evaluationPages.delete(`${source.source_id}\0${source.capture_id}`)
  evaluationReceipts.delete(manifestDigest)
}

function trimEvaluationPages() {
  const retained = new Set<string>()
  for (const receipt of evaluationReceipts.values()) for (const source of receipt.sources)
    retained.add(`${source.source_id}\0${source.capture_id}`)
  let pageCount = [...evaluationPages.values()].reduce((total, capture) => total + capture.pages.size, 0)
  while (evaluationPages.size > 64 || pageCount > 256) {
    let key: string | undefined
    for (const candidate of evaluationPages.keys()) if (!retained.has(candidate)) {
      key = candidate
      break
    }
    if (key === undefined) break
    pageCount -= evaluationPages.get(key)?.pages.size ?? 0
    evaluationPages.delete(key)
  }
}

function localizeCandidate(value: any, source: string): any {
  if (Array.isArray(value)) return value.map(item => localizeCandidate(item, source))
  if (value === null || typeof value !== "object") return value
  const result: Record<string, any> = {}
  for (const [key, item] of Object.entries(value)) {
    if (["session_id", "cycle_id", "parent_session_id"].includes(key) && typeof item === "string"
        && item.startsWith(`${source}:`)) result[key] = item.slice(source.length + 1)
    else result[key] = localizeCandidate(item, source)
  }
  return result
}

function canonicalJSON(value: any): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJSON).join(",")}]`
  if (value !== null && typeof value === "object")
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`).join(",")}}`
  return JSON.stringify(value)
}

function sha256(value: any) {
  return createHash("sha256").update(canonicalJSON(value)).digest("hex")
}

async function federatedSourceOrder(env: NodeJS.ProcessEnv) {
  const path = env.OPENCODE_VM_CONFIG ?? join(homedir(), ".config", "dotfiles-ai", "sandbox.json")
  let config: any
  try {
    config = JSON.parse(await readFile(path, "utf8"))
  } catch {
    throw new Error("sandbox configuration is unavailable")
  }
  const workspaces = config?.workspaces
  const id = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
  if (!Array.isArray(workspaces) || workspaces.length > 32
      || workspaces.some((workspace: any) => workspace === null || typeof workspace !== "object"
        || !id.test(workspace.name) || workspace.name === "host" || typeof workspace.federate !== "boolean"))
    throw new Error("sandbox configuration is invalid")
  const sources = ["host", ...workspaces.filter((workspace: any) => workspace.federate)
    .map((workspace: any) => workspace.name)]
  if (new Set(sources).size !== sources.length) throw new Error("sandbox configuration is invalid")
  return sources
}

function federatedManifestIdentity(filters: any, sources: any[]) {
  return { filters, sources: sources.map(source => {
    const identity: Record<string, any> = { source_id: source.source_id, availability: source.availability }
    if (source.availability === "available") for (const name of [
      "capture_id", "snapshot", "session_ceiling", "part_ceiling", "database_digest", "exclusion_digest",
      "limit", "cursor", "continuation", "digest",
    ]) identity[name] = source.page[name]
    return identity
  }) }
}

export async function run(argv: string[], cwd: string) {
  const child = Bun.spawn(argv, { cwd, stdout: "pipe", stderr: "pipe" })
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
    child.exited,
  ])
  if (exitCode !== 0) throw new Error(stderr.trim() || `${argv[0]} exited ${exitCode}`)
  return stdout.trim()
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

async function runBounded(argv: string[], cwd: string, timeoutMs: number | null = 2000, outputLimit = 64 * 1024) {
  const child = Bun.spawn(argv, { cwd, stdout: "pipe", stderr: "pipe", detached: true })
  const budget = { remaining: outputLimit }
  const killTree = () => {
    try {
      process.kill(-child.pid, "SIGKILL")
    } catch {
      child.kill()
    }
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = timeoutMs === null ? null : new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      killTree()
      reject(new Error("command timed out"))
    }, timeoutMs)
  })
  try {
    const operation = Promise.all([
      boundedText(child.stdout, budget),
      boundedText(child.stderr, budget),
      child.exited,
    ])
    const [stdout, stderr, exitCode] = await (timeout === null ? operation : Promise.race([operation, timeout]))
    if (exitCode !== 0) throw new Error(stderr || `${argv[0]} failed`)
    return stdout
  } catch (error) {
    killTree()
    throw error
  } finally {
    if (timer !== undefined) clearTimeout(timer)
  }
}

async function runBoundedInput(argv: string[], input: string, cwd: string, timeoutMs = 30_000) {
  const child = Bun.spawn(argv, { cwd, stdin: "pipe", stdout: "pipe", stderr: "pipe", detached: true })
  child.stdin.write(input)
  child.stdin.end()
  const budget = { remaining: 256 * 1024 }
  const timer = setTimeout(() => {
    try { process.kill(-child.pid, "SIGKILL") } catch { child.kill() }
  }, timeoutMs)
  try {
    const [stdout, stderr, exitCode] = await Promise.all([
      boundedText(child.stdout, budget), boundedText(child.stderr, budget), child.exited,
    ])
    if (exitCode !== 0) throw new Error(stderr || `${argv[0]} failed`)
    return stdout
  } finally {
    clearTimeout(timer)
  }
}

export async function cycleStatus(cwd: string) {
  return await run(["dbsctrctl", "status", "--json"], cwd)
}

export async function attachRuntime(cwd: string, runtime: {
  sessionID: string
  messageID: string
  directory: string
  worktree: string
}) {
  return await run([
    "dbsctrctl", "attach-runtime",
    "--opencode-session-id", runtime.sessionID,
    "--opencode-message-id", runtime.messageID,
    "--opencode-directory", runtime.directory,
    "--opencode-worktree", runtime.worktree,
    "--harness-activation-json", JSON.stringify(harnessActivation),
  ], cwd)
}

export async function phaseSpan(args: {
  spanID: string
  event: "start" | "finish"
  parentSpanID?: string
  phase?: "domain" | "behavior" | "spec" | "contract" | "test_driven_implementation" | "refactor" | "operation"
  operation?: "marker" | "typed_tool" | "task" | "read" | "readonly_qa"
  dependencies?: string[]
  ownershipPaths?: string[]
  attribution?: "explicit" | "adapter" | "unavailable"
  result?: "passed" | "failed" | "blocked" | "abandoned" | "unavailable"
}, cwd = process.cwd()) {
  const argv = ["dbsctrctl", "phase-span", "--span-id", args.spanID, "--event", args.event]
  const values: [string, string | undefined][] = [
    ["parent-span-id", args.parentSpanID], ["phase", args.phase], ["operation", args.operation],
    ["attribution", args.attribution], ["result", args.result],
  ]
  for (const [name, value] of values) if (value !== undefined) argv.push(`--${name}`, value)
  for (const dependency of args.dependencies ?? []) argv.push("--dependency", dependency)
  for (const path of args.ownershipPaths ?? []) argv.push("--path", path)
  return await run(argv, cwd)
}

export async function validateExecutionDag(nodes: {
  id: string
  depends_on: string[]
  operation: "read" | "readonly_qa" | "reconcile"
  ownership_paths: string[]
}[], completed: string[], mode: "serial" | "benchmark" | "concurrent", cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "execution-dag", "--mode", mode, "--dag-json", JSON.stringify({ nodes, completed }),
  ], cwd)
}

export async function recordExecutionBenchmark(fixture: {
  id: string; commit: string; path: string; blob: string
}, cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "execution-benchmark",
    "--fixture-id", fixture.id, "--fixture-commit", fixture.commit,
    "--fixture-path", fixture.path, "--fixture-blob", fixture.blob,
  ], cwd)
}

export async function runtimeHealth(cwd: string, runtime: {
  sessionID: string
  worktree: string
}, env = process.env) {
  if (env.HERDR_ENV !== "1") return { status: "unavailable" as const }
  let output: string
  try {
    output = await runBounded(["herdr", "pane", "current"], cwd)
  } catch {
    return { status: "unavailable" as const }
  }
  let value: any
  try {
    value = JSON.parse(output)
  } catch {
    return { status: "ambiguous" as const }
  }
  const pane = value?.result?.pane
  if (pane === null) return { status: "missing" as const }
  const id = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
  const agentStatus = ["idle", "working", "blocked", "unknown"].includes(pane?.agent_status)
    ? pane.agent_status
    : "unknown"
  const panePath = typeof pane?.foreground_cwd === "string" ? pane.foreground_cwd : pane?.cwd
  let canonicalPane: string | null = null
  let canonicalWorktree: string | null = null
  try {
    [canonicalPane, canonicalWorktree] = await Promise.all([realpath(panePath), realpath(runtime.worktree)])
  } catch {
    // Missing paths are ambiguous rather than evidence about lifecycle state.
  }
  if (pane?.agent !== "opencode" || pane?.agent_session?.value !== runtime.sessionID
      || canonicalPane === null || canonicalPane !== canonicalWorktree
      || ![pane?.pane_id, pane?.tab_id, pane?.workspace_id, pane?.terminal_id].every(
        value => typeof value === "string" && id.test(value))) {
    return { status: "ambiguous" as const }
  }
  return {
    status: "healthy" as const,
    agent_status: agentStatus,
    pane_id: pane.pane_id,
    tab_id: pane.tab_id,
    workspace_id: pane.workspace_id,
    terminal_id: pane.terminal_id,
  }
}

export async function lifecycleAudit(cwd: string, commit = "HEAD") {
  return await run(["dbsctrctl", "audit", "--commit", commit, "--json"], cwd)
}

export async function fixedCommitInspect(args: {
  action: "read" | "tree" | "search" | "object"
  commit?: string
  path?: string
  query?: string
  limit?: number
  offset?: number
  cursor?: number
  excerpt?: number
}, cwd: string) {
  const argv = ["dbsctrctl", "inspect", "--commit", args.commit ?? "HEAD", "--action", args.action]
  for (const [name, value] of Object.entries(args)) {
    if (name !== "action" && name !== "commit" && value !== undefined) argv.push(`--${name}`, String(value))
  }
  argv.push("--json")
  return await run(argv, cwd)
}

export async function reviewScan(limit = 25, cursor = 0, snapshot?: number, cwd = process.cwd(), sessionCeiling?: number, partCeiling?: number, databaseDigest?: string, excludedSessionID?: string, excludedMessageID?: string, exclusionDigest?: string) {
  const argv = ["dbsctrctl", "review-scan", "--limit", String(limit), "--cursor", String(cursor)]
  if (snapshot !== undefined) argv.push("--snapshot", String(snapshot))
  if (sessionCeiling !== undefined) argv.push("--session-ceiling", String(sessionCeiling))
  if (partCeiling !== undefined) argv.push("--part-ceiling", String(partCeiling))
  if (databaseDigest !== undefined) argv.push("--database-digest", databaseDigest)
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  if (excludedMessageID !== undefined) argv.push("--excluded-message-id", excludedMessageID)
  if (exclusionDigest !== undefined) argv.push("--exclusion-digest", exclusionDigest)
  return await run(argv, cwd)
}

export async function reviewComplete(report: {
  session_ids: string[]
  cycle_ids: string[]
  scan_digest: string
    snapshot: number
    session_ceiling: number
    part_ceiling: number
    database_digest: string
    exclusion_digest?: string
  limit: number
  cursor: number
  decision: string
  notes?: string
  findings: string[]
  scorecards: string[]
  trends: string[]
  proposals: string[]
  caveats: string[]
}, cwd = process.cwd(), excludedSessionID?: string, excludedMessageID?: string) {
  return await run([
    "dbsctrctl", "review-complete", "--report-json", JSON.stringify(report),
    "--scan-digest", report.scan_digest,
    ...(excludedSessionID === undefined ? [] : ["--excluded-session-id", excludedSessionID]),
    ...(excludedMessageID === undefined ? [] : ["--excluded-message-id", excludedMessageID]),
  ], cwd)
}

export async function reviewHistory(args: {
  after?: number
  before?: number
  methodRevision?: string
  cycleId?: string
  state?: "active" | "blocked" | "abandoned" | "completed" | "unknown"
  context?: string
  projectDigest?: string
  reviewedStatus?: "reviewed" | "unreviewed"
  replay?: string
  archiveOnly?: boolean
  snapshot?: number
  sessionCeiling?: number
  partCeiling?: number
  databaseDigest?: string
  exclusionDigest?: string
  limit?: number
  cursor?: number
}, cwd = process.cwd(), excludedSessionID?: string, excludedMessageID?: string) {
  return await run(reviewHistoryArgv(args, excludedSessionID, excludedMessageID), cwd)
}

function validFederatedPage(page: any, limit: number, cursor: number) {
  const pageKeys = ["schema_version", "capture_id", "snapshot", "session_ceiling", "part_ceiling", "database_digest",
    "exclusion_digest", "limit", "cursor", "continuation", "candidates", "digest", "query", "session_ids"]
  const candidateKeys = ["schema_version", "session_id", "snapshot", "session_ceiling", "part_ceiling",
    "database_digest", "project_digest", "context", "completed_at", "reviewed_status", "correlation_quality",
    "cycles", "aggregates", "telemetry", "method_revision"]
  const currentCandidateKeys = [...candidateKeys, "review_session"]
  const aggregateKeys = ["approval_count", "candidate_count", "child_count", "cost_total", "cycle_abandoned_count",
    "cycle_active_count", "cycle_blocked_count", "cycle_completed_count", "cycle_count", "cycle_unknown_count",
    "elapsed_ms", "retry_count", "token_total", "tool_call_count", "tool_count", "tool_error_count"]
  const legacyTelemetryKeys = ["approval_count", "attribution_status", "availability", "cost_total", "delegation_count",
    "error_classes", "model_families", "retry_count", "token_total"]
  const telemetryKeys = [...legacyTelemetryKeys, "schema_version", "provider_ids", "model_ids", "agent_ids",
    "session_relation", "core_revisions", "overlay_revisions", "gate_failure_count", "gate_reopen_count",
    "remediation_round_count"]
  const availabilityKeys = telemetryKeys.filter(key => !["availability", "attribution_status", "schema_version"].includes(key))
  const legacyAvailabilityKeys = legacyTelemetryKeys.filter(key => !["availability", "attribution_status"].includes(key))
  const queryKeys = ["after", "archive_only", "before", "context", "cycle_id", "method_revision", "project_digest",
    "reviewed_status", "state"]
  const digest = /^[0-9a-f]{64}$/
  const id = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
  const unsafe = /(?:https?:\/\/|file:\/\/|"\/|\/(?:Users|home|root|tmp|private|var\/folders)\/|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?:password|secret|api[_-]?key|access[_-]?token|bearer)\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY-----)/i
  const nonnegative = (value: any) => typeof value === "number" && Number.isFinite(value) && value >= 0
  const nonnegativeInteger = (value: any) => Number.isInteger(value) && value >= 0
  const unavailable = (value: any) => value === "unavailable" || nonnegative(value)
  return exactKeys(page, pageKeys) && page.schema_version === 1 && /^[0-9a-f]{24}$/.test(page.capture_id)
    && page.limit === limit
    && !unsafe.test(JSON.stringify(page)) && nonnegativeInteger(page.snapshot) && nonnegativeInteger(page.session_ceiling)
    && nonnegativeInteger(page.part_ceiling) && page.cursor === cursor
    && (page.continuation === null || Number.isInteger(page.continuation) && page.continuation > cursor)
    && digest.test(page.database_digest)
    && digest.test(page.digest) && (page.exclusion_digest === null || digest.test(page.exclusion_digest))
    && Array.isArray(page.session_ids) && page.session_ids.every((value: any) => typeof value === "string" && id.test(value))
    && Array.isArray(page.candidates) && page.candidates.length <= limit && exactKeys(page.query, queryKeys)
    && typeof page.query.archive_only === "boolean"
    && [page.query.after, page.query.before].every((value: any) => value === null || Number.isInteger(value) && value >= 0)
    && [page.query.context, page.query.cycle_id].every((value: any) => value === null || typeof value === "string" && id.test(value))
    && (page.query.method_revision === null || typeof page.query.method_revision === "string" && /^\d+(?:\.\d+)*$/.test(page.query.method_revision))
    && (page.query.project_digest === null || typeof page.query.project_digest === "string" && digest.test(page.query.project_digest))
    && [null, "reviewed", "unreviewed"].includes(page.query.reviewed_status)
    && [null, "active", "blocked", "abandoned", "completed", "unknown"].includes(page.query.state)
    && page.candidates.every((candidate: any) => {
      const currentTelemetry = exactKeys(candidate?.telemetry, telemetryKeys)
      const legacyTelemetry = exactKeys(candidate?.telemetry, legacyTelemetryKeys)
      const expectedAvailability = currentTelemetry ? availabilityKeys : legacyAvailabilityKeys
      return (exactKeys(candidate, candidateKeys) || exactKeys(candidate, currentCandidateKeys))
      && (candidate.review_session === undefined || typeof candidate.review_session === "boolean")
      && exactKeys(candidate.aggregates, aggregateKeys) && (currentTelemetry || legacyTelemetry)
      && (!currentTelemetry || candidate.telemetry.schema_version === 2)
      && exactKeys(candidate.telemetry.availability, expectedAvailability) && Array.isArray(candidate.cycles)
      && candidate.schema_version === 1 && id.test(candidate.session_id) && nonnegativeInteger(candidate.snapshot)
      && nonnegativeInteger(candidate.session_ceiling) && nonnegativeInteger(candidate.part_ceiling)
      && digest.test(candidate.database_digest) && digest.test(candidate.project_digest) && id.test(candidate.context)
      && (candidate.completed_at === null || typeof candidate.completed_at === "string"
        && /^(?:\d{10,16}|\d{4}-\d{2}-\d{2}T\S{1,40}Z)$/.test(candidate.completed_at))
      && ["reviewed", "unreviewed"].includes(candidate.reviewed_status)
      && ["exact", "family", "worktree", "source", "ambiguous", "unavailable"].includes(candidate.correlation_quality)
      && typeof candidate.method_revision === "string" && /^(?:\d+(?:\.\d+)*|unavailable)$/.test(candidate.method_revision)
      && Object.entries(candidate.aggregates).every(([key, value]) => value === "unavailable"
        || (key === "cost_total" ? nonnegative(value) : nonnegativeInteger(value)))
      && [candidate.telemetry.approval_count, candidate.telemetry.retry_count, candidate.telemetry.delegation_count,
        candidate.telemetry.token_total].every(value => value === "unavailable" || nonnegativeInteger(value))
      && unavailable(candidate.telemetry.cost_total)
      && (candidate.telemetry.model_families === "unavailable" || Array.isArray(candidate.telemetry.model_families)
        && candidate.telemetry.model_families.every((value: any) => typeof value === "string" && id.test(value)))
      && (candidate.telemetry.error_classes === "unavailable"
        || candidate.telemetry.error_classes !== null && typeof candidate.telemetry.error_classes === "object"
        && !Array.isArray(candidate.telemetry.error_classes)
        && Object.entries(candidate.telemetry.error_classes).every(([key, value]) => id.test(key) && nonnegativeInteger(value)))
      && ["exact", "family", "worktree", "source", "ambiguous", "unavailable"].includes(candidate.telemetry.attribution_status)
      && Object.values(candidate.telemetry.availability).every(value => ["available", "unavailable"].includes(value as string))
      && (!currentTelemetry || ["primary", "child", "unavailable"].includes(candidate.telemetry.session_relation)
        && ["provider_ids", "model_ids", "agent_ids", "core_revisions", "overlay_revisions"].every(name =>
          candidate.telemetry[name] === "unavailable" || Array.isArray(candidate.telemetry[name])
          && candidate.telemetry[name].length > 0 && candidate.telemetry[name].every((value: any) => typeof value === "string" && id.test(value)))
        && ["gate_failure_count", "gate_reopen_count", "remediation_round_count"].every(name =>
          candidate.telemetry[name] === "unavailable" || nonnegativeInteger(candidate.telemetry[name])))
      && candidate.cycles.every((cycle: any) => {
        if (cycle === null || typeof cycle !== "object" || Array.isArray(cycle)
            || Object.keys(cycle).some(key => !["cycle_id", "state", "risk", "delivery_intent", "phase_profile", "metrics", "harness_activation"].includes(key))
            || !id.test(cycle.cycle_id) || !["active", "blocked", "abandoned", "completed", "unknown"].includes(cycle.state)
            || !["routine", "elevated", "critical", "unavailable"].includes(cycle.risk ?? "unavailable")
            || !["local", "merge", "release", "deploy", "draft_pr", "unavailable"].includes(cycle.delivery_intent ?? "unavailable")) return false
        const phaseValid = cycle.phase_profile === undefined || cycle.phase_profile === null
          || exactKeys(cycle.phase_profile, ["schema_version", "cycle_id", "status",
            "critical_path_ms", "total_wall_ms", "overlap_ms", "repeated_work", "principal_waits", "attribution_caveats"])
            && cycle.phase_profile.schema_version === 1 && cycle.phase_profile.cycle_id === cycle.cycle_id
            && ["complete", "unavailable"].includes(cycle.phase_profile.status)
            && [cycle.phase_profile.critical_path_ms, cycle.phase_profile.total_wall_ms, cycle.phase_profile.overlap_ms]
              .every(value => value === "unavailable" || nonnegativeInteger(value))
            && nonnegativeInteger(cycle.phase_profile.repeated_work) && Array.isArray(cycle.phase_profile.principal_waits)
            && cycle.phase_profile.principal_waits.every((wait: any) => exactKeys(wait, ["span_id", "wait_ms"])
              && id.test(wait.span_id) && nonnegativeInteger(wait.wait_ms))
            && Array.isArray(cycle.phase_profile.attribution_caveats)
            && cycle.phase_profile.attribution_caveats.every((value: any) => typeof value === "string" && id.test(value))
        const metricsValid = cycle.metrics === undefined || exactKeys(cycle.metrics,
          ["elapsed_ms", "gate_failure_count", "gate_reopen_count", "remediation_round_count"])
          && (cycle.metrics.elapsed_ms === "unavailable" || nonnegativeInteger(cycle.metrics.elapsed_ms))
          && ["gate_failure_count", "gate_reopen_count", "remediation_round_count"].every(name => nonnegativeInteger(cycle.metrics[name]))
        const activationValid = cycle.harness_activation === undefined || exactKeys(cycle.harness_activation,
          ["schema_version", "provider_id", "model_id", "agent_id", "core_revision", "overlay_revision"])
          && cycle.harness_activation.schema_version === 1
          && ["provider_id", "model_id", "agent_id", "core_revision", "overlay_revision"].every(name =>
            typeof cycle.harness_activation[name] === "string" && id.test(cycle.harness_activation[name]))
        return phaseValid && metricsValid && activationValid
      })
    })
}

export async function reviewFederated(args: {
  after?: number
  before?: number
  methodRevision?: string
  cycleId?: string
  state?: "active" | "blocked" | "abandoned" | "completed" | "unknown"
  context?: string
  projectDigest?: string
  reviewedStatus?: "reviewed" | "unreviewed"
  archiveOnly?: boolean
  reviewSessions?: "only" | "exclude"
  limit?: number
  cursor?: number
  sourceState?: {
  source_id: string
  capture_id: string
  snapshot: number
  session_ceiling: number
  part_ceiling: number
  database_digest: string
  exclusion_digest: string | null
  query_digest: string
  continuation: number | null
  }[]
} = {}, cwd = process.cwd(), excludedSessionID?: string, excludedMessageID?: string, env = process.env) {
  const { limit = 25, cursor = 0, sourceState, reviewSessions, ...requested } = args
  const opaqueID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
  if ([excludedSessionID, excludedMessageID].some(value => value !== undefined && !opaqueID.test(value)))
    throw new Error("invalid excluded history identity")
  const query = {
    after: requested.after ?? null,
    archive_only: requested.archiveOnly ?? false,
    before: requested.before ?? null,
    context: requested.context ?? null,
    cycle_id: requested.cycleId ?? null,
    method_revision: requested.methodRevision ?? null,
    project_digest: requested.projectDigest ?? null,
    reviewed_status: requested.reviewedStatus ?? null,
    state: requested.state ?? null,
  }
  const argv = ["sandbox-vm", "review", "--limit", String(limit), "--cursor", String(cursor)]
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  if (excludedMessageID !== undefined) argv.push("--excluded-message-id", excludedMessageID)
  if (sourceState !== undefined) argv.push("--source-state-json", JSON.stringify(sourceState))
  const names: Record<string, string> = { methodRevision: "method-revision", cycleId: "cycle-id",
    projectDigest: "project-digest", reviewedStatus: "reviewed-status", archiveOnly: "archive-only" }
  for (const [name, value] of Object.entries(requested)) {
    if (value === true) argv.push(`--${names[name] ?? name}`)
    else if (value !== undefined && value !== false) argv.push(`--${names[name] ?? name}`, String(value))
  }
  const [value, expectedSources] = await Promise.all([
    analyticsJSON(argv, cwd, null), federatedSourceOrder(env),
  ])
  const sourceID = (value: any) => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)
  const validState = (state: any) => exactKeys(state, ["source_id", "capture_id", "snapshot", "session_ceiling", "part_ceiling",
    "database_digest", "exclusion_digest", "query_digest", "continuation"])
    && sourceID(state.source_id)
    && /^[0-9a-f]{24}$/.test(state.capture_id)
    && [state.snapshot, state.session_ceiling, state.part_ceiling].every((item: any) => Number.isInteger(item) && item >= 0)
    && /^[0-9a-f]{64}$/.test(state.database_digest)
    && (state.exclusion_digest === null || /^[0-9a-f]{64}$/.test(state.exclusion_digest))
    && state.query_digest === sha256(query)
    && (state.continuation === null || Number.isInteger(state.continuation) && state.continuation >= 0)
  if (!exactKeys(value, ["schema_version", "sources", "source_state", "manifest_digest"])
      || value.schema_version !== 2 || !/^[0-9a-f]{64}$/.test(value.manifest_digest)
      || !Array.isArray(value.sources) || value.sources.length < 1 || value.sources.length > 33
      || canonicalJSON(value.sources.map((source: any) => source?.source_id)) !== canonicalJSON(expectedSources)
      || new Set(value.sources.map((source: any) => source?.source_id)).size !== value.sources.length
      || value.source_state !== null && (!Array.isArray(value.source_state) || value.source_state.length !== value.sources.length
        || new Set(value.source_state.map((state: any) => state?.source_id)).size !== value.sources.length
        || value.source_state.some((state: any) => !validState(state)))
      || value.sources.some((source: any) => source === null || typeof source !== "object"
        || !sourceID(source.source_id)
        || !["available", "complete", "missing_instance", "invalid_output", "state_restore_failed"].includes(source.availability)
        || !exactKeys(source, source.availability === "available" ? ["source_id", "availability", "page"] : ["source_id", "availability"])
        || source.availability === "available" && !validFederatedPage(source.page, limit,
          sourceState?.find(state => state.source_id === source.source_id)?.continuation ?? cursor)
        || source.availability === "available" && sourceState !== undefined
          && source.page.capture_id !== sourceState.find(state => state.source_id === source.source_id)?.capture_id
        || source.availability === "available" && canonicalJSON(source.page.query) !== canonicalJSON(query))
      || value.manifest_digest !== sha256(federatedManifestIdentity(query, value.sources))
      || value.source_state !== null && value.source_state.some((state: any) => {
        const source = value.sources.find((item: any) => item.source_id === state.source_id)
        const expected = source?.availability === "available" ? {
          source_id: source.source_id, capture_id: source.page.capture_id,
          snapshot: source.page.snapshot, session_ceiling: source.page.session_ceiling,
          part_ceiling: source.page.part_ceiling, database_digest: source.page.database_digest,
          exclusion_digest: source.page.exclusion_digest, query_digest: sha256(query), continuation: source.page.continuation,
        } : source?.availability === "complete"
          ? sourceState?.find(item => item.source_id === state.source_id && item.continuation === null)
          : undefined
        if (expected === undefined) return true
        return canonicalJSON(state) !== canonicalJSON(expected)
      })) {
    throw new Error("sandbox helper returned an invalid federation manifest")
  }
  for (const source of value.sources) if (source.availability === "available") {
    const key = `${source.source_id}\0${source.page.capture_id}`
    const captured = evaluationPages.get(key) ?? {
      source_id: source.source_id, capture_id: source.page.capture_id, pages: new Map<number, any>(),
    }
    const page = localizeCandidate(source.page, source.source_id)
    page.session_ids = source.page.session_ids.map((sessionID: string) =>
      sessionID.startsWith(`${source.source_id}:`) ? sessionID.slice(source.source_id.length + 1) : sessionID)
    page.member_digests = page.candidates.map((candidate: any) => sha256(candidate))
    captured.pages.set(source.page.cursor, page)
    evaluationPages.set(key, captured)
    trimEvaluationPages()
  }
  if (value.source_state === null && value.sources.some((source: any) => source.availability === "available")
      && value.sources.every((source: any) => ["available", "complete"].includes(source.availability))) {
    const privacy = await analyticsJSON(["sandbox-vm", "privacy-epochs"], cwd, null)
    if (!exactKeys(privacy, ["schema_version", "sources"]) || privacy.schema_version !== 1
        || !Array.isArray(privacy.sources)
        || canonicalJSON(privacy.sources.map((source: any) => source?.source_id)) !== canonicalJSON(expectedSources)
        || privacy.sources.some((source: any) => !exactKeys(source,
          source?.availability === "available" ? ["source_id", "availability", "privacy_epoch_digest"] : ["source_id", "availability"])
          || source.availability !== "available" || !/^[0-9a-f]{64}$/.test(source.privacy_epoch_digest)))
      throw new Error("sandbox helper returned invalid privacy epochs")
    const receiptSources = expectedSources.map(sourceID => {
      const page = value.sources.find((source: any) => source.source_id === sourceID)?.page
      const state = sourceState?.find(source => source.source_id === sourceID)
      const captureID = page?.capture_id ?? state?.capture_id
      const captured = evaluationPages.get(`${sourceID}\0${captureID}`)
      if (captured === undefined) throw new Error("federated capture receipt is incomplete")
      return { source_id: sourceID, capture_id: captureID,
        privacy_epoch_digest: privacy.sources.find((source: any) => source.source_id === sourceID).privacy_epoch_digest,
        pages: [...captured.pages.values()].sort((left, right) => left.cursor - right.cursor) }
    })
    const receipt = {
      schema_version: 1, manifest_digest: value.manifest_digest,
      manifest_identity: federatedManifestIdentity(query, value.sources), sources: receiptSources,
    }
    if (new TextEncoder().encode(JSON.stringify(receipt)).byteLength > 2 * 1024 * 1024) {
      for (const source of receiptSources) evaluationPages.delete(`${source.source_id}\0${source.capture_id}`)
      throw new Error("terminal federated capture receipt exceeds bound")
    }
    evaluationReceipts.set(value.manifest_digest, receipt)
    for (const source of receiptSources) evaluationPages.delete(`${source.source_id}\0${source.capture_id}`)
    while (evaluationReceipts.size > 8)
      discardEvaluationReceipt(evaluationReceipts.keys().next().value as string)
  }
  if (reviewSessions !== undefined) for (const source of value.sources) {
    if (source.availability !== "available") continue
    const candidates = source.page.candidates
    const selected = candidates.filter((candidate: any) => reviewSessions === "only"
      ? candidate.review_session === true : candidate.review_session === false)
    source.page.candidates = selected
    source.page.session_ids = selected.map((candidate: any) => candidate.session_id)
    source.page.filter_telemetry = {
      selected_session_count: selected.length,
      selected_review_session_count: selected.filter((candidate: any) => candidate.review_session === true).length,
      excluded_review_session_count: reviewSessions === "exclude"
        ? candidates.filter((candidate: any) => candidate.review_session === true).length : 0,
      unattributed_session_count: candidates.filter((candidate: any) => candidate.review_session === undefined).length,
    }
  }
  return JSON.stringify(value)
}

export async function vmHandoff(report: {
  schema_version: 1
  worker_id: string
  proceed: true
  target: string
  risk: "routine" | "elevated" | "critical"
  summary: string
  paths: string[]
  validation: string[]
}, cwd = process.cwd()) {
  const serialized = JSON.stringify(report)
  const unsafe = /(?:https?:\/\/|file:\/\/|\/(?:Users|home|root|tmp|private|var\/folders)\/|(?:^|\/)\.\.(?:\/|$)|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\b(?:gh[pousr]_|AKIA)[A-Za-z0-9_=-]{16,}|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|\bBearer\s+\S+|\b(?:authorization|password|secret|token|api[_-]?key|access[_-]?token)\s*[:=]\s*\S+)/i
  const safePath = /^(?!\/)(?!.*(?:^|\/)\.{1,2}(?:\/|$))(?!.*\/\/)(?!.*[\\\x00-\x1F\x7F])[^/]+(?:\/[^/]+)*$/
  if (unsafe.test(serialized) || report.paths.some(path => !safePath.test(path))) throw new Error("unsafe VM handoff")
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(report.target)) throw new Error("invalid handoff workspace")
  const instance = await runBounded(["sandbox-vm", "instance", report.target], cwd, 2_000, 1024)
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(instance)) throw new Error("invalid handoff VM instance")
  const home = await runBounded(["limactl", "shell", "--start", instance, "--", "printenv", "HOME"], cwd, 120_000, 1024)
  if (!/^\/home\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(home)) throw new Error("invalid guest home")
  const source = `${home}/.local/share/chezmoi-dotfiles-ai`
  const prompt = `Approved host R&D handoff. Execute the approved decisions and start a separate DBSCTR draft-PR cycle. ${serialized}`
  const workspaceOutput = await runBounded(["limactl", "shell", instance, "--", "herdr", "workspace", "create",
    "--cwd", source, "--label", "DBSCTR Handoff", "--no-focus"], cwd, 120_000)
  let workspace: any
  try {
    workspace = JSON.parse(workspaceOutput)
  } catch {
    throw new Error("VM Herdr returned malformed workspace output")
  }
  const id = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
  const paneID = workspace?.result?.root_pane?.pane_id
  const workspaceID = workspace?.result?.root_pane?.workspace_id
  if (typeof paneID !== "string" || !id.test(paneID)
      || typeof workspaceID !== "string" || !id.test(workspaceID)
      || !paneID.startsWith(`${workspaceID}:`)) throw new Error("VM Herdr returned no workspace pane")
  const output = await runBounded(["limactl", "shell", instance, "--", "herdr", "agent", "start", "DBSCTR Handoff",
    "--kind", "opencode", "--pane", paneID, "--timeout", "120000", "--",
    "run", "--agent", "build", "--interactive", prompt], cwd, 180_000)
  let value: any
  try {
    value = JSON.parse(output)
  } catch {
    throw new Error("VM Herdr returned malformed output")
  }
  const agent = value?.result?.agent ?? value?.result ?? value
  if (agent?.pane_id !== paneID || typeof agent.pane_id !== "string" || !id.test(agent.pane_id)
      || agent?.workspace_id !== undefined && agent.workspace_id !== workspaceID)
    throw new Error("VM Herdr returned no launch identity")
  const result: Record<string, string | number> = { schema_version: 1, target: report.target, status: "launched" }
  for (const key of ["pane_id", "tab_id", "workspace_id"])
    if (typeof agent?.[key] === "string" && id.test(agent[key])) result[key] = agent[key]
  if (typeof agent?.agent_session?.value === "string" && id.test(agent.agent_session.value))
    result.session_id = agent.agent_session.value
  return JSON.stringify(result)
}

export async function vmHandoffTarget(cwd = process.cwd()) {
  const target = await runBounded(["sandbox-vm", "build-workspace"], cwd, 2_000, 1024)
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(target) || target === "host")
    throw new Error("invalid build workspace")
  return target
}

function reviewHistoryArgv(args: {
  after?: number
  before?: number
  methodRevision?: string
  cycleId?: string
  state?: "active" | "blocked" | "abandoned" | "completed" | "unknown"
  context?: string
  projectDigest?: string
  reviewedStatus?: "reviewed" | "unreviewed"
  replay?: string
  archiveOnly?: boolean
  snapshot?: number
  sessionCeiling?: number
  partCeiling?: number
  databaseDigest?: string
  exclusionDigest?: string
  limit?: number
  cursor?: number
}, excludedSessionID?: string, excludedMessageID?: string) {
  const argv = ["dbsctrctl", "review-history"]
  const names: Record<string, string> = {
    methodRevision: "method-revision", cycleId: "cycle-id", projectDigest: "project-digest",
    reviewedStatus: "reviewed-status", sessionCeiling: "session-ceiling", partCeiling: "part-ceiling",
    databaseDigest: "database-digest",
    archiveOnly: "archive-only",
  }
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  if (excludedMessageID !== undefined) argv.push("--excluded-message-id", excludedMessageID)
  for (const [name, value] of Object.entries(args)) {
    if (value === true) argv.push(`--${names[name] ?? name.replace(/[A-Z]/g, value => `-${value.toLowerCase()}`)}`)
    else if (value !== undefined && value !== false) argv.push(`--${names[name] ?? name.replace(/[A-Z]/g, value => `-${value.toLowerCase()}`)}`, String(value))
  }
  return argv
}

async function analyticsJSON(argv: string[], cwd: string, timeoutMs: number | null = 30_000) {
  const output = await runBounded(argv, cwd, timeoutMs, 256 * 1024)
  const unsafe = /(?:https?:\/\/|file:\/\/|\/(?:Users|home|root|tmp|private|var\/folders)\/|-----BEGIN [A-Z ]*PRIVATE KEY-----)/i
  if (unsafe.test(output)) {
    throw new Error("analytics helper returned unsafe content")
  }
  let value: any
  try {
    value = JSON.parse(output)
  } catch {
    throw new Error("analytics helper returned malformed JSON")
  }
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new Error("analytics helper returned malformed JSON")
  }
  if (unsafe.test(JSON.stringify(value))) throw new Error("analytics helper returned unsafe content")
  return value
}

function exactKeys(value: any, keys: string[]) {
  return value !== null && !Array.isArray(value) && typeof value === "object"
    && Object.keys(value).sort().join("\0") === [...keys].sort().join("\0")
}

export async function historyCapture(args: { captureID: string; cursor?: number; limit?: number }, cwd = process.cwd()) {
  const argv = ["dbsctrctl", "history-capture", "--capture-id", args.captureID]
  if (args.cursor !== undefined) argv.push("--cursor", String(args.cursor), "--limit", String(args.limit ?? 100))
  const value = await analyticsJSON(argv, cwd)
  const keys = ["schema_version", "capture_id", "query", "snapshot", "page_size", "page_count", "member_count", "aggregates"]
  if (args.cursor !== undefined) keys.push("cursor", "limit", "members", "continuation")
  if (!exactKeys(value, keys) || value.schema_version !== 1 || value.capture_id !== args.captureID
      || !Number.isInteger(value.member_count) || value.member_count < 0
      || value.query === null || typeof value.query !== "object" || Array.isArray(value.query)
      || value.aggregates === null || typeof value.aggregates !== "object" || Array.isArray(value.aggregates)
      || args.cursor !== undefined && (value.cursor !== args.cursor || value.limit !== (args.limit ?? 100)
        || !Array.isArray(value.members) || value.members.length > value.limit
        || value.continuation !== null && (!Number.isInteger(value.continuation) || value.continuation <= value.cursor))) {
    throw new Error("analytics helper returned an invalid capture")
  }
  return JSON.stringify(value)
}

export async function historyTelemetry(args: Parameters<typeof reviewHistory>[0], cwd = process.cwd(), excludedSessionID?: string, excludedMessageID?: string) {
  const value = await analyticsJSON(reviewHistoryArgv(args, excludedSessionID, excludedMessageID), cwd)
  const limit = args.limit ?? 25
  const telemetryKeys = ["schema_version", "approval_count", "retry_count", "delegation_count", "model_families",
    "error_classes", "token_total", "cost_total", "provider_ids", "model_ids", "agent_ids", "session_relation",
    "core_revisions", "overlay_revisions", "gate_failure_count", "gate_reopen_count", "remediation_round_count",
    "availability", "attribution_status"]
  const availabilityKeys = telemetryKeys.filter(key => !["schema_version", "availability", "attribution_status"].includes(key))
  const attribution = ["exact", "family", "worktree", "source", "ambiguous", "unavailable"]
  for (const candidate of Array.isArray(value.candidates) ? value.candidates : []) {
    if (candidate !== null && typeof candidate === "object" && candidate.telemetry !== undefined
        && candidate.telemetry?.schema_version === undefined) candidate.telemetry = {
      ...candidate.telemetry, schema_version: 2,
      provider_ids: "unavailable", model_ids: "unavailable", agent_ids: "unavailable",
      session_relation: "unavailable", core_revisions: "unavailable", overlay_revisions: "unavailable",
      gate_failure_count: "unavailable", gate_reopen_count: "unavailable", remediation_round_count: "unavailable",
      availability: { ...candidate.telemetry.availability,
        provider_ids: "unavailable", model_ids: "unavailable", agent_ids: "unavailable",
        session_relation: "unavailable", core_revisions: "unavailable", overlay_revisions: "unavailable",
        gate_failure_count: "unavailable", gate_reopen_count: "unavailable", remediation_round_count: "unavailable" },
    }
    if (candidate !== null && typeof candidate === "object" && candidate.telemetry === undefined) candidate.telemetry = {
      schema_version: 2,
      approval_count: "unavailable", retry_count: "unavailable", delegation_count: "unavailable",
      model_families: "unavailable", error_classes: "unavailable", token_total: "unavailable",
      cost_total: "unavailable", provider_ids: "unavailable", model_ids: "unavailable",
      agent_ids: "unavailable", session_relation: "unavailable", core_revisions: "unavailable",
      overlay_revisions: "unavailable", gate_failure_count: "unavailable", gate_reopen_count: "unavailable",
      remediation_round_count: "unavailable",
      availability: Object.fromEntries(availabilityKeys.map(key => [key, "unavailable"])),
      attribution_status: attribution.includes(candidate?.correlation_quality)
        ? candidate.correlation_quality : "unavailable",
    }
  }
  if (value.schema_version !== 1 || !Array.isArray(value.candidates) || value.candidates.length > limit
      || value.limit !== limit || value.cursor !== (args.cursor ?? 0)
      || value.candidates.some((candidate: any) => candidate === null || typeof candidate !== "object"
        || candidate.telemetry !== undefined && (!exactKeys(candidate.telemetry, telemetryKeys)
          || candidate.telemetry.schema_version !== 2
          || !exactKeys(candidate.telemetry.availability, availabilityKeys)
          || !Object.values(candidate.telemetry.availability).every(status => ["available", "unavailable"].includes(status as string))
          || !attribution.includes(candidate.telemetry.attribution_status)))) {
    throw new Error("analytics helper returned invalid telemetry")
  }
  return JSON.stringify(value)
}

export async function benchmarkResult(benchmarkID: string, cwd = process.cwd()) {
  const value = await analyticsJSON(["dbsctrctl", "benchmark", "--benchmark-id", benchmarkID], cwd)
  const classifications = ["improved", "neutral", "regressed", "insufficient"]
  if (!exactKeys(value, ["schema_version", "benchmark_id", "definition", "inputs", "windows", "result", "evaluated_at"])
      || value.schema_version !== 1 || value.benchmark_id !== benchmarkID
      || !exactKeys(value.definition, ["version", "metric", "direction"])
      || !exactKeys(value.inputs, ["baseline_capture_id", "observation_capture_id", "merge_identity", "merged_at",
        "activation_status", "activation_identity", "activated_at"])
      || !exactKeys(value.result, ["classification", "baseline_value", "observation_value", "delta", "confounders",
        "unavailable_metrics", "association_only", "reason"])
      || !classifications.includes(value.result.classification)
      || value.result.association_only !== true) {
    throw new Error("analytics helper returned an invalid benchmark")
  }
  return JSON.stringify(value)
}

export async function reviewHistorySave(report: {
  schema_version: 1
  cohort: string[]
  query_digest: string
  rubric: { name: string; version: string; digest: string }
  snapshot?: number
  session_ceiling?: number
  part_ceiling?: number
  database_digest?: string
  limit?: number
  cursor?: number
  findings: string[]
  scorecards?: string[]
  trends?: string[]
  proposals?: string[]
  caveats?: string[]
}, cwd = process.cwd(), excludedSessionID?: string, excludedMessageID?: string) {
  const argv = ["dbsctrctl", "review-history-save", "--report-json", JSON.stringify(report)]
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  if (excludedMessageID !== undefined) argv.push("--excluded-message-id", excludedMessageID)
  return await run(argv, cwd)
}

export async function providerEvaluationSave(args: {
  manifestDigest: string
  rubric: { name: string; version: string; digest: string }
  findings: string[]
  recommendations: string[]
}, cwd = process.cwd()) {
  const captured = evaluationReceipts.get(args.manifestDigest)
  if (captured === undefined) throw new Error("terminal federated capture receipt is unavailable")
  try {
    const privacy = await analyticsJSON(["sandbox-vm", "privacy-epochs"], cwd, null)
    const sourceIDs = captured.sources.map((source: any) => source.source_id)
    if (!exactKeys(privacy, ["schema_version", "sources"]) || privacy.schema_version !== 1
        || !Array.isArray(privacy.sources)
        || canonicalJSON(privacy.sources.map((source: any) => source?.source_id)) !== canonicalJSON(sourceIDs)
        || privacy.sources.some((source: any) => !exactKeys(source,
          source?.availability === "available" ? ["source_id", "availability", "privacy_epoch_digest"] : ["source_id", "availability"])
          || source.availability !== "available" || !/^[0-9a-f]{64}$/.test(source.privacy_epoch_digest)))
      throw new Error("sandbox helper returned invalid privacy epochs")
    if (captured.sources.some((source: any) => privacy.sources.find(
      (item: any) => item.source_id === source.source_id).privacy_epoch_digest !== source.privacy_epoch_digest))
      throw new Error("terminal federated capture privacy epoch changed")
    const report = JSON.stringify({ rubric: args.rubric, findings: args.findings,
      recommendations: args.recommendations })
    const output = await runBoundedInput([
      "dbsctrctl", "provider-evaluation-save", "--receipt-json", "-", "--report-json", report,
    ], JSON.stringify(captured), cwd)
    const value = JSON.parse(output)
    if (value?.schema_version !== 1 || value?.status === "insufficient"
        && (!Number.isInteger(value.eligible_count) || value.eligible_count < 0)
        || value?.status !== "insufficient" && !/^[0-9a-f]{24}$/.test(value?.report_id ?? ""))
      throw new Error("helper returned invalid provider evaluation")
    return JSON.stringify(value)
  } finally {
    discardEvaluationReceipt(args.manifestDigest)
  }
}

export async function providerEvaluation(reportID?: string, cwd = process.cwd()) {
  const value = await analyticsJSON([
    "dbsctrctl", "provider-evaluation", ...(reportID === undefined ? [] : ["--report-id", reportID]),
  ], cwd)
  if (value?.schema_version !== 1 || reportID !== undefined && value.report_id !== reportID
      || reportID === undefined && !Array.isArray(value.reports))
    throw new Error("helper returned invalid provider evaluation")
  return JSON.stringify(value)
}

export async function improvementStatus(workerID?: string, cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "improvement-status",
    ...(workerID === undefined ? [] : ["--worker-id", workerID]),
  ], cwd)
}

export async function improvementClaim(sessionID: string, summary: string, priority: "P0" | "P1" | "P2" | "P3", cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "improvement-claim",
    "--session-id", sessionID,
    "--summary", summary,
    "--priority", priority,
  ], cwd)
}

export async function improvementUpdate(workerID: string, args: {
  state: "claimed" | "discovery" | "implementing" | "draft_pr" | "blocked" | "merged" | "closed" | "abandoned"
  workspaceID?: string
  tabID?: string
  paneID?: string
  cycleID?: string
  paths?: string[]
  autonomous?: boolean
}, cwd = process.cwd(), bySession = false) {
  const argv = ["dbsctrctl", "improvement-update", bySession ? "--session-id" : "--worker-id", workerID, "--state", args.state]
  const names: Record<string, string> = {
    workspaceID: "workspace-id", tabID: "tab-id", paneID: "pane-id", cycleID: "cycle-id",
  }
  for (const [name, value] of Object.entries(args)) {
    if (name === "autonomous" && value === true) argv.push("--autonomous")
    else if (name !== "state" && name !== "paths" && value !== undefined) argv.push(`--${names[name]}`, String(value))
  }
  for (const path of args.paths ?? []) argv.push("--path", path)
  return await run(argv, cwd)
}

export async function beginCycle(args: {
  cycleId: string
  context: string
  risk: "routine" | "elevated" | "critical"
  deliveryIntent: "local" | "merge" | "release" | "deploy" | "draft_pr"
  planPath: string
  githubAccount?: string
  githubRepository?: string
}, cwd: string, launch = false, env = process.env, runtime?: {
  sessionID: string
  messageID: string
  directory: string
  worktree: string
}) {
  const runtimeArgv = runtime ? [
    "--opencode-session-id", runtime.sessionID,
    "--opencode-message-id", runtime.messageID,
    "--opencode-directory", runtime.directory,
    "--opencode-worktree", runtime.worktree,
    "--harness-activation-json", JSON.stringify(harnessActivation),
  ] : []
  const output = await run([
    "dbsctrctl", "begin",
    "--cycle-id", args.cycleId,
    "--context", args.context,
    "--risk", args.risk,
    "--delivery-intent", args.deliveryIntent,
    "--plan", args.planPath,
    ...(args.githubAccount === undefined ? [] : ["--github-account", args.githubAccount]),
    ...(args.githubRepository === undefined ? [] : ["--github-repository", args.githubRepository]),
    ...runtimeArgv,
  ], cwd)
  const handoff = JSON.parse(output)
  if (!launch || env.HERDR_ENV !== "1") return { ...handoff, herdr: "not_launched" }
  try {
    const started = await run([
      "herdr", "agent", "start", "opencode",
      "--cwd", handoff.worktree,
      "--no-focus", "--", "opencode", handoff.worktree,
    ], cwd)
    try {
      const value = JSON.parse(started)
      const agent = value?.result?.agent ?? value?.agent ?? value
      const terminalID = agent?.terminal_id
      const sessionID = agent?.agent_session?.value
      if (typeof terminalID === "string") return {
        ...handoff,
        herdr: "launched",
        herdr_terminal_id: terminalID,
        ...(typeof sessionID === "string" ? { herdr_opencode_session_id: sessionID } : {}),
      }
    } catch {
      // Herdr launch is useful even when this version emits no structured metadata.
    }
    return { ...handoff, herdr: "launched" }
  } catch (error) {
    return { ...handoff, herdr: `launch_failed: ${error}` }
  }
}

export async function reconcileTarget(mode: "preview" | "prepare", cwd = process.cwd()) {
  return JSON.parse(await run([
    "dbsctrctl", "reconcile-target", "--mode", mode, "--json",
  ], cwd))
}
