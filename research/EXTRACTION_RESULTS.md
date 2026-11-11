# Extraction implementation and first full run

Date: 10 November 2026. Status: unreviewed machine proposals. Primary researcher and independent reviewers: TO CONFIRM.

## Delivered

Implemented `extraction/pipeline.py`, `extraction/run.py`, candidate configuration `extraction/papers.json`, synthetic acceptance tests and usage instructions in `extraction/README.md`. The original PDF is unchanged. No paid calls, cloud OCR, uploads, legal coding or automatic answer validation were used.

Full run: `data/extraction/runs/20261110T043421397159Z/` (local, ignored). Earlier exploratory runs were preserved; use this run for the results below. Verification record: `data/extraction/verification.json`.

The run accounts for all 466 PDF pages: 345 native text extractions and 121 locally OCR-processed pages. The latter includes the initial 94 flagged pages plus 27 pages with unresolved native glyph mappings/replacement characters. OCR ran with Tesseract 5.4.0.20240606, English, 300 DPI, page segmentation mode 3. Word-coordinate reconstruction fixes the separate number-gutter ordering observed in raw OCR block order. Native and raw OCR evidence remain separate.

Outputs contain 1,601 question proposals, 101 passage proposals, 600 separate key entries and 190 unresolved blocks. These are parser output counts, **not reviewed counts of unique examination questions or administrations**. Zero pages are unassigned to a candidate paper or key; that does not prove completeness or validate body exclusions.

## Validation and known limits

- All 1,601 question IDs are unique and match the immediately preceding run's anchors. Raw question text round-trips exactly through its referenced page lines/boxes. Paper bounds, passage references and unreviewed status passed validation.
- Source SHA-256 unchanged. All 12 files listed in the run artifact manifest passed hash verification. Source/config/code hashes and package versions are recorded in run metadata.
- Two AI scan-transcription spot checks matched the four options for printed question 1 on PDF pages 3 and 295. A six-item preview contact sheet and the contextual 2014 crop were visually inspected. These checks do not constitute independent human validation or establish transcription accuracy for the corpus.
- Every question is explicitly unreviewed. Issue counts overlap: 272 proposals have incomplete/duplicate option labels, 92 have numbering discontinuities, 22 have short/missing stems, 447 touch OCR-flagged pages, 268 contain unverified inline answer labels and 248 have unresolved passage links. These are diagnostic flags, not measured error rates.
- The 2014 scan demonstrates a real omission: OCR can detach a stem from its printed number. Raw page evidence is retained and contextual crops expose this; the parser has not silently supplied missing text. This section still needs additional OCR/layout work and human correction.
- Numbered statements and citations can still cause false splits or merged questions. Unlabelled 2020/2021 passage boundaries are not resolved. Geometric heading margins are compilation-specific proposals. Several yearly candidate counts differ from expected counts; `paper_diagnostics.json` records missing and duplicate numbering. A matching count, including the 150 candidates in each of 2016 and 2017, is not proof of correctness.
- Review HTML contains a deterministic 30-question sample across year labels and formats, with full-width contextual crops. All question records and other issues are in `review_queue.jsonl`; the HTML is not a complete annotation application.
- Keys remain provisional/final-labelled/unverified as observed. Set correspondence, authority, completeness, dates, rights and legal interpretation require review. No key is automatically joined to a question.

## Test evidence

Acceptance criteria were written in `research/EXTRACTION_SPEC.md` before implementation. Initial parser stubs produced five assertion failures and two missing-result errors across the eight original fixtures (one boundary-isolation test passed). The earlier import-only failure was not treated as sufficient behavioral evidence.

Additional observed red tests covered numbered essay instructions being mistaken for prompts, inline answers leaking into options, lowercase options, Roman statements mistaken for passages, exported exam metadata, a separate `Ans` line and a number-only question line. Implementations were corrected and the final extraction suite passed all 16 tests. Geometry ordering also has a synthetic fixture. The harness suite passed 16 tests with six shell-hook tests skipped; the known full Git Bash limitation remains.

Tests and provenance checks validate software behavior and traceability, not legal correctness or full extraction accuracy. No independent human reference dataset exists yet. Freeze a reviewed extraction sample, quantify stem/option transcription and boundary/linkage accuracy, record corrections and ID aliases, and resolve corpus/rights decisions before producing reviewed analytical tables.
