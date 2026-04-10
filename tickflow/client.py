"""Main client classes for TickFlow API.

This module provides the primary interfaces for interacting with the TickFlow API:
- `TickFlow`: Synchronous client
- `AsyncTickFlow`: Asynchronous client

Both clients provide access to the same resources with consistent method signatures.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ._base_client import DEFAULT_MAX_RETRIES, AsyncAPIClient, SyncAPIClient
from ._cache import InstrumentNameCache
from ._types import Headers, Timeout
from .resources import (
    AsyncExchanges,
    AsyncFinancials,
    AsyncInstruments,
    AsyncKlines,
    AsyncQuotes,
    AsyncQuoteStream,
    AsyncUniverses,
    Exchanges,
    Financials,
    Instruments,
    Klines,
    Quotes,
    QuoteStream,
    Universes,
)

__all__ = ["TickFlow", "AsyncTickFlow"]


def _print_free_tier_notice() -> None:
    """Print notice about free tier service."""
    print("\n" + "=" * 70)
    print("🆓 TickFlow 免费服务 (Free Tier)")
    print("=" * 70)
    print("✅ 提供历史日K线数据和标的信息（无需注册）")
    print("❌ 不提供实时行情和分钟级K线数据")
    print("⚠️ 日K数据为历史数据，盘中不会实时更新")
    print("")
    print("💡 如需实时行情、分钟K线或更高频率访问，请注册使用完整服务：")
    print(
        "  前往 https://tickflow.org 注册并使用 https://api.tickflow.org 作为 API 地址"
    )
    print("=" * 70 + "\n")


class TickFlow:
    """Synchronous client for TickFlow market data API.

    Provides access to market data including K-lines, quotes, instruments,
    exchanges, and universes.

    Parameters
    ----------
    api_key : str, optional
        API key for authentication. If not provided, reads from TICKFLOW_API_KEY
        environment variable.
    base_url : str, optional
        Base URL for the API. Defaults to https://api.tickflow.org.
        Can also be set via TICKFLOW_BASE_URL environment variable.
    timeout : float, optional
        Request timeout in seconds. Defaults to 30.0.
    default_headers : dict, optional
        Default headers to include in all requests.

    Attributes
    ----------
    klines : Klines
        K-line (OHLCV) data endpoints, including adjustment factors.
        Supports DataFrame conversion and forward/backward adjustment.
    quotes : Quotes
        Real-time quote endpoints.
    instruments : Instruments
        Instrument metadata endpoints.
    exchanges : Exchanges
        Exchange list endpoints.
    universes : Universes
        Universe (symbol pool) endpoints.
    financials : Financials
        Financial statement endpoints (income, balance sheet, cash flow, metrics).
    realtime : QuoteStream
        WebSocket-based real-time quote streaming (requires ``pip install tickflow[realtime]``).

    Examples
    --------
    Basic usage:

    >>> from tickflow import TickFlow
    >>>
    >>> client = TickFlow(api_key="your-api-key")
    >>>
    >>> # Get forward-adjusted K-line data (default)
    >>> df = client.klines.get("600519.SH", as_dataframe=True)
    >>>
    >>> # Get unadjusted K-line data
    >>> df_raw = client.klines.get("600519.SH", adjust="none", as_dataframe=True)
    >>>
    >>> # Get adjustment factors
    >>> factors = client.klines.ex_factors(["600519.SH"], as_dataframe=True)
    >>>
    >>> # Get financial data
    >>> income = client.financials.income(["600519.SH"], as_dataframe=True)

    Real-time streaming:

    >>> stream = client.realtime
    >>> @stream.on_quotes
    ... def handle(quotes):
    ...     for q in quotes:
    ...         print(f"{q['symbol']}: {q['last_price']}")
    >>> stream.subscribe(["600000.SH"])
    >>> stream.connect()

    Using context manager:

    >>> with TickFlow(api_key="your-api-key") as client:
    ...     df = client.klines.get("AAPL.US", as_dataframe=True)
    ...     print(df.tail())

    Using environment variable:

    >>> import os
    >>> os.environ["TICKFLOW_API_KEY"] = "your-api-key"
    >>> client = TickFlow()  # Uses TICKFLOW_API_KEY
    """

    klines: Klines
    quotes: Quotes
    instruments: Instruments
    exchanges: Exchanges
    universes: Universes
    financials: Financials
    realtime: QuoteStream

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Timeout = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        self._client = SyncAPIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._instrument_cache = InstrumentNameCache(cache_dir=cache_dir)

        self.klines = Klines(self._client, instrument_cache=self._instrument_cache)
        self.quotes = Quotes(self._client)
        self.instruments = Instruments(self._client)
        self.exchanges = Exchanges(self._client)
        self.universes = Universes(self._client)
        self.financials = Financials(self._client)
        self.realtime = QuoteStream(self._client)

    def __enter__(self) -> "TickFlow":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client.

        This releases any network resources held by the client.
        Called automatically when using the client as a context manager.
        """
        self._client.close()

    @classmethod
    def free(
        cls,
        *,
        base_url: Optional[str] = None,
        timeout: Timeout = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
        cache_dir: Optional[str] = None,
    ) -> "TickFlow":
        """Create a client for the free tier API server.

        The free tier provides access to daily K-line data and instrument information
        without requiring an API key. No registration needed.

        Features available in free tier:
        - Daily K-line data (1d, 1w, 1M, 1Q, 1Y)
        - Instrument metadata
        - Exchange information
        - Universe (symbol pool) queries
        - Adjustment factors

        Rate limits apply based on IP address (default: 60 requests/minute).

        Parameters
        ----------
        base_url : str, optional
            Base URL for the free tier API. Defaults to https://free-api.tickflow.org.
            Can also be set via TICKFLOW_FREE_BASE_URL environment variable.
        timeout : float, optional
            Request timeout in seconds. Defaults to 30.0.
        max_retries : int, optional
            Maximum number of retry attempts. Defaults to 3.
        default_headers : dict, optional
            Default headers to include in all requests.
        cache_dir : str, optional
            Directory for caching instrument names. Defaults to user cache directory.

        Returns
        -------
        TickFlow
            A configured client for the free tier API.

        Examples
        --------
        Basic usage:

        >>> from tickflow import TickFlow
        >>> client = TickFlow.free()
        >>> df = client.klines.get("600000.SH", as_dataframe=True)
        >>> print(df.tail())

        With custom URL:

        >>> client = TickFlow.free(base_url="https://custom-free-api.example.com")

        Using context manager:

        >>> with TickFlow.free() as client:
        ...     df = client.klines.get("600000.SH", period="1d", as_dataframe=True)
        ...     print(df.tail())

        Notes
        -----
        - No API key required (any provided API key will be ignored)
        - IP-based rate limiting applies
        - Only historical daily data is available (no real-time quotes or minute data)
        - For real-time data and minute-level K-lines, use the paid API with:
          TickFlow(api_key="your-key", base_url="https://api.tickflow.org")
        """
        if base_url is None:
            base_url = os.environ.get(
                "TICKFLOW_FREE_BASE_URL", "https://free-api.tickflow.org"
            )

        _print_free_tier_notice()

        return cls(
            api_key=None,  # Free tier doesn't require API key
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            cache_dir=cache_dir,
        )

    @property
    def instrument_cache(self) -> InstrumentNameCache:
        """The shared instrument name cache."""
        return self._instrument_cache

    @property
    def api_key(self) -> Optional[str]:
        """The API key used for authentication. None for free tier."""
        return self._client.api_key

    @property
    def base_url(self) -> str:
        """The base URL for API requests."""
        return self._client.base_url


