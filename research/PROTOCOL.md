# Draft research protocol

Status: planning; examination, team and venue [TO CONFIRM]. User-selected study range: 2016-2026 inclusive (11 examination-year labels), confirmed on 10 November 2026. No empirical findings yet.

## Questions
1. Which subjects, doctrines and judgments appear, and how does their distribution change by year?
2. How often do exact or near-identical questions recur, versus broader themes or judgments?
3. What is the interval between a verified judgment's decision date and its examination appearance?
4. How do format and cognitive demand vary across years and subjects?

## Corpus and units
Inventory every paper with file hash, source, access date, examination, administration date, year, version/set, page span, answer-key provenance and rights status. Verify coverage of the user-selected 2016-2026 inclusive range from the actual papers. Retain 2014 and 2015 source material and exploratory audits, but exclude those years from study denominators. Eleven year labels do not establish eleven complete, unique administrations. Record missing administrations, incomplete scans, duplicate sets and syllabus/format changes. Findings apply to the sampled examination(s); do not generalize to all Indian LL.M. entrances.

Use the question as the primary unit, linked to a passage where applicable. Preserve subquestion and shared-passage relationships. Track question counts and marks separately. Deduplicate duplicate scans before calculating frequency. Separate paper versions from independently administered examinations.

## Extraction and coding

Workflow amendment, 11 November 2026: the user declined manual extraction benchmarks and chose programmatic validation. Continue local extraction work using the automated quality specification in `AUTOMATED_QUALITY_SPEC.md`: structural invariants, source OCR corroboration, higher-resolution targeted rechecks and synthetic defect challenges. Previous blind human extraction packets are retained as optional historical artifacts, not required work for continuation. Automated checks do not establish human-reviewed labels or a gold-standard error rate. Preserve machine disagreements and uncertainty; do not gate progress on obtaining human extraction reviewers.
Preserve raw OCR alongside corrected text and a correction log. Programmatically check question boundaries, options, pages, dates and case-name text against source evidence, retaining unresolved disagreements. The separate subject/legal coding pilot below remains a draft research-validation design, not a required manual extraction benchmark. Pilot a stratified sample across years and formats; finalize sample size and sampling seed before coding. Two independent reviewers code the pilot before adjudication. Report raw agreement and appropriate chance-corrected agreement, with multi-label methods and uncertainty specified before full analysis. Revise and version the codebook, then freeze it. Audit a prespecified sample of the remaining corpus.

Code subject, doctrine, theme, judgment relationship and cognitive demand. Separate explicit case references from reviewer-inferred links. Verify judgments using official court texts or other authoritative primary sources, capturing citation, decision date, URL and pinpoint evidence. Unresolved links stay unresolved. Answer keys do not automatically validate legal interpretations.

## Repetition and time analysis
Keep raw text unchanged. Define and version normalization rules before exact matching; preserve negation, dates, numbers and option changes. Near-duplicate detection proposes pairs; human review determines equivalence. Shared subject, case or passage alone is insufficient. Store pair-level rationale and group membership; count both repeated items and unique repeat groups with explicit denominators. No arbitrary similarity threshold is treated as truth; calibrate on reviewed pairs.

Report per-year counts and proportions, overall and subject-specific denominators, missing/unreviewed counts, recurrence intervals and sensitivity to uncertain labels. Multi-label totals can exceed the question count. For judgment lag use the decision and actual exam dates; flag unknown or negative lags. Compare coverage with syllabus/format changes. Treat trends as descriptive unless inferential hypotheses and methods are prespecified. Document multiple comparisons, dependence within passages/papers and sensitivity analyses if inference is pursued. Historical recurrence alone does not establish prediction of future papers.

## Reproducibility and publication
Freeze source manifests, extraction version, codebook, reviewed labels and analysis configuration. Record hashes, software versions, random seeds and AI provenance. Maintain a claim-to-table/source ledger and verified bibliography. Report selection bias, OCR errors, incomplete coverage, subjective coding, rights limits and single-exam generalizability. Confirm permissions and any institutional research-review requirements; do not assume exemption. Publish shareable derived aggregates and code after rights review, with manuscript results populated only from verified analysis.
