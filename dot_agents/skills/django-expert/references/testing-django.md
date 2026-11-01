# Testing Django

Use the project's selected Django/DRF test runner, factories and database.
The snippets below assume the Product fragment from [Models](models-orm.md),
the illustrated owner-write policy, and app-local imports. They are examples to
adapt, not a complete test project or evidence that its database was exercised.

## API permissions and input regressions

Use the existing fixture/user factory with `get_user_model()` where runtime user
access is needed. Supply its real `USERNAME_FIELD` and required fields; do not
assume the configured model has a username/email/role field.

For the owner-write policy, prepare `self.owner`, `self.other_user` and
`self.product` through those selected fixtures. These methods belong in the
project's `APITestCase`:

```python
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse


class ProductPermissionTests(APITestCase):
    # setUp uses the project's existing user/product fixtures.

    def test_other_user_cannot_update(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("product-detail", kwargs={"slug": self.product.slug})
        original_name = self.product.name
        response = self.client.patch(url, {"name": "Changed"}, format="json")

        # This example uses an unscoped detail queryset plus object permission.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, original_name)

    def test_invalid_quantity_preserves_stock(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("product-purchase", kwargs={"slug": self.product.slug})
        original_stock = self.product.stock
        for quantity in (0, -1, "invalid", None):
            with self.subTest(quantity=quantity):
                response = self.client.post(
                    url, {"quantity": quantity}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.product.refresh_from_db()
                self.assertEqual(self.product.stock, original_stock)
```

Also test a denied authenticated `PUT`/`PATCH` on another owner's object and
each selected custom action. Projects that hide inaccessible rows may return 404
instead of this example's object-permission 403; assert their actual contract.

For unauthenticated writes, assert the exact status selected by the configured
authenticators: DRF can return 401 or 403 depending on its authentication-header
behavior. Do not hardcode a universal status or change authenticators to make a
test pass. Test session CSRF using the selected real authentication path when
affected; `force_authenticate()` bypasses credential verification and cannot prove
JWT/session/token behavior. Assert pagination/list shape from the real API
configuration, not an assumed `results` key.

## Constraints and transaction recovery

An expected database error must be caught outside the inner atomic block so
Django can roll back its savepoint before the next query. This example assumes
the database-enforced unique Product slug from the model reference, the default
test database, and a prepared valid `self.product`:

```python
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Product


class ProductConstraintTests(TestCase):
    # setUp creates a valid self.product using the project's selected fixtures.

    def test_slug_unique_and_transaction_recovers(self):
        original_stock = self.product.stock
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    name="Duplicate",
                    slug=self.product.slug,
                    price=self.product.price,
                    stock=0,
                    created_by=self.product.created_by,
                )

        # This query must still work; a broad Exception assertion would hide
        # both a wrong failure class and a broken enclosing test transaction.
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, original_stock)
        self.assertEqual(
            Product.objects.filter(slug=self.product.slug).count(), 1
        )
```

Use the same explicit alias for `atomic` and model operations in a multi-database
test. Do not expect `full_clean()` behavior from ordinary `save()`. Test named
validation failures and database constraints at their actual boundaries.

For stock contention or row-lock behavior, use the selected backend and a
transaction-capable test arrangement with independent connections/workers as
required. `TestCase` wraps tests in transactions and can mask missing production
transaction boundaries for locking APIs. SQLite-only success does not establish
PostgreSQL/MySQL locking or concurrent behavior. Preserve real backend failures;
an AST or stubbed transaction probe is a separate claim.

## Partial/nested writes and query behavior

Cover partial updates that omit each cross-field input, explicitly clear it or
change multiple fields. For writable nested services, cover selected replacement
versus merge behavior, omitted versus empty children, rollback after a later child
fails, server-owned fields and cross-owner references. Verify the persisted state
after failure, not only a response status.

Measure query counts around the actual serialized/paginated result to exercise
lazy loading and related access. Use representative nullable relations and
collection sizes; fixed query-count assertions should reflect the selected
scope. A constructed QuerySet is not a completed query.

## Fixtures, optional factories and authentication

Keep JSON fixture model labels, required fields, owner relations and identifiers
compatible with the selected schema. Do not load a Product fixture that omits a
required owner or assume `auth.User` when the project substitutes its user model.
Fixtures can become stale after migrations; run the owning checks.

Use factory_boy only when already selected. Reference `get_user_model()`, supply
its required identity fields, hash test passwords through `set_password` or the
selected factory hook, and generate genuinely unique constrained fields.
Faker words alone do not guarantee unique slugs. Do not switch an existing test
framework or install factory_boy because a reference mentions it.

For an existing JWT/token scheme, use its configured login field, installed
version, routes, claims and lifetimes. Obtain test credentials through that
scheme and verify protected access plus the affected invalid/expired/revoked
paths. Do not print raw credentials or tokens. Forced authentication remains a
useful permission test, with its authentication-coverage limitation recorded.

[Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/),
[DRF testing](https://www.django-rest-framework.org/api-guide/testing/) and
[authentication response status](https://www.django-rest-framework.org/api-guide/authentication/)
are reference authorities; use versions matching the actual project.
