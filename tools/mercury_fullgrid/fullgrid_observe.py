#!/usr/bin/env python3
"""Mercury full-grid observer.

This is the takeover observer: it records dense activation heat grids for
every observed tensor channel, not head-level averages.

Output per module:
  heat/<module_key>.npy    uint32 memmap, shape [dim, Q, S]

Meta:
  meta.json contains module list, total cells, nonzero cells, coverage.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from transformers.pytorch_utils import Conv1D as HFConv1D
except Exception:  # pragma: no cover
    HFConv1D = None


DEFAULT_PROBES = [
    "The cat sat on the mat.",
    "Solve: 17 + 25 =",
    "Once upon a time in a faraway kingdom,",
    "The most efficient algorithm for sorting is",
    "In Python, list comprehension syntax looks like",
    "Q: What is the capital of France? A:",
    "Newton's second law states that",
    "The lobster scuttled across the seabed,",
    "def fibonacci(n):\n    if n <= 1:",
    "translate to french: hello world",
    "Explain photosynthesis in one sentence.",
    "She opened the door and saw",
    "The Roman Empire fell because",
    "Calculate the derivative of x^2 + 3x.",
    "import numpy as np\narr =",
    "<|user|>What is consciousness?<|assistant|>",
    "今天天氣很好，我們去",
    "宇宙的盡頭是什麼？",
    "SELECT * FROM users WHERE",
    'git commit -m "fix:',
    "The protein folds into",
    "When light hits a prism,",
    "他打開冰箱，發現",
    "Theorem: For any prime p,",
    "Once the data is loaded,",
    "犯人在現場留下了",
    "海德格認為存在",
    "如果你穿越到唐朝，",
    "The algorithm runs in O(",
    "I love you because",
]


def module_kind(module: nn.Module) -> str | None:
    if isinstance(module, nn.Linear):
        return "linear"
    if HFConv1D is not None and isinstance(module, HFConv1D):
        return "hf_conv1d"
    if isinstance(module, (nn.LayerNorm, nn.RMSNorm)) if hasattr(nn, "RMSNorm") else isinstance(module, nn.LayerNorm):
        return "norm"
    return None


def safe_key(name: str) -> str:
    key = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip("."))
    return key or "root"


def last_dim_from_output(out) -> int | None:
    if isinstance(out, tuple):
        out = out[0]
    if not torch.is_tensor(out) or out.ndim < 2:
        return None
    return int(out.shape[-1])


def evenly_spaced_positions(length: int, count: int) -> np.ndarray:
    if length <= 0:
        return np.zeros(count, dtype=np.int64)
    if length >= count:
        return np.linspace(0, length - 1, count).astype(np.int64)
    return np.concatenate([np.arange(length), np.full(count - length, length - 1)]).astype(np.int64)


def load_probes(path: str | None) -> list[str]:
    if not path:
        return DEFAULT_PROBES
    text = Path(path).read_text()
    probes = [p.strip() for p in text.split("\n---\n") if p.strip()]
    return probes or DEFAULT_PROBES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model-path", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--out-root", required=True)
    p.add_argument("--target-cells", type=float, default=1e8)
    p.add_argument("--q", type=int, default=0)
    p.add_argument("--s", type=int, default=0)
    p.add_argument("--max-length", type=int, default=192)
    p.add_argument("--device", default="cpu")
    p.add_argument("--dtype", default="float32", choices=["float32", "float16", "bfloat16"])
    p.add_argument("--probes-file")
    p.add_argument("--edges-from", help="Reuse quantile_edges.npz from an existing run and skip calibration.")
    p.add_argument("--calibration-probes", type=int, default=256)
    p.add_argument("--calibration-values-per-module", type=int, default=200_000)
    p.add_argument("--calibration-rows-per-module", type=int, default=512)
    p.add_argument("--per-channel-quantiles", action="store_true")
    p.add_argument("--calibration-only", action="store_true")
    p.add_argument("--heat-shard-index", type=int, default=0)
    p.add_argument("--heat-shard-count", type=int, default=1)
    p.add_argument("--heat-start-index", type=int, default=0)
    p.add_argument("--heat-end-index", type=int, default=0, help="Exclusive; 0 means all probes.")
    p.add_argument("--include-norms", action="store_true")
    p.add_argument("--trust-remote-code", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.heat_shard_count < 1:
        raise ValueError("--heat-shard-count must be >= 1")
    if args.heat_shard_index < 0 or args.heat_shard_index >= args.heat_shard_count:
        raise ValueError("--heat-shard-index must be in [0, heat-shard-count)")
    if args.heat_start_index < 0:
        raise ValueError("--heat-start-index must be >= 0")
    if args.heat_end_index and args.heat_end_index <= args.heat_start_index:
        raise ValueError("--heat-end-index must be greater than --heat-start-index")
    t0 = time.time()
    out_dir = Path(args.out_root) / args.model_name
    heat_dir = out_dir / "heat"
    heat_dir.mkdir(parents=True, exist_ok=True)

    probes = load_probes(args.probes_file)
    (out_dir / "probes.txt").write_text("\n\n".join(f"=== probe {i} ===\n{p}" for i, p in enumerate(probes)))

    dtype = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}[args.dtype]
    print(f"[fullgrid] load tokenizer {args.model_path}", flush=True)
    tok = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=args.trust_remote_code)
    print(f"[fullgrid] load model {args.model_path} device={args.device} dtype={args.dtype}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=dtype,
        trust_remote_code=args.trust_remote_code,
        low_cpu_mem_usage=True,
    )
    if args.device != "cpu":
        model = model.to(args.device)
    model.eval()

    observed: OrderedDict[str, dict] = OrderedDict()
    handles = []

    def discovery_hook(name: str, kind: str):
        def hook(_module, _inp, out):
            dim = last_dim_from_output(out)
            if dim is not None and name not in observed:
                observed[name] = {"key": safe_key(name), "kind": kind, "dim": dim}
        return hook

    for name, module in model.named_modules():
        kind = module_kind(module)
        if kind is None:
            continue
        if kind == "norm" and not args.include_norms:
            continue
        handles.append(module.register_forward_hook(discovery_hook(name, kind)))

    with torch.no_grad():
        ids = tok(probes[0], return_tensors="pt", truncation=True, max_length=args.max_length).input_ids
        if args.device != "cpu":
            ids = ids.to(args.device)
        _ = model(ids)
    for h in handles:
        h.remove()
    handles.clear()

    total_channels = sum(item["dim"] for item in observed.values())
    if total_channels <= 0:
        raise RuntimeError("no observable tensor channels discovered")

    qs_needed = max(1, math.ceil(args.target_cells / total_channels))
    s_count = args.s or min(128, max(10, math.ceil(math.sqrt(qs_needed))))
    q_count = args.q or max(10, math.ceil(qs_needed / s_count))
    actual_cells = total_channels * q_count * s_count
    print(
        f"[fullgrid] modules={len(observed)} channels={total_channels:,} Q={q_count} S={s_count} cells={actual_cells:,}",
        flush=True,
    )

    heat = {}
    for name, item in observed.items():
        shape = (item["dim"], q_count, s_count)
        path = heat_dir / f"{item['key']}.npy"
        heat[name] = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint32, shape=shape)
        item["heat_file"] = str(path)
        item["shape"] = list(shape)

    name_to_module = dict(model.named_modules())

    if args.edges_from:
        edge_path = Path(args.edges_from)
        loaded_edges = np.load(edge_path)
        edges = {}
        missing = []
        for name, item in observed.items():
            key = item["key"]
            if key not in loaded_edges:
                missing.append(key)
            else:
                edges[name] = loaded_edges[key].astype(np.float32)
        if missing:
            raise RuntimeError(f"edges file missing {len(missing)} observed modules, first missing={missing[0]}")
        calib_probes = []
        print(f"[fullgrid] reuse quantile edges from {edge_path}", flush=True)
    else:
        # Calibration builds quantile edges. Per-channel mode avoids module-global
        # bins that can make many channel/bin cells unreachable.
        calib = {name: [] for name in observed}
        calib_value_counts = {name: 0 for name in observed}
        calib_row_counts = {name: 0 for name in observed}

        def calibration_hook(name: str):
            def hook(_module, _inp, out):
                if isinstance(out, tuple):
                    out = out[0]
                if not torch.is_tensor(out) or out.ndim < 2:
                    return
                x = out.detach().float().cpu().numpy()
                if args.per_channel_quantiles:
                    rows = x.reshape(-1, x.shape[-1])
                    remaining = args.calibration_rows_per_module - calib_row_counts[name]
                    if remaining <= 0 or rows.size == 0:
                        return
                    if rows.shape[0] > remaining:
                        idx = np.linspace(0, rows.shape[0] - 1, remaining).astype(np.int64)
                        rows = rows[idx]
                    calib[name].append(rows.astype(np.float32, copy=False))
                    calib_row_counts[name] += int(rows.shape[0])
                else:
                    remaining = args.calibration_values_per_module - calib_value_counts[name]
                    if remaining <= 0:
                        return
                    vals = x.reshape(-1)
                    if vals.size:
                        if vals.size > remaining:
                            idx = np.linspace(0, vals.size - 1, remaining).astype(np.int64)
                            vals = vals[idx]
                        calib[name].append(vals.astype(np.float32, copy=False))
                        calib_value_counts[name] += int(vals.size)
            return hook

        for name in observed:
            handles.append(name_to_module[name].register_forward_hook(calibration_hook(name)))

        if args.calibration_probes > 0 and len(probes) > args.calibration_probes:
            calib_indices = evenly_spaced_positions(len(probes), args.calibration_probes)
            calib_probes = [probes[int(i)] for i in calib_indices]
        else:
            calib_probes = probes
        print(
            f"[fullgrid] pass1 calibration probes={len(calib_probes)} heat_probes={len(probes)}",
            flush=True,
        )
        with torch.no_grad():
            for i, prompt in enumerate(calib_probes):
                ids = tok(prompt, return_tensors="pt", truncation=True, max_length=args.max_length).input_ids
                if args.device != "cpu":
                    ids = ids.to(args.device)
                _ = model(ids)
                if (i + 1) % 5 == 0:
                    print(f"[fullgrid] calibration {i+1}/{len(calib_probes)} elapsed={time.time()-t0:.0f}s", flush=True)
        for h in handles:
            h.remove()
        handles.clear()

        edges = {}
        for name, chunks in calib.items():
            vals = np.concatenate(chunks, axis=0)
            if args.per_channel_quantiles:
                edges[name] = np.quantile(vals, np.linspace(0, 1, q_count + 1), axis=0).T.astype(np.float32)
            else:
                vals = vals.reshape(-1)
                edges[name] = np.quantile(vals, np.linspace(0, 1, q_count + 1)).astype(np.float32)
        np.savez(out_dir / "quantile_edges.npz", **{observed[n]["key"]: e for n, e in edges.items()})
        del calib
        if args.calibration_only:
            meta = {
                "observer": "mercury_fullgrid_observe.py",
                "model_name": args.model_name,
                "model_path": args.model_path,
                "target_cells": int(args.target_cells),
                "actual_cells": int(actual_cells),
                "Q": q_count,
                "S": s_count,
                "max_length": args.max_length,
                "probe_count": len(probes),
                "calibration_probe_count": len(calib_probes),
                "calibration_only": True,
                "calibration_values_per_module": int(args.calibration_values_per_module),
                "calibration_rows_per_module": int(args.calibration_rows_per_module),
                "per_channel_quantiles": bool(args.per_channel_quantiles),
                "include_norms": args.include_norms,
                "total_channels": int(total_channels),
                "module_count": len(observed),
                "modules": observed,
                "wall_seconds": round(time.time() - t0, 1),
                "timestamp": int(time.time()),
            }
            (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
            print(f"[fullgrid] CALIBRATION_ONLY {args.model_name} cells={actual_cells:,}", flush=True)
            return

    def fill_hook(name: str):
        bins_edges = edges[name][:, 1:-1] if args.per_channel_quantiles else edges[name][1:-1]
        arr = heat[name]

        def hook(_module, _inp, out):
            if isinstance(out, tuple):
                out = out[0]
            if not torch.is_tensor(out) or out.ndim < 2:
                return
            x = out.detach().float().cpu().numpy()
            x = x.reshape(-1, x.shape[-2], x.shape[-1])[-1]
            pos_idx = evenly_spaced_positions(x.shape[0], s_count)
            dim = min(arr.shape[0], x.shape[1])
            rows = np.arange(dim)
            for s_idx, pos in enumerate(pos_idx):
                if args.per_channel_quantiles:
                    bins = np.clip((x[pos, :dim, None] > bins_edges[:dim]).sum(axis=1), 0, q_count - 1)
                else:
                    bins = np.clip(np.searchsorted(bins_edges, x[pos, :dim]), 0, q_count - 1)
                np.add.at(arr[:, :, s_idx], (rows, bins), 1)

        return hook

    for name in observed:
        handles.append(name_to_module[name].register_forward_hook(fill_hook(name)))

    heat_end = args.heat_end_index or len(probes)
    heat_end = min(heat_end, len(probes))
    heat_jobs = [
        (i, p)
        for i, p in enumerate(probes)
        if args.heat_start_index <= i < heat_end and i % args.heat_shard_count == args.heat_shard_index
    ]
    print(
        f"[fullgrid] pass2 heat fill shard={args.heat_shard_index}/{args.heat_shard_count} "
        f"range=[{args.heat_start_index},{heat_end}) probes={len(heat_jobs)}/{len(probes)}",
        flush=True,
    )
    with torch.no_grad():
        for j, (i, prompt) in enumerate(heat_jobs):
            ids = tok(prompt, return_tensors="pt", truncation=True, max_length=args.max_length).input_ids
            if args.device != "cpu":
                ids = ids.to(args.device)
            _ = model(ids)
            if (j + 1) % 5 == 0:
                print(
                    f"[fullgrid] heat shard_progress={j+1}/{len(heat_jobs)} "
                    f"global_probe={i+1}/{len(probes)} elapsed={time.time()-t0:.0f}s",
                    flush=True,
                )
    for h in handles:
        h.remove()

    nonzero = 0
    module_nonzero = {}
    for name, arr in heat.items():
        arr.flush()
        nz = int((arr > 0).sum())
        module_nonzero[name] = nz
        nonzero += nz

    meta = {
        "observer": "mercury_fullgrid_observe.py",
        "model_name": args.model_name,
        "model_path": args.model_path,
        "target_cells": int(args.target_cells),
        "actual_cells": int(actual_cells),
        "nonzero_cells": int(nonzero),
        "coverage_pct": round(100 * nonzero / actual_cells, 6),
        "Q": q_count,
        "S": s_count,
        "max_length": args.max_length,
        "probe_count": len(probes),
        "heat_probe_count": len(heat_jobs),
        "heat_start_index": args.heat_start_index,
        "heat_end_index": heat_end,
        "heat_shard_index": args.heat_shard_index,
        "heat_shard_count": args.heat_shard_count,
        "calibration_probe_count": len(calib_probes),
        "edges_from": args.edges_from,
        "calibration_values_per_module": int(args.calibration_values_per_module),
        "calibration_rows_per_module": int(args.calibration_rows_per_module),
        "per_channel_quantiles": bool(args.per_channel_quantiles),
        "include_norms": args.include_norms,
        "total_channels": int(total_channels),
        "module_count": len(observed),
        "modules": observed,
        "module_nonzero_cells": module_nonzero,
        "wall_seconds": round(time.time() - t0, 1),
        "timestamp": int(time.time()),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(
        f"[fullgrid] DONE {args.model_name} cells={actual_cells:,} nonzero={nonzero:,} coverage={meta['coverage_pct']}%",
        flush=True,
    )


if __name__ == "__main__":
    main()
