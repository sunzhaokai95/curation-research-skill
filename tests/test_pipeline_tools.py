#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"


class PipelineToolsTest(unittest.TestCase):
    def run_script(self, name, *args, input_text=None):
        cmd = [sys.executable, str(SCRIPTS / name), *args]
        return subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_historical_plan_requires_life_chronology(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "plan.json"
            res = self.run_script(
                "research_plan.py",
                "--topic", "苏东坡文化馆",
                "--type", "B",
                "--region", "中国",
                "--out", str(out),
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["theme_profile"]["content_subject"], "苏东坡")
            cores = "\n".join(data["theme_profile"]["required_cores"])
            queries = "\n".join(
                q["query"] for group in data["query_groups"] for q in group["queries"]
            )
            self.assertIn("生平年谱", cores)
            self.assertIn("苏东坡 年谱", queries)
            self.assertIn("作品文献", cores)
            self.assertNotIn("IPO", queries)

    def test_outline_audit_rejects_placeholders_notes_inline_compression_and_method_labels(self):
        bad_outline = """# 测试
- 主题解读
  - 地域范围
    - 中国
- 分类谱系与子主题系统
  - 生平年谱系统
    - 出生家学 是 生平年谱系统 下的资料子项,不能只作为短词存在。
    > 正式使用时要关联时间、人物、地点、作品、来源或版本差异。
  - 硬体饵  > 硬质材料制成。
  - 继续下钻方向
    - 关联资料面
  - 时间口径为1037年
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.md"
            path.write_text(bad_outline, encoding="utf-8")
            res = self.run_script("outline_audit.py", str(path), "--type", "B")
            combined = res.stdout + res.stderr
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("占位", combined)
            self.assertIn("备注", combined)
            self.assertIn("压缩", combined)
            self.assertIn("方法标签", combined)
            self.assertIn("字段腔", combined)

    def test_outline_from_evidence_generates_natural_xmind_outline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan = {
                "topic": "苏东坡文化馆",
                "region": "中国",
                "project_type": {"code": "B", "label": "博物馆/文化馆/历史文化"},
                "theme_profile": {
                    "content_subject": "苏东坡",
                    "subject_aliases": ["苏轼", "苏东坡"],
                    "required_cores": ["主题边界与名称体系", "生平年谱"],
                    "source_ladder": ["正史/年谱/文集", "博物馆公开馆藏"],
                    "freshness_rule": "查最新出版、保护和数字化资料",
                },
            }
            cards = [
                {
                    "claim": "苏轼是北宋眉州眉山人，名轼，字子瞻，又字和仲，号东坡居士。",
                    "core": "主题边界与名称体系",
                    "dimension": "主题边界/基础定义",
                    "time": "1037-1101年",
                    "people": ["苏轼"],
                    "places": ["眉州眉山"],
                    "objects": ["姓名", "字", "号"],
                    "data": ["生卒年1037-1101"],
                    "source_title": "苏轼 - 维基百科，自由的百科全书",
                    "source_url": "https://example.com/sushi",
                    "source_type": "web",
                    "confidence": "单一来源",
                },
                {
                    "claim": "嘉祐二年苏轼参加礼部考试，欧阳修读《刑赏忠厚论》后对其文章大为赞赏。",
                    "core": "生平年谱",
                    "dimension": "时间历史/发展阶段",
                    "time": "1057年",
                    "people": ["苏轼", "欧阳修"],
                    "places": ["开封"],
                    "objects": ["礼部考试", "刑赏忠厚论"],
                    "data": ["嘉祐二年"],
                    "source_title": "宋史/卷338 - 维基文库，自由的图书馆",
                    "source_url": "https://example.com/songshi",
                    "source_type": "academic",
                    "confidence": "学术资料",
                },
            ]
            plan_path = tmp_path / "plan.json"
            evidence_path = tmp_path / "evidence.jsonl"
            outline_path = tmp_path / "outline.md"
            xmind_path = tmp_path / "outline.xmind"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n", encoding="utf-8")

            res = self.run_script(
                "outline_from_evidence.py",
                "--plan", str(plan_path),
                "--evidence", str(evidence_path),
                "--out", str(outline_path),
                "--type", "B",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            text = outline_path.read_text(encoding="utf-8")
            self.assertIn("主题解读", text)
            self.assertIn("姓名、身份与主题界定", text)
            self.assertIn("知识解释", text)
            self.assertIn("证据托底", text)
            self.assertIn("资料性质:公开网页资料", text)
            self.assertNotIn("事实1", text)
            self.assertNotIn("基本事实", text)
            self.assertNotIn("知识点1", text)
            self.assertNotIn("时间口径为", text)
            self.assertNotIn("来源类型为", text)

            res = self.run_script(
                "outline_audit.py",
                str(outline_path),
                "--type", "B",
                "--plan", str(plan_path),
                "--min-nodes", "20",
                "--min-depth", "7",
                "--warn-short-leaves",
                "--skip-required-terms",
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

            res = self.run_script("md_to_xmind.py", str(outline_path), "-o", str(xmind_path))
            self.assertEqual(res.returncode, 0, res.stderr)
            res = self.run_script(
                "xmind_audit.py",
                str(xmind_path),
                "--min-nodes", "20",
                "--min-depth", "7",
                "--warn-short-leaves",
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_fetch_sources_marks_government_sources_as_manual_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            search_path = tmp_path / "search_results.jsonl"
            out_path = tmp_path / "sources.jsonl"
            search_path.write_text(json.dumps({
                "kind": "search_result",
                "query": "测试 政府 公告",
                "dimension_id": "policy_standards",
                "dimension": "政策/法规/制度/监管/伦理",
                "title": "政府公开资料测试",
                "url": "https://www.gov.cn/test/public-page.html",
                "snippet": "用于测试官方来源人工读取边界。",
                "date": "2026-06-14",
            }, ensure_ascii=False) + "\n", encoding="utf-8")

            res = self.run_script(
                "fetch_sources.py",
                "--search-results", str(search_path),
                "--out", str(out_path),
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "manual_required")
            self.assertIn("不使用爬虫抓取", rows[0]["reason"])
            self.assertIn("manual_source_note.py", rows[0]["next_step"])

    def test_manual_source_note_records_browser_excerpt_without_network_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "sources.jsonl"
            excerpt = "这是一段人工通过浏览器读取后整理的公开来源摘录,包含足够长度,用于后续抽取证据卡。"
            res = self.run_script(
                "manual_source_note.py",
                "--out", str(out_path),
                "--url", "https://www.gov.cn/test/public-page.html",
                "--title", "政府公开资料测试",
                "--excerpt", excerpt,
                "--source-type", "government",
                "--dimension", "政策/法规/制度/监管/伦理",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            row = json.loads(out_path.read_text(encoding="utf-8").strip())
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["capture_method"], "manual_or_browser")
            self.assertEqual(row["source_type"], "government")
            self.assertEqual(row["text"], excerpt)
            self.assertIn("脚本未抓取该 URL", row["compliance_note"])

    def test_evidence_validation_rejects_placeholders_and_thin_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            rows = [
                {
                    "claim": "正式使用时要关联时间、人物、地点、作品、来源或版本差异,这不是可核验资料。",
                    "core": "生平年谱",
                    "dimension": "时间历史/发展阶段",
                    "time": "1037年",
                    "people": ["苏轼"],
                    "places": [],
                    "objects": [],
                    "data": [],
                    "source_title": "测试来源",
                    "source_url": "https://example.com/source",
                    "source_type": "academic",
                    "confidence": "学术资料",
                },
                {
                    "claim": "苏轼生平资料需要通过年谱、文集和地方志交叉核验,本句只有泛泛要求而非事实。",
                    "core": "生平年谱",
                    "dimension": "时间历史/发展阶段",
                    "time": "不详",
                    "people": [],
                    "places": [],
                    "objects": [],
                    "data": [],
                    "source_title": "测试来源",
                    "source_url": "https://example.com/source-2",
                    "source_type": "academic",
                    "confidence": "学术资料",
                },
            ]
            path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
            res = self.run_script("evidence_cards.py", "validate", str(path))
            combined = res.stdout + res.stderr
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("占位", combined)
            self.assertIn("细节字段不足", combined)

    def test_theme_space_plan_searches_content_alias_not_only_project_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "plan.json"
            res = self.run_script(
                "research_plan.py",
                "--topic", "钓鱼佬博物馆",
                "--type", "C",
                "--region", "中国",
                "--out", str(out),
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["theme_profile"]["content_subject"], "钓鱼佬")
            self.assertIn("钓鱼", data["theme_profile"]["subject_aliases"])
            queries = "\n".join(
                q["query"] for group in data["query_groups"] for q in group["queries"]
            )
            self.assertIn("钓鱼 分类 术语 工具", queries)
            self.assertIn("钓鱼佬 百度百科", queries)
            self.assertIn("钓鱼佬 维基百科", queries)
            self.assertNotIn("IPO", queries)

    def test_plan_declares_knowledge_system_and_compliance_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "plan.json"
            res = self.run_script(
                "research_plan.py",
                "--topic", "星空科学馆",
                "--type", "D",
                "--region", "中国",
                "--out", str(out),
                "--date", "2026-06-14",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            contract = data["research_contract"]
            self.assertTrue(contract["knowledge_system_first"])
            self.assertTrue(contract["evidence_calibration"])
            self.assertTrue(contract["manual_official_sources"])
            queries = "\n".join(
                q["query"] for group in data["query_groups"] for q in group["queries"]
            )
            self.assertIn("星空 百度百科", queries)
            self.assertIn("星空 维基百科", queries)

    def test_research_loop_generates_followup_queries_from_coverage_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_path = tmp_path / "plan.json"
            coverage_path = tmp_path / "coverage.json"
            evidence_path = tmp_path / "evidence.jsonl"
            loop_path = tmp_path / "research_loop.json"

            res = self.run_script(
                "research_plan.py",
                "--topic", "钓鱼佬文化馆",
                "--type", "C",
                "--region", "中国",
                "--out", str(plan_path),
                "--date", "2026-06-14",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            missing_cores = [
                "主题定义与边界",
                "历史源流与阶段变化",
                "分类谱系与子主题系统",
                "关键对象/工具/材料/作品/文本/影像",
                "行为流程/入门路径/进阶路径",
                "人物群体/社群组织/代表人物",
                "产业消费/平台数据/品牌渠道",
                "政策安全/生态伦理/行业规范",
                "最新动态与当前状态",
            ]
            coverage = {
                "topic": "钓鱼佬文化馆",
                "core_reports": [
                    {
                        "core": core,
                        "passed": False,
                        "evidence_cards": 0,
                        "sources": 0,
                        "evidence_fields": [],
                    }
                    for core in missing_cores
                ],
            }
            coverage_path.write_text(json.dumps(coverage, ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(
                json.dumps({
                    "claim": "已有来源示例,用于测试 visited_urls 去重。",
                    "core": "主题定义与边界",
                    "dimension": "主题边界/基础定义",
                    "time": "2026年",
                    "people": ["测试"],
                    "places": ["中国"],
                    "objects": ["测试对象"],
                    "data": ["1条"],
                    "source_title": "测试来源",
                    "source_url": "https://example.com/used",
                    "source_type": "web",
                    "confidence": "单一来源",
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            res = self.run_script(
                "research_loop.py",
                "--plan", str(plan_path),
                "--coverage", str(coverage_path),
                "--evidence", str(evidence_path),
                "--out", str(loop_path),
                "--breadth", "12",
                "--depth", "2",
                "--date", "2026-06-14",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(loop_path.read_text(encoding="utf-8"))
            queries = "\n".join(q["query"] for q in data["queries"])
            goals = "\n".join(q["research_goal"] for q in data["queries"])
            self.assertIn("钓鱼佬 是什么 入门", queries)
            self.assertIn("钓鱼 历史 起源 发展", queries)
            self.assertIn("钓鱼 分类 术语 工具", queries)
            self.assertIn("钓鱼 工具 装备 材料", queries)
            self.assertIn("钓鱼 新手 入门 流程", queries)
            self.assertIn("钓鱼 协会 俱乐部 赛事", queries)
            self.assertIn("钓鱼 市场 消费 行业报告", queries)
            self.assertIn("钓鱼 政策 法规 禁钓 规范", queries)
            self.assertIn("钓鱼 2026 最新 趋势", queries)
            self.assertIn("补足「主题定义与边界」", goals)
            self.assertIn("https://example.com/used", data["visited_urls"])
            self.assertTrue(all(q["research_goal"] for q in data["queries"]))
            self.assertTrue(all(q["expected_evidence_fields"] for q in data["queries"]))
            self.assertNotIn("IPO", queries)

    def test_coverage_audit_requires_factual_fields_per_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan = {
                "topic": "测试主题",
                "theme_profile": {"required_cores": ["生平年谱"]},
                "coverage_thresholds": {
                    "min_evidence_cards_per_required_core": 1,
                    "min_sources_per_required_core": 1,
                    "min_total_sources": 1,
                    "min_authority_sources": 1,
                    "min_factual_fields_per_required_core": 3,
                },
            }
            evidence = {
                "claim": "苏轼生平年谱资料中必须把具体年份、地点、人物关系和文献来源拆开,本测试模拟只有时间字段的薄证据。",
                "core": "生平年谱",
                "dimension": "时间历史/发展阶段",
                "time": "1037年",
                "people": [],
                "places": [],
                "objects": [],
                "data": [],
                "source_title": "测试来源",
                "source_url": "https://example.com/source",
                "source_type": "academic",
                "confidence": "学术资料",
            }
            plan_path = tmp_path / "plan.json"
            evidence_path = tmp_path / "evidence.jsonl"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False) + "\n", encoding="utf-8")
            res = self.run_script(
                "coverage_audit.py",
                "--plan", str(plan_path),
                "--evidence", str(evidence_path),
            )
            combined = res.stdout + res.stderr
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("必查核心证据不足", combined)

    def test_report_pipeline_generates_auditable_markdown_and_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan = {
                "topic": "测试企业",
                "project_type": {"code": "A"},
                "theme_profile": {"required_cores": ["主体身份与名称体系", "财经资本/上市IPO/融资/估值/收入"]},
            }
            cards = []
            for core in ["主体身份与名称体系", "财经资本/上市IPO/融资/估值/收入"]:
                for idx in range(10):
                    cards.append({
                        "claim": "测试企业在2026年形成第%d条可追溯证据,这条证据包含完整事实、明确对象和清晰来源,用于生成连续报告段落。" % (idx + 1),
                        "core": core,
                        "dimension": "测试维度",
                        "time": "2026年",
                        "people": ["测试人物"],
                        "places": ["测试地点"],
                        "objects": ["测试对象"],
                        "data": ["测试数据%d" % idx],
                        "source_title": "测试来源%d" % idx,
                        "source_url": "https://example.com/source-%s-%d" % (core[:2], idx),
                        "source_type": "government",
                        "confidence": "监管文件",
                    })
            plan_path = tmp_path / "plan.json"
            evidence_path = tmp_path / "evidence.jsonl"
            report_path = tmp_path / "report.md"
            audit_path = tmp_path / "report_audit.json"
            docx_path = tmp_path / "report.docx"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n", encoding="utf-8")

            res = self.run_script(
                "report_from_evidence.py",
                "--plan", str(plan_path),
                "--evidence", str(evidence_path),
                "--out", str(report_path),
                "--type", "A",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(report_path.exists())
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("资料调研报告", report_text)
            self.assertNotIn("资料综述", report_text)
            self.assertNotIn("时间口径为", report_text)
            self.assertNotIn("相关人物包括", report_text)
            self.assertNotIn("这些信息分别见于", report_text)
            self.assertIn("以上信息综合参考", report_text)

            res = self.run_script(
                "report_audit.py",
                str(report_path),
                "--min-chars", "3000",
                "--min-headings", "6",
                "--min-paragraphs", "8",
                "--json", str(audit_path),
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            data = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertFalse(data["errors"])

            res = self.run_script("report_to_docx.py", str(report_path), "-o", str(docx_path))
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(docx_path.exists())
            with zipfile.ZipFile(docx_path) as z:
                self.assertIn("word/document.xml", z.namelist())
                self.assertIn("word/styles.xml", z.namelist())

    def test_report_audit_rejects_short_list_and_method_labels(self):
        bad_report = """# 测试报告

## 一、主题

### 一.1 资料综述

短句。

继续下钻方向。

## 二、来源

来源类型为 government。

时间口径为2026年。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.md"
            path.write_text(bad_report, encoding="utf-8")
            res = self.run_script(
                "report_audit.py",
                str(path),
                "--min-chars", "100",
                "--min-headings", "2",
                "--min-paragraphs", "2",
                "--max-short-paragraphs", "0",
            )
            combined = res.stdout + res.stderr
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("方法标签", combined)
            self.assertIn("短段落", combined)
            self.assertIn("泛化小标题", combined)
            self.assertIn("字段腔", combined)


if __name__ == "__main__":
    unittest.main()
