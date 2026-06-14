import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

count = 0

# Fix logo
old = 'ctk.CTkLabel(logo_frame, text="✍",\n                     font=("Segoe UI Emoji", 28)).pack(side="left", padx=(2,8))\n        ctk.CTkLabel(logo_frame, text="写作工坊",\n                     font=("Microsoft YaHei", 17, "bold"),\n                     text_color=ACCENT).pack(side="left")'
new = 'ctk.CTkLabel(logo_frame, text="📖",\n                     font=("Segoe UI Emoji", 22)).pack(side="left", padx=(2,8))\n        ctk.CTkLabel(logo_frame, text="小说工厂",\n                     font=("Microsoft YaHei", 17, "bold"),\n                     text_color=TEXT).pack(side="left")'
if old in content:
    content = content.replace(old, new)
    count += 1
    print("OK logo")
else:
    print("MISS logo")

# Fix status bar
old = '        self.status_frame = ctk.CTkFrame(self.sb, fg_color=CARD_HOVER, corner_radius=6)\n        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 12))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="o", text_color=GREEN,\n                                         font=("Microsoft YaHei", 11))\n        self.status_icon.pack(side="left", padx=(12, 6), pady=8)\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 11),\n                                         text_color=TEXT_DIM)\n        self.status_text.pack(side="left", padx=(0, 12), pady=8)'
new = '        bd2 = ctk.CTkFrame(self.sb, height=1, fg_color=BORDER)\n        bd2.pack(side="bottom", fill="x", padx=16)\n        self.status_frame = ctk.CTkFrame(self.sb, fg_color="transparent", height=36)\n        self.status_frame.pack(side="bottom", fill="x", padx=14, pady=(6, 10))\n        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,\n                                         font=("Segoe UI", 7))\n        self.status_icon.pack(side="left", padx=(6, 6))\n        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",\n                                         font=("Microsoft YaHei", 10),\n                                         text_color=PH)\n        self.status_text.pack(side="left")'
if old in content:
    content = content.replace(old, new)
    count += 1
    print("OK status")
else:
    print("MISS status")

# Fix section header
old = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=14, pady=(8, 0))\n        ctk.CTkLabel(header_frame, text="━",\n                     font=("Segoe UI Emoji", 8),\n                     text_color=ACCENT).pack(side="left", padx=(0, 8))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Segoe UI", 10),\n                     text_color=PH, anchor="w").pack(side="left")\n        # Divider line\n        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)\n        div.pack(fill="x", padx=14, pady=(4, 2))'
new = '    def _sect(self, parent, title):\n        header_frame = ctk.CTkFrame(parent, fg_color="transparent")\n        header_frame.pack(fill="x", padx=20, pady=(12, 0))\n        ctk.CTkLabel(header_frame, text=title,\n                     font=("Microsoft YaHei", 14, "bold"),\n                     text_color=TEXT, anchor="w").pack(side="left")\n        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)\n        div.pack(fill="x", padx=20, pady=(2, 8))'
if old in content:
    content = content.replace(old, new)
    count += 1
    print("OK section")
else:
    print("MISS section")
    # Show what's there
    idx = content.find("def _sect(self, parent, title):")
    if idx >= 0:
        print(content[idx:idx+500])

print(f"\nFixed: {count}")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
