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
