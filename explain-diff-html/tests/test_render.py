import importlib.util
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


RENDERER_PATH = Path(__file__).parents[1] / "scripts" / "render.py"
SPEC = importlib.util.spec_from_file_location("explain_diff_renderer", RENDERER_PATH)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def option(text: str, correct: bool = False) -> dict:
    return {
        "text": text,
        "correct": correct,
        "feedback": "This feedback explains the mechanism rather than merely scoring it.",
    }


def valid_report() -> dict:
    quiz = []
    for index in range(5):
        quiz.append(
            {
                "question": f"Which mechanism establishes guarantee {index + 1}?",
                "options": [
                    option(
                        "The cursor advances after durable storage confirms success.",
                        True,
                    ),
                    option(
                        "The worker sorts each batch before dispatching queued jobs."
                    ),
                    option(
                        "The client retries every request before reading its status."
                    ),
                    option(
                        "The scheduler duplicates each task before assigning a worker."
                    ),
                ],
            }
        )
    return {
        "title": "Why retry order is now stable",
        "slug": "retry-order",
        "target": "main...retry-order",
        "repository": "queue-service",
        "summary": "The queue advances its cursor only after durable persistence succeeds.",
        "sections": {
            "background": [
                {"type": "heading", "text": "The existing queue"},
                {"type": "paragraph", "text": "Jobs move through a durable queue."},
            ],
            "intuition": [
                {
                    "type": "flow",
                    "title": "Persistence flow",
                    "nodes": [
                        {"id": "worker", "label": "Worker", "detail": "job-42"},
                        {"id": "store", "label": "Store", "detail": "commit succeeds"},
                    ],
                    "edges": [{"from": "worker", "to": "store", "label": "persist"}],
                }
            ],
            "code": [
                {
                    "type": "code",
                    "language": "python",
                    "code": "persist(job)\n  advance(cursor)",
                    "caption": "The cursor follows persistence.",
                },
                {
                    "type": "callout",
                    "tone": "key",
                    "title": "Ordering invariant",
                    "text": "A failed write cannot move the cursor.",
                },
            ],
        },
        "quiz": quiz,
        "references": [
            {
                "path": "src/queue.py",
                "start_line": 40,
                "end_line": 52,
                "label": "Cursor advancement",
            }
        ],
    }


class ValidationTests(unittest.TestCase):
    def test_valid_report_is_accepted(self) -> None:
        report = valid_report()
        self.assertIs(renderer.validate_report(report), report)

    def test_rejects_obviously_longer_answer(self) -> None:
        report = valid_report()
        report["quiz"][0]["options"][0]["text"] = (
            "The cursor advances only after durable storage has confirmed successful "
            "replication across every configured persistence node in the cluster."
        )
        with self.assertRaisesRegex(renderer.ValidationError, "answer lengths are"):
            renderer.validate_report(report)

    def test_rejects_instruction_shaped_unknown_fields(self) -> None:
        report = valid_report()
        report["sections"]["code"][0]["raw_html"] = "<script>run()</script>"
        with self.assertRaisesRegex(renderer.ValidationError, "unknown field"):
            renderer.validate_report(report)

    def test_rejects_flow_without_edges(self) -> None:
        report = valid_report()
        report["sections"]["intuition"][0]["edges"] = []
        with self.assertRaisesRegex(renderer.ValidationError, "must not be empty"):
            renderer.validate_report(report)

    def test_rejects_disconnected_flow_nodes(self) -> None:
        report = valid_report()
        report["sections"]["intuition"][0]["nodes"].append(
            {"id": "orphan", "label": "Orphan", "detail": "No edge"}
        )
        with self.assertRaisesRegex(renderer.ValidationError, "must participate"):
            renderer.validate_report(report)

    def test_rejects_non_relative_reference_paths(self) -> None:
        invalid_paths = [
            "/home/user/project/file.py",
            "C:\\Users\\user\\project\\file.py",
            "C:private\\file.py",
            "../private/file.py",
            "src/../../private/file.py",
            "src\\..\\private\\file.py",
        ]
        for path in invalid_paths:
            with self.subTest(path=path):
                report = valid_report()
                report["references"][0]["path"] = path
                with self.assertRaisesRegex(
                    renderer.ValidationError,
                    "repository-relative|parent traversal",
                ):
                    renderer.validate_report(report)

    def test_accepts_repository_relative_reference_path(self) -> None:
        report = valid_report()
        report["references"][0]["path"] = "src/queue/worker.py"
        self.assertIs(renderer.validate_report(report), report)


