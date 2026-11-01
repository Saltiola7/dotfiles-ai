# architecture-patterns — detailed patterns and worked examples

Use only the selected pattern and relevant examples. These fragments omit
application wiring and referenced domain types; they are not a complete runnable
service or an instruction to add frameworks, async I/O or storage dependencies.
Preserve the project's actual model, runtime, units and validation authority.

## Clean Architecture — Directory Structure

```
app/
├── domain/           # Entities, value objects, interfaces
│   ├── entities/
│   │   ├── user.py
│   │   └── order.py
│   ├── value_objects/
│   │   ├── email.py
│   │   └── money.py
│   └── interfaces/   # Abstract ports (no implementations)
│       ├── user_repository.py
│       └── payment_gateway.py
├── use_cases/        # Application business rules
│   ├── create_user.py
│   ├── process_order.py
│   └── send_notification.py
├── adapters/         # Concrete implementations
│   ├── repositories/
│   │   ├── postgres_user_repository.py
│   │   └── redis_cache_repository.py
│   ├── controllers/
│   │   └── user_controller.py
│   └── gateways/
│       ├── stripe_payment_gateway.py
│       └── sendgrid_email_gateway.py
└── infrastructure/   # Framework wiring, config, DI container
    ├── database.py
    ├── config.py
    └── logging.py
```

**Selected dependency rule:** domain/application policy should not depend on
concrete infrastructure in this design. Standard-library imports, appropriate
pure dependencies and cohesive application internals are valid. Define allowed
package edges explicitly; directory names do not enforce them. Other coherent
architectures can use different boundaries.

## Clean Architecture — Core Implementation

```python
# domain/entities/user.py
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class User:
    """Core user entity — no framework dependencies."""
    id: str
    email: str
    name: str
    created_at: datetime
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False

    def can_place_order(self) -> bool:
        return self.is_active


# domain/interfaces/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.user import User

class IUserRepository(ABC):
    """Port: defines contract, no implementation details."""

    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: str) -> bool: ...


# use_cases/create_user.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid
from domain.entities.user import User
from domain.interfaces.user_repository import IUserRepository

@dataclass
class CreateUserRequest:
    email: str
    name: str

@dataclass
class CreateUserResponse:
    user: Optional[User]
    success: bool
    error: Optional[str] = None

class CreateUserUseCase:
    """Use case: orchestrates business logic, no HTTP or DB details."""

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def execute(self, request: CreateUserRequest) -> CreateUserResponse:
        existing = await self.user_repository.find_by_email(request.email)
        if existing:
            return CreateUserResponse(user=None, success=False, error="Email already exists")

        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            name=request.name,
            created_at=datetime.now(timezone.utc),
        )
        saved_user = await self.user_repository.save(user)
        return CreateUserResponse(user=saved_user, success=True)


# adapters/repositories/postgres_user_repository.py
from domain.interfaces.user_repository import IUserRepository
from domain.entities.user import User
from typing import Optional
import asyncpg

class PostgresUserRepository(IUserRepository):
    """Adapter: PostgreSQL implementation of the user port."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def find_by_id(self, user_id: str) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return self._to_entity(row) if row else None

    async def find_by_email(self, email: str) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
            return self._to_entity(row) if row else None

    async def save(self, user: User) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, created_at, is_active)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE
                SET email = $2, name = $3, is_active = $5
                """,
                user.id, user.email, user.name, user.created_at, user.is_active,
            )
        return user

    async def delete(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            return result == "DELETE 1"

    def _to_entity(self, row) -> User:
        return User(
            id=row["id"], email=row["email"], name=row["name"],
            created_at=row["created_at"], is_active=row["is_active"],
        )


# adapters/controllers/user_controller.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from use_cases.create_user import CreateUserUseCase, CreateUserRequest

router = APIRouter()

class CreateUserDTO(BaseModel):
    email: str
    name: str

@router.post("/users")
async def create_user(
    dto: CreateUserDTO,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
):
    """Controller handles HTTP only — no business logic lives here."""
    response = await use_case.execute(CreateUserRequest(email=dto.email, name=dto.name))
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    return {"user": response.user}
```

The user example illustrates boundaries, not a complete uniqueness protocol.
The email precheck can race: the selected persistence contract must enforce the
actual uniqueness invariant and map conflicts to an appropriate domain result.
In-memory tests do not prove database constraints, isolation or adapter mappings.
Do not infer transaction semantics from a method named `save`.

For the FastAPI fragment, the composition root must wire the provider callable
and its resource lifetime. The `Depends` expression is an integration seam, not
an instruction to install or migrate to FastAPI/Pydantic.

## Hexagonal Architecture — Ports and Adapters

The following call sequence illustrates where effects cross ports. It is not an
atomic payment workflow: a charge may succeed before persistence or notification
fails. Before implementation, define stable operation identity, ambiguous-result
handling and durable recovery for the actual effects. A database transaction
cannot roll back an external payment. Use the project's selected consistency and
notification strategy; do not silently retry the entire sequence.


