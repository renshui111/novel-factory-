    # ══════════════════════════════════════
    # 页面: 读者模拟 (全书支持)
    # ══════════════════════════════════════
    def _build_reader(self):
        p = self.pages["reader"]
        self._sect(p, "AI读者模拟 — 全书分析")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # ── Tab bar ──
        tab_bar = ctk.CTkFrame(scroll, fg_color="transparent")
        tab_bar.pack(fill="x", pady=(4, 8))
        self._reader_tab = ctk.StringVar(value="single")
        ctk.CTkSegmentedButton(tab_bar, values=["single", "fullbook"], variable=self._reader_tab,
                               font=("Microsoft YaHei", 12), selected_color=ACCENT,
                               command=self._on_reader_tab_change).pack(side="left")

        # ── Single chapter panel ──
        self._reader_single_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ctk.CTkLabel(self._reader_single_frame, text="章节内容（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._reader_text = ctk.CTkTextbox(self._reader_single_frame, height=160, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_text.pack(fill="x", pady=(0, 8))

        sf = ctk.CTkFrame(self._reader_single_frame, fg_color="transparent")
        sf.pack(fill="x", pady=(4, 8))
        self._reader_type_var = ctk.StringVar(value="all")
        ctk.CTkLabel(sf, text="读者：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        for rt, label in [("all", "全部"), ("hardcore", "硬核"), ("casual", "小白"), ("editor", "编辑"), ("fangirl", "粉丝"), ("skeptic", "喷子"), ("newcomer", "路人")]:
            ctk.CTkRadioButton(sf, text=label, variable=self._reader_type_var, value=rt,
                               font=("Microsoft YaHei", 10), text_color=TEXT, fg_color=ACCENT).pack(side="left", padx=3)
        ctk.CTkLabel(sf, text=" 章号：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._reader_ch_num = ctk.CTkEntry(sf, width=45, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._reader_ch_num.insert(0, "1")
        self._reader_ch_num.pack(side="left", padx=3)
        ctk.CTkButton(sf, text="分析本章", command=self._run_reader_sim,
                      fg_color=ACCENT, font=("Microsoft YaHei", 12), width=90).pack(side="right", padx=2)

        # ── Full book panel ──
        self._reader_full_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ctk.CTkLabel(self._reader_full_frame, text="导入全书文件（.txt / .md）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        ff = ctk.CTkFrame(self._reader_full_frame, fg_color=CARD_HOVER, corner_radius=6)
        ff.pack(fill="x", pady=(0, 8))
        self._reader_book_path = ctk.StringVar(value="")
        ctk.CTkEntry(ff, textvariable=self._reader_book_path, font=("Microsoft YaHei", 10),
                     fg_color=CARD, text_color=TEXT, height=32).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkButton(ff, text="浏览", command=self._browse_reader_book, width=55).pack(side="right", padx=4)

        bf2 = ctk.CTkFrame(self._reader_full_frame, fg_color="transparent")
        bf2.pack(fill="x", pady=(4, 8))
        self._reader_full_btn = ctk.CTkButton(bf2, text="全本分析（6种读者）", command=self._run_full_book_analysis,
                                              fg_color=ACCENT, font=("Microsoft YaHei", 13), width=180)
        self._reader_full_btn.pack(side="left", padx=3)
        ctk.CTkButton(bf2, text="导出报告(MD)", command=self._export_reader_report,
                      fg_color=BLUE, width=110).pack(side="left", padx=3)
        ctk.CTkButton(bf2, text="可读性扫描", command=self._run_readability,
                      fg_color="#555", width=100).pack(side="left", padx=3)

        self._reader_full_status = ctk.CTkLabel(self._reader_full_frame, text="", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reader_full_status.pack(anchor="w")

        # ── Result area (shared) ──
        ctk.CTkLabel(scroll, text="分析结果", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w", pady=(8, 4))
        self._reader_result = ctk.CTkTextbox(scroll, height=400, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_result.pack(fill="both", expand=True)

        # Navigation for full-book chapter detail
        navf = ctk.CTkFrame(scroll, fg_color="transparent")
        navf.pack(fill="x", pady=(6, 8))
        ctk.CTkLabel(navf, text="查看章节详情：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._reader_ch_detail = ctk.CTkEntry(navf, width=60, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._reader_ch_detail.insert(0, "1")
        self._reader_ch_detail.pack(side="left", padx=4)
        ctk.CTkButton(navf, text="跳转", command=self._reader_goto_chapter,
                      fg_color=ACCENT, width=50, height=26).pack(side="left", padx=2)
        self._reader_status = ctk.CTkLabel(navf, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reader_status.pack(side="left", padx=10)

        # State
        self._last_reader_analysis = None  # Full-book analysis result
        self._reader_book_data = None  # load_book result

        # Show single panel by default
        self._reader_single_frame.pack(fill="x")
        self._reader_tab.set("single")

    def _on_reader_tab_change(self, val):
        if val == "single":
            self._reader_full_frame.pack_forget()
            self._reader_single_frame.pack(fill="x", before=self._reader_result.master.winfo_children()[self._reader_result.master.winfo_children().index(self._reader_result)])
        else:
            self._reader_single_frame.pack_forget()
            self._reader_full_frame.pack(fill="x", before=self._reader_result)

    def _browse_reader_book(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._reader_book_path.set(path)

    def _run_full_book_analysis(self):
        path = self._reader_book_path.get().strip()
        if not path or not os.path.isfile(path):
            self._reader_full_status.configure(text="请选择有效的文件")
            return
        self._reader_full_status.configure(text="正在加载+切分章节...", text_color=TEXT)
        self._reader_result.delete("1.0", "end")
        self._reader_full_btn.configure(state="disabled", text="分析中...")
        def task():
            # Load book
            book = load_book(path)
            if "error" in book:
                self.root.after(0, lambda: self._reader_full_status.configure(text=book["error"], text_color=RED))
                self.root.after(0, lambda: self._reader_full_btn.configure(state="normal", text="全本分析（6种读者）"))
                return
            self._reader_book_data = book
            self.root.after(0, lambda: self._reader_full_status.configure(
                text=f"已加载: {book['title']} ({book['total_chapters']}章, {book['total_words']:,}字)，正在逐章分析...",
                text_color=TEXT))
            # Analyze
            def log(msg):
                self.root.after(0, lambda: self._reader_full_status.configure(text=msg, text_color=TEXT))
            result = analyze_full_book(book, log_callback=log)
            self._last_reader_analysis = result
            report = generate_full_book_report(result)
            def show():
                self._reader_result.delete("1.0", "end")
                self._reader_result.insert("1.0", report)
                overall = result.get("overall", {})
                self._reader_full_status.configure(
                    text=f"分析完成 | 综合评分: {overall.get('avg_score', 0)}/10 | 趋势: {overall.get('score_trend_desc', '')} | 弃书风险: {overall.get('abandonment_risk', {}).get('risk', '')}",
                    text_color=GREEN)
                self._reader_full_btn.configure(state="normal", text="全本分析（6种读者）")
                self._reader_status.configure(text=f"共{result['total_chapters']}章，点击「跳转」查看单章详情")
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _reader_goto_chapter(self):
        if not self._last_reader_analysis:
            self._reader_status.configure(text="请先进行全本分析")
            return
        try:
            ch = int(self._reader_ch_detail.get())
        except ValueError:
            ch = 1
        report = generate_chapter_feedback_report(self._last_reader_analysis, ch)
        self._reader_result.delete("1.0", "end")
        self._reader_result.insert("1.0", report)
        self._reader_status.configure(text=f"已跳转到第{ch}章详情")
        self._reader_ch_detail.delete(0, "end")
        self._reader_ch_detail.insert(0, str(ch + 1))

    def _export_reader_report(self):
        if not self._last_reader_analysis:
            self._reader_status.configure(text="请先进行全本分析")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            report = generate_full_book_report(self._last_reader_analysis)
            write_file(path, report)
            self._reader_status.configure(text=f"报告已导出: {path}", text_color=GREEN)

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
            rtypes = None if rtype == "all" else [rtype]
            results = simulate_all_readers(text, ch_num, reader_types=rtypes)
            def show():
                self._reader_result.delete("1.0", "end")
                for r in results:
                    self._reader_result.insert("end",
                        f"\n{'='*40}\n### {r.get('reader_name', '?')}\n{'='*40}\n{r.get('feedback', r.get('error', ''))}\n")
                self._reader_status.configure(text="分析完成 ✓", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_readability(self):
        # If full book loaded, scan all chapters
        if self._reader_book_data:
            chs = self._reader_book_data.get("chapters", [])
            lines = ["📊 全书可读性扫描", "=" * 40, f"总章节: {len(chs)}", ""]
            total_ai = 0
            for ch in chs:
                rd = get_readability_score(ch["text"])
                ai_hits = scan_ai_markers(ch["text"])
                total_ai += len(ai_hits)
                lines.append(
                    f"第{ch['num']:>3}章 | 句长:{rd['avg_sentence_length']:5.0f} | "
                    f"段数:{rd['paragraph_count']:>3} | 对话比:{rd['dialogue_ratio']:.1%} | "
                    f"AI痕:{len(ai_hits):>2}")
            lines += ["", f"全书AI痕迹总计: {total_ai} 处"]
            self._reader_result.delete("1.0", "end")
            self._reader_result.insert("1.0", "\n".join(lines))
            self._reader_status.configure(text=f"可读性扫描完成，共{len(chs)}章")
        else:
            text = self._reader_text.get("1.0", "end-1c").strip()
            if not text:
                self._reader_status.configure(text="请填写章节内容或导入全书")
                return
            score = get_readability_score(text)
            ai_hits = scan_ai_markers(text)
            self._reader_result.delete("1.0", "end")
            lines = [
                "📊 可读性分析（纯规则）",
                "=" * 40,
                f"平均句长：{score['avg_sentence_length']} 字符（<20太碎，>60太长）",
                f"段落数：{score['paragraph_count']}",
                f"平均段落长：{score['avg_paragraph_length']} 字符",
                f"段落长度方差：{score['paragraph_variance']}（大=张弛有度）",
                f"对话占比：{score['dialogue_ratio']:.1%}（20%-40%=网文黄金区间）",
                f"总句数：{score['total_sentences']}",
                f"AI痕迹：{len(ai_hits)} 处",
            ]
            if ai_hits:
                lines.append(f"  → {', '.join(h['marker'] for h in ai_hits[:8])}")
            self._reader_result.insert("1.0", "\n".join(lines))
            self._reader_status.configure(text="可读性分析完成 ✓", text_color=GREEN)
