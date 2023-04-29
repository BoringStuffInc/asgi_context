import uuid
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient as FastAPITestClient
from starlite import Starlite, get
from starlite.testing import TestClient as StarliteTestClient

from asgi_context import (
    ContextMiddleware,
    HeadersExtractorMiddlewareFactory,
    RequestContextException,
    ValidationConfig,
    http_request_context,
)


class TestFastAPI:
    def test_fastapi_correct_setup(self):
        tracing_middleware = HeadersExtractorMiddlewareFactory.build("Tracing", header_names=["X-Trace-ID"])

        app = FastAPI()
        app.add_middleware(tracing_middleware)
        app.add_middleware(ContextMiddleware)

        @app.get("/")
        async def index():
            return {"X-Trace-ID": http_request_context["X-Trace-ID"]}

        with FastAPITestClient(app) as client:
            response = client.get("/", headers={"X-Trace-ID": "123"})
            assert response.status_code == 200
            assert response.json() == {"X-Trace-ID": "123"}

    def test_fastapi_wrong_setup(self):
        tracing_middleware = HeadersExtractorMiddlewareFactory.build("Tracing", header_names=["X-Trace-ID"])

        app = FastAPI()
        app.add_middleware(ContextMiddleware)
        app.add_middleware(tracing_middleware)

        @app.get("/")
        async def index():
            return {"X-Trace-ID": http_request_context["X-Trace-ID"]}

        with FastAPITestClient(app) as client:
            with pytest.raises(RequestContextException):
                client.get("/", headers={"X-Trace-ID": "123"})

    def test_fastapi_with_validator(self):
        def uuid_validator(value: str) -> bool:
            try:
                uuid.UUID(value)
                return True
            except ValueError:
                return False

        tracing_middleware = HeadersExtractorMiddlewareFactory.build(
            "Tracing",
            header_names=["X-Trace-ID"],
            validation_config=ValidationConfig(
                err_on_missing=HTTPStatus.UNPROCESSABLE_ENTITY,
                err_on_invalid=HTTPStatus.BAD_REQUEST,
                validators={"X-Trace-ID": uuid_validator},
            ),
        )

        app = FastAPI()
        app.add_middleware(tracing_middleware)
        app.add_middleware(ContextMiddleware)

        @app.get("/")
        async def index():
            return {"X-Trace-ID": http_request_context["X-Trace-ID"]}

        with FastAPITestClient(app) as client:
            ok_response = client.get("/", headers={"X-Trace-ID": "00703a09-a666-411e-940d-768489c69302"})
            assert ok_response.status_code == 200

            bad_response = client.get("/", headers={"X-Trace-ID": "hello"})
            assert bad_response.status_code == 400
            assert bad_response.json() == {"error": "Invalid value for header: X-Trace-ID"}

            bad_response = client.get("/", headers={})
            assert bad_response.status_code == 422
            assert bad_response.json() == {"error": "Missing header: X-Trace-ID"}


class TestStarlite:
    def test_starlite_correct_setup(self):
        @get("/")
        async def index() -> dict[str, str]:
            return {"X-Trace-ID": http_request_context["X-Trace-ID"]}

        app = Starlite(
            route_handlers=[index],
            middleware=[
                ContextMiddleware,
                HeadersExtractorMiddlewareFactory.build("Tracing", header_names=["X-Trace-ID"]),
            ],
        )

        with StarliteTestClient(app) as client:
            response = client.get("/", headers={"X-Trace-ID": "456"})
            assert response.status_code == 200
            assert response.json() == {"X-Trace-ID": "456"}

    def test_starlite_wrong_setup(self):
        @get("/")
        async def index() -> dict[str, str]:
            return {"X-Trace-ID": http_request_context["X-Trace-ID"]}

        app = Starlite(
            route_handlers=[index],
            middleware=[
                HeadersExtractorMiddlewareFactory.build("Tracing", header_names=["X-Trace-ID"]),
            ],
        )

        with StarliteTestClient(app) as client:
            response = client.get("/", headers={"X-Trace-ID": "456"})
            assert response.status_code == 500
            assert "RequestContextException" in response.json()["detail"]
