import { tool } from "@opencode-ai/plugin"
import { beginCycle, cycleStatus, fixedCommitInspect, lifecycleAudit, reviewComplete, reviewHistory, reviewHistorySave, reviewScan } from "../lib/dbsctr-runtime"

export const status = tool({
  description: "Read authoritative DBSCTR cycle status for the current worktree.",
  args: {},
  async execute(_args, context) {
    return await cycleStatus(context.worktree)
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
  },
  async execute(args, context) {
    return await reviewScan(args.limit, args.cursor, args.snapshot, context.worktree, args.sessionCeiling, args.partCeiling, args.databaseDigest)
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
      limit: args.limit,
      cursor: args.cursor,
      decision: args.decision,
      notes: args.notes,
      findings: args.findings,
      scorecards: args.scorecards,
      trends: args.trends,
      proposals: args.proposals,
      caveats: args.caveats,
    }, context.worktree)
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
    limit: tool.schema.number().int().min(1).max(100).optional().default(100),
    cursor: tool.schema.number().int().min(0).optional().default(0),
  },
  async execute(args, context) {
    return await reviewHistory(args, context.worktree)
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
      findings: args.findings,
      scorecards: args.scorecards,
      trends: args.trends,
      proposals: args.proposals,
      caveats: args.caveats,
    }, context.worktree)
  },
})

export const begin = tool({
  description: "Create an isolated DBSCTR branch/worktree and optionally launch OpenCode there through Herdr.",
  args: {
    cycleId: tool.schema.string(),
    context: tool.schema.string(),
    risk: tool.schema.enum(["routine", "elevated", "critical"]),
    deliveryIntent: tool.schema.enum(["local", "merge", "release", "deploy"]),
    planPath: tool.schema.string(),
    launch: tool.schema.boolean().optional().default(false),
  },
  async execute(args, context) {
    await context.ask({
      permission: "dbsctr_begin",
      patterns: ["*"],
      always: [],
      metadata: {
        cycleId: args.cycleId,
        context: args.context,
        risk: args.risk,
        deliveryIntent: args.deliveryIntent,
      },
    })
    return JSON.stringify(await beginCycle(args, context.worktree, args.launch, process.env, {
      sessionID: context.sessionID,
      directory: context.directory,
      worktree: context.worktree,
    }))
  },
})
