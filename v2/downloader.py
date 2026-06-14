# -*- coding: utf-8 -*-
"""downloader.py --- 小说下载器
支持多平台下载：番茄小说、起点、以及其他通用网站
下载后自动切分章节、提取元数据、保存为项目格式
"""

import os, re, json, time
from datetime import datetime
from urllib.parse import urlparse, urljoin

# 支持的平台配置
PLATFORMS = {
    "fanqie": {
        "name": "番茄小说",
        "domains": ["fanqienovel.com", "changdunovel.com"],
        "selector_chapter_list": "div.chapter-list a, div.catalog a",
        "selector_content": "div.content, div.chapter-content, article",
        "selector_title": "h1, .chapter-title",
        "encoding": "utf-8",
    },
    "qidian": {
        "name": "起点中文网",
        "domains": ["qidian.com", "read.qidian.com"],
        "selector_chapter_list": "div.catalog-content-wrap a, ul.cf li a",
        "selector_content": "div.read-content, div.main-text",
        "selector_title": "h3.j_chapterName, .content h1",
        "encoding": "utf-8",
    },
    "zongheng": {
        "name": "纵横中文网",
        "domains": ["zongheng.com"],
        "selector_chapter_list": "div.volume-list a, ul.chapter-list a",
        "selector_content": "div.content, div.reader-box",
        "selector_title": "h1.title, .chapter-title",
        "encoding": "utf-8",
    },
    "generic": {
        "name": "通用网站",
        "domains": [],
        "selector_chapter_list": "a[href]",
        "selector_content": "article, div.content, div#content, div.article-content, main",
        "selector_title": "h1, h2, .title",
        "encoding": "utf-8",
    },
}


def detect_platform(url: str) -> str:
    """根据 URL 自动检测平台"""
    domain = urlparse(url).netloc.lower()
    for key, cfg in PLATFORMS.items():
        for d in cfg["domains"]:
            if d in domain:
                return key
    return "generic"


