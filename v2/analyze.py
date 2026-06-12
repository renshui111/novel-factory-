# analyze.py — 拆书模块
# 输入一本小说 .txt → 输出结构化分析报告

import os
import re
import json
import time

from core import llm_invoke_ada, read_file, write_file, ensure_dir, count_words, get_output_dir
from prompts import (
    ANALYZE_SETTING, ANALYZE_CHARACTERS,
    ANALYZE_PLOT, ANALYZE_STYLE
)


def analyze_novel(novel_path: str, output_dir: str = "",
                  log_callback=None) -> dict:
    """
    拆书入口：分析一本小说，产出结构化报告。
    
    Args:
        novel_path: 小说文件路径 (.txt)
        output_dir: 产出目录（默认 output/拆书/{书名}/）
        log_callback: 日志回调函数
    
    Returns:
        dict: 分析结果摘要
    """
    # 读取小说
    novel_text = read_file(novel_path)
    if not novel_text:
        return {"error": "文件为空或无法读取"}

    book_name = os.path.splitext(os.path.basename(novel_path))[0]
    total_words = count_words(novel_text)

    if log_callback:
        log_callback(f"📕 {book_name} | {total_words} 字")
        log_callback(f"开始拆书...")

    # 创建输出目录
    if not output_dir:
        output_dir = os.path.join(get_output_dir(), "拆书", book_name)
    ensure_dir(output_dir)

    results = {}

    # 限制小说文本长度（避免提示词过大）
    if total_words > 50000:
        # 取前 5000 + 均匀抽样
        sampled = _sample_novel_text(novel_text, total_words)
    else:
        sampled = novel_text[:50000]

    # ─── 1. 设定分析 ───────────────────
    if log_callback:
        log_callback("[1/4] 分析设定体系...")

    settings = llm_invoke_ada(
        ANALYZE_SETTING.format(novel_text=sampled),
        system_msg="你是一位资深的网文编辑和拆书专家。请按照要求的格式输出分析结果。"
    )
    write_file(os.path.join(output_dir, "设定分析.md"), settings)
    results["setting"] = "完成"
    if log_callback:
        log_callback("  ✓ 设定分析完成")

    # ─── 2. 角色分析 ───────────────────
    if log_callback:
        log_callback("[2/4] 分析角色体系...")

    characters = llm_invoke_ada(
        ANALYZE_CHARACTERS.format(novel_text=sampled),
        system_msg="你是一位资深的网文编辑和拆书专家。请按照要求的格式输出分析结果。"
    )
    write_file(os.path.join(output_dir, "角色分析.md"), characters)
    results["characters"] = "完成"
    if log_callback:
        log_callback("  ✓ 角色分析完成")

    # ─── 3. 剧情分析 ───────────────────
    if log_callback:
        log_callback("[3/4] 分析剧情结构...")

    plot = llm_invoke_ada(
        ANALYZE_PLOT.format(novel_text=sampled),
        system_msg="你是一位资深的网文编辑和拆书专家。请按照要求的格式输出分析结果。"
    )
    write_file(os.path.join(output_dir, "剧情分析.md"), plot)
    results["plot"] = "完成"
    if log_callback:
        log_callback("  ✓ 剧情分析完成")

    # ─── 4. 风格分析 ───────────────────
    if log_callback:
        log_callback("[4/4] 分析写作风格...")

    style = llm_invoke_ada(
        ANALYZE_STYLE.format(novel_text=sampled),
        system_msg="你是一位资深的网文编辑和拆书专家。请按照要求的格式输出分析结果。"
    )
    write_file(os.path.join(output_dir, "风格分析.md"), style)
    results["style"] = "完成"
    if log_callback:
        log_callback("  ✓ 风格分析完成")

    # ─── 生成汇总文件 ─────────────────
    summary = f"""# {book_name} — 拆书报告

## 基本信息
- 文件名：{os.path.basename(novel_path)}
- 总字数：{total_words:,}
- 分析时间：{time.strftime('%Y-%m-%d %H:%M:%S')}

## 分析结果
"""
    for k, v in results.items():
        summary += f"- {k}: {v}\n"

    write_file(os.path.join(output_dir, "拆书报告.md"), summary)
    results["output_dir"] = output_dir

    if log_callback:
        log_callback(f"\n✅ 拆书完成！报告已保存到：\n  {output_dir}")

    return results


def _sample_novel_text(text: str, total_len: int) -> str:
    """对长文本进行智能采样，保留开头中结尾关键部分"""
    part_len = min(total_len // 3, 8000)

    start = text[:part_len]

    mid_start = total_len // 2 - part_len // 2
    mid = text[mid_start:mid_start + part_len]

    end = text[-part_len:]

    return f"[开头部分]\n{start}\n\n[中间部分]\n{mid}\n\n[结尾部分]\n{end}"


def batch_analyze(directory: str, log_callback=None) -> list:
    """
    批量拆书：分析一个目录下的所有 .txt 文件
    
    Args:
        directory: 包含小说的目录
        log_callback: 日志回调
    
    Returns:
        list: 每本小说的分析结果
    """
    results = []
    txt_files = [f for f in os.listdir(directory)
                 if f.lower().endswith('.txt')
                 and os.path.isfile(os.path.join(directory, f))]

    if log_callback:
        log_callback(f"找到 {len(txt_files)} 本小说，开始批量拆书...\n")

    for i, fname in enumerate(txt_files, 1):
        path = os.path.join(directory, fname)
        if log_callback:
            log_callback(f"\n[{i}/{len(txt_files)}] {fname}")
        result = analyze_novel(path, log_callback=log_callback)
        results.append({"file": fname, "result": result})

    if log_callback:
        log_callback(f"\n✅ 批量拆书完成！共分析 {len(txt_files)} 本小说")

    return results