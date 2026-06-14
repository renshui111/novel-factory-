with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# ── 8. Button hover states for all primary buttons ──
# Add hover_color to all ACCENT buttons
content = content.replace('fg_color=ACCENT, font=("Microsoft YaHei", 13), width=140',
                         'fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Microsoft YaHei", 13), width=140')
content = content.replace('fg_color=ACCENT, font=("Microsoft YaHei", 14, "bold")',
                         'fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Microsoft YaHei", 14, "bold")')
content = content.replace('fg_color=BLUE, width=110).pack',
                         'fg_color=BLUE, hover_color="#3b82f6", width=110).pack')
content = content.replace('fg_color=BLUE, width=120).pack',
                         'fg_color=BLUE, hover_color="#3b82f6", width=120).pack')
content = content.replace('fg_color=BLUE, width=140).pack',
                         'fg_color=BLUE, hover_color="#3b82f6", width=140).pack')

# ── 9. Status bar prettier ──
old_status = '''        self.status_frame = ctk.CTkFrame(self.sb, fg_color=CARD_HOVER, corner_radius=6)
        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 12))
        self.status_icon = ctk.CTkLabel(self.status_frame, text="o", text_color=GREEN,
                                         font=("Microsoft YaHei", 11))
        self.status_icon.pack(side="left", padx=(12, 6), pady=8)
        self.status_text = ctk.CTkLabel(self.status_frame, text="\\u5c31\\u7eea",
                                         font=("Microsoft YaHei", 11),
                                         text_color=TEXT_DIM)
        self.status_text.pack(side="left", padx=(0, 12), pady=8)'''
new_status = '''        self.status_frame = ctk.CTkFrame(self.sb, fg_color=CARD, corner_radius=8)
        self.status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,
                                         font=("Segoe UI", 8))
        self.status_icon.pack(side="left", padx=(12, 6), pady=10)
        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",
                                         font=("Microsoft YaHei", 10),
                                         text_color=TEXT_DIM)
        self.status_text.pack(side="left", padx=(0, 12), pady=10)'''
content = content.replace(old_status, new_status)
print("9. Status bar refined")

# ── 10. Card borders - add border_width to CARD frames ──
# Cards should look more defined with subtle borders
content = content.replace('fg_color=CARD, corner_radius=10', 'fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER')
content = content.replace('fg_color=CARD, corner_radius=8', 'fg_color=CARD, corner_radius=8, border_width=1, border_color=BORDER')
# Fix double border on the above
content = content.replace('border_width=1, border_color=BORDER, corner_radius=10, border_width=1, border_color=BORDER',
                         'border_width=1, border_color=BORDER, corner_radius=10')
content = content.replace('border_width=1, border_color=BORDER, corner_radius=8, border_width=1, border_color=BORDER',
                         'border_width=1, border_color=BORDER, corner_radius=8')
print("10. Cards with borders")

# ── 11. Step indicator refinement ──
old_step = '''            sf2 = ctk.CTkFrame(sf, fg_color=CARD_HOVER, corner_radius=6)
            sf2.pack(side="left", padx=2)
            lbl = ctk.CTkLabel(sf2, text=f"{i+1}. {name}", font=("Microsoft YaHei", 10), text_color=PH)
            lbl.pack(padx=6, pady=4)'''
new_step = '''            sf2 = ctk.CTkFrame(sf, fg_color=CARD, corner_radius=8, border_width=1, border_color=BORDER)
            sf2.pack(side="left", padx=2)
            lbl = ctk.CTkLabel(sf2, text=f"{i+1}. {name}", font=("Microsoft YaHei", 10), text_color=PH)
            lbl.pack(padx=8, pady=5)'''
content = content.replace(old_step, new_step)
print("11. Step indicators refined")

# ── 12. Arrow between steps ──
old_arrow = 'ctk.CTkLabel(sf, text="→", font=("Microsoft YaHei", 12), text_color=BORDER).pack(side="left", padx=1)'
new_arrow = 'ctk.CTkLabel(sf, text="›", font=("Segoe UI", 16, "bold"), text_color=PH).pack(side="left", padx=0)'
content = content.replace(old_arrow, new_arrow)
print("12. Step arrows refined")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("All detail refinements done")
