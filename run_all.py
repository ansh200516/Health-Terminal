"""Run evaluation on all chart JSON files and build summary report."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from agents.orchestrator import ClinicalEvalOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full workshop evaluation.")
    parser.add_argument(
        "--input-dir",
        default="workshop_test_data",
        help="Directory containing chart subfolders with .json files",
    )
    parser.add_argument("--output-dir", default="output", help="Directory for output json reports")
    parser.add_argument("--summary-json", default="output/summary.json", help="Summary JSON path")
    return parser.parse_args()


def collect_json_files(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.glob("*/*.json") if p.is_file()])


def average(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


async def run(input_dir: Path, output_dir: Path, summary_path: Path) -> None:
    orchestrator = ClinicalEvalOrchestrator()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = collect_json_files(input_dir)
    summary_rows: List[Dict[str, Any]] = []

    for json_file in files:
        result = await orchestrator.evaluate_json(json_file)
        out_file = output_dir / json_file.name
        out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        summary_rows.append(result)

    summary: Dict[str, Any] = {"files_processed": len(summary_rows), "by_file": summary_rows}
    if summary_rows:
        summary["avg_event_date_accuracy"] = average([r["event_date_accuracy"] for r in summary_rows])
        summary["avg_attribute_completeness"] = average([r["attribute_completeness"] for r in summary_rows])
        summary["avg_entity_type_error_rate"] = _avg_bucket(summary_rows, "entity_type_error_rate")
        summary["avg_assertion_error_rate"] = _avg_bucket(summary_rows, "assertion_error_rate")
        summary["avg_temporality_error_rate"] = _avg_bucket(summary_rows, "temporality_error_rate")
        summary["avg_subject_error_rate"] = _avg_bucket(summary_rows, "subject_error_rate")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _avg_bucket(rows: List[Dict[str, Any]], key: str) -> Dict[str, float]:
    keys = sorted(rows[0][key].keys()) if rows else []
    out: Dict[str, float] = {}
    for k in keys:
        out[k] = average([float(r[key].get(k, 0.0)) for r in rows])
    return out


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            summary_path=Path(args.summary_json),
        )
    )
