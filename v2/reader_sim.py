# -*- coding: utf-8 -*-
"""reader_sim.py --- AI模拟读者
支持：单章分析 / 全书导入 / 全本批量分析 / 6类读者群体 / 弃书预测 / 情绪曲线
"""

import os, re, json
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
    "fangirl": {
        "name": "狂热粉丝",
        "persona": "你是这本书的狂热粉丝，已经三刷了。你对每个角色都充满感情，会脑补CP、写同人。你的反馈代表核心粉丝群体——他们是最可能付费和安利的人。",
        "focus": ["角色魅力", "CP感", "名场面", "情感爆点", "粉丝二创潜力"],
    },
    "skeptic": {
        "name": "毒舌喷子",
        "persona": "你是一星差评专业户，对网文极其挑剔。你讨厌套路、讨厌注水、讨厌逻辑漏洞。你的存在是为了找出这本书所有可能被喷的点，帮作者提前堵枪眼。",
        "focus": ["套路检测", "注水段落", "逻辑漏洞", "毒点", "一星理由"],
    },
    "newcomer": {
        "name": "纯路人",
        "persona": "你从没看过这个作者的书，偶然点进来。你没有耐心，前3章抓不住你就走。你的反馈代表最大量的路人读者——他们决定了书的流量天花板。",
        "focus": ["入坑门槛", "前3章吸引力", "设定理解难度", "是否需要前作知识", "会不会推荐给朋友"],
    },
}


def load_book(file_path: str) -> dict:
    """加载一本书，自动切分章节
    
    Returns: {title, chapters: [{num, text, length}], total_words}
    """
    from core import read_file, count_words
    
    text = read_file(file_path)
    if not text:
        return {"error": f"无法读取文件: {file_path}"}
    
    title = os.path.splitext(os.path.basename(file_path))[0]
    
    # Smart chapter splitting
    chapters = _split_chapters(text)
    
    if not chapters:
        # Fallback: treat whole thing as one chapter
        chapters = [{"num": 1, "text": text, "length": len(text)}]
    
    total_words = sum(c["length"] for c in chapters)
    
    return {
        "title": title,
        "file_path": file_path,
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_words": total_words,
    }


def _split_chapters(text: str) -> list:
    """智能章节切分"""
    # Multiple patterns for chapter headings
    patterns = [
        r'\n(?=第[零一二三四五六七八九十百千\d]+[章回节卷])',
        r'\n(?=[Cc]hapter\s+\d+)',
        r'\n(?=#+\s*第[零一二三四五六七八九十百千\d]+[章回节卷])',
    ]
    
    for pattern in patterns:
        parts = re.split(pattern, text)
        if len(parts) > 1:
            break
    
    if len(parts) <= 1:
        # Try splitting by blank lines into large chunks
        parts = re.split(r'\n{3,}', text)
    
    chapters = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        if len(p) < 100 and i > 0:
            # Too short to be a real chapter, merge with previous
            if chapters:
                chapters[-1]["text"] += "\n" + p
                chapters[-1]["length"] += len(p)
            continue
        chapters.append({
            "num": len(chapters) + 1,
            "text": p,
            "length": len(p),
        })
    
    return chapters


