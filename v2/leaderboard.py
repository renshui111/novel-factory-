# -*- coding: utf-8 -*-
"""leaderboard.py --- 排行榜模拟器
模拟网文平台排行榜：AI预测推荐票/收藏/追读/月票，给出竞争力分析
"""

import json, os, re, random
from datetime import datetime


LEADERBOARD_TYPES = {
    "recommend": "推荐票榜",
    "collection": "收藏榜",
    "monthly": "月票榜",
    "hot": "热销榜",
    "newbook": "新人榜",
    "read": "追读榜",
}

READER_POOL = {
    "快餐党": {"weight": 0.35, "prefer": ["爽文", "快节奏", "打脸", "升级"], "dislike": ["慢热", "大段描写", "文绉绉"]},
    "设定党": {"weight": 0.20, "prefer": ["创新设定", "世界观完整", "逻辑自洽", "独特体系"], "dislike": ["套路化", "设定吃书", "战力崩坏"]},
    "感情党": {"weight": 0.18, "prefer": ["感情线", "人物互动", "CP感", "细腻描写"], "dislike": ["纯打斗", "后宫无脑", "感情突兀"]},
    "考据党": {"weight": 0.12, "prefer": ["历史严谨", "细节真实", "考据充分", "专业感"], "dislike": ["常识错误", "历史穿越漏洞", "不严谨"]},
    "猎奇党": {"weight": 0.10, "prefer": ["脑洞大", "反套路", "新奇设定", "意想不到"], "dislike": ["老套路", "一眼看到底", "平淡"]},
    "文艺党": {"weight": 0.05, "prefer": ["文笔好", "意境美", "哲学思考", "文学性"], "dislike": ["小白文", "流水账", "无深度"]},
}


