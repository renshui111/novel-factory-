# -*- coding: utf-8 -*-
"""workspace.py --- 工作区管理
三级目录结构：主文件夹 → 分类子文件夹 → 单本书项目
"""

import os
import json
from datetime import datetime


def get_workspace_dir() -> str:
    """获取主工作区目录（委托给 core.utils，统一默认目录名）"""
    from core.utils import get_workspace_dir as _ws
    return _ws()


def get_active_category() -> str:
    """获取当前激活的分类"""
    from core import load_config
    cfg = load_config()
    return cfg.get("active_category", "默认")


def set_active_category(category: str):
    """设置当前激活的分类"""
    from core import load_config, save_config
    cfg = load_config()
    cfg["active_category"] = category
    save_config()


def get_category_dir(category: str = "") -> str:
    """获取分类子文件夹路径"""
    if not category:
        category = get_active_category()
    ws = get_workspace_dir()
    # Sanitize
    safe = "".join(c for c in category if c not in r'\/:*?"<>|')[:30].strip()
    if not safe:
        safe = "默认"
    cat_dir = os.path.join(ws, safe)
    os.makedirs(cat_dir, exist_ok=True)
    return cat_dir


def list_categories() -> list:
    """列出所有分类"""
    ws = get_workspace_dir()
    if not os.path.isdir(ws):
        return ["默认"]
    cats = []
    for name in sorted(os.listdir(ws)):
        path = os.path.join(ws, name)
        if os.path.isdir(path):
            # Count projects inside
            proj_count = sum(1 for n in os.listdir(path)
                           if os.path.isdir(os.path.join(path, n))
                           and os.path.isdir(os.path.join(path, n, "正文")))
            cats.append({"name": name, "path": path, "project_count": proj_count})
    if not cats:
        # Create default
        default_dir = os.path.join(ws, "默认")
        os.makedirs(default_dir, exist_ok=True)
        cats = [{"name": "默认", "path": default_dir, "project_count": 0}]
    return cats


def create_category(name: str) -> str:
    """创建新分类"""
    ws = get_workspace_dir()
    safe = "".join(c for c in name if c not in r'\/:*?"<>|')[:30].strip()
    if not safe:
        return ""
    cat_dir = os.path.join(ws, safe)
    os.makedirs(cat_dir, exist_ok=True)
    return cat_dir


def make_project_dir(topic: str, category: str = "") -> str:
    """在指定分类下创建项目目录"""
    import re, time
    cat_dir = get_category_dir(category)
    dir_name = re.sub(r'[\\/:*?"<>|]', '', topic)[:30].strip()
    if not dir_name:
        dir_name = f"novel_{int(time.time())}"
    proj_dir = os.path.join(cat_dir, dir_name)
    os.makedirs(proj_dir, exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "正文"), exist_ok=True)
    return proj_dir


def discover_all_projects() -> list:
    """扫描工作区所有分类下的项目"""
    cats = list_categories()
    projects = []
    for cat in cats:
        cat_name = cat["name"]
        cat_path = cat["path"]
        for name in sorted(os.listdir(cat_path)):
            path = os.path.join(cat_path, name)
            if not os.path.isdir(path):
                continue
            ch_dir = os.path.join(path, "正文")
            if not os.path.isdir(ch_dir):
                continue
            
            # Read metadata
            meta = {}
            meta_path = os.path.join(path, "项目元数据.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            
            ch_count = len([f for f in os.listdir(ch_dir) if f.endswith('.md')])
            total_w = 0
            for f in os.listdir(ch_dir):
                if f.endswith('.md'):
                    try:
                        from core import count_words, read_file
                        total_w += count_words(read_file(os.path.join(ch_dir, f)))
                    except Exception:
                        pass
            
            projects.append({
                "name": name,
                "path": path,
                "category": cat_name,
                "topic": meta.get("topic", name),
                "genre": meta.get("genre", ""),
                "platform": meta.get("platform", ""),
                "author": meta.get("author", ""),
                "chapters": ch_count,
                "words": total_w,
                "last_update": meta.get("last_update", meta.get("download_date", "")),
                "chapter_completed": meta.get("chapter_completed", ch_count),
            })
    projects.sort(key=lambda x: x.get("last_update", ""), reverse=True)
    return projects


def discover_projects_in_category(category: str = "") -> list:
    """获取指定分类下的项目"""
    all_projs = discover_all_projects()
    if not category:
        category = get_active_category()
    return [p for p in all_projs if p["category"] == category]
