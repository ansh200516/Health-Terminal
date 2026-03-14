"""Temporality validator using cue-based temporal reasoning."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.base_agent import BaseLLMAgent, normalize_text
from medical_knowledge.temporal_cues import CURRENT_CUES, HEADING_PRIORS, HISTORY_CUES, UPCOMING_CUES


SYSTEM_PROMPT = """
You are a clinical temporality evaluator.
Infer expected temporality label for each entity:
CURRENT, CLINICAL_HISTORY, UPCOMING, or UNCERTAIN.
Use heading and text cues.
Return JSON: {"predictions":[{"expected_temporality":"CURRENT","confidence":0.0-1.0,"rationale":"..."}]}
""".strip()


class TemporalityValidator(BaseLLMAgent):
    def __init__(self) -> None:
        super().__init__(name="temporality_validator", system_prompt=SYSTEM_PROMPT)

    def _heuristic_temporality(self, entity: Dict[str, Any]) -> str:
        heading = normalize_text(entity.get("heading", ""))
        text = normalize_text(entity.get("text", ""))

        for cue, label in HEADING_PRIORS.items():
            if cue in heading:
                return label
        if any(t in text for t in UPCOMING_CUES):
            return "UPCOMING"
        if any(t in text for t in HISTORY_CUES):
            return "CLINICAL_HISTORY"
        if any(t in text for t in CURRENT_CUES):
            return "CURRENT"
        return "UNCERTAIN"

    async def validate_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact = [
            {
                "idx": i,
                "entity": e.get("entity", ""),
                "temporality": e.get("temporality", ""),
                "heading": e.get("heading", ""),
                "text": (e.get("text", "") or "")[:500],
            }
            for i, e in enumerate(entities)
        ]
        fallback = {
            "predictions": [
                {
                    "expected_temporality": self._heuristic_temporality(e),
                    "confidence": 0.7,
                    "rationale": "Heuristic temporal cue matching.",
                }
                for e in entities
            ]
        }
        data = await self.call_llm_json("Entities:\n" + json.dumps(compact, ensure_ascii=True), fallback=fallback)
        predictions = data.get("predictions", fallback["predictions"])
        if not isinstance(predictions, list) or len(predictions) != len(entities):
            predictions = fallback["predictions"]

        results: List[Dict[str, Any]] = []
        for entity, pred in zip(entities, predictions):
            expected = pred.get("expected_temporality", self._heuristic_temporality(entity))
            if expected not in {"CURRENT", "CLINICAL_HISTORY", "UPCOMING", "UNCERTAIN"}:
                expected = self._heuristic_temporality(entity)
            labeled = (entity.get("temporality", "") or "UNCERTAIN").strip() or "UNCERTAIN"
            results.append(
                {
                    "wrong": labeled != expected,
                    "expected": expected,
                    "confidence": float(pred.get("confidence", 0.6)),
                    "rationale": pred.get("rationale", "No rationale provided."),
                }
            )
        return results
