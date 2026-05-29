#!/usr/bin/env python3
"""Build an internal Iseeu Receipt JP pack artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_FILES = [
    "tools/iseeu/receipt_jp_engine.py",
    "tools/iseeu/eval_receipt_jp.py",
    "tools/iseeu/make_layout_ghost.py",
    "var/product/iseeu-llm/receipt-jp-schema.json",
    "var/product/iseeu-llm/layout-ghost-schema.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--out-dir", default="dist/iseeu")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    build_dir = out_dir / f"iseeu-receipt-jp-pack-{args.version}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    for source in DEFAULT_FILES:
        src = Path(source)
        dst = build_dir / source
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    sample_dir = Path("var/product/iseeu-llm/samples")
    if sample_dir.exists():
        dst = build_dir / "samples"
        shutil.copytree(sample_dir, dst)

    manifest = {
        "product": "Iseeu Receipt JP",
        "version": args.version,
        "artifact_type": "internal_alpha_pack",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pack_size_target_mb": 50,
        "pack_size_alpha_ceiling_mb": 100,
        "mode": "post_ocr_structuring",
        "public_ready": False,
        "reason_not_public": [
            "sample set is too small",
            "no real receipt trial ledger yet",
            "no iOS capture flow yet"
        ],
        "entrypoint": "tools/iseeu/receipt_jp_engine.py",
    }
    (build_dir / "pack-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    zip_path = out_dir / f"iseeu-receipt-jp-pack-{args.version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(build_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(build_dir))

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(json.dumps({"artifact": str(zip_path), "size_mb": size_mb}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
