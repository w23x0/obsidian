from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "backfill_history.py"
SPEC = importlib.util.spec_from_file_location("backfill_history_under_test", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SCRIPT}")
bh = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bh
SPEC.loader.exec_module(bh)


def make_input(index: int, diff: str = "+new content\n") -> bh.CommitInput:
    oid = f"{index:040x}"
    return bh.CommitInput(
        record=bh.CommitRecord(
            oid=oid,
            parents=(),
            email="author@example.com",
            committed_at="2026-07-16T12:00:00+08:00",
            subject="vault backup: 2026-07-16 12:00:00",
        ),
        diff=diff,
        diff_sha256=f"{index:064x}",
    )


class ClassificationTests(unittest.TestCase):
    def test_automation_requires_bot_email_and_known_subject(self) -> None:
        self.assertTrue(
            bh.is_automation(
                "auto-update README [skip ci]", "github-actions[bot]@users.noreply.github.com"
            )
        )
        self.assertFalse(bh.is_automation("auto-update README", "author@example.com"))
        self.assertFalse(
            bh.is_automation(
                "Meaningful manual change", "github-actions[bot]@users.noreply.github.com"
            )
        )

    def test_low_information_subjects_are_selected_for_backfill(self) -> None:
        selected = [
            "vault backup: 2026-01-01 00:00:00",
            "VAULT BACKUP: old format",
            "1",
            "123",
            " README ",
            "First Backup",
            "dify",
        ]
        retained = ["feat: improve README", "backup course notes", "123 notes"]

        for subject in selected:
            with self.subTest(subject=subject):
                self.assertTrue(bh.needs_llm_summary(subject))
        for subject in retained:
            with self.subTest(subject=subject):
                self.assertFalse(bh.needs_llm_summary(subject))


