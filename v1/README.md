# README.md

# 📖 Novel Factory — 网文工厂

## 是什么

一个整合了 7 个开源 AI 小说项目优势的**批量网文生产工具**：

| 功能 | 来源 |
|------|------|
| 小说生成管线 | AI_NovelGenerator |
| 去 AI 味 | oh-story-claudecode |
| 拆书分析 | wfcz10086 + 自定义 |
| 批量生产 | 自定义 + wfcz10086 |
| 质量审稿 | oh-story + ExplosiveCoder |
| 封面提示词 | oh-story-cover |
| 本地模型 (Ollama) | 自定义支持 |

## 功能

- ✅ **写书** — 设定 → 目录 → 逐章生成 → 定稿，单本完整管线
- ✅ **批量写书** — CSV 配置驱动，多本并行生成
- ✅ **拆书** — 分析已有小说结构（设定/角色/剧情/风格）
- ✅ **批量拆书** — 拆整个目录
- ✅ **去 AI 味** — 规则引擎 + LLM 辅助改写
- ✅ **AI 词频扫描** — 检测文本中的高频 AI 词汇
- ✅ **封面提示词生成** — 配合 DALL-E / Midjourney
- ✅ **支持本地 Ollama** — 也支持 OpenAI / DeepSeek 云端
- ✅ **GUI + 命令行双模式**

## 快速使用

### 方式一：运行源码

```bash
pip install -r requirements.txt
python main.py
```

### 方式二：打包为 exe

```bash
pip install pyinstaller
pyinstaller main.spec
```

生成的 exe 在 `dist/NovelFactory.exe`。

## 配置说明

所有配置在 `config.json` 中：

```json
{
    "llm": {
        "provider": "openai",
        "api_key": "sk-...",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o-mini"
    },
    "use_local": false,
    "novel": {
        "topic": "剑道独尊",
        "genre": "玄幻",
        "num_chapters": 30,
        "words_per_chapter": 3000
    }
}
```

本地模型只需改：
```json
"use_local": true
```
并在 GUI 中设置本地模型名称（如 `qwen2.5:14b`、`deepseek-r1:14b`）。

## 产出结构

```
output/
├── 小说名1/
│   ├── 设定.md
│   ├── 目录.md
│   ├── 正文/
│   │   ├── 第001章_标题.md
│   │   └── ...
│   ├── 生成报告.md
│   └── 全局摘要.txt
├── 小说名2/
│   └── ...
├── 拆书/
│   └── 书名/
│       ├── 设定分析.md
│       ├── 角色分析.md
│       ├── 剧情分析.md
│       └── 风格分析.md
└── _batch_report/
    └── batch_20260519_120000.csv
```

## 项目文件清单

| 文件 | 说明 |
|------|------|
| main.py | 入口 |
| gui.py | GUI 界面 (customtkinter) |
| core.py | LLM 调用、配置、文件工具 |
| prompts.py | 所有提示词模板 |
| novel.py | 小说生成管线 |
| analyze.py | 拆书模块 |
| deslop.py | 去 AI 味模块 |
| batch.py | 批量调度模块 |
| cover.py | 封面提示词 |
| config.json | 默认配置 |
| requirements.txt | Python 依赖 |
| main.spec | PyInstaller 打包配置 |