# -*- coding: utf-8 -*-
"""reader_sim.py --- AI模拟读者
三种读者视角同时读你的书，给出不同侧重点的反馈
"""

from datetime import datetime

READER_PROFILES = {
    "hardcore": {
        "name": "硬核书迷",
        "persona": "你是资深网文读者，看过上千本书。你对设定逻辑、战力体系、世界观一致性极度敏感。你能一眼看出战力崩坏、设定吃书、时间线矛盾。你的点评犀利但不恶意。",
        "focus": ["设定一致性", "战力体系", "世界观逻辑", "时间线", "伏笔质量"],
    },
    "casual": {
        "name": "小白读者",
        "persona": "你是轻度小说读者，每天睡前看半小时。你记不住太多角色名字，容易脸盲。你看重故事好不好懂、爽不爽、角色讨不讨喜。你的反馈代表大众读者。",
        "focus": ["可读性", "角色辨识度", "爽感", "情绪共鸣", "弃书风险"],
    },
    "editor": {
        "name": "编辑视角",
        "persona": "你是资深文学编辑，在出版行业干了15年。你关注节奏控制、剧情结构、文笔质量、商业化潜力。你能发现作者自己都没察觉的问题。你的建议专业且可操作。",
        "focus": ["节奏结构", "文笔技法", "商业潜力", "人物弧光", "修改建议"],
    },
}


def simulate_reader(chapter_text: str, reader_type: str = "hardcore",
                    chapter_num: int = 1, book_context: str = "") -> dict:
    """用指定读者类型读一章，给反馈"""
    profile = READER_PROFILES.get(reader_type, READER_PROFILES["hardcore"])
    
    from core import llm_invoke_ada
    
    prompt = f"""{profile['persona']}

你正在读一部小说的第{chapter_num}章。请基于以上身份给出你的阅读反馈。

[前文背景]
{book_context[:1000] if book_context else '无（这是开头章节）'}

[本章内容]
{chapter_text[:5000]}

请从以下角度给出反馈（每个2-3句话）：
{chr(10).join(f'- {f}' for f in profile['focus'])}

最后给本章打个总分(1-10)并给出一个最关键的建议。"""

    try:
        feedback = llm_invoke_ada(prompt)
        if feedback and not feedback.startswith('[错误'):
            return {
                "reader_type": reader_type,
                "reader_name": profile["name"],
                "chapter_num": chapter_num,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": "AI响应失败"}


def simulate_all_readers(chapter_text: str, chapter_num: int = 1,
                         book_context: str = "") -> list:
    """三个读者同时读，返回三种反馈"""
    results = []
    for rtype in ["hardcore", "casual", "editor"]:
        result = simulate_reader(chapter_text, rtype, chapter_num, book_context)
        results.append(result)
    return results


def predict_abandonment(chapters: list, book_context: str = "") -> dict:
    """预测读者弃书风险点
    
    Args:
        chapters: [(chapter_num, chapter_text), ...] 最近5-10章
    """
    from core import llm_invoke_ada
    
    combined = "\n\n".join([f"第{num}章:\n{text[:1500]}" for num, text in chapters])
    
    prompt = f"""你是一个读者行为分析专家。分析以下连续章节，预测读者可能会在哪个点放弃阅读。

{combined}

[全书背景]
{book_context[:800] if book_context else '无'}

请分析：
1. 哪一章最可能导致弃书？为什么？
2. 连续几章的情绪曲线如何？是否有长期低谷？
3. 读者的耐心在第几章会耗尽？
4. 给一个具体的挽救建议"""

    try:
        analysis = llm_invoke_ada(prompt)
        if analysis:
            return {"analysis": analysis, "chapters_analyzed": len(chapters)}
    except Exception:
        pass
    return {"error": "分析失败"}


def get_readability_score(chapter_text: str) -> dict:
    """可读性评分（不含AI，纯规则）"""
    import re
    
    # Average sentence length
    sentences = re.split(r'[。！？]', chapter_text)
    sentences = [s for s in sentences if s.strip()]
    avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    # Paragraph count
    paragraphs = [p for p in chapter_text.split('\n\n') if p.strip()]
    
    # Dialogue ratio
    dialog_markers = len(re.findall(r'["""'']', chapter_text))
    total_chars = len(chapter_text.replace('\n', '').replace(' ', ''))
    dialog_ratio = dialog_markers / max(total_chars, 1)
    
    # Paragraph length variance (good if varied)
    para_lens = [len(p) for p in paragraphs]
    avg_para = sum(para_lens) / max(len(para_lens), 1)
    if len(para_lens) > 1:
        variance = sum((l - avg_para) ** 2 for l in para_lens) / len(para_lens)
    else:
        variance = 0
    
    return {
        "avg_sentence_length": round(avg_len, 1),
        "paragraph_count": len(paragraphs),
        "avg_paragraph_length": round(avg_para, 1),
        "paragraph_variance": round(variance, 1),
        "dialogue_ratio": round(dialog_ratio, 2),
        "total_sentences": len(sentences),
    }
