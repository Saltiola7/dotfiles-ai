import type { Plugin } from "@opencode-ai/plugin"
import { childRead, cyclePath, explicitCycleMutation, nativeContext, registerAdapter, request, requireSuccess, storeExists, targetPath } from "../lib/continuation"
import { continuationOperation, forgetCycleTarget, rememberContinuationOperation } from "../lib/dbsctr-runtime"

const controls = new Set(["dbsctr_begin", "dbsctr_attach", "dbsctr_preflight", "dbsctr_continuation_recover", "dbsctr_continuation_handover"])
const readers = new Set(["read", "glob", "grep", "list", "skill", "question", "todowrite", "webfetch", "websearch",
  "list_mcp_resources", "list_mcp_resource_templates", "read_mcp_resource", "dbsctr_status", "dbsctr_audit", "dbsctr_inspect",
  "dbsctr_runtime_health", "dbsctr_review", "dbsctr_review_history", "dbsctr_history_telemetry", "dbsctr_history_capture",
  "dbsctr_review_federated", "dbsctr_incident_scan", "dbsctr_improvement_status", "dbsctr_provider_evaluation",
  "dbsctr_benchmark", "dbsctr_lens_summary", "dbsctr_execution_dag"])
const files = new Set(["edit", "write", "apply_patch"])
const lifecycle = new Set(["dbsctr_phase_span", "dbsctr_execution_benchmark", "dbsctr_reconcile",
  "dbsctr_review_complete", "dbsctr_review_history_save", "dbsctr_provider_evaluation_save", "dbsctr_incident_register",
  "dbsctr_incident_update", "dbsctr_incident_forget", "dbsctr_improvement_claim", "dbsctr_improvement_update"])

export const Continuation: Plugin = async ({worktree, directory}) => {
  // No optional SDK/network call may prevent hooks from being registered.
  registerAdapter(worktree)
  const home = {worktree, directory}
  const calls = new Map<string, {context: ReturnType<typeof nativeContext>, target: string, operation: string}>()
  const key = (input: {sessionID: string, callID: string}) => `${input.sessionID}\0${input.callID}`
  return {
    "tool.execute.before": async (input, output) => {
      if (controls.has(input.tool)) return
      const context = nativeContext(home, input)
      if (context.primary === false) {
        if (!readers.has(input.tool)) throw Error("continuation_invalid_identity")
        await childRead(context, input.tool, output.args)
        return
      }
      if (!await storeExists(worktree)) return
      const state = await request(context, "check")
      if (!state.ok && ["invalid_state", "invalid_target"].includes(state.reason)
          && readers.has(input.tool) && !input.tool.startsWith("dbsctr_")) return
      requireSuccess(state)
      if (state.reason === "not_enrolled" && state.cycle_id === null) {
        if (await explicitCycleMutation(directory, input.tool, output.args)) throw Error("continuation_attachment_required")
        return
      }
      const target = await targetPath(context, state.target_worktree_id)
      const args = output.args
      if (readers.has(input.tool)) {
        if (input.tool === "read") args.filePath = await cyclePath(directory, target, args.filePath)
        if (["glob", "grep", "list"].includes(input.tool)) args.path = await cyclePath(directory, target, args.path ?? ".")
        return
      }
      const kind = files.has(input.tool) ? "file" : ["bash", "shell"].includes(input.tool) ? "shell"
        : lifecycle.has(input.tool) ? "lifecycle" : undefined
      if (!kind) throw Error("continuation_unqualified_tool")
      if (kind === "file") {
        if (input.tool === "apply_patch") {
          if (typeof args.patchText !== "string") throw Error("continuation_invalid_patch")
          const lines = args.patchText.split("\n")
          let changes = 0
          for (let index = 0; index < lines.length; index++) {
            const header = /^(\*\*\* (?:(?:Add|Update|Delete) File|Move to): )(.+)$/.exec(lines[index])
            if (header) {
              changes++
              lines[index] = header[1] + await cyclePath(directory, target, header[2], true)
            }
          }
          if (!changes || lines[0] !== "*** Begin Patch" || args.patchText.trimEnd().split("\n").at(-1) !== "*** End Patch")
            throw Error("continuation_invalid_patch")
          args.patchText = lines.join("\n")
        } else args.filePath = await cyclePath(directory, target, args.filePath, true)
      }
      if (kind === "shell") args.workdir = await cyclePath(directory, target, args.workdir ?? ".", true)
      const admitted = requireSuccess(await request(context, "admit", target, {
        generation: state.generation, call_id: input.callID, operation_class: kind,
      }))
      calls.set(key(input), {context, target, operation: admitted.operation_id})
      rememberContinuationOperation(context, admitted.operation_id)
    },
    "shell.env": async (input, output) => {
      output.env.DBSCTR_CONTINUATION_OPERATION = ""
      if (!await storeExists(worktree)) return
      if (!input.sessionID || !input.callID) throw Error("continuation_unmediated_shell")
      const operation = continuationOperation({sessionID: input.sessionID, callID: input.callID})
      if (operation) {
        output.env.DBSCTR_CONTINUATION_OPERATION = operation
        return
      }
      const context = nativeContext(home, {sessionID: input.sessionID, callID: input.callID})
      const state = requireSuccess(await request(context, "check"))
      if (state.cycle_id !== null) throw Error("continuation_unmediated_shell")
    },
    "tool.execute.after": async (input, output) => {
      const call = calls.get(key(input))
      if (!call) return
      const finished = requireSuccess(await request(call.context, "finish", call.target, {operation_id: call.operation, outcome: "completed"}))
      if (finished.state === "closed") {
        forgetCycleTarget(call.context.sessionID)
        output.output += "\nDBSCTR cycle completed; execution selection released. This conversation remains in its canonical checkout."
      }
      calls.delete(key(input))
      rememberContinuationOperation(call.context)
    },
  }
}
