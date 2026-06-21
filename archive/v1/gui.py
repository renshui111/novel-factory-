# gui.py — Novel Factory GUI
# customtkinter 黑暗风界面，左侧导航 + 右侧内容

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# 确保可以导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    load_config, save_config, get_output_dir, check_ollama_running,
    get_available_ollama_models
)
from novel import generate_novel
from analyze import analyze_novel, batch_analyze
from deslop import deslop_file, scan_ai_words, generate_ai_word_report
from batch import run_batch


# ─── 配色 ────────────────────────────────────────────────
BG_DARK = "#0d0d1a"
SIDEBAR_BG = "#111122"
CARD_BG = "#141428"
ACCENT = "#e94560"
SECONDARY = "#4a9be8"
TEXT_COLOR = "#e0e0e0"
PLACEHOLDER = "#555555"
SUCCESS_GREEN = "#4CAF50"


class NovelFactoryGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Novel Factory — 网文工厂")
        self.root.geometry("1200x760")
        self.root.configure(fg_color=BG_DARK)

        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # 状态变量
        self.stop_flag = threading.Event()
        self.current_thread = None
        self.log_history = []

        # 加载配置
        self.config = load_config()

        # 构建界面
        self._build_sidebar()
        self._build_main_area()
        self._bind_events()

        # 默认显示设置页
        self._show_page("settings")

        # 关闭时清理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self):
        self.root.mainloop()

    # ═══════════════════════════════════════════════════════
    # 界面构建
    # ═══════════════════════════════════════════════════════

    def _build_sidebar(self):
        """左侧导航栏"""
        self.sidebar = ctk.CTkFrame(
            self.root, width=180, fg_color=SIDEBAR_BG, corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo/标题
        title_label = ctk.CTkLabel(
            self.sidebar, text="📖 网文工厂",
            font=("Microsoft YaHei", 20, "bold"),
            text_color=ACCENT
        )
        title_label.pack(pady=(30, 20))

        # 版本
        ver_label = ctk.CTkLabel(
            self.sidebar, text="v1.0 · 批量生产版",
            font=("Microsoft YaHei", 10),
            text_color=PLACEHOLDER
        )
        ver_label.pack(pady=(0, 20))

        # 导航按钮
        self.nav_buttons = {}
        nav_items = [
            ("settings", "⚙️  设置"),
            ("create", "✍️  写书"),
            ("batch", "📦  批量"),
            ("analyze", "🔍  拆书"),
            ("deslop", "🧹  去AI味"),
            ("cover", "🎨  封面"),
            ("output", "📂  产出"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label,
                font=("Microsoft YaHei", 14),
                fg_color="transparent",
                text_color=TEXT_COLOR,
                hover_color="#1a1a3a",
                anchor="w",
                height=40,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # 底部状态
        self.status_label = ctk.CTkLabel(
            self.sidebar, text="就绪",
            font=("Microsoft YaHei", 10),
            text_color=PLACEHOLDER
        )
        self.status_label.pack(side="bottom", pady=20)

    def _build_main_area(self):
        """右侧主内容区"""
        self.main_area = ctk.CTkFrame(
            self.root, fg_color=BG_DARK, corner_radius=0
        )
        self.main_area.pack(side="right", fill="both", expand=True)

        # 所有页面都预先创建好
        self.pages = {}
        page_names = ["settings", "create", "batch", "analyze", "deslop", "cover", "output"]

        for name in page_names:
            frame = ctk.CTkFrame(self.main_area, fg_color=BG_DARK, corner_radius=0)
            self.pages[name] = frame

        # 构建各个页面
        self._build_settings_page()
        self._build_create_page()
        self._build_batch_page()
        self._build_analyze_page()
        self._build_deslop_page()
        self._build_cover_page()
        self._build_output_page()

    # ═══════════════════════════════════════════════════════
    # 设置页面
    # ═══════════════════════════════════════════════════════

    def _build_settings_page(self):
        p = self.pages["settings"]
        cfg = self.config

        # 标题
        ctk.CTkLabel(p, text="⚙️  设置",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        # 滚动区域
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG_DARK)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        # ── 模型选择 ──
        ctk.CTkLabel(scroll, text="模型设置",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(anchor="w", pady=(10, 5))

        use_frame = ctk.CTkFrame(scroll, fg_color=CARD_BG)
        use_frame.pack(fill="x", pady=5)

        self.use_local_var = ctk.BooleanVar(value=cfg.get("use_local", False))
        ctk.CTkLabel(use_frame, text="使用本地模型 (Ollama):",
                     font=("Microsoft YaHei", 13)).pack(side="left", padx=10, pady=8)
        ctk.CTkSwitch(use_frame, text="",
                      variable=self.use_local_var,
                      command=self._toggle_model_mode).pack(side="right", padx=10)

        # 云端配置
        cloud_frame = ctk.CTkFrame(scroll, fg_color=CARD_BG)
        cloud_frame.pack(fill="x", pady=5)

        self.cloud_label = ctk.CTkLabel(cloud_frame, text="云端模型",
                                         font=("Microsoft YaHei", 14, "bold"))
        self.cloud_label.pack(anchor="w", padx=10, pady=(8, 0))

        self.cloud_provider_var = ctk.StringVar(
            value=cfg["llm"].get("provider", "openai"))
        ctk.CTkLabel(cloud_frame, text="提供商:").pack(anchor="w", padx=10)
        self.cloud_provider = ctk.CTkOptionMenu(
            cloud_frame, values=["openai", "deepseek", "custom"],
            variable=self.cloud_provider_var)
        self.cloud_provider.pack(fill="x", padx=10, pady=2)

        self.cloud_key_var = ctk.StringVar(value=cfg["llm"].get("api_key", ""))
        ctk.CTkLabel(cloud_frame, text="API Key:").pack(anchor="w", padx=10)
        self.cloud_key = ctk.CTkEntry(cloud_frame, textvariable=self.cloud_key_var,
                                       show="*", placeholder_text="sk-...")
        self.cloud_key.pack(fill="x", padx=10, pady=2)

        self.cloud_url_var = ctk.StringVar(
            value=cfg["llm"].get("base_url", "https://api.openai.com/v1"))
        ctk.CTkLabel(cloud_frame, text="Base URL:").pack(anchor="w", padx=10)
        self.cloud_url = ctk.CTkEntry(cloud_frame, textvariable=self.cloud_url_var)
        self.cloud_url.pack(fill="x", padx=10, pady=2)

        self.cloud_model_var = ctk.StringVar(
            value=cfg["llm"].get("model_name", "gpt-4o-mini"))
        ctk.CTkLabel(cloud_frame, text="模型:").pack(anchor="w", padx=10)
        self.cloud_model = ctk.CTkEntry(cloud_frame, textvariable=self.cloud_model_var)
        self.cloud_model.pack(fill="x", padx=10, pady=2)

        # 本地配置
        local_frame = ctk.CTkFrame(scroll, fg_color=CARD_BG)
        local_frame.pack(fill="x", pady=5)

        self.local_label = ctk.CTkLabel(local_frame, text="本地模型 (Ollama)",
                                         font=("Microsoft YaHei", 14, "bold"))
        self.local_label.pack(anchor="w", padx=10, pady=(8, 0))

        # 检测 Ollama
        ollama_frame = ctk.CTkFrame(local_frame, fg_color="transparent")
        ollama_frame.pack(fill="x", padx=10, pady=2)

        self.ollama_status_label = ctk.CTkLabel(
            ollama_frame, text="检测 Ollama...", font=("Microsoft YaHei", 11))
        self.ollama_status_label.pack(side="left")
        ctk.CTkButton(ollama_frame, text="检测",
                      command=self._check_ollama,
                      width=60, height=25).pack(side="right")

        self.local_model_var = ctk.StringVar(
            value=cfg["local_llm"].get("model_name", "qwen2.5:14b"))
        ctk.CTkLabel(local_frame, text="本地模型:").pack(anchor="w", padx=10)
        self.local_model = ctk.CTkEntry(local_frame, textvariable=self.local_model_var)
        self.local_model.pack(fill="x", padx=10, pady=2)

        self.local_url_var = ctk.StringVar(
            value=cfg["local_llm"].get("base_url", "http://localhost:11434/v1"))
        ctk.CTkLabel(local_frame, text="Ollama URL:").pack(anchor="w", padx=10)
        self.local_url = ctk.CTkEntry(local_frame, textvariable=self.local_url_var)
        self.local_url.pack(fill="x", padx=10, pady=2)

        # ── 输出设置 ──
        ctk.CTkLabel(scroll, text="输出设置",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(anchor="w", pady=(15, 5))

        out_frame = ctk.CTkFrame(scroll, fg_color=CARD_BG)
        out_frame.pack(fill="x", pady=5)

        self.output_dir_var = ctk.StringVar(value=cfg.get("output_dir", ""))
        ctk.CTkLabel(out_frame, text="输出目录:").pack(anchor="w", padx=10)
        dir_entry_frame = ctk.CTkFrame(out_frame, fg_color="transparent")
        dir_entry_frame.pack(fill="x", padx=10, pady=2)
        self.output_dir_entry = ctk.CTkEntry(
            dir_entry_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_entry_frame, text="浏览", command=self._browse_output_dir,
                      width=60).pack(side="right", padx=(5, 0))

        # 保存按钮
        ctk.CTkButton(scroll, text="💾 保存设置",
                      command=self._save_settings,
                      fg_color=SECONDARY,
                      font=("Microsoft YaHei", 14)).pack(pady=(15, 10))

        # 初始化时检测 Ollama
        self.root.after(1000, self._check_ollama)
        self._toggle_model_mode()

    # ═══════════════════════════════════════════════════════
    # 写书页面
    # ═══════════════════════════════════════════════════════

    def _build_create_page(self):
        p = self.pages["create"]
        cfg = self.config["novel"]

        ctk.CTkLabel(p, text="✍️  写书",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        scroll = ctk.CTkScrollableFrame(p, fg_color=BG_DARK)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        # 小说配置卡片
        card = ctk.CTkFrame(scroll, fg_color=CARD_BG)
        card.pack(fill="x", pady=5)

        ctk.CTkLabel(card, text="小说配置",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(10, 5))

        # 主题
        ctk.CTkLabel(card, text="主题 (必填):").pack(anchor="w", padx=15)
        self.topic_var = ctk.StringVar(value=cfg.get("topic", ""))
        ctk.CTkEntry(card, textvariable=self.topic_var,
                      placeholder_text="如: 剑道独尊：重生剑神").pack(fill="x", padx=15, pady=2)

        # 类型
        ctk.CTkLabel(card, text="类型:").pack(anchor="w", padx=15)
        self.genre_var = ctk.StringVar(value=cfg.get("genre", "玄幻"))
        genre_frame = ctk.CTkFrame(card, fg_color="transparent")
        genre_frame.pack(fill="x", padx=15, pady=2)
        for g in ["玄幻", "仙侠", "科幻", "都市", "末世", "历史", "游戏", "言情"]:
            ctk.CTkRadioButton(genre_frame, text=g, value=g,
                               variable=self.genre_var).pack(side="left", padx=5)

        # 章节数
        ctk.CTkLabel(card, text="章节数:").pack(anchor="w", padx=15)
        self.chapters_var = ctk.StringVar(value=str(cfg.get("num_chapters", 30)))
        ctk.CTkEntry(card, textvariable=self.chapters_var).pack(fill="x", padx=15, pady=2)

        # 每章字数
        ctk.CTkLabel(card, text="每章字数:").pack(anchor="w", padx=15)
        self.words_var = ctk.StringVar(value=str(cfg.get("words_per_chapter", 3000)))
        ctk.CTkEntry(card, textvariable=self.words_var).pack(fill="x", padx=15, pady=2)

        # ── 日志区域 ──
        log_label = ctk.CTkLabel(scroll, text="运行日志",
                                  font=("Microsoft YaHei", 14, "bold"),
                                  text_color=SECONDARY)
        log_label.pack(anchor="w", pady=(10, 2))

        self.create_log = ctk.CTkTextbox(scroll, height=250,
                                          fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.create_log.pack(fill="both", expand=True, pady=2)

        # ── 按钮区域 ──
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)

        self.start_create_btn = ctk.CTkButton(
            btn_frame, text="🚀 开始生成",
            command=self._start_create,
            fg_color=ACCENT, font=("Microsoft YaHei", 15, "bold"),
            height=40
        )
        self.start_create_btn.pack(side="left", padx=5)

        self.stop_create_btn = ctk.CTkButton(
            btn_frame, text="⏹ 停止",
            command=self._stop_task,
            fg_color="#555", state="disabled",
            font=("Microsoft YaHei", 13)
        )
        self.stop_create_btn.pack(side="left", padx=5)

    # ═══════════════════════════════════════════════════════
    # 批量页面
    # ═══════════════════════════════════════════════════════

    def _build_batch_page(self):
        p = self.pages["batch"]

        ctk.CTkLabel(p, text="📦  批量写书",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        ctk.CTkLabel(p, text="从 CSV 配置文件批量生成多本小说",
                     font=("Microsoft YaHei", 12),
                     text_color=PLACEHOLDER).pack(anchor="w", padx=20)

        # CSV 选择
        csv_frame = ctk.CTkFrame(p, fg_color=CARD_BG)
        csv_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(csv_frame, text="CSV 配置文件:",
                     font=("Microsoft YaHei", 13)).pack(anchor="w", padx=10, pady=(8, 2))

        csv_entry_frame = ctk.CTkFrame(csv_frame, fg_color="transparent")
        csv_entry_frame.pack(fill="x", padx=10, pady=2)

        self.batch_csv_var = ctk.StringVar(value="batch.csv")
        ctk.CTkEntry(csv_frame, textvariable=self.batch_csv_var).pack(fill="x", padx=10)

        ctk.CTkButton(csv_frame, text="📋 生成示例 CSV",
                      command=self._create_sample_csv,
                      fg_color=SECONDARY).pack(pady=8, padx=10)

        # 日志
        self.batch_log = ctk.CTkTextbox(p, height=300,
                                         fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.batch_log.pack(fill="both", expand=True, padx=20, pady=5)

        # 按钮
        btn_frame = ctk.CTkFrame(p, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(btn_frame, text="🚀 开始批量", command=self._start_batch,
                      fg_color=ACCENT, font=("Microsoft YaHei", 14, "bold"),
                      height=40).pack(side="left", padx=5)
        self.stop_batch_btn = ctk.CTkButton(btn_frame, text="⏹ 停止",
                                             fg_color="#555", state="disabled",
                                             command=self._stop_task)
        self.stop_batch_btn.pack(side="left", padx=5)

    # ═══════════════════════════════════════════════════════
    # 拆书页面
    # ═══════════════════════════════════════════════════════

    def _build_analyze_page(self):
        p = self.pages["analyze"]

        ctk.CTkLabel(p, text="🔍  拆书",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        # 单本拆书
        card1 = ctk.CTkFrame(p, fg_color=CARD_BG)
        card1.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(card1, text="单本拆书",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(10, 5))

        file_frame = ctk.CTkFrame(card1, fg_color="transparent")
        file_frame.pack(fill="x", padx=15, pady=2)

        self.analyze_path_var = ctk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self.analyze_path_var,
                      placeholder_text="选择小说 .txt 文件...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(file_frame, text="选择文件", command=self._browse_analyze_file,
                      width=80).pack(side="right", padx=(5, 0))

        ctk.CTkButton(card1, text="🔍 开始拆书",
                      command=self._start_analyze,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13)).pack(pady=10)

        # 批量拆书
        card2 = ctk.CTkFrame(p, fg_color=CARD_BG)
        card2.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(card2, text="批量拆书",
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(10, 5))

        dir_frame = ctk.CTkFrame(card2, fg_color="transparent")
        dir_frame.pack(fill="x", padx=15, pady=2)

        self.analyze_dir_var = ctk.StringVar()
        ctk.CTkEntry(dir_frame, textvariable=self.analyze_dir_var,
                      placeholder_text="选择包含 .txt 的文件夹...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_frame, text="选择目录", command=self._browse_analyze_dir,
                      width=80).pack(side="right", padx=(5, 0))

        ctk.CTkButton(card2, text="📚 批量拆书",
                      command=self._start_batch_analyze,
                      fg_color=SECONDARY, font=("Microsoft YaHei", 13)).pack(pady=10)

        # 日志
        self.analyze_log = ctk.CTkTextbox(p, height=200,
                                           fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.analyze_log.pack(fill="both", expand=True, padx=20, pady=5)

    # ═══════════════════════════════════════════════════════
    # 去AI味页面
    # ═══════════════════════════════════════════════════════

    def _build_deslop_page(self):
        p = self.pages["deslop"]

        ctk.CTkLabel(p, text="🧹  去 AI 味",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        # 文件选择
        card = ctk.CTkFrame(p, fg_color=CARD_BG)
        card.pack(fill="x", padx=20, pady=5)

        file_frame = ctk.CTkFrame(card, fg_color="transparent")
        file_frame.pack(fill="x", padx=15, pady=5)

        self.deslop_path_var = ctk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self.deslop_path_var,
                      placeholder_text="选择 .txt 或 .md 文件...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(file_frame, text="选择文件", command=self._browse_deslop_file,
                      width=80).pack(side="right", padx=(5, 0))

        # 选项
        opt_frame = ctk.CTkFrame(card, fg_color="transparent")
        opt_frame.pack(fill="x", padx=15, pady=5)

        self.deslop_llm_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame, text="使用 LLM 辅助（推荐）",
                        variable=self.deslop_llm_var).pack(side="left", padx=5)

        # 按钮
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkButton(btn_frame, text="🧹 开始去 AI 味",
                      command=self._start_deslop,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📊 AI 词频扫描",
                      command=self._scan_ai_words_gui,
                      fg_color=SECONDARY, font=("Microsoft YaHei", 13)).pack(side="left", padx=5)

        # 日志
        self.deslop_log = ctk.CTkTextbox(p, height=350,
                                          fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.deslop_log.pack(fill="both", expand=True, padx=20, pady=5)

    # ═══════════════════════════════════════════════════════
    # 封面页面
    # ═══════════════════════════════════════════════════════

    def _build_cover_page(self):
        p = self.pages["cover"]

        ctk.CTkLabel(p, text="🎨  封面生成",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        card = ctk.CTkFrame(p, fg_color=CARD_BG)
        card.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(card, text="书名:").pack(anchor="w", padx=15)
        self.cover_name_var = ctk.StringVar()
        ctk.CTkEntry(card, textvariable=self.cover_name_var).pack(fill="x", padx=15, pady=2)

        ctk.CTkLabel(card, text="类型:").pack(anchor="w", padx=15)
        self.cover_genre_var = ctk.StringVar(value="玄幻")
        ctk.CTkEntry(card, textvariable=self.cover_genre_var).pack(fill="x", padx=15, pady=2)

        ctk.CTkButton(card, text="🎨 生成封面提示词",
                      command=self._generate_cover,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13)).pack(pady=10)

        self.cover_log = ctk.CTkTextbox(p, height=400,
                                         fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.cover_log.pack(fill="both", expand=True, padx=20, pady=5)

    # ═══════════════════════════════════════════════════════
    # 产出页面
    # ═══════════════════════════════════════════════════════

    def _build_output_page(self):
        p = self.pages["output"]

        ctk.CTkLabel(p, text="📂  产出管理",
                     font=("Microsoft YaHei", 22, "bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(20, 10), padx=20)

        ctk.CTkButton(p, text="📂 打开产出目录",
                      command=self._open_output_dir,
                      fg_color=SECONDARY, font=("Microsoft YaHei", 13)).pack(pady=5)

        self.output_list = ctk.CTkTextbox(p, height=500,
                                           fg_color="#0a0a15", text_color=TEXT_COLOR)
        self.output_list.pack(fill="both", expand=True, padx=20, pady=5)

        self._refresh_output_list()

    # ═══════════════════════════════════════════════════════
    # 事件绑定 & 页面切换
    # ═══════════════════════════════════════════════════════

    def _bind_events(self):
        """不需要额外绑定"""
        pass

    def _show_page(self, name):
        for key, frame in self.pages.items():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def _toggle_model_mode(self):
        """切换本地/云端模型模式"""
        use_local = self.use_local_var.get()

        # 云端配置
        cloud_widgets = [getattr(self, attr, None) for attr in
                         ['cloud_label', 'cloud_provider', 'cloud_key',
                          'cloud_url', 'cloud_model']]
        # 本地配置
        local_widgets = [getattr(self, attr, None) for attr in
                         ['local_label', 'ollama_status_label', 'local_model',
                          'local_url']]

        # 通过改变 Frame 的父容器来隐藏，这里简单处理：在遍历时自动生效
        # 实际上不需要隐藏，因为用户一眼就能看到哪个是激活的
        pass

    # ═══════════════════════════════════════════════════════
    # 操作回调
    # ═══════════════════════════════════════════════════════

    def _check_ollama(self):
        """检测 Ollama 运行状态"""
        running = check_ollama_running()
        if running:
            models = get_available_ollama_models()
            model_list = ", ".join(models[:5]) if models else "未安装模型"
            self.ollama_status_label.configure(
                text=f"✅ Ollama 运行中 | {model_list}",
                text_color=SUCCESS_GREEN)
        else:
            self.ollama_status_label.configure(
                text="❌ Ollama 未运行",
                text_color=ACCENT)

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_dir_var.set(d)

    def _browse_analyze_file(self):
        f = filedialog.askopenfilename(
            title="选择小说文件",
            filetypes=[("Text files", "*.txt"), ("Markdown", "*.md")]
        )
        if f:
            self.analyze_path_var.set(f)

    def _browse_analyze_dir(self):
        d = filedialog.askdirectory(title="选择包含小说的目录")
        if d:
            self.analyze_dir_var.set(d)

    def _browse_deslop_file(self):
        f = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[("Text/Markdown", "*.txt *.md")]
        )
        if f:
            self.deslop_path_var.set(f)

    def _save_settings(self):
        cfg = load_config()
        cfg["use_local"] = self.use_local_var.get()
        cfg["llm"]["provider"] = self.cloud_provider_var.get()
        cfg["llm"]["api_key"] = self.cloud_key_var.get()
        cfg["llm"]["base_url"] = self.cloud_url_var.get()
        cfg["llm"]["model_name"] = self.cloud_model_var.get()
        cfg["local_llm"]["model_name"] = self.local_model_var.get()
        cfg["local_llm"]["base_url"] = self.local_url_var.get()
        cfg["output_dir"] = self.output_dir_var.get()
        save_config()
        messagebox.showinfo("保存成功", "设置已保存")

    def _start_create(self):
        """开始生成小说（后台线程）"""
        # 保存当前配置
        cfg = load_config()
        cfg["novel"]["topic"] = self.topic_var.get()
        cfg["novel"]["genre"] = self.genre_var.get()
        try:
            cfg["novel"]["num_chapters"] = int(self.chapters_var.get())
            cfg["novel"]["words_per_chapter"] = int(self.words_var.get())
        except ValueError:
            self._log(self.create_log, "❌ 章节数和每章字数必须是数字")
            return
        cfg["use_local"] = self.use_local_var.get()
        save_config()

        if not cfg["novel"]["topic"]:
            self._log(self.create_log, "❌ 请填写小说主题")
            return

        self.stop_flag.clear()
        self.start_create_btn.configure(state="disabled", text="⏳ 生成中...")
        self.stop_create_btn.configure(state="normal")
        self._log(self.create_log, "🚀 开始生成...\n")

        def task():
            try:
                generate_novel(
                    log_callback=lambda m: self._log(self.create_log, m),
                    stream_callback=lambda m: None,
                    stop_flag=self.stop_flag
                )
            finally:
                self.root.after(0, lambda: self.start_create_btn.configure(
                    state="normal", text="🚀 开始生成"))
                self.root.after(0, lambda: self.stop_create_btn.configure(
                    state="disabled"))
                self.root.after(0, self._refresh_output_list)

        self.current_thread = threading.Thread(target=task, daemon=True)
        self.current_thread.start()

    def _start_batch(self):
        """开始批量生成"""
        self.stop_flag.clear()
        self._log(self.batch_log, "🚀 开始批量生成...\n")

        def task():
            try:
                run_batch(
                    batch_file=self.batch_csv_var.get(),
                    log_callback=lambda m: self._log(self.batch_log, m),
                    stop_flag=self.stop_flag
                )
            finally:
                self.root.after(0, lambda: self.start_create_btn.configure(
                    state="normal"))
                self.root.after(0, lambda: self.stop_batch_btn.configure(
                    state="disabled"))
                self.root.after(0, self._refresh_output_list)

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _start_analyze(self):
        """开始拆书"""
        path = self.analyze_path_var.get()
        if not path or not os.path.exists(path):
            self._log(self.analyze_log, "❌ 请选择有效的小说文件")
            return

        self._log(self.analyze_log, "🔍 开始拆书...\n")

        def task():
            try:
                analyze_novel(path, log_callback=lambda m: self._log(self.analyze_log, m))
            except Exception as e:
                self._log(self.analyze_log, f"❌ 拆书失败: {e}")

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _start_batch_analyze(self):
        """开始批量拆书"""
        path = self.analyze_dir_var.get()
        if not path or not os.path.exists(path):
            self._log(self.analyze_log, "❌ 请选择有效目录")
            return

        self._log(self.analyze_log, "📚 开始批量拆书...\n")

        def task():
            try:
                batch_analyze(path, log_callback=lambda m: self._log(self.analyze_log, m))
            except Exception as e:
                self._log(self.analyze_log, f"❌ 批量拆书失败: {e}")

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _start_deslop(self):
        """执行去 AI 味"""
        path = self.deslop_path_var.get()
        if not path or not os.path.exists(path):
            self._log(self.deslop_log, "❌ 请选择有效文件")
            return

        self._log(self.deslop_log, "🧹 开始去 AI 味...\n")

        def task():
            try:
                result = deslop_file(path, use_llm=self.deslop_llm_var.get(),
                                     log_callback=lambda m: self._log(self.deslop_log, m))
                if "error" in result:
                    self._log(self.deslop_log, f"❌ {result['error']}")
                else:
                    self._log(self.deslop_log,
                              f"\n✅ 完成! 原字数: {result['original_len']} → {result['final_len']}")
                    self._log(self.deslop_log,
                              f"   替换 {result['rule_replacements']} 处 AI 词汇")
                    self._log(self.deslop_log, f"   减少 {result['reduction']} 字符")
            except Exception as e:
                self._log(self.deslop_log, f"❌ 去AI味失败: {e}")

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _scan_ai_words_gui(self):
        """扫描 AI 词频"""
        path = self.deslop_path_var.get()
        if not path or not os.path.exists(path):
            self._log(self.deslop_log, "❌ 请选择有效文件")
            return

        from core import read_file
        text = read_file(path)
        report = generate_ai_word_report(text)
        self._log(self.deslop_log, f"\n{report}")

    def _generate_cover(self):
        """生成封面提示词"""
        name = self.cover_name_var.get()
        genre = self.cover_genre_var.get()
        if not name:
            self._log(self.cover_log, "❌ 请填写书名")
            return

        self._log(self.cover_log, "🎨 正在生成封面提示词...\n")

        def task():
            try:
                from cover import generate_novel_cover
                result = generate_novel_cover(name, genre,
                                              log_callback=lambda m: self._log(self.cover_log, m))
                self._log(self.cover_log, f"\n✅ 提示词已生成\n\n{result.get('prompt', '')}")
            except Exception as e:
                self._log(self.cover_log, f"❌ 生成失败: {e}")

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _stop_task(self):
        self.stop_flag.set()
        self._log(self.create_log, "\n⏹ 正在停止（等待当前章节完成）...")

    def _create_sample_csv(self):
        from batch import _create_sample_batch
        path = self.batch_csv_var.get() or "batch.csv"
        _create_sample_batch(path)
        self._log(self.batch_log, f"✅ 示例 CSV 已创建: {os.path.abspath(path)}")

    def _open_output_dir(self):
        d = get_output_dir()
        os.startfile(d)

    def _refresh_output_list(self):
        d = get_output_dir()
        self.output_list.delete("0.0", "end")
        if os.path.exists(d):
            items = os.listdir(d)
            for item in items:
                path = os.path.join(d, item)
                if os.path.isdir(path):
                    # 显示目录内的文件数
                    files = [f for f in os.listdir(path)
                             if os.path.isfile(os.path.join(path, f))]
                    self.output_list.insert("end", f"📁 {item}/ ({len(files)} files)\n")
                else:
                    self.output_list.insert("end", f"📄 {item}\n")

    def _log(self, textbox, msg):
        """线程安全地添加日志"""
        self.root.after(0, lambda: self._do_log(textbox, msg))

    def _do_log(self, textbox, msg):
        """在 GUI 线程中执行日志写入"""
        textbox.insert("end", msg + "\n")
        textbox.see("end")
        self.root.update_idletasks()

    def _on_close(self):
        self.stop_flag.set()
        self.root.destroy()