# Accepted extraction corrections applied

10 November 2026. Six proposals accepted by the session user have been applied to a separate local view at `data/corpus_review/20261110/accepted_derived_v1/questions.jsonl`. Original PDF, baseline, reparse, packet and acceptance log are preserved. Reviewer name remains unconfirmed.

## Changes and provenance

The view starts from the frozen baseline `data/extraction/runs/20261110T043421397159Z/questions.jsonl`, rather than promoting all changes from the corrected reparse. Five accepted replacements restore the proposed earlier anchors for 2026 Q52, 2024 Q108, 2023 Q49 and Q58, and 2018 section Q41. `id_aliases.jsonl` records the five old/new pairs and acceptance decision IDs. Replacement records retain all baseline evidence and include earlier evidence from the accepted packet.

The sixth change retains the Q24 source anchor and raw text while applying the accepted printed number 24, stem including its parenthetical text, and four options. `corrected_text` stores the accepted transcription separately. Q24's packet snapshot had a newer parser-version label than the frozen baseline; all other fields matched. Both snapshots are explicitly retained in the correction log.

`corrections.jsonl` contains six before/after records, packet baseline snapshots and decision references. `manifest.json` hashes code, baseline, packet, decisions and output files. The original decision log continues to describe its historical pending-application state; the new correction log records application without rewriting past decisions. `verification.json` records the corpus checks.

The total remains 1,601 records across the compilation, of which 1,402 are within 2016-2026. Exactly six records differ from baseline; 1,595 are identical. These are record counts, not reviewed question denominators. Out-of-scope source records remain in the derived view for preservation and must be excluded from study analysis.

## Validation evidence

Acceptance criteria and synthetic tests preceded implementation. A no-op implementation failed alias replacement, separate corrected transcription and unsafe-application rejection checks. A separate regression then failed on the real parser-version-only snapshot difference before the narrowly scoped compatibility rule was implemented. All **22 extraction tests pass**, including four correction tests with seven rejection subcases.

Corpus checks passed: all input/output hashes; unchanged source PDF hash; six exact before/after log matches; five aliases; unchanged count and in-scope count; retention of every original evidence entry; preserved Q24 raw text; four accepted Q24 options; existing passage-reference resolution; and refusal to overwrite the existing output without altering it.

## Limits and next work

Each changed record has an `accepted_correction` field identifying the limited decision. Its overall `review_status` remains unreviewed because acceptance of the displayed proposal does not establish full transcription, passage-link, independent pilot or legal validation. Existing diagnostic issue flags are preserved and may reflect the baseline; regenerate derived diagnostics before using them as a current queue. Resolving a passage ID establishes a valid reference, not a correct association.

Next implement the test-driven option-number, citation-number and passage-footer fixes in `REMAINING_EXTRACTION_TRIAGE.md`, then reconcile their frozen-evidence reparse with this accepted view so the six decisions survive subsequent parser changes. Independent validation, source rights/provenance and protocol/codebook freeze remain pending before analysis.
