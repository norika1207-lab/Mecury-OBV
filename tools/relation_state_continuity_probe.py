#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class Case:
    case_id: str
    setup: str
    query: str
    anchor_terms: list[str]
    answer_terms: list[str]


CASES = [
    Case(
        "owner_transfer_key",
        "Mina owned the red key. Mina gave the red key to Juno. Juno put it in the left drawer.",
        "At the end, who controls the red key?",
        ["Mina", "red key", "gave", "Juno", "left drawer"],
        ["Juno"],
    ),
    Case(
        "promise_delegate",
        "Ari promised Bo that the invoice decision would stay with Ari unless Ari delegated it. Ari delegated the invoice decision to Cy.",
        "Who should make the invoice decision now?",
        ["Ari", "promised", "delegated", "invoice decision", "Cy"],
        ["Cy"],
    ),
    Case(
        "permission_revoked",
        "Lina allowed Omar to edit the schedule. Later Lina revoked Omar's editing permission and gave edit permission to Pia.",
        "Who currently has editing permission?",
        ["Lina", "Omar", "revoked", "Pia", "editing permission"],
        ["Pia"],
    ),
    Case(
        "state_location",
        "The archive started in Box A. Niko moved the archive from Box A to Box C. Nobody moved it after that.",
        "Where is the archive now?",
        ["archive", "Box A", "moved", "Box C", "Nobody"],
        ["Box C"],
    ),
    Case(
        "role_successor",
        "Tao was the incident lead. Tao handed the incident lead role to Mira. Mira accepted the role.",
        "Who is the incident lead now?",
        ["Tao", "incident lead", "handed", "Mira", "accepted"],
        ["Mira"],
    ),
    Case(
        "debt_assignment",
        "Kai owed the report update. Kai assigned the update to Ren, and Ren confirmed ownership.",
        "Who owns the report update now?",
        ["Kai", "report update", "assigned", "Ren", "confirmed"],
        ["Ren"],
    ),
    Case(
        "trust_boundary",
        "The system trusted token Alpha at first. After a rotation, token Beta replaced Alpha as the trusted token.",
        "Which token is trusted now?",
        ["trusted", "Alpha", "rotation", "Beta", "replaced"],
        ["Beta"],
    ),
    Case(
        "thread_state",
        "The conversation state was draft. After review, Nia marked the conversation state as approved.",
        "What is the current conversation state?",
        ["conversation state", "draft", "review", "approved"],
        ["approved"],
    ),
]


def token_spans(text, tokenizer, terms):
    enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
    offsets = enc["offset_mapping"]
    spans = []
    lower = text.lower()
    for term in terms:
        for m in re.finditer(re.escape(term.lower()), lower):
            start, end = m.span()
            toks = [i for i, (a, b) in enumerate(offsets) if not (b <= start or a >= end)]
            if toks:
                spans.extend(toks)
    return sorted(set(spans))


def mean_vec(hidden, positions):
    if not positions:
        return None
    idx = torch.tensor(positions, device=hidden.device)
    return hidden.index_select(0, idx).mean(dim=0)


def safe_cos(a, b):
    if a is None or b is None:
        return float("nan")
    return F.cosine_similarity(a.float(), b.float(), dim=0).item()


def auc_like(xs):
    vals = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    return sum(vals) / max(1, len(vals))


def normalize_curve(xs):
    vals = torch.tensor([0.0 if not math.isfinite(float(x)) else float(x) for x in xs])
    lo = vals.min()
    hi = vals.max()
    if (hi - lo).abs().item() < 1e-9:
        return vals
    return (vals - lo) / (hi - lo)


def pearson(a, b):
    x = normalize_curve(a)
    y = normalize_curve(b)
    x = x - x.mean()
    y = y - y.mean()
    denom = (x.norm() * y.norm()).item()
    if denom < 1e-9:
        return 0.0
    return float((x @ y).item() / denom)


