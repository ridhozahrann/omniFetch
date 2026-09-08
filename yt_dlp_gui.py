import os
import sys
import json
import queue
import shutil
import datetime
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Standardize path so yt_dlp module in workspace can be imported cleanly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

HISTORY_FILE = os.path.join(SCRIPT_DIR, "download_history.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "user_config.json")


def find_ffmpeg():
    """Check system PATH and local directories for FFmpeg binary."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    local_paths = [
        os.path.join(SCRIPT_DIR, "ffmpeg.exe"),
        os.path.join(SCRIPT_DIR, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(SCRIPT_DIR, "bin", "ffmpeg.exe"),
    ]
    for p in local_paths:
        if os.path.exists(p):
            return p
    return None


THEMES = {
    "dark": {
        "BG_DARK": "#181825",
        "CARD_BG": "#1e1e2e",
        "CARD_BORDER": "#313244",
        "TEXT_MAIN": "#cdd6f4",
        "TEXT_MUTED": "#a6adc8",
        "ACCENT": "#89b4fa",
        "ACCENT_HOVER": "#74c7ec",
        "ACCENT_FG": "#11111b",
        "SUCCESS": "#a6e3a1",
        "WARNING": "#f9e2af",
        "ERROR": "#f38ba8",
        "INPUT_BG": "#11111b",
        "TOGGLE_BTN_BG": "#313244",
        "TOGGLE_BTN_FG": "#cdd6f4",
        "TOGGLE_TEXT": "☀️ Light Mode",
    },
    "light": {
        "BG_DARK": "#f1f5f9",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#cbd5e1",
        "TEXT_MAIN": "#0f172a",
        "TEXT_MUTED": "#64748b",
        "ACCENT": "#2563eb",
        "ACCENT_HOVER": "#1d4ed8",
        "ACCENT_FG": "#ffffff",
        "SUCCESS": "#16a34a",
        "WARNING": "#d97706",
        "ERROR": "#dc2626",
        "INPUT_BG": "#f8fafc",
        "TOGGLE_BTN_BG": "#e2e8f0",
        "TOGGLE_BTN_FG": "#0f172a",
        "TOGGLE_TEXT": "🌙 Dark Mode",
    },
}


class YtDlpGUI:
    def __init__(self, root):
        self.root = root

        self.root.title("OmniFetch Pro - Universal Media Downloader")
        self.root.geometry("860x840")
        self.root.minsize(760, 720)

        # Load user config for theme preference
        self.user_config = self.load_user_config()
        self.current_theme_name = self.user_config.get("theme", "dark")
        if self.current_theme_name not in THEMES:
            self.current_theme_name = "dark"

        self.palette = THEMES[self.current_theme_name]

        # Queue & Threading state
        self.msg_queue = queue.Queue()
        self.is_downloading = False
        self.cancel_requested = False
        self.ffmpeg_path = find_ffmpeg()

        # History Storage
        self.history_data = self.load_history()

        # Track registered widgets for theme updates
        self.themeable_frames = []
        self.themeable_cards = []
        self.themeable_inputs = []
        self.themeable_buttons = []
        self.themeable_labels = []

        # Setup ttk styles
        self.setup_styles()

        # Build UI with Tabs
        self.build_ui()

        # Apply active theme colors
        self.apply_theme()

        # Refresh History Table
        self.render_history_table()

        # Start checking queue
        self.root.after(100, self.process_queue)

    def load_user_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_user_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.user_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.update_style_colors()

    def update_style_colors(self):
        p = self.palette
        self.style.configure("TNotebook", background=p["BG_DARK"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=p["CARD_BG"],
            foreground=p["TEXT_MUTED"],
            padding=[16, 8],
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", p["ACCENT"]), ("active", p["CARD_BORDER"])],
            foreground=[("selected", p["ACCENT_FG"]), ("active", p["TEXT_MAIN"])],
        )

        self.style.configure("TFrame", background=p["BG_DARK"])
        self.style.configure("Card.TFrame", background=p["CARD_BG"])

        self.style.configure(
            "TLabel",
            background=p["BG_DARK"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Card.TLabel",
            background=p["CARD_BG"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Muted.TLabel",
            background=p["CARD_BG"],
            foreground=p["TEXT_MUTED"],
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Title.TLabel",
            background=p["CARD_BG"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 15, "bold"),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background=p["CARD_BG"],
            foreground=p["TEXT_MUTED"],
            font=("Segoe UI", 9),
        )

        self.style.configure(
            "TCombobox",
            fieldbackground=p["INPUT_BG"],
            background=p["CARD_BORDER"],
            foreground=p["TEXT_MAIN"],
            arrowcolor=p["TEXT_MAIN"],
            font=("Segoe UI", 9),
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", p["INPUT_BG"])],
            foreground=[("readonly", p["TEXT_MAIN"])],
        )

        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=p["INPUT_BG"],
            background=p["ACCENT"],
            thickness=12,
            borderwidth=0,
        )

        self.style.configure(
            "Custom.TRadiobutton",
            background=p["CARD_BG"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 10),
        )
        self.style.map(
            "Custom.TRadiobutton",
            background=[("active", p["CARD_BG"])],
            foreground=[("active", p["ACCENT"])],
        )

        self.style.configure(
            "Custom.TCheckbutton",
            background=p["CARD_BG"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 9),
        )
        self.style.map(
            "Custom.TCheckbutton",
            background=[("active", p["CARD_BG"])],
            foreground=[("active", p["ACCENT"])],
        )

        self.style.configure(
            "Treeview",
            background=p["INPUT_BG"],
            foreground=p["TEXT_MAIN"],
            fieldbackground=p["INPUT_BG"],
            font=("Segoe UI", 9),
            rowheight=26,
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background=p["CARD_BORDER"],
            foreground=p["TEXT_MAIN"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        self.style.map(
            "Treeview",
            background=[("selected", p["ACCENT"])],
            foreground=[("selected", p["ACCENT_FG"])],
        )

    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.palette = THEMES[self.current_theme_name]
        self.user_config["theme"] = self.current_theme_name
        self.save_user_config()

        self.update_style_colors()
        self.apply_theme()

    def apply_theme(self):
        p = self.palette
        self.root.configure(bg=p["BG_DARK"])

        if hasattr(self, "btn_theme_toggle"):
            self.btn_theme_toggle.config(
                text=p["TOGGLE_TEXT"],
                bg=p["TOGGLE_BTN_BG"],
                fg=p["TOGGLE_BTN_FG"],
                activebackground=p["CARD_BORDER"],
                activeforeground=p["TEXT_MAIN"],
            )

        for frame, is_card in self.themeable_frames:
            if is_card:
                frame.config(bg=p["CARD_BG"], highlightbackground=p["CARD_BORDER"])
            else:
                frame.config(bg=p["BG_DARK"])

        for inp in self.themeable_inputs:
            if isinstance(inp, tk.Entry):
                inp.config(
                    bg=p["INPUT_BG"],
                    fg=p["TEXT_MAIN"],
                    insertbackground=p["TEXT_MAIN"],
                    highlightbackground=p["CARD_BORDER"],
                )
            elif isinstance(inp, scrolledtext.ScrolledText):
                inp.config(
                    bg=p["INPUT_BG"],
                    fg=p["TEXT_MUTED"],
                    insertbackground=p["TEXT_MAIN"],
                    highlightbackground=p["CARD_BORDER"],
                )

        for btn, btype in self.themeable_buttons:
            if btype == "primary":
                if not self.is_downloading:
                    btn.config(
                        bg=p["ACCENT"],
                        fg=p["ACCENT_FG"],
                        activebackground=p["ACCENT_HOVER"],
                        activeforeground=p["ACCENT_FG"],
                    )
            elif btype == "secondary":
                btn.config(
                    bg=p["CARD_BORDER"],
                    fg=p["TEXT_MAIN"],
                    activebackground=p["ACCENT"],
                    activeforeground=p["ACCENT_FG"],
                )
            elif btype == "clear":
                btn.config(
                    bg=p["BG_DARK"],
                    fg=p["TEXT_MUTED"],
                    activebackground=p["BG_DARK"],
                    activeforeground=p["TEXT_MAIN"],
                )

        if hasattr(self, "lbl_status") and not self.is_downloading:
            self.lbl_status.config(foreground=p["TEXT_MAIN"])

        self.update_mode_buttons()
        self.render_history_table()

    def build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # TAB 1: Main Downloader
        self.tab_downloader = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_downloader, text="📥 Main Downloader")

        # TAB 2: Download History
        self.tab_history = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_history, text="📜 Download History")

        self.build_tab_downloader()
        self.build_tab_history()

    # ---------------- TAB 1: DOWNLOADER ----------------

    def build_tab_downloader(self):
        container = self.tab_downloader
        p = self.palette

        # --- 1. HEADER CARD ---
        header_card = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        header_card.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((header_card, True))

        title_frame = tk.Frame(header_card, bg=p["CARD_BG"])
        title_frame.pack(fill=tk.X)
        self.themeable_frames.append((title_frame, True))

        title_label = ttk.Label(
            title_frame,
            text="🎬 OmniFetch Pro - Media Downloader",
            style="Title.TLabel",
        )
        title_label.pack(side=tk.LEFT)

        btn_box = tk.Frame(title_frame, bg=p["CARD_BG"])
        btn_box.pack(side=tk.RIGHT)
        self.themeable_frames.append((btn_box, True))

        self.btn_theme_toggle = tk.Button(
            btn_box,
            text=p["TOGGLE_TEXT"],
            bg=p["TOGGLE_BTN_BG"],
            fg=p["TOGGLE_BTN_FG"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.toggle_theme,
        )
        self.btn_theme_toggle.pack(side=tk.RIGHT, padx=(6, 0))

        if self.ffmpeg_path:
            badge_text = "🟢 FFmpeg Detected"
            badge_bg = "#275d38"
            badge_fg = "#a6e3a1"
        else:
            badge_text = "🟡 FFmpeg Not Found"
            badge_bg = "#6e5218"
            badge_fg = "#f9e2af"

        lbl_ffmpeg = tk.Label(
            btn_box,
            text=badge_text,
            bg=badge_bg,
            fg=badge_fg,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
        )
        lbl_ffmpeg.pack(side=tk.RIGHT)

        subtitle_label = ttk.Label(
            header_card,
            text="Download single videos, playlists, or batch URLs. Convert to MP4/MKV or extract MP3/M4A/FLAC audio.",
            style="Subtitle.TLabel",
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # --- 2. URL INPUT CARD ---
        url_card = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        url_card.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((url_card, True))

        url_hdr_frame = tk.Frame(url_card, bg=p["CARD_BG"])
        url_hdr_frame.pack(fill=tk.X, pady=(0, 4))
        self.themeable_frames.append((url_hdr_frame, True))

        url_label = ttk.Label(
            url_hdr_frame,
            text="Video URL / Playlist / Batch Links (One per line):",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
        )
        url_label.pack(side=tk.LEFT)

        btn_paste = tk.Button(
            url_hdr_frame,
            text="📋 Paste Clipboard",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MAIN"],
            activebackground=p["ACCENT"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
            command=self.paste_url,
        )
        btn_paste.pack(side=tk.RIGHT)
        self.themeable_buttons.append((btn_paste, "secondary"))

        btn_fetch_info = tk.Button(
            url_hdr_frame,
            text="🔍 Check Info",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MAIN"],
            activebackground=p["ACCENT"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
            command=self.fetch_info,
        )
        btn_fetch_info.pack(side=tk.RIGHT, padx=(0, 6))
        self.themeable_buttons.append((btn_fetch_info, "secondary"))

        self.url_text = scrolledtext.ScrolledText(
            url_card,
            bg=p["INPUT_BG"],
            fg=p["TEXT_MAIN"],
            insertbackground=p["TEXT_MAIN"],
            font=("Consolas", 9),
            relief="flat",
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            height=3,
        )
        self.url_text.pack(fill=tk.X, pady=(0, 4))
        self.themeable_inputs.append(self.url_text)

        # Video Info Box
        self.info_frame = tk.Frame(
            url_card,
            bg=p["INPUT_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=10,
            pady=6,
        )
        self.themeable_frames.append((self.info_frame, True))

        self.lbl_info_title = ttk.Label(
            self.info_frame,
            text="",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
            wraplength=740,
        )
        self.lbl_info_details = ttk.Label(
            self.info_frame, text="", style="Muted.TLabel"
        )
        self.lbl_info_title.pack(anchor="w")
        self.lbl_info_details.pack(anchor="w")

        # --- 3. FORMAT & OPTIONS CARD ---
        fmt_card = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        fmt_card.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((fmt_card, True))

        mode_hdr = ttk.Label(
            fmt_card,
            text="📌 Choose Mode & Format Options:",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
        )
        mode_hdr.pack(anchor="w", pady=(0, 6))

        self.mode_var = tk.StringVar(value="video")

        mode_btn_frame = tk.Frame(fmt_card, bg=p["CARD_BG"])
        mode_btn_frame.pack(fill=tk.X, pady=(0, 8))
        self.themeable_frames.append((mode_btn_frame, True))

        self.btn_mode_video = tk.Button(
            mode_btn_frame,
            text="✅ 🎥 Video (+ Audio)",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=5,
            command=lambda: self.set_mode("video"),
        )
        self.btn_mode_video.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_mode_audio = tk.Button(
            mode_btn_frame,
            text="⬜ 🎵 Extract Audio Only",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=5,
            command=lambda: self.set_mode("audio"),
        )
        self.btn_mode_audio.pack(side=tk.LEFT)

        sep = tk.Frame(fmt_card, bg=p["CARD_BORDER"], height=1)
        sep.pack(fill=tk.X, pady=(0, 8))
        self.themeable_frames.append((sep, True))

        self.opts_container = tk.Frame(fmt_card, bg=p["CARD_BG"])
        self.opts_container.pack(fill=tk.X)
        self.themeable_frames.append((self.opts_container, True))

        # Video Options Frame
        self.video_opts_frame = tk.Frame(self.opts_container, bg=p["CARD_BG"])
        self.themeable_frames.append((self.video_opts_frame, True))

        row_v1 = tk.Frame(self.video_opts_frame, bg=p["CARD_BG"])
        row_v1.pack(fill=tk.X, pady=(0, 6))
        self.themeable_frames.append((row_v1, True))

        lbl_res = ttk.Label(row_v1, text="Resolution:", style="Card.TLabel")
        lbl_res.pack(side=tk.LEFT, padx=(0, 6))

        self.combo_res = ttk.Combobox(
            row_v1,
            values=[
                "Best Available",
                "4K (2160p)",
                "2K (1440p)",
                "1080p (Full HD)",
                "720p (HD)",
                "480p (SD)",
                "360p",
            ],
            state="readonly",
            width=20,
        )
        self.combo_res.current(0)
        self.combo_res.pack(side=tk.LEFT, padx=(0, 20))

        lbl_container = ttk.Label(
            row_v1, text="Video Format (Container):", style="Card.TLabel"
        )
        lbl_container.pack(side=tk.LEFT, padx=(0, 6))

        self.combo_container = ttk.Combobox(
            row_v1,
            values=[
                "MP4 (Recommended)",
                "MKV (Full Codec)",
                "WEBM",
                "Default / Auto",
            ],
            state="readonly",
            width=22,
        )
        self.combo_container.current(0)
        self.combo_container.pack(side=tk.LEFT)

        # Audio Options Frame
        self.audio_opts_frame = tk.Frame(self.opts_container, bg=p["CARD_BG"])
        self.themeable_frames.append((self.audio_opts_frame, True))

        row_a1 = tk.Frame(self.audio_opts_frame, bg=p["CARD_BG"])
        row_a1.pack(fill=tk.X, pady=(0, 6))
        self.themeable_frames.append((row_a1, True))

        lbl_afmt = ttk.Label(row_a1, text="Audio Format:", style="Card.TLabel")
        lbl_afmt.pack(side=tk.LEFT, padx=(0, 6))

        self.combo_audio_fmt = ttk.Combobox(
            row_a1,
            values=[
                "MP3 (Highly Compatible)",
                "M4A (AAC)",
                "WAV (Lossless)",
                "FLAC (Lossless)",
                "OPUS",
                "OGG",
            ],
            state="readonly",
            width=24,
        )
        self.combo_audio_fmt.current(0)
        self.combo_audio_fmt.pack(side=tk.LEFT, padx=(0, 20))

        lbl_abitrate = ttk.Label(
            row_a1, text="Bitrate Quality:", style="Card.TLabel"
        )
        lbl_abitrate.pack(side=tk.LEFT, padx=(0, 6))

        self.combo_audio_quality = ttk.Combobox(
            row_a1,
            values=[
                "320 kbps (Best Quality)",
                "256 kbps (High)",
                "192 kbps (Medium)",
                "128 kbps (Standard)",
                "Best Original",
            ],
            state="readonly",
            width=22,
        )
        self.combo_audio_quality.current(0)
        self.combo_audio_quality.pack(side=tk.LEFT)

        # Checkboxes (Ceklis Fitur Extra)
        sep_opts = tk.Frame(fmt_card, bg=p["CARD_BORDER"], height=1)
        sep_opts.pack(fill=tk.X, pady=(6, 6))
        self.themeable_frames.append((sep_opts, True))

        row_extras_lbl = ttk.Label(
            fmt_card,
            text="☑️ Additional Features (Pilihan Ceklis):",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
        )
        row_extras_lbl.pack(anchor="w", pady=(0, 4))

        row_extras = tk.Frame(fmt_card, bg=p["CARD_BG"])
        row_extras.pack(fill=tk.X, pady=(2, 0))
        self.themeable_frames.append((row_extras, True))

        self.chk_sub_var = tk.BooleanVar(value=False)
        chk_sub = ttk.Checkbutton(
            row_extras,
            text="📝 Subtitles (ID / EN)",
            variable=self.chk_sub_var,
            style="Custom.TCheckbutton",
        )
        chk_sub.pack(side=tk.LEFT, padx=(0, 16))

        self.chk_thumb_var = tk.BooleanVar(value=True)
        chk_thumb = ttk.Checkbutton(
            row_extras,
            text="🖼️ Cover Thumbnail",
            variable=self.chk_thumb_var,
            style="Custom.TCheckbutton",
        )
        chk_thumb.pack(side=tk.LEFT, padx=(0, 16))

        self.chk_meta_var = tk.BooleanVar(value=True)
        chk_meta = ttk.Checkbutton(
            row_extras,
            text="🏷️ Metadata Tags",
            variable=self.chk_meta_var,
            style="Custom.TCheckbutton",
        )
        chk_meta.pack(side=tk.LEFT, padx=(0, 16))

        self.chk_desc_var = tk.BooleanVar(value=False)
        chk_desc = ttk.Checkbutton(
            row_extras,
            text="📑 Save Description",
            variable=self.chk_desc_var,
            style="Custom.TCheckbutton",
        )
        chk_desc.pack(side=tk.LEFT)

        self.set_mode("video")

        # --- 4. DESTINATION FOLDER CARD ---
        dest_card = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        dest_card.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((dest_card, True))

        path_input_frame = tk.Frame(dest_card, bg=p["CARD_BG"])
        path_input_frame.pack(fill=tk.X)
        self.themeable_frames.append((path_input_frame, True))

        ttk.Label(
            path_input_frame,
            text="Save Directory:",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))

        default_dir = str(Path.home() / "Downloads")
        self.path_entry = tk.Entry(
            path_input_frame,
            bg=p["INPUT_BG"],
            fg=p["TEXT_MAIN"],
            insertbackground=p["TEXT_MAIN"],
            font=("Segoe UI", 9),
            relief="flat",
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
        )
        self.path_entry.insert(0, default_dir)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, ipadx=8)
        self.themeable_inputs.append(self.path_entry)

        btn_browse = tk.Button(
            path_input_frame,
            text="📁 Browse",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MAIN"],
            activebackground=p["ACCENT"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.browse_folder,
        )
        btn_browse.pack(side=tk.RIGHT, padx=(6, 0))
        self.themeable_buttons.append((btn_browse, "secondary"))

        btn_open_folder = tk.Button(
            path_input_frame,
            text="📂 Open",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MAIN"],
            activebackground=p["ACCENT"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.open_output_folder,
        )
        btn_open_folder.pack(side=tk.RIGHT, padx=(4, 0))
        self.themeable_buttons.append((btn_open_folder, "secondary"))

        # --- 5. ACTION & PROGRESS CARD ---
        progress_card = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=14,
            pady=12,
        )
        progress_card.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((progress_card, True))

        btn_action_frame = tk.Frame(progress_card, bg=p["CARD_BG"])
        btn_action_frame.pack(fill=tk.X, pady=(0, 8))
        self.themeable_frames.append((btn_action_frame, True))

        self.btn_download = tk.Button(
            btn_action_frame,
            text="⚡ START DOWNLOAD NOW",
            bg=p["ACCENT"],
            fg=p["ACCENT_FG"],
            activebackground=p["ACCENT_HOVER"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self.start_download,
        )
        self.btn_download.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.themeable_buttons.append((self.btn_download, "primary"))

        self.btn_cancel = tk.Button(
            btn_action_frame,
            text="❌ Cancel",
            bg=p["CARD_BORDER"],
            fg=p["ERROR"],
            activebackground=p["ERROR"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            state=tk.DISABLED,
            padx=14,
            pady=6,
            command=self.cancel_download,
        )
        self.btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        self.progress_bar = ttk.Progressbar(
            progress_card,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        stats_frame = tk.Frame(progress_card, bg=p["CARD_BG"])
        stats_frame.pack(fill=tk.X)
        self.themeable_frames.append((stats_frame, True))

        self.lbl_status = ttk.Label(
            stats_frame, text="Ready to download.", style="Card.TLabel"
        )
        self.lbl_status.pack(side=tk.LEFT, anchor="w")

        self.lbl_speed_eta = ttk.Label(stats_frame, text="", style="Muted.TLabel")
        self.lbl_speed_eta.pack(side=tk.RIGHT, anchor="e")

        # --- 6. CONSOLE LOG ---
        log_frame = tk.Frame(container, bg=p["BG_DARK"])
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.themeable_frames.append((log_frame, False))

        log_hdr = tk.Frame(log_frame, bg=p["BG_DARK"])
        log_hdr.pack(fill=tk.X, pady=(0, 2))
        self.themeable_frames.append((log_hdr, False))

        ttk.Label(
            log_hdr,
            text="Log Activity / Terminal Output:",
            font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.LEFT)

        btn_clear_log = tk.Button(
            log_hdr,
            text="Clear",
            bg=p["BG_DARK"],
            fg=p["TEXT_MUTED"],
            activebackground=p["BG_DARK"],
            activeforeground=p["TEXT_MAIN"],
            font=("Segoe UI", 8),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.clear_log,
        )
        btn_clear_log.pack(side=tk.RIGHT)
        self.themeable_buttons.append((btn_clear_log, "clear"))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=p["INPUT_BG"],
            fg=p["TEXT_MUTED"],
            insertbackground=p["TEXT_MAIN"],
            font=("Consolas", 8),
            relief="flat",
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            height=4,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.themeable_inputs.append(self.log_text)

    # ---------------- TAB 2: HISTORY ----------------

    def build_tab_history(self):
        container = self.tab_history
        p = self.palette

        hdr = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        hdr.pack(fill=tk.X, pady=(0, 10))
        self.themeable_frames.append((hdr, True))

        ttk.Label(
            hdr, text="📜 Registered Download History", style="Title.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            hdr,
            text="List of successfully downloaded media files. You can play files or open file locations directly.",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        toolbar = tk.Frame(container, bg=p["BG_DARK"])
        toolbar.pack(fill=tk.X, pady=(0, 8))
        self.themeable_frames.append((toolbar, False))

        btn_play = tk.Button(
            toolbar,
            text="▶️ Play File",
            bg=p["ACCENT"],
            fg=p["ACCENT_FG"],
            activebackground=p["ACCENT_HOVER"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.history_open_file,
        )
        btn_play.pack(side=tk.LEFT, padx=(0, 6))
        self.themeable_buttons.append((btn_play, "primary"))

        btn_folder = tk.Button(
            toolbar,
            text="📂 Open Folder",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MAIN"],
            activebackground=p["ACCENT"],
            activeforeground=p["ACCENT_FG"],
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.history_open_folder,
        )
        btn_folder.pack(side=tk.LEFT, padx=(0, 6))
        self.themeable_buttons.append((btn_folder, "secondary"))

        btn_del = tk.Button(
            toolbar,
            text="🗑️ Delete Entry",
            bg=p["CARD_BORDER"],
            fg=p["ERROR"],
            activebackground=p["ERROR"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.history_delete_item,
        )
        btn_del.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear_all = tk.Button(
            toolbar,
            text="🧹 Clear All",
            bg=p["CARD_BORDER"],
            fg=p["TEXT_MUTED"],
            activebackground=p["ERROR"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.history_clear_all,
        )
        btn_clear_all.pack(side=tk.RIGHT)

        tree_frame = tk.Frame(
            container,
            bg=p["CARD_BG"],
            highlightbackground=p["CARD_BORDER"],
            highlightthickness=1,
        )
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.themeable_frames.append((tree_frame, True))

        columns = ("datetime", "title", "format", "filepath")
        self.tree_history = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )

        self.tree_history.heading("datetime", text="Date/Time")
        self.tree_history.heading("title", text="Media Title")
        self.tree_history.heading("format", text="Format")
        self.tree_history.heading("filepath", text="File Location")

        self.tree_history.column("datetime", width=140, anchor="w")
        self.tree_history.column("title", width=290, anchor="w")
        self.tree_history.column("format", width=90, anchor="center")
        self.tree_history.column("filepath", width=250, anchor="w")

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree_history.yview
        )
        self.tree_history.configure(yscrollcommand=scrollbar.set)

        self.tree_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_history.bind("<Double-1>", lambda e: self.history_open_file())

    # ---------------- HISTORY PERSISTENCE ----------------

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"[WARN History] Failed to save history: {e}")

    def add_to_history(self, title, fmt_name, filepath):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        item = {
            "datetime": now_str,
            "title": title,
            "format": fmt_name,
            "filepath": filepath,
        }
        self.history_data.insert(0, item)
        self.save_history()
        self.render_history_table()

    def render_history_table(self):
        if not hasattr(self, "tree_history"):
            return
        for row in self.tree_history.get_children():
            self.tree_history.delete(row)

        for item in self.history_data:
            self.tree_history.insert(
                "",
                tk.END,
                values=(
                    item.get("datetime", ""),
                    item.get("title", "Unknown"),
                    item.get("format", "-"),
                    item.get("filepath", ""),
                ),
            )

    def history_open_file(self):
        selected = self.tree_history.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a history entry first!")
            return
        values = self.tree_history.item(selected[0], "values")
        filepath = values[3]

        if os.path.exists(filepath):
            os.startfile(filepath)
        else:
            messagebox.showerror(
                "File Not Found",
                f"The file was moved or deleted:\n{filepath}",
            )

    def history_open_folder(self):
        selected = self.tree_history.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a history entry first!")
            return
        values = self.tree_history.item(selected[0], "values")
        filepath = values[3]
        folder = os.path.dirname(filepath)

        if os.path.exists(filepath):
            subprocess.run(["explorer", "/select,", os.path.normpath(filepath)])
        elif os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showerror("Error", "Directory not found!")

    def history_delete_item(self):
        selected = self.tree_history.selection()
        if not selected:
            return
        idx = self.tree_history.index(selected[0])
        if 0 <= idx < len(self.history_data):
            del self.history_data[idx]
            self.save_history()
            self.render_history_table()

    def history_clear_all(self):
        if not self.history_data:
            return
        if messagebox.askyesno(
            "Confirmation", "Are you sure you want to clear all download history?"
        ):
            self.history_data = []
            self.save_history()
            self.render_history_table()

    # ---------------- HANDLERS & HELPERS ----------------

    def set_mode(self, mode):
        self.mode_var.set(mode)
        self.update_mode_buttons()
        self.on_mode_change()

    def update_mode_buttons(self):
        if not hasattr(self, "btn_mode_video") or not hasattr(self, "btn_mode_audio"):
            return
        p = self.palette
        if self.mode_var.get() == "video":
            self.btn_mode_video.config(
                text="✅ 🎥 Video (+ Audio)",
                bg=p["ACCENT"],
                fg=p["ACCENT_FG"],
                activebackground=p["ACCENT_HOVER"],
                activeforeground=p["ACCENT_FG"],
            )
            self.btn_mode_audio.config(
                text="⬜ 🎵 Extract Audio Only",
                bg=p["INPUT_BG"],
                fg=p["TEXT_MUTED"],
                activebackground=p["CARD_BORDER"],
                activeforeground=p["TEXT_MAIN"],
            )
        else:
            self.btn_mode_video.config(
                text="⬜ 🎥 Video (+ Audio)",
                bg=p["INPUT_BG"],
                fg=p["TEXT_MUTED"],
                activebackground=p["CARD_BORDER"],
                activeforeground=p["TEXT_MAIN"],
            )
            self.btn_mode_audio.config(
                text="✅ 🎵 Extract Audio Only",
                bg=p["ACCENT"],
                fg=p["ACCENT_FG"],
                activebackground=p["ACCENT_HOVER"],
                activeforeground=p["ACCENT_FG"],
            )

    def on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "video":
            self.audio_opts_frame.pack_forget()
            self.video_opts_frame.pack(fill=tk.X)
        else:
            self.video_opts_frame.pack_forget()
            self.audio_opts_frame.pack(fill=tk.X)

    def paste_url(self):
        try:
            clipboard = self.root.clipboard_get().strip()
            if clipboard:
                self.url_text.delete("1.0", tk.END)
                self.url_text.insert("1.0", clipboard)
        except tk.TclError:
            pass

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_entry.get())
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def open_output_folder(self):
        folder = self.path_entry.get().strip()
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showwarning("Warning", "Save directory not found!")

    def log(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def set_ui_downloading(self, downloading):
        self.is_downloading = downloading
        p = self.palette
        if downloading:
            self.btn_download.config(state=tk.DISABLED, bg=p["CARD_BORDER"])
            self.btn_cancel.config(state=tk.NORMAL, bg=p["ERROR"], fg="#ffffff")
        else:
            self.btn_download.config(
                state=tk.NORMAL, bg=p["ACCENT"], fg=p["ACCENT_FG"]
            )
            self.btn_cancel.config(
                state=tk.DISABLED, bg=p["CARD_BORDER"], fg=p["ERROR"]
            )

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.log("[!] Requesting download cancellation...")
            self.lbl_status.config(
                text="Cancelling download...", foreground=self.palette["ERROR"]
            )

    def fetch_info(self):
        raw_text = self.url_text.get("1.0", tk.END).strip()
        urls = [u.strip() for u in raw_text.splitlines() if u.strip()]

        if not urls:
            messagebox.showwarning("Warning", "Please enter a video URL!")
            return

        target_url = urls[0]
        self.lbl_status.config(
            text="🔍 Fetching video metadata...", foreground=self.palette["ACCENT"]
        )
        self.log(f"[+] Checking metadata: {target_url}")

        def _worker():
            try:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "nocheckcertificate": True,
                }
                if self.ffmpeg_path:
                    ydl_opts["ffmpeg_location"] = self.ffmpeg_path

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(target_url, download=False)
                    is_playlist = "entries" in info
                    if is_playlist:
                        title = f"Playlist: {info.get('title', 'Unknown Playlist')}"
                        count = len(list(info.get("entries") or []))
                        uploader = info.get("uploader") or "Playlist Channel"
                        dur_str = f"{count} Videos in Playlist"
                    else:
                        title = info.get("title", "Unknown Title")
                        duration = info.get("duration", 0)
                        uploader = (
                            info.get("uploader") or info.get("channel") or "Unknown"
                        )
                        dur_str = (
                            f"{duration // 60:02d}:{duration % 60:02d}"
                            if duration
                            else "N/A"
                        )

                    self.msg_queue.put(
                        (
                            "fetched_info",
                            {
                                "title": title,
                                "uploader": uploader,
                                "duration": dur_str,
                            },
                        )
                    )
            except Exception as e:
                self.msg_queue.put(("fetch_error", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def build_format_opts(self):
        mode = self.mode_var.get()
        opts = {}

        if mode == "video":
            res_val = self.combo_res.get()
            container_val = self.combo_container.get()

            if "4K" in res_val:
                fmt_str = "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"
            elif "2K" in res_val:
                fmt_str = "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"
            elif "1080p" in res_val:
                fmt_str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif "720p" in res_val:
                fmt_str = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            elif "480p" in res_val:
                fmt_str = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            elif "360p" in res_val:
                fmt_str = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
            else:
                fmt_str = "bestvideo+bestaudio/best"

            opts["format"] = fmt_str

            if "MP4" in container_val:
                opts["merge_output_format"] = "mp4"
            elif "MKV" in container_val:
                opts["merge_output_format"] = "mkv"
            elif "WEBM" in container_val:
                opts["merge_output_format"] = "webm"

        else:
            afmt_val = self.combo_audio_fmt.get().split()[0].lower()
            bitrate_val = self.combo_audio_quality.get()

            opts["format"] = "bestaudio/best"
            target_quality = "320"
            for k in ["320", "256", "192", "128"]:
                if k in bitrate_val:
                    target_quality = k
                    break

            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": afmt_val,
                    "preferredquality": target_quality,
                }
            ]

        postprocessors = opts.get("postprocessors", [])

        if self.chk_thumb_var.get():
            opts["writethumbnail"] = True
            postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
            postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

        if self.chk_sub_var.get():
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = True
            opts["subtitleslangs"] = ["id", "en"]
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})

        if hasattr(self, "chk_meta_var") and self.chk_meta_var.get():
            opts["addmetadata"] = True
            postprocessors.append({"key": "FFmpegMetadata"})

        if hasattr(self, "chk_desc_var") and self.chk_desc_var.get():
            opts["writedescription"] = True

        if postprocessors:
            opts["postprocessors"] = postprocessors

        return opts

    def start_download(self):
        if yt_dlp is None:
            messagebox.showerror("Error", "yt-dlp module not found!")
            return

        raw_text = self.url_text.get("1.0", tk.END).strip()
        urls = [u.strip() for u in raw_text.splitlines() if u.strip()]
        out_dir = self.path_entry.get().strip()

        if not urls:
            messagebox.showwarning(
                "Warning", "Please enter at least one video URL!"
            )
            return

        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory:\n{e}")
                return

        self.set_ui_downloading(True)
        self.cancel_requested = False
        self.progress_bar["value"] = 0
        self.lbl_status.config(
            text="Connecting & analyzing streams...", foreground=self.palette["ACCENT"]
        )
        self.lbl_speed_eta.config(text="")

        fmt_opts = self.build_format_opts()
        mode_name = "Video" if self.mode_var.get() == "video" else "Audio"
        self.log(f"[+] Starting Batch Download ({len(urls)} links) [{mode_name}]...")
        self.log(f"[+] Target folder: {out_dir}")

        thread = threading.Thread(
            target=self._batch_download_worker,
            args=(urls, out_dir, fmt_opts),
            daemon=True,
        )
        thread.start()

    def _progress_hook(self, d):
        if self.cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total > 0 else 0

            speed = d.get("speed") or 0
            speed_mb = speed / (1024 * 1024) if speed else 0
            eta = d.get("eta") or 0

            filename = os.path.basename(d.get("filename", ""))
            self.msg_queue.put(
                (
                    "progress",
                    {
                        "percent": percent,
                        "downloaded_mb": downloaded / (1024 * 1024),
                        "total_mb": total / (1024 * 1024),
                        "speed_mb": speed_mb,
                        "eta": eta,
                        "filename": filename,
                    },
                )
            )
        elif status == "finished":
            filename = os.path.basename(d.get("filename", ""))
            self.msg_queue.put(
                ("status_update", f"Stream download complete ({filename}). Post-processing...")
            )
            self.msg_queue.put(("log", f"[+] Stream complete: {filename}"))

    def _batch_download_worker(self, urls, out_dir, fmt_opts):
        completed_count = 0
        total_urls = len(urls)

        for idx, url in enumerate(urls, start=1):
            if self.cancel_requested:
                break

            self.msg_queue.put(
                (
                    "status_update",
                    f"Downloading Item {idx}/{total_urls}: {url[:40]}...",
                )
            )
            self.msg_queue.put(
                ("log", f"[ Item {idx}/{total_urls} ] Processing URL: {url}")
            )

            try:
                ydl_opts = {
                    "outtmpl": os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s"),
                    "progress_hooks": [self._progress_hook],
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_color": True,
                    "socket_timeout": 30,
                    "retries": 10,
                    "fragment_retries": 10,
                    "ignoreerrors": True,
                }
                if self.ffmpeg_path:
                    ydl_opts["ffmpeg_location"] = self.ffmpeg_path

                ydl_opts.update(fmt_opts)

                class YtLogger:
                    def __init__(self, q):
                        self.q = q

                    def debug(self, msg):
                        msg_str = str(msg).strip()
                        if not msg_str:
                            return
                        if any(
                            msg_str.startswith(prefix)
                            for prefix in [
                                "[download]",
                                "[Merger]",
                                "[ExtractAudio]",
                                "[EmbedThumbnail]",
                                "[ffmpeg]",
                                "[info]",
                                "Deleting",
                            ]
                        ):
                            self.q.put(("log", msg_str))

                        if "[Merger]" in msg_str or "Merging formats" in msg_str:
                            self.q.put(
                                (
                                    "status_update",
                                    "Merging video & audio streams with FFmpeg...",
                                )
                            )
                        elif "[ExtractAudio]" in msg_str:
                            self.q.put(
                                (
                                    "status_update",
                                    "Extracting & converting audio stream...",
                                )
                            )
                        elif "[EmbedThumbnail]" in msg_str:
                            self.q.put(
                                (
                                    "status_update",
                                    "Embedding cover thumbnail into file...",
                                )
                            )

                    def warning(self, msg):
                        self.q.put(("log", f"[WARN] {msg}"))

                    def error(self, msg):
                        self.q.put(("log", f"[ERROR] {msg}"))

                ydl_opts["logger"] = YtLogger(self.msg_queue)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.current_ydl = ydl
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Media File") if info else "Media File"

                    ext = info.get("ext", "mp4") if info else "mp4"
                    if fmt_opts.get("merge_output_format"):
                        ext = fmt_opts["merge_output_format"]
                    elif self.mode_var.get() == "audio":
                        ext = self.combo_audio_fmt.get().split()[0].lower()

                    file_id = info.get("id", "") if info else ""
                    final_path = os.path.join(out_dir, f"{title} [{file_id}].{ext}")
                    if not os.path.exists(final_path):
                        final_path = os.path.join(out_dir, f"{title}.{ext}")

                    mode_label = (
                        "Video"
                        if self.mode_var.get() == "video"
                        else self.combo_audio_fmt.get().split()[0]
                    )
                    self.msg_queue.put(
                        (
                            "item_completed",
                            {
                                "title": title,
                                "format": mode_label,
                                "filepath": final_path,
                            },
                        )
                    )
                    completed_count += 1

            except yt_dlp.utils.DownloadCancelled:
                self.msg_queue.put(("cancelled", None))
                return
            except Exception as e:
                self.msg_queue.put(("error_item", f"Failed {url}: {e}"))

        if not self.cancel_requested:
            self.msg_queue.put(
                ("batch_completed", f"{completed_count}/{total_urls}")
            )

    def process_queue(self):
        p = self.palette
        while not self.msg_queue.empty():
            try:
                msg_type, payload = self.msg_queue.get_nowait()

                if msg_type == "progress":
                    percent = payload["percent"]
                    self.progress_bar["value"] = percent

                    speed = (
                        f"{payload['speed_mb']:.1f} MB/s"
                        if payload["speed_mb"] > 0
                        else "-- MB/s"
                    )
                    eta_sec = payload["eta"]
                    eta = (
                        f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"
                        if eta_sec
                        else "--:--"
                    )
                    size_str = (
                        f"{payload['downloaded_mb']:.1f}MB / {payload['total_mb']:.1f}MB"
                        if payload["total_mb"] > 0
                        else ""
                    )

                    self.lbl_status.config(
                        text=f"Downloading: {percent:.1f}% ({size_str})",
                        foreground=p["TEXT_MAIN"],
                    )
                    self.lbl_speed_eta.config(text=f"Speed: {speed}  |  ETA: {eta}")

                elif msg_type == "status_update":
                    self.lbl_status.config(text=payload, foreground=p["ACCENT"])
                elif msg_type == "log":
                    self.log(payload)
                elif msg_type == "fetched_info":
                    self.lbl_info_title.config(text=f"📌 {payload['title']}")
                    self.lbl_info_details.config(
                        text=f"Channel: {payload['uploader']}   |   Detail: {payload['duration']}"
                    )
                    self.info_frame.pack(fill=tk.X, pady=(4, 0))
                    self.lbl_status.config(
                        text="Video/playlist metadata fetched successfully.",
                        foreground=p["SUCCESS"],
                    )
                    self.log(f"[✓] Info: {payload['title']}")

                elif msg_type == "fetch_error":
                    self.lbl_status.config(
                        text="Failed to fetch video info.", foreground=p["ERROR"]
                    )
                    self.log(f"[ERROR Metadata] {payload}")

                elif msg_type == "item_completed":
                    self.add_to_history(
                        payload["title"],
                        payload["format"],
                        payload["filepath"],
                    )
                    self.log(f"[✓] Added to History: {payload['title']}")

                elif msg_type == "batch_completed":
                    self.progress_bar["value"] = 100
                    self.lbl_status.config(
                        text="✅ All Batch Downloads Complete!",
                        foreground=p["SUCCESS"],
                    )
                    self.lbl_speed_eta.config(text="")
                    self.log(f"[✓] Completed {payload} items!")
                    self.set_ui_downloading(False)
                    messagebox.showinfo(
                        "Batch Download Complete",
                        f"All items have been downloaded successfully ({payload})!\nCheck the Download History tab to access files.",
                    )

                elif msg_type == "cancelled":
                    self.progress_bar["value"] = 0
                    self.lbl_status.config(
                        text="⚠️ Download Cancelled", foreground=p["ERROR"]
                    )
                    self.lbl_speed_eta.config(text="")
                    self.log("[!] Download has been cancelled.")
                    self.set_ui_downloading(False)

                elif msg_type == "error_item":
                    self.log(f"[ERROR Item] {payload}")

            except queue.Empty:
                break

        self.root.after(100, self.process_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = YtDlpGUI(root)
    root.mainloop()