class AsyncTickFlow:
    """Asynchronous client for TickFlow market data API.

    Provides access to market data including K-lines, quotes, instruments,
    exchanges, and universes. All methods are async and must be awaited.

    Parameters
    ----------
    api_key : str, optional
        API key for authentication. If not provided, reads from TICKFLOW_API_KEY
        environment variable.
    base_url : str, optional
        Base URL for the API. Defaults to https://api.tickflow.org.
        Can also be set via TICKFLOW_BASE_URL environment variable.
    timeout : float, optional
        Request timeout in seconds. Defaults to 30.0.
    max_retries : int, optional
        Maximum number of retry attempts for failed requests. Defaults to 3.
        Retries occur on connection errors, timeouts, and server errors (5xx).
    default_headers : dict, optional
        Default headers to include in all requests.

    Attributes
    ----------
    klines : AsyncKlines
        K-line (OHLCV) data endpoints, including adjustment factors.
    quotes : AsyncQuotes
        Real-time quote endpoints.
    instruments : AsyncInstruments
        Instrument metadata endpoints.
    exchanges : AsyncExchanges
        Exchange list endpoints.
    universes : AsyncUniverses
        Universe (symbol pool) endpoints.
    financials : AsyncFinancials
        Financial statement endpoints (income, balance sheet, cash flow, metrics).

    Examples
    --------
    Basic usage:

    >>> import asyncio
    >>> from tickflow import AsyncTickFlow
    >>>
    >>> async def main():
    ...     async with AsyncTickFlow(api_key="your-api-key") as client:
    ...         # Get K-line data as DataFrame
    ...         df = await client.klines.get("600000.SH", as_dataframe=True)
    ...         print(df.tail())
    ...
    ...         # Get multiple symbols in parallel
    ...         import asyncio
    ...         tasks = [
    ...             client.klines.get(s, as_dataframe=True)
    ...             for s in ["600000.SH", "000001.SZ", "600519.SH"]
    ...         ]
    ...         results = await asyncio.gather(*tasks)
    >>>
    >>> asyncio.run(main())

    Manual resource management:

    >>> async def main():
    ...     client = AsyncTickFlow(api_key="your-api-key")
    ...     try:
    ...         quotes = await client.quotes.get(symbols=["600000.SH"])
    ...         print(quotes)
    ...     finally:
    ...         await client.close()
    """

    klines: AsyncKlines
    quotes: AsyncQuotes
    instruments: AsyncInstruments
    exchanges: AsyncExchanges
    universes: AsyncUniverses
    financials: AsyncFinancials
    realtime: AsyncQuoteStream

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Timeout = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        self._client = AsyncAPIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._instrument_cache = InstrumentNameCache(cache_dir=cache_dir)

        self.klines = AsyncKlines(self._client, instrument_cache=self._instrument_cache)
        self.quotes = AsyncQuotes(self._client)
        self.instruments = AsyncInstruments(self._client)
        self.exchanges = AsyncExchanges(self._client)
        self.universes = AsyncUniverses(self._client)
        self.financials = AsyncFinancials(self._client)
        self.realtime = AsyncQuoteStream(self._client)

    async def __aenter__(self) -> "AsyncTickFlow":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client.

        This releases any network resources held by the client.
        Called automatically when using the client as an async context manager.
        """
        await self._client.close()

    @classmethod
    def free(
        cls,
        *,
        base_url: Optional[str] = None,
        timeout: Timeout = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Headers] = None,
        cache_dir: Optional[str] = None,
    ) -> "AsyncTickFlow":
        """Create an async client for the free tier API server.

        The free tier provides access to daily K-line data and instrument information
        without requiring an API key. No registration needed.

        Features available in free tier:
        - Daily K-line data (1d, 1w, 1M, 1Q, 1Y)
        - Instrument metadata
        - Exchange information
        - Universe (symbol pool) queries
        - Adjustment factors

        Rate limits apply based on IP address (default: 60 requests/minute).

        Parameters
        ----------
        base_url : str, optional
            Base URL for the free tier API. Defaults to https://free-api.tickflow.org.
            Can also be set via TICKFLOW_FREE_BASE_URL environment variable.
        timeout : float, optional
            Request timeout in seconds. Defaults to 30.0.
        max_retries : int, optional
            Maximum number of retry attempts. Defaults to 3.
        default_headers : dict, optional
            Default headers to include in all requests.
        cache_dir : str, optional
            Directory for caching instrument names. Defaults to user cache directory.

        Returns
        -------
        AsyncTickFlow
            A configured async client for the free tier API.

        Examples
        --------
        Basic usage:

        >>> import asyncio
        >>> from tickflow import AsyncTickFlow
        >>>
        >>> async def main():
        ...     async with AsyncTickFlow.free() as client:
        ...         df = await client.klines.get("600000.SH", as_dataframe=True)
        ...         print(df.tail())
        >>>
        >>> asyncio.run(main())

        Parallel requests:

        >>> async def fetch_multiple():
        ...     async with AsyncTickFlow.free() as client:
        ...         tasks = [
        ...             client.klines.get(symbol, as_dataframe=True)
        ...             for symbol in ["600000.SH", "000001.SZ", "600519.SH"]
        ...         ]
        ...         results = await asyncio.gather(*tasks)
        ...         return results

        With custom URL:

        >>> async with AsyncTickFlow.free(base_url="https://custom-free-api.example.com") as client:
        ...     df = await client.klines.get("600000.SH", as_dataframe=True)

        Notes
        -----
        - No API key required (any provided API key will be ignored)
        - IP-based rate limiting applies
        - Only historical daily data is available (no real-time quotes or minute data)
        - For real-time data and minute-level K-lines, use the paid API with:
          AsyncTickFlow(api_key="your-key", base_url="https://api.tickflow.org")
        """
        if base_url is None:
            base_url = os.environ.get(
                "TICKFLOW_FREE_BASE_URL", "https://free-api.tickflow.org"
            )

        _print_free_tier_notice()

        return cls(
            api_key=None,  # Free tier doesn't require API key
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            cache_dir=cache_dir,
        )

    @property
    def instrument_cache(self) -> InstrumentNameCache:
        """The shared instrument name cache."""
        return self._instrument_cache

    @property
    def api_key(self) -> Optional[str]:
        """The API key used for authentication. None for free tier."""
        return self._client.api_key

    @property
    def base_url(self) -> str:
        """The base URL for API requests."""
        return self._client.base_url
