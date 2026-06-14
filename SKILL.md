---
name: curation-research
description: 策展前期资料获取助手。用于策展/展览/展厅/主题馆/企业馆/博物馆/文化馆/文旅馆的前期资料调研、主题资料收集、甲方文档解读、公开资料整理,最终生成可用 XMind 打开的超详细资料型思维导图(.xmind);用户明确要求报告、Word、docx 或完整交付时也适用。
---

# 策展前期资料获取助手

这是一个**知识系统建模 + 证据校准**工具。输入甲方需求文档或一个主题词,默认交付一份**可用 XMind 打开的超详细资料型思维导图**(`.xmind`)。

用户明确要求“报告 / Word / docx / 完整交付 / 文本报告”时,可在 `.xmind` 之外追加一份**资料报告型 Word**(`.docx`)。Word 仍然只做资料整理,不写策展方案,不输出展示形式、展项建议、空间表达、核心张力或策展主题。

归档目录、搜索结果、来源文本、证据卡、Markdown 大纲和报告 Markdown 都是工作中间件;最终交付物默认只有 `.xmind`,完整交付模式为 `.xmind + .docx`。

**触发后,先原样输出开场白(一字不差):**

> 你好,我是策展调研小助理。我来帮你做策展前期调研。

## 核心机制:知识系统先行,证据校准托底

旧失败模式有三类:

- 内容被压缩成短词或一句话定义。
- 把“需要补”“正式使用时要”这类内部检查句写进导图。
- 为了追求来源完美而把输出做成碎片来源账本,丢掉大模型本身可以提供的系统解释、概念关系和顺畅表达。

新流程必须按顺序经过,但最终导图不是证据卡流水账:

1. `research_plan.py` 生成可审计检索计划。
2. `search_collect.py` 搜索或导出查询任务。
3. `fetch_sources.py` 合规获取普通公开网页;政府、监管、法院、交易所、官方数据库、robots 禁止或反爬页面只生成 `manual_required` 记录。
4. 对 `manual_required` 来源使用浏览器/人工读取,再用 `manual_source_note.py` 记录摘录。
5. `evidence_cards.py` 校验证据卡。
6. `coverage_audit.py` 审计必查核心是否有证据。
7. `research_loop.py` 根据覆盖缺口生成二轮/三轮深搜补搜计划。
8. 用模型解释层把主题组织成知识系统:定义、边界、分类、机制、场景、数据、历史、人物、术语、误区和关联关系。
9. 新增硬事实必须回到补搜与证据卡;模型知识可用于解释、结构和衔接,不能冒充来源。
10. 用 `outline_from_evidence.py` 生成或辅助生成 `06_提炼笔记/调研大纲.md`,再由模型按知识系统补厚。
11. `outline_audit.py` 审计大纲。
12. `md_to_xmind.py` 生成 `.xmind`。
13. `xmind_audit.py` 审计最终 `.xmind`。
14. 完整交付模式下,用 `report_from_evidence.py` 生成报告 Markdown,用 `report_audit.py` 审计,再用 `report_to_docx.py` 生成 `.docx`。

**没有知识骨架、来源记录、证据卡和覆盖审计,不得写正式大纲。大纲审计失败,不得生成最终 XMind。**

## 关键原则