```python
# Core domain service — no infrastructure dependencies
class OrderService:
    def __init__(
        self,
        order_repository: OrderRepositoryPort,
        payment_gateway: PaymentGatewayPort,
        notification_service: NotificationPort,
    ):
        self.orders = order_repository
        self.payments = payment_gateway
        self.notifications = notification_service

    async def place_order(self, order: Order) -> OrderResult:
        if not order.is_valid():
            return OrderResult(success=False, error="Invalid order")

        payment = await self.payments.charge(amount=order.total, customer=order.customer_id)
        if not payment.success:
            return OrderResult(success=False, error="Payment failed")

        order.mark_as_paid()
        saved_order = await self.orders.save(order)
        await self.notifications.send(
            to=order.customer_email,
            subject="Order confirmed",
            body=f"Order {order.id} confirmed",
        )
        return OrderResult(success=True, order=saved_order)


# Ports (driving and driven interfaces)
class OrderRepositoryPort(ABC):
    @abstractmethod
    async def save(self, order: Order) -> Order: ...

class PaymentGatewayPort(ABC):
    @abstractmethod
    async def charge(self, amount: Money, customer: str) -> PaymentResult: ...

class NotificationPort(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str): ...


# Adapter around an already selected asynchronous provider boundary.
# The injected operation owns SDK compatibility, idempotency, deadlines,
# cancellation and safe domain-error mapping. It does not expose raw exceptions.
from collections.abc import Awaitable, Callable

class PaymentAdapter(PaymentGatewayPort):
    def __init__(self, charge: Callable[[Money, str], Awaitable[PaymentResult]]):
        self._charge = charge

    async def charge(self, amount: Money, customer: str) -> PaymentResult:
        return await self._charge(amount, customer)


# Test adapter: no external dependencies
class MockPaymentAdapter(PaymentGatewayPort):
    async def charge(self, amount: Money, customer: str) -> PaymentResult:
        return PaymentResult(success=True, transaction_id="mock-txn-123")
```

## DDD — Value Objects and Aggregates

These illustrative value rules select a restricted currency/amount model, not
universal business rules. Confirm negative amounts, units, supported currencies,
empty-order meaning and validation policy with the actual domain. The minimal
email predicate below demonstrates construction-time validation; it is not a
complete address validator or deliverability check. Avoid including raw inputs
in error messages that might reach logs or responses.


```python
# Value Objects: immutable, validated at construction
from dataclasses import dataclass

@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if "@" not in self.value or "." not in self.value.split("@")[-1]:
            raise ValueError("Invalid email value")

@dataclass(frozen=True)
class Money:
    amount: int   # cents
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if self.currency not in {"USD", "EUR", "GBP"}:
            raise ValueError(f"Unsupported currency: {self.currency}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)


# Aggregate root: enforces all invariants for its cluster of entities
class Order:
    def __init__(self, id: str, customer_id: str):
        self.id = id
        self.customer_id = customer_id
        self.items: list[OrderItem] = []
        self.status = OrderStatus.PENDING
        self._events: list[DomainEvent] = []

    def add_item(self, product: Product, quantity: int):
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify a submitted order")
        item = OrderItem(product=product, quantity=quantity)
        self.items.append(item)
        self._events.append(ItemAddedEvent(order_id=self.id, item=item))

    @property
    def total(self) -> Money:
        totals = [item.subtotal() for item in self.items]
        if not totals:
            return Money(0, "USD")  # USD-only example; use the actual order currency
        total = totals[0]
        for subtotal in totals[1:]:
            total = total.add(subtotal)  # Money.add checks currency compatibility
        return total

    def submit(self):
        if not self.items:
            raise ValueError("Cannot submit an empty order")
        if self.status != OrderStatus.PENDING:
            raise ValueError("Order already submitted")
        total = self.total
        self.status = OrderStatus.SUBMITTED
        self._events.append(OrderSubmittedEvent(
            order_id=self.id,
            customer_id=self.customer_id,
            total_cents=total.amount,
            currency=total.currency,
        ))

    def pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)

    def clear_events(self) -> None:
        self._events.clear()


# Repository: persist and reconstitute aggregates
class OrderRepository(ABC):
    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]: ...

    @abstractmethod
    async def save(self, order: Order) -> None: ...
    # A selected unit of work persists state and pending events atomically.
    # Clear events only after successful commit, never merely after row writes.
```


## In-memory adapter

The fake below implements only the shown sequential policy contract; it does not
model concurrent uniqueness, transaction isolation or external failure semantics.

```python
class InMemoryUserRepository(IUserRepository):
    def __init__(self):
        self._store: dict[str, User] = {}

    async def find_by_id(self, user_id: str) -> User | None:
        return self._store.get(user_id)

    async def find_by_email(self, email: str) -> User | None:
        return next((user for user in self._store.values() if user.email == email), None)

    async def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

    async def delete(self, user_id: str) -> bool:
        return self._store.pop(user_id, None) is not None
```

## In-memory boundary tests

Use the configured test authority. This synchronous test-body style can run under
ordinary pytest or be adapted to the project's unittest/async harness; it does
not require installing an async plugin. The relevant use case and fake repository
come from the earlier boundary example. These cases establish pure orchestration
behavior only, not the selected database adapter's guarantees.

```python
import asyncio


def test_create_user_policy():
    async def scenario():
        repo = InMemoryUserRepository()
        use_case = CreateUserUseCase(user_repository=repo)
        first = await use_case.execute(CreateUserRequest(email="alice@example.com", name="Alice"))
        assert first.success
        assert first.user is not None
        assert first.user.id
        duplicate = await use_case.execute(CreateUserRequest(email="alice@example.com", name="Alice2"))
        assert not duplicate.success
        assert duplicate.error is not None
        assert "already exists" in duplicate.error

    asyncio.run(scenario())
```

Retain suitable existing example/integration tests. Use separate selected-engine
checks where SQL constraints, concurrency, transactions, serialization, pooling
or recovery are part of the claim; do not infer those results from the fake.
