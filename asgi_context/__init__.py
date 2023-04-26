from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import Awaitable, Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property
from typing import TypeAlias

Scope: TypeAlias = dict
Receive: TypeAlias = Callable[[None], Awaitable[dict]]
Send: TypeAlias = Callable[[dict], Awaitable[None]]
ASGIApp: TypeAlias = Callable[[Scope, Receive, Send], Awaitable[None]]

HeaderName: TypeAlias = str
HeaderValue: TypeAlias = str

Validator: TypeAlias = Callable[[HeaderValue], bool]


_http_request_context: ContextVar[dict] = ContextVar("ctx")


class RequestContextException(Exception):
    pass


class HeaderValidationException(Exception):
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


class AbstractHeadersExtractorMiddleware(ABC):
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @property
    @abstractmethod
    def header_names(self) -> Iterable[HeaderName]:
        pass

    @property
    @abstractmethod
    def validators(self) -> dict[HeaderName, Validator]:
        pass

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert "type" in scope, "ASGI scope must contain a 'type' key"

        if not scope["type"] == "http":
            await self.app(scope, receive, send)
        else:
            headers = {name.decode().lower(): value.decode() for name, value in scope["headers"]}

            for name in self.header_names:
                header_value = headers.get(name.lower())

                if (validate := self.validators.get(name)) and header_value:
                    if not validate(header_value):
                        raise HeaderValidationException(f"Header {name} failed validation")

                http_request_context[name] = header_value

            await self.app(scope, receive, send)


class HeadersExtractorMiddlewareFactory:
    @staticmethod
    def build(
        base_name: str,
        header_names: Iterable[HeaderName],
        validators: dict[HeaderName, Validator] | None = None,
    ) -> type[AbstractHeadersExtractorMiddleware]:
        name_parts = base_name.lower().replace(" ", "_").split("_")
        name = "".join(name_part.capitalize() for name_part in name_parts)
        header_names_property = lambda self: tuple(header_names)
        validators_property = lambda self: validators or dict()

        return type(
            f"{name}HeadersExtractorMiddleware",
            (AbstractHeadersExtractorMiddleware,),
            {
                "header_names": cached_property(header_names_property),
                "validators": cached_property(validators_property),
            },
        )


http_request_context = Context()


__all__ = (
    "http_request_context",
    "ContextMiddleware",
    "HeadersExtractorMiddlewareFactory",
    "RequestContextException",
    "HeaderValidationException",
)
