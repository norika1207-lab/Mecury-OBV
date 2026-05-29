# Neuron Mercury Architecture

## Core Bet

Most AI latency is not model latency alone. It is also:

- context re-reading
- repeated search
- weak routing
- tool loops that rediscover obvious facts
- unstructured agent chatter
- missing writeback

Neuron Mercury treats those as acceleration targets.

The next core bet is the Rosen Cortex model: software acceleration can reduce
the distance between a task and a useful answer. Instead of treating every task
as a fresh walk through files, tools, memories, and models, Mercury keeps a
scoreable map of Rosen bridges between entry signals and likely exits. A bridge
is not an answer cache. It is a route from "this kind of problem" to "these
namespaces, symbols, tools, neurons, and verification checks are probably worth
touching first."

## Components

### Nano Cortex

Small task router. It classifies the task and chooses a sparse circuit of neurons.
The first version is rule-based so the architecture can be benchmarked before
model training.

Nano Cortex now sits in front of the Rosen bridge map. Its job is not merely to
choose neurons; it should identify the task's entry node, select candidate
bridges under budget, and hand a small set of high-value routes to the neuron
control engine.

### Rosen Cortex

Rosen Cortex is the software-space folding layer. It links distant concepts that
are normally slow to connect:

- vague user intent to likely project namespace
- error text to likely file and symbol families
- spend symptoms to paid-provider call sites and slow loops
- latency symptoms to hot-path risk patterns
- past frontier-model solutions to local reusable paths
- benchmark failures to guarded fix routes

Each route is stored as a Rosen bridge with confidence, latency, cost, risk,
freshness, namespace fit, hit/miss counts, and activation rules. At runtime,
Mercury does cheap bridge scoring before expensive tool loops or model calls.

The intended flow is:

```text
entry signal
  -> bridge candidates
  -> sparse neuron probes
  -> judge checkpoint
  -> evidence packet
  -> action or model escalation
  -> bridge telemetry writeback
```

This is the path beyond exact reflex cache. Reflex says "same question, same
answer." Rosen Cortex says "new question, known nearby route."

The first executable surface is `rosen-route`. It builds an entry signature,
generates static family bridges, pulls nearby task-memory bridges, adds UMA
batch evidence bridges, scores the combined candidate set, writes the strongest
bridges under `var/rosen-cortex/bridges/`, and emits a bounded probe plan. The
guard rule stays the same: model hot path remains forbidden, namespace
isolation is mandatory, and high-risk bridges require judge verification.

`executePlan` now preloads the Rosen route before UMA and neuron dispatch. The
preload is emitted as the `memory.rosen_bridge_preload` artifact, with selected
bridges, risk families, probe plan, guard state, and Rosen elapsed time. This
makes the route executable, not just inspectable through the standalone CLI.
`bench-rosen-execute-plan` guards that integration by requiring a ready preload
artifact, selected bridge count, and bounded Rosen latency.

Rosen Pair Runtime adds the state-field layer under the bridge map. It does not
try to control every possible neuron. It pairs a local mirror neuron with a
remote resident sentinel and tracks the shared state digest for a task
signature. If the digest is unchanged, the pair returns `state_replay`; if a
file or route state changes, it emits `correction_pulse`; if no pair exists, it
starts with `pair_seed`. This is the first implementation of the "do not run a
hundred million neurons, sense their state changes" model. Runtime state lives
under `var/rosen-cortex/pairs/`, is observable through `rosen-pair status`,
`rosen-pair pulse`, `speed-state`, `nervous-system`, and resident
`GET /rosen-pairs`, and is guarded by `bench-rosen-pair-runtime`.