def simulate_leaderboard(chapters: list, book_name: str = "",
                         genre: str = "玄幻", word_count: int = 0,
                         log_callback=None) -> dict:
    """模拟一本书在各榜单的表现
    
    Args:
        chapters: [(chapter_num, chapter_text, word_count), ...]
        book_name: 书名
        genre: 类型
        word_count: 总字数
    
    Returns:
        {
            rankings: {榜单名: {rank, score, total_books}},
            reader_votes: {读者类型: 投票},
            competitiveness: 竞争力评估,
            suggestion: 冲榜建议
        }
    """
    from core import llm_invoke_ada, count_words
    
    if not chapters:
        return {"error": "无章节数据"}
    
    # Build analysis context
    sample_chapters = chapters[:5] + chapters[len(chapters)//2:len(chapters)//2+3] + chapters[-3:]
    
    combined = "\n\n".join([
        f"第{num}章 ({wc}字):\n{text[:1500] if text else ''}"
        for num, text, wc in sample_chapters
    ])
    
    if log_callback:
        log_callback("AI正在分析作品竞争力...")
    
    prompt = f"""你是网文平台的资深数据编辑，请分析以下作品在各大排行榜的竞争力：

[书名]
{book_name or '未命名'}

[类型]
{genre}

[总字数]
{word_count:,}字

[章节样本]
{combined[:8000]}

请从以下维度给出预测（每个用1-10分）：

1. **推荐票吸引力**：读者愿意投推荐票的程度
   - 爽点密度 / 节奏 / 钩子质量
2. **收藏转化率**：读者看完免费章节后收藏的概率
   - 黄金三章 / 设定新颖度 / 期待感
3. **追读率**：读者每天追更的意愿
   - 章尾钩子 / 连续高潮 / 断章水平
4. **月票潜力**：读者花钱投票的意愿
   - 付费点设计 / 情感共鸣 / 人物魅力
5. **新人友好度**：新读者入坑的难度
   - 开头可读性 / 设定复杂度 / 阅读门槛

用以下结构化格式输出：
## 评分
| 榜单维度 | 评分(1-10) | 关键理由 |
|---------|-----------|---------|
| ... | ... | ... |

## 预估数据
- 预估收藏/追读比：___%
- 预估首日均订：___
- 预估30万字时收藏：___
- 最可能上榜：___

## 冲榜建议
3条具体的改稿/运营建议"""

    try:
        analysis = llm_invoke_ada(prompt)
        if not analysis or analysis.startswith('[错误'):
            analysis = "AI分析暂不可用，请检查API配置"
    except Exception as e:
        analysis = f"分析失败: {e}"
    
    # Simulate reader votes
    if log_callback:
        log_callback("模拟读者投票中...")
    
    reader_votes = _simulate_reader_votes(chapters, genre)
    
    # Build ranking simulation
    rankings = {}
    base_score = reader_votes.get("total_score", 5.0)
    
    rankings["recommend"] = {
        "rank": _estimate_rank(base_score * 1.1, "recommend"),
        "score": round(base_score * 1.1, 1),
        "total_books": 10000 + random.randint(0, 5000),
    }
    rankings["collection"] = {
        "rank": _estimate_rank(base_score * 0.95, "collection"),
        "score": round(base_score * 0.95, 1),
        "total_books": 50000 + random.randint(0, 20000),
    }
    rankings["monthly"] = {
        "rank": _estimate_rank(base_score * 0.85, "monthly"),
        "score": round(base_score * 0.85, 1),
        "total_books": 8000 + random.randint(0, 3000),
    }
    rankings["hot"] = {
        "rank": _estimate_rank(base_score * 1.0, "hot"),
        "score": round(base_score, 1),
        "total_books": 20000 + random.randint(0, 8000),
    }
    rankings["newbook"] = {
        "rank": _estimate_rank(base_score * 1.15, "newbook"),
        "score": round(base_score * 1.15, 1),
        "total_books": 3000 + random.randint(0, 2000),
    }
    rankings["read"] = {
        "rank": _estimate_rank(base_score * 0.9, "read"),
        "score": round(base_score * 0.9, 1),
        "total_books": 15000 + random.randint(0, 6000),
    }
    
    return {
        "book_name": book_name,
        "genre": genre,
        "word_count": word_count,
        "rankings": rankings,
        "reader_votes": reader_votes,
        "ai_analysis": analysis,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _estimate_rank(score: float, lb_type: str) -> int:
    """根据分数估算排名 (排名越低越好)"""
    # score 1-10, map to rank 1-5000
    if score >= 9.5:
        base = random.randint(1, 50)
    elif score >= 9.0:
        base = random.randint(20, 100)
    elif score >= 8.5:
        base = random.randint(50, 200)
    elif score >= 8.0:
        base = random.randint(100, 500)
    elif score >= 7.5:
        base = random.randint(200, 1000)
    elif score >= 7.0:
        base = random.randint(500, 1500)
    elif score >= 6.5:
        base = random.randint(800, 2000)
    elif score >= 6.0:
        base = random.randint(1000, 2500)
    elif score >= 5.0:
        base = random.randint(1500, 3500)
    elif score >= 4.0:
        base = random.randint(2000, 4000)
    else:
        base = random.randint(3000, 5000)
    return base


def _simulate_reader_votes(chapters: list, genre: str) -> dict:
    """模拟不同类型读者的投票"""
    from core import count_words
    
    results = {}
    total_score = 0
    total_weight = 0
    
    for reader_type, profile in READER_POOL.items():
        # Check genre match
        genre_match = 0.7  # base match
        
        # Score based on chapter analysis
        chapter_scores = []
        for num, text, wc in chapters[:10]:
            if not text:
                continue
            sc = _score_chapter_for_reader(text, profile)
            chapter_scores.append(sc)
        
        avg_score = sum(chapter_scores) / max(len(chapter_scores), 1) if chapter_scores else 5.0
        weighted_score = round(avg_score * genre_match, 1)
        
        # Vote simulation
        votes = int(weighted_score * profile["weight"] * 100)
        
        results[reader_type] = {
            "preference_score": weighted_score,
            "estimated_votes": votes,
            "weight": profile["weight"],
            "verdict": "必追" if weighted_score >= 8 else 
                      "可追" if weighted_score >= 6 else 
                      "观望" if weighted_score >= 4 else "弃书",
        }
        
        total_score += weighted_score * profile["weight"]
        total_weight += profile["weight"]
    
    results["total_score"] = round(total_score / max(total_weight, 0.01), 1)
    
    return results


def _score_chapter_for_reader(text: str, profile: dict) -> float:
    """根据读者偏好给章节打分（规则基+随机）"""
    base = 5.0
    text_lower = text.lower() if text else ""
    
    for pref in profile["prefer"]:
        if any(kw in text_lower for kw in [pref, pref[:2]]):
            base += 0.5
    
    for dis in profile["dislike"]:
        if any(kw in text_lower for kw in [dis, dis[:2]]):
            base -= 0.3
    
    # Add randomness for natural feel
    base += random.uniform(-0.5, 0.5)
    
    return max(1.0, min(10.0, base))


def compare_books(books_data: list, log_callback=None) -> dict:
    """多书横向对比排行榜表现
    
    Args:
        books_data: [{name, chapters, genre, word_count}, ...]
    """
    results = []
    for book in books_data:
        if log_callback:
            log_callback(f"分析: {book.get('name', '未命名')}...")
        lb = simulate_leaderboard(
            chapters=book.get("chapters", []),
            book_name=book.get("name", ""),
            genre=book.get("genre", ""),
            word_count=book.get("word_count", 0),
            log_callback=log_callback,
        )
        results.append(lb)
    
    # Sort by total score
    results.sort(key=lambda x: x.get("reader_votes", {}).get("total_score", 0), reverse=True)
    
    return {
        "books": results,
        "winner": results[0]["book_name"] if results else "",
        "comparison_time": datetime.now().isoformat(),
    }


def generate_leaderboard_report(sim_result: dict, fmt: str = "markdown") -> str:
    """生成排行榜分析报告"""
    rankings = sim_result.get("rankings", {})
    votes = sim_result.get("reader_votes", {})
    
    if fmt == "markdown":
        lines = [
            f"# 📊 排行榜竞争力报告",
            f"",
            f"**作品**：{sim_result.get('book_name', '未命名')}",
            f"**类型**：{sim_result.get('genre', '')}",
            f"**字数**：{sim_result.get('word_count', 0):,}字",
            f"**分析时间**：{sim_result.get('timestamp', '')}",
            f"**综合评分**：{votes.get('total_score', 0)}/10",
            f"",
            f"## 榜单预测",
            f"",
            f"| 榜单 | 预测排名 | 评分 | 总书数 |",
            f"|------|---------|------|-------|",
        ]
        for key, lb in rankings.items():
            name = LEADERBOARD_TYPES.get(key, key)
            lines.append(f"| {name} | #{lb['rank']} | {lb['score']} | {lb['total_books']:,} |")
        
        lines += [
            f"",
            f"## 读者群体分析",
            f"",
        ]
        for rtype, data in votes.items():
            if rtype == "total_score":
                continue
            verdict_icon = {"必追": "🔥", "可追": "👍", "观望": "🤔", "弃书": "👎"}.get(data["verdict"], "")
            lines.append(f"- **{rtype}**：{data['preference_score']}/10 {verdict_icon} {data['verdict']}（预估{data['estimated_votes']}票）")
        
        lines += [
            f"",
            f"## AI深度分析",
            f"",
            sim_result.get("ai_analysis", ""),
        ]
        
        return "\n".join(lines)
    
    elif fmt == "json":
        return json.dumps(sim_result, ensure_ascii=False, indent=2)
    
    return ""
