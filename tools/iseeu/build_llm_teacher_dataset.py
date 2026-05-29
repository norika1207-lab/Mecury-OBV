#!/usr/bin/env python3
"""Build teacher examples for the tiny Iseeu Receipt JP LLM target.

This is the bridge from the parser MVP to a model pack: each example contains a
stable prompt, OCR text, optional privacy-safe layout ghost features, and the
validated structured JSON answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from receipt_jp_engine import load_input, structure_receipt
from validate_receipt_jp_schema import validate_receipt


DEFAULT_SAMPLES = Path("var/product/iseeu-llm/samples")
DEFAULT_GHOSTS = Path("var/product/iseeu-llm/layout-ghosts")
DEFAULT_OUT = Path("var/product/iseeu-llm/llm/receipt-jp-teacher.jsonl")
DEFAULT_MANIFEST = Path("var/product/iseeu-llm/llm/receipt-jp-teacher-manifest.json")

PROMPT = (
    "You are Iseeu Receipt JP. Convert Japanese receipt OCR text and layout "
    "features into strict JSON matching the Iseeu receipt schema. Return JSON only."
)


def stable_id(stem: str, text: str) -> str:
    digest = hashlib.sha256((stem + "\n" + text).encode("utf-8")).hexdigest()[:12]
    return f"rjp_{stem}_{digest}"


def load_ghost_features(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    ghost = json.loads(path.read_text(encoding="utf-8"))
    blocks = ghost.get("blocks", [])
    return {
        "ghost_id": ghost.get("ghost_id"),
        "block_count": len(blocks),
        "text_signatures": [block.get("text_signature") for block in blocks[:64]],
        "failure_type": ghost.get("failure", {}).get("type"),
    }


def compact_answer(payload: dict[str, Any]) -> dict[str, Any]:
    keys = [
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
    return {key: payload.get(key) for key in keys}


def build_examples(samples_dir: Path, ghosts_dir: Path) -> list[dict[str, Any]]:
    examples = []
    for expected_path in sorted(samples_dir.glob("*.expected.json")):
        stem = expected_path.name.removesuffix(".expected.json")
        input_path = samples_dir / f"{stem}.txt"
        text, blocks = load_input(input_path)
        structured = structure_receipt(text, blocks)
        schema_errors = validate_receipt(structured)
        if schema_errors:
            raise SystemExit(f"{stem} does not validate: {schema_errors}")
        answer = compact_answer(structured)
        examples.append(
            {
                "id": stable_id(stem, text),
                "source": str(input_path),
                "task": "receipt_jp_ocr_to_json",
                "prompt": PROMPT,
                "input": {
                    "locale": "ja-JP",
                    "ocr_text": text,
                    "layout_ghost": load_ghost_features(ghosts_dir / f"{stem}.ghost.json"),
                },
                "output": answer,
                "schema": "iseeu_receipt_jp_v1",
                "teacher": {
                    "source": "parser_mvp_v0.1.0_plus_expected_regression",
                    "requires_human_review_before_public_training": True,
                },
            }
        )
    return examples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-dir", default=str(DEFAULT_SAMPLES))
    parser.add_argument("--ghosts-dir", default=str(DEFAULT_GHOSTS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()

    examples = build_examples(Path(args.samples_dir), Path(args.ghosts_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False, sort_keys=True) + "\n")

    output_lengths = [len(json.dumps(example["output"], ensure_ascii=False)) for example in examples]
    input_lengths = [len(example["input"]["ocr_text"]) for example in examples]
    manifest = {
        "dataset": "iseeu_receipt_jp_teacher_v0",
        "path": str(out),
        "examples": len(examples),
        "task": "receipt_jp_ocr_to_json",
        "schema": "iseeu_receipt_jp_v1",
        "privacy": {
            "raw_private_documents_allowed": False,
            "layout_ghosts_only": True,
            "human_review_required_before_public_training": True,
        },
        "size_targets": {
            "model_pack_target_mb": 50,
            "model_pack_alpha_ceiling_mb": 100,
        },
        "stats": {
            "avg_input_chars": round(sum(input_lengths) / len(input_lengths), 2) if input_lengths else 0,
            "avg_output_json_chars": round(sum(output_lengths) / len(output_lengths), 2) if output_lengths else 0,
        },
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
