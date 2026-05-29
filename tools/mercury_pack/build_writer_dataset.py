#!/usr/bin/env python3
"""Build Mercury 300 Writer Pack alpha task files.

This script does not call a model. It converts seed prompts into a strict JSONL
contract that raw 7B, Mercury 300, and teacher runs can fill later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SYSTEM_PROMPT = (
    "You are a writing engine. Improve practical writing for proposals, "
    "presentations, product narratives, founder notes, and long-form creative "
    "arguments. Prioritize clarity, structure, vividness, and usefulness."
)


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for key in ("id", "domain", "language", "prompt"):
                if key not in row:
                    raise ValueError(f"{path}:{line_no} missing {key}")
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        default="tools/mercury_pack/seed_writer_prompts.jsonl",
        help="Seed prompt JSONL.",
    )
    parser.add_argument(
        "--out",
        default="var/product/mercury-300/writer-alpha-tasks.jsonl",
        help="Output task JSONL.",
    )
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--teacher-model", default="Qwen/Qwen3-30B-A3B")
    args = parser.parse_args()

    seed = Path(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(seed)
    with out.open("w", encoding="utf-8") as handle:
        for row in rows:
            task = {
                "id": row["id"],
                "domain": row["domain"],
                "language": row["language"],
                "base_model": args.base_model,
                "teacher_model": args.teacher_model,
                "system": SYSTEM_PROMPT,
                "prompt": row["prompt"],
                "outputs": {
                    "raw_7b": None,
                    "mercury_300": None,
                    "teacher_30b": None,
                },
                "blind_eval": {
                    "preferred": None,
                    "closest_to_teacher": None,
                    "usable_for_real_work": None,
                    "notes": None,
                },
            }
            handle.write(json.dumps(task, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} tasks to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

