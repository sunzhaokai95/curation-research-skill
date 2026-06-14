#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_collect.py - 按 research_plan.json 执行搜索或导出查询任务。

支持的搜索后端均通过环境变量配置,无第三方依赖:
- BRAVE_API_KEY
- SERPER_API_KEY
- BING_SEARCH_KEY

没有 API key 时不会假装搜过,而是输出 query_task 记录,提醒操作者用这些
查询式通过浏览器/模型工具/其他搜索工具补入结果。
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request


USER_AGENT = "curation-research/2.0 (+public research workflow)"


def read_plan(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def request_json(method, url, headers=None, payload=None, timeout=20):
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", "ignore"))


def brave_search(query, count):
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        raise RuntimeError("BRAVE_API_KEY not set")
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({
        "q": query,
        "count": count,
    })
    data = request_json("GET", url, headers={"X-Subscription-Token": key})
    out = []
    for item in data.get("web", {}).get("results", [])[:count]:
        out.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
            "date": (item.get("page_age") or "")[:10],
        })
    return out


def serper_search(query, count):
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        raise RuntimeError("SERPER_API_KEY not set")
    data = request_json(
        "POST",
        "https://google.serper.dev/search",
        headers={"X-API-KEY": key},
        payload={"q": query, "num": count},
    )
    out = []
    for item in data.get("organic", [])[:count]:
        out.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "date": item.get("date", ""),
        })
    return out


def bing_search(query, count):
    key = os.environ.get("BING_SEARCH_KEY")
    if not key:
        raise RuntimeError("BING_SEARCH_KEY not set")
    url = "https://api.bing.microsoft.com/v7.0/search?" + urllib.parse.urlencode({
        "q": query,
        "count": count,
        "responseFilter": "Webpages",
    })
    data = request_json("GET", url, headers={"Ocp-Apim-Subscription-Key": key})
    out = []
    for item in data.get("webPages", {}).get("value", [])[:count]:
        out.append({
            "title": item.get("name", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "date": item.get("dateLastCrawled", "")[:10],
        })
    return out


def pick_backend(requested):
    if requested != "auto":
        return requested
    if os.environ.get("BRAVE_API_KEY"):
        return "brave"
    if os.environ.get("SERPER_API_KEY"):
        return "serper"
    if os.environ.get("BING_SEARCH_KEY"):
        return "bing"
    return "none"


def run_backend(backend, query, count):
    if backend == "brave":
        return brave_search(query, count)
    if backend == "serper":
        return serper_search(query, count)
    if backend == "bing":
        return bing_search(query, count)
    if backend == "none":
        return []
    raise ValueError("unsupported backend: %s" % backend)


def iter_queries(plan, limit_groups=None):
    groups = plan.get("query_groups", [])
    if limit_groups:
        groups = groups[:limit_groups]
    for group in groups:
        for q in group.get("queries", []):
            yield group, q


def main():
    ap = argparse.ArgumentParser(description="按检索计划执行搜索或导出查询任务")
    ap.add_argument("--plan", required=True, help="research_plan.json")
    ap.add_argument("--out", required=True, help="输出 search_results.jsonl")
    ap.add_argument("--backend", default="auto", choices=["auto", "none", "brave", "serper", "bing"])
    ap.add_argument("--limit-per-query", type=int, default=5)
    ap.add_argument("--limit-groups", type=int, help="仅调试用:限制搜索维度数量")
    ap.add_argument("--sleep", type=float, default=0.2, help="查询间隔秒数")
    args = ap.parse_args()

    plan = read_plan(args.plan)
    backend = pick_backend(args.backend)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    seen_urls = set()
    records = []
    errors = []

    for group, q in iter_queries(plan, args.limit_groups):
        query = q["query"]
        if backend == "none":
            records.append({
                "kind": "query_task",
                "topic": plan.get("topic"),
                "dimension_id": group.get("dimension_id"),
                "dimension": group.get("dimension"),
                "query": query,
                "must_extract": q.get("must_extract", []),
                "reason": "未配置搜索 API;请用该查询式通过浏览器或模型搜索工具补充结果",
            })
            continue
        try:
            items = run_backend(backend, query, args.limit_per_query)
        except Exception as exc:
            errors.append({"query": query, "error": str(exc), "backend": backend})
            records.append({
                "kind": "query_error",
                "topic": plan.get("topic"),
                "dimension_id": group.get("dimension_id"),
                "dimension": group.get("dimension"),
                "query": query,
                "backend": backend,
                "error": str(exc),
            })
            continue
        for rank, item in enumerate(items, 1):
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            records.append({
                "kind": "search_result",
                "topic": plan.get("topic"),
                "dimension_id": group.get("dimension_id"),
                "dimension": group.get("dimension"),
                "query": query,
                "backend": backend,
                "rank": rank,
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "must_extract": q.get("must_extract", []),
            })
        time.sleep(args.sleep)

    with open(args.out, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("搜索输出: %s" % args.out)
    print("后端: %s" % backend)
    print("记录数: %d" % len(records))
    if backend == "none":
        print("未配置搜索 API,已输出 query_task;这些任务不能算作已搜到资料。", file=sys.stderr)
    if errors:
        print("搜索错误: %d" % len(errors), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
