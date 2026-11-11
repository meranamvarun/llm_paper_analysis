# Automated extraction checks

11 November 2026. Manual extraction benchmarks are optional following the user's instruction; local work proceeds through programmatic checks and an automatic repair queue.

## Completed run

Working cleaned data was preserved unchanged. The automated pipeline checked all **1,397 in-scope questions** and re-OCRed all **365 configured body pages**, including pages without extracted question evidence. It then rechecked **793 cropped source regions across 697 questions** at higher resolution. No paid API calls, source publication or manual annotation was used.

Final report: `data/automated_quality/20261111/strict_report_v1/report.html`. Its summary and `automatic_repair_queue.jsonl` are machine-readable. Full source images, TSV, OCR coordinates, raw outputs/stderr, settings and hashes are under `run_v1/`. The source PDF and prior cleaned data remain unchanged.

The original full-page/crop triage supplied at least 98% ordered target-token support without numeric/negation discrepancies for 843 questions (700 before crop rechecks). This threshold is a screening category, not an accuracy rate. A stricter gate retains even small target-token gaps: **650 questions meet strict lexical support; 747 remain OCR exceptions**, comprising 340 numeric/negation-priority cases and 407 other lexical gaps. OCR disagreement can arise from OCR noise, source-region boundaries or extracted text; it is not an automatic instruction to rewrite a question.

Structural findings are 184 option-structure flags, 27 empty-option flags, 247 absent passage-link flags, 63 duplicate-number groups, two configured missing-number groups, three out-of-range-number groups and three configured-count mismatches. These counts overlap and mix question-level and paper/group-level units; do not sum them as erroneous questions. Duplicate groups under an unknown section are warnings because section resets remain ambiguous. There are 466 error-level findings and 63 warning groups.

PDF pages 6, 167 and 466 have no question evidence in the current proposals; that alone does not mean a missing question. An additional all-page scan retained 410 unmatched numbered-line candidates, which can include instructions, options and numbered passage paragraphs. These are computational repair leads, not confirmed omitted questions.

## Gate and next computational work

- Input integrity: **PASS**.
- Programmatic quality gate: **NEEDS_AUTOMATED_REPAIR**, due to structural/source-agreement findings.
- Mandatory manual extraction benchmark: **NO**.
- Empirical corpus error rate: not measured by these agreement checks.

Next process option boundaries/empty options and missing passage links, then reconcile critical-token OCR disagreements using source crops and alternate computational readings. Preserve literal source typos, original IDs, machine disagreements and audit logs. Keep the current cleaned view as the working version; produce separate derived repairs. Do not silently replace text with a competing OCR result or infer missing answers/questions from counts.

## Programmatic benchmark

The no-op implementation first failed detection of numerical/negation errors, ordering, absent source evidence and structural defects. Strict-gate tests then failed for a single wrong ordinary word in a long item before the stricter rule was implemented.

A reproducible synthetic challenge used seed 20261111 and 600 cases: 100 unchanged strings, plus 100 cases each with a dropped negation, altered section number, altered year, short wrong word or one wrong ordinary word in a long item. The initial 98% triage missed the last category; this result is retained. The final strict gate flagged all 500 injected defects and none of the 100 unchanged strings **in this synthetic set**. This is detector regression evidence, not a corpus accuracy estimate or a test of every possible omission, punctuation or legal-citation error.

The full extraction test suite passes 49 tests. The previous human-reference scorer remains available as an optional historical tool; its human-gold requirement does not apply to the new automated gate. Source OCR uses Tesseract PSM 6 at 180 DPI and 240-DPI crops; its engine/trained-data hashes are recorded. Repeated OCR can share errors. Ordered target-token support does not prove that every source question or omitted word was found, or that punctuation/case/legal interpretation is correct.
