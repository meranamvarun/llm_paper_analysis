# Local PDF extraction

Current workflow uses automated extraction checks; the user declined manual extraction benchmarks. See `research/AUTOMATED_QUALITY_SPEC.md` and `research/AUTOMATED_QUALITY_RESULTS.md`. The old blind packet is optional and does not block continuation.

```powershell
$researchPython = 'C:/Users/malai/AppData/Local/Programs/Python/Python312/python.exe'
& $researchPython -m extraction.automated_quality --questions data/text_quality/20261111/cleaned_proposed_v2/cleaned_questions.jsonl --passages data/corpus_review/20261110/reconciled_v0.1.2/passages.jsonl --output data/automated_quality/NEW_RUN --workers 6
& $researchPython -m extraction.strict_support --run data/automated_quality/NEW_RUN --output data/automated_quality/NEW_REPORT
```

These commands retain local OCR evidence and refuse existing output directories. The final gate can pass without human annotations; unresolved structural or OCR findings create an automatic repair queue. Token agreement is machine corroboration, not a gold-standard accuracy rate.

Question text cleanup is a separate unreviewed layer; see `research/TEXT_QUALITY_SPEC.md` and `research/TEXT_QUALITY_RESULTS.md`. Final prepared local output is `data/text_quality/20261111/cleaned_proposed_v2/`; the independent blind human benchmark is separate. A dictionary hit or model reading is not an accuracy certificate.

To create a new screening/sample directory (refuses an existing output):

```powershell
$researchPython = 'C:/Users/malai/AppData/Local/Programs/Python/Python312/python.exe'
& $researchPython -m extraction.quality_run --records data/corpus_review/20261110/reconciled_v0.1.2/questions.jsonl --passages data/corpus_review/20261110/reconciled_v0.1.2/passages.jsonl --pages data/extraction/runs/20261110T043421397159Z/pages.jsonl --config extraction/papers.json --output data/text_quality/NEW_SCREEN
```

`quality.py` preserves original records, proposes formatting separately, flags uncertain lexical/symbol spans and applies only source-evidenced AI proposals to that layer. Wordfreq's pinned English frequency list screens absence, including valid names and legal terms; it never automatically fixes spelling. Keep all scan outputs local under ignored `data/`.

Optional historical human-reference mode: after two independent readings and adjudication, prepare eligible alignment JSONL records with `alignment_id`, `stratum_id`, `stem`, ordered `options` (`label`, `text`), `critical_tokens`, `gold_status: "adjudicated"`, two distinct `reviewers` and an `adjudicator`. Use explicit mappings for missed/extra questions and preserve exclusions separately. Export both the original and proposed prediction views with the same alignment IDs. Score each against the same references:

```powershell
& $researchPython -m extraction.benchmark --predictions data/ALIGNED_PREDICTIONS.jsonl --references data/ADJUDICATED_REFERENCE.jsonl --output data/NEW_SCORE.json
```

This scores text and aligned items; page boundaries, splits/merges, passage relationships and sampling uncertainty require their separate prespecified checks. With no human gold, accuracy remains NOT ASSESSED. A passing text subset does not grant an overall release PASS.

Accepted packet decisions can be applied with `python -m extraction.corrections --baseline PATH --packet PATH --decisions PATH --output NEW_DIRECTORY`. Keep output under ignored `data/`. This creates a separate view, full before/after correction log, ID aliases and hash manifest; it refuses existing outputs. The six accepted proposals were applied in `data/corpus_review/20261110/accepted_derived_v1/`; see `research/ACCEPTED_CORRECTIONS.md`. Overall review status remains unreviewed and each applied decision is recorded in `accepted_correction`.

This pipeline emits **unreviewed proposals**, not an analysis-ready dataset. It makes no legal classifications and does not join answer keys to questions automatically. Source text, images and outputs stay in ignored `data/`; nothing is uploaded.

Parser v0.1.2 additionally retains indented numeric continuations within incomplete options and bottom-margin numeric passage footers. See `research/PARSER_FOLLOWUP.md` for regression evidence, frozen-evidence reconciliation and refreshed diagnostics. All new parser changes remain proposals; six accepted records are preserved verbatim in the reconciled view.

Parser v0.1.1 preserves lowercase Roman statements inside incomplete MCQs and indented numeric continuations before options. These geometry rules are compilation-specific. See `research/CORPUS_REVIEW.md` for red/green tests, a separate frozen-evidence reparse, five proposed ID aliases and remaining defects. The original full run remains preserved; the reparse is not human-reviewed data.

