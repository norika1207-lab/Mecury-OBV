# Rosen Cortex Model

Neuron Mercury's next architecture is the Rosen Cortex Model: a software
acceleration runtime that folds task space instead of only making each step
faster.

The core idea is simple:

> speed is distance reduction.

Most AI systems try to accelerate by increasing model throughput, adding more
agents, or caching exact answers. Those help, but they hit a ceiling. The Rosen
Cortex treats software work as a navigable space made of intent, memory, code,
tools, models, risks, and prior outcomes. If that space can be mapped, Mercury
can build verified shortcuts through it.

Those shortcuts are Rosen bridges.

## Model Definition

Neuron Mercury is a Rosen Cortex system. It builds a large, self-correcting map
of bridgeable paths between a task's entry signals and useful exits. Neurons do
not all run at once. They are sparse probes that cross candidate bridges,
inspect the far side, and report whether the route should be reinforced,
demoted, closed, or escalated to a model.

```text
task entry
  -> entry sensing
  -> Rosen bridge candidate map
  -> memory.rosen_bridge_preload
  -> sparse neuron probes
  -> judge and coherence guards
  -> evidence packet / action
  -> bridge writeback
```

This is not ordinary cache. Cache says "I have seen this answer before." Rosen
Cortex says "I have seen enough nearby paths to move this new task closer to a
useful answer before expensive reasoning starts."

Rosen Pair Runtime adds the state-field version of that idea. Instead of
running every possible neuron, Mercury stores paired state neurons. The local
side mirrors a remote project sentinel by digest. If nothing changed, the pair
returns `state_replay`; if the remote state changed, it emits a
`correction_pulse`; if no pair exists, it starts with `pair_seed`. That turns
cold start from "discover everything now" into "react to the small state delta
that already happened."

## The Wormhole Map

The persistent map contains nodes and bridges.

### Nodes

```text
Entry Node    User intent, error text, symptom, command, repo state.
Memory Node   UMA/RAG page, owner rule, task lesson, benchmark trend.
Code Node     File, function, class, route, config, constant, CLI command.
Tool Node     rg, git, curl, test runner, profiler, local model endpoint.
Neuron Node   Retrieval, risk, speed, security, verify, synthesis, judge.
Model Node    Reflex, small local model, slow local model, frontier model.
Exit Node     Diagnosis, patch, evidence packet, report section, action.
Guard Node    Namespace isolation, freshness, risk, cost, destructive action.
```

### Bridges

Each bridge is a typed, scoreable route:

```json
{
  "from": "entry:provider-spend-leak",
  "to": "tool:cost-scan+code:anthropic-call-sites",
  "type": "accelerated_by",
  "confidence": 0.82,
  "latency_ms": 9,
  "cost": "low",
  "risk": "medium",
  "freshness": "valid",
  "hit_count": 12,
  "miss_count": 2,
  "last_verified": "2026-05-18T00:00:00.000Z",
  "activation_rule": "billing/api/provider/spend keywords + project namespace"
}
```

Bridge types include:

- `similar_to`
- `caused_by`
- `fixed_by`
- `verified_by`
- `accelerated_by`
- `blocked_by`
- `unsafe_if`
- `distilled_from`
- `expires_when`

## Sparse Scale

The long-term target can be one hundred million neurons, but not as one hundred
million live processes. In this model, most neurons are dormant functional
routes:

- entry signatures
- known failure patterns
- symbol links
- tool lessons
- benchmark lessons
- blocked routes
- model-distilled paths
- project-specific reflexes

At runtime, the control plane wakes only the few routes that matter.

```text
huge dormant map
  -> cheap candidate scoring
  -> top bridges only
  -> sparse probes
  -> expensive model call only if needed
```

This is the engineering translation of "one hundred million neurons": dormant
scale, active precision.

## First-Time Acceleration

Exact reflex cache accelerates the second time. Rosen Cortex targets the first
time.

It can accelerate a new task when the answer is not cached because the path may
still be known:

```text
new task
  -> similar entry signatures
  -> same project namespace
  -> same risk family
  -> known code symbols
  -> known tools
  -> known verification shape
  -> compressed evidence packet
```

The system does not pretend it already knows the answer. It knows where the
answer is likely to be.

## Relationship To 400B Models

The goal is not to copy a 400B model into a small computer. The goal is to keep
the paths a 400B model helped discover.

```text
frontier model solves one hard task
  -> extract entry signals
  -> extract useful evidence
  -> extract tool sequence
  -> extract mistakes and blocked paths
  -> write bridges into local map
  -> future local task starts near the answer
```

