import { Database } from "bun:sqlite"
import { createHash, randomUUID } from "node:crypto"
import { access, lstat, realpath } from "node:fs/promises"
import { homedir } from "node:os"
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path"
import { continuationRequest, cycleStatus, forgetCycleTarget, harnessActivation, rememberCycleTarget, run } from "./dbsctr-runtime"
import type { CycleSelection } from "./dbsctr-runtime"

export type RuntimeContext = {
  sessionID: string, messageID: string, callID?: string, directory: string, worktree: string,
  primary?: boolean, agentID?: string,
  ask?: (request: { permission: string, patterns: string[], always: string[], metadata?: object }) => Promise<unknown>,
}

const registered = new Set<string>()
const observedStores = new Set<string>()
const commonDirectories = new Map<string, Promise<string>>()
const opaque = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/
const digest = /^[0-9a-f]{64}$/
const reasons = new Set(["ok", "not_enrolled", "state_busy", "invalid_identity", "invalid_state", "registry_mismatch",
  "repository_mismatch", "invalid_target", "capability_unavailable", "continuation_admission_required", "generation_changed",
  "writer_occupied", "operation_in_flight", "recovery_required", "provider_confirmation_required", "revision_incompatible", "approval_required"])
const states = new Set(["reader_only", "owned", "draining", "recovery_required", "closed"])
const actions = new Set(["none", "enroll", "select_target", "switch_to_build", "confirm_provider", "request_handover",
  "wait_for_completion", "confirm_quiescence", "qualify_runtime"])
const fields = ["schema_version", "ok", "reason", "cycle_id", "state", "generation", "writer_relation", "activation_changes",
  "next_action", "approval_binding", "operation_id", "event_id", "target_worktree_id"].sort().join(",")

export function registerAdapter(worktree: string) {
  registered.add(resolve(worktree))
}

export async function storeExists(worktree: string) {
  const key = resolve(worktree)
  let directory = commonDirectories.get(key)
  if (!directory) {
    directory = run(["git", "rev-parse", "--git-common-dir"], key).then(value => resolve(key, value.trim()))
    commonDirectories.set(key, directory)
  }
  try {
    await access(join(await directory, "dbsctr", "continuation"))
    observedStores.add(key)
    return true
  } catch (error: any) {
    if (observedStores.has(key)) throw Error("continuation_state_unavailable")
    if (error.code === "ENOENT") return false
    commonDirectories.delete(key)
    if (String(error.message).includes("not a git repository")) return false
    throw Error("continuation_state_unavailable")
  }
}

export async function explicitCycleMutation(home: string, tool: string, args: any) {
  const names: string[] = []
  if (["write", "edit"].includes(tool) && typeof args.filePath === "string") names.push(args.filePath)
  if (["bash", "shell"].includes(tool)) names.push(args.workdir ?? home)
  if (tool === "apply_patch" && typeof args.patchText === "string") {
    for (const match of args.patchText.matchAll(/^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+)$/gm)) names.push(match[1])
  }
  const roots = new Set<string>()
  for (const name of names) {
    let current = resolve(home, name)
    while (true) {
      const info = await lstat(current).catch(() => undefined)
      if (info) {
        const directory = info.isDirectory() ? current : dirname(current)
        try { roots.add((await run(["git", "rev-parse", "--show-toplevel"], directory)).trim()) }
        catch (error: any) {
          if (!String(error.message).includes("not a git repository")) throw Error("continuation_invalid_target")
        }
        break
      }
      if (dirname(current) === current) break
      current = dirname(current)
    }
  }
  for (const root of roots) {
    // Unrecorded Discovery worktrees stay usable; recorded cycles require selection.
    const record = JSON.parse(await run(["dbsctrctl", "status", "--json"], root))
    if (record !== null) return true
  }
  return false
}