def answer_logit_margin(model, tokenizer, input_ids, answer_terms):
    with torch.no_grad():
        out = model(input_ids=input_ids)
    logits = out.logits[0, -1].float()
    ans_ids = []
    for term in answer_terms:
        ids = tokenizer(" " + term, add_special_tokens=False).input_ids
        if ids:
            ans_ids.append(ids[0])
        ids = tokenizer(term, add_special_tokens=False).input_ids
        if ids:
            ans_ids.append(ids[0])
    ans_ids = sorted(set(ans_ids))
    if not ans_ids:
        return float("nan")
    top_other = torch.topk(logits, k=50).values.mean().item()
    ans = logits[torch.tensor(ans_ids, device=logits.device)].max().item()
    return ans - top_other


def run_case(model, tokenizer, case, device, max_length):
    prompt = (
        f"Track the relation-state exactly.\n"
        f"{case.setup}\n"
        f"{case.query}\n"
        f"Answer:"
    )
    enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = enc.input_ids.to(device)
    text = tokenizer.decode(input_ids[0], skip_special_tokens=False)
    anchor_positions = token_spans(text, tokenizer, case.anchor_terms)
    query_positions = token_spans(text, tokenizer, [case.query, "Answer"])
    final_pos = input_ids.shape[1] - 1

    with torch.no_grad():
        out = model(
            input_ids=input_ids,
            output_hidden_states=True,
            output_attentions=True,
            use_cache=False,
            return_dict=True,
        )

    hidden_states = [h[0].detach().cpu() for h in out.hidden_states]
    attentions = [a[0].detach().cpu() for a in out.attentions] if out.attentions is not None else []

    setup_anchor_by_layer = []
    final_by_layer = []
    query_by_layer = []
    for h in hidden_states:
        setup_anchor_by_layer.append(mean_vec(h, anchor_positions))
        query_by_layer.append(mean_vec(h, query_positions) if query_positions else h[final_pos])
        final_by_layer.append(h[final_pos])

    residual_anchor_to_final = [
        safe_cos(setup_anchor_by_layer[i], final_by_layer[i])
        for i in range(len(hidden_states))
    ]
    residual_carry = [
        safe_cos(final_by_layer[i], final_by_layer[i + 1])
        for i in range(len(hidden_states) - 1)
    ]
    formation_delta = [0.0]
    for i in range(1, len(hidden_states)):
        formation_delta.append(1.0 - safe_cos(final_by_layer[i - 1], final_by_layer[i]))

    attention_anchor_mass = []
    attention_entropy = []
    if attentions:
        anchor_set = set(anchor_positions)
        for a in attentions:
            # [heads, q, k], final query attention to prior anchor tokens.
            final_attn = a[:, final_pos, :]
            if anchor_set:
                idx = torch.tensor(sorted(anchor_set), dtype=torch.long)
                mass = final_attn.index_select(1, idx).sum(dim=1).mean().item()
            else:
                mass = 0.0
            probs = final_attn.clamp_min(1e-12)
            ent = (-(probs * probs.log()).sum(dim=1) / math.log(probs.shape[-1])).mean().item()
            attention_anchor_mass.append(mass)
            attention_entropy.append(ent)

    margin = answer_logit_margin(model, tokenizer, input_ids, case.answer_terms)

    return {
        "case_id": case.case_id,
        "prompt_tokens": int(input_ids.shape[1]),
        "anchor_token_count": len(anchor_positions),
        "query_token_count": len(query_positions),
        "answer_logit_margin": margin,
        "residual_anchor_to_final": residual_anchor_to_final,
        "residual_carry": residual_carry,
        "formation_delta": formation_delta,
        "attention_anchor_mass": attention_anchor_mass,
        "attention_entropy": attention_entropy,
    }


