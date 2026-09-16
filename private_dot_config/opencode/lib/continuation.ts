import { Database } from "bun:sqlite"
import { createHash, randomUUID } from "node:crypto"
import { access, lstat, realpath } from "node:fs/promises"
import { homedir } from "node:os"
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path"
import { continuationRequest, harnessActivation, rememberCycleTarget, run } from "./dbsctr-runtime"

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

export async function preflight(context: RuntimeContext, worktree?: string) {
  const adapter_available = registered.has(resolve(context.worktree))
  try {
    return {...await request(context, "check", worktree), adapter_available}
  } catch {
    return {schema_version: 1, ok: false, reason: "capability_unavailable", cycle_id: null, state: null,
      generation: 0, writer_relation: "none", activation_changes: [], next_action: "qualify_runtime",
      approval_binding: null, operation_id: null, event_id: null, target_worktree_id: null, adapter_available}
  }
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

export async function targetPath(context: RuntimeContext, id: string) {
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
  rememberCycleTarget(context.sessionID, target)
  return target
}

async function approval(context: RuntimeContext, permission: string, binding: any) {
  if (!binding || !context.ask) throw Error("continuation_approval_required")
  await context.ask({permission, patterns: [JSON.stringify(binding)], always: [], metadata: {
    action: binding.action, quiescenceRequired: ["enroll", "recover", "handover", "storage-recover"].includes(binding.action),
  }})
  return {receipt_id: randomUUID(), binding}
}

function requireAdapter(context: RuntimeContext) {
  if (!registered.has(resolve(context.worktree))) throw Error("continuation_adapter_unavailable: restart and reopen this conversation")
}

export async function attach(context: RuntimeContext, worktree?: string, mode = "writer") {
  requireAdapter(context)
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
  await targetPath(context, attached.target_worktree_id)
  return attached
}

export async function recover(context: RuntimeContext, worktree?: string, targetSessionId?: string) {
  requireAdapter(context)
  const action = targetSessionId === undefined ? "recover" : "handover"
  const fields = targetSessionId === undefined ? {} : {target_session_id: targetSessionId}
  let state = await request(context, "check", worktree, {action, ...fields})
  if (!state.ok && state.reason === "invalid_state" && action === "recover") {
    if (!worktree) throw Error("continuation_select_target_for_storage_recovery")
    const snapshot = await storageRequest(context, "storage-check", worktree)
    const consent = await approval(context, "dbsctr_continuation_storage_recover", snapshot.binding)
    await storageRequest(context, "storage-recover", worktree, {approval: consent})
    state = await request(context, "check", worktree, {action, ...fields})
  }
  requireSuccess(state)
  const consent = await approval(context, `dbsctr_continuation_${action}`, state.approval_binding)
  return requireSuccess(await request(context, action, worktree, {...fields, generation: state.generation, approval: consent}))
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
