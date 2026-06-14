#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_init.py —— 为一个前期资料调研项目建立标准化的树形归档目录。

遵循资料整理规范:唯一资料库、树形目录、规范命名。
零第三方依赖。

生成的目录结构:
    <输出目录>/<首字母>_<项目名>_调研_<日期>/
    ├── 00_需求文档/           # 甲方原始需求(pdf/ppt/word)
    ├── 01_检索计划/            # research_plan.json 与查询清单
    ├── 02_搜索结果/            # search_results.jsonl 或手工搜索结果
    ├── 03_来源文本/            # sources.jsonl 与公开来源摘录
    ├── 04_证据卡/              # evidence_cards.jsonl 与校验结果
    ├── 05_覆盖审计/            # coverage_audit.json
    ├── 06_提炼笔记/            # 资料提炼笔记与导图大纲
    ├── 07_产出/               # 思维导图 .xmind
    └── README.md             # 项目元信息 + 命名约定

用法:
    python3 archive_init.py --name "某某企业" --type 企业 --out .
    python3 archive_init.py --name "某某主题馆" --type 主题馆 --out ~/projects
"""
import os
import argparse
import datetime


SUBDIRS = [
    ("00_需求文档", "甲方提供的原始需求(PDF/PPT/Word)"),
    ("01_检索计划", "research_plan.json、查询矩阵、必查核心"),
    ("02_搜索结果", "search_results.jsonl、真实 URL、查询任务"),
    ("03_来源文本", "sources.jsonl、公开来源摘录、用户资料摘录"),
    ("04_证据卡", "evidence_cards.jsonl、证据卡校验结果"),
    ("05_覆盖审计", "coverage_audit.json、缺口清单、补搜记录"),
    ("06_提炼笔记", "资料提炼笔记与导图大纲"),
    ("07_产出", "思维导图 .xmind"),
]


def initials(name):
    """取项目名拼音/字母首字母作为前缀;无 ascii 时退化为 'X'。
    纯标准库不做拼音转换,取首个 ascii 字母,否则用 'P'(Project)。"""
    for ch in name:
        if ch.isascii() and ch.isalpha():
            return ch.upper()
    return "P"


def main():
    ap = argparse.ArgumentParser(description="建立前期资料调研项目归档目录")
    ap.add_argument("--name", required=True, help="项目名称,如 某某企业 / 某某主题")
    ap.add_argument("--type", default="", help="项目类型:企业/博物馆/文旅")
    ap.add_argument("--out", default=".", help="输出父目录")
    ap.add_argument("--prefix", default=None,
                    help="项目名前缀,如拼音首字母 B(某某)。不填则自动推断")
    ap.add_argument("--date", default=None, help="日期 YYYYMMDD,默认今天")
    args = ap.parse_args()

    date = args.date or datetime.date.today().strftime("%Y%m%d")
    prefix = args.prefix or initials(args.name)
    folder = "%s_%s_调研_%s" % (prefix, args.name, date)
    root = os.path.join(os.path.expanduser(args.out), folder)

    os.makedirs(root, exist_ok=True)
    for sub, _desc in SUBDIRS:
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    readme = os.path.join(root, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# %s — 前期资料调研\n\n" % args.name)
        if args.type:
            f.write("- 项目类型:%s\n" % args.type)
        f.write("- 建档日期:%s\n" % date)
        f.write("- 目录前缀:%s\n\n" % prefix)
        f.write("## 文件命名约定\n\n")
        f.write("`%s_%s_<分项>_<事项>_资料_%s`\n\n" % (prefix, args.name, date))
        f.write("例:`%s_%s_企业官网_资料合集_资料_%s.md`\n\n" % (prefix, args.name, date))
        f.write("## 目录说明\n\n")
        for sub, desc in SUBDIRS:
            f.write("- `%s/` — %s\n" % (sub, desc))

    print("已建立归档目录:")
    print(root)
    for sub, _ in SUBDIRS:
        print("  " + sub)
    print("命名前缀:", prefix)


if __name__ == "__main__":
    main()
