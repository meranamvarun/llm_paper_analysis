# Extraction follow-up

10 November 2026. Exploratory AI proposals only; primary researcher: TO CONFIRM.

## Local layout experiment

The baseline remains `20261110T043421397159Z`. Tested PDF pages 330, 339, 405 and 414 at 300 DPI with local Tesseract English modes 3, 6 and 11. These pages were selected because of known audit defects, not randomly; no corpus error rate follows from this experiment. The plan was saved before execution. Reproducible script, page images, TSV coordinates, stderr, outputs, results and hashes are local under ignored `data/ocr_followup/20261110_psm/`.

On page 330, mode 3 returned only three footer words; modes 6 and 11 returned 23 and 15 words respectively, recovering parts of the prompt but scrambling its first clause. The source image visibly contains a complete prompt. This supports a targeted source-image transcription proposal, not accepting either alternate OCR output as a correction. More words alone do not establish better extraction. Other pages' word counts also do not establish option accuracy. No global OCR setting or parser configuration was changed.

The experiment checked that the original source hash and every top-level baseline run file hash were unchanged. Its artifact manifest retains the experiment outputs independently of the baseline.

## Missing-value proposals

At the user's request, a separate agent requested as `gpt-6-luna` was assigned image-first transcription of the known missing essay on page 330 and options on pages 339 and 414. This is the lowest-cost model exposed in this session; exact runtime snapshot, token charges and billed cost are unavailable. No separate paid API calls were launched. Outputs belong under ignored `data/ocr_followup/20261110_luna_missing/`; they must remain AI proposals with literal source readings, page/number evidence, image hashes and uncertainties. They do not update baseline records or establish human review.

## Independent extraction validation draft

Completed five proposal groups: one absent essay stem and six missing option texts across four MCQs. The parent AI visually checked all three source images and agreed with the values. `linkage_and_source_checks.json` links four existing question IDs, explicitly leaves the absent essay unlinked, preserves observed numeric/letter labels separately from normalized labels, and records image-hash verification. The absent essay has no baseline ID to reuse. Artifact hashes preserve both the original agent output and the companion checks. These are AI-to-AI checks, not independent human validation.

This design still needs researcher approval before sampling or coding. Keep this separate from the legal/subject coding pilot.

- Freeze the source, candidate administration/version inventory and extraction run before sampling. Use the confirmed 2016-2026 inclusive range and deduplicate scans first; retain exclusions and incomplete papers in the inventory.
- Sample source pages, including pages with no emitted questions, stratified by administration and native/OCR method. Determine sample size and seed before drawing it; include essay and passage formats. Report stratum denominators and sampling fractions. Audit known defects separately as a targeted challenge set.
- Two independent human reviewers first transcribe visible starts, continuations, stems, options, printed numbers and passage boundaries from full source pages with adjacent-page context, without viewing machine proposals. Preserve uncertain characters and source typos. Freeze both readings before comparison.
- Adjudicate disagreements against the source, preserving original reviewer decisions and adjudicator rationale. Qualified legal review is a separate requirement for interpretation, answers and judgment links.
- Compare the frozen proposals to the adjudicated reference: missing/extra/split/merged questions, stem transcription, option completeness/order/labels, cross-page continuity and passage links. State eligible item/page denominators for each measure; retain abstentions and missingness. Define text alignment/normalization and any accuracy threshold before measurement.
- Store corrections append-only, referencing old question IDs, source hash/page/boxes, proposed and accepted values, actor type, decision, date and reason. Splits/merges require ID aliases. Do not mark AI proposals human-reviewed. A correction tool needs its own acceptance specification and red/green synthetic tests before implementation.

No reviewed analytical frequency tables can yet be produced. Source rights, independent reviewers, corpus completeness and protocol/codebook freeze remain outstanding.

## Verification

Extraction suite: 16 tests passed. Harness suite: 16 tests completed, six shell-hook tests skipped because POSIX sh was unavailable on PATH; the existing full Git Bash limitation remains. No production software was changed. Source-image hashes and four baseline ID matches passed; all five proposal groups retain unreviewed status.
