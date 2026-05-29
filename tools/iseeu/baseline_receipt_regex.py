#!/usr/bin/env python3
"""Naive OCR+regex receipt baseline for Iseeu comparison."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def amount_values(text: str) -> list[int]:
    values = []
    for match in re.finditer(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,}", text):
        values.append(int(match.group(0).replace(",", "")))
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    values = amount_values(text)
    result = {
        "merchant_name": lines[0] if lines else None,
        "invoice_registration_number": None,
        "date": None,
        "total": max(values) if values else None,
        "tax_total": None,
        "payment_method": "unknown",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

