# planner.py — 卷规划 + 节奏表
# 为小说生成提供卷级结构规划和每章节奏分配

import os
import json
from core import write_file, read_file, ensure_dir, count_words


def plan_volumes(novel_setting: str, num_chapters: int,
                 book_dir: str, log_callback=None) -> list:
    """
    卷规划：根据小说设定和总章节数，将全书拆分为3卷。
    使用 LLM 生成每卷的名称、字数目标和核心剧情概要。

    Returns:
        list: [{"name": str, "chapters": (start, end), "summary": str, "target_words": int}, ...]
    """
    from core import llm_invoke_ada

    v1_end = max(1, num_chapters // 3)
    v2_end = max(v1_end + 1, num_chapters * 2 // 3)

    prompt = f"""你是一位专业的网文作家。请根据以下小说设定，为一部{num_chapters}章的小说进行卷规划。

小说设定：
{novel_setting[:3000]}

总章节数：{num_chapters}章

请将{num_chapters}章拆分为3卷，输出格式如下（不要多余内容）：

第一卷（第1-{v1_end}章）：卷名 | 核心剧情概要（50字内） | 字数目标
第二卷（第{v1_end+1}-{v2_end}章）：卷名 | 核心剧情概要（50字内） | 字数目标
第三卷（第{v2_end+1}-{num_chapters}章）：卷名 | 核心剧情概要（50字内） | 字数目标

要求：
1. 第一卷：铺垫+建立世界观，结尾有一个小高潮
2. 第二卷：深度展开+核心冲突升级，结尾大高潮
3. 第三卷：最终冲突+收束主线，完美收官
"""
    if log_callback:
        log_callback("  [规划] 卷规划生成中...")

    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文作家。请严格按照格式输出卷规划。")

    lanes = result.strip().split('\n')
    volumes = []
    chapters_per_volume = num_chapters // 3

    for i, line in enumerate(lanes):
        line = line.strip()
        if not line or '卷' not in line:
            continue
        parts = line.split('：', 1)
        if len(parts) < 2:
            continue

        # Extract volume range from first part (e.g., "第一卷（第1-10章）")
        import re
        vol_range = re.findall(r'(\d+)-(\d+)', parts[0])
        if vol_range:
            start_ch = int(vol_range[0][0])
            end_ch = int(vol_range[0][1])
        else:
            start_ch = i * chapters_per_volume + 1
            end_ch = (i + 1) * chapters_per_volume
            if i == 2:
                end_ch = num_chapters

        # Extract name and summary
        detail = parts[1]
        sub_parts = detail.split('|')
        name = sub_parts[0].strip() if sub_parts else f"第{i+1}卷"
        summary = sub_parts[1].strip() if len(sub_parts) > 1 else ""
        target = int(sub_parts[2].strip()) if len(sub_parts) > 2 and sub_parts[2].strip().isdigit() else 0

        volumes.append({
            "name": name,
            "chapters": (start_ch, end_ch),
            "summary": summary,
            "target_words": target,
            "num_chapters": end_ch - start_ch + 1
        })

    # Fallback if parsing fails
    if not volumes:
        chapters_per_vol = num_chapters // 3
        v1 = max(1, chapters_per_vol)
        v2 = max(v1 + 1, chapters_per_vol * 2)
        volumes = [
            {"name": "第一卷：开局", "chapters": (1, v1), "summary": "铺垫+建立世界观",
             "target_words": 0, "num_chapters": v1},
            {"name": "第二卷：展开", "chapters": (v1 + 1, v2), "summary": "冲突升级",
             "target_words": 0, "num_chapters": v2 - v1},
            {"name": "第三卷：收官", "chapters": (v2 + 1, num_chapters), "summary": "收束主线",
             "target_words": 0, "num_chapters": num_chapters - v2},
        ]

    # 写入卷规划.md
    md_lines = ["# 卷规划\n"]
    for v in volumes:
        md_lines.append(f"## {v['name']}")
        md_lines.append(f"- 章节：{v['chapters'][0]}-{v['chapters'][1]}")
        md_lines.append(f"- 概要：{v['summary']}")
        md_lines.append(f"- 章节数：{v['num_chapters']}")
        if v['target_words']:
            md_lines.append(f"- 字数目标：{v['target_words']:,}")
        md_lines.append("")

    write_file(os.path.join(book_dir, "卷规划.md"), "\n".join(md_lines))

    if log_callback:
        log_callback(f"  [规划] 卷规划完成: {len(volumes)} 卷")

    return volumes


def build_rhythm_table(volumes: list, num_chapters: int,
                       book_dir: str, log_callback=None) -> list:
    """
    节奏表：为每章分配节奏类型，指导写作节奏。

    Returns:
        list: [{"chapter": int, "rhythm": str, "responsibility": str}, ...]
    """
    import re

    rhythm_table = []

    for vol in volumes:
        start, end = vol["chapters"]
        vol_chapters = list(range(start, end + 1))
        total_in_vol = len(vol_chapters)

        for i, ch_num in enumerate(vol_chapters):
            # 节奏分配策略
            progress = i / max(total_in_vol - 1, 1)  # 0.0 ~ 1.0

            if i == 0:
                # 卷首章
                if vol == volumes[0]:
                    rhythm = "快"
                    resp = "开篇即高潮，抓人眼球"
                else:
                    rhythm = "中快"
                    resp = "承接上卷悬念，快速进入新阶段"
            elif i == total_in_vol - 1:
                # 卷末章
                if vol == volumes[-1]:
                    rhythm = "快"
                    resp = "大结局，收束所有伏笔"
                else:
                    rhythm = "快"
                    resp = "卷末大高潮，制造强力悬念"
            elif progress < 0.3:
                # 卷前半段：推进
                if vol == volumes[0]:
                    rhythm = "中快"
                    resp = "铺设设定+制造冲突"
                else:
                    rhythm = "中"
                    resp = "推进剧情+展示升级"
            elif progress < 0.7:
                # 卷中段：深度展开
                rhythm = "中"
                resp = "深化冲突+角色成长+埋设伏笔"
            else:
                # 卷后段：准备高潮
                rhythm = "中快"
                resp = "冲突升温+铺垫卷末高潮"

            rhythm_table.append({
                "chapter": ch_num,
                "rhythm": rhythm,
                "responsibility": resp
            })

    # 写入节奏表.md
    md_lines = ["# 节奏表\n"]
    md_lines.append("| 章节 | 节奏 | 职责 |")
    md_lines.append("|------|------|------|")
    for rt in rhythm_table:
        md_lines.append(f"| 第{rt['chapter']}章 | {rt['rhythm']} | {rt['responsibility']} |")

    write_file(os.path.join(book_dir, "节奏表.md"), "\n".join(md_lines))

    if log_callback:
        log_callback(f"  [规划] 节奏表生成完成: {len(rhythm_table)} 章")

    return rhythm_table