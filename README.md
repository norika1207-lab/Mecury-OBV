# Neuron Mercury

Neuron Mercury is a local-computer acceleration project. Its purpose is not to
make a pretty demo, not to rename cache as intelligence, and not to report a
small first packet as if it were a complete answer. Its purpose is to make a
computer, local software, and local language models feel measurably faster.

The product target is simple:

```text
Same machine.
Same model.
Same prompt.
Same answer length.
Comparable quality.
Neuron Mercury must return the complete useful answer faster.
```

If a result does not satisfy that test, it must not be called complete
generation acceleration.

## Current Truth

The current system has useful pieces, but it is not yet the finished accelerator.
This distinction is mandatory.

What exists:

- A 3000-neuron external catalog on the laptop.
- Per-neuron placement files that list each neuron's lane, substrate, phase, and
  source path.
- A concurrent-control bench proving that a runtime can read the 3000 catalog
  and select bounded work.
- UMA/RAG, cache, resident, first-packet, routing, and deployment-proof
  artifacts.

What does not yet exist:

- The 3000 neurons are not inside Qwen weights.
- The 3000 neurons are not LoRA weights.
- The 3000 neurons are not modified GGUF tensors.
- The 3000 neurons are not vLLM/Ollama kernel hooks.
- The 3000 neurons do not yet produce same-length full answers faster than the
  base local model.
- First-packet hints are not full-answer acceleration.

This README is therefore the corrective specification: what Neuron Mercury must
become, how it must operate, and what must be proven before it is shown as a
real accelerator.

## Deployed Laptop Paths

The 3000-neuron deployment currently exists on the Windows laptop in two repo
locations:

```text
/home/norika/Neuron-Mercury
/mnt/c/Users/norik/Neuron-Mercury
```

Required files:

```text
src/neurons.json
var/bench/neuron-concurrent-control-3000.json
var/bench/neuron-positions-3000.json
var/neuron-positions/neuron-positions-3000.csv
var/neuron-positions/neuron-positions-3000.json
docs/neuron-positions-3000.html
var/deployment-proof/mercury-3000-deployment-proof.json
docs/mercury-3000-deployment-proof.json
```

Verification command on the laptop:

```bash
cd /home/norika/Neuron-Mercury
node src/mercury.js bench-neuron-concurrent-control-3000
python3 - <<'PY'
import json
for path in [
  "src/neurons.json",
  "var/neuron-positions/neuron-positions-3000.json",
  "var/bench/neuron-concurrent-control-3000.json",
]:
  with open(path, encoding="utf-8") as f:
    data = json.load(f)
  print(path, len(data) if isinstance(data, list) else data.get("catalog_neurons"), data.get("pass") if isinstance(data, dict) else "")
PY
```

Expected:

```text
src/neurons.json 3000
var/neuron-positions/neuron-positions-3000.json 3000
var/bench/neuron-concurrent-control-3000.json 3000 True
```

## The Core Idea

Neuron Mercury treats a computer as a body that can grow a nervous system.

The CPU, GPU, memory, disk, filesystem, model runtime, project files, local LLM,
RAG store, and user workflow are not separate tools. They are organs and
surfaces in one local nervous system.

The accelerator is the nervous layer between them:

```text
User intention
  -> state field
  -> twin entanglement pairs
  -> Rosen bridge route map
  -> UMA/RAG memory
  -> 3000-neuron placement field
  -> model boundary control
  -> complete answer synthesis
  -> verification
  -> writeback memory
```

The goal is not to run every neuron as a process. The goal is to maintain a
large state field where every neuron has position, state, responsibility, and
observable changes. Execution is the final collapse, not the whole system.

## Definitions

### Neuron

A Mercury neuron is a stateful responsibility unit. It must have:

- `id`
- `type`
- `cluster`
- `lane`
- `dispatch_phase`
- `substrate`
- `shard_family`
- activation terms
- entanglement edges
- current state
- last observation time
- last usefulness score
- failure score
- promotion/demotion state