- **默认只交 XMind**:最终回复只给 `.xmind` 绝对路径和简短验证结果。
- **完整交付可交 Word**:只有用户明确要求报告、Word、docx 或完整交付时,才追加 `.docx`。Word 是资料报告,不是策展方案。
- **只做资料,不做策展判断**:只写是什么、何时、何地、谁、数据多少、来源在哪、是否有争议;不写后续怎么展示。
- **知识系统优先**:导图首先要像一套给小白也能读懂的知识地图,而不是来源摘录账本。证据卡是校准事实的原料,不是最终层级的形状。
- **百科入口必须查**:百度百科、维基百科和同类百科概览优先用于建立名称、别名、上下位关系、术语地图和常识框架;不能把百科当唯一证据,但也不能绕开百科只抓碎片网页。
- **允许模型解释,不允许模型造事实**:大模型可以把证据讲清楚、拆层级、写衔接、解释概念机制、补出概念之间的关系;但时间、人物、地点、数据、政策、来源和最新动态必须由证据卡支撑。模型提出的新增硬事实只能进入补搜任务或待核实清单。
- **内容密度优先**:节点数不是成功标准。每个重要概念要有定义、边界、分类、组成、机制、场景、时间、数据、人物/组织、来源、争议等多个展开面。
- **把用户当完全不懂**:重要概念必须先讲“是什么”,再讲“不是什么”,然后拆到小白能跟上的层级。
- **不使用备注承载资料**:默认备注数必须为 0。所有解释、事实、数据、来源都写成可见子节点。
- **不压缩资料**:禁止 `概念  >  一句话解释`。能下钻就下钻,不要把解释塞到同一行。
- **禁止占位句**:导图不得出现“正式使用时要”“需要继续”“需要补”“需要绑定”“需要保留”“不能只作为短词存在”“可提供或需要补充”“待补”等任务句。
- **禁止方法标签伪内容**:导图不得出现“继续下钻方向”“下钻方式”“关联资料面”“概念资料卡”“来源类型为”“可信度标注为”等模板痕迹。要直接写事实、时间、人物、数据、来源和争议。
- **禁止策展污染**:不得出现展项、展示形式、空间表达、互动装置、展线、核心张力、独特价值、可借鉴点、观众体验建议。
- **Word 必须是连续报告**:Word 不能是 XMind 节点拷贝,也不能是证据卡列表。它要有章节、导言、连续段落、来源口径和待核实问题,语言要像正式中文资料报告。
- **合规获取来源**:普通公开网页可用 `fetch_sources.py`;政府、监管、法院、交易所、官方数据库、robots 禁止、反爬或访问限制页面不得用爬虫抓取,只能浏览器/人工阅读后用 `manual_source_note.py` 摘录。
- **不暴露真实项目案例**:skill 文件、模板、示例只使用通用表述,不要写入真实项目名、客户名、测试案例名或私有路径。
- **搜新是硬要求**:现代企业、产业、科技、政策、消费和人物主题必须查近一年、近 90 天;历史文化类也要查最新研究、出版、保护、数字化和公共传播动态。

## 深度红线

正式结果必须满足:

- 第一分支固定为「主题解读」。
- 最大层级 ≥ 7。
- 节点 ≥ 400;厚重主题目标 ≥ 600。
- 备注节点 = 0。
- `outline_audit.py` 与 `xmind_audit.py` 均通过。
- 重要概念至少覆盖 5 个展开面。
- 每个一级分支至少能支撑后续策展大纲的 2-3 个资料小节。
- A 类必须有上市/IPO、融资/估值、收入/订单、监管/诉讼、近一年/近 90 天动态。
- B 类必须有生平年谱、文献/档案/实物证据、作品或对象系统、研究/保护/出版/数字化动态。
- C 类必须先研究主题本体,再谈目的地或运营项目。
- 完整交付模式的 Word 报告字符数 ≥ 6000,标题层级 ≥ 8,段落数 ≥ 20,并通过 `report_audit.py`。

不达标就回到搜索、抓取、证据卡和覆盖审计阶段。

## 路径约定

下文 `<skill>` 指本 skill 目录。所有脚本均为 Python 标准库,用 `python3` 直接运行。

必须读取:

- `references/research-method.md`:证据管线与质量红线。
- `references/search-dimensions.md`:检索维度、查询矩阵、来源硬清单。
- `references/mindmap-frameworks.md`:统一导图母骨架与概念展开范式。
- Word 报告使用同一批证据卡生成,不得绕开证据体系另写一套无来源文本。

## 流程

### Step 0 - 确认主题、类型、地域

问清:

- 项目类型:A 企业/机构/品牌 / B 博物馆·文化馆·历史文化 / C 文旅·主题馆·主题空间 / D 其他主题。
- 主题词或甲方需求文档路径。
- 地域范围:国内中国 / 国际 / 特定地区。

用户没说地域范围时必须追问。若主题涉及现代企业、机构、政策、财经、科技、人物、消费或新闻,默认需要最新资料轮次。

### Step 1 - 建工作归档目录

```bash
python3 "<skill>/scripts/archive_init.py" --name "项目名称" --type "A/B/C/D" --prefix X --out .
```

生成目录后,后续所有中间文件都放在该目录内。

### Step 2 - 索取或提取基础资料

建好目录后问:

> 你有没有这个项目的背景资料(需求文档、甲方介绍、PDF/PPT/Word)或相关网站(官网、专题页)?
> 有的话,把文件放进 `00_需求文档/` 文件夹,或把网址发我;没有也没关系,我直接开始调研。

有资料时:

```bash
python3 "<skill>/scripts/extract_doc.py" "00_需求文档/方案.pdf" -o "00_需求文档/需求原文.txt"
```

用户资料是第一手线索,必须进入证据体系并标注来源。

### Step 3 - 生成检索计划

