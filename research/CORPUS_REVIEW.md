# In-scope corpus and parser review

10 November 2026. Study range: 2016-2026 inclusive. All extraction records and AI transcriptions remain unreviewed; primary researcher: TO CONFIRM.

## Source-page findings

For 2019, PDF pages 293-309 correspond to printed pages 1-17. The cover states 32 pages including rough-work and essay-answer space. Frozen extraction contains 100 MCQ proposals with unique numbers 1-100, and five essay prompts on PDF 309/printed 17; the instructions require answering two essays. Source images of the cover, start/end of the MCQs and essay page support these observations. Printed pages 18-32 have not been located in this compilation. Question coverage is plausible, but the entire booklet is not present and the contents of the absent pages must not be inferred. Five essays offered and two required need separate denominators. Text accuracy and intervening pages still require independent human review.

For 2024, PDF 97 identifies set A with symbol `*`. PDF 137 ends at printed page 41 and MCQ 120; PDF 138-140 are rough-work pages 42-44 with `*`. PDF 141-142 are additional rough-work pages 43-44 with `#`. These extras show mixed set material in the compilation, but do not by themselves demonstrate question-body mixing or an additional administration. The sampled question-body and key pages show `*`; complete body/set correspondence remains unverified. The key at PDF 143 explicitly says provisional; it is not automatically an authoritative answer source.

Official 2024 source-link attempts were inaccessible or timed out. Search snippets were not accepted as document verification. The user-reported Consortium source remains recorded, while the exact compilation URL, acquisition date and rights remain unresolved. Attempted URLs are retained in the local source-check record.

## Missing-item proposals

The user-authorized agent requested as `gpt-6-luna` transcribed 2024 Q24 (PDF 107/printed 11) and Q108 (PDF 133/printed 37) from source images. Raw output, uncertainty and image hashes remain local. Exact runtime snapshot and billed cost are unavailable; no separate paid API calls were made. Q24's native number is rendered as spaced digits, causing a false number 2 proposal; its correction remains an AI proposal. No silent digit normalization was introduced. Q108 can be recovered directly from existing evidence by the parser fix below. Neither transcription was promoted to human-reviewed data.

## Parser change and evidence

Acceptance criteria were added to `EXTRACTION_SPEC.md` before implementation. A synthetic lowercase Roman-statement fixture failed because its MCQ disappeared at the passage margin. A guard now preserves lowercase Roman statements within an incomplete MCQ. The first corpus comparison showed that this alone did not recover real Q108: its statements are indented beyond the heading threshold. That initial hypothesis was corrected rather than claimed as a successful repair.

A second synthetic fixture reproduced the actual defect: an indented continuation starting with an unpunctuated number and words was mistaken for a new question. The red result produced question 136 instead of 108. Parser v0.1.1 now preserves that line when an MCQ is open, no options have yet been seen, and its left offset exceeds the question start by 15 PDF points. Explicitly punctuated starts and unpunctuated starts at the original margin remain eligible. This threshold is compilation-specific. Both regression fixtures and all earlier fixtures pass: **18 extraction tests**.

Reparsed all frozen baseline page evidence locally, without rerunning OCR or changing the source. Corrected output is `data/corpus_review/20261110/reparse_v0.1.1_corrected/`, separate from baseline `20261110T043421397159Z`. Unique IDs, source evidence round-trips, paper bounds, passage references and unreviewed status passed validation.

Five IDs were replaced by earlier source anchors, restoring stems/numbers for 2026 Q52, 2024 Q108, 2023 Q49/Q58 and 2018 section Q41 (cross-page). The parent AI checked their source images. Every old record's evidence is contained in its proposed replacement. `proposed_id_aliases.jsonl` preserves all five old/new pairs as pending human decisions. Four unchanged-ID records only change sequence-warning flags. Total proposal count remains 1,601 across the original 13 labels; no reviewed question count is implied. The 2016-2026 selection contains 1,402 proposals, including five essays. Counts alone do not show accurate extraction.

The first, ineffective Roman-only reparse is preserved in `reparse_v0.1.1/` as exploratory evidence; it also omitted runner-added passage warnings. Use only the corrected comparison, which applies the same warning enrichment as the baseline. Its code hash distinguishes it from the first attempt despite sharing the draft version label.

## Remaining work

Final checks: 18 extraction tests passed; the harness suite completed 16 tests with six POSIX-shell tests skipped. Harness check passed. All 41 manifest-listed review artifacts and both agent-recorded image hashes verified. Contact-sheet generation temporarily reused the PDF 133 image path at a different scale; the original rendering was restored and its exact agent-recorded hash verified. The local source-check record preserves this incident. Baseline top-level file hashes and original PDF hash matched the frozen comparison record.

Review the proposed aliases and Q24 transcription against full source pages; continue other missing/duplicate-number diagnostics and unlabelled passage boundaries. Establish independent human extraction validation, confirm source rights and exact provenance, and freeze the coding plan before analytical tables. Original source, baseline files and prior out-of-scope audits are preserved. Raw page images, full question text, scripts, AI output, comparisons and hashes stay under ignored `data/corpus_review/20261110/`.
