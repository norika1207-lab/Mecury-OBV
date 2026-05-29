#!/usr/bin/env python3
"""Score Mercury 300 blind eval JSONL files."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ARMS = ("raw_7b", "mercury_300", "teacher_30b")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="var/product/mercury-300/writer-alpha-tasks.jsonl",
    )
    args = parser.parse_args()

    path = Path(args.path)
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    preferred = Counter()
    closest = Counter()
    usable = Counter()
    filled = 0

    for row in rows:
        blind = row.get("blind_eval") or {}
        if blind.get("preferred") in ARMS:
            preferred[blind["preferred"]] += 1
            filled += 1
        if blind.get("closest_to_teacher") in ARMS:
            closest[blind["closest_to_teacher"]] += 1
        if blind.get("usable_for_real_work") in ARMS:
            usable[blind["usable_for_real_work"]] += 1

    total = len(rows)
    mercury_preferred = preferred["mercury_300"]
    mercury_closest = closest["mercury_300"]
    raw_preferred = preferred["raw_7b"]

    report = {
        "tasks": total,
        "filled_preference_votes": filled,
        "preferred": dict(preferred),
        "closest_to_teacher": dict(closest),
        "usable_for_real_work": dict(usable),
        "mercury_preferred_rate": mercury_preferred / filled if filled else 0.0,
        "mercury_closest_rate": mercury_closest / total if total else 0.0,
        "beats_raw_7b": mercury_preferred > raw_preferred,
        "alpha_teacher_closeness_gate": mercury_closest / total >= 0.30 if total else False,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

