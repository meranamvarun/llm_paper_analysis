# Question text cleanup and benchmark

Workflow update: the user subsequently declined manual extraction benchmarks. Their earlier design below is preserved as optional history; current programmatic validation and results are in `AUTOMATED_QUALITY_RESULTS.md`. No manual extraction benchmark is required for continuation.

11 November 2026. AI proposals only; independent human extraction accuracy is not yet established.

## Delivered files

Final local outputs: `data/text_quality/20261111/cleaned_proposed_v2/`.

- `cleaned_questions.txt`: readable proposed text for all 1,397 in-scope question records.
- `cleaned_questions.jsonl`: convenient in-scope proposed stems/options, original stems/options, stable IDs, source evidence and review status.
- `questions.jsonl`: all 1,596 preserved source records with a separate `text_proposal` layer for in-scope records. Original fields and the six earlier acceptance decisions are unchanged; 199 out-of-scope records remain identical.
- `review.html`: self-contained human cleanup review, with all question texts, before/after comparisons, 177 embedded evidence sheets, uncertainty and downloadable blank decision fields. Entries are not automatically saved; downloaded decisions are not applied automatically.
- `changes.jsonl`, `luna_reviews_with_parent_qa.jsonl`, `field_transcriptions.jsonl`, `residual_flags.jsonl`, `quality_scorecard.json`, and manifests retain the audit trail.

Earlier `cleaned_proposed_v1_checked/` is a preserved intermediate view; use v2. The earlier empty output directory records an integration attempt that stopped when an image reference was invalid. No frozen source record was overwritten.

## Coverage and proposals

Screened every in-scope stem and option. Luna reviewed 1,603 flagged occurrences across 554 questions: 651 lexicon absences, 119 mixed digit/letter tokens, 591 unusual Unicode glyphs, 177 ASCII-symbol candidates, 12 candidate footer spans and 53 additional contextual symbols. Dictionary screening alone cannot find all OCR defects, especially errors that form valid words or plausible numbers.

The final view proposes **885 edits across 279 questions**, including two complete source-field retranscriptions. Six additional change proposals were no-ops and are separately counted. Cleanup removes source-confirmed answer-mark/layout artifacts and footer contamination, repairs source-confirmed OCR spellings, restores punctuation/currency and preserves visible legal symbols, percentages, aliases and blanks. Original question numbers, options, raw evidence, IDs and prior acceptance metadata remain available. No question boundary, option-label inventory, missing essay or passage association was silently repaired by this text layer.

One ambiguous spelling remains explicitly unresolved (flag-01270, PDF 432); the original text is retained. The residual lexical screen still finds 761 candidates: 614 lexicon absences, 118 mixed digit/letter tokens, 28 ASCII symbols and one bullet. These include source-confirmed names, legal terms, article labels, legitimate percentages and literal source punctuation; they are not 761 established errors. Residual screening is preserved rather than optimized to make the dictionary count zero. Separate linked-passage context screening produced 214 flags, not a passage-wide cleanup or validation.

## Luna review and parent checks

The user requested Luna. Three delegated reviewers were requested as `gpt-6-luna`, medium reasoning, over year batches and later symbol supplements. Exact runtime snapshots, token charges and billed cost were not exposed; no separate paid API calls were made. Source images, inputs, raw per-flag outputs, intermediate snapshots and hashes remain local under ignored `data/`. See `data/text_quality/20261111/model_provenance.json` and each batch's provenance files. Prompt summaries are local; the full conversational instructions remain in the session transcript.

Parent AI inspected all 93 initially proposed non-symbol word edits on twelve evidence sheets, selected glyph proposals, and the two full-field retranscriptions. Thirteen candidate decisions were rejected or retained as uncertain; source spellings such as Hohfield, Carllil, Hobeas, Thibant, Rhect, Bneruf and civilie must not be changed merely because a conventional spelling is familiar. A further bracket transcription was corrected against the source image. Disagreements and superseded proposals remain in the parent QA ledger and raw model snapshots. These are AI-to-AI checks, not human adjudication or an estimate of model accuracy.