Mercury does not own all parameters. It owns reusable routes through past
experience.

## Control Plane

The Wormhole Control Plane has seven jobs:

1. Sense the entry: task, cwd, namespace, changed files, host pressure, model
   availability, spend risk, and destructive potential.
2. Generate candidate bridges from UMA, Code Cortex, task memory, reflex
   memory, score ledgers, and benchmark history.
3. Score candidates by confidence, freshness, latency, risk, cost, namespace
   fit, and expected evidence value.
4. Wake sparse neuron probes under a hard budget.
5. Judge probe results, remove duplicates, close false routes, and select the
   smallest useful evidence packet.
6. Choose action: deterministic answer, tool execution, patch plan, local
   model, or frontier escalation.
7. Write back bridge telemetry so the map improves.

The first CLI implementation is:

```bash
node src/mercury.js rosen-route "find hidden Anthropic billing loops and hot path latency" --json
node src/mercury.js rosen-pair pulse "watch src/mercury.js for UMA/RAG acceleration deltas"
node src/mercury.js rosen-proof-report
node src/mercury.js bench-rosen-bridge-route
node src/mercury.js bench-rosen-execute-plan
node src/mercury.js bench-rosen-pair-runtime
```

`rosen-route` creates an entry signature, generates family bridges, reads
task-memory routes, attaches UMA batch evidence, scores candidates, writes the
best bridges to `var/rosen-cortex/bridges/`, and returns a bounded probe plan.
`executePlan` now runs that route before UMA and neuron dispatch, then records a
`memory.rosen_bridge_preload` artifact with the selected bridges, risk families,
probe plan, guard, and elapsed Rosen time.

`rosen-proof-report` turns the current Rosen, cold-start, first-generation,
accelerate-task, and speed-state evidence into `docs/rosen-proof-report.html`
and `docs/rosen-proof-report.json`. Resident `GET /rosen-proof` returns the
same proof payload for local dashboards, and `bench-rosen-proof-report` guards
the artifact plus replay numbers in the resident control plane.

`monster-proof-report` applies the same standard to large-repo diagnosis. It
requires Rosen bridge selection, Code Cortex pages, UMA-backed
`monster-doctor` diagnosis, and a verified `accelerate-task` replay. Resident
`GET /monster-proof` exposes that packet for dashboards and night-runner
verification, while `docs/monster-proof-report.html` gives the same evidence a
browser-readable proof page.

Bridge selection is allowed to wake dormant neurons. A provider-spend bridge can
boost cost, provider, risk, judge, and safety neurons; a local-LLM bridge can
boost provider cache, model avoidance, slow-worker, and distillation neurons.
The resource guard still caps execution, so the map can grow while hot paths
remain sparse.

## Guardrails

Fast wrong routes are worse than slow honest routes. Every bridge must pass
guards:

- Project namespace isolation: self memory cannot pollute Lobster or AFU.
- Coherence: file mtime/size/hash changes invalidate stale code bridges.
- Budget: bridge probing must not block hot paths.
- Risk: destructive, billing, credential, security, deploy, and database tasks
  require stricter verification.
- Demotion: bridges that miss, get stale, or slow the path must lose priority.
- Judge checkpoint: no broad neuron swarm may write unbounded blackboard noise.
- Night runner: the unattended loop includes both Rosen route and Rosen
  execute-plan benches so bridge integration cannot quietly disappear.
- `bench-rosen-neuron-boost`: verifies that bridges can wake dormant relevant
  neurons without full overactivation.

## Benchmark Shift

The old benchmark question was:

```text
How fast is a cache hit?
```

The Rosen Cortex benchmark question is:

```text
How much work did Mercury avoid before the first expensive model call?
```

Useful measurements:

- cold task to first evidence packet
- candidate bridges scored per millisecond
- top bridge precision
- model calls avoided
- context tokens avoided
- wrong bridge close rate
- bridge reinforcement rate
- project pollution failures
- first-generation wall-clock improvement
- executable-plan preload presence and Rosen route latency

The dashboard must clearly separate:

- exact replay cache
- semantic/reflex reuse
- Rosen bridge route reuse
- real cold-start generation

`speed-state` and `nervous-system` make Rosen observable by reporting bridge
count, latest selected route count, latest route latency, and readiness. This
keeps the bridge map visible as part of Mercury's memory/synapse layer instead
of hiding it as an internal optimization.

## Product Sentence

Neuron Mercury builds a Rosen Cortex inside the computer: a self-correcting map
of software-space bridges that turns experience into routes, routes into
reflexes, and reflexes into felt speed.
