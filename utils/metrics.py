"""Metric computation helpers for output schema."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

ENTITY_TYPES = [
    "MEDICINE",
    "PROBLEM",
    "PROCEDURE",
    "TEST",
    "VITAL_NAME",
    "IMMUNIZATION",
    "MEDICAL_DEVICE",
    "MENTAL_STATUS",
    "SDOH",
    "SOCIAL_HISTORY",
]
ASSERTIONS = ["POSITIVE", "NEGATIVE", "UNCERTAIN"]
TEMPORALITIES = ["CURRENT", "CLINICAL_HISTORY", "UPCOMING", "UNCERTAIN"]
SUBJECTS = ["PATIENT", "FAMILY_MEMBER"]


def safe_rate(num: int, den: int) -> float:
    return round((num / den), 4) if den else 0.0


def _bucket_error_rate(
    entities: List[Dict[str, Any]],
    per_entity_results: List[Dict[str, Any]],
    field_name: str,
    keys: Iterable[str],
) -> Dict[str, float]:
    rates: Dict[str, float] = {}
    for key in keys:
        idxs = [i for i, e in enumerate(entities) if (e.get(field_name, "") or "").strip() == key]
        wrong = sum(1 for i in idxs if per_entity_results[i].get("wrong"))
        rates[key] = safe_rate(wrong, len(idxs))
    return rates


def build_output_payload(
    file_name: str,
    entities: List[Dict[str, Any]],
    entity_type_results: List[Dict[str, Any]],
    assertion_results: List[Dict[str, Any]],
    temporality_results: List[Dict[str, Any]],
    subject_results: List[Dict[str, Any]],
    event_date_accuracy: float,
    attribute_completeness: float,
) -> Dict[str, Any]:
    return {
        "file_name": file_name,
        "entity_type_error_rate": _bucket_error_rate(entities, entity_type_results, "entity_type", ENTITY_TYPES),
        "assertion_error_rate": _bucket_error_rate(assertion_results_to_entities(entities), assertion_results, "assertion", ASSERTIONS),
        "temporality_error_rate": _bucket_error_rate(
            temporality_results_to_entities(entities),
            temporality_results,
            "temporality",
            TEMPORALITIES,
        ),
        "subject_error_rate": _bucket_error_rate(subject_results_to_entities(entities), subject_results, "subject", SUBJECTS),
        "event_date_accuracy": round(max(0.0, min(1.0, event_date_accuracy)), 4),
        "attribute_completeness": round(max(0.0, min(1.0, attribute_completeness)), 4),
    }


def assertion_results_to_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Normalize empty labels to required schema buckets.
    out = []
    for e in entities:
        c = dict(e)
        c["assertion"] = (c.get("assertion", "") or "POSITIVE").strip() or "POSITIVE"
        out.append(c)
    return out


def temporality_results_to_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for e in entities:
        c = dict(e)
        c["temporality"] = (c.get("temporality", "") or "UNCERTAIN").strip() or "UNCERTAIN"
        out.append(c)
    return out


def subject_results_to_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for e in entities:
        c = dict(e)
        c["subject"] = (c.get("subject", "") or "PATIENT").strip() or "PATIENT"
        out.append(c)
    return out


def overall_wrong_rate(results: List[Dict[str, Any]]) -> float:
    wrong = sum(1 for r in results if r.get("wrong"))
    return safe_rate(wrong, len(results))
