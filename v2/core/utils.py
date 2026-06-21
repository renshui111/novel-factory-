import os, re, subprocess, logging, json
import sys

logger = logging.getLogger("novel_factory")

# ======================== 文件工具 ========================
def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def append_file(path: str, content: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def count_words(text: str) -> int:
    return len(re.sub(r"\s+", "", text))

# ======================== 工作区函数 ========================
def get_output_dir() -> str:
    """兼容旧版：返回 output_dir，新版推荐用 get_workspace_dir"""
    from .config import load_config, _get_app_dir
    cfg = load_config()
    d = cfg.get("output_dir", "") or cfg.get("workspace_dir", "")
    if not d:
        d = os.path.join(_get_app_dir(), "小说库")
    ensure_dir(d)
    return d

def get_workspace_dir() -> str:
    """获取主文件夹（所有小说项目的根目录）"""
    from .config import load_config, _get_app_dir
    cfg = load_config()
    d = cfg.get("workspace_dir", "") or cfg.get("output_dir", "")
    if not d:
        d = os.path.join(_get_app_dir(), "小说库")
    ensure_dir(d)
    return d

def get_book_dir(book_name: str) -> str:
    """获取某本书的项目目录: 主文件夹/书名/"""
    ws = get_workspace_dir()
    safe = re.sub(r'[\\/:*?"<>|]', "", book_name)[:40].strip()
    if not safe:
        safe = "unnamed"
    book_dir = os.path.join(ws, safe)
    ensure_dir(book_dir)
    ensure_dir(os.path.join(book_dir, "正文"))
    return book_dir

# ======================== 硬件检测 + 模型安装 ========================
def detect_gpu_info() -> dict:
    info = {"gpu_type": "unknown", "vram_gb": 0, "recommended_model": "qwen2.5:7b"}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            if lines:
                parts = lines[0].split(",")
                name = parts[0].strip()
                vram = float(parts[1].strip()) / 1024
                info["gpu_type"] = f"NVIDIA {name}"
                info["vram_gb"] = round(vram, 1)
                if vram >= 24:
                    info["recommended_model"] = "qwen2.5:14b"
                elif vram >= 12:
                    info["recommended_model"] = "qwen2.5:7b"
                else:
                    info["recommended_model"] = "qwen2.5:7b"
                return info
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["gpu_type"] = "Ollama ready"
    except FileNotFoundError:
        info["gpu_type"] = "No Ollama"
    return info

def check_ollama_running() -> bool:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_available_ollama_models() -> list:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        models = []
        for line in result.stdout.strip().split("\n")[1:]:
            line = line.strip()
            if line:
                name = line.split()[0] if line.split() else ""
                if name:
                    models.append(name)
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

def auto_install_model(model_name: str = None, log_callback=None) -> bool:
    if model_name is None:
        gpu = detect_gpu_info()
        model_name = gpu["recommended_model"]
    if log_callback:
        log_callback(f"Pulling {model_name}... (4-5 GB)")
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True)
        for line in iter(proc.stdout.readline, ""):
            if log_callback and line.strip():
                log_callback(f"  {line.strip()[:60]}")
        proc.wait()
        if proc.returncode == 0:
            if log_callback:
                log_callback(f"  {model_name} installed")
            return True
        else:
            if log_callback:
                log_callback(f"  {model_name} install failed")
            return False
    except FileNotFoundError:
        if log_callback:
            log_callback("  Ollama not found, install from https://ollama.com")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"  Error: {e}")
        return False
