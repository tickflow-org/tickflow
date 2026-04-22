"""TickFlow Python SDK - 高性能行情数据客户端。

支持 A股、ETF、美股、港股的行情数据查询，提供同步和异步两种接口。

Examples
--------
同步使用:

>>> from tickflow import TickFlow
>>> client = TickFlow(api_key="your-api-key")
>>> df = client.klines.get("600000.SH", as_dataframe=True)
>>> print(df.tail())

异步使用:

>>> import asyncio
>>> from tickflow import AsyncTickFlow
>>>
>>> async def main():
...     async with AsyncTickFlow(api_key="your-api-key") as client:
...         df = await client.klines.get("600000.SH", as_dataframe=True)
...         print(df.tail())
>>>
>>> asyncio.run(main())
"""

from .__version__ import __version__
from ._exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConnectionError,
    InternalServerError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    TickFlowError,
    TimeoutError,
)
from .client import AsyncTickFlow, TickFlow
from .generated_model import (
    CompactKlineData,
    Instrument,
    InstrumentType,
    Period,
    Quote,
    Region,
    SessionStatus,
)
from .resources.realtime import AsyncQuoteStream, QuoteStream
from .resources.stream import AsyncMarketStream, MarketStream

__all__ = [
    "__version__",
    # Main clients
    "TickFlow",
    "AsyncTickFlow",
    # Exceptions
    "TickFlowError",
    "APIError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "BadRequestError",
    "RateLimitError",
    "InternalServerError",
    "ConnectionError",
    "TimeoutError",
    # Types
    "CompactKlineData",
    "Instrument",
    "InstrumentType",
    "Period",
    "Quote",
    "Region",
    "SessionStatus",
    # Unified streaming (recommended)
    "MarketStream",
    "AsyncMarketStream",
    # Legacy streaming (deprecated, use MarketStream / AsyncMarketStream)
    "QuoteStream",
    "AsyncQuoteStream",
]
