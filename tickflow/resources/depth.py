"""Market depth (order book) resources for TickFlow API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from ._base import AsyncResource, SyncResource

if TYPE_CHECKING:
    from ..generated_model import MarketDepth


class Depth(SyncResource):
    """Synchronous interface for market depth endpoint.

    Examples
    --------
    >>> client = TickFlow(api_key="your-key")
    >>> depth = client.depth.get("600000.SH")
    >>> print(depth["bid_prices"], depth["ask_prices"])
    """

    def get(self, symbol: str) -> "MarketDepth":
        """Get 5-level market depth for a single symbol.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g. "600000.SH").

        Returns
        -------
        MarketDepth
            Market depth data with bid/ask prices and volumes.

        Examples
        --------
        >>> depth = client.depth.get("600000.SH")
        >>> for i in range(5):
        ...     print(f"Bid {i+1}: {depth['bid_prices'][i]} x {depth['bid_volumes'][i]}")
        ...     print(f"Ask {i+1}: {depth['ask_prices'][i]} x {depth['ask_volumes'][i]}")
        """
        response = self._client.get("/v1/depth", params={"symbol": symbol})
        return response["data"]


class AsyncDepth(AsyncResource):
    """Asynchronous interface for market depth endpoint.

    Examples
    --------
    >>> async with AsyncTickFlow(api_key="your-key") as client:
    ...     depth = await client.depth.get("600000.SH")
    """

    async def get(self, symbol: str) -> "MarketDepth":
        """Get 5-level market depth for a single symbol.

        Parameters
        ----------
        symbol : str
            Symbol code (e.g. "600000.SH").

        Returns
        -------
        MarketDepth
            Market depth data with bid/ask prices and volumes.
        """
        response = await self._client.get("/v1/depth", params={"symbol": symbol})
        return response["data"]