## Run on Windows

From the repository root:

```powershell
$researchPython = 'C:/Users/malai/AppData/Local/Programs/Python/Python312/python.exe'
& $researchPython -m pip install -r requirements.txt
& $researchPython -m unittest discover -s extraction/tests -v
& $researchPython -m extraction.run
```

Tesseract is a separate native dependency. The runner discovers it on PATH or at `C:\Program Files\Tesseract-OCR\tesseract.exe`. Use `--tesseract PATH` to select another executable. This installation was tested with Tesseract 5.4.0.20240606 and English trained data. Missing/failed OCR produces explicit unresolved pages. No paid service is used.

Options: `--source`, `--config`, `--output-root`, `--dpi` (default 300), `--workers` (default 2), `--preview-limit` (default 30). Do not point output-root at a public or tracked directory: the outputs contain full source text. For the current source, keep the default ignored location.

## Files and stages

- `papers.json`: candidate paper/key/body boundaries, year labels, essay ranges, passage-heading margins and expected-count evidence. These are reviewable assumptions, not verified corpus metadata. The source hash must match. No automatic year inference.
- `pipeline.py`: question/passage/key proposal parser. Handles cross-page questions, lettered and numbered options, exported exam metadata, sections, essays and inline answer labels. Geometry thresholds are specific to this compilation.
- `run.py`: native word extraction, page rendering, selective OCR, geometry-based line reconstruction, validation and bounded review previews.
- `tests/`: synthetic fixtures only; no copyrighted source question text is committed.

Native extraction uses pdfplumber word positions. Missing text, control-character corruption, unresolved `(cid:...)` glyphs and replacement characters trigger local Tesseract OCR. The known scan/garbled ranges are explicitly routed as well. Raw native words, OCR TSV, OCR coordinates/confidence and rendered pages are retained in the cache. Layout reconstruction uses word coordinates, rather than OCR block order, to reunite number gutters and stems. Current paper bodies are treated as single-column; a different compilation requires layout validation.

Each run creates a new directory under `data/extraction/runs/`; existing runs are preserved. Cache directories are keyed by source, extraction software and OCR settings. A page-specific OCR mode can be configured; its outputs have distinct sidecars. Every run records code/config hashes and software versions. Question anchors combine source hash, PDF page and reconstructed line ID; they are deterministic for unchanged configuration/code/extraction outputs. They can change when segmentation changes. There is no correction editor yet: future reviewed splits/merges must retain the old ID as an alias and log the decision, rather than silently replacing it.

## Review outputs

| Output | Purpose |
|---|---|
| `summary.json`, `run.json`, `artifact_hashes.json` | Counts, provenance, validation and artifact integrity |
| `pages.jsonl` | Selected page extraction with raw words and line boxes |
| `questions.jsonl` | Question proposals, options, evidence, method, issues and unreviewed status |
| `passages.jsonl` | Proposed shared passages and source evidence |
| `answer_keys.jsonl` | Separate key entries; source label does not establish authenticity |
| `unresolved_blocks.jsonl` | Text that was not safely recognized as a question |
| `page_coverage.jsonl` | Paper/key assignment for every PDF page |
| `paper_diagnostics.json` | Duplicate numbers and mismatches against configured expected counts |
| `review_queue.jsonl` | Questions, unresolved text, page issues and paper issues needing review |
| `review.html`, `previews/` | Deterministic sample across years and formats, with full-width contextual scan crops |

Raw text is never silently corrected. `corrected_text`, printed page and marks remain null unless separately established; option-label normalization retains the observed label. Inline answer strings are separated from parsed options while remaining in raw evidence. No confidence score is treated as proof of accurate OCR.

The review HTML is a bounded inspection aid, not a complete annotation interface or the prespecified coding pilot. All records remain in the JSONL queue. Reviewers must check stems, options, cross-page continuity, passage associations, section resets and missing questions against full pages. Unlabelled passages in 2020/2021 remain unresolved; these papers need additional boundary rules. Native line clustering, OCR errors and numbered statements can still produce merged, split, missing or duplicate candidates. A matching count alone does not validate extraction.

Before statistical analysis, create an independently reviewed extraction sample across formats, measure transcription and segmentation accuracy, resolve key/set provenance and completeness, freeze the coding plan, and retain an append-only correction/ID-alias log. The pipeline deliberately does not perform subject coding, judgment verification or repeat analysis.
