#!/usr/bin/env python3
"""Validate structured LLM review records for missing or inconsistent fields."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {"pair_id", "reviewer", "scores", "preferred", "notes"}
SCORE_KEYS = {"task_completion", "factual_accuracy", "instruction_adherence", "clarity"}


def validate_review(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED - set(data)
    if missing:
        errors.append(f"{path.name}: missing fields {sorted(missing)}")
        return errors

    scores = data.get("scores", {})
    for side in ("response_a", "response_b"):
        if side not in scores:
            errors.append(f"{path.name}: scores missing {side}")
            continue
        side_keys = set(scores[side])
        if side_keys != SCORE_KEYS:
            errors.append(f"{path.name}: {side} score keys invalid: {sorted(side_keys)}")
        for key, value in scores[side].items():
            if not isinstance(value, int) or value < 1 or value > 5:
                errors.append(f"{path.name}: {side}.{key} must be int 1-5")

    if data.get("preferred") not in {"response_a", "response_b", "tie"}:
        errors.append(f"{path.name}: preferred must be response_a, response_b, or tie")
    if not str(data.get("notes", "")).strip():
        errors.append(f"{path.name}: notes cannot be empty")
    return errors


def main() -> int:
    review_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "reviews")
    files = sorted(review_dir.glob("*.json"))
    if not files:
        print(f"No review files found in {review_dir}")
        return 1
    all_errors: list[str] = []
    for path in files:
        all_errors.extend(validate_review(path))
    if all_errors:
        print("Validation failed:")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    print(f"Validated {len(files)} review file(s). All required fields present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
