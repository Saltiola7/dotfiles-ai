# Advanced Architecture Patterns — Reference

Read only the selected context-mapping, composition, consistency or cycle example.
These are alternatives whose costs and runtime requirements need actual project
evidence, not a requirement to add services, frameworks or an event platform.
For an audit, report observed coupling and compatibility before proposing code.

---

## Full Multi-Service Project Structure

An example for a system that already selected separate deployment per context.
Bounded contexts can instead remain cohesive packages in a modular monolith.
Compare operational, consistency, latency and change costs before selecting
service extraction. A folder tree is not proof of independent ownership or a
reason to create new repository-root directories.

```
ecommerce/
├── services/
│   ├── identity/                    # Bounded context: users & auth
│   │   ├── identity/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   │   └── user.py
│   │   │   │   ├── value_objects/
│   │   │   │   │   ├── email.py
│   │   │   │   │   └── password_hash.py
│   │   │   │   └── interfaces/
│   │   │   │       └── user_repository.py
│   │   │   ├── use_cases/
│   │   │   │   ├── register_user.py
│   │   │   │   └── authenticate_user.py
│   │   │   ├── adapters/
│   │   │   │   ├── repositories/
│   │   │   │   │   └── postgres_user_repository.py
│   │   │   │   └── controllers/
│   │   │   │       └── auth_controller.py
│   │   │   └── infrastructure/
│   │   │       └── jwt_service.py
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   │
│   ├── catalog/                     # Bounded context: products
│   │   ├── catalog/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   │   └── product.py
│   │   │   │   └── value_objects/
│   │   │   │       ├── sku.py
│   │   │   │       └── price.py
│   │   │   └── use_cases/
│   │   │       ├── create_product.py
│   │   │       └── update_inventory.py
│   │   └── tests/
│   │
│   └── ordering/                    # Bounded context: orders
│       ├── ordering/
│       │   ├── domain/
│       │   │   ├── entities/
│       │   │   │   └── order.py
│       │   │   ├── value_objects/
│       │   │   │   ├── customer_id.py   # NOT imported from identity!
│       │   │   │   └── money.py
│       │   │   └── interfaces/
│       │   │       ├── order_repository.py
│       │   │       └── catalog_client.py  # ACL port to catalog context
│       │   ├── use_cases/
│       │   │   ├── place_order.py
│       │   │   └── cancel_order.py
│       │   └── adapters/
│       │       ├── acl/
│       │       │   └── catalog_http_client.py  # ACL adapter
│       │       └── repositories/
│       │           └── postgres_order_repository.py
│       └── tests/
│
├── shared/                          # Shared kernel (use sparingly)
│   └── domain_events/
│       └── base_event.py
└── docker-compose.yml
```

---

## Onion Architecture vs. Clean Architecture

Both enforce inward-pointing dependencies. The difference is terminology and layering granularity:

| Concern | Clean Architecture | Onion Architecture |
|---|---|---|
| Innermost ring | Entities | Domain Model |
| Second ring | Use Cases | Domain Services |
| Third ring | Interface Adapters | Application Services |
| Outermost ring | Frameworks & Drivers | Infrastructure / UI / Tests |
| Key insight | Controller is an adapter | Application Services = Use Cases |

Onion Architecture makes the Domain Services layer explicit — it hosts pure domain logic that spans multiple entities but has no I/O:

Here `Money.amount` is a nonnegative integer number of cents, quantities are
positive integers, and the shown discounts use whole percentages. This example
rounds each discounted unit price to the nearest cent, with ties rounded upward,
before multiplying by quantity. Preserve the actual project's currency units,
discount rules and rounding policy when adapting it.

```python
# onion/domain/services/pricing_service.py
from domain.entities.product import Product
from domain.value_objects.money import Money
from domain.value_objects.discount import Discount

class PricingService:
    """
    Domain service: logic that doesn't belong to a single entity.
    No ports or adapters here — purely domain computation.
    """

    def apply_bulk_discount(self, product: Product, quantity: int) -> Money:
        """Return a discounted unit price, rounded half-up to integer cents."""
        if quantity >= 100:
            discount = Discount(percentage=20)
        elif quantity >= 50:
            discount = Discount(percentage=10)
        else:
            discount = Discount(percentage=0)
        discounted_cents = (
            product.price.amount * (100 - discount.percentage) + 50
        ) // 100
        return Money(discounted_cents, product.price.currency)

    def calculate_order_total(self, items: list[tuple[Product, int]]) -> Money:
        subtotals = []
        for product, quantity in items:
            unit_price = self.apply_bulk_discount(product, quantity)
            subtotals.append(Money(unit_price.amount * quantity, unit_price.currency))
        if not subtotals:
            return Money(0, "USD")  # Use the actual model's empty-total currency
        total = subtotals[0]
        for subtotal in subtotals[1:]:
            total = total.add(subtotal)
        return total
```

---

## Anti-Corruption Layer (ACL)

