# Remaining extraction triage

10 November 2026. AI findings only; independent human validation pending. No extraction corrections applied.

Refreshed diagnostics from the corrected frozen-evidence reparse rather than the superseded baseline diagnostics. Local evidence is in `data/corpus_review/20261110/remaining_triage/`: `diagnostics.json`, `findings.jsonl`, six full-page renders and an input/output hash manifest. Each finding retains affected records, stable IDs, PDF pages, image hashes and blank human decisions. Original PDF, baseline and corrected reparse hashes remained unchanged.

## Source-image findings

- 2026, PDF 24 / printed 24: the apparent question 16 is a continuation of Q56 option B. Q56 has only two parsed options; the false record receives the remainder. Proposed repair: merge evidence and options with an explicit old-ID disposition.
- 2026, PDF 43-44 / printed 43-44: the apparent question 43 starts at the printed footer. Its subsequent text belongs to the continuation of passage XXIII, which starts on PDF 43 before that footer. Proposed repair: distinguish footer material from question starts and retain the continuation in the existing passage. Preserve the false record's provenance and disposition.
- 2021, PDF 237 / printed 10: the apparent question 3 is the continuation of a citation in Q37 option B. Proposed repair: reunite Q37 and its remaining options, preserving both source anchors.
- 2021, PDF 228-229 / printed 1-2: an unlabelled passage precedes Q1; another begins after Q6 and before Q7. PDF 237 has a further passage between Q36 and Q37, currently absorbed into Q36 raw text. These observations do not establish all passage ranges or associations. Complete passage boundaries require additional review.

These are AI image checks, not human decisions. Printed answer labels and case references were not checked for legal correctness or authoritative provenance.

## Current diagnostic inventory

The selected eleven year labels contain 1,397 MCQ proposals and five separate essay proposals. These are parser outputs, not reviewed question counts. The refreshed diagnostics retain section-aware duplicate groups, option-count anomalies, absent passage links and missing/out-of-range numbers where configuration specifies an expected range. No expected range was invented when configuration leaves it null.

For 2026, every expected number appears despite two extra false candidates. For 2025, the total matches its configured count while numbers 25, 33 and 34 are missing. For 2023, seven configured numbers are missing amid extra candidates. These examples demonstrate why count agreement does not establish extraction accuracy. For 2018, 49 duplicate groups occur under an unknown section; section resets must be checked before interpreting them as duplicate questions. Lack of passage links in older formats is not automatically a defect.

## Verification and next implementation

Consistency checks passed: eleven scoped diagnostic rows, reconciliation to the existing 1,402 total proposals, four source-linked findings, six image hashes, manifest output hashes and unchanged frozen inputs. No parser behavior changed during triage.

Next implement separate synthetic regression fixtures for (1) a numeric continuation inside an option, (2) a footer interrupting a cross-page passage and (3) a citation continuation inside an option. Define acceptance criteria and observe failures before implementation; retain genuine unpunctuated question starts and numeric option labels. Reparse frozen evidence into a new directory, reconcile every changed record and retain proposed aliases/dispositions. Unlabelled passage segmentation requires its own specification and fixtures; avoid a broad heuristic that silently assigns ranges. Human review of both targeted packets and independent extraction validation remain pending.
