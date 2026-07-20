import { realpath } from "node:fs/promises"

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

async function runBounded(argv: string[], cwd: string, timeoutMs = 2000, outputLimit = 64 * 1024) {
  const child = Bun.spawn(argv, { cwd, stdout: "pipe", stderr: "pipe", detached: true })
  const budget = { remaining: outputLimit }
  const killTree = () => {
    try {
      process.kill(-child.pid, "SIGKILL")
    } catch {
      child.kill()
    }
  }
  let timer: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      killTree()
      reject(new Error("command timed out"))
    }, timeoutMs)
  })
  try {
    const [stdout, stderr, exitCode] = await Promise.race([Promise.all([
      boundedText(child.stdout, budget),
      boundedText(child.stderr, budget),
      child.exited,
    ]), timeout])
    if (exitCode !== 0) throw new Error(stderr || `${argv[0]} failed`)
    return stdout
  } catch (error) {
    killTree()
    throw error
  } finally {
    clearTimeout(timer!)
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

async function analyticsJSON(argv: string[], cwd: string) {
  const output = await runBounded(argv, cwd, 30_000, 256 * 1024)
  const unsafe = /(?:https?:\/\/|file:\/\/|\/(?:Users|home|var\/folders)\/|-----BEGIN [A-Z ]*PRIVATE KEY-----)/i
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
      || !Number.isInteger(value.member_count) || value.member_count < 1
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
  const telemetryKeys = ["approval_count", "retry_count", "delegation_count", "model_families", "error_classes",
    "token_total", "cost_total", "availability", "attribution_status"]
  const availabilityKeys = telemetryKeys.filter(key => !["availability", "attribution_status"].includes(key))
  const attribution = ["exact", "family", "worktree", "source", "ambiguous", "unavailable"]
  for (const candidate of Array.isArray(value.candidates) ? value.candidates : []) {
    if (candidate !== null && typeof candidate === "object" && candidate.telemetry === undefined) candidate.telemetry = {
      approval_count: "unavailable", retry_count: "unavailable", delegation_count: "unavailable",
      model_families: "unavailable", error_classes: "unavailable", token_total: "unavailable",
      cost_total: "unavailable",
      availability: Object.fromEntries(availabilityKeys.map(key => [key, "unavailable"])),
      attribution_status: attribution.includes(candidate?.correlation_quality)
        ? candidate.correlation_quality : "unavailable",
    }
  }
  if (value.schema_version !== 1 || !Array.isArray(value.candidates) || value.candidates.length > limit
      || value.limit !== limit || value.cursor !== (args.cursor ?? 0)
      || value.candidates.some((candidate: any) => candidate === null || typeof candidate !== "object"
        || candidate.telemetry !== undefined && (!exactKeys(candidate.telemetry, telemetryKeys)
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

export async function improvementStatus(workerID?: string, cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "improvement-status",
    ...(workerID === undefined ? [] : ["--worker-id", workerID]),
  ], cwd)
}

export async function improvementClaim(sessionID: string, summary: string, cwd = process.cwd()) {
  return await run([
    "dbsctrctl", "improvement-claim",
    "--session-id", sessionID,
    "--summary", summary,
  ], cwd)
}

export async function improvementUpdate(workerID: string, args: {
  state: "claimed" | "discovery" | "implementing" | "draft_pr" | "blocked" | "merged" | "closed" | "abandoned"
  workspaceID?: string
  tabID?: string
  paneID?: string
  cycleID?: string
  paths?: string[]
}, cwd = process.cwd(), bySession = false) {
  const argv = ["dbsctrctl", "improvement-update", bySession ? "--session-id" : "--worker-id", workerID, "--state", args.state]
  const names: Record<string, string> = {
    workspaceID: "workspace-id", tabID: "tab-id", paneID: "pane-id", cycleID: "cycle-id",
  }
  for (const [name, value] of Object.entries(args)) {
    if (name !== "state" && name !== "paths" && value !== undefined) argv.push(`--${names[name]}`, String(value))
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
