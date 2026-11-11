# Random OCR comparison with a Luna agent

10 November 2026. Exploratory AI audit; no human ground truth or reviewed research labels. Primary researcher: TO CONFIRM.

## Model and method

Used a separate agent requested as **gpt-6-luna**, medium reasoning, the lowest-credit model among the models exposed to this session. Official documentation confirms [image input support](https://developers.openai.com/api/docs/models/gpt-6-luna) and [Codex credit rates](https://learn.chatgpt.com/docs/pricing). This establishes the cost rationale, not an OCR quality benchmark. Exact runtime snapshot, token usage and billed cost are unavailable; no separate API or commercial OCR calls were launched.

The plan was recorded before inspection in `research/OCR_AUDIT_PLAN.md`. Python seed **20261110** selected four native-text and four OCR pages without replacement from 307 native and 112 OCR candidate body pages. Eligibility did not depend on successful question extraction. Selected PDF pages: native 105, 178, 305, 449; OCR 330, 339, 405, 414. The sample spans seven year labels, with two pages from 2017.

The agent viewed local source-page PNGs before opening extraction output, recorded visible question starts/continuations and transcribed the first two complete items per page where available. It froze and hashed the blind observations before comparison with run `20261110T043421397159Z`. This yielded **14 complete items: 13 MCQs and one essay prompt**, plus additional boundary/context observations. Four visible question starts were incomplete on the selected pages and were excluded from complete-item comparisons.

## Reconciled findings

| Scope | Finding |
|---|---|
| 14 transcribed complete items | 13 have identifiable separate extracted records; the essay prompt on PDF page 330 has no distinct record. Its stem is entirely absent from selected OCR text, which contains only a footer. |
| 13 transcribed MCQs | Three have confirmed option omission/segmentation issues: page 105 Q19 splits one choice into two; page 414 Q61 and Q62 each omit the fourth choice, and Q62 also duplicates a label. This does not count all text-level OCR corruption. |
| Other issues within the transcribed sample | Page 178 Q91 contains footer contamination; page 339 Q2/Q3 contain answer-mark noise and Q3 has a spurious leading character; page 405 Q20/Q21 have substantial option text/reading-order corruption. A spelling discrepancy on page 449 Q26 remains uncertain. |
| Additional context-only observations | Page 339 Q6 loses three options; page 405 Q23 duplicates a label; page 414 Q63 loses its fourth option. These were not included in the 14-item transcription denominator. |
| Reviewer reliability | Luna normalized an apparent source typo from “Vedio” to “Video” in a frozen transcription. This is recorded as an AI-reviewer discrepancy, not charged to the extraction. |

The parent agent separately inspected source images on pages 105, 330, 405 and 414 and checked the corresponding extracted records. The main boundary/option defects above are consistent with those checks. No full-corpus error rate, character error rate or model accuracy score is reported: the reference is another AI reading and the sample is small and stratified.

Luna was useful for reading visible material missed or damaged by the pipeline. It also made a transcription normalization and initially overstated the mechanism of the missing essay and mixed comparison scopes. These were reconciled rather than accepted automatically. Its output should remain a proposal for source-based review.

## Audit trail and verification

All page images, source text and raw model outputs stay local under ignored `data/ocr_audit/20261110_luna_seed20261110/`. Open `review.html` there for source images beside baseline records. The sampling manifest, exact prompt, blind observations/hash, original comparison and summary, `audit_errata.json`, parent checks and reconciled summary are retained. **Read the errata with the initial comparison:** the original claim that page 330's prompt text was merged into Q2 was incorrect; only its page/footer evidence was attached to that oversized record. The initial mixed option count of seven is superseded by the scoped findings above. Page 405 Q24 is not counted as a confirmed omission because only its first option is visible on the sampled page and the next page was not audited.

Sampling reproduced from the seed; all eight source-image hashes matched; all comparison question IDs resolve to the frozen baseline; its 12 manifest-listed artifact hashes and the unchanged original PDF hash passed verification. The blind observation hash remained unchanged throughout reconciliation. No source, parser, extracted question or review status was modified.

## Priorities suggested by this audit

1. Retry text-sparse scanned pages when a visible prompt is not recognized; test alternate local OCR/layout settings against page 330 before generalizing.
2. Recognize option labels using position/context so references to other options inside an answer do not create extra choices.
3. Test OCR-damaged numeric labels and remove page furniture only from derived fields, preserving raw evidence.
4. Use Luna selectively for flagged-page proposals, with source checks and explicit uncertainty. Independently reviewed extraction fixtures are still required before analytical use.

These are follow-up recommendations; this audit did not implement repairs or mark any record human-reviewed.
