#!/usr/bin/env python3
"""Render a validated diff explanation as Markdown with Mermaid diagrams."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import re
import secrets
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath


SECTIONS = ("background", "intuition", "code")


class ValidationError(ValueError):
    """Input does not satisfy the report contract."""


def check(condition, path, message):
    if not condition:
        raise ValidationError(f"{path}: {message}")


def fields(value, required, path, optional=()):
    check(isinstance(value, dict), path, "must be an object")
    check(set(required) <= value.keys(), path, "missing required fields")
    check(value.keys() <= set(required) | set(optional), path, "unknown fields")


def text(value, path):
    check(
        isinstance(value, str) and bool(value.strip()), path, "must be non-empty text"
    )


def array(value, path, minimum=1):
    check(
        isinstance(value, list) and len(value) >= minimum,
        path,
        f"must be an array of at least {minimum} items",
    )


def validate_block(block, path):
    check(isinstance(block, dict), path, "must be an object")
    kind = block.get("type")
    if kind in ("heading", "paragraph"):
        fields(block, ("type", "text"), path)
        text(block["text"], path + ".text")
    elif kind == "list":
        fields(block, ("type", "ordered", "items"), path)
        check(isinstance(block["ordered"], bool), path, "ordered must be boolean")
        array(block["items"], path)
        for item in block["items"]:
            text(item, path)
    elif kind == "code":
        fields(block, ("type", "language", "code"), path, ("caption",))
        text(block["language"], path)
        check(
            bool(re.fullmatch(r"[A-Za-z0-9_+.-]+", block["language"])),
            path,
            "invalid code language",
        )
        text(block["code"], path)
        if "caption" in block:
            text(block["caption"], path)
    elif kind == "callout":
        fields(block, ("type", "tone", "title", "text"), path)
        check(block["tone"] in ("note", "key", "edge", "warning"), path, "invalid tone")
        text(block["title"], path)
        text(block["text"], path)
    elif kind in ("flow", "sequence"):
        nodes_key, edges_key = (
            ("nodes", "edges") if kind == "flow" else ("participants", "messages")
        )
        fields(block, ("type", "title", nodes_key, edges_key), path)
        text(block["title"], path)
        array(block[nodes_key], path, 2)
        array(block[edges_key], path)
        ids = set()
        for node in block[nodes_key]:
            required = ("id", "label", "detail") if kind == "flow" else ("id", "label")
            fields(node, required, path)
            for key in required:
                text(node[key], path)
            check(node["id"] not in ids, path, "duplicate diagram ID")
            ids.add(node["id"])
        connected = set()
        for edge in block[edges_key]:
            required = (
                ("from", "to", "label")
                if kind == "flow"
                else ("from", "to", "label", "kind")
            )
            fields(edge, required, path)
            for key in required:
                text(edge[key], path)
            check(
                edge["from"] in ids and edge["to"] in ids,
                path,
                "unknown diagram endpoint",
            )
            if kind == "sequence":
                check(
                    edge["kind"] in ("request", "response"),
                    path,
                    "invalid message kind",
                )
            connected.update((edge["from"], edge["to"]))
        check(connected == ids, path, "every diagram ID must participate")
    elif kind == "mockup":
        fields(block, ("type", "title", "regions"), path)
        text(block["title"], path)
        array(block["regions"], path)
        for region in block["regions"]:
            fields(region, ("label", "content"), path)
            text(region["label"], path)
            text(region["content"], path)
    else:
        raise ValidationError(f"{path}: unknown block type")


def validate_report(report):
    fields(
        report,
        (
            "title",
            "slug",
            "target",
            "repository",
            "summary",
            "sections",
            "quiz",
            "references",
        ),
        "report",
        ("_render",),
    )
    for key in ("title", "slug", "target", "repository", "summary"):
        text(report[key], key)
    fields(report["sections"], SECTIONS, "sections")
    for section in SECTIONS:
        array(report["sections"][section], section)
        for index, block in enumerate(report["sections"][section]):
            validate_block(block, f"{section}[{index}]")
    array(report["quiz"], "quiz", 5)
    check(len(report["quiz"]) == 5, "quiz", "requires exactly five questions")
    for question in report["quiz"]:
        fields(question, ("question", "options"), "quiz")
        text(question["question"], "question")
        array(question["options"], "options", 4)
        check(len(question["options"]) == 4, "options", "requires exactly four options")
        lengths = []
        for option in question["options"]:
            fields(option, ("text", "correct", "feedback"), "option")
            text(option["text"], "option.text")
            text(option["feedback"], "option.feedback")
            check(
                isinstance(option["correct"], bool), "option.correct", "must be boolean"
            )
            lengths.append(len(re.findall(r"\b[\w'-]+\b", option["text"])))
        check(
            sum(o["correct"] for o in question["options"]) == 1,
            "options",
            "requires one correct answer",
        )
        check(
            max(lengths) - min(lengths) <= max(3, math.ceil(min(lengths) * 0.35)),
            "options",
            "answer lengths are unbalanced",
        )
    array(report["references"], "references", 0)
    for ref in report["references"]:
        fields(ref, ("path", "start_line", "end_line", "label"), "reference")
        text(ref["path"], "reference.path")
        text(ref["label"], "reference.label")
        p, w = PurePosixPath(ref["path"]), PureWindowsPath(ref["path"])
        check(
            not (
                p.is_absolute()
                or w.is_absolute()
                or w.drive
                or ".." in p.parts
                or ".." in w.parts
            ),
            "reference.path",
            "must be repository-relative without traversal",
        )
        check(
            type(ref["start_line"]) is int
            and type(ref["end_line"]) is int
            and 1 <= ref["start_line"] <= ref["end_line"],
            "reference",
            "invalid line range",
        )
    if "_render" in report:
        fields(report["_render"], ("version", "seed"), "_render")
        check(
            type(report["_render"]["version"]) is int
            and report["_render"]["version"] == 1,
            "_render",
            "unsupported version",
        )
        check(
            type(report["_render"]["seed"]) is int and report["_render"]["seed"] >= 0,
            "_render",
            "invalid seed",
        )


def md(value):
    """Plain text stays text, including HTML and Markdown metacharacters."""
    value = " ".join(value.split())
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~\-])", r"\\\1", value).replace("&", "&amp;")


def fence(value, language):
    width = max(
        3, max((len(m.group()) + 1 for m in re.finditer(r"`+", value)), default=3)
    )
    marker = "`" * width
    return f"{marker}{language}\n{value.rstrip()}\n{marker}"


def label(value):
    # Mermaid's decimal entity syntax keeps punctuation out of its grammar.
    return "".join(
        c if c.isascii() and (c.isalnum() or c == " ") else f"#{ord(c)};"
        for c in " ".join(value.split())
    )


def diagram(block):
    flow = block["type"] == "flow"
    nodes = block["nodes" if flow else "participants"]
    ids = {node["id"]: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["flowchart LR" if flow else "sequenceDiagram"]
    for node in nodes:
        name = label(node["label"] + (": " + node["detail"] if flow else ""))
        lines.append(
            f'    {ids[node["id"]]}["{name}"]'
            if flow
            else f"    participant {ids[node['id']]} as {name}"
        )
    for edge in block["edges" if flow else "messages"]:
        start, end = ids[edge["from"]], ids[edge["to"]]
        name = label(edge["label"])
        if flow:
            lines.append(f'    {start} -->|"{name}"| {end}')
        else:
            arrow = "->>" if edge["kind"] == "request" else "-->>"
            lines.append(f"    {start}{arrow}{end}: {name}")
    return fence("\n".join(lines), "mermaid")


def render_block(block):
    kind = block["type"]
    if kind == "heading":
        return "### " + md(block["text"])
    if kind == "paragraph":
        return md(block["text"])
    if kind == "list":
        return "\n".join(
            f"{str(i) + '.' if block['ordered'] else '-'} {md(item)}"
            for i, item in enumerate(block["items"], 1)
        )
    if kind == "code":
        # Mermaid excerpts are source text; only structured diagrams render live.
        language = (
            "text" if block["language"].lower() == "mermaid" else block["language"]
        )
        return (md(block["caption"]) + "\n\n" if "caption" in block else "") + fence(
            block["code"], language
        )
    if kind == "callout":
        return f"> **{block['tone'].title()}: {md(block['title'])}**\n>\n> {md(block['text'])}"
    if kind in ("flow", "sequence"):
        return f"### {md(block['title'])}\n\n{diagram(block)}"
    return (
        "### "
        + md(block["title"])
        + "\n\n"
        + "\n".join(
            f"- **{md(r['label'])}:** {md(r['content'])}" for r in block["regions"]
        )
    )


def render_markdown(report, seed):
    parts = [
        "# " + md(report["title"]),
        md(report["summary"]),
        f"**Repository:** {md(report['repository'])}  \n**Target:** {md(report['target'])}",
    ]
    for section in SECTIONS:
        parts.append("## " + section.title())
        parts.extend(render_block(block) for block in report["sections"][section])
    rng = random.Random(seed)
    positions = list(range(4)) + [rng.randrange(4)]
    rng.shuffle(positions)
    arranged = []
    parts.append("## Quiz")
    for index, (question, position) in enumerate(zip(report["quiz"], positions), 1):
        options = [o for o in question["options"] if not o["correct"]]
        rng.shuffle(options)
        options.insert(position, next(o for o in question["options"] if o["correct"]))
        arranged.append(options)
        parts.append(
            f"### Question {index}\n\n{md(question['question'])}\n\n"
            + "\n".join(
                f"- **{chr(65 + i)}.** {md(o['text'])}" for i, o in enumerate(options)
            )
        )
    parts.append("## Answer key\n\nRead after attempting all five questions.")
    for index, options in enumerate(arranged, 1):
        parts.append(
            f"### Question {index}\n\n"
            + "\n".join(
                f"- **{chr(65 + i)} — {'Correct' if o['correct'] else 'Incorrect'}:** {md(o['feedback'])}"
                for i, o in enumerate(options)
            )
        )
    parts.append("## References")
    parts.extend(
        f"- {md(r['path'])}:{r['start_line']}–{r['end_line']} — {md(r['label'])}"
        for r in report["references"]
    )
    return "\n\n".join(parts) + "\n"


def write_report(report, output_dir, seed=None):
    validate_report(report)
    seed = (
        report.get("_render", {}).get("seed", secrets.randbits(64))
        if seed is None
        else seed
    )
    normalized = dict(report, _render={"version": 1, "seed": seed})
    validate_report(normalized)
    content = render_markdown(normalized, seed)
    slug = (
        re.sub(r"[^a-z0-9]+", "-", report["slug"].lower()).strip("-")[:80].rstrip("-")
        or "code-change"
    )
    base = f"{dt.date.today().isoformat()}-explanation-{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        stem = base if index == 1 else f"{base}-{index}"
        json_path, md_path = output_dir / f"{stem}.json", output_dir / f"{stem}.md"
        try:
            json_file = json_path.open("x", encoding="utf-8")
        except FileExistsError:
            index += 1
            continue
        try:
            md_file = md_path.open("x", encoding="utf-8")
        except OSError as error:
            json_file.close()
            json_path.unlink()
            if isinstance(error, FileExistsError):
                index += 1
                continue
            raise
        try:
            with json_file, md_file:
                json_file.write(
                    json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
                )
                md_file.write(content)
        except OSError:
            json_path.unlink(missing_ok=True)
            md_path.unlink(missing_ok=True)
            raise
        return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / ".local/share/opencode/explanations",
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.seed is not None and args.seed < 0:
            raise ValidationError("seed must be non-negative")
        report = json.loads(args.input.read_text(encoding="utf-8"))
        validate_report(report)
        if args.validate_only:
            print("Report is valid.")
        else:
            json_path, md_path = write_report(
                report, args.output_dir.expanduser(), args.seed
            )
            print(f"JSON: {json_path}\nMarkdown: {md_path}")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
