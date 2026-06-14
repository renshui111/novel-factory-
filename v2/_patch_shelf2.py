with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Enhance row2 to show platform/author
old_row2_end = '''            ctk.CTkLabel(row2, text=f"更新: {proj.get('last_update','-')[:10]}",
                         font=("Segoe UI", 10), text_color=PH).pack(side="right")'''

# Read metadata for platform/author display
new_row2_end = '''            # Show platform/author if available
            path = proj.get("path", "")
            if path:
                try:
                    import json
                    mp = os.path.join(path, "项目元数据.json")
                    if os.path.exists(mp):
                        bm = json.loads(open(mp, "r", encoding="utf-8").read())
                        platform = bm.get("platform", "")
                        author = bm.get("author", "")
                        extra_info = []
                        if platform:
                            extra_info.append(platform)
                        if author:
                            extra_info.append(f"@{author}")
                        if extra_info:
                            ctk.CTkLabel(row2, text=" | ".join(extra_info),
                                         font=("Microsoft YaHei", 9), text_color=ACCENT_LIGHT).pack(side="left", padx=10)
                except Exception:
                    pass

            ctk.CTkLabel(row2, text=f"更新: {proj.get('last_update','-')[:10]}",
                         font=("Segoe UI", 10), text_color=PH).pack(side="right")'''

# Add Obsidian button in row3
old_row3_end = '''            ctk.CTkButton(row3, text="删除", width=55, height=30,
                          fg_color="transparent", text_color=RED, corner_radius=6,
                          font=("Microsoft YaHei", 10),
                          command=lambda p=book_path: self._delete_project(p)).pack(side="right", padx=2)'''

new_row3_end = '''            ctk.CTkButton(row3, text="Obsidian", width=65, height=30,
                          fg_color="#7c4dff", text_color="white", corner_radius=6,
                          font=("Microsoft YaHei", 10),
                          command=lambda p=book_path: self._open_in_obsidian(p)).pack(side="right", padx=2)

            ctk.CTkButton(row3, text="删除", width=55, height=30,
                          fg_color="transparent", text_color=RED, corner_radius=6,
                          font=("Microsoft YaHei", 10),
                          command=lambda p=book_path: self._delete_project(p)).pack(side="right", padx=2)'''

if old_row2_end in content:
    content = content.replace(old_row2_end, new_row2_end)
    print("Row2 updated")
else:
    print("Row2 pattern not found")

if old_row3_end in content:
    content = content.replace(old_row3_end, new_row3_end)
    print("Row3 updated")
else:
    print("Row3 pattern not found")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
