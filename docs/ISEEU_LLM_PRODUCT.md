# Iseeu LLM

Iseeu LLM is a family of tiny local document-intelligence packs.

It does not try to be a general chatbot. It does not ask users to download a
1GB or 2GB model to understand one receipt, one business card, or one quotation.

The product law:

```text
Tiny pack. Local. Fast. One painful document type. Clean structured output.
```

## First Wedge

The first wedge is Japan receipt and business document cleanup:

```text
Iseeu Receipt JP
```

The user story:

```text
I get a receipt.
I take a quick photo.
Iseeu turns it into clean accounting data.
At month end, the work is already done.
```

The product is not "OCR." OCR reads text. Iseeu sees the document.

## Why It Wins

Current recognition services often fail because they treat receipts, business
cards, and quotations as raw text. They guess fields after OCR. They break on
layout, taxes, stamps, registration numbers, mixed language, small print,
rotated photos, and vendor-specific formats.

Iseeu LLM takes the opposite path:

```text
The pack carries document memory.
```

Inside a tiny pack:

- Hundreds of thousands of layout vectors.
- Field-type vectors.
- Merchant and company pattern memory.
- Tax and invoice structure rules.
- Business-card role and contact patterns.
- Quotation and invoice table patterns.
- Confidence and repair policies.

The result is not a transcript. The result is structured data.

## Privacy-Safe Layout Flywheel

Every correction should make Iseeu better, but Iseeu must not need to collect
the user's private receipt contents.

The learning object is a layout ghost:

```text
Document geometry + field roles + confidence failures - private content
```

The client strips or hashes sensitive content before any shared learning packet
is produced. The useful signal is:

- Where fields appeared.
- Which field type was confused.
- Which visual block belonged together.
- Which table shape appeared.
- Which tax/total relationship failed.
- Which unsupported layout family was encountered.

The forbidden signal is:

- Personal names.
- Phone numbers.
- Email addresses.
- Addresses.
- Raw merchant-specific receipt contents unless explicitly opted in.
- Full receipt images.
- Full OCR transcripts.

This creates the Iseeu flywheel:

```text
More weird documents
  -> more layout ghosts
  -> better pack updates
  -> higher recognition
  -> more users
  -> more weird documents
```

Pack updates should improve recognition by shipping new layout vectors and
repair policies, not by uploading user documents to a giant model.

## Size Target

Hard target:

```text
50MB per pack
```

Alpha ceiling:

```text
100MB per pack
```

Anything larger must be treated as an internal development artifact, not the
public product.

## First Packs

```text
Iseeu Receipt JP
Iseeu Card
Iseeu Quote
```

Later packs:

```text
Iseeu Resume
Iseeu Form
Iseeu Doc
Iseeu Writer
```

## Japan Receipt Pack

Input:

- Receipt photo.
- Invoice photo.
- PDF scan.
- Mobile screenshot.

Output:

```json
{
  "document_type": "receipt",
  "merchant_name": "株式会社...",
  "invoice_registration_number": "T1234567890123",
  "date": "2026-05-29",
  "currency": "JPY",
  "subtotal": 10000,
  "tax_8_percent": 800,
  "tax_10_percent": 1000,
  "total": 11800,
  "payment_method": "credit_card",
  "line_items": [],
  "confidence": {}
}
```

## Pricing Target

Consumer/prosumer:

```text
599 JPY / month
```

This is not a "cheap app" price. It is an occupation price: low enough that
users can install it without asking permission, but useful enough that existing
OCR and receipt workflows start to look irrational.

Plus bundle:

```text
999 JPY / month
```

Plus adds more 50MB packs such as Card, Quote, Form, and Doc.

Business and SDK:

```text
Embedded SDK, annual license, or device/OEM licensing.
```

The business value is margin expansion:

- No giant model dependency.
- No heavy cloud inference for every receipt.
- Small pack can be embedded into existing apps.
- The same pack can live inside scanners, printers, copiers, POS terminals,
  mobile apps, and back-office software.
- Local/private mode reduces privacy objections.
- Better structure means less manual correction.

## Accuracy Standard

The public ambition:

```text
99.999% field-level reliability on supported document families.
```

This cannot be a vague marketing number. It must be measured per field:

- Merchant name.
- Date.
- Total amount.
- Tax amount.
- Registration number.
- Payment method.
- Line item table.
- Address.
- Contact fields.

Unsupported layouts must be detected as unsupported instead of confidently
wrong.

## Product Boundary

Iseeu does not need to understand every document.

It must be brutally good at supported packs:

```text
Receipt is Receipt.
Card is Card.
Quote is Quote.
```

If a document is outside the pack boundary, Iseeu must say so.

## Launch Copy

```text
領収書を読むために、2GBのAIはいらない。
```

```text
Stop downloading giant models to read tiny documents.
```

```text
Take the photo now. Month end is already done.
```

## Release Gate

A pack cannot ship until:

- Public pack size is under 100MB, with a path to 50MB.
- It runs locally.
- It outputs clean JSON.
- It detects unsupported layouts.
- It beats generic OCR plus regex on a hostile sample set.
- It records every failure as a reusable layout vector or rule fix.
- It completes a 1000-document field-level trial.
- The privacy-safe layout packet strips document content and preserves only
  reusable structure.
