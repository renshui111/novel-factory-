# -*- coding: utf-8 -*-
"""tomato.py --- 番茄小说下载（基于 shing-yu/fanqie-novel-download）"""
import os, re, json, time, random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from shingyu.public import get_fanqie, proxies
from shingyu.fanqie_chapter import fanqie_c as get_api

_HERE = os.path.dirname(os.path.abspath(__file__))
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

def extract_book_id(s):
    s = str(s).strip()
    if re.match(r"^\d{15,25}$", s): return s
    for p in [r"fanqienovel\.com/page/(\d+)", r"/reader/(\d+)"]:
        m = re.search(p, s)
        if m: return m.group(1)
    return ""

def get_book_info(book_id):
    try:
        _, title, _, chapters = get_fanqie(f"https://fanqienovel.com/page/{book_id}", _UA)
        return {"title": title, "total_chapters": len(chapters)}
    except Exception as e: return {"error": str(e)}

def get_chapter_list(book_id):
    try:
        _, _, _, chs = get_fanqie(f"https://fanqienovel.com/page/{book_id}", _UA)
        r = []
        for ch in chs:
            a = ch.find("a")
            if a:
                m = re.search(r"/reader/(\d+)", a.get("href",""))
                t = a.get_text(strip=True)
                if m and t: r.append((m.group(1), t, ""))
        return r
    except Exception: return []

def get_chapter_content(chapter_id):
    try:
        _, _, c = get_api(chapter_id, _UA, "txt")
        return c or ""
    except Exception: return ""

def search_books(keyword, page=1):
    u = f"https://fanqienovel.com/api/author/search/search_book?query={keyword}&page={page}&size=10"
    try:
        r = requests.get(u, headers={"User-Agent":_UA}, timeout=10, proxies=proxies)
        d = r.json()
        if d.get("code")==0:
            return [{"book_id":str(i.get("book_id","")),"title":i.get("book_name",""),
                     "author":i.get("author",""),"description":i.get("abstract",""),
                     "category":i.get("category_name","")}
                    for i in d.get("data",{}).get("book_list",[])]
    except Exception: pass
    return []

def download_book(book_id_or_url, output_dir="", log_callback=None, stop_flag=None):
    from core.utils import ensure_dir, get_book_dir, write_file, count_words
    def log(msg):
        if log_callback: log_callback(msg)
    bid = extract_book_id(book_id_or_url)
    if not bid: return {"error":"无法识别 book_id"}
    log(f"book_id: {bid}")
    try:
        resp, title, _, chapters = get_fanqie(f"https://fanqienovel.com/page/{bid}", _UA)
    except Exception as e: return {"error":f"获取失败:{e}"}
    log(f"书名: {title}"); log(f"共 {len(chapters)} 章")
    bk = get_book_dir(title) if not output_dir else os.path.join(output_dir, re.sub(r"[\\/:*?\x22<>|]","",title)[:40].strip())
    if output_dir: ensure_dir(bk)
    cd = os.path.join(bk, "正文"); ensure_dir(cd)
    dn=0; tw=0; fl=[]
    for i,ch in enumerate(chapters):
        if stop_flag and stop_flag.is_set(): log(f"已停止 ({dn}/{len(chapters)})"); break
        a=ch.find("a")
        if not a: continue
        m=re.search(r"/reader/(\d+)",a.get("href",""))
        ct=a.get_text(strip=True)
        if not m or not ct: continue
        cid=m.group(1); cn=i+1
        try: _,_,c=get_api(cid,_UA,"txt")
        except: c=""
        if c:
            c=c.replace("\r\n","\n").strip()
            write_file(os.path.join(cd,f"第{cn:03d}章_{ct}.md"),f"# 第{cn:03d}章 {ct}\n\n{c}\n")
            w=count_words(c); tw+=w; dn+=1
            if i%10==0 or i==len(chapters)-1: log(f"  [{cn}/{len(chapters)}] {ct} ({w}字)")
        else: fl.append(ct); log(f"  [{cn}/{len(chapters)}] {ct} - 失败")
        time.sleep(random.uniform(0.2,0.5))
    write_file(os.path.join(bk,"项目元数据.json"),json.dumps({"title":title,"downloaded":dn,"total_words":tw,"book_id":bid,"download_date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")},ensure_ascii=False,indent=2))
    log(f"\n下载完成: {dn}/{len(chapters)}章 {tw:,}字")
    if fl: log(f"失败: {len(fl)}章")
    return {"title":title,"book_id":bid,"total_chapters":len(chapters),"downloaded":dn,"total_words":tw,"book_dir":bk,"failed":fl}
