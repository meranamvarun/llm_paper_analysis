# Initial corpus analysis — 10 November 2026

Status: exploratory inventory, not reviewed question-pattern findings. Protocol and codebook remain drafts. Primary researcher and reviewers: TO CONFIRM.

## Source and reproducibility

Local source: `question_paper (1).pdf`, 9,679,967 bytes, 466 PDF pages.
SHA-256: `d3905f6d3c31af4cdf5d47d3e6380179c5fd2c8f55e489648d140783b06a0d3b`.
On 10 November 2026, the user reported obtaining the PDF from the website of the Consortium of NLUs. This is user-reported acquisition provenance, not independently verified provenance for this exact compilation. Exact download URL, access date and applicable rights terms remain unconfirmed. Original unchanged; full extracted text and image samples remain in ignored `data/inventory/`.

Extracted all pages with pypdf 6.14.2, default `extract_text()`. Retained text without OCR corrections. Local records: `manifest.json`, `pages.jsonl`, `candidate_papers.json`, `quality_flags.json`, `pilot_questions.jsonl`, `run_notes.json`, and `visual_sample.jpg`. This was an exploratory inspection, not a new reusable extraction pipeline. No paid API calls were made.

## Candidate coverage

CLAT PG is identified in source headings. The compilation appears to contain 13 exam-year labels spanning 2014–2026, with the user subsequently selecting 2016-2026 inclusive (11 year labels) on 10 November 2026. The 2014-2015 material is retained outside study denominators. Candidate boundaries below rely on extracted headings, adjacent keys and sampled page images; they do not establish completeness, authenticity or independent administrations.

| Exam-year label | Candidate paper PDF pages | Separate key PDF pages | Inventory notes |
|---|---|---|---|
| 2026 | 1–48 | 49–50 | Key labelled provisional; page 49 states administration on 7 December 2025 |
| 2025 | 51–94 | 95–96 | Year inferred from adjacent key labelled final; paper linkage needs review |
| 2024 | 97–142 | 143–144 | Extra rough-work pages with a different set symbol at 141–142; inspect version mixing |
| 2023 | 145–188 | 189 | Key labelled provisional |
| 2022 | 190–225 | 226–227 | Key labelled final |
| 2021 | 228–257 | — | Inline answer labels; authority unverified |
| 2020 | 258–292 | — | Inline answer labels; authority unverified |
| 2019 | 293–309 | — | Cover describes 32 pages, but apparent span has 17; Part B essay prompts on page 309 |
| 2014 | 310–337 | — | Year visible on scanned cover; no extracted text throughout this span |
| 2015 | 338–371 | — | Heading readable; question-page extraction garbled |
| 2016 | 372–399 | — | Section-based question numbering needs compound IDs |
| 2017 | 400–432 | — | Heading readable; question-page extraction garbled |
| 2018 | 433–466 | — | Numbering resets in later section; visible answer markings, authority unverified |

An em dash means no separate key was identified in this inventory, not proof of absence. Year labels must be distinguished from actual administration dates. Do not calculate judgment lags from the label alone.

## Extraction quality and sample

- 29/466 pages (6.2%) yielded no text: page 293 and pages 310–337. A visual sample shows that no-text pages include a substantive cover and rough-work pages; this is not a count of missing question pages.
- 65/466 pages (13.9%) contain more than 10% non-whitespace control characters: pages 339–371 and 401–432. This exploratory diagnostic identifies font/text decoding problems, not an OCR accuracy estimate. Sampled images contain readable questions despite garbled extraction.
- Together these flags affect 94/466 pages (20.2%); remaining pages have not been certified accurate. Neither percentage uses questions as its denominator.
- A nine-page contact sheet was inspected (PDF pages 1, 3, 293, 310, 311, 337, 339, 401, 433). This is a visual spot check, not complete scan review.
- Three question records were extracted as a boundary sample: printed question 1 on PDF pages 3 (2026), 295 (2019) and 433 (2018). IDs use the full source hash, PDF page and printed number. Raw character offsets permit exact round-trip verification. Options remain in raw text. Passage linkage is retained for the 2026 item. All three remain unreviewed and uncoded; this is not the prespecified independent-coding pilot.

## Implications and next analysis

The compilation mixes passage-based MCQs, section-numbered material, essay prompts, standalone keys and answer-marked copies. Treat passages and questions separately, and separate questions offered from questions required in essay sections. A single total question denominator would currently be unreliable.

The intended range is now 2016-2026 inclusive. Resolve source rights, verify candidate paper boundaries, and inspect 2019 completeness. Recover scanned and garbled text locally without replacing raw extraction. Check version mixing and duplicate scans before counting administrations. Then define and test a reusable question extraction pipeline with synthetic fixtures; finalize the sampling plan for independent human coding before subject and recurrence estimates.

No exact-repeat rate, subject prevalence, judgment recurrence or decision-to-exam lag is reported. Those require reviewed extraction and coding; case names in questions have not been independently verified against authoritative judgments.

## Verification evidence

Source hash unchanged after processing; 466 page records match PDF page count; 29 no-text and 65 high-control-character flags checked; three unique sample IDs and raw spans verified against stored page text. Harness check passed before this note was created; final checks are recorded in the session retro. Initial console display hit Windows encoding limitations after files had been saved; subsequent inspection explicitly used UTF-8. No source text was repaired.
