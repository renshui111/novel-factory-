# -*- coding: utf-8 -*-
"""splitter.py --- 分块拆书引擎
支持百万字级别全书分析：分块→并行分析→渐进式合成
"""

import os, re, json, math
# core imports moved to function level

# ---------------------------------------------------------------------------
# Core: split book into chunks
# ---------------------------------------------------------------------------

def split_book(filepath: str, chunk_chapters: int = 20) -> list:
    """将书按章节分块，每块 chunk_chapters 章"""
    text = read_file(filepath)
    chapters = split_into_chapters(text)
    
    chunks = []
    for i in range(0, len(chapters), chunk_chapters):
        chunk = chapters[i:i + chunk_chapters]
        chunks.append({
            "index": len(chunks),
            "start_chapter": i + 1,
            "end_chapter": i + len(chunk),
            "chapters": chunk,
            "text": "\n\n".join([c["content"] for c in chunk]),
            "word_count": sum(c["words"] for c in chunk),
        })
    return chunks


def split_into_chapters(text: str) -> list:
    """将全文按章节标记切分"""
    # Match patterns: 第X章, Chapter X, 第X回, Ch.X, # X
    patterns = [
        r'\n(?=第[零一二三四五六七八九十百千\d]+[章回节卷])',
        r'\n(?=Chapter\s+\d+)',
        r'\n(?=Ch\.\s*\d+)',
        r'\n(?=#[^\n]{0,10}第[零一二三四五六七八九十百千\d]+[章回])',
    ]
    
    for pattern in patterns:
        parts = re.split(pattern, text, flags=re.MULTILINE)
        if len(parts) > 3:  # Found chapters
            break
    else:
        # Fallback: split by word count every 3000 words
        words = text
        chunk_size = 3000
        parts = []
        pos = 0
        while pos < len(words):
            chunk = words[pos:pos + chunk_size * 2]  # ~2 chars per Chinese char
            parts.append(chunk)
            pos += len(chunk)
        parts = [p.strip() for p in parts if p.strip()]
    
    chapters = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part or len(part) < 50:
            continue
        chapters.append({
            "num": i + 1,
            "content": part,
            "words": count_words(part),
        })
    
    return chapters


# ---------------------------------------------------------------------------
# Per-chunk analysis
# ---------------------------------------------------------------------------

def analyze_chunk(chunk: dict, book_name: str = "", log_callback=None) -> dict:
    from core import llm_invoke_ada
    """对单个分块做四维分析"""
    result = {
        "chunk_index": chunk["index"],
        "start": chunk["start_chapter"],
        "end": chunk["end_chapter"],
        "setting": "",
        "characters": "",
        "plot": "",
        "style": "",
        "key_events": [],
        "new_characters": [],
    }
    
    text_sample = chunk["text"][:6000]

    # 1. Setting analysis
    setting_prompt = f"""分析以下小说片段的世界观设定：

{text_sample[:4000]}

请提取：
1. 世界观核心设定（力量体系/社会结构/特殊规则）
2. 场景/地点信息
3. 重要物品/道具
用简洁的条目形式回答，不超过500字。"""

    try:
        result["setting"] = llm_invoke_ada(setting_prompt) or ""
        if log_callback:
            log_callback(f"  块{chunk['index']+1}: 设定分析完成")
    except Exception as e:
        result["setting"] = f"[分析失败: {e}]"

    # 2. Character analysis
    char_prompt = f"""分析以下小说片段中的人物：

{text_sample[:4000]}

请列出：
1. 主要人物姓名、身份、性格特征
2. 人物之间的关系
3. 本段中人物的行为与动机
用结构化条目形式，不超过500字。"""

    try:
        result["characters"] = llm_invoke_ada(char_prompt) or ""
        if log_callback:
            log_callback(f"  块{chunk['index']+1}: 角色分析完成")
    except Exception as e:
        result["characters"] = f"[分析失败: {e}]"

    # 3. Plot analysis
    plot_prompt = f"""分析以下小说片段的剧情结构：

{text_sample[:4000]}

请列出：
1. 关键事件（时间顺序）
2. 冲突与转折
3. 伏笔与悬念
用条目形式，不超过500字。"""

    try:
        result["plot"] = llm_invoke_ada(plot_prompt) or ""
        if log_callback:
            log_callback(f"  块{chunk['index']+1}: 剧情分析完成")
    except Exception as e:
        result["plot"] = f"[分析失败: {e}]"

    # 4. Style analysis
    style_prompt = f"""分析以下小说片段的写作风格：

{text_sample[:4000]}

请分析：
1. 句式特点（长短句比例/修辞手法）
2. 叙事节奏
3. 对话风格
4. 描写特点
不超过500字。"""

    try:
        result["style"] = llm_invoke_ada(style_prompt) or ""
        if log_callback:
            log_callback(f"  块{chunk['index']+1}: 风格分析完成")
    except Exception as e:
        result["style"] = f"[分析失败: {e}]"

    return result


# ---------------------------------------------------------------------------
# Progressive synthesis: merge chunk results
# ---------------------------------------------------------------------------