The proof surface is currently a generated docs artifact:
`rosen-proof-report` writes `docs/rosen-proof-report.html` and
`docs/rosen-proof-report.json` from Rosen route state, cold-start evidence,
first-generation replay, accelerate-task replay, and speed-state policy.
Resident `GET /rosen-proof` returns the same proof payload, and
`bench-rosen-proof-report` guards the artifact plus replay numbers.
`monster-proof-report` is the large-repo companion: it binds Rosen routing,
Code Cortex pages, UMA coherence, `monster-doctor` diagnosis, and
`accelerate-task` replay into one pass/fail packet. Resident `GET
/monster-proof` exposes that packet so the control plane can prove the monster
path is accelerated, not only displayed. The command also writes
`docs/monster-proof-report.html` and `docs/monster-proof-report.json` for the
browser-facing proof surface.

Rosen bridges also influence neuron activation. The control map treats a
positive bridge boost as a reason to wake a dormant catalog neuron, then the
resource guard decides whether it can enter the executable circuit. This keeps
the 500-neuron catalog expandable without reverting to full-catalog execution:
bridges can wake new candidates, but only the highest-value lane selections run.

### Cognitive Neurons

Tiny task kernels. They are not chatbots. Each neuron emits one structured
artifact: a signal, evidence list, proposed tool call, risk note, or next action.

The catalog now contains 500 neurons. The new UMA phase layer is deliberately
split into narrow responsibilities:

- decomposition neurons define goals, constraints, targets, dependencies, and
  failure modes
- exploration neurons map repo surface, runtime environment, artifacts, pipeline
  edges, and external interfaces
- analysis neurons inspect latency budgets, evidence density, blast radius,
  cache validity, error handling, state consistency, boundaries, and data quality
- recomposition neurons turn evidence back into patch order, interface contracts,
  rollback shape, test matrix, and release notes
- verification neurons protect syntax, smoke paths, benchmark budgets,
  regression history, and artifact integrity
- acceleration neurons focus on cache strategy, hot-path budgets, parallel work,
  scout ranking, and context pruning
- memory neurons write back trace lessons, neuron scores, benchmark trends, and
  owner guardrails

This expands breadth without making every request pay for every neuron. Broad
repo work can activate the UMA phase layer, while explicit target-file plans keep
the sparse execution path for speed.

### Neuron Control Engine

The 500-neuron catalog is coordinated by a control map, not by spawning every
neuron. Each plan builds `neuron-control-map-v1`, which maps active neurons into
parallel lanes:

- goal
- memory retrieval
- surface exploration
- analysis
- risk
- acceleration
- writeback
- judge
- verification
- synthesis
- support

Each lane has a budget. The scheduler scores active candidates and bridge
probes, selects the best neurons per lane, then hands that bounded set to the
resource guard. On broad acceleration tasks, this lets Mercury use a wider
cognitive surface. On direct target-file tasks, the fast path remains sparse and
finding-producing.

Control selection is now part of the feedback loop. Score rows record each
neuron's control lane, whether the lane selected it, the lane score, the
resource guard cap, and whether it executed. `bench-control-map-score-routing`
proves that a high-utility neuron can be promoted into a future lane-selected
circuit while staying inside the hot-path budget.

The runtime also builds `neuron-dispatch-plan-v1`. This is the first real
distribution surface: selected neurons are grouped into wavefront lanes, each
lane carries substrate metadata, and each wave exposes how many lanes and
neurons can be controlled at once. `bench-lane-dispatch-engine` guards against
regressing back to a plain queue. The current in-process executor keeps tiny
hot-path kernels cheap, while the dispatch plan is the contract for worker
pools, remote nodes, and future GPU/vector batches.

Memory pressure no longer collapses the control engine back to a tiny fixed
circuit. Under pressure, Mercury still preserves a small lane-selected set so
the 500-neuron map can keep improving practical routing without turning into a
slow full-catalog scan.

The long target is 100,000,000 neurons. Neuron Mercury treats that target as a
virtual scale problem, not as one live process per neuron. The physical catalog
defines executable seed behaviors; virtual shards expand those behaviors into
ranked responsibilities that can be scheduled, cached, scored, and written back.
`scale-plan` exposes the current shard math and hardware substrate map.
`shards` writes the current shard registry, and each plan appends a compact
score row per active neuron so later routing can learn which shards are worth
activating.

