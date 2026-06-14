# 资料归档与证据卡模板

本模板用于中间归档,不是最终交付物。最终只交 `.xmind`。

正式调研不要只写“维度笔记”,而要形成可审计材料链:

1. `research_plan.json`
2. `search_results.jsonl`
3. `sources.jsonl`
4. `evidence_cards.jsonl`
5. `coverage_audit.json`
6. `调研大纲.md`
7. `调研导图.xmind`

## 来源摘录文件

如果需要人工整理某个来源,用以下结构:

```markdown
# <来源标题>

- 来源类型:<official / government / academic / institution_or_database / media / industry / web / user_document>
- URL 或文件名:<来源地址或用户文件名>
- 发布日期:<YYYY-MM-DD 或 未注明>
- 抓取日期:<YYYY-MM-DD>
- 对应检索维度:<research_plan.query_groups.dimension>
- 来源可信度:<官方确认 / 监管文件 / 学术资料 / 机构资料 / 媒体报道 / 行业资料 / 单一来源 / 待核实>

## 可抽取事实

- <完整事实 1:谁、何时、何地、发生什么、数据多少、来源依据>
- <完整事实 2>

## 原文摘录

<少量必要摘录或自己的概括;不要整篇复制。>

## 待核实点

- <如果来源单一或口径不清,写清缺什么证据>
```

## 证据卡 JSONL 模板

`evidence_cards.jsonl` 一行一条 JSON:

```json
{"claim":"完整、可核验的事实陈述","core":"对应 research_plan.required_cores 中的核心项","dimension":"对应搜索维度","time":"时间或年代","people":["相关人物"],"places":["相关地点"],"objects":["作品/器物/事件/机构/产品"],"data":["数字、金额、规模、参数或口径"],"source_title":"来源标题","source_url":"来源 URL 或用户资料文件名","source_type":"government/academic/institution_or_database/media/web","confidence":"官方确认/监管文件/学术资料/机构资料/媒体报道/行业资料/分析师估算/单一来源/待核实"}
```

要求:

- `claim` 不能是短词,必须是一条完整事实。
- `core` 必须能对应检索计划中的必查核心。
- 数字必须有年份、单位、口径和来源。
- 历史年代、作品版本、馆藏信息、融资估值、上市传闻等必须标注来源状态。
- 单一来源或冲突来源不能写成确定事实。
- 不能把“需要补”“待补”“正式使用时要”写进证据卡或导图。
