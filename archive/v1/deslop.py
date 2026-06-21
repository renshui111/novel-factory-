# deslop.py — 去 AI 味模块（规则引擎 + LLM 辅助）
# 参考 oh-story-claudecode/deslop 的方法论

import re
from core import llm_invoke, read_file, write_file
from prompts import DESLOP_PROMPT, DESLOP_CHECKLIST


# ─── 高频 AI 词替换表 ────────────────────────────────────
AI_WORD_REPLACEMENTS = [
    # 高频废话词
    (r'\b然而\b', '但'),
    (r'\b不禁\b', ''),
    (r'\b始终\b', '一直'),
    (r'\b忽然\b', ''),
    (r'\b突然\b', ''),
    (r'\b微微\b', ''),
    (r'\b似乎\b', ''),
    (r'\b仿佛\b', ''),
    (r'\b或许\b', ''),
    (r'\b可能\b', ''),
    (r'\b一定\b', ''),
    (r'\b必须\b', ''),
    (r'\b在……中\b', ''),
    (r'\b随着\b', ''),
    (r'\b值得注意的是\b', ''),
    (r'\b需要指出的是\b', ''),
    (r'\b众所周知\b', ''),
    (r'\b毋庸置疑\b', ''),
    (r'\b显而易见\b', ''),
    (r'\b总而言之\b', ''),
    (r'\b综上所述\b', ''),
    (r'\b与此同时\b', ''),
    (r'\b就在这时\b', ''),
    (r'\b就在这时，\b', ''),
    (r'\b就在这时，\b', ''),
]


def rule_based_deslop(text: str) -> str:
    """规则引擎去 AI 味：替换高频词"""
    result = text
    count = 0
    for pattern, replacement in AI_WORD_REPLACEMENTS:
        new_result, n = re.subn(pattern, replacement, result)
        count += n
        result = new_result
    return result, count


def llm_deslop(text: str, stream_callback=None, stop_flag=None) -> str:
    """LLM 辅助去 AI 味"""
    prompt = DESLOP_PROMPT.format(text=text)
    return llm_invoke(prompt, stream_callback=stream_callback, stop_flag=stop_flag)


def deslop_file(input_path: str, output_path: str = "",
                use_llm: bool = True,
                log_callback=None) -> dict:
    """
    对文件执行去 AI 味处理。
    返回统计信息 dict。
    """
    text = read_file(input_path)
    if not text:
        return {"error": "文件为空或无法读取"}

    original_len = len(text)

    # 第一步：规则引擎
    rule_text, rule_count = rule_based_deslop(text)
    if log_callback:
        log_callback(f"[规则引擎] 替换了 {rule_count} 处 AI 词汇")

    # 第二步：LLM 辅助（可选）
    if use_llm:
        if log_callback:
            log_callback("[LLM] 正在去 AI 味改写...")
        final_text = llm_deslop(rule_text)
    else:
        final_text = rule_text

    # 保存
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
    """扫描文本中 AI 高频词的出现位置和频率"""
    results = []
    for pattern, _ in AI_WORD_REPLACEMENTS:
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
    """生成 AI 词频统计报告"""
    word_counts = {}
    for pattern, replacement in AI_WORD_REPLACEMENTS:
        # Extract the base word from the pattern
        word = pattern.replace(r'\b', '')
        count = len(re.findall(pattern, text))
        if count > 0:
            word_counts[word] = count

    if not word_counts:
        return "✅ 未检测到明显 AI 高频词"

    report_lines = ["## AI 高频词统计\n"]
    report_lines.append("| 词汇 | 出现次数 |")
    report_lines.append("|------|---------|")
    for word, count in sorted(word_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {word} | {count} |")

    return "\n".join(report_lines)