"""Instrument resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union, overload

from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    from ..generated_model import Instrument, InstrumentType


class Instruments(SyncResource):
    """Synchronous interface for instrument endpoints.

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>> inst = client.instruments.get("600000.SH")
    >>> print(f"{inst['symbol']}: {inst['name']}")
    """

    @overload
    def get(self, symbol: str) -> "Instrument": ...

    @overload
    def get(self, symbol: List[str]) -> List["Instrument"]: ...

    def get(
        self, symbol: Union[str, List[str]]
    ) -> Union["Instrument", List["Instrument"]]:
        """Get metadata for one or more instruments.

        Parameters
        ----------
        symbol : str or list of str
            Instrument code(s). Can be a single symbol string or a list of symbols.

        Returns
        -------
        Instrument or list of Instrument
            If a single symbol is provided, returns a single Instrument dict.
            If a list is provided, returns a list of Instrument dicts.

            Each Instrument contains:
            - symbol: Full symbol code (e.g., "600000.SH")
            - code: Exchange-specific code (e.g., "600000")
            - exchange: Exchange code (e.g., "SH")
            - region: Region code (e.g., "CN")
            - name: Instrument name
            - instrument_type: Type (stock, etf, index, etc.)
            - ext: Market-specific extension data

        Examples
        --------
        >>> # Single instrument
        >>> inst = client.instruments.get("600000.SH")
        >>> print(inst['name'])

        >>> # Multiple instruments
        >>> insts = client.instruments.get(["600000.SH", "AAPL.US"])
        >>> for i in insts:
        ...     print(f"{i['symbol']}: {i['name']}")
        """
        if isinstance(symbol, str):
            response = self._client.get("/v1/instruments", params={"symbols": symbol})
            data = response["data"]
            return data[0] if data else {}
        else:
            # Use POST for batch queries
            response = self._client.post("/v1/instruments", json={"symbols": symbol})
            return response["data"]

    def batch(self, symbols: List[str]) -> List["Instrument"]:
        """Get metadata for multiple instruments.

        This method uses POST to handle large batches without URL length limits.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes (up to 1000).

        Returns
        -------
        list of Instrument
            List of instrument metadata dicts.

        Examples
        --------
        >>> insts = client.instruments.batch(["600000.SH", "000001.SZ", "AAPL.US"])
        >>> for i in insts:
        ...     print(f"{i['symbol']}: {i['name']}")
        """
        response = self._client.post("/v1/instruments", json={"symbols": symbols})
        return response["data"]


class AsyncInstruments(AsyncResource):
    """Asynchronous interface for instrument endpoints.

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     inst = await client.instruments.get("600000.SH")
    """

    @overload
    async def get(self, symbol: str) -> "Instrument": ...

    @overload
    async def get(self, symbol: List[str]) -> List["Instrument"]: ...

    async def get(
        self, symbol: Union[str, List[str]]
    ) -> Union["Instrument", List["Instrument"]]:
        """Get metadata for one or more instruments.

        Parameters
        ----------
        symbol : str or list of str
            Instrument code(s). Can be a single symbol string or a list of symbols.

        Returns
        -------
        Instrument or list of Instrument
            If a single symbol is provided, returns a single Instrument dict.
            If a list is provided, returns a list of Instrument dicts.

            Each Instrument contains:
            - symbol: Full symbol code (e.g., "600000.SH")
            - code: Exchange-specific code (e.g., "600000")
            - exchange: Exchange code (e.g., "SH")
            - region: Region code (e.g., "CN")
            - name: Instrument name
            - instrument_type: Type (stock, etf, index, etc.)
            - ext: Market-specific extension data

        Examples
        --------
        >>> # Single instrument
        >>> inst = await client.instruments.get("600000.SH")
        >>> print(inst['name'])

        >>> # Multiple instruments
        >>> insts = await client.instruments.get(["600000.SH", "AAPL.US"])
        """
        if isinstance(symbol, str):
            response = await self._client.get(
                "/v1/instruments", params={"symbols": symbol}
            )
            data = response["data"]
            return data[0] if data else {}
        else:
            response = await self._client.post(
                "/v1/instruments", json={"symbols": symbol}
            )
            return response["data"]

    async def batch(self, symbols: List[str]) -> List["Instrument"]:
        """Get metadata for multiple instruments.

        This method uses POST to handle large batches without URL length limits.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes (up to 1000).

        Returns
        -------
        list of Instrument
            List of instrument metadata dicts.

        Examples
        --------
        >>> insts = await client.instruments.batch(["600000.SH", "000001.SZ", "AAPL.US"])
        """
        response = await self._client.post("/v1/instruments", json={"symbols": symbols})
        return response["data"]