export function nativeContext(home: {worktree: string, directory: string}, input: {sessionID: string, callID: string}): RuntimeContext {
  if (!opaque.test(input.sessionID) || !opaque.test(input.callID)) throw Error("continuation_invalid_identity")
  const path = join(process.env.XDG_DATA_HOME ?? join(homedir(), ".local/share"), "opencode", "opencode.db")
  let db: Database | undefined
  try {
    db = new Database(path, {readonly: true})
    const rows = db.query("SELECT p.message_id,s.parent_id,s.agent FROM part p JOIN session s ON s.id=p.session_id "
      + "WHERE p.session_id=? AND json_extract(p.data,'$.callID')=? LIMIT 2")
      .all(input.sessionID, input.callID) as {message_id: string, parent_id: string | null, agent: string}[]
    if (rows.length !== 1 || !opaque.test(rows[0].message_id)) throw Error("identity")
    return {...home, ...input, messageID: rows[0].message_id, primary: rows[0].parent_id === null, agentID: rows[0].agent}
  } catch {
    throw Error("continuation_invalid_identity")
  } finally {
    db?.close()
  }
}

function envelope(context: RuntimeContext, worktree: string | undefined, extra: object) {
  return {
    schema_version: 1, session_id: context.sessionID, message_id: context.messageID,
    runtime_worktree: context.worktree, runtime_directory: context.directory,
    harness_activation: harnessActivation, ...(worktree === undefined ? {} : {worktree}), ...extra,
  }
}

export async function request(context: RuntimeContext, action: string, worktree?: string, extra: object = {}) {
  let value: any
  try {
    value = JSON.parse(await continuationRequest(action, envelope(context, worktree, extra), context.worktree))
  } catch {
    throw Error("continuation_helper_unavailable")
  }
  if (!value || Object.keys(value).sort().join(",") !== fields || value.schema_version !== 1
      || typeof value.ok !== "boolean" || !reasons.has(value.reason)
      || value.cycle_id !== null && (typeof value.cycle_id !== "string" || !opaque.test(value.cycle_id))
      || value.state !== null && !states.has(value.state)
      || !Number.isSafeInteger(value.generation) || value.generation < 0
      || !["none", "self", "other"].includes(value.writer_relation) || !actions.has(value.next_action)
      || !Array.isArray(value.activation_changes) || value.activation_changes.some((key: unknown) =>
        !["schema_version", "provider_id", "model_id", "agent_id", "core_revision", "overlay_revision"].includes(key as string))
      || value.operation_id !== null && !/^[0-9a-f]{32}$/.test(value.operation_id)
      || value.event_id !== null && (!Number.isSafeInteger(value.event_id) || value.event_id < 1)
      || value.target_worktree_id !== null && !/^[0-9a-f]{16}$/.test(value.target_worktree_id))
    throw Error("continuation_invalid_response")
  const binding = value.approval_binding
  if (binding !== null && (typeof binding !== "object" || Array.isArray(binding)
      || Object.keys(binding).sort().join(",") !== ["action", "cycle_id", "worktree_id", "generation", "state_digest",
        "record_digest", "session_key", "activation_digest", "target_session_id", "mode"].sort().join(",")
      || !["check", "enroll", "attach", "admit", "finish", "handover", "recover"].includes(binding.action)
      || binding.cycle_id !== value.cycle_id || !/^[0-9a-f]{16}$/.test(binding.worktree_id)
      || !Number.isSafeInteger(binding.generation) || binding.generation < 0
      || ["state_digest", "record_digest", "session_key", "activation_digest"].some(key => !digest.test(binding[key]))
      || binding.target_session_id !== null && !opaque.test(binding.target_session_id)
      || ![null, "reader", "writer"].includes(binding.mode))) throw Error("continuation_invalid_response")
  return value
}

export function requireSuccess(value: any) {
  if (!value.ok) throw Error(`continuation_${value.reason}`)
  return value
}

const adapterRevision = "checkout-continuation-opencode-2"
const v2Reasons = new Set([...reasons, "source_unavailable", "branch_mismatch", "registration_missing",
  "registration_changed", "binding_required", "route_changed", "protocol_unavailable", "capacity_unavailable"])
const v2Actions = new Set([...actions, "bind", "release", "restore_target"])
const v2Fields = ["schema_version", "ok", "reason", "cycle_id", "state", "generation", "writer_relation", "binding_id",
  "route_version", "activation_changes", "checks", "next_action", "expected", "operation_id", "event_id", "request_id",
  "replayed", "local_target"]
