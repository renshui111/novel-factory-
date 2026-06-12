# analyze.py ? ????
# ?????? .txt ? ?????????

import os
import re
import json
import time

from core import llm_invoke_ada, read_file, write_file, ensure_dir, count_words, get_output_dir
from prompts import (
    ANALYZE_SETTING, ANALYZE_CHARACTERS,
    ANALYZE_PLOT, ANALYZE_STYLE
)

def split_into_chapters(text):
    pattern = r"(第[一二三四五六七八九十百千0-9]+章[^\n]*)"
    splits = re.split(pattern, text)
    if len(splits) > 5:
        chapters = []
        for i in range(1, len(splits), 2):
            title = splits[i].strip()
            body = splits[i+1] if i+1 < len(splits) else ""
            chapters.append({"title": title, "content": body})
        return chapters
    chunk_size = 8000
    chapters = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        chapters.append({"title": f"段落 {i//chunk_size + 1}", "content": chunk})
    return chapters



def analyze_novel(novel_path: str, output_dir: str = "",
                  log_callback=None) -> dict:
    """
    ????????????????????
    
    Args:
        novel_path: ?????? (.txt)
        output_dir: ??????? output/??/{??}/?
        log_callback: ??????
    
    Returns:
        dict: ??????
    """
    # ????
    novel_text = read_file(novel_path)
    if not novel_text:
        return {"error": "?????????"}

    book_name = os.path.splitext(os.path.basename(novel_path))[0]
    total_words = count_words(novel_text)

    if log_callback:
        log_callback(f"?? {book_name} | {total_words} ?")
        log_callback(f"????...")

    # ??????
    if not output_dir:
        output_dir = os.path.join(get_output_dir(), "??", book_name)
    ensure_dir(output_dir)

    results = {}

    # ?????????????????
    if total_words > 50000:
        # ?? 5000 + ????
        sampled = _sample_novel_text(novel_text, total_words)
    else:
        sampled = novel_text[:50000]

    # ??? 1. ???? ???????????????????
    if log_callback:
        log_callback("[1/4] ??????...")

    settings = llm_invoke_ada(
        ANALYZE_SETTING.format(novel_text=sampled),
        system_msg="????????????????????????????????"
    )
    write_file(os.path.join(output_dir, "????.md"), settings)
    results["setting"] = "??"
    if log_callback:
        log_callback("  ? ??????")

    # ??? 2. ???? ???????????????????
    if log_callback:
        log_callback("[2/4] ??????...")

    characters = llm_invoke_ada(
        ANALYZE_CHARACTERS.format(novel_text=sampled),
        system_msg="????????????????????????????????"
    )
    write_file(os.path.join(output_dir, "????.md"), characters)
    results["characters"] = "??"
    if log_callback:
        log_callback("  ? ??????")

    # ??? 3. ???? ???????????????????
    if log_callback:
        log_callback("[3/4] ??????...")

    plot = llm_invoke_ada(
        ANALYZE_PLOT.format(novel_text=sampled),
        system_msg="????????????????????????????????"
    )
    write_file(os.path.join(output_dir, "????.md"), plot)
    results["plot"] = "??"
    if log_callback:
        log_callback("  ? ??????")

    # ??? 4. ???? ???????????????????
    if log_callback:
        log_callback("[4/4] ??????...")

    style = llm_invoke_ada(
        ANALYZE_STYLE.format(novel_text=sampled),
        system_msg="????????????????????????????????"
    )
    write_file(os.path.join(output_dir, "????.md"), style)
    results["style"] = "??"
    if log_callback:
        log_callback("  ? ??????")

    # ??? ?????? ?????????????????
    summary = f"""# {book_name} ? ????

## ????
- ????{os.path.basename(novel_path)}
- ????{total_words:,}
- ?????{time.strftime('%Y-%m-%d %H:%M:%S')}

## ????
"""
    for k, v in results.items():
        summary += f"- {k}: {v}\n"

    write_file(os.path.join(output_dir, "????.md"), summary)
    results["output_dir"] = output_dir

    if log_callback:
        log_callback(f"\n? ????????????\n  {output_dir}")

    return results


def _sample_novel_text(text: str, total_len: int) -> str:
    """??????????????????????"""
    part_len = min(total_len // 3, 8000)

    start = text[:part_len]

    mid_start = total_len // 2 - part_len // 2
    mid = text[mid_start:mid_start + part_len]

    end = text[-part_len:]

    return f"[????]\n{start}\n\n[????]\n{mid}\n\n[????]\n{end}"


def batch_analyze(directory: str, log_callback=None) -> list:
    """
    ??????????????? .txt ??
    
    Args:
        directory: ???????
        log_callback: ????
    
    Returns:
        list: ?????????
    """
    results = []
    txt_files = [f for f in os.listdir(directory)
                 if f.lower().endswith('.txt')
                 and os.path.isfile(os.path.join(directory, f))]

    if log_callback:
        log_callback(f"?? {len(txt_files)} ??????????...\n")

    for i, fname in enumerate(txt_files, 1):
        path = os.path.join(directory, fname)
        if log_callback:
            log_callback(f"\n[{i}/{len(txt_files)}] {fname}")
        result = analyze_novel(path, log_callback=log_callback)
        results.append({"file": fname, "result": result})

    if log_callback:
        log_callback(f"\n? ?????????? {len(txt_files)} ???")

    return results


def analyze_chapters_detail(chapters, book_dir, log_callback=None):
    results = []
    for i, ch in enumerate(chapters):
        t = ch.get("title", "")
        if log_callback:
            log_callback(f"[详情] {t}")
        ch_text = ch.get("content", "")[:3000]
        prompt = "请分析以下章节，输出JSON：" + "\n\n章节：" + ch_text + "\n\n输出JSON: {title, word_count, summary, conflict, characters:[], emotion, hook}"
        result = llm_invoke_ada(prompt)
        try:
            import json
            results.append(json.loads(result))
        except:
            results.append({"title": t})
    import json
    write_file(os.path.join(book_dir, "章节索引.json"), json.dumps(results, ensure_ascii=False, indent=2))
    return results


def extract_style_fingerprint(text, book_dir, log_callback=None):
    prompt = "请分析写作风格，输出JSON：" + "\n\n文本：" + text[:5000] + "\n\n输出: {sentence_pattern, dialogue_ratio, paragraph_length, common_phrases:[], description_style, emotion_expression}"
    result = llm_invoke_ada(prompt)
    try:
        import json
        fp = json.loads(result)
        write_file(os.path.join(book_dir, "风格指纹.json"), json.dumps(fp, ensure_ascii=False, indent=2))
        return fp
    except:
        return {}