Under Rosen Cortex, those future neurons are mostly dormant routes, not live
workers. One hundred million means one hundred million possible entry features,
failure patterns, symbol links, tool lessons, blocked paths, distilled model
routes, and guard checks that can be indexed and sparsely awakened. The runtime
must feel large without paying large cost on every request.

### Blackboard

Append-only JSONL task trace under `var/blackboard/`.

Each artifact has:

- `task_id`
- `neuron_id`
- `kernel`
- `signal`
- `evidence`
- `confidence`
- `elapsed_ms`

Rosen preloads appear in the same trace stream as
`memory.rosen_bridge_preload`, so later memory, score, and replay layers can
see which bridge route was available before the rest of the plan ran.

### CPU Tool Kernels

Native tools are the first acceleration layer:

- `rg`
- `git`
- file stat
- directory scan
- test commands, later gated

### Runtime Detector

Neuron Mercury does not pretend every machine has the same fast path.
`runtime-detect` probes the real local substrate and records which providers are
available: NVIDIA/CUDA telemetry, Ollama, vLLM, SGLang, TensorRT-LLM, ONNX
Runtime, OpenVINO, MLX, and llama.cpp-style binaries. The detector is
read-only. Its result feeds `speed-state --full`, so the control plane can route
Qwen/Ollama to slow-path distillation, prefer vLLM/SGLang/TensorRT where
available, and keep deterministic reflex/UMA ahead of all model calls.
On Windows it uses Windows-native command discovery and one WSL probe for both
CUDA visibility and the Qwer/Ollama binary, because repeated WSL cold starts are
themselves a latency bug.

The detector also writes an acceleration route. The current route hard-codes
the hot path to exact reflex cache, low-risk semantic reflex, project UMA
target-file-first, Code Cortex symbol-first, and deterministic tool kernels.
Model providers are slow-path refresh/distillation targets until a benchmark
proves they can enter a hotter lane.

Cache misses do not re-run hardware discovery. They read the latest runtime
profile when available, attach a `provider_hint` to the slow job, and return.
On the NVIDIA/Qwer laptop that hint selects WSL Ollama as slow-path
distillation, leaving reflex, semantic cache, UMA, and deterministic kernels as
the only user-facing hot path.

The current preferred WSL Ollama model is `qwen2.5:7b` when installed. It fits
the RTX 3060 Laptop GPU envelope through Ollama CUDA offload, while
`qwen2.5:3b` remains the fallback. `local-llm start` owns the WSL Ollama startup
path and `bench-local-qwen-acceleration` verifies the intended shape: model
refresh can be hundreds of milliseconds, but repeated intent answers must return
from Mercury cache/reflex in single-digit milliseconds.

The slow worker also respects that hint. If no real provider is available and
no deterministic `--seed-response` was supplied, the job is marked deferred
instead of spending time on a doomed local model call.

When a slow job is solved, the result is promoted twice: once into generic
reflex memory and once into the provider/model intent cache. That means a Qwen
7B slow answer pays the model cost once, then the same intent can hit
`llm-fast` directly without invoking semantic fallback or the slow worker again.

`speed-state` also reports Rosen readiness, total bridge count, latest selected
route count, and latest route latency. `nervous-system` carries the same signal
in its synapse-memory view, alongside resident endpoints for `/speed-state` and
`/nervous-system`, so operators can see whether the bridge map is warm and
being used. Resident `GET /rosen-proof` is the Rosen proof endpoint, `GET
/monster-proof` is the large-repo proof endpoint, and the generated docs report
is the browser artifact.

### Resource Guard

