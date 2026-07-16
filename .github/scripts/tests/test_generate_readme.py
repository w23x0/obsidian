from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "generate_readme.py"
SPEC = importlib.util.spec_from_file_location("generate_readme_under_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
generate_readme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_readme)


def timeline_item(commit_hash: str, timestamp: str, message: str):
    return {
        "hash": commit_hash,
        "datetime": datetime.fromisoformat(timestamp),
        "message": message,
        "changes": [],
    }


class BalancedHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            raise AssertionError(f"unbalanced HTML tag: {tag}; stack={self.stack}")
        self.stack.pop()


class FilteringAndCacheTests(unittest.TestCase):
    def test_automation_requires_bot_identity_and_marker(self):
        bot = "github-actions[bot]@users.noreply.github.com"
        self.assertTrue(
            generate_readme.is_automation(
                "docs: auto-update README stats & timeline [skip ci]", bot
            )
        )
        self.assertFalse(
            generate_readme.is_automation(
                "解释 auto-update workflow 的笔记", "student@example.com"
            )
        )
        self.assertFalse(generate_readme.is_automation("更新课程笔记", bot))

    def test_low_information_messages_require_llm_summary(self):
        for message in (
            "vault backup: 2026-07-08 22:54:28",
            "1",
            "123",
            "readme",
            "DIFY",
            "First backup",
        ):
            with self.subTest(message=message):
                self.assertTrue(generate_readme.needs_llm_summary(message))
        self.assertFalse(generate_readme.needs_llm_summary("补充 RAG 学习资源"))

    def test_summary_cache_accepts_only_safe_single_line_entries(self):
        valid_hash = "a" * 40
        legacy_hash = "b" * 40
        carriage_return_hash = "c" * 40
        newline_hash = "d" * 40
        long_hash = "e" * 40
        payload = {
            "schema_version": 1,
            "summaries": {
                valid_hash: {"summary": "  补充线性代数证明  "},
                legacy_hash: "整理微积分笔记",
                carriage_return_hash: "第一行\r第二行",
                newline_hash: "第一行\n第二行",
                long_hash: "长" * 51,
                "not-a-full-hash": "无效键",
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache = Path(temporary_directory) / "history_summaries.json"
            cache.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            with mock.patch.object(generate_readme, "HISTORY_SUMMARIES", cache):
                summaries = generate_readme.load_history_summaries()

        self.assertEqual(
            summaries,
            {
                valid_hash: "补充线性代数证明",
                legacy_hash: "整理微积分笔记",
            },
        )


class TimelineParsingTests(unittest.TestCase):
    @staticmethod
    def record(commit_hash, subject, timestamp, email, path="笔记.md"):
        return (
            f"\x1e{commit_hash}\x1f{subject}\x1f{timestamp}\x1f{email}\x00"
            f"\nM\x00{path}\x00"
        )

    def test_git_timeline_filters_bot_commit_sorts_and_uses_override(self):
        old_hash = "a" * 40
        new_hash = "b" * 40
        bot_hash = "c" * 40
        human_skip_hash = "d" * 40
        log_output = "".join(
            [
                self.record(
                    old_hash,
                    "vault backup: 2026-07-01 00:30:00",
                    "2026-07-01T00:30:00+08:00",
                    "student@example.com",
                ),
                self.record(
                    bot_hash,
                    "docs: auto-update README stats & timeline [skip ci]",
                    "2026-07-01T03:00:00+08:00",
                    "github-actions[bot]@users.noreply.github.com",
                ),
                self.record(
                    human_skip_hash,
                    "讲解 [skip ci] 的含义",
                    "2026-07-01T02:00:00+08:00",
                    "student@example.com",
                ),
                self.record(
                    new_hash,
                    "更新控制原理笔记",
                    "2026-06-30T17:00:00+00:00",
                    "student@example.com",
                ),
            ]
        )
        with (
            mock.patch.object(generate_readme, "run_git", return_value=log_output),
            mock.patch.object(
                generate_readme,
                "load_history_summaries",
                return_value={old_hash: "补充线性代数证明"},
            ),
        ):
            items = generate_readme.git_timeline()
            first_only = generate_readme.git_timeline(1)

        self.assertEqual(
            [item["hash"] for item in items],
            [human_skip_hash, new_hash, old_hash],
        )
        self.assertEqual(items[-1]["message"], "补充线性代数证明")
        self.assertEqual(items[-1]["changes"], [{"status": "M", "path": "笔记.md"}])
        self.assertEqual(first_only[0]["hash"], human_skip_hash)


class TimezoneAndHTMLTests(unittest.TestCase):
    def test_daily_counts_use_shanghai_natural_day(self):
        log_output = "\n".join(
            [
                "2026-06-30T16:30:00Z",
                "2026-07-01T00:30:00+08:00",
                "invalid timestamp",
            ]
        )
        with mock.patch.object(generate_readme, "run_git", return_value=log_output):
            counts = generate_readme.git_daily_counts()

        self.assertEqual(dict(counts), {"2026-07-01": 2})

    def test_bucket_boundaries_use_shanghai_calendar(self):
        now_utc = datetime.fromisoformat("2026-07-15T16:00:00+00:00")
        self.assertEqual(
            generate_readme.history_bucket(
                datetime.fromisoformat("2026-06-30T16:30:00+00:00"), now_utc
            ),
            ("day", "2026-07-01"),
        )
        self.assertEqual(
            generate_readme.history_bucket(
                datetime.fromisoformat("2025-12-31T16:30:00+00:00"), now_utc
            ),
            ("month", "2026-01"),
        )
        self.assertEqual(
            generate_readme.history_bucket(
                datetime.fromisoformat("2025-12-01T00:00:00+00:00"), now_utc
            ),
            ("year", "2025"),
        )

    def test_recent_timeline_displays_shanghai_time_and_escapes_message(self):
        item = timeline_item(
            "a" * 40,
            "2026-06-30T16:30:00+00:00",
            "补充 <控制器> & 参数",
        )
        output = generate_readme.gen_timeline([item])
        self.assertIn("07-01&nbsp;00:30", output)
        self.assertIn("2026-07-01 00:30", output)
        self.assertIn('datetime="2026-06-30T16:30:00+00:00"', output)
        self.assertIn("补充 &lt;控制器&gt; &amp; 参数", output)
        self.assertNotIn("补充 <控制器>", output)

    def test_archive_is_sorted_grouped_linked_escaped_and_balanced(self):
        items = [
            timeline_item(
                "d" * 40, "2025-12-01T00:00:00+00:00", "往年更新"
            ),
            timeline_item(
                "b" * 40, "2026-06-15T08:00:00+00:00", "六月更新"
            ),
            timeline_item(
                "a" * 40,
                "2026-06-30T16:30:00+00:00",
                "<script>alert('x')</script> & 整理",
            ),
            timeline_item(
                "c" * 40, "2025-12-31T16:30:00+00:00", "一月更新"
            ),
        ]
        now = datetime.fromisoformat("2026-07-16T00:00:00+08:00")
        with mock.patch.object(
            generate_readme,
            "github_repo_url",
            return_value="https://github.com/w23x0/obsidian",
        ):
            output = generate_readme.gen_history_archive(items, now)

        labels = ["2026-07-01", "2026-06", "2026-01", "2025"]
        positions = [output.index(f"<strong>{label}</strong>") for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(output.count("<details>"), 4)
        self.assertEqual(output.count("</details>"), 4)
        self.assertIn("07-01&nbsp;00:30", output)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; 整理", output)
        self.assertNotIn("<script>", output)
        self.assertIn(
            f'https://github.com/w23x0/obsidian/commit/{"a" * 40}', output
        )

        parser = BalancedHTMLParser()
        parser.feed(output)
        parser.close()
        self.assertEqual(parser.stack, [])


if __name__ == "__main__":
    unittest.main()