A neuron is not valid if it is only a name in a JSON file and never participates
in runtime state.

### State Field

The state field is the living layer that tracks all neurons even when they are
not performing heavy work.

Every neuron must be able to hold one of these states:

```text
dormant
warming
observing
excited
critical
collapsed
cooling
demoted
failed
```

The state field is how Neuron Mercury avoids the false choice between "run all
3000 neurons" and "only use 20 neurons." All 3000 can be observed and updated,
while only the needed subset executes expensive work.

### Twin Entanglement

Twin entanglement is not quantum physics inside the machine. It is a software
contract:

```text
local_neuron.state <-> remote_or_target_surface.state
```

A twin pair binds one Mercury neuron to one external state source:

- a file digest
- a model metadata page
- a KV cache prefix slot
- a prompt prefix
- a UMA page
- a GPU pressure reading
- a resident endpoint
- a RAG namespace
- a benchmark lane
- a process queue
- a local LLM model route

When the target changes, the paired neuron changes. When the paired neuron is
observed, the controller knows whether the target surface is still stable,
stale, hot, cold, risky, or ready.

This is the practical meaning of "observing the other side." It does not claim
zero-latency physics. It means state is pre-bound so the controller does not
start from ignorance.

### Rosen Bridge

A Rosen bridge is a verified shortcut between a task entrance and a useful exit.

It is not a cache hit. A cache hit says:

```text
I have seen this exact answer.
```

A Rosen bridge says:

```text
This new task is near a known route.
Start from the right memory, model boundary, file, neuron set, and evidence.
```

A Rosen bridge must store:

- entrance signature
- exit target
- required evidence
- likely neuron clusters
- model boundary anchors
- UMA/RAG pages
- risk guards
- expected latency
- confidence
- last success
- last failure
- invalidation conditions

### Universe Rosen Bridge Map

The Universe Rosen Bridge Map is the global topology:

```text
project namespaces
  -> UMA pages
  -> code cortex symbols
  -> model boundary anchors
  -> twin pairs
  -> neuron field
  -> hardware substrates
  -> benchmark lanes
  -> user workflows
```

It is the map of all known shortcuts and state-pair bindings. It is not a
presentation page. It must be read by the runtime.

## The 3000-Neuron Placement Model

The current 3000 catalog is divided by cluster:

```text
retrieval: 592
risk: 496
synthesis: 464
judge: 444
memory: 400
decompose: 368
accelerate: 235
evidence: 1
```

It is placed across substrates:

```text
model.inference_boundary: 625
cpu.l1_hot_path: 530
cpu.reflex_uma_edge: 500
memory.cache: 233
cpu.vector_scan: 226
cpu.process_pool: 193
gpu.boundary_probe: 125
memory.hot_pages: 125
resident.reflex_cache: 125
scheduler.nano_cortex: 125
uma.hot_memory: 125
disk.append_log: 35
gpu.nvidia_or_cpu_simd: 33
```

This placement is not enough by itself. The next runtime must make each row
observable:

```text
src/neurons.json row
  -> var/neuron-positions row
  -> state-field entry
  -> twin-pair binding when possible
  -> route score
  -> hot/cold/critical status
  -> writeback score
```

## What "Deployment" Means

Deployment is not copying a JSON file.

Deployment means all of the following are true:

1. The catalog exists on the target machine.
2. The runtime reads the catalog.
3. Each neuron has a placement record.
4. Each neuron has a state record.
5. Each neuron is visible through a status command or endpoint.
6. The scheduler can route to the neuron.
7. The neuron can be promoted, demoted, or invalidated.
8. The neuron has evidence of use or non-use.
9. The benchmark proves the runtime used the deployed catalog.
10. The accelerator result is measured against a fair baseline.

Anything less is staging, not deployment.

## What "Acceleration" Means

Acceleration has strict levels.

### Level 0: Not Acceleration

These do not count:

- returning a shorter answer
- returning only a first packet and comparing it to a full answer
- showing a server-side packet time while browser-visible time is slow
- using cache replay as if it were cold-start generation
- reporting a pretty benchmark without equal quality and length
- saying neurons are inside a model when they are outside

