#!/usr/bin/env python3
"""Compare Iseeu Receipt JP against a naive OCR+regex baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from receipt_jp_engine import load_input, structure_receipt


def baseline(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    values = []
    import re

    for match in re.finditer(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,}", text):
        values.append(int(match.group(0).replace(",", "")))
    return {
        "merchant_name": lines[0] if lines else None,
        "invoice_registration_number": None,
        "date": None,
        "total": max(values) if values else None,
        "tax_total": None,
        "payment_method": "unknown",
    }


def score(actual: dict, expected: dict) -> tuple[int, int]:
    passed = 0
    total = 0
    for key, value in expected.items():
        total += 1
        passed += int(actual.get(key) == value)
    return passed, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default="var/product/iseeu-llm/samples")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    iseeu_passed = baseline_passed = total = 0
    rows = []
    for expected_path in sorted(samples_dir.glob("*.expected.json")):
        stem = expected_path.name.removesuffix(".expected.json")
        input_path = samples_dir / f"{stem}.txt"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        text, blocks = load_input(input_path)
        iseeu = structure_receipt(text, blocks)
        naive = baseline(text)
        ip, it = score(iseeu, expected)
        bp, bt = score(naive, expected)
        iseeu_passed += ip
        baseline_passed += bp
        total += it
        rows.append(
            {
                "sample": stem,
                "iseeu": f"{ip}/{it}",
                "baseline": f"{bp}/{bt}",
            }
        )

    report = {
        "samples": len(rows),
        "field_checks": total,
        "iseeu_passed": iseeu_passed,
        "baseline_passed": baseline_passed,
        "iseeu_accuracy": iseeu_passed / total if total else 0,
        "baseline_accuracy": baseline_passed / total if total else 0,
        "beats_ocr_plus_regex": iseeu_passed > baseline_passed,
        "rows": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["beats_ocr_plus_regex"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

