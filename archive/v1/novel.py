# novel.py — 小说生成管线
# 参考 AI_NovelGenerator 的 pipeline 设计，去掉 GUI 依赖

import os
import re
import time
import json
import threading
from core import (
    llm_invoke, llm_invoke_ada, read_file, write_file,
    append_file, ensure_dir, count_words, get_output_dir
)
from prompts import (
    SETTING_GENERATION, DIRECTORY_GENERATION,
    CHAPTER_GENERATION, SUMMARY_UPDATE
)
from deslop import rule_based_deslop


def generate_novel(config: dict = None,
                   log_callback=None,
                   stream_callback=None,
                   stop_flag=None) -> dict:
    """
    生成一本完整的小说。
    
    Args:
        config: 覆盖配置的字段（可部分覆盖 config.json）
        log_callback: 日志回调 log(text)
        stream_callback: 流式输出回调 stream(text)
        stop_flag: threading.Event，置位则停止生成
    
    Returns:
        dict: 生成结果统计
    """
    from core import load_config
    cfg = load_config()
    if config:
        cfg["novel"].update(config.get("novel", {}))
        if "output_dir" in config:
            cfg["output_dir"] = config["output_dir"]
        if "use_local" in config:
            cfg["use_local"] = config["use_local"]

    topic = cfg["novel"]["topic"]
    genre = cfg["novel"]["genre"]
    num_chapters = cfg["novel"]["num_chapters"]
    target_words = cfg["novel"]["words_per_chapter"]

    if not topic:
        return {"error": "请先填写小说主题（topic）"}

    # 创建输出目录
    # 用主题的简洁版本作为目录名
    dir_name = re.sub(r'[\\/:*?"<>|]', '', topic)[:30].strip()
    if not dir_name:
        dir_name = f"novel_{int(time.time())}"

    book_dir = os.path.join(get_output_dir(), dir_name)
    ensure_dir(book_dir)

    start_time = time.time()

    if log_callback:
        log_callback(f"📖 开始生成小说: {topic}")
        log_callback(f"   类型: {genre} | 章节: {num_chapters} | 每章: {target_words}字")
        log_callback(f"   输出目录: {book_dir}\n")

    # ─── Step 0: 生成设定 ──────────────
    if log_callback:
        log_callback("[1/4] 生成世界观设定...")

    v1 = max(1, num_chapters // 3)
    v2 = max(1, num_chapters * 2 // 3)

    setting_prompt = SETTING_GENERATION.format(
        topic=topic, genre=genre, num_chapters=num_chapters,
        v1=v1, v1p1=v1 + 1, v2=v2, v2p1=v2 + 1
    )

    novel_setting = llm_invoke_ada(
        setting_prompt,
        system_msg="你是一位专业的网文作家。请按照要求的格式输出。"
    )
    write_file(os.path.join(book_dir, "设定.md"), novel_setting)

    if log_callback:
        log_callback(f"  ✓ 设定完成 ({count_words(novel_setting)} 字)")

    if stop_flag and stop_flag.is_set():
        return {"status": "已停止", "book_dir": book_dir}

    # ─── Step 1: 生成目录 ──────────────
    if log_callback:
        log_callback("[2/4] 生成章节目录...")

    dir_prompt = DIRECTORY_GENERATION.format(
        num_chapters=num_chapters,
        novel_setting=novel_setting,
        v1=v1, v2=v2
    )

    directory_text = llm_invoke_ada(
        dir_prompt,
        system_msg="你是一位专业的网文作家。请严格按照格式输出章节目录。"
    )
    write_file(os.path.join(book_dir, "目录.md"), directory_text)

    # 解析目录为章节列表
    chapters = _parse_directory(directory_text, num_chapters)

    if log_callback:
        log_callback(f"  ✓ 目录生成完成 ({len(chapters)} 章)")

    if stop_flag and stop_flag.is_set():
        return {"status": "已停止", "book_dir": book_dir}

    # ─── Step 2&3: 逐章生成 ────────────
    if log_callback:
        log_callback(f"\n[3/4] 逐章生成正文...")

    summary = f"初始设定：{topic}（{genre}，共{num_chapters}章）\n"
    total_generated = 0
    chapters_done = 0

    # 确保正文目录
    chapter_dir = os.path.join(book_dir, "正文")
    ensure_dir(chapter_dir)

    for i, ch in enumerate(chapters, 1):
        if stop_flag and stop_flag.is_set():
            if log_callback:
                log_callback(f"\n⏹ 已停止（完成 {chapters_done}/{num_chapters} 章）")
            break

        chapter_num = ch["num"]
        chapter_title = ch["title"]
        chapter_desc = ch.get("desc", "")

        if log_callback:
            log_callback(f"  [{chapter_num}/{num_chapters}] 第{chapter_num}章 {chapter_title}...")

        # 读取已完成的章节摘要（从文件中）
        summary_file = os.path.join(book_dir, "全局摘要.txt")
        current_summary = read_file(summary_file)
        if not current_summary:
            current_summary = summary

        ch_prompt = CHAPTER_GENERATION.format(
            chapter_num=chapter_num,
            novel_setting=novel_setting,
            directory=directory_text,
            summary_text=current_summary,
            chapter_title=chapter_title,
            chapter_desc=chapter_desc,
            target_words=target_words
        )

        # 生成章节（流式+非流式混合）
        chapter_content = llm_invoke_ada(ch_prompt)

        if not chapter_content or chapter_content.startswith("[错误]"):
            if log_callback:
                log_callback(f"    ✗ 生成失败: {chapter_content}")
            continue

        # 去 AI 味（规则引擎，轻量）
        chapter_content_cleaned, _ = rule_based_deslop(chapter_content)

        # 保存章节
        chapter_file = os.path.join(chapter_dir, f"第{chapter_num:03d}章_{chapter_title}.md")
        write_file(chapter_file, chapter_content_cleaned)

        chapter_words = count_words(chapter_content_cleaned)
        total_generated += chapter_words
        chapters_done += 1

        if log_callback:
            log_callback(f"    ✓ {chapter_words} 字")

        if stream_callback:
            stream_callback(f"第{chapter_num}章完成: {chapter_words}字\n")

        # ─── 更新全局摘要 ────────────────
        if log_callback:
            log_callback(f"    ↻ 更新全局摘要...")

        # 用已经生成的章节摘要来生成新摘要
        summary_prompt = SUMMARY_UPDATE.format(
            summary_text=current_summary,
            chapter_num=chapter_num,
            chapter_title=chapter_title,
            chapter_content=chapter_content_cleaned[:2000]
        )

        new_summary = llm_invoke_ada(summary_prompt)
        write_file(summary_file, new_summary)

    # ─── 结果汇总 ──────────────────────
    elapsed = time.time() - start_time
    result = {
        "status": "完成" if chapters_done == num_chapters else "部分完成",
        "book_dir": book_dir,
        "topic": topic,
        "genre": genre,
        "chapters_planned": num_chapters,
        "chapters_done": chapters_done,
        "total_words": total_generated,
        "elapsed_seconds": round(elapsed, 1),
        "words_per_minute": round(total_generated / (elapsed / 60), 0) if elapsed > 0 else 0
    }

    # 保存摘要报告
    report = f"""# 生成报告：{topic}

- 状态：{result['status']}
- 类型：{genre}
- 计划章节：{num_chapters}
- 完成章节：{chapters_done}
- 总字数：{total_generated:,}
- 用时：{elapsed:.0f} 秒
- 生成速度：{result['words_per_minute']:.0f} 字/分钟
- 输出目录：{book_dir}
"""
    write_file(os.path.join(book_dir, "生成报告.md"), report)

    if log_callback:
        log_callback(f"\n{'='*50}")
        log_callback(f"✅ 生成{'完成' if chapters_done == num_chapters else '部分完成'}")
        log_callback(f"   完成 {chapters_done}/{num_chapters} 章")
        log_callback(f"   总字数: {total_generated:,}")
        log_callback(f"   用时: {elapsed:.0f} 秒")
        log_callback(f"   输出目录: {book_dir}")
        log_callback(f"{'='*50}")

    return result


def _parse_directory(dir_text: str, expected_count: int) -> list:
    """解析目录文本为章节列表"""
    chapters = []
    lines = dir_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 匹配格式: 第001章: 标题 ─ 描述
        m = re.match(r'第(\d+)章[：:]?\s*(.+?)(?:[─\-—]\s*(.+))?$', line)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            desc = m.group(3).strip() if m.group(3) else ""
            chapters.append({"num": num, "title": title, "desc": desc})
        else:
            # 尝试更宽松的匹配
            m2 = re.match(r'(\d+)[.、．\s]+(.+)', line)
            if m2:
                num = int(m2.group(1))
                rest = m2.group(2).strip()
                if '─' in rest or '—' in rest or '-' in rest:
                    parts = re.split(r'[─—\-]', rest, 1)
                    title = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                else:
                    title = rest
                    desc = ""
                chapters.append({"num": num, "title": title, "desc": desc})

    # 按章节号排序
    chapters.sort(key=lambda x: x["num"])

    # 如果解析不到，为每个期望的章节生成占位
    if not chapters:
        chapters = [
            {"num": i, "title": f"第{i}章", "desc": ""}
            for i in range(1, expected_count + 1)
        ]

    return chapters