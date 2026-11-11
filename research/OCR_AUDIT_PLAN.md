# Random AI extraction audit plan

Date: 10 November 2026. Exploratory quality check, separate from the prespecified independent human coding pilot. No extracted records will be changed or marked reviewed.

Reviewer: a separate agent requested as `gpt-6-luna`, medium reasoning. Available session agent metadata describes Luna as the affordable model; official model documentation confirms image input. Official Codex rates list lower input/output credit rates for Luna than the other models exposed in this session. Exact runtime snapshot and billed cost may be unavailable. No separate API or paid OCR service will be launched. Model capability is being tested, not presumed from price.

Model-selection sources fetched on the audit date: [GPT-6 Luna model and modalities](https://developers.openai.com/api/docs/models/gpt-6-luna) and [Codex credit rates](https://learn.chatgpt.com/docs/pricing). API token prices and included Codex subscription usage are different accounting systems; no dollar estimate is inferred for this audit.

Sampling is fixed before reviewer inspection: Python Random seed 20261110; sample four native-extracted and four Tesseract-extracted pages without replacement, independently within each stratum. Population: all configured candidate body pages, including blank or wholly missed pages. No selection based on successful question extraction or existing issue flags. This is a stratified page sample, not a simple random question sample. Do not extrapolate a corpus error rate from the small sample.

Render source page images locally at 180 DPI. Reviewer first sees only source images and a blind manifest, records every visible question number/continuation, and transcribes at most the first two complete questions per page (or fewer if unavailable). Preserve unreadable spans as uncertain. Do not infer missing options, text, answers, case citations or legal interpretations. Save and hash blind observations before opening any extraction output.

Second stage compares those observations to the frozen run `data/extraction/runs/20261110T043421397159Z`. Classify matched/missing/extra/split/merged question boundaries; stem omissions/substitutions; option omissions, order and label problems; passage linkage if visually clear; uncertainty and page continuations. Source excerpts and reviewer outputs stay in ignored `data/`. Record page-level and item-level denominators; abstentions remain explicit. Whitespace/layout-only differences should be distinguished from substantive transcription changes. Do not call either model output human ground truth or calculate character error rates without aligned, verified reference text.

Deliverables: sampling/provenance manifest, frozen blind observations, comparison observations, concise aggregate findings and selected source-page checks by the parent agent. Preserve disagreement between AI reviewers. The audit does not authorize editing the parser, source, extracted questions, reviewed codes or answer keys.
