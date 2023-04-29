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
from http import HTTPStatus

from fastapi import FastAPI

from asgi_context import (
    http_requst_context,
    ContextMiddleware,
    HeadersExtractorMiddlewareFactory,
    ValidationConfig,
)

app = FastAPI()

def example_headers_validator(header_value: str) -> bool:
    return "example" in value

# will return 400 when missing specified headers or headers don't pass validation
example_headers_extractor_with_validation = HeadersExtractorMiddlewareFactory.build(
    base_name="example_with_validation",
    header_names=("X-Example",),
    validation_config=ValidationConfig(
        err_on_missing=HTTPStatus.BAD_REQUEST,
        err_on_invalid=HTTPStatus.BAD_REQUEST,
        validators={
            "X-Example": example_headers_validator,
        },
    ),
)

example_headers_extractor_without_validation = HeadersExtractorMiddlewareFactory.build(
    base_name="example_without_validation",
    header_names=("X-Not-Validated-Example",)
)

app.add_middleware(example_headers_extractor_with_validation)
app.add_middleware(example_headers_extractor_without_validation)
app.add_middleware(ContextMiddleware)

@app.get("/")
def index():
    return http_request_context["X-Example"]
```

### Starlite

```python
from http import HTTPStatus

from starlite import Starlite, get

from asgi_context import (
    http_requst_context,
    ContextMiddleware,
    HeadersExtractorMiddlewareFactory,
    ValidationConfig,
)

def example_headers_validator(header_value: str) -> bool:
    return "example" in value


# will return 400 when missing specified headers or headers don't pass validation
example_headers_extractor_with_validation = HeadersExtractorMiddlewareFactory.build(
    base_name="example",
    header_names=("X-Example",)
    validation_config=ValidationConfig(
        err_on_missing=HTTPStatus.BAD_REQUEST,
        err_on_invalid=HTTPStatus.BAD_REQUEST,
        validators={
            "X-Example": example_headers_validator,
        },
    ),
)


example_headers_extractor_without_validation = HeadersExtractorMiddlewareFactory.build(
    base_name="example_without_validation",
    header_names=("X-Not-Validated-Example",)
)


@get("/")
def index() -> str:
    return http_request_context["X-Example"]


app = Starlite(
    route_handlers=[index],
    middleware=[
        ContextMiddleware,
        example_headers_extractor_with_validation,
        example_headers_extractor_without_validation,
    ]
)
```
