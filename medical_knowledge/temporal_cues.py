"""Temporal cue lexicons inspired by TimeML-style reasoning."""

from __future__ import annotations

CURRENT_CUES = [
    "currently",
    "today",
    "active",
    "presents with",
    "presented with",
    "on exam",
    "was noted",
    "is noted",
    "underwent",
]

HISTORY_CUES = [
    "history of",
    "past medical history",
    "previous",
    "previously",
    "remote",
    "prior",
    "had",
]

UPCOMING_CUES = [
    "plan for",
    "scheduled",
    "will",
    "to return",
    "follow-up",
    "upcoming",
    "next visit",
    "pending",
]

HEADING_PRIORS = {
    "history": "CLINICAL_HISTORY",
    "past medical history": "CLINICAL_HISTORY",
    "assessment and plan": "UPCOMING",
    "plan": "UPCOMING",
    "follow-up": "UPCOMING",
    "chief complaint": "CURRENT",
    "physical examination": "CURRENT",
    "findings": "CURRENT",
}
