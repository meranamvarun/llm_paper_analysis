#!/usr/bin/env python3
"""Self-improvement harness for agent sessions in this repo (Claude Code, Codex, other tools).

Primary researcher: TO CONFIRM. AI tools are drafting/verification aids, never authors.

  retro        record this session's retro; token metrics are read from the tool's transcript
  rate         add the researcher's own 1-5 score to a retro
  report       trends for tokens, quality and completion
  consolidate  review lessons + metrics and edit PLAYBOOK.md; --done records the consolidation
  sync         regenerate AGENTS.md from CLAUDE.md + harness/PLAYBOOK.md
  check        lint budget, sync, retro schema and identifiers (exit 1 on errors)

See harness/README.md. Stdlib only, except PyYAML for reading retros (in requirements.txt).
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import glob
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent
PLAYBOOK = HARNESS / "PLAYBOOK.md"
CHANGELOG = HARNESS / "CHANGELOG.md"
SESSIONS = HARNESS / "sessions"
ARCHIVE = SESSIONS / "consolidated"
STATE = HARNESS / ".state"
CLAUDE_MD = ROOT / "CLAUDE.md"
AGENTS_MD = ROOT / "AGENTS.md"
GEMINI_MD = ROOT / "GEMINI.md"
HOOK_CONFIGS = (ROOT / ".claude" / "settings.json", ROOT / ".codex" / "hooks.json")

RESEARCHER = "TO CONFIRM"
IMPORT_LINE = "@harness/PLAYBOOK.md"
GENERATED_NOTE = ("<!-- Generated from CLAUDE.md and harness/PLAYBOOK.md by `harness.py sync`; "
                  "edit those files, not this one. -->")
PLAYBOOK_MAX_CHARS = 4000   # ~1k tokens: loaded into every session, so it must stay lean
PLAYBOOK_WARN_CHARS = 3400
CONSOLIDATE_EVERY = 5       # unconsolidated retros that make a consolidation due
MAX_LESSONS = 3
STATE_TTL_DAYS = 30

TOOLS = ("claude-code", "codex", "gemini-cli", "cursor", "copilot", "other")
TOOL_ALIASES = {"claude": "claude-code", "gemini": "gemini-cli"}
TASK_TYPES = ("lit-search", "lit-review", "writing", "citation-check", "analysis", "admin", "tooling", "other")
OUTCOMES = ("completed", "partial", "blocked", "abandoned")
LESSON_TAGS = ("tokens", "quality", "completion")
FREE_TEXT = ("task", "waste", "handoff")
# Input-token equivalents per token class (list-price ratios). Compare sessions within one tool.
WEIGHTS = {
    "claude-code": {"input": 1.0, "cw5m": 1.25, "cw1h": 2.0, "cache_read": 0.1, "output": 5.0},
    "codex": {"input": 1.0, "cw5m": 1.25, "cw1h": 1.25, "cache_read": 0.1, "output": 8.0},
}
IDENTIFIER_PATTERNS = (
    (re.compile(r"\b(?:UHID|MRN|IPD|OPD|CR|IP|Hosp(?:ital)?|Lab|Biopsy)\s*(?:no\.?|num(?:ber)?|#)\s*[:#-]?\s*\w*\d{3,}", re.I),
     "hospital/record number"),
    (re.compile(r"\b(?:UHID|MRN)\b\s*[:#-]?\s*\w*\d{3,}", re.I), "hospital/record number"),
    (re.compile(r"\b[A-Z]{1,3}[-/ ]?\d{2,6}/\d{2,4}\b"), "accession-like number"),
    (re.compile(r"(?<![\d.,])\d{8,}(?![\d.,])"), "long digit run"),
    (re.compile(r"[\w.+-]+@(?!anthropic\.com\b)[\w-]+(?:\.[\w-]+)+"), "email address"),
)
RUBRIC = ("5 all asks met and verified, no rework; 4 minor gaps or light verification; "
          "3 user had to correct, or part missing/unverified; 2 major rework or missed asks; 1 failed")


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows pipes default to a legacy code page
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="harness.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("retro", help="record this session's retro (one per session; rerun to update)",
                       epilog=f"Score rubric: {RUBRIC}. Public corpus IDs only: no private personal data.")
    r.add_argument("--tool", help="/".join(TOOLS) + " (default: from session state)")
    r.add_argument("--session", help="session id (default: $HARNESS_SESSION_ID, $CLAUDE_CODE_SESSION_ID, newest state)")
    r.add_argument("--transcript", help="transcript/rollout .jsonl (default: found from the session id)")
    r.add_argument("--outcome", choices=OUTCOMES)
    r.add_argument("--task-type", choices=TASK_TYPES)
    r.add_argument("--task", help="one line: what was asked")
    r.add_argument("--score", type=int, choices=range(1, 6), help="self score 1-5 (see rubric below)")
    r.add_argument("--corrections", type=int, help="times the user had to correct or redirect you")
    r.add_argument("--rework", type=int, help="times you redid your own work")
    r.add_argument("--checks", help="what you verified (tests, checks, sources) or 'none'")
    r.add_argument("--waste", help="biggest avoidable token cost, or 'none'")
    r.add_argument("--lesson", action="append", default=[], metavar="TAG | RULE | EVIDENCE",
                   help=f"0-{MAX_LESSONS}; TAG is one of {'/'.join(LESSON_TAGS)}")
    r.add_argument("--helped", default="", help="playbook rule ids that helped, e.g. T1,C2")
    r.add_argument("--missed", default="", help="playbook rule ids you missed or that failed")
    r.add_argument("--handoff", help="handoff note updated for unfinished work, or 'none'")
    r.add_argument("--tokens", type=int, help="total tokens, if the tool shows them but keeps no transcript")
    r.add_argument("--urgent", action="store_true", help="a lesson is important enough to consolidate now")
    r.add_argument("--dry-run", action="store_true", help="print the retro instead of writing it")

    r = sub.add_parser("rate", help="record the researcher's own score for a session")
    r.add_argument("session", help="session id or its first characters")
    r.add_argument("score", type=int, choices=range(1, 6))
    r.add_argument("--note", default="", help="short reason (no private personal data)")

    sub.add_parser("report", help="metric trends across sessions")

    r = sub.add_parser("consolidate", help="review lessons/metrics; --done records the consolidation")
    r.add_argument("--done", action="store_true", help="archive the reviewed retros and log the changes")
    r.add_argument("--note", action="append", default=[], help="one per playbook change, e.g. 'added T4: ...'")

    sub.add_parser("sync", help="regenerate AGENTS.md from CLAUDE.md + harness/PLAYBOOK.md")
    sub.add_parser("check", help="lint the harness; exit 1 on errors")

    args = ap.parse_args(argv)
    return {"retro": cmd_retro, "rate": cmd_rate, "report": cmd_report, "consolidate": cmd_consolidate,
            "sync": cmd_sync, "check": cmd_check}[args.cmd](args)


# --------------------------------------------------------------------------------------------
# Session and transcript discovery


def normalize_tool(tool: str | None) -> str | None:
    if not tool:
        return None
    tool = TOOL_ALIASES.get(tool.lower(), tool.lower())
    return tool if tool in TOOLS else "other"


def read_state(sid: str) -> dict:
    st: dict = {}
    env = STATE / f"{sid}.env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep:
                st[key.strip()] = value.strip()
    raw = STATE / f"{sid}.json"
    if raw.is_file():
        try:
            payload = json.loads(raw.read_text(encoding="utf-8", errors="replace"))
            st["transcript_path"] = payload.get("transcript_path") or ""
        except ValueError:
            pass
    return st


def newest_state() -> dict:
    envs = sorted(STATE.glob("*.env"), key=lambda p: p.stat().st_mtime) if STATE.is_dir() else []
    return read_state(envs[-1].stem) if envs else {}


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def newest(paths) -> Path | None:
    paths = [Path(p) for p in paths if Path(p).is_file()]
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def codex_rollout_for_repo() -> tuple[Path | None, str | None]:
    """Newest Codex rollout whose session started inside this repo (used when hooks are off)."""
    rollouts = sorted(glob.glob(str(codex_home() / "sessions" / "**" / "rollout-*.jsonl"), recursive=True),
                      key=os.path.getmtime, reverse=True)
    for path in rollouts[:30]:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                first = json.loads(fh.readline() or "{}")
        except (OSError, ValueError):
            continue
        payload = first.get("payload") or {}
        cwd = payload.get("cwd")
        if cwd and _inside_repo(cwd):
            return Path(path), payload.get("id") or payload.get("session_id")
    return None, None


def _inside_repo(path: str) -> bool:
    try:
        Path(path).resolve().relative_to(ROOT.resolve())
        return True
    except (ValueError, OSError):
        return False


def resolve_session(args) -> tuple[str, str, dict, Path | None]:
    """Return (session id, tool, state, transcript path) using flags, env, hook state, then transcripts."""
    sid = args.session or os.environ.get("HARNESS_SESSION_ID") or os.environ.get("CLAUDE_CODE_SESSION_ID")
    st = read_state(sid) if sid else newest_state()
    sid = sid or st.get("HARNESS_SESSION_ID")
    tool = (normalize_tool(args.tool) or normalize_tool(os.environ.get("HARNESS_TOOL"))
            or normalize_tool(st.get("HARNESS_TOOL")) or ("claude-code" if os.environ.get("CLAUDECODE") else None))
    transcript = Path(args.transcript) if args.transcript else None
    if transcript is None and st.get("transcript_path") and Path(st["transcript_path"]).is_file():
        transcript = Path(st["transcript_path"])
    if transcript is None and tool == "claude-code":
        if sid:
            transcript = newest(glob.glob(str(claude_home() / "projects" / "*" / f"{sid}.jsonl")))
        else:
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
            transcript = newest(glob.glob(str(claude_home() / "projects" / slug / "*.jsonl")))
            sid = transcript.stem if transcript else None
    if transcript is None and tool in ("codex", None):
        if sid:
            transcript = newest(glob.glob(str(codex_home() / "sessions" / "**" / f"rollout-*{sid}*.jsonl"),
                                     recursive=True))
        else:
            transcript, sid = codex_rollout_for_repo()
        if transcript is not None:
            tool = "codex"
    if not sid:
        sid = "manual-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return sid, tool or "other", st, transcript


# --------------------------------------------------------------------------------------------
# Transcript metrics


def iter_jsonl(path: Path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj


def _ts(value) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes(first, last) -> int | None:
    return int((last - first).total_seconds() // 60) if first and last else None


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_claude(path: Path) -> dict:
    """Claude Code transcript: one API response spans several lines sharing message.id (same usage)."""
    files = [path] + sorted((path.parent / path.stem / "subagents").glob("*.jsonl"))
    usage: dict = {}
    tool_ids: set = set()
    errors = users = 0
    first = last = None
    for f in files:
        for obj in iter_jsonl(f):
            ts = _ts(obj.get("timestamp"))
            if ts:
                first, last = min(first or ts, ts), max(last or ts, ts)
            msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            if obj.get("type") == "assistant":
                key = msg.get("id") or obj.get("requestId") or obj.get("uuid")
                if isinstance(msg.get("usage"), dict) and key:
                    usage[key] = msg["usage"]
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") in ("tool_use", "server_tool_use"):
                        tool_ids.add(block.get("id") or len(tool_ids))
            elif obj.get("type") == "user":
                content = msg.get("content")
                blocks = content if isinstance(content, list) else []
                results = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
                errors += sum(1 for b in results if b.get("is_error"))
                is_prompt = isinstance(content, str) or any(
                    isinstance(b, dict) and b.get("type") == "text" for b in blocks)
                if is_prompt and not results and not obj.get("isMeta") and not obj.get("isSidechain") \
                        and f == path:
                    users += 1
    m = {"input": 0, "cw5m": 0, "cw1h": 0, "cache_read": 0, "output": 0}
    peak = 0
    for u in usage.values():
        cw = _int(u.get("cache_creation_input_tokens"))
        split = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
        cw1h = min(cw, _int(split.get("ephemeral_1h_input_tokens")))
        m["input"] += _int(u.get("input_tokens"))
        m["cw1h"] += cw1h
        m["cw5m"] += cw - cw1h
        m["cache_read"] += _int(u.get("cache_read_input_tokens"))
        m["output"] += _int(u.get("output_tokens"))
        peak = max(peak, _int(u.get("input_tokens")) + cw + _int(u.get("cache_read_input_tokens")))
    return _finish(m, "claude-code", api_calls=len(usage), peak=peak, tool_calls=len(tool_ids),
                   tool_errors=errors, user_turns=users, minutes=_minutes(first, last))


def _codex_failed(output) -> bool:
    if isinstance(output, str):
        match = re.match(r"\s*Exit code:\s*(-?\d+)", output)
        if match:
            return match.group(1) != "0"
        try:
            output = json.loads(output)
        except ValueError:
            return False
    if isinstance(output, dict):
        meta = output.get("metadata") if isinstance(output.get("metadata"), dict) else {}
        code = meta.get("exit_code", output.get("exit_code"))
        return code not in (None, 0)
    return False


def parse_codex(path: Path) -> dict:
    """Codex rollout: token_count events carry cumulative totals; input_tokens includes cached input."""
    total = None
    last_seen = None
    peak = calls = tools = errors = users = 0
    first = last = None
    for obj in iter_jsonl(path):
        ts = _ts(obj.get("timestamp"))
        if ts:
            first, last = min(first or ts, ts), max(last or ts, ts)
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        kind, ptype = obj.get("type"), payload.get("type")
        if kind == "event_msg" and ptype == "token_count":
            info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
            if isinstance(info.get("total_token_usage"), dict) and info["total_token_usage"] != last_seen:
                last_seen = total = info["total_token_usage"]
                calls += 1
                last_use = info.get("last_token_usage") if isinstance(info.get("last_token_usage"), dict) else {}
                peak = max(peak, _int(last_use.get("input_tokens")))
        elif kind == "event_msg" and ptype == "user_message":
            users += 1
        elif kind == "response_item" and ptype in ("function_call", "custom_tool_call", "local_shell_call",
                                                   "web_search_call"):
            tools += 1
        elif kind == "response_item" and ptype in ("function_call_output", "custom_tool_call_output"):
            errors += _codex_failed(payload.get("output"))
    m = {"input": 0, "cw5m": 0, "cw1h": 0, "cache_read": 0, "output": 0}
    if total:
        cached = _int(total.get("cached_input_tokens"))
        m["cw5m"] = _int(total.get("cache_write_input_tokens"))
        m["input"] = max(0, _int(total.get("input_tokens")) - cached - m["cw5m"])
        m["cache_read"] = cached
        m["output"] = _int(total.get("output_tokens"))
    return _finish(m, "codex", api_calls=calls, peak=peak, tool_calls=tools, tool_errors=errors,
                   user_turns=users, minutes=_minutes(first, last))


def _finish(m: dict, tool: str, **extra) -> dict:
    w = WEIGHTS[tool]
    out = {
        "source": "transcript",
        "api_calls": extra["api_calls"],
        "input": m["input"],
        "cache_write": m["cw5m"] + m["cw1h"],
        "cache_read": m["cache_read"],
        "output": m["output"],
        "total": m["input"] + m["cw5m"] + m["cw1h"] + m["cache_read"] + m["output"],
        "weighted": round(sum(m[k] * w[k] for k in m)),
        "peak_context": extra["peak"],
        "tool_calls": extra["tool_calls"],
        "tool_errors": extra["tool_errors"],
        "user_turns": extra["user_turns"],
        "minutes": extra["minutes"],
    }
    return out


def collect_metrics(tool: str, transcript: Path | None, tokens: int | None) -> dict:
    if transcript is not None and transcript.is_file():
        try:
            return parse_codex(transcript) if tool == "codex" else parse_claude(transcript)
        except OSError as exc:
            print(f"harness: could not read transcript ({exc}); metrics left empty", file=sys.stderr)
    return {"source": "self-reported" if tokens else "none", "total": tokens}


# --------------------------------------------------------------------------------------------
# Retro files


def _scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)  # JSON strings are valid YAML scalars


def dump_retro(data: dict) -> str:
    lines = ["# Harness session retro (schema 1), written by `harness.py retro`. See harness/README.md."]
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines += [f"  {k}: {_scalar(v)}" for k, v in value.items()]
        elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            lines.append(f"{key}:")
            for item in value:
                for i, (k, v) in enumerate(item.items()):
                    lines.append(("  - " if i == 0 else "    ") + f"{k}: {_scalar(v)}")
        elif isinstance(value, list):
            lines.append(f"{key}: [" + ", ".join(_scalar(x) for x in value) + "]")
        else:
            lines.append(f"{key}: {_scalar(value)}")
    return "\n".join(lines) + "\n"


def _yaml():
    try:
        import yaml  # type: ignore
    except ImportError:
        sys.exit("harness: PyYAML is needed to read retros: pip install pyyaml (see requirements.txt)")
    return yaml


def load_retros() -> list[dict]:
    yaml = _yaml()
    retros = []
    for path in sorted(SESSIONS.glob("*.yaml")) + sorted(ARCHIVE.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # report malformed files instead of crashing the report
            data = {"_error": str(exc)}
        if not isinstance(data, dict):
            data = {"_error": "not a mapping"}
        data["_path"] = path
        data["_new"] = path.parent == SESSIONS
        retros.append(data)
    retros.sort(key=lambda d: (str(d.get("date", "")), d["_path"].name))
    return retros


def find_identifiers(text: str) -> list[str]:
    return sorted({label for pattern, label in IDENTIFIER_PATTERNS if pattern.search(text or "")})


def parse_lesson(raw: str) -> dict:
    parts = [p.strip() for p in raw.split("|", 2)]
    if len(parts) < 2 or parts[0].lower() not in LESSON_TAGS or not parts[1]:
        raise ValueError(f"--lesson must be 'TAG | RULE | EVIDENCE' with TAG in {LESSON_TAGS}: {raw!r}")
    return {"tag": parts[0].lower(), "rule": parts[1], "evidence": parts[2] if len(parts) > 2 else ""}


def _ids(raw: str) -> list[str]:
    return [x.strip().upper() for x in re.split(r"[,\s]+", raw or "") if x.strip()]


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def cmd_retro(args) -> int:
    try:
        lessons = [parse_lesson(x) for x in args.lesson]
    except ValueError as exc:
        print(f"harness: {exc}", file=sys.stderr)
        return 2
    if len(lessons) > MAX_LESSONS:
        print(f"harness: at most {MAX_LESSONS} lessons; keep the ones with the strongest evidence", file=sys.stderr)
        return 2
    free = {"task": args.task, "waste": args.waste, "handoff": args.handoff, "checks": args.checks,
            **{f"lesson {i + 1}": f"{l['rule']} {l['evidence']}" for i, l in enumerate(lessons)}}
    flagged = {k: find_identifiers(v) for k, v in free.items() if v and find_identifiers(v)}
    if flagged:
        print(f"harness: possible identifiers {flagged}; rewrite with public corpus IDs only (nothing written)",
              file=sys.stderr)
        return 2

    sid, tool, st, transcript = resolve_session(args)
    started = st.get("HARNESS_STARTED_AT", "")[:10] or dt.date.today().isoformat()
    existing = sorted(list(SESSIONS.glob(f"*_{sid[:8]}.yaml")) + list(ARCHIVE.glob(f"*_{sid[:8]}.yaml")))
    path = existing[0] if existing else SESSIONS / f"{started}_{tool}_{sid[:8]}.yaml"
    previous = {}
    if existing:
        previous = _yaml().safe_load(path.read_text(encoding="utf-8")) or {}

    def keep(new, key, section=None):
        if new is not None:
            return new
        old = previous.get(section, {}) if section else previous
        return old.get(key) if isinstance(old, dict) else None

    quality_prev = previous.get("quality") if isinstance(previous.get("quality"), dict) else {}
    data = {
        "schema": 1,
        "primary_researcher": RESEARCHER,
        "session_id": sid,
        "tool": tool,
        "date": str(previous.get("date") or started),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD") or previous.get("branch") or "",
        "task_type": keep(args.task_type, "task_type"),
        "task": keep(args.task, "task"),
        "outcome": keep(args.outcome, "outcome"),
        "urgent": bool(args.urgent or previous.get("urgent")),
        "metrics": collect_metrics(tool, transcript, args.tokens),
        "quality": {
            "self_score": keep(args.score, "self_score", "quality"),
            "user_score": quality_prev.get("user_score"),
            "user_note": quality_prev.get("user_note") or "",
            "corrections": keep(args.corrections, "corrections", "quality"),
            "rework": keep(args.rework, "rework", "quality"),
            "checks": keep(args.checks, "checks", "quality"),
        },
        "waste": keep(args.waste, "waste"),
        "lessons": lessons or previous.get("lessons") or [],
        "rules_helped": _ids(args.helped) or previous.get("rules_helped") or [],
        "rules_missed": _ids(args.missed) or previous.get("rules_missed") or [],
        "handoff": keep(args.handoff, "handoff"),
    }
    text = dump_retro(data)
    if args.dry_run:
        print(text, end="")
        return 0
    SESSIONS.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    _prune_state()
    missing = [k for k in ("task_type", "task", "outcome", "waste") if not data[k]]
    missing += [k for k in ("self_score", "checks") if data["quality"][k] in (None, "")]
    m = data["metrics"]
    tokens = (f"tokens total {human(m.get('total'))}, weighted {human(m.get('weighted'))}, "
              f"peak context {human(m.get('peak_context'))}, {m.get('tool_calls', '?')} tool calls"
              if m.get("source") == "transcript" else f"tokens: {m.get('source')}")
    print(f"harness: wrote {path.relative_to(ROOT).as_posix()} ({tokens})")
    if missing:
        print(f"harness: still missing {', '.join(missing)}: rerun with those flags", file=sys.stderr)
    return 0


def _prune_state() -> None:
    if not STATE.is_dir():
        return
    cutoff = dt.datetime.now().timestamp() - STATE_TTL_DAYS * 86400
    for path in STATE.iterdir():
        try:
            if path.is_file() and path.name != "python" and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def cmd_rate(args) -> int:
    matches = sorted(p for p in list(SESSIONS.glob("*.yaml")) + list(ARCHIVE.glob("*.yaml"))
                     if re.search(rf"^session_id: \"{re.escape(args.session)}", p.read_text(encoding="utf-8"), re.M))
    if len(matches) != 1:
        print(f"harness: {len(matches)} retros match {args.session!r}; give more of the session id", file=sys.stderr)
        return 2
    if find_identifiers(args.note):
        print("harness: the note looks like it contains an identifier; use public corpus IDs only", file=sys.stderr)
        return 2
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^  user_score: .*$", f"  user_score: {args.score}", text, count=1, flags=re.M)
    text = re.sub(r"^  user_note: .*$", lambda _: f"  user_note: {_scalar(args.note)}", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"harness: rated {path.relative_to(ROOT).as_posix()} {args.score}/5")
    return 0


# --------------------------------------------------------------------------------------------
# Reporting and consolidation


def human(n) -> str:
    if n is None or n == "":
        return "-"
    n = float(n)
    for unit, size in (("M", 1e6), ("k", 1e3)):
        if abs(n) >= size:
            return f"{n / size:.1f}{unit}"
    return f"{n:.0f}"


def _score(r: dict):
    q = r.get("quality") if isinstance(r.get("quality"), dict) else {}
    return q.get("user_score") if q.get("user_score") is not None else q.get("self_score")


def _median(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(values) if values else None


def _mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return statistics.mean(values) if values else None


def summarize(retros: list[dict]) -> dict:
    metrics = [r.get("metrics") if isinstance(r.get("metrics"), dict) else {} for r in retros]
    quality = [r.get("quality") if isinstance(r.get("quality"), dict) else {} for r in retros]
    n = len(retros)
    return {
        "n": n,
        "done": sum(r.get("outcome") == "completed" for r in retros) / n if n else None,
        "score": _mean(_score(r) for r in retros),
        "corrections": _mean(q.get("corrections") for q in quality),
        "weighted": _median(m.get("weighted") for m in metrics),
        "total": _median(m.get("total") for m in metrics),
        "peak": _median(m.get("peak_context") for m in metrics),
        "output": _median(m.get("output") for m in metrics),
    }


def playbook_rules() -> dict:
    text = PLAYBOOK.read_text(encoding="utf-8") if PLAYBOOK.is_file() else ""
    return {m.group(1): m.group(2) for m in re.finditer(r"^- ([TQC]\d+) (.+)$", text, re.M)}


def report_text(retros: list[dict]) -> str:
    ok = [r for r in retros if "_error" not in r]
    tools = {}
    for r in ok:
        tools[r.get("tool", "?")] = tools.get(r.get("tool", "?"), 0) + 1
    lines = [f"Harness report: {len(ok)} sessions ({', '.join(f'{k} {v}' for k, v in sorted(tools.items())) or 'none'})."
             f" Primary researcher: {RESEARCHER}",
             f"{'':16}{'n':>4}{'done':>7}{'score':>7}{'corr':>6}{'weighted':>10}{'total':>9}{'peak':>8}{'output':>8}"]

    def row(name, s):
        pct = f"{s['done'] * 100:.0f}%" if s["done"] is not None else "-"
        score = f"{s['score']:.1f}" if s["score"] is not None else "-"
        corr = f"{s['corrections']:.1f}" if s["corrections"] is not None else "-"
        return (f"{name:16}{s['n']:>4}{pct:>7}{score:>7}{corr:>6}{human(s['weighted']):>10}{human(s['total']):>9}"
                f"{human(s['peak']):>8}{human(s['output']):>8}")

    lines.append(row("all", summarize(ok)))
    for task_type in TASK_TYPES:
        subset = [r for r in ok if r.get("task_type") == task_type]
        if subset:
            lines.append(row("  " + task_type, summarize(subset)))
    if len(ok) >= 4:
        half = min(5, len(ok) // 2)
        recent, before = summarize(ok[-half:]), summarize(ok[-2 * half:-half])

        def delta(key, pct=True):
            a, b = recent[key], before[key]
            if a is None or b is None or (pct and not b):
                return "n/a"
            return f"{(a - b) / b * 100:+.0f}%" if pct else f"{(a - b):+.2f}"
        lines.append(f"Trend (last {half} vs previous {half}; lower tokens is better): weighted {delta('weighted')},"
                     f" peak {delta('peak')}, output {delta('output')}, done {delta('done', False)},"
                     f" score {delta('score', False)}, corrections {delta('corrections', False)}")
    rules = playbook_rules()
    if rules:
        stats = []
        recent10 = ok[-10:]
        for rid in rules:
            helped = sum(rid in (r.get("rules_helped") or []) for r in ok)
            missed = sum(rid in (r.get("rules_missed") or []) for r in ok)
            idle = len(recent10) >= 10 and not any(
                rid in (r.get("rules_helped") or []) + (r.get("rules_missed") or []) for r in recent10)
            flag = " strengthen/automate?" if missed > helped else (" retire?" if idle else "")
            stats.append(f"{rid} +{helped}/-{missed}{flag}")
        lines.append("Rules (+helped/-missed): " + ", ".join(stats))
    bad = [r["_path"].name for r in retros if "_error" in r]
    if bad:
        lines.append("Unreadable retros: " + ", ".join(bad))
    return "\n".join(lines)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def lesson_groups(retros: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for r in retros:
        for lesson in r.get("lessons") or []:
            if not isinstance(lesson, dict) or not lesson.get("rule"):
                continue
            key = _norm(lesson["rule"])
            for g in groups:
                if difflib.SequenceMatcher(None, key, g["key"]).ratio() >= 0.6:
                    g["items"].append((lesson, r))
                    break
            else:
                groups.append({"key": key, "items": [(lesson, r)]})
    rules = {rid: _norm(text) for rid, text in playbook_rules().items()}
    for g in groups:
        g["new"] = any(r.get("_new") for _, r in g["items"])
        g["urgent"] = any(r.get("_new") and r.get("urgent") for _, r in g["items"])
        g["sessions"] = sorted({str(r.get("session_id", "?"))[:8] for _, r in g["items"]})
        best = max(rules.items(), key=lambda kv: difflib.SequenceMatcher(None, g["key"], kv[1]).ratio(),
                   default=None)
        g["similar"] = best[0] if best and difflib.SequenceMatcher(None, g["key"], best[1]).ratio() >= 0.5 else ""
    return sorted(groups, key=lambda g: (-len(g["sessions"]), g["key"]))


def cmd_report(args) -> int:
    print(report_text(load_retros()))
    return 0


def cmd_consolidate(args) -> int:
    retros = load_retros()
    new = [r for r in retros if r.get("_new")]
    if args.done:
        if not new:
            print("harness: no unconsolidated retros")
            return 0
        if not args.note:
            print("harness: pass one --note per playbook change (or --note 'no change: <why>')", file=sys.stderr)
            return 2
        if find_identifiers(" ".join(args.note)):
            print("harness: a note looks like it contains an identifier; use public corpus IDs only", file=sys.stderr)
            return 2
        text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.is_file() else "# Harness changelog\n"
        ids = [int(x) for x in re.findall(r"^## C(\d{3})", text, re.M)]
        cid = f"C{(max(ids) + 1) if ids else 1:03d}"
        s = summarize([r for r in new if "_error" not in r])
        pct = f"{s['done'] * 100:.0f}%" if s["done"] is not None else "-"
        score = f"{s['score']:.1f}" if s["score"] is not None else "-"
        entry = [f"## {cid}: {dt.date.today().isoformat()}, {len(new)} sessions reviewed",
                 f"Primary researcher: {RESEARCHER}",
                 "Sessions: " + ", ".join(r["_path"].stem for r in new),
                 f"Metrics: done {pct}, mean score {score}, median weighted {human(s['weighted'])},"
                 f" median peak context {human(s['peak'])}",
                 "Changes:"] + [f"- {note}" for note in args.note]
        CHANGELOG.write_text(text.rstrip("\n") + "\n\n" + "\n".join(entry) + "\n", encoding="utf-8", newline="\n")
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        for r in new:
            shutil.move(str(r["_path"]), str(ARCHIVE / r["_path"].name))
        print(f"harness: logged {cid} in harness/CHANGELOG.md and archived {len(new)} retros to "
              "harness/sessions/consolidated/. Run check, then commit.")
        return 0

    print(report_text(retros))
    groups = [g for g in lesson_groups(retros) if g["new"]]
    print(f"\nLesson candidates from {len(new)} unconsolidated sessions (count = sessions, all history):")
    for g in groups:
        lesson = g["items"][-1][0]
        mark = " URGENT" if g["urgent"] else ""
        similar = f" ~ {g['similar']}" if g["similar"] else ""
        print(f"  [{len(g['sessions'])}x{mark}] {lesson.get('tag', '?')}: {lesson['rule']}{similar}"
              f" (evidence: {lesson.get('evidence') or '-'}; sessions {', '.join(g['sessions'])})")
    if not groups:
        print("  none")
    size = len(PLAYBOOK.read_text(encoding="utf-8")) if PLAYBOOK.is_file() else 0
    print(f"\nPlaybook: {size}/{PLAYBOOK_MAX_CHARS} chars.")
    print("""Steps (edit harness/PLAYBOOK.md only; the researcher reviews the PR):
  1. Promote a lesson seen in >=2 sessions, or marked URGENT, to a rule. Merge into a similar rule (~ Tn)
     rather than adding one. One line per rule; new ids continue the series; never reuse a retired id.
  2. A rule with more misses than helps: make it concrete, or automate it (hook/check) instead of rewording.
  3. Retire rules marked 'retire?' or made redundant by automation. Stay under the char budget.
  4. Run: harness.py sync && harness.py check
  5. Run: harness.py consolidate --done --note "added T4: ..." --note "retired C3: ..." (one note per change)
  6. Commit with the Primary-Researcher trailer.""")
    return 0


# --------------------------------------------------------------------------------------------
# Sync and checks


def generate_agents() -> str:
    """AGENTS.md = CLAUDE.md with the playbook inlined (Codex and most tools cannot follow @imports)."""
    claude = CLAUDE_MD.read_text(encoding="utf-8").splitlines()
    playbook = PLAYBOOK.read_text(encoding="utf-8").splitlines()  # must match gen_agents() in bin/hook.sh
    if claude and claude[0] == "# CLAUDE.md":
        claude = claude[1:]
    out = ["# AGENTS.md", GENERATED_NOTE]
    for line in claude:
        out.extend(playbook if line == IMPORT_LINE else [line])
    return "\n".join(out) + "\n"


def cmd_sync(args) -> int:
    text = generate_agents()
    current = AGENTS_MD.read_text(encoding="utf-8") if AGENTS_MD.is_file() else ""
    if current == text:
        print("harness: AGENTS.md already in sync")
        return 0
    AGENTS_MD.write_text(text, encoding="utf-8", newline="\n")
    print("harness: regenerated AGENTS.md from CLAUDE.md + harness/PLAYBOOK.md")
    return 0


def check_retro(r: dict) -> tuple[list[str], list[str]]:
    name = r["_path"].name
    errors, warnings = [], []
    if "_error" in r:
        return [f"{name}: unreadable ({r['_error']})"], []
    if r.get("primary_researcher") != RESEARCHER:
        errors.append(f"{name}: primary_researcher must be '{RESEARCHER}'")
    for key, allowed in (("tool", TOOLS), ("task_type", TASK_TYPES), ("outcome", OUTCOMES)):
        value = r.get(key)
        if value is None:
            warnings.append(f"{name}: {key} not filled")
        elif value not in allowed:
            errors.append(f"{name}: {key}={value!r} not in {allowed}")
    q = r.get("quality") if isinstance(r.get("quality"), dict) else {}
    for key in ("self_score", "user_score"):
        if q.get(key) is not None and q.get(key) not in (1, 2, 3, 4, 5):
            errors.append(f"{name}: quality.{key} must be 1-5")
    if q.get("self_score") is None:
        warnings.append(f"{name}: quality.self_score not filled")
    lessons = r.get("lessons") or []
    if len(lessons) > MAX_LESSONS:
        errors.append(f"{name}: more than {MAX_LESSONS} lessons")
    for lesson in lessons:
        if not isinstance(lesson, dict) or lesson.get("tag") not in LESSON_TAGS or not lesson.get("rule"):
            errors.append(f"{name}: lesson needs tag ({'/'.join(LESSON_TAGS)}) and rule")
    texts = [str(r.get(k) or "") for k in FREE_TEXT] + [str(q.get("checks") or ""), str(q.get("user_note") or "")]
    texts += [f"{l.get('rule', '')} {l.get('evidence', '')}" for l in lessons if isinstance(l, dict)]
    hits = find_identifiers(" \n".join(texts))
    if hits:
        errors.append(f"{name}: possible identifiers ({', '.join(hits)}); use public corpus IDs only")
    return errors, warnings


def _hook_commands(node) -> list[str]:
    if isinstance(node, dict):
        found = [v for k, v in node.items() if k in ("command", "commandWindows") and isinstance(v, str)]
        return found + [c for v in node.values() for c in _hook_commands(v)]
    if isinstance(node, list):
        return [c for v in node for c in _hook_commands(v)]
    return []


def cmd_check(args) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not PLAYBOOK.is_file():
        errors.append("harness/PLAYBOOK.md missing")
    else:
        size = len(PLAYBOOK.read_text(encoding="utf-8"))
        if size > PLAYBOOK_MAX_CHARS:
            errors.append(f"PLAYBOOK.md is {size} chars (> {PLAYBOOK_MAX_CHARS}); merge or retire rules")
        elif size > PLAYBOOK_WARN_CHARS:
            warnings.append(f"PLAYBOOK.md is {size} chars; consolidate before it reaches {PLAYBOOK_MAX_CHARS}")
        for label, text in (("PLAYBOOK.md", PLAYBOOK.read_text(encoding="utf-8")),
                            ("CHANGELOG.md", CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.is_file() else "")):
            hits = find_identifiers(text)
            if hits:
                errors.append(f"{label}: possible identifiers ({', '.join(hits)})")
    if not CLAUDE_MD.is_file() or IMPORT_LINE not in CLAUDE_MD.read_text(encoding="utf-8").splitlines():
        errors.append(f"CLAUDE.md must contain the line {IMPORT_LINE}")
    elif PLAYBOOK.is_file():
        current = AGENTS_MD.read_text(encoding="utf-8") if AGENTS_MD.is_file() else ""
        if current.replace("\r\n", "\n") != generate_agents():
            diff = list(difflib.unified_diff(generate_agents().splitlines(), current.splitlines(),
                                             "expected", "AGENTS.md", lineterm="", n=0))[2:8]
            errors.append("AGENTS.md is out of sync: edit CLAUDE.md/PLAYBOOK.md, then run harness.py sync\n    "
                          + "\n    ".join(diff))
    if GEMINI_MD.is_file() and "@./AGENTS.md" not in GEMINI_MD.read_text(encoding="utf-8"):
        warnings.append("GEMINI.md should import @./AGENTS.md")
    for config in HOOK_CONFIGS:
        if not config.is_file():
            warnings.append(f"{config.relative_to(ROOT).as_posix()} missing: harness hooks not registered there")
            continue
        try:
            commands = _hook_commands(json.loads(config.read_text(encoding="utf-8")))
        except ValueError as exc:
            errors.append(f"{config.relative_to(ROOT).as_posix()}: invalid JSON ({exc})")
            continue
        for event in ("session-start", "stop"):
            if not any(re.search(rf"harness/bin/hook\.sh\"?\s+{event}\b", c) for c in commands):
                errors.append(f"{config.relative_to(ROOT).as_posix()}: no harness {event} hook")
    retros = load_retros() if SESSIONS.is_dir() else []
    for r in retros:
        e, w = check_retro(r)
        errors += e
        warnings += w
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"harness check: {len(errors)} errors, {len(warnings)} warnings, {len(retros)} retros")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
