# core/config.py — 配置管理
import json
import os
import sys
import shutil
import threading

_config: dict = {}
_config_lock = threading.Lock()
_config_path: str = ""


def _get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_data_dir() -> str:
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def load_config(config_path: str = "") -> dict:
    global _config, _config_path
    if config_path:
        _config_path = config_path
    if not _config_path:
        _config_path = os.path.join(_get_app_dir(), "config.json")
        if not os.path.exists(_config_path) and getattr(sys, 'frozen', False):
            bundle_cfg = os.path.join(_get_data_dir(), "config.json")
            if os.path.exists(bundle_cfg):
                shutil.copy2(bundle_cfg, _config_path)
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
            cfg_dir = os.path.dirname(_config_path) or "."
            os.makedirs(cfg_dir, exist_ok=True)
            with open(_config_path, "w", encoding="utf-8") as f:
                json.dump(_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            import logging
            logging.getLogger('novel_factory').error(f"保存配置失败: {e}")


def _default_config() -> dict:
    return {
        "llm": {
            "provider": "openai", "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7, "max_tokens": 8192, "timeout": 600
        },
        "local_llm": {
            "provider": "ollama", "api_key": "ollama",
            "base_url": "http://localhost:11434/v1",
            "model_name": "qwen2.5-chat:14b",
            "temperature": 0.7, "max_tokens": 8192, "timeout": 600
        },
        "use_local": False, "output_dir": "", "workspace_dir": "",
        "novel": {"topic": "", "genre": "\u7384\u5e7b",
                  "num_chapters": 30, "words_per_chapter": 3000}
    }


def get_llm_config() -> dict:
    cfg = load_config()
    if cfg.get("use_local"):
        return cfg.get("local_llm", cfg["llm"])
    return cfg["llm"]


def validate_config(config: dict) -> list:
    """返回错误列表，空列表表示配置合法"""
    errors = []
    llm = config.get("llm", {})

    if not config.get("use_local", False):
        if not llm.get("api_key"):
            errors.append("API key 不能为空（请填写或切换到本地模型）")
        if not llm.get("base_url", "").startswith(("http://", "https://")):
            errors.append(f"base_url 格式错误：{llm.get('base_url')}（需要 http:// 或 https:// 开头）")
        if not llm.get("model_name"):
            errors.append("model_name 不能为空")

    valid_providers = ["openai", "deepseek", "dashscope", "ollama", "custom"]
    provider = llm.get("provider", "")
    if provider not in valid_providers and not config.get("use_local", False):
        errors.append(f"不支持的 provider：{provider}（可选：{', '.join(valid_providers)}）")

    return errors