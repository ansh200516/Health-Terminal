"""Metadata and date validation agent."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Set

from medical_knowledge.expected_attributes import DATE_RELATION_TYPES, EXPECTED_RELATIONS


class MetadataValidator:
    """Rule-guided validator for metadata relation quality and completeness."""

    @staticmethod
    def _relations(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        md = entity.get("metadata_from_qa", {}) or {}
        rels = md.get("relations", []) if isinstance(md, dict) else []
        return rels if isinstance(rels, list) else []

    @staticmethod
    def _is_iso_date(value: str) -> bool:
        try:
            dt.datetime.strptime(value, "%Y-%m-%d")
            return True
        except Exception:
            return False

    def validate_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        entity_results: List[Dict[str, Any]] = []
        date_total = 0
        date_correct = 0
        completeness_numerator = 0
        completeness_denominator = 0

        for entity in entities:
            e_type = entity.get("entity_type", "")
            relations = self._relations(entity)
            relation_types: Set[str] = {str(r.get("entity_type", "")).strip() for r in relations}
            expected_set = EXPECTED_RELATIONS.get(e_type, set())

            wrong_reasons: List[str] = []

            # Attribute completeness contribution.
            if expected_set:
                present = len(expected_set.intersection(relation_types))
                completeness_numerator += present
                completeness_denominator += len(expected_set)

            # Relation sanity checks.
            for rel in relations:
                rel_type = str(rel.get("entity_type", "")).strip()
                rel_value = str(rel.get("entity", "")).strip()
                if rel_type in DATE_RELATION_TYPES:
                    date_total += 1
                    if self._is_iso_date(rel_value):
                        date_correct += 1
                    else:
                        wrong_reasons.append(f"Invalid date relation value: {rel_value!r}")
                if rel_type in {"STRENGTH", "UNIT", "DOSE", "ROUTE", "FREQUENCY"} and e_type not in {"MEDICINE"}:
                    wrong_reasons.append(f"Medication-like relation {rel_type} on {e_type}")
                if rel_type in {"VITAL_NAME_VALUE", "VITAL_NAME_UNIT"} and e_type != "VITAL_NAME":
                    wrong_reasons.append(f"Vital relation {rel_type} on {e_type}")
                if rel_type in {"TEST_VALUE", "TEST_UNIT"} and e_type != "TEST":
                    wrong_reasons.append(f"Test relation {rel_type} on {e_type}")

            entity_results.append(
                {
                    "wrong": len(wrong_reasons) > 0,
                    "expected": "metadata_consistent",
                    "confidence": 0.8,
                    "rationale": "; ".join(wrong_reasons) if wrong_reasons else "Metadata is consistent.",
                }
            )

        event_date_accuracy = (date_correct / date_total) if date_total else 1.0
        attribute_completeness = (
            completeness_numerator / completeness_denominator if completeness_denominator else 1.0
        )

        return {
            "entity_results": entity_results,
            "event_date_accuracy": round(max(0.0, min(1.0, event_date_accuracy)), 4),
            "attribute_completeness": round(max(0.0, min(1.0, attribute_completeness)), 4),
        }
