# Selected server and authentication

Use the server already selected by the current task or verified existing native
entry. Redacted CLI configuration can resolve identifiers; do not read raw CLI
credential files, print `jf config export`, dump environment values, or extract a
hostname to invent a server ID. Multiple unresolved targets require clarification.

Authentication belongs to the selected native JFrog/client owner. Do not initiate
browser login, create sessions, persist tokens, retarget a URL or migrate
credentials as an automatic diagnostic repair. An explicitly authorized login
uses native secret entry and actual supported authentication for that target.
Keep token-bearing output, auth headers and raw exceptions out of agent evidence.
See [server ambiguity](server-picker.md) and [helper effects](script-invocation.md).
