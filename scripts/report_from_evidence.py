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
    "主体身份与名称体系": "法人登记与主体边界",
    "创始人/领导层/组织结构": "管理层、股权与治理关系",
    "产品业务谱系": "产品谱系与业务边界",
    "技术能力与生产系统": "技术能力与运行数据",
    "市场客户与产业链": "客户场景与产业链关系",
    "财经资本/上市IPO/融资/估值/收入": "资本事件、估值与收入",
    "监管诉讼/合规/风险": "监管事项与风险记录",
    "最新动态/近一年/近90天": "近期事件与状态变化",
    "同类企业事实对照": "同类对象事实对照",
    "主题边界与名称体系": "姓名、身份与主题界定",
    "生平年谱": "生平节点与人生阶段",
    "家族师友与关系网络": "家族、师友与人物关系",
    "时代制度背景": "时代制度与政治环境",
    "地理行旅与空间遗存": "行旅地点与空间遗存",
    "作品文献/版本/注本": "作品、版本与文本来源",
    "实物馆藏/碑刻/图像档案": "实物、馆藏与图像档案",
    "思想风格与术语体系": "思想术语与风格特征",
    "后世接受/传播/研究史": "后世评价与传播研究",
    "当代保护/出版/数字化/纪念活动": "保护、出版与数字化",
}

