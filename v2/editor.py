# -*- coding: utf-8 -*-
"""editor.py --- AI交互式编辑器
对话式改稿：给指令→AI重写→before/after对比→可回退
"""

import os, json, re
from datetime import datetime

def edit_chapter(chapter_text: str, instruction: str, 
                 genre: str = "", context: str = "") -> dict:
    """根据自然语言指令修改章节
    
    Args:
        chapter_text: 原始章节
        instruction: 自然语言修改指令，如"打斗太软了，加点狠劲"
        genre: 小说类型
        context: 前后文上下文
    
    Returns:
        {original, edited, instruction, changes_summary, diff_segments}
    """
    from core import llm_invoke_ada
    
    prompt = f"""你是小说改稿编辑。根据用户指令修改以下章节。

[用户指令]
{instruction}

[原文]
{chapter_text[:5000]}

[前后文参考]
{context[:1000] if context else '无'}

要求：
1. 只修改指令要求的部分，其他尽量保持原样
2. 保持人物性格一致性
3. 改完后返回完整修改后的章节
4. 在章节末尾用【修改摘要】列出做了哪些改动

直接返回修改后的完整章节。"""

    try:
        edited = llm_invoke_ada(prompt)
        if not edited or edited.startswith('[错误'):
            return {"error": "AI响应失败", "original": chapter_text}
        
        # Extract change summary
        changes = ""
        match = re.search(r'【修改摘要】([\s\S]*?)$', edited)
        if match:
            changes = match.group(1).strip()
            edited = edited[:match.start()].strip()
        
        # Build diff segments
        diff = build_diff(chapter_text, edited)
        
        return {
            "original": chapter_text,
            "edited": edited,
            "instruction": instruction,
            "changes_summary": changes,
            "diff_segments": diff,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e), "original": chapter_text}


def build_diff(original: str, edited: str) -> list:
    """简易diff：标记增删改段落"""
    orig_lines = original.split('\n')
    edit_lines = edited.split('\n')
    
    segments = []
    max_len = max(len(orig_lines), len(edit_lines))
    
    for i in range(max_len):
        o = orig_lines[i] if i < len(orig_lines) else None
        e = edit_lines[i] if i < len(edit_lines) else None
        
        if o is None:
            segments.append({"type": "added", "new": e, "line": i+1})
        elif e is None:
            segments.append({"type": "removed", "old": o, "line": i+1})
        elif o != e:
            segments.append({"type": "changed", "old": o, "new": e, "line": i+1})
    
    return segments


def edit_dialogue(chapter_text: str, character_name: str, 
                  tone_instruction: str, genre: str = "") -> dict:
    """针对性修改某个角色的对话
    
    Args:
        chapter_text: 章节文本
        character_name: 角色名
        tone_instruction: 语气指令，如"更冷一点""更幽默"
    """
    from core import llm_invoke_ada
    
    prompt = f"""你是小说对话编辑。只修改以下章节中角色"{character_name}"的对话。

[修改要求]
{character_name}的对话应该：{tone_instruction}

[原文]
{chapter_text[:5000]}

要求：
1. 只修改{character_name}的对话部分，旁白和其他角色对话不动
2. 保持剧情走向不变
3. 返回完整修改后的章节"""

    try:
        edited = llm_invoke_ada(prompt)
        if edited and not edited.startswith('[错误'):
            return {"original": chapter_text, "edited": edited, "character": character_name, "tone": tone_instruction}
    except Exception:
        pass
    return {"error": "修改失败", "original": chapter_text}


def add_scene(chapter_text: str, scene_description: str, 
              position: str = "middle", genre: str = "") -> dict:
    """在章节中插入新场景
    
    Args:
        position: 'beginning', 'middle', 'end', 或 'after_paragraph:N'
    """
    from core import llm_invoke_ada
    
    prompt = f"""在以下章节的{position}位置插入一个新场景。

[新场景描述]
{scene_description}

[原文]
{chapter_text[:5000]}

要求：
1. 新场景自然融入，不显突兀
2. 保持文风一致
3. 返回完整修改后的章节"""

    try:
        edited = llm_invoke_ada(prompt)
        if edited and not edited.startswith('[错误'):
            return {"original": chapter_text, "edited": edited, "scene": scene_description}
    except Exception:
        pass
    return {"error": "添加失败", "original": chapter_text}


# ---------------------------------------------------------------------------
# Edit history (undo/redo)
# ---------------------------------------------------------------------------

class EditHistory:
    """编辑历史管理器"""
    def __init__(self, max_history: int = 20):
        self.history = []   # [(chapter_text, instruction)]
        self.current = -1
        self.max_history = max_history
    
    def push(self, text: str, instruction: str = ""):
        """保存当前状态"""
        self.history = self.history[:self.current + 1]
        self.history.append({"text": text, "instruction": instruction, "time": datetime.now().isoformat()})
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.current = len(self.history) - 1
    
    def undo(self):
        """撤销"""
        if self.current > 0:
            self.current -= 1
            return self.history[self.current]["text"]
        return None
    
    def redo(self):
        """重做"""
        if self.current < len(self.history) - 1:
            self.current += 1
            return self.history[self.current]["text"]
        return None
    
    def can_undo(self) -> bool:
        return self.current > 0
    
    def can_redo(self) -> bool:
        return self.current < len(self.history) - 1
