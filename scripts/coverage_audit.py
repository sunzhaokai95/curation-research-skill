#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coverage_audit.py - 对 evidence_cards.jsonl 做覆盖审计。

通过条件不是“分支很多”,而是 research_plan.json 中的必查核心都有足够证据卡
和来源支撑。未通过时不允许写调研大纲。
"""
import argparse
import json
import os
import re
import sys


AUTHORITY_TYPES = {
    "government",
    "regulatory",
    "academic",
    "institution_or_database",
    "机构资料",
    "学术资料",
    "官方确认",
    "监管文件",
}


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def core_tokens(core):
    parts = re.split(r"[/、与和及\|\s]+", core)
    out = []
    for part in parts:
        part = part.strip()
        if len(part) >= 2:
            out.append(part)
    out.append(core)
    return list(dict.fromkeys(out))


def card_text(card):
    values = [
        card.get("core", ""),
        card.get("dimension", ""),
        card.get("claim", ""),
        " ".join(card.get("topic_path", []) if isinstance(card.get("topic_path"), list) else []),
    ]
    return "\n".join(str(v) for v in values)


def matches_core(card, core):
    text = card_text(card)
    if str(card.get("core", "")).strip() == core:
        return True
    return any(token in text for token in core_tokens(core))


def is_evidence(card):
    if card.get("status") == "needs_extraction":
        return False
    return bool(str(card.get("claim", "")).strip() and str(card.get("source_url", "")).strip())


def audit(plan_path, evidence_path, args):
    plan = read_json(plan_path)
    cards = [c for c in read_jsonl(evidence_path) if is_evidence(c)]
    thresholds = plan.get("coverage_thresholds", {})
    min_cards = args.min_cards_per_core or thresholds.get("min_evidence_cards_per_required_core", 5)
    min_sources = args.min_sources_per_core or thresholds.get("min_sources_per_required_core", 2)
    min_total_sources = args.min_total_sources or thresholds.get("min_total_sources", 30)
    min_authority = args.min_authority_sources or thresholds.get("min_authority_sources", 8)
    min_fields = args.min_fields_per_core or thresholds.get("min_factual_fields_per_required_core", 3)

    total_sources = sorted({c.get("source_url", "") for c in cards if c.get("source_url")})
    authority_sources = sorted({
        c.get("source_url", "")
        for c in cards
        if c.get("source_url") and (
            c.get("source_type") in AUTHORITY_TYPES or c.get("confidence") in AUTHORITY_TYPES
        )
    })

    core_reports = []
    for core in plan.get("theme_profile", {}).get("required_cores", []):
        matched = [c for c in cards if matches_core(c, core)]
        urls = sorted({c.get("source_url", "") for c in matched if c.get("source_url")})
        fields = set()
        for c in matched:
            for field in ("time", "people", "places", "objects", "data"):
                value = c.get(field)
                if value:
                    fields.add(field)
        field_requirement_applies = "来源索引" not in core and "待核实清单" not in core
        fields_passed = (not field_requirement_applies) or len(fields) >= min_fields
        core_reports.append({
            "core": core,
            "evidence_cards": len(matched),
            "sources": len(urls),
            "evidence_fields": sorted(fields),
            "min_factual_fields": min_fields if field_requirement_applies else 0,
            "passed": len(matched) >= min_cards and len(urls) >= min_sources and fields_passed,
            "sample_claims": [c.get("claim", "") for c in matched[:3]],
        })

    errors = []
    missing = [r for r in core_reports if not r["passed"]]
    if missing:
        errors.append("必查核心证据不足: %d 项未通过" % len(missing))
    if len(total_sources) < min_total_sources:
        errors.append("总来源数不足: %d < %d" % (len(total_sources), min_total_sources))
    if len(authority_sources) < min_authority:
        errors.append("权威来源数不足: %d < %d" % (len(authority_sources), min_authority))

    return {
        "plan": os.path.abspath(plan_path),
        "evidence": os.path.abspath(evidence_path),
        "topic": plan.get("topic", ""),
        "total_evidence_cards": len(cards),
        "total_sources": len(total_sources),
        "authority_sources": len(authority_sources),
        "thresholds": {
            "min_cards_per_core": min_cards,
            "min_sources_per_core": min_sources,
            "min_total_sources": min_total_sources,
            "min_authority_sources": min_authority,
            "min_fields_per_core": min_fields,
        },
        "core_reports": core_reports,
        "errors": errors,
    }


def print_report(report):
    print("覆盖审计%s: %s" % ("通过" if not report["errors"] else "失败", report["topic"]))
    print("证据卡: %d" % report["total_evidence_cards"])
    print("总来源: %d" % report["total_sources"])
    print("权威来源: %d" % report["authority_sources"])
    for err in report["errors"]:
        print("ERROR: " + err)
    for core in report["core_reports"]:
        flag = "OK" if core["passed"] else "MISS"
        print("%s %s: cards=%d sources=%d fields=%s" % (
            flag,
            core["core"],
            core["evidence_cards"],
            core["sources"],
            ",".join(core["evidence_fields"]) or "-",
        ))


def main():
    ap = argparse.ArgumentParser(description="审计证据卡是否覆盖检索计划")
    ap.add_argument("--plan", required=True, help="research_plan.json")
    ap.add_argument("--evidence", required=True, help="evidence_cards.jsonl")
    ap.add_argument("--json", help="输出 coverage_audit.json")
    ap.add_argument("--min-cards-per-core", type=int)
    ap.add_argument("--min-sources-per-core", type=int)
    ap.add_argument("--min-fields-per-core", type=int)
    ap.add_argument("--min-total-sources", type=int)
    ap.add_argument("--min-authority-sources", type=int)
    args = ap.parse_args()

    report = audit(args.plan, args.evidence, args)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print_report(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
