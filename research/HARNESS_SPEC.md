# Harness adaptation specification

Adapt the source project's reusable session harness for Indian Master of Laws entrance-exam research. Do not copy source sessions, machine state, clinical material, manuscript content or researcher identities.

Acceptance criteria:
- Sync generates AGENTS.md from this project's CLAUDE.md and playbook.
- Session records and commit trailers use the explicit placeholder TO CONFIRM until a researcher is named.
- Preserve token accounting, retrospective validation, rating, consolidation and hook behavior; use synthetic fixtures in tests.
- Research instructions require question/page provenance, judgment verification, uncertainty and human coding review.
- No claim that the supplied PDF has been extracted or that ten-year coverage is verified.

Verification: inherited harness regression suite; attribution assertions updated to the new placeholder before implementation (red), then adapted harness and hooks (green); sync and check; source-specific text scan. Documentation gets consistency review.

## Verification evidence ? 2026-11-10
- RED: updated attribution regression failed with expected TO CONFIRM versus inherited identity. An earlier run had incomplete fixture files; corrected before the meaningful red run.
- GREEN: default unittest discovery passed 16 tests, with 6 POSIX-shell tests skipped because sh was not on PATH.
- Full Git Bash run attempted with Git bin on PATH; shell tests stalled and the test process tree was stopped. Full Windows hook verification remains incomplete. No claim of active client hooks.
- `harness.py sync` and `harness.py check` passed (zero errors/warnings). Source-specific manuscript hook removed; no source researcher identity remains.
- Supplied PDF unchanged by setup. SHA256: D3905F6D3C31AF4CDF5D47D3E6380179C5FD2C8F55E489648D140783B06A0D3B. Contents not inspected.
