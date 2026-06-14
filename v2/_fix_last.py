import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

count = 0

# Fix status bar
old = '        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 12))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="o", text_color=GREEN,\n                                         font=("Microsoft YaHei", 11))\n        self.status_icon.pack(side="left", padx=(12, 6), pady=8)\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 11), text_color=TEXT_DIM)\n        self.status_text.pack(side="left", padx=(0, 12), pady=8)'
new = '        self.status_frame.pack(side="bottom", fill="x", padx=14, pady=(0, 10))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,\n                                         font=("Segoe UI", 7))\n        self.status_icon.pack(side="left", padx=(6, 6), pady=10)\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 10), text_color=PH)\n        self.status_text.pack(side="left", pady=10)'
if old in content:
    content = content.replace(old, new)
    count += 1
    print("OK status")
else:
    print("MISS status")

# Fix section header method
old = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=20, pady=(15, 5))\n        # Accent dot\n        ctk.CTkLabel(header_frame, text="●", text_color=ACCENT,\n                     font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Microsoft YaHei", 16, "bold"),\n                     text_color=ACCENT,\n                     anchor="w").pack(side="left")\n        # Divider line\n        ctk.CTkLabel(parent, text="",\n                     fg_color=BORDER, height=1,\n                     corner_radius=0).pack(fill="x", padx=20, pady=(0, 8))'
new = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=20, pady=(12, 0))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Microsoft YaHei", 14, "bold"),\n                     text_color=TEXT, anchor="w").pack(side="left")\n        # Subtle divider\n        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)\n        div.pack(fill="x", padx=20, pady=(2, 8))'
if old in content:
    content = content.replace(old, new)
    count += 1
    print("OK section header")
else:
    print("MISS section header")
    # Show actual
    idx = content.find("def _sect(self, parent, title):")
    if idx >= 0:
        print("Actual:", repr(content[idx:idx+400]))

# Also fix status frame creation
old2 = '        self.status_frame = ctk.CTkFrame(self.sb, fg_color=CARD_HOVER, corner_radius=6)'
new2 = '        self.status_frame = ctk.CTkFrame(self.sb, fg_color="transparent")'
if old2 in content:
    content = content.replace(old2, new2)
    count += 1
    print("OK status frame")
else:
    print("MISS status frame")

print(f"\nFixed: {count}")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