const expectedFields = ["action", "cycle_id", "binding_id", "generation", "route_version", "state_digest", "record_digest",
  "registration_digest", "session_key", "activation_digest", "mode", "target_session_id"]
const operationActions = new Set(["check", "enroll", "bind", "attach", "admit", "finish", "handover", "recover", "release", "resolve"])
const activationFields = new Set(["schema_version", "provider_id", "model_id", "agent_id", "core_revision", "overlay_revision"])
const exact = (value: any, keys: string[]) => value !== null && typeof value === "object" && !Array.isArray(value)
  && Object.keys(value).sort().join(",") === [...keys].sort().join(",")
const counter = (value: any) => Number.isSafeInteger(value) && value >= 0
const matches = (pattern: RegExp, value: any) => typeof value === "string" && pattern.test(value)
const identifier = /^[0-9a-f]{32}$/

export function validateV2(value: any, action: string) {
  if (!exact(value, v2Fields) || value.schema_version !== 2 || typeof value.ok !== "boolean"
      || !v2Reasons.has(value.reason) || !v2Actions.has(value.next_action) || typeof value.replayed !== "boolean"
      || value.cycle_id !== null && !matches(opaque, value.cycle_id)
      || value.state !== null && !states.has(value.state)
      || value.generation !== null && !counter(value.generation)
      || value.route_version !== null && !counter(value.route_version)
      || ![null, "self", "other", "none"].includes(value.writer_relation)
      || value.binding_id !== null && !matches(identifier, value.binding_id)
      || value.operation_id !== null && !matches(identifier, value.operation_id)
      || value.event_id !== null && (!counter(value.event_id) || value.event_id === 0)
      || value.request_id !== null && !matches(opaque, value.request_id)
      || !Array.isArray(value.activation_changes) || value.activation_changes.some((key: any) => !activationFields.has(key))
      || !exact(value.checks, ["source", "target", "ownership", "storage"])) throw Error("continuation_invalid_response")
  for (const item of Object.values(value.checks) as any[]) {
    if (!exact(item, ["status", "reason"]) || !["available", "unavailable", "not_requested"].includes(item.status)
        || (item.status === "unavailable" ? !v2Reasons.has(item.reason) || item.reason === "ok" : item.reason !== null))
      throw Error("continuation_invalid_response")
  }
  const expected = value.expected
  if (expected !== null) {
    if (!exact(expected, expectedFields) || !operationActions.has(expected.action)
        || expected.cycle_id !== value.cycle_id || expected.binding_id !== value.binding_id
        || !counter(expected.generation) || expected.generation !== value.generation
        || !counter(expected.route_version) || expected.route_version !== value.route_version
        || ![null, "reader", "writer"].includes(expected.mode)
        || expected.target_session_id !== null && !matches(opaque, expected.target_session_id))
      throw Error("continuation_invalid_response")
    for (const key of ["state_digest", "record_digest", "registration_digest", "session_key", "activation_digest"]) {
      if (expected[key] === null && ["record_digest", "registration_digest"].includes(key)
          && ["release", "recover"].includes(expected.action)) continue
      if (!matches(digest, expected[key])) throw Error("continuation_invalid_response")
    }
  }
  if (!value.ok && (expected !== null || value.operation_id !== null || value.event_id !== null || value.local_target !== null))
    throw Error("continuation_invalid_response")
  if (value.local_target !== null && (action !== "resolve" || !value.ok
      || !exact(value.local_target, ["path", "binding_id", "registration_digest"])
      || typeof value.local_target.path !== "string" || !isAbsolute(value.local_target.path)
      || /[\x00-\x1f\x7f]/.test(value.local_target.path)
      || !matches(identifier, value.local_target.binding_id) || value.local_target.binding_id !== value.binding_id
      || !matches(digest, value.local_target.registration_digest)
      || value.local_target.registration_digest !== expected?.registration_digest)) throw Error("continuation_invalid_response")
  return value
}

export async function requestV2(context: RuntimeContext, action: string, extra: object = {}) {
  if (!operationActions.has(action)) throw Error("continuation_invalid_action")
  let raw: string
  try {
    raw = await continuationRequest("v2", envelope(context, undefined, {schema_version: 2, action, ...extra}), context.worktree)
  } catch { throw Error("continuation_helper_unavailable") }
  if (Buffer.byteLength(raw) > 65536) throw Error("continuation_invalid_response")
  let value: any
  try { value = JSON.parse(raw) } catch { throw Error("continuation_protocol_unavailable") }
  return validateV2(value, action)
}

