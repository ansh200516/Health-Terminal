"""Batch helper for chunking entity lists."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List


def batched_entities(entities: List[Dict[str, Any]], batch_size: int) -> Iterator[List[Dict[str, Any]]]:
    size = max(1, batch_size)
    for i in range(0, len(entities), size):
        yield entities[i : i + size]
