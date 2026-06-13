# Inserts at line 3030 - 5 new page build methods
    # ══════════════════════════════════════
    # 页面: AI交互式编辑器
    # ══════════════════════════════════════
    def _build_editor_page(self):
        p = self.pages["editor"]
        self._sect(p, "AI交互式编辑器")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Chapter input
        ctk.CTkLabel(scroll, text="原文章节（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._editor_text = ctk.CTkTextbox(scroll, height=200, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_text.pack(fill="x", pady=(0, 8))

        # Instruction
        ctk.CTkLabel(scroll, text="修改指令（自然语言描述）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._editor_instruction = ctk.CTkTextbox(scroll, height=60, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_instruction.pack(fill="x", pady=(0, 8))
        self._editor_instruction.insert("1.0", "例如：打斗太软了，加点狠劲 / 对话不够自然 / 加一段心理描写")

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        ctk.CTkButton(bf, text="AI改稿", command=self._run_editor_edit,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=140).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="编辑对话", command=self._run_dialogue_edit,
                      fg_color=BLUE, width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="插入场景", command=self._run_add_scene,
                      fg_color="#9c27b0", width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="撤销", command=self._editor_undo,
                      fg_color="#666", width=80).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="重做", command=self._editor_redo,
                      fg_color="#666", width=80).pack(side="left", padx=3)

        # Result
        ctk.CTkLabel(scroll, text="改稿结果", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w", pady=(8, 4))
        self._editor_result = ctk.CTkTextbox(scroll, height=280, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_result.pack(fill="both", expand=True)

        # Status
        self._editor_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._editor_status.pack(anchor="w", pady=(4, 8))

        # Init edit history
        self._edit_history = EditHistory()

    def _run_editor_edit(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text or not instruction:
            self._editor_status.configure(text="请填写原文和修改指令")
            return
        self._edit_history.push(text, instruction)
        self._editor_status.configure(text="AI改稿中...")
        def task():
            result = edit_chapter(text, instruction)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_dialogue_edit(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text:
            self._editor_status.configure(text="请填写原文")
            return
        if "角色" not in instruction and "对话" not in instruction:
            self._editor_status.configure(text='指令中请包含"角色名"和"语气要求"')
            return
        self._editor_status.configure(text="编辑对话中...")
        def task():
            parts = instruction.split("，")
            char = parts[0] if parts else ""
            tone = parts[1] if len(parts) > 1 else instruction
            result = edit_dialogue(text, char, tone)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_add_scene(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text or not instruction:
            self._editor_status.configure(text="请填写原文和场景描述")
            return
        self._editor_status.configure(text="插入场景中...")
        def task():
            result = add_scene(text, instruction)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _show_editor_result(self, result):
        if "error" in result:
            self._editor_result.delete("1.0", "end")
            self._editor_result.insert("1.0", f"错误: {result['error']}")
            self._editor_status.configure(text=f"失败: {result['error']}", text_color=RED)
            return
        edited = result.get("edited", "")
        summary = result.get("changes_summary", "")
        self._editor_result.delete("1.0", "end")
        self._editor_result.insert("1.0", edited)
        if summary:
            self._editor_result.insert("end", f"\n\n{'='*40}\n【修改摘要】\n{summary}")
        self._editor_status.configure(text="改稿完成 ✓", text_color=GREEN)

    def _editor_undo(self):
        text = self._edit_history.undo()
        if text:
            self._editor_text.delete("1.0", "end")
            self._editor_text.insert("1.0", text)
            self._editor_status.configure(text="已撤销")
        else:
            self._editor_status.configure(text="无法继续撤销")

    def _editor_redo(self):
        text = self._edit_history.redo()
        if text:
            self._editor_text.delete("1.0", "end")
            self._editor_text.insert("1.0", text)
            self._editor_status.configure(text="已重做")
        else:
            self._editor_status.configure(text="无法继续重做")

    # ══════════════════════════════════════
    # 页面: 读者模拟
    # ══════════════════════════════════════
    def _build_reader(self):
        p = self.pages["reader"]
        self._sect(p, "AI读者模拟")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkLabel(scroll, text="章节内容（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._reader_text = ctk.CTkTextbox(scroll, height=180, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_text.pack(fill="x", pady=(0, 8))

        # Reader type selection
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        self._reader_type_var = ctk.StringVar(value="all")
        ctk.CTkLabel(bf, text="读者类型：", font=("Microsoft YaHei", 12), text_color=TEXT).pack(side="left", padx=(0, 8))
        for rt, label in [("all", "全部"), ("hardcore", "硬核书迷"), ("casual", "小白读者"), ("editor", "编辑视角")]:
            ctk.CTkRadioButton(bf, text=label, variable=self._reader_type_var, value=rt,
                               font=("Microsoft YaHei", 11), text_color=TEXT, fg_color=ACCENT).pack(side="left", padx=6)

        # Chapter number
        ctk.CTkLabel(bf, text="  章节号：", font=("Microsoft YaHei", 12), text_color=TEXT).pack(side="left")
        self._reader_ch_num = ctk.CTkEntry(bf, width=50, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._reader_ch_num.insert(0, "1")
        self._reader_ch_num.pack(side="left", padx=4)

        ctk.CTkButton(bf, text="模拟读者", command=self._run_reader_sim,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=120).pack(side="right", padx=3)
        ctk.CTkButton(bf, text="可读性分析", command=self._run_readability,
                      fg_color=BLUE, width=100).pack(side="right", padx=3)

        # Results
        self._reader_result = ctk.CTkTextbox(scroll, height=350, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_result.pack(fill="both", expand=True)
        self._reader_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reader_status.pack(anchor="w", pady=(4, 8))

    def _run_reader_sim(self):
        text = self._reader_text.get("1.0", "end-1c").strip()
        if not text:
            self._reader_status.configure(text="请填写章节内容")
            return
        rtype = self._reader_type_var.get()
        try:
            ch_num = int(self._reader_ch_num.get())
        except ValueError:
            ch_num = 1
        self._reader_status.configure(text="AI读者正在阅读...")
        self._reader_result.delete("1.0", "end")
        def task():
            if rtype == "all":
                results = simulate_all_readers(text, ch_num)
                def show():
                    self._reader_result.delete("1.0", "end")
                    for r in results:
                        self._reader_result.insert("end", f"\n{'='*40}\n### {r.get('reader_name', '')}\n{'='*40}\n{r.get('feedback', r.get('error', ''))}\n")
                    self._reader_status.configure(text="三种读者模拟完成 ✓", text_color=GREEN)
                self.root.after(0, show)
            else:
                result = simulate_reader(text, rtype, ch_num)
                def show():
                    self._reader_result.delete("1.0", "end")
                    self._reader_result.insert("1.0", result.get("feedback", result.get("error", "")))
                    self._reader_status.configure(text=f"{result.get('reader_name', '')} 反馈完成 ✓", text_color=GREEN)
                self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_readability(self):
        text = self._reader_text.get("1.0", "end-1c").strip()
        if not text:
            self._reader_status.configure(text="请填写章节内容")
            return
        score = get_readability_score(text)
        self._reader_result.delete("1.0", "end")
        lines = [
            "📊 可读性分析（纯规则，不调AI）",
            "=" * 40,
            f"平均句长：{score['avg_sentence_length']} 字符",
            f"段落数：{score['paragraph_count']}",
            f"平均段落长：{score['avg_paragraph_length']} 字符",
            f"段落长度方差：{score['paragraph_variance']}（越大变化越多）",
            f"对话占比：{score['dialogue_ratio']:.2%}",
            f"总句数：{score['total_sentences']}",
            "",
            "💡 解读：",
            "平均句长 < 20 → 太碎；> 60 → 太长",
            "对话占比 20%-40% → 网文黄金区间",
            "段落方差大 → 张弛有度",
        ]
        self._reader_result.insert("1.0", "\n".join(lines))
        self._reader_status.configure(text="可读性分析完成 ✓", text_color=GREEN)

    # ══════════════════════════════════════
    # 页面: 逆向工程
    # ══════════════════════════════════════
    def _build_reverse(self):
        p = self.pages["reverse"]
        self._sect(p, "逆向工程畅销书")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # File selection
        ctk.CTkLabel(scroll, text="选择一本小说文件（.txt/.md）进行深度解构", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        ff = ctk.CTkFrame(scroll, fg_color=CARD_HOVER, corner_radius=6)
        ff.pack(fill="x", pady=(0, 8))
        self._reverse_file_var = ctk.StringVar(value="")
        ctk.CTkEntry(ff, textvariable=self._reverse_file_var, font=("Microsoft YaHei", 10),
                     fg_color=CARD, text_color=TEXT, height=32).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkButton(ff, text="浏览", command=self._browse_reverse_file, width=55).pack(side="right", padx=4)

        # New book topic for formula application
        ctk.CTkLabel(scroll, text="（可选）新书主题：应用解构公式生成大纲", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._reverse_topic = ctk.CTkEntry(scroll, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, height=32)
        self._reverse_topic.pack(fill="x", pady=(0, 8))
        self._reverse_topic.insert(0, "例如：废柴少年获得修仙系统")

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        ctk.CTkButton(bf, text="开始解构", command=self._run_reverse,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=140).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="套用公式生成大纲", command=self._run_apply_formula,
                      fg_color=BLUE, width=140).pack(side="left", padx=3)

        # Result
        self._reverse_result = ctk.CTkTextbox(scroll, height=380, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reverse_result.pack(fill="both", expand=True)
        self._reverse_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reverse_status.pack(anchor="w", pady=(4, 8))

        # Store last reverse report for apply_formula
        self._last_reverse_report = None

    def _browse_reverse_file(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._reverse_file_var.set(path)

    def _run_reverse(self):
        path = self._reverse_file_var.get().strip()
        if not path or not os.path.isfile(path):
            self._reverse_status.configure(text="请选择有效的文件")
            return
        self._reverse_status.configure(text="正在解构分析（6步）...")
        self._reverse_result.delete("1.0", "end")
        def task():
            def log(msg):
                self.root.after(0, lambda: self._reverse_status.configure(text=msg))
            report = reverse_engineer(path, log_callback=log)
            self._last_reverse_report = report
            def show():
                self._reverse_result.delete("1.0", "end")
                self._reverse_result.insert("1.0", json.dumps(report, ensure_ascii=False, indent=2))
                self._reverse_status.configure(text=f"解构完成 ✓ ({report.get('total_chapters', 0)}章, {report.get('total_words', 0):,}字)", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_apply_formula(self):
        if not self._last_reverse_report:
            self._reverse_status.configure(text="请先执行「开始解构」")
            return
        topic = self._reverse_topic.get().strip()
        if not topic:
            self._reverse_status.configure(text="请填写新书主题")
            return
        self._reverse_status.configure(text="正在套用公式生成大纲...")
        def task():
            outline = apply_formula_to_new_book(self._last_reverse_report, topic)
            def show():
                self._reverse_result.delete("1.0", "end")
                self._reverse_result.insert("1.0", outline)
                self._reverse_status.configure(text="公式套用完成 ✓", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    # ══════════════════════════════════════
    # 页面: 排行榜模拟
    # ══════════════════════════════════════
    def _build_leaderboard(self):
        p = self.pages["leaderboard"]
        self._sect(p, "排行榜模拟器")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Book info
        ctk.CTkLabel(scroll, text="作品信息", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w", pady=(8, 4))
        inf = ctk.CTkFrame(scroll, fg_color="transparent")
        inf.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(inf, text="书名：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._lb_book_name = ctk.CTkEntry(inf, width=200, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._lb_book_name.pack(side="left", padx=(4, 16))
        ctk.CTkLabel(inf, text="类型：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._lb_genre = ctk.CTkComboBox(inf, values=["玄幻", "仙侠", "都市", "历史", "科幻", "游戏", "悬疑", "言情", "轻小说"],
                                          font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, button_color=ACCENT,
                                          width=100, state="readonly")
        self._lb_genre.set("玄幻")
        self._lb_genre.pack(side="left", padx=4)

        # Chapter input
        ctk.CTkLabel(scroll, text="章节内容（粘贴多章，用空行分隔）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._lb_text = ctk.CTkTextbox(scroll, height=180, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._lb_text.pack(fill="x", pady=(0, 8))

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        ctk.CTkButton(bf, text="模拟排行榜", command=self._run_leaderboard,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=140).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="导出报告(MD)", command=self._export_lb_report,
                      fg_color=BLUE, width=120).pack(side="left", padx=3)

        # Result
        self._lb_result = ctk.CTkTextbox(scroll, height=380, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._lb_result.pack(fill="both", expand=True)
        self._lb_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._lb_status.pack(anchor="w", pady=(4, 8))

        # Store last result
        self._last_lb_result = None

    def _run_leaderboard(self):
        text = self._lb_text.get("1.0", "end-1c").strip()
        if not text:
            self._lb_status.configure(text="请填写章节内容")
            return
        # Parse chapters
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        chapters = [(i+1, p, len(p)) for i, p in enumerate(parts)]
        name = self._lb_book_name.get().strip() or "未命名作品"
        genre = self._lb_genre.get()
        wc = sum(len(p) for _, p, _ in chapters)
        self._lb_status.configure(text="AI正在分析竞争力...")
        def task():
            def log(msg):
                self.root.after(0, lambda: self._lb_status.configure(text=msg))
            result = simulate_leaderboard(chapters, name, genre, wc, log_callback=log)
            self._last_lb_result = result
            report = generate_leaderboard_report(result)
            def show():
                self._lb_result.delete("1.0", "end")
                self._lb_result.insert("1.0", report)
                score = result.get("reader_votes", {}).get("total_score", 0)
                self._lb_status.configure(text=f"排行榜分析完成 ✓ 综合评分: {score}/10", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _export_lb_report(self):
        if not self._last_lb_result:
            self._lb_status.configure(text="请先执行「模拟排行榜」")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            report = generate_leaderboard_report(self._last_lb_result)
            write_file(path, report)
            self._lb_status.configure(text=f"报告已导出: {path}", text_color=GREEN)

    # ══════════════════════════════════════
    # 页面: AI配音预览
    # ══════════════════════════════════════
    def _build_voice(self):
        p = self.pages["voice"]
        self._sect(p, "AI配音脚本预览")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkLabel(scroll, text="章节内容（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._voice_text = ctk.CTkTextbox(scroll, height=180, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._voice_text.pack(fill="x", pady=(0, 8))

        # Settings
        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(sf, text="旁白音色：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._voice_narrator = ctk.CTkComboBox(sf, values=["沉稳男声", "温和女声", "清亮男声", "磁性男声", "知性女声"],
                                               font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, button_color=ACCENT,
                                               width=120, state="readonly")
        self._voice_narrator.set("沉稳男声")
        self._voice_narrator.pack(side="left", padx=(4, 16))
        ctk.CTkLabel(sf, text="章节号：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._voice_ch_num = ctk.CTkEntry(sf, width=50, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._voice_ch_num.insert(0, "1")
        self._voice_ch_num.pack(side="left", padx=4)
        ctk.CTkButton(sf, text="生成脚本", command=self._run_voice,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13), width=120).pack(side="right", padx=3)
        self._voice_preview_btn = ctk.CTkButton(sf, text="预览前10行", command=self._preview_voice,
                                                 fg_color=BLUE, width=100)
        self._voice_preview_btn.pack(side="right", padx=3)

        # Result
        self._voice_result = ctk.CTkTextbox(scroll, height=350, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._voice_result.pack(fill="both", expand=True)
        self._voice_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._voice_status.pack(anchor="w", pady=(4, 8))

        # Store last script
        self._last_voice_script = None

    def _run_voice(self):
        text = self._voice_text.get("1.0", "end-1c").strip()
        if not text:
            self._voice_status.configure(text="请填写章节内容")
            return
        try:
            ch_num = int(self._voice_ch_num.get())
        except ValueError:
            ch_num = 1
        narrator = self._voice_narrator.get()
        self._voice_status.configure(text="生成配音脚本中...")
        def task():
            script = generate_voice_script(text, ch_num, narrator_voice=narrator)
            self._last_voice_script = script
            output = export_voice_script_as_text(script)
            def show():
                self._voice_result.delete("1.0", "end")
                self._voice_result.insert("1.0", output)
                stats = script.get("stats", {})
                self._voice_status.configure(
                    text=f"配音脚本完成 ✓ {stats.get('total_lines', 0)}行, {stats.get('dialogue_count', 0)}句对话, 预估{stats.get('total_duration_estimate_minutes', 0)}分钟",
                    text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _preview_voice(self):
        if not self._last_voice_script:
            self._voice_status.configure(text="请先生成配音脚本")
            return
        preview = preview_first_lines(self._last_voice_script, 15)
        self._voice_result.delete("1.0", "end")
        self._voice_result.insert("1.0", f"【配音预览（前15行）】\n{'='*40}\n{preview}")
        self._voice_status.configure(text="预览模式", text_color=ACCENT)

