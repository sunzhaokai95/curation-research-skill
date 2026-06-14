#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_to_xmind.py —— 把缩进式 Markdown 大纲转成 .xmind 思维导图(XMind 2021/Zen 格式)。

零第三方依赖,仅用 Python 标准库(zipfile + json)。生成的 .xmind 是一个 zip 包,
含 content.json / manifest.json / metadata.json,可被 XMind 桌面软件直接打开。

输入大纲格式(两种缩进标记都支持,可混用):
  - 用 "#" 表示中心主题(可省略,省略时取第一行或文件名)
  - 用缩进(2 或 4 空格、Tab)或 Markdown 列表 "- " / "* " 表示层级
  - 也支持 Markdown 标题 #/##/### 作为层级
  - 用 ">" 开头的行 = 上一个节点的详细备注(notes),承载史实/故事/数据,
    不作为子节点;连续多个 ">" 行合并为多段。XMind 中双击节点可查看备注。

示例 outline.md:
    # 某某博物馆调研
    - 茶之饮·饮茶方式演变
      - 唐·煎茶
        > 陆羽在《茶经·五之煮》确立煎茶法:茶饼炙烤碾末,投入沸水煎煮,
        > 讲究"三沸"。一沸如鱼目微有声,二沸缘边如涌泉连珠,三沸腾波鼓浪。
        - 蒸青工艺
        - 加盐调味
      - 宋·点茶
        > 研磨极细茶末置盏中,沸水冲点,以茶筅击拂出沫饽,由此衍生斗茶。

用法:
    python3 md_to_xmind.py outline.md -o out.xmind
    python3 md_to_xmind.py outline.md            # 默认输出同名 .xmind
    cat outline.md | python3 md_to_xmind.py - -o out.xmind   # 从 stdin 读
"""
import sys
import os
import json
import zipfile
import argparse


def _indent_width(line):
    """计算一行的缩进宽度,Tab 记为 4。"""
    w = 0
    for ch in line:
        if ch == ' ':
            w += 1
        elif ch == '\t':
            w += 4
        else:
            break
    return w


def parse_outline(text):
    """把缩进/列表/标题式大纲解析成嵌套 dict 树。返回 (中心主题title, [一级节点])。

    支持节点备注:以 '>' 开头的行(去掉缩进后)是"上一个节点"的详细备注(notes),
    不作为子节点。连续多个 '>' 行合并为多段。备注用于承载详细史实/故事/数据,
    在 XMind 中双击节点即可查看。"""
    root_title = None
    raw_items = []  # {'kind':'node'/'note', ...}
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = raw.strip()

        # 备注行:以 > 开头
        if stripped.startswith('>'):
            note = stripped.lstrip('>').strip()
            if note:
                raw_items.append({'kind': 'note', 'text': note})
            continue

        # Markdown 标题
        if stripped.startswith('#'):
            hashes = len(stripped) - len(stripped.lstrip('#'))
            title = stripped[hashes:].strip()
            if not title:
                continue
            if hashes == 1 and root_title is None:
                root_title = title
                continue
            raw_items.append({'kind': 'node', 'title': title,
                              'indent': None, 'level': hashes})
            continue

        indent = _indent_width(raw)
        # 去掉列表符号
        body = stripped
        for marker in ('- ', '* ', '+ '):
            if body.startswith(marker):
                body = body[len(marker):].strip()
                break
        else:
            # 形如 "1. xxx"
            if len(body) > 2 and body[0].isdigit() and body[1] in ').':
                body = body[2:].strip()
        if not body:
            continue
        raw_items.append({'kind': 'node', 'title': body,
                          'indent': indent, 'level': None})

    # 归一化 list 节点的缩进为 depth(0 = 一级分支)
    list_indents = sorted({it['indent'] for it in raw_items
                           if it['kind'] == 'node' and it['indent'] is not None})
    indent_to_depth = {v: i for i, v in enumerate(list_indents)}

    # 用栈构建树;note 行附加到最近创建的节点
    forest = []
    stack = []  # 元素: (depth, node_dict)
    last_node = None
    for it in raw_items:
        if it['kind'] == 'note':
            if last_node is not None:
                last_node['notes'].append(it['text'])
            continue
        if it['indent'] is None:  # heading
            depth = max(0, it['level'] - 2)  # ## -> 0, ### -> 1
        else:
            depth = indent_to_depth.get(it['indent'], 0)
        node = {'title': it['title'], 'children': [], 'notes': []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            stack[-1][1]['children'].append(node)
        else:
            forest.append(node)
        stack.append((depth, node))
        last_node = node

    return root_title, forest


_id_counter = [0]


def _new_id():
    _id_counter[0] += 1
    return "topic%d" % _id_counter[0]


STRUCTURE = "org.xmind.ui.logic.right"


def to_topic(node):
    """把内部树节点转成 XMind topic 结构(含 class/structureClass 等必填字段)。
    若节点带备注(notes),写入 XMind 的 notes.plain(双击节点可查看)。"""
    topic = {
        "id": _new_id(),
        "class": "topic",
        "structureClass": STRUCTURE,
        "title": node['title'],
    }
    notes = node.get('notes') or []
    if notes:
        content = "\n\n".join(notes)
        topic["notes"] = {"plain": {"content": content}}
    if node['children']:
        topic["children"] = {
            "attached": [to_topic(c) for c in node['children']]
        }
    return topic


def build_xmind(root_title, forest, out_path):
    root_topic = {
        "id": "root",
        "class": "topic",
        "structureClass": STRUCTURE,
        "title": root_title or "思维导图",
    }
    if forest:
        root_topic["children"] = {
            "attached": [to_topic(n) for n in forest]
        }
    content = [{
        "id": "sheet1",
        "class": "sheet",
        "title": "Sheet 1",
        "extensions": [],
        "topicPositioning": "fixed",
        "topicOverlapping": "overlap",
        "coreVersion": "2.100.0",
        "rootTopic": root_topic,
    }]
    manifest = {"file-entries": {
        "content.json": {},
        "metadata.json": {},
    }}
    metadata = {
        "dataStructureVersion": "2",
        "creator": {"name": "curation-research", "version": "1.0"},
        "layoutEngineVersion": "3",
        "activeSheetId": "sheet1",
    }

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("content.json", json.dumps(content, ensure_ascii=False))
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        z.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
    return content


def count_topics(content):
    def walk(t):
        n = 1
        for c in t.get("children", {}).get("attached", []):
            n += walk(c)
        return n
    return walk(content[0]["rootTopic"])


def main():
    ap = argparse.ArgumentParser(description="Markdown 大纲 -> .xmind")
    ap.add_argument("input", help="输入大纲 .md 文件,'-' 表示 stdin")
    ap.add_argument("-o", "--output", help="输出 .xmind 路径")
    args = ap.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
        default_root = "思维导图"
        out = args.output or "out.xmind"
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
        default_root = os.path.splitext(os.path.basename(args.input))[0]
        out = args.output or (os.path.splitext(args.input)[0] + ".xmind")

    root_title, forest = parse_outline(text)
    if not root_title:
        root_title = default_root
    content = build_xmind(root_title, forest, out)
    n = count_topics(content)
    print("已生成: %s" % out)
    print("中心主题: %s" % root_title)
    print("一级分支: %d  总主题数: %d" % (
        len(content[0]["rootTopic"].get("children", {}).get("attached", [])), n))


if __name__ == "__main__":
    main()
