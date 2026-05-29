#!/usr/bin/env python3
"""Evaluate Iseeu Receipt JP samples against expected fields."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from receipt_jp_engine import load_input, structure_receipt
from validate_receipt_jp_schema import validate_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--samples-dir", default="var/product/iseeu-llm/samples"
    )
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    expected_paths = sorted(samples_dir.glob("*.expected.json"))
    checks = []
    schema = []
    passed = 0
    schema_passed = 0
    total = 0

    for expected_path in expected_paths:
        stem = expected_path.name.removesuffix(".expected.json")
        input_path = samples_dir / f"{stem}.txt"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        text, blocks = load_input(input_path)
        actual = structure_receipt(text, blocks)
        schema_errors = validate_receipt(actual)
        schema_ok = not schema_errors
        schema_passed += int(schema_ok)
        schema.append({"sample": stem, "valid": schema_ok, "errors": schema_errors})
        for key, expected_value in expected.items():
            total += 1
            actual_value = actual.get(key)
            ok = actual_value == expected_value
            passed += int(ok)
            checks.append(
                {
                    "sample": stem,
                    "field": key,
                    "expected": expected_value,
                    "actual": actual_value,
                    "pass": ok,
                }
            )

    report = {
        "samples": len(expected_paths),
        "field_checks": total,
        "passed": passed,
        "field_accuracy": passed / total if total else 0.0,
        "schema_valid_samples": schema_passed,
        "schema_accuracy": schema_passed / len(expected_paths) if expected_paths else 0.0,
        "schema": schema,
        "checks": checks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == total and schema_passed == len(expected_paths) else 1


if __name__ == "__main__":
    raise SystemExit(main())
