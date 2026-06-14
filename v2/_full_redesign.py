import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

count = 0
def replace(old, new, label=""):
    global content, count
    if old in content:
        content = content.replace(old, new)
        count += 1
        if label:
            print(f"  OK {label}")
        return True
    else:
        print(f"  MISS: {label or old[:50]}")
        return False

print("=" * 50)
print("  小说工厂 UI 全面重设计")
print("=" * 50)

# 1. DESIGN TOKENS
print("\n1. Design tokens")
replace(
    "# ── shadcn/ui inspired dark design system ──\n"
    'BG = "#09090b"          # 页面背景 - 极深\n'
    'SB = "#0d0d12"          # 侧栏背景\n'
    'CARD = "#13131a"        # 卡片背景\n'
    'CARD_HOVER = "#1a1a24"  # 卡片悬停\n'
    'BORDER = "#1e1e2a"      # 边框/分割线\n'
    'ACCENT = "#3b82f6"      # 主色调 - 清爽蓝\n'
    'ACCENT_HOVER = "#2563eb" # 主色悬停\n'
    'ACCENT_LIGHT = "#93c5fd" # 主色浅色\n'
    'BLUE = "#60a5fa"        # 次要蓝\n'
    'GREEN = "#22c55e"       # 成功绿\n'
    'ORANGE = "#f59e0b"      # 警告橙\n'
    'RED = "#ef4444"         # 危险红\n'
    'TEXT = "#fafafa"        # 主文字 - 近白\n'
    'TEXT_DIM = "#a1a1aa"    # 次要文字\n'
    'PH = "#52525b"          # 占位/更淡文字\n'
    '# Card border style\n'
    'CARD_BORDER = 1         # card border width\n'
    'CARD_RADIUS = 10        # card corner radius',
    "# shadcn/ui dark design tokens\n"
    'BG          = "#09090b"\n'
    'SB          = "#0b0b10"\n'
    'CARD        = "#111115"\n'
    'CARD_HOVER  = "#18181f"\n'
    'BORDER      = "#1f1f2a"\n'
    'BORDER_LIGHT = "#27272f"\n'
    'ACCENT      = "#3b82f6"\n'
    'ACCENT_HOVER = "#2563eb"\n'
    'ACCENT_SOFT  = "#1e3a5f"\n'
    'BLUE        = "#60a5fa"\n'
    'PURPLE      = "#8b5cf6"\n'
    'GREEN       = "#22c55e"\n'
    'ORANGE      = "#f59e0b"\n'
    'RED         = "#ef4444"\n'
    'TEXT        = "#fafafa"\n'
    'TEXT_DIM    = "#a1a1aa"\n'
    'PH          = "#71717a"',
    "tokens"
)

# 2. Window
print("\n2. Window")
replace(
    'self.root.title("小说工厂 NovelFactory")\n        self.root.geometry("1320x850")\n        self.root.minsize(1050, 680)',
    'self.root.title("小说工厂")\n        self.root.geometry("1360x880")\n        self.root.minsize(1100, 700)',
    "window"
)

# 3. Sidebar width
replace(
    'self.sb = ctk.CTkFrame(self.root, width=185, fg_color=SB, corner_radius=0)',
    'self.sb = ctk.CTkFrame(self.root, width=200, fg_color=SB, corner_radius=0)',
    "sidebar width"
)

# 4. Logo
print("\n3. Logo")
replace(
    'ctk.CTkLabel(logo_frame, text="📖",\n                     font=("Segoe UI Emoji", 24)).pack(side="left", padx=(2,6))\n        ctk.CTkLabel(logo_frame, text="小说工厂",\n                     font=("Microsoft YaHei", 16, "bold"),\n                     text_color=ACCENT).pack(side="left")',
    'ctk.CTkLabel(logo_frame, text="📖",\n                     font=("Segoe UI Emoji", 22)).pack(side="left", padx=(2,8))\n        ctk.CTkLabel(logo_frame, text="小说工厂",\n                     font=("Microsoft YaHei", 17, "bold"),\n                     text_color=TEXT).pack(side="left")',
    "logo"
)

