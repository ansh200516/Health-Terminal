"""Main orchestrator that coordinates all evaluator agents."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from agents.assertion_validator import AssertionValidator
from agents.entity_type_validator import EntityTypeValidator
from agents.metadata_validator import MetadataValidator
from agents.subject_validator import SubjectValidator
from agents.temporality_validator import TemporalityValidator
from config import SETTINGS
from utils.batch_processor import batched_entities
from utils.data_loader import load_chart
from utils.metrics import build_output_payload


class ClinicalEvalOrchestrator:
    def __init__(self) -> None:
        self.entity_agent = EntityTypeValidator()
        self.assertion_agent = AssertionValidator()
        self.temporality_agent = TemporalityValidator()
        self.subject_agent = SubjectValidator()
        self.metadata_agent = MetadataValidator()

    async def _run_llm_agents(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        entity_type_results: List[Dict[str, Any]] = []
        assertion_results: List[Dict[str, Any]] = []
        temporality_results: List[Dict[str, Any]] = []
        subject_results: List[Dict[str, Any]] = []

        for batch in batched_entities(entities, SETTINGS.max_batch_size):
            et_task = self.entity_agent.validate_batch(batch)
            as_task = self.assertion_agent.validate_batch(batch)
            tp_task = self.temporality_agent.validate_batch(batch)
            sb_task = self.subject_agent.validate_batch(batch)
            et, asr, tmp, sub = await asyncio.gather(et_task, as_task, tp_task, sb_task)
            entity_type_results.extend(et)
            assertion_results.extend(asr)
            temporality_results.extend(tmp)
            subject_results.extend(sub)

        return {
            "entity_type_results": entity_type_results,
            "assertion_results": assertion_results,
            "temporality_results": temporality_results,
            "subject_results": subject_results,
        }

    async def evaluate_json(self, input_json_path: str | Path) -> Dict[str, Any]:
        entities, _markdown = load_chart(input_json_path)
        llm_results = await self._run_llm_agents(entities)
        metadata_results = self.metadata_agent.validate_entities(entities)

        payload = build_output_payload(
            file_name=Path(input_json_path).name,
            entities=entities,
            entity_type_results=llm_results["entity_type_results"],
            assertion_results=llm_results["assertion_results"],
            temporality_results=llm_results["temporality_results"],
            subject_results=llm_results["subject_results"],
            event_date_accuracy=metadata_results["event_date_accuracy"],
            attribute_completeness=metadata_results["attribute_completeness"],
        )
        return payload
