#!/bin/sh
# Self-improvement harness hook for Claude Code and Codex (both use the same JSON contract).
#   sh harness/bin/hook.sh session-start <tool>   inject harness status as additionalContext
#   sh harness/bin/hook.sh stop <tool>            ask once per repo state for a retro if the session changed files
#   sh harness/bin/hook.sh verify-sync            exit 1 if AGENTS.md is stale (used by .githooks/pre-commit)
# POSIX sh (dash, bash 3.2, Git Bash). A hook must never break a session: degraded paths exit 0 silently.
# Primary researcher: TO CONFIRM. See harness/README.md.

EVENT=${1:-}
TOOL=${2:-other}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." 2>/dev/null && pwd) || exit 0
STATE=$ROOT/harness/.state
SESSIONS=$ROOT/harness/sessions
DUE_AT=5

INPUT=""
case $EVENT in session-start | stop) INPUT=$(tr -d '\r\n') ;; esac

# First value of a top-level "key" in the hook payload (ids, enums and booleans only).
json_field() {
  printf '%s' "$INPUT" | awk -v key="\"$1\"" '{
    i = index($0, key); if (!i) exit
    s = substr($0, i + length(key)); sub(/^[ \t]*:[ \t]*/, "", s)
    if (substr(s, 1, 1) == "\"") { s = substr(s, 2); print substr(s, 1, index(s, "\"") - 1) }
    else if (match(s, /^[A-Za-z0-9_.-]+/)) print substr(s, RSTART, RLENGTH)
  }'
}

json_escape() {
  tr -d '\r' | tr -d '\000-\010\013\014\016-\037' | tr '\t' ' ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' |
    awk 'NR > 1 { printf "%s", "\\n" } { printf "%s", $0 }'
}

HAS_TIMEOUT=0
timeout --version >/dev/null 2>&1 && HAS_TIMEOUT=1 # GNU timeout, not Windows timeout.exe
bounded() { if [ "$HAS_TIMEOUT" = 1 ]; then timeout 5 "$@"; else "$@"; fi; }

is_python3() {
  out=$(bounded "$@" -c 'import sys; print("HARNESS_PY_OK", sys.version_info[0])' 2>/dev/null) || return 1
  case $out in "HARNESS_PY_OK 3"*) return 0 ;; esac
  return 1
}

# Print a working Python 3 command and cache it. PATH python on Windows is often the Store stub.
find_python() {
  for cand in "${HARNESS_PYTHON:-}" "$(cat "$STATE/python" 2>/dev/null)" python3 python "py -3"; do
    [ -n "$cand" ] || continue
    if [ -f "$cand" ]; then is_python3 "$cand" || continue
    else is_python3 $cand || continue # unquoted on purpose: "py -3" is two words
    fi
    printf '%s\n' "$cand" >"$STATE/python" 2>/dev/null
    printf '%s' "$cand"
    return 0
  done
  if [ -n "${LOCALAPPDATA:-}" ]; then
    base=$LOCALAPPDATA
    command -v cygpath >/dev/null 2>&1 && base=$(cygpath -u "$LOCALAPPDATA")
    for exe in "$base"/Programs/Python/Python3*/python.exe; do
      [ -f "$exe" ] && is_python3 "$exe" || continue
      printf '%s\n' "$exe" >"$STATE/python" 2>/dev/null
      printf '%s' "$exe"
      return 0
    done
  fi
  return 1
}

# Codex on Windows runs agent commands in PowerShell, which needs a Windows-style path.
py_display() {
  py=$1
  if [ "$TOOL" = codex ] && [ -f "$py" ] && command -v cygpath >/dev/null 2>&1; then py=$(cygpath -w "$py"); fi
  case $py in *" "*) [ -f "$py" ] && py="\"$py\"" ;; esac
  printf '%s' "$py"
}

count() {
  n=0
  for f in "$@"; do [ -f "$f" ] && n=$((n + 1)); done
  echo "$n"
}

yget() { sed -n "s/^$1: \"\{0,1\}\([^\"]*\)\"\{0,1\}\$/\1/p" "$2" 2>/dev/null | head -n 1; }

