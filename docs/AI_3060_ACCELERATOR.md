# Neuron Mercury AI 3060 Accelerator

This branch is not a Windows cleaner, registry tool, RAM cleaner, or game
booster. Its target is local AI workload acceleration on the RTX 3060 laptop.

## Product Boundary

Neuron Mercury should make local AI work feel faster by reducing repeated model
waiting, keeping the right model state warm, and replaying already-distilled
work. It must not claim general computer acceleration from closing user apps,
deleting files, or changing system settings.

Counted acceleration:

- same-prompt full-answer race against direct Ollama
- warm-model full answer after Mercury prewarm
- replay of a previously distilled full answer
- low-impact scheduling that avoids GPU contention during games

Not counted:

- first packet only
- shorter placeholder answers
- registry cleanup
- RAM cleanup
- closing unrelated user programs

## First Honest Race

Run on the Windows/WSL laptop where Ollama is available:

```bash
cd /home/norika/Neuron-Mercury
node src/mercury.js ai-accelerator prepare --model=qwen2.5:7b --low-impact
node src/mercury.js bench-ai-3060-accelerator \
  --model=qwen2.5:7b \
  --num-predict=256 \
  --target-warm-speedup=1.25
```

Output artifact:

```text
var/bench/ai-3060-accelerator-race.json
docs/ai-3060-accelerator-race.json
```

The race records:

- direct Ollama full answer
- Mercury prewarm
- Mercury warm full answer
- Mercury replay after distillation
- length ratio
- heuristic quality ratio
- warm speedup
- replay speedup

## Pass Rule

The warm full-answer lane passes only if:

```text
mercury_chars >= baseline_chars * 0.8
mercury_quality >= baseline_quality * 0.9
baseline_ms / mercury_ms >= 1.25
```

Replay is reported separately. Replay can prove useful AI workflow
acceleration, but it is not a claim that the model generated new tokens faster.

## Daily Tool Commands

Prepare after boot:

```bash
node src/mercury.js ai-accelerator prepare --model=qwen2.5:7b --low-impact
```

Check readiness:

```bash
node src/mercury.js ai-accelerator status
```

Select the fastest acceptable local model for the current machine state:

```bash
node src/mercury.js ai-accelerator select \
  --models=qwen2.5:7b,deepseek-r1:8b,qwen2.5:3b \
  --teacher-models=qwen3:14b,deepseek-r1:14b,qwen3:30b \
  --num-predict=96
```

Prepare the larger teacher model after installing it:

```bash
ollama pull qwen3:14b
node src/mercury.js ai-accelerator teacher-prepare \
  --model=auto \
  --teacher-model=qwen3:14b
```

Distill a hard answer once with the teacher, then replay it through the hot
model cache/reflex path:

```bash
node src/mercury.js ai-accelerator teacher-distill \
  --model=auto \
  --teacher-model=auto \
  --intent=work.hard.answer \
  --prompt="請解決這個較難的問題，並給出可重用答案"
```

Let the teacher model process queued instant misses in the background:

```bash
node src/mercury.js ai-accelerator teacher-worker \
  --teacher-model=auto \
  --limit=4
```

Probe whether a new, different prompt can reuse a distilled problem-family
recipe instead of exact prompt cache:

```bash
node src/mercury.js ai-accelerator family-probe \
  --model=auto \
  --prompt="我的本地模型很慢但問題跟上次不一樣，先判斷該怎麼加速"
```

Inspect learned family recipes:

```bash
node src/mercury.js ai-accelerator family-status --model=auto
```

Seed distilled domain packs for broad knowledge routing:

```bash
node src/mercury.js ai-accelerator domain-prepare --model=auto
```

Probe whether a never-seen question can hit a broad domain pack:

```bash
node src/mercury.js ai-accelerator domain-probe \
  --model=auto \
  --prompt="我想知道地震和板塊運動的關係，先給我地球科學框架"
```

Inspect available domain packs:

```bash
node src/mercury.js ai-accelerator domain-status --model=auto
```

Seed and probe Lobster-specific packs:

```bash
npm run ai3060:lobster-prepare
npm run ai3060:lobster-probe
```

Measure the real token aperture for this model and machine:

```bash
node src/mercury.js ai-accelerator token-frontier \
  --model=auto \
  --predicts=32,64 \
  --parallel=1,2
```

Run a multi-prompt race using the selected model:

```bash
node src/mercury.js ai-accelerator suite --model=auto --num-predict=128
```

Return a useful first answer in the millisecond lane:

```bash
node src/mercury.js ai-accelerator instant \
  --model=auto \
  --intent=ai3060.instant.demo \
  --prompt="請用神經元和羅森橋說明如何讓本地 AI 回覆接近毫秒級"
```

Measure the instant lane across several prompts:

```bash
node src/mercury.js ai-accelerator instant-suite --model=auto --limit=5
```

Answer from cache/reflex if possible, queue unknown work instead of blocking:

```bash
node src/mercury.js ai-accelerator answer \
  --model=qwen2.5:7b \
  --intent=work.summary \
  --prompt="請摘要這個專案目前的 AI 加速狀態"
```

Force a local model refresh and distill the full answer into replay cache:

```bash
node src/mercury.js ai-accelerator answer \
  --model=qwen2.5:7b \
  --intent=work.summary \
  --prompt="請摘要這個專案目前的 AI 加速狀態" \
  --refresh
```

## Millisecond Lane

The `instant` path is the aggressive path for perceived speed:

- exact cache first
- exact reflex match second, when `--reflex` is explicitly enabled
- small semantic reflex match only when `--semantic` is explicitly enabled
- Rosen/UMA scaffold third
- teacher model completion queued outside the hot path

