# -*- coding: utf-8 -*-
"""snapshot.py --- 角色状态快照
每 N 章自动冻结所有角色的当前状态，续写时注入最近快照而非全文摘要
解决长篇小说后期人物跑偏、设定遗忘的问题
"""

import os, json, re
from datetime import datetime


SNAPSHOT_DIR = "角色快照"
SNAPSHOT_INTERVAL = 10  # 每10章自动快照一次


def take_snapshot(book_dir: str, chapter_num: int, log_callback=None) -> dict:
    """在第 chapter_num 章后冻结角色状态
    
    扫描最近几章 + 角色档案，用 AI 提炼每个角色的当前快照
    """
    from core import read_file, write_file, llm_invoke_ada, ensure_dir
    from novel import CHARACTER_ARCHIVE_FILE
    
    snap_dir = os.path.join(book_dir, SNAPSHOT_DIR)
    ensure_dir(snap_dir)
    
    # 读取角色档案
    archive_path = os.path.join(book_dir, CHARACTER_ARCHIVE_FILE)
    archive = read_file(archive_path) if os.path.exists(archive_path) else ""
    
    # 读取最近3章正文
    ch_dir = os.path.join(book_dir, "正文")
    recent_chapters = ""
    if os.path.isdir(ch_dir):
        files = sorted([f for f in os.listdir(ch_dir) if f.endswith('.md')])
        for fname in files[-3:]:
            content = read_file(os.path.join(ch_dir, fname))
            recent_chapters += f"\n--- {fname} ---\n{content[:2000]}\n"
    
    # 读取全局摘要
    summary = read_file(os.path.join(book_dir, "全局摘要.txt")) or ""
    
    prompt = f"""你是小说角色状态管理员。请根据以下信息，冻结第{chapter_num}章结束时所有角色的当前状态。

[角色档案]
{archive[-3000:]}

[最近章节]
{recent_chapters[:4000]}

[全局摘要]
{summary[-1500:]}

请为每个出现过的角色输出当前状态快照，格式严格如下：

## 角色名
- 当前境界/等级：
- 当前位置：
- 当前状态：（健康/受伤/闭关/失踪等）
- 持有重要物品：
- 当前目标：
- 近期关键事件：（最近3章发生了什么）
- 人际关系变化：（与谁关系变了）
- 伏笔状态：（此角色身上有哪些未解伏笔）

只输出有变化的角色，没出场的角色不用列。"""

    if log_callback:
        log_callback(f"  正在第{chapter_num}章后冻结角色状态...")
    
    try:
        result = llm_invoke_ada(prompt, system_msg="你是专业的小说 continuity 管理员。")
        if not result or result.startswith("[错误"):
            return {"error": "AI生成快照失败"}
        
        snapshot = {
            "chapter": chapter_num,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": result,
        }
        
        # 保存
        snap_file = os.path.join(snap_dir, f"快照_{chapter_num:04d}.md")
        write_file(snap_file, result)
        
        # 更新索引
        index_path = os.path.join(snap_dir, "索引.json")
        index = []
        if os.path.exists(index_path):
            try:
                index = json.loads(read_file(index_path))
            except Exception:
                pass
        index.append({"chapter": chapter_num, "file": f"快照_{chapter_num:04d}.md",
                       "timestamp": snapshot["timestamp"]})
        write_file(index_path, json.dumps(index, ensure_ascii=False, indent=2))
        
        if log_callback:
            log_callback(f"  角色快照已保存 (第{chapter_num}章)")
        
        return snapshot
    except Exception as e:
        return {"error": str(e)}


def get_latest_snapshot(book_dir: str) -> dict:
    """获取最近的角色快照"""
    from core import read_file
    
    snap_dir = os.path.join(book_dir, SNAPSHOT_DIR)
    index_path = os.path.join(snap_dir, "索引.json")
    
    if not os.path.exists(index_path):
        return None
    
    try:
        index = json.loads(read_file(index_path))
        if not index:
            return None
        latest = index[-1]
        content = read_file(os.path.join(snap_dir, latest["file"]))
        return {
            "chapter": latest["chapter"],
            "content": content,
            "timestamp": latest["timestamp"],
        }
    except Exception:
        return None


def should_snapshot(chapter_num: int) -> bool:
    """判断当前章节是否需要快照"""
    return chapter_num > 0 and chapter_num % SNAPSHOT_INTERVAL == 0


def get_snapshot_context(book_dir: str, max_chars: int = 2000) -> str:
    """获取快照上下文（用于注入续写prompt）
    
    优先用快照而不是全文摘要，因为快照是结构化的角色状态
    """
    snap = get_latest_snapshot(book_dir)
    if snap and snap.get("content"):
        return f"[角色状态快照 · 第{snap['chapter']}章]\n{snap['content'][:max_chars]}"
    return ""