```bash
python3 "<skill>/scripts/research_plan.py" \
  --topic "主题" \
  --type "A/B/C/D" \
  --region "中国/国际/特定地区" \
  --out "01_检索计划/research_plan.json" \
  --print-queries
```

执行后先阅读 `research_plan.json`,确认:

- `theme_profile.content_subject` 已经剥离“馆/展厅/主题空间”等项目外壳;如主题是“某某文化馆”,主体资料应优先搜索“某某”而不是只搜“某某文化馆”。
- `theme_profile.required_cores` 中有该类型的硬核资料项。
- A 类有财经资本/上市/融资/估值/收入。
- B 类有生平年谱、作品文献、馆藏档案、当代保护/出版/数字化。
- C 类有主题本体的定义、历史、分类、工具/对象、行为、社群、产业、政策和最新动态。

### Step 4 - 搜索或导出查询任务

优先使用脚本搜索。支持 `BRAVE_API_KEY`、`SERPER_API_KEY`、`BING_SEARCH_KEY`。

```bash
python3 "<skill>/scripts/search_collect.py" \
  --plan "01_检索计划/research_plan.json" \
  --out "02_搜索结果/search_results.jsonl"
```

若没有 API key,脚本会输出 `query_task`。这只代表“应搜什么”,不代表“已经搜到资料”。此时必须用可用的搜索工具逐项搜索,并把真实 URL/标题/摘要整理成 `02_搜索结果/search_results.jsonl` 或直接进入 `03_来源文本/sources.jsonl`。

### Step 5 - 合规获取来源

```bash
python3 "<skill>/scripts/fetch_sources.py" \
  --search-results "02_搜索结果/search_results.jsonl" \
  --out "03_来源文本/sources.jsonl"
```

`fetch_sources.py` 只处理允许自动访问的普通公开网页,并尊重 robots.txt。不绕过登录、付费、反爬或非公开系统。

遇到以下来源,脚本会写出 `manual_required` 记录,不得改脚本强行抓取:

- 政府、监管、法院、交易所、官方数据库。
- robots.txt 不允许抓取的页面。
- 有明显反爬、登录、付费、验证码或访问控制的页面。

这些来源仍然可以作为权威资料使用,但必须用浏览器/人工读取后记录摘录:

```bash
python3 "<skill>/scripts/manual_source_note.py" \
  --out "03_来源文本/sources.jsonl" \
  --append \
  --url "公开页面 URL" \
  --title "来源标题" \
  --excerpt "人工阅读后整理的必要摘录" \
  --source-type government
```

`manual_source_note.py` 不访问网络,只把已经人工读取的公开信息写入 `sources.jsonl`。摘录要少量、必要、可支撑证据卡,不要整篇复制。

### Step 6 - 抽取证据卡

可先生成抽取种子:

```bash
python3 "<skill>/scripts/evidence_cards.py" seed \
  --sources "03_来源文本/sources.jsonl" \
  --topic "主题" \
  --out "04_证据卡/evidence_seed.jsonl"
```

然后阅读 `03_来源文本/sources.jsonl` / `04_证据卡/evidence_seed.jsonl`,写成 `04_证据卡/evidence_cards.jsonl`。每条证据卡必须至少包含:

```json
{
  "claim": "完整、可核验的事实陈述",
  "core": "对应 research_plan.required_cores 中的核心项",
  "dimension": "对应搜索维度",
  "time": "时间或年代",
  "people": ["相关人物"],
  "places": ["相关地点"],
  "objects": ["作品/器物/事件/机构/产品"],
  "data": ["数字、金额、规模、参数或口径"],
  "source_title": "来源标题",
  "source_url": "来源 URL 或用户资料文件名",
  "source_type": "government/academic/institution_or_database/media/web...",
  "confidence": "官方确认/监管文件/学术资料/机构资料/媒体报道/行业资料/分析师估算/单一来源/待核实"
}
```

`time`、`people`、`places`、`objects`、`data` 这 5 个细节字段中,每条证据卡至少填实 2 个;不要用“不详”“待补”“正式使用时要”等占位词凑字段。

鼓励在证据卡中补充可选解释字段,供导图和 Word 写得更厚:

```json
{
  "explanation": "给完全不懂的人看的解释",
  "mechanism": "它为什么这样运作或形成",
  "boundary": "它不是什么,与相似概念的区别",
  "misconception": "常见误区",
  "teaching_points": ["可用于讲清概念的要点"]
}
```

这些解释字段可以来自模型知识和来源综合,但不能替代 `claim` 中的可核验硬事实。

校验证据卡:

```bash
python3 "<skill>/scripts/evidence_cards.py" validate \
  "04_证据卡/evidence_cards.jsonl" \
  --json "04_证据卡/evidence_cards_validate.json"
```

