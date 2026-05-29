#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import urllib.request


def post_json(url, payload, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def run_raw_ollama(args):
    rows = []
    for trial in range(1, args.repeat + 1):
        payload = {
            "model": args.model,
            "prompt": args.prompt,
            "stream": False,
            "options": {"num_predict": args.num_predict},
        }
        started = time.perf_counter()
        try:
            out = post_json(args.url.rstrip("/") + "/api/generate", payload, timeout=args.timeout)
            elapsed_ms = (time.perf_counter() - started) * 1000
            rows.append({
                "trial": trial,
                "ok": True,
                "ms": round(elapsed_ms, 2),
                "chars": len(out.get("response", "")),
                "eval_count": out.get("eval_count"),
                "eval_duration_ns": out.get("eval_duration"),
            })
        except Exception as exc:
            rows.append({
                "trial": trial,
                "ok": False,
                "ms": round((time.perf_counter() - started) * 1000, 2),
                "error": repr(exc),
            })
    return rows


def run_reflex_cache(args):
    cache_dir = args.cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.sha256(json.dumps({
        "model": args.model,
        "prompt": args.prompt,
        "num_predict": args.num_predict,
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cache_path = os.path.join(cache_dir, key + ".json")
    rows = []
    for trial in range(1, args.repeat + 1):
        started = time.perf_counter()
        if os.path.exists(cache_path) and not (args.refresh and trial == 1):
            with open(cache_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            rows.append({
                "trial": trial,
                "ok": True,
                "mode": "cache_hit",
                "ms": round((time.perf_counter() - started) * 1000, 3),
                "chars": len(cached.get("response", "")),
            })
            continue
        try:
            out = post_json(args.url.rstrip("/") + "/api/generate", {
                "model": args.model,
                "prompt": args.prompt,
                "stream": False,
                "options": {"num_predict": args.num_predict},
            }, timeout=args.timeout)
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump({
                    "created_at": time.time(),
                    "model": args.model,
                    "prompt": args.prompt,
                    "response": out.get("response", ""),
                }, fh, ensure_ascii=False)
            rows.append({
                "trial": trial,
                "ok": True,
                "mode": "cache_seed",
                "ms": round((time.perf_counter() - started) * 1000, 2),
                "chars": len(out.get("response", "")),
            })
        except Exception as exc:
            rows.append({
                "trial": trial,
                "ok": False,
                "mode": "cache_seed_failed",
                "ms": round((time.perf_counter() - started) * 1000, 2),
                "error": repr(exc),
            })
    return rows


def summarize(rows):
    ok_ms = [row["ms"] for row in rows if row.get("ok")]
    if not ok_ms:
        return {"ok": False, "count": 0}
    sorted_ms = sorted(ok_ms)
    return {
        "ok": True,
        "count": len(ok_ms),
        "min_ms": sorted_ms[0],
        "p50_ms": sorted_ms[len(sorted_ms) // 2],
        "max_ms": sorted_ms[-1],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "cache"], default="raw")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--prompt", default="用繁體中文用三句話說明 RTX 3060 筆電現在如何讓本地 AI 回覆更快。")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--num-predict", type=int, default=80)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--cache-dir", default="/tmp/neuron-mercury-qwen-cache")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    rows = run_raw_ollama(args) if args.mode == "raw" else run_reflex_cache(args)
    print(json.dumps({
        "schema": "mercury-qwen-3060-benchmark-v1",
        "mode": args.mode,
        "model": args.model,
        "prompt": args.prompt,
        "repeat": args.repeat,
        "num_predict": args.num_predict,
        "rows": rows,
        "summary": summarize(rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
