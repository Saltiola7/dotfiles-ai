// Read-only V2 route observation. No request, navigation, input or prompt access.
import fs from "node:fs"
import path from "node:path"
import { createHash, randomUUID } from "node:crypto"

const session = /^ses_[A-Za-z0-9]{1,120}$/
const opaque = /^[A-Za-z0-9:_-]{1,160}$/
function check(value) { if (!value) throw new Error("observer unavailable") }
function text(value, limit = 4096) {
  check(typeof value === "string" && value.length > 0 && value.length <= limit && !/[\x00-\x1f]/.test(value))
  return value
}
function sessionID(value) { check(typeof value === "string" && session.test(value)); return value }

export function sample(context, lastViewed) {
  const route = context.ui.router.current()
  check(route && typeof route.type === "string")
  const viewed = route.type === "session" ? sessionID(route.sessionID) : null
  const cached = viewed ? context.data.session.get(viewed) : null
  let directory = null
  if (cached && cached.id === viewed && cached.location?.directory != null) {
    directory = text(cached.location.directory)
    check(path.isAbsolute(directory))
  }
  const tabs = context.ui.tabs.enabled() ? context.ui.tabs.list() : []
  check(Array.isArray(tabs) && tabs.length <= 128)
  return {
    client_version: text(context.app.version, 80),
    viewed_session_id: viewed,
    last_viewed_session_id: viewed ?? lastViewed,
    session_directory: directory,
    tabs: tabs.map(tab => {
      check(typeof tab.active === "boolean")
      return { session_id: sessionID(tab.sessionID), active: tab.active }
    }),
  }
}

function safeDirectory(directory, privateMode = false) {
  check(path.isAbsolute(directory) && path.normalize(directory) === directory)
  let current = path.parse(directory).root
  for (const part of directory.slice(current.length).split("/").filter(Boolean)) {
    current = path.join(current, part)
    const info = fs.lstatSync(current)
    check(info.isDirectory() && (!(info.mode & 0o022) || (info.uid === 0 && (info.mode & 0o1000))))
  }
  const info = fs.lstatSync(directory)
  check(info.uid === process.getuid() && !(info.mode & (privateMode ? 0o077 : 0o022)))
  return info
}
function privateFile(file) {
  const info = fs.lstatSync(file)
  check(info.isFile() && info.uid === process.getuid() && !(info.mode & 0o077))
  return info
}
function same(left, right) { return left.dev === right.dev && left.ino === right.ino }

export function startObserver(context, environment = process.env) {
  let timer
  let disabled = false
  const stop = () => { disabled = true; if (timer) clearInterval(timer) }
  try {
    if (environment.HERDR_ENV !== "1") return stop
    const root = text(environment.DOTFILES_AI_STATE_ROOT)
    const socket = text(environment.HERDR_SOCKET_PATH)
    const pane = text(environment.HERDR_PANE_ID, 160)
    check(opaque.test(pane) && path.isAbsolute(socket))
    safeDirectory(root)
    const sentinel = fs.lstatSync(path.join(root, ".dotfiles-ai-state"))
    check(sentinel.isFile() && sentinel.uid === process.getuid() && !(sentinel.mode & 0o022))
    const socketInfo = fs.lstatSync(socket)
    check(socketInfo.isSocket() && socketInfo.uid === process.getuid())
    const herdr = path.join(root, "herdr")
    safeDirectory(herdr)
    const directory = path.join(herdr, "opencode-observers")
    try { fs.mkdirSync(directory, { mode: 0o700 }) } catch (error) { if (error.code !== "EEXIST") throw error }
    const directoryInfo = safeDirectory(directory, true)
    const incarnation = randomUUID().replaceAll("-", "")
    const filename = createHash("sha256").update(`${socket}\n${pane}\n${process.pid}`).digest("hex") + "-" + incarnation + ".json"
    const destination = path.join(directory, filename)
    let lastViewed = null
    let sequence = 0
    let previous = null
    let writtenAt = 0
    const tick = () => {
      if (disabled) return
      let temporary = null
      try {
        check(same(directoryInfo, safeDirectory(directory, true)))
        check(same(socketInfo, fs.lstatSync(socket)))
        const fields = sample(context, lastViewed)
        lastViewed = fields.last_viewed_session_id
        const serialized = JSON.stringify(fields)
        const now = Date.now()
        if (serialized === previous && now - writtenAt < 5000) return
        const record = JSON.stringify({ schema_version: 1, socket, socket_device: socketInfo.dev,
          socket_inode: socketInfo.ino, pane_id: pane, pid: process.pid, incarnation,
          captured_at: Math.floor(now / 1000), sequence: sequence++, ...fields }) + "\n"
        check(Buffer.byteLength(record) <= 65536)
        try { privateFile(destination) } catch (error) { if (error.code !== "ENOENT") throw error }
        temporary = path.join(directory, `.${incarnation}.tmp`)
        const fd = fs.openSync(temporary, fs.constants.O_WRONLY | fs.constants.O_CREAT |
          fs.constants.O_EXCL | fs.constants.O_NOFOLLOW, 0o600)
        try { fs.writeFileSync(fd, record); fs.fsyncSync(fd) } finally { fs.closeSync(fd) }
        check(same(directoryInfo, safeDirectory(directory, true)))
        fs.renameSync(temporary, destination)
        temporary = null
        const dirfd = fs.openSync(directory, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW)
        try { fs.fsyncSync(dirfd) } finally { fs.closeSync(dirfd) }
        previous = serialized
        writtenAt = now
      } catch {
        // Observation is optional. Never expose native data or fail the client lifecycle.
        stop()
      } finally {
        if (temporary) { try { fs.unlinkSync(temporary) } catch {} }
      }
    }
    tick()
    if (!disabled) timer = setInterval(tick, 500)
  } catch { stop() }
  return stop
}