### Level 1: Routing Acceleration

The system finds the right files, memory, route, and evidence faster than a
generic agent loop.

Valid metric:

```text
same repo task
same search budget
Mercury identifies target files or risk family faster
```

### Level 2: First Useful Packet

The system gives an early useful preview before full generation completes.

Valid label:

```text
first useful packet
```

Invalid label:

```text
complete answer acceleration
```

### Level 3: Complete Answer Acceleration

The system produces a complete answer faster.

Required metric:

```text
same prompt
same model or clearly declared model route
same target length
same minimum quality score
Mercury wall-clock time < baseline wall-clock time
```

This is the product threshold.

### Level 4: Model-Internal Acceleration

The system changes the model runtime path itself through one or more of:

- KV cache priming
- prompt prefix tuning
- speculative decoding
- draft model
- LoRA adapter
- GGUF sidecar index
- vLLM/Ollama runtime hook
- token planning
- batched decode path

Only this level may use language like "inside the model."

## Required Runtime Architecture

```text
mercury resident
  -> /state-field
  -> /neuron/:id
  -> /neuron-positions
  -> /rosen-map
  -> /twin-pairs
  -> /llm/full-race
  -> /llm/first-packet
  -> /llm/final-merge
  -> /bench/fair-race
```

### State Field Runtime

The runtime must maintain:

```json
{
  "id": "accelerate.local_llm_route_v7",
  "state": "observing",
  "position": {
    "lane": "acceleration_lane",
    "substrate": "model.inference_boundary",
    "dispatch_phase": 1
  },
  "twin": {
    "kind": "model_boundary",
    "target": "qwen2.5:7b:gguf:layer_map",
    "digest": "..."
  },
  "score": {
    "usefulness": 0,
    "latency_saved_ms": 0,
    "false_positive": 0
  }
}
```

### Twin Pair Runtime

Twin pairs must be generated for:

- project file pages
- UMA pages
- model metadata pages
- tokenizer anchors
- prompt prefixes
- local LLM model routes
- GPU/CPU pressure
- resident cache entries
- benchmark lanes

Each pair must support:

```text
seed
pulse
observe
changed?
collapse
writeback
```

### Rosen Bridge Runtime

Rosen bridges must be promoted only after measured success.

Promotion requires:

- at least one task success
- a saved route
- evidence packet
- latency measurement
- invalidation rule
- no namespace pollution

Demotion occurs when:

- answer quality fails
- route becomes stale
- file digest changes
- model changes
- project namespace changes
- benchmark regresses

## LLM Acceleration Plan

The next product-critical work is full local LLM acceleration on the RTX 3060
laptop.

### Stage 1: Fair Race Harness

Build a harness that runs:

```text
baseline: Ollama direct qwen2.5:7b
mercury: same qwen2.5:7b plus allowed Mercury acceleration path
```

Required output:

```text
wall_clock_ms
chars
tokens
chars_per_second
quality_score
same_length_ratio
pass/fail
```

Fail if:

```text
Mercury chars < baseline chars * 0.8
quality_score < baseline quality_score * 0.9
Mercury answer is only first packet
```

### Stage 2: KV Cache Priming

Build model-boundary neurons that warm:

- system prompt prefix
- frequent instruction patterns
- task schema
- UMA evidence headers
- summary templates
- tokenizer phrase anchors

The goal is to reduce first-token and early-token latency without pretending the
model was fully changed.

### Stage 3: Speculative Draft Path

Use a smaller or deterministic Mercury draft path to generate a candidate
outline while Qwen produces the full answer.

Valid acceleration:

```text
draft guides full answer
full answer reaches same length faster
```

Invalid acceleration:

```text
draft replaces full answer while being much shorter
```

### Stage 4: Full Merge

The final answer must merge:

- Mercury fast packet
- Qwen full generation
- UMA/RAG evidence
- judge corrections
- length/quality guard

The visible result must be complete, not a placeholder.

