# deslop.py — 去 AI 味模块（规则引擎 + LLM 辅助）
# 参考 oh-story-claudecode/deslop 的方法论

import re
from core import llm_invoke, read_file, write_file
from prompts import DESLOP_PROMPT, DESLOP_CHECKLIST


# ─── 强度级别 ──────────────────────────────────────────
INTENSITY_LIGHT = 1
INTENSITY_MEDIUM = 2
INTENSITY_DEEP = 3

# ─── 高频 AI 词替换表 ────────────────────────────────────
# 注意：中文不能用 \b 单词边界，直接用普通字符串匹配
# (old, replacement, severity_level) — level 1 轻度, 2 中度, 3 深度
AI_WORD_REPLACEMENTS = [
    # Level 1
    ("然而", "但", 1),
    ("不禁", "", 1),
    ("始终", "一直", 1),
    ("忽然", "", 1),
    ("突然", "", 1),
    ("微微", "", 1),
    ("似乎", "", 1),
    ("仿佛", "", 1),
    ("竟然", "", 1),
    ("缓缓", "慢慢", 1),
    ("淡淡", "", 1),
    ("静静", "", 1),
    ("默默", "", 1),
    ("轻轻", "", 1),
    ("深深", "", 1),
    ("微微一笑", "笑了笑", 1),
    ("嘴角微扬", "笑了", 1),
    ("嘴角上扬", "笑了", 1),
    ("嘴角勾起一抹弧度", "笑了", 1),
    ("眼中闪过一丝", "", 1),
    ("心中暗道", "心想", 1),
    ("心中一动", "", 1),
    ("心头一震", "", 1),
    ("不由自主", "", 1),
    ("情不自禁", "", 1),
    ("下意识", "", 1),
    # Level 2
    ("或许", "", 2),
    ("可能", "", 2),
    ("一定", "", 2),
    ("必须", "", 2),
    ("在……中", "", 2),
    ("随着", "", 2),
    ("某种程度上", "", 2),
    ("毫无疑问", "", 2),
    ("不言而喻", "", 2),
    ("事实上", "", 2),
    ("实际上", "", 2),
    ("换言之", "", 2),
    ("换句话说", "", 2),
    ("可以说", "", 2),
    ("不得不说", "", 2),
    ("坦白说", "", 2),
    ("说实话", "", 2),
    ("令他意外的是", "", 2),
    ("让他没想到的是", "", 2),
    ("出乎意料的是", "", 2),
    ("不可思议的是", "", 2),
    ("难以置信的是", "", 2),
    # Level 3
    ("值得注意的是", "", 3),
    ("需要指出的是", "", 3),
    ("众所周知", "", 3),
    ("毋庸置疑", "", 3),
    ("显而易见", "", 3),
    ("总而言之", "", 3),
    ("综上所述", "", 3),
    ("与此同时", "", 3),
    ("就在这时", "", 3),
    ("不禁想到", "", 3),
    ("脑海里浮现出", "", 3),
    ("脑海中闪过", "", 3),
    ("内心深处", "", 3),
    ("一股莫名的", "", 3),
    ("一阵莫名的", "", 3),
    ("说时迟那时快", "", 3),
    ("话音刚落", "", 3),
    ("此言一出", "", 3),
]


def _is_inside_quotes(text: str, pos: int) -> bool:
    """检测位置 pos 是否在中文引号内（""/「」/『』）"""
    before = text[:pos]
    pairs = [('\u201c', '\u201d'), ('\u300c', '\u300d'), ('\u300e', '\u300f')]
    for open_q, close_q in pairs:
        opens = before.count(open_q)
        closes = before.count(close_q)
        if opens > closes:
            return True
    return False


def rule_based_deslop(text: str, intensity: int = 3) -> tuple:
    """规则引擎去 AI 味：替换高频词（跳过引号内内容）
    intensity: 1-轻度, 2-中度, 3-深度
    """
    result = text
    count = 0
    for pattern, replacement, level in AI_WORD_REPLACEMENTS:
        if level > intensity:
            continue
        new_parts = []
        last_end = 0
        for m in re.finditer(pattern, result):
            start, end = m.start(), m.end()
            if _is_inside_quotes(result, start):
                # 在引号内，保留原文
                new_parts.append(result[last_end:end])
            else:
                new_parts.append(result[last_end:start])
                new_parts.append(replacement)
                count += 1
            last_end = end
        new_parts.append(result[last_end:])
        result = "".join(new_parts)
    return result, count


def llm_deslop(text: str, stream_callback=None, stop_flag=None) -> str:
    """LLM 辅助去 AI 味"""
    prompt = DESLOP_PROMPT.format(text=text)
    return llm_invoke(prompt, stream_callback=stream_callback, stop_flag=stop_flag)


