# ASGI Context

Zero dependency middleware for storing HTTP request data in scoped context.
By default the library exposes the middleware for creating the context and
header extrator builder which can be used e.g. for storing tracing headers.

## Installation

The project is available on PyPI:

```shell
pip install asgi_context
```

or you can use pre-built sdist and wheels from `Releases` page.

## Example usage

### FastAPI

```python
from fastapi import FastAPI

from asgi_context import (
    http_requst_context,
    ContextMiddleware,
    HeadersExtractorMiddlewareFactory,
)

app = FastAPI()

def example_headers_validator(header_value: str) -> bool:
    return "example" in value

example_headers_extractor_middleware = HeadersExtractorMiddlewareFactory.build(
    base_name="example",
    header_names=("X-Example",)
    validators={
        "X-Example": example_headers_validator,
    }
)

app.add_middleware(example_headers_extractor_middleware)
app.add_middleware(ContextMiddleware)

@app.get("/")
def index():
    return http_request_context["X-Example"]
```

### Starlite

```python
from starlite import Starlite, get

from asgi_context import (
    http_requst_context,
    ContextMiddleware,
    HeadersExtractorMiddlewareFactory,
)

def example_headers_validator(header_value: str) -> bool:
    return "example" in value


example_headers_extractor_middleware = HeadersExtractorMiddlewareFactory.build(
    base_name="example",
    header_names=("X-Example",)
    validators={
        "X-Example": example_headers_validator,
    }
)


@get("/")
def index() -> str:
    return http_request_context["X-Example"]


app = Starlite(
    route_handlers=[index],
    middleware=[
        ContextMiddleware,
        example_headers_extractor_middleware
    ]
)
```
