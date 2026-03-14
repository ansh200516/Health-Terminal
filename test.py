"""Entry point: evaluate one chart JSON and write output JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from agents.orchestrator import ClinicalEvalOrchestrator


async def run(input_json: str, output_json: str) -> None:
    orchestrator = ClinicalEvalOrchestrator()
    result = await orchestrator.evaluate_json(input_json)

    out_path = Path(output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clinical AI evaluation entry point")
    parser.add_argument("input_json", help="Path to input chart JSON")
    parser.add_argument("output_json", help="Path to output evaluation JSON")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.input_json, args.output_json))
