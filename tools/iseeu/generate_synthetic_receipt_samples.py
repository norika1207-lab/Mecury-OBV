#!/usr/bin/env python3
"""Generate deterministic synthetic hostile Japanese receipt samples.

These are artificial receipts only. They are for scaling the Iseeu LLM teacher
pipeline without collecting raw private documents.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUT = Path("var/product/iseeu-llm/samples")

MERCHANTS = [
    "合成ローソン 日本橋店",
    "合成ファミリーマート 神田北口店",
    "合成セブン-イレブン 銀座三丁目店",
    "合成ドラッグ青葉 新宿店",
    "合成文具堂 渋谷店",
    "合成カフェ 札幌駅前店",
    "合成電器サービス 横浜店",
    "合成キッチン 大阪本町店",
]
PAYMENTS = [
    ("現金", "cash"),
    ("VISA", "credit_card"),
    ("MasterCard", "credit_card"),
    ("PayPay", "electronic_money"),
    ("Suica", "electronic_money"),
    ("交通系IC", "electronic_money"),
]


def money(value: int, variant: int) -> str:
    if variant % 3 == 0:
        return f"¥{value:,}"
    if variant % 3 == 1:
        return f"{value:,}円"
    return f"{value}"


def build_sample(index: int) -> tuple[str, dict]:
    merchant = MERCHANTS[index % len(MERCHANTS)]
    payment_text, payment_label = PAYMENTS[index % len(PAYMENTS)]
    year = 2026
    month = (index % 12) + 1
    day = (index % 27) + 1
    date_iso = f"{year}-{month:02d}-{day:02d}"
    registration_digits = f"{(1000000000000 + index * 7919) % 9000000000000 + 1000000000000:013d}"
    registration = "T" + registration_digits

    food_base = 180 + (index * 17) % 700
    goods_base = 220 + (index * 31) % 1500
    tax8 = round(food_base * 8 / 108)
    tax10 = round(goods_base * 10 / 110)
    total = food_base + goods_base

    date_forms = [
        f"{year}年{month:02d}月{day:02d}日",
        f"{year}/{month:02d}/{day:02d}",
        f"R8.{month}.{day}",
        f"令和8年{month}月{day}日",
    ]
    reg_forms = [
        f"登録番号 {registration}",
        f"登録番号 T {registration_digits[:4]}-{registration_digits[4:8]}-{registration_digits[8:]}",
        f"事業者番号 T-{registration_digits[:4]}-{registration_digits[4:8]}-{registration_digits[8:]}",
        f"登錄番号 T {registration_digits[:4]} {registration_digits[4:8]} {registration_digits[8:]}",
    ]
    total_forms = [
        f"合計 {money(total, index)}",
        f"お支払い {money(total, index)}",
        f"税込合計 {money(total, index)}",
        f"ご請求額 {money(total, index)}",
    ]

    lines = [
        merchant,
        "領収書" if index % 2 == 0 else "レシート",
        date_forms[index % len(date_forms)],
        reg_forms[index % len(reg_forms)],
        f"食品A 8% {money(food_base, index + 1)}",
        f"日用品B 10% {money(goods_base, index + 2)}",
        f"対象8% {money(food_base, index)}",
        f"内消費税8% {money(tax8, index + 1)}",
        f"対象10% {money(goods_base, index)}",
        f"内税10% {money(tax10, index + 2)}",
        total_forms[index % len(total_forms)],
        payment_text,
    ]
    if index % 5 == 0:
        lines.insert(4, "非課税 110")
    expected = {
        "merchant_name": merchant,
        "invoice_registration_number": registration,
        "date": date_iso,
        "total": total,
        "tax_8_percent": tax8,
        "tax_10_percent": tax10,
        "tax_total": tax8 + tax10,
        "payment_method": payment_label,
        "unsupported_reason": None,
    }
    return "\n".join(lines) + "\n", expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--offset", type=int, default=1)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index in range(args.offset, args.offset + args.count):
        text, expected = build_sample(index)
        stem = f"synthetic-{index:04d}"
        text_path = out_dir / f"{stem}.txt"
        expected_path = out_dir / f"{stem}.expected.json"
        text_path.write_text(text, encoding="utf-8")
        expected_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(stem)
    print(json.dumps({"written": len(written), "first": written[0], "last": written[-1]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
