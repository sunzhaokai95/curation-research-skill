#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_doc.py —— 把需求文档(.docx / .pptx / .pdf / .txt / .md)提取为纯文本。

零第三方依赖,仅用 Python 标准库。设计目标是"够用就好":
  - .docx / .pptx —— 本质是 zip+XML,解压后抽取 <w:t> / <a:t> 文本节点
  - .pdf          —— 标准库无法可靠解析 PDF;若系统有 pdftotext(poppler)则调用,
                     否则做极简文本流提取并提示用户。扫描件(图片型 PDF)不支持。
  - .txt / .md    —— 直接读

用法:
    python3 extract_doc.py 需求文档.docx
    python3 extract_doc.py 方案.pptx -o out.txt
    python3 extract_doc.py *.pdf                  # 多文件,依次输出

PDF 若需完整能力(扫描件 OCR),另装 poppler/tesseract;本脚本默认纯零依赖。
"""
import sys
import os
import re
import zipfile
import argparse
import shutil
import subprocess


def extract_docx(path):
    """从 .docx 抽取段落文本。按 </w:p> 切段保留换行。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    out = []
    for p in paras:
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
        line = "".join(texts).strip()
        if line:
            out.append(_unescape(line))
    return "\n".join(out)


def extract_pptx(path):
    """从 .pptx 抽取每张幻灯片的文本(<a:t> 节点),按幻灯片分段。"""
    with zipfile.ZipFile(path) as z:
        slide_names = sorted(
            [n for n in z.namelist()
             if re.match(r"ppt/slides/slide\d+\.xml$", n)],
            key=lambda n: int(re.search(r"slide(\d+)", n).group(1)))
        out = []
        for i, name in enumerate(slide_names, 1):
            xml = z.read(name).decode("utf-8", "ignore")
            texts = re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)
            body = "\n".join(_unescape(t.strip()) for t in texts if t.strip())
            if body:
                out.append("=== 幻灯片 %d ===\n%s" % (i, body))
        return "\n\n".join(out)


def extract_pdf(path):
    """优先用系统 pdftotext;无则极简提取并提示。"""
    exe = shutil.which("pdftotext")
    if exe:
        try:
            res = subprocess.run([exe, "-layout", path, "-"],
                                 capture_output=True, timeout=120)
            txt = res.stdout.decode("utf-8", "ignore").strip()
            if txt:
                return txt
        except Exception as e:
            sys.stderr.write("pdftotext 调用失败: %s\n" % e)
    # 极简降级:抽取 PDF 流里的可见文本(对部分简单 PDF 有效)
    sys.stderr.write(
        "[提示] 未找到 pdftotext。正在用标准库做极简提取,"
        "效果有限;扫描件/复杂排版请安装 poppler:`brew install poppler`。\n")
    with open(path, "rb") as f:
        data = f.read()
    # 抽取括号内文本(PDF Tj 操作符常见形式),非常粗糙
    chunks = re.findall(rb"\((?:[^()\\]|\\.)*\)", data)
    out = []
    for c in chunks:
        s = c[1:-1].decode("latin-1", "ignore")
        s = s.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
        if s.strip():
            out.append(s)
    return "\n".join(out)


def _unescape(s):
    # 个别由转换工具生成的文档,文本节点里会混入字面的 w:/a: 命名空间标签,
    # 先精准剥除这类残留标签(不动正常文本里的 < >),再做实体反转义。
    s = re.sub(r"</?[wa]:[^>]*>", "", s)
    return (s.replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'"))


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".pptx":
        return extract_pptx(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext in (".txt", ".md", ".markdown"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    raise ValueError("不支持的格式: %s(支持 docx/pptx/pdf/txt/md)" % ext)


def main():
    ap = argparse.ArgumentParser(description="文档 -> 纯文本")
    ap.add_argument("inputs", nargs="+", help="一个或多个文档路径")
    ap.add_argument("-o", "--output", help="输出文本路径(仅单文件时)")
    args = ap.parse_args()

    if len(args.inputs) == 1:
        text = extract(args.inputs[0])
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            sys.stderr.write("已写入 %s(%d 字)\n" % (args.output, len(text)))
        else:
            sys.stdout.write(text)
    else:
        for p in args.inputs:
            try:
                text = extract(p)
                print("\n########## %s (%d 字) ##########" % (p, len(text)))
                print(text)
            except Exception as e:
                sys.stderr.write("跳过 %s: %s\n" % (p, e))


if __name__ == "__main__":
    main()
