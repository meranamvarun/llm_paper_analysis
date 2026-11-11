# Self-improvement harness

Primary researcher: TO CONFIRM. AI tools (Claude Code, Codex and others) are drafting and verification aids; every change the harness makes to the process reaches `main` only through a PR the researcher reviews.

The harness makes each agent session a little better than the last on three measures:

| Goal | Measured by |
|---|---|
| **Quality of output** | self score and researcher score (1-5), user corrections, rework, what was verified |
| **Tokens (less is better)** | total, weighted and peak-context tokens read from the tool's own transcript |
| **Process completion** | outcome (completed / partial / blocked / abandoned), handoff note kept current |

## The loop

1. **Push at session start.** Every tool loads the playbook (`PLAYBOOK.md`, about 500 tokens) through its instruction file. In Claude Code and Codex a SessionStart hook also injects a short status block with the session id, retro counts, whether consolidation is due, the Python to use, git hook state and sync warnings.
2. **Work** under the playbook rules (IDs like `T1`, `Q2`, `C1`).
3. **Retro at the end.** If the session changed files, the agent runs a single `harness.py retro ...` command. It writes `sessions/<date>_<tool>_<id>.yaml`, reading token metrics from the transcript and taking the qualitative answers from flags. In Claude Code and Codex a Stop hook asks for the retro if the agent forgets, at most once per repo state.
4. **Consolidate** after 5 new retros, or sooner when one is marked `--urgent`. `harness.py consolidate` groups lessons across sessions, shows metric trends and flags rules that are missed or unused. The agent then edits `PLAYBOOK.md`: it promotes recurring lessons, automates rules that keep being missed, and retires dead ones, all within a 4,000-character budget. It runs `sync` and `check`, and records the round with `consolidate --done`. The retros move to `sessions/consolidated/` and `CHANGELOG.md` gets an entry.
5. **Review.** The researcher reviews the PR and can score any session with `harness.py rate <id> <1-5> --note "..."`. Where a researcher score exists, reports use it instead of the self score.

## How each tool gets the playbook

| Tool | Playbook | Status and retro nudge |
|---|---|---|
| Claude Code (CLI, desktop, web) | `CLAUDE.md` imports `@harness/PLAYBOOK.md` | `.claude/settings.json` hooks |
| Codex | `AGENTS.md` (generated; playbook inlined) | `.codex/hooks.json` hooks (trusted projects; approve each hook once) |
| Gemini CLI | `GEMINI.md` imports `@./AGENTS.md` | none: playbook loop text only |
| Cursor, GitHub Copilot agent and other AGENTS.md readers | `AGENTS.md` | none: playbook loop text only |
| Aider | add `read: AGENTS.md` to `.aider.conf.yml` | none |

`AGENTS.md` is generated from `CLAUDE.md` + `PLAYBOOK.md` by `harness.py sync`. Edit those two files, never `AGENTS.md`. `check`, the SessionStart status and `.githooks/pre-commit` all catch a stale copy. Only the `@harness/PLAYBOOK.md` import is inlined, so don't add other `@` imports to `CLAUDE.md` without extending `sync`.

## Commands

Run them with the Python the status line names: `python3` on Linux, macOS and cloud sessions. On Windows use the full path in `CLAUDE.md`, because PATH `python` is a Store stub.

```
harness.py retro --outcome completed --task-type lit-review --task "Review recurring constitutional themes" --score 4 \
  --corrections 0 --rework 1 --checks "source checks on reviewed case links" --waste "read candidates file whole" \
  --lesson "tokens | Search the corpus manifest by paper ID before reading it | 46 KB read twice" \
  --helped T1,C2 --missed T2          # one per session; rerun to update; --dry-run to preview
harness.py rate 29ed7271 3 --note "missed two references"   # researcher's score
harness.py report                     # trends by task type, last-5 vs previous-5, rule usage
harness.py consolidate [--done --note "added T4: ..."]
harness.py sync                       # regenerate AGENTS.md
harness.py check                      # budget, sync, hook configs, retro schema, identifier scan
python3 -m unittest discover -s harness/tests
```

Values: tool `claude-code|codex|gemini-cli|cursor|copilot|other`; task type `lit-search|lit-review|writing|citation-check|analysis|admin|tooling|other`; lesson tag `tokens|quality|completion`.