校验失败不得进入下一步。

### Step 7 - 覆盖审计

```bash
python3 "<skill>/scripts/coverage_audit.py" \
  --plan "01_检索计划/research_plan.json" \
  --evidence "04_证据卡/evidence_cards.jsonl" \
  --json "05_覆盖审计/coverage_audit.json"
```

只要有必查核心证据不足,不得直接写大纲,也不得用“需要补”占位。必须先生成深搜补搜计划:

```bash
python3 "<skill>/scripts/research_loop.py" \
  --plan "01_检索计划/research_plan.json" \
  --coverage "05_覆盖审计/coverage_audit.json" \
  --evidence "04_证据卡/evidence_cards.jsonl" \
  --out "01_检索计划/research_loop.json" \
  --breadth 4 \
  --depth 2
```

阅读 `research_loop.json`,逐条执行其中的 `queries`。每条查询都有:

- `research_goal`:本轮要补哪一个必查核心,为什么补。
- `expected_evidence_fields`:搜索后必须抽取哪些事实字段。
- `stop_condition`:什么时候可以停止该核心补搜。
- `parent_query`、`iteration`、`depth_remaining`:用于记录深搜轮次。
- `visited_urls`:已进入证据卡的 URL,补搜时避免重复当作新增来源。

补搜后回到 Step 4-7,更新 `search_results.jsonl`、`sources.jsonl`、`evidence_cards.jsonl` 和 `coverage_audit.json`。覆盖审计通过后才能进入下一步。

### Step 7.5 - 模型解释层补厚

覆盖审计通过后,可以使用大模型对证据卡做解释性展开,但必须遵守:

- 可以补:概念定义的小白解释、分类之间的差异、工具工作方式、行为流程、术语关系、上下位概念、段落衔接、章节标题、报告文气。
- 可以提:可能遗漏的别名、术语、人名、政策名、数据口径和后续查询方向。
- 不可以直接补:具体年份、人物关系、地点、政策条款、市场数字、赛事时间、最新新闻、来源标题或 URL。
- 若模型提出新事实,先进入 `research_loop.json` 或待核实清单,搜索验证后再进入证据卡。
- 进入最终 XMind 或 Word 的确定性事实必须能回到 `evidence_cards.jsonl`。
- 百科、教材、综述、入门手册提供知识框架;官方、学术、监管、数据库和主流媒体提供硬事实校准。两者缺一不可。

### Step 8 - 组织知识型导图大纲

只有覆盖审计通过后,才写:

```text
06_提炼笔记/调研大纲.md
```

优先用证据卡生成自然中文大纲底稿:

```bash
python3 "<skill>/scripts/outline_from_evidence.py" \
  --plan "01_检索计划/research_plan.json" \
  --evidence "04_证据卡/evidence_cards.jsonl" \
  --out "06_提炼笔记/调研大纲.md" \
  --title "主题" \
  --type "A/B/C/D"
```

要求:

- 第一分支固定为「主题解读」。
- 使用 `references/mindmap-frameworks.md` 的统一母骨架。
- 每个重要概念按“是什么 / 不是什么 / 怎么分 / 怎么工作 / 怎么用 / 有哪些数据 / 有哪些例子 / 来源如何托底”的知识结构展开。
- 证据卡中的事实、数据、来源和不确定性要转成可见子节点,但来源节点不能压过知识阅读主线。
- 资料缺口只能写成具体缺口:已查哪些来源,缺少什么证据。不能写成内部待办。
- 导图节点也要使用自然中文,不要出现“时间口径为”“相关人物包括”“来源类型为”“可信度标注为”等字段腔。

### Step 9 - 大纲审计

```bash
python3 "<skill>/scripts/outline_audit.py" \
  "06_提炼笔记/调研大纲.md" \
  --type "A/B/C/D" \
  --plan "01_检索计划/research_plan.json" \
  --json "06_提炼笔记/outline_audit.json"
```

审计失败时,按错误类型回到对应阶段:

- 占位句、短叶子、压缩写法:重写大纲或继续下钻证据。
- 方法标签伪内容:删除模板词,改写为具体资料事实。
- 缺少核心词:回到检索计划和覆盖审计。
- 策展污染:删除方案语言,改成事实资料。
- 备注行:改成可见子节点。

### Step 10 - 生成 XMind

```bash
python3 "<skill>/scripts/md_to_xmind.py" \
  "06_提炼笔记/调研大纲.md" \
  -o "07_产出/调研导图.xmind"
```

### Step 11 - XMind 审计

