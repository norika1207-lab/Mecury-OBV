# H100 Fullgrid Runbook

Goal: avoid paying H100 time for setup. Do all slow preparation before the GPU
instance starts, then use the H100 only for CUDA heat shards.

## What Must Be Ready Before Renting

- The repo branch with `fullgrid_observe.py`, `merge_fullgrid_shards.py`, and
  `h100_run_fullgrid.sh`.
- `probes_1200.txt`.
- `quantile_edges.npz` for the exact model/run settings.
- Model weights already on a persistent volume, provider cache, or a fast object
  store close to the H100 region.
- A tested Python environment image or startup script.

Do not start the H100 and then decide which model, probes, or edges to use.

## Minimal H100 Sequence

On the H100 host:

```bash
git clone https://github.com/norika1207-lab/Mecury-OBV.git mercury-obv
cd mercury-obv
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install torch transformers accelerate safetensors numpy
```

Then run a shard:

```bash
bash tools/mercury_fullgrid/h100_run_fullgrid.sh \
  --model-path /data/models/MODEL \
  --model-name MODEL-fullgrid-100m-p1200-perchannel-h100-shard-0-of-4 \
  --edges /data/edges/MODEL/quantile_edges.npz \
  --probes /data/probes_1200.txt \
  --out-root /data/fullgrid \
  --shard-index 0 \
  --shard-count 4
```

For one H100, use `--shard-count 1`. For several H100 workers, run one shard
index per worker and merge when all finish.

## Cost Control Rules

- Use H100 only after `nvidia-smi` and the model path are verified.
- Keep model weights on persistent storage or a snapshot so the second run does
  not download again.
- Pull from VPS/object storage, not from a home network or Tailscale path.
- Upload only shard outputs and logs back to the VPS.
- Shut down the instance immediately after upload.

## Why This Helps

The expensive part should be only forward passes. Calibration and edge creation
can be done once, then heat fill can be split by probe shards. The shard outputs
are additive heat arrays, so they can be merged later with:

```bash
python3 tools/mercury_fullgrid/merge_fullgrid_shards.py \
  --model-name MODEL-fullgrid-100m-p1200-perchannel-merged \
  --out-dir /data/merged/MODEL \
  --shard-dir /data/fullgrid/MODEL-shard-0 \
  --shard-dir /data/fullgrid/MODEL-shard-1
```