### Stage 5: Model-Internal Research Path

To truly "enter the model," implement one of:

- LoRA adapter training from Mercury memory
- vLLM plugin for prefix/KV reuse
- Ollama wrapper with persistent context sessions
- GGUF sidecar tensor/metadata map
- speculative decoding with draft model
- tokenizer-anchor routing

Until one exists, the system must say "model boundary," not "inside model."

## 3000-Neuron Runtime Plan

### Phase A: Placement Complete

Status: partially complete.

Required files:

```text
src/neurons.json
var/neuron-positions/neuron-positions-3000.csv
var/neuron-positions/neuron-positions-3000.json
docs/neuron-positions-3000.html
```

### Phase B: State Complete

Required next files:

```text
var/state-field/neuron-state-3000.json
var/state-field/neuron-state-3000.jsonl
var/bench/neuron-state-3000.json
```

Each neuron must have a current state. This proves the catalog is not dead.

### Phase C: Twin Complete

Required next files:

```text
var/twin-pairs/twin-pairs-3000.json
var/bench/twin-pairs-3000.json
```

Each neuron should be bound to a target surface where possible. If no target
exists, the reason must be explicit.

### Phase D: Collective Pulse

Required command:

```bash
node src/mercury.js pulse-neurons-3000 --task "accelerate local qwen full answer"
```

Expected:

```text
3000 observed
N warmed
N excited
N critical
N collapsed
N demoted
elapsed_ms
```

This is how Mercury proves it is not still using only the old 20-neuron route.

### Phase E: Collapse To Execution

After all 3000 update state, the controller may collapse to a smaller execution
set. But the report must distinguish:

```text
observed_neurons: 3000
state_updated_neurons: 3000
executed_heavy_neurons: 22-200
```

The old mistake was reporting only `executed_heavy_neurons` and implying the
whole brain was active.

## Anti-Deception Rules

The system must never claim:

- "deployed" unless the target machine has files and runtime verification
- "inside model" unless model weights/runtime/KV/prefix path is actually changed
- "complete answer acceleration" unless same-length quality race passes
- "3000 active neurons" unless all 3000 have state updates
- "night runner progress" unless artifacts changed and pass/fail is recorded
- "investor-ready" unless failure cases are visible

Every claim must point to a file, command, or measured artifact.

## Product Demo Rules

The demo must have three lanes:

```text
Lane 1: baseline full answer
Lane 2: Mercury first packet
Lane 3: Mercury full answer
```

Only Lane 3 may compete with Lane 1 for complete-generation speed.

The page must show:

```text
model
prompt
wall-clock time
server time
first token/packet time
full answer time
chars
chars/sec
quality score
same-length pass/fail
status
```

If Lane 2 is fast but Lane 3 is not, the product has not proven full LLM
acceleration.

## One-Day Rescue Plan

The immediate rescue sequence is:

1. Freeze all marketing pages.
2. Keep only the honest local race page.
3. Build state-field runtime for all 3000 neurons.
4. Build twin-pair binding for model, UMA, file, cache, and GPU surfaces.
5. Build fair full-answer race.
6. Add quality/length gate.
7. Implement one real local-model acceleration method:
   - persistent Ollama context reuse, or
   - KV/prefix priming, or
   - speculative draft model, or
   - LoRA sidecar plan.
8. Re-run on laptop.
9. Publish only what passes.

## Success Criteria

Neuron Mercury becomes real only when this command passes:

```bash
node src/mercury.js bench-full-answer-acceleration \
  --model=qwen2.5:7b \
  --prompt-file=tasks/hard-product-engineering-prompt.txt \
  --min-length-ratio=0.8 \
  --min-quality-ratio=0.9
```

Required pass:

```text
baseline_full_ms > mercury_full_ms
mercury_chars >= baseline_chars * 0.8
mercury_quality >= baseline_quality * 0.9
first_packet_ms reported separately
all 3000 neurons state-updated
```

Until then, Neuron Mercury is an experimental nervous-system runtime, not a
finished local LLM accelerator.