# 5. Nav with sections
print("\n4. Navigation")
old_nav = '        items = [\n            ("bookshelf", "  📊 仪表盘"),\n            ("create",    "  ✍️ 写书"),\n            ("editor",    "  📝 编辑器"),\n            ("analyze",   "  🔍 拆书"),\n            ("reverse",   "  🧬 逆向工程"),\n            ("reader",    "  👥 读者模拟"),\n            ("download",  "  📥 下载"),\n            ("settings",  "  ⚙️ 设置"),\n        ]'

new_nav = '        nav_sections = [\n            ("创作", [("bookshelf", "  📊 仪表盘"), ("create", "  ✍️ 写书"), ("editor", "  📝 编辑器")]),\n            ("分析", [("analyze", "  🔍 拆书"), ("reverse", "  🧬 逆向"), ("reader", "  👥 读者")]),\n            ("工具", [("download", "  📥 下载"), ("settings", "  ⚙️ 设置")]),\n        ]\n        items = []\n        first = True\n        for section_title, section_items in nav_sections:\n            sh = ctk.CTkLabel(self.sb, text=section_title,\n                              font=("Microsoft YaHei", 9, "bold"),\n                              text_color=PH, anchor="w")\n            sh.pack(fill="x", padx=18, pady=(12 if first else 10, 2))\n            first = False\n            for key, label in section_items:\n                items.append((key, label))'

if old_nav in content:
    content = content.replace(old_nav, new_nav)
    count += 1
    print("  OK nav sections")
else:
    print("  MISS nav")

# 6. Status bar
print("\n5. Status bar")
old_status = '        self.status_frame = ctk.CTkFrame(self.sb, fg_color=CARD, corner_radius=8)\n        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,\n                                         font=("Segoe UI", 8))\n        self.status_icon.pack(side="left", padx=(12, 6), pady=10)\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 10),\n                                         text_color=TEXT_DIM)\n        self.status_text.pack(side="left", padx=(0, 12), pady=10)'
new_status = '        bd2 = ctk.CTkFrame(self.sb, height=1, fg_color=BORDER)\n        bd2.pack(side="bottom", fill="x", padx=16)\n        self.status_frame = ctk.CTkFrame(self.sb, fg_color="transparent", height=36)\n        self.status_frame.pack(side="bottom", fill="x", padx=14, pady=(6, 10))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,\n                                         font=("Segoe UI", 7))\n        self.status_icon.pack(side="left", padx=(6, 6))\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 10),\n                                         text_color=PH)\n        self.status_text.pack(side="left")'
if old_status in content:
    content = content.replace(old_status, new_status)
    count += 1
    print("  OK status")
else:
    print("  MISS status")

# 7. Section header method
print("\n6. Section header")
old_sect = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=20, pady=(8, 0))\n        ctk.CTkLabel(header_frame, text="━",\n                     font=("Segoe UI Emoji", 8),\n                     text_color=ACCENT).pack(side="left", padx=(0, 8))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Microsoft YaHei", 10, "bold"),\n                     text_color=TEXT_DIM, anchor="w").pack(side="left")\n        # Divider line\n        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)\n        div.pack(fill="x", padx=20, pady=(4, 2))'
new_sect = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=20, pady=(12, 0))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Microsoft YaHei", 14, "bold"),\n                     text_color=TEXT, anchor="w").pack(side="left")\n        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)\n        div.pack(fill="x", padx=20, pady=(2, 8))'
if old_sect in content:
    content = content.replace(old_sect, new_sect)
    count += 1
    print("  OK section header")
else:
    print("  MISS section header")

# 8. Create page - top card
print("\n7. Create page")
replace(
    '        top = ctk.CTkFrame(p, fg_color=CARD)\n        top.pack(fill="x", padx=20, pady=3)',
    '        top = ctk.CTkFrame(p, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)\n        top.pack(fill="x", padx=20, pady=(0, 8))',
    "create top card"
)

