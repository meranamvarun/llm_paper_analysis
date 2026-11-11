# Extraction acceptance specification

## Accepted-proposal application (10 November 2026)

Create a separate derived view from the frozen baseline and the six explicitly accepted packet items. Require matching packet-byte hashes, one unique acceptance per item, baseline-record content matches and valid alias evidence containment. A parser-version-only snapshot difference is permitted and must be retained explicitly alongside the actual baseline in the log; no text, evidence or other metadata mismatch is permitted. Reject stale/tampered packets, rejected decisions, duplicate decisions, missing IDs and ID collisions before writing output. Apply only the six accepted records; leave every other record identical to baseline. Preserve raw source text and evidence; Q24 uses a separate corrected-text field and accepted number/stem/options. Record before/after records, old/new aliases, decision IDs and input/output hashes in a new output directory; refuse overwrites. Acceptance is limited to the displayed proposal and must not imply independent pilot completion, passage validation or legal correctness. Synthetic tests must demonstrate application and rejection behavior, with an observed failing test before implementation.

Version 0.1; exploratory extraction only. No reviewed codes or legal conclusions.

Acceptance criteria, defined before implementation:

1. Preserve the source PDF hash and raw native/OCR outputs separately. Every emitted question has a deterministic source anchor, paper/year label, PDF pages, printed question number, extraction method, evidence line boxes and unreviewed status. Unknown printed pages and marks remain null.
2. Synthetic fixtures must demonstrate cross-page options, section numbering resets, shared passage links, rejection of numbered passage paragraphs without options, essay instructions, multi-column key rows, and missing-option review flags.
3. A page with no native text or excessive control characters requests OCR. Missing OCR must produce an explicit unresolved page, never a blank-page assumption. OCR does not overwrite native output.
4. No question continuation crosses a configured paper boundary. Every numbered candidate that cannot be safely parsed is retained as an unresolved block. All questions remain review candidates; malformed options, sequence anomalies and inline answers have explicit flags.
5. Keys remain independent, with source page and provisional/final/unverified status. No automatic claim of official correctness or legal verification.
6. Re-running unchanged inputs/configuration gives the same question anchors. Existing completed run directories are not overwritten. Cache keys include source hash and extraction settings/software versions.
7. Run the pipeline on the local source, reconcile every source page to a paper/key/unassigned category, verify evidence references and unchanged source hash, and record counts and limitations. Compare a small manually transcribed boundary sample; it does not establish corpus-wide accuracy.

Implementation order: tests and observed red result; parser and routing implementation; green tests; full extraction; provenance/traceability checks; handoff and retro. The independent human coding pilot, protocol freeze, legal verification and reviewed analytical dataset remain separate later work.

## Follow-up acceptance criteria: Roman statements (10 November 2026)

Within an open MCQ whose four options have not yet been seen, lowercase Roman-numbered statements must remain question evidence even when their left margin meets the configured passage-heading threshold. An uppercase passage heading after a completed MCQ must still open a passage. Synthetic fixtures must assert both behaviors, exact evidence retention and unreviewed status. Compare a reparse of frozen page evidence against the preserved baseline, validate source traceability and record changed IDs/content. This does not authorize normalizing spaced question digits or accepting AI transcriptions as reviewed corrections.

An indented continuation consisting of an unpunctuated number followed by words, before any options in an open MCQ, must not split that question. Require a left offset greater than 15 PDF points relative to the question start; numbered starts at the original margin and explicitly punctuated starts must remain recognizable. This geometry rule is compilation-specific and requires review on changed corpus records. The Roman-statement fixture exposed a separate potential defect; actual PDF 133 Q108 was instead split at an indented numeric continuation.