def download_novel(url: str, output_dir: str = "",
                   log_callback=None, stop_flag=None) -> dict:
    """下载一本小说的全部章节
    
    Args:
        url: 小说目录页或第一章URL
        output_dir: 输出目录
        log_callback: 进度回调
        stop_flag: 停止标志
    
    Returns:
        {title, author, platform, chapters, total_words, book_dir, metadata}
    """
    import requests
    from bs4 import BeautifulSoup
    
    platform_key = detect_platform(url)
    platform_cfg = PLATFORMS.get(platform_key, PLATFORMS["generic"])
    
    if log_callback:
        log_callback(f"检测到平台: {platform_cfg['name']}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    try:
        # Step 1: Fetch the page
        if log_callback:
            log_callback("正在获取小说信息...")
        
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = platform_cfg["encoding"]
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Step 2: Extract title
        title = _extract_title(soup, platform_key)
        if not title:
            title = f"downloaded_{int(time.time())}"
        title = re.sub(r'[\\/:*?"<>|]', '', title)[:40].strip()
        
        if log_callback:
            log_callback(f"书名: {title}")
        
        # Step 3: Extract author
        author = _extract_author(soup, platform_key)
        
        if log_callback and author:
            log_callback(f"作者: {author}")
        
        # Step 4: Find chapter list
        chapter_links = _extract_chapter_links(soup, url, platform_cfg, platform_key)
        
        if not chapter_links:
            return {"error": "未找到章节目录，请确认URL是小说目录页"}
        
        if log_callback:
            log_callback(f"发现 {len(chapter_links)} 章")
        
        # Step 5: Create output directory
        from core import ensure_dir
        if not output_dir:
            from core import get_output_dir
            output_dir = get_output_dir()
        
        book_dir = os.path.join(output_dir, title)
        ensure_dir(book_dir)
        chapter_dir = os.path.join(book_dir, "正文")
        ensure_dir(chapter_dir)
        
        # Step 6: Download chapters
        total_words = 0
        downloaded = 0
        
        for i, (ch_title, ch_url) in enumerate(chapter_links):
            if stop_flag and stop_flag.is_set():
                if log_callback:
                    log_callback(f"已停止，完成 {downloaded}/{len(chapter_links)} 章")
                break
            
            ch_num = i + 1
            if log_callback and (ch_num % 10 == 0 or ch_num == 1):
                log_callback(f"下载中: {ch_num}/{len(chapter_links)}")
            
            try:
                ch_resp = requests.get(ch_url, headers=headers, timeout=30)
                ch_resp.encoding = platform_cfg["encoding"]
                ch_soup = BeautifulSoup(ch_resp.text, "html.parser")
                
                content = _extract_content(ch_soup, platform_cfg, platform_key)
                
                if content:
                    # Clean and format
                    content = _clean_content(content)
                    
                    # Save chapter
                    safe_title = re.sub(r'[\\/:*?"<>|]', '', ch_title)[:30].strip()
                    if not safe_title:
                        safe_title = f"第{ch_num:03d}章"
                    
                    filename = f"第{ch_num:03d}章_{safe_title}.md"
                    filepath = os.path.join(chapter_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"# {ch_title}\n\n{content}")
                    
                    total_words += len(content)
                    downloaded += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.3)
            except Exception as e:
                if log_callback:
                    log_callback(f"第{ch_num}章下载失败: {e}")
                continue
        
        # Step 7: Save metadata
        meta = {
            "title": title,
            "author": author,
            "platform": platform_cfg["name"],
            "platform_key": platform_key,
            "source_url": url,
            "total_chapters": len(chapter_links),
            "downloaded_chapters": downloaded,
            "total_words": total_words,
            "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "genre": "",
            "style_tags": [],
            "status": "downloaded",
        }
        
        meta_path = os.path.join(book_dir, "项目元数据.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # Also save a readable info file
        info_path = os.path.join(book_dir, "书籍信息.md")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"- **作者**: {author or '未知'}\n")
            f.write(f"- **来源平台**: {platform_cfg['name']}\n")
            f.write(f"- **来源URL**: {url}\n")
            f.write(f"- **总章节数**: {len(chapter_links)}\n")
            f.write(f"- **已下载**: {downloaded} 章\n")
            f.write(f"- **总字数**: {total_words:,}\n")
            f.write(f"- **下载日期**: {meta['download_date']}\n")
        
        if log_callback:
            log_callback(f"下载完成: {title} ({downloaded}章, {total_words:,}字)")
            log_callback(f"保存位置: {book_dir}")
        
        return {
            "title": title,
            "author": author,
            "platform": platform_cfg["name"],
            "total_chapters": len(chapter_links),
            "downloaded": downloaded,
            "total_words": total_words,
            "book_dir": book_dir,
            "metadata": meta,
        }
        
    except requests.exceptions.ConnectionError:
        return {"error": f"无法连接到服务器，请检查网络或URL"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时，请重试"}
    except Exception as e:
        return {"error": f"下载失败: {str(e)}"}


def _extract_title(soup, platform_key: str) -> str:
    """提取书名"""
    # Try common title selectors
    selectors = [
        "h1", ".book-title", ".bookName", ".novel-title",
        "meta[property='og:title']", "meta[name='title']",
        ".info h1", ".book-info h1",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            if sel.startswith("meta"):
                return el.get("content", "")
            return el.get_text(strip=True)
    # Fallback: page title
    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.get_text(strip=True)
        # Remove site suffix
        for suffix in [" - 番茄小说", " - 起点中文", " | 起点中文", "_起点中文"]:
            if suffix in t:
                t = t.split(suffix)[0]
        return t
    return ""


def _extract_author(soup, platform_key: str) -> str:
    """提取作者"""
    selectors = [
        ".author", ".book-author", "meta[name='author']",
        "a[href*='author']", ".writer", ".authorname",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            if sel.startswith("meta"):
                return el.get("content", "")
            return el.get_text(strip=True)
    return ""


def _extract_chapter_links(soup, base_url: str, cfg: dict, platform_key: str) -> list:
    """提取章节链接列表 [(title, url), ...]"""
    from urllib.parse import urljoin as uj
    
    links = []
    
    # Platform-specific extraction
    if platform_key == "fanqie":
        # 番茄小说: chapters in div with specific structure
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if text and len(text) > 1 and "chapter" in href.lower() or "/read/" in href:
                full_url = uj(base_url, href)
                links.append((text, full_url))
    
    elif platform_key == "qidian":
        # 起点: chapter list in specific containers
        for a in soup.select("ul.cf li a, div.catalog-content-wrap a, div.volume ul li a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if text and href:
                full_url = uj(base_url, href)
                links.append((text, full_url))
    
    else:
        # Generic: find all links that look like chapter links
        chapter_patterns = [
            r'第[零一二三四五六七八九十百千\d]+[章回节卷]',
            r'[Cc]hapter\s*\d+',
            r'^\d+[\.、\s]',
        ]
        
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if not text or not href:
                continue
            if any(re.search(p, text) for p in chapter_patterns):
                full_url = uj(base_url, href)
                # Deduplicate
                if (text, full_url) not in links:
                    links.append((text, full_url))
        
        # If still no links found, try broader search
        if not links:
            for a in soup.select(cfg["selector_chapter_list"]):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if text and href and len(text) > 2:
                    full_url = uj(base_url, href)
                    if (text, full_url) not in links:
                        links.append((text, full_url))
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for title, url in links:
        if url not in seen:
            seen.add(url)
            unique.append((title, url))
    
    return unique


def _extract_content(soup, cfg: dict, platform_key: str) -> str:
    """提取章节正文"""
    # Platform-specific extraction
    if platform_key == "qidian":
        content_div = soup.select_one("div.read-content, div.main-text")
        if content_div:
            return content_div.get_text("\n", strip=True)
    
    # Generic extraction
    for sel in cfg["selector_content"].split(", "):
        div = soup.select_one(sel.strip())
        if div:
            # Remove scripts, ads, etc.
            for tag in div.select("script, style, .ads, .toolbar, .nav"):
                tag.decompose()
            return div.get_text("\n", strip=True)
    
    # Fallback: get all text from body
    body = soup.find("body")
    if body:
        for tag in body.select("script, style, nav, header, footer, .nav, .toolbar"):
            tag.decompose()
        return body.get_text("\n", strip=True)
    
    return ""


def _clean_content(text: str) -> str:
    """清理正文内容"""
    # Remove excessive blank lines
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # Remove common ad patterns
    text = re.sub(r'本章未完.*?请点击下一页.*?', '', text, flags=re.DOTALL)
    text = re.sub(r'请记住本书首发域名.*?', '', text)
    text = re.sub(r'手机用户请浏览.*?', '', text)
    # Trim
    text = text.strip()
    return text


def download_from_url_list(urls: list, output_dir: str = "",
                           log_callback=None, stop_flag=None) -> list:
    """批量下载多个小说URL"""
    results = []
    for url in urls:
        if stop_flag and stop_flag.is_set():
            break
        result = download_novel(url, output_dir, log_callback, stop_flag)
        results.append(result)
    return results