# 9. Step frame
replace(
    '        self.step_frame = ctk.CTkFrame(p, fg_color=CARD)\n        self.step_frame.pack(fill="x", padx=20, pady=3)\n        sf = ctk.CTkFrame(self.step_frame, fg_color="transparent")\n        sf.pack(pady=8)',
    '        self.step_frame = ctk.CTkFrame(p, fg_color="transparent")\n        self.step_frame.pack(fill="x", padx=20, pady=(0, 4))\n        sf = ctk.CTkFrame(self.step_frame, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)\n        sf.pack(pady=0, fill="x")',
    "step frame card"
)

replace(
    '            sf2 = ctk.CTkFrame(sf, fg_color=CARD, corner_radius=8, border_width=1, border_color=BORDER)\n            sf2.pack(side="left", padx=2)\n            lbl = ctk.CTkLabel(sf2, text=f"{i+1}. {name}", font=("Microsoft YaHei", 10), text_color=PH)\n            lbl.pack(padx=8, pady=5)',
    '            sf2 = ctk.CTkFrame(sf, fg_color="transparent", corner_radius=6)\n            sf2.pack(side="left", padx=1)\n            lbl = ctk.CTkLabel(sf2, text=f"{i+1}.{name}", font=("Microsoft YaHei", 10), text_color=PH)\n            lbl.pack(padx=7, pady=6)',
    "step items"
)

replace(
    'ctk.CTkLabel(sf, text="›", font=("Segoe UI", 16, "bold"), text_color=PH).pack(side="left", padx=0)',
    'ctk.CTkLabel(sf, text="·", font=("Segoe UI", 14, "bold"), text_color=BORDER).pack(side="left", padx=0)',
    "step divider"
)

# 10. Create mid area
replace(
    '        mid = ctk.CTkFrame(p, fg_color=BG)\n        mid.pack(fill="both", expand=True, padx=20, pady=3)',
    '        mid = ctk.CTkFrame(p, fg_color="transparent")\n        mid.pack(fill="both", expand=True, padx=20, pady=(4, 0))',
    "mid area"
)

replace(
    '        self._step_panel = ctk.CTkFrame(mid, fg_color=CARD, width=360, corner_radius=10)\n        self._step_panel.pack(side="left", fill="y", padx=(0, 5))\n        self._step_panel.pack_propagate(False)',
    '        self._step_panel = ctk.CTkFrame(mid, fg_color=CARD, width=340, corner_radius=10, border_width=1, border_color=BORDER)\n        self._step_panel.pack(side="left", fill="y", padx=(0, 8))\n        self._step_panel.pack_propagate(False)',
    "step panel card"
)

replace(
    '        right = ctk.CTkFrame(mid, fg_color=BG)\n        right.pack(side="right", fill="both", expand=True)',
    '        right = ctk.CTkFrame(mid, fg_color="transparent")\n        right.pack(side="right", fill="both", expand=True)',
    "right area"
)

# 11. Reader page — fix segmented button labels
print("\n8. Reader tabs")
content = content.replace('"single"', '"单章分析"')
content = content.replace('"fullbook"', '"全书分析"')
content = content.replace('values=["single", "fullbook"]', 'values=["单章分析", "全书分析"]')
print("  OK reader tabs")

# 12. Global fixes
print("\n9. Global fixes")
content = content.replace('fg_color="#555"', 'fg_color="#3f3f46"')
content = content.replace('fg_color="#666"', 'fg_color="#52525b"')
content = content.replace('fg_color="#9c27b0"', 'fg_color=PURPLE')
# Remove double borders
content = content.replace('border_width=1, border_color=BORDER, corner_radius=10, border_width=1, border_color=BORDER',
                         'border_width=1, border_color=BORDER, corner_radius=10')
content = content.replace('border_width=1, border_color=BORDER, border_width=1, border_color=BORDER',
                         'border_width=1, border_color=BORDER')
print("  OK global fixes")

print(f"\n{'='*50}")
print(f"  Total: {count} changes applied")
print(f"{'='*50}")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
