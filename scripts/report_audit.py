#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_audit.py - 审计资料报告 Markdown 是否像报告,而不是短句清单。
"""
import argparse
import json
import os
import re
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from outline_audit import CURATION_PATTERNS, METHOD_LABEL_PATTERNS  # noqa: E402


REPORT_PLACEHOLDER_PATTERNS = [
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
    r"需要用[^。；\n]{0,40}核验",
    r"用[^。；\n]{0,40}核验[,，。；]",
]

GENERIC_HEADING_PATTERNS = [
    r"资料综述$",
    r"材料综述$",
    r"内容综述$",
    r"基本情况$",
]


def line_hits(text, patterns):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            if re.search(pat, line):
                hits.append({"line": lineno, "pattern": pat, "text": line.strip()})
    return hits


def paragraphs(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b or b.startswith("#"):
            continue
        if re.match(r"^https?://", b):
            continue
        out.append(b)
    return out


def generic_heading_hits(heads):
    hits = []
    for heading in heads:
        for pat in GENERIC_HEADING_PATTERNS:
            if re.search(pat, heading):
                hits.append({"pattern": pat, "text": heading.strip()})
    return hits


def audit(path, args):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    heads = re.findall(r"^#{1,4}\s+(.+)$", text, flags=re.M)
    ps = paragraphs(text)
    short = [p for p in ps if len(re.sub(r"\s+", "", p)) < args.min_paragraph_chars]
    report = {
        "path": os.path.abspath(path),
        "chars": len(text),
        "headings": len(heads),
        "paragraphs": len(ps),
        "short_paragraph_samples": short[:20],
        "placeholder_hits": line_hits(text, REPORT_PLACEHOLDER_PATTERNS),
        "method_label_hits": line_hits(text, METHOD_LABEL_PATTERNS),
        "curation_hits": line_hits(text, CURATION_PATTERNS),
        "generic_heading_hits": generic_heading_hits(heads),
        "errors": [],
        "warnings": [],
    }
    if len(text) < args.min_chars:
        report["errors"].append("报告字数不足: %d < %d" % (len(text), args.min_chars))
    if len(heads) < args.min_headings:
        report["errors"].append("标题层级不足: %d < %d" % (len(heads), args.min_headings))
    if len(ps) < args.min_paragraphs:
        report["errors"].append("段落数量不足: %d < %d" % (len(ps), args.min_paragraphs))
    if len(short) > args.max_short_paragraphs:
        report["errors"].append("短段落过多: %d > %d;报告不能退化为短句清单" % (
            len(short), args.max_short_paragraphs))
    if report["placeholder_hits"]:
        report["errors"].append("发现占位句/任务句: %d 条" % len(report["placeholder_hits"]))
    if report["method_label_hits"]:
        report["errors"].append("发现方法标签伪内容: %d 条" % len(report["method_label_hits"]))
    if report["curation_hits"]:
        report["errors"].append("发现策展污染词: %d 条" % len(report["curation_hits"]))
    if report["generic_heading_hits"]:
        report["errors"].append("发现泛化小标题: %d 条;小标题应来自具体对象、人物、时间或问题" % (
            len(report["generic_heading_hits"])))
    return report


def print_report(report):
    print("报告审计%s: %s" % ("通过" if not report["errors"] else "失败", report["path"]))
    print("字符数: %d" % report["chars"])
    print("标题数: %d" % report["headings"])
    print("段落数: %d" % report["paragraphs"])
    print("短段落样例: %d" % len(report["short_paragraph_samples"]))
    print("占位句: %d" % len(report["placeholder_hits"]))
    print("方法标签: %d" % len(report["method_label_hits"]))
    print("策展污染: %d" % len(report["curation_hits"]))
    print("泛化小标题: %d" % len(report.get("generic_heading_hits", [])))
    for err in report["errors"]:
        print("ERROR: " + err)
    for key in ("placeholder_hits", "method_label_hits", "curation_hits", "generic_heading_hits", "short_paragraph_samples"):
        for item in report.get(key, [])[:5]:
            print("样例[%s]: %s" % (key, json.dumps(item, ensure_ascii=False)))


def main():
    ap = argparse.ArgumentParser(description="审计资料报告 Markdown")
    ap.add_argument("report")
    ap.add_argument("--min-chars", type=int, default=6000)
    ap.add_argument("--min-headings", type=int, default=8)
    ap.add_argument("--min-paragraphs", type=int, default=20)
    ap.add_argument("--min-paragraph-chars", type=int, default=45)
    ap.add_argument("--max-short-paragraphs", type=int, default=8)
    ap.add_argument("--json", help="输出 report_audit.json")
    args = ap.parse_args()

    report = audit(args.report, args)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print_report(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
