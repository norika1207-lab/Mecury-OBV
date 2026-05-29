#!/usr/bin/env python3
"""Train/export the first tiny Iseeu Receipt JP extractor baseline.

This is deliberately a baseline artifact, not the final LLM. It proves the
training/evaluation/export contract with a tiny nearest-neighbor model over
character n-gram hashes. The next model can replace this artifact without
changing the surrounding gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DATASET = Path("var/product/iseeu-llm/llm/receipt-jp-teacher.jsonl")
DEFAULT_OUT = Path("var/product/iseeu-llm/llm/artifacts/receipt-jp-tiny-baseline.json")


def ngrams(text: str, min_n: int = 2, max_n: int = 5) -> Counter[str]:
    compact = "".join(text.lower().split())
    counts: Counter[str] = Counter()
    for n in range(min_n, max_n + 1):
        for index in range(0, max(0, len(compact) - n + 1)):
            gram = compact[index : index + n]
            counts[gram] += 1
    return counts


def hashed_features(text: str, buckets: int) -> dict[str, float]:
    features: dict[str, float] = {}
    for gram, count in ngrams(text).items():
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=4).hexdigest()
        bucket = str(int(digest, 16) % buckets)
        features[bucket] = features.get(bucket, 0.0) + float(count)
    norm = sum(value * value for value in features.values()) ** 0.5 or 1.0
    return {key: round(value / norm, 6) for key, value in sorted(features.items())}


def load_examples(path: Path) -> list[dict[str, Any]]:
    examples = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--buckets", type=int, default=512)
    args = parser.parse_args()

    dataset = Path(args.dataset)
    examples = load_examples(dataset)
    if not examples:
        raise SystemExit(f"no examples found in {dataset}")

    records = []
    for example in examples:
        text = example["input"]["ocr_text"]
        records.append(
            {
                "id": example["id"],
                "features": hashed_features(text, args.buckets),
                "output": example["output"],
                "source": example["source"],
            }
        )

    artifact = {
        "product": "Iseeu Receipt JP LLM",
        "artifact_type": "tiny_extractor_baseline",
        "version": "0.0.1",
        "is_final_llm": False,
        "task": "receipt_jp_ocr_to_json",
        "algorithm": "char_ngram_hash_nearest_neighbor",
        "feature_buckets": args.buckets,
        "training_examples": len(records),
        "model_size_target_mb": 50,
        "model_size_alpha_ceiling_mb": 100,
        "records": records,
        "notes": [
            "This baseline creates the model artifact contract.",
            "It must be replaced by a learned neural extractor before public LLM claims.",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(out), "examples": len(records), "size_mb": out.stat().st_size / 1024 / 1024}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