def summarize(results, n_layers):
    layer_scores = [0.0 for _ in range(n_layers + 1)]
    residual_scores = [0.0 for _ in range(n_layers + 1)]
    formation_scores = [0.0 for _ in range(n_layers + 1)]
    attn_scores = [0.0 for _ in range(n_layers)]

    for r in results:
        for i, v in enumerate(r["residual_anchor_to_final"]):
            residual_scores[i] += v
        for i, v in enumerate(r["formation_delta"]):
            formation_scores[i] += v
        for i, v in enumerate(r["attention_anchor_mass"]):
            attn_scores[i] += v

    denom = max(1, len(results))
    residual_scores = [x / denom for x in residual_scores]
    formation_scores = [x / denom for x in formation_scores]
    attn_scores = [x / denom for x in attn_scores]

    res_norm = normalize_curve(residual_scores).tolist()
    form_norm = normalize_curve(formation_scores).tolist()
    attn_norm = normalize_curve(attn_scores).tolist()

    for i in range(n_layers + 1):
        layer_scores[i] = 0.55 * res_norm[i] + 0.45 * form_norm[i]

    top_formation = sorted(
        [(i, formation_scores[i]) for i in range(1, len(formation_scores))],
        key=lambda x: x[1],
        reverse=True,
    )[:8]
    top_residual = sorted(
        [(i, residual_scores[i]) for i in range(len(residual_scores))],
        key=lambda x: x[1],
        reverse=True,
    )[:8]
    top_attention = sorted(
        [(i, attn_scores[i]) for i in range(len(attn_scores))],
        key=lambda x: x[1],
        reverse=True,
    )[:8]

    cross_layer_circuit_score = pearson(residual_scores[1:], attn_scores) * 0.5 + pearson(formation_scores[1:], attn_scores) * 0.5
    residual_auc = auc_like(residual_scores)
    attention_auc = auc_like(attn_scores)
    formation_peak = max(formation_scores) if formation_scores else 0.0

    if cross_layer_circuit_score > 0.45 and attention_auc > 0.04:
        verdict = "cross_layer_circuit"
    elif attention_auc > 0.08:
        verdict = "attention_topology_path"
    elif residual_auc > 0.35:
        verdict = "residual_stream_continuity"
    else:
        verdict = "localized_layer_formation"

    return {
        "verdict": verdict,
        "scores": {
            "residual_auc": residual_auc,
            "attention_anchor_mass_auc": attention_auc,
            "formation_peak": formation_peak,
            "cross_layer_circuit_score": cross_layer_circuit_score,
        },
        "top_formation_layers": top_formation,
        "top_residual_layers": top_residual,
        "top_attention_layers": top_attention,
        "mean_curves": {
            "residual_anchor_to_final": residual_scores,
            "formation_delta": formation_scores,
            "attention_anchor_mass": attn_scores,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--dtype", default="bfloat16", choices=["float32", "float16", "bfloat16"])
    ap.add_argument("--max-cases", type=int, default=len(CASES))
    ap.add_argument("--max-length", type=int, default=384)
    args = ap.parse_args()

    dtype = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}[args.dtype]
    Path(args.out).mkdir(parents=True, exist_ok=True)

    print(f"[continuity] load tokenizer {args.model}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    print(f"[continuity] load model {args.model} device={args.device} dtype={args.dtype}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        trust_remote_code=True,
        attn_implementation="eager",
    ).to(args.device)
    model.eval()

    t0 = time.time()
    results = []
    for i, case in enumerate(CASES[: args.max_cases]):
        print(f"[continuity] case {i+1}/{min(args.max_cases, len(CASES))} {case.case_id}", flush=True)
        results.append(run_case(model, tokenizer, case, args.device, args.max_length))

    n_layers = int(getattr(model.config, "num_hidden_layers", len(results[0]["attention_anchor_mass"])))
    summary = summarize(results, n_layers)
    artifact = {
        "schema": "relation-state-continuity-probe-v1",
        "model": args.model,
        "dtype": args.dtype,
        "device": args.device,
        "elapsed_sec": round(time.time() - t0, 3),
        "case_count": len(results),
        "summary": summary,
        "cases": results,
    }
    out_json = Path(args.out) / "relation_state_continuity.json"
    out_md = Path(args.out) / "README.md"
    out_json.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Relation-State Continuity Probe",
                "",
                f"Model: `{args.model}`",
                f"Verdict: `{summary['verdict']}`",
                "",
                "## Scores",
                json.dumps(summary["scores"], indent=2),
                "",
                "## Top Layers",
                f"formation: {summary['top_formation_layers']}",
                f"residual: {summary['top_residual_layers']}",
                f"attention: {summary['top_attention_layers']}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[continuity] DONE {out_json}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
