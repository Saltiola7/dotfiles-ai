import { tool } from "@opencode-ai/plugin"
import { attachRuntime, benchmarkResult, beginCycle, cycleStatus, fixedCommitInspect, historyCapture, historyTelemetry, improvementClaim, improvementStatus, improvementUpdate, lifecycleAudit, phaseSpan, recordExecutionBenchmark, reviewComplete, reviewHistory, reviewHistorySave, reviewScan, runtimeHealth, validateExecutionDag } from "../lib/dbsctr-runtime"

export const status = tool({
  description: "Read authoritative DBSCTR cycle status for the current worktree.",
  args: {},
  async execute(_args, context) {
    return await cycleStatus(context.worktree)
  },
})

export const attach = tool({
  description: "Attach the current validated Build runtime to the active DBSCTR cycle.",
  args: {},
  async execute(_args, context) {
    await context.ask({ permission: "dbsctr_attach", patterns: ["*"], always: [] })
    return await attachRuntime(context.worktree, {
      sessionID: context.sessionID,
      messageID: context.messageID,
      directory: context.directory,
      worktree: context.worktree,
    })
  },
})

export const runtime_health = tool({
  description: "Read normalized advisory Herdr health for the current OpenCode runtime.",
  args: {},
  async execute(_args, context) {
    return await runtimeHealth(context.worktree, {
      sessionID: context.sessionID,
      worktree: context.worktree,
    })
  },
})

export const phase_span = tool({
  description: "Record one private explicit DBSCTR phase-span boundary and return a path-free compact profile.",
  args: {
    spanId: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
    event: tool.schema.enum(["start", "finish"]),
    parentSpanId: tool.schema.string().optional(),
    phase: tool.schema.enum(["domain", "behavior", "spec", "contract", "test_driven_implementation", "refactor", "operation"]).optional(),
    operation: tool.schema.enum(["marker", "typed_tool", "task", "read", "readonly_qa"]).optional(),
    dependencies: tool.schema.array(tool.schema.string()).max(100).optional().default([]),
    ownershipPaths: tool.schema.array(tool.schema.string().min(1).max(512)).max(100).optional().default([]),
    attribution: tool.schema.enum(["explicit", "adapter", "unavailable"]).optional(),
    result: tool.schema.enum(["passed", "failed", "blocked", "abandoned", "unavailable"]).optional(),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_phase_span", patterns: ["*"], always: [] })
    return await phaseSpan({
      spanID: args.spanId, event: args.event, parentSpanID: args.parentSpanId,
      phase: args.phase, operation: args.operation, dependencies: args.dependencies,
      ownershipPaths: args.ownershipPaths, attribution: args.attribution, result: args.result,
    }, context.worktree)
  },
})

export const execution_dag = tool({
  description: "Validate a bounded read-only DBSCTR execution DAG and return concurrent or forced-serial authorization.",
  args: {
    mode: tool.schema.enum(["serial", "benchmark", "concurrent"]),
    nodes: tool.schema.array(tool.schema.object({
      id: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
      depends_on: tool.schema.array(tool.schema.string()).max(100),
      operation: tool.schema.enum(["read", "readonly_qa"]),
      ownership_paths: tool.schema.array(tool.schema.string().min(1).max(512)).min(1).max(100),
    })).min(1).max(100),
  },
  async execute(args, context) {
    return await validateExecutionDag(args.nodes, args.mode, context.worktree)
  },
})