```bash
python3 "<skill>/scripts/xmind_audit.py" \
  "07_产出/调研导图.xmind" \
  --json "07_产出/xmind_audit.json"
```

审计失败不得交付。

### Step 12 - 完整交付模式:生成 Word 资料报告

只有用户明确要求报告、Word、docx 或完整交付时执行。

先生成报告 Markdown:

```bash
python3 "<skill>/scripts/report_from_evidence.py" \
  --plan "01_检索计划/research_plan.json" \
  --evidence "04_证据卡/evidence_cards.jsonl" \
  --out "07_产出/资料调研报告.md"
```

报告写作要求:

- 参考策展大纲的层级感:总述、主题边界、历史/时间线、对象系统、人物组织、机制/制度、地理空间、数据市场、监管争议、同类对照、来源索引。
- 句子和段落要流畅,有长短句变化,不能是一个个短句或证据卡堆叠。
- 每章先说明“本章回答什么”,再把证据卡转成连续段落。
- 证据卡字段必须转写成报告语言,不得把“时间口径为”“相关人物包括”“涉及对象包括”“数据口径包括”“这些信息分别见于”直接写进正文。
- 小节标题要像正式报告标题,例如“姓名、身份与主题界定”“早年教育与科举入仕”,不要写成“资料综述”“基本情况”。
- 来源引用要自然收束,优先写“以上信息综合参考:来源 A、来源 B。”不要把可信度字段机械塞进每个事实句。
- 数据必须写清年份、单位、口径和来源性质。
- 来源章节必须说明来源用途和可信度边界。
- 不写展项、展示形式、空间表达、策展主题或观众体验建议。

审计报告:

```bash
python3 "<skill>/scripts/report_audit.py" \
  "07_产出/资料调研报告.md" \
  --json "07_产出/report_audit.json"
```

审计通过后生成 Word:

```bash
python3 "<skill>/scripts/report_to_docx.py" \
  "07_产出/资料调研报告.md" \
  -o "07_产出/资料调研报告.docx"
```

报告审计失败不得交付 Word;必须回到证据卡或报告 Markdown 改写。

### Step 13 - 最终回复

最终只告诉用户:

- `.xmind` 绝对路径。
- 完整交付模式下追加 `.docx` 绝对路径。
- 简短验证结果:节点数、最大层级、备注数、第一分支、占位句/方法标签/策展污染检查是否通过;如果生成 Word,同时给报告字符数、标题数、段落数和审计是否通过。

不要把资料笔记、大段目录或报告全文当最终成果贴出来。

## 脚本速查

| 脚本 | 作用 |
| --- | --- |
| `archive_init.py` | 建树形资料归档目录 |
| `extract_doc.py` | PDF/PPT/Word/TXT/MD 转文本 |
| `research_plan.py` | 生成检索计划、必查核心和查询矩阵 |
| `search_collect.py` | 调用搜索 API 或导出查询任务 |
| `fetch_sources.py` | 合规获取普通公开网页;官方/监管等受限来源转人工记录 |
| `manual_source_note.py` | 记录浏览器/人工读取的公开来源摘录,不访问网络 |
| `evidence_cards.py` | 生成证据抽取种子、校验证据卡 |
| `coverage_audit.py` | 审计必查核心是否有足够证据和来源 |
| `research_loop.py` | 根据覆盖缺口生成带 research_goal 的多轮深搜补搜任务 |
| `outline_from_evidence.py` | 从证据卡生成自然中文导图大纲 |
| `outline_audit.py` | 审计 Markdown 大纲是否含占位句、备注、压缩、策展污染 |
| `md_to_xmind.py` | 缩进 Markdown 转 `.xmind` |
| `xmind_audit.py` | 审计最终 `.xmind` |
| `report_from_evidence.py` | 从证据卡生成资料报告 Markdown |
| `report_audit.py` | 审计资料报告是否像连续报告而非短句清单 |
| `report_to_docx.py` | 资料报告 Markdown 转 `.docx` |

## Gotchas

- `query_task` 不是资料来源,不能进入覆盖审计。
- `evidence_seed.jsonl` 不是证据卡,必须抽取成 `evidence_cards.jsonl`。
- `coverage_audit.py` 失败时不要写大纲。
- `outline_audit.py` 失败时不要生成 XMind。
- `xmind_audit.py` 失败时不要交付。
- `report_audit.py` 失败时不要交付 Word。
- `.xmind` 是 zip 包,含 `content.json`、`manifest.json`、`metadata.json`。
- `.docx` 由标准 Office Open XML zip 包生成,可用 Word/WPS 打开。
