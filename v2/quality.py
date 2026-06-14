# -*- coding: utf-8 -*-
"""quality.py --- 四层文笔防线
Layer 1: 生成时约束（prompt注入）
Layer 2: 生成后6维评分
Layer 3: 低分自动重写（多版本择优）
Layer 4: 人性化终审（去工整、加不完美）
"""

import os, re, json, random
# core imports: use local imports within functions

# ---------------------------------------------------------------------------
# Layer 1: Generation-time constraints
# ---------------------------------------------------------------------------

def get_style_constraint_prompt(genre: str = "") -> str:
    """生成时注入的风格约束prompt"""
    base = """
[写作要求]
1. 句式多样化：禁止连续3句以上同样长度、同样结构
2. 对话要有"人味"：加入口语词（吧/嘛/呢/啊/啦）、打断、省略号
3. 少用"说"字：用"道/问/喊/低语/喃喃/笑道"等替换
4. 描写用五感：每场景至少调用2种感官（视/听/嗅/触/味）
5. 不要总结/说教：禁止"从此/总之/这告诉我们/由此可见"
6. 情绪要有起伏：同一段内不能全程平淡描写
7. 章节结尾留钩子：可以是悬念、情绪波动、或新信息
"""
    if genre == "玄幻":
        base += "\n8. 打斗描写要有节奏感，避免回合制叙述"
    elif genre == "都市":
        base += "\n8. 对话要口语化，加入网络用语和方言韵味"
    elif genre == "言情":
        base += "\n8. 情感描写要细腻，用动作和环境烘托心理"
    return base.strip()


# ---------------------------------------------------------------------------
# Layer 2: 6-dimension quality scoring
# ---------------------------------------------------------------------------

def score_chapter(chapter_text: str, chapter_num: int, target_words: int, 
                  prev_chapter: str = "", genre: str = "") -> dict:
    from core import count_words
    """6维评分：字数/ai词/对话密度/结尾钩子/连贯性/综合"""
    scores = {}
    details = []
    
    # 1. Word count score (0-100)
    wc = count_words(chapter_text)
    if wc >= target_words * 0.9:
        scores["words"] = 100
    elif wc >= target_words * 0.7:
        scores["words"] = 80
    elif wc >= target_words * 0.5:
        scores["words"] = 60
    else:
        scores["words"] = 40
    details.append(f"字数字数{wc}/{target_words}")
    
    # 2. AI word density (0-100): lower is better, so invert
    ai_patterns = [
        "总而言之", "综上所述", "不可否认", "显而易见", "值得注意的是",
        "在某种程度上", "从某种意义", "不仅而且", "与此同时",
        "然而", "因此", "所以", "于是", "接着", "随后",
        "缓缓", "深深", "不由得", "不禁", "默默",
    ]
    ai_count = sum(1 for p in ai_patterns if p in chapter_text)
    ai_score = max(0, 100 - ai_count * 5)
    scores["ai_words"] = ai_score
    if ai_count > 5:
        details.append(f"AI词多({ai_count}个)")
    
    # 3. Dialogue density (0-100)
    dialog_chars = len(re.findall(r'["""''](.*?)[""''\"]', chapter_text))
    total_chars = len(chapter_text.replace(" ", "").replace("\n", ""))
    dialog_ratio = dialog_chars / max(total_chars, 1)
    if 0.15 <= dialog_ratio <= 0.5:
        scores["dialog"] = 90
    elif 0.05 <= dialog_ratio <= 0.6:
        scores["dialog"] = 70
    else:
        scores["dialog"] = 40
    details.append(f"对话比{dialog_ratio:.0%}")
    
    # 4. Ending hook (0-100)
    ending = chapter_text[-300:]
    hook_patterns = ["?", "!", "难道", "忽然", "突然", "猛地", "就在这", "这时",
                      "...", "……", "心中一惊", "瞳孔", "没想到", "居然"]
    hook_count = sum(1 for p in hook_patterns if p in ending)
    scores["ending"] = min(100, hook_count * 15 + 30)
    
    # 5. Continuity (0-100)
    cont_score = 80  # Default
    if prev_chapter:
        prev_end = prev_chapter[-100:]
        if "说" in prev_end and chapter_text[:50].count('"') > 0:
            cont_score += 10
        if prev_chapter.rstrip()[-1] in "的了呢吗啊" and chapter_text[:2] in {"可是", "然而", "不过", "但是"}:
            cont_score -= 10
    scores["continuity"] = cont_score
    
    # 6. Overall
    total = sum(scores.values()) / len(scores)
    scores["total"] = round(total)
    
    # Star rating
    if total >= 85:
        star = "5星"
    elif total >= 70:
        star = "4星"
    elif total >= 55:
        star = "3星"
    elif total >= 40:
        star = "2星"
    else:
        star = "1星"
    scores["star"] = star
    scores["details"] = details
    
    return scores


# ---------------------------------------------------------------------------
# Layer 3: Multi-version generation + auto best-pick
# ---------------------------------------------------------------------------

def rewrite_chapter(original: str, genre: str, chapter_num: int,
                    target_words: int, prev_text: str = "",
                    custom_instruction: str = "") -> str:
    from core import llm_invoke_ada
    """重写章节（换个角度）"""
    angles = [
        "从不同角色的视角重新叙述本章事件",
        "增加更多环境和心理描写",
        "改写成更口语化、更自然的风格",
        "增加对话密度，让角色多互动",
        "压缩冗余描写，加快节奏",
    ]
    angle = random.choice(angles)
    if custom_instruction:
        angle = custom_instruction

    prompt = f"""重写以下小说章节，要求：{angle}

原始章节：
{original[:4000]}

目标字数：{target_words}字
注意事项：
- 保持核心情节不变
- 人物性格不偏离
- 去掉生硬的AI表达
- 自然流畅，像真人写的"""

    try:
        rewritten = llm_invoke_ada(prompt, system_msg=get_style_constraint_prompt(genre))
        return rewritten or original
    except Exception:
        return original


