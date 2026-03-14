"""Assertion validator using NegEx-style cue logic."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.base_agent import BaseLLMAgent, normalize_text
from medical_knowledge.negation_cues import (
    POST_NEGATION_TRIGGERS,
    PRE_NEGATION_TRIGGERS,
    PSEUDO_NEGATION_TRIGGERS,
    UNCERTAINTY_TRIGGERS,
)


SYSTEM_PROMPT = """
You are a clinical assertion evaluator.
Infer expected assertion label for each entity: POSITIVE, NEGATIVE, or UNCERTAIN.
Use linguistic negation and uncertainty cues from context.
Return JSON: {"predictions":[{"expected_assertion":"POSITIVE","confidence":0.0-1.0,"rationale":"..."}]}
""".strip()


class AssertionValidator(BaseLLMAgent):
    def __init__(self) -> None:
        super().__init__(name="assertion_validator", system_prompt=SYSTEM_PROMPT)

    def _heuristic_assertion(self, entity: Dict[str, Any]) -> str:
        text = normalize_text(entity.get("text", ""))
        if any(p in text for p in PSEUDO_NEGATION_TRIGGERS):
            # Do not over-trigger on pseudo-negation.
            pass
        if any(t in text for t in UNCERTAINTY_TRIGGERS):
            return "UNCERTAIN"
        if any(t in text for t in PRE_NEGATION_TRIGGERS) or any(t in text for t in POST_NEGATION_TRIGGERS):
            return "NEGATIVE"
        return "POSITIVE"

    async def validate_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact = [
            {
                "idx": i,
                "entity": e.get("entity", ""),
                "assertion": e.get("assertion", ""),
                "text": (e.get("text", "") or "")[:500],
            }
            for i, e in enumerate(entities)
        ]
        fallback = {
            "predictions": [
                {
                    "expected_assertion": self._heuristic_assertion(e),
                    "confidence": 0.7,
                    "rationale": "Heuristic NegEx cue matching.",
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
            expected = pred.get("expected_assertion", self._heuristic_assertion(entity))
            if expected not in {"POSITIVE", "NEGATIVE", "UNCERTAIN"}:
                expected = self._heuristic_assertion(entity)
            labeled = (entity.get("assertion", "") or "POSITIVE").strip() or "POSITIVE"
            results.append(
                {
                    "wrong": labeled != expected,
                    "expected": expected,
                    "confidence": float(pred.get("confidence", 0.6)),
                    "rationale": pred.get("rationale", "No rationale provided."),
                }
            )
        return results
