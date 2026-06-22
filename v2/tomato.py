# -*- coding: utf-8 -*-
"""tomato.py --- ????????v3 ????

?? ying-ck/fanqienovel-downloader (AGPL-3.0) ????????
- cookie ???novel_web_id ???? + ?????
- charset.json ??????????????
- ??? fallback?/reader/{id} HTML ?? + /api/reader/full JSON
- ?? UA???????????
- ?????? socket.setdefaulttimeout

?? API ????????GUI ?????
"""

import os
import re
import json
import time
import random
import requests
from datetime import datetime
from urllib.parse import urlparse

_HEADRES_LIB = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

_BASE_HEADERS = {
    "Referer": "https://fanqienovel.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charset.json").replace("charset.json", "cookie.json")
_CHARSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charset.json")
_SAMPLE_NOVEL_ID = 7143038691944959011

_CHARSET = None
_COOKIE = None
_SESSION = requests.Session()


def _load_charset():
    global _CHARSET
    if _CHARSET is None:
        try:
            with open(_CHARSET_FILE, "r", encoding="utf-8") as f:
                _CHARSET = json.load(f)
        except Exception:
            _CHARSET = {}
    return _CHARSET


def _random_ua():
    _BASE_HEADERS["User-Agent"] = random.choice(_HEADRES_LIB)


def _get_cookie():
    global _COOKIE
    if _COOKIE is None:
        try:
            if os.path.exists(_COOKIE_FILE):
                with open(_COOKIE_FILE, "r", encoding="utf-8") as f:
                    _COOKIE = json.load(f)
                    return _COOKIE
        except Exception:
            pass
        _COOKIE = _brute_force_cookie()
    return _COOKIE


def _brute_force_cookie():
    import logging
    log = logging.getLogger("novel_factory")
    log.info("cookie: ?????? novel_web_id")
    test_ch_id = _get_sample_chapter_id()
    if not test_ch_id:
        log.warning("cookie: ???????? ID????? cookie")
        return "novel_web_id=7143038691944959011"
    bas = 10 ** 18
    start = random.randint(bas * 6, bas * 8)
    for i in range(start, bas * 9):
        candidate = f"novel_web_id={i}"
        if _test_cookie(candidate, test_ch_id):
            try:
                with open(_COOKIE_FILE, "w", encoding="utf-8") as f:
                    json.dump(candidate, f)
            except Exception:
                pass
            log.info("cookie: ????")
            return candidate
        time.sleep(random.randint(50, 150) / 1000)
    return "novel_web_id=7143038691944959011"


def _get_sample_chapter_id():
    try:
        chs = get_chapter_list(_SAMPLE_NOVEL_ID)
        if chs and len(chs) > 21:
            return chs[21][0]
    except Exception:
        pass
    return None


def _test_cookie(cookie, chapter_id):
    try:
        content = _fetch_content_html(chapter_id, cookie)
        return len(content) > 200
    except Exception:
        return False


def _decode_content(content, mode=0):
    cs = _load_charset()
    table = cs.get(str(mode), {})
    if not table:
        return content
    result = []
    for ch in content:
        if ch in table:
            result.append(table[ch])
        else:
            result.append(ch)
    return "".join(result)


def _fetch_content_html(chapter_id, cookie=None):
    if cookie is None:
        cookie = _get_cookie()
    _random_ua()
    headers = dict(_BASE_HEADERS)
    headers["cookie"] = cookie
    url = f"https://fanqienovel.com/reader/{chapter_id}"
    resp = _SESSION.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    parts = re.findall(r'<div class="muye-reader-content noselect">(.*?)</div>', resp.text, re.S)
    if parts:
        paras = re.findall(r"<p[^>]*>([^<]+)</p>", parts[0])
        return "\n".join(p.strip() for p in paras if p.strip())
    return ""


def _fetch_content_api(chapter_id):
    url = f"https://fanqienovel.com/api/reader/full?itemId={chapter_id}"
    _random_ua()
    headers = dict(_BASE_HEADERS)
    headers["cookie"] = _get_cookie()
    resp = _SESSION.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") == 0:
        return data.get("data", {}).get("chapterData", {}).get("content", "")
    return ""


def extract_book_id(url_or_id):
    s = str(url_or_id).strip()
    if re.match(r"^\d+$", s):
        return s
    patterns = [
        r"fanqienovel\.com/page/(\d+)",
        r"book_id=(\d+)",
        r"/book/(\d+)",
        r"novel/(\d+)",
        r"fanqienovel\.com/reader/(\d+)",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)
    return ""


def _check_host(host, port=443, timeout=3):
    import socket
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def get_book_info(book_id):
    if not _check_host("fanqienovel.com"):
        return {"error": "???? fanqienovel.com???????????"}
    url = f"https://fanqienovel.com/page/{book_id}"
    _random_ua()
    try:
        resp = _SESSION.get(url, headers=_BASE_HEADERS, timeout=(5, 15))
        resp.raise_for_status()
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', resp.text)
        if m:
            data = json.loads(m.group(1))
            book = data.get("props", {}).get("pageProps", {}).get("bookInfo", {})
            if not book:
                book = data.get("props", {}).get("pageProps", {}).get("book", {})
            return {
                "title": book.get("book_name", book.get("name", "")),
                "author": book.get("author", ""),
                "description": book.get("abstract", book.get("description", "")),
                "cover": book.get("thumb_url", book.get("cover", "")),
                "category": book.get("category_name", book.get("category", "")),
                "total_chapters": book.get("total_chapter_num", book.get("chapter_count", 0)),
                "total_words": book.get("word_count", 0),
                "status": "??" if book.get("is_finish") else "???",
            }
        title_m = re.search(r"<h1[^>]*>([^<]+)</h1>", resp.text)
        if title_m:
            return {"title": title_m.group(1).strip(), "author": "", "status": "??"}
        return {"error": "??????????????????"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"??????: {e}"}
    except requests.exceptions.Timeout:
        return {"error": "??????????"}
    except Exception as e:
        return {"error": f"??????: {e}"}


