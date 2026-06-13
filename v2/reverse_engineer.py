# -*- coding: utf-8 -*-
"""reverse_engineer.py --- 逆向工程畅销书
解构一本小说为什么成功：黄金三章+爽点密度+节奏公式+可复制模板
"""

import json, os, re

def reverse_engineer(novel_path: str, log_callback=None) -> dict:
    """完整逆向工程一本书
    
    Returns:
        {golden_chapters, pleasure_density, pacing_formula, character_formula,
         hook_techniques, replicable_template, overall_score}
    """
    from core import read_file, count_words
    
    text = read_file(novel_path)
    if not text:
        return {"error": "无法读取文件"}
    
    book_name = os.path.basename(novel_path)
    total_words = count_words(text)
    
    if log_callback:
        log_callback(f"正在逆向分析: {book_name} ({total_words:,}字)")
    
    # Split into chapters
    chapters = _split_chapters(text)
    
    result = {
        "book_name": book_name,
        "total_words": total_words,
        "total_chapters": len(chapters),
    }
    
    # 1. Golden three chapters analysis
    if log_callback:
        log_callback("[1/6] 黄金三章分析...")
    result["golden_chapters"] = _analyze_golden_three(chapters[:3], log_callback)
    
    # 2. Pleasure point density
    if log_callback:
        log_callback("[2/6] 爽点密度分析...")
    result["pleasure_density"] = _analyze_pleasure_points(chapters, log_callback)
    
    # 3. Pacing formula
    if log_callback:
        log_callback("[3/6] 节奏公式提取...")
    result["pacing_formula"] = _extract_pacing_formula(chapters, log_callback)
    
    # 4. Character formula
    if log_callback:
        log_callback("[4/6] 角色公式分析...")
    result["character_formula"] = _analyze_character_formula(chapters, log_callback)
    
    # 5. Hook techniques
    if log_callback:
        log_callback("[5/6] 钩子技法提取...")
    result["hook_techniques"] = _extract_hook_techniques(chapters, log_callback)
    
    # 6. Replicable template
    if log_callback:
        log_callback("[6/6] 生成可复制公式...")
    result["replicable_template"] = _build_template(result, log_callback)
    
    return result


def _split_chapters(text: str) -> list:
    """简易章节切分"""
    pattern = r'\n(?=第[零一二三四五六七八九十百千\d]+[章回节卷])'
    parts = re.split(pattern, text)
    chapters = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        chapters.append({
            "num": i + 1,
            "text": p,
            "length": len(p),
        })
    return chapters


def _analyze_golden_three(chapters: list, log=None) -> dict:
    """分析前三章的钩子设置"""
    from core import llm_invoke_ada
    
    if not chapters:
        return {}
    
    text = "\n---\n".join([f"第{c['num']}章:\n{c['text'][:3000]}" for c in chapters[:3]])
    
    prompt = f"""分析以下小说的前三章（黄金三章），找出它为什么能抓住读者：

{text[:8000]}

请分析：
1. 第一章有几个钩子？分别在第几句话？
2. 世界观如何展开？（一次性倾倒/渐进式/悬念式）
3. 主角在第几章建立读者共情？通过什么方式？
4. 每章的结尾钩子是什么？
5. 如果这本书成功了，黄金三章最值得学习的3个技法是什么？

请用结构化格式回答。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def _analyze_pleasure_points(chapters: list, log=None) -> dict:
    """分析爽点密度和分布"""
    from core import llm_invoke_ada
    
    # Sample: first 10, middle 5, last 5
    sample = chapters[:10]
    mid_start = len(chapters) // 2 - 3
    sample += chapters[mid_start:mid_start + 5] if mid_start > 10 else []
    sample += chapters[-5:] if len(chapters) > 15 else []
    
    text = "\n---\n".join([f"第{c['num']}章:\n{c['text'][:2000]}" for c in sample])
    
    prompt = f"""分析以下小说章节中的"爽点"密度和类型：

{text[:8000]}

请分析：
1. 平均每章有多少个爽点？（打脸/升级/获得宝物/征服/解谜等）
2. 爽点之间的间隔大概多少字？
3. 大高潮和小爽点各占多少章一次？
4. 爽点类型分布（打脸___%/升级___%/解谜___%/感情___%/其他___%）
5. 是否存在"爽点疲劳"的章节？

