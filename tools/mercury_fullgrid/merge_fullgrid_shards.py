#!/usr/bin/env python3
"""Merge Mercury fullgrid probe shards.

Each shard must be produced with the same model, probes, quantile edges,
Q/S shape, and module list. Heat arrays are additive, so merging is a
streaming sum over matching .npy files.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--shard-dir", action="append", required=True)
    p.add_argument("--model-name", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    heat_out = out_dir / "heat"
    heat_out.mkdir(parents=True, exist_ok=True)

    shard_dirs = [Path(p) for p in args.shard_dir]
    metas = [json.loads((p / "meta.json").read_text()) for p in shard_dirs]
    base = metas[0]
    modules = base["modules"]
    actual_cells = int(base["actual_cells"])

    for meta in metas[1:]:
        if int(meta["actual_cells"]) != actual_cells:
            raise RuntimeError("shard actual_cells mismatch")
        if set(meta["modules"].keys()) != set(modules.keys()):
            raise RuntimeError("shard module set mismatch")

    module_nonzero = {}
    nonzero = 0
    for name, item in modules.items():
        key = item["key"]
        arrays = [np.load(p / "heat" / f"{key}.npy", mmap_mode="r") for p in shard_dirs]
        shape = arrays[0].shape
        out = np.lib.format.open_memmap(heat_out / f"{key}.npy", mode="w+", dtype=np.uint32, shape=shape)
        out[:] = 0
        for arr in arrays:
            if arr.shape != shape:
                raise RuntimeError(f"shape mismatch for {key}")
            out[:] += arr
        out.flush()
        nz = int((out > 0).sum())
        module_nonzero[name] = nz
        nonzero += nz
        item["heat_file"] = str(heat_out / f"{key}.npy")

    meta = dict(base)
    meta.update(
        {
            "observer": "merge_fullgrid_shards.py",
            "model_name": args.model_name,
            "merged_from": [str(p) for p in shard_dirs],
            "shard_count": len(shard_dirs),
            "heat_probe_count": sum(int(m.get("heat_probe_count", 0)) for m in metas),
            "nonzero_cells": int(nonzero),
            "coverage_pct": round(100 * nonzero / actual_cells, 6),
            "modules": modules,
            "module_nonzero_cells": module_nonzero,
            "wall_seconds": None,
            "timestamp": int(time.time()),
        }
    )
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(
        f"[merge] DONE {args.model_name} shards={len(shard_dirs)} "
        f"cells={actual_cells:,} nonzero={nonzero:,} coverage={meta['coverage_pct']}%",
        flush=True,
    )


if __name__ == "__main__":
    main()