export const execution_benchmark = tool({
  description: "Persist paired local execution evidence and activate concurrency only when the V3.24 threshold passes.",
  args: {
    serialMs: tool.schema.array(tool.schema.number().int().min(1).max(86_400_000)).min(5).max(100),
    concurrentMs: tool.schema.array(tool.schema.number().int().min(1).max(86_400_000)).min(5).max(100),
    serialFailedGates: tool.schema.number().int().min(0),
    concurrentFailedGates: tool.schema.number().int().min(0),
    serialRemediationRounds: tool.schema.number().int().min(0),
    concurrentRemediationRounds: tool.schema.number().int().min(0),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_execution_benchmark", patterns: ["*"], always: [] })
    return await recordExecutionBenchmark({
      serial_ms: args.serialMs, concurrent_ms: args.concurrentMs,
      serial_failed_gates: args.serialFailedGates,
      concurrent_failed_gates: args.concurrentFailedGates,
      serial_remediation_rounds: args.serialRemediationRounds,
      concurrent_remediation_rounds: args.concurrentRemediationRounds,
    }, context.worktree)
  },
})

export const audit = tool({
  description: "Inventory DBSCTR lifecycle artifacts at a fixed Git commit without changing files.",
  args: { commit: tool.schema.string().optional().default("HEAD") },
  async execute(args, context) {
    return await lifecycleAudit(context.worktree, args.commit)
  },
})

export const inspect = tool({
  description: "Read, list, search, or inspect metadata from one fixed Git commit without using the worktree overlay.",
  args: {
    action: tool.schema.enum(["read", "tree", "search", "object"]),
    commit: tool.schema.string().optional().default("HEAD"),
    path: tool.schema.string().optional(),
    query: tool.schema.string().optional(),
    limit: tool.schema.number().int().optional(),
    offset: tool.schema.number().int().optional(),
    cursor: tool.schema.number().int().optional(),
    excerpt: tool.schema.number().int().optional(),
  },
  async execute(args, context) {
    return await fixedCommitInspect(args, context.worktree)
  },
})

export const review = tool({
  description: "Scan bounded private DBSCTR session metadata without changing files.",
  args: {
    limit: tool.schema.number().int().min(1).max(100).optional().default(25),
    cursor: tool.schema.number().int().min(0).optional().default(0),
    snapshot: tool.schema.number().int().min(0).optional(),
    sessionCeiling: tool.schema.number().int().min(0).optional(),
    partCeiling: tool.schema.number().int().min(0).optional(),
    databaseDigest: tool.schema.string().optional(),
    exclusionDigest: tool.schema.string().optional(),
  },
  async execute(args, context) {
    return await reviewScan(args.limit, args.cursor, args.snapshot, context.worktree, args.sessionCeiling, args.partCeiling, args.databaseDigest, context.sessionID, context.messageID, args.exclusionDigest)
  },
})

export const review_complete = tool({
  description: "Persist one sanitized private DBSCTR review and mark its exact candidates reviewed.",
  args: {
    sessionIds: tool.schema.array(tool.schema.string()).min(1).max(100),
    cycleIds: tool.schema.array(tool.schema.string()).max(100),
    scanDigest: tool.schema.string(),
    snapshot: tool.schema.number().int().min(0),
    sessionCeiling: tool.schema.number().int().min(0),
    partCeiling: tool.schema.number().int().min(0),
    databaseDigest: tool.schema.string(),
    exclusionDigest: tool.schema.string().optional(),
    limit: tool.schema.number().int().min(1).max(100),
    cursor: tool.schema.number().int().min(0),
    decision: tool.schema.string().max(256),
    notes: tool.schema.string().max(2048).optional(),
    findings: tool.schema.array(tool.schema.string().max(512)).max(50),
    scorecards: tool.schema.array(tool.schema.string().max(512)).max(50),
    trends: tool.schema.array(tool.schema.string().max(512)).max(50),
    proposals: tool.schema.array(tool.schema.string().max(512)).max(50),
    caveats: tool.schema.array(tool.schema.string().max(512)).max(50),
  },
  async execute(args, context) {
    await context.ask({
      permission: "dbsctr_review_complete",
      patterns: ["*"],
      always: [],
      metadata: { sessions: args.sessionIds.length, cycles: args.cycleIds.length },
    })
    return await reviewComplete({
      session_ids: args.sessionIds,
      cycle_ids: args.cycleIds,
      scan_digest: args.scanDigest,
      snapshot: args.snapshot,
      session_ceiling: args.sessionCeiling,
      part_ceiling: args.partCeiling,
      database_digest: args.databaseDigest,
      exclusion_digest: args.exclusionDigest,
      limit: args.limit,
      cursor: args.cursor,
      decision: args.decision,
      notes: args.notes,
      findings: args.findings,
      scorecards: args.scorecards,
      trends: args.trends,
      proposals: args.proposals,
      caveats: args.caveats,
    }, context.worktree, context.sessionID, context.messageID)
  },
})

