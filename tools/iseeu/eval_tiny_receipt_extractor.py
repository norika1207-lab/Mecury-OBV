#!/usr/bin/env python3
"""Evaluate a tiny Iseeu Receipt JP extractor artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from train_tiny_receipt_extractor import hashed_features


DEFAULT_DATASET = Path("var/product/iseeu-llm/llm/receipt-jp-teacher.jsonl")
DEFAULT_MODEL = Path("var/product/iseeu-llm/llm/artifacts/receipt-jp-tiny-baseline.json")


def dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def predict(model: dict[str, Any], text: str) -> dict[str, Any]:
    query = hashed_features(text, int(model["feature_buckets"]))
    best = max(model["records"], key=lambda record: dot(query, record["features"]))
    return {
        "matched_id": best["id"],
        "score": round(dot(query, best["features"]), 6),
        "output": best["output"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    args = parser.parse_args()

    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    examples = load_jsonl(Path(args.dataset))
    rows = []
    passed = 0
    total = 0
    exact = 0
    for example in examples:
        pred = predict(model, example["input"]["ocr_text"])
        expected = example["output"]
        if pred["output"] == expected:
            exact += 1
        for key, expected_value in expected.items():
            total += 1
            ok = pred["output"].get(key) == expected_value
            passed += int(ok)
            rows.append(
                {
                    "id": example["id"],
                    "matched_id": pred["matched_id"],
                    "field": key,
                    "expected": expected_value,
                    "actual": pred["output"].get(key),
                    "pass": ok,
                }
            )

    report = {
        "model": str(args.model),
        "dataset": str(args.dataset),
        "examples": len(examples),
        "exact_match_examples": exact,
        "exact_match_accuracy": exact / len(examples) if examples else 0.0,
        "field_checks": total,
        "field_passed": passed,
        "field_accuracy": passed / total if total else 0.0,
        "is_final_llm": model.get("is_final_llm", False),
        "rows": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
