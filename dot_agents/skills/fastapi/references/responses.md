# Responses

## Return Type or Response Model

When possible, include a return type. It will be used to validate, filter, document, and serialize the response.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me")
async def get_item() -> Item:
    return Item(name="Plumbus", description="All-purpose home device")
```

For ordinary returned values, return types/response models can filter and
serialize data. An explicitly returned `Response` bypasses model validation and
filtering. Custom serializers, aliases, subclass output and include/exclude flags
also affect public fields; assert actual emitted JSON and wire metadata.

The return type doesn't have to be a Pydantic model. It can be a different type, like a list of integers, a dict, etc.

## When to use `response_model`

If the return type is not the same as the type that you want to use to validate, filter, or serialize, use the `response_model` parameter on the decorator.

```python
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me", response_model=Item)
async def get_item() -> Any:
    return {"name": "Foo", "description": "A very nice Item"}
```

This is particularly useful when filtering data to expose only public fields.
The example explicitly converts the internal model to mapping input before the
public response model validates and filters it; unrelated model types may not
validate directly in the selected Pydantic/FastAPI combination.

```python
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class InternalItem(BaseModel):
    name: str
    description: str | None = None
    secret_key: str


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me", response_model=Item)
async def get_item() -> Any:
    item = InternalItem(
        name="Foo", description="A very nice Item", secret_key="supersecret"
    )
    # Make the model-to-public-schema input explicit for compatible validation.
    return item.model_dump()
```

## Verify the response boundary

Keep status codes, headers, media type, field aliases and error shape compatible.
Test representative internal objects with private fields against the public output
model, and separately test any explicit `Response` or streaming path. Do not use
`Any`, `response_model=None` or a hand-built response solely to silence validation.
A model-filtering test does not prove authorization, redacted logs or data-source
correctness. The fake secret above illustrates field exclusion, not secret handling.
