"""Generic batched GET utilities for splitting large symbol lists across requests.

Handles URL length limits by automatically chunking the symbol list and
merging ``response["data"]`` dicts from each chunk.  Both synchronous
(ThreadPoolExecutor) and asynchronous (asyncio.Semaphore) variants are
provided so that any resource can reuse the same logic.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ._base_client import AsyncAPIClient, SyncAPIClient

DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_WORKERS = 5


def _chunk_list(lst: List[str], chunk_size: int) -> List[List[str]]:
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def _get_progress_bar(total: int, desc: str, show: bool):
    if show:
        try:
            from tqdm.auto import tqdm

            return tqdm(total=total, desc=desc, leave=False)
        except ImportError:
            pass
    return None


def batched_get_sync(
    client: "SyncAPIClient",
    endpoint: str,
    symbols: List[str],
    params: Dict[str, Any],
    *,
    symbols_param: str = "symbols",
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_workers: int = DEFAULT_MAX_WORKERS,
    show_progress: bool = False,
    progress_desc: str = "Fetching data",
    merge: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Fetch *endpoint* in chunks, merging ``response["data"]`` dicts.

    Parameters
    ----------
    merge : callable, optional
        ``merge(accumulated, chunk_data)`` – custom merge strategy.
        Defaults to ``accumulated.update(chunk_data)``.
    """
    if not symbols:
        return {}

    chunks = _chunk_list(symbols, batch_size)
    _merge = merge or _default_merge

    if len(chunks) == 1:
        chunk_params = {**params, symbols_param: ",".join(chunks[0])}
        return client.get(endpoint, params=chunk_params)["data"]

    pbar = _get_progress_bar(len(chunks), progress_desc, show_progress)
    all_data: Dict[str, Any] = {}

    def _fetch(chunk: List[str]) -> Dict[str, Any]:
        chunk_params = {**params, symbols_param: ",".join(chunk)}
        return client.get(endpoint, params=chunk_params)["data"]

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch, c): c for c in chunks}
            for future in concurrent.futures.as_completed(futures):
                _merge(all_data, future.result())
                if pbar:
                    pbar.update(1)
    finally:
        if pbar:
            pbar.close()

    return all_data


async def batched_get_async(
    client: "AsyncAPIClient",
    endpoint: str,
    symbols: List[str],
    params: Dict[str, Any],
    *,
    symbols_param: str = "symbols",
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_concurrency: int = DEFAULT_MAX_WORKERS,
    show_progress: bool = False,
    progress_desc: str = "Fetching data",
    merge: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Async variant of :func:`batched_get_sync`."""
    if not symbols:
        return {}

    chunks = _chunk_list(symbols, batch_size)
    _merge = merge or _default_merge

    if len(chunks) == 1:
        chunk_params = {**params, symbols_param: ",".join(chunks[0])}
        return (await client.get(endpoint, params=chunk_params))["data"]

    pbar = _get_progress_bar(len(chunks), progress_desc, show_progress)
    sem = asyncio.Semaphore(max_concurrency)
    all_data: Dict[str, Any] = {}

    async def _fetch(chunk: List[str]) -> Dict[str, Any]:
        async with sem:
            chunk_params = {**params, symbols_param: ",".join(chunk)}
            resp = await client.get(endpoint, params=chunk_params)
            if pbar:
                pbar.update(1)
            return resp["data"]

    try:
        results = await asyncio.gather(
            *[_fetch(c) for c in chunks], return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                raise r
            _merge(all_data, r)
    finally:
        if pbar:
            pbar.close()

    return all_data


def _default_merge(acc: Dict[str, Any], chunk: Dict[str, Any]) -> None:
    acc.update(chunk)
