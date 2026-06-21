# core.py — LLM 统一调用接口 & 工具函数
# 支持 OpenAI / DeepSeek 兼容接口 + Ollama 本地模型
# 轻量实现，不依赖 langchain

import json
import os
import re
import time
import threading
from typing import Optional
from pathlib import Path

import requests


# ─── 全局变量 ────────────────────────────────────────────────
_config: dict = {}
_config_lock = threading.Lock()
_config_path: str = ""


# ─── 配置管理 ────────────────────────────────────────────────
def load_config(config_path: str = "") -> dict:
    global _config, _config_path
    if config_path:
        _config_path = config_path
    if not _config_path:
        _config_path = os.path.join(os.path.dirname(__file__), "config.json")

    if not os.path.exists(_config_path):
        _config = _default_config()
        save_config()
        return _config

    with _config_lock:
        try:
            with open(_config_path, "r", encoding="utf-8") as f:
                _config = json.load(f)
        except Exception:
            _config = _default_config()
        return _config


def save_config():
    with _config_lock:
        try:
            with open(_config_path, "w", encoding="utf-8") as f:
                json.dump(_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[core] 保存配置失败: {e}")


def _default_config() -> dict:
    return {
        "llm": {
            "provider": "openai",
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 8192,
            "timeout": 600
        },
        "local_llm": {
            "provider": "ollama",
            "api_key": "ollama",
            "base_url": "http://localhost:11434/v1",
            "model_name": "qwen2.5:14b",
            "temperature": 0.7,
            "max_tokens": 8192,
            "timeout": 600
        },
        "use_local": False,
        "output_dir": "",
        "novel": {
            "topic": "",
            "genre": "玄幻",
            "num_chapters": 30,
            "words_per_chapter": 3000
        }
    }


def get_llm_config() -> dict:
    cfg = load_config()
    if cfg.get("use_local"):
        return cfg.get("local_llm", cfg["llm"])
    return cfg["llm"]


# ─── LLM 调用 ────────────────────────────────────────────────
def llm_invoke(prompt: str, system_msg: str = "",
               stream_callback=None, stop_flag=None) -> str:
    """
    统一的 LLM 调用入口。
    - stream_callback: 如果提供，每收到一段文本就调用 callback(text)
    - stop_flag: threading.Event，设置后停止生成
    """
    cfg = get_llm_config()
    api_key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "https://api.openai.com/v1")
    model = cfg.get("model_name", "gpt-4o-mini")
    temperature = cfg.get("temperature", 0.7)
    max_tokens = cfg.get("max_tokens", 8192)
    timeout = cfg.get("timeout", 600)
    provider = cfg.get("provider", "openai")

    # 处理 base_url
    base_url = _normalize_url(base_url)
    api_url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json"
    }
    if api_key and provider != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream_callback is not None
    }

    try:
        resp = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=timeout,
            stream=stream_callback is not None
        )
        resp.raise_for_status()

        if stream_callback:
            # 流式输出
            collected = []
            for line in resp.iter_lines():
                if stop_flag and stop_flag.is_set():
                    break
                if line:
                    decoded = line.decode("utf-8", errors="ignore")
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            for ch in choices:
                                delta = ch.get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    collected.append(content)
                                    stream_callback(content)
                        except json.JSONDecodeError:
                            pass
            return "".join(collected)
        else:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

    except requests.exceptions.Timeout:
        return f"[错误] LLM 请求超时 (>{timeout}s)"
    except requests.exceptions.ConnectionError:
        return f"[错误] 无法连接到 {base_url}，请检查地址和网络"
    except requests.exceptions.HTTPError as e:
        return f"[错误] HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"[错误] {e}"


def llm_invoke_ada(prompt: str, system_msg: str = "", retries: int = 2) -> str:
    """带自动重试的 LLM 调用，适合拆书等不需要流式的场景"""
    for attempt in range(retries + 1):
        result = llm_invoke(prompt, system_msg)
        if result and not result.startswith("[错误]"):
            return result
        if attempt < retries:
            time.sleep(2)
    return result


def _normalize_url(url: str) -> str:
    """确保 base_url 格式正确"""
    url = url.strip()
    if not url:
        return "https://api.openai.com/v1"
    if url.endswith("#"):
        return url.rstrip("#")
    if not re.search(r'/v\d+$', url):
        if '/v1' not in url:
            url = url.rstrip('/') + '/v1'
    return url


# ─── 文件工具 ────────────────────────────────────────────────
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


def get_output_dir() -> str:
    cfg = load_config()
    d = cfg.get("output_dir", "")
    if not d:
        d = os.path.join(os.path.dirname(__file__), "output")
    ensure_dir(d)
    return d


# ─── 字数统计 ────────────────────────────────────────────────
def count_words(text: str) -> int:
    text = re.sub(r'\s+', '', text)
    return len(text)


def get_available_ollama_models() -> list:
    """检测本地 Ollama 已安装的模型列表"""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []


def check_ollama_running() -> bool:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False