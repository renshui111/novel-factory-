with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Insert helper methods before _ai_generate_step
old = "    def _ai_generate_step(self, step_key):"
new = """    def _apply_style_preset(self, name, desc):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if current.startswith("例如：") or current.startswith("输入你的"):
                current = ""
            if current:
                current = current + "；" + desc
            else:
                current = desc
            self._extra_req_text.delete("1.0", "end")
            self._extra_req_text.insert("1.0", current)
            self._log(self._create_log, f"已套用风格预设: {name}")

    def _on_extra_focus_in(self, placeholder):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if current == placeholder:
                self._extra_req_text.delete("1.0", "end")
                self._extra_req_text.configure(text_color=TEXT)

    def _on_extra_focus_out(self, placeholder):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if not current:
                self._extra_req_text.insert("1.0", placeholder)
                self._extra_req_text.configure(text_color=PH)

    def _ai_generate_step(self, step_key):"""

if old in content:
    content = content.replace(old, new)
    print("Helpers inserted before _ai_generate_step")
else:
    print("NOT FOUND")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
