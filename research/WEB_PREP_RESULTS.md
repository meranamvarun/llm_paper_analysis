# CLAT PG Study Studio — local delivery

This is the local-build verification record, prepared before Git publication. Later commits and remote publication are recorded in Git history; the original test and archive evidence below is retained.

17 November 2026. The user requested a complete preparatory website with flashcards and other learning tools, ready for GitHub Pages. After checking the official date, the user confirmed **CLAT PG on 6 December 2026**. This supersedes the initial 13 December instruction. The default sprint has nineteen study days, 17 November–5 December inclusive.

## Deliverable

`site/` is a buildless, relative-URL static website. `output/clat-pg-study-studio.zip` is the standalone public-site package; `site/README.md` explains both standalone branch hosting and the repository's manual GitHub Pages workflow. The workflow at `.github/workflows/pages.yml` uploads only `site/` and runs only on manual dispatch. No commit, push or deployment was performed.

The website includes sixteen substantive modules, 128 original flashcards, 64 original standalone MCQs and eight original passage sets with three questions each: **88 original questions total**. Lessons teach rules, distinctions, pitfalls and self-explanation; practice supplies source-linked rationales and distractor explanations. It is a selective foundation/revision companion, not an exhaustive textbook, current-affairs digest, difficulty-calibrated mock programme or forecast of easy marks.

The learning loop combines retrieval before reveal, spaced returns, mixed practice after topic study, confidence before feedback, repair of wrong/uncertain answers and blind retests. A daily new-card cap and final-72-hour taper bound the queue. Correct final-day reviews are not put into a repeated ten-minute loop; forgotten cards return after ten minutes. Review intervals and time allocations are editorial heuristics, not a validated CLAT optimiser. See `WEB_LEARNING_METHODS.md` and the public `learning-evidence.json` for primary-study evidence and transfer limits.

## State and privacy

Browser-local storage retains card dates, lesson notes, attempted-question history, repair rules, practice scores, calendar checks and unfinished quizzes. Import validates the schema and content IDs before confirmation/replacement; malformed imports preserve good state. Storage failure is visible. Export/restore allows moving between browser origins/devices. User notes are escaped, not injected as HTML. No analytics, sign-in, paid API or remote progress service is used. Initial assets and external sources still need connectivity; offline caching is not promised.

## Evidence boundaries

The source registry records 37 references across legal and learning sources, with specific pinpoints and retrieval/version qualifications. Some direct source access was blocked or timed out; those entries explicitly distinguish inspected indexed provisions from full-text retrieval. Statutory extracts from historical editions are not described as complete current consolidations. Original legal teaching summaries remain AI-drafted with qualified review pending; no historical legal answers or exam–judgment links were invented.

Only aggregate historical cue observations appear publicly. The working corpus, PDF, question text, private source downloads, annotations and student QA backups stay outside `site/` and the ZIP. The original source/extraction hashes are verified against the earlier manifest. Researcher/team attribution remains TO CONFIRM.

## Test evidence

Red: the core browser-module tests failed before `site/core.js` existed. The content completeness tests then failed on the partial ten-topic/zero-passage draft. Green: all 32 analysis tests pass, including five browser-executed core tests and three content-integrity tests. Coverage includes India-local date arithmetic, leap dates, new-card taper, lapse timing, final-day schedule, correct/wrong/skipped scoring, state rejection, daily caps, distinct source/card IDs, lesson coverage, answer indices/options, original-passage provenance and encoding.

The isolated headless-Chrome end-to-end checker passes: lesson search, private notes/reload/HTML escaping, recall attempt gate and due persistence, correct confidence/feedback/skip scoring, notebook repair/blind retest/history, simulation feedback withholding, reload/resume and expiry submission, eight passage sets, nineteen calendar dates/checks, actual exported-file download, invalid-import preservation, valid restore and visible storage denial. Mobile 390×844 checks cover all main views, lessons, recall and active passage questions, with no body overflow. Passage collapse survives moving between questions; focus moves to newly revealed answers/feedback. Browser console is empty. Desktop/mobile screenshots were captured and inspected. QA uses an isolated temporary profile, never the user's browser.

Harness suite: sixteen tests run successfully, six shell tests skipped. No shell-hook validation is claimed. Harness check and final archive/source integrity results are in the release record. A test-fixture timestamp was corrected, a search expectation was narrowed to a unique term, and browser automation was made insensitive to smooth-scroll timing; those were fixture/automation issues, not evidence of legal accuracy.

Reproduce: `python -m unittest discover -s analysis/tests`; serve repository root at port 8765, then `python -m analysis.check_prep_browser`. Optional development browser dependency is in `requirements-prep-test.txt`. The public website has no dependency installation/build step. Current release file hashes and ZIP hash are in `WEB_PREP_RELEASE.json`.
