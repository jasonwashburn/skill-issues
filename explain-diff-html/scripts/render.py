#!/usr/bin/env python3
"""Render a validated explain-diff report as self-contained HTML."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import random
import re
import secrets
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, TextIO


VERSION = 1
SECTION_TITLES = {
    "background": "Background",
    "intuition": "Intuition",
    "code": "Code",
}
BLOCK_TYPES = {"heading", "paragraph", "list", "code", "callout", "flow", "mockup"}
CALLOUT_TONES = {"note", "key", "edge", "warning"}


class ValidationError(ValueError):
    """Raised when report input does not satisfy the rendering contract."""


def fail(path: str, message: str) -> None:
    raise ValidationError(f"{path}: {message}")


def require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(path, "must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        fail(path, "must be an array")
    return value


def require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(path, "must be a non-empty string")
    return value.strip()


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail(path, "must be a boolean")
    return value


def require_keys(
    value: dict[str, Any], required: set[str], allowed: set[str], path: str
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        fail(path, f"missing required field(s): {', '.join(missing)}")
    if unknown:
        fail(path, f"contains unknown field(s): {', '.join(unknown)}")


def validate_block(block: Any, path: str) -> None:
    item = require_dict(block, path)
    kind = require_text(item.get("type"), f"{path}.type")
    if kind not in BLOCK_TYPES:
        fail(f"{path}.type", f"must be one of {', '.join(sorted(BLOCK_TYPES))}")

    if kind in {"heading", "paragraph"}:
        require_keys(item, {"type", "text"}, {"type", "text"}, path)
        require_text(item["text"], f"{path}.text")
        return

    if kind == "list":
        require_keys(
            item, {"type", "ordered", "items"}, {"type", "ordered", "items"}, path
        )
        require_bool(item["ordered"], f"{path}.ordered")
        values = require_list(item["items"], f"{path}.items")
        if not values:
            fail(f"{path}.items", "must not be empty")
        for index, value in enumerate(values):
            require_text(value, f"{path}.items[{index}]")
        return

    if kind == "code":
        require_keys(
            item,
            {"type", "language", "code"},
            {"type", "language", "code", "caption"},
            path,
        )
        require_text(item["language"], f"{path}.language")
        if not isinstance(item["code"], str) or not item["code"]:
            fail(f"{path}.code", "must be a non-empty string")
        if "caption" in item:
            require_text(item["caption"], f"{path}.caption")
        return

    if kind == "callout":
        require_keys(
            item,
            {"type", "tone", "title", "text"},
            {"type", "tone", "title", "text"},
            path,
        )
        tone = require_text(item["tone"], f"{path}.tone")
        if tone not in CALLOUT_TONES:
            fail(f"{path}.tone", f"must be one of {', '.join(sorted(CALLOUT_TONES))}")
        require_text(item["title"], f"{path}.title")
        require_text(item["text"], f"{path}.text")
        return

    if kind == "flow":
        require_keys(
            item,
            {"type", "title", "nodes", "edges"},
            {"type", "title", "nodes", "edges"},
            path,
        )
        require_text(item["title"], f"{path}.title")
        nodes = require_list(item["nodes"], f"{path}.nodes")
        edges = require_list(item["edges"], f"{path}.edges")
        if len(nodes) < 2:
            fail(f"{path}.nodes", "must contain at least two nodes")
        if not edges:
            fail(f"{path}.edges", "must not be empty")
        node_ids: set[str] = set()
        for index, node in enumerate(nodes):
            node_path = f"{path}.nodes[{index}]"
            node = require_dict(node, node_path)
            require_keys(
                node, {"id", "label", "detail"}, {"id", "label", "detail"}, node_path
            )
            node_id = require_text(node["id"], f"{node_path}.id")
            if node_id in node_ids:
                fail(f"{node_path}.id", "must be unique within the flow")
            node_ids.add(node_id)
            require_text(node["label"], f"{node_path}.label")
            require_text(node["detail"], f"{node_path}.detail")
        connected_node_ids: set[str] = set()
        for index, edge in enumerate(edges):
            edge_path = f"{path}.edges[{index}]"
            edge = require_dict(edge, edge_path)
            require_keys(
                edge, {"from", "to", "label"}, {"from", "to", "label"}, edge_path
            )
            start = require_text(edge["from"], f"{edge_path}.from")
            end = require_text(edge["to"], f"{edge_path}.to")
            require_text(edge["label"], f"{edge_path}.label")
            if start not in node_ids or end not in node_ids:
                fail(edge_path, "must refer only to node IDs in this flow")
            connected_node_ids.update((start, end))
        if connected_node_ids != node_ids:
            fail(f"{path}.nodes", "every node must participate in an edge")
        return

    require_keys(item, {"type", "title", "regions"}, {"type", "title", "regions"}, path)
    require_text(item["title"], f"{path}.title")
    regions = require_list(item["regions"], f"{path}.regions")
    if not regions:
        fail(f"{path}.regions", "must not be empty")
    for index, region in enumerate(regions):
        region_path = f"{path}.regions[{index}]"
        region = require_dict(region, region_path)
        require_keys(region, {"label", "content"}, {"label", "content"}, region_path)
        require_text(region["label"], f"{region_path}.label")
        require_text(region["content"], f"{region_path}.content")


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def validate_report(report: Any) -> dict[str, Any]:
    data = require_dict(report, "report")
    required = {
        "title",
        "slug",
        "target",
        "repository",
        "summary",
        "sections",
        "quiz",
        "references",
    }
    require_keys(data, required, required | {"_render"}, "report")
    for field in ("title", "slug", "target", "repository", "summary"):
        require_text(data[field], f"report.{field}")

    sections = require_dict(data["sections"], "report.sections")
    require_keys(sections, set(SECTION_TITLES), set(SECTION_TITLES), "report.sections")
    for section_name in SECTION_TITLES:
        blocks = require_list(sections[section_name], f"report.sections.{section_name}")
        if not blocks:
            fail(f"report.sections.{section_name}", "must not be empty")
        for index, block in enumerate(blocks):
            validate_block(block, f"report.sections.{section_name}[{index}]")

    quiz = require_list(data["quiz"], "report.quiz")
    if len(quiz) != 5:
        fail("report.quiz", "must contain exactly five questions")
    for question_index, question in enumerate(quiz):
        question_path = f"report.quiz[{question_index}]"
        question = require_dict(question, question_path)
        require_keys(
            question, {"question", "options"}, {"question", "options"}, question_path
        )
        require_text(question["question"], f"{question_path}.question")
        options = require_list(question["options"], f"{question_path}.options")
        if len(options) != 4:
            fail(f"{question_path}.options", "must contain exactly four options")
        correct_count = 0
        lengths: list[int] = []
        for option_index, option in enumerate(options):
            option_path = f"{question_path}.options[{option_index}]"
            option = require_dict(option, option_path)
            require_keys(
                option,
                {"text", "correct", "feedback"},
                {"text", "correct", "feedback"},
                option_path,
            )
            text = require_text(option["text"], f"{option_path}.text")
            correct_count += int(
                require_bool(option["correct"], f"{option_path}.correct")
            )
            require_text(option["feedback"], f"{option_path}.feedback")
            lengths.append(word_count(text))
        if correct_count != 1:
            fail(f"{question_path}.options", "must contain exactly one correct option")
        shortest, longest = min(lengths), max(lengths)
        allowance = max(3, math.ceil(shortest * 0.35))
        if longest - shortest > allowance:
            fail(
                f"{question_path}.options",
                f"answer lengths are {lengths} words; longest may exceed shortest by at most {allowance}",
            )

    references = require_list(data["references"], "report.references")
    for index, reference in enumerate(references):
        ref_path = f"report.references[{index}]"
        reference = require_dict(reference, ref_path)
        require_keys(
            reference,
            {"path", "start_line", "end_line", "label"},
            {"path", "start_line", "end_line", "label"},
            ref_path,
        )
        reference_path = require_text(reference["path"], f"{ref_path}.path")
        posix_path = PurePosixPath(reference_path)
        windows_path = PureWindowsPath(reference_path)
        if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
            fail(f"{ref_path}.path", "must be repository-relative")
        if ".." in posix_path.parts or ".." in windows_path.parts:
            fail(f"{ref_path}.path", "must not contain parent traversal")
        require_text(reference["label"], f"{ref_path}.label")
        start, end = reference["start_line"], reference["end_line"]
        if isinstance(start, bool) or not isinstance(start, int) or start < 1:
            fail(f"{ref_path}.start_line", "must be a positive integer")
        if isinstance(end, bool) or not isinstance(end, int) or end < start:
            fail(
                f"{ref_path}.end_line",
                "must be an integer at least as large as start_line",
            )

    if "_render" in data:
        render = require_dict(data["_render"], "report._render")
        require_keys(render, {"version", "seed"}, {"version", "seed"}, "report._render")
        if render["version"] != VERSION:
            fail("report._render.version", f"must equal {VERSION}")
        if (
            isinstance(render["seed"], bool)
            or not isinstance(render["seed"], int)
            or render["seed"] < 0
        ):
            fail("report._render.seed", "must be a non-negative integer")
    return data


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80].rstrip("-") or "code-change"


def answer_positions(seed: int, count: int = 5) -> list[int]:
    rng = random.Random(seed)
    positions = list(range(4))
    while len(positions) < count:
        positions.append(rng.randrange(4))
    rng.shuffle(positions)
    return positions


def shuffled_quiz(quiz: list[dict[str, Any]], seed: int) -> list[list[dict[str, Any]]]:
    rng = random.Random(seed)
    positions = answer_positions(seed, len(quiz))
    result: list[list[dict[str, Any]]] = []
    for question, correct_position in zip(quiz, positions):
        correct = next(option for option in question["options"] if option["correct"])
        distractors = [
            option for option in question["options"] if not option["correct"]
        ]
        rng.shuffle(distractors)
        arranged = distractors[:]
        arranged.insert(correct_position, correct)
        result.append(arranged)
    return result


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_block(block: dict[str, Any]) -> str:
    kind = block["type"]
    if kind == "heading":
        return f'<h3 class="subheading">{esc(block["text"])}</h3>'
    if kind == "paragraph":
        return f"<p>{esc(block['text'])}</p>"
    if kind == "list":
        tag = "ol" if block["ordered"] else "ul"
        items = "".join(f"<li>{esc(item)}</li>" for item in block["items"])
        return f"<{tag}>{items}</{tag}>"
    if kind == "code":
        caption = (
            f"<figcaption>{esc(block['caption'])}</figcaption>"
            if block.get("caption")
            else ""
        )
        return (
            f'<figure class="code"><div class="code-bar"><span>{esc(block["language"])}</span></div>'
            f"<pre><code>{esc(block['code'])}</code></pre>{caption}</figure>"
        )
    if kind == "callout":
        return (
            f'<aside class="callout {esc(block["tone"])}"><strong>{esc(block["title"])}</strong>'
            f"<p>{esc(block['text'])}</p></aside>"
        )
    if kind == "flow":
        nodes = {node["id"]: node for node in block["nodes"]}
        connected: list[str] = []
        for edge in block["edges"]:
            start, end = nodes[edge["from"]], nodes[edge["to"]]
            connected.append(
                '<div class="flow-row">'
                f'<div class="flow-node"><strong>{esc(start["label"])}</strong><span>{esc(start["detail"])}</span></div>'
                f'<div class="flow-edge"><span>{esc(edge["label"])}</span><b aria-hidden="true">→</b></div>'
                f'<div class="flow-node"><strong>{esc(end["label"])}</strong><span>{esc(end["detail"])}</span></div>'
                "</div>"
            )
        return f'<figure class="diagram"><figcaption>{esc(block["title"])}</figcaption>{"".join(connected)}</figure>'
    regions = "".join(
        f'<div class="mock-region"><span>{esc(region["label"])}</span><p>{esc(region["content"])}</p></div>'
        for region in block["regions"]
    )
    return (
        f'<figure class="diagram mockup"><figcaption>{esc(block["title"])}</figcaption>'
        f'<div class="mock-window"><div class="mock-chrome" aria-hidden="true"><i></i><i></i><i></i></div>{regions}</div></figure>'
    )


def render_quiz(report: dict[str, Any], seed: int) -> str:
    arranged_quiz = shuffled_quiz(report["quiz"], seed)
    questions: list[str] = []
    letters = "ABCD"
    for question_index, (question, options) in enumerate(
        zip(report["quiz"], arranged_quiz), start=1
    ):
        rendered_options = []
        for option_index, option in enumerate(options):
            correct = "true" if option["correct"] else "false"
            rendered_options.append(
                f'<button class="answer" type="button" data-correct="{correct}" '
                f'aria-describedby="feedback-{question_index}-{option_index}">'
                f'<span class="answer-letter">{letters[option_index]}</span><span>{esc(option["text"])}</span></button>'
                f'<div class="answer-feedback" id="feedback-{question_index}-{option_index}" hidden>{esc(option["feedback"])}</div>'
            )
        questions.append(
            f'<article class="question" data-question="{question_index}"><div class="question-number">Question {question_index} of 5</div>'
            f'<h3>{esc(question["question"])}</h3><div class="answers">{"".join(rendered_options)}</div>'
            '<p class="result" role="status" aria-live="polite"></p></article>'
        )
    return "".join(questions)


def render_references(references: list[dict[str, Any]]) -> str:
    if not references:
        return '<p class="muted">No line-specific references were available.</p>'
    items = []
    for reference in references:
        location = (
            f"{reference['path']}:{reference['start_line']}-{reference['end_line']}"
        )
        items.append(
            f"<li><code>{esc(location)}</code><span>{esc(reference['label'])}</span></li>"
        )
    return f'<ul class="references">{"".join(items)}</ul>'


CSS = r"""
:root{--ink:#18201f;--muted:#5d6966;--paper:#f5f1e8;--card:#fffdf8;--line:#d9d2c3;--accent:#b5482c;--accent-dark:#7e2f1e;--teal:#276b67;--gold:#d49b3b;--shadow:0 16px 45px rgba(51,43,31,.10);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--paper);line-height:1.65}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(90deg,rgba(181,72,44,.035) 1px,transparent 1px),linear-gradient(rgba(39,107,103,.03) 1px,transparent 1px),var(--paper);background-size:32px 32px}a{color:var(--accent-dark);text-underline-offset:3px}a:focus-visible,button:focus-visible{outline:3px solid var(--gold);outline-offset:3px}.masthead{padding:5rem max(1.5rem,calc((100vw - 1080px)/2));background:var(--ink);color:#fffdf8;position:relative;overflow:hidden}.masthead:after{content:"";position:absolute;width:380px;height:380px;border:80px solid var(--accent);border-radius:50%;right:-130px;top:-170px;opacity:.55}.eyebrow{font-size:.75rem;letter-spacing:.16em;text-transform:uppercase;color:#e7bc77;font-weight:800}.masthead h1{font-family:Georgia,"Times New Roman",serif;font-size:clamp(2.5rem,7vw,5.4rem);line-height:.98;max-width:900px;margin:.7rem 0 1.4rem;letter-spacing:-.045em;position:relative;z-index:1}.summary{font-size:1.16rem;max-width:750px;color:#dce5df;position:relative;z-index:1}.meta{display:flex;flex-wrap:wrap;gap:.65rem;margin-top:1.8rem;position:relative;z-index:1}.meta span{border:1px solid #53605d;border-radius:999px;padding:.35rem .75rem;font-size:.8rem;color:#e7e1d5}.layout{display:grid;grid-template-columns:220px minmax(0,760px);gap:64px;max-width:1080px;margin:0 auto;padding:3.5rem 1.5rem 7rem}.toc{position:sticky;top:1.5rem;align-self:start;border-top:4px solid var(--accent);padding-top:1rem}.toc strong{font-family:Georgia,serif}.toc a{display:block;color:var(--muted);text-decoration:none;padding:.4rem 0;border-bottom:1px solid var(--line);font-size:.9rem}.toc a:hover{color:var(--accent)}main section{scroll-margin-top:1rem;margin-bottom:5rem}.section-kicker{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:900}.section-title{font-family:Georgia,"Times New Roman",serif;font-size:clamp(2.2rem,5vw,3.5rem);line-height:1.05;margin:.3rem 0 1.5rem;letter-spacing:-.035em}.subheading{font-family:Georgia,"Times New Roman",serif;font-size:1.55rem;line-height:1.2;margin:2.5rem 0 .7rem}p,li{font-size:1.02rem}li+li{margin-top:.45rem}.callout{margin:2rem 0;padding:1rem 1.2rem 1rem 1.4rem;border-left:5px solid var(--teal);background:var(--card);box-shadow:var(--shadow)}.callout strong{font-family:Georgia,serif;font-size:1.1rem}.callout p{margin:.3rem 0 0}.callout.key{border-color:var(--accent)}.callout.edge{border-color:var(--gold)}.callout.warning{border-color:#923b3b;background:#fff8f5}.code{margin:2rem 0;background:#111918;color:#e7ece9;border-radius:5px;overflow:hidden;box-shadow:var(--shadow)}.code-bar{padding:.55rem 1rem;background:#202b29;color:#9ec5bd;font:700 .72rem ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.08em}.code pre{margin:0;padding:1.25rem;overflow-x:auto;white-space:pre;font:14px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace}.code figcaption{padding:.65rem 1rem;background:#202b29;color:#c7d0cc;font-size:.8rem}.diagram{margin:2.2rem 0;padding:1.2rem;background:#ece6d9;border:1px solid var(--line);box-shadow:var(--shadow)}.diagram>figcaption{font:700 1rem Georgia,serif;margin-bottom:1rem}.flow-row{display:grid;grid-template-columns:minmax(0,1fr) 120px minmax(0,1fr);align-items:stretch;margin:.75rem 0}.flow-node{display:flex;flex-direction:column;justify-content:center;background:var(--card);border-top:4px solid var(--teal);padding:1rem;min-height:95px}.flow-node span{color:var(--muted);font-size:.85rem;margin-top:.3rem}.flow-edge{display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--accent);text-align:center;font-size:.72rem}.flow-edge b{font-size:1.7rem;line-height:1}.mock-window{background:var(--card);border:1px solid #b9b1a2}.mock-chrome{height:30px;background:#25312f;display:flex;gap:6px;align-items:center;padding:0 10px}.mock-chrome i{display:block;width:8px;height:8px;border-radius:50%;background:#d7a14c}.mock-region{margin:1rem;padding:1rem;border:1px solid var(--line);background:#fff}.mock-region span{display:block;color:var(--teal);font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;font-weight:800}.mock-region p{margin:.25rem 0 0}.question{padding:1.4rem;margin:1.3rem 0;background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow)}.question-number{font-size:.72rem;color:var(--accent);font-weight:900;text-transform:uppercase;letter-spacing:.12em}.question h3{font:700 1.3rem/1.3 Georgia,serif}.answers{display:grid;gap:.7rem}.answer{display:grid;grid-template-columns:2rem 1fr;align-items:center;text-align:left;gap:.75rem;width:100%;padding:.8rem;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;cursor:pointer}.answer:hover:not(:disabled){border-color:var(--teal);transform:translateY(-1px)}.answer-letter{display:grid;place-items:center;width:2rem;height:2rem;background:#e7eee9;color:var(--teal);font-size:.8rem;font-weight:900}.answer.correct{border-color:var(--teal);background:#f0f7f3}.answer.incorrect{border-color:#a24b3f;background:#fff4f1}.answer-feedback{margin:-.3rem 0 .5rem;padding:.7rem 1rem;background:#f1ede4;color:var(--muted);font-size:.9rem}.result{font-weight:800;min-height:1.6rem;margin-bottom:0}.references{list-style:none;padding:0}.references li{display:grid;grid-template-columns:minmax(170px,auto) 1fr;gap:1rem;padding:.8rem 0;border-bottom:1px solid var(--line)}.references code{color:var(--teal);overflow-wrap:anywhere}.muted{color:var(--muted)}.footer{padding:2rem;text-align:center;background:var(--ink);color:#bfc9c5;font-size:.8rem}
@media(max-width:760px){.masthead{padding:3.5rem 1.25rem}.layout{display:block;padding:2rem 1.1rem 5rem}.toc{position:static;margin-bottom:3.5rem}.flow-row{grid-template-columns:1fr}.flow-edge{min-height:75px}.flow-edge b{transform:rotate(90deg)}.references li{grid-template-columns:1fr;gap:.2rem}.code pre{white-space:pre;overflow-x:auto}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.answer{transition:none}}
"""


SCRIPT = r"""
document.querySelectorAll('.question').forEach((question) => {
  const buttons = Array.from(question.querySelectorAll('.answer'));
  const result = question.querySelector('.result');
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      if (question.dataset.answered === 'true') return;
      question.dataset.answered = 'true';
      const isCorrect = button.dataset.correct === 'true';
      buttons.forEach((candidate) => {
        candidate.disabled = true;
        if (candidate.dataset.correct === 'true') candidate.classList.add('correct');
      });
      if (!isCorrect) button.classList.add('incorrect');
      const feedback = button.nextElementSibling;
      feedback.hidden = false;
      result.textContent = isCorrect ? 'Correct.' : 'Not quite. The correct answer is highlighted.';
    });
  });
});
"""


def render_html(report: dict[str, Any], seed: int, generated_date: str) -> str:
    sections = []
    for index, (section_name, title) in enumerate(SECTION_TITLES.items(), start=1):
        blocks = "".join(
            render_block(block) for block in report["sections"][section_name]
        )
        sections.append(
            f'<section id="{section_name}"><div class="section-kicker">Section {index:02d}</div>'
            f'<h2 class="section-title">{title}</h2>{blocks}</section>'
        )
    quiz = render_quiz(report, seed)
    references = render_references(report["references"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>{esc(report["title"])}</title>
<style>{CSS}</style>
</head>
<body>
<header class="masthead">
  <div class="eyebrow">Code change field guide</div>
  <h1>{esc(report["title"])}</h1>
  <p class="summary">{esc(report["summary"])}</p>
  <div class="meta"><span>{esc(report["repository"])}</span><span>{esc(report["target"])}</span><span>{esc(generated_date)}</span></div>
</header>
<div class="layout">
  <nav class="toc" aria-label="Table of contents"><strong>On this page</strong><a href="#background">Background</a><a href="#intuition">Intuition</a><a href="#code">Code</a><a href="#quiz">Quiz</a><a href="#references">References</a></nav>
  <main>{"".join(sections)}
    <section id="quiz"><div class="section-kicker">Section 04</div><h2 class="section-title">Quiz</h2><p>Choose the best answer. Each response includes an explanation.</p>{quiz}</section>
    <section id="references"><div class="section-kicker">Evidence</div><h2 class="section-title">References</h2>{references}</section>
  </main>
</div>
<footer class="footer">Generated from validated structured data by explain-diff-html.</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


def reserve_paths(
    output_dir: Path, date: str, slug: str
) -> tuple[Path, Path, TextIO, TextIO]:
    base = f"{date}-explanation-{slug}"
    suffix = 1
    while True:
        stem = base if suffix == 1 else f"{base}-{suffix}"
        json_path = output_dir / f"{stem}.json"
        html_path = output_dir / f"{stem}.html"
        try:
            json_file = json_path.open("x", encoding="utf-8")
        except FileExistsError:
            suffix += 1
            continue
        try:
            html_file = html_path.open("x", encoding="utf-8")
        except FileExistsError:
            json_file.close()
            json_path.unlink()
            suffix += 1
            continue
        return json_path, html_path, json_file, html_file


def write_report(
    report: dict[str, Any], output_dir: Path, seed: int | None = None
) -> tuple[Path, Path]:
    validate_report(report)
    resolved_seed: int = (
        report.get("_render", {}).get("seed", secrets.randbits(64))
        if seed is None
        else seed
    )
    normalized = dict(report)
    normalized["_render"] = {"version": VERSION, "seed": resolved_seed}
    validate_report(normalized)

    date = dt.date.today().isoformat()
    json_content = json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
    html_content = render_html(normalized, resolved_seed, date)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, html_path, json_file, html_file = reserve_paths(
        output_dir, date, safe_slug(report["slug"])
    )
    try:
        with json_file, html_file:
            json_file.write(json_content)
            html_file.write(html_content)
    except OSError:
        json_path.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
        raise
    return json_path, html_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 report JSON")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / ".local" / "share" / "opencode" / "explanations",
        help="destination directory (default: %(default)s)",
    )
    parser.add_argument("--seed", type=int, help="fixed non-negative quiz shuffle seed")
    parser.add_argument(
        "--validate-only", action="store_true", help="validate without writing output"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.seed is not None and args.seed < 0:
            raise ValidationError("--seed must be a non-negative integer")
        report = json.loads(args.input.read_text(encoding="utf-8"))
        validate_report(report)
        if args.validate_only:
            print("Report is valid.")
            return 0
        json_path, html_path = write_report(
            report, args.output_dir.expanduser(), args.seed
        )
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"JSON: {json_path}")
    print(f"HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
