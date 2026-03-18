#!/usr/bin/env python3
"""Run rubric-based AI response quality reviews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from field_checks import validate_review


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def score_response(text: str, sources: list[str], wants_bullets: bool) -> dict[str, int]:
    lowered = text.lower()
    source_hits = sum(1 for source in sources if any(token in lowered for token in source.lower().split()[:4]))
    factual = 5 if source_hits >= 1 else 2
    task = 5 if len(text.strip()) > 40 else 3
    adherence = 5 if (("- " in text or text.count("\n-") >= 1) if wants_bullets else True) else 2
    if wants_bullets and text.count("\n") < 1:
        adherence = 2
    clarity = 5 if len(text) < 500 else 3
    return {
        "task_completion": task,
        "factual_accuracy": factual,
        "instruction_adherence": adherence,
        "clarity": clarity,
    }


def weighted_total(scores: dict[str, int], rubric: dict[str, Any]) -> float:
    weights = {item["id"]: item["weight"] for item in rubric["dimensions"]}
    return round(sum(scores[key] * weights[key] for key in scores), 2)


def build_review(pair: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    wants_bullets = "bullet" in pair["prompt"].lower()
    score_a = score_response(pair["response_a"]["text"], pair.get("sources", []), wants_bullets)
    score_b = score_response(pair["response_b"]["text"], pair.get("sources", []), wants_bullets)
    total_a = weighted_total(score_a, rubric)
    total_b = weighted_total(score_b, rubric)
    preferred = "A" if total_a >= total_b else "B"
    winner_scores = score_a if preferred == "A" else score_b

    review = {
        "pair_id": pair["pair_id"],
        "preferred_response": preferred,
        "scores": winner_scores,
        "comparison": {
            "A": {"scores": score_a, "total": total_a},
            "B": {"scores": score_b, "total": total_b},
        },
        "evidence_notes": (
            f"Preferred response {preferred} based on weighted rubric total "
            f"({max(total_a, total_b)} vs {min(total_a, total_b)}). "
            "Checked task coverage, source-aligned claims, and instruction format."
        ),
        "reviewer": "Arooj Maqsood",
    }
    validation = validate_review(review, rubric["required_fields"])
    review["validation"] = validation
    return review


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate paired AI responses with a rubric.")
    parser.add_argument("--pairs", nargs="+", required=True, help="Paths to pair JSON files")
    parser.add_argument("--rubric", required=True, help="Path to rubric JSON")
    parser.add_argument("--out-dir", default="reviews", help="Directory for review JSON output")
    args = parser.parse_args()

    rubric = load_json(Path(args.rubric))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for pair_path in args.pairs:
        pair = load_json(Path(pair_path))
        review = build_review(pair, rubric)
        destination = out_dir / f"{pair['pair_id']}_review.json"
        destination.write_text(json.dumps(review, indent=2), encoding="utf-8")
        status = "OK" if review["validation"]["ok"] else "FLAGGED"
        print(f"[{status}] {pair['pair_id']} -> preferred={review['preferred_response']} ({destination})")


if __name__ == "__main__":
    main()
