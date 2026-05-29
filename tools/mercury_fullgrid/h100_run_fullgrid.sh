#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  h100_run_fullgrid.sh --model-path PATH --model-name NAME --edges PATH \
    --probes PATH --out-root PATH [--shard-index N --shard-count N]

This script is meant for a rented GPU host after the data bundle is already
present. It fails fast before starting the expensive run if CUDA, model files,
edges, or probes are missing.
USAGE
}

MODEL_PATH=""
MODEL_NAME=""
EDGES=""
PROBES=""
OUT_ROOT=""
SHARD_INDEX="0"
SHARD_COUNT="1"
DTYPE="bfloat16"
TARGET_CELLS="100000000"
MAX_LENGTH="192"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-path) MODEL_PATH="$2"; shift 2 ;;
    --model-name) MODEL_NAME="$2"; shift 2 ;;
    --edges) EDGES="$2"; shift 2 ;;
    --probes) PROBES="$2"; shift 2 ;;
    --out-root) OUT_ROOT="$2"; shift 2 ;;
    --shard-index) SHARD_INDEX="$2"; shift 2 ;;
    --shard-count) SHARD_COUNT="$2"; shift 2 ;;
    --dtype) DTYPE="$2"; shift 2 ;;
    --target-cells) TARGET_CELLS="$2"; shift 2 ;;
    --max-length) MAX_LENGTH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for required in MODEL_PATH MODEL_NAME EDGES PROBES OUT_ROOT; do
  if [[ -z "${!required}" ]]; then
    echo "missing --${required,,}" >&2
    usage >&2
    exit 2
  fi
done

if [[ ! -d "$MODEL_PATH" ]]; then
  echo "model path not found: $MODEL_PATH" >&2
  exit 10
fi
if [[ ! -s "$EDGES" ]]; then
  echo "quantile edges not found or empty: $EDGES" >&2
  exit 11
fi
if [[ ! -s "$PROBES" ]]; then
  echo "probes file not found or empty: $PROBES" >&2
  exit 12
fi

python3 - <<'PY'
import torch
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available; refusing to burn GPU rental time on CPU")
print("cuda", torch.cuda.get_device_name(0))
PY

mkdir -p "$OUT_ROOT/logs"
LOG="$OUT_ROOT/logs/${MODEL_NAME}.log"

exec python3 "$(dirname "$0")/fullgrid_observe.py" \
  --model-path "$MODEL_PATH" \
  --model-name "$MODEL_NAME" \
  --out-root "$OUT_ROOT" \
  --target-cells "$TARGET_CELLS" \
  --device cuda \
  --dtype "$DTYPE" \
  --trust-remote-code \
  --include-norms \
  --probes-file "$PROBES" \
  --edges-from "$EDGES" \
  --per-channel-quantiles \
  --heat-shard-index "$SHARD_INDEX" \
  --heat-shard-count "$SHARD_COUNT" \
  --max-length "$MAX_LENGTH" \
  2>&1 | tee "$LOG"
