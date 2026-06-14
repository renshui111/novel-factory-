# -*- coding: utf-8 -*-
import os
BASE = r"D:\项目\小说工厂\v2"
def read(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f: return f.read()
def write(name, content):
    with open(os.path.join(BASE, name), "w", encoding="utf-8", newline="\n") as f: f.write(content)
print("Test OK")