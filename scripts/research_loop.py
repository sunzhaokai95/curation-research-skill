#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
research_loop.py - 根据检索计划、覆盖审计和已抽取证据生成深搜补搜任务。

这个脚本借鉴 deep-research 的递归思路,但保持纯 Python 标准库和可审计输出:
- 每条补搜查询都带 research_goal,说明为什么搜、要补哪类证据。
- 根据 coverage_audit.json 的缺口优先补搜,没有审计文件时覆盖全部必查核心。
- 读取 evidence_cards.jsonl 后记录 visited_urls,避免重复把已用来源当作新发现。
- 用 breadth/depth 形成多轮查询,让操作者看到当前轮次、剩余深度和父查询。
"""
import argparse
import datetime
import json
import os
import re
import sys


CORE_DIMENSION_HINTS = [
    (("主题", "边界", "名称", "定义", "身份"), "topic_boundary"),
    (("历史", "源流", "阶段", "时间", "生平", "年谱", "大事记"), "history_timeline"),
    (("地理", "空间", "区域", "行旅", "遗址"), "geography_space"),
    (("人物", "群体", "组织", "社群", "家族", "师友", "领导"), "people_network"),
    (("分类", "谱系", "子主题", "类型"), "classification"),
    (("对象", "工具", "材料", "作品", "文本", "影像", "档案", "文献", "馆藏", "载体"), "objects_archives"),
    (("原理", "机制", "流程", "工艺", "操作", "入门", "进阶", "技术"), "mechanism_process"),
    (("行为", "场景", "日常", "实践", "使用"), "scenes_practice"),
    (("产业", "消费", "市场", "数据", "规模", "平台", "品牌", "渠道", "客户"), "data_market"),
    (("企业", "机构", "主体", "品牌", "研究会", "协会"), "institutions"),
    (("财经", "资本", "上市", "IPO", "融资", "估值", "收入", "当代", "最新"), "finance_recent"),
    (("政策", "安全", "生态", "伦理", "行业规范", "法规", "制度", "监管", "合规"), "policy_standards"),
    (("文化", "圈层", "语言", "媒介", "传播", "符号"), "culture_media"),
    (("故事", "事件", "争议", "失败", "版本"), "stories_debates"),
    (("学术", "权威", "来源", "出处", "论文", "专著"), "authority_sources"),
    (("最新", "当前", "近一年", "近90天", "近30天"), "latest_status"),
    (("同类", "对照", "横向"), "comparables"),
    (("来源索引", "待核实"), "source_index"),
]


TYPE_CORE_QUERY_PATTERNS = {
    "A": {
        "主体身份与名称体系": ["{subject} 官网 公司简介", "{subject} 法人 主体 总部 成立时间", "{subject} founder leadership organization"],
        "创始人/领导层/组织结构": ["{subject} 创始人 领导层", "{subject} executive team organization", "{subject} 子公司 组织结构"],
        "产品业务谱系": ["{subject} 产品 业务线", "{subject} product portfolio business", "{subject} 客户 合作伙伴"],
        "技术能力与生产系统": ["{subject} 技术 能力 生产 设施", "{subject} technology manufacturing delivery", "{subject} 专利 设施 供应链"],
        "市场客户与产业链": ["{subject} 市场 客户 产业链", "{subject} market share customers suppliers", "{subject} 行业报告 竞争格局"],
        "财经资本/上市IPO/融资/估值/收入": ["{subject} IPO 上市 融资 估值", "{subject} revenue funding valuation investors", "site:sec.gov {subject} OR {subject} S-1"],
        "监管诉讼/合规/风险": ["{subject} 监管 诉讼 处罚 合规", "{subject} lawsuit regulator license", "{subject} risk compliance court"],
        "最新动态/近一年/近90天": ["{subject} {year} 最新 动态", "{subject} latest news {year}", "{subject} 近90天 新闻 监管"],
        "同类企业事实对照": ["{subject} competitors comparison", "{subject} 同类 企业 对比", "{subject} 替代 技术路线"],
        "来源索引与待核实清单": ["{subject} investor relations official news", "{subject} annual report filing database", "{subject} source database official"],
    },
    "B": {
        "主题边界与名称体系": ["{subject} 是谁 名 字 号", "{subject} 生卒年 籍贯 身份", "{subject} 名称 别名 主题边界"],
        "生平年谱": ["{subject} 年谱", "{subject} 生平 年表", "{subject} chronology biography"],
        "家族师友与关系网络": ["{subject} 家族 师友 同僚 关系", "{subject} 交游 门生 研究", "{subject} family friends network"],
        "时代制度背景": ["{subject} 时代背景 制度", "{subject} 官制 科举 政治 背景", "{subject} historical context"],
        "地理行旅与空间遗存": ["{subject} 行旅 地理 轨迹", "{subject} 任职地 流寓地 遗址", "{subject} 纪念地 博物馆 馆藏地"],
        "作品文献/版本/注本": ["{subject} 文集 全集 注本", "{subject} 作品 版本 目录", "{subject} poems writings editions"],
        "实物馆藏/碑刻/图像档案": ["{subject} 馆藏 碑刻 书画 图录", "{subject} 文物 档案 图像", "{subject} collection archive inscription"],
        "思想风格与术语体系": ["{subject} 思想 风格 术语", "{subject} 文学风格 艺术风格", "{subject} 研究 关键词"],
        "后世接受/传播/研究史": ["{subject} 接受史 传播 研究史", "{subject} 后世评价 纪念", "{subject} scholarship reception"],
        "当代保护/出版/数字化/纪念活动": ["{subject} {year} 研究 出版 数字化", "{subject} 保护 纪念 活动 {year}", "{subject} 数据库 数字资源 更新"],
        "来源索引与待核实清单": ["{subject} 年谱 文集 地方志 正史", "{subject} 论文 专著 数据库", "{subject} 博物馆 图书馆 档案馆"],
    },
    "C": {
        "主题定义与边界": ["{subject} 是什么 入门", "{alias} 是什么 入门", "{subject} 与 相邻概念 区别"],
        "历史源流与阶段变化": ["{alias} 历史 起源 发展", "{alias} history timeline", "{subject} 文化 发展阶段 中国"],
        "分类谱系与子主题系统": ["{alias} 分类 术语 工具", "{alias} types classification", "{subject} 分类 入门 术语"],
        "关键对象/工具/材料/作品/文本/影像": ["{alias} 工具 装备 材料", "{alias} 器具 产品 种类", "{subject} 装备 入门 分类"],
        "行为流程/入门路径/进阶路径": ["{alias} 新手 入门 流程", "{alias} 技巧 方法 进阶", "{subject} 入门 教程 安全"],
        "人物群体/社群组织/代表人物": ["{alias} 协会 俱乐部 赛事", "{subject} 社群 人群 画像", "{alias} 代表人物 组织"],
        "场景空间与日常实践": ["{alias} 场景 水域 地域", "{alias} 日常实践 场景 中国", "{subject} 去哪里 场景"],
        "产业消费/平台数据/品牌渠道": ["{alias} 市场 消费 行业报告", "{alias} 渔具 品牌 渠道 数据", "{subject} 消费 装备 平台"],
        "社会文化/圈层语言/媒介传播": ["{alias} 黑话 梗 传播", "{alias} 文化 圈层 身份", "{subject} 短视频 社交媒体 传播"],
        "政策安全/生态伦理/行业规范": ["{alias} 政策 法规 禁钓 规范", "{alias} 安全 生态 伦理", "{alias} 休闲垂钓 管理办法"],
        "最新动态与当前状态": ["{alias} {year} 最新 趋势", "{subject} {year} 最新 动态", "{alias} 近一年 活动 赛事 政策"],
        "来源索引与待核实清单": ["{subject} 协会 官网 政策 数据库", "{subject} 行业报告 学术论文", "{subject} 规则 手册 标准"],
    },
    "D": {
        "主题定义与边界": ["{subject} 是什么 definition", "{subject} 入门 概览", "{subject} 术语 边界"],
        "历史源流与时间线": ["{subject} 历史 时间线", "{subject} 起源 发展", "{subject} 大事记"],
        "人物组织与关系网络": ["{subject} 人物 组织 机构", "{subject} experts organizations", "{subject} 代表人物"],
        "分类谱系与子主题系统": ["{subject} 分类 类型", "{subject} taxonomy classification", "{subject} 子主题"],
        "关键对象/载体/作品/档案": ["{subject} 对象 作品 档案", "{subject} materials archives", "{subject} 数据库 来源"],
        "机制流程与方法": ["{subject} 原理 方法 流程", "{subject} how it works", "{subject} practice process"],
        "场景实践与使用方式": ["{subject} 场景 使用 实践", "{subject} use cases", "{subject} 入门 进阶"],
        "数据规模与现状": ["{subject} 数据 规模 现状", "{subject} statistics current status", "{subject} 报告 数据"],
        "政策制度与风险伦理": ["{subject} 政策 法规 风险", "{subject} regulation ethics", "{subject} 标准 监管"],
        "社会文化与传播": ["{subject} 文化 传播 媒介", "{subject} symbolism media", "{subject} 舆论"],
        "最新动态与当前状态": ["{subject} {year} 最新 动态", "{subject} latest news {year}", "{subject} 当前状态"],
        "来源索引与待核实清单": ["{subject} 权威资料 来源", "{subject} source database", "{subject} 论文 专著"],
    },
}


DEPTH_FOCUS_PATTERNS = [
    ("authority", "权威来源轮", "{subject} {core_keyword} 官方 政府 学术 协会 数据库"),
    ("detail", "细节下钻轮", "{subject} {core_keyword} 时间 人物 地点 对象 数据 来源"),
    ("freshness", "最新核验轮", "{subject} {core_keyword} {year} 最新 近一年"),
    ("crosscheck", "交叉核验轮", "{subject} {core_keyword} 争议 口径 不同说法 来源"),
]


CORE_KEYWORD_STOP = {
    "主题", "边界", "名称", "体系", "历史", "源流", "阶段", "变化", "关键", "对象",
    "材料", "作品", "文本", "影像", "流程", "路径", "群体", "组织", "人物", "空间",
    "日常", "实践", "产业", "消费", "平台", "数据", "品牌", "渠道", "社会", "文化",
    "语言", "传播", "政策", "安全", "生态", "伦理", "行业规范", "最新", "动态",
    "当前", "状态", "来源", "索引", "待核实", "清单", "分类", "谱系", "子主题",
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


def safe_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def first_alias(plan, subject):
    aliases = plan.get("theme_profile", {}).get("subject_aliases") or []
    for alias in aliases:
        if alias and alias != subject:
            return alias
    return subject


def dimension_for_core(core):
    for tokens, dim_id in CORE_DIMENSION_HINTS:
        if any(token in core for token in tokens):
            return dim_id
    return "topic_boundary"


def dimension_info(plan):
    out = {}
    for group in plan.get("query_groups", []):
        out[group.get("dimension_id")] = {
            "dimension": group.get("dimension", ""),
            "expected_evidence_fields": group.get("evidence_fields", []),
        }
    return out


def core_keyword(core):
    parts = re.split(r"[/、与和及\|\s]+", core)
    for part in parts:
        part = part.strip()
        if len(part) >= 2 and part not in CORE_KEYWORD_STOP:
            return part
    clean = re.sub(r"[/、与和及\|\s]+", " ", core).strip()
    return clean[:12] if clean else core


def coverage_missing_cores(plan, coverage):
    required = plan.get("theme_profile", {}).get("required_cores", [])
    if not coverage:
        return list(required), {core: "未提供覆盖审计,按全部必查核心生成深搜任务" for core in required}
    missing = []
    reasons = {}
    by_core = {r.get("core"): r for r in coverage.get("core_reports", [])}
    for core in required:
        report = by_core.get(core)
        if not report or not report.get("passed"):
            missing.append(core)
            if report:
                reasons[core] = "证据卡%d条/来源%d个/事实字段%s,未达到覆盖阈值" % (
                    report.get("evidence_cards", 0),
                    report.get("sources", 0),
                    ",".join(report.get("evidence_fields", [])) or "-",
                )
            else:
                reasons[core] = "覆盖审计缺少该核心项"
    return missing, reasons


def visited_urls_from_evidence(path):
    if not path or not os.path.exists(path):
        return []
    urls = []
    seen = set()
    for card in read_jsonl(path):
        url = str(card.get("source_url", "")).strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def plan_queries_by_core(plan, core, type_code, subject, alias, year):
    patterns = TYPE_CORE_QUERY_PATTERNS.get(type_code, {}).get(core)
    if not patterns:
        keyword = core_keyword(core)
        patterns = [
            "{subject} " + keyword,
            "{subject} " + keyword + " 权威 来源",
            "{subject} " + keyword + " 数据 时间 人物",
        ]
    out = []
    for pattern in patterns:
        query = pattern.format(
            subject=subject,
            alias=alias,
            year=year,
            core=core,
            core_keyword=core_keyword(core),
        )
        query = re.sub(r"\s+", " ", query).strip()
        if query:
            out.append(query)
    return out


def build_query_record(query, plan, core, iteration, depth_remaining, parent_query, reason, focus):
    dim_id = dimension_for_core(core)
    dims = dimension_info(plan)
    info = dims.get(dim_id, {})
    expected = list(info.get("expected_evidence_fields") or [])
    for field in ("时间", "人物", "地点", "对象", "数据", "来源"):
        if field not in expected:
            expected.append(field)
    return {
        "query": query,
        "core": core,
        "dimension_id": dim_id,
        "dimension": info.get("dimension", dim_id),
        "research_goal": "补足「%s」: %s; 搜索后必须抽取可核验事实,包含时间、人物/组织、地点/场景、对象、数据口径和来源边界。" % (core, reason),
        "expected_evidence_fields": expected,
        "stop_condition": "该核心至少达到覆盖审计阈值:每个必查核心有足够证据卡、至少2个来源、事实字段不少于3类;若仍不足,继续下一轮深搜。",
        "parent_query": parent_query,
        "iteration": iteration,
        "depth_remaining": depth_remaining,
        "focus": focus,
    }


def generate_loop(plan, coverage=None, evidence_path=None, breadth=4, depth=2, date=None):
    today = date or datetime.date.today().isoformat()
    year = today[:4]
    type_code = plan.get("project_type", {}).get("code", "D")
    subject = plan.get("theme_profile", {}).get("content_subject") or plan.get("topic", "")
    alias = first_alias(plan, subject)
    missing, reasons = coverage_missing_cores(plan, coverage)
    if not missing:
        missing = plan.get("theme_profile", {}).get("required_cores", [])[: max(1, breadth)]
        reasons = {core: "覆盖审计已通过,生成抽样复核任务以检查是否仍有最新资料或口径差异" for core in missing}

    query_records = []
    iterations = []
    seen_queries = set()
    candidate_cores = missing[:]
    if len(candidate_cores) > breadth * max(depth, 1):
        candidate_cores = candidate_cores[: breadth * max(depth, 1)]

    for iteration in range(1, max(depth, 1) + 1):
        depth_remaining = max(depth - iteration + 1, 0)
        batch = []
        start = (iteration - 1) * breadth
        cores_for_round = candidate_cores[start:start + breadth] or candidate_cores[:breadth]
        for core in cores_for_round:
            base_queries = plan_queries_by_core(plan, core, type_code, subject, alias, year)
            if iteration == 1:
                selected = base_queries[: max(1, min(3, breadth))]
                focus = "coverage_gap"
                parent = None
            else:
                keyword = core_keyword(core)
                focus_id, focus_name, template = DEPTH_FOCUS_PATTERNS[(iteration - 2) % len(DEPTH_FOCUS_PATTERNS)]
                selected = [template.format(subject=subject, core_keyword=keyword, year=year)]
                focus = "%s/%s" % (focus_id, focus_name)
                parent = base_queries[0] if base_queries else None
            for q in selected:
                if q in seen_queries:
                    continue
                seen_queries.add(q)
                record = build_query_record(
                    q,
                    plan,
                    core,
                    iteration,
                    depth_remaining,
                    parent,
                    reasons.get(core, "覆盖不足"),
                    focus,
                )
                query_records.append(record)
                batch.append(record)
        iterations.append({
            "iteration": iteration,
            "current_depth": depth_remaining,
            "breadth": breadth,
            "cores": cores_for_round,
            "queries": batch,
        })

    return {
        "schema_version": "1.0",
        "topic": plan.get("topic", ""),
        "content_subject": subject,
        "project_type": plan.get("project_type", {}),
        "region": plan.get("region", ""),
        "generated_at": today,
        "breadth": breadth,
        "depth": depth,
        "missing_cores": missing,
        "visited_urls": visited_urls_from_evidence(evidence_path),
        "progress": {
            "total_queries": len(query_records),
            "completed_queries": 0,
            "current_query": query_records[0]["query"] if query_records else "",
        },
        "iterations": iterations,
        "queries": query_records,
    }


def main():
    ap = argparse.ArgumentParser(description="根据覆盖缺口生成多轮深搜补搜任务")
    ap.add_argument("--plan", required=True, help="research_plan.json")
    ap.add_argument("--coverage", help="coverage_audit.json;不提供则按全部必查核心生成任务")
    ap.add_argument("--evidence", help="evidence_cards.jsonl;用于记录 visited_urls")
    ap.add_argument("--out", required=True, help="输出 research_loop.json")
    ap.add_argument("--breadth", type=int, default=4, help="每轮最多优先处理多少个核心")
    ap.add_argument("--depth", type=int, default=2, help="补搜轮数")
    ap.add_argument("--date", help="生成日期 YYYY-MM-DD;默认今天")
    args = ap.parse_args()

    plan = read_json(args.plan)
    coverage = read_json(args.coverage) if args.coverage else None
    result = generate_loop(
        plan,
        coverage=coverage,
        evidence_path=args.evidence,
        breadth=max(1, args.breadth),
        depth=max(1, args.depth),
        date=args.date,
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("已生成深搜补搜计划: %s" % args.out)
    print("缺口核心: %d" % len(result["missing_cores"]))
    print("补搜查询: %d" % len(result["queries"]))
    for q in result["queries"][:20]:
        print("- [%s] %s" % (q["core"], q["query"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
