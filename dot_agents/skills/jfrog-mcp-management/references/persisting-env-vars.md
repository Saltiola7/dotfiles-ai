# Native secret and environment inputs

Use the actual selected client's supported secret references/environment
forwarding and existing credential owner. A launching shell, GUI environment and
native server environment can differ. Inspect actual current client/version
behavior rather than universal all/no ambient forwarding claims.

Never ask for credentials in chat, print them, place them in command arguments,
commit them or silently persist them in startup files/global launch environments.
Named references/allowlists carry no secret values in portable source. Required
catalog input names are case-sensitive; preserve their exact supported identity.
An unset reference is an actual readiness gap, not permission to insert a token.

Persistent non-secret environment changes retain the real shell/dotfiles/native
owner. POSIX export, fish `set -gx`, PowerShell session variables and Windows
persistent settings have different lifetimes; do not guess a startup file from
`$SHELL` or treat a process flag as proof of GUI inheritance. Secret entry and
storage stay with the user/native secret manager. Restart only the selected
client when needed and authorized. No broad PATH/startup or credential migration
is required by merely installing a JFrog skill or inspecting a catalog.
