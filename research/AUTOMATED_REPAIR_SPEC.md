# Conservative structural repair specification

12 November 2026. Acceptance criteria before implementation:
- Read cleaned_proposed_v2; preserve all input records, IDs, original fields, out-of-scope records and accepted decisions. Write a new output directory only.
- Rejoin parser-created option fragments only after Both/Neither/Either or a subsequent and/or connector, retaining observed parenthetical labels literally. Require exactly A-D, nonempty options, and whitespace/case-normalized literal source support for each joined answer in raw_text.
- Leave ambiguous labels, source mismatches, missing content and passage relationships unresolved. Never supply an answer or infer passage ranges.
- Log every changed field with before/after, source pages and machine-proposal status. Hash inputs, code and outputs. Rerun structural checks and reuse frozen OCR comparisons only for records whose question text is unchanged; changed records require fresh comparison against retained OCR evidence.
- Synthetic tests must first fail for supported nested references, ambiguity/source mismatch, original preservation and out-of-scope preservation. No empirical accuracy claim.


## Expanded recovery acceptance criteria (12 November 2026)
- Recover primary letter options from line starts, excluding inline case initials, statute subsections and answer references. Only accept an unambiguous final A-D block; material before that block remains stem evidence. Do not discard prior lexical corrections: transfer unique normalized field edits or abstain.
- For metadata-form papers, use explicit Question Number boundaries and literal numeric 1-4 option anchors in retained source OCR. Canonical labels may be repaired from those anchors; preserve matched prior cleaned text and log new source-OCR text separately.
- Restore question boundaries/numbers only from explicit source starts, never expected counts alone. Preserve old IDs through alias/disposition logs and retain every original record, including false candidates.
- For unlabelled passages, use explicit inline answer terminators and source gaps before the next actual question. Every proposed passage/link needs source anchors and a logged boundary rationale; never assume fixed question groups.
- New OCR passes retain images, raw outputs, settings and hashes. OCR corroboration remains distinct from reviewed transcription and legal coding.


## Native-source corroboration amendment
Direct bounded PDF text is additional computational evidence alongside OCR. Apply the same strict ordered lexical, numeric and negation checks; never use this to waive a mismatch. Retain bounded source strings, geometry, decoder version and hashes. Corrupt embedded fonts remain unresolved when the target is unsupported. Native text agreement is not exact punctuation accuracy or independent human validation.


## Source boilerplate and typography
Exclude only explicitly recognized export metadata lines (including Single Line Question Option: No) from question-source comparisons; retain prose negations. Preserve raw source strings and filtered counterparts. Remove source-anchored page headers/footers accidentally included in proposed fields, and join spaced printed-number prefixes only when they equal the explicitly recovered source number. Lexical screening may normalize Unicode compatibility ligatures and apostrophe shapes while preserving every raw field, number and negation; missing apostrophes remain discrepancies.


## Embedded field-image OCR
For the 2017 export, source PDF XObject bounds expose one stem image followed by four answer images per metadata-delimited question. Preserve image objects, coordinates and hashes; require those five source objects, and explicitly log post-question section instructions separately. Exclude only the known option-label/correctness-icon gutter from answer-image OCR. Retain uncropped originals. Run two layout modes on each field; exact nonempty lexical agreement can propose a source-image transcription with raw outputs retained. No grammar repair, legal inference, or accuracy claim. Disagreements remain in the queue and need source-image reconciliation. Every proposed text change retains before/after and source evidence.


## Final source-reading contract (sign-off record)
The final checker accepts an explicit assistant image transcription as an additional computational source reading only with a matching source-PDF hash, displayed source images, image hashes and retained transcription provenance. It applies the same strict lexical/numeric/negation check; there is no bypass flag. All 25 final readings and any record changes are retained separately, and independent_human_validation remains false. This engineering extension is not an independent extraction benchmark or a frozen research coding plan. The final release freezes current code and data; earlier intermediate stages remain historical.
