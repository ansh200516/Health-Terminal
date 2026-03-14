"""Load chart-level JSON and optional markdown context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_entities(json_path: str | Path) -> List[Dict[str, Any]]:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list of entities in {path}")
    return data


def infer_md_path(json_path: str | Path) -> Path:
    path = Path(json_path)
    return path.with_suffix(".md")


def load_chart(json_path: str | Path) -> Tuple[List[Dict[str, Any]], str]:
    entities = load_entities(json_path)
    md_path = infer_md_path(json_path)
    markdown = ""
    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8", errors="ignore")
    return entities, markdown
