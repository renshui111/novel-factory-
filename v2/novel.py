# novel.py — 小说生成管线
# 分步 + 断点续写 + 并行生成 + 自动保存 + 单章重写 + 角色档案

import os
import re
import time
import json
import threading
from datetime import datetime
from core import (
    llm_invoke, llm_invoke_ada, read_file, write_file,
    append_file, ensure_dir, count_words, get_output_dir
)
from prompts import (
    SETTING_GENERATION, DIRECTORY_GENERATION,
    CHAPTER_GENERATION, SUMMARY_UPDATE,
    CONSISTENCY_CHECK_PROMPT, EXTRACT_CHARACTERS_PROMPT
)
from deslop import rule_based_deslop

CHECKPOINT_FILE = "checkpoint.json"


# ═══════════════════════════════════════════════════════════
# 准备
# ═══════════════════════════════════════════════════════════
def prepare_book_dir(topic: str) -> str:
    dir_name = re.sub(r'[\\/:*?"<>|]', '', topic)[:30].strip()
    if not dir_name:
        dir_name = f"novel_{int(time.time())}"
    book_dir = os.path.join(get_output_dir(), dir_name)
    ensure_dir(book_dir)
    ensure_dir(os.path.join(book_dir, "正文"))
    return book_dir


# ═══════════════════════════════════════════════════════════
# 任务 1：断点续写
# ═══════════════════════════════════════════════════════════
def save_checkpoint(book_dir: str, chapter_num: int, summary: str):
    cp = {
        "chapter_completed": chapter_num,
        "summary": summary,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    # 原子写入：先写 tmp，再 rename
    tmp_path = os.path.join(book_dir, CHECKPOINT_FILE + ".tmp")
    write_file(tmp_path, json.dumps(cp, ensure_ascii=False, indent=2))
    target = os.path.join(book_dir, CHECKPOINT_FILE)
    if os.path.exists(target):
        os.remove(target)
    os.rename(tmp_path, target)


def load_checkpoint(book_dir: str):
    path = os.path.join(book_dir, CHECKPOINT_FILE)
    if not os.path.exists(path):
        return None
    try:
        return json.loads(read_file(path))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
# Step 1: 生成设定
# ═══════════════════════════════════════════════════════════
def generate_setting(topic: str, genre: str, num_chapters: int,
                     book_dir: str, log_callback=None) -> str:
    v1 = max(1, num_chapters // 3)
    v2 = max(1, num_chapters * 2 // 3)
    prompt = SETTING_GENERATION.format(
        topic=topic, genre=genre, num_chapters=num_chapters,
        v1=v1, v1p1=v1 + 1, v2=v2, v2p1=v2 + 1)
    if log_callback:
        log_callback("正在生成世界观设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文作家。请按照要求的格式输出。")
    write_file(os.path.join(book_dir, "设定.md"), result)
    if log_callback:
        log_callback(f"设定完成 ({count_words(result)} 字)")
    return result


# ═══════════════════════════════════════════════════════════
# Step 2: 生成目录
# ═══════════════════════════════════════════════════════════
def generate_directory(novel_setting: str, num_chapters: int,
                       book_dir: str, log_callback=None) -> list:
    v1 = max(1, num_chapters // 3)
    v2 = max(1, num_chapters * 2 // 3)
    prompt = DIRECTORY_GENERATION.format(
        num_chapters=num_chapters, novel_setting=novel_setting,
        v1=v1, v2=v2)
    if log_callback:
        log_callback("正在生成章节目录...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文作家。请严格按照格式输出章节目录。")
    write_file(os.path.join(book_dir, "目录.md"), result)
    chapters = _parse_directory(result, num_chapters)
    if log_callback:
        log_callback(f"目录生成完成 ({len(chapters)} 章)")
    return chapters


# ═══════════════════════════════════════════════════════════
# Step 3: 生成单章
# ═══════════════════════════════════════════════════════════
def generate_chapter(chapter_num: int, chapter_title: str,
                     novel_setting: str, directory_text: str,
                     summary: str, target_words: int,
                     book_dir: str, log_callback=None,
                     stream_callback=None, stop_flag=None) -> dict:
    chapter_dir = os.path.join(book_dir, "正文")
    ensure_dir(chapter_dir)
    prompt = CHAPTER_GENERATION.format(
        chapter_num=chapter_num, novel_setting=novel_setting,
        directory=directory_text, summary_text=summary,
        chapter_title=chapter_title, chapter_desc="",
        target_words=target_words)

    if stream_callback:
        collected = []
        content = llm_invoke(prompt,
            system_msg="你是一位专业的网文作家。请直接输出章节正文，不要额外解释。",
            stream_callback=lambda c: (collected.append(c), stream_callback(c)) and None,
            stop_flag=stop_flag)
        if collected:
            content = "".join(collected)
    else:
        if log_callback:
            log_callback("  生成中...")
        content = llm_invoke_ada(prompt)

    if not content or content.startswith("[错误]"):
        if log_callback:
            log_callback(f"  \u2717 生成失败: {content}")
        return {"content": "", "path": "", "words": 0, "success": False}

    cleaned, _ = rule_based_deslop(content)

    # 字数校验 + 自动补钩子
    validation = validate_chapter(cleaned, chapter_num, target_words, book_dir)
    if not validation["pass"]:
        if "结尾缺少悬念钩子" in str(validation["issues"]):
            hooks = [
                "\n\n但他不知道，更大的危机正在悄然逼近。",
                "\n\n远处的天际，一道黑影正急速逼近……",
                "\n\n而在暗处，一双眼睛正静静注视着这一切。",
                "\n\n真正的危险，才刚刚开始。",
            ]
            import random
            cleaned += random.choice(hooks)
        if log_callback and validation["issues"]:
            joined_issues = "; ".join(validation["issues"])
            log_callback(f"  ⚠️ 校验提醒: {joined_issues}")

    ch_file = os.path.join(chapter_dir, f"第{chapter_num:03d}章_{chapter_title}.md")
    write_file(ch_file, cleaned)
    wc = count_words(cleaned)
    if log_callback:
        log_callback(f"  ✓ {wc} 字")
    return {"content": cleaned, "path": ch_file, "words": wc, "success": True}


# ═══════════════════════════════════════════════════════════
# Step 3b: 更新全局摘要
# ═══════════════════════════════════════════════════════════
def update_summary(chapter_num: int, chapter_title: str,
                   chapter_content: str, current_summary: str,
                   book_dir: str, log_callback=None) -> str:
    prompt = SUMMARY_UPDATE.format(
        summary_text=current_summary, chapter_num=chapter_num,
        chapter_title=chapter_title, chapter_content=chapter_content[:2000])
    new_summary = llm_invoke_ada(prompt)
    write_file(os.path.join(book_dir, "全局摘要.txt"), new_summary)
    return new_summary


# ═══════════════════════════════════════════════════════════
# 任务 7：自动保存（每 30 秒）
# ═══════════════════════════════════════════════════════════
_auto_save_timer = None

def auto_save(book_dir: str, novel_setting: str, chapters: list, summary: str):
    """每 30 秒将已生成的章节备份到 autosave/ 目录"""
    save_dir = os.path.join(book_dir, "autosave")
    ensure_dir(save_dir)
    ch_dir = os.path.join(book_dir, "正文")
    if os.path.exists(ch_dir):
        for fname in os.listdir(ch_dir):
            if fname.endswith(".md"):
                src = os.path.join(ch_dir, fname)
                dst = os.path.join(save_dir, fname)
                now = time.time()
                # 跳过最近 5 秒修改的文件（防主线程半写）
                if now - os.path.getmtime(src) < 5:
                    continue
                if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                    write_file(dst, read_file(src))

    global _auto_save_timer
    _auto_save_timer = threading.Timer(30.0, auto_save,
        args=(book_dir, novel_setting, chapters, summary))
    _auto_save_timer.daemon = True
    _auto_save_timer.start()


def stop_auto_save():
    global _auto_save_timer
    if _auto_save_timer:
        _auto_save_timer.cancel()
        _auto_save_timer = None


# ═══════════════════════════════════════════════════════════
# 任务 8：单章重写
# ═══════════════════════════════════════════════════════════
def rewrite_chapter(chapter_num: int, reason: str, book_dir: str,
                    novel_setting: str, directory_text: str,
                    target_words: int, log_callback=None) -> dict:
    """重写指定章节"""
    reason_map = {
        "short": "本章字数不足，请扩充内容，增加更多细节和对话。",
        "water": "本章注水严重，请删除无关内容，聚焦主线冲突。",
        "off_outline": "本章偏离了大纲，请严格按照章节定位重写。",
        "change_style": "请改变写作风格，增加文采和画面感。",
    }
    extra_instruction = reason_map.get(reason, "请重新生成本章，提高质量。")

    ch_dir = os.path.join(book_dir, "正文")
    chapters_path = os.path.join(book_dir, "目录.md")
    dir_text = read_file(chapters_path) or directory_text

    summary = read_file(os.path.join(book_dir, "全局摘要.txt"))

    # 读取原章节标题
    old_path = None
    for fname in os.listdir(ch_dir):
        if fname.startswith(f"第{chapter_num:03d}章"):
            old_path = os.path.join(ch_dir, fname)
            break

    if old_path:
        # 旧版重命名为 v2
        base, ext = os.path.splitext(old_path)
        os.rename(old_path, f"{base}_v2{ext}")

    prompt = CHAPTER_GENERATION.format(
        chapter_num=chapter_num,
        novel_setting=novel_setting,
        directory=dir_text,
        summary_text=summary,
        chapter_title=f"第{chapter_num}章（重写）",
        chapter_desc=extra_instruction,
        target_words=target_words)

    if log_callback:
        log_callback(f"正在重写第{chapter_num}章（原因: {reason}）...")

    content = llm_invoke_ada(prompt)
    if not content or content.startswith("[错误]"):
        return {"content": "", "path": "", "words": 0, "success": False}

    cleaned, _ = rule_based_deslop(content)

    # 用原标题保存
    if old_path:
        title = os.path.basename(old_path).replace(f"第{chapter_num:03d}章_", "").replace(".md", "")
    else:
        title = f"第{chapter_num}章"
    ch_file = os.path.join(ch_dir, f"第{chapter_num:03d}章_{title}.md")
    write_file(ch_file, cleaned)

    wc = count_words(cleaned)
    if log_callback:
        log_callback(f"  重写完成: {wc} 字")
    return {"content": cleaned, "path": ch_file, "words": wc, "success": True}


# ═══════════════════════════════════════════════════════════
# 任务 9：角色档案系统
# ═══════════════════════════════════════════════════════════
CHARACTER_ARCHIVE_FILE = "角色档案.md"




def init_character_archive(book_dir: str, novel_setting: str = ""):
    """创建初始角色档案"""
    content = "# 角色档案\n\n"
    if novel_setting:
        content += "## 初始设定中提取的角色\n\n"
        content += "（角色将在章节生成过程中自动提取和更新）\n\n"
    write_file(os.path.join(book_dir, CHARACTER_ARCHIVE_FILE), content)


def update_character_archive(chapter_content: str, chapter_num: int, book_dir: str,
                              log_callback=None):
    """从章节中提取角色信息并更新档案"""
    archive_path = os.path.join(book_dir, CHARACTER_ARCHIVE_FILE)
    existing = read_file(archive_path)
    if not existing:
        init_character_archive(book_dir)

    prompt = EXTRACT_CHARACTERS_PROMPT.format(
        existing_archive=existing[-3000:] if len(existing) > 3000 else existing,
        chapter_text=chapter_content[:4000],
        chapter_num=chapter_num
    )

    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的小说角色分析师。请提取角色信息并格式化输出。")

    if result and not result.startswith("[错误]"):
        append_file(os.path.join(book_dir, CHARACTER_ARCHIVE_FILE),
                    f"\n\n--- 第{chapter_num}章更新 ---\n" + result)

    if log_callback:
        log_callback(f"  角色档案已更新")


def check_character_consistency(book_dir: str) -> str:
    """检查角色档案的一致性"""
    archive = read_file(os.path.join(book_dir, CHARACTER_ARCHIVE_FILE))
    if not archive:
        return "未找到角色档案"

    prompt = CONSISTENCY_CHECK_PROMPT + "\n\n角色档案：\n" + archive[:6000]
    result = llm_invoke_ada(prompt,
        system_msg="你是一位严格的网文角色一致性检查员。")
    return result


# ═══════════════════════════════════════════════════════════
# 完整管线
# ═══════════════════════════════════════════════════════════
def generate_novel(config: dict = None,
                   log_callback=None,
                   stream_callback=None,
                   stop_flag=None,
                   progress_callback=None,
                   custom_outline_path: str = None) -> dict:
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

    book_dir = prepare_book_dir(topic)
    start_time = time.time()

    if log_callback:
        log_callback(f"[小说] {topic}")
        log_callback(f"   类型: {genre} | {num_chapters}\u7ae0 \u00d7 {target_words}\u5b57")
        log_callback(f"   目录: {book_dir}\n")

    if progress_callback:
        progress_callback("step_start", {"step": "生成设定", "total": num_chapters, "desc": topic})

    # ─── Step 1 ─────────────────────────
    novel_setting = generate_setting(topic, genre, num_chapters, book_dir, log_callback)
    if not novel_setting or (stop_flag and stop_flag.is_set()):
        return {"status": "\u5df2\u505c\u6b62", "book_dir": book_dir}

    if progress_callback:
        progress_callback("step_done", {"step": "生成设定", "result": f"{count_words(novel_setting)} 字"})
        progress_callback("step_start", {"step": "生成目录", "total": num_chapters, "desc": ""})

    # ─── 卷规划 + 节奏表 ────────────────
    try:
        from planner import plan_volumes, build_rhythm_table
        volumes = plan_volumes(novel_setting, num_chapters, book_dir, log_callback)
        rhythm = build_rhythm_table(volumes, num_chapters, book_dir, log_callback)
    except ImportError:
        if log_callback:
            log_callback("  [!] planner模块未找到，跳过卷规划")
    except Exception as e:
        if log_callback:
            log_callback(f"  [!] 卷规划异常: {e}")

    # ─── Step 2: 目录（自定义大纲或 AI 生成） ────────
    if custom_outline_path and os.path.exists(custom_outline_path):
        # 用户导入自定义大纲
        if log_callback:
            log_callback(f"  使用自定义大纲: {custom_outline_path}")
        dir_text = read_file(custom_outline_path)
        chapters = _parse_directory(dir_text, num_chapters)
        if not chapters:
            if log_callback:
                log_callback("  [!] 自定义大纲解析失败，回退到 AI 生成")
            chapters = generate_directory(novel_setting, num_chapters, book_dir, log_callback)
        else:
            # 保存到目录.md
            write_file(os.path.join(book_dir, "目录.md"), dir_text)
            if log_callback:
                log_callback(f"  自定义大纲导入成功 ({len(chapters)} 章)")
    else:
        chapters = generate_directory(novel_setting, num_chapters, book_dir, log_callback)
    
    if not chapters or (stop_flag and stop_flag.is_set()):
        return {"status": "\u5df2\u505c\u6b62", "book_dir": book_dir}

    dir_lines = "\n".join([f"\u7b2c{c['num']:03d}\u7ae0: {c['title']}" for c in chapters])
    directory_text = read_file(os.path.join(book_dir, "\u76ee\u5f55.md")) or dir_lines

    # 初始化角色档案
    init_character_archive(book_dir, novel_setting)

    # ─── Step 3 ─────────────────────────
    if log_callback:
        log_callback(f"\n\u5f00\u59cb\u9010\u7ae0\u751f\u6210 ({num_chapters} \u7ae0)...")

    # 检测断点
    cp = load_checkpoint(book_dir)
    start_from = 0
    summary = f"{topic}（{genre}，共{num_chapters}章）\n"
    if cp:
        start_from = cp.get("chapter_completed", 0)
        summary = cp.get("summary", summary)
        if log_callback and start_from > 0:
            log_callback(f"  检测到断点：已完成 {start_from} 章，从第 {start_from + 1} 章继续")

    total_generated = 0
    chapters_done = start_from

    # 跳过已完成的
    pending = []
    for ch in chapters:
        if ch['num'] <= start_from:
            p = os.path.join(book_dir, "正文", f"\u7b2c{ch['num']:03d}\u7ae0_{ch['title']}.md")
            if os.path.exists(p):
                total_generated += count_words(read_file(p))
            continue
        pending.append(ch)

    # 启动自动保存
    auto_save(book_dir, novel_setting, chapters, summary)

    # 向量上下文检索（可选，无依赖时 fallback 到纯文本摘要）
    try:
        _vector_ctx = VectorContext()
    except Exception:
        _vector_ctx = None

    # 并行生成（最多同时 3 章），每批共用当前摘要，批完后串行更新
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _submit_chapter(ch, current_summary):
        """提交单章生成任务"""
        route = _route_model('chapter', cfg)
        if route.get('use_local') != cfg.get('use_local', False):
            cfg['use_local'] = route['use_local']
        return generate_chapter(
            ch['num'], ch['title'],
            novel_setting, directory_text, current_summary,
            target_words, book_dir, log_callback=None,
            stream_callback=None, stop_flag=stop_flag)

    BATCH_SIZE = 3
    for batch_start in range(0, len(pending), BATCH_SIZE):
        if stop_flag and stop_flag.is_set():
            break

        batch = pending[batch_start:batch_start + BATCH_SIZE]
        batch_summary = read_file(os.path.join(book_dir, "全局摘要.txt")) or summary

        # 向量检索增强上下文
        if _vector_ctx and chapters_done > start_from:
            for ch in batch:
                query = ch.get('title', '') + ' ' + ch.get('desc', '')
                if query.strip():
                    retrieved = _vector_ctx.search(query, n=min(3, chapters_done))
                    if retrieved:
                        batch_summary = f"{batch_summary}\n\n## 相关前文检索\n{retrieved}"

        if log_callback:
            log_callback(f"[批次 {batch_start // BATCH_SIZE + 1}] {len(batch)} 章并行生成...")

        # 并行提交
        batch_results = {}  # ch_num -> result
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_submit_chapter, ch, batch_summary): ch for ch in batch}

            for future in as_completed(futures):
                if stop_flag and stop_flag.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                ch = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    if log_callback:
                        log_callback(f"  ✗ 第{ch['num']}章异常: {e}")
                    continue

                # 日志+进度回调（线程安全，通过 root.after）
                if log_callback:
                    log_callback(f"[{ch['num']}/{num_chapters}] {ch['title']} {'✓' + str(result['words']) + '字' if result['success'] else '失败'}")
                if progress_callback:
                    progress_callback("chapter_start", {
                        "chapter_num": ch['num'], "title": ch['title'], "total": num_chapters})

                if not result["success"]:
                    continue

                chapters_done += 1
                total_generated += result["words"]
                batch_results[ch['num']] = result

                if progress_callback:
                    progress_callback("chapter_done", {
                        "chapter_num": ch['num'], "title": ch['title'],
                        "words": result['words'], "path": result.get('path', ''),
                        "elapsed": round(time.time() - start_time, 1),
                        "total_words": total_generated})

                if stream_callback:
                    stream_callback(f"第{ch['num']}章完成: {result['words']}字\n")

                # 立即写 checkpoint（只存进度，摘要后续统一更新）
                save_checkpoint(book_dir, chapters_done, batch_summary)

        # 批次结束后：串行更新摘要 + 角色档案（按章节号排序）
        if not stop_flag or not stop_flag.is_set():
            for ch in sorted(batch, key=lambda x: x['num']):
                result = batch_results.get(ch['num'])
                if not result:
                    continue
                # 更新全局摘要
                current_summ = read_file(os.path.join(book_dir, "全局摘要.txt")) or summary
                new_summary = update_summary(
                    ch['num'], ch['title'], result['content'],
                    current_summ, book_dir, log_callback=log_callback)
                # 更新角色档案
                update_character_archive(
                    result['content'], ch['num'], book_dir,
                    log_callback=log_callback)
                # 向量索引
                if _vector_ctx:
                    _vector_ctx.add_chapter(ch['num'], ch['title'], result["content"])
                # 更新断点摘要
                save_checkpoint(book_dir, chapters_done, new_summary or current_summ)

    stop_auto_save()

    # ─── 结果 ───────────────────────────
    elapsed = time.time() - start_time
    res = {
        "status": "完成" if chapters_done == num_chapters else "部分完成",
        "book_dir": book_dir, "topic": topic, "genre": genre,
        "chapters_planned": num_chapters, "chapters_done": chapters_done,
        "total_words": total_generated,
        "elapsed_seconds": round(elapsed, 1),
        "words_per_minute": round(total_generated / (elapsed / 60), 0) if elapsed > 0 else 0
    }

    report = f"""# 生成报告：{topic}

- 状态：{res['status']}
- 类型：{genre}
- 计划章节：{num_chapters}
- 完成章节：{chapters_done}
- 总字数：{total_generated:,}
- 用时：{elapsed:.0f} 秒
- 生成速度：{res['words_per_minute']:.0f} 字/分钟
- 输出目录：{book_dir}
"""
    write_file(os.path.join(book_dir, "生成报告.md"), report)

    # 全部完成时删除 checkpoint
    if chapters_done == num_chapters:
        cp_path = os.path.join(book_dir, CHECKPOINT_FILE)
        if os.path.exists(cp_path):
            os.remove(cp_path)

    if log_callback:
        log_callback(f"\n{'='*50}")
        log_callback(f"\u2705 完成 {chapters_done}/{num_chapters} 章 | {total_generated:,} 字 | {elapsed:.0f}s")
        log_callback(f"[目录] {book_dir}")
        log_callback(f"{'='*50}")

    # 自动导出
    try:
        from export import export_all
        export_all(book_dir, log_callback)
    except ImportError:
        pass

    return res


# ─── 工具 ────────────────────────────────────────────────
def _parse_directory(dir_text: str, expected_count: int) -> list:
    chapters = []
    for line in dir_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'第(\d+)章[：:]?\s*(.+?)(?:[─\-—]\s*(.+))?$', line)
        if m:
            chapters.append({"num": int(m.group(1)), "title": m.group(2).strip(),
                             "desc": m.group(3).strip() if m.group(3) else ""})
        else:
            m2 = re.match(r'(\d+)[.、．\s]+(.+)', line)
            if m2:
                rest = m2.group(2).strip()
                parts = re.split(r'[─—\-]', rest, 1)
                chapters.append({"num": int(m2.group(1)),
                                 "title": parts[0].strip(),
                                 "desc": parts[1].strip() if len(parts) > 1 else ""})
    chapters.sort(key=lambda x: x["num"])
    if not chapters:
        chapters = [{"num": i, "title": f"第{i}章", "desc": ""}
                    for i in range(1, expected_count + 1)]
    return chapters

# ═══════════════════════════════════════════════════════════
# VectorContext — 轻量向量检索上下文
# ═══════════════════════════════════════════════════════════

class VectorContext:
    """
    轻量级向量上下文检索。
    使用 sentence-transformers 做 embedding + 余弦相似度检索。
    不需要 Chroma/FAISS，纯 numpy 实现。

    pip install sentence-transformers numpy
    """
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self._numpy = np
            self._model = SentenceTransformer(model_name)
            self._chapters = []  # [{num, title, text, vec}]
        except ImportError:
            self._model = None
            import logging
            logging.getLogger('novel_factory').warning(
                "sentence-transformers not installed, falling back to text summary")

    def add_chapter(self, chapter_num: int, title: str, text: str):
        """添加一章到索引"""
        if not self._model:
            return
        vec = self._model.encode(text[:2000])  # 只编码前 2000 字
        self._chapters.append({
            "num": chapter_num,
            "title": title,
            "text": text[:1000],  # 存储摘要
            "vec": vec
        })

    def search(self, query: str, n: int = 3) -> str:
        """检索最相关的 n 章作为上下文"""
        if not self._model or not self._chapters:
            return ""
        q_vec = self._model.encode(query)
        scores = []
        for ch in self._chapters:
            sim = float(self._numpy.dot(q_vec, ch["vec"]) /
                       (self._numpy.linalg.norm(q_vec) * self._numpy.linalg.norm(ch["vec"])))
            scores.append((sim, ch))
        scores.sort(reverse=True)
        parts = []
        for sim, ch in scores[:n]:
            parts.append(f"第{ch['num']}章《{ch['title']}》：{ch['text']}")
        return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════
# validate_chapter — 字数/禁用词/钩子校验
# ═══════════════════════════════════════════════════════════

def validate_chapter(content: str, chapter_num: int, target_words: int,
                     book_dir: str) -> dict:
    """
    每章生成后自动校验：
    1. 字数：目标 ±30%
    2. 禁用词：检查是否包含 "然而" "不禁" "微微" "似乎" "仿佛" 等
    3. 钩子：最后 300 字是否有悬念/转折
    """
    issues = []

    # 字数检查
    wc = count_words(content)
    min_w = int(target_words * 0.7)
    max_w = int(target_words * 1.3)
    if wc < min_w:
        issues.append(f"字数不足: {wc}/{target_words} (低于 {min_w})")
    elif wc > max_w:
        issues.append(f"字数超标: {wc}/{target_words} (超过 {max_w})")

    # 禁用词检查
    banned = ["然而", "不禁", "微微", "似乎", "仿佛", "许愿", "可能"]
    found_banned = [w for w in banned if w in content]
    if found_banned:
        issues.append(f"包含禁用词: {', '.join(found_banned)}")

    # 钩子检查（最后 300 字）
    if len(content) > 300:
        last_300 = content[-300:]
    else:
        last_300 = content
    hook_kw = ["但", "却", "发现", "真相", "陷阱", "危机",
               "就在这时", "原来", "难道", "到底", "怎么会", "突然"]
    if not any(kw in last_300 for kw in hook_kw):
        issues.append("结尾缺少悬念钩子")

    return {"pass": len(issues) == 0, "issues": issues}


# ═══════════════════════════════════════════════════════════
# _route_model — 双模型路由
# ═══════════════════════════════════════════════════════════

def _route_model(task_type: str, config: dict) -> dict:
    """
    智能模型路由：
    - use_local=true → 全部走本地（含生成/拆书）
    - use_local=false → 全部走云端
    - 云端 API key 为空 → 自动回退到本地
    """
    use_local = config.get("use_local", False)
    has_cloud_key = bool(config.get("llm", {}).get("api_key", ""))

    # 如果配置了本地优先，或云端没 API key
    if use_local or not has_cloud_key:
        return {
            "provider": "ollama",
            "model": config.get("local_llm", {}).get("model_name", "qwen2.5:7b"),
            "api_key": config.get("local_llm", {}).get("api_key", "ollama"),
            "base_url": config.get("local_llm", {}).get("base_url", "http://localhost:11434/v1"),
            "use_local": True,
        }

    # 云端模式
    return {
        "provider": config["llm"]["provider"],
        "model": config["llm"]["model_name"],
        "api_key": config["llm"]["api_key"],
        "base_url": config["llm"]["base_url"],
        "use_local": False,
    }


# ═══════════════════════════════════════════════════════════
# 续写 — 在已有小说后追加章节
# ═══════════════════════════════════════════════════════════
def continue_novel(book_dir: str, additional_chapters: int = 10,
                   log_callback=None, stream_callback=None,
                   stop_flag=None, progress_callback=None) -> dict:
    """
    在已有小说后追加额外章节。
    读取已有的设定/摘要/角色档案，从下一章开始续写。
    """
    from core import load_config, read_file, count_words, write_file

    cfg = load_config()
    topic = cfg["novel"]["topic"]
    target_words = cfg["novel"]["words_per_chapter"]

    # 读取已有状态
    novel_setting = read_file(os.path.join(book_dir, "设定.md"))
    directory_text = read_file(os.path.join(book_dir, "目录.md"))
    summary = read_file(os.path.join(book_dir, "全局摘要.txt"))
    if not summary:
        summary = f"{topic}（已有完成章节）\n"

    # 统计已有章节数
    ch_dir = os.path.join(book_dir, "正文")
    existing = sorted([f for f in os.listdir(ch_dir) if f.endswith('.md')]) if os.path.exists(ch_dir) else []
    num_existing = 0
    for fname in existing:
        m = re.match(r'第(\d+)章', fname)
        if m:
            num_existing = max(num_existing, int(m.group(1)))

    start_chapter = num_existing + 1
    end_chapter = num_existing + additional_chapters

    if log_callback:
        log_callback(f"\n[续写] 从第{start_chapter}章开始，计划 {additional_chapters} 章 (第{start_chapter}-{end_chapter}章)")

    start_time = time.time()
    total_generated = 0
    chapters_done = 0

    # 向量上下文（可选）
    try:
        _vector_ctx = VectorContext()
        # 索引已有章节
        for fname in existing[-5:]:  # 最近5章
            content = read_file(os.path.join(ch_dir, fname))
            m = re.match(r'第(\d+)章_(.+)\.md', fname)
            if m and content:
                _vector_ctx.add_chapter(int(m.group(1)), m.group(2), content[:2000])
    except Exception:
        _vector_ctx = None

    # 续写
    for ch_num in range(start_chapter, start_chapter + additional_chapters):
        if stop_flag and stop_flag.is_set():
            break

        if _vector_ctx and chapters_done > 0:
            retrieved = _vector_ctx.search(f"第{ch_num}章", n=3)
            if retrieved:
                current_summary = f"{summary}\n\n## 相关前文\n{retrieved}"
            else:
                current_summary = summary
        else:
            current_summary = summary

        if log_callback:
            log_callback(f"  [{ch_num-start_chapter+1}/{additional_chapters}] 第{ch_num}章 生成中...")
        if progress_callback:
            progress_callback("chapter_start", {
                "chapter_num": ch_num, "title": f"续写第{ch_num}章",
                "total": additional_chapters})

        # 从目录获取章节标题
        ch_title = f"续写第{ch_num}章"

        prompt = CHAPTER_GENERATION.format(
            chapter_num=ch_num, novel_setting=novel_setting,
            directory=directory_text, summary_text=current_summary,
            chapter_title=ch_title, chapter_desc="续写内容，承接前文",
            target_words=target_words)

        if stream_callback:
            content = llm_invoke(prompt,
                system_msg="你是一位专业的网文作家。请直接输出章节正文，不要额外解释。",
                stream_callback=stream_callback, stop_flag=stop_flag)
        else:
            content = llm_invoke_ada(prompt,
                system_msg="你是一位专业的网文作家。请直接输出章节正文，不要额外解释。")

        if not content or content.startswith("[错误]"):
            if log_callback:
                log_callback(f"  ✗ 第{ch_num}章生成失败")
            continue

        # 去 AI 味
        from deslop import rule_based_deslop
        cleaned, _ = rule_based_deslop(content)

        ch_file = os.path.join(ch_dir, f"第{ch_num:03d}章_{ch_title}.md")
        write_file(ch_file, cleaned)

        wc = count_words(cleaned)
        chapters_done += 1
        total_generated += wc

        if log_callback:
            log_callback(f"  ✓ {wc} 字")
        if progress_callback:
            progress_callback("chapter_done", {
                "chapter_num": ch_num, "title": ch_title,
                "words": wc, "path": ch_file, "elapsed": round(time.time()-start_time,1)})

        # 更新摘要
        new_summary = update_summary(ch_num, ch_title, cleaned, summary, book_dir, log_callback)
        if new_summary:
            summary = new_summary

        # 索引
        if _vector_ctx:
            _vector_ctx.add_chapter(ch_num, ch_title, cleaned)

        # 存断点
        save_checkpoint(book_dir, chapters_done, summary)

    elapsed = time.time() - start_time
    res = {
        "status": "完成" if chapters_done == additional_chapters else "部分完成",
        "book_dir": book_dir, "chapters_added": chapters_done,
        "total_words": total_generated,
        "elapsed_seconds": round(elapsed, 1),
    }

    if log_callback:
        log_callback(f"\n[续写] 完成 {chapters_done}/{additional_chapters} 章 | {total_generated:,} 字 | {elapsed:.0f}s")

    return res


# ═══════════════════════════════════════════════════════════
# 手动分步流程 - 新增5个生成函数
# ═══════════════════════════════════════════════════════════

def generate_outline(topic: str, genre: str, num_chapters: int,
                     words_per_chapter: int, book_dir: str,
                     log_callback=None, extra_requirements: str = "") -> str:
    """Step 1: 生成大纲"""
    from prompts import OUTLINE_GENERATION
    extra = extra_requirements if extra_requirements.strip() else "无特殊要求，按网文最佳实践自由发挥"
    prompt = OUTLINE_GENERATION.format(
        topic=topic, genre=genre, num_chapters=num_chapters,
        words_per_chapter=words_per_chapter, extra_requirements=extra)
    if log_callback:
        log_callback("正在生成大纲...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文作家，擅长规划长篇小说的结构。请严格按照要求的Markdown格式输出。")
    write_file(os.path.join(book_dir, "大纲.md"), result)
    if log_callback:
        log_callback(f"大纲完成 ({count_words(result)} 字)")
    return result


def generate_world_building(outline: str, genre: str, book_dir: str,
                            log_callback=None, extra_requirements: str = "") -> str:
    """Step 2: 生成世界观设定"""
    from prompts import WORLD_BUILDING_PROMPT
    extra = extra_requirements if extra_requirements.strip() else "无特殊要求，按网文最佳实践自由发挥"
    prompt = WORLD_BUILDING_PROMPT.format(outline=outline[:6000], genre=genre, extra_requirements=extra)
    if log_callback:
        log_callback("正在生成世界观设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细具体地输出世界观设定，不要笼统概括。")
    write_file(os.path.join(book_dir, "世界观.md"), result)
    if log_callback:
        log_callback(f"世界观完成 ({count_words(result)} 字)")
    return result


def generate_characters(outline: str, world_setting: str, genre: str,
                        book_dir: str, log_callback=None, extra_requirements: str = "") -> str:
    """Step 3: 生成人物设定"""
    from prompts import CHARACTER_GENERATION
    extra = extra_requirements if extra_requirements.strip() else "无特殊要求，按网文最佳实践自由发挥"
    prompt = CHARACTER_GENERATION.format(
        outline=outline[:4000], world_setting=world_setting[:3000], genre=genre, extra_requirements=extra)
    if log_callback:
        log_callback("正在生成人物设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文人设师。请为每个角色输出详细的具体描述。")
    write_file(os.path.join(book_dir, "人物设定.md"), result)
    if log_callback:
        log_callback(f"人物设定完成 ({count_words(result)} 字)")
    return result


def generate_organizations(outline: str, world_setting: str,
                           characters: str, genre: str, book_dir: str,
                           log_callback=None, extra_requirements: str = "") -> str:
    """Step 4: 生成组织/势力设定"""
    from prompts import ORGANIZATION_GENERATION
    extra = extra_requirements if extra_requirements.strip() else "无特殊要求，按网文最佳实践自由发挥"
    prompt = ORGANIZATION_GENERATION.format(
        outline=outline[:3000], world_setting=world_setting[:2500],
        characters=characters[:2500], genre=genre, extra_requirements=extra)
    if log_callback:
        log_callback("正在生成组织设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细输出组织体系设定。")
    write_file(os.path.join(book_dir, "组织设定.md"), result)
    if log_callback:
        log_callback(f"组织设定完成 ({count_words(result)} 字)")
    return result


def generate_relationships(outline: str, characters: str,
                           organizations: str, genre: str, book_dir: str,
                           log_callback=None, extra_requirements: str = "") -> str:
    """Step 5: 生成人物关系+组织关系"""
    from prompts import RELATIONSHIP_GENERATION
    extra = extra_requirements if extra_requirements.strip() else "无特殊要求，按网文最佳实践自由发挥"
    prompt = RELATIONSHIP_GENERATION.format(
        outline=outline[:3000], characters=characters[:3000],
        organizations=organizations[:2000], genre=genre, extra_requirements=extra)
    if log_callback:
        log_callback("正在生成关系网络...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细输出人物关系和组织关系图。")
    write_file(os.path.join(book_dir, "关系图谱.md"), result)
    if log_callback:
        log_callback(f"关系图谱完成 ({count_words(result)} 字)")
    return result