def simulate_reader(chapter_text: str, reader_type: str = "hardcore",
                    chapter_num: int = 1, book_context: str = "") -> dict:
    """用指定读者类型读一章，给反馈"""
    profile = READER_PROFILES.get(reader_type, READER_PROFILES["hardcore"])
    
    from core import llm_invoke_ada
    
    prompt = f"""{profile['persona']}

你正在读一部小说的第{chapter_num}章。请基于以上身份给出你的阅读反馈。

[前文背景]
{book_context[:1500] if book_context else '无（这是开头章节）'}

[本章内容]
{chapter_text[:6000]}

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
                         book_context: str = "",
                         reader_types: list = None) -> list:
    """多个读者同时读，返回多种反馈
    
    Args:
        reader_types: 指定读者类型列表，默认全部6种
    """
    if reader_types is None:
        reader_types = list(READER_PROFILES.keys())
    
    results = []
    for rtype in reader_types:
        result = simulate_reader(chapter_text, rtype, chapter_num, book_context)
        results.append(result)
    return results


def analyze_full_book(book_data: dict, log_callback=None,
                      reader_types: list = None) -> dict:
    """全书级分析：逐章+全局
    
    Args:
        book_data: load_book()的返回结果
        reader_types: 读者类型列表，默认用casual+hardcore+editor三种
        log_callback: 进度回调
    
    Returns: {
        title, total_chapters, total_words,
        chapter_analyses: [{chapter_num, scores, feedbacks, issues}],
        overall: {avg_score, score_trend, best_chapter, worst_chapter,
                   abandonment_risk, emotion_curve, global_issues},
    }
    """
    if reader_types is None:
        reader_types = ["hardcore", "casual", "editor"]
    
    chapters = book_data.get("chapters", [])
    total = len(chapters)
    
    if not chapters:
        return {"error": "无章节数据"}
    
    chapter_analyses = []
    
    # Build progressive context
    context_buffer = ""
    
    for ch in chapters:
        num = ch["num"]
        if log_callback:
            log_callback(f"分析第{num}/{total}章...")
        
        # Get multi-reader feedback
        feedbacks = simulate_all_readers(
            ch["text"], num, context_buffer, reader_types
        )
        
        # Extract scores
        scores = {}
        for fb in feedbacks:
            rtype = fb.get("reader_type", "?")
            score = _extract_score(fb.get("feedback", ""))
            scores[rtype] = score
        
        # Rule-based readability
        readability = get_readability_score(ch["text"])
        
        # AI word density scan
        ai_hits = scan_ai_markers(ch["text"])
        
        chapter_analyses.append({
            "chapter_num": num,
            "word_count": ch["length"],
            "scores": scores,
            "avg_score": round(sum(scores.values()) / max(len(scores), 1), 1),
            "feedbacks": feedbacks,
            "readability": readability,
            "ai_marker_count": len(ai_hits),
            "ai_markers": ai_hits[:5],
        })
        
        # Update context buffer (keep last 3000 chars)
        context_buffer = (context_buffer + "\n" + ch["text"][:1000])[-3000:]
    
    # Global analysis
    all_scores = [ca["avg_score"] for ca in chapter_analyses]
    avg_score = round(sum(all_scores) / max(len(all_scores), 1), 1)
    
    # Find best/worst
    best_idx = all_scores.index(max(all_scores)) if all_scores else 0
    worst_idx = all_scores.index(min(all_scores)) if all_scores else 0
    
    # Score trend (simple linear regression gradient)
    score_trend = _calc_trend(all_scores)
    
    # Abandonment risk
    abandonment_risk = _analyze_abandonment_risk(chapter_analyses)
    
    # Emotion curve
    emotion_curve = _build_emotion_curve(chapter_analyses)
    
    # Global issues aggregation
    global_issues = _aggregate_issues(chapter_analyses)
    
    overall = {
        "avg_score": avg_score,
        "score_trend": score_trend,
        "score_trend_desc": "上升趋势" if score_trend > 0.05 else "下降趋势" if score_trend < -0.05 else "平稳",
        "best_chapter": best_idx + 1,
        "best_score": max(all_scores) if all_scores else 0,
        "worst_chapter": worst_idx + 1,
        "worst_score": min(all_scores) if all_scores else 0,
        "abandonment_risk": abandonment_risk,
        "emotion_curve": emotion_curve,
        "global_issues": global_issues,
    }
    
    return {
        "title": book_data.get("title", ""),
        "total_chapters": total,
        "total_words": book_data.get("total_words", 0),
        "chapter_analyses": chapter_analyses,
        "overall": overall,
        "timestamp": datetime.now().isoformat(),
    }


def _extract_score(feedback: str) -> float:
    """从反馈中提取评分"""
    # Pattern: "总分：X" or "评分：X" or "X/10" or "X分"
    patterns = [
        r'(?:总分|评分|打分)[：:]\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*/?\s*10\s*分',
        r'(\d+(?:\.\d+)?)\s*分\b',
    ]
    for p in patterns:
        m = re.search(p, feedback)
        if m:
            score = float(m.group(1))
            return min(10, max(1, score))
    return 5.0  # Default


def _calc_trend(scores: list) -> float:
    """计算分数趋势（简易线性回归斜率）"""
    if len(scores) < 2:
        return 0.0
    n = len(scores)
    x_mean = (n - 1) / 2
    y_mean = sum(scores) / n
    numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _analyze_abandonment_risk(analyses: list) -> dict:
    """分析弃书风险"""
    if not analyses:
        return {"risk": "unknown", "level": 0}
    
    # Find low-score chapters
    low_chapters = [ca for ca in analyses if ca["avg_score"] < 5.0]
    
    # Find consecutive low streaks
    max_streak = 0
    current_streak = 0
    streak_start = 0
    worst_streak_start = 0
    
    for i, ca in enumerate(analyses):
        if ca["avg_score"] < 5.5:
            if current_streak == 0:
                streak_start = ca["chapter_num"]
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                worst_streak_start = streak_start
        else:
            current_streak = 0
    
    # Risk assessment
    total = len(analyses)
    low_ratio = len(low_chapters) / total if total > 0 else 0
    
    if max_streak >= 5 or low_ratio > 0.5:
        risk_level = "极高"
        risk_color = "red"
    elif max_streak >= 3 or low_ratio > 0.3:
        risk_level = "高"
        risk_color = "orange"
    elif max_streak >= 2 or low_ratio > 0.15:
        risk_level = "中"
        risk_color = "yellow"
    else:
        risk_level = "低"
        risk_color = "green"
    
    return {
        "risk": risk_level,
        "risk_color": risk_color,
        "low_chapters": [c["chapter_num"] for c in low_chapters],
        "low_ratio": round(low_ratio, 2),
        "max_consecutive_low": max_streak,
        "worst_streak_from": worst_streak_start if max_streak > 0 else 0,
    }


def _build_emotion_curve(analyses: list) -> list:
    """构建情绪曲线（简化版：基于可读性数据的句子长度方差）"""
    curve = []
    for ca in analyses:
        rd = ca.get("readability", {})
        variance = rd.get("paragraph_variance", 0)
        
        # Higher variance = more emotional variety
        if variance > 500:
            mood = "激烈"
        elif variance > 200:
            mood = "起伏"
        elif variance > 100:
            mood = "温和"
        else:
            mood = "平淡"
        
        curve.append({
            "chapter": ca["chapter_num"],
            "mood": mood,
            "score": ca["avg_score"],
        })
    return curve


def _aggregate_issues(analyses: list) -> list:
    """聚合全书共性问题"""
    issues = []
    
    # Check AI marker accumulation
    total_ai = sum(ca.get("ai_marker_count", 0) for ca in analyses)
    high_ai_chapters = [ca["chapter_num"] for ca in analyses if ca.get("ai_marker_count", 0) > 10]
    if high_ai_chapters:
        issues.append({
            "type": "AI痕迹",
            "severity": "高" if total_ai > 100 else "中",
            "detail": f"共{total_ai}处AI痕迹，集中在第{min(high_ai_chapters)}-{max(high_ai_chapters)}章",
        })
    
    # Check short chapters
    short_chapters = [ca["chapter_num"] for ca in analyses if ca.get("word_count", 0) < 800]
    if short_chapters:
        issues.append({
            "type": "章节过短",
            "severity": "中",
            "detail": f"第{short_chapters[0] if len(short_chapters)==1 else f'{len(short_chapters)}章'}字数不足800",
        })
    
    # Check score variance
    scores = [ca["avg_score"] for ca in analyses]
    if len(scores) > 1:
        score_range = max(scores) - min(scores)
        if score_range > 4:
            issues.append({
                "type": "质量波动大",
                "severity": "高",
                "detail": f"章节评分波动{score_range:.1f}分，读者体验不稳定",
            })
    
    return issues


def scan_ai_markers(text: str) -> list:
    """扫描AI写作痕迹标记词"""
    markers = [
        "总的来说", "总而言之", "综上所述", "毫无疑问", "不可否认",
        "不仅……而且", "与此同时", "在这种情况下", "值得注意的是",
        "然而", "因此", "所以", "于是", "紧接着", "随后",
        "深深地", "无比", "极其", "格外", "异常",
        "嘴角微微上扬", "眼中闪过一丝", "深吸一口气", "缓缓地",
        "并非", "展现出了", "起到了……作用", "毋庸置疑",
        "在这个过程当中", "可以理解为", "严格意义上来说",
    ]
    hits = []
    text_clean = text.replace('\n', '').replace(' ', '')
    for marker in markers:
        count = text_clean.count(marker)
        if count > 0:
            hits.append({"marker": marker, "count": count})
    return sorted(hits, key=lambda x: x["count"], reverse=True)


def predict_abandonment(chapters: list, book_context: str = "") -> dict:
    """预测读者弃书风险点（使用AI）
    
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
    """可读性评分（纯规则，不调AI）"""
    # Average sentence length
    sentences = re.split(r'[。！？]', chapter_text)
    sentences = [s for s in sentences if s.strip()]
    avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    # Paragraph count
    paragraphs = [p for p in chapter_text.split('\n\n') if p.strip()]
    
    # Dialogue ratio
    dialog_markers = len(re.findall(r'[""''""]', chapter_text))
    total_chars = max(len(chapter_text.replace('\n', '').replace(' ', '')), 1)
    dialog_ratio = dialog_markers / total_chars
    
    # Paragraph length variance
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