export const review_history = tool({
  description: "Read bounded sanitized private DBSCTR review history, or replay an immutable saved cohort.",
  args: {
    after: tool.schema.number().int().min(0).optional(),
    before: tool.schema.number().int().min(0).optional(),
    methodRevision: tool.schema.string().optional(),
    cycleId: tool.schema.string().optional(),
    state: tool.schema.enum(["active", "blocked", "abandoned", "completed", "unknown"]).optional(),
    context: tool.schema.string().optional(),
    projectDigest: tool.schema.string().optional(),
    reviewedStatus: tool.schema.enum(["reviewed", "unreviewed"]).optional(),
    replay: tool.schema.string().optional(),
    archiveOnly: tool.schema.boolean().optional().default(false),
    snapshot: tool.schema.number().int().min(0).optional(),
    sessionCeiling: tool.schema.number().int().min(0).optional(),
    partCeiling: tool.schema.number().int().min(0).optional(),
    databaseDigest: tool.schema.string().optional(),
    exclusionDigest: tool.schema.string().optional(),
    limit: tool.schema.number().int().min(1).max(100).optional().default(100),
    cursor: tool.schema.number().int().min(0).optional().default(0),
  },
  async execute(args, context) {
    return await reviewHistory(args, context.worktree, context.sessionID, context.messageID)
  },
})

export const history_capture = tool({
  description: "Read a bounded immutable history-capture summary or ordered member page.",
  args: {
    captureId: tool.schema.string().regex(/^[0-9a-f]{24}$/),
    cursor: tool.schema.number().int().min(0).optional(),
    limit: tool.schema.number().int().min(1).max(100).optional().default(100),
  },
  async execute(args, context) {
    return await historyCapture({ captureID: args.captureId, cursor: args.cursor, limit: args.limit }, context.worktree)
  },
})

export const history_telemetry = tool({
  description: "Read bounded structured history telemetry with explicit availability and attribution.",
  args: {
    after: tool.schema.number().int().min(0).optional(),
    before: tool.schema.number().int().min(0).optional(),
    methodRevision: tool.schema.string().optional(),
    cycleId: tool.schema.string().optional(),
    state: tool.schema.enum(["active", "blocked", "abandoned", "completed", "unknown"]).optional(),
    context: tool.schema.string().optional(),
    projectDigest: tool.schema.string().optional(),
    reviewedStatus: tool.schema.enum(["reviewed", "unreviewed"]).optional(),
    replay: tool.schema.string().optional(),
    archiveOnly: tool.schema.boolean().optional().default(false),
    snapshot: tool.schema.number().int().min(0).optional(),
    sessionCeiling: tool.schema.number().int().min(0).optional(),
    partCeiling: tool.schema.number().int().min(0).optional(),
    databaseDigest: tool.schema.string().optional(),
    exclusionDigest: tool.schema.string().optional(),
    limit: tool.schema.number().int().min(1).max(100).optional().default(25),
    cursor: tool.schema.number().int().min(0).optional().default(0),
  },
  async execute(args, context) {
    return await historyTelemetry(args, context.worktree, context.sessionID, context.messageID)
  },
})

export const benchmark = tool({
  description: "Replay one immutable versioned longitudinal benchmark result.",
  args: { benchmarkId: tool.schema.string().regex(/^[0-9a-f]{24}$/) },
  async execute(args, context) {
    return await benchmarkResult(args.benchmarkId, context.worktree)
  },
})

