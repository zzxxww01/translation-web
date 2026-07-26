# -*- coding: utf-8 -*-
"""Generate the four-step-translate skill glossary from the single term source.

单一术语源整改（C-1）：`glossary/global_glossary_semi.json` 是唯一术语源，
skill 侧的 `references/glossary-en-zh.md` 由本脚本生成，禁止手工双向维护。

用法：
    python scripts/sync_glossary_to_skill.py                # 输出到 stdout 预览
    python scripts/sync_glossary_to_skill.py --output out.md  # 写入指定文件

默认**不**写入 skill 目录；确认无误后，把 --output 指向
`~/.claude/skills/four-step-translate/references/glossary-en-zh.md` 手动同步。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GLOSSARY = REPO_ROOT / "glossary" / "global_glossary_semi.json"

HEADER = """# English → Chinese Glossary

> 本文件由 `translation_agent/scripts/sync_glossary_to_skill.py` 从
> `glossary/global_glossary_semi.json`（单一术语源）生成，请勿手工编辑。

Terms where standard translation is non-obvious or easily mistranslated. Common terms with straightforward translations are omitted.

| English | Chinese | Notes |
|---------|---------|-------|
"""

FOOTER = """
> **硬性红线**（保留英文清单、语气锚定、结构零增删、数字换算、标点空格）见 [hard-rules-zh.md](hard-rules-zh.md)，优先级高于本表。
"""

STRATEGY_HINTS = {
    "preserve": "保留英文，不加注释",
    "preserve_annotate": "首现保留英文+括注中文，后文只用英文",
    "first_annotate": "首现写中文（English），后文只用中文",
    "translate": "",
}


def _cell(value: str) -> str:
    """Escape a markdown table cell."""
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(glossary: dict) -> str:
    rows = []
    for term in glossary.get("terms", []):
        if term.get("status", "active") != "active":
            continue
        original = _cell(term.get("original", ""))
        if not original:
            continue

        strategy = term.get("strategy", "translate")
        translation = _cell(term.get("translation") or "")
        if strategy == "preserve" and not translation:
            translation = original

        note_parts = []
        hint = STRATEGY_HINTS.get(strategy, "")
        if hint:
            note_parts.append(hint)
        note = _cell(term.get("note") or "")
        if note:
            note_parts.append(note)

        rows.append(f"| {original} | {translation} | {'；'.join(note_parts)} |")

    version = glossary.get("version", "?")
    body = HEADER + "\n".join(rows) + "\n" + FOOTER
    return body.replace(
        "# English → Chinese Glossary",
        f"# English → Chinese Glossary (v{version})",
        1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate skill-side glossary-en-zh.md from global_glossary_semi.json"
    )
    parser.add_argument(
        "--glossary",
        type=Path,
        default=DEFAULT_GLOSSARY,
        help=f"Path to the JSON term source (default: {DEFAULT_GLOSSARY})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output markdown path; omit to print to stdout",
    )
    args = parser.parse_args(argv)

    glossary = json.loads(args.glossary.read_text(encoding="utf-8"))
    markdown = render_markdown(glossary)

    if args.output is None:
        sys.stdout.write(markdown)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.output} ({len(markdown.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
