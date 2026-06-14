#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
outline_audit.py - 在 Markdown 大纲转 XMind 前做硬审计。

它检查的是生产事故:
- 把工作备注写进 `>` notes。
- 用 `节点 > 一句话` 压缩内容。
- 把“需要补”“正式使用时要”这类占位句当资料。
- 把展项、展示形式、策展创意混进资料导图。
- 把“继续下钻方向”“关联资料面”这类方法标签当资料内容。
- 重要历史/文化主题缺少生平年谱等核心资料分支。
"""
import argparse
import json
import os
import re
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from md_to_xmind import parse_outline  # noqa: E402


PLACEHOLDER_PATTERNS = [
    r"正式使用时要",
    r"需要继续",
    r"需要补",
    r"需要绑定",
    r"需要保留",
    r"不能只作为短词存在",
    r"可提供或需要补充",
    r"待补[:：]",
    r"待补充正式出处",
    r"已列入正式调研来源或待补来源清单",
    r"正式资料中补齐",
    r"用.*核验",
]


METHOD_LABEL_PATTERNS = [
    r"继续下钻方向",
    r"下钻方式",
    r"关联资料面",
    r"资料密度检查",
    r"概念资料卡",
    r"认知阶梯骨架",
    r"这一层不是结论",
    r"作为资料节点",
    r"来源类型为",
    r"可信度标注为",
    r"对应证据卡",
]

FIELD_PROSE_PATTERNS = [
    r"时间口径为",
    r"相关人物包括",
    r"相关地点包括",
    r"涉及对象包括",
    r"数据口径包括",
    r"这些信息分别见于",
    r"本章处理.+问题",
]


CURATION_PATTERNS = [
    r"展项",
    r"展示形式",
    r"空间表达",
    r"展线",
    r"互动装置",
    r"策展独特价值",
    r"核心张力",
    r"策展主题",
    r"主题口号",
    r"可借鉴",
    r"展陈启示",
    r"观众体验",
    r"打卡展项",
    r"适合展示",
    r"建议做成",
    r"可做",
]


STRUCTURE_SHORT_TITLES = {
    "定义", "来源", "链接", "时间", "地点", "人物", "机构", "数据",
    "经过", "结果", "争议", "作用", "用途", "分类", "特征", "背景",
    "版本", "出处", "现状", "边界", "误区", "对象", "材料", "工具",
    "资料性质", "采信边界", "来源用途", "时间地点", "人物对象",
    "主题名称", "资料主体", "别名与检索名称", "项目类型", "地域范围",
    "资料规模", "权威来源路线", "最新资料要求", "支撑内容",
}


TYPE_REQUIRED_TERMS = {
    "A": ["上市", "融资", "估值", "收入", "最新动态"],
    "B": ["生平", "年谱", "作品", "文献", "馆藏"],
    "C": ["定义", "历史", "分类", "工具", "行为", "社群"],
}


def line_hits(text, patterns):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            if re.search(pat, line):
                hits.append({"line": lineno, "pattern": pat, "text": line.strip()})
    return hits


def inline_compression_hits(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if re.search(r"\s>\s", stripped):
            hits.append({"line": lineno, "text": stripped})
    return hits


def note_hits(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith(">"):
            hits.append({"line": lineno, "text": line.strip()})
    return hits


def flatten_nodes(forest):
    rows = []

    def walk(node, depth, parent):
        rows.append({
            "title": node.get("title", ""),
            "depth": depth,
            "children": node.get("children", []),
            "parent": parent,
            "notes": node.get("notes", []),
        })
        for child in node.get("children", []):
            walk(child, depth + 1, node.get("title", ""))

    for n in forest:
        walk(n, 2, "")
    return rows


def text_len_for_short_rule(title):
    compact = re.sub(r"\s+", "", title)
    compact = re.sub(r"^[\-*+#\d\.\)]+", "", compact)
    return len(compact)


def short_leaf_hits(rows):
    hits = []
    for row in rows:
        title = row["title"].strip()
        if row["children"]:
            continue
        if not title or title in STRUCTURE_SHORT_TITLES:
            continue
        if row["parent"] in STRUCTURE_SHORT_TITLES:
            continue
        if title.startswith(("http://", "https://")):
            continue
        if re.search(r"\d{4}[-年]", title) and len(title) >= 8:
            continue
        if text_len_for_short_rule(title) <= 4:
            hits.append({
                "title": title,
                "parent": row["parent"],
                "depth": row["depth"],
            })
    return hits


def load_plan(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def outline_contains_all_terms(all_titles_text, terms):
    haystack = all_titles_text.casefold()
    missing = []
    for term in terms:
        if str(term).casefold() not in haystack:
            missing.append(term)
    return missing


def required_item_tokens(item):
    raw_parts = re.split(r"[/、与和及\|\s]+", str(item))
    tokens = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if re.search(r"ipo", part, re.I) and len(part) > 3:
            prefix = re.sub(r"ipo", "", part, flags=re.I).strip()
            if len(prefix) >= 2:
                tokens.append(prefix)
            tokens.append("IPO")
            continue
        if len(part) >= 2:
            tokens.append(part)
    return list(dict.fromkeys(tokens)) or [str(item)]


def outline_missing_core_items(all_titles_text, core_items):
    haystack = all_titles_text.casefold()
    missing = []
    for item in core_items:
        tokens = required_item_tokens(item)
        missing_tokens = [token for token in tokens if token.casefold() not in haystack]
        if missing_tokens:
            missing.append("%s(缺:%s)" % (item, ",".join(missing_tokens)))
    return missing


def audit(path, args):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    root_title, forest = parse_outline(text)
    rows = flatten_nodes(forest)
    all_titles_text = "\n".join(row["title"] for row in rows)
    max_depth = max([row["depth"] for row in rows] or [1])
    report = {
        "path": os.path.abspath(path),
        "root_title": root_title,
        "node_count_without_root": len(rows),
        "max_depth_including_root": max_depth,
        "first_branch": forest[0]["title"] if forest else "",
        "notes": note_hits(text),
        "inline_compression": inline_compression_hits(text),
        "placeholder_hits": line_hits(text, PLACEHOLDER_PATTERNS),
        "method_label_hits": line_hits(text, METHOD_LABEL_PATTERNS),
        "field_prose_hits": line_hits(text, FIELD_PROSE_PATTERNS),
        "curation_hits": line_hits(text, CURATION_PATTERNS),
        "short_leaf_samples": short_leaf_hits(rows)[:20],
        "missing_required_terms": [],
        "errors": [],
        "warnings": [],
    }

    if args.require_first and report["first_branch"] != args.require_first:
        report["errors"].append("第一分支必须是「%s」,当前是「%s」" % (
            args.require_first, report["first_branch"] or "空"))
    if len(rows) < args.min_nodes:
        report["errors"].append("节点数不足: %d < %d" % (len(rows), args.min_nodes))
    if max_depth < args.min_depth:
        report["errors"].append("层级不足: %d < %d" % (max_depth, args.min_depth))
    if report["notes"]:
        report["errors"].append("发现备注行: %d 条;资料必须写成可见子节点" % len(report["notes"]))
    if report["inline_compression"]:
        report["errors"].append("发现同一行压缩写法: %d 条;不能使用「节点 > 一句话」" % len(report["inline_compression"]))
    if report["placeholder_hits"]:
        report["errors"].append("发现占位句/任务句: %d 条;不能把检查要求写进导图" % len(report["placeholder_hits"]))
    if report["method_label_hits"]:
        report["errors"].append("发现方法标签伪内容: %d 条;导图节点必须写具体事实,不能写模板提示或下钻方式" % len(report["method_label_hits"]))
    if report["field_prose_hits"]:
        report["errors"].append("发现字段腔节点: %d 条;导图节点应写自然中文,不能直接拼接证据卡字段" % len(report["field_prose_hits"]))
    if report["curation_hits"]:
        report["errors"].append("发现策展污染词: %d 条;调研阶段只保留资料事实" % len(report["curation_hits"]))
    if report["short_leaf_samples"] and not args.warn_short_leaves:
        report["errors"].append("发现疑似资料短词叶子: %d 条样例;资料名词必须继续解释" % len(report["short_leaf_samples"]))
    elif report["short_leaf_samples"]:
        report["warnings"].append("疑似资料短词叶子样例: %d 条" % len(report["short_leaf_samples"]))

    type_code = (args.type or "").strip().upper()
    required_terms = list(TYPE_REQUIRED_TERMS.get(type_code, []))
    required_core_items = []
    plan = load_plan(args.plan)
    if plan:
        required_core_items.extend(plan.get("theme_profile", {}).get("required_cores", []))
    if (required_terms or required_core_items) and not args.skip_required_terms:
        missing = outline_contains_all_terms(all_titles_text, required_terms)
        if required_core_items:
            missing.extend(outline_missing_core_items(all_titles_text, required_core_items))
        report["missing_required_terms"] = missing
        if missing:
            report["errors"].append("缺少类型/计划要求的核心资料词: %s" % "、".join(missing[:12]))

    return report


def print_report(report):
    status = "通过" if not report["errors"] else "失败"
    print("大纲审计%s: %s" % (status, report["path"]))
    print("节点数(不含中心): %d" % report["node_count_without_root"])
    print("最大层级(含中心): %d" % report["max_depth_including_root"])
    print("第一分支: %s" % (report["first_branch"] or "空"))
    print("备注行: %d" % len(report["notes"]))
    print("压缩写法: %d" % len(report["inline_compression"]))
    print("占位句: %d" % len(report["placeholder_hits"]))
    print("方法标签: %d" % len(report["method_label_hits"]))
    print("字段腔: %d" % len(report["field_prose_hits"]))
    print("策展污染: %d" % len(report["curation_hits"]))
    if report["missing_required_terms"]:
        print("缺少核心词: %s" % "、".join(report["missing_required_terms"][:20]))
    for item in report["errors"]:
        print("ERROR: " + item)
    for item in report["warnings"]:
        print("WARN: " + item)
    for key in ("placeholder_hits", "method_label_hits", "field_prose_hits", "notes", "inline_compression", "curation_hits", "short_leaf_samples"):
        samples = report[key][:5]
        if samples:
            print("样例[%s]:" % key)
            for s in samples:
                print("  " + json.dumps(s, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="审计调研 Markdown 大纲是否可进入 XMind 生成")
    ap.add_argument("outline", help="调研大纲.md")
    ap.add_argument("--type", default="", help="A/B/C/D,用于检查类型硬要求")
    ap.add_argument("--plan", help="research_plan.json,用于检查计划核心词")
    ap.add_argument("--min-depth", type=int, default=7)
    ap.add_argument("--min-nodes", type=int, default=400)
    ap.add_argument("--require-first", default="主题解读")
    ap.add_argument("--skip-required-terms", action="store_true")
    ap.add_argument("--warn-short-leaves", action="store_true")
    ap.add_argument("--json", help="输出审计 JSON 路径")
    args = ap.parse_args()

    report = audit(args.outline, args)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print_report(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