def generate_multi_version(book_dir: str, chapter_num: int, chapter_title: str,
                            context: dict, target_words: int, genre: str = "",
                            log_callback=None, stream_callback=None, stop_flag=None) -> str:
    from core import llm_invoke_ada
    """生成3个版本，自动选最优"""
    versions = []
    scores = []
    
    for v_idx in range(3):
        if stop_flag and stop_flag.is_set():
            break
        
        if log_callback:
            log_callback(f"  生成版本{v_idx+1}/3...")
        
        prompt = _build_multi_prompt(context, chapter_num, chapter_title, target_words, v_idx, genre)
        
        try:
            content = llm_invoke_ada(prompt, system_msg=get_style_constraint_prompt(genre))
            if content and not content.startswith("[错误]"):
                versions.append(content)
                sc = score_chapter(content, chapter_num, target_words)
                scores.append(sc)
                if log_callback:
                    log_callback(f"    版本{v_idx+1}: {sc['total']}分 {sc['star']}")
        except Exception as e:
            if log_callback:
                log_callback(f"    版本{v_idx+1}: 生成失败 - {e}")
    
    if not versions:
        return ""
    
    # Pick best
    best_idx = max(range(len(scores)), key=lambda i: scores[i]["total"])
    if log_callback:
        log_callback(f"  选择版本{best_idx+1} ({scores[best_idx]['total']}分)")
    
    return versions[best_idx]


def _build_multi_prompt(ctx: dict, chapter_num: int, chapter_title: str,
                        target_words: int, variant: int, genre: str) -> str:
    """为多版本生成构建不同的prompt"""
    base = f"""请续写小说章节。

章节信息：
- 第{chapter_num}章：{chapter_title}
- 目标字数：{target_words}字
- 类型：{genre or '小说'}

前文上下文：
{ctx.get('recent_summary', '')[:1500]}
"""

    variants = [
        "请以快节奏、高密度的方式写作，减少描写，增加剧情推进。",
        "请注重环境氛围和心理描写，让读者沉浸其中。",
        "请注重人物对话和互动，通过对话推进剧情。",
    ]
    
    base += f"\n{variants[variant]}\n"
    base += "\n注意：保持人物性格一致，情节合理推进，结尾留悬念。"
    return base


# ---------------------------------------------------------------------------
# Layer 4: Humanization (post-processing)
# ---------------------------------------------------------------------------

def humanize(text: str) -> str:
    """人性化终审：去工整、加不完美"""
    
    # 1. 随机打断过长段落
    lines = text.split("\n")
    result = []
    for line in lines:
        if len(line) > 200 and random.random() < 0.3:
            split_pos = line.find("。", len(line)//3)
            if split_pos > 0:
                result.append(line[:split_pos+1])
                result.append("")
                result.append(line[split_pos+1:])
                continue
        result.append(line)
    text = "\n".join(result)
    
    # 2. 刻意加省略号替换部分句号（概率性）
    if random.random() < 0.15:
        sentences = re.split(r'(?<=。)(?!")', text)
        for i in range(len(sentences)):
            if random.random() < 0.08 and sentences[i].strip():
                s = sentences[i]
                sentences[i] = s.rstrip("。") + "……"
        text = "".join(sentences)
    
    # 3. 长句随机拆分
    sentences = re.split(r'(?<=[。！？])(?!")', text)
    for i in range(len(sentences)):
        s = sentences[i]
        if len(s) > 80 and random.random() < 0.2:
            mid = s.find("，", len(s)//3)
            if mid > 0:
                sentences[i] = s[:mid+1] + "\n" + s[mid+1:]
    text = "".join(sentences)
    
    # 4. 随机插入口语化短句（3%概率）
    if random.random() < 0.03:
        fillers = ["说来也怪。", "真是的。", "这还不算完。", "谁能想到呢。", "就这样。"]
        paras = text.split("\n\n")
        if len(paras) > 3:
            idx = random.randint(1, len(paras)-2)
            paras.insert(idx, random.choice(fillers))
        text = "\n\n".join(paras)
    
    return text


# ---------------------------------------------------------------------------
# Full pipeline: generate -> score -> rewrite if needed -> humanize
# ---------------------------------------------------------------------------

def quality_pipeline(content: str, chapter_num: int, target_words: int,
                     genre: str = "", prev_text: str = "", 
                     context: dict = None, book_dir: str = "",
                     log_callback=None) -> dict:
    """完整质量流水线"""
    result = {
        "content": content,
        "score": None,
        "rewrites": 0,
        "humanized": False,
    }
    
    # Score
    result["score"] = score_chapter(content, chapter_num, target_words, prev_text, genre)
    
    if log_callback:
        log_callback(f"  评分: {result['score']['total']}分 {result['score']['star']}")
        for d in result['score'].get('details', []):
            log_callback(f"    {d}")
    
    # Rewrite if low
    if result["score"]["total"] < 65:
        if log_callback:
            log_callback("  分数偏低，触发重写...")
        content = rewrite_chapter(content, genre, chapter_num, target_words, prev_text)
        result["rewrites"] += 1
        result["score"] = score_chapter(content, chapter_num, target_words, prev_text, genre)
        if log_callback:
            log_callback(f"  重写后: {result['score']['total']}分")
    
    # Humanize
    content = humanize(content)
    result["humanized"] = True
    result["content"] = content
    
    return result
