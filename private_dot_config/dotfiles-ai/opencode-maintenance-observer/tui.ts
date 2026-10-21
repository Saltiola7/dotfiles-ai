import { Plugin } from "@opencode/plugin/tui"
import { startObserver } from "./observer.mjs"

export default Plugin.define({
  id: "dotfiles.maintenance-observer",
  setup(context) {
    return startObserver(context)
  },
})
