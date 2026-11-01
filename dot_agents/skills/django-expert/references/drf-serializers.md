# DRF serializers

Keep an explicit field allow-list. Ownership, roles, totals, line prices and other
server-owned values must not become writable merely because a ModelSerializer
finds model fields. Match the model/API contract; the illustrative Product below
lets a caller provide its slug but does not let them set stock or ownership.

## Field boundaries and related-object scope

```python
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Product

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["pk"]
        read_only_fields = ["pk"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.none(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    created_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "price", "stock",
            "category_name", "category_id", "created_by", "created_at",
        ]
        read_only_fields = ["id", "stock", "created_by", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The authorized view/service supplies this selected queryset.
        if "eligible_categories" in self.context:
            self.fields["category_id"].queryset = self.context["eligible_categories"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
```

The empty related queryset denies category selection until the owning view/service
supplies the authorized scope through serializer context. A valid ID alone does
not prove access. If slugs or other required values are server-generated in the
actual project, mark them read-only and preserve the existing creation service.

Where the selected contract requires a name availability check, exclude the
current instance during updates:

```python
def validate_name(self, value):
    matches = Product.objects.filter(name__iexact=value)
    if self.instance is not None:
        matches = matches.exclude(pk=self.instance.pk)
    if matches.exists():
        raise serializers.ValidationError("Product name already exists.")
    return value
```

This check is user feedback, not a concurrency guarantee. If name uniqueness is a
real invariant, enforce the selected database constraint/collation and translate
its expected conflict at the proper transaction boundary. Do not add a new naming
rule or duplicate constraint to an existing project without that requirement.

## Partial and cross-field updates

Example only: an existing Order contract has a non-null product, positive quantity
and requires a shipping address above five items. Adapt to the actual contract;
the availability check below does not reserve inventory.

```python
from rest_framework import serializers

from .models import Order


class OrderValidationSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Order
        fields = ["product", "quantity", "shipping_address"]

    def validate(self, attrs):
        def effective(name):
            if name in attrs:
                return attrs[name]
            if self.instance is not None:
                return getattr(self.instance, name)
            return None

        product = effective("product")
        quantity = effective("quantity")
        address = effective("shipping_address")
        if product is None or quantity is None:
            raise serializers.ValidationError("Product and quantity are required.")
        if quantity < 1:
            raise serializers.ValidationError({"quantity": "Must be positive."})
        if quantity > product.stock:
            raise serializers.ValidationError({"quantity": "Insufficient stock."})
        if quantity > 5 and not address:
            raise serializers.ValidationError(
                {"shipping_address": "Required for this order quantity."}
            )
        return attrs
```

`partial=True` omits unchanged fields from `attrs`. Resolve the proposed state
against the existing instance, while distinguishing omission from explicit null
or clearing. Test changing each participating field alone, combined changes and
invalid existing/proposed states. Scope the generated product relation to the
caller's allowed products in the actual serializer.

## Nested representations and write atomicity

A nested read representation is straightforward and does not imply writable
nested support. This fragment assumes the selected Order/OrderItem models and
their computed/server-maintained values already exist:

```python
from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price"]
        read_only_fields = ["product", "quantity", "price"]


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "items", "total", "created_at"]
        read_only_fields = ["id", "user", "items", "total", "created_at"]
```

The original generic writable create/update recipe is deliberately replaced with
this read representation and the following write contract. It omitted the
project's order/pricing models; inventing their persistence rules would make the
example misleading.

For an actual writable nested request, implement its established service/serializer
consistency unit within `transaction.atomic(using=selected_database)`, including
parent changes, child changes and required server-side price/total/inventory
updates. Validate and authorize the parent and each related input before writes,
then recheck concurrency-sensitive invariants at the owning database operation.
Keep client owner/price/total values out of the writable field list.

Define the selected child-update semantics explicitly. Under a replacement
contract, omitted `items` preserves children, `items=[]` clears them only when
allowed, and a provided list replaces them as one unit. Under a merge contract,
identify allowed child IDs and their ownership, and distinguish additions,
updates and deletion. Do not silently adopt replacement for a merge API.

Use a transaction/locking strategy appropriate to concurrent parent/child writes;
`atomic()` alone does not serialize conflicting read-modify-write operations.
Test rollback when a later child write fails, partial omission, explicit clearing,
cross-owner child IDs, and rejection of server-owned input. Catch expected
database errors outside the atomic boundary that must be rolled back. External
effects require the existing after-commit/outbox policy.

## Computed fields

`SerializerMethodField` is read-only. Use the project's pricing/rounding and
serialization contract for money, preserving Decimal values until the selected
representation boundary; do not return a float annotation for Decimal arithmetic.
For availability, a computed boolean is a display snapshot, not a reservation.

[DRF serializers](https://www.django-rest-framework.org/api-guide/serializers/)
describe partial/nested behavior. [Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
describe the database boundary. Match the project's selected versions and schema.
