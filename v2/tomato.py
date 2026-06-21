# -*- coding: utf-8 -*-
"""tomato.py — 番茄小说下载器

Cookie auto-acquire + charset decode + dual endpoint fallback.
No socket.setdefaulttimeout global side effect.
"""
import os, re, json, time, random, logging, requests
from datetime import datetime
logger = logging.getLogger("novel_factory")

# Session + UA
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/121 Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/120 Safari/537.36",
]
_http = requests.Session()
_http.headers.update({"Referer":"https://fanqienovel.com/","Accept":"application/json, text/plain, */*","Accept-Language":"zh-CN,zh;q=0.9"})

COOKIE_FILE = "cookie.json"
CHARSET_FILE = "charset.json"
SAMPLE_ID = 7143038691944959011
_HERE = os.path.dirname(os.path.abspath(__file__))

def _random_ua():
    _http.headers["User-Agent"] = random.choice(USER_AGENTS)
def _random_delay(lo=50, hi=150):
    time.sleep(random.randint(lo, hi) / 1000)

# Charset
def _load_charset():
    for p in [os.path.join(_HERE, CHARSET_FILE), CHARSET_FILE]:
        if os.path.exists(p):
            with open(p,"r",encoding="utf-8") as f:
                return json.load(f)
    return {}

def _decode_content(raw, mode=0):
    cs = _load_charset()
    if not cs: return raw
    codes = cs[1] if mode == 1 else cs[0]
    return re.sub(r"([-])", lambda m: codes.get(m.group(1),m.group(0)), raw)

# Cookie
def _get_cookie_path():
    return os.path.join(_HERE, COOKIE_FILE)