def generate_full_book_report(analysis: dict, fmt: str = "markdown") -> str:
    """生成全书分析报告"""
    overall = analysis.get("overall", {})
    ca_list = analysis.get("chapter_analyses", [])
    
    if fmt == "markdown":
        lines = [
            f"# 📖 全书读者分析报告",
            f"",
            f"**作品**：{analysis.get('title', '未命名')}",
            f"**总章节**：{analysis.get('total_chapters', 0)}",
            f"**总字数**：{analysis.get('total_words', 0):,}",
            f"**分析时间**：{analysis.get('timestamp', '')}",
            f"",
            f"## 总览",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 综合评分 | {overall.get('avg_score', 0)}/10 |",
            f"| 分数趋势 | {overall.get('score_trend_desc', '')} |",
            f"| 最佳章节 | 第{overall.get('best_chapter', 0)}章 ({overall.get('best_score', 0)}分) |",
            f"| 最差章节 | 第{overall.get('worst_chapter', 0)}章 ({overall.get('worst_score', 0)}分) |",
            f"| 弃书风险 | {overall.get('abandonment_risk', {}).get('risk', '?')} |",
            f"",
            f"## 情绪曲线",
            f"```",
        ]
        
        ec = overall.get("emotion_curve", [])
        if ec:
            # Simple ASCII chart
            for point in ec:
                bar = "█" * int(point["score"])
                lines.append(f"第{point['chapter']:>3}章 [{point['mood']}] {bar} {point['score']}")
        
        lines += [
            f"```",
            f"",
            f"## 全局问题",
        ]
        
        issues = overall.get("global_issues", [])
        if issues:
            for iss in issues:
                lines.append(f"- **[{iss['severity']}] {iss['type']}**：{iss['detail']}")
        else:
            lines.append("未检测到明显的全局问题。")
        
        lines += [
            f"",
            f"## 逐章数据",
            f"",
            f"| 章节 | 字数 | 评分 | AI痕迹 | 句长 | 对话比 |",
            f"|------|------|------|--------|------|--------|",
        ]
        
        for ca in ca_list[:50]:  # Limit to 50 chapters
            rd = ca.get("readability", {})
            lines.append(
                f"| {ca['chapter_num']} | {ca['word_count']:,} | {ca['avg_score']} | {ca['ai_marker_count']} | "
                f"{rd.get('avg_sentence_length', 0)} | {rd.get('dialogue_ratio', 0):.1%} |"
            )
        
        if len(ca_list) > 50:
            lines.append(f"| ... | ... | ... | ... | ... | ... |")
            lines.append(f"| *共{len(ca_list)}章* | | | | | |")
        
        return "\n".join(lines)
    
    elif fmt == "json":
        return json.dumps(analysis, ensure_ascii=False, indent=2)
    
    return ""


