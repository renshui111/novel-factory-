# -*- coding: utf-8 -*-
"""tomato.py --- 番茄小说专用下载器（基于 fanqienovel.com API）"""

import os, re, json, time, requests, socket
from datetime import datetime
from urllib.parse import urlparse

# Force socket timeout to prevent hanging on DNS
socket.setdefaulttimeout(10)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fanqienovel.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def extract_book_id(url_or_id: str) -> str:
    """从URL或直接输入的ID中提取book_id"""
    s = url_or_id.strip()
    # If it's a pure number, return directly
    if re.match(r'^\d+$', s):
        return s
    # Try to extract from URL
    patterns = [
        r'fanqienovel\.com/page/(\d+)',
        r'book_id=(\d+)',
        r'/book/(\d+)',
        r'novel/(\d+)',
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)
    return ""

def _check_host(host, port=443, timeout=3):
    """预检: TCP连接是否可达"""
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def get_book_info(book_id: str) -> dict:
    """获取书籍基本信息 - 从HTML页面解析NEXT_DATA"""
    if not _check_host("fanqienovel.com"):
        return {"error": "无法连接 fanqienovel.com，请检查网络或使用VPN"}
    url = f"https://fanqienovel.com/page/{book_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(5, 10))
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            book = data.get("data", {}).get("book", {})
            return {
                "title": book.get("book_name", ""),
                "author": book.get("author", ""),
                "description": book.get("abstract", ""),
                "cover": book.get("thumb_url", ""),
                "category": book.get("category_name", ""),
                "total_chapters": book.get("total_chapter_num", 0),
                "total_words": book.get("word_count", 0),
                "status": "完结" if book.get("is_finish") else "连载中",
            }
    except requests.exceptions.ConnectionError as e:
        return {"error": f"网络连接失败: {e}"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时，请检查网络"}
    except Exception as e:
        return {"error": f"获取信息失败: {e}"}
    return {}

def get_chapter_list(book_id: str) -> list:
    """获取所有章节列表 [(chapter_id, title, volume_name), ...]"""
    url = f"https://fanqienovel.com/api/reader/directory/detail?bookId={book_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(5, 10))
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            chapters = []
            for item in data.get("data", []):
                chapter_id = item.get("item_id", "")
                title = item.get("title", "")
                volume = item.get("volume_name", "")
                if chapter_id and title:
                    chapters.append((chapter_id, title, volume))
            return chapters
    except Exception:
        pass
    return []

def get_chapter_content(chapter_id: str) -> str:
    """获取章节正文"""
    url = f"https://novel.snssdk.com/api/novel/book/reader/full/v1/?item_id={chapter_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(5, 10))
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("content", "")
    except Exception:
        pass
    return ""

def search_books(keyword: str, page: int = 1) -> list:
    """搜索书籍"""
    url = f"https://fanqienovel.com/api/author/search/search_book?query={keyword}&page={page}&size=10"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(5, 10))
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            results = []
            for item in data.get("data", {}).get("book_list", []):
                results.append({
                    "book_id": item.get("book_id", ""),
                    "title": item.get("book_name", ""),
                    "author": item.get("author", ""),
                    "description": item.get("abstract", ""),
                    "category": item.get("category_name", ""),
                })
            return results
    except Exception:
        pass
    return []

def download_book(book_id_or_url: str, output_dir: str = "",
                  log_callback=None, stop_flag=None) -> dict:
    """下载整本番茄小说，返回结果字典"""
    from core.utils import ensure_dir, get_book_dir, write_file, count_words

    book_id = extract_book_id(book_id_or_url)
    if not book_id:
        return {"error": "无法识别book_id，请粘贴番茄小说URL或直接输入book_id"}

    if log_callback:
        log_callback(f"book_id: {book_id}")

    # Get book info
    if log_callback:
        log_callback("获取书籍信息...")
    info = get_book_info(book_id)
    if not info:
        return {"error": "获取书籍信息失败，请检查book_id是否正确"}

    title = info["title"]
    if not title:
        return {"error": "获取书名失败"}

    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:40].strip()
    if log_callback:
        log_callback(f"书名: {title}")
        log_callback(f"作者: {info['author']}")
        log_callback(f"状态: {info['status']} ({info.get('total_chapters', '?')}章)")

    # Create book directory
    if not output_dir:
        book_dir = get_book_dir(title)
    else:
        book_dir = os.path.join(output_dir, safe_title)
        ensure_dir(book_dir)
    chapter_dir = os.path.join(book_dir, "正文")
    ensure_dir(chapter_dir)

    # Get chapter list
    if log_callback:
        log_callback("获取章节列表...")
    chapters = get_chapter_list(book_id)
    if not chapters:
        return {"error": "获取章节列表失败"}

    total = len(chapters)
    if log_callback:
        log_callback(f"共 {total} 章")

    # Download chapters
    downloaded = 0
    total_words = 0
    failed = []

    for i, (ch_id, ch_title, volume) in enumerate(chapters):
        if stop_flag and stop_flag.is_set():
            if log_callback:
                log_callback(f"已停止 (已完成 {downloaded}/{total})")
            break

        ch_num = i + 1
        content = get_chapter_content(ch_id)
        if not content:
            failed.append(ch_title)
            if log_callback:
                log_callback(f"  [{ch_num}/{total}] {ch_title} - 失败 (重试中...)")
            # Retry once
            time.sleep(1)
            content = get_chapter_content(ch_id)

        if content:
            # Clean content
            content = content.replace("\r\n", "\n").strip()
            # Write chapter
            fname = f"第{ch_num}章 {ch_title}.md"
            ch_text = f"# 第{ch_num}章 {ch_title}\n\n{content}\n"
            write_file(os.path.join(chapter_dir, fname), ch_text)
            wc = count_words(content)
            total_words += wc
            downloaded += 1
            if log_callback and (i % 10 == 0 or i == total - 1):
                log_callback(f"  [{ch_num}/{total}] {ch_title} ({wc}字)")
        else:
            failed.append(ch_title)
            if log_callback:
                log_callback(f"  [{ch_num}/{total}] {ch_title} - 失败")

        # Rate limiting
        time.sleep(0.3)

    # Save metadata
    meta = {
        "title": title,
        "author": info["author"],
        "description": info["description"],
        "category": info["category"],
        "status": info["status"],
        "total_chapters": total,
        "downloaded": downloaded,
        "total_words": total_words,
        "platform": "番茄小说",
        "book_id": book_id,
        "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_file(os.path.join(book_dir, "项目元数据.json"),
               json.dumps(meta, ensure_ascii=False, indent=2))

    if log_callback:
        log_callback(f"\n下载完成: {downloaded}/{total}章, {total_words:,}字")
        if failed:
            log_callback(f"失败章节: {len(failed)}")

    return {
        "title": title,
        "author": info["author"],
        "book_id": book_id,
        "total_chapters": total,
        "downloaded": downloaded,
        "total_words": total_words,
        "book_dir": book_dir,
        "failed": failed,
    }