function publicResult(value: any) {
  const {local_target: _privateTarget, ...result} = value
  return result
}

function expectedFor(value: any, action: string) {
  requireSuccess(value)
  if (value.next_action === "switch_to_build") throw Error("continuation_switch_to_build")
  if (!value.expected || value.expected.action !== action) throw Error("continuation_approval_required")
  return value.expected
}

function requestID(context: RuntimeContext, action: string) {
  if (!context.callID || !opaque.test(context.callID)) throw Error("continuation_invalid_identity")
  return createHash("sha256").update(`${context.sessionID}\0${context.messageID}\0${context.callID}\0${action}`).digest("hex")
}

// Retain bounded exact call bodies for transport retries; the core owns durable replay authority.
const controlBodies = new Map<string, {signature: string, body: Promise<any>, active: number}>()
async function mutate(context: RuntimeContext, action: string, parameters: object,
                      prepare: () => Promise<object>) {
  const id = requestID(context, action)
  const signature = JSON.stringify(parameters)
  let entry = controlBodies.get(id)
  if (entry && entry.signature !== signature) throw Error("continuation_invalid_identity")
  if (!entry) {
    if (controlBodies.size >= 100) {
      const oldest = [...controlBodies].find(([, value]) => value.active === 0)
      if (!oldest) throw Error("continuation_state_busy")
      controlBodies.delete(oldest[0])
    }
    entry = {signature, active: 0, body: prepare().then(fields => ({...fields, request_id: id}))}
    controlBodies.set(id, entry)
    entry.body.catch(() => { if (controlBodies.get(id) === entry) controlBodies.delete(id) })
  }
  entry.active++
  try { return requireSuccess(await requestV2(context, action, await entry.body)) }
  finally { entry.active-- }
}

export function selection(value: any): CycleSelection {
  if (!matches(opaque, value.cycle_id) || !counter(value.route_version)) throw Error("continuation_invalid_response")
  return {cycleID: value.cycle_id, routeVersion: value.route_version}
}

export async function executionState(context: RuntimeContext) {
  const paired = requireSuccess(await requestV2(context, "check"))
  if (paired.cycle_id === null || paired.binding_id !== null) return {...paired, protocol: 2}
  if (paired.checks.target.status !== "available") throw Error(`continuation_${paired.checks.target.reason}`)
  return {...requireSuccess(await request(context, "check")), protocol: 1, route_version: paired.route_version}
}

export async function executionTarget(context: RuntimeContext, state: any) {
  if (state.protocol === 1) return targetPath(context, state.target_worktree_id, selection(state))
  const prepared = await requestV2(context, "check", {for_action: "resolve"})
  const expected = expectedFor(prepared, "resolve")
  if (prepared.cycle_id !== state.cycle_id || prepared.route_version !== state.route_version
      || prepared.generation !== state.generation || prepared.binding_id !== state.binding_id)
    throw Error("continuation_route_changed")
  const resolved = requireSuccess(await requestV2(context, "resolve", {expected}))
  if (!resolved.local_target) throw Error("continuation_invalid_response")
  const target = await realpath(resolved.local_target.path)
  if (target !== resolved.local_target.path) throw Error("continuation_invalid_target")
  state.resolvedRegistration = resolved.local_target.registration_digest
  rememberCycleTarget(context.sessionID, target, selection(resolved))
  return target
}

export async function admit(context: RuntimeContext, state: any, target: string, kind: string) {
  if (state.protocol === 1) return requireSuccess(await request(context, "admit", target, {
    generation: state.generation, call_id: context.callID, operation_class: kind,
  }))
  const prepared = await requestV2(context, "check", {for_action: "admit"})
  const expected = expectedFor(prepared, "admit")
  if (prepared.cycle_id !== state.cycle_id || prepared.route_version !== state.route_version
      || prepared.generation !== state.generation || prepared.binding_id !== state.binding_id
      || expected.registration_digest !== state.resolvedRegistration)
    throw Error("continuation_route_changed")
  return requireSuccess(await requestV2(context, "admit", {
    expected, call_id: context.callID, operation_class: kind,
  }))
}

