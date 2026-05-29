# Mercury 300 Alpha

Mercury 300 is not a benchmark dashboard, a model atlas, or a consulting report.

It is a small creative power pack:

```text
300MB. No subscription. Better writing on your own computer.
```

The alpha target is deliberately narrow:

```text
Make a local 7B model write closer to a 30B teacher on everyday creative work:
plans, proposals, presentation copy, founder notes, product narratives, and
long-form opinion drafts.
```

If it does not make a normal person say "I can use this," it is not the product.

## Product Power Law

The first working internals may be ugly. The public alpha cannot be ugly.

Development boards are private. The outside world only sees a desirable object:

```text
Download this small thing. Your writing gets better.
```

No user owes us patience. No user cares how many failed trials, broken adapters,
teacher runs, prompt compilers, or repair loops were needed. Those failures are
the factory floor. They are not the storefront.

The storefront standard is:

```text
I want this on my computer.
```

Once Mercury 300 clears that bar, the specification belongs to us. The market
will ask for larger packs, narrower packs, team packs, local packs, and private
packs. We do not earn that pricing power by explaining the research. We earn it
by shipping the first small object people actually want.

## Non-Negotiable Promise

The public claim for the first alpha is:

```text
Mercury 300 is a 300-500MB writing pack that makes a local 7B model produce
answers that feel closer to a 30B model for practical writing tasks.
```

The pack does not need to solve math, coding, search, RAG, agents, legal advice,
or every benchmark. Those are other packs.

The first pack has one job:

```text
Make ordinary writing noticeably better.
```

## Why People Download

The hook is disbelief:

```text
300MB? Better proposals and writing on an 8GB laptop?
No subscription? No cloud bill? You are lying. I will download it.
```

The product must survive that hostile first use.

## Alpha Name

```text
Mercury 300 Writer Pack
```

Working tagline:

```text
A 300MB creative spark for your local 7B.
```

## Base And Teacher

Initial base:

```text
Qwen2.5-7B-Instruct
```

Initial teacher candidates:

```text
Qwen3-30B-A3B
Qwen3-14B
DeepSeek-R1-Distill-Qwen-14B
```

The teacher is allowed to be larger than what the user runs. The pack is the
portable artifact.

## Pack Budget

Hard target:

```text
<= 300MB
```

Alpha escape hatch:

```text
<= 500MB
```

Anything larger must be treated as a failed alpha candidate, even if quality is
good.

## What The Pack May Contain

The pack is allowed to be a combination of:

- LoRA or adapter weights.
- Steering vectors.
- Prompt compiler templates.
- Task routing metadata.
- Answer repair policy data.
- Calibration data for one base model.
- Lightweight eval fingerprints.

The pack is not allowed to require:

- A cloud subscription.
- A proprietary runtime.
- A 30B model at inference time.
- A GPU-only path for the alpha demo.
- More than one base model to prove the first claim.

## First Demo

The first public demo is a blind writing test:

```text
Prompt
  -> raw 7B
  -> 7B + Mercury 300 Writer Pack
  -> 30B teacher
```

The UI initially hides labels. The user votes:

```text
Which answer would you use?
Which answer sounds like the larger model?
Which answer would you send to a boss, investor, or reader?
```

The reveal only matters after the user has made a choice.

## Alpha Success Criteria

The alpha passes only if all of these are true:

- Pack size is at most 500MB, with a tracked path toward 300MB.
- The pack can be loaded on a normal local 7B workflow.
- On blind writing prompts, 7B + pack beats raw 7B by a visible margin.
- On at least 30% of prompts, users rate 7B + pack as closer to the 30B teacher
  than raw 7B.
- The demo can be explained in one sentence without internal Mercury jargon.

## Public Release Gate

The alpha is not allowed to go public until it satisfies every gate below:

- Public artifact size is at most 500MB.
- The intended product path to 300MB is written down.
- The pack loads without exposing training scripts, raw experiments, or internal
  development-board machinery.
- The first-run path produces a visible writing improvement in under five
  minutes.
- The product claim is writing-only.
- The demo starts with useful writing, not architecture.
- The blind test is available before any internal explanation.
- Failure cases are known and named, but not used as excuses.

If any gate fails, the alpha remains internal.

## 1000-Use Experiment Rule

Mercury 300 is not proven by looking at model internals. It is proven by use.

The alpha must collect 1000 writing trials before the product claim is treated
as real. A trial is valid only when it starts from a practical writing need:

```text
I need to write this proposal, slide, founder note, argument, or product copy.
```

It is not valid if the prompt exists only to flatter the pack.

Each trial records:

- User intent.
- Raw 7B output.
- Mercury 300 output.
- Teacher output when available.
- Which output the user would actually use.
- Whether Mercury 300 saved time.
- Whether the result felt larger than the base model.
- What failed.

The point is not to make every trial look good. The point is to discover the
shape of the real product:

```text
Where does the pack work?
Where does it collapse?
Which failures can be fixed by data?
Which failures require a different pack?
Which failures prove this is not the right battlefield?
```

This use ledger outranks internal beauty. Fullgrid may guide where to apply
force, but writing trials decide whether the force matters.

## First Prompt Domains

The alpha dataset focuses on high-perception writing tasks:

- Startup pitch rewrite.
- Product positioning.
- Proposal structure.
- Slide narrative.
- Executive summary.
- Founder manifesto.
- Brand voice.
- Long-form argument.
- Plain-language explanation.
- Emotional but disciplined copy.

## Things We Refuse To Optimize In Alpha

- Math benchmark scores.
- Coding benchmark scores.
- Agent tool use.
- Legal or medical correctness.
- General factual recall.
- Long-context retrieval.
- Enterprise procurement reports.
- Beautiful internal maps.

Those can exist later. They are not the first bite.

## Launch Surface

The first page should say:

```text
Think it is fake? Try the blind test.
```

The invite mechanic:

```text
Mercury 300 Alpha Keys go first to people willing to prove us wrong.
```

The product must welcome skeptics. Skeptics who change their mind are the first
growth channel.
