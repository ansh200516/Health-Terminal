"""Expected metadata attributes by entity type for completeness scoring."""

from __future__ import annotations

EXPECTED_RELATIONS = {
    "MEDICINE": {"STRENGTH", "UNIT", "DOSE", "ROUTE", "FREQUENCY", "FORM", "DURATION", "STATUS"},
    "TEST": {"TEST_VALUE", "TEST_UNIT", "VALUE", "exact_date", "derived_date"},
    "VITAL_NAME": {"VITAL_NAME_VALUE", "VITAL_NAME_UNIT", "exact_date", "derived_date"},
    "PROCEDURE": {"exact_date", "derived_date", "STATUS"},
    "PROBLEM": {"exact_date", "derived_date", "STATUS"},
    "IMMUNIZATION": {"exact_date", "derived_date", "STATUS"},
    "MEDICAL_DEVICE": {"STATUS"},
    "MENTAL_STATUS": {"STATUS"},
    "SDOH": {"STATUS"},
    "SOCIAL_HISTORY": {"STATUS"},
}


DATE_RELATION_TYPES = {"exact_date", "derived_date"}
