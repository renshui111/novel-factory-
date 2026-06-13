with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find _show_step_panel and add extra requirements section after the info Textbox
# Look for the pattern: info.configure(state="disabled") followed by the "Show existing result" block
old_section = '''        info.configure(state="disabled")

        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:
            self._create_editor.delete("1.0", "end")
            self._create_editor.insert("1.0", self._step_results[step_key])
            ctk.CTkButton(self._step_panel, text="重新生成",
                          command=lambda: self._ai_generate_step(step_key),
                          fg_color=ORANGE, width=100).pack(pady=8, padx=15)
        else:
            if step_key != "step1":
                self._create_editor.delete("1.0", "end")'''

new_section = '''        info.configure(state="disabled")

        # ── Extra requirements input (steps 1-5) ──
        if step_key in ["step1", "step2", "step3", "step4", "step5"]:
            # Style presets
            ctk.CTkLabel(self._step_panel, text="风格预设：",
                         font=("Microsoft YaHei", 10), text_color=PH).pack(anchor="w", padx=15, pady=(10, 2))
            pf = ctk.CTkFrame(self._step_panel, fg_color="transparent")
            pf.pack(fill="x", padx=12, pady=(0, 4))
            for i, (name, desc) in enumerate(self._style_presets.items()):
                ctk.CTkButton(pf, text=name, width=50, height=22,
                              font=("Microsoft YaHei", 9),
                              fg_color=CARD_HOVER, text_color=TEXT_DIM,
                              command=lambda n=name, d=desc: self._apply_style_preset(n, d)
                              ).pack(side="left", padx=1)

            # Extra requirements text area
            ctk.CTkLabel(self._step_panel, text="额外要求（引导AI生成方向）：",
                         font=("Microsoft YaHei", 10, "bold"), text_color=ACCENT_LIGHT).pack(anchor="w", padx=15, pady=(6, 2))
            
            placeholders = {
                "step1": "例如：要有反转剧情、主角一开始是废柴、加入师门试炼、前3章必须出现金手指",
                "step2": "例如：修真体系分9境、有魔族入侵背景、宗门分上中下三等、灵石是硬通货",
                "step3": "例如：主角性格冷傲但重情义、需要一个逗比跟班、反派是伪君子类型、加入一个女性强者",
                "step4": "例如：三大宗门互相制衡、有一个隐藏的幕后组织、正邪两道各有内斗",
                "step5": "例如：主角和女二是青梅竹马、师门内部有叛徒、正邪两道暗中有交易",
            }
            ph = placeholders.get(step_key, "输入你的具体要求...")
            
            self._extra_req_text = ctk.CTkTextbox(self._step_panel, height=80,
                                                   font=("Microsoft YaHei", 10),
                                                   fg_color=CARD, text_color=TEXT, wrap="word")
            self._extra_req_text.pack(fill="x", padx=12, pady=(0, 6))
            # Restore saved extra requirements
            saved_extra = self._step_extra.get(step_key, "")
            if saved_extra:
                self._extra_req_text.insert("1.0", saved_extra)
            else:
                self._extra_req_text.insert("1.0", ph)
            self._extra_req_text.bind("<FocusIn>", lambda e: self._on_extra_focus_in(ph))
            self._extra_req_text.bind("<FocusOut>", lambda e: self._on_extra_focus_out(ph))

        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:
            self._create_editor.delete("1.0", "end")
            self._create_editor.insert("1.0", self._step_results[step_key])
            ctk.CTkButton(self._step_panel, text="重新生成",
                          command=lambda: self._ai_generate_step(step_key),
                          fg_color=ORANGE, width=100).pack(pady=8, padx=15)
        else:
            if step_key != "step1":
                self._create_editor.delete("1.0", "end")'''

if old_section in content:
    content = content.replace(old_section, new_section)
    print("Show_step_panel updated")
else:
    print("Pattern not found - searching...")
    # Try without the extra indentation on the else clause
    if "info.configure(state=\"disabled\")" in content:
        print("info.configure found at index:", content.index("info.configure(state=\"disabled\")"))
    else:
        print("info.configure NOT found")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
