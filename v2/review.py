# review.py — 质量审查模块
# 拆书/审稿/一致性核验/毒点检测

import os
from core import llm_invoke_ada, read_file, write_file
from prompts import REVIEW_CHAPTER, CONSISTENCY_CHECK_PROMPT


def review_chapter(chapter_text: str, novel_setting: str = "",
                   log_callback=None) -> str:
    prompt = REVIEW_CHAPTER.format(
        novel_setting=novel_setting or "（未提供设定）",
        chapter_text=chapter_text)
    return llm_invoke_ada(prompt,
        system_msg="你是一位严格的网文审稿编辑。请输出每个维度的审查结果。")


def review_book(book_dir: str, log_callback=None) -> list:
    chapter_dir = os.path.join(book_dir, "正文")
    if not os.path.exists(chapter_dir):
        if log_callback:
            log_callback("未找到正文目录")
        return []
    setting = read_file(os.path.join(book_dir, "设定.md"))
    chapters = sorted([f for f in os.listdir(chapter_dir) if f.endswith('.md')])
    results = []
    for ch_file in chapters:
        if log_callback:
            log_callback(f"审查: {ch_file}...")
        text = read_file(os.path.join(chapter_dir, ch_file))
        result = review_chapter(text, setting)
        results.append({"chapter": ch_file, "review": result})
        review_dir = os.path.join(book_dir, "审稿")
        os.makedirs(review_dir, exist_ok=True)
        write_file(os.path.join(review_dir, ch_file), result)
    if log_callback:
        log_callback(f"审稿完成 ({len(results)} 章)")
    return results


TOXICITY_CHECK_PROMPT = """你是一位严格的网文毒点检测编辑。请审查以下章节，找出所有可能让读者反感的毒点。

章节文本：
{chapter_text}

检查以下毒点：
1. **圣母情节**：主角无原则原谅敌人
2. **降智操作**：角色做出不符合人设的愚蠢行为
3. **机械降神**：关键时刻靠巧合/外力解决问题
4. **主角话痨**：战斗中废话过多
5. **注水/拖戏**：大量无意义对话或描写

输出格式：
## 毒点检测报告

| 毒点类型 | 位置 | 具体描述 | 严重程度 |
|---------|------|---------|---------|
| ... | ... | ... | 高/中/低 |
"""


def consistency_check(book_dir: str, log_callback=None) -> str:
    """扫描全书，检测境界跳跃、角色凭空出现、时间线矛盾"""
    novel_setting = read_file(os.path.join(book_dir, "设定.md"))
    if not novel_setting:
        return "未找到设定文件"
    chapter_dir = os.path.join(book_dir, "正文")
    if not os.path.exists(chapter_dir):
        return "未找到正文目录"
    chapters = sorted([f for f in os.listdir(chapter_dir) if f.endswith('.md')])
    chapters_text = ""
    for fname in chapters[:20]:
        content = read_file(os.path.join(chapter_dir, fname))
        chapters_text += f"\n--- {fname} ---\n{content[:3000]}\n"
    if log_callback:
        log_callback("正在进行一致性检查...")
    result = llm_invoke_ada(
        CONSISTENCY_CHECK_PROMPT.format(
            novel_setting=novel_setting[:4000],
            chapters_text=chapters_text[:8000]),
        system_msg="你是一位严格的网文校对编辑。请输出格式化检查报告。")
    report_path = os.path.join(book_dir, "一致性检查报告.md")
    write_file(report_path, result)
    return result


def toxicity_check(chapter_text: str, log_callback=None) -> str:
    prompt = TOXICITY_CHECK_PROMPT.format(chapter_text=chapter_text[:8000])
    if log_callback:
        log_callback("正在进行毒点检测...")
    return llm_invoke_ada(prompt,
        system_msg="你是一位严格的网文毒点检测编辑。请输出格式化检测报告。")

# ═══════════════════════════════════════════════════════════
# 阶段二: 增强一致性检查
# ═══════════════════════════════════════════════════════════

