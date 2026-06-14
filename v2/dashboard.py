# -*- coding: utf-8 -*-
"""dashboard.py — AI写作导演台：章节队列、质量评分、多版本管理、智能上下文"""

import os, re, json, time
from datetime import datetime
from pathlib import Path as _Path
from core import read_file, write_file, ensure_dir, count_words


# ═══════════════════════════════════════════════════════════
# 1. 章节队列
# ═══════════════════════════════════════════════════════════

def load_chapter_queue(book_dir: str) -> dict:
    """加载章节队列状态"""
    path = os.path.join(book_dir, "chapter_queue.json")
    if os.path.exists(path):
        try:
            return json.loads(read_file(path))
        except Exception:
            pass
    return {"chapters": [], "status": "idle"}


def save_chapter_queue(book_dir: str, queue: dict):
    """保存章节队列"""
    queue["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_file(os.path.join(book_dir, "chapter_queue.json"),
               json.dumps(queue, ensure_ascii=False, indent=2))


def init_chapter_queue(book_dir: str, total_chapters: int, titles: list) -> dict:
    """初始化章节队列，每章一个条目"""
    queue = {
        "book_dir": book_dir,
        "total_chapters": total_chapters,
        "status": "ready",
        "chapters": []
    }
    for i in range(total_chapters):
        title = titles[i] if i < len(titles) else f"第{i+1}章"
        queue["chapters"].append({
            "chapter_num": i + 1,
            "title": title,
            "status": "pending",
            "words": 0,
            "score": None,
            "ai_words": 0,
            "version": 0,
            "best_version": 0,
            "error": None,
        })
    save_chapter_queue(book_dir, queue)
    return queue


def update_chapter_status(book_dir: str, chapter_num: int, **kwargs):
    """更新单章状态"""
    queue = load_chapter_queue(book_dir)
    for ch in queue["chapters"]:
        if ch["chapter_num"] == chapter_num:
            ch.update(kwargs)
            break
    save_chapter_queue(book_dir, queue)


# ═══════════════════════════════════════════════════════════
# 2. 质量评分
# ═══════════════════════════════════════════════════════════

