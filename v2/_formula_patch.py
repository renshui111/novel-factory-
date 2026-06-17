with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find _build_create and add a "参考已拆书籍" button in step1 panel
# Look for the step1 description area
old_step1_desc = '''        descriptions = {
            "step1": "输入主题后点击「AI 生成」，AI 将生成完整的小说大纲，\\n包括分卷结构、每章概要、高潮节点、爽点分布。\\n生成后可在右侧编辑区修改。",'''

new_step1_desc = '''        descriptions = {
            "step1": "输入主题后点击「AI 生成」，AI 将生成完整的小说大纲，\\n包括分卷结构、每章概要、高潮节点、爽点分布。\\n生成后可在右侧编辑区修改。\\n\\n可点击「导入拆书公式」将已拆书籍的节奏/爽点/钩子\\n技法注入大纲生成。",'''

content = content.replace(old_step1_desc, new_step1_desc)

# Add import拆书公式 button in _show_step_panel for step1
old_info_step1 = '''            "step1": "大纲会保存在「大纲.md」\\n后续步骤依赖大纲内容",'''
new_info_step1 = '''            "step1": "大纲会保存在「大纲.md」\\n后续步骤依赖大纲内容\\n\\n可导入拆书公式增强生成",'''
content = content.replace(old_info_step1, new_info_step1)

# Add button after the info textbox for step1
old_show_existing = '''        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:'''
new_show_existing = '''        # Step1: add import formula button
        if step_key == "step1":
            ctk.CTkButton(self._step_panel, text="导入拆书公式",
                          command=self._import_analyze_formula,
                          fg_color=PURPLE, hover_color="#7c3aed",
                          width=140, height=28,
                          font=("Microsoft YaHei", 11)).pack(pady=4, padx=15)
            self._formula_ref = ""  # Store imported formula text

        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:'''
content = content.replace(old_show_existing, new_show_existing)

# Add the _import_analyze_formula method before _ai_generate_step
old_gen = "    def _ai_generate_step(self, step_key):"
new_gen = '''    def _import_analyze_formula(self):
        """从已拆书籍导入写作公式，注入大纲生成"""
        from project import get_output_dir
        output_dir = get_output_dir()
        # Find projects with analyze data
        import os
        candidates = []
        if os.path.isdir(output_dir):
            for name in os.listdir(output_dir):
                path = os.path.join(output_dir, name)
                rep_file = os.path.join(path, "可复制公式.md")
                if os.path.isfile(rep_file):
                    candidates.append((name, path, rep_file))
        
        if not candidates:
            # Also check for reverse_engineer results
            for name in os.listdir(output_dir):
                path = os.path.join(output_dir, name)
                if os.path.isdir(path):
                    for fname in os.listdir(path):
                        if "公式" in fname or "template" in fname.lower() or "formula" in fname.lower():
                            candidates.append((name, path, os.path.join(path, fname)))
        
        if not candidates:
            self._log(self._create_log, "未找到已拆书籍的公式文件。请先在「拆书」或「逆向工程」中分析一本书。")
            return
        
        # Show selection dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("选择参考书籍")
        dialog.geometry("400x350")
        dialog.configure(fg_color=BG)
        
        ctk.CTkLabel(dialog, text="选择一本已拆书籍的写作公式：",
                     font=("Microsoft YaHei", 13, "bold"), text_color=TEXT).pack(pady=10)
        
        for name, path, rep_file in candidates:
            def make_cb(n, f):
                def cb():
                    from core import read_file
                    formula = read_file(f)
                    self._formula_ref = formula[:2000]
                    self._log(self._create_log, f"已导入《{n}》的写作公式 ({len(formula)}字)")
                    self._log(self._create_log, "公式将在生成大纲时注入AI prompt")
                    dialog.destroy()
                return cb
            ctk.CTkButton(dialog, text=name, command=make_cb(name, rep_file),
                          fg_color=CARD, hover_color=CARD_HOVER, text_color=TEXT,
                          anchor="w", height=36).pack(fill="x", padx=20, pady=3)

    def _ai_generate_step(self, step_key):'''
content = content.replace(old_gen, new_gen)

# Modify step1 generation to inject formula
old_step1_gen = '''                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m),
                                              extra_requirements=extra)'''
new_step1_gen = '''                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    # If formula imported, append to extra requirements
                    formula = getattr(self, '_formula_ref', '')
                    if formula:
                        extra = (extra + "\\n\\n[参考写作公式]\\n" + formula) if extra else f"[参考写作公式]\\n{formula}"
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m),
                                              extra_requirements=extra)'''
content = content.replace(old_step1_gen, new_step1_gen)

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("GUI: analyze formula import added")