export async function finish(context: RuntimeContext, protocol: number, target: string, operation: string,
                             outcome: "completed" | "native_error" = "completed") {
  return requireSuccess(protocol === 2
    ? await requestV2(context, "finish", {operation_id: operation, outcome})
    : await request(context, "finish", target, {operation_id: operation, outcome}))
}

export async function finishFailedFile(context: RuntimeContext, operationId: string, worktree?: string) {
  requireAdapter(context)
  if (!matches(identifier, operationId)) throw Error("continuation_invalid_identity")
  const result = requireSuccess(await requestV2(context, "finish", {
    operation_id: operationId, outcome: "native_error", ...(worktree === undefined ? {} : {worktree}),
  }))
  if (result.state === "closed") forgetCycleTarget(context.sessionID, selection(result))
  return {...publicResult(result), completion_class: "native_error"}
}

export async function preflight(context: RuntimeContext, worktree?: string) {
  const adapter_available = registered.has(resolve(context.worktree))
  try {
    const value = await requestV2(context, "check", worktree === undefined ? {} : {worktree})
    return {...publicResult(value), adapter_available, adapter_revision: adapterRevision,
      capabilities: {protocol: 2, bind: adapter_available, recover: adapter_available, release: adapter_available}}
  } catch {
    return {schema_version: 2, ok: false, reason: "capability_unavailable", cycle_id: null, state: null,
      generation: null, writer_relation: null, activation_changes: [], next_action: "qualify_runtime",
      expected: null, operation_id: null, event_id: null, binding_id: null, route_version: null,
      request_id: null, replayed: false, checks: {source: {status: "not_requested", reason: null},
        target: {status: "unavailable", reason: "capability_unavailable"},
        ownership: {status: "unavailable", reason: "capability_unavailable"},
        storage: {status: "unavailable", reason: "capability_unavailable"}},
      adapter_available, adapter_revision: adapterRevision,
      capabilities: {protocol: null, bind: false, recover: false, release: false}}
  }
}

export async function diagnosticRoot(context: RuntimeContext) {
  const state = await preflight(context)
  if (!state.ok || state.cycle_id === null || state.checks.target.status !== "available") return context.worktree
  try { return await executionTarget(context, await executionState(context)) }
  catch { return context.worktree }
}

export async function diagnosticStatus(context: RuntimeContext) {
  const state = await preflight(context)
  if (!state.ok || state.cycle_id !== null && (state.checks.target.status !== "available"
      || state.next_action === "switch_to_build")) return JSON.stringify(state)
  try {
    const target = state.cycle_id === null ? context.worktree : await executionTarget(context, await executionState(context))
    const record = await cycleStatus(target)
    return state.cycle_id !== null && record.trim() === "null" ? JSON.stringify(await preflight(context)) : record
  } catch { return JSON.stringify(await preflight(context)) }
}

async function storageRequest(context: RuntimeContext, action: string, worktree: string, extra: object = {}) {
  let value: any
  try {
    value = JSON.parse(await continuationRequest(action, envelope(context, worktree, extra), context.worktree))
  } catch { throw Error("continuation_storage_unavailable") }
  if (!value || Object.keys(value).sort().join(",") !== "binding,ok,reason,recovered,schema_version"
      || value.schema_version !== 1 || typeof value.ok !== "boolean" || typeof value.recovered !== "boolean"
      || !["ok", "invalid_identity", "invalid_target", "invalid_state", "state_busy", "approval_required",
        "capacity_unavailable", "recovery_incomplete"].includes(value.reason)) throw Error("continuation_invalid_response")
  const binding = value.binding
  if (binding !== null && (typeof binding !== "object" || Array.isArray(binding)
      || Object.keys(binding).sort().join(",") !== ["action", "cycle_id", "worktree_id", "repository_digest",
        "actor_digest", "activation_digest", "record_digest", "storage_digest"].sort().join(",")
      || binding.action !== "storage-recover" || !opaque.test(binding.cycle_id)
      || !/^[0-9a-f]{16}$/.test(binding.worktree_id)
      || ["repository_digest", "actor_digest", "activation_digest", "record_digest", "storage_digest"].some(key => !digest.test(binding[key]))))
    throw Error("continuation_invalid_response")
  return requireSuccess(value)
}

