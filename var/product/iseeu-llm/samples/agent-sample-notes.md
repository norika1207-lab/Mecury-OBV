# Agent Hostile Samples

These samples are sidecar additions only. They intentionally stress the current post-OCR parser without changing `tools/iseeu/receipt_jp_engine.py`.

- `agent-001`: convenience store mixed 8%/10% tax with transport IC payment.
- `agent-002`: handwritten-style receipt text, OCR typo in `登録番号`, and spaced invoice number.
- `agent-003`: drugstore receipt where total and tax appear on separate lines after multiline item names.
- `agent-004`: invoice registration number split by hyphens and PayPay payment.
- `agent-005`: mixed tax plus non-taxable item and invoice number with spaces/hyphens.
- `agent-006`: compact Reiwa date as `R8.5.29` plus credit-card wording.
- `agent-007`: missing date should be unsupported.
- `agent-008`: missing explicit total should be unsupported even though tax/payment/date exist.
