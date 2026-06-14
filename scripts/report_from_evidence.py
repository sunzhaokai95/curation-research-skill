#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_from_evidence.py - 从 evidence_cards.jsonl 生成资料报告型 Markdown。

报告是可读文本,不是 XMind 节点列表。它复用同一批证据卡,把事实、时间、
人物、地点、数据和来源组织成分章段落,用于后续转成 .docx。
"""
import argparse
import datetime
import json
import os
import re
import sys
from collections import defaultdict


CORE_ORDER_A = [
    "主体身份与名称体系",
    "创始人/领导层/组织结构",
    "产品业务谱系",
    "技术能力与生产系统",
    "市场客户与产业链",
    "财经资本/上市IPO/融资/估值/收入",
    "监管诉讼/合规/风险",
    "最新动态/近一年/近90天",
    "同类企业事实对照",
]

CORE_ORDER_B = [
    "主题边界与名称体系",
    "生平年谱",
    "家族师友与关系网络",
    "时代制度背景",
    "地理行旅与空间遗存",
    "作品文献/版本/注本",
    "实物馆藏/碑刻/图像档案",
    "思想风格与术语体系",
    "后世接受/传播/研究史",
    "当代保护/出版/数字化/纪念活动",
]

CN_NUMS = [
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
]

CORE_TITLE_HINTS = {
    "主体身份与名称体系": "主体身份与名称体系",
    "创始人/领导层/组织结构": "人物与组织结构",
    "产品业务谱系": "产品与业务谱系",
    "技术能力与生产系统": "技术能力与生产系统",
    "市场客户与产业链": "市场客户与产业链",
    "财经资本/上市IPO/融资/估值/收入": "财经资本、IPO 与收入口径",
    "监管诉讼/合规/风险": "监管、诉讼与合规风险",
    "最新动态/近一年/近90天": "最新动态与当前状态",
    "同类企业事实对照": "同类对象事实对照",
    "主题边界与名称体系": "主题边界与名称体系",
    "生平年谱": "生平年谱与人生阶段",
    "家族师友与关系网络": "家族师友与关系网络",
    "时代制度背景": "时代制度与社会背景",
    "地理行旅与空间遗存": "地理行旅与空间遗存",
    "作品文献/版本/注本": "作品、文献、版本与注本",
    "实物馆藏/碑刻/图像档案": "实物、馆藏、碑刻与图像档案",
    "思想风格与术语体系": "思想风格与术语体系",
    "后世接受/传播/研究史": "后世接受、传播与研究史",
    "当代保护/出版/数字化/纪念活动": "当代保护、出版整理与公共传播",
    "来源索引与待核实清单": "来源索引与待核实清单",
}

CORE_SUBHEADING_HINTS = {
    "主体身份与名称体系": "名称、登记与主体边界",
    "创始人/领导层/组织结构": "人物、股权与治理线索",
    "产品业务谱系": "产品线、业务入口与能力边界",
    "技术能力与生产系统": "技术能力、设施与运行数据",
    "市场客户与产业链": "客户场景、合同与产业链关系",
    "财经资本/上市IPO/融资/估值/收入": "资本事件、估值与收入口径",
    "监管诉讼/合规/风险": "监管事项、诉讼与风险口径",
    "最新动态/近一年/近90天": "近期事件、时间节点与状态变化",
    "同类企业事实对照": "同类对象与事实差异",
    "主题边界与名称体系": "名称、身份与主题边界",
    "生平年谱": "年谱节点、转折事件与阶段线索",
    "家族师友与关系网络": "人物关系、家族与师友网络",
    "时代制度背景": "制度背景、政局与社会环境",
    "地理行旅与空间遗存": "行旅地点、任职地与遗存线索",
    "作品文献/版本/注本": "作品、版本与文本来源",
    "实物馆藏/碑刻/图像档案": "实物、馆藏与图像档案",
    "思想风格与术语体系": "思想术语、风格与观念线索",
    "后世接受/传播/研究史": "后世评价、传播与研究脉络",
    "当代保护/出版/数字化/纪念活动": "保护出版、数字化与公共传播",
}

INTRO_BY_TYPE = {
    "A": "本报告围绕企业主体、产品技术、市场客户、资本动态、监管风险与国际对照展开。它只整理公开资料事实,不进入后续方案表达。",
    "B": "本报告围绕主题边界、生平年谱、人物关系、时代背景、地理行旅、作品文献、实物档案、思想风格、传播接受与当代保护展开。它只整理可核验资料,不进入后续方案表达。",
    "C": "本报告先研究主题本体,再展开历史源流、分类对象、行为场景、社群语言、产业消费、政策伦理与最新动态。它只提供资料基础,不进入运营方案表达。",
    "D": "本报告围绕主题定义、历史、对象、机制、场景、数据、政策、文化传播、最新动态和来源口径展开。它只整理公开资料事实,不进入后续方案表达。",
}


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def clean_text(text):
    text = str(text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def ensure_sentence(text):
    text = clean_text(text)
    if not text:
        return ""
    if text[-1] not in "。！？.!?":
        text += "。"
    return text


def join_values(values):
    if isinstance(values, list):
        vals = [clean_text(v) for v in values if clean_text(v)]
    elif values:
        vals = [clean_text(values)]
    else:
        vals = []
    return "、".join(vals)


def card_sentence(card):
    claim = ensure_sentence(card.get("claim", ""))
    extras = []
    time = clean_text(card.get("time", ""))
    people = join_values(card.get("people", []))
    places = join_values(card.get("places", []))
    objects = join_values(card.get("objects", []))
    data = join_values(card.get("data", []))
    if time:
        extras.append("时间口径为%s" % time)
    if people:
        extras.append("相关人物包括%s" % people)
    if places:
        extras.append("相关地点包括%s" % places)
    if objects:
        extras.append("涉及对象包括%s" % objects)
    if data:
        extras.append("数据口径包括%s" % data)
    if extras:
        claim += " " + "；".join(extras) + "。"
    return claim


def source_phrase(card):
    title = clean_text(card.get("source_title", "未命名来源"))
    confidence = clean_text(card.get("confidence", ""))
    if confidence:
        return "%s（%s）" % (title, confidence)
    return title


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def unique_values(cards, field, limit=3):
    values = []
    seen = set()
    for card in cards:
        raw = card.get(field, [])
        if not isinstance(raw, list):
            raw = [raw]
        for item in raw:
            item = clean_text(item)
            if not item or item in seen:
                continue
            if item.startswith(("http://", "https://")):
                continue
            if len(item) > 36:
                item = item[:34] + "..."
            seen.add(item)
            values.append(item)
            if len(values) >= limit:
                return values
    return values


def time_values(cards, limit=2):
    values = []
    seen = set()
    for card in cards:
        item = clean_text(card.get("time", ""))
        if not item or item in seen:
            continue
        if len(item) > 28:
            item = item[:26] + "..."
        seen.add(item)
        values.append(item)
        if len(values) >= limit:
            return values
    return values


def group_heading(num, pidx, core, cards):
    base = CORE_SUBHEADING_HINTS.get(core, CORE_TITLE_HINTS.get(core, core))
    terms = []
    for field in ("objects", "people", "places", "data"):
        terms.extend(unique_values(cards, field, limit=3))
        if len(terms) >= 3:
            break
    if not terms:
        terms.extend(time_values(cards, limit=3))
    if terms:
        suffix = "、".join(terms[:3])
        heading = "%s.%d %s:%s" % (num, pidx, base, suffix)
    else:
        heading = "%s.%d %s" % (num, pidx, base)
    if len(heading) > 58:
        heading = heading[:56] + "..."
    return heading


def chapter_intro(topic, core, cards, type_code):
    title = CORE_TITLE_HINTS.get(core, core)
    sources = sorted({source_phrase(c) for c in cards})[:4]
    dims = sorted({clean_text(c.get("dimension", "")) for c in cards if clean_text(c.get("dimension", ""))})[:4]
    source_text = "、".join(sources) if sources else "已归档来源"
    dim_text = "、".join(dims) if dims else "基础资料维度"
    if type_code == "A":
        return "本章处理%s的%s问题。资料主要来自%s,覆盖%s等维度。阅读时应把公司自述、监管文件、媒体报道和分析估算区分开,避免把不同口径合并为一句结论。" % (topic, title, source_text, dim_text)
    if type_code == "B":
        return "本章处理%s的%s问题。资料主要来自%s,覆盖%s等维度。阅读时应把正史、年谱、文集、地方资料、数据库和当代传播资料分层看待,既保留事实,也保留来源差异。" % (topic, title, source_text, dim_text)
    return "本章处理%s的%s问题。资料主要来自%s,覆盖%s等维度。阅读时应先把主题本体讲清,再进入对象、机制、场景、数据和争议。" % (topic, title, source_text, dim_text)


def paragraph_from_cards(cards):
    sentences = [card_sentence(c) for c in cards]
    sources = sorted({source_phrase(c) for c in cards})
    paragraph = "".join(sentences)
    if sources:
        paragraph += "这些信息分别见于%s。" % "、".join(sources[:5])
    return paragraph


def source_index(cards):
    grouped = {}
    for c in cards:
        url = clean_text(c.get("source_url", ""))
        if not url:
            continue
        grouped.setdefault(url, {
            "title": clean_text(c.get("source_title", "")),
            "type": clean_text(c.get("source_type", "")),
            "confidence": clean_text(c.get("confidence", "")),
            "cores": set(),
        })
        grouped[url]["cores"].add(clean_text(c.get("core", "")))
    return grouped


def report(plan, cards, args):
    topic = args.title or plan.get("topic") or "资料调研"
    type_code = (args.type or plan.get("project_type", {}).get("code") or "").upper() or "D"
    now = datetime.date.today().isoformat()

    by_core = defaultdict(list)
    for c in cards:
        core = clean_text(c.get("core", "其他资料"))
        if "来源索引" in core:
            continue
        by_core[core].append(c)

    if type_code == "A":
        order = CORE_ORDER_A
    elif type_code == "B":
        order = CORE_ORDER_B
    else:
        order = []
    ordered_cores = [c for c in order if c in by_core]
    ordered_cores.extend([c for c in by_core.keys() if c not in ordered_cores])

    lines = []
    lines.append("# %s资料调研报告" % topic)
    lines.append("")
    lines.append("## 前言")
    lines.append("")
    lines.append(INTRO_BY_TYPE.get(type_code, INTRO_BY_TYPE["D"]))
    lines.append("本报告依据同一项目归档中的证据卡生成,与 XMind 导图共享资料来源。XMind 负责保留资料颗粒度,本报告负责把资料转成连续、可读、层级清楚的文本。报告生成日期为%s。" % now)
    lines.append("")
    lines.append("## 一、主题总述")
    lines.append("")
    all_sources = len({c.get("source_url", "") for c in cards if c.get("source_url")})
    all_cards = len(cards)
    cores_text = "、".join(CORE_TITLE_HINTS.get(c, c) for c in ordered_cores[:8])
    lines.append("%s的前期资料不宜只停留在一句定义或少量关键词上。现有资料共形成%d条证据卡,关联%d个来源,覆盖%s等核心方向。这些资料共同构成后续策展大纲的事实底座:一方面说明主题是什么、从哪里来、由哪些对象组成;另一方面说明资料中有哪些时间、地点、人物、数据、政策、争议和来源口径。" % (topic, all_cards, all_sources, cores_text))
    lines.append("")

    for idx, core in enumerate(ordered_cores, 2):
        title = CORE_TITLE_HINTS.get(core, core)
        num = CN_NUMS[idx - 1] if idx - 1 < len(CN_NUMS) else str(idx)
        core_cards = by_core[core]
        lines.append("## %s、%s" % (num, title))
        lines.append("")
        lines.append(chapter_intro(topic, core, core_cards, type_code))
        lines.append("")
        groups = list(chunked(core_cards, max(2, args.cards_per_paragraph)))
        for pidx, group in enumerate(groups, 1):
            lines.append("### %s" % group_heading(num, pidx, core, group))
            lines.append("")
            lines.append(paragraph_from_cards(group))
            lines.append("")
        lines.append("### %s.%d 本章来源口径" % (num, len(groups) + 1))
        lines.append("")
        source_names = sorted({source_phrase(c) for c in core_cards})
        lines.append("本章资料来源包括%s。不同来源的功能并不相同:官方或监管文件用于确认事实边界,媒体报道用于补足事件过程和时效动态,机构或数据库资料用于补充索引、馆藏、案件、估算或横向对照。" % "、".join(source_names[:8]))
        lines.append("")

    lines.append("## 来源索引与待核实问题")
    lines.append("")
    lines.append("资料报告的可靠性取决于来源层级。以下来源索引不是装饰性附录,而是后续撰写大纲、正文或解说词时追溯事实的入口。")
    lines.append("")
    for i, (url, info) in enumerate(source_index(cards).items(), 1):
        lines.append("### 来源%d:%s" % (i, info["title"] or url))
        lines.append("")
        lines.append("该来源的资料性质为%s,当前采信状态为%s,在本报告中主要支撑%s。引用时应同时查看原始页面标题、发布时间、发布机构和上下文语境,不要只截取单句结论;若后续正文需要使用其中的数据、年代或人物关系,应回到该来源核对原文表述和相邻证据。" % (
            info["type"] or "未标注",
            info["confidence"] or "未标注",
            "、".join(sorted(info["cores"])) or "综合资料",
        ))
        lines.append("")
        lines.append(url)
        lines.append("")
    lines.append("## 结语")
    lines.append("")
    lines.append("这份报告的目标不是替代后续大纲,而是为大纲提供可阅读、可追溯、可继续扩展的资料底座。后续进入文本组织阶段时,可以在不重新寻找基础事实的前提下,从本报告中抽取人物、事件、对象、时间线、数据、争议和来源,再进一步转化为单元结构和具体文本。")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="从证据卡生成资料报告 Markdown")
    ap.add_argument("--plan", required=True, help="research_plan.json")
    ap.add_argument("--evidence", required=True, help="evidence_cards.jsonl")
    ap.add_argument("--out", required=True, help="输出 report.md")
    ap.add_argument("--title", default="")
    ap.add_argument("--type", default="")
    ap.add_argument("--cards-per-paragraph", type=int, default=3)
    args = ap.parse_args()

    plan = read_json(args.plan)
    cards = list(read_jsonl(args.evidence))
    text = report(plan, cards, args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print("已生成资料报告 Markdown: %s" % args.out)
    print("证据卡: %d" % len(cards))
    print("字符数: %d" % len(text))


if __name__ == "__main__":
    sys.exit(main())
