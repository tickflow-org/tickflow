"""Base HTTP client implementation with retry support for sync and async operations."""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Optional, TypeVar, Union

import httpx

from . import __version__
from ._exceptions import (
    APIError,
    ConnectionError,
    InternalServerError,
    RateLimitError,
    TimeoutError,
    raise_for_status,
)
from ._types import NOT_GIVEN, Headers, NotGiven, Query, Timeout

__all__ = ["SyncAPIClient", "AsyncAPIClient"]

DEFAULT_BASE_URL = "https://api.tickflow.org"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3

T = TypeVar("T")


def _should_retry(exception: Exception) -> bool:
    """Determine if an exception is retryable.

    Parameters
    ----------
    exception : Exception
        The exception to check.

    Returns
    -------
    bool
        True if the request should be retried.
    """
    # Retry on connection errors and timeouts
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True

    # Retry on server errors (5xx) and rate limits (429)
    if isinstance(exception, (InternalServerError, RateLimitError)):
        return True

    return False


def _calculate_retry_delay(
    attempt: int, base_delay: float = 1.0, max_delay: float = 30.0
) -> float:
    """Calculate exponential backoff delay with jitter.

    Parameters
    ----------
    attempt : int
        Current attempt number (0-indexed).
    base_delay : float
        Base delay in seconds.
    max_delay : float
        Maximum delay in seconds.

    Returns
    -------
    float
        Delay in seconds.
    """
    # Exponential backoff: 1s, 2s, 4s, 8s, ...
    delay = base_delay * (2**attempt)
    # Add jitter (±25%)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    delay = delay + jitter
    # Cap at max delay
    return min(delay, max_delay)


