#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xmind_audit.py - 读取 .xmind zip 内的 content.json 做最终验证。
"""
import argparse
import json
import os
import re
import sys
import zipfile


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from outline_audit import (  # noqa: E402
    CURATION_PATTERNS,
    METHOD_LABEL_PATTERNS,
    PLACEHOLDER_PATTERNS,
    STRUCTURE_SHORT_TITLES,
    text_len_for_short_rule,
)


def load_content(path):
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())
        required = {"content.json", "manifest.json", "metadata.json"}
        missing = sorted(required - names)
        content = json.loads(z.read("content.json").decode("utf-8"))
    return content, missing


def walk(topic, depth=1, parent=""):
    rows = [{
        "title": topic.get("title", ""),
        "depth": depth,
        "parent": parent,
        "notes": topic.get("notes", {}),
        "children": topic.get("children", {}).get("attached", []),
    }]
    for child in topic.get("children", {}).get("attached", []):
        rows.extend(walk(child, depth + 1, topic.get("title", "")))
    return rows


def pattern_hits(rows, patterns):
    hits = []
    for row in rows:
        text = row["title"]
        note = row.get("notes", {})
        if note:
            text += "\n" + json.dumps(note, ensure_ascii=False)
        for pat in patterns:
            if re.search(pat, text):
                hits.append({"title": row["title"], "pattern": pat, "depth": row["depth"]})
    return hits


def short_leaf_hits(rows):
    hits = []
    for row in rows:
        title = row["title"].strip()
        if row["children"]:
            continue
        if not title or title in STRUCTURE_SHORT_TITLES or row["parent"] in STRUCTURE_SHORT_TITLES:
            continue
        if title.startswith(("http://", "https://")):
            continue
        if re.search(r"\d{4}[-年]", title) and len(title) >= 8:
            continue
        if text_len_for_short_rule(title) <= 4:
            hits.append({"title": title, "parent": row["parent"], "depth": row["depth"]})
    return hits


def audit(path, args):
    content, missing_zip_entries = load_content(path)
    root = content[0]["rootTopic"]
    rows = walk(root)
    root_children = root.get("children", {}).get("attached", [])
    notes_count = sum(1 for r in rows if r.get("notes"))
    placeholder = pattern_hits(rows, PLACEHOLDER_PATTERNS)
    method_labels = pattern_hits(rows, METHOD_LABEL_PATTERNS)
    curation = pattern_hits(rows, CURATION_PATTERNS)
    short_samples = short_leaf_hits(rows)[:20]
    max_depth = max(r["depth"] for r in rows)
    report = {
        "path": os.path.abspath(path),
        "zip_missing_entries": missing_zip_entries,
        "root_title": root.get("title", ""),
        "first_branch": root_children[0].get("title", "") if root_children else "",
        "topic_count": len(rows),
        "max_depth": max_depth,
        "topics_with_notes": notes_count,
        "placeholder_hits": placeholder,
        "method_label_hits": method_labels,
        "curation_hits": curation,
        "short_leaf_samples": short_samples,
        "errors": [],
        "warnings": [],
    }
    if missing_zip_entries:
        report["errors"].append("XMind zip 缺少文件: %s" % ",".join(missing_zip_entries))
    if args.require_first and report["first_branch"] != args.require_first:
        report["errors"].append("第一分支必须是「%s」,当前是「%s」" % (
            args.require_first, report["first_branch"] or "空"))
    if report["topic_count"] < args.min_nodes:
        report["errors"].append("节点数不足: %d < %d" % (report["topic_count"], args.min_nodes))
    if report["max_depth"] < args.min_depth:
        report["errors"].append("层级不足: %d < %d" % (report["max_depth"], args.min_depth))
    if notes_count != args.notes_allowed:
        report["errors"].append("备注节点数不合格: %d != %d" % (notes_count, args.notes_allowed))
    if placeholder:
        report["errors"].append("发现占位句: %d 条" % len(placeholder))
    if method_labels:
        report["errors"].append("发现方法标签伪内容: %d 条" % len(method_labels))
    if curation:
        report["errors"].append("发现策展污染词: %d 条" % len(curation))
    if short_samples and not args.warn_short_leaves:
        report["errors"].append("发现疑似资料短词叶子: %d 条样例" % len(short_samples))
    elif short_samples:
        report["warnings"].append("疑似资料短词叶子样例: %d 条" % len(short_samples))
    return report


def print_report(report):
    print("XMind 审计%s: %s" % ("通过" if not report["errors"] else "失败", report["path"]))
    print("中心主题: %s" % report["root_title"])
    print("第一分支: %s" % report["first_branch"])
    print("节点数: %d" % report["topic_count"])
    print("最大层级: %d" % report["max_depth"])
    print("备注节点: %d" % report["topics_with_notes"])
    print("占位句: %d" % len(report["placeholder_hits"]))
    print("方法标签: %d" % len(report["method_label_hits"]))
    print("策展污染: %d" % len(report["curation_hits"]))
    for err in report["errors"]:
        print("ERROR: " + err)
    for warn in report["warnings"]:
        print("WARN: " + warn)
    for key in ("placeholder_hits", "method_label_hits", "curation_hits", "short_leaf_samples"):
        for item in report[key][:5]:
            print("样例[%s]: %s" % (key, json.dumps(item, ensure_ascii=False)))


def main():
    ap = argparse.ArgumentParser(description="审计 .xmind 产物")
    ap.add_argument("xmind")
    ap.add_argument("--min-depth", type=int, default=7)
    ap.add_argument("--min-nodes", type=int, default=400)
    ap.add_argument("--require-first", default="主题解读")
    ap.add_argument("--notes-allowed", type=int, default=0)
    ap.add_argument("--warn-short-leaves", action="store_true")
    ap.add_argument("--json", help="输出 xmind_audit.json")
    args = ap.parse_args()

    report = audit(args.xmind, args)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print_report(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
