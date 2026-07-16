from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_DIR))

import gen_commit as gc  # noqa: E402


class RecordingClient:
    def __init__(self, large_facts: bool = False):
        self.calls: list[tuple[str, str, int, str]] = []
        self.large_facts = large_facts

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
        purpose: str,
        validator=None,
    ) -> str:
        self.calls.append((system, user, max_tokens, purpose))
        if purpose.startswith("final"):
            result = '"归纳全部笔记变更并优化提交摘要。"\n这行不应进入标题'
            return validator(result) if validator else result
        padding = "事实" * 900 if self.large_facts and purpose.startswith("facts-diff") else "完整事实"
        covered_ids = re.findall(r'<(?:SOURCE|SUMMARY) id="([^"]+)"', user)
        result = json.dumps(
            {
                "covered_ids": covered_ids,
                "changes": [
                    {"scope": "测试范围", "action": "修改", "facts": [padding]}
                ],
                "overall": "覆盖本批次",
            },
            ensure_ascii=False,
        )
        return validator(result) if validator else result


def make_config(**overrides) -> gc.Config:
    values = {
        "direct_input_bytes": 18_000,
        "chunk_input_bytes": 9_000,
        "intermediate_max_tokens": 1_024,
        "final_max_tokens": 64,
        "max_reduction_levels": 6,
        "max_subject_chars": 50,
    }
    values.update(overrides)
    return gc.Config(**values)


class TextChunkTests(unittest.TestCase):
    def test_unicode_and_long_line_are_preserved_exactly(self) -> None:
        text = "中文第一行\n" + "甲" * 120 + "\nlast-line"
        parts = gc.split_text_by_utf8_bytes(text, 31)
        self.assertEqual("".join(parts), text)
        self.assertGreater(len(parts), 3)
        self.assertTrue(all(gc.utf8_size(part) <= 31 for part in parts))

    def test_diff_segments_cover_every_character_once(self) -> None:
        diff = (
            "diff --git a/一.md b/一.md\n--- a/一.md\n+++ b/一.md\n@@ -1 +1 @@\n"
            + "-旧内容\n+新内容\n"
            + "diff --git a/two.md b/two.md\nnew file mode 100644\n"
            + "+" + "x" * 20_000 + "\n"
        )
        segments = gc.build_source_segments(diff, 9_000)
        self.assertEqual("".join(item.text for item in segments), diff)
        self.assertEqual(len({item.source_id for item in segments}), len(segments))


class SummaryTests(unittest.TestCase):
    def test_small_diff_uses_one_direct_final_call(self) -> None:
        client = RecordingClient()
        summarizer = gc.HierarchicalSummarizer(
            client, make_config(direct_input_bytes=80_000)
        )
        result = summarizer.summarize(
            "diff --git a/a.md b/a.md\n@@ -1 +1 @@\n-old\n+new\n"
        )
        self.assertEqual(result, "归纳全部笔记变更并优化提交摘要")
        self.assertEqual([call[3] for call in client.calls], ["final-direct"])

    def test_large_diff_sends_every_source_marker_to_leaf_calls(self) -> None:
        markers = [f"UNIQUE_MARKER_{index:03d}" for index in range(24)]
        sections = []
        for index, marker in enumerate(markers):
            sections.append(
                f"diff --git a/f{index}.md b/f{index}.md\n"
                f"--- a/f{index}.md\n+++ b/f{index}.md\n@@ -1 +1 @@\n"
                f"-old-{index}\n+{marker}-" + ("内容" * 500) + "\n"
            )
        diff = "".join(sections)
        client = RecordingClient(large_facts=True)
        summarizer = gc.HierarchicalSummarizer(
            client,
            make_config(
                direct_input_bytes=30_000,
                chunk_input_bytes=15_000,
                max_batch_items=4,
            ),
        )

        result = summarizer.summarize(diff)

        self.assertEqual(result, "归纳全部笔记变更并优化提交摘要")
        leaf_input = "\n".join(
            call[1] for call in client.calls if call[3].startswith("facts-diff")
        )
        for marker in markers:
            self.assertEqual(leaf_input.count(marker), 1)
        self.assertTrue(
            all(
                call[1].count("<SOURCE id=") <= 4
                for call in client.calls
                if call[3].startswith("facts-diff")
            )
        )
        self.assertTrue(
            any(call[3].startswith("facts-reduce") for call in client.calls)
        )
        self.assertEqual(client.calls[-1][3], "final-reduced")

    def test_invalid_json_is_retried_with_a_distinct_prompt(self) -> None:
        class RepairingClient(RecordingClient):
            def complete(
                self, system, user, max_tokens, purpose, validator=None
            ):
                self.calls.append((system, user, max_tokens, purpose))
                if purpose.endswith("format-0"):
                    result = "not-json"
                else:
                    result = json.dumps(
                        {
                            "covered_ids": ["S1"],
                            "changes": [
                                {
                                    "scope": "测试",
                                    "action": "修改",
                                    "facts": ["已修复"],
                                }
                            ],
                            "overall": "已修复",
                        },
                        ensure_ascii=False,
                    )
                return validator(result) if validator else result

        client = RepairingClient()
        summarizer = gc.HierarchicalSummarizer(client, make_config())
        node = summarizer._fact_call(
            gc.FACT_SYSTEM_PROMPT,
            "input",
            ("S1",),
            ("S1",),
            "facts-diff",
        )
        self.assertEqual(node.source_ids, ("S1",))
        self.assertEqual(len(client.calls), 2)
        self.assertIn("格式无效", client.calls[1][0])

    def test_subject_cleanup_is_single_line_and_bounded(self) -> None:
        raw = "提交摘要：" + "改" * 80 + "。\n额外正文"
        result = gc.clean_subject(raw, 50)
        self.assertNotIn("\n", result)
        self.assertLessEqual(len(result), 50)
        self.assertFalse(result.startswith("提交摘要"))

    def test_fact_response_rejects_missing_coverage_and_empty_changes(self) -> None:
        with self.assertRaises(gc.APIError):
            gc.normalize_fact_response(
                '{"covered_ids":[],"changes":[],"overall":"无"}', ["S1"]
            )
        with self.assertRaises(gc.APIError):
            gc.normalize_fact_response(
                '{"covered_ids":["S1"],"changes":[],"overall":"无"}', ["S1"]
            )


