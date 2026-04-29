"""Financial data resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Union

from .._batch import batched_get_async, batched_get_sync
from .._types import NOT_GIVEN, NotGiven
from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    import pandas as pd

    from ..generated_model import (
        BalanceSheetRecord,
        CashFlowRecord,
        IncomeRecord,
        MetricsRecord,
        SharesRecord,
    )

MAX_FINANCIAL_SYMBOLS = 100

_STMT_ENDPOINTS = {
    "income": "/v1/financials/income",
    "balance_sheet": "/v1/financials/balance-sheet",
    "cash_flow": "/v1/financials/cash-flow",
    "metrics": "/v1/financials/metrics",
    "shares": "/v1/financials/shares",
}


def _financial_to_dataframe(
    data: Dict[str, List[dict]], statement: str
) -> "pd.DataFrame":
    """Convert financial dict response to a long-format DataFrame."""
    import pandas as pd

    rows = []
    for symbol, records in data.items():
        for rec in records:
            row = {"symbol": symbol, **rec}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


class Financials(SyncResource):
    """Synchronous interface for financial data endpoints.

    Supports four statement types: income, balance_sheet, cash_flow, metrics.

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>> income = client.financials.income(["600519.SH"])
    >>> df = client.financials.income(["600519.SH"], as_dataframe=True)
    """

    def _query(
        self,
        endpoint: str,
        symbols: List[str],
        start_date: Union[str, None, NotGiven],
        end_date: Union[str, None, NotGiven],
        latest: Union[bool, None, NotGiven],
        as_dataframe: bool,
        statement: str,
        batch_size: int,
        show_progress: bool,
        max_workers: int,
    ) -> Any:
        params: Dict[str, Any] = {}
        if not isinstance(start_date, NotGiven) and start_date is not None:
            params["start_date"] = start_date
        if not isinstance(end_date, NotGiven) and end_date is not None:
            params["end_date"] = end_date
        if not isinstance(latest, NotGiven) and latest is not None:
            params["latest"] = latest

        data = batched_get_sync(
            self._client,
            endpoint,
            symbols,
            params,
            batch_size=batch_size,
            max_workers=max_workers,
            show_progress=show_progress,
            progress_desc=f"Fetching {statement}",
        )
        if as_dataframe:
            return _financial_to_dataframe(data, statement)
        return data

    def income(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["IncomeRecord"]], "pd.DataFrame"]:
        """Get income statement data.

        Parameters
        ----------
        symbols : list of str
            Symbol codes (e.g., ["600519.SH"]).
        start_date : str, optional
            Filter: period_end >= start_date (YYYY-MM-DD).
        end_date : str, optional
            Filter: period_end <= end_date (YYYY-MM-DD).
        latest : bool, optional
            If True, return only the latest period.
        as_dataframe : bool, optional
            If True, return a pandas DataFrame.
        batch_size : int, optional
            Max symbols per request (default 100).
        show_progress : bool, optional
            Show a tqdm progress bar for multi-chunk fetches.
        max_workers : int, optional
            Concurrent request threads (default 5).
        """
        return self._query(
            _STMT_ENDPOINTS["income"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "income",
            batch_size,
            show_progress,
            max_workers,
        )

    def balance_sheet(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["BalanceSheetRecord"]], "pd.DataFrame"]:
        """Get balance sheet data."""
        return self._query(
            _STMT_ENDPOINTS["balance_sheet"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "balance_sheet",
            batch_size,
            show_progress,
            max_workers,
        )

    def cash_flow(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["CashFlowRecord"]], "pd.DataFrame"]:
        """Get cash flow statement data."""
        return self._query(
            _STMT_ENDPOINTS["cash_flow"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "cash_flow",
            batch_size,
            show_progress,
            max_workers,
        )

    def metrics(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["MetricsRecord"]], "pd.DataFrame"]:
        """Get core financial metrics (ROE, PE, etc.)."""
        return self._query(
            _STMT_ENDPOINTS["metrics"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "metrics",
            batch_size,
            show_progress,
            max_workers,
        )

    def shares(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_workers: int = 5,
    ) -> Union[Dict[str, List["SharesRecord"]], "pd.DataFrame"]:
        """Get shares data (total shares and float shares)."""
        return self._query(
            _STMT_ENDPOINTS["shares"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "shares",
            batch_size,
            show_progress,
            max_workers,
        )


class AsyncFinancials(AsyncResource):
    """Asynchronous interface for financial data endpoints.

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     df = await client.financials.income(["600519.SH"], as_dataframe=True)
    """

    async def _query(
        self,
        endpoint: str,
        symbols: List[str],
        start_date: Union[str, None, NotGiven],
        end_date: Union[str, None, NotGiven],
        latest: Union[bool, None, NotGiven],
        as_dataframe: bool,
        statement: str,
        batch_size: int,
        show_progress: bool,
        max_concurrency: int,
    ) -> Any:
        params: Dict[str, Any] = {}
        if not isinstance(start_date, NotGiven) and start_date is not None:
            params["start_date"] = start_date
        if not isinstance(end_date, NotGiven) and end_date is not None:
            params["end_date"] = end_date
        if not isinstance(latest, NotGiven) and latest is not None:
            params["latest"] = latest

        data = await batched_get_async(
            self._client,
            endpoint,
            symbols,
            params,
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            show_progress=show_progress,
            progress_desc=f"Fetching {statement}",
        )
        if as_dataframe:
            return _financial_to_dataframe(data, statement)
        return data

    async def income(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["IncomeRecord"]], "pd.DataFrame"]:
        """Get income statement data."""
        return await self._query(
            _STMT_ENDPOINTS["income"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "income",
            batch_size,
            show_progress,
            max_concurrency,
        )

    async def balance_sheet(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["BalanceSheetRecord"]], "pd.DataFrame"]:
        """Get balance sheet data."""
        return await self._query(
            _STMT_ENDPOINTS["balance_sheet"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "balance_sheet",
            batch_size,
            show_progress,
            max_concurrency,
        )

    async def cash_flow(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["CashFlowRecord"]], "pd.DataFrame"]:
        """Get cash flow statement data."""
        return await self._query(
            _STMT_ENDPOINTS["cash_flow"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "cash_flow",
            batch_size,
            show_progress,
            max_concurrency,
        )

    async def metrics(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["MetricsRecord"]], "pd.DataFrame"]:
        """Get core financial metrics (ROE, PE, etc.)."""
        return await self._query(
            _STMT_ENDPOINTS["metrics"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "metrics",
            batch_size,
            show_progress,
            max_concurrency,
        )

    async def shares(
        self,
        symbols: List[str],
        *,
        start_date: Union[str, None, NotGiven] = NOT_GIVEN,
        end_date: Union[str, None, NotGiven] = NOT_GIVEN,
        latest: Union[bool, None, NotGiven] = NOT_GIVEN,
        as_dataframe: bool = False,
        batch_size: int = MAX_FINANCIAL_SYMBOLS,
        show_progress: bool = False,
        max_concurrency: int = 5,
    ) -> Union[Dict[str, List["SharesRecord"]], "pd.DataFrame"]:
        """Get shares data (total shares and float shares)."""
        return await self._query(
            _STMT_ENDPOINTS["shares"],
            symbols,
            start_date,
            end_date,
            latest,
            as_dataframe,
            "shares",
            batch_size,
            show_progress,
            max_concurrency,
        )
