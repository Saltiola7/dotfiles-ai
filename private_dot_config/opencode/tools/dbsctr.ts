import { tool } from "@opencode-ai/plugin"
import { attachRuntime, benchmarkResult, beginCycle, boundedCycleWorktree, cycleStatus, cycleTarget, fileDigest, fixedCommitInspect, gitDefaultBranch, gitRepositorySlug, historyCapture, historyTelemetry, improvementClaim, improvementStatus, improvementUpdate, incidentForget, incidentRegister, incidentScan, incidentUpdate, initiativeCycleCheck, initiativeReceipt, lifecycleAudit, phaseSpan, providerEvaluation, providerEvaluationSave, reconcileTarget, recordExecutionBenchmark, rememberCycleTarget, reviewComplete, reviewFederated, reviewFederatedSummary, reviewHistory, reviewHistorySave, reviewScan, runtimeHealth, validateExecutionDag, validateVmHandoffRequest, verifyVmHandoffParity, vmHandoff, vmHandoffInstance, vmHandoffTarget } from "../lib/dbsctr-runtime"

export const status = tool({
  description: "Read authoritative DBSCTR cycle status for the current or attached worktree.",
  args: {},
  async execute(_args, context) {
    return await cycleStatus(cycleTarget(context.sessionID, context.worktree))
  },
})

export const attach = tool({
  description: "Attach the current validated Build runtime to an active DBSCTR cycle worktree without relaunching OpenCode.",
  args: { worktree: tool.schema.string().optional() },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_attach", patterns: ["*"], always: [] })
    const target = await boundedCycleWorktree(context.worktree, args.worktree)
    const result = await attachRuntime(target, {
      sessionID: context.sessionID,
      messageID: context.messageID,
      directory: context.directory,
      worktree: context.worktree,
    })
    rememberCycleTarget(context.sessionID, target)
    return result
  },
})

export const runtime_health = tool({
  description: "Read normalized advisory Herdr health for the current OpenCode runtime.",
  args: {},
  async execute(_args, context) {
    return JSON.stringify(await runtimeHealth(context.worktree, {
      sessionID: context.sessionID,
      worktree: context.worktree,
    }))
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
    }, cycleTarget(context.sessionID, context.worktree))
  },
})

export const execution_dag = tool({
  description: "Validate a bounded read-only DBSCTR execution DAG and return concurrent or forced-serial authorization.",
  args: {
    mode: tool.schema.enum(["serial", "benchmark", "concurrent"]),
    completed: tool.schema.array(tool.schema.string()).max(100).optional().default([]),
    nodes: tool.schema.array(tool.schema.object({
      id: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
      depends_on: tool.schema.array(tool.schema.string()).max(100),
      operation: tool.schema.enum(["read", "readonly_qa", "reconcile"]),
      ownership_paths: tool.schema.array(tool.schema.string().min(1).max(512)).max(100),
    })).min(1).max(100),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_execution_dag", patterns: ["*"], always: [] })
    return await validateExecutionDag(args.nodes, args.completed, args.mode, cycleTarget(context.sessionID, context.worktree))
  },
})

export const execution_benchmark = tool({
  description: "Persist paired local execution evidence and activate concurrency only when the V3.24 threshold passes.",
  args: {
    fixture: tool.schema.object({
      id: tool.schema.string(), commit: tool.schema.string(), path: tool.schema.string(), blob: tool.schema.string(),
    }),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_execution_benchmark", patterns: ["*"], always: [] })
    return await recordExecutionBenchmark(args.fixture, cycleTarget(context.sessionID, context.worktree))
  },
})

