with open("D:/项目/小说工厂/v2/gui.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace(
    'PURPLE      = "#8b5cf6"',
    'PURPLE      = "#8b5cf6"\nACCENT_LIGHT = "#93c5fd"'
)
with open("D:/项目/小说工厂/v2/gui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("OK")
