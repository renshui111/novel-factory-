# batch.py — 批量生产模块
# 支持 CSV 配置驱动并行生成多本小说

import os
import csv
import json
import time
import threading
from core import load_config, save_config, get_output_dir, ensure_dir
from novel import generate_novel


def run_batch(batch_file: str = "",
              log_callback=None,
              stop_flag=None) -> list:
    """
    批量生成多本小说。
    
    Args:
        batch_file: CSV 配置文件路径
        log_callback: 日志回调
        stop_flag: threading.Event，停止标志
    
    Returns:
        list: 每本书的生成结果
    """
    tasks = _load_batch_config(batch_file)
    if not tasks:
        if log_callback:
            log_callback("未找到批量任务配置")
        return []

    if log_callback:
        log_callback(f"📋 批量任务: {len(tasks)} 本小说\n")

    results = []
    for i, task in enumerate(tasks, 1):
        if stop_flag and stop_flag.is_set():
            break

        if log_callback:
            log_callback(f"\n{'='*60}")
            log_callback(f" [{i}/{len(tasks)}] {task.get('topic', '未命名')}")
            log_callback(f"{'='*60}")

        # 临时覆盖配置
        result = generate_novel(
            config={"novel": task},
            log_callback=log_callback,
            stop_flag=stop_flag
        )

        result["batch_index"] = i
        results.append(result)

    # 生成批量报告
    _write_batch_report(results, log_callback)

    return results


def _load_batch_config(batch_file: str) -> list:
    """加载批量配置"""
    tasks = []

    if not batch_file:
        # 使用默认路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        batch_file = os.path.join(base_dir, "batch.csv")

    if not os.path.exists(batch_file):
        # 创建示例配置
        _create_sample_batch(batch_file)
        return []

    try:
        with open(batch_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items() if k}
                if row.get("topic"):
                    task = {
                        "topic": row["topic"],
                        "genre": row.get("genre", "玄幻"),
                        "num_chapters": int(row.get("num_chapters", 30)),
                        "words_per_chapter": int(row.get("words_per_chapter", 3000))
                    }
                    tasks.append(task)
    except Exception as e:
        print(f"[batch] 读取配置失败: {e}")

    return tasks


def _create_sample_batch(path: str):
    """创建示例 CSV 批量配置"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["topic", "genre", "num_chapters", "words_per_chapter"])
        writer.writerow(["剑道独尊：重生剑神", "玄幻", 30, 3000])
        writer.writerow(["星际领主：开局一座空间站", "科幻", 20, 4000])
        writer.writerow(["我的修仙模拟器", "仙侠", 40, 2500])
        writer.writerow(["末世：我的仓库能刷新", "末世", 25, 3500])
    print(f"[batch] 已创建示例配置: {path}")


def _write_batch_report(results: list, log_callback=None):
    """生成批量报告"""
    report_dir = os.path.join(get_output_dir(), "_batch_report")
    ensure_dir(report_dir)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # CSV 报告
    csv_path = os.path.join(report_dir, f"batch_{timestamp}.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "主题", "类型", "计划章节", "完成章节",
                         "总字数", "用时(秒)", "状态", "输出目录"])
        for r in results:
            writer.writerow([
                r.get("batch_index", ""),
                r.get("topic", ""),
                r.get("genre", ""),
                r.get("chapters_planned", 0),
                r.get("chapters_done", 0),
                r.get("total_words", 0),
                r.get("elapsed_seconds", 0),
                r.get("status", ""),
                r.get("book_dir", "")
            ])

    # Markdown 报告
    md_lines = [f"# 批量生成报告 ({timestamp})\n"]
    md_lines.append(f"| # | 主题 | 章节 | 字数 | 用时 | 状态 |")
    md_lines.append(f"|---|------|------|------|------|------|")
    for r in results:
        md_lines.append(
            f"| {r.get('batch_index', '')} "
            f"| {r.get('topic', '')} "
            f"| {r.get('chapters_done', 0)}/{r.get('chapters_planned', 0)} "
            f"| {r.get('total_words', 0):,} "
            f"| {r.get('elapsed_seconds', 0):.0f}s "
            f"| {r.get('status', '')} |"
        )

    total_words = sum(r.get("total_words", 0) for r in results)
    total_time = sum(r.get("elapsed_seconds", 0) for r in results)
    md_lines.append(f"\n**总计**: {len(results)} 本, {total_words:,} 字, {total_time:.0f} 秒")

    md_path = os.path.join(report_dir, f"batch_{timestamp}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    if log_callback:
        log_callback(f"\n📊 批量报告已保存: {csv_path}")
        log_callback(f"  Markdown: {md_path}")