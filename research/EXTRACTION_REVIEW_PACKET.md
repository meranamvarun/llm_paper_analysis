# Targeted extraction review packet

10 November 2026. Status: user accepted all six proposals; applied in a separate derived view described in `research/ACCEPTED_CORRECTIONS.md`. Independent validation pilot remains pending.

## User decision

On 10 November 2026 the session user instructed, "accept for all", in response to the six-item packet. All six acceptances are recorded separately in `data/corpus_review/20261110/human_review_packet/human_decisions_20261110.jsonl`, with a companion hash manifest. The original packet, its blank review fields and original manifest remain unchanged as historical evidence. Reviewer is recorded as `session_user`; a personal name, detailed checks and rationale were not supplied and remain null. This records acceptance of these proposals only; it does not establish passage-link validation, independent pilot completion, legal correctness or corpus-wide accuracy. Subsequent application is recorded separately in `accepted_derived_v1/corrections.jsonl` under the same dated corpus-review directory.

## Packet preparation record

Prepared `data/corpus_review/20261110/human_review_packet/review.html` for the five proposed ID aliases and 2024 Q24. Open this local HTML file to inspect full source images alongside baseline records and proposals. `items.jsonl` retains stable source IDs, paper/year, PDF pages, evidence boxes, source-image hashes and blank human decision fields. Printed page observations are explicitly AI observations. `manifest.json` hashes the inputs and packet outputs. Full source text remains under ignored `data/`.

The existing six-page contact sheet supports the five proposed number/anchor changes at a visual spot-check level. The full PDF 107 image supports the Q24 number and supplied transcription, including four options and the parenthetical text. These are further AI checks, not independent human validation. No alias or transcription was applied to extraction records. Passage linkage, detailed transcription accuracy and corpus-wide segmentation remain unresolved.

Consistency checks passed: six packet items, five baseline-evidence containment checks against proposed replacements, seven linked source images, all manifest input/output hashes and blank human decisions. The preparation initially encountered a UTF-8 BOM in a proposal file; reading with UTF-8-sig resolved it without altering the input. No parser/software behavior changed.

A human reviewer should compare the full pages with each candidate, record reviewer/date, accept/reject/unresolved and a rationale, and separately check transcription, segmentation and passage links. Preserve disagreements and both IDs. This deliberately selected defect packet does not estimate extraction accuracy and is not the independently sampled extraction-validation pilot. Reviewed corrections require a separate append-only decision log before integration.

Next local work: triage remaining in-scope numbering and passage-boundary diagnostics against frozen evidence. Independent human validation, source provenance/rights and protocol freeze remain required before analysis.
