#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_sources.py - 抓取允许自动访问的普通公开网页并抽取基础文本。

合规边界:
- 政府、监管、法院、交易所、官方数据库等权威来源默认不抓取。
- 这些来源会被写成 manual_required 记录,由操作者用浏览器人工读取后,
  再用 manual_source_note.py 记录摘录。
- 普通网页也不绕过登录墙、付费墙、反爬或 robots.txt 限制。
"""
import argparse
import datetime
import html
import json
import os
import re
import urllib.robotparser
import sys
import urllib.parse
import urllib.request


USER_AGENT = "curation-research/2.0 (+public research workflow)"

MANUAL_DOMAIN_HINTS = (
    ".gov.",
    ".gov/",
    "gov.cn",
    "sec.gov",
    "court.gov",
    "chinacourt.gov.cn",
    "sse.com.cn",
    "szse.cn",
    "hkexnews.hk",
    "cninfo.com.cn",
    "pbc.gov.cn",
    "csrc.gov.cn",
    "samr.gov.cn",
    "stats.gov.cn",
    "ndrc.gov.cn",
    "miit.gov.cn",
    "moa.gov.cn",
    "npc.gov.cn",
)


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def domain(url):
    return urllib.parse.urlparse(url).netloc.lower()


def should_require_manual(url):
    d = domain(url)
    if not d:
        return False
    if d.endswith(".gov") or d.endswith(".gov.cn"):
        return True
    return any(hint in d for hint in MANUAL_DOMAIN_HINTS)


def robots_allows(url, timeout=8):
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    robots_url = "%s://%s/robots.txt" % (parsed.scheme, parsed.netloc)
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return True
    return parser.can_fetch(USER_AGENT, url)


def fetch_url(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("content-type", "")
        raw = resp.read()
    charset = "utf-8"
    m = re.search(r"charset=([\w.-]+)", content_type, re.I)
    if m:
        charset = m.group(1)
    return raw.decode(charset, "ignore"), content_type


def extract_title(text):
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if not m:
        return ""
    return clean_text(m.group(1))[:200]


def extract_meta(text, names):
    for name in names:
        patterns = [
            r'<meta[^>]+name=["\']%s["\'][^>]+content=["\'](.*?)["\']' % re.escape(name),
            r'<meta[^>]+property=["\']%s["\'][^>]+content=["\'](.*?)["\']' % re.escape(name),
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']%s["\']' % re.escape(name),
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']%s["\']' % re.escape(name),
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.S)
            if m:
                return clean_text(m.group(1))
    return ""


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_body(text, max_chars):
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<header.*?</header>", " ", text)
    text = re.sub(r"(?is)<footer.*?</footer>", " ", text)
    text = re.sub(r"(?is)<nav.*?</nav>", " ", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 20:
            lines.append(line)
    body = "\n".join(lines)
    return body[:max_chars]


def guess_source_type(url):
    d = domain(url)
    if d.endswith(".gov") or ".gov." in d:
        return "government"
    if d.endswith(".edu") or ".edu." in d or "edu.cn" in d:
        return "academic"
    if "museum" in d or "library" in d or "archive" in d or "db" in d:
        return "institution_or_database"
    if "sec.gov" in d or "exchange" in d:
        return "regulatory"
    if any(x in d for x in ("news", "reuters", "apnews", "xinhuanet", "people.com", "chinanews")):
        return "media"
    return "web"


def manual_required_record(record, seq, reason):
    url = record.get("url", "")
    return {
        "source_id": "S%04d" % seq,
        "status": "manual_required",
        "reason": reason,
        "url": url,
        "source_domain": domain(url),
        "query": record.get("query", ""),
        "dimension_id": record.get("dimension_id", ""),
        "dimension": record.get("dimension", ""),
        "search_title": record.get("title", ""),
        "search_snippet": record.get("snippet", ""),
        "search_date": record.get("date", ""),
        "source_type": guess_source_type(url),
        "fetched_at": datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "title": record.get("title", ""),
        "published_date": record.get("date", ""),
        "description": record.get("snippet", ""),
        "text": "",
        "text_length": 0,
        "next_step": "请用浏览器人工读取该公开页面,再用 scripts/manual_source_note.py 记录标题、URL、摘录和采信边界。",
    }


def source_from_search_record(record, seq, timeout, max_chars):
    url = record.get("url", "")
    if should_require_manual(url):
        return manual_required_record(record, seq, "官方/监管/政府/交易所类来源不使用爬虫抓取")
    if not robots_allows(url):
        return manual_required_record(record, seq, "robots.txt 不允许自动抓取")
    base = {
        "source_id": "S%04d" % seq,
        "url": url,
        "source_domain": domain(url),
        "query": record.get("query", ""),
        "dimension_id": record.get("dimension_id", ""),
        "dimension": record.get("dimension", ""),
        "search_title": record.get("title", ""),
        "search_snippet": record.get("snippet", ""),
        "search_date": record.get("date", ""),
        "source_type": guess_source_type(url),
        "fetched_at": datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    try:
        html_text, content_type = fetch_url(url, timeout)
        title = extract_title(html_text) or record.get("title", "")
        published = extract_meta(html_text, [
            "article:published_time", "og:published_time", "date", "pubdate",
            "citation_publication_date", "dc.date", "DC.date",
        ])
        description = extract_meta(html_text, ["description", "og:description"])
        body = extract_body(html_text, max_chars)
        base.update({
            "status": "ok",
            "content_type": content_type,
            "title": title,
            "published_date": published or record.get("date", ""),
            "description": description,
            "text": body,
            "text_length": len(body),
        })
    except Exception as exc:
        base.update({
            "status": "error",
            "error": str(exc),
            "title": record.get("title", ""),
            "published_date": record.get("date", ""),
            "description": record.get("snippet", ""),
            "text": "",
            "text_length": 0,
        })
    return base


def main():
    ap = argparse.ArgumentParser(description="抓取搜索结果 URL 并抽取基础文本")
    ap.add_argument("--search-results", required=True, help="search_results.jsonl")
    ap.add_argument("--out", required=True, help="输出 sources.jsonl")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--max-chars", type=int, default=12000)
    ap.add_argument("--limit", type=int, help="最多抓取 URL 数")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    seen = set()
    seq = 0
    wrote = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for record in read_jsonl(args.search_results):
            if record.get("kind") != "search_result":
                continue
            url = record.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            seq += 1
            if args.limit and seq > args.limit:
                break
            source = source_from_search_record(record, seq, args.timeout, args.max_chars)
            out.write(json.dumps(source, ensure_ascii=False) + "\n")
            wrote += 1
    print("来源抓取输出: %s" % args.out)
    print("来源记录: %d" % wrote)
    if wrote == 0:
        print("没有可抓取的 search_result;query_task 不能当作资料来源。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