**Score rubric:** 5 = all asks met and verified, no rework. 4 = minor gaps or light verification. 3 = the user had to correct something, or part was missing or unverified. 2 = major rework or missed asks. 1 = failed.

## Metrics

- **Tokens** are parsed from the transcript: Claude Code `~/.claude/projects/*/<session>.jsonl` (plus subagents), Codex `~/.codex/sessions/**/rollout-*.jsonl`. One Claude API response spans several transcript lines that repeat the same usage, so the parser counts each message id once. `total` = input + cache writes + cache reads + output. `weighted` counts each class at its list-price ratio to plain input. Claude: cache write 1.25x (5 min) or 2x (1 h), cache read 0.1x, output 5x. Codex: cached input 0.1x, output 8x. This tracks cost better than `total`, which cheap cache reads dominate, but compare it within one tool. `peak_context` is the largest single request and the best early sign of bloat (large files or skills loaded into context). Tools without a transcript record `--tokens` if they show a count, else `none`.
- **Quality:** `self_score`, `user_score`, `corrections`, `rework`, `checks`.
- **Completion:** `outcome`, `handoff`. `report` shows the share completed.
- **Rule feedback:** `--helped` and `--missed` rule IDs. `report` marks rules with more misses than helps (`strengthen/automate?`) and rules unused in the last 10 sessions (`retire?`).

## Guardrails

- The playbook refines `CLAUDE.md`/`AGENTS.md` and never overrides them: source rights and research integrity, verified citations and attribution come first.
- **No private personal data in harness files.** `retro`, `rate` and `consolidate` refuse text that looks like a record number, accession number, long digit run or email. `check` scans all retros, `PLAYBOOK.md` and `CHANGELOG.md`. Use public corpus IDs only.
- No model identifiers are written: retros record the tool, not the model.
- Every retro and changelog entry states `Primary researcher: TO CONFIRM`. Retros are an audit trail of AI assistance and document AI assistance.
- The playbook stays under 4,000 characters, since every session pays for it. Retros are never loaded at session start.
- Hooks fail open: missing Python, git or state never blocks a session. The Stop hook never blocks a continuation it caused (`stop_hook_active`), and asks again only after the repo changes.

## Setup and opt-out

- **Git hooks:** the SessionStart hook sets `core.hooksPath=.githooks` if it is unset and no other git hooks are installed. `commit-msg` then adds the `Primary-Researcher` trailer, and `pre-commit` blocks a stale `AGENTS.md`.
- **Windows:** Claude Code runs hooks through Git Bash. Codex runs `commandWindows` through `cmd.exe`, which calls `%ProgramFiles%\Git\bin\bash.exe`; edit `.codex/hooks.json` if Git lives elsewhere. The hook looks for a real Python in this order: `HARNESS_PYTHON`, the cached result, `python3`, `python`, `py -3`, then `%LOCALAPPDATA%\Programs\Python\Python3*\python.exe`. It caches the hit in `harness/.state/python`.
- **Codex trust:** Codex reads `.codex/hooks.json` only for a trusted project and runs a hook only after you approve it. Approval is tied to the hook's content, so an edited hook needs approving again.
- **Opt-out:** set `HARNESS_RETRO=off` to silence the retro nudge. Disable the hooks with Claude Code's `/hooks` menu, or remove the entries from `.claude/settings.json` or `.codex/hooks.json`.
- `harness/.state/` holds per-machine session bookkeeping and is git-ignored. `retro` prunes entries older than 30 days.

## LL.M. project adaptation

Researcher identity is unconfirmed; `TO CONFIRM` is an explicit placeholder in session records and commit trailers, not an authorship assignment. Once confirmed, update `RESEARCHER` in harness.py, attribution in hook configurations/scripts, tests and documentation together. No source-project retros or state were imported.

The inherited conservative identifier scanner applies only to process retros and playbook text. It is not a legal-citation validator; keep full case citations, public judgment identifiers and file hashes in the research provenance records rather than session lessons. Exact model/version provenance belongs in research run records; the harness itself records only the agent tool.

Install the harness dependency with `python -m pip install -r requirements.txt`. For complete Windows hook tests, add `C:\Program Files\Git\bin` to PATH for that test process.
