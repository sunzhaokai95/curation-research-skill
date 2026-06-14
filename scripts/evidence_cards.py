#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evidence_cards.py - 生成/校验证据卡。

证据卡是导图写作前的中间层。模型可以阅读 sources.jsonl 后写 evidence_cards.jsonl,
本脚本负责校验字段是否足以支撑覆盖审计。
"""
import argparse
import json
import os
import re
import sys


REQUIRED_FIELDS = [
    "claim",
    "core",
    "dimension",
    "source_title",
    "source_url",
    "source_type",
    "confidence",
]


DETAIL_FIELDS = ["time", "people", "places", "objects", "data"]
EMPTY_DETAIL_VALUES = {"", "不详", "未知", "无", "不适用", "待补", "待补充", "n/a", "na", "none"}


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
    r"正式资料中补齐",
]


VALID_CONFIDENCE = {
    "官方确认",
    "监管文件",
    "学术资料",
    "机构资料",
    "媒体报道",
    "行业资料",
    "分析师估算",
    "单一来源",
    "待核实",
}


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_seed(sources_path, out_path, topic):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    count = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for src in read_jsonl(sources_path):
            if src.get("status") != "ok":
                continue
            count += 1
            seed = {
                "status": "needs_extraction",
                "topic": topic,
                "claim": "",
                "core": "",
                "dimension": src.get("dimension", ""),
                "time": "",
                "people": [],
                "places": [],
                "objects": [],
                "data": [],
                "source_title": src.get("title") or src.get("search_title", ""),
                "source_url": src.get("url", ""),
                "source_type": src.get("source_type", "web"),
                "confidence": "",
                "source_excerpt": (src.get("text") or src.get("description") or "")[:600],
            }
            out.write(json.dumps(seed, ensure_ascii=False) + "\n")
    print("已生成证据卡抽取种子: %s (%d 条)" % (out_path, count))


def has_detail_value(value):
    if isinstance(value, list):
        return any(has_detail_value(item) for item in value)
    text = str(value or "").strip()
    return text.lower() not in EMPTY_DETAIL_VALUES


def detail_field_count(card):
    return sum(1 for field in DETAIL_FIELDS if has_detail_value(card.get(field)))


def placeholder_hits(card):
    text = "\n".join(str(card.get(field, "")) for field in (
        "claim", "core", "dimension", "time", "source_title", "confidence"
    ))
    hits = []
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


def validate_cards(path, min_detail_fields=2, min_claim_len=30):
    invalid = []
    valid = 0
    total = 0
    for lineno, card in enumerate(read_jsonl(path), 1):
        total += 1
        if card.get("status") == "needs_extraction":
            invalid.append({"line": lineno, "error": "仍是抽取种子,不是证据卡"})
            continue
        missing = [field for field in REQUIRED_FIELDS if not str(card.get(field, "")).strip()]
        if missing:
            invalid.append({"line": lineno, "error": "缺少字段: " + ",".join(missing)})
            continue
        claim = str(card.get("claim", "")).strip()
        if len(claim) < min_claim_len:
            invalid.append({"line": lineno, "error": "claim 过短,不像可核验证据"})
            continue
        placeholders = placeholder_hits(card)
        if placeholders:
            invalid.append({"line": lineno, "error": "含占位句/任务句: " + ",".join(placeholders)})
            continue
        details = detail_field_count(card)
        if details < min_detail_fields:
            invalid.append({
                "line": lineno,
                "error": "细节字段不足: %d < %d;time/people/places/objects/data 至少填足"
                % (details, min_detail_fields),
            })
            continue
        confidence = str(card.get("confidence", "")).strip()
        if confidence not in VALID_CONFIDENCE:
            invalid.append({"line": lineno, "error": "confidence 必须是来源状态枚举"})
            continue
        valid += 1
    return {
        "path": os.path.abspath(path),
        "total": total,
        "valid": valid,
        "invalid_count": len(invalid),
        "invalid_samples": invalid[:30],
    }


def print_validation(report):
    print("证据卡校验: %s" % ("通过" if report["invalid_count"] == 0 else "失败"))
    print("总数: %d" % report["total"])
    print("有效: %d" % report["valid"])
    print("无效: %d" % report["invalid_count"])
    for item in report["invalid_samples"][:10]:
        print("ERROR: line %s %s" % (item["line"], item["error"]))


def main():
    ap = argparse.ArgumentParser(description="证据卡生成与校验")
    sub = ap.add_subparsers(dest="cmd", required=True)

    seed = sub.add_parser("seed", help="从 sources.jsonl 生成待抽取种子")
    seed.add_argument("--sources", required=True)
    seed.add_argument("--out", required=True)
    seed.add_argument("--topic", default="")

    val = sub.add_parser("validate", help="校验 evidence_cards.jsonl")
    val.add_argument("evidence")
    val.add_argument("--json", help="输出校验 JSON")
    val.add_argument("--min-detail-fields", type=int, default=2,
                     help="每条证据卡至少包含多少个 time/people/places/objects/data 细节字段")
    val.add_argument("--min-claim-len", type=int, default=30,
                     help="claim 最小字符数")
    args = ap.parse_args()

    if args.cmd == "seed":
        write_seed(args.sources, args.out, args.topic)
        return 0

    report = validate_cards(args.evidence, args.min_detail_fields, args.min_claim_len)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print_validation(report)
    return 1 if report["invalid_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
