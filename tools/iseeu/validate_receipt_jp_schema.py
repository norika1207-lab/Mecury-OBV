#!/usr/bin/env python3
"""Validate Iseeu Receipt JP structured output.

The JSON schema in var/product is product documentation. This file is the
executable contract used by the eval loop and pack build.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DOCUMENT_TYPES = {"receipt", "invoice", "payment_slip", "unknown"}
PAYMENT_METHODS = {"cash", "credit_card", "electronic_money", "bank_transfer", "unknown"}
REQUIRED_KEYS = {
    "document_type",
    "merchant_name",
    "invoice_registration_number",
    "date",
    "currency",
    "subtotal",
    "tax_8_percent",
    "tax_10_percent",
    "tax_total",
    "total",
    "payment_method",
    "line_items",
    "confidence",
    "unsupported_reason",
    "engine",
}
CONFIDENCE_KEYS = {
    "merchant_name",
    "date",
    "invoice_registration_number",
    "total",
    "tax",
    "line_items",
}


def nullable_string(value: Any) -> bool:
    return value is None or isinstance(value, str)


def nullable_int(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def confidence_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def validate_receipt(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_KEYS - set(payload)
    if missing:
        errors.append("missing keys: " + ", ".join(sorted(missing)))

    if payload.get("document_type") not in DOCUMENT_TYPES:
        errors.append("document_type must be one of " + ", ".join(sorted(DOCUMENT_TYPES)))
    if payload.get("currency") != "JPY":
        errors.append("currency must be JPY")
    if not nullable_string(payload.get("merchant_name")):
        errors.append("merchant_name must be string|null")

    registration = payload.get("invoice_registration_number")
    if registration is not None and not re.fullmatch(r"T\d{12,13}", str(registration)):
        errors.append("invoice_registration_number must be T plus 12-13 digits or null")

    parsed_date = payload.get("date")
    if parsed_date is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(parsed_date)):
        errors.append("date must be YYYY-MM-DD or null")

    for key in ("subtotal", "tax_8_percent", "tax_10_percent", "tax_total", "total"):
        if not nullable_int(payload.get(key)):
            errors.append(f"{key} must be int|null")

    if payload.get("payment_method") not in PAYMENT_METHODS:
        errors.append("payment_method must be one of " + ", ".join(sorted(PAYMENT_METHODS)))
    if not nullable_string(payload.get("unsupported_reason")):
        errors.append("unsupported_reason must be string|null")

    line_items = payload.get("line_items")
    if not isinstance(line_items, list):
        errors.append("line_items must be list")
    else:
        for index, item in enumerate(line_items):
            if not isinstance(item, dict):
                errors.append(f"line_items[{index}] must be object")
                continue
            if not isinstance(item.get("name"), str):
                errors.append(f"line_items[{index}].name must be string")
            if item.get("quantity") is not None and not isinstance(item.get("quantity"), (int, float)):
                errors.append(f"line_items[{index}].quantity must be number|null")
            if item.get("unit_price") is not None and not isinstance(item.get("unit_price"), (int, float)):
                errors.append(f"line_items[{index}].unit_price must be number|null")
            if item.get("tax_rate") not in (None, 0.08, 0.10):
                errors.append(f"line_items[{index}].tax_rate must be 0.08|0.10|null")
            if not nullable_int(item.get("amount")):
                errors.append(f"line_items[{index}].amount must be int|null")

    confidence = payload.get("confidence")
    if not isinstance(confidence, dict):
        errors.append("confidence must be object")
    else:
        missing_confidence = CONFIDENCE_KEYS - set(confidence)
        if missing_confidence:
            errors.append("confidence missing keys: " + ", ".join(sorted(missing_confidence)))
        for key in CONFIDENCE_KEYS & set(confidence):
            if not confidence_value(confidence[key]):
                errors.append(f"confidence.{key} must be 0..1")

    engine = payload.get("engine")
    if not isinstance(engine, dict):
        errors.append("engine must be object")
    elif not engine.get("name") or not engine.get("version"):
        errors.append("engine.name and engine.version are required")

    if payload.get("unsupported_reason") is None and payload.get("total") is None:
        errors.append("supported receipt must have total")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="Structured receipt JSON files.")
    args = parser.parse_args()

    reports = []
    valid = True
    for input_path in args.inputs:
        path = Path(input_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_receipt(payload)
        valid = valid and not errors
        reports.append({"path": str(path), "valid": not errors, "errors": errors})

    print(json.dumps({"valid": valid, "files": reports}, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
