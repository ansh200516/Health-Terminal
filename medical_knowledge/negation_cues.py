"""NegEx-inspired lexical cues for assertion detection."""

from __future__ import annotations

PRE_NEGATION_TRIGGERS = [
    "no",
    "denies",
    "without",
    "negative for",
    "free of",
    "not have",
    "not experiencing",
]

POST_NEGATION_TRIGGERS = [
    "was ruled out",
    "were ruled out",
    "is excluded",
    "are excluded",
]

UNCERTAINTY_TRIGGERS = [
    "possible",
    "possibly",
    "suspected",
    "suggestive of",
    "cannot exclude",
    "may represent",
    "likely",
    "rule out",
    "question of",
    "concern for",
]

PSEUDO_NEGATION_TRIGGERS = [
    "not only",
    "noted",
    "not necessarily",
]