human() {
  awk -v n="$1" 'BEGIN { if (n == "" || n == "null") print "-"; else if (n >= 1e6) printf "%.1fM\n", n / 1e6;
    else if (n >= 1e3) printf "%.0fk\n", n / 1e3; else print n }'
}

dirty_sum() { git -C "$ROOT" status --porcelain 2>/dev/null | grep -v 'harness/\.state/' | cksum | cut -d' ' -f1; }

# AGENTS.md = CLAUDE.md with the playbook inlined; must match generate_agents() in harness.py.
gen_agents() {
  printf '%s\n%s\n' '# AGENTS.md' '<!-- Generated from CLAUDE.md and harness/PLAYBOOK.md by `harness.py sync`; edit those files, not this one. -->'
  tr -d '\r' <"$ROOT/CLAUDE.md" | awk -v pb="$ROOT/harness/PLAYBOOK.md" '
    NR == 1 && $0 == "# CLAUDE.md" { next }
    $0 == "@harness/PLAYBOOK.md" { while ((getline line < pb) > 0) { sub(/\r$/, "", line); print line } close(pb); next }
    { print }'
}

verify_sync() {
  [ -f "$ROOT/CLAUDE.md" ] && [ -f "$ROOT/harness/PLAYBOOK.md" ] && [ -f "$ROOT/AGENTS.md" ] || return 1
  [ "$(gen_agents)" = "$(tr -d '\r' <"$ROOT/AGENTS.md")" ]
}

