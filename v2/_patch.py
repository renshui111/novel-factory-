with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '        self._current_step = "step1"\n        self._step_results = {}  # {step_key: text}\n        self._show_step_panel("step1")'

new = '        self._current_step = "step1"\n        self._step_results = {}  # {step_key: text}\n        self._step_extra = {}  # {step_key: extra_requirements}\n        self._style_presets = {\n            "爽文流": "节奏快，每3章小爽点，打脸狠，升级明显",\n            "暗黑流": "基调阴暗残酷，角色灰色，丛林法则",\n            "轻松流": "轻松幽默，主角魅力型，搞笑日常",\n            "严谨流": "设定经得起推敲，力量体系精确，伏笔缜密",\n            "热血流": "兄弟情义，战斗燃，为守护而战",\n        }\n        self._show_step_panel("step1")'

if old in content:
    content = content.replace(old, new)
    print("State init OK")
else:
    print("Pattern not found")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