export async function targetPath(context: RuntimeContext, id: string, selected?: CycleSelection) {
  const [initial, listing] = await Promise.all([
    run(["git", "rev-list", "--max-parents=0", "HEAD"], context.worktree),
    run(["git", "worktree", "list", "--porcelain"], context.worktree),
  ])
  if (initial.trim().split("\n").length !== 1) throw Error("continuation_invalid_target")
  const matches = listing.split("\n\n").flatMap(block => {
    const lines = block.split("\n")
    const path = lines.find(line => line.startsWith("worktree "))?.slice(9)
    const branch = lines.find(line => line.startsWith("branch refs/heads/"))?.slice(18) ?? "detached"
    const identity = createHash("sha256").update(`${initial.trim()}\0${branch}`).digest("hex").slice(0, 16)
    return path && identity === id ? [path] : []
  })
  if (matches.length !== 1) throw Error("continuation_invalid_target")
  const target = await realpath(matches[0])
  rememberCycleTarget(context.sessionID, target, selected)
  return target
}

async function approval(context: RuntimeContext, permission: string, binding: any) {
  if (!binding || !context.ask) throw Error("continuation_approval_required")
  await context.ask({permission, patterns: [JSON.stringify(binding)], always: [], metadata: {
    action: binding.action, quiescenceRequired: ["enroll", "bind", "recover", "handover", "storage-recover"].includes(binding.action),
  }})
  return {receipt_id: randomUUID(), binding}
}

function requireAdapter(context: RuntimeContext) {
  if (!registered.has(resolve(context.worktree))) throw Error("continuation_adapter_unavailable: restart and reopen this conversation")
}

export async function attach(context: RuntimeContext, worktree?: string, mode = "writer") {
  requireAdapter(context)
  const paired = requireSuccess(await requestV2(context, "check", worktree === undefined ? {} : {worktree}))
  if (paired.next_action === "switch_to_build") throw Error("continuation_switch_to_build")
  if (paired.binding_id !== null) {
    const extra = {mode, ...(worktree === undefined ? {} : {worktree})}
    const attached = await mutate(context, "attach", extra, async () => {
      const prepared = await requestV2(context, "check", {for_action: "attach", ...extra})
      const expected = expectedFor(prepared, "attach")
      const consent = prepared.activation_changes.includes("provider_id")
        ? await approval(context, "dbsctr_continuation_provider", expected) : undefined
      return {...extra, expected, ...(consent ? {approval: consent} : {})}
    })
    await executionTarget(context, {...attached, protocol: 2})
    return publicResult(attached)
  }
  let state = requireSuccess(await request(context, "check", worktree, {action: "enroll"}))
  if (state.cycle_id === null) throw Error("continuation_select_target")
  if (state.reason === "not_enrolled") {
    const consent = await approval(context, "dbsctr_continuation_enroll", state.approval_binding)
    requireSuccess(await request(context, "enroll", worktree, {approval: consent}))
  }
  state = requireSuccess(await request(context, "check", worktree, {action: "attach", mode}))
  let consent: object | undefined
  if (state.activation_changes.includes("provider_id"))
    consent = await approval(context, "dbsctr_continuation_provider", state.approval_binding)
  const attached = requireSuccess(await request(context, "attach", worktree, {
    mode, generation: state.generation, ...(consent ? {approval: consent} : {}),
  }))
  const selected = requireSuccess(await requestV2(context, "check"))
  await targetPath(context, attached.target_worktree_id, selection(selected))
  return attached
}

export async function bind(context: RuntimeContext, worktree: string) {
  requireAdapter(context)
  const state = requireSuccess(await requestV2(context, "check", {worktree}))
  if (state.next_action === "switch_to_build") throw Error("continuation_switch_to_build")
  if (state.binding_id !== null) return publicResult(state)
  if (state.writer_relation !== "none" || state.next_action === "confirm_quiescence"
      || ["owned", "draining", "recovery_required"].includes(state.state)) throw Error("continuation_recovery_required")
  const action = state.state === null ? "enroll" : "bind"
  const prepared = await requestV2(context, "check", {worktree, for_action: action})
  const expected = expectedFor(prepared, action)
  const consent = await approval(context, `dbsctr_continuation_${action}`, expected)
  return publicResult(requireSuccess(await requestV2(context, action, {
    worktree, expected, request_id: requestID(context, action), approval: consent,
  })))
}

