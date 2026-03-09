"""Universe resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    from ..generated_model import UniverseDetail, UniverseSummary


class Universes(SyncResource):
    """Synchronous interface for universe (symbol pool) endpoints.

    Universes are predefined collections of symbols, such as "A-shares" or "US equities".

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>> universes = client.universes.list()
    >>> for u in universes:
    ...     print(f"{u['id']}: {u['name']} ({u['symbol_count']} symbols)")
    """

    def list(self) -> List["UniverseSummary"]:
        """Get list of all available universes.

        Returns
        -------
        list of UniverseSummary
            List of universe summaries containing:
            - id: Unique identifier (e.g., "CN_Equity_A")
            - name: Display name
            - region: Region code
            - category: Category (equity, etf, index, etc.)
            - symbol_count: Number of symbols
            - description: Optional description

        Examples
        --------
        >>> universes = client.universes.list()
        >>> cn_equity = next(u for u in universes if u['id'] == 'CN_Equity_A')
        >>> print(f"A-shares: {cn_equity['symbol_count']} symbols")
        """
        response = self._client.get("/v1/universes")
        return response["data"]

    def get(self, universe_id: str) -> "UniverseDetail":
        """Get detailed information for a specific universe.

        Parameters
        ----------
        universe_id : str
            Universe identifier (e.g., "CN_Equity_A", "US_Equity").

        Returns
        -------
        UniverseDetail
            Universe details including the full list of symbols:
            - id: Unique identifier
            - name: Display name
            - region: Region code
            - category: Category
            - symbol_count: Number of symbols
            - symbols: List of symbol codes
            - description: Optional description

        Examples
        --------
        >>> universe = client.universes.get("CN_Equity_A")
        >>> print(f"Found {len(universe['symbols'])} A-share symbols")
        """
        response = self._client.get(f"/v1/universes/{universe_id}")
        return response["data"]

    def batch(self, ids: List[str]) -> Dict[str, "UniverseDetail"]:
        """Batch get detailed information for multiple universes.

        Only valid universe IDs will be included in the response.

        Parameters
        ----------
        ids : list of str
            List of universe identifiers (e.g., ["CN_Equity_A", "CN_ETF"]).

        Returns
        -------
        dict of str to UniverseDetail
            Mapping from valid universe ID to its detail.

        Examples
        --------
        >>> details = client.universes.batch(["CN_Equity_A", "CN_ETF"])
        >>> for uid, detail in details.items():
        ...     print(f"{uid}: {detail['symbol_count']} symbols")
        """
        response = self._client.post("/v1/universes/batch", json={"ids": ids})
        return response["data"]


class AsyncUniverses(AsyncResource):
    """Asynchronous interface for universe (symbol pool) endpoints.

    Universes are predefined collections of symbols, such as "A-shares" or "US equities".

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     universes = await client.universes.list()
    """

    async def list(self) -> List["UniverseSummary"]:
        """Get list of all available universes.

        Returns
        -------
        list of UniverseSummary
            List of universe summaries containing:
            - id: Unique identifier (e.g., "CN_Equity_A")
            - name: Display name
            - region: Region code
            - category: Category (equity, etf, index, etc.)
            - symbol_count: Number of symbols
            - description: Optional description

        Examples
        --------
        >>> universes = await client.universes.list()
        >>> cn_equity = next(u for u in universes if u['id'] == 'CN_Equity_A')
        >>> print(f"A-shares: {cn_equity['symbol_count']} symbols")
        """
        response = await self._client.get("/v1/universes")
        return response["data"]

    async def get(self, universe_id: str) -> "UniverseDetail":
        """Get detailed information for a specific universe.

        Parameters
        ----------
        universe_id : str
            Universe identifier (e.g., "CN_Equity_A", "US_Equity").

        Returns
        -------
        UniverseDetail
            Universe details including the full list of symbols:
            - id: Unique identifier
            - name: Display name
            - region: Region code
            - category: Category
            - symbol_count: Number of symbols
            - symbols: List of symbol codes
            - description: Optional description

        Examples
        --------
        >>> universe = await client.universes.get("CN_Equity_A")
        >>> print(f"Found {len(universe['symbols'])} A-share symbols")
        """
        response = await self._client.get(f"/v1/universes/{universe_id}")
        return response["data"]

    async def batch(self, ids: List[str]) -> Dict[str, "UniverseDetail"]:
        """Batch get detailed information for multiple universes.

        Only valid universe IDs will be included in the response.

        Parameters
        ----------
        ids : list of str
            List of universe identifiers (e.g., ["CN_Equity_A", "CN_ETF"]).

        Returns
        -------
        dict of str to UniverseDetail
            Mapping from valid universe ID to its detail.

        Examples
        --------
        >>> details = await client.universes.batch(["CN_Equity_A", "CN_ETF"])
        >>> for uid, detail in details.items():
        ...     print(f"{uid}: {detail['symbol_count']} symbols")
        """
        response = await self._client.post("/v1/universes/batch", json={"ids": ids})
        return response["data"]
