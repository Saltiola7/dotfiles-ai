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

export async function cycleStatus(cwd: string) {
  return await run(["dbsctrctl", "status", "--json"], cwd)
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

export async function reviewScan(limit = 25, cursor = 0, snapshot?: number, cwd = process.cwd(), sessionCeiling?: number, partCeiling?: number, databaseDigest?: string, excludedSessionID?: string) {
  const argv = ["dbsctrctl", "review-scan", "--limit", String(limit), "--cursor", String(cursor)]
  if (snapshot !== undefined) argv.push("--snapshot", String(snapshot))
  if (sessionCeiling !== undefined) argv.push("--session-ceiling", String(sessionCeiling))
  if (partCeiling !== undefined) argv.push("--part-ceiling", String(partCeiling))
  if (databaseDigest !== undefined) argv.push("--database-digest", databaseDigest)
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
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
  limit: number
  cursor: number
  decision: string
  notes?: string
  findings: string[]
  scorecards: string[]
  trends: string[]
  proposals: string[]
  caveats: string[]
}, cwd = process.cwd(), excludedSessionID?: string) {
  return await run([
    "dbsctrctl", "review-complete", "--report-json", JSON.stringify(report),
    "--scan-digest", report.scan_digest,
    ...(excludedSessionID === undefined ? [] : ["--excluded-session-id", excludedSessionID]),
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
  limit?: number
  cursor?: number
}, cwd = process.cwd(), excludedSessionID?: string) {
  const argv = ["dbsctrctl", "review-history"]
  const names: Record<string, string> = {
    methodRevision: "method-revision", cycleId: "cycle-id", projectDigest: "project-digest",
    reviewedStatus: "reviewed-status", sessionCeiling: "session-ceiling", partCeiling: "part-ceiling",
    databaseDigest: "database-digest",
    archiveOnly: "archive-only",
  }
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  for (const [name, value] of Object.entries(args)) {
    if (value === true) argv.push(`--${names[name] ?? name.replace(/[A-Z]/g, value => `-${value.toLowerCase()}`)}`)
    else if (value !== undefined && value !== false) argv.push(`--${names[name] ?? name.replace(/[A-Z]/g, value => `-${value.toLowerCase()}`)}`, String(value))
  }
  return await run(argv, cwd)
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
  findings: string[]
  scorecards?: string[]
  trends?: string[]
  proposals?: string[]
  caveats?: string[]
}, cwd = process.cwd(), excludedSessionID?: string) {
  const argv = ["dbsctrctl", "review-history-save", "--report-json", JSON.stringify(report)]
  if (excludedSessionID !== undefined) argv.push("--excluded-session-id", excludedSessionID)
  return await run(argv, cwd)
}

export async function beginCycle(args: {
  cycleId: string
  context: string
  risk: "routine" | "elevated" | "critical"
  deliveryIntent: "local" | "merge" | "release" | "deploy"
  planPath: string
}, cwd: string, launch = false, env = process.env, runtime?: {
  sessionID: string
  directory: string
  worktree: string
}) {
  const runtimeArgv = runtime ? [
    "--opencode-session-id", runtime.sessionID,
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
