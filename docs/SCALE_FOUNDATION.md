# Scale Foundation

Neuron Mercury's long target is one hundred million neurons coordinated with
available computer hardware to accelerate useful work.

The foundation must avoid one fatal mistake: treating every neuron as a live
process. A 100,000,000-neuron system has to be virtual, sparse, measured, and
hardware-aware.

## North Star

```text
1 user task
  -> sparse routing
  -> virtual neuron shards
  -> CPU/cache/disk/network/GPU substrate placement
  -> structured evidence
  -> benchmark guard
  -> writeback learning
```

The system is only allowed to grow when speed, evidence, and precision budgets
continue to pass.

## Virtual Neurons

The current 1500-neuron catalog is the physical seed: 1000 general UMA/RAG/state-field neurons plus 500 model-field neurons. Future scale comes from
virtual neurons:

- a virtual neuron is a scored responsibility, not necessarily a running worker
- a shard groups thousands of virtual neurons under one executable strategy
- only active shards materialize for a task
- inactive shards remain metadata and learned routing weights
- writeback decides which shards become hotter or colder over time

Default planning assumes 4,096 virtual neurons per shard. A 100,000,000-neuron
target becomes 24,415 virtual shards, which is large but schedulable as metadata,
ranked queues, cache keys, and bounded worker batches.

## Hardware Substrates

Different work belongs on different hardware surfaces:

- CPU L1/hot path: regex, ranking, hashing, tiny routing, evidence scoring
- CPU process pool: bounded parallel scans, syntax gates, smoke tests
- memory/cache: target bundles, plan cache, neuron scores, hot evidence
- disk append log: blackboard, bench history, approvals, audit records
- network nodes: broad exploration that must not block the local hot path
- GPU/vector batch: future embeddings, similarity search, dense learned routing
- local LLM service: private synthesis, grading, and routing experiments after
  latency is measured

Acceleration comes from placement. A slow neuron on the wrong substrate is not
intelligence; it is latency.

## Sparse Execution Rule

The hot path must remain sparse:

- explicit target-file tasks execute finding-producing risk neurons and safety
  gates first
- broad tasks may activate phase neurons for decomposition and exploration
- target scanning is batched once, then fanned out to many risk families
- benchmark budgets are part of the architecture, not optional tests

## 100M Roadmap

1. Physical seed: 1500 measured neurons with deterministic CPU kernels and model-field inference-boundary hooks.
2. Virtual shard planner: `scale-plan` reports target size, shard count, catalog
   groups, and hardware substrates.
3. Shard registry: store shard metadata separately from executable neurons.
4. Score ledger: write accepted speed/evidence outcomes into per-neuron and
   per-shard scores.
5. Scheduler: assign active shards to CPU, memory, disk, network, or GPU lanes.
6. Distributed workers: allow remote VPS/LAN shards for broad non-blocking scans.
7. Learned router: train or tune routing weights from trace and benchmark data.
8. Hardware feedback loop: promote strategies only when real latency improves.

## Non-Negotiable Guardrail

Scale is not success by itself.

The project only advances when the expanded brain finds useful signals faster
than an ordinary tool loop. Every added layer must answer:

```text
Did it reduce time-to-first-useful-signal?
Did it preserve evidence quality?
Did it avoid unnecessary work?
Did it write back a reusable lesson?
```

## Current Implementation

Two commands now turn the scale foundation into runtime artifacts:

```bash
node src/mercury.js shards --target=100000000
node src/mercury.js scores --limit=12
```

`shards` writes `var/shards/registry.json`. It maps the 500 physical seed neurons
into shard families and hardware substrates. This registry is the bridge between
the small executable catalog and the future virtual neuron field.

`scores` reads `var/scores/neuron_scores.jsonl`. Every plan run appends compact
rows with:

- active neuron id and type
- shard family and shard id
- planned hardware substrate
- whether the neuron actually executed on the sparse path
- elapsed time
- evidence and high-evidence counts
- utility score
- cache-hit state

This is still simple, but it creates the essential feedback loop: routing can
eventually prefer neurons and shards that repeatedly produce useful evidence
with lower latency.

Cache-hit target-file plans skip full score-ledger writeback on the hot path.
Learning rows are written when neurons actually execute; repeated cache hits
must stay fast enough to satisfy speed budgets.

`llm-probe` checks a local Ollama-compatible endpoint before local model work is
allowed into a circuit:

```bash
node src/mercury.js llm-probe --url=http://127.0.0.1:11434 --model=qwen2.5:3b
```

This keeps local LLM use measurable. The model is treated as another substrate:
useful when it reduces repeated reasoning, rejected when it slows the hot path.

`llm-fast` is the first reflex layer for a weak local model:

```bash
node src/mercury.js llm-fast --model=qwen2.5:3b --prompt="Reply with exactly: mercury-ok" --refresh
node src/mercury.js llm-fast --model=qwen2.5:3b --prompt="Reply with exactly: mercury-ok"
```

The first command pays the model latency once and writes a normalized cache
entry. The second command answers from `var/llm-cache/` without invoking the
model. This is the core UMA bet for local LLM acceleration: slow generation
becomes a durable reflex when the same question, intent, or route appears again.

`llm-fast` also supports intent keys:

```bash
node src/mercury.js llm-fast --model=qwen2.5:3b --intent=health.ping --prompt="say mercury-ok"
```

Intent keys let different phrasings share one reflex. When no explicit key is
provided, Mercury builds a small deterministic intent fingerprint by removing
filler words and punctuation from the prompt. This is still cheaper than
embedding search and keeps the hot path filesystem-only.

Known-safe reflexes can be seeded without calling the model:

```bash
node src/mercury.js llm-fast --model=qwen2.5:3b --intent=health.ping --prompt=ping --seed-response=pong
```

This turns trusted fixed routes, health checks, and operator-approved answers
into immediate reflex memory. The weak model remains available for unknown
questions, but common paths do not need to pay model latency even once.

Reflex memory is bounded with:

```bash
node src/mercury.js llm-cache stats --limit=12
node src/mercury.js llm-cache prune --max-files=256
```

This protects the acceleration layer from its own growth. A cache that cannot
be inspected and pruned eventually becomes another slow subsystem.

On the Windows/WSL Qwen2.5:3B node, the raw probe measured about 5.5s for a tiny
generation after runner load. A warmed `llm-fast` cache hit returned in the
same millisecond clock tick. That is the first practical target: keep local LLM
generation off the hot path, and promote useful answers into reflex memory.
