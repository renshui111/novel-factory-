# -*- coding: utf-8 -*-
"""project.py — 项目管理核心：统一目录结构、项目元数据、知识库"""

import os
import re
import json
import time
from datetime import datetime
from core import read_file, write_file, ensure_dir, count_words, get_output_dir


# ═══════════════════════════════════════════════════════════
# 项目目录结构规范
# ═══════════════════════════════════════════════════════════
PROJECT_STRUCTURE = {
    "正文": "章节正文",
    "知识库": "拆书/角色/伏笔等结构化数据",
    "导出": "导出的成品文件",
    "autosave": "自动备份",
}

KNOWLEDGE_FILES = {
    "设定": "设定.md",
    "目录": "目录.md",
    "全局摘要": "全局摘要.txt",
    "角色档案": "角色档案.md",
    "伏笔表": "伏笔表.md",
    "章节节奏表": "章节节奏表.md",
    "风格指纹": "风格指纹.json",
    "项目元数据": "项目元数据.json",
    "checkpoint": "checkpoint.json",
}


def make_book_dir(topic: str) -> str:
    """根据书名创建标准化项目目录"""
    dir_name = re.sub(r'[\\/:*?"<>|]', '', topic)[:30].strip()
    if not dir_name:
        dir_name = f"novel_{int(time.time())}"
    book_dir = os.path.join(get_output_dir(), dir_name)
    ensure_dir(book_dir)
    for subdir in PROJECT_STRUCTURE:
        ensure_dir(os.path.join(book_dir, subdir))
    return book_dir


def get_project_meta(book_dir: str) -> dict:
    """读取项目元数据"""
    meta_path = os.path.join(book_dir, KNOWLEDGE_FILES["项目元数据"])
    if os.path.exists(meta_path):
        try:
            return json.loads(read_file(meta_path))
        except Exception:
            pass
    return {}


def save_project_meta(book_dir: str, meta: dict):
    """保存项目元数据"""
    meta["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_path = os.path.join(book_dir, KNOWLEDGE_FILES["项目元数据"])
    write_file(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))


