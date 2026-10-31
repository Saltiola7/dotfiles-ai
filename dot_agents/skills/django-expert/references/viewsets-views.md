# ViewSets and views

Apply the project's access, queryset scope, writable-field and service contracts
before exposing routes. The following Product example combines the explicitly
illustrated public-read/owner-write policy with the model and serializer
fragments in the sibling references. It is not a buyer/payment/order workflow.

## ViewSet and atomic stock change

```python
from django.db import router, transaction
from django.db.models import F
from rest_framework import filters, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product
from .permissions import IsOwnerOrReadOnly
from .serializers import ProductSerializer


class PurchaseQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, default=1)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "created_by")
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]
    lookup_field = "slug"

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def purchase(self, request, slug=None):
        product = self.get_object()  # Includes the selected object permissions.
        data = PurchaseQuantitySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        quantity = data.validated_data["quantity"]
        database = router.db_for_write(Product, instance=product)

        with transaction.atomic(using=database):
            updated = (
                self.get_queryset()
                .using(database)
                .filter(
                    pk=product.pk,
                    created_by=request.user,
                    stock__gte=quantity,
                )
                .update(stock=F("stock") - quantity)
            )
            if updated != 1:
                raise serializers.ValidationError(
                    {"quantity": "Stock is unavailable for this operation."}
                )
        return Response({"quantity": quantity}, status=status.HTTP_200_OK)
```

Put `IsOwnerOrReadOnly` in the illustrated app's `permissions.py` as shown in
[Authentication](authentication.md). The extra owner predicate binds this
example's write policy to the same conditional update. A real purchase action
must use its established buyer/object policy instead; do not silently impose
this example's owner policy on an existing application.

A positive integer boundary plus a single `stock__gte`/`F()` update avoids the
original read/decrement/save race for this one-row stock invariant. Keep
authorization scope and the project's selected write database in the statement;
the loaded object's read alias is not necessarily its write target. Verify affected
row semantics, constraints, transaction support and concurrency on the selected
Django/database backend. This is not proof of multi-row order/payment consistency,
exactly-once requests or successful fulfillment. ORM `update()` bypasses `save()`,
model validation and signals; do not use it if those carry required invariants
without preserving them in the selected service. Network/payment calls are not
rolled back by `atomic()`.

Use `DjangoFilterBackend` only when django-filter is already selected, importing
it explicitly and preserving the project's allowed filter fields. Add featured
or other custom filters only for fields and visibility rules the model defines.

## Async boundaries

Match the selected Django, asgiref, middleware and serving stack. Django async
support does not imply an existing DRF view or authentication scheme is async.
Do not call blocking ORM code directly on an event loop or turn off async safety.

This helper accepts an already authorized/scoped queryset and returns explicit,
approved fields. It does not assume a custom `User.to_dict()` method or expose an
unauthenticated user listing:

```python
from asgiref.sync import sync_to_async


async def product_summaries(authorized_products):
    return await sync_to_async(list, thread_sensitive=True)(
        authorized_products.values("id", "name")[:100]
    )
```

Use available async ORM methods only for versions that support the needed
operation. For selected versions without async transaction support, put the
complete transaction in a synchronous function and adapt that function once
with `sync_to_async(..., thread_sensitive=True)`. Constructing a lazy QuerySet
is not query completion. Test cancellation/resource ownership when concurrent
behavior changes; preserve the project's existing sync/async boundary.

## Generic views, URLs and pagination

Generic view classes still need explicit queryset scope, serializer and
permissions. A detail update view does not acquire the owner policy from a
different ViewSet. Reuse the same selected object check and server-owned fields.

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
urlpatterns = [path("api/", include(router.urls))]
```

Keep the existing URL namespace and lookup contract. Configure pagination through
the selected settings or pagination class; a `page_size` query parameter needs a
bounded maximum. A limit is not a stable ordering or a substitute for access
scope. Do not add endpoint fields, routes or pagination policy merely to match
these examples.

[Django async support](https://docs.djangoproject.com/en/5.2/topics/async/),
[database routing](https://docs.djangoproject.com/en/5.2/topics/db/multi-db/),
[QuerySet update semantics](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#update)
and [DRF permissions](https://www.django-rest-framework.org/api-guide/permissions/)
describe the relevant boundaries; verify the project's selected versions.