Sparse activation is mandatory. The resource guard caps executable neurons by
available memory and target-file specificity, records the decision under
`var/resource-guard/`, and keeps `model_hot_path=forbidden`. This is the
anti-overactivation layer: more virtual neurons should mean better routing, not
more work on every request.

The night runner is part of this guard surface. Its unattended loop runs both
`bench-rosen-bridge-route` and `bench-rosen-execute-plan`, plus speed-state and
nervous-system checks, so route observability and executable preload coverage
stay protected during long runs.

### Workflow Cache and Temporal Memory

Successful plans write compact workflow records under `var/workflow-cache/`.
Each record stores the nested DAG, circuit ids, evidence packet, finding
summary, and timings. The temporal memory graph under `var/memory-graph/`
stores append-only project events, so future routing can learn from prior
decisions without mixing namespaces.

Durable workflow writeback is controlled separately from hot-path execution.
Benchmarks that prove millisecond RAG/code-cortex speed can disable durable
writeback; normal development runs keep it on so Mercury improves itself over
time.

### Semantic Cache Safety

Semantic cache is acceleration only when the wrong answer is cheap. The risk
gate allows semantic reuse for low-risk speed/status/explanation prompts and
bypasses it for admin, billing, destructive, production, database, deployment,
secret, or permission-like prompts. Bypassed misses go to the slow-worker queue
for later distillation instead of poisoning the hot path.

Hardware is treated as part of the cognitive runtime. CPU hot paths handle
ranking and regex scans; memory stores cache and scores; disk holds durable
trace and bench ledgers; network nodes are reserved for future non-blocking
remote shards; GPU/vector batches are reserved for future dense similarity and
learned routing.

When the user gives explicit target files, Neuron Mercury uses in-process file
scans before spawning external search tools. This reduces process overhead and
keeps the working set small.

Repeated target-file scans also write through to `var/cache/` using a key built
from cwd, target path, file size, mtime, and search pattern. File outlines use
the same fingerprint style. This turns "same file, same question family" into a
cache hit on the next CLI process instead of another cold scan.

For repo diagnosis, the target-file kernel also builds a batched evidence bundle
for the standard risk families in one file pass. Risk neurons read their slice
from that bundle instead of each scanning the same file independently.

Each command also creates a shared run context. Target-file extraction happens
once per task, and recent git history is cached once per CLI process, so a
benchmark suite can reuse the same repository snapshot across tasks.

Risk neurons consume bundle line arrays directly on hot paths. They avoid
join/split churn and reuse line-context snippets across risk families in the
same process.

The shared run context owns the target bundle for a task, so risk neurons do not
recompute bundle fingerprints or reload the same cached bundle repeatedly.

Recent git history is lazy on the fast path. If a task names explicit target
files and does not ask for git/history/commit context, the git neuron records a
speed skip instead of spawning `git log`.

Risk neurons cap candidate expansion before context lookup. The ranking stage
only emits the top six evidence rows per finding, so expanding dozens of extra
candidate lines is treated as avoidable latency.

Blackboard traces are written as compact JSON. They stay structured and
machine-readable while avoiding pretty-print writeback overhead on the hot path.
Patch-plan trace artifacts store summary metadata instead of duplicating the
full patch plan already returned by the caller.

Patch-plan synthesis is executed once. The router may include the synthesis
neuron in the circuit, but the runtime skips the placeholder artifact and writes
the real synthesis artifact after building the plan.

For explicit target-file plans, execution is sparser than routing: the circuit
may record helper neurons, but the hot path executes only finding-producing risk
neurons and required safety gates.

UMA phase neurons follow the same rule. They can structure broad decomposition,
exploration, analysis, recomposition, verification, acceleration, and memory
passes, but a named-file speed path records them in the circuit without forcing
extra file scans.

Symbol outlines are deferred out of the target-file fast path. Direct line
evidence is enough to rank findings; outline/context can be loaded later when a
task explicitly asks for symbol-level explanation.

