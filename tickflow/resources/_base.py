"""Base resource class for API resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient


ClientT = TypeVar("ClientT", "SyncAPIClient", "AsyncAPIClient")


class SyncResource:
    """Base class for synchronous API resources."""

    _client: "SyncAPIClient"

    def __init__(self, client: "SyncAPIClient") -> None:
        self._client = client


class AsyncResource:
    """Base class for asynchronous API resources."""

    _client: "AsyncAPIClient"

    def __init__(self, client: "AsyncAPIClient") -> None:
        self._client = client