class ShuffleTests(unittest.TestCase):
    def test_positions_are_reproducible_and_balanced(self) -> None:
        first = renderer.answer_positions(8128)
        second = renderer.answer_positions(8128)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {0, 1, 2, 3})
        self.assertEqual(len(first), 5)

    def test_correct_answers_use_balanced_positions(self) -> None:
        report = valid_report()
        shuffled = renderer.shuffled_quiz(report["quiz"], 42)
        positions = [
            next(i for i, item in enumerate(options) if item["correct"])
            for options in shuffled
        ]
        self.assertEqual(set(positions), {0, 1, 2, 3})


class RenderingTests(unittest.TestCase):
    def test_untrusted_text_is_escaped(self) -> None:
        report = valid_report()
        report["sections"]["background"][1]["text"] = (
            '</script><script src="https://bad.invalid/x.js">'
        )
        output = renderer.render_html(report, 1, "2026-08-14")
        self.assertIn(
            "&lt;/script&gt;&lt;script src=&quot;https://bad.invalid/x.js&quot;&gt;",
            output,
        )
        self.assertNotIn('<script src="https://bad.invalid/x.js">', output)

    def test_code_uses_pre_and_preserves_whitespace(self) -> None:
        output = renderer.render_html(valid_report(), 1, "2026-08-14")
        self.assertIn("<pre><code>persist(job)\n  advance(cursor)</code></pre>", output)
        self.assertRegex(output, r"\.code pre\{[^}]*white-space:pre")

    def test_output_pair_persists_seed_and_avoids_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            first_json, first_html = renderer.write_report(
                valid_report(), output_dir, seed=99
            )
            second_json, second_html = renderer.write_report(
                valid_report(), output_dir, seed=99
            )
            self.assertTrue(first_json.exists() and first_html.exists())
            self.assertTrue(second_json.exists() and second_html.exists())
            self.assertNotEqual(first_json, second_json)
            saved = json.loads(first_json.read_text(encoding="utf-8"))
            self.assertEqual(saved["_render"], {"version": 1, "seed": 99})
            self.assertNotRegex(first_html.read_text(encoding="utf-8"), r"https?://")

    def test_concurrent_renders_create_distinct_complete_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(
                        lambda seed: renderer.write_report(
                            valid_report(), output_dir, seed=seed
                        ),
                        range(8),
                    )
                )

            paths = [path for pair in results for path in pair]
            self.assertEqual(len(set(paths)), 16)
            for json_path, html_path in results:
                saved = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["slug"], "retry-order")
                self.assertIn("<!doctype html>", html_path.read_text(encoding="utf-8"))

    def test_existing_symlink_is_not_followed_or_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            date = renderer.dt.date.today().isoformat()
            base = output_dir / f"{date}-explanation-retry-order"
            sentinel = output_dir / "sentinel.txt"
            sentinel.write_text("unchanged", encoding="utf-8")
            base.with_suffix(".html").symlink_to(sentinel)

            json_path, html_path = renderer.write_report(
                valid_report(), output_dir, seed=99
            )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")
            self.assertFalse(base.with_suffix(".json").exists())
            self.assertTrue(json_path.name.endswith("-2.json"))
            self.assertTrue(html_path.name.endswith("-2.html"))


if __name__ == "__main__":
    unittest.main()
