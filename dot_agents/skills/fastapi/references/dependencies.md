# Dependency Injection

Use dependencies when:

* They can't be declared in Pydantic validation and require additional logic
* The logic depends on external resources or could block in any other way
* Other dependencies need their results (it's a sub-dependency)
* The logic can be shared by multiple endpoints to do things like error early, handle authentication, etc.
* They need to handle cleanup (e.g., DB sessions, file handles), using dependencies with `yield`
* Their logic needs input data from the request, like headers, query parameters, etc.

## Dependencies with `yield` and `scope`

When using dependencies with `yield`, they can have a `scope` that defines when the exit code is run.

In installed versions with these scope semantics, default `"request"` cleanup
runs after sending the response. Verify behavior against the selected FastAPI
release; cleanup timing has changed across releases. Streaming may keep the
resource alive for the response lifetime. The next fragment assumes existing
`DBSession`/`Item` definitions; it is not database setup or an executable application.
Its synchronous query belongs in a synchronous handler, not on the event loop.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()


DBDep = Annotated[DBSession, Depends(get_db)]


@app.get("/items/")
def read_items(db: DBDep):
    return db.query(Item).all()
```

Use `scope="function"` only when the installed version supports it and cleanup
should occur after handler execution but before sending the response. A stream
that still needs a dependency cannot use a resource already closed at this scope.
Check the project's session/thread affinity and transaction boundaries separately;
yield/close alone does not define commit or rollback policy.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_username():
    try:
        yield "Rick"
    finally:
        print("Clean up before response is sent")


UserNameDep = Annotated[str, Depends(get_username, scope="function")]


@app.get("/users/me")
def get_user_me(username: UserNameDep):
    return username
```

## Class Dependencies

Function factories can make construction and lifetime explicit. Callable classes
are also supported; preserve existing ones unless an actual lifetime, testability
or coupling problem justifies a change. For example, a function factory:

```python
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


@dataclass
class DatabasePaginator:
    offset: int = 0
    limit: int = 100
    q: str | None = None

    def get_page(self) -> dict:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


def get_db_paginator(
    offset: int = 0, limit: int = 100, q: str | None = None
) -> DatabasePaginator:
    return DatabasePaginator(offset=offset, limit=limit, q=q)


PaginatorDep = Annotated[DatabasePaginator, Depends(get_db_paginator)]


@app.get("/items/")
async def read_items(paginator: PaginatorDep):
    return paginator.get_page()
```

Alternative callable-class form (valid when it matches project policy):

```python
# Alternative; not an automatic refactor target
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


class DatabasePaginator:
    def __init__(self, offset: int = 0, limit: int = 100, q: str | None = None):
        self.offset = offset
        self.limit = limit
        self.q = q

    def get_page(self) -> dict:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


@app.get("/items/")
async def read_items(paginator: Annotated[DatabasePaginator, Depends()]):
    return paginator.get_page()
```
