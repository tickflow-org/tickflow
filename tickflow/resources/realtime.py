"""WebSocket-based real-time quote streaming for TickFlow API."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient

logger = logging.getLogger("tickflow.realtime")


def _build_ws_url(base_url: str, api_key: str) -> str:
    base = base_url.rstrip("/")
    scheme = "wss" if base.startswith("https") else "ws"
    stripped = base.replace("https://", "").replace("http://", "")
    return f"{scheme}://{stripped}/v1/ws/quotes?api_key={api_key}"


_NO_RETRY_STATUS_CODES = {401, 403, 404}


def _get_status_code(exc: Exception) -> Optional[int]:
    """Extract HTTP status code from a websockets rejection exception."""
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def _extract_rejection_reason(exc: Exception) -> str:
    """Extract a human-readable reason from a websockets rejection error."""
    try:
        resp = getattr(exc, "response", None)
        if resp is not None:
            body = getattr(resp, "body", None)
            if body:
                text = (
                    body.decode("utf-8", errors="replace")
                    if isinstance(body, bytes)
                    else str(body)
                )
                import json

                try:
                    data = json.loads(text)
                    msg = data.get("message") or data.get("error") or text
                    code = data.get("code", "")
                    return f"{code}: {msg}" if code else str(msg)
                except (json.JSONDecodeError, TypeError):
                    return text.strip()[:200]
    except Exception:
        pass
    return str(exc)


class QuoteStream:
    """Synchronous real-time quote stream over WebSocket.

    Runs the async event loop in a background thread and dispatches
    quote callbacks on that thread. Use `on_quotes` to register a handler.

    Parameters
    ----------
    client : SyncAPIClient
        The underlying HTTP client (used for base_url and api_key).

    Examples
    --------
    >>> from tickflow import TickFlow
    >>> client = TickFlow(api_key="your-key")
    >>> stream = client.realtime
    >>>
    >>> @stream.on_quotes
    ... def handle(quotes):
    ...     for q in quotes:
    ...         print(f"{q['symbol']}: {q['last_price']}")
    >>>
    >>> stream.subscribe(["600000.SH", "000001.SZ"])
    >>> stream.connect()  # blocks until close() or KeyboardInterrupt
    """

    def __init__(self, client: "SyncAPIClient") -> None:
        self._base_url = client.base_url
        self._api_key = client.api_key or ""
        self._handler: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self._error_handler: Optional[Callable[[str], None]] = None
        self._symbols: Set[str] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._inner: Optional[AsyncQuoteStream] = None

    def on_quotes(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        """Register a callback for incoming quote batches. Can be used as decorator."""
        self._handler = fn
        return fn

    def on_error(self, fn: Callable[[str], None]) -> Callable:
        """Register a callback for server error messages. Can be used as decorator."""
        self._error_handler = fn
        return fn

    def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to symbols. Can be called before or after connect()."""
        self._symbols.update(symbols)
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._inner.subscribe(symbols), self._loop)

    def unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols."""
        self._symbols -= set(symbols)
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._inner.unsubscribe(symbols), self._loop
            )

    def connect(self, *, block: bool = True) -> None:
        """Start the WebSocket connection.

        Parameters
        ----------
        block : bool
            If True (default), blocks the calling thread until the stream
            is closed or interrupted. If False, runs in a background thread.
        """
        if block:
            try:
                asyncio.run(self._run())
            except KeyboardInterrupt:
                logger.info("Interrupted, closing stream")
        else:
            self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
            self._thread.start()

    def close(self) -> None:
        """Stop the stream and clean up."""
        self._stop.set()
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._inner.close(), self._loop)

    def _run_in_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._inner = AsyncQuoteStream.__new__(AsyncQuoteStream)
        self._inner._ws_url = _build_ws_url(self._base_url, self._api_key)
        self._inner._handler = self._handler
        self._inner._error_handler = self._error_handler
        self._inner._symbols = set(self._symbols)
        self._inner._ws = None
        self._inner._closed = False
        await self._inner._connect_and_run()


class AsyncQuoteStream:
    """Async real-time quote stream over WebSocket.

    Parameters
    ----------
    client : AsyncAPIClient
        The underlying async HTTP client (used for base_url and api_key).

    Examples
    --------
    >>> import asyncio
    >>> from tickflow import AsyncTickFlow
    >>>
    >>> async def main():
    ...     async with AsyncTickFlow(api_key="your-key") as client:
    ...         stream = client.realtime
    ...
    ...         @stream.on_quotes
    ...         def handle(quotes):
    ...             for q in quotes:
    ...                 print(f"{q['symbol']}: {q['last_price']}")
    ...
    ...         await stream.subscribe(["600000.SH", "000001.SZ"])
    ...         await stream.connect()
    >>>
    >>> asyncio.run(main())
    """

    def __init__(self, client: "AsyncAPIClient") -> None:
        self._ws_url = _build_ws_url(client.base_url, client.api_key or "")
        self._handler: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self._error_handler: Optional[Callable[[str], None]] = None
        self._symbols: Set[str] = set()
        self._ws: Any = None
        self._closed = False

    def on_quotes(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        """Register a callback for incoming quote batches. Can be used as decorator."""
        self._handler = fn
        return fn

    def on_error(self, fn: Callable[[str], None]) -> Callable:
        """Register a callback for server error messages. Can be used as decorator."""
        self._error_handler = fn
        return fn

    async def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to symbols."""
        self._symbols.update(symbols)
        if self._ws:
            await self._send_op("subscribe", list(symbols))

    async def unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols."""
        self._symbols -= set(symbols)
        if self._ws:
            await self._send_op("unsubscribe", list(symbols))

    async def connect(self) -> None:
        """Start the WebSocket connection. Blocks until closed."""
        await self._connect_and_run()

    async def close(self) -> None:
        """Close the stream."""
        self._closed = True
        if self._ws:
            await self._ws.close()

    async def _send_op(self, op: str, symbols: List[str]) -> None:
        import json

        await self._ws.send(json.dumps({"op": op, "symbols": symbols}))

    async def _connect_and_run(self) -> None:
        import json

        import websockets

        while not self._closed:
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=16 * 1024 * 1024,
                    compression="deflate",
                ) as ws:
                    self._ws = ws
                    logger.info("Connected to %s", self._ws_url.split("?")[0])

                    # Re-subscribe all symbols on (re)connect
                    if self._symbols:
                        await self._send_op("subscribe", list(self._symbols))

                    async for raw in ws:
                        msg = json.loads(raw)

                        op = msg.get("op")
                        if op == "quotes" and self._handler:
                            self._handler(msg.get("data", []))
                        elif op == "subscribed":
                            logger.info("Subscribed: %d symbols", msg.get("total", 0))
                        elif op == "error":
                            err_msg = msg.get("message", "unknown error")
                            logger.warning("Server error: %s", err_msg)
                            if self._error_handler:
                                self._error_handler(err_msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._closed:
                    break
                reason = _extract_rejection_reason(e)
                status = _get_status_code(e)
                if status in _NO_RETRY_STATUS_CODES:
                    logger.error("WS connection rejected (HTTP %d): %s", status, reason)
                    if self._error_handler:
                        self._error_handler(reason)
                    break
                logger.warning("WS error: %s — reconnecting in 3s", reason)
                await asyncio.sleep(3)
            finally:
                self._ws = None

        logger.info("Quote stream closed")
