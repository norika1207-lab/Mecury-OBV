# Mercury Fullgrid Sync - 2026-05-29

This directory is the Git-safe index for the May 29 Mercury observation sync.

Raw fullgrid heat data was centralized on the VPS:

`/root/mercury_obv/fullgrid-sync/2026-05-29`

VPS snapshot summary:

- Total size on VPS: `15G`
- Files indexed: `6081`
- `meta.json` files: `38`
- Qualified fullgrid results: `26`
- Continuity result files: `1`

Qualification rule:

- `actual_cells >= 100000000`
- `coverage_pct >= 90`
- Preferred method: dense fullgrid with per-channel quantiles

Important completed raw backups on VPS:

- `gx10/fullgrid/qwen25-3b-fullgrid-100m-p1200-perchannel`
- `gx10/fullgrid/qwen7b-fullgrid-100m-p1200-perchannel`
- `john/fullgrid`
- `ai/fullgrid` snapshot

Notes:

- The `ai/fullgrid` copy is a live snapshot because Gemma and Qwen Instruct runs were still writing heat files during transfer.
- The Git repository intentionally stores metadata, logs, summaries, and manifests only. Raw heat arrays are kept on the VPS to avoid putting multi-GB binary data into Git history.
- `vps/SUMMARY.json` and `vps/MANIFEST.tsv` are generated from the VPS copy.

