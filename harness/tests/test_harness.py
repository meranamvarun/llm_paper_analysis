"""Tests for the self-improvement harness: python -m unittest discover -s harness/tests

Each test builds a throwaway git repo holding a copy of the harness, with HOME, CLAUDE_CONFIG_DIR
and CODEX_HOME pointed at temp dirs, so real transcripts and session state are never touched.
Primary researcher: TO CONFIRM.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SH = shutil.which("sh")
SID = "11111111-2222-3333-4444-555555555555"


def line(obj):
    return json.dumps(obj) + "\n"


def claude_transcript():
    usage1 = {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 5000,
              "output_tokens": 200, "cache_creation": {"ephemeral_1h_input_tokens": 400}}
    usage2 = {"input_tokens": 5, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 7000,
              "output_tokens": 100}
    return "".join([
        line({"type": "user", "timestamp": "2026-09-27T10:00:00Z", "message": {"content": "please do X"}}),
        line({"type": "user", "isMeta": True, "timestamp": "2026-09-27T10:00:01Z",
              "message": {"content": [{"type": "text", "text": "skill loaded"}]}}),
        # one API response split over two lines with the same id and usage: must be counted once
        line({"type": "assistant", "timestamp": "2026-09-27T10:00:05Z",
              "message": {"id": "m1", "usage": usage1, "content": [{"type": "thinking"}]}}),
        line({"type": "assistant", "timestamp": "2026-09-27T10:00:06Z",
              "message": {"id": "m1", "usage": usage1, "content": [{"type": "tool_use", "id": "t1"}]}}),
        line({"type": "user", "timestamp": "2026-09-27T10:00:07Z",
              "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]}}),
        line({"type": "assistant", "timestamp": "2026-09-27T10:12:00Z",
              "message": {"id": "m2", "usage": usage2, "content": [{"type": "tool_use", "id": "t2"}]}}),
        "not json\n",
    ])


def codex_rollout(cwd):
    def tc(inp, cached, out, last_inp):
        return {"timestamp": "2026-09-27T10:05:00Z", "type": "event_msg", "payload": {
            "type": "token_count", "info": {
                "total_token_usage": {"input_tokens": inp, "cached_input_tokens": cached,
                                      "output_tokens": out, "reasoning_output_tokens": 0,
                                      "total_tokens": inp + out},
                "last_token_usage": {"input_tokens": last_inp, "cached_input_tokens": 0, "output_tokens": 1,
                                     "reasoning_output_tokens": 0, "total_tokens": last_inp + 1}}}}
    rows = [
        {"timestamp": "2026-09-27T10:00:00Z", "type": "session_meta", "payload": {"id": SID, "cwd": cwd}},
        {"timestamp": "2026-09-27T10:00:01Z", "type": "event_msg", "payload": {"type": "user_message",
                                                                                "message": "do Y"}},
        {"timestamp": "2026-09-27T10:00:02Z", "type": "response_item", "payload": {"type": "function_call",
                                                                                    "name": "shell"}},
        {"timestamp": "2026-09-27T10:00:03Z", "type": "response_item",
         "payload": {"type": "function_call_output", "output": "Exit code: 1\nWall time: 0.1 seconds"}},
        tc(1000, 600, 50, 1000),
        tc(1000, 600, 50, 1000),  # repeated snapshot: not a new API call
        {"timestamp": "2026-09-27T10:09:00Z", "type": "event_msg", "payload": {"type": "token_count",
                                                                                "info": None}},
        tc(3000, 2000, 120, 2000),
    ]
    return "".join(line(r) for r in rows)


class HarnessRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness-test-"))
        self.root = self.tmp / "repo"
        for rel in ("harness/harness.py", "harness/bin/hook.sh", "harness/PLAYBOOK.md", ".githooks/pre-commit",
                    ".githooks/commit-msg", ".claude/settings.json", ".codex/hooks.json", "CLAUDE.md",
                    "GEMINI.md", ".gitignore"):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, dest)
        self.home = self.tmp / "home"
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("HARNESS_", "CLAUDE", "CODEX"))}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), GIT_CONFIG_NOSYSTEM="1",
                        CLAUDE_CONFIG_DIR=str(self.home / ".claude"), CODEX_HOME=str(self.home / ".codex"),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        self.git("init", "-q")
        self.harness("sync")
        self.git("add", "-A")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "init")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, capture_output=True, text=True)

    def harness(self, *args):
        return subprocess.run([sys.executable, str(self.root / "harness/harness.py"), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def hook(self, event, payload=None, tool="claude-code"):
        return subprocess.run([SH, str(self.root / "harness/bin/hook.sh"), event, tool], cwd=self.root,
                              env=self.env, input=json.dumps(payload or {}), capture_output=True, text=True)

    def write_claude_transcript(self, sid=SID):
        path = self.home / ".claude" / "projects" / "some-project" / f"{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(claude_transcript())
        return path

    def retro(self, *extra, sid=SID):
        return self.harness("retro", "--tool", "claude-code", "--session", sid, "--outcome", "completed",
                            "--task-type", "tooling", "--task", "test task", "--score", "4", "--corrections", "0",
                            "--rework", "1", "--checks", "unit tests", "--waste", "none", *extra)

    def retro_files(self):
        return sorted((self.root / "harness/sessions").glob("*.yaml"))


class TestMetrics(HarnessRepo):
    def test_claude_transcript_metrics_dedupe_split_responses(self):
        self.write_claude_transcript()
        res = self.retro("--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        text = res.stdout
        for expected in ("api_calls: 2", "input: 15", "cache_write: 1000", "cache_read: 12000", "output: 300",
                         "total: 13315", "peak_context: 7005", "tool_calls: 2", "tool_errors: 1",
                         "user_turns: 1", "minutes: 12"):
            self.assertIn(expected, text)
        # weighted = 15 + 600*1.25 + 400*2 + 12000*0.1 + 300*5
        self.assertIn("weighted: 4265", text)
        self.assertNotIn("model", text)  # no model identifiers in committed files

    def test_codex_rollout_metrics(self):
        path = self.home / ".codex" / "sessions" / "2026" / "09" / "27" / f"rollout-2026-09-27T10-00-00-{SID}.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(codex_rollout(str(self.root)))
        res = self.harness("retro", "--tool", "codex", "--session", SID, "--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        for expected in ("api_calls: 2", "input: 1000", "cache_read: 2000", "output: 120", "total: 3120",
                         "peak_context: 2000", "tool_calls: 1", "tool_errors: 1", "user_turns: 1"):
            self.assertIn(expected, res.stdout)

    def test_codex_rollout_found_without_hooks(self):
        path = self.home / ".codex" / "sessions" / "2026" / "09" / "27" / "rollout-x.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(codex_rollout(str(self.root)))
        res = self.harness("retro", "--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn(f'session_id: "{SID}"', res.stdout)
        self.assertIn('tool: "codex"', res.stdout)


class TestRetro(HarnessRepo):
    def test_retro_writes_then_updates_same_file(self):
        self.write_claude_transcript()
        self.assertEqual(self.retro("--lesson", "tokens | Grep before reading | 46 KB file read").returncode, 0)
        files = self.retro_files()
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name.endswith("_claude-code_11111111.yaml"))
        res = self.harness("retro", "--session", SID, "--tool", "claude-code", "--outcome", "partial")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.retro_files(), files)
        text = files[0].read_text()
        self.assertIn('outcome: "partial"', text)
        self.assertIn('task: "test task"', text)       # kept from the first run
        self.assertIn('rule: "Grep before reading"', text)
        self.assertIn('primary_researcher: "TO CONFIRM"', text)
        self.assertEqual(self.harness("check").returncode, 0, self.harness("check").stdout)

    def test_retro_refuses_identifiers(self):
        for task in ("reviewed UHID 1234567", "case 12345678 done", "slide B-1234/24 recut", "mail a@b.org"):
            res = self.harness("retro", "--tool", "claude-code", "--session", SID, "--task", task)
            self.assertEqual(res.returncode, 2, task)
        self.assertEqual(self.retro_files(), [])

    def test_bad_lesson_and_too_many_lessons(self):
        self.assertEqual(self.retro("--lesson", "speed | x | y").returncode, 2)
        many = [a for i in range(4) for a in ("--lesson", f"quality | rule {i} | e")]
        self.assertEqual(self.retro(*many).returncode, 2)

    def test_rate_sets_user_score(self):
        self.retro()
        res = self.harness("rate", SID[:8], "2", "--note", "missed a citation")
        self.assertEqual(res.returncode, 0, res.stderr)
        text = self.retro_files()[0].read_text()
        self.assertIn("user_score: 2", text)
        self.assertIn('user_note: "missed a citation"', text)
        self.assertIn("2.0", self.harness("report").stdout)  # report prefers the researcher's score


class TestConsolidation(HarnessRepo):
    def test_consolidate_report_then_done(self):
        for i, sid in enumerate(("aaaaaaaa-1", "bbbbbbbb-2")):
            res = self.harness("retro", "--tool", "codex", "--session", sid, "--outcome", "completed",
                               "--task-type", "writing", "--task", f"t{i}", "--score", "4", "--checks", "c",
                               "--waste", "none", "--lesson", "tokens | Grep large notes before reading them | x",
                               "--helped", "T1")
            self.assertEqual(res.returncode, 0, res.stderr)
        report = self.harness("consolidate")
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("[2x] tokens: Grep large notes before reading them", report.stdout)
        self.assertIn("T1 +2/-0", report.stdout)
        self.assertEqual(self.harness("consolidate", "--done").returncode, 2)  # notes are required
        done = self.harness("consolidate", "--done", "--note", "no change: covered by T2")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.retro_files(), [])
        self.assertEqual(len(list((self.root / "harness/sessions/consolidated").glob("*.yaml"))), 2)
        log = (self.root / "harness/CHANGELOG.md").read_text()
        self.assertIn("## C001:", log)
        self.assertIn("Primary researcher: TO CONFIRM", log)
        self.assertIn("- no change: covered by T2", log)


class TestSyncAndCheck(HarnessRepo):
    def test_sync_check_and_shell_verify_agree(self):
        self.assertEqual(self.harness("check").returncode, 0)
        playbook = self.root / "harness/PLAYBOOK.md"
        playbook.write_text(playbook.read_text() + "- T9 extra rule\n\n")
        self.assertEqual(self.harness("check").returncode, 1)
        if SH:
            self.assertEqual(self.hook("verify-sync").returncode, 1)
        self.harness("sync")
        self.assertEqual(self.harness("check").returncode, 0)
        agents = (self.root / "AGENTS.md").read_text()
        self.assertTrue(agents.startswith("# AGENTS.md\n<!-- Generated"))
        self.assertIn("- T9 extra rule", agents)
        self.assertNotIn("@harness/PLAYBOOK.md", agents)
        if SH:
            self.assertEqual(self.hook("verify-sync").returncode, 0)

    def test_check_flags_oversized_playbook(self):
        playbook = self.root / "harness/PLAYBOOK.md"
        playbook.write_text(playbook.read_text() + "x" * 4000 + "\n")
        self.harness("sync")
        self.assertIn("merge or retire rules", self.harness("check").stdout)


@unittest.skipUnless(SH, "needs a POSIX sh")
class TestHooks(HarnessRepo):
    def start(self, sid=SID, tool="claude-code", source="startup"):
        return self.hook("session-start", {"session_id": sid, "source": source, "transcript_path": None},
                         tool)

    def stop(self, sid=SID, active=False, tool="claude-code"):
        return self.hook("stop", {"session_id": sid, "stop_hook_active": active,
                                  "last_assistant_message": 'said "session_id": "zzz"'}, tool)

    def test_session_start_emits_status_json(self):
        env_file = self.tmp / "envfile"
        self.env["CLAUDE_ENV_FILE"] = str(env_file)
        res = self.start()
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn("Harness status", out["additionalContext"])
        self.assertIn("claude-code 11111111", out["additionalContext"])
        self.assertIn("core.hooksPath=.githooks", out["additionalContext"])
        self.assertIn(f"export HARNESS_SESSION_ID={SID}", env_file.read_text())
        self.assertEqual(self.git("config", "--get", "core.hooksPath").stdout.strip(), ".githooks")

    def test_session_start_flags_due_consolidation_and_stale_agents(self):
        for i in range(5):
            self.harness("retro", "--tool", "codex", "--session", f"s{i}xxxxxxx", "--outcome", "completed")
        (self.root / "AGENTS.md").write_text("stale\n")
        context = json.loads(self.start(tool="codex").stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("CONSOLIDATION DUE", context)
        self.assertIn("AGENTS.md is out of sync", context)
        self.assertIn("5 unconsolidated", context)

    def test_stop_nudges_once_per_repo_state(self):
        self.start()
        self.assertEqual(self.stop().stdout, "")                   # nothing changed yet
        (self.root / "notes.md").write_text("draft\n")
        self.assertEqual(self.stop(active=True).stdout, "")        # never loop on a stop-hook continuation
        body = json.loads(self.stop().stdout)
        self.assertEqual(body["decision"], "block")
        self.assertIn(f"--session {SID}", body["reason"])
        self.assertEqual(self.stop().stdout, "")                   # same state: no repeat
        (self.root / "more.md").write_text("draft 2\n")
        self.assertIn("block", self.stop().stdout)                 # repo state changed, still no retro
        self.retro()
        (self.root / "notes.md").write_text("draft 3\n")
        self.assertEqual(self.stop().stdout, "")                   # retro exists

    def test_stop_ignores_changes_that_predate_the_session(self):
        (self.root / "old.md").write_text("uncommitted before the session\n")
        self.start()
        self.assertEqual(self.stop().stdout, "")
        self.git("add", "-A")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "work")
        self.assertIn("block", self.stop().stdout)                 # a commit is work

    def test_stop_respects_opt_out(self):
        self.start()
        (self.root / "notes.md").write_text("x\n")
        self.env["HARNESS_RETRO"] = "off"
        self.assertEqual(self.stop().stdout, "")

    def test_pre_commit_blocks_stale_agents(self):
        self.git("config", "core.hooksPath", ".githooks")
        (self.root / "CLAUDE.md").write_text((self.root / "CLAUDE.md").read_text() + "\nNew rule.\n")
        self.git("add", "CLAUDE.md")
        self.assertNotEqual(self.git("commit", "-qm", "stale").returncode, 0)
        self.harness("sync")
        self.git("add", "-A")
        res = self.git("commit", "-qm", "synced")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Primary-Researcher: TO CONFIRM", self.git("log", "-1", "--format=%B").stdout)


if __name__ == "__main__":
    unittest.main()
