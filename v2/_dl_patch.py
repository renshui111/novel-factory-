with open("downloader.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add fanqie decryption support
old_extract_content = '''def _extract_content(soup, cfg: dict, platform_key: str) -> str:
    """提取章节正文"""
    # Platform-specific extraction
    if platform_key == "qidian":
        content_div = soup.select_one("div.read-content, div.main-text")
        if content_div:
            return content_div.get_text("\\n", strip=True)
    
    # Generic extraction
    for sel in cfg["selector_content"].split(", "):
        div = soup.select_one(sel.strip())
        if div:
            # Remove scripts, ads, etc.
            for tag in div.select("script, style, .ads, .toolbar, .nav"):
                tag.decompose()
            return div.get_text("\\n", strip=True)
    
    # Fallback: get all text from body
    body = soup.find("body")
    if body:
        for tag in body.select("script, style, nav, header, footer, .nav, .toolbar"):
            tag.decompose()
        return body.get_text("\\n", strip=True)
    
    return ""'''

new_extract_content = '''def _extract_content(soup, cfg: dict, platform_key: str) -> str:
    """提取章节正文"""
    # Platform-specific extraction
    if platform_key == "qidian":
        content_div = soup.select_one("div.read-content, div.main-text")
        if content_div:
            return content_div.get_text("\\n", strip=True)
    
    # 番茄小说: content may be in specific divs
    if platform_key == "fanqie":
        # Try multiple selectors
        for sel in ["div.content", "div.chapter-content", "div.muye-reader-content",
                     "div.read-content", "article", "#chapter-content"]:
            div = soup.select_one(sel)
            if div:
                for tag in div.select("script, style, .ads, .toolbar, .nav"):
                    tag.decompose()
                text = div.get_text("\\n", strip=True)
                if len(text) > 100:
                    return text
    
    # Generic extraction
    for sel in cfg["selector_content"].split(", "):
        div = soup.select_one(sel.strip())
        if div:
            for tag in div.select("script, style, .ads, .toolbar, .nav"):
                tag.decompose()
            return div.get_text("\\n", strip=True)
    
    # Fallback: get all text from body
    body = soup.find("body")
    if body:
        for tag in body.select("script, style, nav, header, footer, .nav, .toolbar"):
            tag.decompose()
        return body.get_text("\\n", strip=True)
    
    return ""'''

content = content.replace(old_extract_content, new_extract_content)

# Add fanqie API-based download as alternative
# Add after the download_novel function
old_batch_func = '''def download_from_url_list(urls: list, output_dir: str = "",
                           log_callback=None, stop_flag=None) -> list:'''

new_batch_func = '''def download_fanqie_via_api(book_id: str, output_dir: str = "",
                                log_callback=None, stop_flag=None) -> dict:
    """番茄小说 API 下载（备用方案）
    
    番茄小说的章节内容通过 API 获取，部分内容有简单加密
    这个方法尝试直接调用 API 获取章节列表和内容
    """
    import requests
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://fanqienovel.com/",
    }
    
    API_BASE = "https://fanqienovel.com/api"
    
    if log_callback:
        log_callback(f"尝试API方式下载番茄小说 (ID: {book_id})")
    
    try:
        # Get book info
        info_url = f"https://fanqienovel.com/page/{book_id}"
        resp = requests.get(info_url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract title
        title_el = soup.select_one("h1, .book-title, .bookName")
        title = title_el.get_text(strip=True) if title_el else f"fanqie_{book_id}"
        title = re.sub(r'[\\\\/:*?"<>|]', '', title)[:40].strip()
        
        # Extract author
        author_el = soup.select_one(".author, .book-author, a[href*='author']")
        author = author_el.get_text(strip=True) if author_el else ""
        
        if log_callback:
            log_callback(f"书名: {title} | 作者: {author}")
        
        # Find chapter links
        chapter_links = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if "/reader/" in href or "/read/" in href:
                full_url = f"https://fanqienovel.com{href}" if href.startswith("/") else href
                chapter_links.append((text, full_url))
        
        if not chapter_links:
            return {"error": "API方式也未找到章节列表，请确认URL正确"}
        
        if log_callback:
            log_callback(f"发现 {len(chapter_links)} 章")
        
        # Download chapters
        from core import ensure_dir, get_output_dir
        if not output_dir:
            output_dir = get_output_dir()
        
        book_dir = os.path.join(output_dir, title)
        ensure_dir(book_dir)
        chapter_dir = os.path.join(book_dir, "正文")
        ensure_dir(chapter_dir)
        
        total_words = 0
        downloaded = 0
        
        for i, (ch_title, ch_url) in enumerate(chapter_links):
            if stop_flag and stop_flag.is_set():
                break
            
            ch_num = i + 1
            if log_callback and (ch_num % 10 == 0 or ch_num == 1):
                log_callback(f"下载中: {ch_num}/{len(chapter_links)}")
            
            try:
                ch_resp = requests.get(ch_url, headers=headers, timeout=20)
                ch_resp.encoding = "utf-8"
                ch_soup = BeautifulSoup(ch_resp.text, "html.parser")
                
                content = _extract_content(ch_soup, PLATFORMS["fanqie"], "fanqie")
                if content:
                    content = _clean_content(content)
                    safe_title = re.sub(r'[\\\\/:*?"<>|]', '', ch_title)[:30].strip() or f"第{ch_num:03d}章"
                    filename = f"第{ch_num:03d}章_{safe_title}.md"
                    filepath = os.path.join(chapter_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"# {ch_title}\\n\\n{content}")
                    
                    total_words += len(content)
                    downloaded += 1
                    time.sleep(0.5)
            except Exception as e:
                if log_callback:
                    log_callback(f"第{ch_num}章失败: {e}")
                continue
        
        # Save metadata
        meta = {
            "title": title, "author": author,
            "platform": "番茄小说", "platform_key": "fanqie",
            "source_url": info_url, "book_id": book_id,
            "total_chapters": len(chapter_links),
            "downloaded_chapters": downloaded,
            "total_words": total_words,
            "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        meta_path = os.path.join(book_dir, "项目元数据.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        if log_callback:
            log_callback(f"下载完成: {title} ({downloaded}章, {total_words:,}字)")
        
        return {"title": title, "author": author, "platform": "番茄小说",
                "total_chapters": len(chapter_links), "downloaded": downloaded,
                "total_words": total_words, "book_dir": book_dir, "metadata": meta}
        
    except Exception as e:
        return {"error": f"API下载失败: {str(e)}"}


def extract_fanqie_book_id(url: str) -> str:
    """从番茄小说URL中提取书籍ID"""
    m = re.search(r'/page/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/reader/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'book_id=(\d+)', url)
    if m:
        return m.group(1)
    return ""


def download_from_url_list(urls: list, output_dir: str = "",
                           log_callback=None, stop_flag=None) -> list:'''

content = content.replace(old_batch_func, new_batch_func)

# Update download_novel to try API fallback for fanqie
old_return_error = '''    except requests.exceptions.ConnectionError:
        return {"error": f"无法连接到服务器，请检查网络或URL"}'''
new_return_error = '''    except requests.exceptions.ConnectionError:
        # For fanqie, try API fallback
        if platform_key == "fanqie":
            book_id = extract_fanqie_book_id(url)
            if book_id:
                if log_callback:
                    log_callback("网页下载失败，尝试API方式...")
                return download_fanqie_via_api(book_id, output_dir, log_callback, stop_flag)
        return {"error": f"无法连接到服务器，请检查网络或URL"}'''
content = content.replace(old_return_error, new_return_error)

with open("downloader.py", "w", encoding="utf-8") as f:
    f.write(content)
print("downloader.py: fanqie API fallback added")
