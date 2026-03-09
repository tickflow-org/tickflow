"""Exchange resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    from ..generated_model import ExchangeSummary, Instrument, InstrumentType


class Exchanges(SyncResource):
    """Synchronous interface for exchange endpoints.

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>> exchanges = client.exchanges.list()
    >>> for exchange in exchanges:
    ...     print(f"{exchange['exchange']}: {exchange['count']} instruments")
    """

    def list(self) -> List["ExchangeSummary"]:
        """Get list of all exchanges with instrument counts.

        Returns
        -------
        list of ExchangeSummary
            List of exchange information containing:
            - exchange: Exchange code (e.g., "SH", "SZ", "US")
            - region: Region code (e.g., "CN", "US", "HK")
            - count: Number of instruments in the exchange

        Examples
        --------
        >>> exchanges = client.exchanges.list()
        >>> print(exchanges)
        [{'exchange': 'SH', 'region': 'CN', 'count': 2100}, ...]
        """
        response = self._client.get("/v1/exchanges")
        return response["data"]

    def get_instruments(
        self, exchange: str, instrument_type: Optional["InstrumentType"] = None
    ) -> List["Instrument"]:
        """Get all instruments for a specific exchange.

        Parameters
        ----------
        exchange : str
            Exchange code (e.g., "SH", "SZ", "BJ", "US", "HK").
        instrument_type : InstrumentType, optional
            Filter by instrument type (stock, etf, index, bond, fund, etc.).

        Returns
        -------
        list of Instrument
            List of instrument metadata.

        Examples
        --------
        >>> # Get all instruments
        >>> instruments = client.exchanges.get_instruments("SH")
        >>> print(f"Found {len(instruments)} instruments")

        >>> # Get only ETFs
        >>> etfs = client.exchanges.get_instruments("SH", instrument_type="etf")
        >>> print(f"Found {len(etfs)} ETFs")
        """
        params = {}
        if instrument_type is not None:
            params["type"] = instrument_type
        response = self._client.get(
            f"/v1/exchanges/{exchange}/instruments", params=params or None
        )
        return response["data"]


class AsyncExchanges(AsyncResource):
    """Asynchronous interface for exchange endpoints.

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     exchanges = await client.exchanges.list()
    """

    async def list(self) -> List["ExchangeSummary"]:
        """Get list of all exchanges with instrument counts.

        Returns
        -------
        list of ExchangeSummary
            List of exchange information containing:
            - exchange: Exchange code (e.g., "SH", "SZ", "US")
            - region: Region code (e.g., "CN", "US", "HK")
            - count: Number of instruments in the exchange

        Examples
        --------
        >>> exchanges = await client.exchanges.list()
        >>> print(exchanges)
        [{'exchange': 'SH', 'region': 'CN', 'count': 2100}, ...]
        """
        response = await self._client.get("/v1/exchanges")
        return response["data"]

    async def get_instruments(
        self, exchange: str, instrument_type: Optional["InstrumentType"] = None
    ) -> List["Instrument"]:
        """Get all instruments for a specific exchange.

        Parameters
        ----------
        exchange : str
            Exchange code (e.g., "SH", "SZ", "BJ", "US", "HK").
        instrument_type : InstrumentType, optional
            Filter by instrument type (stock, etf, index, bond, fund, etc.).

        Returns
        -------
        list of Instrument
            List of instrument metadata.

        Examples
        --------
        >>> # Get all instruments
        >>> instruments = await client.exchanges.get_instruments("SH")
        >>> print(f"Found {len(instruments)} instruments")

        >>> # Get only ETFs
        >>> etfs = await client.exchanges.get_instruments("SH", instrument_type="etf")
        >>> print(f"Found {len(etfs)} ETFs")
        """
        params = {}
        if instrument_type is not None:
            params["type"] = instrument_type
        response = await self._client.get(
            f"/v1/exchanges/{exchange}/instruments", params=params or None
        )
        return response["data"]
