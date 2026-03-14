"""Subject attribution validator."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.base_agent import BaseLLMAgent, normalize_text


SYSTEM_PROMPT = """
You are a clinical subject attribution evaluator.
Infer expected subject label for each entity: PATIENT or FAMILY_MEMBER.
Return JSON: {"predictions":[{"expected_subject":"PATIENT","confidence":0.0-1.0,"rationale":"..."}]}
""".strip()

FAMILY_CUES = [
    "family history",
    "mother",
    "father",
    "sister",
    "brother",
    "grandmother",
    "grandfather",
]


class SubjectValidator(BaseLLMAgent):
    def __init__(self) -> None:
        super().__init__(name="subject_validator", system_prompt=SYSTEM_PROMPT)

    def _heuristic_subject(self, entity: Dict[str, Any]) -> str:
        text = normalize_text(entity.get("text", ""))
        heading = normalize_text(entity.get("heading", ""))
        merged = f"{heading} {text}"
        if any(cue in merged for cue in FAMILY_CUES):
            return "FAMILY_MEMBER"
        return "PATIENT"

    async def validate_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact = [
            {
                "idx": i,
                "entity": e.get("entity", ""),
                "subject": e.get("subject", ""),
                "heading": e.get("heading", ""),
                "text": (e.get("text", "") or "")[:400],
            }
            for i, e in enumerate(entities)
        ]
        fallback = {
            "predictions": [
                {
                    "expected_subject": self._heuristic_subject(e),
                    "confidence": 0.75,
                    "rationale": "Heuristic subject attribution.",
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
            expected = pred.get("expected_subject", self._heuristic_subject(entity))
            if expected not in {"PATIENT", "FAMILY_MEMBER"}:
                expected = self._heuristic_subject(entity)
            labeled = (entity.get("subject", "") or "PATIENT").strip() or "PATIENT"
            results.append(
                {
                    "wrong": labeled != expected,
                    "expected": expected,
                    "confidence": float(pred.get("confidence", 0.6)),
                    "rationale": pred.get("rationale", "No rationale provided."),
                }
            )
        return results
