# cover.py — 封面生成模块
# 参考 oh-story-cover 的提示词方案

from core import llm_invoke_ada
from prompts import COVER_PROMPT_GENERATION


def generate_cover_prompt(book_name: str, genre: str,
                          core_appeal: str = "", protagonist: str = "") -> str:
    """根据小说信息生成 AI 绘图提示词"""
    prompt = COVER_PROMPT_GENERATION.format(
        book_name=book_name,
        genre=genre,
        core_appeal=core_appeal or f"一部{genre}小说",
        protagonist=protagonist or book_name
    )

    result = llm_invoke_ada(
        prompt,
        system_msg="你是一位专业的封面设计师。请生成高质量的绘图提示词。"
    )

    return result


def generate_novel_cover(book_name: str, genre: str,
                         settings_dir: str = "",
                         log_callback=None) -> dict:
    """
    生成本地提示词（后续可配合 DALL-E / Midjourney 等使用）
    
    Returns:
        dict: {"prompt": str, "revision": str}
    """
    # 尝试从设定文件中提取关键信息
    core_appeal = ""
    protagonist = ""

    if settings_dir:
        import os
        setting_file = os.path.join(settings_dir, "设定.md")
        if os.path.exists(setting_file):
            from core import read_file
            text = read_file(setting_file)
            # 提取角色和核心卖点
            lines = text.split('\n')
            for line in lines:
                if '主角' in line or '核心' in line:
                    if not protagonist and '主角' in line:
                        # 取这行和下一行
                        idx = lines.index(line)
                        if idx + 1 < len(lines):
                            protagonist = lines[idx + 1]
                    if '核心' in line:
                        core_appeal = line

    prompt = generate_cover_prompt(book_name, genre, core_appeal, protagonist)

    if log_callback:
        log_callback(f"✅ 封面提示词已生成")
        log_callback(f"\n{prompt}")

    return {"prompt": prompt}

# review.py — 质量审查模块

import os
from core import llm_invoke_ada, read_file, write_file
from prompts import REVIEW_CHAPTER


def review_chapter(chapter_text: str, novel_setting: str = "",
                   log_callback=None) -> str:
    """审查单个章节"""
    prompt = REVIEW_CHAPTER.format(
        novel_setting=novel_setting or "（未提供设定）",
        chapter_text=chapter_text
    )

    result = llm_invoke_ada(
        prompt,
        system_msg="你是一位严格的网文审稿编辑。请输出每个维度的审查结果。"
    )

    return result


def review_book(book_dir: str, log_callback=None) -> list:
    """审查一本小说的所有章节"""
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

        # 保存审稿结果
        review_dir = os.path.join(book_dir, "审稿")
        os.makedirs(review_dir, exist_ok=True)
        write_file(os.path.join(review_dir, ch_file), result)

    if log_callback:
        log_callback(f"✅ 审稿完成 ({len(results)} 章)")

    return results