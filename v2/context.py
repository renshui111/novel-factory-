# -*- coding: utf-8 -*-
"""context.py --- 智能上下文引擎
端点续写核心：动态上下文窗口 + 人物状态追踪 + 伏笔账本 + 风格指纹
"""

import os, json, re
from datetime import datetime
# core imports moved to function level

# ---------------------------------------------------------------------------
# Tiered context window builder
# ---------------------------------------------------------------------------

def build_context(book_dir: str, chapter_num: int) -> dict:
    """多级上下文窗口：近章完整+中章摘要+远章世界状态"""
    ctx = {
        "setting": _load_know(book_dir, "设定")[:800],
        "characters": _load_know(book_dir, "角色档案")[:1200],
        "foreshadows": _load_unresolved_foreshadows(book_dir),
        "recent_chapters": "",       # 最近3章完整原文
        "medium_summary": "",        # 4-10章摘要
        "distant_state": "",         # 10章+ 世界状态/人物位置
        "style_guide": _load_style(book_dir),
        "character_states": _load_character_states(book_dir),
        "rhythm_hint": _get_rhythm(book_dir, chapter_num),
    }

    chapters_dir = os.path.join(book_dir, "章节")
    if os.path.isdir(chapters_dir):
        files = sorted([f for f in os.listdir(chapters_dir) if f.endswith('.md')])
        
        # Recent 3 chapters: full text
        recent = files[-3:] if len(files) >= 3 else files
        recent_texts = []
        for f in recent:
            try:
                recent_texts.append(read_file(os.path.join(chapters_dir, f))[:3000])
            except Exception:
                pass
        ctx["recent_chapters"] = "\n---\n".join(recent_texts)

        # Chapters 4-10 back: medium summary (last 200 chars each)
        mid_range = files[-10:-3] if len(files) > 3 else []
        mid_texts = []
        for f in mid_range:
            try:
                t = read_file(os.path.join(chapters_dir, f))
                mid_texts.append(f"  {f}: {t[-200:]}")
            except Exception:
                pass
        ctx["medium_summary"] = "\n".join(mid_texts)

        # Chapter 10+: world state only
        if len(files) > 10:
            ctx["distant_state"] = _load_know(book_dir, "世界状态")[:500]

    # Load checkpoint summary
    summary = _load_know(book_dir, "全局摘要")
    if summary:
        ctx["recent_summary"] = _compress(summary, chapter_num)

    return ctx