export const audit = tool({
  description: "Inventory DBSCTR lifecycle artifacts at a fixed Git commit without changing files.",
  args: { commit: tool.schema.string().optional().default("HEAD") },
  async execute(args, context) {
    return await lifecycleAudit(cycleTarget(context.sessionID, context.worktree), args.commit)
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
    return await fixedCommitInspect(args, cycleTarget(context.sessionID, context.worktree))
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

export const incident_scan = tool({
  description: "Read registered incidents and bounded redacted failed-call signals without changing state.",
  args: {
    scope: tool.schema.enum(["global", "current"]).optional().default("global"),
    summaryOnly: tool.schema.boolean().optional().default(false),
  },
  async execute(args, context) {
    return await incidentScan(context.worktree, args.scope === "current" ? context.sessionID : undefined,
      args.summaryOnly)
  },
})

export const incident_register = tool({
  description: "Register the invoking OpenCode fork as one private incident.",
  args: {
    kind: tool.schema.enum(["defect", "friction", "behavior_gap", "capability_idea"]),
    title: tool.schema.string().min(11).max(128),
    summary: tool.schema.string().min(1).max(1024),
    signalIds: tool.schema.array(tool.schema.string().regex(/^[0-9a-f]{24}$/)).max(20),
    diagnostics: tool.schema.array(tool.schema.string().min(1).max(2048)).max(20),
    evidence: tool.schema.array(tool.schema.string().min(1).max(2048)).max(20),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_incident_register", patterns: ["*"], always: [],
      metadata: { kind: args.kind, signals: args.signalIds.length } })
    return await incidentRegister({ sessionID: context.sessionID, messageID: context.messageID,
      kind: args.kind, title: args.title, summary: args.summary, signalIDs: args.signalIds,
      diagnostics: args.diagnostics, evidence: args.evidence }, context.worktree)
  },
})

export const incident_update = tool({
  description: "Advance one private incident without changing repository state.",
  args: {
    incidentId: tool.schema.string().regex(/^[0-9a-f]{24}$/),
    state: tool.schema.enum(["open", "investigating", "fixing", "resolved", "dismissed"]),
    cycleId: tool.schema.string().optional(),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_incident_update", patterns: ["*"], always: [],
      metadata: { state: args.state } })
    return await incidentUpdate(context.sessionID, context.messageID, args.incidentId, args.state,
      context.worktree, args.cycleId)
  },
})

export const incident_forget = tool({
  description: "Delete one incident's private evidence while preserving its OpenCode fork.",
  args: { incidentId: tool.schema.string().regex(/^[0-9a-f]{24}$/) },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_incident_forget", patterns: ["*"], always: [],
      metadata: { incident: args.incidentId } })
    return await incidentForget(context.sessionID, context.messageID, args.incidentId, context.worktree)
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
    aggregateOnly: tool.schema.boolean().optional().default(false),
  },
  async execute(args, context) {
    return await reviewHistory(args, context.worktree, context.sessionID, context.messageID)
  },
})

export const review_federated = tool({
  description: "Capture and read bounded sanitized review history from the host and configured workspaces; transient private captures expire after 24 hours.",
  args: {
    after: tool.schema.number().int().min(0).optional(),
    before: tool.schema.number().int().min(0).optional(),
    methodRevision: tool.schema.string().regex(/^\d+(?:\.\d+)*$/).optional(),
    cycleId: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/).optional(),
    state: tool.schema.enum(["active", "blocked", "abandoned", "completed", "unknown"]).optional(),
    context: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/).optional(),
    projectDigest: tool.schema.string().regex(/^[0-9a-f]{64}$/).optional(),
    reviewedStatus: tool.schema.enum(["reviewed", "unreviewed"]).optional(),
    archiveOnly: tool.schema.boolean().optional().default(false),
    reviewSessions: tool.schema.enum(["only", "exclude"]).optional(),
    limit: tool.schema.number().int().min(1).max(100).optional().default(25),
    cursor: tool.schema.number().int().min(0).optional().default(0),
    sourceState: tool.schema.array(tool.schema.object({
      source_id: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/),
      capture_id: tool.schema.string().regex(/^[0-9a-f]{24}$/),
      snapshot: tool.schema.number().int().min(0),
      session_ceiling: tool.schema.number().int().min(0),
      part_ceiling: tool.schema.number().int().min(0),
      database_digest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
      exclusion_digest: tool.schema.string().regex(/^[0-9a-f]{64}$/).nullable(),
      query_digest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
      continuation: tool.schema.number().int().min(0).nullable(),
    })).min(1).max(33).optional(),
  },
  async execute(args, context) {
    return await reviewFederated(args, context.worktree, context.sessionID, context.messageID)
  },
})

