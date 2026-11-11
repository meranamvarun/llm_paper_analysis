# Parser follow-up acceptance criteria

10 November 2026. Proposals remain unreviewed.

Before implementation: synthetic fixtures must fail for indented unpunctuated numeric continuations within incomplete lettered options (including citation fragments) and a bottom-margin numeric footer interrupting a cross-page passage. Preserve all raw lines and evidence, retain genuine unpunctuated question starts at the question margin, and retain numeric option labels. Do not introduce unlabelled passage inference. Reparse frozen page evidence into a new local directory, log every semantic record change and removed-ID disposition, preserve all six accepted corrections, refresh diagnostics, and verify frozen input hashes.

## Implementation and verification

Parser v0.1.2 extends the existing indented numeric-continuation rule to incomplete options and recognizes a narrow bottom-margin numeric footer while a passage is active. Raw footer lines remain in passage evidence. Genuine margin-aligned unpunctuated questions and numeric options retain existing regression coverage. No unlabelled passage rules were added.

Red evidence: the new synthetic tests failed in three subcases (option number, citation number, passage footer). Green evidence: all 24 extraction tests pass. A Windows stdin encoding substitution initially replaced the Greek footer glyph; this was corrected to an explicit Unicode escape in code and fixtures, and the frozen-evidence run was repeated. The first attempt is retained locally and is superseded by `reparse_v0.1.2_corrected/`.

Local outputs are under `data/corpus_review/20261110/`. `reparse_v0.1.2_corrected/` reparses frozen baseline pages. `reconciled_v0.1.2/` preserves all six accepted records verbatim, including their limited decision metadata; its manifest hashes frozen inputs and output artifacts. The earlier accepted view is unchanged. Reproduction scripts are `reparse_v012.py` and `reconcile_v012.py` in the same ignored local directory.

The reconciled view contains 1,596 proposals across the compilation, including 1,397 in scope (five essays and 1,392 MCQs). These are unreviewed parser counts, not research denominators. Relative to the prior corrected reparse, five false candidate IDs have explicit proposed dispositions to records/passages containing all their source anchors. Three address the triaged defects (PDF 24, 43-44 and 237); two additional numeric continuations appear on PDF 130 and 438. The latter require contextual source-image review before acceptance. Full before/after records and all other semantic changes are retained in `reconciliation.jsonl`; `id_dispositions.jsonl` preserves removed records and their proposed targets. Five previously accepted ID aliases are retained separately.

`diagnostics.json` recomputes numbering, section-aware duplicates, option-label anomalies and missing passage references from the reconciled view. Historical issue flags inside the six verbatim accepted records remain historical; use the regenerated diagnostics for the current queue. Corpus checks confirm unique IDs, all six accepted records identical, all passage references resolved, every removed record's anchors retained in its proposed target, and unchanged frozen inputs/source hash. Reference resolution does not validate passage associations.

## Remaining work

Review the additional PDF 130/438 proposals and the complete semantic reconciliation against source images. Resolve remaining numbering defects and unlabelled passage boundaries; establish independent human extraction validation. Source provenance/rights, incomplete coverage, reviewer attribution and protocol/codebook freeze remain pending. No frequencies, legal labels or publication findings were produced.
