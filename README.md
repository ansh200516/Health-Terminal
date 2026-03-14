# Multi-Agentic Clinical AI Evaluation Framework

> **HiLabs Workshop — Building Evals and Reliability Layers for Generative AI in Healthcare**

An evaluation and reliability framework for clinical entity extraction pipelines, built around five specialized LLM-powered agents operating in parallel. Each agent applies a dedicated medical reasoning framework — NegEx, TimeML, SNOMED-CT/RxNorm taxonomy — to assess the quality of AI-generated clinical annotations across six dimensions.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Our Approach](#our-approach)
- [Architecture](#architecture)
- [Agent Design](#agent-design)
- [Medical Frameworks](#medical-frameworks)
- [Mathematical Framework](#mathematical-framework)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Output Schema](#output-schema)
- [Results Summary](#results-summary)

---

## Problem Statement

Clinical AI pipelines convert scanned medical charts into structured entities (diagnoses, medications, procedures, labs, vitals, etc.) enriched with assertion, temporality, subject, and metadata attributes. The goal is **not** to retrain the model, but to build a rigorous evaluation layer that:

1. Identifies where the pipeline is correct and where it fails
2. Quantifies error rates across every annotation dimension
3. Pinpoints the most clinically dangerous failure modes
4. Proposes concrete guardrails to improve reliability

**Dataset:** 30 de-identified clinical charts, ~16,500 extracted entities, 10 entity types

---

## Our Approach

We treat evaluation itself as an intelligent reasoning problem. Rather than applying hand-coded rules or statistical baselines, each dimension of the annotation is assessed by a **dedicated LLM agent** that:

- Carries domain-specific medical knowledge in its system prompt
- Applies a named clinical/linguistic framework (NegEx, TimeML, SNOMED taxonomy)
- Falls back to a deterministic heuristic if the LLM is unavailable
- Can optionally query the web (via Tavily) to resolve unfamiliar medical terms

All four LLM agents run **concurrently per batch** using `asyncio.gather`, and the Metadata agent runs as a deterministic rule engine in parallel, so each chart is processed in a single asynchronous pass.

---

## Architecture

```
test.py input.json output.json
            │
            ▼
  ClinicalEvalOrchestrator
            │
     ┌──────┴──────┐
     │   load_chart │  ← JSON entities + optional markdown OCR text
     └──────┬──────┘
            │  batch_size entities per round
            ▼
  ┌─────────────────────────────────────────┐
  │          asyncio.gather (parallel)       │
  │                                         │
  │  EntityTypeValidator  AssertionValidator │
  │  TemporalityValidator SubjectValidator   │
  └─────────────────────────────────────────┘
            │
            │  (synchronous, rule-based)
            ▼
       MetadataValidator
            │
            ▼
     build_output_payload
            │
            ▼
      output/chart.json
```

Every agent extends `BaseLLMAgent`, which provides:
- **Gemini 2.0 Flash** calls with `temperature=0` and `response_mime_type=application/json`
- **Tenacity retry** with exponential backoff (3 attempts, 1–8 s)
- **Rate-limit throttle** — configurable soft RPM cap to stay within free-tier limits
- **Tavily web search** for low-confidence entity lookups
- **OpenRouter fallback** (Qwen/Mistral) when Gemini is unavailable
- **Deterministic heuristic fallback** when no LLM is configured

---

## Agent Design

### Agent 1 — Entity Type Validator (`entity_type_validator.py`)

Determines whether each entity was assigned the correct semantic category from the 10-class SNOMED-CT/ICD-10/RxNorm-inspired taxonomy.

**Mechanism:**
1. Packages entity text, heading, and surrounding context into a compact JSON batch
2. Sends to Gemini with a detailed taxonomy system prompt
3. Parses `expected_type`, `confidence`, and `rationale` for each entity
4. For `confidence < 0.45`, triggers a Tavily web search to ground rare medical terms
5. Falls back to lexical taxonomy-hint scoring if LLM is unavailable

**System prompt encodes:**
- MEDICINE: drugs, substances, dose forms (RxNorm-style)
- PROBLEM: diagnoses, findings, symptoms (ICD-10 style)
- PROCEDURE: interventions, clinical actions (CPT-style)
- TEST: labs, diagnostics, pathology
- VITAL_NAME: vital sign concept labels (not values)
- MEDICAL_DEVICE: instruments, equipment
- IMMUNIZATION: vaccine administration/history
- MENTAL_STATUS: psychiatric/cognitive state
- SOCIAL_HISTORY: behavior, lifestyle, exposures
- SDOH: social determinants and access constraints

---

### Agent 2 — Assertion Validator (`assertion_validator.py`)

Validates whether the polarity label (POSITIVE / NEGATIVE / UNCERTAIN) is linguistically supported by the surrounding text.

**Mechanism:**
1. Sends entity text to Gemini with a clinical assertion system prompt
2. Heuristic fallback uses structured **NegEx** trigger lists:
   - Pre-negation triggers: *"no", "denies", "without", "negative for"*
   - Post-negation triggers: *"was ruled out", "is excluded"*
   - Pseudo-negation guards: *"not only", "noted"* (prevent false negation)
   - Uncertainty triggers: *"possible", "suspected", "suggestive of", "cannot exclude"*
3. Scope is evaluated per-sentence around the entity mention

---

### Agent 3 — Temporality Validator (`temporality_validator.py`)

Validates whether the temporal label (CURRENT / CLINICAL_HISTORY / UPCOMING / UNCERTAIN) correctly represents when the clinical event occurs relative to the encounter.

**Mechanism:**
1. Sends entity, heading, and context to Gemini with a TimeML-inspired system prompt
2. Heuristic fallback applies a two-layer resolution:
   - **Layer 1 — Heading priors:** "Past Medical History" → CLINICAL_HISTORY, "Assessment and Plan" → UPCOMING, "Physical Examination" → CURRENT
   - **Layer 2 — Text cues:** "presented with", "currently" → CURRENT; "history of", "previously" → CLINICAL_HISTORY; "scheduled", "follow-up", "plan for" → UPCOMING

---

### Agent 4 — Subject Validator (`subject_validator.py`)

Validates whether the entity is correctly attributed to the patient or a family member.

**Mechanism:**
1. Sends entity, heading, and context to Gemini
2. Heuristic fallback scans for family-history section headers and linguistic cues: *"family history", "mother", "father", "sister", "brother", "grandmother"*
3. Default is PATIENT for all contexts without explicit family attribution

---

### Agent 5 — Metadata Validator (`metadata_validator.py`)

A deterministic rule-based agent (no LLM call) that validates QA relation quality and computes two scalar metrics.

**What it checks:**
- **Type-relation consistency:** STRENGTH/UNIT/DOSE/ROUTE/FREQUENCY relations should only appear on MEDICINE entities; VITAL_NAME_VALUE/UNIT only on VITAL_NAME; TEST_VALUE/UNIT only on TEST
- **Date validity:** All `exact_date` and `derived_date` relations must parse as ISO-8601 (`YYYY-MM-DD`)
- **Attribute completeness:** Computes fraction of expected attributes actually present per entity type

**Expected attribute matrix:**

| Entity Type | Required Relations |
|---|---|
| MEDICINE | STRENGTH, UNIT, DOSE, ROUTE, FREQUENCY, FORM, DURATION, STATUS |
| TEST | TEST_VALUE, TEST_UNIT, exact_date |
| VITAL_NAME | VITAL_NAME_VALUE, VITAL_NAME_UNIT |
| PROCEDURE / PROBLEM | exact_date or derived_date |

---

### Agent 6 — Orchestrator (`orchestrator.py`)

Coordinates the full evaluation pipeline.

**Responsibilities:**
1. Loads chart JSON and companion markdown OCR text via `data_loader`
2. Chunks entities into configurable batches (`MAX_BATCH_SIZE`, default 20)
3. Dispatches batches to the 4 LLM agents concurrently with `asyncio.gather`
4. Calls `MetadataValidator` sequentially (deterministic, fast)
5. Passes all per-entity verdicts to `build_output_payload` for metric computation

---

## Medical Frameworks

| Framework | Applied By | Description |
|---|---|---|
| **SNOMED CT / ICD-10 / RxNorm** | Entity Type Agent | Clinical ontology taxonomy used to define correct entity categories and encode lexical priors |
| **NegEx** | Assertion Agent | Rule-based clinical NLP algorithm for negation and uncertainty detection using trigger lists and scope windows |
| **TimeML** | Temporality Agent | ISO standard for temporal event annotation; used to define current, historical, and future event anchoring relative to encounter context |
| **Expected Attribute Matrix** | Metadata Agent | Custom schema defining required/optional QA relation types per entity category, modeled after RxNorm dosage attributes and LOINC result fields |

---

## Mathematical Framework

Error rates are computed per dimension bucket:

```
error_rate(bucket) =  count(entities labeled as bucket AND judged incorrect)
                      ─────────────────────────────────────────────────────
                            count(entities labeled as bucket)
```

| Metric | Formula |
|---|---|
| `entity_type_error_rate[T]` | Wrong entity-type labels / total labeled T |
| `assertion_error_rate[A]` | Wrong assertion labels / total labeled A |
| `temporality_error_rate[T]` | Wrong temporality labels / total labeled T |
| `subject_error_rate[S]` | Wrong subject labels / total labeled S |
| `event_date_accuracy` | Valid ISO-8601 dates / total date relations |
| `attribute_completeness` | Present expected attributes / total expected attributes |

All values are clamped to **[0.0, 1.0]**.

---

## Project Structure

```
hiworkshop/
│
├── test.py                        # Entry point: evaluate one chart
├── run_all.py                     # Batch runner: all 30 charts
├── config.py                      # Environment-variable configuration
├── requirements.txt               # Python dependencies
│
├── agents/
│   ├── base_agent.py              # Shared LLM base (Gemini, Tavily, OpenRouter, fallback)
│   ├── orchestrator.py            # Async coordination and aggregation
│   ├── entity_type_validator.py   # Agent 1: SNOMED-CT taxonomy validation
│   ├── assertion_validator.py     # Agent 2: NegEx assertion detection
│   ├── temporality_validator.py   # Agent 3: TimeML temporal reasoning
│   ├── subject_validator.py       # Agent 4: subject attribution
│   └── metadata_validator.py      # Agent 5: QA relation and date validation
│
├── medical_knowledge/
│   ├── entity_taxonomy.py         # SNOMED/RxNorm/ICD-10 classification reference
│   ├── negation_cues.py           # NegEx trigger lists
│   ├── temporal_cues.py           # TimeML temporal indicator patterns
│   └── expected_attributes.py     # Expected QA relation schemas per entity type
│
├── utils/
│   ├── data_loader.py             # JSON + markdown chart loader
│   ├── batch_processor.py         # Entity batching helper
│   └── metrics.py                 # Error rate computation and output schema builder
│
├── output/
│   ├── *.json                     # 30 per-chart evaluation reports
│   └── summary.json               # Aggregated metrics across all charts
│
├── error_heatmap.png              # Generated heatmap visualization
└── report.md                      # Evaluation report
```

---

## Setup and Installation

**1. Clone and enter the project:**

```bash
git clone <repo-url>
cd hiworkshop
```

**2. Create and activate a conda environment:**

```bash
conda create -n cogni python=3.10 -y
conda activate cogni
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Configure API keys** — create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_key_here
TAVILY_API_KEY=your_tavily_key_here   # optional
OPENROUTER_API_KEY=your_key_here      # optional fallback
GEMINI_MODEL=gemini-2.0-flash         # optional, this is the default
```

> The system works without any API keys using its deterministic heuristic fallback. Set keys to enable full LLM-powered evaluation.

---

## Usage

**Evaluate a single chart:**

```bash
python test.py workshop_test_data/<folder>/<file>.json output/<file>.json
```

Example:

```bash
python test.py workshop_test_data/943W19621_J727-317855_20241217/943W19621_J727-317855_20241217.json output/943W19621_J727-317855_20241217.json
```

**Evaluate all 30 charts:**

```bash
python run_all.py --input-dir workshop_test_data --output-dir output
```

This produces `output/*.json` (one per chart) and `output/summary.json`.

**Regenerate the heatmap:**

```bash
python generate_heatmap.py
```

---

## Output Schema

Each output file follows the required submission schema:

```json
{
  "file_name": "943W19621_J727-317855_20241217.json",
  "entity_type_error_rate": {
    "MEDICINE": 0.0, "PROBLEM": 0.0, "PROCEDURE": 0.0, "TEST": 0.0,
    "VITAL_NAME": 0.0, "IMMUNIZATION": 0.0, "MEDICAL_DEVICE": 0.0,
    "MENTAL_STATUS": 0.0, "SDOH": 0.0, "SOCIAL_HISTORY": 0.0
  },
  "assertion_error_rate": {
    "POSITIVE": 0.0, "NEGATIVE": 0.0, "UNCERTAIN": 0.0
  },
  "temporality_error_rate": {
    "CURRENT": 0.0, "CLINICAL_HISTORY": 0.0, "UPCOMING": 0.0, "UNCERTAIN": 0.0
  },
  "subject_error_rate": {
    "PATIENT": 0.0, "FAMILY_MEMBER": 0.0
  },
  "event_date_accuracy": 0.0,
  "attribute_completeness": 0.0
}
```

---

## Results Summary

| Dimension | Bucket | Mean Error Rate |
|---|---|---:|
| Entity Type | MEDICAL_DEVICE | **0.9538** ← critical |
| Entity Type | SDOH | **0.8556** ← critical |
| Entity Type | MENTAL_STATUS | 0.7361 |
| Entity Type | PROBLEM | 0.6710 |
| Assertion | UNCERTAIN | **0.8268** ← critical |
| Assertion | POSITIVE | 0.5019 |
| Temporality | CURRENT | **0.8834** ← critical |
| Temporality | UPCOMING | 0.6049 |
| Subject | FAMILY_MEMBER | 0.1814 |
| Subject | PATIENT | **0.0201** ← best |
| Global | Event Date Accuracy | **0.9218** ← best |
| Global | Attribute Completeness | 0.1784 |

> See `report.md` for the full heatmap visualization and detailed analysis.

---

## Dependencies

| Package | Purpose |
|---|---|
| `google-generativeai` | Gemini 2.0 Flash LLM calls |
| `tavily-python` | Web search for rare term resolution |
| `aiohttp` | Async HTTP for OpenRouter fallback |
| `tenacity` | Retry logic with exponential backoff |
| `matplotlib` / `seaborn` | Heatmap visualization |