def score_chapter(text: str, target_words: int = 2000, book_dir: str = "") -> dict:
    """综合评分一章（0-100）"""
    scores = {}
    details = []
    wc = count_words(text)

    # 字数分 (25分)
    ratio = min(wc / max(target_words, 1), 2.0)
    if ratio < 0.5:
        word_score = int(25 * ratio / 0.5)
        details.append(f"字数严重不足({wc}/{target_words})")
    elif ratio < 0.8:
        word_score = int(15 + 10 * (ratio - 0.5) / 0.3)
        details.append(f"字数偏少({wc})")
    elif ratio <= 1.3:
        word_score = 25
    else:
        word_score = max(20, 30 - int((ratio - 1.3) * 30))
    scores["字数"] = word_score

    # AI词分 (25分)
    from deslop import scan_ai_words
    ai_hits = scan_ai_words(text)
    ai_count = len(ai_hits)
    ai_density = ai_count / max(wc / 100, 1)
    if ai_density < 0.3:
        ai_score = 25
    elif ai_density < 0.6:
        ai_score = 20
        details.append(f"AI词偏高({ai_count}处)")
    elif ai_density < 1.0:
        ai_score = 12
        details.append(f"AI词过多({ai_count}处)")
    else:
        ai_score = 5
        details.append(f"AI词严重超标({ai_count}处)")
    scores["AI词"] = ai_score

    # 对话密度分 (15分)
    dialog_matches = len(re.findall(r'["""「」『』]', text))
    dialog_ratio = dialog_matches / max(wc, 1) * 100
    if 2 < dialog_ratio < 12:
        dialog_score = 15
    elif 1 < dialog_ratio <= 2 or 12 <= dialog_ratio < 18:
        dialog_score = 10
        details.append(f"对话密度偏差({dialog_ratio:.1f}%)")
    else:
        dialog_score = 5
        details.append(f"对话密度异常({dialog_ratio:.1f}%)")
    scores["对话"] = dialog_score

    # 结尾钩子分 (20分)
    ending = text[-300:] if len(text) >= 300 else text
    hook_patterns = [
        r'[？?](?![""」』])', r'突然|忽然|猛地|骤然',
        r'难道|莫非|到底|究竟', r'不知|未知|未解',
        r'危险|危机|杀机|生死', r'发现|出现|浮现'
    ]
    hook_hits = sum(1 for p in hook_patterns if re.search(p, ending))
    hook_score = min(20, hook_hits * 5 + 5)
    if hook_hits < 2:
        details.append("结尾钩子偏弱")
    scores["钩子"] = hook_score

    # 衔接分 (15分) — 如果有前一章
    continuity_score = 15
    if book_dir:
        try:
            from novel import check_continuity
            ch_dir = os.path.join(book_dir, "正文")
            if os.path.isdir(ch_dir):
                prev_files = sorted([f for f in os.listdir(ch_dir) if f.endswith('.md')])
                if prev_files:
                    prev_text = read_file(os.path.join(ch_dir, prev_files[-1]))
                    issues = check_continuity(prev_text, text, book_dir)
                    continuity_score = max(5, 15 - len(issues) * 5)
                    if issues:
                        details.append(f"衔接问题: {', '.join(issues[:2])}")
        except Exception:
            pass
    scores["衔接"] = continuity_score

    total = sum(scores.values())
    star = "\u2605" * min(5, max(1, total // 20)) + "\u2606" * max(0, 5 - min(5, max(1, total // 20)))

    return {
        "total": total,
        "star": star,
        "scores": scores,
        "details": details,
        "words": wc,
        "ai_words": ai_count,
        "dialog_ratio": round(dialog_ratio, 1),
    }


# ═══════════════════════════════════════════════════════════
# 3. 多版本生成 + 自动择优
# ═══════════════════════════════════════════════════════════

def generate_chapter_multi_version(chapter_num: int, chapter_title: str,
                                   novel_setting: str, directory_text: str,
                                   summary: str, target_words: int,
                                   book_dir: str, log_callback=None,
                                   versions: int = 3, auto_pick: bool = True) -> dict:
    """生成一章的多个版本，自动选最优"""
    from prompts import CHAPTER_GENERATION
    from core import llm_invoke_ada

    candidates = []
    for v in range(versions):
        if log_callback:
            log_callback(f"  [v{v+1}/{versions}] 第{chapter_num}章 生成中...")

        prompt = CHAPTER_GENERATION.format(
            chapter_num=chapter_num, novel_setting=novel_setting,
            directory=directory_text, summary_text=summary,
            chapter_title=chapter_title, chapter_desc="",
            target_words=target_words,
            prev_chapter_ending="", character_context="", rhythm_context="")

        try:
            content = llm_invoke_ada(prompt)
        except Exception as e:
            candidates.append({"content": "", "score": 0, "error": str(e)})
            continue

        if not content or content.startswith("[错误]"):
            candidates.append({"content": "", "score": 0, "error": str(content)})
            continue

        # 去 AI 味
        from deslop import rule_based_deslop
        cleaned, _ = rule_based_deslop(content)

        # 评分
        score = score_chapter(cleaned, target_words, book_dir)
        candidates.append({
            "version": v + 1,
            "content": cleaned,
            "words": score["words"],
            "score": score,
        })

    if not candidates:
        return {"content": "", "path": "", "words": 0, "success": False, "error": "所有版本生成失败"}

    # 选最优
    best = max(candidates, key=lambda c: c["score"]["total"] if isinstance(c.get("score"), dict) else 0)
    best_score = best["score"]

    if log_callback:
        log_callback(f"  \u2714 {best_score['words']}字 | 评分{best_score['total']} | {best_score['star']}")

    # 保存最优版本
    from core import write_file as _wf
    ch_dir = os.path.join(book_dir, "正文")
    ensure_dir(ch_dir)
    fname = f"\u7b2c{chapter_num:03d}\u7ae0_{chapter_title}.md"
    _wf(os.path.join(ch_dir, fname), best["content"])

    return {
        "content": best["content"],
        "path": os.path.join(ch_dir, fname),
        "words": best_score["words"],
        "success": True,
        "score": best_score,
        "candidates": len(candidates),
    }


# ═══════════════════════════════════════════════════════════
# 4. 智能上下文管理
# ═══════════════════════════════════════════════════════════

def build_smart_context(book_dir: str, chapter_num: int, max_tokens: int = 8000) -> dict:
    """根据当前章节数，智能构建注入上下文字典"""
    from project import load_knowledge, get_unresolved_foreshadows, load_knowledge_json

    setting = load_knowledge(book_dir, "设定") or ""
    characters = load_knowledge(book_dir, "角色档案") or ""
    summary = load_knowledge(book_dir, "全局摘要") or ""
    fps = get_unresolved_foreshadows(book_dir)
    rhyme = load_knowledge_json(book_dir, "章节节奏表")

    ctx = {
        "setting": setting[:500],
        "characters": characters[:1000],
        "foreshadows": "",
        "recent_summary": "",
        "style_guide": "",
    }

    # 前50章：详细上下文
    if chapter_num <= 50:
        ctx["recent_summary"] = summary[:2000]
        ctx["foreshadows"] = "\n".join([f"#{f['id']} 第{f['chapter_planted']}章: {f['content'][:50]}" for f in fps])
    # 50-150章：压缩摘要
    elif chapter_num <= 150:
        lines = summary.strip().split("\n")
        ctx["recent_summary"] = "\n".join(lines[-40:])[:1500]
        ctx["foreshadows"] = "\n".join([f"#{f['id']}: {f['content'][:30]}" for f in fps[:10]])
    # 150+章：只保留关键信息
    else:
        lines = summary.strip().split("\n")
        ctx["recent_summary"] = "\n".join(lines[-20:])[:800]
        ctx["foreshadows"] = "\n".join([f"#{f['id']}: {f['content'][:20]}" for f in fps[:5]])

    return ctx
