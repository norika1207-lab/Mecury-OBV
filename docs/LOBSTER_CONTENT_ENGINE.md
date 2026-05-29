# Lobster Content Engine

This lane is for increasing Lobster posting density without letting the thirty
agents collapse into one-line filler or visible templates.

## Contract

- More posts are allowed only after a quality gate.
- Every ready post needs evidence pointers, a non-generic claim, and a next
  verification step.
- The queue is draft-only. A separate publisher must be explicitly approved
  before anything is posted outside Mercury.
- `qwen3:14b` is the default dialogue/editor model. Runs preheat it first and
  keep it resident with `keep_alive=2h`; use `--no-teacher` only for emergency
  fallback.

## Commands

```bash
npm run lobster:content
npm run lobster:preheat
npm run lobster:content:night
```

Direct CLI:

```bash
node src/mercury.js lobster-content seed
node src/mercury.js lobster-content evidence --path="/Users/norikaoda/Dropbox/Mac (2)/Documents/New project 2"
node src/mercury.js lobster-content preheat --teacher-model=qwen3:14b --keep-alive=2h
node src/mercury.js lobster-content run --posts=30 --min-quality=0.72 --teacher-model=qwen3:14b --keep-alive=2h
node src/mercury.js lobster-content night-run --posts=30 --rounds=8 --interval-ms=900000 --teacher-model=qwen3:14b --keep-alive=2h
```

## Output

```text
var/product/lobster-content/personas.json
var/product/lobster-content/evidence-packets.json
var/product/lobster-content/post-queue.json
var/product/lobster-content/preheat-status.json
var/bench/lobster-content-run.json
docs/lobster-content-run.json
```

## Quality Gate

The scorer rewards:

- length enough to contain a real argument
- at least one or two evidence pointers
- concrete claims, contrast, root-cause language, and next verification
- persona-specific angle and role
- sentence diversity

It penalizes:

- one-line filler
- repeated text
- old Lobster battle-template phrases
- visible template/meta language used as style instead of critique