def generate_chapter_feedback_report(analysis: dict, chapter_num: int) -> str:
    """生成单章详细反馈（含6种读者反馈）"""
    ca_list = analysis.get("chapter_analyses", [])
    target = None
    for ca in ca_list:
        if ca["chapter_num"] == chapter_num:
            target = ca
            break
    
    if not target:
        return f"未找到第{chapter_num}章数据"
    
    lines = [
        f"# 第{chapter_num}章 — 读者反馈详细报告",
        f"",
        f"**字数**：{target['word_count']:,}  |  **综合评分**：{target['avg_score']}/10",
        f"",
        f"---",
    ]
    
    for fb in target.get("feedbacks", []):
        lines.append(f"")
        lines.append(f"## {fb.get('reader_name', '?')}")
        lines.append(f"")
        lines.append(fb.get("feedback", "无反馈"))
        lines.append(f"")
        lines.append(f"---")
    
    lines.append(f"")
    lines.append(f"## 可读性数据")
    rd = target.get("readability", {})
    lines.append(f"- 平均句长：{rd.get('avg_sentence_length', 0)} 字符")
    lines.append(f"- 段落数：{rd.get('paragraph_count', 0)}")
    lines.append(f"- 对话占比：{rd.get('dialogue_ratio', 0):.1%}")
    lines.append(f"- AI痕迹：{target.get('ai_marker_count', 0)} 处")
    
    return "\n".join(lines)