This is the closest honest version of "millisecond answers." It does not make a
new Qwen generation finish in milliseconds. It makes the first useful response
arrive in milliseconds, then lets the slower model path refine or replace it for
future replay.

On the RTX 3060 WSL path, a fresh unknown prompt returned a Rosen scaffold in
83ms total, then exact replay of the same prompt returned in 1ms. A five-prompt
instant suite with warm exact cache averaged 0.2ms.

Output artifact:

```text
var/bench/ai-3060-instant-suite.json
docs/ai-3060-instant-suite.json
```

## Teacher Model Lane

The recommended larger model is `qwen3:14b`. Mercury treats it as a teacher,
not as the always-on hot path:

- hot path: `qwen2.5:7b`, `deepseek-r1:8b`, or whichever model wins `select`
- teacher path: `qwen3:14b` by default
- slow path: teacher generates or refines one answer
- distill path: teacher answer is written to hot cache, local reflex memory, and a problem-family recipe
- replay path: same or matching task family returns a reusable reasoning route in milliseconds

`qwen3:30b` can be tested as an experimental teacher, but it should not be the
default hot path on the RTX 3060 laptop.

The family recipe layer is the non-trivial part: it stores reusable reasoning
steps, risk families, Rosen bridges, and activation tokens. A later prompt does
not need to be the same sentence. It only needs to match the same problem family
strongly enough to reuse the route while the teacher handles uncertain details
in the background.

## Domain Pack Lane

Domain packs are the next layer above family recipes. They are small distilled
maps for broad areas such as business, legal language, medical triage,
education, earth science, physics, psychology/behavior/social science,
philosophy, and local AI acceleration.

Lobster has dedicated packs because it is mostly background diagnosis rather
than front-stage chat:

- `lobster_latency`: hot-path, queue, retry, timeout, worker diagnosis
- `lobster_db_bloat`: final-summary storage, retention, DB growth control
- `lobster_provider_spend`: paid-provider/API-key/billing loop guard
- `lobster_file_search`: file-first evidence packets before LLM calls
- `lobster_error_log`: stack trace, incident, root-cause candidate triage

They are intentionally not raw book or paper dumps. The pack stores activation
tokens, common intents, answer frames, and risk gates. Full copyrighted
textbooks, paid papers, and licensed course material should not be copied into
the runtime unless the user owns or licenses them. Mercury should store
distilled maps, citations, and pointers, then let the teacher model synthesize
details in the slow path.

Default hot-path order:

- exact cache
- optional reflex or semantic reflex when explicitly enabled
- distilled family recipe
- distilled domain pack
- Rosen/UMA instant scaffold
- teacher slow-path completion

Lobster prompts are treated as a special case: Lobster domain packs are checked
before generic family recipes so operational diagnosis does not get swallowed by
a broader chat recipe.

This means a first-time question about plate tectonics, contract clauses,
medical terminology, physics formulas, or philosophy can still get an immediate
framework without pretending that a 14B model generated a fresh full answer in
milliseconds.

For Lobster, the intended model split is:

- hot path: Mercury packs, file indexes, UMA/Rosen routes, and `qwen2.5:7b`
- background teacher: `qwen3:14b`
- not recommended on this laptop: `qwen3:30b`, because it needs about 17.6GiB
  total memory and pushed WSL into swap/not-responding on the 16GB RAM laptop

Local verification for the current seed pack set: domain preparation wrote 14
packs in 10ms, a Lobster diagnostic probe hit `lobster_db_bloat` in 6ms, and
the full `instant` path hit `ai_accelerator_instant_lobster_domain_pack_hit` in
7ms while enqueueing `qwen3:14b` for slow-path completion.

Output artifacts:

```text
var/bench/ai-3060-domain-status.json
docs/ai-3060-domain-status.json
var/bench/ai-3060-domain-probe.json
docs/ai-3060-domain-probe.json
var/product/ai-domain-packs/pack_*.json
```

## Token Frontier Lane

The token frontier lane is the honest version of "open the token output." It
does not claim unlimited generation. It measures how far the current model can
be pushed on this machine before latency and concurrency become bad.

It records:

- single-request tokens/sec across several `num_predict` values
- aggregate tokens/sec under limited parallel requests
- max and average latency for the parallel edge
- the recommended direct-generation concurrency limit

This matters for multi-user use. If 20 people ask questions, search files,
summarize documents, and identify images at the same time, Mercury should not
send all work to one model lane. The token frontier tells the router how many
direct generations are safe, then excess work is routed to cache, domain packs,
family recipes, file indexes, vision queues, or teacher slow path.

Output artifacts:

```text
var/bench/ai-3060-token-frontier.json
docs/ai-3060-token-frontier.json
```

Output artifacts:

```text
var/bench/ai-3060-teacher-prepare.json
docs/ai-3060-teacher-prepare.json
var/bench/ai-3060-teacher-distill.json
docs/ai-3060-teacher-distill.json
var/bench/ai-3060-family-probe.json
docs/ai-3060-family-probe.json
var/bench/ai-3060-family-status.json
docs/ai-3060-family-status.json
var/product/ai-family-recipes/recipe_*.json
```

RTX 3060 WSL verification with `qwen3:14b`:

- install: `ollama pull qwen3:14b`
- teacher prepare warmup: 30414ms
- teacher distill: 110712ms for one reusable answer
- instant replay of the distilled answer: 1ms
- answer replay of the distilled answer: 0ms
- different-prompt family probe: 5ms, matched `local_llm_speed`
- different-prompt instant family route: 85ms total, family lookup 5ms
