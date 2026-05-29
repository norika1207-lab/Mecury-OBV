#!/usr/bin/env python3
"""Check Iseeu LLM pack release gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="var/product/iseeu-llm/product-line.json"
    )
    parser.add_argument("--artifact", default=None)
    parser.add_argument("--trial-count", type=int, default=0)
    parser.add_argument("--beats-ocr-plus-regex", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    gate = manifest["release_gate"]

    artifact_mb = None
    if args.artifact:
        path = Path(args.artifact)
        if path.exists():
            artifact_mb = path.stat().st_size / 1024 / 1024

    checks = [
        {
            "name": "target_is_50mb",
            "pass": manifest.get("pack_size_target_mb") == 50,
            "detail": manifest.get("pack_size_target_mb"),
        },
        {
            "name": "alpha_ceiling_is_100mb",
            "pass": manifest.get("pack_size_alpha_ceiling_mb") == 100,
            "detail": manifest.get("pack_size_alpha_ceiling_mb"),
        },
        {
            "name": "artifact_under_public_ceiling",
            "pass": artifact_mb is not None and artifact_mb <= gate["max_public_pack_mb"],
            "detail": artifact_mb,
        },
        {
            "name": "thousand_document_trial",
            "pass": args.trial_count >= gate["trial_documents_required"],
            "detail": args.trial_count,
        },
        {
            "name": "beats_ocr_plus_regex",
            "pass": bool(args.beats_ocr_plus_regex),
            "detail": bool(args.beats_ocr_plus_regex),
        },
    ]

    report = {
        "product": manifest["product"],
        "release_gate": all(item["pass"] for item in checks),
        "checks": checks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
