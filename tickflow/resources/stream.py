"""Unified WebSocket stream with per-channel subscriptions (`/v1/ws/stream`).

Supported channels: ``quotes``, ``depth``.

Usage::

    stream = tf.stream

    @stream.on_quotes
    def handle(quotes):
        for q in quotes:
            print(q["symbol"], q["last_price"])

    @stream.on_depth
    def handle_depth(depths):
        for d in depths:
            print(d["symbol"], d["bid_prices"][0])

    stream.subscribe("quotes", ["600000.SH"])
    stream.subscribe("depth", ["600000.SH"])
    stream.connect()
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Set

from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from .._base_client import AsyncAPIClient, SyncAPIClient

logger = logging.getLogger("tickflow.stream")

_NO_RETRY_STATUS_CODES = {401, 403, 404}

Channel: TypeAlias = Literal["quotes", "depth"]


def _build_ws_url(base_url: str, api_key: str) -> str:
    base = base_url.rstrip("/")
    scheme = "wss" if base.startswith("https") else "ws"
    stripped = base.replace("https://", "").replace("http://", "")
    return f"{scheme}://{stripped}/v1/ws/stream?api_key={api_key}"


def _get_status_code(exc: Exception) -> Optional[int]:
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def _extract_rejection_reason(exc: Exception) -> str:
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


# ============================================================================
# Synchronous wrapper
# ============================================================================


class MarketStream:
    """Synchronous unified stream over WebSocket.

    Runs the async loop in a background thread.

    Parameters
    ----------
    client : SyncAPIClient
        The underlying HTTP client (used for base_url and api_key).
    """

    def __init__(self, client: "SyncAPIClient") -> None:
        self._base_url = client.base_url
        self._api_key = client.api_key or ""
        self._handlers: Dict[str, Callable[[List[Dict[str, Any]]], None]] = {}
        self._error_handler: Optional[Callable[[str], None]] = None
        # channel -> symbols (pending subscriptions before connect)
        self._pending_subs: Dict[str, Set[str]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._inner: Optional[AsyncMarketStream] = None

    # -- callbacks --

    def on_quotes(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        """Register a handler for ``quotes`` channel. Usable as decorator."""
        self._handlers["quotes"] = fn
        return fn

    def on_depth(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        """Register a handler for ``depth`` channel. Usable as decorator."""
        self._handlers["depth"] = fn
        return fn

    def on_error(self, fn: Callable[[str], None]) -> Callable:
        """Register an error handler. Usable as decorator."""
        self._error_handler = fn
        return fn

    # -- subscription --

    def subscribe(self, channel: Channel, symbols: List[str]) -> None:
        """Subscribe to *channel* for *symbols*. Safe before or after connect()."""
        self._pending_subs.setdefault(channel, set()).update(symbols)
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._inner.subscribe(channel, symbols), self._loop
            )

    def unsubscribe(self, channel: Channel, symbols: List[str]) -> None:
        """Unsubscribe *symbols* from *channel*."""
        if channel in self._pending_subs:
            self._pending_subs[channel] -= set(symbols)
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._inner.unsubscribe(channel, symbols), self._loop
            )

    # -- lifecycle --

    def connect(self, *, block: bool = True) -> None:
        """Start the WebSocket connection.

        Parameters
        ----------
        block : bool
            If True (default), blocks until close() or KeyboardInterrupt.
            If False, runs in a daemon thread.
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
        self._stop.set()
        if self._inner and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._inner.close(), self._loop)

    def _run_in_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        self._loop = asyncio.get_event_loop()
        inner = AsyncMarketStream.__new__(AsyncMarketStream)
        inner._ws_url = _build_ws_url(self._base_url, self._api_key)
        inner._handlers = dict(self._handlers)
        inner._error_handler = self._error_handler
        inner._subs = {ch: set(s) for ch, s in self._pending_subs.items()}
        inner._ws = None
        inner._closed = False
        self._inner = inner
        await inner._connect_and_run()


# ============================================================================
# Async implementation
# ============================================================================


class AsyncMarketStream:
    """Async unified stream over WebSocket.

    Parameters
    ----------
    client : AsyncAPIClient
        The underlying async HTTP client.
    """

    def __init__(self, client: "AsyncAPIClient") -> None:
        self._ws_url = _build_ws_url(client.base_url, client.api_key or "")
        self._handlers: Dict[str, Callable[[List[Dict[str, Any]]], None]] = {}
        self._error_handler: Optional[Callable[[str], None]] = None
        self._subs: Dict[str, Set[str]] = {}
        self._ws: Any = None
        self._closed = False

    # -- callbacks --

    def on_quotes(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        self._handlers["quotes"] = fn
        return fn

    def on_depth(self, fn: Callable[[List[Dict[str, Any]]], None]) -> Callable:
        self._handlers["depth"] = fn
        return fn

    def on_error(self, fn: Callable[[str], None]) -> Callable:
        self._error_handler = fn
        return fn

    # -- subscription --

    async def subscribe(self, channel: Channel, symbols: List[str]) -> None:
        """Subscribe to *channel* for *symbols*."""
        self._subs.setdefault(channel, set()).update(symbols)
        if self._ws:
            await self._send(
                {"op": "subscribe", "channel": channel, "symbols": symbols}
            )

    async def unsubscribe(self, channel: Channel, symbols: List[str]) -> None:
        """Unsubscribe *symbols* from *channel*."""
        if channel in self._subs:
            self._subs[channel] -= set(symbols)
        if self._ws:
            await self._send(
                {"op": "unsubscribe", "channel": channel, "symbols": symbols}
            )

    # -- lifecycle --

    async def connect(self) -> None:
        """Start the WebSocket connection. Blocks until closed."""
        await self._connect_and_run()

    async def close(self) -> None:
        self._closed = True
        if self._ws:
            await self._ws.close()

    # -- internals --

    async def _send(self, payload: dict) -> None:
        import json

        await self._ws.send(json.dumps(payload))

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

                    # Re-subscribe all channels on (re)connect
                    for ch, syms in self._subs.items():
                        if syms:
                            await self._send(
                                {
                                    "op": "subscribe",
                                    "channel": ch,
                                    "symbols": list(syms),
                                }
                            )

                    async for raw in ws:
                        msg = json.loads(raw)
                        op = msg.get("op")

                        if op in ("quotes", "depth"):
                            handler = self._handlers.get(op)
                            if handler:
                                handler(msg.get("data", []))
                        elif op == "subscribed":
                            logger.info(
                                "Subscribed [%s]: %d symbols",
                                msg.get("channel", "?"),
                                msg.get("total", 0),
                            )
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

        logger.info("Market stream closed")
