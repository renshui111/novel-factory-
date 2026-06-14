# -*- coding: utf-8 -*-
import os
BASE = r"D:\项目\小说工厂\v2"
def read(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f: return f.read()
def write(name, content):
    with open(os.path.join(BASE, name), "w", encoding="utf-8", newline="\n") as f: f.write(content)
print("=" * 60)
print("Applying all changes...")
print("=" * 60)
# 1. deslop.py
print("1. deslop.py")
c = read("deslop.py")
s = c.index("AI_WORD_REPLACEMENTS = [")
e = c.index("]", s) + 1
nt = "AI_WORD_REPLACEMENTS = [\n"
nt += "    # Level 1\n"
w1 = [("\u7136\u800c","\u4f46"),("\u4e0d\u7981",""),("\u59cb\u7ec8","\u4e00\u76f4"),("\u5ffd\u7136",""),("\u7a81\u7136",""),("\u5fae\u5fae",""),("\u4f3c\u4e4e",""),("\u4eff\u4f5b",""),("\u7adf\u7136",""),("\u7f13\u7f13","\u6162\u6162"),("\u6de1\u6de1",""),("\u9759\u9759",""),("\u9ed8\u9ed8",""),("\u8f7b\u8f7b",""),("\u6df1\u6df1",""),("\u5fae\u5fae\u4e00\u7b11","\u7b11\u4e86\u7b11"),("\u5634\u89d2\u5fae\u626c","\u7b11\u4e86"),("\u5634\u89d2\u4e0a\u626c","\u7b11\u4e86"),("\u5634\u89d2\u52fe\u8d77\u4e00\u62b9\u5f27\u5ea6","\u7b11\u4e86"),("\u773c\u4e2d\u95ea\u8fc7\u4e00\u4e1d",""),("\u5fc3\u4e2d\u6697\u9053","\u5fc3\u60f3"),("\u5fc3\u4e2d\u4e00\u52a8",""),("\u5fc3\u5934\u4e00\u9707",""),("\u4e0d\u7531\u81ea\u4e3b",""),("\u60c5\u4e0d\u81ea\u7981",""),("\u4e0b\u610f\u8bc6","")]
for o,n in w1: nt += f'    ("{o}", "{n}", 1),\n'
nt += "    # Level 2\n"
w2 = [("\u6216\u8bb8",""),("\u53ef\u80fd",""),("\u4e00\u5b9a",""),("\u5fc5\u987b",""),("\u5728\u2026\u2026\u4e2d",""),("\u968f\u7740",""),("\u67d0\u79cd\u7a0b\u5ea6\u4e0a",""),("\u6beb\u65e0\u7591\u95ee",""),("\u4e0d\u8a00\u800c\u55bb",""),("\u4e8b\u5b9e\u4e0a",""),("\u5b9e\u9645\u4e0a",""),("\u6362\u8a00\u4e4b",""),("\u6362\u53e5\u8bdd\u8bf4",""),("\u53ef\u4ee5\u8bf4",""),("\u4e0d\u5f97\u4e0d\u8bf4",""),("\u5766\u767d\u8bf4",""),("\u8bf4\u5b9e\u8bdd",""),("\u4ee4\u4ed6\u610f\u5916\u7684\u662f",""),("\u8ba9\u4ed6\u6ca1\u60f3\u5230\u7684\u662f",""),("\u51fa\u4e4e\u610f\u6599\u7684\u662f",""),("\u4e0d\u53ef\u601d\u8bae\u7684\u662f",""),("\u96be\u4ee5\u7f6e\u4fe1\u7684\u662f","")]
for o,n in w2: nt += f'    ("{o}", "{n}", 2),\n'
nt += "    # Level 3\n"
w3 = [("\u503c\u5f97\u6ce8\u610f\u7684\u662f",""),("\u9700\u8981\u6307\u51fa\u7684\u662f",""),("\u4f17\u6240\u5468\u77e5",""),("\u6bcb\u5eb8\u7f6e\u7591",""),("\u663e\u800c\u6613\u89c1",""),("\u603b\u800c\u8a00\u4e4b",""),("\u7efc\u4e0a\u6240\u8ff0",""),("\u4e0e\u6b64\u540c\u65f6",""),("\u5c31\u5728\u8fd9\u65f6",""),("\u4e0d\u7981\u60f3\u5230",""),("\u8111\u6d77\u91cc\u6d6e\u73b0\u51fa",""),("\u8111\u6d77\u4e2d\u95ea\u8fc7",""),("\u5185\u5fc3\u6df1\u5904",""),("\u4e00\u80a1\u83ab\u540d\u7684",""),("\u4e00\u9635\u83ab\u540d\u7684",""),("\u8bf4\u65f6\u8fdf\u90a3\u65f6\u5feb",""),("\u8bdd\u97f3\u521a\u843d",""),("\u6b64\u8a00\u4e00\u51fa","")]
for o,n in w3: nt += f'    ("{o}", "{n}", 3),\n'
nt += "]"
c = c[:s] + nt + c[e:]
write("deslop.py", c)
print("  done")