def build_prompt_context(ctx: dict, chapter_num: int, chapter_title: str) -> str:
    """把上下文字典拼成注入prompt的文本"""
    parts = []

    if ctx.get("setting"):
        parts.append(f"[世界观设定]\n{ctx['setting']}")

    if ctx.get("characters"):
        parts.append(f"[角色档案]\n{ctx['characters']}")

    if ctx.get("character_states"):
        parts.append(f"[当前人物状态]\n{ctx['character_states']}")

    if ctx.get("foreshadows"):
        parts.append(f"[待回收伏笔]\n{ctx['foreshadows']}")

    if ctx.get("recent_chapters"):
        parts.append(f"[前文回顾-最近章节]\n{ctx['recent_chapters']}")

    if ctx.get("medium_summary"):
        parts.append(f"[前文回顾-中程]\n{ctx['medium_summary']}")

    if ctx.get("distant_state"):
        parts.append(f"[世界状态]\n{ctx['distant_state']}")

    if ctx.get("style_guide"):
        parts.append(f"[风格指引]\n{ctx['style_guide']}")

    if ctx.get("rhythm_hint"):
        parts.append(f"[节奏提示]\n{ctx['rhythm_hint']}")

    parts.append(f"[本章信息]\n第{chapter_num}章: {chapter_title}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Character state tracker
# ---------------------------------------------------------------------------

CHARACTER_STATE_FILE = "角色状态表.json"

def _load_character_states(book_dir: str) -> str:
    path = os.path.join(book_dir, CHARACTER_STATE_FILE)
    if os.path.exists(path):
        try:
            data = json.loads(read_file(path))
            lines = []
            for c in data.get("characters", []):
                name = c.get("name", "?")
                loc = c.get("location", "未知")
                mood = c.get("mood", "平静")
                goal = c.get("goal", "无")
                relation = c.get("relations", "")
                lines.append(f"{name}: 在{loc}, 情绪{mood}, 目标:{goal}")
                if relation:
                    lines.append(f"  关系: {relation}")
            return "\n".join(lines)
        except Exception:
            pass
    return ""


def update_character_states(book_dir: str, chapter_text: str, chapter_num: int):
    """用AI从新章节中提取并更新人物状态"""
    existing = {}
    path = os.path.join(book_dir, CHARACTER_STATE_FILE)
    if os.path.exists(path):
        try:
            existing = json.loads(read_file(path))
        except Exception:
            pass

    prompt = f"""从以下小说章节中提取所有主要人物的当前状态：

章节内容：
{chapter_text[:3000]}

请以JSON格式返回，结构如下：
{{
  "characters": [
    {{
      "name": "角色名",
      "location": "当前位置",
      "mood": "当前情绪",
      "goal": "当前目标",
      "relations": "与其他角色的关系变化",
      "status_change": "本章中状态变化"
    }}
  ]
}}

只返回JSON，不要其他内容。"""

    try:
        result = llm_invoke_ada(prompt)
        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            new_data = json.loads(json_match.group())
            # Merge with existing
            existing_chars = {c["name"]: c for c in existing.get("characters", [])}
            for c in new_data.get("characters", []):
                existing_chars[c["name"]] = c
            existing["characters"] = list(existing_chars.values())
            existing["last_update"] = chapter_num
            write_file(path, json.dumps(existing, ensure_ascii=False, indent=2))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Foreshadow ledger
# ---------------------------------------------------------------------------

FORESHADOW_FILE = "伏笔账本.json"

def _load_unresolved_foreshadows(book_dir: str) -> str:
    path = os.path.join(book_dir, FORESHADOW_FILE)
    if os.path.exists(path):
        try:
            data = json.loads(read_file(path))
            unresolved = [f for f in data.get("foreshadows", []) if not f.get("resolved")]
            if not unresolved:
                return ""
            lines = ["[以下伏笔尚未回收，请在后续章节中安排回收：]"]
            for f in unresolved[-10:]:
                fid = f.get("id", "?")
                planted = f.get("planted_chapter", "?")
                content = f.get("content", "")
                lines.append(f"  伏笔#{fid} (第{planted}章埋下): {content[:80]}")
            return "\n".join(lines)
        except Exception:
            pass
    return ""


def extract_foreshadows(book_dir: str, chapter_text: str, chapter_num: int):
    """AI分析新章节，自动识别新埋的伏笔"""
    path = os.path.join(book_dir, FORESHADOW_FILE)
    existing = {"foreshadows": [], "last_update": 0}
    if os.path.exists(path):
        try:
            existing = json.loads(read_file(path))
        except Exception:
            pass

    prompt = f"""分析以下小说章节，找出作者新埋下的伏笔（悬而未决的线索、未解释的细节、暗示未来发展的内容）：

章节内容：
{chapter_text[:2500]}

请以JSON格式返回：
{{
  "new_foreshadows": [
    {{
      "content": "伏笔内容描述",
      "type": "人物/剧情/世界观/物品"
    }}
  ]
}}

如果没有新伏笔，返回空数组。只返回JSON。"""

    try:
        result = llm_invoke_ada(prompt)
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            new_data = json.loads(json_match.group())
            max_id = max([f.get("id", 0) for f in existing.get("foreshadows", [])], default=0)
            for item in new_data.get("new_foreshadows", []):
                max_id += 1
                existing.setdefault("foreshadows", []).append({
                    "id": max_id,
                    "planted_chapter": chapter_num,
                    "content": item.get("content", ""),
                    "type": item.get("type", "剧情"),
                    "resolved": False,
                    "resolved_chapter": None,
                })
            existing["last_update"] = chapter_num
            write_file(path, json.dumps(existing, ensure_ascii=False, indent=2))
    except Exception:
        pass


def mark_foreshadow_resolved(book_dir: str, chapter_num: int, keyword: str = ""):
    """标记伏笔已回收（基于章节内容匹配）"""
    path = os.path.join(book_dir, FORESHADOW_FILE)
    if not os.path.exists(path):
        return
    try:
        data = json.loads(read_file(path))
        changed = False
        for f in data.get("foreshadows", []):
            if not f.get("resolved") and (not keyword or keyword in f.get("content", "")):
                f["resolved"] = True
                f["resolved_chapter"] = chapter_num
                changed = True
        if changed:
            write_file(path, json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Style fingerprint
# ---------------------------------------------------------------------------

STYLE_FILE = "风格指纹.json"

def _load_style(book_dir: str) -> str:
    path = os.path.join(book_dir, STYLE_FILE)
    if os.path.exists(path):
        try:
            data = json.loads(read_file(path))
            return json.dumps(data, ensure_ascii=False, indent=1)[:800]
        except Exception:
            pass
    return ""


def update_style(book_dir: str, chapter_texts: list):
    """从已有章节中提取风格指纹"""
    if not chapter_texts:
        return

    sample = "\n---\n".join([t[:500] for t in chapter_texts[-5:]])
    prompt = f"""分析以下小说的写作风格，提取关键特征：

内容样本：
{sample[:4000]}

请以JSON格式返回以下维度（尽量量化）：
{{
  "avg_sentence_length": 平均句长(字数),
  "dialogue_ratio": 对话占比(0-1),
  "description_ratio": 描写占比(0-1),
  "tense": "时态",
  "person": "人称",
  "paragraph_style": "段落风格(短/中/长)",
  "tone": "语气(严肃/轻松/幽默/沉重等)",
  "vocabulary_level": "用词难度(简单/中等/华丽)",
  "signature_patterns": ["标志性句式1", "标志性句式2"],
  "avoid_patterns": ["应避免的句式1"]
}}

只返回JSON。"""

    try:
        result = llm_invoke_ada(prompt)
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            data = json.loads(json_match.group())
            data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            write_file(os.path.join(book_dir, STYLE_FILE),
                       json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KNOWLEDGE_FILE = "知识库.json"

def _load_know(book_dir: str, key: str) -> str:
    path = os.path.join(book_dir, KNOWLEDGE_FILE)
    if os.path.exists(path):
        try:
            data = json.loads(read_file(path))
            return str(data.get(key, ""))
        except Exception:
            pass
    # Fallback: individual files
    for ext in ['.md', '.txt']:
        p = os.path.join(book_dir, f"{key}{ext}")
        if os.path.exists(p):
            try:
                return read_file(p)
            except Exception:
                pass
    return ""


def _compress(summary: str, chapter_num: int) -> str:
    """根据章节数动态压缩摘要"""
    lines = [l.strip() for l in summary.strip().split("\n") if l.strip()]
    if chapter_num <= 30:
        return "\n".join(lines[-60:])[:2500]
    elif chapter_num <= 100:
        return "\n".join(lines[-40:])[:1500]
    else:
        return "\n".join(lines[-20:])[:800]


def _get_rhythm(book_dir: str, chapter_num: int) -> str:
    """章节节奏提示"""
    path = os.path.join(book_dir, "章节节奏表.json")
    if os.path.exists(path):
        try:
            data = json.loads(read_file(path))
            hints = data.get("hints", {})
            key = str(chapter_num)
            if key in hints:
                return hints[key]
            # Find nearest
            for k in sorted(hints.keys(), key=int, reverse=True):
                if int(k) < chapter_num:
                    return f"最近的节奏指引(第{k}章): {hints[k]}"
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# Continuity auto-fix
# ---------------------------------------------------------------------------

def auto_fix_continuity(book_dir: str, chapter_text: str, chapter_num: int) -> str:
    """检测并自动修复前后章节的连贯性问题"""
    issues = []

    # Check for hanging dialogue quotes
    open_quotes = chapter_text.count("\u201c") - chapter_text.count("\u201d")
    if open_quotes > 0:
        issues.append(f"有{open_quotes}处左引号未闭合")

    # Check chapter ending quality
    ending = chapter_text[-200:]
    weak_endings = ["未完待续", "欲知后事", "且听下回", "预知后事"]
    for we in weak_endings:
        if we in ending:
            issues.append(f"章节结尾用了俗套用语'{we}'")

    # Check for character state consistency
    states_str = _load_character_states(book_dir)
    if states_str and chapter_num > 1:
        # Count named characters in this chapter vs state tracker
        state_names = set(re.findall(r'^(\S+):', states_str, re.MULTILINE))
        for name in state_names:
            if name not in chapter_text and len(name) >= 2:
                issues.append(f"人物'{name}'在状态表中存在但本章未出现")

    return "; ".join(issues) if issues else ""
