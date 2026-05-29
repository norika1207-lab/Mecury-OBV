#!/usr/bin/env python3
"""Create an empty Mercury 300 use trial record."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", required=True)
    parser.add_argument("--domain", default="other")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--pack", default="Mercury 300 Writer Pack alpha")
    parser.add_argument("--teacher-model", default=None)
    parser.add_argument(
        "--out-dir", default="var/product/mercury-300/use-trials"
    )
    args = parser.parse_args()

    trial_id = "m300_" + uuid4().hex[:12]
    row = {
        "trial_id": trial_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": args.intent,
        "domain": args.domain,
        "base_model": args.base_model,
        "pack": args.pack,
        "teacher_model": args.teacher_model,
        "prompt": args.prompt,
        "outputs": {
            "raw_7b": None,
            "mercury_300": None,
            "teacher": None,
        },
        "judgment": {
            "would_use": None,
            "closest_to_bigger_model": None,
            "saved_time": None,
            "felt_like_upgrade": None,
            "failure_mode": None,
            "notes": None,
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{trial_id}.json"
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
