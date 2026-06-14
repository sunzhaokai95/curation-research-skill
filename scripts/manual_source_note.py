#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manual_source_note.py - 记录人工/浏览器读取的公开来源摘录。

用于政府、监管、法院、交易所、官方数据库、反爬或 robots.txt 不允许自动抓取
的页面。脚本不访问网络,只把操作者已经人工读取到的标题、URL 和摘录写入
sources.jsonl,供 evidence_cards.py seed 或人工证据卡抽取使用。
"""
import argparse
import datetime
import json
import os
import sys
import urllib.parse


SOURCE_TYPES = {
    "government",
    "regulatory",
    "court",
    "exchange",
    "academic",
    "institution_or_database",
    "media",
    "web",
    "user",
}


def domain(url):
    return urllib.parse.urlparse(url).netloc.lower()


def read_text_arg(value):
    if value == "-":
        return sys.stdin.read().strip()
    if value and os.path.exists(value):
        with open(value, "r", encoding="utf-8") as f:
            return f.read().strip()
    return value or ""


def main():
    ap = argparse.ArgumentParser(description="记录人工/浏览器读取的公开来源摘录")
    ap.add_argument("--out", required=True, help="输出 sources.jsonl")
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--excerpt", required=True, help="摘录文本;传 - 从 stdin 读取;也可传文本文件路径")
    ap.add_argument("--source-type", default="web", choices=sorted(SOURCE_TYPES))
    ap.add_argument("--dimension-id", default="")
    ap.add_argument("--dimension", default="")
    ap.add_argument("--query", default="")
    ap.add_argument("--published-date", default="")
    ap.add_argument("--source-id", default="")
    ap.add_argument("--append", action="store_true", help="追加写入,默认覆盖")
    args = ap.parse_args()

    excerpt = read_text_arg(args.excerpt)
    if len(excerpt.strip()) < 20:
        print("ERROR: excerpt 太短,不像人工读取摘录", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    record = {
        "source_id": args.source_id or "M%s" % datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "status": "ok",
        "capture_method": "manual_or_browser",
        "url": args.url,
        "source_domain": domain(args.url),
        "query": args.query,
        "dimension_id": args.dimension_id,
        "dimension": args.dimension,
        "search_title": args.title,
        "search_snippet": excerpt[:220],
        "search_date": args.published_date,
        "source_type": args.source_type,
        "fetched_at": datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "title": args.title,
        "published_date": args.published_date,
        "description": excerpt[:500],
        "text": excerpt,
        "text_length": len(excerpt),
        "compliance_note": "人工/浏览器读取公开页面后记录;脚本未抓取该 URL。",
    }

    mode = "a" if args.append else "w"
    with open(args.out, mode, encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("已记录人工来源摘录: %s" % args.out)
    print("来源: %s" % args.title)
    print("URL: %s" % args.url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