def full_consistency_check(book_dir: str, log_callback=None) -> dict:
    """全面一致性检查：时间线、角色、设定、伏笔"""
    from core import read_file, count_words
    from project import load_foreshadow_table, get_unresolved_foreshadows, load_knowledge_json
    import os, re

    results = {"issues": [], "warnings": [], "info": []}
    ch_dir = os.path.join(book_dir, "正文")
    if not os.path.isdir(ch_dir):
        results["issues"].append("正文目录不存在")
        return results

    chapters = sorted([f for f in os.listdir(ch_dir) if f.endswith('.md')])
    if not chapters:
        results["issues"].append("无章节文件")
        return results

    if log_callback:
        log_callback(f"检查 {len(chapters)} 个章节...")

    # 1. 字数检查
    for f in chapters:
        content = read_file(os.path.join(ch_dir, f))
        wc = count_words(content)
        if wc < 500:
            results["warnings"].append(f"{f}: 字数过少({wc}字)")
        elif wc < 1000:
            results["warnings"].append(f"{f}: 字数偏少({wc}字)")

    # 2. AI 词密度检查
    from deslop import scan_ai_words
    total_ai = 0
    for f in chapters:
        content = read_file(os.path.join(ch_dir, f))
        hits = scan_ai_words(content)
        total_ai += len(hits)
        if len(hits) > 15:
            results["warnings"].append(f"{f}: AI词过多({len(hits)}处)")
    results["info"].append(f"AI词总计: {total_ai}处")

    # 3. 角色一致性
    char_file = os.path.join(book_dir, "角色档案.md")
    if os.path.isfile(char_file):
        char_text = read_file(char_file)
        char_names = re.findall(r'(?:姓名|名字)[：:]\s*(\S+)', char_text)
        if char_names:
            # 检查角色名在各章中的出现
            first_appear = {}
            for f in chapters:
                content = read_file(os.path.join(ch_dir, f))
                for name in char_names:
                    if name in content and name not in first_appear:
                        first_appear[name] = f
            results["info"].append(f"角色出场: {len(first_appear)}/{len(char_names)}")

    # 4. 伏笔检查
    unresolved = get_unresolved_foreshadows(book_dir)
    if unresolved:
        results["warnings"].append(f"未回收伏笔: {len(unresolved)}条")
        for fs in unresolved[:5]:
            results["info"].append(f"  伏笔#{fs['id']}: {fs['content'][:30]}...")

    # 5. 章节连续性检查（相邻章节）
    prev_content = ""
    for f in chapters:
        content = read_file(os.path.join(ch_dir, f))
        if prev_content:
            # 检查时间词连续性
            time_words_prev = re.findall(r'(?:第[一二三四五六七八九十\d]+天|次日|翌日|当天|傍晚|清晨|深夜|黎明)', prev_content)
            time_words_curr = re.findall(r'(?:第[一二三四五六七八九十\d]+天|次日|翌日|当天|傍晚|清晨|深夜|黎明)', content)
            if time_words_prev and time_words_curr:
                results["info"].append(f"{f}: 时间标记 {time_words_curr[-1] if time_words_curr else '?'}")
        prev_content = content

    results["total_chapters"] = len(chapters)
    results["total_issues"] = len(results["issues"])
    results["total_warnings"] = len(results["warnings"])

    if log_callback:
        log_callback(f"检查完成: {results['total_issues']} 问题, {results['total_warnings']} 警告")

    return results


def style_deviation_check(chapter_text: str, book_dir: str) -> dict:
    """风格偏差检测：对比新章节与已有风格指纹"""
    from project import load_knowledge_json
    import re

    fp = load_knowledge_json(book_dir, "风格指纹")
    if not fp:
        return {"deviation": 0, "details": "无风格指纹数据"}

    details = []
    score = 0

    # 句长偏差
    sentences = re.split(r'[。！？]', chapter_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        fp_avg = fp.get("avg_sentence_len", 30)
        if abs(avg_len - fp_avg) > 15:
            score += 1
            details.append(f"句长偏差: 当前{avg_len:.0f} vs 基准{fp_avg:.0f}")

    # 对话密度偏差
    dialog_count = len(re.findall(r'[""「」『』]', chapter_text)) // 2
    dialog_ratio = dialog_count / max(len(sentences), 1)
    fp_dialog = fp.get("dialog_ratio", 0.2)
    if abs(dialog_ratio - fp_dialog) > 0.15:
        score += 1
        details.append(f"对话密度偏差: 当前{dialog_ratio:.2f} vs 基准{fp_dialog:.2f}")

    return {"deviation": score, "details": "; ".join(details) if details else "风格一致"}
