with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# ── 1. Replace color palette with shadcn-inspired design system ──
old_colors = '''BG = "#111318"
SB = "#181b23"
CARD = "#1f2230"
CARD_HOVER = "#292d3d"
ACCENT = "#f0a040"
ACCENT_HOVER = "#f5b860"
ACCENT_LIGHT = "#f8d090"
BLUE = "#5b9bd5"
GREEN = "#6bba62"
ORANGE = "#e8913a"
RED = "#e05555"
TEXT = "#e2e4e9"
TEXT_DIM = "#8a8f9a"
PH = "#5a5f6b"
BORDER = "#2a2d38"'''

new_colors = '''# ── shadcn/ui inspired dark design system ──
BG = "#09090b"          # 页面背景 - 极深
SB = "#0d0d12"          # 侧栏背景
CARD = "#13131a"        # 卡片背景
CARD_HOVER = "#1a1a24"  # 卡片悬停
BORDER = "#1e1e2a"      # 边框/分割线
ACCENT = "#3b82f6"      # 主色调 - 清爽蓝
ACCENT_HOVER = "#2563eb" # 主色悬停
ACCENT_LIGHT = "#93c5fd" # 主色浅色
BLUE = "#60a5fa"        # 次要蓝
GREEN = "#22c55e"       # 成功绿
ORANGE = "#f59e0b"      # 警告橙
RED = "#ef4444"         # 危险红
TEXT = "#fafafa"        # 主文字 - 近白
TEXT_DIM = "#a1a1aa"    # 次要文字
PH = "#52525b"          # 占位/更淡文字
# Card border style
CARD_BORDER = 1         # card border width
CARD_RADIUS = 10        # card corner radius'''

content = content.replace(old_colors, new_colors)
print("1. Colors updated")

# ── 2. Upgrade window title and appearance ──
old_title = '''self.root.title("写书工坊 — AI Writing Studio")
        self.root.geometry("1250x800")
        self.root.minsize(1000, 650)'''
new_title = '''self.root.title("小说工厂 NovelFactory")
        self.root.geometry("1320x850")
        self.root.minsize(1050, 680)'''
content = content.replace(old_title, new_title)
print("2. Window upgraded")

# ── 3. Sidebar width upgrade ──
old_sb = "self.sb = ctk.CTkFrame(self.root, width=170, fg_color=SB, corner_radius=0)"
new_sb = "self.sb = ctk.CTkFrame(self.root, width=185, fg_color=SB, corner_radius=0)"
content = content.replace(old_sb, new_sb)
print("3. Sidebar wider")

# ── 4. Logo area prettier ──
old_logo = '''        ctk.CTkLabel(logo_frame, text="\\u270d",
                     font=("Segoe UI Emoji", 28)).pack(side="left", padx=(2,8))
        ctk.CTkLabel(logo_frame, text="\\u5199\\u4f5c\\u5de5\\u574a",
                     font=("Microsoft YaHei", 17, "bold"),
                     text_color=ACCENT).pack(side="left")'''
new_logo = '''        ctk.CTkLabel(logo_frame, text="📖",
                     font=("Segoe UI Emoji", 24)).pack(side="left", padx=(2,6))
        ctk.CTkLabel(logo_frame, text="小说工厂",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(side="left")'''
content = content.replace(old_logo, new_logo)
print("4. Logo updated")

# ── 5. Nav buttons with icons ──
old_nav = '''        items = [
            ("bookshelf", "  仪表盘"),
            ("create",    "  写书"),
            ("editor",    "  编辑器"),
            ("analyze",   "  拆书"),
            ("reverse",   "  逆向工程"),
            ("reader",    "  读者模拟"),
            ("download",  "  下载"),
            ("settings",  "  设置"),
        ]'''
new_nav = '''        items = [
            ("bookshelf", "  📊 仪表盘"),
            ("create",    "  ✍️ 写书"),
            ("editor",    "  📝 编辑器"),
            ("analyze",   "  🔍 拆书"),
            ("reverse",   "  🧬 逆向工程"),
            ("reader",    "  👥 读者模拟"),
            ("download",  "  📥 下载"),
            ("settings",  "  ⚙️ 设置"),
        ]'''
content = content.replace(old_nav, new_nav)
print("5. Nav with icons")

# ── 6. Nav button styling upgraded ──
old_nav_btn = '''            btn = ctk.CTkButton(
                self.sb, text=label,
                font=("Microsoft YaHei", 13),
                fg_color="transparent", text_color=TEXT_DIM,
                hover_color=CARD_HOVER, anchor="w", height=38, corner_radius=6,
                border_spacing=0,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=8, pady=1)'''
new_nav_btn = '''            btn = ctk.CTkButton(
                self.sb, text=label,
                font=("Microsoft YaHei", 12),
                fg_color="transparent", text_color=TEXT_DIM,
                hover_color=CARD_HOVER, anchor="w", height=36, corner_radius=8,
                border_spacing=6,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=6, pady=1)'''
content = content.replace(old_nav_btn, new_nav_btn)
print("6. Nav buttons refined")

# ── 7. Section header style ──
old_sect = '''        ctk.CTkLabel(header_frame, text=title,
                     font=("Segoe UI", 10),
                     text_color=PH, anchor="w").pack(side="left")'''
new_sect = '''        ctk.CTkLabel(header_frame, text=title,
                     font=("Microsoft YaHei", 10, "bold"),
                     text_color=TEXT_DIM, anchor="w").pack(side="left")'''
content = content.replace(old_sect, new_sect)
print("7. Section headers improved")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("All done")