export const lens_summary = tool({
  description: "Inspect every member of one immutable federated capture server-side and return bounded lens evidence.",
  args: {
    lens: tool.schema.enum(["correctness_safety", "reliability_recovery", "performance_cost",
      "operator_experience", "architecture_rnd_meta", "review_session_governance"]),
    reviewSessions: tool.schema.enum(["only", "exclude"]),
  },
  async execute(args, context) {
    return await reviewFederatedSummary(args.lens, args.reviewSessions, context.worktree,
      context.sessionID, context.messageID)
  },
})

export const vm_handoff = tool({
  description: "Only use as /dbsctr-improve's final approved step: launch its ledger-bound sanitized implementation handoff in the configured Build workspace. Never probe this tool.",
  args: {
    workerId: tool.schema.string().regex(/^dbsctr-[0-9a-f]{8}$/),
    proceed: tool.schema.literal(true),
    risk: tool.schema.enum(["routine", "elevated", "critical"]),
    summary: tool.schema.string().min(1).max(512),
    paths: tool.schema.array(tool.schema.string().min(1).max(512)
      .regex(/^(?!\/)(?!.*(?:^|\/)\.{1,2}(?:\/|$))(?!.*\/\/)(?!.*[\\\x00-\x1F\x7F])[^/]+(?:\/[^/]+)*$/)).min(1).max(100),
    validation: tool.schema.array(tool.schema.string().min(1).max(512)).min(1).max(50),
  },
  async execute(args, context) {
    await validateVmHandoffRequest(args, context.sessionID, context.worktree)
    const target = await vmHandoffTarget(context.worktree)
    const instance = await vmHandoffInstance(target, context.worktree)
    await context.ask({ permission: "dbsctr_vm_handoff", patterns: [`${target}:${instance}`], always: [] })
    await validateVmHandoffRequest(args, context.sessionID, context.worktree)
    await verifyVmHandoffParity(target, instance, context.worktree)
    await validateVmHandoffRequest(args, context.sessionID, context.worktree)
    return await vmHandoff({
      schema_version: 1, worker_id: args.workerId, proceed: true, target,
      risk: args.risk, summary: args.summary, paths: args.paths, validation: args.validation,
    }, instance, context.worktree)
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
    aggregateOnly: tool.schema.boolean().optional().default(false),
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

export const provider_evaluation = tool({
  description: "List report-only provider harness evaluations or replay one immutable report.",
  args: { reportId: tool.schema.string().regex(/^[0-9a-f]{24}$/).optional() },
  async execute(args, context) {
    return await providerEvaluation(args.reportId, context.worktree)
  },
})

export const provider_evaluation_save = tool({
  description: "Derive and persist one report-only five-cycle provider harness evaluation from a terminal federated capture.",
  args: {
    manifestDigest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
    rubricName: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
    rubricVersion: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
    rubricDigest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
    findings: tool.schema.array(tool.schema.string().min(1).max(512)).max(50),
    recommendations: tool.schema.array(tool.schema.string().min(1).max(512)).max(50),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_provider_evaluation_save", patterns: [args.manifestDigest], always: [] })
    return await providerEvaluationSave({ manifestDigest: args.manifestDigest,
      rubric: { name: args.rubricName, version: args.rubricVersion, digest: args.rubricDigest },
      findings: args.findings, recommendations: args.recommendations }, context.worktree)
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
  args: {
    summary: tool.schema.string().min(1).max(512),
    priority: tool.schema.enum(["P0", "P1", "P2", "P3"]),
    kind: tool.schema.enum(["fix", "feature", "process"]).optional().default("fix"),
    measurementPlan: tool.schema.object({
      hypothesis: tool.schema.string().min(1).max(512),
      baseline: tool.schema.string().min(1).max(512),
      metric: tool.schema.string().min(1).max(512),
      procedure: tool.schema.string().min(1).max(512),
      successThreshold: tool.schema.string().min(1).max(512),
      evidencePath: tool.schema.string().min(1).max(512),
    }).optional(),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_improvement_claim", patterns: ["*"], always: [] })
    return await improvementClaim(context.sessionID, args.summary, args.priority, context.worktree,
      args.kind, args.measurementPlan)
  },
})

export const improvement_update = tool({
  description: "Advance the current improvement claim and declare its exact repository-relative ownership.",
  args: {
    state: tool.schema.enum(["claimed", "discovery", "implementing", "draft_pr", "blocked", "merged", "closed", "abandoned"]),
    cycleId: tool.schema.string().optional(),
    paths: tool.schema.array(tool.schema.string().min(1).max(512)).max(100).optional().default([]),
    autonomous: tool.schema.boolean().optional().default(false),
    readiness: tool.schema.object({
      workerId: tool.schema.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/),
      opportunityId: tool.schema.string().regex(/^[0-9a-f]{64}$/),
      risk: tool.schema.enum(["routine", "elevated", "critical"]),
      materialQuestionsResolved: tool.schema.literal(true),
      evidenceDigest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
    }).optional(),
    discovery: tool.schema.object({
      interview: tool.schema.array(tool.schema.object({
        question: tool.schema.string().min(1).max(512),
        answer: tool.schema.string().min(1).max(512),
      })).min(1).max(20),
      assumptions: tool.schema.array(tool.schema.string().min(1).max(512)).max(20),
      citations: tool.schema.array(tool.schema.string().min(1).max(512)).max(20),
      risks: tool.schema.array(tool.schema.string().min(1).max(512)).max(20),
      evidenceDigest: tool.schema.string().regex(/^[0-9a-f]{64}$/),
    }).optional(),
  },
  async execute(args, context) {
    await context.ask({ permission: "dbsctr_improvement_update", patterns: ["*"], always: [] })
    return await improvementUpdate(context.sessionID, {
      state: args.state,
      cycleID: args.cycleId,
      paths: args.paths,
      autonomous: args.autonomous,
      readiness: args.readiness,
      discovery: args.discovery,
    }, context.worktree, true)
  },
})

type InitiativeLaunchArgs = {
  manifestPath: string
  sliceId: string
  proceed: true
  cycleId: string
  context: string
  risk: "routine" | "elevated" | "critical"
  deliveryIntent: "local" | "merge" | "release" | "deploy" | "draft_pr"
  planPath: string
  githubAccount?: string
  githubRepository?: string
  initiativeSourceRepository?: string
  targetRepository?: string
}

type InitiativeToolContext = {
  worktree: string
  directory: string
  sessionID: string
  messageID: string
  ask: (request: { permission: string; patterns: string[]; always: string[] }) => Promise<unknown>
}

async function launchInitiative(args: InitiativeLaunchArgs, context: InitiativeToolContext) {
  const source = args.initiativeSourceRepository ?? context.worktree
  const receipt = await initiativeReceipt(args.manifestPath, args.sliceId, source)
  if (receipt.context !== args.context)
    throw new Error("Initiative receipt context does not match the requested DBSCTR context")
  const sourceRepository = await gitRepositorySlug(source)
  if (sourceRepository.toLowerCase() !== receipt.coordinator_repository.toLowerCase())
    throw new Error("Initiative source does not match the coordinator repository")
  const target = args.targetRepository ?? context.worktree
  const targetRepository = await gitRepositorySlug(target)
  if (targetRepository.toLowerCase() !== receipt.repository.toLowerCase())
    throw new Error("Initiative context home does not match the target repository")
  const baseBranch = await gitDefaultBranch(target)
  await initiativeCycleCheck(args.cycleId, receipt, target)
  const planDigest = await fileDigest(args.planPath, target)
  const approval = JSON.stringify({
    initiative_id: receipt.initiative_id,
    slice_id: receipt.slice_id,
    manifest_digest: receipt.manifest_digest,
    manifest_blob: receipt.manifest_blob,
    manifest_commit: receipt.manifest_commit,
    coordinator_repository: receipt.coordinator_repository,
    repository: receipt.repository,
    execution_owner: receipt.execution_owner,
    target_repository: targetRepository,
    cycle_id: args.cycleId,
    context: args.context,
    risk: args.risk,
    delivery_intent: args.deliveryIntent,
    plan_path: args.planPath,
    plan_digest: planDigest,
    base_branch: baseBranch,
    github_account: args.githubAccount ?? null,
    github_repository: args.githubRepository ?? null,
  })
  await context.ask({
    permission: "dbsctr_initiative_launch",
    patterns: [approval],
    always: [],
  })
  const current = await initiativeReceipt(args.manifestPath, args.sliceId, source)
  if (JSON.stringify(current) !== JSON.stringify(receipt))
    throw new Error("Initiative readiness changed after approval; request approval for the new digest")
  if ((await gitRepositorySlug(source)).toLowerCase() !== sourceRepository.toLowerCase())
    throw new Error("Initiative source repository changed after approval")
  if ((await gitRepositorySlug(target)).toLowerCase() !== targetRepository.toLowerCase())
    throw new Error("Initiative target repository changed after approval")
  await initiativeCycleCheck(args.cycleId, receipt, target)
  if (await fileDigest(args.planPath, target) !== planDigest)
    throw new Error("DBSCTR applicability plan changed after approval")
  if (await gitDefaultBranch(target) !== baseBranch)
    throw new Error("Initiative target default branch changed after approval")
  return JSON.stringify(await beginCycle({ ...args, baseBranch }, target, true, process.env, {
    sessionID: context.sessionID,
    messageID: context.messageID,
    directory: context.directory,
    worktree: context.worktree,
  }, receipt, source, { planDigest, targetRepository }))
}

export const begin = tool({
  description: "Create an isolated DBSCTR branch/worktree, or launch an exactly approved Initiative slice when initiative is provided. Protected-base merge delivery becomes draft_pr; githubRepository is derived from origin.",
  args: {
    cycleId: tool.schema.string(),
    context: tool.schema.string(),
    risk: tool.schema.enum(["routine", "elevated", "critical"]),
    deliveryIntent: tool.schema.enum(["local", "merge", "release", "deploy", "draft_pr"]),
    planPath: tool.schema.string(),
    githubAccount: tool.schema.string().optional(),
    githubRepository: tool.schema.string().optional(),
    baseBranch: tool.schema.string().optional(),
    launch: tool.schema.boolean().optional().default(false),
    initiative: tool.schema.object({
      manifestPath: tool.schema.string(),
      sliceId: tool.schema.string(),
      proceed: tool.schema.literal(true),
      initiativeSourceRepository: tool.schema.string().optional(),
      targetRepository: tool.schema.string().optional(),
    }).optional(),
  },
  async execute(args, context) {
    if (args.initiative !== undefined)
      return await launchInitiative({ ...args, ...args.initiative }, context)
    return JSON.stringify(await beginCycle(args, context.worktree, args.launch, process.env, {
      sessionID: context.sessionID,
      messageID: context.messageID,
      directory: context.directory,
      worktree: context.worktree,
    }))
  },
})

export const initiative_launch = tool({
  description: "Validate one ready Initiative slice, require exact approval, and launch its isolated DBSCTR Build fork.",
  args: {
    manifestPath: tool.schema.string(),
    sliceId: tool.schema.string(),
    proceed: tool.schema.literal(true),
    cycleId: tool.schema.string(),
    context: tool.schema.string(),
    risk: tool.schema.enum(["routine", "elevated", "critical"]),
    deliveryIntent: tool.schema.enum(["local", "merge", "release", "deploy", "draft_pr"]),
    planPath: tool.schema.string(),
    githubAccount: tool.schema.string().optional(),
    githubRepository: tool.schema.string().optional(),
    initiativeSourceRepository: tool.schema.string().optional(),
    targetRepository: tool.schema.string().optional(),
  },
  async execute(args, context) {
    return await launchInitiative(args, context)
  },
})

export const reconcile = tool({
  description: "Preview or prepare explicit reconciliation with the current cycle's advanced upstream, optionally in a linked worktree of the current repository.",
  args: {
    mode: tool.schema.enum(["preview", "prepare"]),
    worktree: tool.schema.string().optional(),
  },
  async execute(args, context) {
    return JSON.stringify(await reconcileTarget(args.mode, cycleTarget(context.sessionID, context.worktree), args.worktree))
  },
})