def synthesize_chunks(chunk_results: list, book_name: str = "", log_callback=None) -> dict:
    """渐进式合成：将分块分析结果合并为全书分析"""
    if not chunk_results:
        return {}

    # Combine all chunk analyses
    all_setting = "\n".join([r["setting"] for r in chunk_results if r["setting"]])
    all_characters = "\n".join([r["characters"] for r in chunk_results if r["characters"]])
    all_plot = "\n".join([r["plot"] for r in chunk_results if r["plot"]])
    all_style = "\n".join([r["style"] for r in chunk_results if r["style"]])

    result = {
        "book_name": book_name,
        "total_chunks": len(chunk_results),
        "setting": all_setting,
        "characters": all_characters,
        "plot": all_plot,
        "style": all_style,
        "synthesized": {},
    }

    # If many chunks, do a final AI synthesis
    if len(chunk_results) > 3:
        if log_callback:
            log_callback("  正在进行最终合成...")

        # Synthesize setting
        try:
            synth_prompt = f"""将以下多段设定分析合并为一份完整的全书设定报告：

{all_setting[:5000]}

请整合去重，形成结构化的：
1. 世界背景
2. 力量/规则体系
3. 关键地点
4. 重要物品/概念
不超过1000字。"""
            result["synthesized"]["setting"] = llm_invoke_ada(synth_prompt) or ""
        except Exception:
            result["synthesized"]["setting"] = all_setting[:2000]

        # Synthesize characters
        try:
            char_synth = f"""将以下多段角色分析合并为完整的全书角色关系网络：

{all_characters[:5000]}

请整合为：
1. 角色列表（姓名+身份+性格+命运走向）
2. 关系网络图（文字描述）
3. 角色成长弧线
不超过1500字。"""
            result["synthesized"]["characters"] = llm_invoke_ada(char_synth) or ""
        except Exception:
            result["synthesized"]["characters"] = all_characters[:2000]

        # Synthesize plot
        try:
            plot_synth = f"""将以下多段剧情分析合并为完整的全书情节报告：

{all_plot[:5000]}

请整合为：
1. 主线剧情概述
2. 关键转折点时间线
3. 支线/伏笔追踪
4. 情节结构评价
不超过1500字。"""
            result["synthesized"]["plot"] = llm_invoke_ada(plot_synth) or ""
        except Exception:
            result["synthesized"]["plot"] = all_plot[:2000]

        # Synthesize style
        try:
            style_synth = f"""将以下多段风格分析合并为完整的写作风格报告：

{all_style[:5000]}

请整合为：
1. 核心风格特征
2. 可学习的技法清单
3. 句式/节奏特点
4. AI写作模仿要点
不超过1000字。"""
            result["synthesized"]["style"] = llm_invoke_ada(style_synth) or ""
        except Exception:
            result["synthesized"]["style"] = all_style[:2000]
    else:
        result["synthesized"] = {
            "setting": all_setting[:2000],
            "characters": all_characters[:2000],
            "plot": all_plot[:2000],
            "style": all_style[:2000],
        }

    return result


# ---------------------------------------------------------------------------
# Full pipeline: split -> analyze -> synthesize
# ---------------------------------------------------------------------------

def full_analyze(filepath: str, output_dir: str = "", log_callback=None) -> dict:
    """完整拆书流程：分块→分析→合成"""
    book_name = os.path.splitext(os.path.basename(filepath))[0]
    
    if log_callback:
        log_callback(f"正在拆分 {book_name}...")
    
    chunks = split_book(filepath)
    total = len(chunks)
    
    if log_callback:
        log_callback(f"拆分为 {total} 块，开始逐块分析...")
    
    results = []
    for i, chunk in enumerate(chunks):
        if log_callback:
            log_callback(f"[{i+1}/{total}] 分析第{chunk['start_chapter']}-{chunk['end_chapter']}章 ({chunk['word_count']}字)")
        
        result = analyze_chunk(chunk, book_name, log_callback)
        results.append(result)
    
    if log_callback:
        log_callback("分析完成，开始合成...")
    
    final = synthesize_chunks(results, book_name, log_callback)
    final["chunks"] = [{"index": r["chunk_index"], "start": r["start"], "end": r["end"]} for r in results]
    final["total_chapters"] = chunks[-1]["end_chapter"] if chunks else 0
    final["total_words"] = sum(c["word_count"] for c in chunks)
    
    # Save
    if output_dir:
        ensure_dir(output_dir)
        out_path = os.path.join(output_dir, f"{book_name}_分析报告.json")
        write_file(out_path, json.dumps(final, ensure_ascii=False, indent=2))
        
        # Also save human-readable markdown
        md_path = os.path.join(output_dir, f"{book_name}_分析报告.md")
        md = _format_report_md(final)
        write_file(md_path, md)
        
        if log_callback:
            log_callback(f"报告已保存: {out_path}")
            log_callback(f"Markdown版: {md_path}")
    
    return final


def _format_report_md(report: dict) -> str:
    """将分析报告格式化为Markdown"""
    lines = []
    lines.append(f"# {report.get('book_name', '小说')} 分析报告")
    lines.append(f"")
    lines.append(f"- 总章节: {report.get('total_chapters', '?')}")
    lines.append(f"- 总字数: {report.get('total_words', 0):,}")
    lines.append(f"- 分析块数: {report.get('total_chunks', 0)}")
    lines.append(f"")

    syn = report.get("synthesized", {})
    
    if syn.get("setting"):
        lines.append("## 世界观设定")
        lines.append(syn["setting"])
        lines.append("")
    
    if syn.get("characters"):
        lines.append("## 角色分析")
        lines.append(syn["characters"])
        lines.append("")
    
    if syn.get("plot"):
        lines.append("## 剧情分析")
        lines.append(syn["plot"])
        lines.append("")
    
    if syn.get("style"):
        lines.append("## 写作风格")
        lines.append(syn["style"])
        lines.append("")
    
    return "\n".join(lines)
