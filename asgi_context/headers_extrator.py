import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cached_property
from http import HTTPStatus
from typing import Literal, TypeAlias

from mypy_extensions import mypyc_attr

from asgi_context.context import http_request_context
from asgi_context.protocol import ASGIApp, HeaderName, HeaderValue, Receive, Scope, Send

Validator: TypeAlias = Callable[[HeaderValue], bool]

ErrOnMissing: TypeAlias = Literal[False] | HTTPStatus
ErrOnInvalid: TypeAlias = Literal[False] | HTTPStatus


@dataclass(frozen=True)
class ValidationConfig:
    err_on_missing: ErrOnMissing = False
    err_on_invalid: ErrOnInvalid = False
    validators: dict[HeaderName, Validator] = field(default_factory=dict)


@mypyc_attr(allow_interpreted_subclasses=True)
class AbstractHeadersExtractorMiddleware(ABC):
    __slots__ = ("app", "__dict__")

    ON_MISSING: ErrOnMissing
    ON_INVALID: ErrOnInvalid

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.__dict__ = {}

    @property
    @abstractmethod
    def header_names(self) -> Iterable[HeaderName]:
        pass

    @property
    @abstractmethod
    def validation_config(self) -> ValidationConfig:
        pass

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert "type" in scope, "ASGI scope must contain a 'type' key"

        if not scope["type"] == "http":
            await self.app(scope, receive, send)
        else:
            headers = {name.decode().lower(): value.decode() for name, value in scope["headers"]}

            for name in self.header_names:
                header_value = headers.get(name.lower())

                if not header_value and self.validation_config.err_on_missing:
                    return await self.send_response(
                        send,
                        status=self.validation_config.err_on_missing,
                        details=f"Missing header: {name}",
                    )

                if self.validation_config.err_on_invalid and header_value:
                    validate = self.validation_config.validators.get(name)

                    if validate and not validate(header_value):
                        return await self.send_response(
                            send,
                            status=self.validation_config.err_on_invalid,
                            details=f"Invalid value for header: {name}",
                        )

                if header_value:
                    http_request_context[name] = header_value

            await self.app(scope, receive, send)

    @staticmethod
    async def send_response(send: Send, *, status: HTTPStatus, details: str) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [],
                "trailers": False,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"error": details}).encode(),
                "more_body": False,
            }
        )


class HeadersExtractorMiddlewareFactory:
    @staticmethod
    def build(
        base_name: str,
        header_names: Iterable[HeaderName],
        validation_config: ValidationConfig = ValidationConfig(),  # noqa: B008
    ) -> type[AbstractHeadersExtractorMiddleware]:
        header_names_property = lambda self: tuple(header_names)
        validation_config_property = lambda self: validation_config

        return type(
            HeadersExtractorMiddlewareFactory._build_name(base_name),
            (AbstractHeadersExtractorMiddleware,),
            {
                "header_names": cached_property(header_names_property),
                "validation_config": cached_property(validation_config_property),
            },
        )

    @staticmethod
    def _build_name(base_name: str) -> str:
        name_parts = base_name.lower().replace(" ", "_").split("_")
        name = "".join(name_part.capitalize() for name_part in name_parts)
        return f"{name}HeadersExtractorMiddleware"
