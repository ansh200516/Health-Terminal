"""Domain taxonomy and lexical priors for entity type validation."""

from __future__ import annotations

ENTITY_TYPES = [
    "IMMUNIZATION",
    "MEDICAL_DEVICE",
    "MEDICINE",
    "MENTAL_STATUS",
    "PROBLEM",
    "PROCEDURE",
    "SDOH",
    "SOCIAL_HISTORY",
    "TEST",
    "VITAL_NAME",
]


TAXONOMY_HINTS = {
    "MEDICINE": [
        "aspirin",
        "metformin",
        "lisinopril",
        "atorvastatin",
        "ibuprofen",
        "insulin",
        "tablet",
        "capsule",
        "mg",
        "mcg",
        "dose",
    ],
    "PROBLEM": [
        "hypertension",
        "diabetes",
        "asthma",
        "pain",
        "infection",
        "colitis",
        "ulceration",
        "hemorrhoid",
        "adenoma",
        "encephalopathy",
    ],
    "PROCEDURE": [
        "biopsy",
        "surgery",
        "consultation",
        "ultrasound",
        "ct",
        "mri",
        "colonoscopy",
        "polypectomy",
        "exam",
        "follow-up",
        "screening",
    ],
    "TEST": [
        "a1c",
        "glucose",
        "creatinine",
        "histology",
        "pathology",
        "panel",
        "test",
        "lab",
        "specimen",
        "result",
    ],
    "VITAL_NAME": [
        "blood pressure",
        "bp",
        "heart rate",
        "hr",
        "respiratory rate",
        "temp",
        "temperature",
        "spo2",
        "oxygen saturation",
    ],
    "MEDICAL_DEVICE": [
        "pacemaker",
        "pump",
        "cpap",
        "catheter",
        "scope",
        "colonoscope",
        "snare",
        "monitor",
        "instrument",
        "olympus",
    ],
    "IMMUNIZATION": [
        "vaccine",
        "immunization",
        "flu shot",
        "covid",
        "tetanus",
        "pneumococcal",
        "booster",
    ],
    "MENTAL_STATUS": [
        "anxiety",
        "depression",
        "agitated",
        "alert",
        "oriented",
        "confused",
        "mood",
        "affect",
        "psych",
    ],
    "SOCIAL_HISTORY": [
        "smoker",
        "alcohol",
        "drinks",
        "occupation",
        "lives with",
        "married",
        "tobacco",
        "drug use",
    ],
    "SDOH": [
        "housing",
        "food insecurity",
        "transportation",
        "financial",
        "insurance",
        "employment",
        "education",
        "social support",
    ],
}


PROMPT_TAXONOMY_GUIDE = """
Clinical taxonomy guide:
- MEDICINE: drugs/substances administered to patient (including oxygen therapy) and dose forms.
- PROBLEM: diagnoses, diseases, findings, symptoms, complications.
- PROCEDURE: interventions/operations/clinical actions, including planned or completed procedures.
- TEST: diagnostics/labs/pathology requests or results.
- VITAL_NAME: a vital sign concept label (not its value).
- MEDICAL_DEVICE: tangible devices/instruments/equipment.
- IMMUNIZATION: vaccine administration/history.
- MENTAL_STATUS: psychiatry/behavioral/cognitive state terms.
- SOCIAL_HISTORY: behavior/lifestyle/exposures.
- SDOH: social determinants and access constraints.
""".strip()
