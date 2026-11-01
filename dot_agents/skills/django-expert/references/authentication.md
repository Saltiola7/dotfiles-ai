# Authentication and authorization

Preserve the selected authenticators, user model, credential sources and
permission policy. Session, token, JWT and delegated identity have different
CSRF, expiry, revocation and transport contracts. Do not install or switch schemes
because an example mentions one. In DRF, denied unauthenticated requests can be
401 or 403 depending on the configured authentication classes; assert the
project's contract rather than choosing a universal status.

## Object ownership and action permissions

Example policy: public safe reads, authenticated creation, owner-only updates
and staff-only deletion. This is illustrative, not a product access policy.
Use `created_by_id` only when this is the selected model's ownership field.

```python
from rest_framework import permissions, viewsets

from .models import Product
from .serializers import ProductSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated
            and obj.created_by_id == request.user.pk
        )


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def get_permissions(self):
        if self.action == "destroy":
            # This explicit example policy allows staff deletion.
            return [permissions.IsAdminUser()]
        # Keep the owner permission for update, partial_update and custom writes.
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
```

DRF generic `get_object()` performs object permission checks. An overridden
lookup or custom view must call `check_object_permissions(request, obj)`.
Object checks do not filter list results or authorize creation; scope querysets
and related-object inputs, and enforce creation rules separately. Authentication
alone must not replace an ownership permission in `get_permissions()`.
Explicitly review each custom action and the destroy policy. Do not expose
server-owned `created_by`, roles or other privilege fields as writable inputs.
Test a different authenticated user's update and partial update.

The unsafe homemade `HasAPIKey` example has been removed. A missing header and
missing configuration must never authorize each other. If API keys are selected,
use the project's established authentication/key-verification implementation,
including nonempty configured credentials, verification, scope and revocation;
a header equality permission is not a complete authentication scheme.

## Existing SimpleJWT deployments

Only for a project that already selects SimpleJWT: inspect its installed version,
authenticator order, algorithm/key configuration, claims, audience/issuer,
lifetimes, rotation and revocation rules. Blacklisting requires the selected
blacklist app, its migrations and compatible configuration; setting a flag alone
does not establish revocation. Treat token endpoints and blacklist database
changes as separately authorized behavior, and retain existing routes and policy.
Do not copy guessed key material or token lifetimes from a tutorial.

Keep claims minimal. Do not assume a custom `user.role` or expose personal fields
without an explicit contract. A claim can outlive a permission change; verify how
the selected system applies current authorization and invalidates credentials.

## Registration and current-user endpoints

Use `get_user_model()` or the project's selected user serializers/services.
Fields must fit its `USERNAME_FIELD`, required fields and account lifecycle.
Explicitly allow-list editable fields; reject client-selected ownership,
privileges, verification state and password hashes. Use the configured password
validators with the candidate user and `create_user()`/`set_password()` so clear
passwords are never stored. Password confirmation, normalization and account
enumeration responses follow project policy.

A current-user endpoint may return `request.user`, but its serializer still
needs a narrow writable field list and explicit password/change handling. Do not
replace an existing identity-provider or invitation workflow with open
registration. Keep CSRF protections for selected session authentication and keep
credentials/tokens out of diagnostic output.

[DRF permissions](https://www.django-rest-framework.org/api-guide/permissions/),
[authentication and response status](https://www.django-rest-framework.org/api-guide/authentication/)
and [Django user customization](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/)
provide the framework contracts; choose the versions selected by the project.
