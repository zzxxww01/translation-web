from src.services.claude_alignment import Target, align_claude_translation, pair_blocks, parse_blocks

EN = """# Datacenters 2027: The Year of Acceleration

By Jeremie Eliahou Ontiveros and Dylan Patel

## Introduction

Not a week goes without another piece of datacenter FUD about the 2027 buildout.

![](https://cdn.example.com/img1.png)

Behind these pictures there are real shortages of labor and transformers.

- There aren't enough wafers for the 12-hi cubes
- 4-Hi resolves the stranded memory capacity issue

## Will There Be Enough GPUs?

HBM takes roughly 3x the wafer area of commodity DRAM per bit.
"""

ZH = """# 2027 数据中心：加速之年

作者：Jeremie Eliahou Ontiveros、Dylan Patel

## 引言

每周都有新的数据中心唱衰论调，矛头指向 2027 年的建设。

![](https://cdn.example.com/img1.png)

这些图片背后，劳动力和变压器确实短缺。

- 晶圆不够做 12-hi 堆叠
- 4-Hi 解决了容量「搁浅」的问题

## GPU 够不够？

每比特 HBM 占用的晶圆面积约为普通 DRAM 的 3 倍。
"""


def targets():
    return [
        Target("p000", "s0", "By Jeremie Eliahou Ontiveros and Dylan Patel"),
        Target("section:s1", "s1", "Introduction", "section"),
        Target("p001", "s1", "Not a week goes without another piece of datacenter FUD about the 2027 buildout."),
        Target("p002", "s1", "https://cdn.example.com/img1.png", "image"),
        Target("p003", "s1", "Behind these pictures there are real shortages of labor and transformers."),
        Target("p004", "s1", "There aren't enough wafers for the 12-hi cubes", "li"),
        Target("p005", "s1", "4-Hi resolves the stranded memory capacity issue", "li"),
        Target("section:s2", "s2", "Will There Be Enough GPUs?", "section"),
        Target("p006", "s2", "HBM takes roughly 3x the wafer area of commodity DRAM per bit."),
    ]


def test_parse_blocks_strips_markers_and_keeps_structure():
    kinds = [(b.kind, b.text[:6]) for b in parse_blocks(ZH)]
    assert kinds[0] == ("h1", "2027 数")
    assert ("li", "晶圆不够做 ") in kinds and ("image", "![](ht") in kinds


def test_one_to_one_alignment_fills_every_target_and_extracts_title():
    result = align_claude_translation(EN, ZH, targets())
    assert result.title == "2027 数据中心：加速之年"
    assert result.texts["section:s1"] == "引言"
    assert result.texts["p001"].startswith("每周都有")
    assert result.texts["p005"] == "4-Hi 解决了容量「搁浅」的问题"
    assert result.texts["section:s2"] == "GPU 够不够？"
    assert result.stats["unaligned"] == 0


def test_block_split_across_two_paragraphs_keeps_all_chinese_on_the_first():
    en = "## Intro\n\nAlpha beta gamma delta. Epsilon zeta eta theta.\n"
    zh = "## 引言\n\n甲乙丙丁。戊己庚辛。\n"
    split = [Target("section:s", "s", "Intro", "section"),
             Target("p1", "s", "Alpha beta gamma delta."), Target("p2", "s", "Epsilon zeta eta theta.")]
    result = align_claude_translation(en, zh, split)
    assert result.texts["p1"] == "甲乙丙丁。戊己庚辛。" and "p2" not in result.texts
    assert result.stats["split_failures"] == 1


def test_block_missing_from_project_is_merged_into_previous_paragraph():
    en = "First paragraph about wafer supply.\n\nSubscribe for the full model.\n\nSecond paragraph about HBM demand.\n"
    zh = "关于晶圆供给的第一段。\n\n订阅即可获取完整模型。\n\n关于 HBM 需求的第二段。\n"
    project = [Target("p1", "s", "First paragraph about wafer supply."), Target("p2", "s", "Second paragraph about HBM demand.")]
    result = align_claude_translation(en, zh, project)
    assert result.texts["p1"] == "关于晶圆供给的第一段。\n\n订阅即可获取完整模型。"
    assert result.texts["p2"] == "关于 HBM 需求的第二段。"
    assert result.stats["merged_blocks"] == 1


def test_extra_chinese_block_is_paired_with_its_neighbour_not_dropped():
    en = parse_blocks("## A\n\nOne 2027 paragraph.\n\n## B\n")
    zh = parse_blocks("## 甲\n\n一段 2027。\n\n补充一句。\n\n## 乙\n")
    pairs = dict(pair_blocks(en, zh))
    assert pairs[1] == [1, 2] and pairs[2] == [3]
