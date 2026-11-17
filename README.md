# CLAT PG Study Studio and LL.M. paper research

The public preparation website is in [site/](site/). It includes sixteen topic lessons, 128 flashcards, 88 original practice questions, spaced reviews, passage drills, a mistake notebook and an editable plan targeting **6 December 2026**. Material is AI-assisted and source-linked; qualified legal review remains pending.

## Host this repository on GitHub Pages

Keep the website in `site/`. The [Pages workflow](.github/workflows/pages.yml) uploads that folder directly to the Pages project root.

1. Commit and push the intended website files and workflow when ready. Avoid blindly staging the existing research data.
2. In [repository Pages settings](https://github.com/meranamvarun/llm_paper_analysis/settings/pages), set **Source** to **GitHub Actions**.
3. Open [Publish Study Studio to GitHub Pages](https://github.com/meranamvarun/llm_paper_analysis/actions/workflows/pages.yml), choose **Run workflow**, and select the branch containing the website.
4. Use the address returned by the successful deployment. Without a custom domain, the expected address is **https://meranamvarun.github.io/llm_paper_analysis/**.

The expected address is not a claim that the website is already live. No `/site/` suffix or ZIP upload is needed for this repository. The manual workflow publishes only `site/`; research folders and PDFs are outside the Pages artifact. No commit, push or deployment is automatic. See [the full site guide](site/README.md) for preview and backup/restore instructions.

## Research workspace

Study judgment references, recurring themes and repeated questions across the user-selected 2016-2026 inclusive study range (11 examination-year labels), with reproducible evidence suitable for a possible research paper.

Start with [next steps](research/NEXT_STEPS.md), the [draft protocol](research/PROTOCOL.md), and the [coding manual](research/CODEBOOK.md). Extraction and exploratory analysis are implemented. Corpus completeness, administration identity, independent semantic coding and legal adjudication remain unresolved. The supplied original PDF remains unchanged.

The [session harness](harness/README.md) includes instruction sync, session retrospectives, token metrics, consolidation, hooks and regression tests. Researcher attribution remains `TO CONFIRM`.

```powershell
python harness/harness.py sync
python harness/harness.py check
python -m unittest discover -s harness/tests
```

Git Bash is needed for shell hooks and their tests. Hook activation depends on client support/trust; copying configuration does not prove that hooks have run. Session-start may configure local Git hooks when none are installed. No commits or publication are automatic.

Keep restricted corpus text and intermediate outputs local under ignored `data/`. The root PDF is excluded to avoid accidental redistribution. Do not move or overwrite originals, or redistribute papers without checking source rights. The public website uses original teaching scenarios rather than extracted examination text.
