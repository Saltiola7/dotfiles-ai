# Pydantic

## Required fields

For new compatible declarations, omit defaults to express required fields
clearly. Existing ellipsis forms are valid; do not change required/null behavior
or rewrite working code merely for style.

Do this, without Ellipsis (`...`):

```python
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query()]):
    return item
```

Existing valid form:

```python
# Older explicit required-field form
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str = ...
    description: str | None = None
    price: float = Field(..., gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query(...)]):
    return item
```

## Plain annotations and RootModel

A simple list body can use regular annotations plus `Annotated` without a wrapper.
`RootModel` is also valid when a named schema or custom validation/serialization
needs it. Preserve the selected public schema identity and installed-version
compatibility; do not mandate a wrapper or its removal.

For example, for a list with validations:

```python
from typing import Annotated

from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()


@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

Existing valid form:

```python
# Alternative named root schema
from typing import Annotated

from fastapi import FastAPI
from pydantic import Field, RootModel

app = FastAPI()


class ItemList(RootModel[Annotated[list[int], Field(min_length=1)]]):
    pass


@app.post("/items/")
async def create_items(items: ItemList):
    return items
```

FastAPI supports these type annotations and will create a Pydantic `TypeAdapter` for them, so types work normally without custom wrapper models.

For full Pydantic contracts, use the available `pydantic` technique when needed.
No internal domain-model replacement or dependency migration is implied.
