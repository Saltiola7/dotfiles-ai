<!-- Adapted by dotfiles-ai, 2026-10-28; see UPSTREAM.md and security-toolkit provenance. -->

# Triage: Deciding Whether a Candidate Is Real

Strategy for the verification stage. You have candidate locations that resemble a known
bug. Establish which candidates violate a reachable trust boundary. Assign severity
only after the primary workflow confirms the affected principal, control and impact.

## Argue Against the Candidate

The snippet alone is never enough. Read the surrounding function, the callers, and the type
of every value involved, then look specifically for the thing that makes it safe:

- A guard earlier in the function or in a decorator/middleware
- A sanitizer, validator, or parameterized API between source and sink
- A type constraint that makes the dangerous value unreachable
- A caller set that never supplies attacker-controlled input

A candidate survives only if you looked for these and did not find them.

Having no callers is a reachability limitation. Record unprotected but unreachable
code as a hardening candidate with the condition that would make it reachable;
do not label it a confirmed vulnerability merely because a caller might appear.

## Exploitability

For a surviving candidate, establish:

- **Reachable** — is there a path from an external entry point to this code?
- **Controllable** — can an attacker influence the value that makes it dangerous?
- **Unprotected** — is the protection named in the root cause genuinely absent here?

A candidate that is reachable and controllable but has a different protection in place is a
false positive worth recording, not a finding. An unreachable or unresolved candidate stays unconfirmed, with no vulnerability
severity. State the missing reachability evidence and safe next validation step.

## Edge Cases That Hide Real Bugs

Test every candidate against these if applicable, because normal-path reasoning misses them.

### Null equality bypasses

A common authorization bypass. If both sides of a comparison can be null at the same time,
the comparison succeeds for the wrong reason:

```python
# anonymous_user.id is None, guest_order.owner_id is None
# None == None is True, so the check passes for a user who owns nothing
if order.owner_id == current_user.id:
    return True
```

Ask: what values can each side hold? Can both be null simultaneously? Who can cause that?

### Documentation/code mismatch

The function does the opposite of what its name or docstring claims:

```python
def check_restricted_permission(user, perm):
    """Returns True if access should be DENIED."""
    if user.has_perm(perm):
        return True   # BUG: returns "deny" for users who DO have permission
    return False
```

Every caller of a function like this is a potential finding, even where the call site looks
correct. Verify the return semantics against the name before trusting any use of it.

### Others worth testing

- Unauthenticated and anonymous callers
- Empty strings vs null, zero vs null
- Empty arrays and collections
- Boundary values at the limits of the type

## Severity and Confidence

Assign severity only to confirmed boundary violations under the primary policy,
using concrete impact and reachability. Needs-validation, rejected and hardening
candidates have their own disposition, without vulnerability severity. Keep
unresolved facts and safe next checks explicit.

## Recording False Positives

When a candidate is ruled out, record *why* it was safe. Grouped by reason, these become the
false-positive table in the report, and they are what lets the next stage refine the
pattern instead of re-triaging the same matches.
