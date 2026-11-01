# Models and ORM

Preserve the configured `AUTH_USER_MODEL`. Use `settings.AUTH_USER_MODEL` in model
relations and `get_user_model()` for runtime access; do not replace the project's
user model or assume a `username`, `email` or `role` field. A custom user-model
migration is a separate compatibility decision.

## Model and chainable QuerySet

This fragment assumes the project already defines `Category` and `Tag` in this
app and selects the illustrated Product fields. Foreign-key deletion, money,
stock and visibility policies remain project decisions.

```python
from django.conf import settings
from django.db import models


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_stock(self):
        return self.filter(stock__gt=0)

    def with_related(self):
        return self.select_related("category", "created_by").prefetch_related("tags")


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(
        "Category", on_delete=models.SET_NULL, null=True, related_name="products"
    )
    tags = models.ManyToManyField("Tag", related_name="products", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# Each step remains a ProductQuerySet.
products = Product.objects.active().in_stock().with_related()
```

Methods defined only on a Manager disappear after its first ordinary `filter()`.
Use a QuerySet plus `as_manager()`, or the selected `Manager.from_queryset()`
pattern when custom manager-only behavior is also needed. Preserve base/default
manager semantics, including those used for related access and migrations.

## Query cost and shape

Use `select_related` for needed single-valued relations and `prefetch_related` for
needed collections. Confirm query counts with representative pagination and
serialization. Loading unrelated data or filtering a prefetched manager again can
defeat the intended optimization.

```python
from django.db.models import Avg, Count, Q, Sum

summary = Product.objects.aggregate(
    avg_price=Avg("price"),
    total_stock=Sum("stock"),
)
products = Product.objects.filter(
    Q(price__lt=100) | Q(stock__gt=50), is_active=True
)
```

`only()`/`defer()` can introduce deferred-field queries; do not assume they save
work in a serializer or async path. Nullable related objects need a `None` case.
Use the project's query plans and read/write workload to justify indexes;
`unique=True` normally already supplies its uniqueness index. Additional
composite, conditional or ordering indexes depend on the selected backend.

## Database-side and bulk writes

Use a database-side `F()` expression when a value depends on its current database
value. A read followed by a Python assignment can lose concurrent changes.
For stock reservation, see the conditional update in
[Views](viewsets-views.md); a preliminary stock query does not reserve inventory.

```python
from django.db.models import F

# Example replenishment only when this stock operation is authorized.
updated = Product.objects.filter(pk=product_id).update(stock=F("stock") + quantity)
```

Validate positive quantities at the owning input boundary. `update()`,
`bulk_update()` and `bulk_create()` bypass model `save()` and its signals; model
validation is not automatically invoked by `save()` either. Required values,
database constraints, generated identifiers and invariant maintenance must be
accounted for explicitly. Chunk/batch behavior, returned IDs and conflict options
vary by Django/backend version. Keep external side effects outside an assumed
rollback guarantee and use the project's after-commit/outbox contract when needed.

[Django 5.2 managers](https://docs.djangoproject.com/en/5.2/topics/db/managers/),
[QuerySet API](https://docs.djangoproject.com/en/5.2/ref/models/querysets/) and
[custom user references](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#referencing-the-user-model)
verify these patterns; select documentation matching the actual project.
