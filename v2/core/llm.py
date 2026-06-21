# core/llm.py — LLM 调用
import json
import re
import time
import logging
import requests

from .config import get_llm_config

logger = logging.getLogger('novel_factory')


def llm_invoke(prompt: str, system_msg: str = "",
               stream_callback=None, stop_flag=None) -> str:
    cfg = get_llm_config()
    api_key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "https://api.openai.com/v1")
    model = cfg.get("model_name", "gpt-4o-mini")
    temperature = cfg.get("temperature", 0.7)
    max_tokens = cfg.get("max_tokens", 8192)
    timeout = cfg.get("timeout", 600)
    provider = cfg.get("provider", "openai")

    base_url = _normalize_url(base_url)
    api_url = f"{base_url}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key and provider != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
        "stream": stream_callback is not None
    }

    try:
        resp = requests.post(api_url, headers=headers, json=payload,
                             timeout=timeout, stream=stream_callback is not None)
        resp.raise_for_status()

        if stream_callback:
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
                            for ch in data.get("choices", []):
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
        logger.warning(f"LLM 请求超时 (>{timeout}s)")
        return f"[错误] LLM 请求超时 (>{timeout}s)"
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到 {base_url}")
        return f"[错误] 无法连接到 {base_url}，请检查地址和网络"
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return f"[错误] HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        logger.exception(f"LLM 调用异常: {e}")
        return f"[错误] {e}"


def llm_invoke_ada(prompt: str, system_msg: str = "", retries: int = 2) -> str:
    for attempt in range(retries + 1):
        result = llm_invoke(prompt, system_msg)
        if result and not result.startswith("[错误]"):
            return result
        if attempt < retries:
            time.sleep(2)
    return result


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return "https://api.openai.com/v1"
    if url.endswith("#"):
        return url.rstrip("#")
    if not re.search(r'/v\d+$', url):
        if '/v1' not in url:
            url = url.rstrip('/') + '/v1'
    return url
