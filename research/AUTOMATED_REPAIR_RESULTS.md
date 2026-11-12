# Automated repair and final quality gate

12 November 2026. **PASS: zero current source-support or structural flags.**

## Working release

Use `data/automated_quality/20261112/final_quality_v2/`:
- `questions.jsonl` and `passages.jsonl`: current derived views.
- `summary.json`, `verification.json` and `report.html`: machine checks, integrity evidence and offline audit report.
- `comparisons.jsonl` and `source_readings.jsonl`: current target hashes, all computational readings, filtered/raw source strings, selected evidence and unchanged strict comparison results.
- `automatic_repair_queue.jsonl`, `structural_findings.jsonl` and `abstentions.jsonl`: empty at sign-off.
- `manifest.json` and `code_snapshot/`: source/data/code hashes, software versions and frozen implementation.

All **1,395 active source records** pass source-support-v2: **1,387 MCQs, five essays and three items explicitly printed as ?Omitted for Valuation.?** The omitted items have no invented options and are not MCQs. These are extraction diagnostics, not reviewed research denominators or proof of complete unique exam administrations.

The original working input has 1,397 records. Eight false question candidates are retained with explicit dispositions: one numbered passage paragraph and seven citation/footer/passage fragments. Six source-anchored records were added: three MCQs and three explicit omitted items. IDs of surviving records are unchanged. Disposition targets, added IDs and accepted-decision metadata are checked in verification.json. The source PDF, original extraction, earlier views, raw OCR and all six historical accepted snapshots remain available.

## Repairs and evidence

The work repaired nested answer references, initials/subsections mistaken for options, numeric-label OCR failures, split printed numbers, numbering-block resets, QR/header/footer noise, missing cross-page answer content, two missed Roman passage headings and an incomplete question stem. It retained literal source spellings in image readings rather than repairing case names or legal answers from outside knowledge. The three 2018 numbering blocks remain within the same candidate paper; they were not counted as separate administrations.

The first conservative batch repaired 43 questions (184 -> 141 option-structure flags; 27 -> 17 empty-option flags). Subsequent source-boundary passes resolved the remaining structural categories. Complete metadata frames and source-image readings resolved the final 31 option structures. Original records and before/after proposals are retained in the stage directories and append-only run logs.

Source support then used the original all-page OCR, retained 240-DPI crops, additional 400/500-DPI OCR with multiple layout modes, bounded PDFium native text, PDFplumber geometry with documented word-spacing tolerances, and separately bounded embedded stem/option images from the 2017 export. Embedded-image decoding explicitly resolves indirect PNG predictor parameters and checks decoded byte lengths. Correctness icons were excluded from answer-image OCR; original uncropped images remain.

A final **25 assistant source-image readings** were recorded in `final_image_reconciliation_v1/vision_source_readings.jsonl`, with images/hashes, provenance and before/after proposals. Eleven are the selected support source in the final check; the other records also have passing native/OCR support after correction. These are AI transcriptions, not independent human annotations. Prompt/settings availability and unexposed runtime model identity are disclosed in the records.

## Gate version and validation

The final gate is **source-support-v2**. Its strict condition still requires every target lexical token in order, with no numeric or negation discrepancy. It now admits additional native and image-based computational source readings. Explicit export boilerplate such as ?Single Line Question Option: No? is excluded from comparison, while prose negations are retained. Compatibility ligatures and typographic apostrophe variants normalize for lexical comparison; raw strings remain unchanged. Tests retain wrong-word, missing-negation, changed-number and missing-evidence failures. No unresolved item was waived merely to produce zero.

Observed red/green evidence includes no-op failures for nested references, primary option boundaries, literal numbering/reset handling, stale image proposals, source-region containment, metadata negations, typographic normalization, native coordinate conversion, indirect image-predictor decoding and per-field source support. **All 78 extraction tests pass.** Harness: 16 tests pass, six shell-hook tests skipped; harness check has zero errors/warnings. The final synthetic detector challenge is recorded separately from corpus claims.

## Limits and next work

Zero configured flags does **not** establish a zero transcription error rate, independent human validation, exact punctuation accuracy, complete source coverage or correct legal interpretation. OCR and assistant readings can share errors. Historical extractor issues remain historical provenance; current diagnostics are the regenerated gate outputs. No human-gold CER/WER exists. The optional manual extraction benchmark remains optional.

Source URL/compilation provenance, rights, completeness (including the previously unlocated 2019 printed pages), duplicate administrations, attribution, legal reviewers and the draft protocol/codebook remain unresolved research tasks. Do not turn this engineering PASS into reviewed subject/judgment labels, frequency claims or publication results. No commit, push, upload or publication was performed.