def update_project_meta_from_config(book_dir: str, config: dict, chapter_num: int = 0, summary: str = ""):
    """从 config 和当前进度更新项目元数据"""
    meta = get_project_meta(book_dir)
    novel_cfg = config.get("novel", {})
    meta.update({
        "topic": novel_cfg.get("topic", meta.get("topic", "")),
        "genre": novel_cfg.get("genre", meta.get("genre", "")),
        "target_words": novel_cfg.get("words_per_chapter", meta.get("target_words", 2000)),
        "total_chapters": novel_cfg.get("num_chapters", meta.get("total_chapters", 0)),
        "chapter_completed": chapter_num or meta.get("chapter_completed", 0),
        "summary_preview": (summary or meta.get("summary_preview", ""))[:200],
        "created": meta.get("created", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    # 统计实际字数
    ch_dir = os.path.join(book_dir, "正文")
    if os.path.isdir(ch_dir):
        total_w = 0
        ch_count = 0
        for f in os.listdir(ch_dir):
            if f.endswith(".md"):
                ch_count += 1
                try:
                    total_w += count_words(read_file(os.path.join(ch_dir, f)))
                except Exception:
                    pass
        meta["actual_words"] = total_w
        meta["actual_chapters"] = ch_count
    save_project_meta(book_dir, meta)
    return meta


# ═══════════════════════════════════════════════════════════
# 知识库管理
# ═══════════════════════════════════════════════════════════
def save_knowledge(book_dir: str, key: str, content: str):
    """保存知识库条目"""
    if key not in KNOWLEDGE_FILES:
        return
    path = os.path.join(book_dir, KNOWLEDGE_FILES[key])
    write_file(path, content)


def load_knowledge(book_dir: str, key: str) -> str:
    """读取知识库条目"""
    if key not in KNOWLEDGE_FILES:
        return ""
    path = os.path.join(book_dir, KNOWLEDGE_FILES[key])
    if os.path.exists(path):
        return read_file(path)
    return ""


def load_knowledge_json(book_dir: str, key: str) -> dict:
    """读取知识库 JSON 条目"""
    raw = load_knowledge(book_dir, key)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}


def save_knowledge_json(book_dir: str, key: str, data: dict):
    """保存知识库 JSON 条目"""
    if key not in KNOWLEDGE_FILES:
        return
    path = os.path.join(book_dir, KNOWLEDGE_FILES[key])
    write_file(path, json.dumps(data, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════════════════════════
# 伏笔系统
# ═══════════════════════════════════════════════════════════
def load_foreshadow_table(book_dir: str) -> list:
    """加载伏笔表"""
    raw = load_knowledge_json(book_dir, "伏笔表")
    if isinstance(raw, list):
        return raw
    return raw.get("items", []) if isinstance(raw, dict) else []


def save_foreshadow_table(book_dir: str, items: list):
    """保存伏笔表"""
    save_knowledge_json(book_dir, "伏笔表", {"items": items, "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


def add_foreshadow(book_dir: str, chapter_num: int, content: str, status: str = "未回收"):
    """添加一条伏笔"""
    items = load_foreshadow_table(book_dir)
    items.append({
        "id": len(items) + 1,
        "chapter_planted": chapter_num,
        "content": content,
        "status": status,
        "chapter_resolved": 0,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_foreshadow_table(book_dir, items)


def resolve_foreshadow(book_dir: str, foreshadow_id: int, chapter_num: int):
    """标记伏笔已回收"""
    items = load_foreshadow_table(book_dir)
    for item in items:
        if item["id"] == foreshadow_id:
            item["status"] = "已回收"
            item["chapter_resolved"] = chapter_num
            break
    save_foreshadow_table(book_dir, items)


def get_unresolved_foreshadows(book_dir: str) -> list:
    """获取未回收伏笔"""
    return [i for i in load_foreshadow_table(book_dir) if i.get("status") != "已回收"]


# ═══════════════════════════════════════════════════════════
# 风格指纹系统
# ═══════════════════════════════════════════════════════════
def compute_style_fingerprint(book_dir: str) -> dict:
    """从已写章节计算风格指纹"""
    import re as _re
    ch_dir = os.path.join(book_dir, "正文")
    if not os.path.isdir(ch_dir):
        return {}
    all_text = []
    for f in sorted(os.listdir(ch_dir)):
        if f.endswith(".md"):
            try:
                all_text.append(read_file(os.path.join(ch_dir, f)))
            except Exception:
                pass
    if not all_text:
        return {}
    combined = "\n".join(all_text)
    # 高频词
    words = _re.findall(r'[\u4e00-\u9fff]{2,6}', combined)
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top_phrases = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30]
    # 句式统计
    sentences = _re.split(r'[。！？]', combined)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    # 段落统计
    paragraphs = [p.strip() for p in combined.split('\n\n') if p.strip()]
    avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
    # 对话密度
    dialog_count = len(_re.findall(r'[""「」『』]', combined)) // 2
    dialog_ratio = dialog_count / max(len(sentences), 1)
    fp = {
        "top_phrases": top_phrases,
        "avg_sentence_len": round(avg_sentence_len, 1),
        "avg_paragraph_len": round(avg_para_len, 1),
        "dialog_ratio": round(dialog_ratio, 3),
        "total_chars": len(combined),
        "total_sentences": len(sentences),
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_knowledge_json(book_dir, "风格指纹", fp)
    return fp


# ═══════════════════════════════════════════════════════════
# 节奏表
# ═══════════════════════════════════════════════════════════
def save_rhythm_table(book_dir: str, table: list):
    """保存章节节奏表"""
    save_knowledge_json(book_dir, "章节节奏表", {"chapters": table})


def load_rhythm_table(book_dir: str) -> list:
    """加载章节节奏表"""
    data = load_knowledge_json(book_dir, "章节节奏表")
    return data.get("chapters", []) if isinstance(data, dict) else []


def get_rhythm_hint(book_dir: str, chapter_num: int) -> str:
    """获取指定章节的节奏提示"""
    table = load_rhythm_table(book_dir)
    if not table:
        if chapter_num <= 3:
            return "黄金三章，钩子前置，节奏紧凑"
        return "标准章节，起伏推进"
    for ch in table:
        if ch.get("chapter_num") == chapter_num:
            return ch.get("rhythm", "标准章节")
    return "标准章节，起伏推进"


# ═══════════════════════════════════════════════════════════
# 项目发现（书架用）
# ═══════════════════════════════════════════════════════════
def discover_projects(output_dir: str = "") -> list:
    """扫描 output 目录，发现所有已有项目"""
    if not output_dir:
        try:
            output_dir = get_output_dir()
        except Exception:
            return []
    if not os.path.isdir(output_dir):
        return []
    projects = []
    for name in sorted(os.listdir(output_dir)):
        path = os.path.join(output_dir, name)
        if not os.path.isdir(path):
            continue
        ch_dir = os.path.join(path, "正文")
        if not os.path.isdir(ch_dir):
            continue
        meta = get_project_meta(path)
        ch_count = len([f for f in os.listdir(ch_dir) if f.endswith('.md')])
        total_w = 0
        for f in os.listdir(ch_dir):
            if f.endswith('.md'):
                try:
                    total_w += count_words(read_file(os.path.join(ch_dir, f)))
                except Exception:
                    pass
        projects.append({
            "name": name,
            "path": path,
            "topic": meta.get("topic", name),
            "genre": meta.get("genre", ""),
            "chapters": ch_count,
            "words": total_w,
            "last_update": meta.get("last_update", ""),
            "chapter_completed": meta.get("chapter_completed", ch_count),
        })
    projects.sort(key=lambda x: x.get("last_update", ""), reverse=True)
    return projects


# ═══════════════════════════════════════════════════════════
# 拆书 → 写书联动
# ═══════════════════════════════════════════════════════════
def import_analyze_to_project(analyze_dir: str, topic: str = "", genre: str = "") -> str:
    """将拆书结果导入为新的写书项目，返回新项目目录"""
    import json
    if not topic:
        topic = os.path.basename(analyze_dir) + "_仿写"

    book_dir = make_book_dir(topic)
    imported = []

    # 导入设定
    setting_file = os.path.join(analyze_dir, "设定分析.md")
    if os.path.exists(setting_file):
        save_knowledge(book_dir, "设定", read_file(setting_file))
        imported.append("设定")

    # 导入角色
    char_file = os.path.join(analyze_dir, "角色分析.md")
    if os.path.exists(char_file):
        save_knowledge(book_dir, "角色档案", read_file(char_file))
        imported.append("角色档案")

    # 导入风格指纹
    fp_file = os.path.join(analyze_dir, "风格指纹.json")
    if os.path.exists(fp_file):
        save_knowledge(book_dir, "风格指纹", read_file(fp_file))
        imported.append("风格指纹")

    # 导入角色卡片 JSON
    card_file = os.path.join(analyze_dir, "角色卡片.json")
    if os.path.exists(card_file):
        save_knowledge(book_dir, "角色档案", read_file(card_file))
        imported.append("角色卡片")

    # 导入剧情分析作为大纲参考
    plot_file = os.path.join(analyze_dir, "剧情分析.md")
    if os.path.exists(plot_file):
        save_knowledge(book_dir, "目录", read_file(plot_file))
        imported.append("剧情/大纲参考")

    # 导入风格分析
    style_file = os.path.join(analyze_dir, "风格分析.md")
    if os.path.exists(style_file):
        raw = read_file(style_file)
        existing = load_knowledge(book_dir, "设定")
        combined = existing + "\n\n---\n\n## 风格参考（来自拆书）\n" + raw
        save_knowledge(book_dir, "设定", combined)
        imported.append("风格参考")

    # 保存项目元数据
    save_project_meta(book_dir, {
        "topic": topic,
        "genre": genre,
        "source": "拆书导入",
        "source_dir": analyze_dir,
        "imported_items": imported,
    })

    return book_dir


def get_project_context_for_writing(book_dir: str) -> dict:
    """为写书提供完整上下文（用于 prompt 注入）"""
    return {
        "setting": load_knowledge(book_dir, "设定")[:3000],
        "characters": load_knowledge(book_dir, "角色档案")[:2000],
        "outline": load_knowledge(book_dir, "目录")[:2000],
        "foreshadows": get_unresolved_foreshadows(book_dir),
        "style_fingerprint": load_knowledge_json(book_dir, "风格指纹"),
        "summary": load_knowledge(book_dir, "全局摘要"),
        "rhythm_table": load_rhythm_table(book_dir),
    }

