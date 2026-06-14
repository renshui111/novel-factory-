with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add download import
old_import = "from reader_sim import simulate_reader, simulate_all_readers, predict_abandonment, get_readability_score"
new_import = "from reader_sim import simulate_reader, simulate_all_readers, predict_abandonment, get_readability_score\nfrom downloader import download_novel, detect_platform, PLATFORMS"
content = content.replace(old_import, new_import)

# 2. Add "download" to sidebar nav items
old_nav = '''            ("settings",  "  设置"),
        ]'''
new_nav = '''            ("download",  "  下载"),
            ("settings",  "  设置"),
        ]'''
content = content.replace(old_nav, new_nav)

# 3. Add emoji
old_emoji = '''            "settings": "gear",
        }'''
new_emoji = '''            "download": "download", "settings": "gear",
        }'''
content = content.replace(old_emoji, new_emoji)

# 4. Add "download" to page names in _build_main
old_names = 'names = ["bookshelf", "create", "editor", "analyze", "reverse", "reader", "settings"]'
new_names = 'names = ["bookshelf", "create", "editor", "analyze", "reverse", "reader", "download", "settings"]'
content = content.replace(old_names, new_names)

# 5. Add _build_download call
old_build_calls = '        self._build_settings()'
new_build_calls = '        self._build_download()\n        self._build_settings()'
content = content.replace(old_build_calls, new_build_calls)

# 6. Add Obsidian path constant and helper
old_on_close = "    def _on_close(self):"
obsidian_insert = '''    # Obsidian路径
    OBSIDIAN_EXE = r"C:\\Users\\CodexSandboxOffline\\AppData\\Local\\Programs\\Obsidian\\Obsidian.exe"

    def _open_in_obsidian(self, path):
        """在 Obsidian 中打开指定目录"""
        import subprocess
        if not path or not os.path.isdir(path):
            return
        try:
            subprocess.Popen([self.OBSIDIAN_EXE, path], shell=False)
        except FileNotFoundError:
            # Try shortcut path
            obs_path = r"C:\\Users\\g\\AppData\\Local\\Programs\\Obsidian\\Obsidian.exe"
            try:
                subprocess.Popen([obs_path, path], shell=False)
            except Exception:
                pass
        except Exception:
            pass

    # ================================================================
    # 页面: 下载
    # ================================================================
    def _build_download(self):
        p = self.pages["download"]
        self._sect(p, "小说下载")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkLabel(scroll, text="粘贴小说URL（目录页或第一章）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        urlf = ctk.CTkFrame(scroll, fg_color=CARD_HOVER, corner_radius=6)
        urlf.pack(fill="x", pady=(0, 8))
        self._dl_url = ctk.CTkEntry(urlf, font=("Microsoft YaHei", 10), fg_color=CARD, text_color=TEXT, height=32,
                                     placeholder_text="https://...")
        self._dl_url.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        # Platform info
        inf = ctk.CTkFrame(scroll, fg_color="transparent")
        inf.pack(fill="x", pady=(4, 8))
        self._dl_platform_label = ctk.CTkLabel(inf, text="检测平台：", font=("Microsoft YaHei", 11), text_color=TEXT_DIM)
        self._dl_platform_label.pack(side="left")
        ctk.CTkButton(inf, text="检测", command=self._detect_dl_platform,
                      fg_color=CARD_HOVER, width=50, height=26).pack(side="left", padx=4)

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        self._dl_btn = ctk.CTkButton(bf, text="开始下载", command=self._start_download,
                                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=140)
        self._dl_btn.pack(side="left", padx=3)
        ctk.CTkButton(bf, text="停止", command=self._stop_download,
                      fg_color="#555", width=80).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="在 Obsidian 打开", command=lambda: self._open_in_obsidian(self._dl_last_dir if hasattr(self, "_dl_last_dir") else ""),
                      fg_color="#7c4dff", width=120).pack(side="right", padx=3)

        # Log
        self._dl_log = ctk.CTkTextbox(scroll, fg_color="#10121c", text_color=TEXT,
                                       font=("Consolas", 11), height=300)
        self._dl_log.pack(fill="both", expand=True)
        self._dl_status = ctk.CTkLabel(scroll, text="就绪 — 支持番茄小说、起点、纵横等平台", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._dl_status.pack(anchor="w", pady=(4, 8))

        self._dl_stop_flag = None
        self._dl_last_dir = ""

    def _detect_dl_platform(self):
        url = self._dl_url.get().strip()
        if not url:
            return
        platform = detect_platform(url)
        name = PLATFORMS.get(platform, {}).get("name", "未知")
        self._dl_platform_label.configure(text=f"检测平台：{name}", text_color=GREEN)

    def _start_download(self):
        url = self._dl_url.get().strip()
        if not url:
            self._dl_status.configure(text="请粘贴小说URL")
            return
        self._dl_stop_flag = threading.Event()
        self._dl_btn.configure(state="disabled", text="下载中...")
        self._dl_log.delete("1.0", "end")
        self._dl_status.configure(text="正在连接...")
        def task():
            result = download_novel(url, log_callback=lambda m: self._log(self._dl_log, m),
                                    stop_flag=self._dl_stop_flag)
            if "error" in result:
                self.root.after(0, lambda: self._dl_status.configure(text=result["error"], text_color=RED))
            else:
                self._dl_last_dir = result.get("book_dir", "")
                self.root.after(0, lambda: self._dl_status.configure(
                    text=f"下载完成: {result['title']} ({result['downloaded']}章, {result['total_words']:,}字) | 作者: {result.get('author', '未知')}",
                    text_color=GREEN))
            self.root.after(0, lambda: self._dl_btn.configure(state="normal", text="开始下载"))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _stop_download(self):
        if self._dl_stop_flag:
            self._dl_stop_flag.set()
            self._dl_status.configure(text="已停止")

    def _on_close(self):'''

content = content.replace(old_on_close, obsidian_insert)

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("GUI updated with download + Obsidian")
