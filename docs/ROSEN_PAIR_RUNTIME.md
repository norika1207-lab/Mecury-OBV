# Rosen Pair Runtime

Rosen Pair Runtime is the cold-start answer for Neuron Mercury.

The goal is not to run millions of live agents. The goal is to maintain a huge
field of cheap state neurons and wake real work only when state changes.

## Core Model

Traditional agent scaling says:

```text
task -> start many agents -> wait for results -> synthesize
```

Rosen Pair Runtime says:

```text
project state -> paired neuron digest -> pulse only on delta -> wake route
```

A pair has two software neurons:

- `local_neuron`: the local mirror that can answer from a known state digest.
- `remote_neuron`: the resident sentinel attached to a project, file set, model,
  or service.

They do not communicate through physics or quantum signaling. The acceleration
comes from software pre-synchronization: the local side already knows the last
digest, route confidence, target files, and top Rosen bridges. When the remote
state changes, it emits a correction pulse.

## Why This Attacks Cold Start

Reflex cache accelerates repeated exact work. UMA and Rosen bridges accelerate
known nearby work. Rosen Pair Runtime moves one level earlier:

```text
before question:
  keep project state summarized as digest + bridge map

when question arrives:
  if digest unchanged -> state_replay
  if digest changed -> correction_pulse
  if pair missing -> pair_seed
```

Cold start becomes less cold because the expensive discovery layer has already
been reduced into small state transitions.

## Commands

```bash
node src/mercury.js rosen-pair status
node src/mercury.js rosen-pair pulse "watch src/mercury.js for UMA/RAG acceleration deltas"
node src/mercury.js bench-rosen-pair-runtime
```

Resident endpoint:

```bash
curl -s "http://127.0.0.1:17345/rosen-pairs?task=watch%20provider%20spend%20latency"
```

## Runtime Files

Pairs are stored under:

```text
var/rosen-cortex/pairs/
var/rosen-cortex/latest-pair.json
```

Each pair records:

- namespace
- target files
- source digest
- risk families
- top Rosen bridges
- shared state digest
- pulse mode
- local/remote neuron role
- confidence

## Pulse Modes

- `pair_seed`: first time a pair is created.
- `state_replay`: digest unchanged; use the known state immediately.
- `correction_pulse`: digest changed; wake the route and update the mirror.

## Product Meaning

This is the bridge from "many agents" to "computer nervous system."

A billion possible neurons do not need to be billion processes. They can be
billion possible state nodes, most of them dormant, with real compute activated
only by state change.

