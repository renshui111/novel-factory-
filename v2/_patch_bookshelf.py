with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find _render_project_list and enhance it to show platform/author
old_render = '''    def _render_project_list(self, projects):
        """渲染书架项目列表"""
        for w in self._shelf_list.winfo_children():
            w.destroy()

        if not projects:
            ctk.CTkLabel(self._shelf_list, text="暂无项目",
                         font=("Microsoft YaHei", 13), text_color=PH).pack(pady=20)
            return'''

new_render = '''    def _render_project_list(self, projects):
        """渲染书架项目列表（含平台/作者信息）"""
        for w in self._shelf_list.winfo_children():
            w.destroy()

        if not projects:
            ctk.CTkLabel(self._shelf_list, text="暂无项目",
                         font=("Microsoft YaHei", 13), text_color=PH).pack(pady=20)
            return

        # Read metadata for each project to get platform/author
        for proj in projects:
            path = proj.get("path", "")
            meta = {}
            meta_path = os.path.join(path, "项目元数据.json") if path else ""
            if meta_path and os.path.exists(meta_path):
                try:
                    import json
                    meta = json.loads(open(meta_path, "r", encoding="utf-8").read())
                except Exception:
                    pass

            platform = meta.get("platform", "")
            author = meta.get("author", "")
            source_url = meta.get("source_url", "")

            row = ctk.CTkFrame(self._shelf_list, fg_color=CARD, corner_radius=6)
            row.pack(fill="x", padx=2, pady=2)

            # Left: title + meta
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            # Title row
            title_row = ctk.CTkFrame(left, fg_color="transparent")
            title_row.pack(fill="x")
            ctk.CTkLabel(title_row, text=proj.get("topic", proj["name"]),
                         font=("Microsoft YaHei", 13, "bold"), text_color=TEXT).pack(side="left")

            # Platform badge
            if platform:
                badge_colors = {"番茄小说": RED, "起点中文网": BLUE, "纵横中文网": ORANGE}
                bc = badge_colors.get(platform, CARD_HOVER)
                ctk.CTkLabel(title_row, text=f" {platform} ",
                             font=("Microsoft YaHei", 9), text_color=bc,
                             fg_color=CARD_HOVER, corner_radius=3).pack(side="left", padx=6)

            # Info row
            info_text = f"{proj.get('genre', '')} | {proj.get('chapters', 0)}章 | {proj.get('words', 0):,}字"
            if author:
                info_text = f"作者: {author} | " + info_text
            ctk.CTkLabel(left, text=info_text,
                         font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(anchor="w")

            # Right: action buttons
            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=8, pady=6)
            ctk.CTkButton(right, text="续写", command=lambda p=path: self._quick_continue(p),
                          fg_color=ACCENT, width=50, height=26).pack(side="left", padx=2)
            ctk.CTkButton(right, text="Obsidian",
                          command=lambda p=path: self._open_in_obsidian(p),
                          fg_color="#7c4dff", width=65, height=26).pack(side="left", padx=2)
            ctk.CTkButton(right, text="导出", command=lambda p=path: self._quick_export(p),
                          fg_color=BLUE, width=50, height=26).pack(side="left", padx=2)
            ctk.CTkButton(right, text="删除", command=lambda p=path: self._delete_project(p),
                          fg_color="#555", width=50, height=26).pack(side="left", padx=2)'''

if old_render in content:
    content = content.replace(old_render, new_render)
    print("Bookshelf enhanced with platform/author/Obsidian")
else:
    print("Pattern not found - searching...")
    idx = content.find("def _render_project_list")
    if idx >= 0:
        print("Found at", idx)
        print(content[idx:idx+300])

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
