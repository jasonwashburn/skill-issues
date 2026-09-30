import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mermaid_renderer", ROOT / "scripts/render.py"
)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "examples/example-report.json").read_text())

    def test_render_preserves_diagrams_quiz_feedback_and_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path, md_path = renderer.write_report(self.report, Path(directory), 17)
            normalized = json.loads(json_path.read_text())
            output = md_path.read_text()
            self.assertIn("```mermaid\nflowchart LR", output)
            self.assertIn("```mermaid\nsequenceDiagram", output)
            self.assertIn("n1-->>n0: Commit succeeded", output)
            self.assertEqual(output.count(" — Correct:"), 5)
            self.assertEqual(output.count(" — Incorrect:"), 15)
            self.assertLess(output.index("## Quiz"), output.index("## Answer key"))
            quiz = output.split("## Quiz\n", 1)[1].split("## Answer key", 1)[0]
            for letter in "ABCD":
                self.assertEqual(quiz.count(f"\n- **{letter}.** "), 5)
            self.assertEqual(
                output,
                renderer.render_markdown(normalized, normalized["_render"]["seed"]),
            )
            again = renderer.write_report(normalized, Path(directory))
            self.assertNotEqual(md_path, again[1])
            self.assertEqual(output, again[1].read_text())

    def test_reviewed_text_cannot_inject_diagram_statements_or_break_code_fences(self):
        for block in self.report["sections"]["intuition"][1:]:
            nodes = block.get("nodes", block.get("participants"))
            nodes[0]["id"] = 'end\nclick n0 "https://example.com"'
            nodes[0]["label"] = 'Worker"; <script> & %%{init: {}}%%\nend'
            edges = block.get("edges", block.get("messages"))
            edges[0]["from"] = nodes[0]["id"]
            if block["type"] == "sequence":
                edges[1]["to"] = nodes[0]["id"]
            edges[0]["label"] = 'result|"\nclick n0'
        self.report["title"] = "<img src=x> [click](https://example.com)"
        self.report["sections"]["code"][1]["code"] = (
            "```\n<script>example</script>\n```"
        )
        renderer.validate_report(self.report)
        output = renderer.render_markdown(self.report, 1)
        self.assertIn('n0["Worker#34;#59;', output)
        self.assertNotIn("\nclick n0", output)
        self.assertIn("#60;script#62;", output)
        self.assertIn("````python\n```", output)
        self.assertIn(r"\<img src=x\>", output)

    def test_mermaid_code_excerpts_remain_literal_text(self):
        code = (
            '%%{init: {"securityLevel": "loose"}}%%\n'
            'flowchart LR\nA --> B\nclick A "https://example.com"'
        )
        for language in ("mermaid", "Mermaid"):
            with self.subTest(language=language):
                self.report["sections"]["code"][1].update(language=language, code=code)
                renderer.validate_report(self.report)
                output = renderer.render_markdown(self.report, 1)
                self.assertIn(f"```text\n{code}\n```", output)
                self.assertEqual(output.count("```mermaid\n"), 2)

    def test_rejects_broken_evidence_diagrams_and_quizzes_before_writing(self):
        invalid = []
        report = copy.deepcopy(self.report)
        report["sections"]["intuition"][1]["edges"][0]["to"] = "missing"
        invalid.append(report)
        report = copy.deepcopy(self.report)
        report["references"][0]["path"] = "../private.py"
        invalid.append(report)
        report = copy.deepcopy(self.report)
        report["quiz"][0]["options"][1]["correct"] = True
        invalid.append(report)
        report = copy.deepcopy(self.report)
        report["quiz"][0]["options"][1]["text"] = " ".join(["extra"] * 30)
        invalid.append(report)
        for report in invalid:
            with (
                self.subTest(report=report),
                tempfile.TemporaryDirectory() as directory,
            ):
                with self.assertRaises(renderer.ValidationError):
                    renderer.write_report(report, Path(directory))
                self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
