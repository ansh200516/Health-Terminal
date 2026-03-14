"""Entity type validator agent."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from agents.base_agent import BaseLLMAgent, normalize_text
from medical_knowledge.entity_taxonomy import ENTITY_TYPES, PROMPT_TAXONOMY_GUIDE, TAXONOMY_HINTS


SYSTEM_PROMPT = f"""
You are a clinical NLP evaluator for entity type validation.
{PROMPT_TAXONOMY_GUIDE}
Given entities with text context and headings, infer the medically correct entity_type.
Return JSON object with key "predictions", a list matching input order:
{{"predictions":[{{"expected_type":"PROBLEM","confidence":0.0-1.0,"rationale":"..."}}]}}
""".strip()


class EntityTypeValidator(BaseLLMAgent):
    def __init__(self) -> None:
        super().__init__(name="entity_type_validator", system_prompt=SYSTEM_PROMPT)

    def _heuristic_type(self, entity: Dict[str, Any]) -> str:
        text = " ".join(
            [
                normalize_text(entity.get("entity", "")),
                normalize_text(entity.get("text", "")),
                normalize_text(entity.get("heading", "")),
            ]
        )
        best_type = entity.get("entity_type", "PROBLEM")
        best_score = -1

        for entity_type, hints in TAXONOMY_HINTS.items():
            score = sum(1 for hint in hints if hint in text)
            if score > best_score:
                best_type = entity_type
                best_score = score
        return best_type if best_type in ENTITY_TYPES else "PROBLEM"

    async def _llm_predictions(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]] | None:
        compact = []
        for idx, e in enumerate(entities):
            compact.append(
                {
                    "idx": idx,
                    "entity": e.get("entity", ""),
                    "entity_type": e.get("entity_type", ""),
                    "heading": e.get("heading", ""),
                    "text": (e.get("text", "") or "")[:500],
                }
            )
        fallback = {
            "predictions": [
                {
                    "expected_type": self._heuristic_type(entity),
                    "confidence": 0.65,
                    "rationale": "Heuristic fallback using taxonomy hints.",
                }
                for entity in entities
            ]
        }
        prompt = "Entities:\n" + json.dumps(compact, ensure_ascii=True)
        data = await self.call_llm_json(prompt, fallback=fallback)
        predictions = data.get("predictions")
        if not isinstance(predictions, list) or len(predictions) != len(entities):
            return fallback["predictions"]
        return predictions

    async def validate_batch(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        predictions = await self._llm_predictions(entities)
        results: List[Dict[str, Any]] = []
        for entity, prediction in zip(entities, predictions):
            labeled = entity.get("entity_type", "")
            expected = prediction.get("expected_type", labeled)
            if expected not in ENTITY_TYPES:
                expected = self._heuristic_type(entity)

            # Optional web search for unusual tokens with low confidence.
            confidence = float(prediction.get("confidence", 0.6))
            if confidence < 0.45 and re.search(r"[a-z]{4,}", normalize_text(entity.get("entity", ""))):
                evidence = await self.web_search(f"medical term classification: {entity.get('entity', '')}")
                if evidence:
                    confidence = min(0.55, confidence + 0.1)

            results.append(
                {
                    "wrong": labeled != expected,
                    "expected": expected,
                    "confidence": round(confidence, 3),
                    "rationale": prediction.get("rationale", "No rationale provided."),
                }
            )
        return results