When the contexts have genuinely different models or compatibility needs, an
anti-corruption adapter can translate between them. Shared stable identifiers,
a documented upstream interface or a governed shared model can be sufficient
when semantics align; do not duplicate models purely to satisfy a diagram.

```python
# ordering/domain/interfaces/catalog_client.py
from abc import ABC, abstractmethod
from ordering.domain.value_objects.product_snapshot import ProductSnapshot

class CatalogClientPort(ABC):
    """
    Ordering's view of product data. Uses Ordering's own value object,
    not Catalog's Product entity.
    """

    @abstractmethod
    async def get_product_snapshot(self, sku: str) -> ProductSnapshot: ...


# ordering/domain/value_objects/product_snapshot.py
from dataclasses import dataclass
from ordering.domain.value_objects.money import Money

@dataclass(frozen=True)
class ProductSnapshot:
    """Ordering's local representation of a product at order time."""
    sku: str
    name: str
    unit_price: Money
    available: bool


# ordering/adapters/acl/catalog_http_client.py
import httpx
from ordering.domain.interfaces.catalog_client import CatalogClientPort
from ordering.domain.value_objects.product_snapshot import ProductSnapshot
from ordering.domain.value_objects.money import Money

class CatalogHttpClient(CatalogClientPort):
    """
    ACL adapter: calls Catalog's HTTP API and translates
    Catalog's response schema into Ordering's ProductSnapshot.
    """

    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self._base_url = base_url
        self._http = http_client

    async def get_product_snapshot(self, sku: str) -> ProductSnapshot:
        response = await self._http.get(f"{self._base_url}/products/{sku}")
        response.raise_for_status()
        data = response.json()

        # Translation: Catalog speaks "price_cents" + "currency_code";
        # Ordering speaks Money(amount, currency).
        return ProductSnapshot(
            sku=data["sku"],
            name=data["title"],              # field name differs between contexts
            unit_price=Money(
                amount=data["price_cents"],
                currency=data["currency_code"],
            ),
            available=data["stock_count"] > 0,
        )


# Test ACL with a stub — no HTTP required
class StubCatalogClient(CatalogClientPort):
    def __init__(self, products: dict[str, ProductSnapshot]):
        self._products = products

    async def get_product_snapshot(self, sku: str) -> ProductSnapshot:
        if sku not in self._products:
            raise ValueError(f"Unknown SKU: {sku}")
        return self._products[sku]
```

---

## Context Map — Relationships Between Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                        E-Commerce System                         │
│                                                                  │
│   ┌─────────────┐   Open Host   ┌─────────────────────────┐    │
│   │  Identity   │──────────────▶│        Ordering          │    │
│   │  Context    │               │  (uses CustomerId VO,    │    │
│   │             │               │   not User entity)       │    │
│   └─────────────┘               └─────────────────────────┘    │
│                                          │ ACL                   │
│                                          ▼                       │
│                                 ┌─────────────────┐             │
│   ┌─────────────┐  Shared       │    Catalog      │             │
│   │  Payments   │  Kernel       │    Context      │             │
│   │  Context    │◀─────────────▶│                 │             │
│   │             │  (Money VO)   └─────────────────┘             │
│   └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘

Relationship types:
  Open Host Service  — upstream provides a stable API for many downstream contexts
  ACL (Anti-Corruption Layer) — downstream translates upstream model to its own
  Shared Kernel     — two contexts share a small, explicitly governed sub-model
  Conformist        — downstream adopts a suitable upstream model under its contract
```

---

## Dependency Injection Wiring — Infrastructure Layer

For this selected inward-dependency design, the composition root wires concrete
adapters. A framework container is optional; constructor arguments or a simple
factory can suffice. The application's existing startup/shutdown owner creates
and closes shared pools; request/use-case factories borrow them.

```python
# infrastructure/container.py
import asyncpg
from adapters.repositories.postgres_user_repository import PostgresUserRepository
from use_cases.create_user import CreateUserUseCase


def make_create_user_use_case_factory(pool: asyncpg.Pool):
    # pool is borrowed from the existing application lifetime owner.
    # Do not create an unclosed pool for every use-case/request.
    def get_create_user_use_case() -> CreateUserUseCase:
        repository = PostgresUserRepository(pool=pool)
        return CreateUserUseCase(user_repository=repository)

    return get_create_user_use_case

# The selected framework wires the returned provider at startup. Its pool
# acquisition, capacity, shutdown and cancellation remain application-owned.
# Tests can provide a fake repository without opening a database.
```

---

## Aggregate Design Heuristics

Use these rules when deciding aggregate boundaries:

| Question | Guidance |
|---|---|
| Does a real invariant require atomic consistency across these objects? | Consider a common aggregate or the actual selected atomic unit; document ownership and costs. |
| Can the requirement tolerate eventual consistency? | Consider independent aggregates; define ordering, replay and recovery if events are selected. |
| Is one object the "owner" that controls access? | That object is the aggregate root. |
| Does removing the root make the child meaningless? | Child belongs inside the aggregate. |
| Are you loading many objects to change one? | Measure the access pattern and invariant needs; consider query shape, batching or a justified boundary change. |

**Practical example — Order vs. Customer:**

```python
# Bad: Customer aggregate holds full Order objects
class Customer:
    def __init__(self):
        self._orders: list[Order] = []   # loads all orders every time

