# Windows WSL Qwen Node

This node is a local hardware substrate for Neuron Mercury.

## Observed Hardware

- Host: `LAPTOP-T7B5N79C`
- OS: Windows 11
- CPU: Intel Core i7-12700H, 20 logical processors
- RAM: 16GB
- GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6GB VRAM
- WSL distro: Ubuntu

## Local LLM Substrate

- Runtime: Ollama inside WSL
- Binary: `/home/norika/local-llm/ollama/bin/ollama`
- Model dir: `/home/norika/.ollama/models`
- Model: `qwen2.5:3b`
- Format: GGUF
- Quantization: `Q4_K_M`
- Parameter size: 3.1B
- Model size: about 1.93GB
- Context: 4096
- vLLM: not installed
- `torch` / `transformers`: not installed

## Safe Startup

Keep Ollama local to WSL unless an explicit network exposure decision is made.
Do not enable Tailscale serve by default.

```bash
mkdir -p /home/norika/local-llm/logs /home/norika/.ollama/models
OLLAMA_HOST=127.0.0.1:11434 \
OLLAMA_MODELS=/home/norika/.ollama/models \
OLLAMA_KEEP_ALIVE=30m \
nohup /home/norika/local-llm/ollama/bin/ollama serve \
  >> /home/norika/local-llm/logs/ollama.log 2>&1 &
```

Probe from WSL:

```bash
cd /home/norika/Neuron-Mercury
node src/mercury.js llm-probe --url=http://127.0.0.1:11434 --model=qwen2.5:3b
```

## Reflex Tests

Slow path, pay model once:

```bash
node src/mercury.js llm-fast \
  --url=http://127.0.0.1:11434 \
  --model=qwen2.5:3b \
  --intent=health.ping \
  --prompt=ping \
  --refresh
```

Hot path, same intent with different prompt:

```bash
node src/mercury.js llm-fast \
  --url=http://127.0.0.1:11434 \
  --model=qwen2.5:3b \
  --intent=health.ping \
  --prompt=please-answer-health-ping
```

Seeded reflex, no model call:

```bash
node src/mercury.js llm-fast \
  --url=http://127.0.0.1:11434 \
  --model=qwen2.5:3b \
  --intent=seeded.health \
  --prompt=ping \
  --seed-response=pong
```

Cache health:

```bash
node src/mercury.js llm-cache stats --limit=12
node src/mercury.js llm-cache prune --max-files=256
```

Host speed profile:

```bash
node src/mercury.js host-speed --ollama-url=http://127.0.0.1:11434
node src/mercury.js runtime-detect
node src/mercury.js speed-state --full
node src/mercury.js bench-runtime-route
node src/mercury.js bench-slow-provider-hint
node src/mercury.js bench-slow-worker-provider-gate
```

Use this before changing anything. It is read-only and reports CPU, RAM, disk,
GPU, Ollama, reflex cache, top process pressure, and available acceleration
providers. On the NVIDIA laptop, the useful signal is not only "GPU exists"; it
is whether the actual runtime path can use CUDA/vLLM/SGLang/TensorRT-LLM,
Ollama, or another local backend without touching the user-facing hot path.
Mercury probes WSL in one pass for both NVIDIA visibility and the local Qwer
Ollama binary, then routes Qwer to slow-path distillation rather than direct
user-facing generation.

After `runtime-detect`, cache misses only read the saved profile and attach a
`provider_hint` to the slow job. That is the practical acceleration rule for
this laptop: no WSL cold start, no Qwer call, and no GPU probe on the hot path.

Prepare game-friendly reflex mode:

```bash
node src/mercury.js game-mode --prepare
```

This only writes Mercury reflex cache entries. It does not close apps, change
Windows settings, change GPU settings, or expose network services. During game
time, Qwen should stay off the hot path; use reflex/cache answers first.

Serve local reflexes over HTTP:

```bash
node src/mercury.js reflex-serve --host=127.0.0.1 --port=17345 --enqueue-miss
```

Routes:

```text
GET  /health
GET  /stats
GET  /reflex?intent=game.status&prompt=hello&model=game-mode
POST /reflex {"intent":"game.status","prompt":"hello","model":"game-mode"}
POST /seed {"intent":"game.tip","prompt":"fps low","response":"Keep Qwen off the hot path and use reflex/cache first.","model":"game-mode"}
POST /seed-batch {"items":[{"intent":"game.tip.1","prompt":"fps low","response":"Stay in reflex mode.","model":"game-mode"}]}
POST /reflex-batch {"items":[{"intent":"game.tip.1","prompt":"anything","model":"game-mode"}]}
```

This server is cache/reflex only. It does not call Qwen, does not run repo
scans, and should be safe to keep on during games.

HTTP seed test:

```bash
curl -s -X POST http://127.0.0.1:17345/seed \
  -H 'content-type: application/json' \
  -d '{"intent":"game.tip","prompt":"fps low","response":"Keep Qwen off the hot path and use reflex/cache first.","model":"game-mode"}'

curl -s 'http://127.0.0.1:17345/reflex?intent=game.tip&prompt=anything&model=game-mode'
```

Batch reflex test:

```bash
curl -s -X POST http://127.0.0.1:17345/seed-batch \
  -H 'content-type: application/json' \
  -d '{"items":[{"intent":"game.tip.1","prompt":"fps low","response":"Stay in reflex mode.","model":"game-mode"},{"intent":"game.tip.2","prompt":"lag spike","response":"Defer broad scans until after play.","model":"game-mode"}]}'

curl -s -X POST http://127.0.0.1:17345/reflex-batch \
  -H 'content-type: application/json' \
  -d '{"items":[{"intent":"game.tip.1","prompt":"anything","model":"game-mode"},{"intent":"game.tip.2","prompt":"anything","model":"game-mode"}]}'
```

Miss queue test:

```bash
curl -s 'http://127.0.0.1:17345/reflex?intent=unknown.game.tip&prompt=unknown&model=game-mode&enqueue=1'
node src/mercury.js slow-jobs list --limit=8
node src/mercury.js slow-worker --limit=1 --seed-response="Use reflex/cache first; local model refinement can run later."
```

The listed job should show `provider_hint.route=qwer_ollama_distill_once` when
the Windows/WSL Qwer profile is warm.

If that route is missing, the slow worker should defer the miss instead of
burning time on an unavailable model path.

## Measured Behavior

- Raw tiny generation after runner load: about 5.5s.
- Warm `llm-fast --refresh`: hundreds of ms to a few seconds, depending on
  runner state.
- Intent cache hit: 0-1ms on observed runs.
- Seeded reflex write: single-digit ms on observed runs.
- Seeded reflex cache hit: 0-1ms on observed runs.

## Rule

The local model is not allowed into the hot path directly. It may generate,
grade, or synthesize on a slow path, but the accelerated user-facing path should
prefer seeded reflexes, intent cache hits, deterministic retrieval, and CPU
kernels before invoking Qwen.

Semantic cache is also gated. Low-risk speed/status prompts may reuse semantic
reflexes. Admin, billing, destructive, production, database, deployment,
permission, or secret-like prompts bypass semantic reuse and enter the slow job
queue instead.
