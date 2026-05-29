#!/usr/bin/env python3
"""Check whether a Mercury 300 alpha artifact can be shown externally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="var/product/mercury-300/writer-alpha.json"
    )
    parser.add_argument(
        "--tasks", default="var/product/mercury-300/writer-alpha-tasks.jsonl"
    )
    parser.add_argument("--artifact", default=None)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = Path(args.tasks)
    task_count = count_lines(tasks)

    artifact_size_mb = None
    if args.artifact:
        artifact = Path(args.artifact)
        if artifact.exists():
            artifact_size_mb = artifact.stat().st_size / 1024 / 1024

    checks = [
        {
            "name": "single_base_model",
            "pass": bool(manifest.get("base_model")),
            "detail": manifest.get("base_model"),
        },
        {
            "name": "writer_only_claim",
            "pass": manifest.get("first_pack") == "writer",
            "detail": manifest.get("first_pack"),
        },
        {
            "name": "alpha_size_ceiling_500mb",
            "pass": manifest.get("pack_size_alpha_ceiling_mb") == 500,
            "detail": manifest.get("pack_size_alpha_ceiling_mb"),
        },
        {
            "name": "target_size_300mb",
            "pass": manifest.get("pack_size_target_mb") == 300,
            "detail": manifest.get("pack_size_target_mb"),
        },
        {
            "name": "has_seed_tasks",
            "pass": task_count >= 10,
            "detail": task_count,
        },
        {
            "name": "artifact_under_ceiling",
            "pass": artifact_size_mb is not None and artifact_size_mb <= 500,
            "detail": artifact_size_mb,
        },
    ]

    report = {
        "product": manifest.get("product"),
        "release_gate": all(item["pass"] for item in checks),
        "checks": checks,
        "next_required_action": None,
    }

    if not report["release_gate"]:
        failed = [item["name"] for item in checks if not item["pass"]]
        report["next_required_action"] = "fix_failed_checks: " + ", ".join(failed)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
