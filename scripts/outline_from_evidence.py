#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
outline_from_evidence.py - 从 evidence_cards.jsonl 生成知识型 XMind Markdown 大纲。

这个脚本不再把证据卡机械展开成“事实1/时间地点/人物对象”的来源流水账。
它先把每条证据转成可理解的知识点,再把时间、地点、人物、对象、数据和
来源放到“关键细节”和“证据托底”中。这样 XMind 首先承担知识传播功能,
证据负责校准和追溯。
"""
import argparse
import json
import os
import sys
from collections import defaultdict

from report_from_evidence import (  # noqa: E402
    CN_NUMS,
    CORE_GROUP_HEADINGS,
    CORE_ORDER_A,
    CORE_ORDER_B,
    CORE_SUBHEADING_HINTS,
    CORE_TITLE_HINTS,
    chunked,
    clean_text,
    compact_values,
    polished_claim,
    readable_source_title,
    read_json,
    read_jsonl,
    unique_values,
)


TYPE_LABELS = {
    "A": "企业、机构或品牌",
    "B": "博物馆、文化馆或历史文化主题",
    "C": "文旅、主题馆或主题空间",
    "D": "其他主题",
}

SOURCE_TYPE_LABELS = {
    "government": "政府、监管或官方公开资料",
    "academic": "学术资料",
    "institution_or_database": "机构或数据库资料",
    "media": "媒体报道",
    "web": "公开网页资料",
    "user": "用户提供资料",
}


def add(lines, depth, text):
    text = clean_text(text)
    if not text:
        return
    lines.append("%s- %s" % ("  " * depth, text))


def add_values(lines, depth, label, values, empty_text="未在证据卡中明确"):
    vals = compact_values(values, limit=8)
    add(lines, depth, label)
    if vals:
        for val in vals:
            add(lines, depth + 1, val)
    else:
        add(lines, depth + 1, empty_text)


def source_type_label(value):
    return SOURCE_TYPE_LABELS.get(clean_text(value), clean_text(value) or "未标注来源性质")


def group_label(core, index, cards):
    templates = CORE_GROUP_HEADINGS.get(core, [])
    if index <= len(templates):
        return templates[index - 1]
    base = CORE_SUBHEADING_HINTS.get(core, CORE_TITLE_HINTS.get(core, core))
    terms = []
    for field in ("objects", "people", "places", "data"):
        terms.extend(unique_values(cards, field, limit=3))
        if len(terms) >= 3:
            break
    if terms:
        return "%s:%s" % (base, "、".join(terms[:3]))
    return base


def source_count(cards):
    return len({c.get("source_url", "") for c in cards if c.get("source_url")})


def ordered_cores(type_code, by_core):
    if type_code == "A":
        order = CORE_ORDER_A
    elif type_code == "B":
        order = CORE_ORDER_B
    else:
        order = []
    out = [c for c in order if c in by_core]
    out.extend([c for c in by_core.keys() if c not in out])
    return out


def knowledge_label(card, index):
    terms = []
    for field in ("objects", "people", "places"):
        values = compact_values(card.get(field, []), limit=3)
        for value in values:
            if value not in terms:
                terms.append(value)
    if terms:
        return "%s的资料说明" % "、".join(terms[:3])
    claim = clean_text(card.get("claim", ""))
    if claim:
        return claim[:28].rstrip("，。；;:：") + "的资料说明"
    return "资料说明%d" % index


def add_optional_knowledge(lines, depth, card):
    extra_fields = [
        ("小白解释", "explanation"),
        ("机制说明", "mechanism"),
        ("边界说明", "boundary"),
        ("常见误区", "misconception"),
    ]
    for label, field in extra_fields:
        value = card.get(field)
        if not value:
            continue
        add(lines, depth, label)
        if isinstance(value, list):
            for item in value:
                add(lines, depth + 1, item)
        else:
            add(lines, depth + 1, value)
    teaching_points = card.get("teaching_points")
    if teaching_points:
        add(lines, depth, "讲解要点")
        for item in teaching_points if isinstance(teaching_points, list) else [teaching_points]:
            add(lines, depth + 1, item)


def add_card(lines, depth, card, index):
    claim = polished_claim(card)
    add(lines, depth, knowledge_label(card, index))
    add(lines, depth + 1, "知识解释")
    add(lines, depth + 2, claim)
    add_optional_knowledge(lines, depth + 1, card)

    add(lines, depth + 1, "关键细节")
    time = clean_text(card.get("time", ""))
    add(lines, depth + 2, "时间")
    add(lines, depth + 3, time or "未在证据卡中明确")
    add_values(lines, depth + 2, "地点", card.get("places", []))
    add_values(lines, depth + 2, "人物", card.get("people", []))
    add_values(lines, depth + 2, "对象", card.get("objects", []))
    add_values(lines, depth + 2, "数据", card.get("data", []))

    add(lines, depth + 1, "证据托底")
    add(lines, depth + 2, readable_source_title(card.get("source_title", "")))
    url = clean_text(card.get("source_url", ""))
    if url:
        add(lines, depth + 2, "链接")
        add(lines, depth + 3, url)
    add(lines, depth + 2, "资料性质:%s" % source_type_label(card.get("source_type", "")))
    confidence = clean_text(card.get("confidence", ""))
    add(lines, depth + 2, "采信边界:%s" % (confidence or "未标注"))


def build_outline(plan, cards, args):
    topic = args.title or plan.get("topic") or "资料调研"
    type_code = (args.type or plan.get("project_type", {}).get("code") or "D").upper()
    profile = plan.get("theme_profile", {})
    subject = profile.get("content_subject") or topic
    aliases = profile.get("subject_aliases") or []
    lines = ["# %s资料调研" % topic]

    add(lines, 0, "主题解读")
    add(lines, 1, "主题名称")
    add(lines, 2, topic)
    add(lines, 1, "资料主体")
    add(lines, 2, subject)
    if aliases:
        add_values(lines, 1, "别名与检索名称", aliases)
    add(lines, 1, "项目类型")
    add(lines, 2, TYPE_LABELS.get(type_code, type_code))
    add(lines, 1, "地域范围")
    add(lines, 2, plan.get("region") or "未标注")
    add(lines, 1, "资料规模")
    add(lines, 2, "本次归档形成%d条证据卡" % len(cards))
    add(lines, 2, "关联%d个公开来源或用户资料来源" % source_count(cards))
    source_ladder = profile.get("source_ladder") or []
    if source_ladder:
        add(lines, 1, "权威来源路线")
        for item in source_ladder:
            add(lines, 2, item)
    freshness = profile.get("freshness_rule")
    if freshness:
        add(lines, 1, "最新资料要求")
        add(lines, 2, freshness)

    by_core = defaultdict(list)
    for card in cards:
        core = clean_text(card.get("core", "其他资料"))
        if "来源索引" in core:
            continue
        by_core[core].append(card)

    for core_index, core in enumerate(ordered_cores(type_code, by_core), 2):
        core_title = CORE_TITLE_HINTS.get(core, core)
        add(lines, 0, core_title)
        groups = list(chunked(by_core[core], max(1, args.cards_per_group)))
        for group_index, group in enumerate(groups, 1):
            add(lines, 1, group_label(core, group_index, group))
            for card_index, card in enumerate(group, 1):
                add_card(lines, 2, card, card_index)

    add(lines, 0, "来源索引与待核实清单")
    source_map = {}
    for card in cards:
        url = clean_text(card.get("source_url", ""))
        if not url:
            continue
        source_map.setdefault(url, {
            "title": readable_source_title(card.get("source_title", "")),
            "type": source_type_label(card.get("source_type", "")),
            "confidence": clean_text(card.get("confidence", "")) or "未标注",
            "cores": set(),
        })
        source_map[url]["cores"].add(clean_text(card.get("core", "")))
    for idx, (url, info) in enumerate(source_map.items(), 1):
        add(lines, 1, "来源%d:%s" % (idx, info["title"] or url))
        add(lines, 2, "资料性质:%s" % info["type"])
        add(lines, 2, "采信边界:%s" % info["confidence"])
        add(lines, 2, "支撑内容")
        for core in sorted(info["cores"]):
            add(lines, 3, core)
        add(lines, 2, "链接")
        add(lines, 3, url)

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="从证据卡生成自然中文 XMind Markdown 大纲")
    ap.add_argument("--plan", required=True, help="research_plan.json")
    ap.add_argument("--evidence", required=True, help="evidence_cards.jsonl")
    ap.add_argument("--out", required=True, help="输出调研大纲.md")
    ap.add_argument("--title", default="")
    ap.add_argument("--type", default="")
    ap.add_argument("--cards-per-group", type=int, default=3)
    args = ap.parse_args()

    plan = read_json(args.plan)
    cards = list(read_jsonl(args.evidence))
    text = build_outline(plan, cards, args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print("已生成自然中文导图大纲: %s" % args.out)
    print("证据卡: %d" % len(cards))
    print("节点行: %d" % sum(1 for line in text.splitlines() if line.strip().startswith("- ")))


if __name__ == "__main__":
    sys.exit(main())
