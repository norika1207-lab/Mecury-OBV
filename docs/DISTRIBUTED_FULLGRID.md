# Distributed Mercury Fullgrid

The old fullgrid workflow ran one whole model on one machine. That is too slow
for 14B+ models. The new workflow splits heat fill by probe shard and then
merges additive heat arrays.

## Workflow

1. Run one calibration job to create shared quantile edges.

```bash
python3 tools/mercury_fullgrid/fullgrid_observe.py \
  --model-path /path/to/model \
  --model-name MODEL-calibration \
  --out-root /path/to/out \
  --target-cells 100000000 \
  --device cpu \
  --dtype bfloat16 \
  --include-norms \
  --probes-file /path/to/probes_1200.txt \
  --calibration-probes 256 \
  --calibration-rows-per-module 512 \
  --per-channel-quantiles \
  --calibration-only \
  --trust-remote-code
```

2. Copy `quantile_edges.npz` to every worker.

3. Run heat shards. Example for four workers:

```bash
python3 tools/mercury_fullgrid/fullgrid_observe.py \
  --model-path /path/to/model \
  --model-name MODEL-shard-0-of-4 \
  --out-root /path/to/out \
  --target-cells 100000000 \
  --device cpu \
  --dtype bfloat16 \
  --include-norms \
  --probes-file /path/to/probes_1200.txt \
  --edges-from /path/to/quantile_edges.npz \
  --per-channel-quantiles \
  --heat-shard-index 0 \
  --heat-shard-count 4 \
  --trust-remote-code
```

Change `--heat-shard-index` to `1`, `2`, and `3` on the other workers.

4. Copy shard directories back to one merge host.

5. Merge:

```bash
python3 tools/mercury_fullgrid/merge_fullgrid_shards.py \
  --model-name MODEL-fullgrid-100m-p1200-perchannel-merged \
  --out-dir /path/to/merged \
  --shard-dir /path/to/MODEL-shard-0-of-4 \
  --shard-dir /path/to/MODEL-shard-1-of-4 \
  --shard-dir /path/to/MODEL-shard-2-of-4 \
  --shard-dir /path/to/MODEL-shard-3-of-4
```

## Notes

- All shards must use the same model weights, probes file, `Q/S`, norms setting,
  dtype, and `quantile_edges.npz`.
- Heat arrays are additive because each cell stores counts.
- This is the minimum viable distributed path. It parallelizes probe fill, not
  model loading or calibration.
- For heterogeneous machines, assign faster machines more shard indices by
  running multiple shards there, or use a larger shard count than machine count.