class BatchResponseTests(unittest.TestCase):
    def test_valid_response_covers_exact_ids_and_normalizes_summaries(self) -> None:
        ids = ["a" * 40, "b" * 40]
        response = json.dumps(
            {
                "covered_ids": list(reversed(ids)),
                "summaries": {
                    ids[1]: "整理第二门课程。",
                    ids[0]: "提交摘要：补充第一门课程",
                },
            },
            ensure_ascii=False,
        )

        normalized = json.loads(bh.normalize_batch_response(response, ids))

        self.assertEqual(normalized["covered_ids"], ids)
        self.assertEqual(
            normalized["summaries"],
            {ids[0]: "补充第一门课程", ids[1]: "整理第二门课程"},
        )

    def test_response_rejects_incomplete_duplicate_or_extra_coverage(self) -> None:
        first, second, extra = "a" * 40, "b" * 40, "c" * 40
        invalid_payloads = [
            {"covered_ids": [first], "summaries": {first: "整理内容"}},
            {
                "covered_ids": [first, first],
                "summaries": {first: "整理内容", second: "补充内容"},
            },
            {
                "covered_ids": [first, second, extra],
                "summaries": {
                    first: "整理内容",
                    second: "补充内容",
                    extra: "增加内容",
                },
            },
            {
                "covered_ids": [first, second],
                "summaries": {
                    first: "整理内容",
                    second: "补充内容",
                    extra: "增加内容",
                },
            },
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(bh.BackfillError):
                    bh.normalize_batch_response(
                        json.dumps(payload, ensure_ascii=False), [first, second]
                    )

    def test_response_rejects_invalid_or_generic_summary_text(self) -> None:
        oid = "a" * 40
        for summary in ["", "第一行\n第二行", "更新笔记", "改" * 51]:
            with self.subTest(summary=summary):
                payload = {
                    "covered_ids": [oid],
                    "summaries": {oid: summary},
                }
                with self.assertRaises(bh.BackfillError):
                    bh.normalize_batch_response(
                        json.dumps(payload, ensure_ascii=False), [oid]
                    )


class BatchPackingTests(unittest.TestCase):
    def test_batches_cover_every_input_once_and_respect_commit_limit(self) -> None:
        items = [make_input(index) for index in range(1, 6)]
        batches, oversized = bh.pack_batches(
            items,
            input_budget=bh.prompt_size(items),
            max_commits=2,
        )

        self.assertEqual(oversized, [])
        self.assertEqual([len(batch) for batch in batches], [2, 2, 1])
        flattened = [item.record.oid for batch in batches for item in batch]
        self.assertEqual(flattened, [item.record.oid for item in items])
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_oversized_item_is_routed_out_without_losing_other_items(self) -> None:
        first = make_input(1, "+small one\n")
        oversized_item = make_input(2, "+" + "large" * 2_000 + "\n")
        last = make_input(3, "+small two\n")
        budget = max(bh.prompt_size([first]), bh.prompt_size([last]))

        batches, oversized = bh.pack_batches(
            [first, oversized_item, last], input_budget=budget, max_commits=10
        )

        self.assertEqual(oversized, [oversized_item])
        self.assertTrue(all(bh.prompt_size(batch) <= budget for batch in batches))
        self.assertTrue(all(len(batch) <= 10 for batch in batches))
        routed = [item for batch in batches for item in batch] + oversized
        self.assertCountEqual(routed, [first, oversized_item, last])
        self.assertEqual(len(routed), len({item.record.oid for item in routed}))


class StoreTests(unittest.TestCase):
    def test_cached_summary_matches_only_current_prompt_and_diff(self) -> None:
        item = make_input(1)
        valid = bh.make_entry(item, "补充课程知识点", "deepseek-chat")
        self.assertTrue(bh.cached_summary_matches(valid, item, "deepseek-chat"))

        invalid_entries = [
            None,
            "补充课程知识点",
            {**valid, "summary": ""},
            {**valid, "summary": "第一行\n第二行"},
            {**valid, "summary": "改" * 51},
            {**valid, "prompt_version": "old-prompt"},
            {**valid, "diff_sha256": "0" * 64},
        ]
        for entry in invalid_entries:
            with self.subTest(entry=entry):
                self.assertFalse(
                    bh.cached_summary_matches(entry, item, "deepseek-chat")
                )

        wrong_model = dict(valid, model="another-model")
        self.assertFalse(
            bh.cached_summary_matches(wrong_model, item, "deepseek-chat")
        )

    def test_atomic_save_replaces_a_same_directory_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "history_summaries.json"
            store = bh._new_store("deepseek-chat")
            store["summaries"]["a" * 40] = {"summary": "补充课程知识点"}
            replace_calls: list[tuple[Path, Path]] = []
            real_replace = os.replace

            def recording_replace(source: os.PathLike[str], target: os.PathLike[str]) -> None:
                source_path, target_path = Path(source), Path(target)
                self.assertTrue(source_path.exists())
                self.assertEqual(source_path.parent, path.parent)
                self.assertEqual(
                    json.loads(source_path.read_text(encoding="utf-8"))["schema_version"],
                    1,
                )
                replace_calls.append((source_path, target_path))
                real_replace(source_path, target_path)

            with mock.patch.object(bh.os, "replace", side_effect=recording_replace):
                bh.atomic_save_store(path, store)

            self.assertEqual(len(replace_calls), 1)
            temporary, target = replace_calls[0]
            self.assertEqual(target, path)
            self.assertFalse(temporary.exists())
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summaries"]["a" * 40]["summary"], "补充课程知识点")
            self.assertRegex(saved["updated_at"], r"Z$")

    def test_atomic_save_removes_temporary_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history_summaries.json"
            original = '{"existing": true}\n'
            path.write_text(original, encoding="utf-8")
            with mock.patch.object(bh.os, "replace", side_effect=OSError("locked")):
                with self.assertRaises(bh.BackfillError):
                    bh.atomic_save_store(path, bh._new_store("deepseek-chat"))

            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
