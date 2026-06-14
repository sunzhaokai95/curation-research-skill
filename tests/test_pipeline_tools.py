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


if __name__ == "__main__":
    unittest.main()
