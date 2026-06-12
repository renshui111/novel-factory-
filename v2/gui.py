# gui.py ? Novel Factory GUI v1.1
# ??? + ???? + ????

from __future__ import annotations
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    load_config, save_config, get_output_dir, check_ollama_running,
    get_available_ollama_models, read_file, write_file, count_words
)
from novel import (
    generate_novel, generate_setting, generate_directory,
    generate_chapter, update_summary, prepare_book_dir
)
from analyze import analyze_novel, batch_analyze
from deslop import deslop_file, generate_ai_word_report
from batch import run_batch
from export import (
    export_to_txt, export_to_epub, export_to_pdf,
    export_to_docx, export_to_html, _get_book_info
)

BG = "#0d0d1a"
SB = "#111122"
CARD = "#141428"
ACCENT = "#e94560"
BLUE = "#4a9be8"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
TEXT = "#e0e0e0"
PH = "#555555"


class NovelFactoryGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("???? - v2.0")
        self.root.geometry("1250x800")
        self.root.minsize(1000, 650)
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
        self._show_page("settings")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # ????
        self.root.after(200, self._validate_on_startup)
        # ???????
        self._update_status_bar()
        self.root.after(10000, self._schedule_status_bar)

    def run(self):
        self.root.mainloop()

    # ??? ?? ????????????????????????????
    def _build_sidebar(self):
        self.sb = ctk.CTkFrame(self.root, width=170, fg_color=SB, corner_radius=0)
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        ctk.CTkLabel(self.sb, text="????",
                     font=("Microsoft YaHei", 18, "bold"),
                     text_color=ACCENT).pack(pady=(25, 5))
        ctk.CTkLabel(self.sb, text="v2.0",
                     font=("Microsoft YaHei", 10), text_color=PH).pack(pady=(0, 15))

        self.nav = {}
        items = [
            ("settings", "Setup"),
            ("create",   "??"),
            ("batch",    "??"),
            ("analyze",  "??"),
            ("deslop",   "?AI"),
            ("cover",    "??"),
            ("review",   "??"),
            ("output",   "??"),
        ]
        emojis = {
            "settings": "gear", "create": "pencil", "batch": "package",
            "analyze": "mag", "deslop": "broom", "cover": "art",
            "review": "search",
            "output": "folder"
        }
        for key, label in items:
            btn = ctk.CTkButton(
                self.sb, text=label,
                font=("Microsoft YaHei", 13),
                fg_color="transparent", text_color=TEXT,
                hover_color="#1a1a3a", anchor="w", height=36,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=8, pady=1)
            self.nav[key] = btn

        self.status_frame = ctk.CTkFrame(self.sb, fg_color="transparent")
        self.status_frame.pack(side="bottom", fill="x", padx=8, pady=10)
        self.status_icon = ctk.CTkLabel(self.status_frame, text="o", text_color=GREEN,
                                         font=("Microsoft YaHei", 10))
        self.status_icon.pack(side="left")
        self.status_text = ctk.CTkLabel(self.status_frame, text="??",
                                         font=("Microsoft YaHei", 10), text_color=PH)
        self.status_text.pack(side="left", padx=4)

    def _sect(self, parent, title):
        ctk.CTkLabel(parent, text=title,
                     font=("Microsoft YaHei", 16, "bold"),
                     text_color=ACCENT,
                     anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(parent, text="",
                     fg_color=ACCENT, height=2,
                     corner_radius=1).pack(fill="x", padx=20, pady=(0, 8))

    def _show_page(self, name):
        self.active_tab = name
        for k, btn in self.nav.items():
            btn.configure(fg_color="#1a1a2e" if k == name else "transparent",
                          text_color=ACCENT if k == name else TEXT)
        for key, frame in self.pages.items():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def _log(self, tb, msg):
        self.root.after(0, lambda: self._do_log(tb, msg))

    def _do_log(self, tb, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        tb.insert("end", f"[{ts}] {msg}\n")
        tb.see("end")

    # ??? ??? ??????????????????????????
    def _build_main(self):
        self.main_area = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

        names = ["settings", "create", "batch", "analyze", "deslop", "cover", "review", "output"]
        self.pages = {}
        for n in names:
            self.pages[n] = ctk.CTkFrame(self.main_area, fg_color=BG, corner_radius=0)
        self._build_settings()
        self._build_create()
        self._build_batch()
        self._build_analyze()
        self._build_deslop()
        self._build_cover()
        self._build_review()
        self._build_output()

    # ??????????????????????????????????????
    # ??: Settings
    # ??????????????????????????????????????
    def _build_settings(self):
        p = self.pages["settings"]
        cfg = load_config()
        self._sect(p, "??")

        scroll = ctk.CTkScrollableFrame(p, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        self._card_lbl(scroll, "????")
        card = ctk.CTkFrame(scroll, fg_color=CARD)
        card.pack(fill="x", pady=3)

        rf = ctk.CTkFrame(card, fg_color="transparent")
        rf.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(rf, text="?????? (Ollama):",
                     font=("Microsoft YaHei", 13)).pack(side="left")
        self.use_local_var = ctk.BooleanVar(value=cfg.get("use_local", False))
        ctk.CTkSwitch(rf, text="", variable=self.use_local_var,
                      command=self._toggle_model).pack(side="right")

        # Cloud
        self._cloud_f = ctk.CTkFrame(card, fg_color="transparent")
        self._cloud_f.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(self._cloud_f, text="????",
                     font=("Microsoft YaHei", 13, "bold")).pack(anchor="w")
        # Provider dropdown
        ctk.CTkLabel(self._cloud_f, text="???:").pack(anchor="w")
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
        ctk.CTkLabel(self._cloud_f, text="????:").pack(anchor="w")
        self.cloud_url_var = ctk.StringVar(
            value=cfg["llm"].get("base_url", "https://api.openai.com/v1"))
        ctk.CTkEntry(self._cloud_f, textvariable=self.cloud_url_var).pack(fill="x", pady=1)

        # Model
        ctk.CTkLabel(self._cloud_f, text="??:").pack(anchor="w")
        self.cloud_model_var = ctk.StringVar(
            value=cfg["llm"].get("model_name", "gpt-4o-mini"))
        ctk.CTkEntry(self._cloud_f, textvariable=self.cloud_model_var).pack(fill="x", pady=1)

        # Local
        self._local_f = ctk.CTkFrame(card, fg_color="transparent")
        self._local_f.pack(fill="x", padx=15, pady=2)

        hf = ctk.CTkFrame(self._local_f, fg_color="transparent")
        hf.pack(fill="x")
        ctk.CTkLabel(hf, text="???? (Ollama)",
                     font=("Microsoft YaHei", 13, "bold")).pack(side="left")
        self.ollama_status = ctk.CTkLabel(hf, text="???...",
                                           font=("Microsoft YaHei", 11))
        self.ollama_status.pack(side="right")
        ctk.CTkButton(hf, text="??", command=self._check_ollama,
                      width=50, height=22).pack(side="right", padx=4)

        self.local_model_var = ctk.StringVar(
            value=cfg["local_llm"].get("model_name", "qwen2.5:7b"))
        # ?????????
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

        # ????: ??? + ?????
        ctk.CTkLabel(self._local_f, text="????:").pack(anchor="w")
        self._local_model_cb = ctk.CTkComboBox(
            self._local_f,
            values=self._local_model_list,
            variable=self.local_model_var)
        self._local_model_cb.pack(fill="x", pady=1)

        # ???? + ????
        btn_f = ctk.CTkFrame(self._local_f, fg_color="transparent")
        btn_f.pack(fill="x", pady=2)
        self._detect_gpu_btn = ctk.CTkButton(
            btn_f, text="???????", width=120, height=26,
            command=self._detect_hardware)
        self._detect_gpu_btn.pack(side="left", padx=(0,4))
        self._install_btn = ctk.CTkButton(
            btn_f, text="??????", width=100, height=26,
            fg_color=GREEN, command=self._install_recommended_model)
        self._install_btn.pack(side="left")
        self._gpu_label = ctk.CTkLabel(
            btn_f, text="", font=("Consolas", 10), text_color=PH)
        self._gpu_label.pack(side="left", padx=6)

        # Ollama URL
        ctk.CTkLabel(self._local_f, text="Ollama URL:").pack(anchor="w")
        ctk.CTkEntry(self._local_f, textvariable=self.local_url_var).pack(fill="x", pady=1)

        # Output
        self._card_lbl(scroll, "????")
        oc = ctk.CTkFrame(scroll, fg_color=CARD)
        oc.pack(fill="x", pady=3)

        self.output_dir_var = ctk.StringVar(value=cfg.get("output_dir", ""))
        ef = ctk.CTkFrame(oc, fg_color="transparent")
        ef.pack(fill="x", padx=15, pady=5)
        ctk.CTkEntry(ef, textvariable=self.output_dir_var,
                     placeholder_text="?????? exe ???"
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ef, text="??", command=self._browse_dir,
                      width=55).pack(side="right", padx=4)

        # ??????
        self._validate_label = ctk.CTkLabel(scroll, text="",
                                             font=("Microsoft YaHei", 11))
        self._validate_label.pack(pady=(0, 5))

        ctk.CTkButton(scroll, text="????",
                      command=self._save_settings,
                      fg_color=BLUE, font=("Microsoft YaHei", 14)
                      ).pack(pady=(12, 10))

        self._update_model_visibility()
        self.root.after(1000, self._check_ollama)

    # ??????????????????????????????????????
    # ??: Create (step-by-step)
    # ??????????????????????????????????????
    def _build_create(self):
        p = self.pages["create"]
        self._sect(p, "?? - ????")

        cfg = load_config()["novel"]
        top = ctk.CTkFrame(p, fg_color=CARD)
        top.pack(fill="x", padx=20, pady=3)

        gf = ctk.CTkFrame(top, fg_color="transparent")
        gf.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(gf, text="??:", font=("Microsoft YaHei", 12)).grid(row=0, column=0, sticky="w")
        self._topic_var = ctk.StringVar(value=cfg.get("topic", ""))
        ctk.CTkEntry(gf, textvariable=self._topic_var, width=250,
                     placeholder_text="?: ????:??").grid(row=0, column=1, padx=2)

        ctk.CTkLabel(gf, text="??:", font=("Microsoft YaHei", 12)).grid(row=0, column=2, sticky="w", padx=8)
        self._genre_var = ctk.StringVar(value=cfg.get("genre", "??"))
        ctk.CTkComboBox(gf, values=["??", "??", "??", "??", "??", "??", "??", "??"],
                        variable=self._genre_var, width=110).grid(row=0, column=3, padx=2)

        ctk.CTkLabel(gf, text="??:", font=("Microsoft YaHei", 12)).grid(row=0, column=4, sticky="w", padx=8)
        self._ch_var = ctk.StringVar(value=str(cfg.get("num_chapters", 30)))
        ctk.CTkEntry(gf, textvariable=self._ch_var, width=60).grid(row=0, column=5, padx=2)

        ctk.CTkLabel(gf, text="??/?:", font=("Microsoft YaHei", 12)).grid(row=0, column=6, sticky="w", padx=8)
        self._wc_var = ctk.StringVar(value=str(cfg.get("words_per_chapter", 3000)))
        ctk.CTkEntry(gf, textvariable=self._wc_var, width=70).grid(row=0, column=7, padx=2)

        # ?? Mode selector ??
        mode_frame = ctk.CTkFrame(p, fg_color=CARD)
        mode_frame.pack(fill="x", padx=20, pady=3)
        mf = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mf.pack(pady=6)
        self._create_mode.trace_add("write", lambda *_: self._on_create_mode_change())
        self._mode_selector = ctk.CTkSegmentedButton(
            mf,
            values=["???", "???", "??"],
            variable=self._create_mode,
            font=("Microsoft YaHei", 12),
            selected_color=ACCENT,
            unselected_color="#2a2a3e",
            unselected_hover_color="#3a3a5e",
        )
        self._mode_selector.pack()
        self._mode_selector.set("???")
        # Map user-facing labels to internal values
        self._mode_map = {"???": "auto", "???": "semi", "??": "manual"}
        self._mode_rev = {"auto": "???", "semi": "???", "manual": "??"}
        # CTkSegmentedButton stores display text; sync via callback

        # Step indicator
        self.step_frame = ctk.CTkFrame(p, fg_color=CARD)
        self.step_frame.pack(fill="x", padx=20, pady=3)
        sf = ctk.CTkFrame(self.step_frame, fg_color="transparent")
        sf.pack(pady=8)
        self._step_labels = {}
        steps = [
            ("step1", "1. ????"),
            ("step2", "2. ????"),
            ("step3", "3. ????"),
            ("step4", "4. ??"),
        ]
        for i, (key, label) in enumerate(steps):
            lbl = ctk.CTkLabel(sf, text=label, font=("Microsoft YaHei", 12), text_color=PH)
            lbl.pack(side="left", padx=6)
            self._step_labels[key] = lbl
            if i < len(steps) - 1:
                ctk.CTkLabel(sf, text=" ? ", font=("Microsoft YaHei", 14), text_color=PH).pack(side="left")

        # Content area: left panel + dashboard + right log
        mid = ctk.CTkFrame(p, fg_color=BG)
        mid.pack(fill="both", expand=True, padx=20, pady=3)

        self._step_panel = ctk.CTkFrame(mid, fg_color=CARD, width=360)
        self._step_panel.pack(side="left", fill="y", padx=(0, 5))
        self._step_panel.pack_propagate(False)

        # Dashboard panel (fixed width, between step panel and log)
        dash_frame = ctk.CTkFrame(mid, fg_color=CARD, width=200)
        dash_frame.pack(side="left", fill="y", padx=(0, 5))
        dash_frame.pack_propagate(False)
        ctk.CTkLabel(dash_frame, text="???",
                     font=("Microsoft YaHei", 12, "bold"),
                     text_color=GREEN).pack(anchor="w", padx=8, pady=5)
        self._dash_labels = {}
        dash_items = [
            ("progress", "??", "0 / 0 ?"),
            ("words", "????", "0 ?"),
            ("speed", "????", "?"),
            ("eta", "????", "?"),
            ("tokens", "Token ??", "?"),
            ("foreshadow", "?????", "0"),
        ]
        for key, label, default in dash_items:
            f = ctk.CTkFrame(dash_frame, fg_color="transparent")
            f.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(f, text=label, font=("Microsoft YaHei", 10),
                         text_color=PH).pack(anchor="w")
            val = ctk.CTkLabel(f, text=default,
                               font=("Microsoft YaHei", 13, "bold"),
                               text_color=TEXT, anchor="w", justify="left")
            val.pack(anchor="w", fill="x")
            self._dash_labels[key] = val

        log_frame = ctk.CTkFrame(mid, fg_color=BG)
        log_frame.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(log_frame, text="??",
                     font=("Microsoft YaHei", 12, "bold"),
                     text_color=BLUE).pack(anchor="w")
        self._create_log = ctk.CTkTextbox(log_frame, fg_color="#0a0a15",
                                           text_color=TEXT, font=("Consolas", 11))
        self._create_log.pack(fill="both", expand=True)

        self._progress_bar = ctk.CTkProgressBar(p, height=6, fg_color="#333",
                                                  progress_color=ACCENT)
        self._progress_bar.pack(fill="x", padx=20, pady=(0, 3))
        self._progress_bar.set(0)

        btn_frame = ctk.CTkFrame(p, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)

        # ?????????????
        self._create_progress = ctk.CTkTextbox(p, fg_color="#0a0a15",
                                                 text_color=GREEN, font=("Consolas", 11),
                                                 height=150)
        self._create_progress.pack(fill="x", padx=20, pady=(0, 3))
        self._create_progress.insert("end", "??? ???? ???\n")
        self._create_progress.insert("end", "??? ?? ???\n")
        self._create_progress.configure(state="disabled")

        self._step_btn = ctk.CTkButton(btn_frame, text="?????",
                                        command=self._on_create_start,
                                        fg_color=ACCENT,
                                        font=("Microsoft YaHei", 14, "bold"),
                                        height=38)
        self._step_btn.pack(side="left", padx=3)
        self._stop_btn = ctk.CTkButton(btn_frame, text="??",
                                        command=self._stop,
                                        fg_color="#555", state="disabled")
        self._stop_btn.pack(side="left", padx=3)
        self._pause_btn = ctk.CTkButton(btn_frame, text="??",
                                        command=self._toggle_pause,
                                        fg_color=ORANGE, state="disabled")
        self._pause_btn.pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="????",
                      command=lambda: self._open_dir(self._book_dir),
                      fg_color=BLUE).pack(side="right", padx=3)

        self._show_step_panel("step1")

    def _show_step_panel(self, step_key):
        for w in self._step_panel.winfo_children():
            w.destroy()

        colors = {"step1": ACCENT, "step2": BLUE, "step3": GREEN, "step4": ORANGE}
        c = colors.get(step_key, ACCENT)
        for k, lbl in self._step_labels.items():
            lbl.configure(text_color=c if k == step_key else PH)

        if step_key == "step1":
            self._build_panel_1()
        elif step_key == "step2":
            self._build_panel_2()
        elif step_key == "step3":
            self._build_panel_3()
        elif step_key == "step4":
            self._build_panel_4()

    def _build_panel_1(self):
        ctk.CTkLabel(self._step_panel, text="??1: ????",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=15, pady=(12, 5))
        ctk.CTkLabel(self._step_panel,
                     text="Generate complete world-building, characters,\npower system, and story outline.",
                     font=("Microsoft YaHei", 11), text_color=PH,
                     wraplength=330).pack(anchor="w", padx=15, pady=3)

        info = ctk.CTkTextbox(self._step_panel, height=140, fg_color="#0a0a15",
                               text_color=TEXT, font=("Microsoft YaHei", 10))
        info.pack(fill="x", padx=15, pady=5)
        info.insert("end", "Tips:\n")
        info.insert("end", "- Be specific with your topic\n")
        info.insert("end", "- Setting can be edited after generation\n")
        info.insert("end", "- Click below or use 'Full Auto' for all steps")
        info.configure(state="disabled")

        self._step1_btn = ctk.CTkButton(self._step_panel, text="????",
                                          command=self._run_step1,
                                          fg_color=ACCENT, height=35)
        self._step1_btn.pack(pady=8, padx=15)

    def _build_panel_2(self):
        ctk.CTkLabel(self._step_panel, text="??2: ????",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=BLUE).pack(anchor="w", padx=15, pady=(12, 5))
        ctk.CTkLabel(self._step_panel,
                     text="Generate chapter titles and positioning.\nEach chapter ends with a hook.",
                     font=("Microsoft YaHei", 11), text_color=PH,
                     wraplength=330).pack(anchor="w", padx=15, pady=3)

        # ???????
        self._use_custom_outline = ctk.BooleanVar(value=False)
        self._outline_cb = ctk.CTkCheckBox(
            self._step_panel, text="???????",
            variable=self._use_custom_outline,
            command=self._toggle_outline_mode,
            font=("Microsoft YaHei", 11), text_color=TEXT)
        self._outline_cb.pack(anchor="w", padx=15, pady=(5, 0))

        # ?????????????
        self._custom_outline_path = ctk.StringVar()
        self._outline_file_frame = ctk.CTkFrame(self._step_panel, fg_color=CARD)
        self._outline_file_frame.pack_forget()
        outline_row = ctk.CTkFrame(self._outline_file_frame, fg_color="transparent")
        outline_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkEntry(outline_row, textvariable=self._custom_outline_path,
                     placeholder_text="?? .txt / .md ????...",
                     font=("Microsoft YaHei", 10)).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(outline_row, text="??", command=self._browse_outline,
                      width=48, height=24).pack(side="right")

        # ????
        self._outline_hint = ctk.CTkLabel(
            self._step_panel, text="",
            font=("Microsoft YaHei", 9), text_color=ORANGE)
        self._outline_hint.pack(anchor="w", padx=15, pady=(0, 2))

        self._dir_preview = ctk.CTkTextbox(self._step_panel, height=180,
                                            fg_color="#0a0a15",
                                            text_color=TEXT,
                                            font=("Consolas", 10))
        self._dir_preview.pack(fill="both", expand=True, padx=15, pady=5)
        self._dir_preview.insert("end", "????????")

        self._step2_btn = ctk.CTkButton(self._step_panel, text="????",
                                          command=self._run_step2,
                                          fg_color=BLUE, height=35)
        self._step2_btn.pack(pady=8, padx=15)

    def _build_panel_3(self):
        ctk.CTkLabel(self._step_panel, text="??3: ????",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=GREEN).pack(anchor="w", padx=15, pady=(12, 5))

        # ????
        self._ch_progress = ctk.CTkLabel(self._step_panel, text="0 / 0 ?",
                                          font=("Microsoft YaHei", 20, "bold"),
                                          text_color=GREEN)
        self._ch_progress.pack(pady=2)

        self._ch_eta = ctk.CTkLabel(self._step_panel, text="",
                                     font=("Microsoft YaHei", 11), text_color=PH)
        self._ch_eta.pack()

        self._ch_bar = ctk.CTkProgressBar(self._step_panel, height=8,
                                            fg_color="#333",
                                            progress_color=GREEN)
        self._ch_bar.pack(fill="x", padx=15, pady=3)
        self._ch_bar.set(0)

        # ???????????
        self._ch_status = ctk.CTkLabel(self._step_panel, text="???????????",
                                        font=("Microsoft YaHei", 11), text_color=PH,
                                        wraplength=330)
        self._ch_status.pack(pady=2)

        # ?????????????????????
        preview_frame = ctk.CTkFrame(self._step_panel, fg_color="#0a0a15", corner_radius=4)
        preview_frame.pack(fill="both", expand=True, padx=15, pady=3)
        self._ch_preview = ctk.CTkTextbox(preview_frame, fg_color="#0a0a15",
                                            text_color=TEXT, font=("Consolas", 10),
                                            wrap="word")
        self._ch_preview.pack(fill="both", expand=True)
        self._ch_preview.insert("end", "???????????????????")

        self._step3_btn = ctk.CTkButton(self._step_panel, text="????",
                                          command=self._run_step3,
                                          fg_color=GREEN, height=35)
        self._step3_btn.pack(pady=6, padx=15)

    def _build_panel_4(self):
        ctk.CTkLabel(self._step_panel, text="??4: ??",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=ORANGE).pack(anchor="w", padx=15, pady=(12, 5))
        ctk.CTkLabel(self._step_panel,
                     text="????AI???????",
                     font=("Microsoft YaHei", 11), text_color=PH,
                     wraplength=330).pack(anchor="w", padx=15, pady=3)

        self._final_info = ctk.CTkTextbox(self._step_panel, height=200,
                                           fg_color="#0a0a15",
                                           text_color=TEXT,
                                           font=("Consolas", 10))
        self._final_info.pack(fill="both", expand=True, padx=15, pady=5)

        bf = ctk.CTkFrame(self._step_panel, fg_color="transparent")
        bf.pack(pady=8)
        ctk.CTkButton(bf, text="???AI?", command=self._run_step4_deslop,
                      fg_color=ORANGE, width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="????",
                      command=lambda: self._open_dir(self._book_dir),
                      fg_color=BLUE, width=120).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="??10?",
                      command=self._run_continue,
                      fg_color="#9c27b0", width=100).pack(side="left", padx=3)
        ctk.CTkButton(bf, text="??10?",
                      command=self._run_continue,
                      fg_color="#9c27b0", width=100).pack(side="left", padx=3)

    # ??? Step execution ?????????????
    def _get_novel_config(self):
        try:
            nc = int(self._ch_var.get())
            wc = int(self._wc_var.get())
        except ValueError:
            self._log(self._create_log, "??: ???????????")
            return None
        return {
            "topic": self._topic_var.get(),
            "genre": self._genre_var.get(),
            "num_chapters": nc,
            "words_per_chapter": wc,
        }

    def _run_step1(self):
        cfg = self._get_novel_config()
        if not cfg or not cfg["topic"]:
            self._log(self._create_log, "??: ?????")
            return
        self._save_novel_cfg(cfg)
        self._step1_btn.configure(state="disabled", text="???...")

        def task():
            try:
                self._book_dir = prepare_book_dir(cfg["topic"])
                self._setting_text = generate_setting(
                    cfg["topic"], cfg["genre"], cfg["num_chapters"],
                    self._book_dir,
                    log_callback=lambda m: self._log(self._create_log, m))
                self.root.after(0, lambda: self._show_step_panel("step2"))
                self.root.after(0, lambda: self._dir_preview.delete("0.0", "end"))
            finally:
                self.root.after(0, lambda: self._step1_btn.configure(
                    state="normal", text="????"))

        threading.Thread(target=task, daemon=True).start()

    def _run_step2(self):
        if not self._setting_text:
            self._log(self._create_log, "??: ??????(??1)")
            return

        # ???????
        if self._use_custom_outline.get():
            path = self._custom_outline_path.get()
            if not path or not os.path.exists(path):
                self._log(self._create_log, "??: ??????????")
                return
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                self._chapters_list = self._parse_outline(raw)
                if not self._chapters_list:
                    self._log(self._create_log, "??: ????????????? ?001?: ?? ? ??")
                    return
                # ????.md
                md_lines = "\n".join([
                    f"?{c['num']:03d}?: {c['title']} ? {c['desc']}"
                    for c in self._chapters_list
                ])
                write_file(os.path.join(self._book_dir, "??.md"), md_lines)
                preview = "\n".join([
                    f"Ch.{c['num']:03d}: {c['title']}"
                    for c in self._chapters_list[:20]
                ])
                if len(self._chapters_list) > 20:
                    preview += f"\n... ({len(self._chapters_list)} total)"
                self.root.after(0, lambda: (
                    self._dir_preview.delete("0.0", "end"),
                    self._dir_preview.insert("end", preview),
                    self._show_step_panel("step3"),
                    self._ch_progress.configure(
                        text=f"0 / {len(self._chapters_list)} chapters"),
                    self._ch_bar.set(0)))
                self._log(self._create_log, f"??? {len(self._chapters_list)} ???")
            except Exception as e:
                self._log(self._create_log, f"??????: {e}")
            return

        cfg = self._get_novel_config()
        self._step2_btn.configure(state="disabled", text="???...")

        def task():
            try:
                self._chapters_list = generate_directory(
                    self._setting_text, cfg["num_chapters"],
                    self._book_dir,
                    log_callback=lambda m: self._log(self._create_log, m))
                preview = "\n".join([
                    f"Ch.{c['num']:03d}: {c['title']}"
                    for c in self._chapters_list[:20]
                ])
                if len(self._chapters_list) > 20:
                    preview += f"\n... ({len(self._chapters_list)} total)"
                self.root.after(0, lambda: (
                    self._dir_preview.delete("0.0", "end"),
                    self._dir_preview.insert("end", preview),
                    self._show_step_panel("step3"),
                    self._ch_progress.configure(
                        text=f"0 / {len(self._chapters_list)} chapters"),
                    self._ch_bar.set(0)))
            finally:
                self.root.after(0, lambda: self._step2_btn.configure(
                    state="normal", text="????"))

        threading.Thread(target=task, daemon=True).start()

    def _parse_outline(self, raw: str) -> list:
        """????????????: ?001?: ?? ? ??"""
        import re
        chapters = []
        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # ?001?: ?? ? ??
            m = re.match(r'?(\d+)?[?:]\s*(.+?)(?:[?\-?]\s*(.+))?$', line)
            if m:
                chapters.append({
                    "num": int(m.group(1)),
                    "title": m.group(2).strip(),
                    "desc": m.group(3).strip() if m.group(3) else ""
                })
                continue
            # ????: 1. ?? ? ??
            m2 = re.match(r'(\d+)[.??\s]+(.+)', line)
            if m2:
                rest = m2.group(2).strip()
                parts = re.split(r'[?\-?]', rest, 1)
                chapters.append({
                    "num": int(m2.group(1)),
                    "title": parts[0].strip(),
                    "desc": parts[1].strip() if len(parts) > 1 else ""
                })
        chapters.sort(key=lambda x: x['num'])
        return chapters

    def _run_step3(self):
        if not self._chapters_list:
            self._log(self._create_log, "??: ??????(??2)")
            return
        cfg = self._get_novel_config()
        self.stop_flag.clear()
        self.pause_flag.clear()
        self._step3_btn.configure(state="disabled", text="???...")
        self._stop_btn.configure(state="normal")
        self._pause_btn.configure(state="normal", text="??")
        self._init_progress(cfg)

        def task():
            import time as _time
            try:
                total = len(self._chapters_list)
                self.progress["total_chapters"] = total
                summary = f"{cfg['topic']} ({cfg['genre']}, {total}?)\n"
                total_wc = 0
                done = 0
                dir_text = "\n".join([
                    f"Ch.{c['num']:03d}: {c['title']}"
                    for c in self._chapters_list
                ])
                chapter_times = []

                for i, ch in enumerate(self._chapters_list, 1):
                    if self.stop_flag.is_set():
                        self._log(self._create_log, f"??? ({done}/{total}?)")
                        break

                    # ??????????????????????
                    while self.pause_flag.is_set() and not self.stop_flag.is_set():
                        self.root.after(0, lambda n=ch['num'], t=total: (
                            self._ch_status.configure(
                                text=f"??? (? {n}/{t} ?)"),
                            self._ch_preview.delete("0.0", "end"),
                            self._ch_preview.insert("end", "???????")
                        ))
                        _time.sleep(0.5)
                    if self.stop_flag.is_set():
                        break

                    t_start = _time.time()
                    self._log(self._create_log, f"[{ch['num']}/{total}] {ch['title']}")
                    self._log_progress(f"? ???? ?{ch['num']}/{total}??{ch['title']}?")

                    # ?????????????
                    self.root.after(0, lambda n=ch['num'], t=total: (
                        self._ch_status.configure(
                            text=f"???? LLM ??? {n}/{t} ?..."),
                        self._ch_preview.delete("0.0", "end"),
                        self._ch_preview.insert("end", "??? LLM ??...?")
                    ))

                    summary_file = os.path.join(self._book_dir, "????.txt")
                    from core import read_file
                    cur = read_file(summary_file) or summary

                    # ???????????
                    def make_stream_cb():
                        preview_chars = []
                        def cb(chunk):
                            preview_chars.append(chunk)
                            preview_text = "".join(preview_chars)
                            # ???????? 2000 ??
                            display = preview_text[-2000:] if len(preview_text) > 2000 else preview_text
                            self.root.after(0, lambda d=display: (
                                self._ch_preview.delete("0.0", "end"),
                                self._ch_preview.insert("end", d),
                                self._ch_preview.see("end")
                            ))
                        return cb

                    result = generate_chapter(
                        ch["num"], ch["title"],
                        self._setting_text, dir_text, cur,
                        cfg["words_per_chapter"],
                        self._book_dir,
                        log_callback=lambda m: self._log(self._create_log, m),
                        stream_callback=make_stream_cb(),
                        stop_flag=self.stop_flag
                    )
                    if not result["success"]:
                        self._log_progress(f"? ?{ch['num']}?????")
                        continue

                    t_elapsed = _time.time() - t_start
                    chapter_times.append(t_elapsed)

                    self._log_progress(f"? ?{ch['num']}????{result['words']:,}?, ??{t_elapsed:.0f}s?")

                    # ??????????
                    self.root.after(0, lambda: self._ch_status.configure(
                        text=f"????????..."))

                    done += 1
                    total_wc += result["words"]
                    update_summary(ch["num"], ch["title"],
                                   result["content"], cur, self._book_dir)

                    # ?? ETA
                    avg_time = sum(chapter_times) / len(chapter_times) if chapter_times else 0
                    remaining = total - done
                    eta_seconds = int(avg_time * remaining)
                    eta_str = f"{eta_seconds//60}?{eta_seconds%60}?" if eta_seconds > 60 else f"{eta_seconds}?"

                    pct = done / total
                    self.root.after(0, lambda p=pct, d=done, w=total_wc, eta=eta_str: (
                        self._ch_bar.set(p),
                        self._ch_progress.configure(
                            text=f"{d} / {total} ?  |  ?? {w:,} ?"),
                        self._ch_status.configure(
                            text=f"???? {t_elapsed:.0f}? | ???? {eta}")
                    ))

                # ??
                self.root.after(0, lambda: (
                    self._show_step_panel("step4"),
                    self._final_info.delete("0.0", "end"),
                    self._final_info.insert("end",
                        f"??: {done}/{total} ?\n\n"
                        f"???: {total_wc:,}\n"
                        f"????: {self._book_dir}\n\n"
                        f"???:\n"
                        f"1. ????????AI??????\n"
                        f"2. ????????\n"
                        f"3. ????????")
                ))
            finally:
                self.root.after(0, lambda: self._step3_btn.configure(
                    state="normal", text="????"))
                self.root.after(0, lambda: self._stop_btn.configure(state="disabled"))
                self.root.after(0, lambda: self._pause_btn.configure(state="disabled", text="??"))

        threading.Thread(target=task, daemon=True).start()

    def _run_step4_deslop(self):
        if not self._book_dir or not os.path.exists(self._book_dir):
            self._log(self._create_log, "??: ???????")
            return
        ch_dir = os.path.join(self._book_dir, "??")
        if not os.path.exists(ch_dir):
            self._log(self._create_log, "???????")
            return

        files = sorted([f for f in os.listdir(ch_dir) if f.endswith(".md")])
        if not files:
            self._log(self._create_log, "?????")
            return

        self._log(self._create_log, "??????AI?...")
        def task():
            for fname in files:
                path = os.path.join(ch_dir, fname)
                r = deslop_file(path, use_llm=False,
                                log_callback=lambda m: self._log(self._create_log, m))
                if "error" not in r:
                    self._log(self._create_log,
                              f"  {fname}: {r.get('rule_replacements', 0)} replacements")
            self._log(self._create_log, "Done! All chapters de-AI'd")

        threading.Thread(target=task, daemon=True).start()

    # ??? ????? ????????????????????????
    def _on_create_mode_change(self):
        """Called when create mode changes. Updates the main button text."""
        mode = self._create_mode.get()  # e.g. "???", "???", "??"
        btn_texts = {
            "???": "?????",
            "???": "?????",
            "??": "????",
        }
        if hasattr(self, '_step_btn'):
            self._step_btn.configure(text=btn_texts.get(mode, "?????"))

    def _on_create_start(self):
        """Dispatcher: start generation based on current mode."""
        mode_label = self._create_mode.get()
        mode = self._mode_map.get(mode_label, "auto")
        if mode == "auto":
            self._run_full_auto()
        elif mode == "semi":
            self._run_semi_auto()
        else:
            self._run_manual()

    # ??? ????? ????????????????????????
    def _run_semi_auto(self):
        """????????????????/??????????"""
        cfg = self._get_novel_config()
        if not cfg or not cfg["topic"]:
            self._log(self._create_log, "??: ?????")
            return
        self._save_novel_cfg(cfg)
        self.stop_flag.clear()
        self._step_btn.configure(state="disabled", text="????...")
        self._stop_btn.configure(state="normal")
        self._pause_btn.configure(state="disabled", text="??")
        self._init_progress(cfg)

        def task():
            import time as _time
            from novel import generate_setting, generate_directory, prepare_book_dir
            try:
                # Step 1: ???? ? ????
                self.root.after(0, lambda: self._show_step_panel("step1"))
                self._log(self._create_log, "[???] ?????...")
                setting = generate_setting(
                    config={"novel": cfg},
                    log_callback=lambda m: self._log(self._create_log, m),
                    stop_flag=self.stop_flag)
                if self.stop_flag.is_set() or "error" in setting:
                    return
                confirmed = self._show_confirm_dialog(
                    "??1: ????",
                    f"?????\n\n{setting.get('setting', '')}",
                    edit_enabled=True)
                if not confirmed or self.stop_flag.is_set():
                    self._log(self._create_log, "[???] ????")
                    return

                # Step 2: ???? ? ????
                self.root.after(0, lambda: self._show_step_panel("step2"))
                self._log(self._create_log, "[???] ?????...")
                directory = generate_directory(
                    config={"novel": cfg},
                    setting_text=setting.get("setting", ""),
                    log_callback=lambda m: self._log(self._create_log, m),
                    stop_flag=self.stop_flag)
                if self.stop_flag.is_set() or "error" in directory:
                    return
                confirmed = self._show_confirm_dialog(
                    "??2: ????",
                    f"?????\n\n{directory.get('directory', '')}",
                    edit_enabled=True)
                if not confirmed or self.stop_flag.is_set():
                    self._log(self._create_log, "[???] ????")
                    return

                # Step 3+4: ?????? ? ???? ? ??
                self.root.after(0, lambda: self._show_step_panel("step3"))
                book_dir = prepare_book_dir(cfg["topic"])
                self._book_dir = book_dir
                chapters = self._parse_dir_text(directory.get("directory", ""))
                if not chapters:
                    self._log(self._create_log, "??: ????????")
                    return
                cfg["num_chapters"] = len(chapters)
                cfg["chapters"] = chapters

                from novel import generate_chapter, update_summary
                total_chapters = len(chapters)
                for idx, ch in enumerate(chapters):
                    if self.stop_flag.is_set():
                        break
                    ch_num = ch["num"]
                    ch_title = ch["title"]
                    self.root.after(0, lambda n=ch_num, t=ch_title:
                        self._log(self._create_log, f"?????{n}?: {t}"))

                    # Semi-auto: confirm each chapter
                    confirmed = self._show_confirm_dialog(
                        f"?{ch_num}?: {ch_title}",
                        f"?????{ch_num}??{ch_title}?\n????: {cfg['words_per_chapter']:,}?",
                        edit_enabled=False, confirm_text="????")
                    if not confirmed or self.stop_flag.is_set():
                        self._log(self._create_log, f"[???] ???{ch_num}?")
                        continue

                    self._log(self._create_log, f"[???] ?{ch_num}????...")
                    content = generate_chapter(
                        novel_config=cfg,
                        chapter_index=idx,
                        chapter=ch,
                        book_dir=book_dir,
                        all_chapters=chapters,
                        log_callback=lambda m: self._log(self._create_log, m),
                        stop_flag=self.stop_flag)
                    if self.stop_flag.is_set() or "error" in content:
                        self._log(self._create_log, f"[???] ?{ch_num}?????")
                        continue

                    update_summary(book_dir, ch_title, content.get("chapter_text", ""))

                # Step 4: ??
                self.root.after(0, lambda: self._show_step_panel("step4"))
                self._log(self._create_log, "[???] ??????")
                self.root.after(0, lambda: self._final_info.delete("0.0", "end"))
                self.root.after(0, lambda: self._final_info.insert("end",
                    f"?????\n\nChapters: {total_chapters}\n"
                    f"Output: {book_dir}"))

            finally:
                self.root.after(0, lambda: self._step_btn.configure(
                    state="normal", text="?????"))
                self.root.after(0, lambda: self._stop_btn.configure(state="disabled"))
                self.root.after(0, lambda: self._pause_btn.configure(state="disabled", text="??"))

        threading.Thread(target=task, daemon=True).start()

    # ??? ???? (???) ??????????????????
    def _run_manual(self):
        """??????????????????????????"""
        cfg = self._get_novel_config()
        if not cfg or not cfg["topic"]:
            self._log(self._create_log, "??: ?????")
            return
        self._save_novel_cfg(cfg)
        from novel import prepare_book_dir, generate_chapter, save_checkpoint, load_checkpoint, update_character_archive
        from core import read_file, write_file
        from export import export_to_txt, export_to_epub

        # ????????
        import tkinter.filedialog as fd
        set_path = fd.askopenfilename(title="??????",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")])
        if not set_path:
            self._log(self._create_log, "???")
            return
        novel_setting = read_file(set_path)
        if not novel_setting:
            self._log(self._create_log, "??????")
            return
        self._log(self._create_log, f"?????: {set_path}")

        # ????????
        dir_path = fd.askopenfilename(title="????/????",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")])
        if not dir_path:
            self._log(self._create_log, "???")
            return
        dir_text = read_file(dir_path)
        if not dir_text:
            self._log(self._create_log, "??????")
            return
        self._log(self._create_log, f"?????: {dir_path}")

        # ????
        chapters = self._parse_outline(dir_text)
        if not chapters:
            self._log(self._create_log, "????????????? ?001?: ??")
            return

        # ??????
        self.stop_flag.clear()
        self._step_btn.configure(state="disabled", text="?????...")
        self._stop_btn.configure(state="normal")
        self._pause_btn.configure(state="disabled")
        book_dir = prepare_book_dir(cfg["topic"])
        write_file(os.path.join(book_dir, "??.md"), novel_setting)
        write_file(os.path.join(book_dir, "??.md"), dir_text)
        from novel import init_character_archive
        init_character_archive(book_dir, novel_setting)
        self._init_progress({**cfg, "num_chapters": len(chapters)})
        self.root.after(0, lambda: self._show_step_panel("step3"))

        def task():
            try:
                summary = f"{cfg['topic']}?{cfg.get('genre','')}??{len(chapters)}??\n"
                for ch in chapters:
                    if self.stop_flag and self.stop_flag.is_set():
                        break
                    ch_result = generate_chapter(
                        ch['num'], ch['title'],
                        novel_setting, dir_text, summary,
                        cfg.get('words_per_chapter', 2000),
                        book_dir, lambda m: self._log(self._create_log, m),
                        None, self.stop_flag)
                    if ch_result.get('success'):
                        save_checkpoint(book_dir, ch['num'], summary)
                self._log(self._create_log, f"?????????: {book_dir}")
            finally:
                self.root.after(0, lambda: (self._step_btn.configure(state="normal", text="????"),
                    self._stop_btn.configure(state="disabled"),
                    self._pause_btn.configure(state="disabled")))
        threading.Thread(target=task, daemon=True).start()

    # ??? ?????????? ??????????????
    def _show_confirm_dialog(self, title: str, message: str,
                              edit_enabled: bool = False,
                              confirm_text: str = "????") -> bool:
        """????????????????????? True=??, False=???"""
        import queue
        result_queue = queue.Queue()

        def show():
            dlg = ctk.CTkToplevel(self.root)
            dlg.title(title)
            dlg.geometry("600x450")
            dlg.transient(self.root)
            dlg.grab_set()
            dlg.configure(fg_color=BG)

            lbl = ctk.CTkLabel(dlg, text=title,
                               font=("Microsoft YaHei", 15, "bold"),
                               text_color=ACCENT)
            lbl.pack(anchor="w", padx=15, pady=(12, 5))

            if edit_enabled:
                txt = ctk.CTkTextbox(dlg, fg_color="#0a0a15",
                                     text_color=TEXT, font=("Consolas", 11))
                txt.pack(fill="both", expand=True, padx=15, pady=5)
                txt.insert("1.0", message)
            else:
                txt = ctk.CTkTextbox(dlg, fg_color="#0a0a15",
                                     text_color=TEXT, font=("Consolas", 11))
                txt.pack(fill="both", expand=True, padx=15, pady=5)
                txt.insert("1.0", message)
                txt.configure(state="disabled")

            bf = ctk.CTkFrame(dlg, fg_color="transparent")
            bf.pack(pady=8)

            def on_confirm():
                dlg.destroy()
                result_queue.put(True)

            def on_cancel():
                dlg.destroy()
                result_queue.put(False)

            ctk.CTkButton(bf, text=confirm_text,
                          command=on_confirm,
                          fg_color=GREEN).pack(side="left", padx=4)
            ctk.CTkButton(bf, text="??",
                          command=on_cancel,
                          fg_color="#666").pack(side="left", padx=4)

        self.root.after(0, show)
        return result_queue.get()

    def _show_edit_dialog(self, title: str, prompt: str, initial: str) -> str | None:
        """???????????????????????? None?"""
        import queue
        result_queue = queue.Queue()

        def show():
            dlg = ctk.CTkToplevel(self.root)
            dlg.title(title)
            dlg.geometry("700x500")
            dlg.transient(self.root)
            dlg.grab_set()
            dlg.configure(fg_color=BG)

            ctk.CTkLabel(dlg, text=prompt,
                         font=("Microsoft YaHei", 12),
                         text_color=TEXT).pack(anchor="w", padx=15, pady=(12, 3))

            txt = ctk.CTkTextbox(dlg, fg_color="#0a0a15",
                                 text_color=TEXT, font=("Consolas", 11))
            txt.pack(fill="both", expand=True, padx=15, pady=5)
            txt.insert("1.0", initial)

            bf = ctk.CTkFrame(dlg, fg_color="transparent")
            bf.pack(pady=8)

            def on_ok():
                result = txt.get("1.0", "end-1c")
                dlg.destroy()
                result_queue.put(result)

            def on_cancel():
                dlg.destroy()
                result_queue.put(None)

            ctk.CTkButton(bf, text="??",
                          command=on_ok,
                          fg_color=GREEN).pack(side="left", padx=4)
            ctk.CTkButton(bf, text="??",
                          command=on_cancel,
                          fg_color="#666").pack(side="left", padx=4)

        self.root.after(0, show)
        return result_queue.get()

    def _run_full_auto(self):
        cfg = self._get_novel_config()
        if not cfg or not cfg["topic"]:
            self._log(self._create_log, "??: ?????")
            return
        self._save_novel_cfg(cfg)
        self.stop_flag.clear()
        self.pause_flag.clear()
        self._step_btn.configure(state="disabled", text="????...")
        self._stop_btn.configure(state="normal")
        self._pause_btn.configure(state="normal", text="??")
        self._init_progress(cfg)

        def task():
            import time as _time
            try:
                result = generate_novel(
                    config={"novel": cfg},
                    log_callback=lambda m: self._log(self._create_log, m),
                    stop_flag=self.stop_flag,
                    progress_callback=self._on_novel_progress,
                    custom_outline_path=self._custom_outline_path.get()
                        if self._use_custom_outline.get() else None)
                # ??????????? progress_callback ???
                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                    _time.sleep(0.5)
                if "book_dir" in result:
                    self._book_dir = result["book_dir"]
                    self.root.after(0, lambda: (
                        self._show_step_panel("step4"),
                        self._final_info.delete("0.0", "end"),
                        self._final_info.insert("end",
                            f"{result.get('status', 'Done')}\n\n"
                            f"Chapters: {result.get('chapters_done', 0)}/"
                            f"{result.get('chapters_planned', 0)}\n"
                            f"Words: {result.get('total_words', 0):,}\n"
                            f"Time: {result.get('elapsed_seconds', 0):.0f}s\n"
                            f"Output: {result.get('book_dir', '')}")))
            finally:
                mode_label = self._mode_rev.get(self._create_mode.get(), "???")
                btn_texts = {"???": "?????", "???": "?????", "??": "????"}
                self.root.after(0, lambda: self._step_btn.configure(
                    state="normal",
                    text=btn_texts.get(mode_label, "?????")))
                self.root.after(0, lambda: self._stop_btn.configure(state="disabled"))
                self.root.after(0, lambda: self._pause_btn.configure(state="disabled", text="??"))

        threading.Thread(target=task, daemon=True).start()

    def _parse_dir_text(self, dir_text: str) -> list:
        import re
        chapters = []
        for line in dir_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            m = re.match(r'?(\d+)?[\uff1a:]\s*(.+?)(?:[\u2500\u2014\u2015\-]\s*(.+))?$', line)
            if m:
                chapters.append({
                    "num": int(m.group(1)),
                    "title": m.group(2).strip(),
                    "desc": m.group(3).strip() if m.group(3) else ""
                })
        return chapters

    def _save_novel_cfg(self, cfg):
        c = load_config()
        c["novel"] = cfg
        save_config()

    def _toggle_outline_mode(self):
        if self._use_custom_outline.get():
            self._outline_file_frame.pack(fill="x", padx=10, pady=3)
            self._outline_hint.configure(
                text="??: ?001?: ?? ? ?????")
            self._step2_btn.configure(text="????", fg_color=GREEN)
        else:
            self._outline_file_frame.pack_forget()
            self._outline_hint.configure(text="")
            self._step2_btn.configure(text="????", fg_color=BLUE)

    def _browse_outline(self):
        f = filedialog.askopenfilename(
            title="??????",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")])
        if f:
            self._custom_outline_path.set(f)
            # Preview the outline
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    preview = fp.read()[:500]
                self._dir_preview.delete("0.0", "end")
                self._dir_preview.insert("end", preview)
                ch_count = len(re.findall(r'?\d+?', preview))
                self._outline_hint.configure(
                    text=f"??? {ch_count} ? | {f}")
            except Exception as e:
                self._outline_hint.configure(text=f"????: {e}")

    def _run_continue(self):
        """????????????"""
        if not self._book_dir or not os.path.exists(self._book_dir):
            self._log(self._create_log, "??: ??????")
            return
        
        from novel import continue_novel
        
        def task():
            try:
                self._log(self._create_log, "????...")
                result = continue_novel(
                    book_dir=self._book_dir,
                    additional_chapters=10,
                    log_callback=lambda m: self._log(self._create_log, m),
                    stop_flag=self.stop_flag,
                    progress_callback=self._on_novel_progress)
                self._log(self._create_log,
                    f"????: +{result.get('chapters_added', 0)}?")
                self.root.after(0, lambda: self._final_info.insert("end",
                    f"\n????: +{result.get('chapters_added', 0)}?"))
            except Exception as e:
                self._log(self._create_log, f"????: {e}")
        
            import threading
            threading.Thread(target=task, daemon=True).start()

