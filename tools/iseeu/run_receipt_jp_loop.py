#!/usr/bin/env python3
"""Run the Iseeu Receipt JP local build/test loop."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "var/product/iseeu-llm/samples"
GHOSTS = ROOT / "var/product/iseeu-llm/layout-ghosts"
STATUS = ROOT / "var/product/iseeu-llm/receipt-jp-mvp-status.json"
ARTIFACT = ROOT / "dist/iseeu/iseeu-receipt-jp-pack-0.1.0.zip"


def run(args: list[str], allow_fail: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode and not allow_fail:
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def load_json(proc: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(proc.stdout)


def main() -> int:
    run([sys.executable, "-m", "py_compile", *[
        "tools/iseeu/receipt_jp_engine.py",
        "tools/iseeu/eval_receipt_jp.py",
        "tools/iseeu/compare_receipt_engines.py",
        "tools/iseeu/build_receipt_jp_pack.py",
        "tools/iseeu/check_pack_gate.py",
        "tools/iseeu/make_layout_ghost.py",
    ]])

    eval_report = load_json(run([sys.executable, "tools/iseeu/eval_receipt_jp.py"]))
    compare_report = load_json(run([sys.executable, "tools/iseeu/compare_receipt_engines.py"]))
    build_report = load_json(run([sys.executable, "tools/iseeu/build_receipt_jp_pack.py"]))

    GHOSTS.mkdir(parents=True, exist_ok=True)
    ghost_count = 0
    for sample in sorted(SAMPLES.glob("*.txt")):
        out = GHOSTS / f"{sample.stem}.ghost.json"
        run([sys.executable, "tools/iseeu/make_layout_ghost.py", str(sample), "--out", str(out)])
        ghost_count += 1

    gate_report = load_json(
        run(
            [
                sys.executable,
                "tools/iseeu/check_pack_gate.py",
                "--artifact",
                str(ARTIFACT),
                "--trial-count",
                str(eval_report["samples"]),
                "--beats-ocr-plus-regex",
            ],
            allow_fail=True,
        )
    )

    status = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "product": "Iseeu Receipt JP",
        "target": "50MB local Japanese receipt/document intelligence pack",
        "pricing_strategy": {
            "entry_monthly_jpy": 599,
            "plus_monthly_jpy": 999,
            "business_path": "embedded SDK, annual license, scanner/printer/copier/POS OEM",
        },
        "artifact": {
            "path": str(ARTIFACT.relative_to(ROOT)),
            "size_mb": build_report["size_mb"],
            "target_mb": 50,
            "alpha_ceiling_mb": 100,
        },
        "evaluation": {
            "samples": eval_report["samples"],
            "field_checks": eval_report["field_checks"],
            "iseeu_passed": eval_report["passed"],
            "iseeu_accuracy": eval_report["field_accuracy"],
            "baseline_passed": compare_report["baseline_passed"],
            "baseline_accuracy": compare_report["baseline_accuracy"],
            "beats_ocr_plus_regex": compare_report["beats_ocr_plus_regex"],
        },
        "privacy_safe_layout_ghosts": {
            "count": ghost_count,
            "path": str(GHOSTS.relative_to(ROOT)),
        },
        "release_gate": {
            "public_release": gate_report["release_gate"],
            "checks": gate_report["checks"],
        },
        "next_work": [
            "Grow hostile sample trial toward 1000 documents.",
            "Add image OCR adapter boundary without forcing a cloud model.",
            "Add app/API wrapper for photo-to-json integration.",
            "Track unsupported layouts as product-learning targets.",
        ],
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if eval_report["passed"] == eval_report["field_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