# Good: Customer holds Order IDs only; Order is its own aggregate
class Customer:
    def __init__(self):
        self._order_ids: list[str] = []  # lightweight reference

class Order:
    def __init__(self, id: str, customer_id: str):
        self.id = id
        self.customer_id = customer_id   # reference back, not the full object
```

---

An ID list can still be unbounded and duplicate relationship ownership. The
example does not prove a performance improvement. Review actual queries and
consumers before choosing eager IDs, pagination or a different model.

## Domain Events — Publishing and Handling

Domain events decouple aggregates that need to react to each other's state changes:

```python
# domain/events/order_events.py
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class DomainEvent:
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )

@dataclass
class OrderSubmittedEvent(DomainEvent):
    order_id: str
    customer_id: str
    total_cents: int
    currency: str


# adapters/event_publisher/postgres_outbox.py
# Transactional outbox pattern: write events to the same DB transaction as state
import json

class PostgresOutboxPublisher:
    """
    Appends events through a caller-owned transaction. Atomicity requires
    the same actual transactional unit as aggregate persistence. A selected
    relay, acknowledgements and consumers determine delivery/replay guarantees.
    """

    def __init__(self, encode_event):
        # Explicit schema/versioned field encoder, not whole-object serialization.
        self._encode_event = encode_event

    async def publish(self, conn, events: tuple[DomainEvent, ...]):
        for event in events:
            await conn.execute(
                """
                INSERT INTO outbox (event_type, payload, published_at)
                VALUES ($1, $2, NULL)
                """,
                type(event).__name__,
                json.dumps(self._encode_event(event)),
            )


# use_cases/place_order.py — selected atomic persistence variant.
# TransactionPort, OrderRepository and EventPublisherPort are project contracts;
# the composition root supplies concrete adapters. In this variant, the selected
# save/publish contracts accept the same opaque transaction context. This is not
# a drop-in implementation of a port that independently acquires a connection.
# Successful context exit must mean actual commit for the chosen driver.
class PlaceOrderUseCase:
    def __init__(
        self,
        db: TransactionPort,
        order_repo: OrderRepository,
        event_publisher: EventPublisherPort,
    ):
        self.db = db
        self.orders = order_repo
        self.publisher = event_publisher

    async def execute(self, request: PlaceOrderRequest) -> PlaceOrderResponse:
        order = Order(id=str(uuid.uuid4()), customer_id=request.customer_id)
        for item in request.items:
            order.add_item(product=item.product, quantity=item.quantity)
        order.submit()

        async with self.db.transaction() as conn:
            await self.orders.save(order, conn)
            await self.publisher.publish(conn, order.pending_events())

        # Clear only after actual commit. Rollback/failed commit retains events.
        order.clear_events()
        return PlaceOrderResponse(order_id=order.id, success=True)
```

---

The event encoder must enumerate permitted fields and their units/version;
validate its schema and privacy contract. Do not serialize an entire domain
object with `__dict__`/`default=str`. Retrying publication requires stable event
identity and an explicit relay/deduplication/recovery design. This fragment does
not implement that relay or claim exactly-once behavior.

## Detecting and Breaking Dependency Cycles

For a selected layering contract, investigate actual import paths and owners.
These are candidate repairs, not mandatory patterns. Consolidation or a simpler
function interface may be better than a new abstract class, event or module.

```
Symptom: use_cases/create_order.py imports from adapters/email_sender.py
Fix:     Create domain/interfaces/notification_service.py (abstract port).
         use_cases imports the port. adapters implements it.
         DI container wires them together.

Symptom: domain/entities/user.py imports from infrastructure/config.py
Fix:     Pass config values as constructor arguments or environment at
         the infrastructure boundary. Domain entities must not read config.

Symptom: Two aggregates import each other
Fix:     Introduce a domain event. Aggregate A emits OrderPlaced.
         Aggregate B's use case subscribes and reacts. They never import
         each other.

Symptom: Repository imports a use case to "do extra work" after saving
Fix:     Extract the extra work into a separate domain service or use case.
         Repositories persist state only; they do not orchestrate behaviour.
```

A dependency diagram can help explain observed edges. Use an existing selected
authority or `python-architecture-fitness` guidance when available. Do not install
or execute a graph tool merely to complete an audit. Inspect its import/execution
behavior, scope and supported runtime before running it on target source.

For a project already selecting pydeps, an illustrative command is:

```bash
pydeps app --max-bacon=4 --cluster --rankdir=BT
```

Check the actual selected version/help. A graph can omit dynamic dependencies;
visual inspection does not establish contract coverage or good design. Keep the
existing allowed-edge authority and actual command/result evidence separate.
