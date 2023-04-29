from collections import UserDict
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from asgi_context.protocol import ASGIApp, Receive, Scope, Send

_http_request_context: ContextVar[dict] = ContextVar("ctx")


class RequestContextException(Exception):
    pass


class Context(UserDict):
    def __init__(self) -> None:
        pass

    @property
    def data(self) -> dict:  # type: ignore[override]
        try:
            return _http_request_context.get()
        except LookupError as e:
            raise RequestContextException(
                "No request context available - make sure you are using the ContextMiddleware. "
                "In case you're using Starlette based framework and using add_middleware method "
                "make sure to call it after any middleware that uses http_request_context."
            ) from e


@contextmanager
def new_context() -> Iterator[None]:
    token = _http_request_context.set(dict())
    try:
        yield
    finally:
        _http_request_context.reset(token)


class ContextMiddleware:
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert "type" in scope, "ASGI scope must contain a 'type' key"

        if not scope["type"] == "http":
            await self.app(scope, receive, send)
        else:
            with new_context():
                await self.app(scope, receive, send)


http_request_context = Context()
