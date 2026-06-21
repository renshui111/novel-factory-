# main.py — Novel Factory 入口
# 启动 GUI 应用，带崩溃日志

import sys
import os
import traceback

# 模块级别导入（确保 PyInstaller 扫描到）
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from gui import NovelFactoryGUI


def main():
    app = NovelFactoryGUI()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # frozen 时 _MEIPASS 只读，crash log 写到 exe 同级目录
        log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base_dir
        log_path = os.path.join(log_dir, "crash.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"NovelFactory 崩溃报告\n")
            f.write(f"{'='*60}\n")
            f.write(f"错误: {e}\n\n")
            f.write(traceback.format_exc())
        # GUI 弹窗
        import tkinter.messagebox as mb
        try:
            mb.showerror("NovelFactory",
                f"启动失败: {e}\n\n详情: {log_path}")
        except Exception:
            pass
        sys.exit(1)