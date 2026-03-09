"""K-line (OHLCV) data resources for TickFlow API."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    overload,
)

from .._batch import _chunk_list, _get_progress_bar, batched_get_async, batched_get_sync
from .._cache import InstrumentNameCache
from .._types import NOT_GIVEN, NotGiven
from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    import pandas as pd

    from ..generated_model import AdjustType, CompactKlineData, ExFactorEntry, Period

# Maximum symbols per batch request (API limit)
MAX_SYMBOLS_PER_BATCH = 100


def _klines_to_dataframe(
    data: "CompactKlineData",
    symbol: Optional[str] = None,
    name: Optional[str] = None,
) -> "pd.DataFrame":
    """Convert compact K-line data to a pandas DataFrame.

    Parameters
    ----------
    data : CompactKlineData
        Compact columnar K-line data from the API.
    symbol : str, optional
        Symbol code to include as a column.
    name : str, optional
        Instrument name to include as a column.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: timestamp, open, high, low, close, volume, amount.
    """
    import datetime

    import pandas as pd

    from ..utils import get_instrument_region, get_region_timezone

    timestamps = data["timestamp"]

    if not timestamps:
        trade_dates = []
        trade_times = []
    else:
        region = get_instrument_region(symbol) if symbol else None
        tz = get_region_timezone(region) if region else None

        if tz:
            trade_dates = []
            trade_times = []
            append_date = trade_dates.append
            append_time = trade_times.append
            fromtimestamp = datetime.datetime.fromtimestamp

            for ts in timestamps:
                dt = fromtimestamp(ts / 1000, tz)
                append_date(f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}")
                append_time(
                    f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
                )
        else:
            n = len(timestamps)
            trade_dates = [None] * n
            trade_times = [None] * n

    df = pd.DataFrame(
        {
            "symbol": symbol,
            "name": name,
            "timestamp": timestamps,
            "trade_date": trade_dates,
            "trade_time": trade_times,
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"],
            "amount": (data["amount"] if "amount" in data else [0.0] * len(timestamps)),
        }
    )

    return df


def _batch_klines_to_dataframes(
    data: Dict[str, "CompactKlineData"],
    names: Optional[Dict[str, str]] = None,
) -> Dict[str, "pd.DataFrame"]:
    """Convert batch K-line data to DataFrames with optional name column.

    Parameters
    ----------
    data : dict
        Dictionary mapping symbol codes to compact K-line data.
    names : dict, optional
        Dictionary mapping symbol codes to instrument names.

    Returns
    -------
    dict of str to pd.DataFrame
        Dictionary mapping symbol codes to pandas DataFrames.
    """
    names = names or {}
    dfs: Dict[str, "pd.DataFrame"] = {}
    for symbol, kline_data in data.items():
        df = _klines_to_dataframe(kline_data, symbol=symbol, name=names.get(symbol))
        dfs[symbol] = df

    return dfs


def _factors_to_dataframe(
    data: Dict[str, List["ExFactorEntry"]],
) -> "pd.DataFrame":
    """Convert factor response to a single long-format DataFrame."""
    import pandas as pd

    from ..utils import get_instrument_region, get_region_timezone

    if not data:
        return pd.DataFrame(columns=["symbol", "timestamp", "trade_date", "ex_factor"])

    rows = []
    for symbol, entries in data.items():
        if not entries:
            continue

        region = get_instrument_region(symbol)
        tz = get_region_timezone(region) if region else None

        timestamps = [e["timestamp"] for e in entries]

        if tz:
            ts_series = pd.to_datetime(timestamps, unit="ms", utc=True).tz_convert(tz)
            trade_dates = ts_series.strftime("%Y-%m-%d").tolist()
        else:
            trade_dates = [None] * len(timestamps)

        for i, e in enumerate(entries):
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": e["timestamp"],
                    "trade_date": trade_dates[i],
                    "ex_factor": e["ex_factor"],
                }
            )

    return (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(columns=["symbol", "timestamp", "trade_date", "ex_factor"])
    )


class Klines(SyncResource):
    """Synchronous interface for K-line (OHLCV) data endpoints.

    Supports returning data as raw dicts or pandas DataFrames.
    When returning DataFrames, instrument names are automatically resolved
    from a local cache (fetched from the instruments API on first access).

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>>
    >>> # Get raw K-line data
    >>> klines = client.klines.get("600000.SH", count=100)
    >>>
    >>> # Get as DataFrame (includes name column)
    >>> df = client.klines.get("600000.SH", count=100, as_dataframe=True)
    >>> print(df.head())
    """

    _instrument_cache: Optional[InstrumentNameCache]

    def __init__(
        self, client: Any, instrument_cache: Optional[InstrumentNameCache] = None
    ) -> None:
        super().__init__(client)
        self._instrument_cache = instrument_cache

    def _resolve_name(self, symbol: str) -> Optional[str]:
        if not self._instrument_cache:
            return None
        names = self._instrument_cache.resolve_sync([symbol], self._client)
        return names.get(symbol)

    def _resolve_names(self, symbols: List[str]) -> Dict[str, str]:
        if not self._instrument_cache:
            return {}
        return self._instrument_cache.resolve_sync(symbols, self._client)

    @overload
    def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
    ) -> "CompactKlineData": ...

    @overload
    def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
    ) -> Union["CompactKlineData", "pd.DataFrame"]:
        """Get K-line (OHLCV) data for a single symbol.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g., "600000.SH", "AAPL.US").
        period : str, optional
            K-line period. One of: "1m", "5m", "10m", "15m", "30m", "60m",
            "4h", "1d", "1w", "1M". Defaults to "1d".
        count : int, optional
            Number of K-lines to return. Default 100, max 10000.
        start_time : int, optional
            Start timestamp in milliseconds.
        end_time : int, optional
            End timestamp in milliseconds.
        adjust : str, optional
            Adjustment type: "forward" (前复权, default), "backward" (后复权),
            or "none" (不复权).
        as_dataframe : bool, optional
            If True, return a pandas DataFrame. If False (default), return
            the raw compact columnar data.

        Returns
        -------
        CompactKlineData or pd.DataFrame
            If as_dataframe=False: dict with keys 'timestamp', 'open', 'high',
            'low', 'close', 'volume', 'amount' (each a list).
            If as_dataframe=True: pandas DataFrame with datetime index.

        Examples
        --------
        >>> # Get forward-adjusted data (default)
        >>> df = client.klines.get("600519.SH", period="1d", count=100, as_dataframe=True)
        >>>
        >>> # Get unadjusted data
        >>> df_raw = client.klines.get("600519.SH", adjust="none", as_dataframe=True)
        >>>
        >>> # Get backward-adjusted data
        >>> df_hfq = client.klines.get("600519.SH", adjust="backward", as_dataframe=True)
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time
        if not isinstance(adjust, NotGiven):
            params["adjust"] = adjust

        response = self._client.get("/v1/klines", params=params)
        data = response["data"]

        if as_dataframe:
            name = self._resolve_name(symbol)
            return _klines_to_dataframe(data, symbol=symbol, name=name)
        return data

    def _fetch_batch_chunk(
        self,
        symbols: List[str],
        params: Dict[str, Any],
        endpoint: str = "/v1/klines/batch",
    ) -> Tuple[Dict[str, "CompactKlineData"], List[Tuple[str, Exception]]]:
        """Fetch a single batch chunk.

        Returns
        -------
        tuple
            (data dict, list of (symbol, error) for failed symbols)
        """
        symbols_str = ",".join(symbols)
        chunk_params = {**params, "symbols": symbols_str}

        response = self._client.get(endpoint, params=chunk_params)
        return response["data"], []

    def _run_batch(
        self,
        symbols: List[str],
        params: Dict[str, Any],
        endpoint: str,
        batch_size: int,
        as_dataframe: bool,
        show_progress: bool,
        max_workers: int,
        progress_desc: str = "Fetching K-lines",
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        if not symbols:
            return {} if not as_dataframe else _batch_klines_to_dataframes({})

        chunks = _chunk_list(symbols, batch_size)

        if len(chunks) == 1:
            data, errors = self._fetch_batch_chunk(chunks[0], params, endpoint)
            if as_dataframe:
                names = self._resolve_names(list(data.keys()))
                return _batch_klines_to_dataframes(data, names=names)
            return data

        pbar = _get_progress_bar(len(chunks), progress_desc, show_progress)

        all_data: Dict[str, "CompactKlineData"] = {}
        all_errors: List[Tuple[str, Exception]] = []

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = {
                    executor.submit(
                        self._fetch_batch_chunk, chunk, params, endpoint
                    ): chunk
                    for chunk in chunks
                }

                for future in concurrent.futures.as_completed(futures):
                    try:
                        data, errors = future.result()
                        all_data.update(data)
                        all_errors.extend(errors)
                    except Exception as e:
                        chunk = futures[future]
                        all_errors.extend((s, e) for s in chunk)

                    if pbar:
                        pbar.update(1)
        finally:
            if pbar:
                pbar.close()

        if as_dataframe:
            names = self._resolve_names(list(all_data.keys()))
            return _batch_klines_to_dataframes(all_data, names=names)
        return all_data

    @overload
    def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Dict[str, "CompactKlineData"]: ...

    @overload
    def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> "pd.DataFrame": ...

    def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        """Get K-line data for multiple symbols in batched concurrent requests.

        Automatically splits large symbol lists into chunks and fetches them
        concurrently. Failed chunks don't affect other chunks.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        period : str, optional
            K-line period. Defaults to "1d".
        count : int, optional
            Number of K-lines per symbol. Default 100.
        start_time : int, optional
            Start timestamp in milliseconds.
        end_time : int, optional
            End timestamp in milliseconds.
        adjust : str, optional
            Adjustment type: "forward" (前复权, default), "backward" (后复权),
            or "none" (不复权).
        as_dataframe : bool, optional
            If True, return dict of DataFrames. Default False.
        show_progress : bool, optional
            If True, display a progress bar (requires tqdm). Default False.
        max_workers : int, optional
            Maximum number of concurrent requests. Default 5.
        batch_size : int, optional
            Number of symbols per request. Default 100.
            Reduce this if the server enforces a lower per-request limit.

        Returns
        -------
        dict or pd.DataFrame
            If as_dataframe=False: dict mapping symbol codes to CompactKlineData.
            If as_dataframe=True: dict mapping symbol codes to DataFrames.

        Examples
        --------
        >>> symbols = client.exchanges.get_symbols("SH")[:500]
        >>> dfs = client.klines.batch(symbols, as_dataframe=True, show_progress=True)
        """
        params: Dict[str, Any] = {}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time
        if not isinstance(adjust, NotGiven):
            params["adjust"] = adjust

        return self._run_batch(
            symbols=symbols,
            params=params,
            endpoint="/v1/klines/batch",
            batch_size=batch_size,
            as_dataframe=as_dataframe,
            show_progress=show_progress,
            max_workers=max_workers,
            progress_desc="Fetching K-lines",
        )

    @overload
    def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
    ) -> "CompactKlineData": ...

    @overload
    def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
    ) -> Union["CompactKlineData", "pd.DataFrame"]:
        """Get intraday minute K-line data for a single symbol.

        This endpoint returns today's minute-level K-line data. The data is
        continuously updated during trading hours.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g., "600000.SH", "AAPL.US").
        period : str, optional
            K-line period. One of: "1m", "5m", "15m", "30m", "60m".
            Defaults to "1m".
        count : int, optional
            Number of K-lines to return. If not specified, returns all
            available data for today.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame. If False (default), return
            the raw compact columnar data.

        Returns
        -------
        CompactKlineData or pd.DataFrame
            If as_dataframe=False: dict with keys 'timestamp', 'open', 'high',
            'low', 'close', 'volume', 'amount' (each a list).
            If as_dataframe=True: pandas DataFrame with datetime index.

        Examples
        --------
        >>> # Get today's 1-minute K-lines
        >>> data = client.klines.intraday("600000.SH")
        >>> print(f"Got {len(data['timestamp'])} bars")

        >>> # Get as DataFrame
        >>> df = client.klines.intraday("600000.SH", as_dataframe=True)
        >>> print(df.tail())

        >>> # Get 5-minute aggregated data
        >>> df = client.klines.intraday("600000.SH", period="5m", as_dataframe=True)
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count

        response = self._client.get("/v1/klines/intraday", params=params)
        data = response["data"]

        if as_dataframe:
            name = self._resolve_name(symbol)
            return _klines_to_dataframe(data, symbol=symbol, name=name)
        return data

    @overload
    def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Dict[str, "CompactKlineData"]: ...

    @overload
    def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> "pd.DataFrame": ...

    def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        show_progress: bool = False,
        max_workers: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        """Get intraday K-line data for multiple symbols in batched concurrent requests.

        Automatically splits large symbol lists into chunks and fetches them
        concurrently. Failed chunks don't affect other chunks.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        period : str, optional
            K-line period. One of: "1m", "5m", "15m", "30m", "60m".
            Defaults to "1m".
        count : int, optional
            Number of K-lines per symbol. If not specified, returns all
            available data for today.
        as_dataframe : bool, optional
            If True, return dict of DataFrames. Default False.
        show_progress : bool, optional
            If True, display a progress bar (requires tqdm). Default False.
        max_workers : int, optional
            Maximum number of concurrent requests. Default 5.
        batch_size : int, optional
            Number of symbols per request. Default 100.
            Reduce this if the server enforces a lower per-request limit.

        Returns
        -------
        dict or pd.DataFrame
            If as_dataframe=False: dict mapping symbol codes to CompactKlineData.
            If as_dataframe=True: dict mapping symbol codes to DataFrames.

        Examples
        --------
        >>> symbols = ["600000.SH", "000001.SZ", "600519.SH"]
        >>> dfs = client.klines.intraday_batch(symbols, as_dataframe=True)
        """
        params: Dict[str, Any] = {}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count

        return self._run_batch(
            symbols=symbols,
            params=params,
            endpoint="/v1/klines/intraday/batch",
            batch_size=batch_size,
            as_dataframe=as_dataframe,
            show_progress=show_progress,
            max_workers=max_workers,
            progress_desc="Fetching intraday K-lines",
        )

    def ex_factors(
        self,
        symbols: List[str],
        *,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["ExFactorEntry"]], "pd.DataFrame"]:
        """Get dividend/split adjustment factors for one or more symbols.

        Parameters
        ----------
        symbols : list of str
            Symbol codes (e.g., ["600519.SH", "000001.SZ"]).
        start_time : int, optional
            Filter: only factors with timestamp >= start_time (ms).
        end_time : int, optional
            Filter: only factors with timestamp <= end_time (ms).
        as_dataframe : bool, optional
            If True, return a long-format pandas DataFrame with columns:
            symbol, timestamp, ex_factor, trade_date.
        batch_size : int, optional
            Max symbols per request (default 100).
        show_progress : bool, optional
            Show a tqdm progress bar for multi-chunk fetches.
        max_workers : int, optional
            Concurrent request threads (default 5).

        Returns
        -------
        dict or pd.DataFrame
            If as_dataframe=False: ``{symbol: [{timestamp, ex_factor}, ...]}``.
            If as_dataframe=True: long-format DataFrame.

        Examples
        --------
        >>> factors = client.klines.ex_factors(["600519.SH"])
        >>> df = client.klines.ex_factors(["600519.SH", "000001.SZ"], as_dataframe=True)
        """
        params: Dict[str, Any] = {}
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time

        data = batched_get_sync(
            self._client,
            "/v1/klines/ex-factors",
            symbols,
            params,
            batch_size=batch_size,
            max_workers=max_workers,
            show_progress=show_progress,
            progress_desc="Fetching ex-factors",
        )
        if as_dataframe:
            return _factors_to_dataframe(data)
        return data


class AsyncKlines(AsyncResource):
    """Asynchronous interface for K-line (OHLCV) data endpoints.

    Supports returning data as raw dicts or pandas DataFrames.
    When returning DataFrames, instrument names are automatically resolved
    from a local cache (fetched from the instruments API on first access).

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     # Get raw K-line data
    ...     klines = await client.klines.get("600000.SH", count=100)
    ...
    ...     # Get as DataFrame (includes name column)
    ...     df = await client.klines.get("600000.SH", count=100, as_dataframe=True)
    """

    _instrument_cache: Optional[InstrumentNameCache]

    def __init__(
        self, client: Any, instrument_cache: Optional[InstrumentNameCache] = None
    ) -> None:
        super().__init__(client)
        self._instrument_cache = instrument_cache

    async def _resolve_name(self, symbol: str) -> Optional[str]:
        if not self._instrument_cache:
            return None
        names = await self._instrument_cache.resolve_async([symbol], self._client)
        return names.get(symbol)

    async def _resolve_names(self, symbols: List[str]) -> Dict[str, str]:
        if not self._instrument_cache:
            return {}
        return await self._instrument_cache.resolve_async(symbols, self._client)

    @overload
    async def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
    ) -> "CompactKlineData": ...

    @overload
    async def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    async def get(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
    ) -> Union["CompactKlineData", "pd.DataFrame"]:
        """Get K-line (OHLCV) data for a single symbol.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g., "600000.SH", "AAPL.US").
        period : str, optional
            K-line period. One of: "1m", "5m", "10m", "15m", "30m", "60m",
            "4h", "1d", "1w", "1M". Defaults to "1d".
        count : int, optional
            Number of K-lines to return. Default 100, max 10000.
        start_time : int, optional
            Start timestamp in milliseconds.
        end_time : int, optional
            End timestamp in milliseconds.
        adjust : str, optional
            Adjustment type: "forward" (前复权, default), "backward" (后复权),
            or "none" (不复权).
        as_dataframe : bool, optional
            If True, return a pandas DataFrame. If False (default), return
            the raw compact columnar data.

        Returns
        -------
        CompactKlineData or pd.DataFrame
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time
        if not isinstance(adjust, NotGiven):
            params["adjust"] = adjust

        response = await self._client.get("/v1/klines", params=params)
        data = response["data"]

        if as_dataframe:
            name = await self._resolve_name(symbol)
            return _klines_to_dataframe(data, symbol=symbol, name=name)
        return data

    async def _fetch_batch_chunk(
        self,
        symbols: List[str],
        params: Dict[str, Any],
        endpoint: str = "/v1/klines/batch",
    ) -> Tuple[Dict[str, "CompactKlineData"], List[Tuple[str, Exception]]]:
        """Fetch a single batch chunk asynchronously.

        Returns
        -------
        tuple
            (data dict, list of (symbol, error) for failed symbols)
        """
        symbols_str = ",".join(symbols)
        chunk_params = {**params, "symbols": symbols_str}

        try:
            response = await self._client.get(endpoint, params=chunk_params)
            return response["data"], []
        except Exception as e:
            return {}, [(s, e) for s in symbols]

    async def _run_batch(
        self,
        symbols: List[str],
        params: Dict[str, Any],
        endpoint: str,
        batch_size: int,
        as_dataframe: bool,
        show_progress: bool,
        max_concurrency: int,
        progress_desc: str = "Fetching K-lines",
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        if not symbols:
            return {} if not as_dataframe else _batch_klines_to_dataframes({})

        chunks = _chunk_list(symbols, batch_size)

        if len(chunks) == 1:
            data, errors = await self._fetch_batch_chunk(chunks[0], params, endpoint)
            if as_dataframe:
                names = await self._resolve_names(list(data.keys()))
                return _batch_klines_to_dataframes(data, names=names)
            return data

        pbar = _get_progress_bar(len(chunks), progress_desc, show_progress)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def fetch_with_semaphore(
            chunk: List[str],
        ) -> Tuple[Dict[str, "CompactKlineData"], List[Tuple[str, Exception]]]:
            async with semaphore:
                result = await self._fetch_batch_chunk(chunk, params, endpoint)
                if pbar:
                    pbar.update(1)
                return result

        all_data: Dict[str, "CompactKlineData"] = {}
        all_errors: List[Tuple[str, Exception]] = []

        try:
            tasks = [fetch_with_semaphore(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    all_errors.extend((s, result) for s in chunks[i])
                else:
                    data, errors = result
                    all_data.update(data)
                    all_errors.extend(errors)
        finally:
            if pbar:
                pbar.close()

        if as_dataframe:
            names = await self._resolve_names(list(all_data.keys()))
            return _batch_klines_to_dataframes(all_data, names=names)
        return all_data

    @overload
    async def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Dict[str, "CompactKlineData"]: ...

    @overload
    async def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> "pd.DataFrame": ...

    async def batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        adjust: Union["AdjustType", NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        """Get K-line data for multiple symbols in batched concurrent requests.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        period : str, optional
            K-line period. Defaults to "1d".
        count : int, optional
            Number of K-lines per symbol. Default 100.
        start_time : int, optional
            Start timestamp in milliseconds.
        end_time : int, optional
            End timestamp in milliseconds.
        adjust : str, optional
            Adjustment type: "forward" (前复权, default), "backward" (后复权),
            or "none" (不复权).
        as_dataframe : bool, optional
            If True, return dict of DataFrames. Default False.
        show_progress : bool, optional
            If True, display a progress bar (requires tqdm). Default False.
        max_concurrency : int, optional
            Maximum number of concurrent requests. Default 5.
        batch_size : int, optional
            Number of symbols per request. Default 100.

        Returns
        -------
        dict or pd.DataFrame
        """
        params: Dict[str, Any] = {}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time
        if not isinstance(adjust, NotGiven):
            params["adjust"] = adjust

        return await self._run_batch(
            symbols=symbols,
            params=params,
            endpoint="/v1/klines/batch",
            batch_size=batch_size,
            as_dataframe=as_dataframe,
            show_progress=show_progress,
            max_concurrency=max_concurrency,
            progress_desc="Fetching K-lines",
        )

    @overload
    async def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
    ) -> "CompactKlineData": ...

    @overload
    async def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
    ) -> "pd.DataFrame": ...

    async def intraday(
        self,
        symbol: str,
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
    ) -> Union["CompactKlineData", "pd.DataFrame"]:
        """Get intraday minute K-line data for a single symbol.

        This endpoint returns today's minute-level K-line data. The data is
        continuously updated during trading hours.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g., "600000.SH", "AAPL.US").
        period : str, optional
            K-line period. One of: "1m", "5m", "15m", "30m", "60m".
            Defaults to "1m".
        count : int, optional
            Number of K-lines to return. If not specified, returns all
            available data for today.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame. If False (default), return
            the raw compact columnar data.

        Returns
        -------
        CompactKlineData or pd.DataFrame
            If as_dataframe=False: dict with keys 'timestamp', 'open', 'high',
            'low', 'close', 'volume', 'amount' (each a list).
            If as_dataframe=True: pandas DataFrame with datetime index.

        Examples
        --------
        >>> # Get today's 1-minute K-lines
        >>> data = await client.klines.intraday("600000.SH")
        >>> print(f"Got {len(data['timestamp'])} bars")

        >>> # Get as DataFrame
        >>> df = await client.klines.intraday("600000.SH", as_dataframe=True)
        >>> print(df.tail())
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count

        response = await self._client.get("/v1/klines/intraday", params=params)
        data = response["data"]

        if as_dataframe:
            name = await self._resolve_name(symbol)
            return _klines_to_dataframe(data, symbol=symbol, name=name)
        return data

    @overload
    async def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[False] = False,
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Dict[str, "CompactKlineData"]: ...

    @overload
    async def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: Literal[True],
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> "pd.DataFrame": ...

    async def intraday_batch(
        self,
        symbols: List[str],
        *,
        period: Union["Period", NotGiven] = NOT_GIVEN,
        count: Union[int, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        show_progress: bool = False,
        max_concurrency: int = 5,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
    ) -> Union[Dict[str, "CompactKlineData"], "pd.DataFrame"]:
        """Get intraday K-line data for multiple symbols in batched concurrent requests.

        Automatically splits large symbol lists into chunks and fetches them
        concurrently. Failed chunks don't affect other chunks.

        Parameters
        ----------
        symbols : list of str
            List of symbol codes.
        period : str, optional
            K-line period. One of: "1m", "5m", "15m", "30m", "60m".
            Defaults to "1m".
        count : int, optional
            Number of K-lines per symbol. If not specified, returns all
            available data for today.
        as_dataframe : bool, optional
            If True, return dict of DataFrames. Default False.
        show_progress : bool, optional
            If True, display a progress bar (requires tqdm). Default False.
        max_concurrency : int, optional
            Maximum number of concurrent requests. Default 5.
        batch_size : int, optional
            Number of symbols per request. Default 100.
            Reduce this if the server enforces a lower per-request limit.

        Returns
        -------
        dict or pd.DataFrame
            If as_dataframe=False: dict mapping symbol codes to CompactKlineData.
            If as_dataframe=True: dict mapping symbol codes to DataFrames.

        Examples
        --------
        >>> symbols = ["600000.SH", "000001.SZ", "600519.SH"]
        >>> dfs = await client.klines.intraday_batch(symbols, as_dataframe=True)
        """
        params: Dict[str, Any] = {}
        if not isinstance(period, NotGiven):
            params["period"] = period
        if not isinstance(count, NotGiven):
            params["count"] = count

        return await self._run_batch(
            symbols=symbols,
            params=params,
            endpoint="/v1/klines/intraday/batch",
            batch_size=batch_size,
            as_dataframe=as_dataframe,
            show_progress=show_progress,
            max_concurrency=max_concurrency,
            progress_desc="Fetching intraday K-lines",
        )

    async def ex_factors(
        self,
        symbols: List[str],
        *,
        start_time: Union[int, None, NotGiven] = NOT_GIVEN,
        end_time: Union[int, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_SYMBOLS_PER_BATCH,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["ExFactorEntry"]], "pd.DataFrame"]:
        """Get dividend/split adjustment factors for one or more symbols.

        Parameters
        ----------
        symbols : list of str
            Symbol codes (e.g., ["600519.SH", "000001.SZ"]).
        start_time : int, optional
            Filter: only factors with timestamp >= start_time (ms).
        end_time : int, optional
            Filter: only factors with timestamp <= end_time (ms).
        as_dataframe : bool, optional
            If True, return a long-format pandas DataFrame.
        batch_size : int, optional
            Max symbols per request (default 100).
        show_progress : bool, optional
            Show a tqdm progress bar for multi-chunk fetches.
        max_concurrency : int, optional
            Concurrent async requests (default 5).

        Returns
        -------
        dict or pd.DataFrame
        """
        params: Dict[str, Any] = {}
        if not isinstance(start_time, NotGiven) and start_time is not None:
            params["start_time"] = start_time
        if not isinstance(end_time, NotGiven) and end_time is not None:
            params["end_time"] = end_time

        data = await batched_get_async(
            self._client,
            "/v1/klines/ex-factors",
            symbols,
            params,
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            show_progress=show_progress,
            progress_desc="Fetching ex-factors",
        )
        if as_dataframe:
            return _factors_to_dataframe(data)
        return data
