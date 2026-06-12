# main.py — Novel Factory 入口
# 启动 GUI 应用

import sys
import os

# 确保能找到同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import NovelFactoryGUI


def main():
    app = NovelFactoryGUI()
    app.run()


if __name__ == "__main__":
    main()