from collections.abc import Awaitable, Callable
from typing import TypeAlias

Scope: TypeAlias = dict
Receive: TypeAlias = Callable[[None], Awaitable[dict]]
Send: TypeAlias = Callable[[dict], Awaitable[None]]
ASGIApp: TypeAlias = Callable[[Scope, Receive, Send], Awaitable[None]]

HeaderName: TypeAlias = str
HeaderValue: TypeAlias = str