export async function release(context: RuntimeContext) {
  requireAdapter(context)
  const released = await mutate(context, "release", {}, async () => {
    const prepared = await requestV2(context, "check", {for_action: "release"})
    return {expected: expectedFor(prepared, "release")}
  })
  forgetCycleTarget(context.sessionID, selection(released))
  return publicResult(released)
}

export async function recover(context: RuntimeContext, worktree?: string, targetSessionId?: string) {
  requireAdapter(context)
  const action = targetSessionId === undefined ? "recover" : "handover"
  const fields = targetSessionId === undefined ? {} : {target_session_id: targetSessionId}
  const target = worktree === undefined ? {} : {worktree}
  const result = await mutate(context, action, {...target, ...fields}, async () => {
    let state = await requestV2(context, "check", {for_action: action, ...target, ...fields})
    if (!state.ok && state.reason === "invalid_state" && action === "recover") {
      if (!worktree) throw Error("continuation_select_target_for_storage_recovery")
      const snapshot = await storageRequest(context, "storage-check", worktree)
      const consent = await approval(context, "dbsctr_continuation_storage_recover", snapshot.binding)
      await storageRequest(context, "storage-recover", worktree, {approval: consent})
      state = await requestV2(context, "check", {for_action: action, ...target, ...fields})
    }
    const expected = expectedFor(state, action)
    const consent = await approval(context, `dbsctr_continuation_${action}`, expected)
    return {...(action === "recover" ? target : {}), ...fields, expected, approval: consent}
  })
  return publicResult(result)
}

function inside(root: string, path: string) {
  const name = relative(root, path)
  return name === "" || name !== ".." && !name.startsWith(`..${sep}`) && !isAbsolute(name)
}

export async function childRead(context: RuntimeContext, tool: string, args: any) {
  if (!["builder-openai", "builder-vertex"].includes(context.agentID ?? "") || !["read", "glob", "grep", "list"].includes(tool)) return
  const path = await realpath(resolve(context.directory, tool === "read" ? args.filePath : args.path ?? "."))
  const own = await realpath(context.worktree === "/" ? context.directory : context.worktree)
  if (inside(own, path)) return
  const configured = process.env.DBSCTR_WORKTREE_ROOT ?? join(homedir(), ".local/state/dbsctr/worktrees")
  const registry = await realpath(configured).catch(() => resolve(configured))
  if (inside(registry, path)) throw Error("continuation_child_external_read")
  const linked = await run(["git", "worktree", "list", "--porcelain"], own)
  for (const line of linked.split("\n")) {
    if (!line.startsWith("worktree ")) continue
    const root = await realpath(line.slice("worktree ".length)).catch(() => undefined)
    if (root && root !== own && inside(root, path)) throw Error("continuation_child_external_read")
  }
}

export async function cyclePath(home: string, target: string, value: string, write = false) {
  if (typeof value !== "string" || /[\x00-\x1f\x7f]/.test(value)) throw Error("continuation_invalid_path")
  const original = resolve(home, value)
  const path = inside(home, original) ? resolve(target, relative(home, original)) : original
  const metadata = (name: string) => relative(target, name).split(sep).some(part => part.toLowerCase() === ".git")
  if (write && (!inside(target, path) || metadata(path)))
    throw Error("continuation_external_write")
  let ancestor = path
  while (true) {
    try {
      const actual = await realpath(ancestor)
      if (write && (!inside(target, actual) || metadata(actual))) throw Error("continuation_external_write")
      return path
    } catch (error: any) {
      if (error.code !== "ENOENT" || dirname(ancestor) === ancestor) throw error
      if (write && (await lstat(ancestor).catch(() => undefined))?.isSymbolicLink())
        throw Error("continuation_external_write")
      ancestor = dirname(ancestor)
    }
  }
}
