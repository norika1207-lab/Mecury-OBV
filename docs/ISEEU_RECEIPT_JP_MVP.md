# Iseeu Receipt JP MVP

This is the first runnable Iseeu Receipt JP artifact.

It is not public-ready. It is the first internal pack that proves the product
can move from idea to executable code.

## What Works

- Accepts post-OCR Japanese receipt text.
- Extracts merchant, date, qualified invoice registration number, total, tax,
  payment method, and simple line items.
- Outputs structured JSON.
- Exports CSV.
- Produces privacy-safe layout ghosts through `make_layout_ghost.py`.
- Has a small sample evaluation harness.
- Can be packed into a small local artifact.

## What Does Not Work Yet

- No image OCR pipeline.
- No iOS capture flow.
- No real Japanese receipt dataset.
- No 1000-document trial ledger.
- No proof against real commercial OCR tools.
- No 50MB vector layout memory yet.

## Commands

Run sample eval:

```bash
python3 tools/iseeu/eval_receipt_jp.py
```

Parse one receipt OCR text file:

```bash
python3 tools/iseeu/receipt_jp_engine.py \
  var/product/iseeu-llm/samples/receipt-jp-001.txt \
  --out var/product/iseeu-llm/samples/receipt-jp-001.actual.json \
  --csv var/product/iseeu-llm/samples/receipt-jp-001.actual.csv
```

Build internal pack:

```bash
python3 tools/iseeu/build_receipt_jp_pack.py
```

Check release gate:

```bash
python3 tools/iseeu/check_pack_gate.py \
  --artifact dist/iseeu/iseeu-receipt-jp-pack-0.1.0.zip \
  --trial-count 2
```

The gate should fail until real trials and OCR+regex baseline comparison exist.