class CacheTests(unittest.TestCase):
    def test_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = gc.ResponseCache(Path(directory))
            self.assertIsNone(cache.get("a" * 64))
            cache.put("a" * 64, "摘要内容")
            self.assertEqual(cache.get("a" * 64), "摘要内容")

    def test_non_object_cache_file_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = gc.ResponseCache(Path(directory))
            key = "b" * 64
            path = cache._path(key)
            path.parent.mkdir(parents=True)
            path.write_text("[]", encoding="utf-8")
            self.assertIsNone(cache.get(key))


class DeepSeekClientTests(unittest.TestCase):
    def test_utf8_request_and_cached_response_with_local_server(self) -> None:
        requests: list[tuple[str | None, dict]] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                requests.append((self.headers.get("Authorization"), body))
                payload = json.dumps(
                    {"choices": [{"message": {"content": "中文响应"}}]},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                config = make_config(
                    api_url=f"http://127.0.0.1:{server.server_port}/chat/completions",
                    api_retries=1,
                    timeout_seconds=5,
                )
                client = gc.DeepSeekClient(
                    "test-key", config, gc.ResponseCache(Path(directory))
                )
                first = client.complete("系统提示", "完整中文 diff\n第二行", 64, "test")
                second = client.complete("系统提示", "完整中文 diff\n第二行", 64, "test")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(first, "中文响应")
        self.assertEqual(second, "中文响应")
        self.assertEqual(len(requests), 1)
        authorization, body = requests[0]
        self.assertEqual(authorization, "Bearer test-key")
        self.assertEqual(body["messages"][1]["content"], "完整中文 diff\n第二行")

    def test_invalid_response_is_not_cached_before_validation(self) -> None:
        responses = [
            "not-json",
            json.dumps(
                {
                    "covered_ids": ["S1"],
                    "changes": [
                        {"scope": "测试", "action": "修改", "facts": ["有效"]}
                    ],
                    "overall": "有效",
                },
                ensure_ascii=False,
            ),
        ]
        request_count = 0

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                nonlocal request_count
                length = int(self.headers["Content-Length"])
                self.rfile.read(length)
                content = responses[min(request_count, len(responses) - 1)]
                request_count += 1
                payload = json.dumps(
                    {"choices": [{"message": {"content": content}}]},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                config = make_config(
                    api_url=f"http://127.0.0.1:{server.server_port}/chat/completions",
                    api_retries=1,
                    timeout_seconds=5,
                )
                client = gc.DeepSeekClient(
                    "test-key", config, gc.ResponseCache(Path(directory))
                )
                validator = lambda value: gc.normalize_fact_response(value, ["S1"])
                with self.assertRaises(gc.APIError):
                    client.complete("system", "user", 64, "validated", validator)
                valid = client.complete("system", "user", 64, "validated", validator)
                cached = client.complete("system", "user", 64, "validated", validator)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(valid, cached)
        self.assertEqual(request_count, 2)


class GitSnapshotTests(unittest.TestCase):
    def run_git(self, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def test_snapshot_stages_tracked_untracked_deleted_and_unicode_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_git(root, "init", "-q")
            self.run_git(root, "config", "user.name", "Test")
            self.run_git(root, "config", "user.email", "test@example.com")
            (root / "tracked.md").write_text("old\n", encoding="utf-8")
            (root / "delete.md").write_text("delete me\n", encoding="utf-8")
            self.run_git(root, "add", "-A")
            self.run_git(root, "commit", "-qm", "base")

            (root / "tracked.md").write_text("new\n", encoding="utf-8")
            (root / "delete.md").unlink()
            (root / "中文 新文件.md").write_text("完整新内容\n", encoding="utf-8")

            repo = gc.GitRepository.discover(root)
            snapshot = repo.prepare_snapshot()

            self.assertIn("tracked.md", snapshot.changed_paths)
            self.assertIn("delete.md", snapshot.changed_paths)
            self.assertIn("中文 新文件.md", snapshot.changed_paths)
            self.assertIn("完整新内容", snapshot.diff)
            self.assertTrue(repo.is_stable(snapshot.tree, snapshot.head))

            (root / "tracked.md").write_text("changed during summary\n", encoding="utf-8")
            self.assertFalse(repo.is_stable(snapshot.tree, snapshot.head))

    def test_head_change_invalidates_snapshot_even_when_tree_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_git(root, "init", "-q")
            self.run_git(root, "config", "user.name", "Test")
            self.run_git(root, "config", "user.email", "test@example.com")
            (root / "note.md").write_text("base\n", encoding="utf-8")
            self.run_git(root, "add", "-A")
            self.run_git(root, "commit", "-qm", "base")

            repo = gc.GitRepository.discover(root)
            snapshot = repo.prepare_snapshot()
            self.run_git(root, "commit", "--allow-empty", "-qm", "other process")

            self.assertEqual(repo.tree_hash(), snapshot.tree)
            self.assertFalse(repo.is_stable(snapshot.tree, snapshot.head))

    def test_staged_only_snapshot_does_not_add_unstaged_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_git(root, "init", "-q")
            self.run_git(root, "config", "user.name", "Test")
            self.run_git(root, "config", "user.email", "test@example.com")
            (root / "staged.md").write_text("old\n", encoding="utf-8")
            (root / "unstaged.md").write_text("old\n", encoding="utf-8")
            self.run_git(root, "add", "-A")
            self.run_git(root, "commit", "-qm", "base")

            (root / "staged.md").write_text("new\n", encoding="utf-8")
            self.run_git(root, "add", "staged.md")
            (root / "unstaged.md").write_text("not for this commit\n", encoding="utf-8")
            (root / "untracked.md").write_text("also not staged\n", encoding="utf-8")

            repo = gc.GitRepository.discover(root)
            snapshot = repo.prepare_snapshot(stage_all=False)

            self.assertEqual(snapshot.changed_paths, ("staged.md",))
            self.assertNotIn("not for this commit", snapshot.diff)
            self.assertTrue(
                repo.is_stable(
                    snapshot.tree,
                    snapshot.head,
                    require_clean_worktree=False,
                )
            )


@unittest.skipUnless(
    shutil.which("powershell") and shutil.which("sh"),
    "PowerShell and sh are required",
)
class PowerShellWrapperTests(unittest.TestCase):
    @staticmethod
    def initialize_repo(root: Path) -> Path:
        plugin = root / ".obsidian" / "plugins" / "obsidian-git"
        plugin.mkdir(parents=True)
        shutil.copy2(PLUGIN_DIR / "gen-commit.ps1", plugin / "gen-commit.ps1")
        shutil.copy2(PLUGIN_DIR / "gen_commit.py", plugin / "gen_commit.py")

        def git(*args: str) -> None:
            subprocess.run(
                ["git", *args],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        git("init", "-q")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.com")
        git("add", "-A")
        git("commit", "-qm", "base")
        return plugin

    @staticmethod
    def run_wrapper(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                "sh",
                "-c",
                "powershell -NoProfile -ExecutionPolicy Bypass "
                "-File .obsidian/plugins/obsidian-git/gen-commit.ps1",
            ],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def test_wrapper_outputs_utf8_fallback_and_stages_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repo(root)

            def git(*args: str) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    ["git", *args],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )

            (root / "新笔记.md").write_text("全部内容\n", encoding="utf-8")

            env = os.environ.copy()
            env.pop("DEEPSEEK_API_KEY", None)
            env["DEEPSEEK_API_KEY_FILE"] = str(root / "missing-key")
            result = self.run_wrapper(root, env)
            stdout = result.stdout.decode("utf-8").strip()
            self.assertEqual(stdout, "更新笔记：新笔记.md")
            staged = git("diff", "--cached", "--name-only", "-z").stdout
            self.assertIn("新笔记.md", staged.decode("utf-8").split("\0"))

    def test_wrapper_calls_local_api_without_mixing_logs_into_stdout(self) -> None:
        requests: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                length = int(self.headers["Content-Length"])
                requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
                payload = json.dumps(
                    {"choices": [{"message": {"content": "完善完整变更摘要"}}]},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.initialize_repo(root)
                (root / "新笔记.md").write_text("全部内容\n", encoding="utf-8")
                env = os.environ.copy()
                env["DEEPSEEK_API_KEY"] = "test-key"
                env["DEEPSEEK_API_URL"] = (
                    f"http://127.0.0.1:{server.server_port}/chat/completions"
                )
                env["DEEPSEEK_API_RETRIES"] = "1"
                result = self.run_wrapper(root, env)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(result.stdout.decode("utf-8").strip(), "完善完整变更摘要")
        self.assertIn("[commit-summary]", result.stderr.decode("utf-8"))
        self.assertEqual(len(requests), 1)
        self.assertIn("+全部内容", requests[0]["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
