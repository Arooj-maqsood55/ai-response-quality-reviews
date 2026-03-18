"""Validate evaluation records for missing or inconsistent fields."""

from __future__ import annotations

from typing import Any


REQUIRED_SCORE_KEYS = (
    "task_completion",
    "factual_accuracy",
    "instruction_adherence",
    "clarity",
)


def missing_fields(record: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if field not in record or record[field] in (None, "", [])]


def inconsistent_scores(scores: dict[str, Any], min_score: int = 1, max_score: int = 5) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_SCORE_KEYS:
        if key not in scores:
            issues.append(f"missing score: {key}")
            continue
        value = scores[key]
        if not isinstance(value, (int, float)) or not (min_score <= value <= max_score):
            issues.append(f"out-of-range score: {key}={value}")
    return issues


def validate_review(record: dict[str, Any], required_fields: list[str]) -> dict[str, Any]:
    missing = missing_fields(record, required_fields)
    score_issues = inconsistent_scores(record.get("scores", {}))
    return {
        "ok": not missing and not score_issues,
        "missing_fields": missing,
        "score_issues": score_issues,
    }
