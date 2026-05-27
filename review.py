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