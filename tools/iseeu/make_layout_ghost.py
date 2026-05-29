#!/usr/bin/env python3
"""Create a privacy-safe Iseeu layout ghost from block annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


FORBIDDEN_KEYS = {
    "raw_image",
    "raw_ocr_transcript",
    "personal_name",
    "phone_number",
    "email",
    "address",
    "full_merchant_text",
    "full_line_item_text",
    "text",
    "value",
}


def signature(text: str) -> str:
    shape = []
    for char in text:
        if char.isdigit():
            shape.append("0")
        elif char.isalpha():
            shape.append("A")
        elif char.isspace():
            shape.append(" ")
        else:
            shape.append(char)
    normalized = "".join(shape)[:128]
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"shape:{digest}:{normalized[:32]}"


def scrub_block(block: dict) -> dict:
    clean = {k: v for k, v in block.items() if k not in FORBIDDEN_KEYS}
    raw_text = block.get("text") or block.get("value") or ""
    clean["text_signature"] = signature(str(raw_text)) if raw_text else block.get("text_signature")
    return clean


def text_to_source(raw: str) -> dict:
    blocks = []
    for index, line in enumerate(line.strip() for line in raw.splitlines()):
        if not line:
            continue
        blocks.append(
            {
                "block_id": f"line_{index:04d}",
                "kind": "ocr_line",
                "order": index,
                "bbox": None,
                "text": line,
            }
        )
    return {
        "locale": "ja-JP",
        "document_type": "receipt",
        "image_geometry": {},
        "blocks": blocks,
        "relations": [],
        "failure": {"type": "none"},
        "user_fix_summary": {},
    }


def load_source(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return text_to_source(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Annotated JSON with geometry and blocks.")
    parser.add_argument("--out", default=None)
    parser.add_argument("--pack", default="Iseeu Receipt JP")
    args = parser.parse_args()

    source = load_source(Path(args.input))
    blocks = [scrub_block(block) for block in source.get("blocks", [])]
    ghost = {
        "ghost_id": "ghost_" + uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pack": args.pack,
        "locale": source.get("locale", "ja-JP"),
        "document_type": source.get("document_type", "unknown"),
        "image_geometry": source.get("image_geometry", {}),
        "blocks": blocks,
        "relations": source.get("relations", []),
        "failure": source.get("failure", {"type": "none"}),
        "user_fix_summary": source.get("user_fix_summary", {}),
    }

    serialized = json.dumps(ghost, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(serialized, encoding="utf-8")
        print(out)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