Some reviewer image references were inconsistent with the generated sheet grouping. Integration stopped on an invalid path, then resolved each flag through the deterministic exact-line crop mapping, preserving original claimed paths separately. This repairs evidence metadata; it does not independently prove a model read every image it claims to have read. Earlier Windows shell-fed proposals also introduced question marks in place of apostrophes/diacritics. Those outputs were preserved and corrected with explicit Unicode escapes; the application code rejects replacement characters and question marks embedded in words.

The dictionary is a pinned **wordfreq 3.1.1 English large frequency list**, used only as a lexical screen. A zero frequency means absence from that list, not an invalid legal word. Package versions and the lexicon hash are recorded. Wordfreq is by Robyn Speer and includes SUBTLEX data by Marc Brysbaert and collaborators; see the [primary project documentation and data attribution](https://github.com/rspeer/wordfreq). No source question text was sent to a dictionary website.

## Accuracy benchmark

The benchmark specification preceded implementation in `research/TEXT_QUALITY_SPEC.md`. The source-page sample is frozen in `data/text_quality/20261111/frozen_benchmark/benchmark_sample.json`: seed 20261111, up to five pages per year/method stratum, **60 sampled pages across 12 strata from 365 configured candidate body pages**. Pages with no emitted questions remained eligible. These are candidate corpus boundaries, not verified unique administration counts. The sample is disproportionate; preserve stratum sampling fractions and use an appropriate page/cluster analysis before population inference.

The self-contained blind human file is `data/text_quality/20261111/human_benchmark/blind_review.html`, with 153 sampled/context page images. It shows no extracted text or Luna proposals. Two independent reviewers should use separate copies, freeze their readings, then adjudicate. The downloaded readings remain pending adjudication; the file cannot declare itself gold. A separate purposive known-defect challenge manifest is saved locally and must not be used to infer corpus accuracy.

The runnable scorer `extraction/benchmark.py` measures micro character/word edit rates, exact fields/items, missing/extra aligned items, ordered/labeled option correctness, critical-token errors and per-stratum text results. It preserves case, punctuation and numbers; only NFC and whitespace folding are allowed. It refuses unadjudicated reference records or records without two reviewer identities and an adjudicator. Alignment must be human checked, including absent questions. Raw extraction and cleaned proposals must be compared to the same eligible gold alignments, with explicit exclusions and unreadable-field denominators retained separately.

Proposed targets: CER at most 0.5%, WER at most 1%, question precision/recall and fully correct options at least 99%, zero observed critical-token errors, and no unresolved missing/split/merged items in the evaluated set. Boundary/split/merge audits, passage links, critical-token annotation coverage, stratum results and uncertainty analysis remain separate release gates; the current text scorer deliberately cannot issue an overall PASS. These are targets, not achieved results. Source terms, corpus completeness, independent reviewers and research-protocol approval remain pending.

There are currently **zero human gold reference items**. CER/WER and empirical corpus accuracy are unknown; the benchmark gate is **NOT ASSESSED**. Passing software tests or Luna inspection does not establish high extraction accuracy.

## Software verification

Acceptance criteria and synthetic fixtures preceded behavior changes. No-op implementations failed cleanup/traceability, safe-application and edit-distance/gold-gate tests; further regressions failed option metadata/whitespace handling, ASCII/contextual-symbol coverage, encoding-damage rejection and per-stratum reporting before their fixes. All 42 extraction tests pass. Tests include missing/extra items, swapped options, altered negation, section numbers and dates, stale spans, missing source evidence, input immutability and overwrite refusal. These validate software behavior, not the accuracy of the papers.

Artifact checks cover record/ID counts, out-of-scope identity, preservation of original fields and six accepted decisions, exact replacement spans, source/corpus input hashes, output hashes, source-image evidence, and blank human references. The harness suite ran 16 tests with six shell tests skipped; sync/check reports zero errors/warnings. Due lesson consolidation was completed without adding redundant rules. Review-file content/count/hash checks passed; interactive browser behavior was not exercised.