# The commit-msg hook adds the Primary-Researcher trailer. Enable it unless other git hooks are in use.
git_hooks_line() {
  hp=$(git -C "$ROOT" config --get core.hooksPath 2>/dev/null)
  [ "$hp" = .githooks ] && { echo "git: core.hooksPath=.githooks (commit-msg adds the Primary-Researcher trailer)"; return; }
  if [ -z "$hp" ] && [ -f "$ROOT/.githooks/commit-msg" ]; then
    dir=$(git -C "$ROOT" rev-parse --git-path hooks 2>/dev/null)
    case $dir in /* | [A-Za-z]:*) ;; *) dir=$ROOT/$dir ;; esac
    if [ -z "$(ls "$dir" 2>/dev/null | grep -v '\.sample$')" ] && git -C "$ROOT" config core.hooksPath .githooks 2>/dev/null; then
      echo "git: set core.hooksPath=.githooks just now (commit-msg adds the Primary-Researcher trailer)"
      return
    fi
  fi
  echo "git: core.hooksPath is '${hp:-unset}', so add 'Primary-Researcher: TO CONFIRM' to each commit yourself"
}

session_start() {
  sid=$(json_field session_id | tr -cd 'A-Za-z0-9._-')
  src=$(json_field source | tr -cd 'a-z')
  [ -n "$sid" ] || sid=manual-$(date -u +%Y%m%d%H%M%S)
  mkdir -p "$STATE" 2>/dev/null
  head=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)
  if [ ! -f "$STATE/$sid.env" ]; then
    printf 'HARNESS_SESSION_ID=%s\nHARNESS_TOOL=%s\nHARNESS_START_HEAD=%s\nHARNESS_START_DIRTY=%s\nHARNESS_STARTED_AT=%s\n' \
      "$sid" "$TOOL" "$head" "$(dirty_sum)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$STATE/$sid.env" 2>/dev/null
    printf '%s\n' "$INPUT" >"$STATE/$sid.json" 2>/dev/null
  fi
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    printf 'export HARNESS_SESSION_ID=%s\nexport HARNESS_TOOL=%s\n' "$sid" "$TOOL" >>"$CLAUDE_ENV_FILE" 2>/dev/null
  fi

  py=$(find_python) && py=$(py_display "$py")
  run=${py:-python3}
  n_new=$(count "$SESSIONS"/*.yaml)
  n_all=$((n_new + $(count "$SESSIONS"/consolidated/*.yaml)))
  last=$(ls "$SESSIONS"/*.yaml "$SESSIONS"/consolidated/*.yaml 2>/dev/null | awk -F/ '{ print $NF "\t" $0 }' | sort | tail -n 1 | cut -f2)
  branch=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)

  status="Harness status (rules: the \"Self-improvement harness\" section of your instructions)
- Session: $TOOL $(printf '%s' "$sid" | cut -c1-8) (${src:-startup}) on ${branch:-?} @$(printf '%s' "$head" | cut -c1-7)"
  if [ -n "$last" ]; then
    status="$status
- Retros: $n_all logged, $n_new unconsolidated (consolidation due at $DUE_AT). Last: $(yget date "$last") $(yget tool "$last") $(yget task_type "$last") $(yget outcome "$last"), $(human "$(yget '  weighted' "$last")") weighted tokens"
  else
    status="$status
- Retros: none yet (consolidation due at $DUE_AT)"
  fi
  if [ "$n_new" -ge "$DUE_AT" ] || grep -l '^urgent: true' "$SESSIONS"/*.yaml >/dev/null 2>&1; then
    status="$status
- CONSOLIDATION DUE: after the user's task, run: $run harness/harness.py consolidate"
  fi
  if [ -n "$py" ]; then
    status="$status
- Python for harness commands: $py"
  else
    status="$status
- Python 3 not found: set HARNESS_PYTHON to its path (harness commands need it)"
  fi
  status="$status
- $(git_hooks_line)"
  verify_sync || status="$status
- WARNING: AGENTS.md is out of sync with CLAUDE.md + harness/PLAYBOOK.md: run $run harness/harness.py sync"
  status="$status
- If you change files: finish with one '$run harness/harness.py retro ...' (see --help), committed with the work"

  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(printf '%s' "$status" | json_escape)"
}

stop_hook() {
  [ "$(json_field stop_hook_active)" = true ] && return
  [ "${HARNESS_RETRO:-on}" = off ] && return
  sid=$(json_field session_id | tr -cd 'A-Za-z0-9._-')
  [ -n "$sid" ] || return
  sid8=$(printf '%s' "$sid" | cut -c1-8)
  for f in "$SESSIONS"/*_"$sid8".yaml "$SESSIONS"/consolidated/*_"$sid8".yaml; do [ -f "$f" ] && return; done
  head=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) || return
  dirty=$(dirty_sum)
  if [ -f "$STATE/$sid.env" ]; then
    start_head=$(sed -n 's/^HARNESS_START_HEAD=//p' "$STATE/$sid.env")
    start_dirty=$(sed -n 's/^HARNESS_START_DIRTY=//p' "$STATE/$sid.env")
    [ "$head" = "$start_head" ] && [ "$dirty" = "$start_dirty" ] && return
  else
    [ -z "$(git -C "$ROOT" status --porcelain 2>/dev/null | grep -v 'harness/\.state/')" ] && return
  fi
  mark="$head $dirty" # nudge again only if the repo changed since the last nudge
  [ "$(cat "$STATE/$sid.nudged" 2>/dev/null)" = "$mark" ] && return
  mkdir -p "$STATE" 2>/dev/null
  printf '%s\n' "$mark" >"$STATE/$sid.nudged" 2>/dev/null
  py=$(py_display "$(cat "$STATE/python" 2>/dev/null)")

  reason="Harness: this session changed the repo, so log one retro before you finish (skip only if the user said so; if you are only pausing for the user, stop and do it at the end). Replace each <...>; public corpus IDs only, no private personal data:
${py:-python3} harness/harness.py retro --tool $TOOL --session $sid --outcome <completed|partial|blocked|abandoned> --task-type <lit-search|lit-review|writing|citation-check|analysis|admin|tooling|other> --task \"<one line>\" --score <1-5> --corrections <n> --rework <n> --checks \"<what you verified>\" --waste \"<biggest avoidable token cost, or none>\" --lesson \"<tokens|quality|completion> | <rule to adopt> | <evidence>\" --helped <rule ids> --missed <rule ids>
Score: 5 all asks met and verified; 4 minor gaps; 3 user corrected you or part unverified; 2 major rework; 1 failed. Commit the retro file with your work."
  printf '{"decision":"block","reason":"%s"}\n' "$(printf '%s' "$reason" | json_escape)"
}

case $EVENT in
  session-start) session_start ;;
  stop) stop_hook ;;
  verify-sync) verify_sync; exit $? ;;
  *) echo "usage: sh harness/bin/hook.sh session-start|stop <tool> | verify-sync" >&2 ;;
esac
exit 0
