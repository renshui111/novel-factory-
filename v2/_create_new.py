    # ══════════════════════════════════════
    # 页面: 写书 — 手动分步流程
    # ══════════════════════════════════════
    def _build_create(self):
        p = self.pages["create"]
        self._sect(p, "写书 — 手动分步")

        cfg = load_config()["novel"]
        top = ctk.CTkFrame(p, fg_color=CARD)
        top.pack(fill="x", padx=20, pady=3)

        gf = ctk.CTkFrame(top, fg_color="transparent")
        gf.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(gf, text="主题:", font=("Microsoft YaHei", 12)).grid(row=0, column=0, sticky="w")
        self._topic_var = ctk.StringVar(value=cfg.get("topic", ""))
        ctk.CTkEntry(gf, textvariable=self._topic_var, width=250,
                     placeholder_text="如: 剑道独尊:重生").grid(row=0, column=1, padx=2)

        ctk.CTkLabel(gf, text="类型:", font=("Microsoft YaHei", 12)).grid(row=0, column=2, sticky="w", padx=8)
        self._genre_var = ctk.StringVar(value=cfg.get("genre", "玄幻"))
        ctk.CTkComboBox(gf, values=["玄幻", "仙侠", "科幻", "都市", "末世", "历史", "游戏", "言情"],
                        variable=self._genre_var, width=110).grid(row=0, column=3, padx=2)

        ctk.CTkLabel(gf, text="章节:", font=("Microsoft YaHei", 12)).grid(row=0, column=4, sticky="w", padx=8)
        self._ch_var = ctk.StringVar(value=str(cfg.get("num_chapters", 30)))
        ctk.CTkEntry(gf, textvariable=self._ch_var, width=60).grid(row=0, column=5, padx=2)

        ctk.CTkLabel(gf, text="字数/章:", font=("Microsoft YaHei", 12)).grid(row=0, column=6, sticky="w", padx=8)
        self._wc_var = ctk.StringVar(value=str(cfg.get("words_per_chapter", 3000)))
        ctk.CTkEntry(gf, textvariable=self._wc_var, width=70).grid(row=0, column=7, padx=2)

        # ── Step indicator (7 steps) ──
        self.step_frame = ctk.CTkFrame(p, fg_color=CARD)
        self.step_frame.pack(fill="x", padx=20, pady=3)
        sf = ctk.CTkFrame(self.step_frame, fg_color="transparent")
        sf.pack(pady=8)
        self._step_labels = {}
        self._step_keys = ["step1", "step2", "step3", "step4", "step5", "step6", "step7"]
        self._step_names = {
            "step1": "大纲", "step2": "世界观", "step3": "人物设定",
            "step4": "组织设定", "step5": "关系图谱", "step6": "章节目录", "step7": "写正文"
        }
        self._step_colors = {
            "step1": ACCENT, "step2": "#7c4dff", "step3": BLUE,
            "step4": "#00bcd4", "step5": "#4caf50", "step6": ORANGE, "step7": RED
        }
        for i, key in enumerate(self._step_keys):
            name = self._step_names[key]
            c = self._step_colors[key]
            sf2 = ctk.CTkFrame(sf, fg_color=CARD_HOVER, corner_radius=6)
            sf2.pack(side="left", padx=2)
            lbl = ctk.CTkLabel(sf2, text=f"{i+1}. {name}", font=("Microsoft YaHei", 10), text_color=PH)
            lbl.pack(padx=6, pady=4)
            self._step_labels[key] = lbl
            if i < 6:
                ctk.CTkLabel(sf, text="→", font=("Microsoft YaHei", 12), text_color=BORDER).pack(side="left", padx=1)

        # ── Main area ──
        mid = ctk.CTkFrame(p, fg_color=BG)
        mid.pack(fill="both", expand=True, padx=20, pady=3)

        # Left: step panel
        self._step_panel = ctk.CTkFrame(mid, fg_color=CARD, width=360, corner_radius=10)
        self._step_panel.pack(side="left", fill="y", padx=(0, 5))
        self._step_panel.pack_propagate(False)

        # Right: editor + log
        right = ctk.CTkFrame(mid, fg_color=BG)
        right.pack(side="right", fill="both", expand=True)

        # Editable text area
        ctk.CTkLabel(right, text="编辑区（可手动修改）", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w")
        self._create_editor = ctk.CTkTextbox(right, fg_color=CARD, text_color=TEXT,
                                              font=("Microsoft YaHei", 11), wrap="word")
        self._create_editor.pack(fill="both", expand=True, pady=(4, 4))

        # Log
        self._create_log = ctk.CTkTextbox(right, fg_color="#10121c", text_color=TEXT,
                                           font=("Consolas", 10), height=100)
        self._create_log.pack(fill="x", pady=(2, 0))
        self._log(self._create_log, "就绪 — 按步骤从「大纲」开始")

        # ── Bottom buttons ──
        btn_frame = ctk.CTkFrame(p, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self._step_btn = ctk.CTkButton(btn_frame, text="AI 生成",
                                        command=self._on_create_start,
                                        fg_color=ACCENT,
                                        font=("Microsoft YaHei", 14, "bold"),
                                        height=38, width=120)
        self._step_btn.pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="确认 → 下一步",
                      command=self._on_confirm_step,
                      fg_color=GREEN, font=("Microsoft YaHei", 13),
                      height=38, width=140).pack(side="left", padx=3)
        self._stop_btn = ctk.CTkButton(btn_frame, text="停止",
                                        command=self._stop,
                                        fg_color="#555", state="disabled")
        self._stop_btn.pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="打开目录",
                      command=lambda: self._open_dir(self._book_dir),
                      fg_color=BLUE).pack(side="right", padx=3)

        # State
        self._current_step = "step1"
        self._step_results = {}  # {step_key: text}
        self._show_step_panel("step1")

    def _show_step_panel(self, step_key):
        for w in self._step_panel.winfo_children():
            w.destroy()

        self._current_step = step_key
        c = self._step_colors.get(step_key, ACCENT)
        for k, lbl in self._step_labels.items():
            if k in self._step_results and self._step_results[k]:
                lbl.configure(text_color=GREEN)
            elif k == step_key:
                lbl.configure(text_color=c)
            else:
                lbl.configure(text_color=PH)

        name = self._step_names[step_key]
        step_num = self._step_keys.index(step_key) + 1

        header = ctk.CTkLabel(self._step_panel, text=f"步骤{step_num}: {name}",
                              font=("Microsoft YaHei", 15, "bold"), text_color=c)
        header.pack(anchor="w", padx=15, pady=(12, 5))

        descriptions = {
            "step1": "输入主题后点击「AI 生成」，AI 将生成完整的小说大纲，\n包括分卷结构、每章概要、高潮节点、爽点分布。\n生成后可在右侧编辑区修改。",
            "step2": "根据大纲生成世界观设定：时代背景、力量体系、\n势力分布、地理格局、特殊规则、货币资源。",
            "step3": "生成人物设定：主角、重要配角、反派的详细信息，\n包括性格、背景、能力、动机、成长弧线。",
            "step4": "生成组织/势力体系：宗门、国家、佣兵团等，\n各组织的等级、资源、历史恩怨。",
            "step5": "生成关系图谱：人物之间的关系网、组织间的关系、\n情感线设计。基于前4步的设定自动整合。",
            "step6": "生成章节目录：根据所有设定生成完整的章节目录，\n每章含标题和概要。确认后进入正文生成。",
            "step7": "开始逐章生成正文。每章根据设定自动写作，\n保证文风一致、人物不跑偏、剧情连贯。",
        }
        desc = descriptions.get(step_key, "")
        ctk.CTkLabel(self._step_panel, text=desc, font=("Microsoft YaHei", 11),
                     text_color=PH, wraplength=330, justify="left").pack(anchor="w", padx=15, pady=3)

        # Info area
        info = ctk.CTkTextbox(self._step_panel, height=120, fg_color="#10121c",
                               text_color=TEXT, font=("Microsoft YaHei", 10), state="disabled")
        info.pack(fill="x", padx=12, pady=5)
        summary_texts = {
            "step1": "大纲会保存在「大纲.md」\n后续步骤依赖大纲内容",
            "step2": "世界观保存在「世界观.md」\n核心设定，影响全局",
            "step3": "人物保存在「人物设定.md」\n至少10个角色的详细档案",
            "step4": "组织保存在「组织设定.md」\n势力的权力结构和利益关系",
            "step5": "关系保存在「关系图谱.md」\n谁和谁是什么关系",
            "step6": "目录保存在「目录.md」\n每章标题+概要",
            "step7": "正文逐章保存在「正文/」目录\n每章独立一个 .md 文件",
        }
        info.configure(state="normal")
        info.insert("1.0", summary_texts.get(step_key, ""))
        info.configure(state="disabled")

        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:
            self._create_editor.delete("1.0", "end")
            self._create_editor.insert("1.0", self._step_results[step_key])
            ctk.CTkButton(self._step_panel, text="重新生成",
                          command=lambda: self._ai_generate_step(step_key),
                          fg_color=ORANGE, width=100).pack(pady=8, padx=15)
        else:
            if step_key != "step1":
                self._create_editor.delete("1.0", "end")

    # ─── Step generation ───
    def _on_create_start(self):
        """AI 生成当前步骤"""
        self._ai_generate_step(self._current_step)

    def _ai_generate_step(self, step_key):
        """为指定步骤调用 AI 生成"""
        topic = self._topic_var.get().strip()
        genre = self._genre_var.get()
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000

        if step_key == "step1" and not topic:
            self._log(self._create_log, "请先填写主题")
            return

        self._step_btn.configure(state="disabled", text="生成中...")
        self._stop_btn.configure(state="normal")
        self._log(self._create_log, f"正在 AI 生成: {self._step_names[step_key]}...")

        def task():
            try:
                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step2":
                    outline = self._step_results.get("step1", "")
                    result = generate_world_building(outline, genre, self._book_dir,
                                                     log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step3":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    result = generate_characters(outline, world, genre, self._book_dir,
                                                 log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step4":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    result = generate_organizations(outline, world, chars, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step5":
                    outline = self._step_results.get("step1", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    result = generate_relationships(outline, chars, orgs, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step6":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    rels = self._step_results.get("step5", "")
                    combined = f"{outline[:2000]}\n\n{world[:1500]}\n\n{chars[:1500]}\n\n{orgs[:1000]}\n\n{rels[:1000]}"
                    result = generate_directory(combined, num_ch, self._book_dir,
                                                log_callback=lambda m: self._log(self._create_log, m))
                    # Parse chapters
                    self._chapters_list = _parse_directory(result, num_ch) if callable(eval("_parse_directory")) else []
                elif step_key == "step7":
                    self.root.after(0, lambda: self._start_chapter_generation())
                    self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
                    return

                self._step_results[step_key] = result
                self.root.after(0, lambda: self._show_result(step_key, result))
            except Exception as e:
                self.root.after(0, lambda: self._log(self._create_log, f"生成失败: {e}"))
                self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
                self.root.after(0, lambda: self._stop_btn.configure(state="disabled"))

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _show_result(self, step_key, result):
        self._create_editor.delete("1.0", "end")
        self._create_editor.insert("1.0", result)
        self._step_btn.configure(state="normal", text="AI 生成")
        self._stop_btn.configure(state="disabled")
        self._log(self._create_log, f"{self._step_names[step_key]} 完成 ✓ — 可在右侧编辑区修改，确认后点「确认→下一步」")
        self._show_step_panel(step_key)

    def _on_confirm_step(self):
        """确认当前步骤，保存编辑内容，进入下一步"""
        current = self._current_step
        # Save edited content
        edited = self._create_editor.get("1.0", "end-1c").strip()
        if edited:
            self._step_results[current] = edited
            # Also save to file
            file_map = {
                "step1": "大纲.md", "step2": "世界观.md", "step3": "人物设定.md",
                "step4": "组织设定.md", "step5": "关系图谱.md", "step6": "目录.md",
            }
            if current in file_map and self._book_dir:
                write_file(os.path.join(self._book_dir, file_map[current]), edited)

        # Go to next step
        idx = self._step_keys.index(current)
        if idx < 6:
            next_step = self._step_keys[idx + 1]
            self._show_step_panel(next_step)
            self._log(self._create_log, f"→ 进入: {self._step_names[next_step]}")
        else:
            self._log(self._create_log, "所有设定步骤完成！点击「AI 生成」开始逐章写正文")
            self._show_step_panel("step7")

    def _start_chapter_generation(self):
        """Step 7: 开始逐章生成正文"""
        topic = self._topic_var.get().strip()
        genre = self._genre_var.get()
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000

        if not self._book_dir:
            self._log(self._create_log, "错误: 未创建书籍目录")
            return

        self._save_novel_cfg()
        self._log(self._create_log, "开始逐章生成正文...")
        self._step_btn.configure(state="disabled")

        def task():
            chapters = self._chapters_list if hasattr(self, '_chapters_list') and self._chapters_list else []
            result = generate_novel(
                topic, genre, num_ch, wc, self._book_dir,
                log_callback=lambda m: self._log(self._create_log, m),
                stop_flag=self.stop_flag)
            self.root.after(0, lambda: self._on_novel_done(result))

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _on_novel_done(self, result):
        self._step_btn.configure(state="normal", text="AI 生成")
        status = result.get("status", "完成")
        words = result.get("total_words", 0)
        self._log(self._create_log, f"写书{status} | 共{words:,}字 | 目录: {self._book_dir}")

    def _get_novel_config(self):
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000
        return {
            "topic": self._topic_var.get().strip(),
            "genre": self._genre_var.get(),
            "num_chapters": num_ch,
            "words_per_chapter": wc,
        }

    def _save_novel_cfg(self):
        from core import load_config, save_config
        cfg = load_config()
        cfg["novel"] = self._get_novel_config()
        save_config()

    def _toggle_pause(self):
        if self.pause_flag.is_set():
            self.pause_flag.clear()
            self._pause_btn.configure(text="暂停")
        else:
            self.pause_flag.set()
            self._pause_btn.configure(text="继续")

    def _stop(self):
        self.stop_flag.set()
        self._stop_btn.configure(state="disabled")
        self._step_btn.configure(state="normal", text="AI 生成")
        self._log(self._create_log, "已停止")

    def _init_progress(self, total_chapters):
        self.progress["total_chapters"] = total_chapters
        self.progress["current_chapter"] = 0
        self.progress["chapter_words"] = 0
        self.progress["elapsed_seconds"] = 0
        self.progress["status"] = "running"
        self._progress_bar.set(0)

    def _update_dashboard(self):
        p = self.progress
        cur = p.get("current_chapter", 0)
        total = p.get("total_chapters", 0)
        w = p.get("chapter_words", 0)
        elapsed = p.get("elapsed_seconds", 0)
        if cur > 0 and elapsed > 0:
            speed = round(w * cur / elapsed)
            eta_sec = (total - cur) * (elapsed / cur) if cur > 0 else 0
            eta = f"{int(eta_sec // 60)}分{int(eta_sec % 60)}秒" if eta_sec > 0 else "—"
        else:
            speed = "—"
            eta = "—"
        self._dash_labels["progress"].configure(text=f"{cur} / {total} 章")
        self._dash_labels["words"].configure(text=f"{w * cur:,} 字")
        self._dash_labels["speed"].configure(text=f"{speed}" if isinstance(speed, str) else f"{speed} 字/秒")
        self._dash_labels["eta"].configure(text=eta)
        if cur > 0 and total > 0:
            self._progress_bar.set(cur / total)

    def _log_progress(self, msg):
        self._create_progress.configure(state="normal")
        self._create_progress.insert("end", msg + "\n")
        self._create_progress.see("end")
        self._create_progress.configure(state="disabled")

    def _on_novel_progress(self, data):
        self.progress.update(data)
        self.root.after(0, self._update_dashboard)

    def _browse_outline(self):
        f = filedialog.askopenfilename(filetypes=[("Markdown", "*.md"), ("Text", "*.txt")])
        if f:
            text = read_file(f)
            if text:
                self._create_editor.delete("1.0", "end")
                self._create_editor.insert("1.0", text)
                self._log(self._create_log, f"已加载: {f}")

    def _run_continue(self):
        d = self._book_dir
        if not d or not os.path.isdir(d):
            self._log(self._create_log, "请先生成至少一次")
            return
        self._log(self._create_log, "开始续写...")
        self._step_btn.configure(state="disabled")
        def task():
            try:
                result = continue_novel(d, additional_chapters=10,
                                        log_callback=lambda m: self._log(self._create_log, m),
                                        stop_flag=self.stop_flag)
                self.root.after(0, lambda: self._log(self._create_log, f"续写完成: {result.get('chapters_added', 0)}章"))
            except Exception as e:
                self.root.after(0, lambda: self._log(self._create_log, f"续写失败: {e}"))
            self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _toggle_outline_mode(self):
        pass  # 已整合到手动流程中
