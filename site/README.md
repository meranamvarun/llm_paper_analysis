# CLAT PG Study Studio

A buildless study website for the 19 study days from 17 November through 5 December 2026. The confirmed target is CLAT PG on **6 December 2026**, not 13 December. Dates and daily minutes are editable in settings.

## Included

- Sixteen substantive foundation topics with rule explanations, distinctions, pitfalls and sources.
- 128 original flashcards; recall before reveal, honest self-rating and spaced returns.
- 64 original standalone MCQs and eight original passage sets with three questions each: **88 questions total**.
- Topic/mixed practice, simulation mode, timers, confidence checks, +1/−0.25 scoring and explanation review.
- A mistake notebook that retains error history and corrected rules, including uncertain correct answers.
- A date-aware study calendar, progress checks, private lesson notes and a focus timer.
- Browser-local persistence and validated JSON backup/restore. No account, remote progress service, analytics, paid API or build dependencies.

These are original teaching scenarios, not copied previous examination questions. The short sets are not validated full-length mock examinations. Legal summaries are AI-assisted with primary references; qualified legal review remains pending. The studio is a selective sprint companion, not an exhaustive textbook, current-affairs digest or guarantee of easy marks. Sources and version warnings appear in the site.

## Preview locally

Serve this folder over HTTP; do not double-click `index.html`, because browsers restrict JSON/module loading from `file://`.

From the repository root, using an installed Python:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open `http://127.0.0.1:8765/`. Stop the server with Ctrl+C. On Windows, use `py -3` or the installed Python executable if `python` is not on PATH. Any ordinary static server works. No installation is required for the hosted public website.

## Host this repository with the supplied GitHub Actions workflow

1. Review the public files under `site/`. Keep restricted papers and research data outside it.
2. Commit/push **only the intended files** when you are ready. The supplied work does not itself commit, push or publish anything. Avoid blindly staging the repository's pre-existing untracked research data.
3. In GitHub, open the repository → **Settings → Pages → Source → GitHub Actions**.
4. Open **Actions → Publish Study Studio to GitHub Pages → Run workflow**, choosing the branch containing the site.
5. Use the deployed address returned by the completed action. The workflow uploads **only `site/`**, not the repository root.

The workflow is manual (`workflow_dispatch`), uses the Pages environment and required permissions, and does not deploy on every push. Its action versions follow the official GitHub Pages documentation checked on 17 November 2026: [custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Host the standalone ZIP in a new repository

Extract the contents so `index.html`, `app.js`, `core.js`, the JSON files and styles are at the repository root. Upload/commit those files, including `.nojekyll` and `LICENSE`. In **Settings → Pages**, choose **Deploy from a branch**, the desired branch and **/(root)**. Do not copy the parent repository's workflow unchanged into this standalone layout: that workflow expects a `site/` subdirectory.

All asset and data URLs are relative. Project URLs such as `https://OWNER.github.io/REPOSITORY/` are supported. There is no SPA rewrite requirement because navigation uses URL hashes.

## Progress and privacy

Progress belongs to this browser, origin and address. Clearing browser data removes it; moving between localhost and GitHub Pages creates separate stores. Use **Plan & backup settings → Export my progress**, then import on the other address/device. Import validates the schema/content IDs before replacing state and asks for explicit confirmation. Keep backups private if your notes contain personal details.

Changing the exam date retains existing card schedules and changes the new-card taper/calendar. Clock-based features depend on the device clock. Dates use Asia/Kolkata. The website needs a network connection for its initial assets and source links; offline caching is not implemented or promised.

## Content and verification

`content-foundations.json` and `content-breadth.json` contain public original material and a source registry. `learning-evidence.json` records primary learning studies and official exam references. No PDFs, raw past-paper text, historical answer guesses or student progress backups are shipped. Source documents are linked rather than bundled. A few source entries explicitly record partial/indexed access or historical editions; do not interpret them as a claim of complete current consolidation.

Tests and QA tools live outside the deployable folder. From the repository root, run:

```powershell
python -m unittest analysis.tests.test_prep_core analysis.tests.test_prep_content
```

Core tests use an isolated headless Chrome through Selenium available on this development machine. They are not a runtime requirement for students. The public release manifest records site hashes and verification results in the research handoff.

For a fresh development machine, the optional browser-test dependency is pinned in the parent repository's `requirements-prep-test.txt`. Install it in a development environment and provide Chrome. To run the end-to-end checker, serve the **repository root** at port 8765 (so the site is at `/site/`) and run `python -m analysis.check_prep_browser`. That checker uses an isolated temporary browser profile and private QA output; it never uses a student's saved progress.

Code/original authored material follow the accompanying repository MIT licence. Linked third-party sources retain their own rights. AI assistance is disclosed in the application; research-team attribution remains TO CONFIRM.