export const review_history_save = tool({
  description: "Save an immutable, sanitized private review-history cohort under the standing local-write boundary.",
  args: {
    cohort: tool.schema.array(tool.schema.string()).min(1).max(100),
    queryDigest: tool.schema.string(),
    rubricName: tool.schema.string().max(256),
    rubricVersion: tool.schema.string().max(256),
    rubricDigest: tool.schema.string(),
    snapshot: tool.schema.number().int().min(0).optional(),
    sessionCeiling: tool.schema.number().int().min(0).optional(),
    partCeiling: tool.schema.number().int().min(0).optional(),
    databaseDigest: tool.schema.string().optional(),
    limit: tool.schema.number().int().min(1).max(100).optional(),
    cursor: tool.schema.number().int().min(0).optional(),
    findings: tool.schema.array(tool.schema.string().max(512)).max(50),
    scorecards: tool.schema.array(tool.schema.string().max(512)).max(50).optional().default([]),
    trends: tool.schema.array(tool.schema.string().max(512)).max(50).optional().default([]),
    proposals: tool.schema.array(tool.schema.string().max(512)).max(50).optional().default([]),
    caveats: tool.schema.array(tool.schema.string().max(512)).max(50).optional().default([]),
  },
  async execute(args, context) {
    return await reviewHistorySave({
      schema_version: 1,
      cohort: args.cohort,
      query_digest: args.queryDigest,
      rubric: { name: args.rubricName, version: args.rubricVersion, digest: args.rubricDigest },
      snapshot: args.snapshot,
      session_ceiling: args.sessionCeiling,
      part_ceiling: args.partCeiling,
      database_digest: args.databaseDigest,
      limit: args.limit,
      cursor: args.cursor,
      findings: args.findings,
      scorecards: args.scorecards,
      trends: args.trends,
      proposals: args.proposals,
      caveats: args.caveats,
    }, context.worktree, context.sessionID, context.messageID)
  },
})

export const improvement_status = tool({
  description: "Read durable sanitized autonomous-improvement worker and claim state.",
  args: { workerId: tool.schema.string().optional() },
  async execute(args, context) {
    return await improvementStatus(args.workerId, context.worktree)
  },
})

export const improvement_claim = tool({
  description: "Atomically claim one sanitized distinct improvement for the current native-Build session.",
  args: { summary: tool.schema.string().min(1).max(512) },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_improvement_claim", patterns: ["*"], always: [] })
    return await improvementClaim(context.sessionID, args.summary, context.worktree)
  },
})

export const improvement_update = tool({
  description: "Advance the current improvement claim and declare its exact repository-relative ownership.",
  args: {
    state: tool.schema.enum(["claimed", "discovery", "implementing", "draft_pr", "blocked", "merged", "closed", "abandoned"]),
    cycleId: tool.schema.string().optional(),
    paths: tool.schema.array(tool.schema.string().min(1).max(512)).max(100).optional().default([]),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_improvement_update", patterns: ["*"], always: [] })
    return await improvementUpdate(context.sessionID, {
      state: args.state,
      cycleID: args.cycleId,
      paths: args.paths,
    }, context.worktree, true)
  },
})

export const begin = tool({
  description: "Create an isolated DBSCTR branch/worktree and optionally launch OpenCode there through Herdr.",
  args: {
    cycleId: tool.schema.string(),
    context: tool.schema.string(),
    risk: tool.schema.enum(["routine", "elevated", "critical"]),
    deliveryIntent: tool.schema.enum(["local", "merge", "release", "deploy", "draft_pr"]),
    planPath: tool.schema.string(),
    githubAccount: tool.schema.string().optional(),
    githubRepository: tool.schema.string().optional(),
    launch: tool.schema.boolean().optional().default(false),
  },
  async execute(args, context) {
    return JSON.stringify(await beginCycle(args, context.worktree, args.launch, process.env, {
      sessionID: context.sessionID,
      messageID: context.messageID,
      directory: context.directory,
      worktree: context.worktree,
    }))
  },
})
