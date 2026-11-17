# CLAT PG Study Studio — acceptance specification

17 November 2026. User confirmed CLAT PG on 6 December 2026 after correcting the initially supplied 13 December date. Nineteen study days: 17 November through 5 December. Build a complete static preparation website, ready for GitHub Pages; publication/commit/push is not requested.

## Content and evidence

Provide sixteen substantive foundation modules, 128 original flashcards, 64 standalone original MCQs and eight original passage sets with three questions each. All legal answers and lessons must identify primary/statutory/academic source URLs and pinpoints; source checking is distinct from qualified legal review. Preserve historical-law/version caveats. Do not distribute original examination texts, source PDFs, raw AI/research records or answer-key guesses. Original educational scenarios must be labelled original. Do not claim comprehensive syllabus mastery or guaranteed easy marks. Historical cue counts are exploratory and overlapping, not subject weightages. Learning-method sources should support retrieval, feedback, spacing, self-explanation and cautious interleaving, not a purported optimal exam algorithm.

## Functional acceptance

- Buildless relative-URL HTML/CSS/ES modules/JSON work under a GitHub project subpath.
- Default plan covers 19 study days before 6 December; India-local calendar dates avoid UTC rollover bugs. Target date and daily time budget editable; final 72 hours default to no new cards.
- Today page shows real activity, due cards, daily capped new cards, study tasks and weak-topic practice.
- Lessons provide doctrine, distinctions, pitfalls, source links and a closed-book explanation tool.
- Recall requires an attempted answer before reveal, then self-rating; responses persist with due dates. Misses return after ten minutes; successful reviews expand over days, capped before the target when applicable. No fake AI grading or exam-probability score.
- Quiz supports topic/mixed practice, confidence before answer, explanations after commit, original passage sets, configurable timer, explicit skipped/expired items, +1/−0.25 scoring and error-log integration.
- Mistakes can be repaired with a rule and retested without showing the answer first; original attempt history retained. Confidence-wrong responses surfaced for repair.
- Date-aware plan and completion checks survive reload. Export/import validated progress JSON; reject malformed/oversized/foreign-content records without replacing good state. Storage failure is visible. Provide explicit reset confirmation. No login, analytics or remote progress transmission.
- Keyboard/accessibility: visible focus, labelled controls, announcements for answers/results, mobile navigation and no body overflow at 390px. Source explanations and content status discoverable without interrupting the study loop.
- GitHub Pages workflow deploys only `site/` and only on manual dispatch. ZIP contains public site assets and licence, not restricted research data. Deployment README names exact steps.

## Verification

Observe a failing core-module test before implementation. Test calendar arithmetic, leap/date validation, no-new-card taper, spaced intervals and same-day lapse, scoring and skipped answers, state validation/migration, daily new-card cap, independent missed-topic prioritisation and project-subpath assets. Then test real content cardinality, source references, unique IDs, correct option ranges, no duplicate options/embedded HTML, every lesson section populated and original-passage provenance. Browser-check lesson/recall/quiz/passage/mistake/plan/export-import/reload flows, timer expiry, desktop and 390px mobile, console errors and keyboard reachability. Run relevant analysis tests and harness checks; keep evidence, handoff and one retro. Freeze public release content/code hashes with qualified-review status still pending. No original corpus or coding ledger changes.