Target bundle construction uses a broad prefilter before running family regexes,
so irrelevant lines do not pay every risk-family check on cold scans.

Per-neuron elapsed timing is profile-on-demand. Normal fast paths avoid timing
each neuron; `bench --profile` turns it back on when diagnosing the runtime.

Completed target-file plans are cached by task text, cwd, target fingerprints,
circuit ids, and cache schema. If the file has not changed, repeated tasks reuse
the patch plan and redacted artifacts without rerunning the neuron pipeline.

The RAG evidence packet is pointer-first. Instead of forwarding full UMA hits to
later neurons or model calls, Mercury emits source indexes, short excerpts,
token hints, and the retrieval route. This keeps context reduction on the hot
path and leaves full text available by pointer only when needed.

UMA search also writes tiny buffered hit events. `uma hot-pages` turns those
events into promotion and demotion candidates, giving the scheduler a path to
prefer repeatedly useful semantic pages while keeping the search itself inside
the speed budget.
Cache-hit traces write a compact cache artifact plus synthesis summary instead
of duplicating every cached evidence row into the blackboard again.
Cache files are compact JSON too, so cold-path writeback avoids pretty-print
overhead.
Bench reports are compact JSON for the same reason; `history.jsonl` remains the
quick human-sized speed ledger.
Benchmark suites can define speed budgets. The Lobster debug suite currently
expects warm cache total latency at or below 10ms, with full target precision
and 117 high-evidence rows.
The AFU UMA suite expects warm cache latency at or below 12ms, full target
precision, and 55 high-evidence rows per measured run.
`bench --budget` returns a non-zero process exit code on regression, so scripts
can fail fast instead of merely printing a warning.
For repeated benchmarks, evidence and precision budgets use the weakest
measured run rather than the sum across repeats.

Cache storage is bounded with `cache prune --max-files=<n>`, which removes the
oldest Neuron Mercury cache JSON files and keeps the newest entries.
Pruning is whitelist-based: only known cache namespaces in `var/cache/` are
eligible, and symlinks/directories are ignored.

Cache keys use fast mtime/size fingerprints by default to protect the hot path.
`cache audit <file>` prints a strict SHA-256 fingerprint when exact invalidation
needs to be checked.

`bench --warmup --repeat=N` separates cache warmup from measured runs and stores
the run index in each result row, making cold/warm comparisons explicit.
Speed budgets use the maximum per-run elapsed time, so repeated measurements do
not fail merely because totals are accumulated.

`trace latest --summary` prints the blackboard path, cache-hit state, circuit
size, artifact count, and artifact signals without dumping full JSON.

The UMA track adds three pipeline-focused risk neurons for monster repos:
non-atomic latest/manifest writes, silent JSONL data loss, and packaging
entrypoint drift. They run inside the same target-file bundle, so AFU-sized
pipeline diagnostics stay fast instead of becoming a separate slow audit pass.
For `pyproject.toml`, the packaging neuron also parses `[project.scripts]` and
checks whether each `module:function` target maps to a local file and function,
without installing the package or spawning a full environment.
SQLite-heavy pipelines also get a separate aggregate-scan neuron. It flags
COUNT, AVG, GROUP BY, ORDER BY, and fetch-all patterns as production-size
pressure distinct from generic SQLite lock or timeout risk.

`scout` is the first repo-level target discovery mode. It walks a bounded file
set, scores files by risk-family hits, and prints suggested doctor commands for
the highest-pressure targets. This moves Mercury beyond "inspect this file" and
toward "find where the acceleration work should start."

Risk neurons are raw-line-first. The fast path ranks direct matching lines
before expanding nearby context, because top evidence selection only needs a
small set of exact hits.

Secret-like evidence uses the same already-redacted bundle rows. The fast path
does not reread the source line for radius-zero context.

Generic latency-term evidence is skipped when an explicit target file is already
being scanned by risk-family bundles. It is useful as a broad fallback, not as a
hot-path requirement.