用数据化格式回答。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def _extract_pacing_formula(chapters: list, log=None) -> dict:
    """提取节奏公式"""
    from core import llm_invoke_ada
    
    # Take structural sample
    sample_indices = [0, 1, len(chapters)//4, len(chapters)//3, 
                      len(chapters)//2, len(chapters)*2//3, len(chapters)-2, len(chapters)-1]
    sample_indices = [i for i in sample_indices if 0 <= i < len(chapters)]
    
    text = "\n---\n".join([f"第{chapters[i]['num']}章(前200字):\n{chapters[i]['text'][:200]}" 
                           for i in sample_indices])
    
    prompt = f"""分析以下小说的节奏结构：

{text[:6000]}

请提取：
1. 多少章一次小高潮？多少章一次大高潮？
2. 战斗章节和日常章节的比例？
3. 过渡章节（纯过渡/铺垫）大概占多少比例？
4. 每卷/每篇大概多少章？
5. 可复制的节奏公式（如"3章铺垫+1章爆发"）

用结构化格式回答。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def _analyze_character_formula(chapters: list, log=None) -> dict:
    """分析角色塑造公式"""
    from core import llm_invoke_ada
    
    text = "\n---\n".join([f"第{c['num']}章:\n{c['text'][:2000]}" 
                           for c in chapters[:5]])
    
    prompt = f"""分析以下小说的角色塑造公式：

{text[:8000]}

请分析：
1. 主角的人设公式（身份+性格+目标+缺陷）
2. 配角的配置（几个核心配角/各有什么功能）
3. 反派塑造模式（扁平反派/立体反派/阶段性反派）
4. 情感线的节奏
5. 角色成长弧线设计

用结构化格式回答。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def _extract_hook_techniques(chapters: list, log=None) -> dict:
    """提取钩子技法"""
    from core import llm_invoke_ada
    
    endings = [f"第{c['num']}章结尾:\n{c['text'][-300:]}" 
               for c in chapters[:20]]
    text = "\n---\n".join(endings)
    
    prompt = f"""分析以下小说章节结尾的钩子技法：

{text[:6000]}

请分类统计：
1. 悬念型结尾：___%
2. 情绪型结尾：___%
3. 信息型结尾（新信息/揭示）：___%
4. 动作型结尾（战斗/冲突未完）：___%
5. 各举一个典型例子
6. 总结3个最有效的结尾钩子公式

用结构化格式回答。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def _build_template(analysis: dict, log=None) -> dict:
    """综合所有分析，生成可复制公式"""
    from core import llm_invoke_ada
    
    gathered = []
    for key in ["golden_chapters", "pleasure_density", "pacing_formula", 
                "character_formula", "hook_techniques"]:
        raw = analysis.get(key, {}).get("raw", "")
        if raw:
            gathered.append(f"[{key}]\n{raw[:1500]}")
    
    content = "\n\n".join(gathered)
    
    prompt = f"""基于以下分析数据，为这本书提炼一个"可复制写作公式"：

{content[:8000]}

请给出：
1. 一句话概括这本书成功的核心原因
2. 3条可以直接套用到新书上的写作规则
3. 建议的章节规划模板（如：前X章做什么，中段怎么走，结尾怎么收）
4. 适合模仿这本书风格的新书题材建议（3个）

用简洁实用的格式回答，每条规则要具体可操作。"""

    try:
        result = llm_invoke_ada(prompt)
        return {"raw": result} if result else {}
    except Exception:
        return {}


def apply_formula_to_new_book(report: dict, topic: str, num_chapters: int = 30) -> str:
    """把逆向工程得出的公式应用到新书上，生成大纲"""
    from core import llm_invoke_ada
    
    template = report.get("replicable_template", {}).get("raw", "")
    
    prompt = f"""根据以下写作公式，为新书生成大纲：

[写作公式]
{template[:3000]}

[新书主题]
{topic}

[章节数]
{num_chapters}章

请生成完整章节大纲，格式：第XXX章: 标题 -- 50字概要
要求体现公式中的节奏、爽点分布、钩子技法。"""

    try:
        return llm_invoke_ada(prompt) or ""
    except Exception:
        return ""
