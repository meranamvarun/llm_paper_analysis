# Indian LL.M. entrance examination pattern research

Study judgment references, recurring themes and repeated questions across the user-selected 2016-2026 inclusive study range (11 examination-year labels), with reproducible evidence suitable for a possible research paper.

Start with [next steps](research/NEXT_STEPS.md), the [draft protocol](research/PROTOCOL.md), and the [coding manual](research/CODEBOOK.md). Exam identity and year coverage have not yet been verified. The supplied `question_paper (1).pdf` remains unchanged and has not been extracted during harness setup.

The [session harness](harness/README.md) was adapted from `C:/Users/malai/varun_code/ai-pathology-recreate-paper`. It includes instruction sync, session retrospectives, token metrics, consolidation, Codex/Claude hooks and regression tests. Source-project sessions, clinical material and machine state were excluded. Researcher attribution is deliberately `TO CONFIRM`.

```powershell
python harness/harness.py sync
python harness/harness.py check
python -m unittest discover -s harness/tests
```

Git Bash is needed for shell hooks and their tests. Hook activation depends on client support/trust; copying configuration does not prove that hooks have run. Session-start may configure local Git hooks when none are installed. No commits or publication are automatic.

Store restricted corpus text and intermediate outputs in ignored `data/`. The existing root PDF is also ignored to avoid accidental redistribution. Hash and inventory it before extraction; do not move or overwrite the original. There is no extraction or analysis pipeline yet.
