#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
research_plan.py - 为策展前期资料调研生成机器可审计的检索计划。

这个脚本不做事实判断,只把主题拆成必查核心、搜索方向、查询式和覆盖门槛。
后续脚本用它判断:是否真的搜过关键方向,是否能进入导图写作阶段。
"""
import argparse
import datetime
import json
import os
import re
import sys


TYPE_ALIASES = {
    "A": "企业/机构/品牌",
    "企业": "企业/机构/品牌",
    "机构": "企业/机构/品牌",
    "品牌": "企业/机构/品牌",
    "B": "博物馆/文化馆/历史文化",
    "博物馆": "博物馆/文化馆/历史文化",
    "文化馆": "博物馆/文化馆/历史文化",
    "历史文化": "博物馆/文化馆/历史文化",
    "C": "文旅/主题馆/主题空间",
    "文旅": "文旅/主题馆/主题空间",
    "主题馆": "文旅/主题馆/主题空间",
    "主题空间": "文旅/主题馆/主题空间",
    "D": "其他主题",
    "其他": "其他主题",
}


TYPE_CODES = {
    "企业/机构/品牌": "A",
    "博物馆/文化馆/历史文化": "B",
    "文旅/主题馆/主题空间": "C",
    "其他主题": "D",
}


DIMENSIONS = [
    ("topic_boundary", "主题边界/基础定义", ["定义", "边界", "别名", "上下位概念", "误区"]),
    ("history_timeline", "时间历史/发展阶段", ["起源", "分期", "大事记", "当前阶段", "未来计划"]),
    ("geography_space", "地理空间/区域差异", ["地点", "分布", "设施", "路线", "区域差异"]),
    ("people_network", "人物/群体/组织网络", ["人物", "组织", "关系", "任职", "贡献"]),
    ("classification", "分类谱系/类型系统", ["分类依据", "子类", "典型特征", "适用场景"]),
    ("objects_archives", "关键对象/载体/实物/作品/档案", ["对象", "作品", "档案", "馆藏", "版本"]),
    ("mechanism_process", "原理/机制/工艺/操作流程", ["机制", "流程", "材料", "工具", "限制"]),
    ("scenes_practice", "场景/行为/使用方式/生活实践", ["参与者", "场景", "流程", "入门", "进阶"]),
    ("data_market", "数据/规模/市场/消费", ["数量", "金额", "规模", "口径", "年份"]),
    ("institutions", "企业/机构/品牌/组织公开资料", ["主体", "官网", "组织结构", "公开文件"]),
    ("finance_recent", "财经资本/交易/当代动态", ["上市", "融资", "估值", "收入", "当代保护"]),
    ("policy_standards", "政策/法规/制度/监管/伦理", ["政策", "标准", "许可", "监管", "风险"]),
    ("culture_media", "社会文化/符号/语言/传播", ["符号", "语言", "媒介", "舆论", "圈层"]),
    ("stories_debates", "故事/事件/争议/失败", ["事件", "经过", "结果", "争议", "版本差异"]),
    ("authority_sources", "学术/权威资料/文献出处", ["论文", "专著", "年报", "地方志", "数据库"]),
    ("latest_status", "最新动态/当前状态", ["当前年份", "近一年", "近90天", "来源状态"]),
    ("comparables", "同类对象/横向事实对照", ["同类对象", "差异", "事实对照", "来源"]),
    ("source_index", "来源索引/待核实清单", ["来源类型", "URL", "可信度", "冲突", "缺口"]),
]


VENUE_SUFFIXES = [
    "企业展厅",
    "企业馆",
    "文化馆",
    "博物馆",
    "纪念馆",
    "科学馆",
    "主题馆",
    "主题空间",
    "文旅馆",
    "展览馆",
    "展陈馆",
    "展厅",
    "展馆",
    "馆",
    "厅",
]


CONTENT_FIRST_DIMENSIONS = {
    "topic_boundary",
    "history_timeline",
    "people_network",
    "classification",
    "objects_archives",
    "mechanism_process",
    "scenes_practice",
    "data_market",
    "finance_recent",
    "policy_standards",
    "culture_media",
    "stories_debates",
    "authority_sources",
    "comparables",
}


PROFILE_CORES = {
    "A": [
        "主体身份与名称体系",
        "创始人/领导层/组织结构",
        "产品业务谱系",
        "技术能力与生产系统",
        "市场客户与产业链",
        "财经资本/上市IPO/融资/估值/收入",
        "监管诉讼/合规/风险",
        "最新动态/近一年/近90天",
        "同类企业事实对照",
        "来源索引与待核实清单",
    ],
    "B": [
        "主题边界与名称体系",
        "生平年谱",
        "家族师友与关系网络",
        "时代制度背景",
        "地理行旅与空间遗存",
        "作品文献/版本/注本",
        "实物馆藏/碑刻/图像档案",
        "思想风格与术语体系",
        "后世接受/传播/研究史",
        "当代保护/出版/数字化/纪念活动",
        "来源索引与待核实清单",
    ],
    "C": [
        "主题定义与边界",
        "历史源流与阶段变化",
        "分类谱系与子主题系统",
        "关键对象/工具/材料/作品/文本/影像",
        "行为流程/入门路径/进阶路径",
        "人物群体/社群组织/代表人物",
        "场景空间与日常实践",
        "产业消费/平台数据/品牌渠道",
        "社会文化/圈层语言/媒介传播",
        "政策安全/生态伦理/行业规范",
        "最新动态与当前状态",
        "来源索引与待核实清单",
    ],
    "D": [
        "主题定义与边界",
        "历史源流与时间线",
        "人物组织与关系网络",
        "分类谱系与子主题系统",
        "关键对象/载体/作品/档案",
        "机制流程与方法",
        "场景实践与使用方式",
        "数据规模与现状",
        "政策制度与风险伦理",
        "社会文化与传播",
        "最新动态与当前状态",
        "来源索引与待核实清单",
    ],
}


SOURCE_LADDERS = {
    "A": [
        "百度百科/维基百科/百科概览用于建立名称、别名、分类和术语入口",
        "官网/新闻室/产品文档/投资者关系页",
        "交易所/监管文件/招股书/年报/法院/专利/招标",
        "主流财经媒体/行业协会/产业数据库/咨询报告",
        "近一年/近90天/近30天新闻与监管进展",
    ],
    "B": [
        "百度百科/维基百科/百科概览用于建立人物、别名、时代和作品入口",
        "正史/地方志/年谱/文集/全集/别集/书信/奏议",
        "碑刻/谱牒/墓志/题跋/报刊/照片/影像/口述史",
        "博物馆/纪念馆/图书馆/档案馆公开馆藏",
        "文物图录/书画图录/考古或调查报告/论文/专著",
        "当代保护/出版整理/数字化公开/纪念活动/研究动态",
    ],
    "C": [
        "百度百科/维基百科/百科概览/入门手册/术语表/规则手册",
        "协会/俱乐部/平台社区/赛事活动/代表人物资料",
        "工具产品资料/行业报告/消费平台数据/安全规范",
        "主流媒体/社交平台/短视频平台/近年传播动态",
    ],
    "D": [
        "百度百科/维基百科/百科概览用于建立知识入口和术语地图",
        "官方/机构/学术/标准/数据库来源",
        "主流媒体/行业资料/专业社区/公开课程",
        "政策法规/统计数据/最新动态来源",
    ],
}


BASE_QUERY_TEMPLATES = {
    "topic_boundary": ["{topic} 是什么", "{topic} 百度百科", "{topic} 维基百科", "{topic} definition", "{topic} overview", "{topic} 术语 边界"],
    "history_timeline": ["{topic} history timeline", "{topic} 发展历程", "{topic} 大事记", "{topic} 起源 分期"],
    "geography_space": ["{topic} 地理 分布", "{topic} location map", "{topic} 重要地点", "{topic} 空间 遗址"],
    "people_network": ["{topic} 代表人物 组织", "{topic} biography", "{topic} 人物 关系", "{topic} 研究者"],
    "classification": ["{topic} 分类", "{topic} types classification", "{topic} taxonomy", "{topic} 子主题"],
    "objects_archives": ["{topic} 作品 文献 档案", "{topic} artifacts collection archives", "{topic} 馆藏 图录", "{topic} 实物 载体"],
    "mechanism_process": ["{topic} 原理 流程", "{topic} how it works", "{topic} 工艺 方法", "{topic} 操作 入门"],
    "scenes_practice": ["{topic} 场景 行为 用法", "{topic} practice beginner guide", "{topic} 日常实践", "{topic} 入门 进阶"],
    "data_market": ["{topic} 数据 规模", "{topic} market size statistics", "{topic} 产业链 消费", "{topic} 报告 数据"],
    "institutions": ["{topic} 官方 官网 机构", "{topic} organization official", "{topic} 主管机构", "{topic} 研究机构"],
    "finance_recent": ["{topic} IPO 上市 融资 估值", "{topic} funding valuation revenue", "{topic} 最新 商业动态", "{topic} {year} 资本"],
    "policy_standards": ["{topic} 政策 法规 标准", "{topic} regulation policy standard", "{topic} 监管 伦理 风险"],
    "culture_media": ["{topic} 文化 符号 传播", "{topic} media culture symbolism", "{topic} 圈层语言", "{topic} 舆论"],
    "stories_debates": ["{topic} 事件 争议", "{topic} controversy incident story", "{topic} 失败 案例", "{topic} 版本差异"],
    "authority_sources": ["{topic} 论文 专著 文献", "{topic} research paper book", "{topic} 数据库 来源", "{topic} 权威资料"],
    "latest_status": ["{topic} {year} 最新", "{topic} latest current status", "{topic} 近况 动态", "{topic} news {year}"],
    "comparables": ["{topic} 同类 对比", "{topic} comparison alternatives", "{topic} 同类对象", "{topic} 竞品 替代"],
    "source_index": ["{topic} 百度百科 维基百科", "{topic} source database", "{topic} 官方 数据库", "{topic} 文献目录", "{topic} 资料来源"],
}


TYPE_DIMENSION_QUERY_TEMPLATES = {
    "finance_recent": {
        "A": [
            "{subject} IPO 上市 融资 估值",
            "{subject} funding valuation revenue",
            "{subject} revenue contract backlog",
            "{subject} 最新 商业动态",
            "{subject} {year} 资本",
        ],
        "B": [
            "{subject} 当代保护 出版 数字化",
            "{subject} {year} 研究 出版 纪念",
            "{subject} 馆藏 数字资源 更新",
            "{subject} 教育 活动 公共传播",
        ],
        "C": [
            "{subject} 市场 消费 行业报告",
            "{subject} 品牌 渠道 平台 数据",
            "{subject} {year} 趋势 最新",
            "{subject} 活动 赛事 社群 动态",
        ],
        "D": [
            "{subject} {year} 最新 动态",
            "{subject} 当前状态 数据",
            "{subject} 项目 建设 研究 进展",
        ],
    },
    "institutions": {
        "B": [
            "{subject} 纪念馆 博物馆 文化馆",
            "{subject} 研究会 研究中心 学会",
            "{subject} 图书馆 档案馆 馆藏",
            "{project} 官方 官网 主管机构",
        ],
        "C": [
            "{subject} 协会 俱乐部 平台 社群",
            "{subject} 代表机构 组织 活动",
            "{project} 官方 官网 运营主体",
        ],
    },
    "comparables": {
        "A": [
            "{subject} 同类 企业 对比",
            "{subject} competitors comparison alternatives",
            "{subject} 竞品 替代 技术路线",
        ],
        "B": [
            "{subject} 同类 人物 对照",
            "{subject} 同时代 人物 比较",
            "{subject} 同类 文化主题 文献 对照",
            "{project} 同类 文化馆 博物馆",
        ],
        "C": [
            "{subject} 同类 主题 对照",
            "{subject} 相邻兴趣 社群 比较",
            "{subject} 同类 工具 行为 场景",
            "{project} 同类 主题馆 主题空间",
        ],
    },
}


TYPE_EXTRA_QUERIES = {
    "A": [
        ("finance_recent", "{topic} IPO OR initial public offering"),
        ("finance_recent", "{topic} funding round valuation investors"),
        ("finance_recent", "{topic} revenue contract backlog"),
        ("policy_standards", "site:sec.gov {topic}"),
        ("policy_standards", "{topic} lawsuit regulator license"),
    ],
    "B": [
        ("history_timeline", "{topic} 年谱"),
        ("history_timeline", "{topic} 生平 年表"),
        ("people_network", "{topic} 家族 师友 关系"),
        ("authority_sources", "{topic} 文集 全集 注本"),
        ("authority_sources", "{topic} 地方志 正史"),
        ("objects_archives", "{topic} 书画 馆藏 图录 碑刻"),
        ("latest_status", "{topic} {year} 研究 出版 数字化 纪念"),
    ],
    "C": [
        ("topic_boundary", "{topic} 入门 是什么"),
        ("classification", "{topic} 分类 术语 工具"),
        ("scenes_practice", "{topic} 新手 入门 教程 流程"),
        ("culture_media", "{topic} 社群 黑话 梗 传播"),
        ("data_market", "{topic} 消费 市场 行业报告"),
        ("latest_status", "{topic} {year} 趋势 最新"),
    ],
    "D": [
        ("topic_boundary", "{topic} 是什么 definition"),
        ("authority_sources", "{topic} 权威资料 论文 专著"),
        ("latest_status", "{topic} {year} 最新 动态"),
    ],
}


def normalize_type(raw):
    if not raw:
        return "D", TYPE_ALIASES["D"]
    value = raw.strip()
    label = TYPE_ALIASES.get(value)
    if not label:
        upper = value.upper()
        label = TYPE_ALIASES.get(upper, TYPE_ALIASES["D"])
    return TYPE_CODES[label], label


def clean_topic(topic):
    return re.sub(r"\s+", " ", topic.strip())


def derive_content_subject(topic):
    subject = clean_topic(topic)
    subject = re.sub(r"\s*(国际|中国|国内|全球|世界|新版|测试)$", "", subject).strip()
    for suffix in sorted(VENUE_SUFFIXES, key=len, reverse=True):
        if subject.endswith(suffix) and len(subject) > len(suffix):
            stripped = subject[:-len(suffix)].strip(" \t\r\n·-_/：:")
            if len(stripped) >= 2:
                return stripped
    return subject or clean_topic(topic)


def derive_subject_aliases(subject, type_code):
    aliases = [subject]
    if type_code == "C" and subject.endswith("佬") and len(subject) > 2:
        aliases.append(subject[:-1])
    return list(dict.fromkeys(alias for alias in aliases if alias))


def subjects_for_dimension(topic, subject, type_code, dim_id):
    subjects = derive_subject_aliases(subject, type_code)
    if subject != topic and type_code in ("B", "C") and dim_id in {
        "geography_space", "institutions", "source_index", "latest_status",
    }:
        subjects.append(topic)
    return list(dict.fromkeys(s for s in subjects if s))


def templates_for_dimension(type_code, dim_id):
    by_type = TYPE_DIMENSION_QUERY_TEMPLATES.get(dim_id)
    if by_type and type_code in by_type:
        return list(by_type[type_code])
    return list(BASE_QUERY_TEMPLATES[dim_id])


def build_queries(topic, type_code, year):
    groups = []
    extras = {}
    for dim_id, query in TYPE_EXTRA_QUERIES.get(type_code, []):
        extras.setdefault(dim_id, []).append(query)
    subject = derive_content_subject(topic)
    for dim_id, name, fields in DIMENSIONS:
        templates = templates_for_dimension(type_code, dim_id) + extras.get(dim_id, [])
        queries = []
        seen = set()
        for query_subject in subjects_for_dimension(topic, subject, type_code, dim_id):
            for template in templates:
                q = template.format(
                    topic=query_subject,
                    subject=query_subject,
                    project=topic,
                    year=year,
                ).strip()
                if q in seen:
                    continue
                seen.add(q)
                queries.append({
                    "query": q,
                    "intent": name,
                    "freshness": "latest" if dim_id in ("latest_status", "finance_recent") else "evergreen_or_historical",
                    "must_extract": fields,
                    "query_subject": query_subject,
                    "project_title": topic,
                })
        groups.append({
            "dimension_id": dim_id,
            "dimension": name,
            "evidence_fields": fields,
            "queries": queries,
        })
    return groups


def build_plan(topic, project_type, region, date=None):
    today = date or datetime.date.today().isoformat()
    year = today[:4]
    type_code, type_label = normalize_type(project_type)
    topic = clean_topic(topic)
    content_subject = derive_content_subject(topic)
    return {
        "schema_version": "1.0",
        "topic": topic,
        "project_type": {
            "code": type_code,
            "label": type_label,
            "raw": project_type,
        },
        "region": region,
        "generated_at": today,
        "research_contract": {
            "final_output": "xmind_only",
            "knowledge_system_first": True,
            "evidence_calibration": True,
            "model_explanation_layer": True,
            "evidence_first": False,
            "no_curation_suggestions": True,
            "no_placeholders_in_outline": True,
            "manual_official_sources": True,
            "encyclopedia_entry_sources": ["百度百科", "维基百科", "百科概览"],
            "notes_in_xmind": 0,
        },
        "theme_profile": {
            "project_title": topic,
            "content_subject": content_subject,
            "subject_aliases": derive_subject_aliases(content_subject, type_code),
            "subject_rule": "先剥离馆/展厅/主题空间等项目外壳,优先检索主题本体;机构类分支再补项目本身。",
            "required_cores": PROFILE_CORES[type_code],
            "source_ladder": SOURCE_LADDERS[type_code],
            "freshness_rule": "近一年/近90天必查" if type_code == "A" else "按主题查最新研究、保护、出版、传播或行业动态",
        },
        "query_groups": build_queries(topic, type_code, year),
        "coverage_thresholds": {
            "min_total_sources": 30,
            "min_authority_sources": 8,
            "min_sources_per_required_core": 2,
            "min_evidence_cards_per_required_core": 5,
            "min_factual_fields_per_required_core": 3,
            "min_evidence_fields_per_important_concept": 5,
            "outline_min_depth": 7,
            "outline_min_nodes": 400,
            "thick_topic_target_nodes": 600,
            "placeholder_hits_allowed": 0,
            "notes_allowed": 0,
        },
        "handoff_files": {
            "research_plan": "01_检索计划/research_plan.json",
            "search_results": "02_搜索结果/search_results.jsonl",
            "sources": "03_来源文本/sources.jsonl",
            "evidence_cards": "04_证据卡/evidence_cards.jsonl",
            "coverage_report": "05_覆盖审计/coverage_audit.json",
            "outline": "06_提炼笔记/调研大纲.md",
            "outline_audit": "06_提炼笔记/outline_audit.json",
            "xmind_audit": "07_产出/xmind_audit.json",
        },
    }


def main():
    ap = argparse.ArgumentParser(description="生成策展前期资料调研检索计划")
    ap.add_argument("--topic", required=True, help="调研主题")
    ap.add_argument("--type", default="D", help="A/B/C/D 或中文类型")
    ap.add_argument("--region", required=True, help="地域范围:中国/国际/特定地区")
    ap.add_argument("--out", help="输出 research_plan.json 路径;不填则输出 stdout")
    ap.add_argument("--date", help="生成日期 YYYY-MM-DD;默认今天")
    ap.add_argument("--print-queries", action="store_true", help="同时在 stderr 输出查询式清单")
    args = ap.parse_args()

    plan = build_plan(args.topic, args.type, args.region, args.date)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("已生成检索计划: %s" % args.out)
    else:
        print(text)

    if args.print_queries:
        for group in plan["query_groups"]:
            print("\n[%s]" % group["dimension"], file=sys.stderr)
            for q in group["queries"]:
                print("- " + q["query"], file=sys.stderr)


if __name__ == "__main__":
    main()
