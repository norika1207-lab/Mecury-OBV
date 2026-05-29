#!/usr/bin/env python3
"""Iseeu Receipt JP v0.1 post-OCR structuring engine.

This is intentionally small and local. It does not perform image OCR. It turns
OCR text or OCR blocks into structured Japanese receipt data, with confidence
and unsupported-layout detection.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


REGISTRATION_RE = re.compile(r"(?<![A-Za-z])T[ \t\-]*([0-9][0-9 \t\-]{10,}[0-9])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4})(?!\d)")
URL_RE = re.compile(r"https?://|www\.")
DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})[年/\-.](?P<m>\d{1,2})[月/\-.](?P<d>\d{1,2})日?"),
    re.compile(r"令和(?P<r>\d{1,2})年(?P<m>\d{1,2})月(?P<d>\d{1,2})日"),
    re.compile(r"R(?P<r>\d{1,2})[./\-](?P<m>\d{1,2})[./\-](?P<d>\d{1,2})"),
]

TOTAL_HINTS = (
    "合計",
    "総計",
    "総合計",
    "税込合計",
    "お支払",
    "お支払い",
    "請求金額",
    "領収金額",
    "ご利用金額",
    "total",
)
SUBTOTAL_HINTS = ("小計", "税抜", "税抜計", "対象額", "subtotal")
TAX_HINTS = ("消費税", "内税", "税額", "税")
PAYMENT_HINTS = {
    "cash": ("現金", "cash"),
    "credit_card": ("クレジット", "visa", "master", "カード", "credit"),
    "electronic_money": ("交通系", "電子マネー", "suica", "pasmo", "paypay", "楽天pay"),
    "bank_transfer": ("振込", "銀行振込"),
}
MERCHANT_NOISE = (
    "領収書",
    "領収証",
    "レシート",
    "receipt",
    "上様",
    "但し",
    "請求書",
    "納品書",
    "見積書",
    "登録番号",
    "登錄番号",
    "事業者番号",
    "合計",
    "小計",
)


def normalize_text(text: str) -> str:
    replacements = {
        "￥": "¥",
        "，": ",",
        "．": ".",
        "／": "/",
        "－": "-",
        "―": "-",
        "−": "-",
        "　": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def parse_amount(raw: str) -> int | None:
    cleaned = raw.replace(",", "").replace("¥", "").replace("円", "")
    cleaned = re.sub(r"[^\d]", "", cleaned)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def amount_candidates(line: str) -> list[int]:
    line = re.sub(r"(?<![A-Za-z])T[ \t\-]*[0-9][0-9 \t\-]{10,}[0-9]", "", line)
    values: list[int] = []
    for match in re.finditer(
        r"(?:¥\s*)?[0-9]{1,3}(?:,[0-9]{3})+|(?:¥\s*)[0-9]{1,}|[0-9]{1,}円|[0-9]{3,}",
        line,
    ):
        value = parse_amount(match.group(0))
        if value is not None:
            values.append(value)
    if any(hint in line for hint in TAX_HINTS) and "非課税" not in line:
        for match in re.finditer(r"%\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:円)?", line):
            value = parse_amount(match.group(1))
            if value is not None:
                values.append(value)
        if not values:
            for match in re.finditer(r"(?<![%\d])([0-9]{1,3})(?:円)?(?![%\d])", line):
                value = parse_amount(match.group(1))
                if value is not None:
                    values.append(value)
    return values


def parse_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groupdict()
        year = int(groups["y"]) if groups.get("y") else 2018 + int(groups["r"])
        month = int(groups["m"])
        day = int(groups["d"])
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    return None


def extract_registration_number(text: str) -> str | None:
    match = REGISTRATION_RE.search(text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    if 12 <= len(digits) <= 13:
        return "T" + digits
    return None


def detect_payment(text: str) -> str:
    lowered = text.lower()
    for label, hints in PAYMENT_HINTS.items():
        if any(hint.lower() in lowered for hint in hints):
            return label
    return "unknown"


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize_text(text).splitlines() if line.strip()]


def load_input(path: Path) -> tuple[str, list[dict[str, Any]]]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(raw)
        if isinstance(payload, dict):
            blocks = payload.get("blocks", [])
            text = payload.get("text") or "\n".join(
                str(block.get("text", "")) for block in blocks
            )
            return text, blocks
    return raw, []


def choose_merchant(lines: list[str]) -> tuple[str | None, float]:
    for line in lines[:8]:
        lowered = line.lower()
        if any(noise.lower() in lowered for noise in MERCHANT_NOISE):
            continue
        if parse_date(line):
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line) or URL_RE.search(lowered):
            continue
        if amount_candidates(line):
            continue
        if len(line) < 2:
            continue
        return line, 0.72
    return None, 0.0


@dataclass
class AmountEvidence:
    total: int | None = None
    subtotal: int | None = None
    tax_8: int | None = None
    tax_10: int | None = None
    tax_total: int | None = None
    total_confidence: float = 0.0
    tax_confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


def extract_amounts(lines: list[str]) -> AmountEvidence:
    evidence = AmountEvidence()
    all_values: list[int] = []

    for line in lines:
        if "登録番号" in line or "登錄番号" in line or "事業者番号" in line or REGISTRATION_RE.search(line):
            continue
        values = amount_candidates(line)
        if values:
            all_values.extend(values)
        lowered = line.lower()
        compact_lowered = re.sub(r"\s+", "", lowered)

        if ("請求額" in compact_lowered or any(hint.lower() in compact_lowered for hint in TOTAL_HINTS)) and values:
            value = max(values)
            if evidence.total is None or value >= evidence.total:
                evidence.total = value
                evidence.total_confidence = 0.88

        if "金額" in line and values and evidence.total is None:
            evidence.total = max(values)
            evidence.total_confidence = 0.82

        if any(hint.lower() in compact_lowered for hint in SUBTOTAL_HINTS) and values:
            evidence.subtotal = max(values)

        if "8%" in line and any(hint in line for hint in TAX_HINTS) and values:
            evidence.tax_8 = values[-1]
        if "10%" in line and any(hint in line for hint in TAX_HINTS) and values:
            evidence.tax_10 = values[-1]
        if any(hint in line for hint in TAX_HINTS) and "非課税" not in line and values:
            possible_tax = min(values)
            if evidence.tax_total is None or possible_tax <= evidence.tax_total:
                evidence.tax_total = possible_tax

    if evidence.total is None:
        evidence.notes.append("total not found by explicit hint")

    taxes = [value for value in (evidence.tax_8, evidence.tax_10) if value is not None]
    if taxes:
        evidence.tax_total = sum(taxes)

    if evidence.tax_8 is not None or evidence.tax_10 is not None or evidence.tax_total is not None:
        evidence.tax_confidence = 0.72

    return evidence


def extract_line_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        if "登録番号" in line or REGISTRATION_RE.search(line):
            continue
        if any(hint.lower() in line.lower() for hint in TOTAL_HINTS + SUBTOTAL_HINTS):
            continue
        if any(hint in line for hint in TAX_HINTS):
            continue
        values = amount_candidates(line)
        if not values:
            continue
        name = re.sub(r"(?:¥\s*)?[0-9]{1,3}(?:,[0-9]{3})+|(?:¥\s*)?[0-9]{3,}", "", line).strip()
        name = re.sub(r"\s+", " ", name)
        if not name or len(name) < 2:
            continue
        items.append(
            {
                "name": name,
                "quantity": None,
                "unit_price": None,
                "tax_rate": 0.08 if "8%" in line else 0.10 if "10%" in line else None,
                "amount": values[-1],
            }
        )
    return items[:30]


def confidence(value: Any, base: float) -> float:
    return base if value not in (None, "", []) else 0.0


def structure_receipt(text: str, blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized = normalize_text(text)
    lines = split_lines(normalized)
    merchant, merchant_conf = choose_merchant(lines)
    amounts = extract_amounts(lines)
    registration = extract_registration_number(normalized)
    parsed_date = parse_date(normalized)
    line_items = extract_line_items(lines)

    unsupported_reasons: list[str] = []
    if not lines:
        unsupported_reasons.append("empty_ocr")
    if amounts.total is None:
        unsupported_reasons.append("missing_total")
    if merchant is None:
        unsupported_reasons.append("missing_merchant")
    if parsed_date is None:
        unsupported_reasons.append("missing_date")

    result = {
        "document_type": "receipt" if amounts.total is not None else "unknown",
        "merchant_name": merchant,
        "invoice_registration_number": registration,
        "date": parsed_date,
        "currency": "JPY",
        "subtotal": amounts.subtotal,
        "tax_8_percent": amounts.tax_8,
        "tax_10_percent": amounts.tax_10,
        "tax_total": amounts.tax_total,
        "total": amounts.total,
        "payment_method": detect_payment(normalized),
        "line_items": line_items,
        "confidence": {
            "merchant_name": round(merchant_conf, 3),
            "date": confidence(parsed_date, 0.92),
            "invoice_registration_number": confidence(registration, 0.98),
            "total": round(amounts.total_confidence, 3),
            "tax": round(amounts.tax_confidence, 3),
            "line_items": 0.62 if line_items else 0.0,
        },
        "unsupported_reason": ",".join(unsupported_reasons) if unsupported_reasons else None,
        "engine": {
            "name": "iseeu_receipt_jp",
            "version": "0.1.0",
            "mode": "post_ocr_structuring",
            "notes": amounts.notes,
            "block_count": len(blocks or []),
        },
    }
    return result


def write_csv(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
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
        "unsupported_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({field: result.get(field) for field in fields})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="OCR text file or JSON block file.")
    parser.add_argument("--out", default=None, help="Structured JSON output path.")
    parser.add_argument("--csv", default=None, help="CSV output path.")
    args = parser.parse_args()

    text, blocks = load_input(Path(args.input))
    result = structure_receipt(text, blocks)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")

    if args.csv:
        write_csv(result, Path(args.csv))

    return 0 if result["unsupported_reason"] is None else 3


if __name__ == "__main__":
    raise SystemExit(main())
