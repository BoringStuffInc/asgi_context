from collections import UserDict
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeAlias

Scope: TypeAlias = dict
Receive: TypeAlias = Callable[[None], Awaitable[dict]]
Send: TypeAlias = Callable[[dict], Awaitable[None]]
ASGIApp: TypeAlias = Callable[[Scope, Receive, Send], Awaitable[None]]


_http_request_context: ContextVar[dict] = ContextVar("ctx", default=dict())


class RequestContextException(Exception):
    pass


class Context(UserDict):
    def __init__(self) -> None:
        pass

    @property
    def data(self) -> dict:  # type: ignore[override]
        try:
            return _http_request_context.get()
        except LookupError:
            raise RequestContextException(
                "No request context available - make sure you are using the ContextMiddleware"
            )


@contextmanager
def new_context() -> Iterator[None]:
    token = _http_request_context.set(dict())
    try:
        yield
    finally:
        _http_request_context.reset(token)


http_request_context = Context()


class ContextMiddleware:
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not scope["type"] == "http":
            return await self.app(scope, receive, send)

        with new_context():
            await self.app(scope, receive, send)


__all__ = ("http_request_context", "ContextMiddleware")
