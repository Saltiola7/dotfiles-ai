# Resolve a JFrog project

Reuse explicit task/project configuration for the selected platform. A workspace
directory, project display name and JFrog project key are different identifiers.
Ask only if unresolved identity blocks the requested operation. Offer verified
accessible candidates when already available, or accept the user's explicit key
without pretending it has been validated.

Do not enumerate admin-only project APIs to manufacture a picker for a non-admin.
If enumeration is authorized, preserve the actual permission/availability result;
a 403 does not prove the named project is absent. Typed input is a selection,
not proof of existence or access. Do not export a new global JF_PROJECT or write
setup state merely to record the answer. See [state reuse](project-state-reuse.md)
and [resolution branches](project-resolution-branches.md).