def _load_cookie():
    cp = _get_cookie_path()
    if os.path.exists(cp):
        try:
            with open(cp,"r",encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return ""

def _save_cookie(cookie):
    try:
        with open(_get_cookie_path(),"w",encoding="utf-8") as f:
            json.dump(cookie, f)
    except Exception: pass

# HTML patterns - pre-compiled regex
_RE_CHAP = re.compile(r"""<a[^>]*href="[^"]*/reader/(d+)[^"]*"[^>]*>([^<]+)</a>""")
_RE_H1 = re.compile(r"<h1[^>]*>([^<]+)</h1>")
_RE_ST = re.compile(r"""<span[^>]*class="[^"]*info-label[^"]*"[^>]*>([^<]+)</span>""")
_RE_DIV = re.compile(r"""<div[^>]*class="[^"]*muye-reader-content[^"]*"[^>]*>(.*?)</div>""", re.DOTALL)
_RE_P = re.compile(r"<p[^>]*>([^<]*)</p>")

def _get_chapter_list_html(novel_id):
    url = f"https://fanqienovel.com/page/{novel_id}"
    _random_ua()
    resp = _http.get(url, timeout=15)
    resp.raise_for_status()
    text = resp.text
    chapters = {}
    for m in _RE_CHAP.finditer(text):
        cid, ct = m.group(1), m.group(2).strip()
        if ct: chapters[ct] = cid
    tm = _RE_H1.search(text)
    title = tm.group(1).strip() if tm else ""
    sm = _RE_ST.search(text)
    status = [sm.group(1).strip()] if sm else ["未知"]
    return title, chapters, status

def _fetch_content_html(chapter_id):
    url = f"https://fanqienovel.com/reader/{chapter_id}"
    _random_ua()
    ck = _load_cookie()
    kw = {"timeout": 15}
    if ck: kw["cookies"] = {"novel_web_id": ck}
    resp = _http.get(url, **kw)
    resp.raise_for_status()
    parts = _RE_DIV.findall(resp.text)
    if parts:
        paras = _RE_P.findall(parts[0])
        return "
".join(p.strip() for p in paras if p.strip())
    return ""

def _fetch_content_api(chapter_id):
    url = f"https://fanqienovel.com/api/reader/full?itemId={chapter_id}"
    _random_ua()
    hdrs = {}
    ck = _load_cookie()
    if ck: hdrs["Cookie"] = f"novel_web_id={ck}"
    resp = _http.get(url, headers=hdrs, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data",{}).get("chapterData",{}).get("content","")

def _test_cookie(cookie, test_id=None):
    if not test_id:
        _, chs, _ = _get_chapter_list_html(SAMPLE_ID)
        if not chs: return False
        test_id = list(chs.values())[-1]
    url = f"https://fanqienovel.com/api/reader/full?itemId={test_id}"
    _random_ua()
    try:
        resp = _http.get(url, headers={"Cookie":f"novel_web_id={cookie}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return len(data.get("data",{}).get("chapterData",{}).get("content","")) > 200
    except Exception: pass
    return False

def _init_cookie(log_cb=None):
    cookie = _load_cookie()
    if cookie:
        if log_cb: log_cb("检测已缓存 cookie，验证中...")
        _, chs, _ = _get_chapter_list_html(SAMPLE_ID)
        if chs and _test_cookie(cookie, list(chs.values())[-1]):
            if log_cb: log_cb("Cookie 有效")
            return cookie
    if log_cb: log_cb("正在获取新 cookie...")
    return _brute_cookie(log_cb)

def _brute_cookie(log_cb=None):
    _, chs, _ = _get_chapter_list_html(SAMPLE_ID)
    if not chs:
        if log_cb: log_cb("无法获取章节，无 cookie 模式")
        return ""
    test_id = list(chs.values())[-1]
    bas = 10 ** 18
    lo = random.randint(bas * 6, bas * 8)
    hi = bas * 9
    cnt = 0
    for i in range(lo, hi):
        _random_delay(50, 150)
        c = str(i)
        if _test_cookie(c, test_id):
            _save_cookie(c)
            if log_cb: log_cb(f"Cookie 获取成功 ({cnt}次)")
            return c
        cnt += 1
        if log_cb and cnt % 200 == 0:
            log_cb(f"  仍在尝试... ({cnt})")
    if log_cb: log_cb("未找到有效 cookie")
    return ""

# Public API
def extract_book_id(url_or_id):
    s = url_or_id.strip()
    if re.match(r"^d{15,25}$", s): return s
    for p in [r"fanqienovel.com/page/(d+)", r"/reader/(d+)", r"book_id=(d+)"]:
        m = re.search(p, s)
        if m: return m.group(1)
    return ""

def get_book_info(book_id):
    _random_ua()
    try:
        title, chs, status = _get_chapter_list_html(book_id)
        if not title: return {"error":"无法获取书籍信息"}
        return {"title":title,"author":"","description":"","cover":"","category":"","total_chapters":len(chs),"status":"完结" if status and "完结" in str(status) else "连载中"}
    except Exception as e: return {"error":str(e)}

def get_chapter_list(book_id):
    try:
        _, chs, _ = _get_chapter_list_html(book_id)
        return [(cid, title, "") for title, cid in chs.items()]
    except Exception: return []

def get_chapter_content(chapter_id):
    ck = _load_cookie()
    for att in range(3):
        try:
            url = f"https://fanqienovel.com/api/reader/full?itemId={chapter_id}"
            _random_ua(); hdrs = {}
            if ck: hdrs["Cookie"] = f"novel_web_id={ck}"
            resp = _http.get(url, headers=hdrs, timeout=15)
            if resp.status_code == 403 and att < 2:
                ck = _init_cookie(); continue
            resp.raise_for_status()
            raw = resp.json().get("data",{}).get("chapterData",{}).get("content","")
            if not raw: raise ValueError("empty")
            dec = _decode_content(raw)
            if dec and len(dec) > 10: return dec
        except Exception: pass
        try:
            html = _fetch_content_html(chapter_id)
            if html and len(html) > 10: return html
        except Exception: pass
        time.sleep(1)
    return ""

def search_books(keyword, page=1):
    url = f"https://fanqienovel.com/api/author/search/search_book?query={keyword}&page={page}&size=10"
    try:
        _random_ua()
        resp = _http.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return [{"book_id":str(item.get("book_id","")),"title":item.get("book_name",""),"author":item.get("author",""),"description":item.get("abstract",""),"category":item.get("category_name","")} for item in data.get("data",{}).get("book_list",[])]
    except Exception: pass
    return []

def download_book(book_id_or_url, output_dir="", log_callback=None, stop_flag=None):
    from core.utils import ensure_dir, get_book_dir, write_file, count_words
    book_id = extract_book_id(book_id_or_url)
    if not book_id: return {"error":"无法识别 book_id"}
    if log_callback: log_callback(f"book_id: {book_id}")
    _init_cookie(log_callback)
    if log_callback: log_callback("获取书籍信息...")
    title, chs, status = _get_chapter_list_html(book_id)
    if not title: return {"error":"获取书名失败"}
    if log_callback:
        log_callback(f"书名: {title}")
        log_callback(f"共 {len(chs)} 章")
    safe = re.sub(r"[\\/:*?"<>|]","",title)[:40].strip()
    book_dir = get_book_dir(title) if not output_dir else os.path.join(output_dir, safe)
    if output_dir: ensure_dir(book_dir)
    ch_dir = os.path.join(book_dir, "正文")
    ensure_dir(ch_dir)
    done = 0; total_w = 0; failed = []; total = len(chs)
    items = list(chs.items())
    for i, (ctitle, cid) in enumerate(items):
        if stop_flag and stop_flag.is_set():
            if log_callback: log_callback(f"已停止 ({done}/{total})")
            break
        cn = i + 1
        content = get_chapter_content(cid)
        if not content:
            time.sleep(2); content = get_chapter_content(cid)
            if not content:
                failed.append(ctitle)
                if log_callback: log_callback(f"  [{cn}/{total}] {ctitle} - 失败")
                continue
        content = content.replace("","").strip()
        fname = f"第{cn}章_{ctitle}.md"
        write_file(os.path.join(ch_dir, fname), f"# 第{cn}章  {ctitle}

{content}
")
        wc = count_words(content); total_w += wc; done += 1
        if log_callback and (i % 10 == 0 or i == total - 1):
            log_callback(f"  [{cn}/{total}] {ctitle} ({wc}字)")
        _random_delay(50, 200)
    meta = {"title":title,"book_id":book_id,"total_chapters":total,"downloaded":done,"total_words":total_w,"platform":"番茄小说","download_date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    write_file(os.path.join(book_dir,"项目元数据.json"), json.dumps(meta, ensure_ascii=False, indent=2))
    if log_callback:
        log_callback(f"
下载完成: {done}/{total}章  {total_w:,}字")
        if failed: log_callback(f"失败: {len(failed)}章")
    return {"title":title,"book_id":book_id,"total_chapters":total,"downloaded":done,"total_words":total_w,"book_dir":book_dir,"failed":failed}