CORE_GROUP_HEADINGS = {
    "主体身份与名称体系": ["法人登记与总部信息", "企业使命与公开识别"],
    "创始人/领导层/组织结构": ["管理层与 IPO 文件信息", "股权结构与承销网络"],
    "产品业务谱系": ["主要产品线与业务入口", "航天器、卫星网络与政府业务"],
    "技术能力与生产系统": ["可重复使用能力与发射数据", "运力参数与许可审查"],
    "市场客户与产业链": ["政府客户与载人航天合同", "商业客户、卫星服务与移动连接"],
    "财经资本/上市IPO/融资/估值/收入": ["IPO 状态与证券识别", "收入、估值与发行规模", "股本结构与锁定安排"],
    "监管诉讼/合规/风险": ["发射许可与事故调查", "政府合同与安全义务", "环境诉讼与监管争议", "劳工安全与合规风险"],
    "最新动态/近一年/近90天": ["近期任务与公开事件", "交易动态与发射记录"],
    "同类企业事实对照": ["美国商业航天企业对照", "欧洲与中小型发射企业对照"],
    "主题边界与名称体系": ["姓名、身份与主题界定", "三苏关系与后世称谓"],
    "生平年谱": ["早年教育与科举入仕", "外任经历与地方治理", "乌台诗案与黄州转折", "晚年贬谪与北归"],
    "家族师友与关系网络": ["三苏家族与早年教育", "婚姻家庭与晚年陪伴", "师友赏识与现代研究者"],
    "时代制度背景": ["北宋政局与变法背景", "监察制度与乌台诗案", "党争、制科与士人处境"],
    "地理行旅与空间遗存": ["眉山故里与早年空间", "杭州、密州与作品发生地", "黄州、惠州与贬谪空间", "海南遗存与纪念空间", "当代纪念地与地方传播"],
    "作品文献/版本/注本": ["文集整理与年谱系统", "赤壁作品与经典篇章", "书法名迹与版本流传", "教材选篇与公共阅读"],
    "实物馆藏/碑刻/图像档案": ["主题书画与馆藏展品", "文物等级与馆藏规模", "碑刻、御碑与图像线索"],
    "思想风格与术语体系": ["文章风格与书法谱系", "民本意识与处世态度", "人格风范与生活趣味"],
    "后世接受/传播/研究史": ["专题展览与行旅叙事", "大众传播与公共文化", "纪念活动与学术研究"],
    "当代保护/出版/数字化/纪念活动": ["机构建设与保护工程", "展厅库房与数据库建设", "邮票、出版与寿苏会"],
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
        extras.append("时间可落在%s" % time)
    if people:
        extras.append("人物线索集中在%s" % people)
    if places:
        extras.append("地点线索指向%s" % places)
    if objects:
        extras.append("对象线索包括%s" % objects)
    if data:
        extras.append("可引用的数据包括%s" % data)
    if extras:
        claim += " " + "；".join(extras) + "。"
    return claim


def compact_values(values, limit=3):
    if isinstance(values, list):
        vals = [clean_text(v) for v in values if clean_text(v)]
    elif values:
        vals = [clean_text(values)]
    else:
        vals = []
    out = []
    seen = set()
    for val in vals:
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
        if len(out) >= limit:
            break
    return out


def readable_source_title(title):
    title = clean_text(title)
    if " - 维基百科，自由的百科全书" in title:
        base = title.replace(" - 维基百科，自由的百科全书", "").strip()
        return "维基百科“%s”词条" % base
    if " - 维基文库，自由的图书馆" in title:
        base = title.replace(" - 维基文库，自由的图书馆", "").strip()
        base = base.replace("/", "·")
        return "维基文库《%s》" % base
    if title.endswith(" - 新华网客户端"):
        base = title.replace(" - 新华网客户端", "").strip()
        base = base.replace("《", "〈").replace("》", "〉")
        return "新华网客户端《%s》" % base
    title = title.replace("_四川在线", "")
    return title or "未命名来源"


def source_phrase(card):
    title = readable_source_title(card.get("source_title", "未命名来源"))
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
    templates = CORE_GROUP_HEADINGS.get(core, [])
    if pidx <= len(templates):
        return "%s.%d %s" % (num, pidx, templates[pidx - 1])
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
        return "本章梳理%s的%s。资料主要来自%s,覆盖%s等维度。公司自述、监管文件、媒体报道和分析估算承担的作用不同,阅读时需要分开看。" % (topic, title, source_text, dim_text)
    if type_code == "B":
        return "本章梳理%s的%s。资料主要来自%s,覆盖%s等维度。正史、年谱、文集、地方资料、数据库和当代传播材料各有侧重,这里尽量保留事实本身,也保留来源之间的差异。" % (topic, title, source_text, dim_text)
    return "本章梳理%s的%s。资料主要来自%s,覆盖%s等维度。阅读顺序是先界定主题本体,再进入对象、机制、场景、数据和争议。" % (topic, title, source_text, dim_text)


def value_in_claim(value, claim):
    value = clean_text(value)
    if not value:
        return True
    return value in claim


def normalize_year_range(text):
    m = re.search(r"(\d{3,4})\s*[-—]\s*(\d{3,4})", clean_text(text))
    if not m:
        return ""
    return "%s—%s" % (m.group(1), m.group(2))


def inject_life_dates(card, claim):
    people = compact_values(card.get("people", []), 1)
    if not people:
        return claim
    person = people[0]
    data_text = " ".join(compact_values(card.get("data", []), 4))
    if "生卒" not in data_text:
        return claim
    years = normalize_year_range(data_text)
    if not years or years in claim:
        return claim
    return claim.replace("%s是" % person, "%s（%s），" % (person, years), 1)


def detail_sentence(card, claim):
    sentences = []
    data = [v for v in compact_values(card.get("data", []), 2) if not value_in_claim(v, claim)]
    useful_data = []
    for item in data:
        if item.startswith(("名称字段", "身份维度")):
            continue
        if re.search(r"(资料|来源|证据|工具对象|分类依据|术语|场景|流程环节|组织或群体|补充证据|电商商品词)\d*[项组类]?$", item):
            continue
        if re.match(r"来源编号S\d+", item):
            continue
        if "生卒" in item and normalize_year_range(item) and normalize_year_range(item) in claim:
            continue
        if "source" in item.lower() or "url" in item.lower():
            continue
        useful_data.append(item)
    if useful_data:
        sentences.append("其中较适合直接进入正文的数据或口径包括%s。" % "、".join(useful_data[:2]))
    return "".join(sentences)


def polished_claim(card):
    claim = ensure_sentence(card.get("claim", ""))
    claim = re.sub(r"字([^，。]+)，又字([^，。]+)", r"字\1、\2", claim)
    claim = inject_life_dates(card, claim)
    claim = claim.replace("不能只归为", "并非单纯是")
    claim = claim.replace("共同构成资料主体", "均应纳入资料梳理范围")
    claim = claim.replace("他同时是", "更是")
    claim = claim.replace("均应纳入资料梳理范围", "均为资料梳理的核心内容")
    claim = claim.replace("这组数字直接体现", "这组数字说明")
    claim = claim.replace("这是", "这也是")
    return claim


def paragraph_from_cards(cards):
    paragraphs = []
    for card in cards:
        claim = polished_claim(card)
        detail = detail_sentence(card, claim)
        if detail:
            paragraphs.append(claim + "\n" + detail)
        else:
            paragraphs.append(claim)
    sources = sorted({readable_source_title(c.get("source_title", "")) for c in cards if c.get("source_title")})
    paragraph = "\n".join(paragraphs)
    if sources:
        paragraph += "\n以上信息综合参考:%s。" % "、".join(sources[:5])
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
    lines.append("%s的资料整理不能停在一句定义或几组关键词上。本次归档形成%d条证据卡,关联%d个来源,覆盖%s等方向。报告正文按资料问题展开:先说明主题是什么、从哪里来、由哪些对象组成,再整理时间、地点、人物、数据、政策、争议和来源口径。" % (topic, all_cards, all_sources, cores_text))
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
