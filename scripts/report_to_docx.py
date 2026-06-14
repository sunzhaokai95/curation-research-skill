#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_to_docx.py - 将报告型 Markdown 转为最小可打开 .docx。

纯 Python 标准库实现,不依赖 python-docx。支持 #/##/### 标题、普通段落和 URL 段落。
"""
import argparse
import html
import os
import re
import sys
import zipfile


def md_blocks(text):
    blocks = []
    current = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        if line.startswith("#"):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            blocks.append(line.strip())
        else:
            current.append(line.strip())
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def paragraph_xml(text, style="Normal"):
    text = re.sub(r"\s+", " ", text).strip()
    escaped = html.escape(text)
    style_xml = '<w:pStyle w:val="%s"/>' % style if style else ""
    return (
        "<w:p><w:pPr>%s</w:pPr><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>"
        % (style_xml, escaped)
    )


def document_xml(blocks):
    body = []
    for block in blocks:
        m = re.match(r"^(#{1,6})\s+(.*)$", block)
        if m:
            level = min(len(m.group(1)), 3)
            title = m.group(2).strip()
            body.append(paragraph_xml(title, "Heading%d" % level))
        else:
            body.append(paragraph_xml(block, "Normal"))
    body.append('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>%s</w:body>
</w:document>""" % "".join(body)


def styles_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr><w:spacing w:after="160" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="360" w:after="240"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="300" w:after="180"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="2"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
</w:styles>"""


def write_docx(markdown, out_path):
    blocks = md_blocks(markdown)
    doc = document_xml(blocks)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles_xml())
    return len(blocks)


def main():
    ap = argparse.ArgumentParser(description="报告 Markdown -> .docx")
    ap.add_argument("input", help="报告 Markdown")
    ap.add_argument("-o", "--output", required=True, help="输出 .docx")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()
    blocks = write_docx(text, args.output)
    print("已生成 Word: %s" % args.output)
    print("段落/标题块: %d" % blocks)


if __name__ == "__main__":
    sys.exit(main())