### Writeback

Every run writes a trace. Later versions will update neuron scores and routing
weights from accepted results.

Writeback now includes safe acceleration cache records. These are not source
edits; they are redacted runtime artifacts used to avoid repeated deterministic
work across follow-up commands.

Writeback also includes a score ledger under `var/scores/neuron_scores.jsonl`.
The ledger records active neurons, virtual shard family, substrate placement,
execution status, elapsed time, evidence counts, utility score, and cache-hit
state. This keeps future learned routing grounded in measured speed and evidence
instead of intuition.

## MVP Circuits

The first circuits are still documented here for comparison, but the active
runtime has moved from small MVP wiring to a 500-neuron UMA catalog with sparse
execution on hot paths.

### Repo Diagnosis

```text
intent.repo_diagnosis
  -> retrieval.target_file
  -> retrieval.repo_files
  -> tool.file_outline
  -> git.recent_changes
  -> tool.rg_latency_terms
  -> risk.sqlite_timeout
  -> risk.aggregate_scan
  -> risk.sync_exec
  -> risk.network_timeout
  -> risk.retry_loop
  -> risk.secret_exposure
  -> risk.hot_path
  -> risk.atomic_write
  -> risk.silent_data_loss
  -> risk.packaging_entrypoint
  -> evidence.rank
  -> critic.risk_surface
  -> compression.evidence_packet
  -> synthesis.patch_plan
```

### Report Boost

```text
intent.report
  -> retrieval.docs
  -> compression.evidence_packet
  -> critic.missing_citations
  -> style.outline
```

### Safety Gate

```text
safety.destructive_action
  -> block execution
  -> produce approval-required artifact
```

## Patch Plan Mode

`plan` is the first step beyond raw evidence packets.

```text
task text
  -> explicit target-file neuron
  -> lightweight file outline
  -> risk-specific neurons
  -> context snippets
  -> symbol / hot-path annotation
  -> evidence ranking
  -> grouped findings
  -> patch order
  -> verification checklist
  -> blackboard writeback
```

The output is intentionally proposal-only. It can name likely code changes, but
it does not edit files or run destructive actions.

## Benchmark Mode

`bench` runs a fixed suite of tasks through the same plan pipeline and records
metrics:

- wall-clock elapsed time
- target-file precision
- circuit size
- risk family count
- high-ranked evidence count
- blackboard trace path
- stage timings and per-neuron elapsed time when profiling

The first suite is `tasks/lobster-debug.json`.

Every bench run appends to `var/bench/history.jsonl`. This makes speed a tracked
artifact instead of a feeling: new commits can be judged against real elapsed
time and evidence count.
`bench-history` summarizes recent rows by suite, including max run latency,
weakest-run evidence, weakest-run precision, and budget pass/fail.

## Doctor Mode

`doctor` is the accelerated end-to-end workflow:

```text
plan -> proposal -> markdown draft -> scaffold patchset
```

It prints timing for each stage and writes artifacts without changing target
files.

## Proposal Mode

`propose` turns ranked findings into proposal-only patch suggestions.

It writes JSON under `var/proposals/` and never edits target files. Each proposal
contains:

- risk family
- target file / symbol when known
- top ranked evidence
- proposed change steps
- rationale
- verification commands
- approval gate text

## Apply-Safe Scaffold

Phase 4 adds two non-mutating commands:

- `draft latest` turns a proposal JSON into a human-readable patch draft under
  `var/patch-drafts/`.
- `patchset latest` turns a proposal JSON into a unified diff draft under
  `var/patchsets/`.
- `patchset latest --mode template` emits a narrow code-changing diff only for
  approved safe templates. The first template converts hardcoded secret-like
  constants to environment-variable fallbacks.
- `approve latest --owner <name> --note <note>` records an approval artifact
  under `var/approvals/`.

None of these commands applies patches. They prepare an auditable approval path
before any future manual or automated edit.