def get_chapter_list(book_id):
    if not _check_host("fanqienovel.com"):
        return []
    url = f"https://fanqienovel.com/page/{book_id}"
    _random_ua()
    try:
        resp = _SESSION.get(url, headers=_BASE_HEADERS, timeout=(5, 15))
        resp.raise_for_status()
        chapters = []
        for m in re.finditer(r'<a[^>]*href="/reader/(\d+)"[^>]*>([^<]+)</a>', resp.text):
            chapters.append((m.group(1), m.group(2).strip(), ""))
        if not chapters:
            for m in re.finditer(r'"item_id":"(\d+)","title":"([^"]+)"', resp.text):
                chapters.append((m.group(1), m.group(2), ""))
        return chapters
    except Exception:
        return []


def get_chapter_content(chapter_id):
    for attempt in range(3):
        try:
            content = _fetch_content_html(chapter_id)
            if content and len(content) > 100:
                try:
                    return _decode_content(content, mode=0)
                except Exception:
                    try:
                        return _decode_content(content, mode=1)
                    except Exception:
                        return content
            content = _fetch_content_api(chapter_id)
            if content and len(content) > 100:
                try:
                    return _decode_content(content, mode=0)
                except Exception:
                    return content
        except Exception:
            if attempt < 2:
                time.sleep(1 + attempt)
    return ""


def search_books(keyword, page=1):
    if not _check_host("fanqienovel.com"):
        return []
    url = f"https://fanqienovel.com/api/author/search/search_book?query={keyword}&page={page}&size=10"
    _random_ua()
    try:
        resp = _SESSION.get(url, headers=_BASE_HEADERS, timeout=(5, 15))
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


def download_book(book_id_or_url, output_dir="", log_callback=None, stop_flag=None):
    from core.utils import ensure_dir, get_book_dir, write_file, count_words

    book_id = extract_book_id(book_id_or_url)
    if not book_id:
        return {"error": "???? book_id???????? URL ????? book_id"}

    if log_callback:
        log_callback(f"book_id: {book_id}")

    if log_callback:
        log_callback("??????...")
    info = get_book_info(book_id)
    if "error" in info:
        return info
    if not info.get("title"):
        return {"error": "??????"}

    title = info["title"]
    if log_callback:
        log_callback(f"??: {title}")
        log_callback(f"??: {info.get('author', '')}")
        log_callback(f"??: {info.get('status', '')} ({info.get('total_chapters', '?')}?)")

    safe_title = re.sub(r"[\\/:*?<>|]", "", title)[:40].strip()
    if not output_dir:
        book_dir = get_book_dir(title)
    else:
        book_dir = os.path.join(output_dir, safe_title)
        ensure_dir(book_dir)
    chapter_dir = os.path.join(book_dir, "??")
    ensure_dir(chapter_dir)

    if log_callback:
        log_callback("??????...")
    chapters = get_chapter_list(book_id)
    if not chapters:
        return {"error": "????????"}

    total = len(chapters)
    if log_callback:
        log_callback(f"? {total} ?")

    if log_callback:
        log_callback("??? cookie...")
    _get_cookie()

    downloaded = 0
    total_words = 0
    failed = []

    for i, (ch_id, ch_title, volume) in enumerate(chapters):
        if stop_flag and stop_flag.is_set():
            if log_callback:
                log_callback(f"??? (??? {downloaded}/{total})")
            break

        ch_num = i + 1
        content = get_chapter_content(ch_id)
        if not content:
            if log_callback:
                log_callback(f"  [{ch_num}/{total}] {ch_title} - ?? (???...)")
            time.sleep(1)
            content = get_chapter_content(ch_id)

        if content:
            content = content.replace("\r\n", "\n").strip()
            fname = f"?{ch_num:03d}? {ch_title}.md"
            ch_text = f"# ?{ch_num}? {ch_title}\n\n{content}\n"
            write_file(os.path.join(chapter_dir, fname), ch_text)
            wc = count_words(content)
            total_words += wc
            downloaded += 1
            if log_callback and (i % 10 == 0 or i == total - 1):
                log_callback(f"  [{ch_num}/{total}] {ch_title} ({wc}?)")
        else:
            failed.append(ch_title)
            if log_callback:
                log_callback(f"  [{ch_num}/{total}] {ch_title} - ??")

        time.sleep(random.randint(50, 150) / 1000)

    meta = {
        "title": title,
        "author": info.get("author", ""),
        "description": info.get("description", ""),
        "category": info.get("category", ""),
        "status": info.get("status", ""),
        "total_chapters": total,
        "downloaded": downloaded,
        "total_words": total_words,
        "platform": "????",
        "book_id": book_id,
        "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_file(os.path.join(book_dir, "?????.json"),
               json.dumps(meta, ensure_ascii=False, indent=2))

    if log_callback:
        log_callback(f"\n????: {downloaded}/{total}? {total_words:,}?")
        if failed:
            log_callback(f"????: {len(failed)}")

    return {
        "title": title,
        "author": info.get("author", ""),
        "book_id": book_id,
        "total_chapters": total,
        "downloaded": downloaded,
        "total_words": total_words,
        "book_dir": book_dir,
        "failed": failed,
    }
