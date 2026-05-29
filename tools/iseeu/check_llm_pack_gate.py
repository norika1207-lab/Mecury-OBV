#!/usr/bin/env python3
"""Check whether Iseeu Receipt JP has crossed from parser MVP to LLM pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher-manifest", default="var/product/iseeu-llm/llm/receipt-jp-teacher-manifest.json")
    parser.add_argument("--model-artifact", default=None)
    parser.add_argument("--teacher-min", type=int, default=1000)
    parser.add_argument("--target-mb", type=float, default=50)
    parser.add_argument("--alpha-ceiling-mb", type=float, default=100)
    args = parser.parse_args()

    manifest_path = Path(args.teacher_manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    model_artifact = Path(args.model_artifact) if args.model_artifact else None
    model_payload = {}
    if model_artifact and model_artifact.exists():
        model_size_mb = model_artifact.stat().st_size / 1024 / 1024
        if model_artifact.suffix.lower() == ".json":
            model_payload = json.loads(model_artifact.read_text(encoding="utf-8"))
    else:
        model_size_mb = None

    checks = [
        {
            "name": "teacher_dataset_exists",
            "pass": manifest_path.exists(),
            "detail": str(manifest_path),
        },
        {
            "name": "teacher_examples_minimum",
            "pass": manifest.get("examples", 0) >= args.teacher_min,
            "detail": manifest.get("examples", 0),
        },
        {
            "name": "privacy_raw_documents_disallowed",
            "pass": manifest.get("privacy", {}).get("raw_private_documents_allowed") is False,
            "detail": manifest.get("privacy", {}),
        },
        {
            "name": "model_artifact_exists",
            "pass": bool(model_artifact and model_artifact.exists()),
            "detail": str(model_artifact) if model_artifact else None,
        },
        {
            "name": "model_under_alpha_ceiling",
            "pass": model_size_mb is not None and model_size_mb <= args.alpha_ceiling_mb,
            "detail": model_size_mb,
        },
        {
            "name": "model_under_target",
            "pass": model_size_mb is not None and model_size_mb <= args.target_mb,
            "detail": model_size_mb,
        },
        {
            "name": "model_not_baseline_placeholder",
            "pass": model_payload.get("is_final_llm") is True,
            "detail": {
                "artifact_type": model_payload.get("artifact_type"),
                "is_final_llm": model_payload.get("is_final_llm"),
            },
        },
    ]
    report = {
        "product": "Iseeu Receipt JP LLM",
        "llm_pack_gate": all(check["pass"] for check in checks),
        "checks": checks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["llm_pack_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
