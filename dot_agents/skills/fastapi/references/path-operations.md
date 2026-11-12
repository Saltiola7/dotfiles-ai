# Path Operations and Routing

## Including Routers

When creating a router for one stable context, router-level prefix/tags/shared
dependencies can keep its contract together. Existing include-time configuration
is valid and useful when the same router is mounted in different contexts.
Preserve paths, operation IDs, slash redirects and authorization composition.

Router-owned option:

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def list_items():
    return []


app.include_router(router)
```

Include-time option:

```python
# Valid alternative for reusable routers
from fastapi import APIRouter, FastAPI

app = FastAPI()

router = APIRouter()


@router.get("/")
async def list_items():
    return []


app.include_router(router, prefix="/items", tags=["items"])
```

Choose from actual reuse and ownership; neither form is a standalone defect.

Use router-level `dependencies=[Depends(...)]` only for genuinely shared checks;
keep endpoint-specific checks and dependency return values explicit.

## Use one HTTP operation per function

Prefer separate handlers for operations with different validation, authorization
or response behavior. Intentional multi-method handlers can also be valid; test
every declared method and preserve an existing shared contract.

Router-owned option:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str


@app.get("/items/")
async def list_items():
    return []


@app.post("/items/")
async def create_item(item: Item):
    return item
```

Include-time option:

```python
# Incomplete illustration: POST behavior would still need a defined contract
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str


@app.api_route("/items/", methods=["GET", "POST"])
async def handle_items(request: Request):
    if request.method == "GET":
        return []
```
