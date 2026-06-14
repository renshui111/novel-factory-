with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

old_obs = '''    # Obsidian路径
    OBSIDIAN_EXE = r"C:\\Users\\CodexSandboxOffline\\AppData\\Local\\Programs\\Obsidian\\Obsidian.exe"

    def _open_in_obsidian(self, path):
        """在 Obsidian 中打开指定目录"""
        import subprocess
        if not path or not os.path.isdir(path):
            return
        try:
            subprocess.Popen([self.OBSIDIAN_EXE, path], shell=False)
        except FileNotFoundError:
            # Try shortcut path
            obs_path = r"C:\\Users\\g\\AppData\\Local\\Programs\\Obsidian\\Obsidian.exe"
            try:
                subprocess.Popen([obs_path, path], shell=False)
            except Exception:
                pass
        except Exception:
            pass'''

new_obs = '''    def _open_in_obsidian(self, path):
        """在 Obsidian 中打开指定目录
        
        原理：
        1. 你的小说保存在 output_dir/书名/ 下
        2. 每本书是一个完整目录（正文/设定/大纲等都在里面）
        3. 点击按钮 → 调用 Obsidian.exe 打开这个目录
        4. Obsidian 将其作为 Vault 打开，你可以在 Obsidian 里：
           - 编辑所有 .md 文件
           - 用 [[双向链接]] 串联角色/设定/章节
           - 用图谱视图看人物关系
           - 用 Obsidian 插件增强写作体验
        """
        import subprocess, webbrowser
        
        if not path or not os.path.isdir(path):
            return
        
        # 方法1: 直接用 Obsidian URI（最可靠）
        obs_uri = f"obsidian://open?path={path.replace(chr(92), '/')}"
        try:
            webbrowser.open(obs_uri)
            return
        except Exception:
            pass
        
        # 方法2: 直接启动 Obsidian.exe
        obs_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Obsidian", "Obsidian.exe"),
            r"C:\\Users\\g\\AppData\\Local\\Programs\\Obsidian\\Obsidian.exe",
        ]
        for obs_path in obs_paths:
            if os.path.isfile(obs_path):
                try:
                    subprocess.Popen([obs_path, path], shell=False)
                    return
                except Exception:
                    continue
        
        # 方法3: 兜底 - 打开文件夹
        try:
            os.startfile(path)
        except Exception:
            pass'''

content = content.replace(old_obs, new_obs)
print("Obsidian method updated" if old_obs in content else "Pattern not found")

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
