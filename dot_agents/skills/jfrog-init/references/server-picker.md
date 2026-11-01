# Resolve an ambiguous JFrog server

Keep an existing explicit task/server selection. If it is absent, inspect only
redacted configured server identifiers through the selected CLI or existing native
entry. A configured default is usable only when consistent with task/project
policy; an unrelated ambient default is not authority.

When several plausible servers remain, present their non-secret identifiers and
ask which target is intended. Do not choose by machine name, Git identity, MCP
package name or a hostname parsed from a URL. Preserve the chosen ID throughout
the task. Failure, empty results, 401/403/404 and missing entitlement never justify
switching servers, changing the global default or inventing a replacement.