class BaseClient:
    """Base class with shared configuration for API clients."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
    ) -> None:
        # Allow None for free tier mode
        if api_key is None:
            self.api_key = os.environ.get("TICKFLOW_API_KEY")
        else:
            self.api_key = api_key

        # Only raise error if we're trying to use the default paid URL without a key
        if not self.api_key:
            effective_base_url = base_url or os.environ.get("TICKFLOW_BASE_URL")
            if effective_base_url is None or effective_base_url == DEFAULT_BASE_URL:
                raise ValueError(
                    "API key is required for paid API. Pass `api_key` or set TICKFLOW_API_KEY environment variable. "
                    "For free tier access, use TickFlow.free() or AsyncTickFlow.free()."
                )

        self.base_url = (
            base_url or os.environ.get("TICKFLOW_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._default_headers = dict(default_headers) if default_headers else {}

    def _build_headers(self, extra_headers: Optional[Headers] = None) -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"tickflow-python-sdk/{__version__}",
            **self._default_headers,
        }
        # Only add API key if present (free tier doesn't need it)
        if self.api_key:
            headers["x-api-key"] = self.api_key
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.base_url}{path}"


class SyncAPIClient(BaseClient):
    """Synchronous HTTP client for TickFlow API with automatic retry.

    Parameters
    ----------
    api_key : str, optional
        API key for authentication. If not provided, reads from TICKFLOW_API_KEY
        environment variable.
    base_url : str, optional
        Base URL for the API. Defaults to https://api.tickflow.org.
    timeout : float, optional
        Request timeout in seconds. Defaults to 30.0.
    max_retries : int, optional
        Maximum number of retry attempts for failed requests. Defaults to 3.
        Retries occur on connection errors, timeouts, server errors (5xx),
        and rate limits (429).
    default_headers : dict, optional
        Default headers to include in all requests.

    Examples
    --------
    >>> client = SyncAPIClient(api_key="your-api-key")
    >>> response = client.get("/v1/exchanges")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, default_headers)
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "SyncAPIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Query] = None,
        json: Optional[dict[str, Any]] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make an HTTP request with automatic retry on failures.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.).
        path : str
            API endpoint path.
        params : dict, optional
            Query parameters.
        json : dict, optional
            JSON request body.
        extra_headers : dict, optional
            Additional headers for this request.
        timeout : float, optional
            Override timeout for this request.
        max_retries : int, optional
            Override max retries for this request.

        Returns
        -------
        Any
            Parsed JSON response.

        Raises
        ------
        APIError
            If the API returns an error response after all retries.
        ConnectionError
            If there's a network connection issue after all retries.
        TimeoutError
            If the request times out after all retries.
        """
        url = self._build_url(path)
        headers = self._build_headers(extra_headers)
        request_timeout = timeout if not isinstance(timeout, NotGiven) else self.timeout
        retries = (
            max_retries if not isinstance(max_retries, NotGiven) else self.max_retries
        )

        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        last_exception: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=request_timeout,
                )

                # Parse response
                try:
                    response_body = response.json()
                except Exception:
                    response_body = {"message": response.text, "code": "PARSE_ERROR"}

                # Check for errors (may raise retryable exceptions)
                raise_for_status(response.status_code, response_body)

                return response_body

            except httpx.ConnectError as e:
                last_exception = ConnectionError(f"Failed to connect to {url}: {e}")
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request to {url} timed out")
            except APIError as e:
                last_exception = e
                if not _should_retry(e):
                    raise

            # Check if we should retry
            if attempt < retries and _should_retry(last_exception):
                delay = _calculate_retry_delay(attempt)
                time.sleep(delay)
            else:
                break

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state: no exception but request failed")

    def get(
        self,
        path: str,
        *,
        params: Optional[Query] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make a GET request with automatic retry."""
        return self._request(
            "GET",
            path,
            params=params,
            extra_headers=extra_headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    def post(
        self,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[Query] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make a POST request with automatic retry."""
        return self._request(
            "POST",
            path,
            json=json,
            params=params,
            extra_headers=extra_headers,
            timeout=timeout,
            max_retries=max_retries,
        )


class AsyncAPIClient(BaseClient):
    """Asynchronous HTTP client for TickFlow API with automatic retry.

    Parameters
    ----------
    api_key : str, optional
        API key for authentication. If not provided, reads from TICKFLOW_API_KEY
        environment variable.
    base_url : str, optional
        Base URL for the API. Defaults to https://api.tickflow.org.
    timeout : float, optional
        Request timeout in seconds. Defaults to 30.0.
    max_retries : int, optional
        Maximum number of retry attempts for failed requests. Defaults to 3.
        Retries occur on connection errors, timeouts, server errors (5xx),
        and rate limits (429).
    default_headers : dict, optional
        Default headers to include in all requests.

    Examples
    --------
    >>> async with AsyncAPIClient(api_key="your-api-key") as client:
    ...     response = await client.get("/v1/exchanges")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, default_headers)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> "AsyncAPIClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Query] = None,
        json: Optional[dict[str, Any]] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make an async HTTP request with automatic retry on failures.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.).
        path : str
            API endpoint path.
        params : dict, optional
            Query parameters.
        json : dict, optional
            JSON request body.
        extra_headers : dict, optional
            Additional headers for this request.
        timeout : float, optional
            Override timeout for this request.
        max_retries : int, optional
            Override max retries for this request.

        Returns
        -------
        Any
            Parsed JSON response.

        Raises
        ------
        APIError
            If the API returns an error response after all retries.
        ConnectionError
            If there's a network connection issue after all retries.
        TimeoutError
            If the request times out after all retries.
        """
        url = self._build_url(path)
        headers = self._build_headers(extra_headers)
        request_timeout = timeout if not isinstance(timeout, NotGiven) else self.timeout
        retries = (
            max_retries if not isinstance(max_retries, NotGiven) else self.max_retries
        )

        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        last_exception: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=request_timeout,
                )

                # Parse response
                try:
                    response_body = response.json()
                except Exception:
                    response_body = {"message": response.text, "code": "PARSE_ERROR"}

                # Check for errors (may raise retryable exceptions)
                raise_for_status(response.status_code, response_body)

                return response_body

            except httpx.ConnectError as e:
                last_exception = ConnectionError(f"Failed to connect to {url}: {e}")
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request to {url} timed out")
            except APIError as e:
                last_exception = e
                if not _should_retry(e):
                    raise

            # Check if we should retry
            if attempt < retries and _should_retry(last_exception):
                delay = _calculate_retry_delay(attempt)
                await asyncio.sleep(delay)
            else:
                break

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state: no exception but request failed")

    async def get(
        self,
        path: str,
        *,
        params: Optional[Query] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make an async GET request with automatic retry."""
        return await self._request(
            "GET",
            path,
            params=params,
            extra_headers=extra_headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def post(
        self,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[Query] = None,
        extra_headers: Optional[Headers] = None,
        timeout: Union[Timeout, NotGiven] = NOT_GIVEN,
        max_retries: Union[int, NotGiven] = NOT_GIVEN,
    ) -> Any:
        """Make an async POST request with automatic retry."""
        return await self._request(
            "POST",
            path,
            json=json,
            params=params,
            extra_headers=extra_headers,
            timeout=timeout,
            max_retries=max_retries,
        )
