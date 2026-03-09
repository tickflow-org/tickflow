"""Real-time quote resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Union, overload

from .._types import NOT_GIVEN, NotGiven
from ..utils import (
    instrument_timestamp_to_trade_date,
    instrument_timestamp_to_trade_time,
)
from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    import pandas as pd

    from ..generated_model import Quote


def _quotes_to_dataframe(data: List["Quote"]) -> "pd.DataFrame":
    """Convert quote data to a pandas DataFrame.

    Parameters
    ----------
    data : list of Quote
        List of quote dictionaries.

    Returns
    -------
    pd.DataFrame
        DataFrame with symbol as index. Includes trade_date, trade_time columns
        and flattened ext fields with "ext." prefix (e.g., ext.limit_up, ext.change_pct).
    """
    import pandas as pd

    if not data:
        return pd.DataFrame()

    # Build rows with flattened ext fields
    rows = []
    for q in data:
        row = {
            k: v
            for k, v in q.items()
            if k not in ("ext", "session")  # Handle ext separately, skip session
        }

        # Add trade_date and trade_time
        row["trade_date"] = instrument_timestamp_to_trade_date(
            q["symbol"], q["timestamp"], unit="ms"
        )
        row["trade_time"] = instrument_timestamp_to_trade_time(
            q["symbol"], q["timestamp"], unit="ms"
        )

        # Flatten ext field with "ext." prefix for all fields
        ext = q.get("ext")
        if ext:
            for key, value in ext.items():
                # Skip None values and nested dicts (like bid_ask)
                if value is not None and not isinstance(value, dict):
                    row[f"ext.{key}"] = value

        rows.append(row)

    df = pd.DataFrame(rows)
    return df


class Quotes(SyncResource):
    """Synchronous interface for real-time quote endpoints.

    Supports querying quotes by symbol codes or universe IDs.

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>>
    >>> # Get quotes by symbols
    >>> quotes = client.quotes.get(symbols=["600000.SH", "AAPL.US"])
    >>>
    >>> # Get quotes by universe
    >>> quotes = client.quotes.get(universes=["CN_Equity_A"])
    """

    @overload
    def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: Literal[False] = False,
    ) -> List["Quote"]: ...

    @overload
    def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for symbols or universes.

        Must provide either `symbols` or `universes`, but not both.

        Parameters
        ----------
        symbols : str or list of str, optional
            Symbol code(s) to query. Can be a single symbol, comma-separated
            string, or list of symbols.
        universes : str or list of str, optional
            Universe ID(s) to query. Can be a single ID, comma-separated
            string, or list of IDs.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame indexed by symbol.
            If False (default), return a list of Quote dicts.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for the requested symbols.

            Each Quote contains:
            - symbol: Symbol code
            - name: Symbol name
            - region: Region code
            - last_price: Latest price
            - prev_close: Previous close
            - open, high, low: OHLC prices
            - volume: Trading volume
            - amount: Trading amount
            - timestamp: Quote timestamp (milliseconds)
            - session: Trading session status
            - ext: Market-specific extension data

        Raises
        ------
        ValueError
            If neither or both of `symbols` and `universes` are provided.

        Examples
        --------
        >>> # Query by symbols
        >>> quotes = client.quotes.get(symbols=["600000.SH", "AAPL.US"])
        >>> for q in quotes:
        ...     print(f"{q['symbol']}: {q['last_price']}")

        >>> # Query by universe, as DataFrame
        >>> df = client.quotes.get(universes="CN_Equity_A", as_dataframe=True)
        >>> print(df[["last_price", "volume"]].head())

        >>> # Find top gainers
        >>> df["change_pct"] = (df["last_price"] - df["prev_close"]) / df["prev_close"] * 100
        >>> top_gainers = df.nlargest(10, "change_pct")
        """
        if (symbols is None) == (universes is None):
            raise ValueError(
                "Must provide either 'symbols' or 'universes', but not both"
            )

        # Determine whether to use GET (small query) or POST (large query)
        if symbols is not None:
            if isinstance(symbols, str):
                symbols_list = [s.strip() for s in symbols.split(",")]
            else:
                symbols_list = symbols

            if len(symbols_list) <= 20:
                # Use GET for small queries
                response = self._client.get(
                    "/v1/quotes", params={"symbols": ",".join(symbols_list)}
                )
            else:
                # Use POST for large queries
                response = self._client.post(
                    "/v1/quotes", json={"symbols": symbols_list}
                )
        else:
            # Universe query
            if isinstance(universes, str):
                universes_list = [u.strip() for u in universes.split(",")]
            else:
                universes_list = universes

            if len(universes_list) <= 5:
                response = self._client.get(
                    "/v1/quotes", params={"universes": ",".join(universes_list)}
                )
            else:
                response = self._client.post(
                    "/v1/quotes", json={"universes": universes_list}
                )

        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data

    def get_by_symbols(
        self,
        symbols: List[str],
        *,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for a list of symbols.

        This is a convenience method that always uses POST for batch queries.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for the requested symbols.

        Examples
        --------
        >>> quotes = client.quotes.get_by_symbols(["600000.SH", "000001.SZ", "AAPL.US"])
        """
        response = self._client.post("/v1/quotes", json={"symbols": symbols})
        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data

    def get_by_universes(
        self,
        universes: List[str],
        *,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for all symbols in the specified universes.

        Parameters
        ----------
        universes : list of str
            List of universe IDs.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for all symbols in the universes.

        Examples
        --------
        >>> # Get all A-share quotes
        >>> quotes = client.quotes.get_by_universes(["CN_Equity_A"], as_dataframe=True)
        """
        response = self._client.post("/v1/quotes", json={"universes": universes})
        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data


class AsyncQuotes(AsyncResource):
    """Asynchronous interface for real-time quote endpoints.

    Supports querying quotes by symbol codes or universe IDs.

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     quotes = await client.quotes.get(symbols=["600000.SH", "AAPL.US"])
    """

    @overload
    async def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: Literal[False] = False,
    ) -> List["Quote"]: ...

    @overload
    async def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    async def get(
        self,
        *,
        symbols: Union[List[str], str, None] = None,
        universes: Union[List[str], str, None] = None,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for symbols or universes.

        Must provide either `symbols` or `universes`, but not both.

        Parameters
        ----------
        symbols : str or list of str, optional
            Symbol code(s) to query.
        universes : str or list of str, optional
            Universe ID(s) to query.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame indexed by symbol.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for the requested symbols.

        Examples
        --------
        >>> quotes = await client.quotes.get(symbols=["600000.SH", "AAPL.US"])
        >>> df = await client.quotes.get(universes="CN_Equity_A", as_dataframe=True)
        """
        if (symbols is None) == (universes is None):
            raise ValueError(
                "Must provide either 'symbols' or 'universes', but not both"
            )

        if symbols is not None:
            if isinstance(symbols, str):
                symbols_list = [s.strip() for s in symbols.split(",")]
            else:
                symbols_list = symbols

            if len(symbols_list) <= 20:
                response = await self._client.get(
                    "/v1/quotes", params={"symbols": ",".join(symbols_list)}
                )
            else:
                response = await self._client.post(
                    "/v1/quotes", json={"symbols": symbols_list}
                )
        else:
            if isinstance(universes, str):
                universes_list = [u.strip() for u in universes.split(",")]
            else:
                universes_list = universes

            if len(universes_list) <= 5:
                response = await self._client.get(
                    "/v1/quotes", params={"universes": ",".join(universes_list)}
                )
            else:
                response = await self._client.post(
                    "/v1/quotes", json={"universes": universes_list}
                )

        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data

    async def get_by_symbols(
        self,
        symbols: List[str],
        *,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for a list of symbols.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for the requested symbols.
        """
        response = await self._client.post("/v1/quotes", json={"symbols": symbols})
        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data

    async def get_by_universes(
        self,
        universes: List[str],
        *,
        as_dataframe: bool = False,
    ) -> Union[List["Quote"], "pd.DataFrame"]:
        """Get real-time quotes for all symbols in the specified universes.

        Parameters
        ----------
        universes : list of str
            List of universe IDs.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame.

        Returns
        -------
        list of Quote or pd.DataFrame
            Quote data for all symbols in the universes.
        """
        response = await self._client.post("/v1/quotes", json={"universes": universes})
        data = response["data"]

        if as_dataframe:
            return _quotes_to_dataframe(data)
        return data
