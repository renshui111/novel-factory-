# gui.py — Novel Factory GUI v1.1
# 黑暗风 + 分步引导 + 侧栏导航

from __future__ import annotations
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from project import discover_projects, get_project_meta, update_project_meta_from_config, import_analyze_to_project
from core import (
    load_config, save_config, get_output_dir, check_ollama_running,
    get_available_ollama_models, read_file, write_file, count_words
)
from novel import (
    generate_novel, generate_setting, generate_directory,
    generate_chapter, update_summary, prepare_book_dir,
    generate_outline, generate_world_building, generate_characters,
    generate_organizations, generate_relationships, continue_novel
)
from analyze import analyze_novel, batch_analyze
from deslop import deslop_file, generate_ai_word_report
from batch import run_batch
from export import (
    export_to_txt, export_to_epub, export_to_pdf,
    export_to_docx, export_to_html, _get_book_info
)
from editor import edit_chapter, edit_dialogue, add_scene, EditHistory
from reader_sim import simulate_reader, simulate_all_readers, predict_abandonment, get_readability_score
from downloader import download_novel, detect_platform, PLATFORMS
from reverse_engineer import reverse_engineer, apply_formula_to_new_book

# shadcn/ui dark design tokens
BG          = "#09090b"
SB          = "#0b0b10"
CARD        = "#111115"
CARD_HOVER  = "#18181f"
BORDER      = "#1f1f2a"
BORDER_LIGHT = "#27272f"
ACCENT      = "#3b82f6"
ACCENT_HOVER = "#2563eb"
ACCENT_SOFT  = "#1e3a5f"
BLUE        = "#60a5fa"
PURPLE      = "#8b5cf6"
ACCENT_LIGHT = "#93c5fd"
GREEN       = "#22c55e"
ORANGE      = "#f59e0b"
RED         = "#ef4444"
TEXT        = "#fafafa"
TEXT_DIM    = "#a1a1aa"
PH          = "#71717a"


class NovelFactoryGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("小说工厂")
        self.root.geometry("1360x880")
        self.root.minsize(1100, 700)
        self.root.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")

        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.active_tab = "settings"
        self._setting_text = ""
        self._chapters_list = []
        self._book_dir = ""
        self._create_mode = ctk.StringVar(value="auto")
        self._create_paused_event = threading.Event()
        self._confirm_response = None
        self.progress = {
            "current_chapter": 0,
            "total_chapters": 0,
            "current_step": "",
            "chapter_title": "",
            "chapter_words": 0,
            "elapsed_seconds": 0,
            "estimated_remaining": "",
            "status": "idle",
            "errors": [],
        }

        self._build_sidebar()
        self._build_main()
        self._build_status_bar()
        self._show_page("bookshelf")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # 启动校验
        self.root.after(200, self._validate_on_startup)
        # 状态栏定期刷新
        self._update_status_bar()
        self.root.after(10000, self._schedule_status_bar)

    def run(self):
        self.root.mainloop()

    # ─── 侧栏 ────────────────────────────
    def _build_sidebar(self):
        self.sb = ctk.CTkFrame(self.root, width=200, fg_color=SB, corner_radius=0)
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        # Logo area
        logo_frame = ctk.CTkFrame(self.sb, fg_color="transparent")
        logo_frame.pack(fill="x", padx=14, pady=(22, 4))
        ctk.CTkLabel(logo_frame, text="📖",
                     font=("Segoe UI Emoji", 22)).pack(side="left", padx=(2,8))
        ctk.CTkLabel(logo_frame, text="小说工厂",
                     font=("Microsoft YaHei", 17, "bold"),
                     text_color=TEXT).pack(side="left")
        # Divider
        div = ctk.CTkFrame(self.sb, height=1, fg_color=BORDER)
        div.pack(fill="x", padx=14, pady=(10, 12))

        self.nav = {}
        nav_sections = [
            ("创作", [("bookshelf", "  📊 仪表盘"), ("create", "  ✍️ 写书"), ("editor", "  📝 编辑器")]),
            ("分析", [("analyze", "  🔍 拆书"), ("reverse", "  🧬 逆向"), ("reader", "  👥 读者")]),
            ("工具", [("download", "  📥 下载"), ("settings", "  ⚙️ 设置")]),
        ]
        items = []
        first = True
        for section_title, section_items in nav_sections:
            sh = ctk.CTkLabel(self.sb, text=section_title,
                              font=("Microsoft YaHei", 9, "bold"),
                              text_color=PH, anchor="w")
            sh.pack(fill="x", padx=18, pady=(12 if first else 10, 2))
            first = False
            for key, label in section_items:
                items.append((key, label))
        emojis = {
            "bookshelf": "books", "create": "pencil",
            "editor": "pen-nib", "analyze": "mag",
            "reverse": "cube", "reader": "people",
            "download": "download", "settings": "gear",
        }
        for key, label in items:
            btn = ctk.CTkButton(
                self.sb, text=label,
                font=("Microsoft YaHei", 12),
                fg_color="transparent", text_color=TEXT_DIM,
                hover_color=CARD_HOVER, anchor="w", height=36, corner_radius=8,
                border_spacing=6,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=6, pady=1)
            self.nav[key] = btn

        # Bottom status
        bot_div = ctk.CTkFrame(self.sb, height=1, fg_color=BORDER)
        bot_div.pack(side="bottom", fill="x", padx=14, pady=(0, 8))
        self.status_frame = ctk.CTkFrame(self.sb, fg_color="transparent")
        self.status_frame.pack(side="bottom", fill="x", padx=14, pady=(0, 10))
        self.status_icon = ctk.CTkLabel(self.status_frame, text="●", text_color=GREEN,
                                         font=("Segoe UI", 7))
        self.status_icon.pack(side="left", padx=(6, 6), pady=10)
        self.status_text = ctk.CTkLabel(self.status_frame, text="就绪",
                                         font=("Microsoft YaHei", 10), text_color=PH)
        self.status_text.pack(side="left", pady=10)

    def _sect(self, parent, title):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkLabel(header_frame, text=title,
                     font=("Microsoft YaHei", 14, "bold"),
                     text_color=TEXT, anchor="w").pack(side="left")
        # Subtle divider
        div = ctk.CTkFrame(parent, height=1, fg_color=BORDER)
        div.pack(fill="x", padx=20, pady=(2, 8))

    def _show_page(self, name):
        self.active_tab = name
        for k, btn in self.nav.items():
            btn.configure(fg_color=CARD if k == name else "transparent",
                          text_color=ACCENT if k == name else TEXT_DIM)
        for key, frame in self.pages.items():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def _log(self, tb, msg):
        self.root.after(0, lambda: self._do_log(tb, msg))

    def _do_log(self, tb, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        tb.insert("end", f"[{ts}] {msg}\n")
        tb.see("end")

    # ─── 主区域 ──────────────────────────
    def _build_main(self):
        self.main_area = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

        names = ["bookshelf", "create", "editor", "analyze", "reverse", "reader", "download", "settings"]
        self.pages = {}
        for n in names:
            self.pages[n] = ctk.CTkFrame(self.main_area, fg_color=BG, corner_radius=0)
        self._build_bookshelf()
        self._build_create()
        self._build_analyze()
        self._build_reverse()
        self._build_editor_page()
        self._build_reader()
        self._build_download()
        self._build_settings()

    # ══════════════════════════════════════
    # 页面: Settings
    # ══════════════════════════════════════
    def _build_settings(self):
        p = self.pages["settings"]
        cfg = load_config()
        self._sect(p, "设置")

        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        self._card_lbl(scroll, "模型选择")
        card = ctk.CTkFrame(scroll, fg_color=CARD)
        card.pack(fill="x", pady=3)

        rf = ctk.CTkFrame(card, fg_color="transparent")
        rf.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(rf, text="使用本地模型 (Ollama):",
                     font=("Microsoft YaHei", 13)).pack(side="left")
        self.use_local_var = ctk.BooleanVar(value=cfg.get("use_local", False))
        ctk.CTkSwitch(rf, text="", variable=self.use_local_var,
                      command=self._toggle_model).pack(side="right")

        # Cloud
        self._cloud_f = ctk.CTkFrame(card, fg_color="transparent")
        self._cloud_f.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(self._cloud_f, text="云端模型",
                     font=("Microsoft YaHei", 13, "bold")).pack(anchor="w")
        # Provider dropdown
        ctk.CTkLabel(self._cloud_f, text="提供商:").pack(anchor="w")
        self.cloud_provider_var = ctk.StringVar(value=cfg["llm"].get("provider", "openai"))
        ctk.CTkOptionMenu(self._cloud_f,
            values=["openai", "deepseek", "dashscope", "ollama", "custom"],
            variable=self.cloud_provider_var,
            command=self._on_provider_change).pack(fill="x", pady=1)

        # API Key
        ctk.CTkLabel(self._cloud_f, text="API Key:").pack(anchor="w")
        self.cloud_key_var = ctk.StringVar(value=cfg["llm"].get("api_key", ""))
        ctk.CTkEntry(self._cloud_f, textvariable=self.cloud_key_var,
                     show="*", placeholder_text="sk-...").pack(fill="x", pady=1)

        # Base URL
        ctk.CTkLabel(self._cloud_f, text="接口地址:").pack(anchor="w")
        self.cloud_url_var = ctk.StringVar(
            value=cfg["llm"].get("base_url", "https://api.openai.com/v1"))
        ctk.CTkEntry(self._cloud_f, textvariable=self.cloud_url_var).pack(fill="x", pady=1)

        # Model
        ctk.CTkLabel(self._cloud_f, text="模型:").pack(anchor="w")
        self.cloud_model_var = ctk.StringVar(
            value=cfg["llm"].get("model_name", "gpt-4o-mini"))
        ctk.CTkEntry(self._cloud_f, textvariable=self.cloud_model_var).pack(fill="x", pady=1)

        # Local
        self._local_f = ctk.CTkFrame(card, fg_color="transparent")
        self._local_f.pack(fill="x", padx=15, pady=2)

        hf = ctk.CTkFrame(self._local_f, fg_color="transparent")
        hf.pack(fill="x")
        ctk.CTkLabel(hf, text="本地模型 (Ollama)",
                     font=("Microsoft YaHei", 13, "bold")).pack(side="left")
        self.ollama_status = ctk.CTkLabel(hf, text="检测中...",
                                           font=("Microsoft YaHei", 11))
        self.ollama_status.pack(side="right")
        ctk.CTkButton(hf, text="检测", command=self._check_ollama,
                      width=50, height=22).pack(side="right", padx=4)

        self.local_model_var = ctk.StringVar(
            value=cfg["local_llm"].get("model_name", "qwen2.5:7b"))
        # 自动检测已安装模型
        self._local_model_list = get_available_ollama_models()
        if not self._local_model_list:
            self._local_model_list = [
                "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
                "qwen2.5-coder:7b", "qwen2.5-coder:14b",
                "deepseek-r1:7b", "deepseek-r1:14b",
                "llama3.1:8b", "llama3.1:70b",
                "mistral:7b", "mixtral:8x7b",
            ]

        self.local_url_var = ctk.StringVar(
            value=cfg["local_llm"].get("base_url", "http://localhost:11434/v1"))

        # 模型名称: 下拉框 + 可手动输入
        ctk.CTkLabel(self._local_f, text="模型名称:").pack(anchor="w")
        self._local_model_cb = ctk.CTkComboBox(
            self._local_f,
            values=self._local_model_list,
            variable=self.local_model_var)
        self._local_model_cb.pack(fill="x", pady=1)

        # 硬件检测 + 安装按钮
        btn_f = ctk.CTkFrame(self._local_f, fg_color="transparent")
        btn_f.pack(fill="x", pady=2)
        self._detect_gpu_btn = ctk.CTkButton(
            btn_f, text="检测硬件并推荐", width=120, height=26,
            command=self._detect_hardware)
        self._detect_gpu_btn.pack(side="left", padx=(0,4))
        self._install_btn = ctk.CTkButton(
            btn_f, text="安装推荐模型", width=100, height=26,
            fg_color=GREEN, command=self._install_recommended_model)
        self._install_btn.pack(side="left")
        self._gpu_label = ctk.CTkLabel(
            btn_f, text="", font=("Consolas", 10), text_color=PH)
        self._gpu_label.pack(side="left", padx=6)

        # Ollama URL
        ctk.CTkLabel(self._local_f, text="Ollama URL:").pack(anchor="w")
        ctk.CTkEntry(self._local_f, textvariable=self.local_url_var).pack(fill="x", pady=1)

        # Output
        self._card_lbl(scroll, "输出设置")
        oc = ctk.CTkFrame(scroll, fg_color=CARD)
        oc.pack(fill="x", pady=3)

        self.output_dir_var = ctk.StringVar(value=cfg.get("output_dir", ""))
        ef = ctk.CTkFrame(oc, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=5)
        ctk.CTkEntry(ef, textvariable=self.output_dir_var,
                     placeholder_text="留空则保存在 exe 同目录"
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="浏览", command=self._browse_dir,
                      width=55).pack(side="right", padx=4)

        # 校验状态显示
        self._validate_label = ctk.CTkLabel(scroll, text="",
                                             font=("Microsoft YaHei", 11))
        self._validate_label.pack(pady=(0, 5))

        ctk.CTkButton(scroll, text="保存设置",
                      command=self._save_settings,
                      fg_color=BLUE, font=("Microsoft YaHei", 14)
                      ).pack(pady=(12, 10))

        self._update_model_visibility()
        self.root.after(1000, self._check_ollama)

    # ══════════════════════════════════════
    # 页面: Create (step-by-step)
    # ══════════════════════════════════════
        # ══════════════════════════════════════
    # 页面: 写书 — 手动分步流程
    # ══════════════════════════════════════
    def _build_create(self):
        p = self.pages["create"]
        self._sect(p, "写书 — 手动分步")

        cfg = load_config()["novel"]
        top = ctk.CTkFrame(p, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        top.pack(fill="x", padx=20, pady=(0, 8))

        gf = ctk.CTkFrame(top, fg_color="transparent")
        gf.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(gf, text="主题:", font=("Microsoft YaHei", 12)).grid(row=0, column=0, sticky="w")
        self._topic_var = ctk.StringVar(value=cfg.get("topic", ""))
        ctk.CTkEntry(gf, textvariable=self._topic_var, width=250,
                     placeholder_text="如: 剑道独尊:重生").grid(row=0, column=1, padx=2)

        ctk.CTkLabel(gf, text="类型:", font=("Microsoft YaHei", 12)).grid(row=0, column=2, sticky="w", padx=8)
        self._genre_var = ctk.StringVar(value=cfg.get("genre", "玄幻"))
        ctk.CTkComboBox(gf, values=["玄幻", "仙侠", "科幻", "都市", "末世", "历史", "游戏", "言情"],
                        variable=self._genre_var, width=110).grid(row=0, column=3, padx=2)

        ctk.CTkLabel(gf, text="章节:", font=("Microsoft YaHei", 12)).grid(row=0, column=4, sticky="w", padx=8)
        self._ch_var = ctk.StringVar(value=str(cfg.get("num_chapters", 30)))
        ctk.CTkEntry(gf, textvariable=self._ch_var, width=60).grid(row=0, column=5, padx=2)

        ctk.CTkLabel(gf, text="字数/章:", font=("Microsoft YaHei", 12)).grid(row=0, column=6, sticky="w", padx=8)
        self._wc_var = ctk.StringVar(value=str(cfg.get("words_per_chapter", 3000)))
        ctk.CTkEntry(gf, textvariable=self._wc_var, width=70).grid(row=0, column=7, padx=2)

        # ── Step indicator (7 steps) ──
        self.step_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.step_frame.pack(fill="x", padx=20, pady=(0, 4))
        sf = ctk.CTkFrame(self.step_frame, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        sf.pack(pady=0, fill="x")
        self._step_labels = {}
        self._step_keys = ["step1", "step2", "step3", "step4", "step5", "step6", "step7"]
        self._step_names = {
            "step1": "大纲", "step2": "世界观", "step3": "人物设定",
            "step4": "组织设定", "step5": "关系图谱", "step6": "章节目录", "step7": "写正文"
        }
        self._step_colors = {
            "step1": ACCENT, "step2": "#7c4dff", "step3": BLUE,
            "step4": "#00bcd4", "step5": "#4caf50", "step6": ORANGE, "step7": RED
        }
        for i, key in enumerate(self._step_keys):
            name = self._step_names[key]
            c = self._step_colors[key]
            sf2 = ctk.CTkFrame(sf, fg_color="transparent", corner_radius=6)
            sf2.pack(side="left", padx=1)
            lbl = ctk.CTkLabel(sf2, text=f"{i+1}.{name}", font=("Microsoft YaHei", 10), text_color=PH)
            lbl.pack(padx=7, pady=6)
            self._step_labels[key] = lbl
            if i < 6:
                ctk.CTkLabel(sf, text="·", font=("Segoe UI", 14, "bold"), text_color=BORDER).pack(side="left", padx=0)

        # ── Main area ──
        mid = ctk.CTkFrame(p, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=20, pady=(4, 0))

        # Left: step panel
        self._step_panel = ctk.CTkFrame(mid, fg_color=CARD, width=340, corner_radius=10, border_width=1, border_color=BORDER)
        self._step_panel.pack(side="left", fill="y", padx=(0, 8))
        self._step_panel.pack_propagate(False)

        # Right: editor + log
        right = ctk.CTkFrame(mid, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        # Editable text area
        ctk.CTkLabel(right, text="编辑区（可手动修改）", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w")
        self._create_editor = ctk.CTkTextbox(right, fg_color=CARD, text_color=TEXT,
                                              font=("Microsoft YaHei", 11), wrap="word")
        self._create_editor.pack(fill="both", expand=True, pady=(4, 4))

        # Log
        self._create_log = ctk.CTkTextbox(right, fg_color="#10121c", text_color=TEXT,
                                           font=("Consolas", 10), height=100)
        self._create_log.pack(fill="x", pady=(2, 0))
        self._log(self._create_log, "就绪 — 按步骤从「大纲」开始")

        # ── Bottom buttons ──
        btn_frame = ctk.CTkFrame(p, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self._step_btn = ctk.CTkButton(btn_frame, text="AI 生成",
                                        command=self._on_create_start,
                                        fg_color=ACCENT,
                                        font=("Microsoft YaHei", 14, "bold"),
                                        height=38, width=120)
        self._step_btn.pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="确认 → 下一步",
                      command=self._on_confirm_step,
                      fg_color=GREEN, font=("Microsoft YaHei", 13),
                      height=38, width=140).pack(side="left", padx=3)
        self._stop_btn = ctk.CTkButton(btn_frame, text="停止",
                                        command=self._stop,
                                        fg_color="#3f3f46", state="disabled")
        self._stop_btn.pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="打开目录",
                      command=lambda: self._open_dir(self._book_dir),
                      fg_color=BLUE).pack(side="right", padx=3)

        # State
        self._current_step = "step1"
        self._step_results = {}  # {step_key: text}
        self._step_extra = {}  # {step_key: extra_requirements}
        self._style_presets = {
            "爽文流": "节奏快，每3章小爽点，打脸狠，升级明显",
            "暗黑流": "基调阴暗残酷，角色灰色，丛林法则",
            "轻松流": "轻松幽默，主角魅力型，搞笑日常",
            "严谨流": "设定经得起推敲，力量体系精确，伏笔缜密",
            "热血流": "兄弟情义，战斗燃，为守护而战",
        }
        self._show_step_panel("step1")

    def _show_step_panel(self, step_key):
        for w in self._step_panel.winfo_children():
            w.destroy()

        self._current_step = step_key
        c = self._step_colors.get(step_key, ACCENT)
        for k, lbl in self._step_labels.items():
            if k in self._step_results and self._step_results[k]:
                lbl.configure(text_color=GREEN)
            elif k == step_key:
                lbl.configure(text_color=c)
            else:
                lbl.configure(text_color=PH)

        name = self._step_names[step_key]
        step_num = self._step_keys.index(step_key) + 1

        header = ctk.CTkLabel(self._step_panel, text=f"步骤{step_num}: {name}",
                              font=("Microsoft YaHei", 15, "bold"), text_color=c)
        header.pack(anchor="w", padx=15, pady=(12, 5))

        descriptions = {
            "step1": "输入主题后点击「AI 生成」，AI 将生成完整的小说大纲，\n包括分卷结构、每章概要、高潮节点、爽点分布。\n生成后可在右侧编辑区修改。\n\n可点击「导入拆书公式」将已拆书籍的节奏/爽点/钩子\n技法注入大纲生成。",
            "step2": "根据大纲生成世界观设定：时代背景、力量体系、\n势力分布、地理格局、特殊规则、货币资源。",
            "step3": "生成人物设定：主角、重要配角、反派的详细信息，\n包括性格、背景、能力、动机、成长弧线。",
            "step4": "生成组织/势力体系：宗门、国家、佣兵团等，\n各组织的等级、资源、历史恩怨。",
            "step5": "生成关系图谱：人物之间的关系网、组织间的关系、\n情感线设计。基于前4步的设定自动整合。",
            "step6": "生成章节目录：根据所有设定生成完整的章节目录，\n每章含标题和概要。确认后进入正文生成。",
            "step7": "开始逐章生成正文。每章根据设定自动写作，\n保证文风一致、人物不跑偏、剧情连贯。",
        }
        desc = descriptions.get(step_key, "")
        ctk.CTkLabel(self._step_panel, text=desc, font=("Microsoft YaHei", 11),
                     text_color=PH, wraplength=330, justify="left").pack(anchor="w", padx=15, pady=3)

        # Info area
        info = ctk.CTkTextbox(self._step_panel, height=120, fg_color="#10121c",
                               text_color=TEXT, font=("Microsoft YaHei", 10), state="disabled")
        info.pack(fill="x", padx=12, pady=5)
        summary_texts = {
            "step1": "大纲会保存在「大纲.md」\n后续步骤依赖大纲内容\n\n可导入拆书公式增强生成",
            "step2": "世界观保存在「世界观.md」\n核心设定，影响全局",
            "step3": "人物保存在「人物设定.md」\n至少10个角色的详细档案",
            "step4": "组织保存在「组织设定.md」\n势力的权力结构和利益关系",
            "step5": "关系保存在「关系图谱.md」\n谁和谁是什么关系",
            "step6": "目录保存在「目录.md」\n每章标题+概要",
            "step7": "正文逐章保存在「正文/」目录\n每章独立一个 .md 文件",
        }
        info.configure(state="normal")
        info.insert("1.0", summary_texts.get(step_key, ""))
        info.configure(state="disabled")

        # ── Extra requirements input (steps 1-5) ──
        if step_key in ["step1", "step2", "step3", "step4", "step5"]:
            # Style presets
            ctk.CTkLabel(self._step_panel, text="风格预设：",
                         font=("Microsoft YaHei", 10), text_color=PH).pack(anchor="w", padx=15, pady=(10, 2))
            pf = ctk.CTkFrame(self._step_panel, fg_color="transparent")
            pf.pack(fill="x", padx=12, pady=(0, 4))
            for i, (name, desc) in enumerate(self._style_presets.items()):
                ctk.CTkButton(pf, text=name, width=50, height=22,
                              font=("Microsoft YaHei", 9),
                              fg_color=CARD_HOVER, text_color=TEXT_DIM,
                              command=lambda n=name, d=desc: self._apply_style_preset(n, d)
                              ).pack(side="left", padx=1)

            # Extra requirements text area
            ctk.CTkLabel(self._step_panel, text="额外要求（引导AI生成方向）：",
                         font=("Microsoft YaHei", 10, "bold"), text_color=ACCENT_LIGHT).pack(anchor="w", padx=15, pady=(6, 2))
            
            placeholders = {
                "step1": "例如：要有反转剧情、主角一开始是废柴、加入师门试炼、前3章必须出现金手指",
                "step2": "例如：修真体系分9境、有魔族入侵背景、宗门分上中下三等、灵石是硬通货",
                "step3": "例如：主角性格冷傲但重情义、需要一个逗比跟班、反派是伪君子类型、加入一个女性强者",
                "step4": "例如：三大宗门互相制衡、有一个隐藏的幕后组织、正邪两道各有内斗",
                "step5": "例如：主角和女二是青梅竹马、师门内部有叛徒、正邪两道暗中有交易",
            }
            ph = placeholders.get(step_key, "输入你的具体要求...")
            
            self._extra_req_text = ctk.CTkTextbox(self._step_panel, height=80,
                                                   font=("Microsoft YaHei", 10),
                                                   fg_color=CARD, text_color=TEXT, wrap="word")
            self._extra_req_text.pack(fill="x", padx=12, pady=(0, 6))
            # Restore saved extra requirements
            saved_extra = self._step_extra.get(step_key, "")
            if saved_extra:
                self._extra_req_text.insert("1.0", saved_extra)
            else:
                self._extra_req_text.insert("1.0", ph)
            self._extra_req_text.bind("<FocusIn>", lambda e: self._on_extra_focus_in(ph))
            self._extra_req_text.bind("<FocusOut>", lambda e: self._on_extra_focus_out(ph))

        # Step1: add import formula button
        if step_key == "step1":
            ctk.CTkButton(self._step_panel, text="导入拆书公式",
                          command=self._import_analyze_formula,
                          fg_color=PURPLE, hover_color="#7c3aed",
                          width=140, height=28,
                          font=("Microsoft YaHei", 11)).pack(pady=4, padx=15)
            self._formula_ref = ""  # Store imported formula text

        # Show existing result if any
        if step_key in self._step_results and self._step_results[step_key]:
            self._create_editor.delete("1.0", "end")
            self._create_editor.insert("1.0", self._step_results[step_key])
            ctk.CTkButton(self._step_panel, text="重新生成",
                          command=lambda: self._ai_generate_step(step_key),
                          fg_color=ORANGE, width=100).pack(pady=8, padx=15)
        else:
            if step_key != "step1":
                self._create_editor.delete("1.0", "end")

    # ─── Step generation ───
    def _on_create_start(self):
        """AI 生成当前步骤"""
        self._ai_generate_step(self._current_step)

    def _apply_style_preset(self, name, desc):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if current.startswith("例如：") or current.startswith("输入你的"):
                current = ""
            if current:
                current = current + "；" + desc
            else:
                current = desc
            self._extra_req_text.delete("1.0", "end")
            self._extra_req_text.insert("1.0", current)
            self._log(self._create_log, f"已套用风格预设: {name}")

    def _on_extra_focus_in(self, placeholder):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if current == placeholder:
                self._extra_req_text.delete("1.0", "end")
                self._extra_req_text.configure(text_color=TEXT)

    def _on_extra_focus_out(self, placeholder):
        if hasattr(self, '_extra_req_text'):
            current = self._extra_req_text.get("1.0", "end-1c").strip()
            if not current:
                self._extra_req_text.insert("1.0", placeholder)
                self._extra_req_text.configure(text_color=PH)

    def _import_analyze_formula(self):
        """从已拆书籍导入写作公式，注入大纲生成"""
        from project import get_output_dir
        output_dir = get_output_dir()
        # Find projects with analyze data
        import os
        candidates = []
        if os.path.isdir(output_dir):
            for name in os.listdir(output_dir):
                path = os.path.join(output_dir, name)
                rep_file = os.path.join(path, "可复制公式.md")
                if os.path.isfile(rep_file):
                    candidates.append((name, path, rep_file))
        
        if not candidates:
            # Also check for reverse_engineer results
            for name in os.listdir(output_dir):
                path = os.path.join(output_dir, name)
                if os.path.isdir(path):
                    for fname in os.listdir(path):
                        if "公式" in fname or "template" in fname.lower() or "formula" in fname.lower():
                            candidates.append((name, path, os.path.join(path, fname)))
        
        if not candidates:
            self._log(self._create_log, "未找到已拆书籍的公式文件。请先在「拆书」或「逆向工程」中分析一本书。")
            return
        
        # Show selection dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("选择参考书籍")
        dialog.geometry("400x350")
        dialog.configure(fg_color=BG)
        
        ctk.CTkLabel(dialog, text="选择一本已拆书籍的写作公式：",
                     font=("Microsoft YaHei", 13, "bold"), text_color=TEXT).pack(pady=10)
        
        for name, path, rep_file in candidates:
            def make_cb(n, f):
                def cb():
                    from core import read_file
                    formula = read_file(f)
                    self._formula_ref = formula[:2000]
                    self._log(self._create_log, f"已导入《{n}》的写作公式 ({len(formula)}字)")
                    self._log(self._create_log, "公式将在生成大纲时注入AI prompt")
                    dialog.destroy()
                return cb
            ctk.CTkButton(dialog, text=name, command=make_cb(name, rep_file),
                          fg_color=CARD, hover_color=CARD_HOVER, text_color=TEXT,
                          anchor="w", height=36).pack(fill="x", padx=20, pady=3)

    def _ai_generate_step(self, step_key):
        """为指定步骤调用 AI 生成"""
        topic = self._topic_var.get().strip()
        genre = self._genre_var.get()
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000

        if step_key == "step1" and not topic:
            self._log(self._create_log, "请先填写主题")
            return

        self._step_btn.configure(state="disabled", text="生成中...")
        self._stop_btn.configure(state="normal")
        self._log(self._create_log, f"正在 AI 生成: {self._step_names[step_key]}...")

        def task():
            try:
                # Collect extra requirements
                extra = ""
                if hasattr(self, '_extra_req_text'):
                    extra = self._extra_req_text.get("1.0", "end-1c").strip()
                    # Remove placeholder text
                    if extra.startswith("例如：") or extra.startswith("输入你的"):
                        extra = ""
                self._step_extra[step_key] = extra

                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    # If formula imported, append to extra requirements
                    formula = getattr(self, '_formula_ref', '')
                    if formula:
                        extra = (extra + "\n\n[参考写作公式]\n" + formula) if extra else f"[参考写作公式]\n{formula}"
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m),
                                              extra_requirements=extra)
                elif step_key == "step2":
                    outline = self._step_results.get("step1", "")
                    result = generate_world_building(outline, genre, self._book_dir,
                                                     log_callback=lambda m: self._log(self._create_log, m),
                                                     extra_requirements=extra)
                elif step_key == "step3":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    result = generate_characters(outline, world, genre, self._book_dir,
                                                 log_callback=lambda m: self._log(self._create_log, m),
                                                 extra_requirements=extra)
                elif step_key == "step4":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    result = generate_organizations(outline, world, chars, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m),
                                                    extra_requirements=extra)
                elif step_key == "step5":
                    outline = self._step_results.get("step1", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    result = generate_relationships(outline, chars, orgs, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m),
                                                    extra_requirements=extra)
                elif step_key == "step6":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    rels = self._step_results.get("step5", "")
                    combined = f"{outline[:2000]}\n\n{world[:1500]}\n\n{chars[:1500]}\n\n{orgs[:1000]}\n\n{rels[:1000]}"
                    result = generate_directory(combined, num_ch, self._book_dir,
                                                log_callback=lambda m: self._log(self._create_log, m))
                    # Parse chapters
                    self._chapters_list = _parse_directory(result, num_ch) if callable(eval("_parse_directory")) else []
                elif step_key == "step7":
                    self.root.after(0, lambda: self._start_chapter_generation())
                    self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
                    return

                self._step_results[step_key] = result
                self.root.after(0, lambda: self._show_result(step_key, result))
            except Exception as e:
                self.root.after(0, lambda: self._log(self._create_log, f"生成失败: {e}"))
                self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
                self.root.after(0, lambda: self._stop_btn.configure(state="disabled"))

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _show_result(self, step_key, result):
        self._create_editor.delete("1.0", "end")
        self._create_editor.insert("1.0", result)
        self._step_btn.configure(state="normal", text="AI 生成")
        self._stop_btn.configure(state="disabled")
        self._log(self._create_log, f"{self._step_names[step_key]} 完成 ✓ — 可在右侧编辑区修改，确认后点「确认→下一步」")
        self._show_step_panel(step_key)

    def _on_confirm_step(self):
        """确认当前步骤，保存编辑内容，进入下一步"""
        current = self._current_step
        # Save edited content
        edited = self._create_editor.get("1.0", "end-1c").strip()
        if edited:
            self._step_results[current] = edited
            # Also save to file
            file_map = {
                "step1": "大纲.md", "step2": "世界观.md", "step3": "人物设定.md",
                "step4": "组织设定.md", "step5": "关系图谱.md", "step6": "目录.md",
            }
            if current in file_map and self._book_dir:
                write_file(os.path.join(self._book_dir, file_map[current]), edited)

        # Go to next step
        idx = self._step_keys.index(current)
        if idx < 6:
            next_step = self._step_keys[idx + 1]
            self._show_step_panel(next_step)
            self._log(self._create_log, f"→ 进入: {self._step_names[next_step]}")
        else:
            self._log(self._create_log, "所有设定步骤完成！点击「AI 生成」开始逐章写正文")
            self._show_step_panel("step7")

    def _start_chapter_generation(self):
        """Step 7: 开始逐章生成正文"""
        topic = self._topic_var.get().strip()
        genre = self._genre_var.get()
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000

        if not self._book_dir:
            self._log(self._create_log, "错误: 未创建书籍目录")
            return

        self._save_novel_cfg()
        self._log(self._create_log, "开始逐章生成正文...")
        self._step_btn.configure(state="disabled")

        def task():
            chapters = self._chapters_list if hasattr(self, '_chapters_list') and self._chapters_list else []
            result = generate_novel(
                topic, genre, num_ch, wc, self._book_dir,
                log_callback=lambda m: self._log(self._create_log, m),
                stop_flag=self.stop_flag)
            self.root.after(0, lambda: self._on_novel_done(result))

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _on_novel_done(self, result):
        self._step_btn.configure(state="normal", text="AI 生成")
        status = result.get("status", "完成")
        words = result.get("total_words", 0)
        self._log(self._create_log, f"写书{status} | 共{words:,}字 | 目录: {self._book_dir}")

    def _get_novel_config(self):
        try:
            num_ch = int(self._ch_var.get())
        except ValueError:
            num_ch = 30
        try:
            wc = int(self._wc_var.get())
        except ValueError:
            wc = 3000
        return {
            "topic": self._topic_var.get().strip(),
            "genre": self._genre_var.get(),
            "num_chapters": num_ch,
            "words_per_chapter": wc,
        }

    def _save_novel_cfg(self):
        from core import load_config, save_config
        cfg = load_config()
        cfg["novel"] = self._get_novel_config()
        save_config()

    def _toggle_pause(self):
        if self.pause_flag.is_set():
            self.pause_flag.clear()
            self._pause_btn.configure(text="暂停")
        else:
            self.pause_flag.set()
            self._pause_btn.configure(text="继续")

    def _stop(self):
        self.stop_flag.set()
        self._stop_btn.configure(state="disabled")
        self._step_btn.configure(state="normal", text="AI 生成")
        self._log(self._create_log, "已停止")

    def _init_progress(self, total_chapters):
        self.progress["total_chapters"] = total_chapters
        self.progress["current_chapter"] = 0
        self.progress["chapter_words"] = 0
        self.progress["elapsed_seconds"] = 0
        self.progress["status"] = "running"
        # self._progress_bar.set(0)

    def _update_dashboard(self):
        p = self.progress
        cur = p.get("current_chapter", 0)
        total = p.get("total_chapters", 0)
        w = p.get("chapter_words", 0)
        elapsed = p.get("elapsed_seconds", 0)
        if cur > 0 and elapsed > 0:
            speed = round(w * cur / elapsed)
            eta_sec = (total - cur) * (elapsed / cur) if cur > 0 else 0
            eta = f"{int(eta_sec // 60)}分{int(eta_sec % 60)}秒" if eta_sec > 0 else "—"
        else:
            speed = "—"
            eta = "—"
        # self._dash_labels["progress"].configure(text=f"{cur} / {total} 章")
        # self._dash_labels["words"].configure(text=f"{w * cur:,} 字")
        # self._dash_labels["speed"].configure(text=f"{speed}" if isinstance(speed, str) else f"{speed} 字/秒")
        # self._dash_labels["eta"].configure(text=eta)
        # if cur > 0 and total > 0:\n        #     self._progress_bar.set(cur / total)

    def _log_progress(self, msg):
        self._create_log.configure(state="normal")
        self._create_log.insert("end", msg + "\n")
        self._create_log.see("end")
        self._create_log.configure(state="disabled")

    def _on_novel_progress(self, data):
        self.progress.update(data)
        self.root.after(0, self._update_dashboard)

    def _browse_outline(self):
        f = filedialog.askopenfilename(filetypes=[("Markdown", "*.md"), ("Text", "*.txt")])
        if f:
            text = read_file(f)
            if text:
                self._create_editor.delete("1.0", "end")
                self._create_editor.insert("1.0", text)
                self._log(self._create_log, f"已加载: {f}")

    def _run_continue(self):
        d = self._book_dir
        if not d or not os.path.isdir(d):
            self._log(self._create_log, "请先生成至少一次")
            return
        self._log(self._create_log, "开始续写...")
        self._step_btn.configure(state="disabled")
        def task():
            try:
                result = continue_novel(d, additional_chapters=10,
                                        log_callback=lambda m: self._log(self._create_log, m),
                                        stop_flag=self.stop_flag)
                self.root.after(0, lambda: self._log(self._create_log, f"续写完成: {result.get('chapters_added', 0)}章"))
            except Exception as e:
                self.root.after(0, lambda: self._log(self._create_log, f"续写失败: {e}"))
            self.root.after(0, lambda: self._step_btn.configure(state="normal", text="AI 生成"))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _toggle_outline_mode(self):
        pass  # 已整合到手动流程中


    def _build_batch(self):
        p = self.pages["batch"]
        self._sect(p, "批量写书")
        ctk.CTkLabel(p, text="从CSV批量生成多本小说",
                     font=("Microsoft YaHei", 11), text_color=PH).pack(anchor="w", padx=20)

        card = ctk.CTkFrame(p, fg_color=CARD)
        card.pack(fill="x", padx=20, pady=5)

        self.batch_csv_var = ctk.StringVar(value="")
        ctk.CTkLabel(card, text="CSV配置文件:").pack(anchor="w", padx=15)
        ef = ctk.CTkFrame(card, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=3)
        ctk.CTkEntry(ef, textvariable=self.batch_csv_var,
                     placeholder_text="留空默认batch.csv"
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="浏览", command=self._browse_batch_csv,
                      width=55).pack(side="right", padx=4)

        # 并发数控制
        wf = ctk.CTkFrame(card, fg_color="transparent")
        wf.pack(fill="x", padx=15, pady=(5, 0))
        ctk.CTkLabel(wf, text="并行数:",
                     font=("Microsoft YaHei", 11),
                     text_color=TEXT).pack(side="left")
        self.batch_max_workers_var = ctk.StringVar(value="3")
        ctk.CTkOptionMenu(wf,
                          variable=self.batch_max_workers_var,
                          values=[str(i) for i in range(1, 11)],
                          width=60,
                          font=("Microsoft YaHei", 11)).pack(side="left", padx=4)

        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(pady=8, padx=15)
        ctk.CTkButton(bf, text="生成示例CSV",
                      command=self._create_sample_csv,
                      fg_color=BLUE).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="开始批量",
                      command=self._start_batch,
                      fg_color=ACCENT, font=("Microsoft YaHei", 13)).pack(side="left", padx=3)

        self.batch_log = ctk.CTkTextbox(p, fg_color="#10121c", text_color=TEXT,
                                         font=("Consolas", 11))
        self.batch_log.pack(fill="both", expand=True, padx=20, pady=5)

    # ══════════════════════════════════════
    # 页面: Analyze
    # ══════════════════════════════════════
    def _build_analyze(self):
        p = self.pages["analyze"]
        self._sect(p, "拆书")

        c1 = ctk.CTkFrame(p, fg_color=CARD)
        c1.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(c1, text="单本拆书",
                     font=("Microsoft YaHei", 14, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(8, 2))

        ef = ctk.CTkFrame(c1, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=3)
        self.analyze_path_var = ctk.StringVar()
        ctk.CTkEntry(ef, textvariable=self.analyze_path_var,
                     placeholder_text="选择.txt文件...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="浏览", command=self._browse_file,
                      width=50).pack(side="right", padx=4)
        ctk.CTkButton(c1, text="拆书", command=self._start_analyze,
                      fg_color=ACCENT, height=32).pack(pady=6)

        c2 = ctk.CTkFrame(p, fg_color=CARD)
        c2.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(c2, text="批量拆书",
                     font=("Microsoft YaHei", 14, "bold"),
                     text_color=BLUE).pack(anchor="w", padx=15, pady=(8, 2))

        df = ctk.CTkFrame(c2, fg_color="transparent")
        df.pack(fill="x", padx=15, pady=3)
        self.analyze_dir_var = ctk.StringVar()
        ctk.CTkEntry(df, textvariable=self.analyze_dir_var,
                     placeholder_text="选择含.txt的文件夹...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(df, text="浏览", command=self._browse_dir_2,
                      width=50).pack(side="right", padx=4)
        ctk.CTkButton(c2, text="批量拆书", command=self._start_batch_analyze,
                      fg_color=BLUE, height=32).pack(pady=6)

        # ─── 拆书进度指示 ────────────────
        self._analyze_progress_frame = ctk.CTkFrame(p, fg_color=CARD)
        self._analyze_progress_frame.pack(fill="x", padx=20, pady=3)

        self._analyze_progress_labels = {}
        analyze_steps = [
            ("setting", "设定分析"),
            ("char", "角色分析"),
            ("plot", "剧情分析"),
            ("style", "风格分析"),
        ]
        sf = ctk.CTkFrame(self._analyze_progress_frame, fg_color="transparent")
        sf.pack(pady=6)
        for key, label in analyze_steps:
            lbl = ctk.CTkLabel(sf, text=f"[ ] {label}",
                               font=("Microsoft YaHei", 12), text_color=PH)
            lbl.pack(side="left", padx=8)
            self._analyze_progress_labels[key] = lbl
            ctk.CTkLabel(sf, text="→",
                         font=("Microsoft YaHei", 12), text_color=PH).pack(side="left")
        # 去掉最后一个箭头
        sf.winfo_children()[-1].destroy()

        self._analyze_status = ctk.CTkLabel(
            self._analyze_progress_frame,
            text="就绪，选择小说文件后点击拆书",
            font=("Microsoft YaHei", 11), text_color=PH)
        self._analyze_status.pack(pady=(0, 6))

        # ─── 对比分析 ────────────────
        c3 = ctk.CTkFrame(p, fg_color=CARD)
        c3.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(c3, text="对比分析",
                     font=("Microsoft YaHei", 14, "bold"),
                     text_color=ORANGE).pack(anchor="w", padx=15, pady=(8, 2))

        # 书A 选择
        aef = ctk.CTkFrame(c3, fg_color="transparent")
        aef.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(aef, text="书A:", font=("Microsoft YaHei", 12),
                     text_color=TEXT).pack(side="left", padx=(0, 5))
        self._compare_a_var = ctk.StringVar()
        ctk.CTkEntry(aef, textvariable=self._compare_a_var,
                     placeholder_text="选择书A的 .md/.txt 文件...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(aef, text="浏览", command=self._browse_compare_a,
                      width=50).pack(side="right", padx=4)

        # 书B 选择
        bef = ctk.CTkFrame(c3, fg_color="transparent")
        bef.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(bef, text="书B:", font=("Microsoft YaHei", 12),
                     text_color=TEXT).pack(side="left", padx=(0, 5))
        self._compare_b_var = ctk.StringVar()
        ctk.CTkEntry(bef, textvariable=self._compare_b_var,
                     placeholder_text="选择书B的 .md/.txt 文件...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(bef, text="浏览", command=self._browse_compare_b,
                      width=50).pack(side="right", padx=4)

        ctk.CTkButton(c3, text="开始对比", command=self._start_compare,
                      fg_color=ORANGE, height=32).pack(pady=6)

        # ─── 对比结果 Tab 视图 ────────────────
        self._compare_tabview = ctk.CTkTabview(p, fg_color=CARD, text_color=TEXT)
        # CTkTabview 4 tabs: 设定对比、角色对比、风格对比、节奏对比
        self._compare_tab_names = {
            "setting": "设定对比",
            "char":    "角色对比",
            "style":   "风格对比",
            "plot":    "节奏对比",
        }
        self._compare_textboxes = {}  # will store {tab_key: {a: CTkTextbox, b: CTkTextbox}}

        for key, label in self._compare_tab_names.items():
            tab = self._compare_tabview.add(label)

            # 书A 侧
            left_frame = ctk.CTkFrame(tab, fg_color="#10121c")
            left_frame.pack(side="left", fill="both", expand=True, padx=1, pady=1)
            ctk.CTkLabel(left_frame, text="书A",
                         font=("Microsoft YaHei", 11, "bold"),
                         text_color=ACCENT).pack(anchor="w", padx=4, pady=(2, 0))
            txt_a = ctk.CTkTextbox(left_frame, fg_color="#10121c",
                                   text_color=TEXT, font=("Consolas", 11))
            txt_a.pack(fill="both", expand=True, padx=2, pady=2)

            # 分隔线
            sep = ctk.CTkFrame(tab, width=2, fg_color="#333")
            sep.pack(side="left", fill="y")

            # 书B 侧
            right_frame = ctk.CTkFrame(tab, fg_color="#10121c")
            right_frame.pack(side="left", fill="both", expand=True, padx=1, pady=1)
            ctk.CTkLabel(right_frame, text="书B",
                         font=("Microsoft YaHei", 11, "bold"),
                         text_color=GREEN).pack(anchor="w", padx=4, pady=(2, 0))
            txt_b = ctk.CTkTextbox(right_frame, fg_color="#10121c",
                                   text_color=TEXT, font=("Consolas", 11))
            txt_b.pack(fill="both", expand=True, padx=2, pady=2)

            self._compare_textboxes[key] = {"a": txt_a, "b": txt_b}

        self._compare_tabview.pack(fill="both", expand=True, padx=20, pady=3)

        # ─── 日志（放最后，减少展开权重） ────
        self.analyze_log = ctk.CTkTextbox(p, fg_color="#10121c", text_color=TEXT,
                                           font=("Consolas", 11))
        self.analyze_log.pack(fill="x", padx=20, pady=3)

    # ══════════════════════════════════════
    # 页面: De-AI
    # ══════════════════════════════════════
    def _build_deslop(self):
        p = self.pages["deslop"]
        self._sect(p, "去AI味")

        # 顶部控件卡
        card = ctk.CTkFrame(p, fg_color=CARD)
        card.pack(fill="x", padx=20, pady=5)

        # 文件选择
        ef = ctk.CTkFrame(card, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=5)
        self.deslop_path_var = ctk.StringVar()
        ctk.CTkEntry(ef, textvariable=self.deslop_path_var,
                     placeholder_text="选择.txt或.md文件...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="浏览", command=self._browse_file_md,
                      width=50).pack(side="right", padx=4)

        # 强度选择 + 选项
        opt = ctk.CTkFrame(card, fg_color="transparent")
        opt.pack(fill="x", padx=15, pady=(2, 5))

        ctk.CTkLabel(opt, text="替换强度:",
                     font=("Microsoft YaHei", 11)).pack(side="left")
        self._deslop_intensity = ctk.StringVar(value="中度")
        ctk.CTkOptionMenu(opt,
            values=["轻度", "中度", "深度"],
            variable=self._deslop_intensity,
            width=100).pack(side="left", padx=5)

        self.deslop_llm_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt, text="使用LLM(更彻底)",
                        variable=self.deslop_llm_var).pack(side="left", padx=10)

        # 按钮组
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(pady=6, padx=15)
        ctk.CTkButton(bf, text="去AI", command=self._start_deslop,
                      fg_color=ACCENT).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="扫描预览",
                      command=self._preview_deslop,
                      fg_color="#9C27B0").pack(side="left", padx=3)

        # ─── 左右对比预览区 ────────────────────────
        preview_card = ctk.CTkFrame(p, fg_color=CARD)
        preview_card.pack(fill="both", expand=True, padx=20, pady=2)

        # 标题栏
        title_bar = ctk.CTkFrame(preview_card, fg_color="transparent")
        title_bar.pack(fill="x", padx=10, pady=(5, 2))
        lt = ctk.CTkFrame(title_bar, fg_color="transparent")
        lt.pack(side="left", fill="x", expand=True)
        lt.pack_propagate(False)
        ctk.CTkLabel(lt, text="原始文本",
                     font=("Microsoft YaHei", 11, "bold"),
                     text_color=ACCENT).pack(anchor="center")
        rt = ctk.CTkFrame(title_bar, fg_color="transparent")
        rt.pack(side="right", fill="x", expand=True)
        rt.pack_propagate(False)
        ctk.CTkLabel(rt, text="处理后文本",
                     font=("Microsoft YaHei", 11, "bold"),
                     text_color=GREEN).pack(anchor="center")

        # 左右内容区
        content_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=5, pady=2)

        # 左栏
        lf = ctk.CTkFrame(content_frame, fg_color="#10121c")
        lf.pack(side="left", fill="both", expand=True)
        self._orig_preview = ctk.CTkTextbox(lf, fg_color="#10121c",
                                              text_color=TEXT,
                                              font=("Consolas", 11))
        self._orig_preview.pack(fill="both", expand=True, padx=2, pady=2)
        self._orig_preview.insert("end", "(点击「扫描预览」查看原始文本中的AI词汇)")
        self._orig_preview.tag_config("ai_word",
                                       background="#5c1a1a",
                                       foreground="#ff6b6b")

        # 分隔线
        dv = ctk.CTkFrame(content_frame, width=2, fg_color="#333")
        dv.pack(side="left", fill="y")

        # 右栏
        rf = ctk.CTkFrame(content_frame, fg_color="#10121c")
        rf.pack(side="left", fill="both", expand=True)
        self._proc_preview = ctk.CTkTextbox(rf, fg_color="#10121c",
                                              text_color=TEXT,
                                              font=("Consolas", 11))
        self._proc_preview.pack(fill="both", expand=True, padx=2, pady=2)
        self._proc_preview.insert("end", "(点击「扫描预览」查看替换结果)")
        self._proc_preview.tag_config("replaced_word",
                                       background="#1a5c1a",
                                       foreground="#6bff6b")

        # 统计区 + 确认按钮
        stats_bar = ctk.CTkFrame(preview_card, fg_color="transparent")
        stats_bar.pack(fill="x", padx=10, pady=(2, 5))
        self._deslop_stats = ctk.CTkLabel(
            stats_bar,
            text="原始字数：- | 处理后字数：- | 替换了-处，涉及-个词汇",
            font=("Microsoft YaHei", 10),
            text_color=PH)
        self._deslop_stats.pack(side="left", padx=5)
        self._confirm_replace_btn = ctk.CTkButton(
            stats_bar, text="确认替换",
            command=self._confirm_replace,
            fg_color=GREEN,
            width=80, height=24,
            font=("Microsoft YaHei", 11))
        self._confirm_replace_btn.pack(side="right", padx=5)
        self._confirm_replace_btn.configure(state="disabled")

        # 日志区
        self.deslop_log = ctk.CTkTextbox(p, fg_color="#10121c", text_color=TEXT,
                                          font=("Consolas", 11))
        self.deslop_log.pack(fill="x", padx=20, pady=3)

    def _pos_to_tk(self, text: str, pos: int) -> str:
        """将字符位置转为 tkinter 的 line.char 格式 (line 1-indexed, char 0-indexed)"""
        before = text[:pos]
        lines = before.split('\n')
        return f"{len(lines)}.{len(lines[-1])}"

    def _preview_deslop(self):
        """扫描预览替换 - 填充左右对比视图"""
        path = self.deslop_path_var.get()
        from core import read_file
        text = read_file(path) if path and os.path.exists(path) else ""
        if not text:
            self._log(self.deslop_log, "错误: 请选择文件或输入文本")
            return

        # 强度映射
        intensity_map = {"轻度": 1, "中度": 2, "深度": 3}
        intensity = intensity_map.get(self._deslop_intensity.get(), 2)

        from deslop import preview_replacements
        pv = preview_replacements(text, intensity=intensity)
        s = pv['stats']

        # --- 左栏：原始文本 + 红色高亮 AI 词 ---
        self._orig_preview.delete("0.0", "end")
        self._orig_preview.insert("end", pv['original'])
        self._orig_preview.tag_remove("ai_word", "0.0", "end")
        orig = pv['original']
        for r in pv['replacements']:
            start_idx = self._pos_to_tk(orig, r['pos'])
            end_idx = self._pos_to_tk(orig, r['pos'] + len(r['old']))
            self._orig_preview.tag_add("ai_word", start_idx, end_idx)

        # --- 右栏：处理后文本 + 绿色高亮替换词 ---
        self._proc_preview.delete("0.0", "end")
        self._proc_preview.insert("end", pv['processed'])
        self._proc_preview.tag_remove("replaced_word", "0.0", "end")
        proc = pv['processed']
        for r in pv['replacements']:
            if r['new']:
                pp = r['processed_pos']
                if pp >= 0 and pp + len(r['new']) <= len(proc):
                    start_idx = self._pos_to_tk(proc, pp)
                    end_idx = self._pos_to_tk(proc, pp + len(r['new']))
                    self._proc_preview.tag_add("replaced_word", start_idx, end_idx)

        # --- 统计 ---
        orig_len = len(orig)
        proc_len = len(proc)
        stats_text = "原始字数：%d | 处理后字数：%d | 替换了%d处，涉及%d个词汇" % (
            orig_len, proc_len, s['total'], s['unique_words'])
        self._deslop_stats.configure(text=stats_text)

        self._log(self.deslop_log, "[%s] %s" % (self._deslop_intensity.get(), stats_text))
        if pv['replacements']:
            self._log(self.deslop_log, "替换明细:")
            for r in pv['replacements'][:10]:
                self._log(self.deslop_log, "  %s → %s | %s" % (r['old'], r['new'] or "(删除)", r['context'][:40]))
            if len(pv['replacements']) > 10:
                self._log(self.deslop_log, "  ... 共 %d 条" % len(pv['replacements']))

        # 启用确认替换按钮
        self._confirm_replace_btn.configure(state="normal")

    def _confirm_replace(self):
        """确认替换：将右栏处理后的文本写回文件"""
        path = self.deslop_path_var.get()
        if not path or not os.path.exists(path):
            self._log(self.deslop_log, "错误: 请选择文件")
            return
        final = self._proc_preview.get("0.0", "end").strip()
        if not final or final == "(点击「扫描预览」查看替换结果)":
            self._log(self.deslop_log, "错误: 请先点击「扫描预览」")
            return
        from core import write_file
        write_file(path, final)
        self._log(self.deslop_log, "✅ 已确认替换并保存到: %s" % path)
        self._confirm_replace_btn.configure(state="disabled")

    def _start_deslop(self):
        path = self.deslop_path_var.get()
        if not path or not os.path.exists(path):
            self._log(self.deslop_log, "错误: 请选择文件")
            return
        self._log(self.deslop_log, "正在去AI味...")
        def task():
            from deslop import deslop_file, rule_based_deslop, preview_replacements
            # 先用规则替换
            intensity_map = {"轻度": 1, "中度": 2, "深度": 3}
            intensity = intensity_map.get(self._deslop_intensity.get(), 2)
            from core import read_file
            text = read_file(path)
            rule_text, rule_count = rule_based_deslop(text, intensity=intensity)
            self._log(self.deslop_log, "[规则引擎] 替换了 %d 处" % rule_count)

            # 更新左右对比预览
            pv = preview_replacements(text, intensity=intensity)
            s = pv['stats']
            def update_preview():
                # 左栏
                self._orig_preview.delete("0.0", "end")
                self._orig_preview.insert("end", pv['original'])
                self._orig_preview.tag_remove("ai_word", "0.0", "end")
                orig = pv['original']
                for r in pv['replacements']:
                    start_idx = self._pos_to_tk(orig, r['pos'])
                    end_idx = self._pos_to_tk(orig, r['pos'] + len(r['old']))
                    self._orig_preview.tag_add("ai_word", start_idx, end_idx)
                # 右栏
                self._proc_preview.delete("0.0", "end")
                self._proc_preview.insert("end", pv['processed'])
                self._proc_preview.tag_remove("replaced_word", "0.0", "end")
                proc = pv['processed']
                for r in pv['replacements']:
                    if r['new']:
                        pp = r['processed_pos']
                        if pp >= 0 and pp + len(r['new']) <= len(proc):
                            start_idx = self._pos_to_tk(proc, pp)
                            end_idx = self._pos_to_tk(proc, pp + len(r['new']))
                            self._proc_preview.tag_add("replaced_word", start_idx, end_idx)
                # 统计
                self._deslop_stats.configure(
                    text="原始字数：%d | 处理后字数：%d | 替换了%d处，涉及%d个词汇" % (
                        len(orig), len(proc), s['total'], s['unique_words']))
            self.root.after(0, update_preview)
            self.root.after(0, lambda: self._confirm_replace_btn.configure(state="normal"))

            # LLM 辅助（深度模式默认开启）
            if self.deslop_llm_var.get() or intensity == 3:
                from deslop import llm_deslop
                self._log(self.deslop_log, "[LLM] 正在改写...")
                final_text = llm_deslop(rule_text)
                if final_text and not final_text.startswith("[错误]"):
                    self._log(self.deslop_log, "LLM 改写完成，点击确认替换保存")
            else:
                self._log(self.deslop_log, "规则替换完成，点击确认替换保存")
        threading.Thread(target=task, daemon=True).start()
    def _gen_cover(self):
        name = self._cover_name.get()
        genre = self._cover_genre.get()
        if not name:
            self._log(self.cover_log, "错误: 请填写书名")
            return
        self._log(self.cover_log, "生成封面提示词...")
        def task():
            from cover import generate_novel_cover
            r = generate_novel_cover(name, genre,
                                     log_callback=lambda m: self._log(self.cover_log, m))
            self._log(self.cover_log, f"\nPrompt:\n\n{r.get('prompt', '')}")
        threading.Thread(target=task, daemon=True).start()

    def _start_batch(self):
        max_workers = int(self.batch_max_workers_var.get())
        self._log(self.batch_log, f"开始批量 (并发: {max_workers} 路)...")
        def task():
            run_batch(batch_file=self.batch_csv_var.get(),
                      log_callback=lambda m: self._log(self.batch_log, m),
                      stop_flag=self.stop_flag,
                      max_workers=max_workers)
            self._log(self.batch_log, "批量完成")
        threading.Thread(target=task, daemon=True).start()

    def _create_sample_csv(self):
        from batch import _create_sample_batch
        path = self.batch_csv_var.get() or "batch.csv"
        _create_sample_batch(path)
        self._log(self.batch_log, f"Created: {os.path.abspath(path)}")

    # ─── 对比分析 ──────────────────────────
    def _browse_compare_a(self):
        path = filedialog.askopenfilename(
            title="选择书A",
            filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._compare_a_var.set(path)

    def _browse_compare_b(self):
        path = filedialog.askopenfilename(
            title="选择书B",
            filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._compare_b_var.set(path)

    def _start_compare(self):
        path_a = self._compare_a_var.get()
        path_b = self._compare_b_var.get()
        if not path_a or not path_b:
            self._log(self.analyze_log, "错误: 请选择两本小说")
            return
        if not os.path.exists(path_a):
            self._log(self.analyze_log, f"错误: 书A文件不存在: {path_a}")
            return
        if not os.path.exists(path_b):
            self._log(self.analyze_log, f"错误: 书B文件不存在: {path_b}")
            return

        self._log(self.analyze_log, "开始对比分析，请稍候...")
        self._compare_tabview.pack(fill="both", expand=True, padx=20, pady=3)
        # 清空旧内容
        for key in self._compare_textboxes:
            for side in ("a", "b"):
                self._compare_textboxes[key][side].delete("0.0", "end")
                self._compare_textboxes[key][side].insert("end", "分析中...")

        threading.Thread(target=self._compare_books,
                         args=(path_a, path_b), daemon=True).start()

    def _compare_books(self, path_a: str, path_b: str):
        """运行两本书的拆书分析并以并排 Tab 展示对比结果"""
        book_a_name = os.path.splitext(os.path.basename(path_a))[0]
        book_b_name = os.path.splitext(os.path.basename(path_b))[0]

        def log(msg):
            self.root.after(0, lambda: self._log(self.analyze_log, msg))

        try:
            # ─── 分析书A ────────────────
            log(f"扫描 {book_a_name}...")
            result_a = analyze_novel(path_a, log_callback=log)
            if "error" in result_a:
                log(f"书A 分析失败: {result_a['error']}")
                return
            out_a = result_a.get("output_dir", "")

            # ─── 分析书B ────────────────
            log(f"扫描 {book_b_name}...")
            result_b = analyze_novel(path_b, log_callback=log)
            if "error" in result_b:
                log(f"书B 分析失败: {result_b['error']}")
                return
            out_b = result_b.get("output_dir", "")

            log(f"\n✅ 两本书分析完成，生成对比视图...")

            # ─── 读取各模块的分析结果 ────
            # 映射：tab key -> (filename, fallback section label)
            tab_map = [
                ("setting", "设定分析.md", "# 设定分析"),
                ("char",    "角色分析.md", "# 角色分析"),
                ("style",   "风格分析.md", "# 风格分析"),
                ("plot",    "剧情分析.md", "# 剧情分析"),
            ]

            for key, fname, label in tab_map:
                content_a = "(无内容)"
                content_b = "(无内容)"

                if out_a:
                    file_a = os.path.join(out_a, fname)
                    if os.path.exists(file_a):
                        with open(file_a, "r", encoding="utf-8") as fh:
                            content_a = fh.read()

                if out_b:
                    file_b = os.path.join(out_b, fname)
                    if os.path.exists(file_b):
                        with open(file_b, "r", encoding="utf-8") as fh:
                            content_b = fh.read()

                # 填充到 UI（必须用 after(0, ...) 从子线程切回主线程）
                self.root.after(0, lambda k=key, ca=content_a, cb=content_b: (
                    self._compare_textboxes[k]["a"].delete("0.0", "end"),
                    self._compare_textboxes[k]["a"].insert("end", ca),
                    self._compare_textboxes[k]["b"].delete("0.0", "end"),
                    self._compare_textboxes[k]["b"].insert("end", cb),
                ))
                log(f"  ✓ {fname} 对比已加载")

            log(f"\n✅ 对比完成 | 书A: {book_a_name}  ↔  书B: {book_b_name}")

        except Exception as e:
            log(f"❌ 对比分析出错: {e}")
            import traceback
            log(traceback.format_exc())

    # ─── 硬件检测 ──────────────────────────
    def _detect_hardware(self):
        from core.utils import detect_gpu_info, get_available_ollama_models
        def task():
            self.root.after(0, lambda: self._detect_gpu_btn.configure(
                state="disabled", text="检测中..."))
            models = get_available_ollama_models()
            if models:
                self._local_model_list = models
                self.root.after(0, lambda: self._local_model_cb.configure(values=models))
            gpu = detect_gpu_info()
            gpu_text = f"{gpu['gpu_type']} | VRAM: {gpu['vram_gb']}G"
            if gpu['recommended_model']:
                self.local_model_var.set(gpu['recommended_model'])
                gpu_text += f" -> {gpu['recommended_model']}"
            self.root.after(0, lambda: (
                self._gpu_label.configure(text=gpu_text),
                self._detect_gpu_btn.configure(state="normal", text="检测硬件并推荐")))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _install_recommended_model(self):
        from core.utils import auto_install_model
        model = self.local_model_var.get()
        if not model:
            return
        def task():
            self.root.after(0, lambda: self._install_btn.configure(
                state="disabled", text="安装中..."))
            def log(msg):
                self.root.after(0, lambda: self._gpu_label.configure(text=msg[:60]))
            result = auto_install_model(model, log_callback=log)
            self.root.after(0, lambda: (
                self._install_btn.configure(state="normal", text="安装推荐模型"),
                self._gpu_label.configure(
                    text=("完成" if result else "失败") + ": " + str(model))))
            if result:
                from core.utils import get_available_ollama_models
                models = get_available_ollama_models()
                if models:
                    self._local_model_list = models
                    self.root.after(0, lambda: self._local_model_cb.configure(values=models))
        import threading
        threading.Thread(target=task, daemon=True).start()

    # ══════════════════════════════════════
    # 页面: Output (导出中心)
    # ══════════════════════════════════════
    def _build_output(self):
        p = self.pages["output"]
        self._sect(p, "导出中心")

        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=20, pady=3)

        # ─── 导出卡片 ────────────────────────
        export_card = ctk.CTkFrame(scroll, fg_color=CARD)
        export_card.pack(fill="x", pady=3)

        ctk.CTkLabel(export_card, text="导出中心",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(8, 2))

        ctk.CTkLabel(export_card,
                     text="选择小说目录，导出为多种格式",
                     font=("Microsoft YaHei", 11), text_color=PH,
                     wraplength=600).pack(anchor="w", padx=15, pady=1)

        # 目录选择
        dir_frame = ctk.CTkFrame(export_card, fg_color="transparent")
        dir_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(dir_frame, text="小说目录:",
                     font=("Microsoft YaHei", 12)).pack(side="left")
        self._export_dir_var = ctk.StringVar(value=self._book_dir if self._book_dir else "")
        self._export_dir_entry = ctk.CTkEntry(
            dir_frame, textvariable=self._export_dir_var,
            placeholder_text="选择小说目录...", width=400)
        self._export_dir_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(dir_frame, text="浏览",
                      command=self._browse_export_dir,
                      width=55).pack(side="right")

        # 书籍信息
        info_frame = ctk.CTkFrame(export_card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=2)
        self._export_info_label = ctk.CTkLabel(
            info_frame, text="当前无选中目录",
            font=("Microsoft YaHei", 11), text_color=PH)
        self._export_info_label.pack(anchor="w")

        # 格式按钮组
        btn_frame = ctk.CTkFrame(export_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=8)

        fmt_buttons = [
            ("TXT", "#4CAF50", "_export_single", "txt"),
            ("EPUB", "#2196F3", "_export_single", "epub"),
            ("PDF", "#FF5722", "_export_single", "pdf"),
            ("DOCX", "#9C27B0", "_export_single", "docx"),
            ("HTML", "#FF9800", "_export_single", "html"),
        ]
        for label, color, cmd, fmt in fmt_buttons:
            btn = ctk.CTkButton(
                btn_frame, text=label, width=80, height=36,
                fg_color=color, text_color="white",
                font=("Microsoft YaHei", 13, "bold"),
                command=lambda f=fmt: self._export_file(f))
            btn.pack(side="left", padx=4)

        # 全部导出按钮
        ctk.CTkButton(btn_frame, text="导出全部格式",
                      command=self._export_all_formats,
                      fg_color=ACCENT,
                      font=("Microsoft YaHei", 13, "bold"),
                      width=130, height=36).pack(side="left", padx=15)

        # 打开目录按钮
        ctk.CTkButton(btn_frame, text="打开目录",
                      command=self._open_export_dir,
                      fg_color=BLUE, width=90, height=36).pack(side="right", padx=4)

        # ─── 日志区 ──────────────────────────
        ctk.CTkLabel(scroll, text="导出日志",
                     font=("Microsoft YaHei", 12, "bold"),
                     text_color=BLUE).pack(anchor="w", pady=(8, 2))

        self._export_log = ctk.CTkTextbox(scroll, fg_color="#10121c",
                                           text_color=TEXT, font=("Consolas", 11),
                                           height=300)
        self._export_log.pack(fill="both", expand=True)
        self._export_log.insert("end", "（选择小说目录后点击格式按钮开始导出）\n")

        # 绑定目录变更事件
        self._export_dir_var.trace_add("write", self._on_export_dir_change)

    def _browse_export_dir(self):
        """浏览选择小说目录"""
        d = filedialog.askdirectory(title="选择小说目录")
        if d:
            self._export_dir_var.set(d)

    def _on_export_dir_change(self, *_):
        """目录变更时更新书籍信息"""
        d = self._export_dir_var.get().strip()
        if d and os.path.exists(d) and os.path.isdir(d):
            ch_dir = os.path.join(d, "正文")
            if os.path.exists(ch_dir):
                info = _get_book_info(d)
                self._export_info_label.configure(
                    text=f"章节: {info['chapters']} 章  |  字数: {info['words']:,} 字")
            else:
                self._export_info_label.configure(
                    text="所选目录不是有效的小说目录（缺少「正文」文件夹）",
                    text_color=ORANGE)
        else:
            self._export_info_label.configure(text="当前无选中目录", text_color=PH)

    def _open_export_dir(self):
        """打开导出目录"""
        d = self._export_dir_var.get().strip()
        if d and os.path.exists(d):
            self._open_dir(d)

    def _log_export(self, msg):
        """向导出日志追加消息（线程安全）"""
        ts = datetime.now().strftime("%H:%M:%S")
        def do_log():
            self._export_log.insert("end", f"[{ts}] {msg}\n")
            self._export_log.see("end")
        self.root.after(0, do_log)

    def _export_file(self, fmt: str):
        """导出单个格式"""
        d = self._export_dir_var.get().strip()
        if not d or not os.path.exists(d):
            self._log_export("错误: 请选择有效的小说目录")
            return
        ch_dir = os.path.join(d, "正文")
        if not os.path.exists(ch_dir):
            self._log_export("错误: 所选目录缺少「正文」文件夹")
            return

        export_map = {
            "txt": export_to_txt,
            "epub": export_to_epub,
            "pdf": export_to_pdf,
            "docx": export_to_docx,
            "html": export_to_html,
        }
        func = export_map.get(fmt)
        if not func:
            self._log_export(f"错误: 不支持的格式 {fmt}")
            return

        def task():
            try:
                self._log_export(f"正在导出 {fmt.upper()}...")
                result = func(d, log_callback=lambda m: self._log_export(m))
                if result:
                    self._log_export(f"✅ {fmt.upper()} 导出完成: {result}")
                else:
                    self._log_export(f"⚠️ {fmt.upper()} 导出失败")
            except Exception as e:
                self._log_export(f"❌ 导出 {fmt.upper()} 出错: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _export_all_formats(self):
        """导出全部支持的格式"""
        d = self._export_dir_var.get().strip()
        if not d or not os.path.exists(d):
            self._log_export("错误: 请选择有效的小说目录")
            return
        ch_dir = os.path.join(d, "正文")
        if not os.path.exists(ch_dir):
            self._log_export("错误: 所选目录缺少「正文」文件夹")
            return

        def task():
            self._log_export("开始导出全部格式...")
            export_funcs = [
                ("TXT", export_to_txt),
                ("EPUB", export_to_epub),
                ("PDF", export_to_pdf),
                ("DOCX", export_to_docx),
                ("HTML", export_to_html),
            ]
            for label, func in export_funcs:
                try:
                    self._log_export(f"正在导出 {label}...")
                    result = func(d, log_callback=lambda m: self._log_export(m))
                    if result:
                        self._log_export(f"✅ {label} 完成")
                    else:
                        self._log_export(f"⚠️ {label} 未导出")
                except Exception as e:
                    self._log_export(f"❌ {label} 出错: {e}")
            self._log_export("━━━ 全部格式导出完毕 ━━━")
            # 自动打开目录
            self._open_dir(d)

        threading.Thread(target=task, daemon=True).start()

    def _open_dir(self, path: str):
        """在资源管理器中打开目录"""
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception:
                pass

    # ─── 状态栏 ────────────────────────────
    def _build_status_bar(self):
        self._status_bar = ctk.CTkFrame(self.root, fg_color=SB, height=28, corner_radius=0)
        self._status_bar.pack(side="bottom", fill="x")
        self._status_bar.pack_propagate(False)

        self._sb_left = ctk.CTkLabel(self._status_bar,
                                       text="[LLM: --]",
                                       font=("Consolas", 10), text_color=PH)
        self._sb_left.pack(side="left", padx=10)

        self._sb_center = ctk.CTkLabel(self._status_bar,
                                         text="[今日字数: 0]",
                                         font=("Consolas", 10), text_color=PH)
        self._sb_center.pack(side="left", padx=10)

        self._sb_right = ctk.CTkLabel(self._status_bar,
                                        text="[总耗时: 0s]",
                                        font=("Consolas", 10), text_color=PH)
        self._sb_right.pack(side="right", padx=10)

    def _update_status_bar(self):
        """刷新状态栏信息"""
        # LLM 状态
        cfg = load_config()
        use_local = cfg.get("use_local", False)
        if use_local:
            provider = "ollama"
            model = cfg.get("local_llm", {}).get("model_name", "?")
        else:
            provider = cfg.get("llm", {}).get("provider", "?")
            model = cfg.get("llm", {}).get("model_name", "?")
        self._sb_left.configure(text=f"[LLM: {provider}/{model}]")

        # 今日字数
        daily_words = self._get_daily_word_count()
        self._sb_center.configure(text=f"[今日字数: {daily_words:,}]")

        # 总耗时（从运行中的进度读取）
        elapsed = self.progress.get("elapsed_seconds", 0)
        self._sb_right.configure(text=f"[耗时: {elapsed}s]")

    def _schedule_status_bar(self):
        self._update_status_bar()
        self.root.after(10000, self._schedule_status_bar)

    def _get_daily_word_count(self) -> int:
        """计算 output/ 目录下各章节文件的总字数（当日）"""
        try:
            output_dir = get_output_dir()
        except Exception:
            return 0
        if not os.path.exists(output_dir):
            return 0
        total = 0
        today = datetime.now().strftime("%Y-%m-%d")
        for root_dir, dirs, files in os.walk(output_dir):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime.strftime("%Y-%m-%d") == today:
                        content = read_file(fpath)
                        total += count_words(content)
                except Exception:
                    continue
        return total

    def _browse_file_md(self):
        f = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")])
        if f and hasattr(self, 'deslop_path_var'):
            self.deslop_path_var.set(f)

    def _build_cover(self):
        p = self.pages["cover"]
        self._sect(p, "封面生成")
        card = ctk.CTkFrame(p, fg_color=CARD)
        card.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(card, text="书名:",
                     font=("Microsoft YaHei", 11)).pack(anchor="w", padx=15, pady=(10, 2))
        self._cover_name = ctk.StringVar()
        ctk.CTkEntry(card, textvariable=self._cover_name,
                     placeholder_text="输入书名").pack(fill="x", padx=15, pady=2)

        ctk.CTkLabel(card, text="类型:",
                     font=("Microsoft YaHei", 11)).pack(anchor="w", padx=15, pady=(5, 2))
        self._cover_genre = ctk.StringVar(value="玄幻")
        ctk.CTkOptionMenu(card,
            values=["玄幻", "都市", "奇幻", "科幻", "历史", "悬疑", "武侠", "言情"],
            variable=self._cover_genre).pack(fill="x", padx=15, pady=2)

        ctk.CTkButton(card, text="生成封面提示词",
                      command=self._gen_cover,
                      fg_color=ACCENT).pack(pady=15)

    def _build_review(self):
        p = self.pages["review"]
        self._sect(p, "审稿 - 一致性核验 + 毒点检测")

        # 选择区域
        card = ctk.CTkFrame(p, fg_color=CARD)
        card.pack(fill="x", padx=20, pady=5)

        # 目录选择
        ef = ctk.CTkFrame(card, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=5)
        self.review_dir_var = ctk.StringVar()
        ctk.CTkEntry(ef, textvariable=self.review_dir_var,
                     placeholder_text="选择小说目录（含正文/文件夹）...").pack(
                         side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="浏览", command=lambda: self.review_dir_var.set(
            filedialog.askdirectory(title="选择小说目录") or self.review_dir_var.get()
        ), width=50).pack(side="right", padx=4)

        # 按钮组
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(pady=6, padx=15)
        ctk.CTkButton(bf, text="一致性检查", command=self._run_consistency,
                      fg_color=ACCENT).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="毒点检测", command=self._run_toxicity,
                      fg_color="#9C27B0").pack(side="left", padx=3)
        ctk.CTkButton(bf, text="AI修复", command=self._fix_with_ai,
                      fg_color=GREEN).pack(side="left", padx=3)
        ctk.CTkLabel(bf, text="选择小说目录 -> 检查 -> AI一键修复",
                     font=("Microsoft YaHei", 10), text_color=PH).pack(side="left", padx=10)

        # 结果区
        self.review_result = ctk.CTkTextbox(p, fg_color="#10121c",
                                             text_color=TEXT,
                                             font=("Consolas", 11))
        self.review_result.pack(fill="both", expand=True, padx=20, pady=5)
        self.review_result.insert("end", "（选择小说目录后点按钮开始审稿）")

    def _run_consistency(self):
        d = self.review_dir_var.get().strip()
        if not d or not os.path.isdir(d):
            self.review_result.delete("0.0", "end")
            self.review_result.insert("end", "错误: 请选择有效的小说目录")
            return
        self.review_result.delete("0.0", "end")
        self.review_result.insert("end", "一致性检查中...")
        self._review_report = None
        def task():
            from review import consistency_check
            result = consistency_check(d, log_callback=lambda m: None)
            self._review_report = result
            self.root.after(0, lambda: (
                self.review_result.delete("0.0", "end"),
                self.review_result.insert("end", result or "未发现问题")))
        threading.Thread(target=task, daemon=True).start()

    def _run_toxicity(self):
        d = self.review_dir_var.get().strip()
        if not d or not os.path.isdir(d):
            self.review_result.delete("0.0", "end")
            self.review_result.insert("end", "错误: 请选择有效的小说目录")
            return
        self.review_result.delete("0.0", "end")
        self.review_result.insert("end", "毒点检测中...")
        from core import read_file, write_file
        ch_dir = os.path.join(d, "正文")
        self._toxicity_results = []
        def task():
            from review import toxicity_check
            report = []
            if os.path.exists(ch_dir):
                for f in sorted(os.listdir(ch_dir)):
                    if f.endswith('.md') or f.endswith('.txt'):
                        text = read_file(os.path.join(ch_dir, f))
                        r = toxicity_check(text, log_callback=lambda m: None)
                        if r:
                            report.append(f"=== {f} ===\n{r}")
                            self._toxicity_results.append({"file": f, "text": text, "issues": r})
            result = "\n\n".join(report) if report else "未检测到明显毒点"
            self.root.after(0, lambda: (
                self.review_result.delete("0.0", "end"),
                self.review_result.insert("end", result)))
        threading.Thread(target=task, daemon=True).start()

    def _fix_with_ai(self):
        d = self.review_dir_var.get().strip()
        if not d or not os.path.isdir(d):
            return
        from core import read_file, write_file
        from core.llm import llm_invoke_ada
        ch_dir = os.path.join(d, "正文")
        if not os.path.exists(ch_dir):
            return
        self.review_result.delete("0.0", "end")
        self.review_result.insert("end", "AI批量修复中...\n")
        def task():
            fixed = 0
            for f in sorted(os.listdir(ch_dir)):
                if not (f.endswith('.md') or f.endswith('.txt')):
                    continue
                text = read_file(os.path.join(ch_dir, f))
                prompt = (
                    "你是一位专业的小说编辑。请修复以下章节中所有问题："
                    "1. 去除圣母行为（让角色为自己的选择付出代价）\n"
                    "2. 去除降智操作（给反派合理动机）\n"
                    "3. 去除机械降神（提前埋伏笔或删掉突兀救兵）\n"
                    "4. 减少主角话痨（用动作代替内心独白）\n\n"
                    "保留原文风格和情节走向，只修复上述问题。\n"
                    "直接输出修复后的完整内容：\n\n")
                result = llm_invoke_ada(prompt + text[:4000],
                    system_msg="你是一位资深网络小说编辑，擅长修复毒点。")
                if result and not result.startswith("[错误"):
                    write_file(os.path.join(ch_dir, f), result)
                    fixed += 1
                    self.root.after(0, lambda m=f: self.review_result.insert("end", f"  ✓ {m}\n"))
            self.root.after(0, lambda: self.review_result.insert("end", f"\nAI修复完成，共处理 {fixed} 章"))
        threading.Thread(target=task, daemon=True).start()

    def _card_lbl(self, parent, title):
        ctk.CTkLabel(parent, text=title,
                     font=("Microsoft YaHei", 13, "bold"),
                     text_color=BLUE,
                     anchor="w").pack(fill="x", padx=10, pady=(10, 2))

    def _update_model_visibility(self):
        provider = self.cloud_provider_var.get()
        hide = provider != "custom"
        if hide:
            self._cloud_f.pack(fill="x", padx=15, pady=2)
        else:
            self._cloud_f.pack(fill="x", padx=15, pady=2)

    def _on_provider_change(self, choice):
        templates = {
            "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
            "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
            "dashscope": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
            "ollama": ("http://localhost:11434/v1", "qwen2.5:7b"),
        }
        if choice in templates:
            url, model = templates[choice]
            self.cloud_url_var.set(url)
            self.cloud_model_var.set(model)

    def _toggle_model(self):
        use_local = self.use_local_var.get()
        if use_local:
            self._cloud_f.pack_forget()
            self._local_f.pack(fill="x", padx=15, pady=2)
        else:
            self._local_f.pack_forget()
            self._cloud_f.pack(fill="x", padx=15, pady=2)

    def _check_ollama(self):
        from core.utils import check_ollama_running
        def task():
            ok = check_ollama_running()
            self.root.after(0, lambda: self.ollama_status.configure(
                text="Ollama OK" if ok else "Ollama offline",
                text_color=GREEN if ok else ORANGE))
        threading.Thread(target=task, daemon=True).start()

    def _validate_on_startup(self):
        from core import load_config
        cfg = load_config()
        api_key = cfg.get("api", {}).get("api_key", "")
        if not api_key:
            msg = ctk.CTkToplevel(self.root)
            msg.title("首次使用")
            msg.geometry("400x200")
            ctk.CTkLabel(msg, text="欢迎使用NovelFactory\n\n请先在设置页配置API Key",
                         font=("Microsoft YaHei", 14)).pack(pady=30)
            ctk.CTkButton(msg, text="去设置",
                          command=lambda: (msg.destroy(), self._show_page("settings"))
                          ).pack(pady=10)
        self._update_status_bar()

    def _browse_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_dir_var.set(d)

    def _browse_batch_csv(self):
        f = filedialog.askopenfilename(title="选择CSV", filetypes=[("CSV", "*.csv")])
        if f:
            self.batch_csv_var.set(f)

    def _browse_dir_2(self):
        d = filedialog.askdirectory(title="选择小说目录")
        if d:
            self.analyze_dir_var.set(d)

    def _browse_file(self):
        f = filedialog.askopenfilename(title="选择文件",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")])
        if f:
            self.analyze_file_var.set(f)

    def _save_settings(self):
        from core import save_config, load_config
        cfg = load_config()
        cfg["llm"] = {
            "provider": self.cloud_provider_var.get(),
            "api_key": self.cloud_key_var.get(),
            "base_url": self.cloud_url_var.get(),
            "model_name": self.cloud_model_var.get(),
        }
        cfg["local_llm"] = {
            "base_url": self.local_url_var.get(),
            "model_name": self.local_model_var.get(),
        }
        cfg["use_local"] = self.use_local_var.get()
        cfg["output_dir"] = self.output_dir_var.get()
        save_config()
        log_target = getattr(self, 'settings_log', None) or getattr(self, 'deslop_log', None)
        if log_target:
            self._log(log_target, "设置已保存")

    def _start_analyze(self):
        path = self.analyze_file_var.get()
        if not path or not os.path.exists(path):
            self._log(self.analyze_log, "请选择文件")
            return
        self._log(self.analyze_log, "分析中...")
        def task():
            from analyze import analyze_novel
            result = analyze_novel(path, log_callback=lambda m: self._log(self.analyze_log, m))
            self._log(self.analyze_log, f"分析完成: {len(result.get('chapters',[]))} 章")
        threading.Thread(target=task, daemon=True).start()

    def _start_batch_analyze(self):
        d = self.analyze_dir_var.get()
        if not d or not os.path.exists(d):
            self._log(self.analyze_log, "请选择目录")
            return
        self._log(self.analyze_log, "批量分析中...")
        def task():
            from analyze import analyze_novel
            for f in os.listdir(d):
                if f.endswith('.txt') or f.endswith('.md'):
                    fp = os.path.join(d, f)
                    self._log(self.analyze_log, f"分析: {f}")
                    analyze_novel(fp, log_callback=lambda m: None)
            self._log(self.analyze_log, "批量分析完成")
        threading.Thread(target=task, daemon=True).start()


    # 书架
    def _build_bookshelf(self):
        """仪表盘 — 默认页：项目列表 + 章节看板"""
        p = self.pages["bookshelf"]

        # ── 顶部卡片区 ──
        top = ctk.CTkFrame(p, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        top.pack(fill="x", padx=20, pady=(8,4))

        top_inner = ctk.CTkFrame(top, fg_color="transparent")
        top_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkButton(top_inner, text="▶  继续上次写作",
                      font=("Microsoft YaHei", 15, "bold"),
                      fg_color=ACCENT, text_color=BG, hover_color=ACCENT_HOVER,
                      height=42, corner_radius=8, width=200,
                      command=self._quick_continue_last).pack(side="left", padx=4)

        ctk.CTkButton(top_inner, text="+ 新建项目",
                      font=("Microsoft YaHei", 13),
                      fg_color=CARD_HOVER, text_color=TEXT,
                      height=42, corner_radius=8, width=120,
                      command=lambda: self._show_page("create")).pack(side="left", padx=4)

        ctk.CTkButton(top_inner, text="← 从拆书创建",
                      font=("Microsoft YaHei", 12),
                      fg_color="transparent", text_color=TEXT_DIM,
                      height=42, corner_radius=8, width=130,
                      command=lambda: self._show_page("analyze")).pack(side="left", padx=4)

        ctk.CTkButton(top_inner, text="↻ 刷新",
                      font=("Microsoft YaHei", 12),
                      fg_color="transparent", text_color=TEXT_DIM,
                      height=42, corner_radius=8, width=70,
                      command=self._refresh_bookshelf).pack(side="right", padx=4)

        # ── 项目滚动区 ──
        self._shelf_list_frame = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self._shelf_list_frame.pack(fill="both", expand=True, padx=20, pady=4)

        # 日志区（底部）
        self._shelf_log = ctk.CTkTextbox(p, fg_color=CARD, text_color=TEXT,
                                         font=("Consolas", 11), height=120,
                                         border_width=0, corner_radius=8)
        self._shelf_log.pack(fill="x", padx=20, pady=(0,8))
        self._shelf_log.insert("end", "仪表盘——显示所有项目，点击即可续写或导出。\n")

        self._shelf_dir_var = ctk.StringVar(value=self._book_dir if self._book_dir else "")
        self.root.after(300, self._refresh_bookshelf)

    def _refresh_bookshelf(self):
        import threading
        def task():
            projects = discover_projects()
            # 同时获取每个项目的章节队列
            enriched = []
            for proj in projects:
                try:
                    from dashboard import load_chapter_queue
                    q = load_chapter_queue(proj["path"])
                    proj["queue"] = q
                except Exception:
                    proj["queue"] = {"chapters": [], "status": "idle"}
                enriched.append(proj)
            self.root.after(0, lambda: self._render_project_list(enriched))
        threading.Thread(target=task, daemon=True).start()

    def _render_project_list(self, projects):
        for w in self._shelf_list_frame.winfo_children():
            w.destroy()

        if not projects:
            empty = ctk.CTkFrame(self._shelf_list_frame, fg_color="transparent")
            empty.pack(pady=40)
            ctk.CTkLabel(empty, text="还没有项目",
                         font=("Microsoft YaHei", 14), text_color=TEXT_DIM).pack()
            ctk.CTkLabel(empty, text="点击「新建项目」开始创作",
                         font=("Microsoft YaHei", 11), text_color=PH).pack(pady=(4,0))
            return

        for proj in projects:
            # Card with left accent strip
            card_outer = ctk.CTkFrame(self._shelf_list_frame, fg_color="transparent")
            card_outer.pack(fill="x", pady=2, padx=2)
            
            queue = proj.get("queue", {}).get("chapters", [])
            done = sum(1 for c in queue if c.get("status") == "done")
            total = len(queue)
            generating = sum(1 for c in queue if c.get("status") == "generating")
            
            # Determine accent color based on status
            if generating > 0:
                accent_strip = ORANGE
            elif total > 0 and done == total:
                accent_strip = GREEN
            elif total > 0 and done > 0:
                accent_strip = ACCENT
            else:
                accent_strip = PH
            
            strip = ctk.CTkFrame(card_outer, width=4, fg_color=accent_strip, corner_radius=0)
            strip.pack(side="left", fill="y", padx=(0, 0))
            
            card = ctk.CTkFrame(card_outer, fg_color=CARD, corner_radius=8, border_width=1, border_color=BORDER)
            card.pack(side="left", fill="x", expand=True)

            # Row 1: Title + genre badge + chapter dots
            row1 = ctk.CTkFrame(card, fg_color="transparent")
            row1.pack(fill="x", padx=14, pady=(10, 2))

            name = proj.get("topic") or proj["name"]
            ctk.CTkLabel(row1, text=name[:22],
                         font=("Microsoft YaHei", 14, "bold"),
                         text_color=TEXT).pack(side="left")

            genre = proj.get("genre", "")
            if genre:
                tag = ctk.CTkFrame(row1, fg_color=CARD_HOVER, corner_radius=4)
                tag.pack(side="left", padx=8)
                ctk.CTkLabel(tag, text=genre,
                             font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(padx=6, pady=1)

            # Mini chapter dots on the right
            if total > 0 and total <= 60:
                dots_frame = ctk.CTkFrame(row1, fg_color="transparent")
                dots_frame.pack(side="right")
                show_max = min(total, 40)
                step = max(1, total // 40)
                for idx in range(0, total, step):
                    if idx >= show_max:
                        ctk.CTkLabel(dots_frame, text="...",
                                     font=("Segoe UI", 7), text_color=PH).pack(side="left")
                        break
                    ch = queue[idx] if idx < len(queue) else {}
                    st = ch.get("status", "pending")
                    colors = {"done": GREEN, "generating": ORANGE, "pending": PH, "failed": RED}
                    dot = ctk.CTkLabel(dots_frame, text="o",
                                       font=("Segoe UI", 8),
                                       text_color=colors.get(st, PH))
                    dot.pack(side="left", padx=1)

            # Row 2: Progress bar + stats + update time
            row2 = ctk.CTkFrame(card, fg_color="transparent")
            row2.pack(fill="x", padx=14, pady=(2, 6))

            if total > 0:
                bar = ctk.CTkProgressBar(row2, width=180, height=5, corner_radius=3,
                                         fg_color=CARD_HOVER, progress_color=ACCENT)
                bar.pack(side="left", padx=(0, 8))
                bar.set(done / max(total, 1))
                status_text = f"{done}/{total}章"
                if generating > 0:
                    status_text += f"  (生成中...)"
                ctk.CTkLabel(row2, text=status_text,
                             font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="left")
            else:
                chap_count = proj.get("chapters", 0)
                word_count = proj.get("words", 0)
                ctk.CTkLabel(row2, text=f"计划{chap_count}章 · 已写{word_count:,}字",
                             font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="left")

            # Show platform/author if available
            path = proj.get("path", "")
            if path:
                try:
                    import json
                    mp = os.path.join(path, "项目元数据.json")
                    if os.path.exists(mp):
                        bm = json.loads(open(mp, "r", encoding="utf-8").read())
                        platform = bm.get("platform", "")
                        author = bm.get("author", "")
                        extra_info = []
                        if platform:
                            extra_info.append(platform)
                        if author:
                            extra_info.append(f"@{author}")
                        if extra_info:
                            ctk.CTkLabel(row2, text=" | ".join(extra_info),
                                         font=("Microsoft YaHei", 9), text_color=ACCENT_LIGHT).pack(side="left", padx=10)
                except Exception:
                    pass

            ctk.CTkLabel(row2, text=f"更新: {proj.get('last_update','-')[:10]}",
                         font=("Segoe UI", 10), text_color=PH).pack(side="right")

            # Row 3: Action buttons
            row3 = ctk.CTkFrame(card, fg_color="transparent")
            row3.pack(fill="x", padx=14, pady=(0, 10))

            book_path = proj["path"]
            ctk.CTkButton(row3, text="▶ 续写", width=75, height=30,
                          fg_color=ACCENT, text_color=BG, corner_radius=6,
                          font=("Microsoft YaHei", 11, "bold"),
                          command=lambda p=book_path: self._quick_continue(p)).pack(side="left", padx=2)

            ctk.CTkButton(row3, text="▦ 看板", width=75, height=30,
                          fg_color=CARD_HOVER, text_color=TEXT, corner_radius=6,
                          font=("Microsoft YaHei", 11),
                          command=lambda p=book_path: self._show_chapter_board(p)).pack(side="left", padx=2)

            ctk.CTkButton(row3, text="TXT", width=55, height=30,
                          fg_color=BLUE, text_color="white", corner_radius=6,
                          font=("Segoe UI", 10, "bold"),
                          command=lambda p=book_path: self._quick_export(p, "txt")).pack(side="left", padx=2)

            ctk.CTkButton(row3, text="Obsidian", width=65, height=30,
                          fg_color="#7c4dff", text_color="white", corner_radius=6,
                          font=("Microsoft YaHei", 10),
                          command=lambda p=book_path: self._open_in_obsidian(p)).pack(side="right", padx=2)

            ctk.CTkButton(row3, text="删除", width=55, height=30,
                          fg_color="transparent", text_color=RED, corner_radius=6,
                          font=("Microsoft YaHei", 10),
                          command=lambda p=book_path: self._delete_project(p)).pack(side="right", padx=2)


    def _show_chapter_board(self, book_dir):
        """章节看板：展示所有章节状态和评分"""
        from dashboard import load_chapter_queue
        queue = load_chapter_queue(book_dir)
        chapters = queue.get("chapters", [])

        self._shelf_log.delete("1.0", "end")
        if not chapters:
            self._shelf_log.insert("end", "暂无章节数据\n")
            return

        sep = "-" * 64
        self._shelf_log.insert("end", "+" + sep + "+\n")
        self._shelf_log.insert("end", "| 章节         状态     字数     评分   质量                    |\n")
        self._shelf_log.insert("end", "|" + sep + "|\n")

        for ch in chapters:
            num = ch["chapter_num"]
            sm = {"done": "[OK]", "generating": "[..]", "pending": "[  ]", "failed": "[XX]"}
            status = sm.get(ch.get("status", "pending"), "[?]")
            words = ch.get("words", 0)
            score = ch.get("score")
            if isinstance(score, dict):
                total_s = score.get("total", 0)
                stars = score.get("star", "-")
            else:
                total_s = 0
                stars = "-"
            detail_str = ""
            if isinstance(score, dict) and score.get("details"):
                detail_str = "; ".join(score["details"][:2])
            self._shelf_log.insert("end",
                "| Ch%03d  %-6s  %5d字  %3d分  %-25s|\n" % (num, status, words, total_s, str(stars)[:25]))

        done = sum(1 for c in chapters if c.get("status") == "done")
        total = len(chapters)
        self._shelf_log.insert("end", "|" + sep + "|\n")
        self._shelf_log.insert("end", "| Completed: %d/%d chapters" % (done, total) + " " * max(1, 64-18-len(str(done))-len(str(total))) + "|\n")
        self._shelf_log.insert("end", "+" + sep + "+\n")
    def _quick_continue(self, book_dir):
        self._shelf_dir_var.set(book_dir)
        self._book_dir = book_dir
        self._continue_from_shelf()

    def _quick_export(self, book_dir, fmt):
        self._shelf_dir_var.set(book_dir)
        self._export_from_shelf(fmt)

    def _delete_project(self, book_dir):
        """删除项目（确认后）"""
        import shutil, messagebox
        name = os.path.basename(book_dir)
        ok = messagebox.askyesno("删除项目", f"确定删除「{name}」？\n这个操作不可撤销。")
        if ok:
            try:
                shutil.rmtree(book_dir)
                self._log(self._shelf_log, f"✓ 已删除: {name}")
                self._refresh_bookshelf()
            except Exception as e:
                self._log(self._shelf_log, f"✗ 删除失败: {e}")

    def _quick_continue_last(self):
        projects = discover_projects()
        if not projects:
            self._show_page("create")
            return
        last = projects[0]
        self._book_dir = last["path"]
        self._continue_from_shelf()

    def _browse_shelf_dir(self):
        d = filedialog.askdirectory(title="选择小说目录")
        if d:
            self._shelf_dir_var.set(d)
            self._book_dir = d
            self._refresh_bookshelf()

    def _continue_from_shelf(self):
        d = self._shelf_dir_var.get().strip()
        if not d or not os.path.exists(d):
            self._log(self._shelf_log, "请选择有效的小说目录")
            return
        self._book_dir = d
        from novel import continue_novel
        def task():
            try:
                self._log(self._shelf_log, "开始续写...")
                result = continue_novel(
                    book_dir=d, additional_chapters=10,
                    log_callback=lambda m: self._log(self._shelf_log, m),
                    stop_flag=self.stop_flag,
                    progress_callback=self._on_novel_progress)
                self._log(self._shelf_log, f"续写完成: +{result.get('chapters_added', 0)}章")
                self.root.after(2000, self._refresh_bookshelf)
            except Exception as e:
                self._log(self._shelf_log, f"续写失败: {e}")
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _export_from_shelf(self, fmt: str):
        d = self._shelf_dir_var.get().strip()
        if not d or not os.path.exists(d):
            self._log(self._shelf_log, "请选择有效的小说目录")
            return
        from export import export_to_txt
        def task():
            try:
                self._log(self._shelf_log, f"导出 {fmt.upper()} ...")
                out = export_to_txt(d, log_callback=lambda m: self._log(self._shelf_log, m))
                self._log(self._shelf_log, f"导出完成: {out}")
            except Exception as e:
                self._log(self._shelf_log, f"导出失败: {e}")
        import threading
        threading.Thread(target=task, daemon=True).start()


    # ══════════════════════════════════════
    # 5个新功能模块页面
    # ══════════════════════════════════════
# Inserts at line 3030 - 5 new page build methods
    # ══════════════════════════════════════
    # 页面: AI交互式编辑器
    # ══════════════════════════════════════
    def _build_editor_page(self):
        p = self.pages["editor"]
        self._sect(p, "AI交互式编辑器")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Chapter input
        ctk.CTkLabel(scroll, text="原文章节（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._editor_text = ctk.CTkTextbox(scroll, height=200, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_text.pack(fill="x", pady=(0, 8))

        # Instruction
        ctk.CTkLabel(scroll, text="修改指令（自然语言描述）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._editor_instruction = ctk.CTkTextbox(scroll, height=60, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_instruction.pack(fill="x", pady=(0, 8))
        self._editor_instruction.insert("1.0", "例如：打斗太软了，加点狠劲 / 对话不够自然 / 加一段心理描写")

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        ctk.CTkButton(bf, text="AI改稿", command=self._run_editor_edit,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Microsoft YaHei", 13), width=140).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="编辑对话", command=self._run_dialogue_edit,
                      fg_color=BLUE, hover_color="#3b82f6", width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="插入场景", command=self._run_add_scene,
                      fg_color=PURPLE, width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="撤销", command=self._editor_undo,
                      fg_color="#52525b", width=80).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="重做", command=self._editor_redo,
                      fg_color="#52525b", width=80).pack(side="left", padx=3)

        # Result
        ctk.CTkLabel(scroll, text="改稿结果", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w", pady=(8, 4))
        self._editor_result = ctk.CTkTextbox(scroll, height=280, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._editor_result.pack(fill="both", expand=True)

        # Status
        self._editor_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._editor_status.pack(anchor="w", pady=(4, 8))

        # Init edit history
        self._edit_history = EditHistory()

    def _run_editor_edit(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text or not instruction:
            self._editor_status.configure(text="请填写原文和修改指令")
            return
        self._edit_history.push(text, instruction)
        self._editor_status.configure(text="AI改稿中...")
        def task():
            result = edit_chapter(text, instruction)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_dialogue_edit(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text:
            self._editor_status.configure(text="请填写原文")
            return
        if "角色" not in instruction and "对话" not in instruction:
            self._editor_status.configure(text='指令中请包含"角色名"和"语气要求"')
            return
        self._editor_status.configure(text="编辑对话中...")
        def task():
            parts = instruction.split("，")
            char = parts[0] if parts else ""
            tone = parts[1] if len(parts) > 1 else instruction
            result = edit_dialogue(text, char, tone)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_add_scene(self):
        text = self._editor_text.get("1.0", "end-1c").strip()
        instruction = self._editor_instruction.get("1.0", "end-1c").strip()
        if not text or not instruction:
            self._editor_status.configure(text="请填写原文和场景描述")
            return
        self._editor_status.configure(text="插入场景中...")
        def task():
            result = add_scene(text, instruction)
            self.root.after(0, lambda: self._show_editor_result(result))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _show_editor_result(self, result):
        if "error" in result:
            self._editor_result.delete("1.0", "end")
            self._editor_result.insert("1.0", f"错误: {result['error']}")
            self._editor_status.configure(text=f"失败: {result['error']}", text_color=RED)
            return
        edited = result.get("edited", "")
        summary = result.get("changes_summary", "")
        self._editor_result.delete("1.0", "end")
        self._editor_result.insert("1.0", edited)
        if summary:
            self._editor_result.insert("end", f"\n\n{'='*40}\n【修改摘要】\n{summary}")
        self._editor_status.configure(text="改稿完成 ✓", text_color=GREEN)

    def _editor_undo(self):
        text = self._edit_history.undo()
        if text:
            self._editor_text.delete("1.0", "end")
            self._editor_text.insert("1.0", text)
            self._editor_status.configure(text="已撤销")
        else:
            self._editor_status.configure(text="无法继续撤销")

    def _editor_redo(self):
        text = self._edit_history.redo()
        if text:
            self._editor_text.delete("1.0", "end")
            self._editor_text.insert("1.0", text)
            self._editor_status.configure(text="已重做")
        else:
            self._editor_status.configure(text="无法继续重做")

    # ══════════════════════════════════════
    # 页面: 读者模拟
    # ══════════════════════════════════════
        # ══════════════════════════════════════
    # 页面: 读者模拟 (全书支持)
    # ══════════════════════════════════════
    def _build_reader(self):
        p = self.pages["reader"]
        self._sect(p, "AI读者模拟 — 全书分析")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # ── Tab bar ──
        tab_bar = ctk.CTkFrame(scroll, fg_color="transparent")
        tab_bar.pack(fill="x", pady=(4, 8))
        self._reader_tab = ctk.StringVar(value="单章分析")
        ctk.CTkSegmentedButton(tab_bar, values=["单章分析", "全书分析"], variable=self._reader_tab,
                               font=("Microsoft YaHei", 12), selected_color=ACCENT,
                               command=self._on_reader_tab_change).pack(side="left")

        # ── Single chapter panel ──
        self._reader_single_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ctk.CTkLabel(self._reader_single_frame, text="章节内容（粘贴到下方）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._reader_text = ctk.CTkTextbox(self._reader_single_frame, height=160, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_text.pack(fill="x", pady=(0, 8))

        sf = ctk.CTkFrame(self._reader_single_frame, fg_color="transparent")
        sf.pack(fill="x", pady=(4, 8))
        self._reader_type_var = ctk.StringVar(value="all")
        ctk.CTkLabel(sf, text="读者：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        for rt, label in [("all", "全部"), ("hardcore", "硬核"), ("casual", "小白"), ("editor", "编辑"), ("fangirl", "粉丝"), ("skeptic", "喷子"), ("newcomer", "路人")]:
            ctk.CTkRadioButton(sf, text=label, variable=self._reader_type_var, value=rt,
                               font=("Microsoft YaHei", 10), text_color=TEXT, fg_color=ACCENT).pack(side="left", padx=3)
        ctk.CTkLabel(sf, text=" 章号：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._reader_ch_num = ctk.CTkEntry(sf, width=45, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._reader_ch_num.insert(0, "1")
        self._reader_ch_num.pack(side="left", padx=3)
        ctk.CTkButton(sf, text="分析本章", command=self._run_reader_sim,
                      fg_color=ACCENT, font=("Microsoft YaHei", 12), width=90).pack(side="right", padx=2)

        # ── Full book panel ──
        self._reader_full_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ctk.CTkLabel(self._reader_full_frame, text="导入全书文件（.txt / .md）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        ff = ctk.CTkFrame(self._reader_full_frame, fg_color=CARD_HOVER, corner_radius=6)
        ff.pack(fill="x", pady=(0, 8))
        self._reader_book_path = ctk.StringVar(value="")
        ctk.CTkEntry(ff, textvariable=self._reader_book_path, font=("Microsoft YaHei", 10),
                     fg_color=CARD, text_color=TEXT, height=32).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkButton(ff, text="浏览", command=self._browse_reader_book, width=55).pack(side="right", padx=4)

        bf2 = ctk.CTkFrame(self._reader_full_frame, fg_color="transparent")
        bf2.pack(fill="x", pady=(4, 8))
        self._reader_full_btn = ctk.CTkButton(bf2, text="全本分析（6种读者）", command=self._run_full_book_analysis,
                                              fg_color=ACCENT, font=("Microsoft YaHei", 13), width=180)
        self._reader_full_btn.pack(side="left", padx=3)
        ctk.CTkButton(bf2, text="导出报告(MD)", command=self._export_reader_report,
                      fg_color=BLUE, hover_color="#3b82f6", width=110).pack(side="left", padx=3)
        ctk.CTkButton(bf2, text="可读性扫描", command=self._run_readability,
                      fg_color="#3f3f46", width=100).pack(side="left", padx=3)

        self._reader_full_status = ctk.CTkLabel(self._reader_full_frame, text="", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reader_full_status.pack(anchor="w")

        # ── Result area (shared) ──
        ctk.CTkLabel(scroll, text="分析结果", font=("Microsoft YaHei", 12, "bold"), text_color=ACCENT).pack(anchor="w", pady=(8, 4))
        self._reader_result = ctk.CTkTextbox(scroll, height=400, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reader_result.pack(fill="both", expand=True)

        # Navigation for full-book chapter detail
        navf = ctk.CTkFrame(scroll, fg_color="transparent")
        navf.pack(fill="x", pady=(6, 8))
        ctk.CTkLabel(navf, text="查看章节详情：", font=("Microsoft YaHei", 11), text_color=TEXT).pack(side="left")
        self._reader_ch_detail = ctk.CTkEntry(navf, width=60, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT)
        self._reader_ch_detail.insert(0, "1")
        self._reader_ch_detail.pack(side="left", padx=4)
        ctk.CTkButton(navf, text="跳转", command=self._reader_goto_chapter,
                      fg_color=ACCENT, width=50, height=26).pack(side="left", padx=2)
        self._reader_status = ctk.CTkLabel(navf, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reader_status.pack(side="left", padx=10)

        # State
        self._last_reader_analysis = None  # Full-book analysis result
        self._reader_book_data = None  # load_book result

        # Show single panel by default
        self._reader_single_frame.pack(fill="x")
        self._reader_tab.set("单章分析")

    def _on_reader_tab_change(self, val):
        if val == "单章分析":
            self._reader_full_frame.pack_forget()
            self._reader_single_frame.pack(fill="x", before=self._reader_result.master.winfo_children()[self._reader_result.master.winfo_children().index(self._reader_result)])
        else:
            self._reader_single_frame.pack_forget()
            self._reader_full_frame.pack(fill="x", before=self._reader_result)

    def _browse_reader_book(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._reader_book_path.set(path)

    def _run_full_book_analysis(self):
        path = self._reader_book_path.get().strip()
        if not path or not os.path.isfile(path):
            self._reader_full_status.configure(text="请选择有效的文件")
            return
        self._reader_full_status.configure(text="正在加载+切分章节...", text_color=TEXT)
        self._reader_result.delete("1.0", "end")
        self._reader_full_btn.configure(state="disabled", text="分析中...")
        def task():
            # Load book
            book = load_book(path)
            if "error" in book:
                self.root.after(0, lambda: self._reader_full_status.configure(text=book["error"], text_color=RED))
                self.root.after(0, lambda: self._reader_full_btn.configure(state="normal", text="全本分析（6种读者）"))
                return
            self._reader_book_data = book
            self.root.after(0, lambda: self._reader_full_status.configure(
                text=f"已加载: {book['title']} ({book['total_chapters']}章, {book['total_words']:,}字)，正在逐章分析...",
                text_color=TEXT))
            # Analyze
            def log(msg):
                self.root.after(0, lambda: self._reader_full_status.configure(text=msg, text_color=TEXT))
            result = analyze_full_book(book, log_callback=log)
            self._last_reader_analysis = result
            report = generate_full_book_report(result)
            def show():
                self._reader_result.delete("1.0", "end")
                self._reader_result.insert("1.0", report)
                overall = result.get("overall", {})
                self._reader_full_status.configure(
                    text=f"分析完成 | 综合评分: {overall.get('avg_score', 0)}/10 | 趋势: {overall.get('score_trend_desc', '')} | 弃书风险: {overall.get('abandonment_risk', {}).get('risk', '')}",
                    text_color=GREEN)
                self._reader_full_btn.configure(state="normal", text="全本分析（6种读者）")
                self._reader_status.configure(text=f"共{result['total_chapters']}章，点击「跳转」查看单章详情")
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _reader_goto_chapter(self):
        if not self._last_reader_analysis:
            self._reader_status.configure(text="请先进行全本分析")
            return
        try:
            ch = int(self._reader_ch_detail.get())
        except ValueError:
            ch = 1
        report = generate_chapter_feedback_report(self._last_reader_analysis, ch)
        self._reader_result.delete("1.0", "end")
        self._reader_result.insert("1.0", report)
        self._reader_status.configure(text=f"已跳转到第{ch}章详情")
        self._reader_ch_detail.delete(0, "end")
        self._reader_ch_detail.insert(0, str(ch + 1))

    def _export_reader_report(self):
        if not self._last_reader_analysis:
            self._reader_status.configure(text="请先进行全本分析")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            report = generate_full_book_report(self._last_reader_analysis)
            write_file(path, report)
            self._reader_status.configure(text=f"报告已导出: {path}", text_color=GREEN)

    def _run_reader_sim(self):
        text = self._reader_text.get("1.0", "end-1c").strip()
        if not text:
            self._reader_status.configure(text="请填写章节内容")
            return
        rtype = self._reader_type_var.get()
        try:
            ch_num = int(self._reader_ch_num.get())
        except ValueError:
            ch_num = 1
        self._reader_status.configure(text="AI读者正在阅读...")
        self._reader_result.delete("1.0", "end")
        def task():
            rtypes = None if rtype == "all" else [rtype]
            results = simulate_all_readers(text, ch_num, reader_types=rtypes)
            def show():
                self._reader_result.delete("1.0", "end")
                for r in results:
                    self._reader_result.insert("end",
                        f"\n{'='*40}\n### {r.get('reader_name', '?')}\n{'='*40}\n{r.get('feedback', r.get('error', ''))}\n")
                self._reader_status.configure(text="分析完成 ✓", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_readability(self):
        # If full book loaded, scan all chapters
        if self._reader_book_data:
            chs = self._reader_book_data.get("chapters", [])
            lines = ["📊 全书可读性扫描", "=" * 40, f"总章节: {len(chs)}", ""]
            total_ai = 0
            for ch in chs:
                rd = get_readability_score(ch["text"])
                ai_hits = scan_ai_markers(ch["text"])
                total_ai += len(ai_hits)
                lines.append(
                    f"第{ch['num']:>3}章 | 句长:{rd['avg_sentence_length']:5.0f} | "
                    f"段数:{rd['paragraph_count']:>3} | 对话比:{rd['dialogue_ratio']:.1%} | "
                    f"AI痕:{len(ai_hits):>2}")
            lines += ["", f"全书AI痕迹总计: {total_ai} 处"]
            self._reader_result.delete("1.0", "end")
            self._reader_result.insert("1.0", "\n".join(lines))
            self._reader_status.configure(text=f"可读性扫描完成，共{len(chs)}章")
        else:
            text = self._reader_text.get("1.0", "end-1c").strip()
            if not text:
                self._reader_status.configure(text="请填写章节内容或导入全书")
                return
            score = get_readability_score(text)
            ai_hits = scan_ai_markers(text)
            self._reader_result.delete("1.0", "end")
            lines = [
                "📊 可读性分析（纯规则）",
                "=" * 40,
                f"平均句长：{score['avg_sentence_length']} 字符（<20太碎，>60太长）",
                f"段落数：{score['paragraph_count']}",
                f"平均段落长：{score['avg_paragraph_length']} 字符",
                f"段落长度方差：{score['paragraph_variance']}（大=张弛有度）",
                f"对话占比：{score['dialogue_ratio']:.1%}（20%-40%=网文黄金区间）",
                f"总句数：{score['total_sentences']}",
                f"AI痕迹：{len(ai_hits)} 处",
            ]
            if ai_hits:
                lines.append(f"  → {', '.join(h['marker'] for h in ai_hits[:8])}")
            self._reader_result.insert("1.0", "\n".join(lines))
            self._reader_status.configure(text="可读性分析完成 ✓", text_color=GREEN)


    def _build_reverse(self):
        p = self.pages["reverse"]
        self._sect(p, "逆向工程畅销书")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # File selection
        ctk.CTkLabel(scroll, text="选择一本小说文件（.txt/.md）进行深度解构", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        ff = ctk.CTkFrame(scroll, fg_color=CARD_HOVER, corner_radius=6)
        ff.pack(fill="x", pady=(0, 8))
        self._reverse_file_var = ctk.StringVar(value="")
        ctk.CTkEntry(ff, textvariable=self._reverse_file_var, font=("Microsoft YaHei", 10),
                     fg_color=CARD, text_color=TEXT, height=32).pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkButton(ff, text="浏览", command=self._browse_reverse_file, width=55).pack(side="right", padx=4)

        # New book topic for formula application
        ctk.CTkLabel(scroll, text="（可选）新书主题：应用解构公式生成大纲", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        self._reverse_topic = ctk.CTkEntry(scroll, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, height=32)
        self._reverse_topic.pack(fill="x", pady=(0, 8))
        self._reverse_topic.insert(0, "例如：废柴少年获得修仙系统")

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        ctk.CTkButton(bf, text="开始解构", command=self._run_reverse,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Microsoft YaHei", 13), width=140).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="套用公式生成大纲", command=self._run_apply_formula,
                      fg_color=BLUE, hover_color="#3b82f6", width=140).pack(side="left", padx=3)

        # Result
        self._reverse_result = ctk.CTkTextbox(scroll, height=380, font=("Microsoft YaHei", 11), fg_color=CARD, text_color=TEXT, wrap="word")
        self._reverse_result.pack(fill="both", expand=True)
        self._reverse_status = ctk.CTkLabel(scroll, text="就绪", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._reverse_status.pack(anchor="w", pady=(4, 8))

        # Store last reverse report for apply_formula
        self._last_reverse_report = None

    def _browse_reverse_file(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self._reverse_file_var.set(path)

    def _run_reverse(self):
        path = self._reverse_file_var.get().strip()
        if not path or not os.path.isfile(path):
            self._reverse_status.configure(text="请选择有效的文件")
            return
        self._reverse_status.configure(text="正在解构分析（6步）...")
        self._reverse_result.delete("1.0", "end")
        def task():
            def log(msg):
                self.root.after(0, lambda: self._reverse_status.configure(text=msg))
            report = reverse_engineer(path, log_callback=log)
            self._last_reverse_report = report
            def show():
                self._reverse_result.delete("1.0", "end")
                self._reverse_result.insert("1.0", json.dumps(report, ensure_ascii=False, indent=2))
                self._reverse_status.configure(text=f"解构完成 ✓ ({report.get('total_chapters', 0)}章, {report.get('total_words', 0):,}字)", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _run_apply_formula(self):
        if not self._last_reverse_report:
            self._reverse_status.configure(text="请先执行「开始解构」")
            return
        topic = self._reverse_topic.get().strip()
        if not topic:
            self._reverse_status.configure(text="请填写新书主题")
            return
        self._reverse_status.configure(text="正在套用公式生成大纲...")
        def task():
            outline = apply_formula_to_new_book(self._last_reverse_report, topic)
            def show():
                self._reverse_result.delete("1.0", "end")
                self._reverse_result.insert("1.0", outline)
                self._reverse_status.configure(text="公式套用完成 ✓", text_color=GREEN)
            self.root.after(0, show)
        import threading
        threading.Thread(target=task, daemon=True).start()

    # ══════════════════════════════════════
    # 页面: 排行榜模拟
    # ══════════════════════════════════════
    def _open_in_obsidian(self, path):
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
            r"C:\Users\g\AppData\Local\Programs\Obsidian\Obsidian.exe",
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
            pass

    # ================================================================
    # 页面: 下载
    # ================================================================
    def _build_download(self):
        p = self.pages["download"]
        self._sect(p, "小说下载")
        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkLabel(scroll, text="粘贴小说URL（目录页或第一章）", font=("Microsoft YaHei", 12), text_color=TEXT).pack(anchor="w", pady=(8, 4))
        urlf = ctk.CTkFrame(scroll, fg_color=CARD_HOVER, corner_radius=6)
        urlf.pack(fill="x", pady=(0, 8))
        self._dl_url = ctk.CTkEntry(urlf, font=("Microsoft YaHei", 10), fg_color=CARD, text_color=TEXT, height=32,
                                     placeholder_text="https://...")
        self._dl_url.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        # Platform info
        inf = ctk.CTkFrame(scroll, fg_color="transparent")
        inf.pack(fill="x", pady=(4, 8))
        self._dl_platform_label = ctk.CTkLabel(inf, text="检测平台：", font=("Microsoft YaHei", 11), text_color=TEXT_DIM)
        self._dl_platform_label.pack(side="left")
        ctk.CTkButton(inf, text="检测", command=self._detect_dl_platform,
                      fg_color=CARD_HOVER, width=50, height=26).pack(side="left", padx=4)

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.pack(fill="x", pady=(4, 8))
        self._dl_btn = ctk.CTkButton(bf, text="开始下载", command=self._start_download,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Microsoft YaHei", 13), width=140)
        self._dl_btn.pack(side="left", padx=3)
        ctk.CTkButton(bf, text="停止", command=self._stop_download,
                      fg_color="#3f3f46", width=80).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="在 Obsidian 打开", command=lambda: self._open_in_obsidian(self._dl_last_dir if hasattr(self, "_dl_last_dir") else ""),
                      fg_color="#7c4dff", width=120).pack(side="right", padx=3)

        # Log
        self._dl_log = ctk.CTkTextbox(scroll, fg_color="#10121c", text_color=TEXT,
                                       font=("Consolas", 11), height=300)
        self._dl_log.pack(fill="both", expand=True)
        self._dl_status = ctk.CTkLabel(scroll, text="就绪 — 支持番茄小说、起点、纵横等平台", font=("Microsoft YaHei", 10), text_color=TEXT_DIM)
        self._dl_status.pack(anchor="w", pady=(4, 8))

        self._dl_stop_flag = None
        self._dl_last_dir = ""

    def _detect_dl_platform(self):
        url = self._dl_url.get().strip()
        if not url:
            return
        platform = detect_platform(url)
        name = PLATFORMS.get(platform, {}).get("name", "未知")
        self._dl_platform_label.configure(text=f"检测平台：{name}", text_color=GREEN)

    def _start_download(self):
        url = self._dl_url.get().strip()
        if not url:
            self._dl_status.configure(text="请粘贴小说URL")
            return
        self._dl_stop_flag = threading.Event()
        self._dl_btn.configure(state="disabled", text="下载中...")
        self._dl_log.delete("1.0", "end")
        self._dl_status.configure(text="正在连接...")
        def task():
            result = download_novel(url, log_callback=lambda m: self._log(self._dl_log, m),
                                    stop_flag=self._dl_stop_flag)
            if "error" in result:
                self.root.after(0, lambda: self._dl_status.configure(text=result["error"], text_color=RED))
            else:
                self._dl_last_dir = result.get("book_dir", "")
                self.root.after(0, lambda: self._dl_status.configure(
                    text=f"下载完成: {result['title']} ({result['downloaded']}章, {result['total_words']:,}字) | 作者: {result.get('author', '未知')}",
                    text_color=GREEN))
            self.root.after(0, lambda: self._dl_btn.configure(state="normal", text="开始下载"))
        import threading
        threading.Thread(target=task, daemon=True).start()

    def _stop_download(self):
        if self._dl_stop_flag:
            self._dl_stop_flag.set()
            self._dl_status.configure(text="已停止")

    def _on_close(self):
        try:
            self.stop_flag.set()
        except Exception:
            pass
        self.root.destroy()