def deslop_file(input_path: str, output_path: str = "",
                use_llm: bool = True,
                log_callback=None) -> dict:
    text = read_file(input_path)
    if not text:
        return {"error": "文件为空或无法读取"}

    original_len = len(text)
    rule_text, rule_count = rule_based_deslop(text)
    if log_callback:
        log_callback(f"[规则引擎] 替换了 {rule_count} 处 AI 词汇")

    if use_llm:
        if log_callback:
            log_callback("[LLM] 正在去 AI 味改写...")
        final_text = llm_deslop(rule_text)
    else:
        final_text = rule_text

    if not output_path:
        output_path = input_path
    write_file(output_path, final_text)

    return {
        "original_len": original_len,
        "final_len": len(final_text),
        "rule_replacements": rule_count,
        "reduction": original_len - len(final_text)
    }


def scan_ai_words(text: str) -> list:
    results = []
    for pattern, _, _ in AI_WORD_REPLACEMENTS:
        matches = list(re.finditer(pattern, text))
        if matches:
            for m in matches:
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 20)
                context = text[start:end]
                results.append({
                    "word": m.group(),
                    "count": 1,
                    "context": f"...{context}..."
                })
    return results


def generate_ai_word_report(text: str) -> str:
    word_counts = {}
    for pattern, _, _ in AI_WORD_REPLACEMENTS:
        count = len(re.findall(pattern, text))
        if count > 0:
            word_counts[pattern] = count

    if not word_counts:
        return "未检测到明显 AI 高频词"

    report_lines = ["## AI 高频词统计\n"]
    report_lines.append("| 词汇 | 出现次数 |")
    report_lines.append("|------|---------|")
    for word, count in sorted(word_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {word} | {count} |")
    return "\n".join(report_lines)

# ═══════════════════════════════════════════════════════════
# 预览 + 导出替换列表
# ═══════════════════════════════════════════════════════════

def get_active_replacements(intensity: int = 2) -> list:
    """返回指定强度级别的活跃替换规则"""
    return [(p, r) for p, r, l in AI_WORD_REPLACEMENTS if l <= intensity]


def preview_replacements(text: str, intensity: int = 2) -> dict:
    """
    返回结构化替换预览数据，用于 GUI 对比视图
    
    Returns:
        dict: {
            "original": str,
            "processed": str,
            "replacements": [{old, new, pos, processed_pos, context}],
            "stats": {total, unique_words}
        }
    """
    active_rules = get_active_replacements(intensity)
    all_replacements = []
    result = text
    total = 0
    seen_words = set()
    offset = 0  # cumulative offset from previous replacements

    for pattern, replacement in active_rules:
        new_parts = []
        last_end = 0
        for m in re.finditer(pattern, result):
            start, end = m.start(), m.end()
            if _is_inside_quotes(result, start):
                new_parts.append(result[last_end:end])
                last_end = end
                continue

            # 记录替换（含 processed_pos 用于右栏高亮）
            ctx_start = max(0, start - 15)
            ctx_end = min(len(result), end + 15)
            processed_pos = start + offset
            all_replacements.append({
                "old": m.group(),
                "new": replacement,
                "pos": start,
                "processed_pos": processed_pos,
                "context": (
                    ("..." if start > 15 else "") +
                    result[ctx_start:start] +
                    f"[{m.group()}]" +
                    result[end:ctx_end] +
                    ("..." if ctx_end < len(result) else "")
                )
            })
            total += 1
            seen_words.add(pattern)
            new_parts.append(result[last_end:start])
            new_parts.append(replacement)
            offset += len(replacement) - len(m.group())
            last_end = end
        new_parts.append(result[last_end:])
        result = "".join(new_parts)

    return {
        "original": text,
        "processed": result,
        "replacements": all_replacements,
        "stats": {
            "total": total,
            "unique_words": len(seen_words)
        }
    }


def apply_selected_replacements(original: str, selected: list) -> str:
    """
    据用户选择的替换列表应用替换
    
    Args:
        original: 原始文本
        selected: [(old_word, replacement), ...] — 用户确认的替换规则
    Returns:
        str: 处理后的文本
    """
    result = original
    for pattern, replacement in selected:
        new_parts = []
        last_end = 0
        for m in re.finditer(pattern, result):
            start, end = m.start(), m.end()
            if _is_inside_quotes(result, start):
                new_parts.append(result[last_end:end])
            else:
                new_parts.append(result[last_end:start])
                new_parts.append(replacement)
            last_end = end
        new_parts.append(result[last_end:])
        result = "".join(new_parts)
    return result
