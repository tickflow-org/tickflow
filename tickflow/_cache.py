"""Local instrument name cache for TickFlow.

Caches symbol -> name mappings to avoid frequent API calls.
Cache directory is configurable via TICKFLOW_CACHE_DIR environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from ._base_client import AsyncAPIClient, SyncAPIClient

logger = logging.getLogger("tickflow.cache")

DEFAULT_CACHE_DIR = os.path.join(Path.home(), ".tickflow", "cache")
CACHE_FILENAME = "instruments.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
MAX_BATCH_SIZE = 500


def _get_cache_dir() -> str:
    return os.environ.get("TICKFLOW_CACHE_DIR", DEFAULT_CACHE_DIR)


class InstrumentNameCache:
    """Thread-safe local cache for instrument names.

    Backed by an in-memory dict and a JSON file on disk.
    Resolves missing names from the instruments API on demand.
    """

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self._cache_dir = cache_dir or _get_cache_dir()
        self._names: Dict[str, str] = {}
        self._updated_at: float = 0.0
        self._lock = threading.Lock()
        self._load_from_disk()

    @property
    def _cache_path(self) -> str:
        return os.path.join(self._cache_dir, CACHE_FILENAME)

    # ---- public API ----

    def get_name(self, symbol: str) -> Optional[str]:
        with self._lock:
            return self._names.get(symbol)

    def get_names(self, symbols: List[str]) -> Dict[str, str]:
        with self._lock:
            return {s: self._names[s] for s in symbols if s in self._names}

    def missing(self, symbols: List[str]) -> List[str]:
        with self._lock:
            return [s for s in symbols if s not in self._names]

    def update(self, names: Dict[str, str]) -> None:
        if not names:
            return
        with self._lock:
            self._names.update(names)
            self._updated_at = time.time()
        self._save_to_disk()

    def resolve_sync(
        self, symbols: List[str], client: "SyncAPIClient"
    ) -> Dict[str, str]:
        """Resolve names for symbols, fetching missing ones via sync client."""
        missing = self.missing(symbols)
        if missing:
            self._fetch_sync(missing, client)
        return self.get_names(symbols)

    async def resolve_async(
        self, symbols: List[str], client: "AsyncAPIClient"
    ) -> Dict[str, str]:
        """Resolve names for symbols, fetching missing ones via async client."""
        missing = self.missing(symbols)
        if missing:
            await self._fetch_async(missing, client)
        return self.get_names(symbols)

    # ---- internal: fetch from API ----

    def _fetch_sync(self, symbols: List[str], client: "SyncAPIClient") -> None:
        try:
            for i in range(0, len(symbols), MAX_BATCH_SIZE):
                chunk = symbols[i : i + MAX_BATCH_SIZE]
                response = client.post("/v1/instruments", json={"symbols": chunk})
                names = {
                    inst["symbol"]: inst["name"]
                    for inst in response.get("data", [])
                    if inst.get("name")
                }
                self.update(names)
        except Exception as e:
            logger.debug("Failed to fetch instrument names: %s", e)

    async def _fetch_async(self, symbols: List[str], client: "AsyncAPIClient") -> None:
        try:
            for i in range(0, len(symbols), MAX_BATCH_SIZE):
                chunk = symbols[i : i + MAX_BATCH_SIZE]
                response = await client.post("/v1/instruments", json={"symbols": chunk})
                names = {
                    inst["symbol"]: inst["name"]
                    for inst in response.get("data", [])
                    if inst.get("name")
                }
                self.update(names)
        except Exception as e:
            logger.debug("Failed to fetch instrument names: %s", e)

    # ---- disk persistence ----

    def _load_from_disk(self) -> None:
        path = self._cache_path
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            meta = data.get("_meta", {})
            saved_at = meta.get("updated_at", 0)

            if time.time() - saved_at > CACHE_TTL_SECONDS:
                logger.debug("Cache expired, ignoring disk cache")
                return

            names = data.get("data", {})
            if isinstance(names, dict):
                with self._lock:
                    self._names.update(names)
                    self._updated_at = saved_at
                logger.debug("Loaded %d instrument names from cache", len(names))
        except Exception as e:
            logger.debug("Failed to load cache from %s: %s", path, e)

    def _save_to_disk(self) -> None:
        path = self._cache_path
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with self._lock:
                payload = {
                    "_meta": {"updated_at": self._updated_at, "version": 1},
                    "data": dict(self._names),
                }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed to save cache to %s: %s", path, e)
