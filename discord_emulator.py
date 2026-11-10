# -*- coding: utf-8 -*-
import os
import sys
import re
import time
import glob
import math
import base64
import shutil
import subprocess
import threading
import json
import winreg
import ctypes
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox

# Импортируем языки из отдельного файла locales.py
try:
    from locales import LOCALES as TRANSLATIONS, DEFAULT_LANG as DEFAULT_LANGUAGE
except ImportError as err:
    raise SystemExit("Файл locales.py не найден! Положите locales.py в одну папку с discord_emulator.py.") from err

# 1. Включаем High-DPI масштабирование и скрываем консоль
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_hwnd:
            ctypes.windll.user32.ShowWindow(console_hwnd, 0)
    except Exception:
        pass

APP_VERSION = "0.15.1 beta"
APP_VERSION_NUM = (0, 15, 1)
APP_TITLE = f"Discord Farmix v{APP_VERSION}"

GITHUB_REPO = "ItsGudarak/Farmix"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
GITHUB_COMMITS_API = f"https://api.github.com/repos/{GITHUB_REPO}/commits?per_page=10"
GITHUB_RAW_MAIN = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"

AUTORUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTORUN_REG_NAME = "DiscordFarmix"

DISCORD_API_BASE = "https://discord.com/api/v9"
DISCORD_DETECTABLE_URL = f"{DISCORD_API_BASE}/applications/detectable"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WORK_DIR = os.path.join(BASE_DIR, "fake_games")
CACHE_AVATARS_DIR = os.path.join(WORK_DIR, "cache", "avatars")
CACHE_ICONS_DIR = os.path.join(WORK_DIR, "cache", "game_icons")
CACHE_BANNERS_DIR = os.path.join(WORK_DIR, "cache", "quest_banners")
CACHE_REWARDS_DIR = os.path.join(WORK_DIR, "cache", "reward_items")
CACHE_UI_DIR = os.path.join(WORK_DIR, "cache", "ui")
LOCAL_JSON_PATH = os.path.join(BASE_DIR, "detectable.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config_farmix.json")
QUEST_TARGET_SECONDS = (15 * 60) + 10

DWM_GLASS_KEY = "#010102"
PLAY_TASK_TYPES = ("PLAY_ON_DESKTOP", "PLAY_ON_DESKTOP_V2", "STREAM_ON_DESKTOP", "PLAY_ACTIVITY")

COLORS = {
    "bg_window": DWM_GLASS_KEY,
    "bg_card": "#232327",
    "bg_card_highlight": "#2A2A30",
    "border_card": "#36363C",
    "bg_input": "#1A1A1D",
    "bg_selected": "#32323A",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9E9EA8",
    "accent": "#60CDFF",
    "accent_hover": "#82D9FF",
    "accent_text": "#000000",
    "orb_purple": "#C88CFF",
    "item_gold": "#FFB74D",
    "item_bg": "#2E251A",
    "nitro_pink": "#FF73FA",
    "nitro_bg": "#381F3A",
    "vip_gold": "#FFD700",
    "vip_bg": "#3A3218",
    "secondary_btn": "#323238",
    "secondary_hover": "#42424A",
    "danger": "#FF99A4",
    "danger_bg": "#442726",
    "danger_hover": "#5C3130",
    "success": "#6CCB5F",
    "warning": "#FCE100",
}

DUMMY_CS_CODE = """
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

[ComImport]
[Guid("56FDF342-FD6D-11d0-958A-006097C9A090")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface ITaskbarList {
    void HrInit();
    void AddTab(IntPtr hwnd);
    void DeleteTab(IntPtr hwnd);
    void ActivateTab(IntPtr hwnd);
    void SetActiveAlt(IntPtr hwnd);
}

[ComImport]
[Guid("56FDF344-FD6D-11d0-958A-006097C9A090")]
class TaskbarList { }

class DummyGame : Form {
    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateRectRgn(int x1, int y1, int x2, int y2);
    [DllImport("user32.dll")]
    private static extern int SetWindowRgn(IntPtr hWnd, IntPtr hRgn, bool bRedraw);
    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    public DummyGame(string title) {
        this.Text = title;
        this.Size = new Size(120, 80);
        this.StartPosition = FormStartPosition.Manual;
        this.Location = new Point(-3200, -3200);
        this.ShowInTaskbar = true;
        this.FormBorderStyle = FormBorderStyle.FixedSingle;

        this.Load += (s, e) => {
            IntPtr rgn = CreateRectRgn(0, 0, 0, 0);
            SetWindowRgn(this.Handle, rgn, true);
            try {
                ITaskbarList tbl = (ITaskbarList)new TaskbarList();
                tbl.HrInit();
                tbl.DeleteTab(this.Handle);
            } catch { }
        };

        this.Shown += (s, e) => {
            IntPtr prevFg = GetForegroundWindow();
            SetForegroundWindow(this.Handle);
            Timer restoreTimer = new Timer { Interval = 60 };
            restoreTimer.Tick += (ts, te) => {
                restoreTimer.Stop();
                if (prevFg != IntPtr.Zero) SetForegroundWindow(prevFg);
            };
            restoreTimer.Start();
        };
    }

    [STAThread]
    static void Main(string[] args) {
        Application.EnableVisualStyles();
        Application.Run(new DummyGame(args.Length > 0 ? args[0] : "Game"));
    }
}
"""

IMAGE_PROC_CS_CODE = """
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;

class ImageProcessor {
    static void Main(string[] args) {
        if (args.Length < 5) return;
        string mode = args[0];
        string inPath = args[1];
        string outPath = args[2];
        int targetW = int.Parse(args[3]);
        int targetH = int.Parse(args[4]);

        try {
            using (Image src = Image.FromFile(inPath)) {
                using (Bitmap bmp = new Bitmap(targetW, targetH, PixelFormat.Format32bppArgb)) {
                    using (Graphics g = Graphics.FromImage(bmp)) {
                        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                        g.SmoothingMode = SmoothingMode.AntiAlias;
                        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                        g.Clear(Color.Transparent);

                        if (mode == "icon") {
                            g.DrawImage(src, new Rectangle(0, 0, targetW, targetH));
                        } else if (mode == "banner") {
                            float srcRatio = (float)src.Width / src.Height;
                            float dstRatio = (float)targetW / targetH;
                            int cropW = src.Width, cropH = src.Height, cropX = 0, cropY = 0;
                            if (srcRatio > dstRatio) {
                                cropW = (int)(src.Height * dstRatio);
                                cropX = (src.Width - cropW) / 2;
                            } else {
                                cropH = (int)(src.Width / dstRatio);
                                cropY = (src.Height - cropH) / 3;
                            }
                            g.DrawImage(src, new Rectangle(0, 0, targetW, targetH), new Rectangle(cropX, cropY, cropW, cropH), GraphicsUnit.Pixel);

                            using (LinearGradientBrush brush = new LinearGradientBrush(
                                new Rectangle(0, 0, targetW, targetH),
                                Color.FromArgb(238, 19, 20, 26),
                                Color.FromArgb(140, 24, 25, 34),
                                LinearGradientMode.Horizontal)) {
                                g.FillRectangle(brush, new Rectangle(0, 0, targetW, targetH));
                            }
                        } else if (mode == "iconbanner") {
                            g.Clear(Color.FromArgb(255, 24, 25, 32));
                            int zoomH = targetW;
                            int zoomY = -(zoomH - targetH) / 2;
                            g.DrawImage(src, new Rectangle(targetW / 5, zoomY, zoomH, zoomH));
                            using (LinearGradientBrush brush = new LinearGradientBrush(
                                new Rectangle(0, 0, targetW, targetH),
                                Color.FromArgb(245, 20, 21, 27),
                                Color.FromArgb(185, 26, 27, 36),
                                LinearGradientMode.Horizontal)) {
                                g.FillRectangle(brush, new Rectangle(0, 0, targetW, targetH));
                            }
                            int icoSz = targetH - 20;
                            g.DrawImage(src, new Rectangle(targetW - 205, 10, icoSz, icoSz));
                        }
                    }
                    bmp.Save(outPath, ImageFormat.Png);
                }
            }
        } catch { }
    }
}
"""

TOAST_CS_CODE = """
using System;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

class ToastSender {
    [STAThread]
    static void Main(string[] args) {
        string title = args.Length > 0 ? args[0] : "Discord Farmix";
        string body = args.Length > 1 ? args[1] : "Quest Complete!";
        using (NotifyIcon ni = new NotifyIcon()) {
            ni.Icon = SystemIcons.Information;
            ni.Text = "Discord Farmix";
            ni.Visible = true;
            ni.ShowBalloonTip(5000, title, body, ToolTipIcon.Info);
            Thread.Sleep(5500);
            ni.Visible = false;
        }
    }
}
"""

TOKEN_DECRYPTOR_CS = """
using System;
using System.Text;
using System.Security.Cryptography;
using System.Runtime.InteropServices;

class TokenDecryptor {
    [StructLayout(LayoutKind.Sequential)]
    public struct BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO {
        public int cbSize;
        public int dwInfoVersion;
        public IntPtr pbNonce;
        public int cbNonce;
        public IntPtr pbAuthData;
        public int cbAuthData;
        public IntPtr pbTag;
        public int cbTag;
        public IntPtr pbMacContext;
        public int cbMacContext;
        public int cbAAD;
        public long cbData;
        public int dwFlags;
    }

    [DllImport("bcrypt.dll")]
    static extern int BCryptOpenAlgorithmProvider(out IntPtr phAlgorithm, [MarshalAs(UnmanagedType.LPWStr)] string pszAlgId, [MarshalAs(UnmanagedType.LPWStr)] string pszImplementation, uint dwFlags);
    [DllImport("bcrypt.dll")]
    static extern int BCryptSetProperty(IntPtr hObject, [MarshalAs(UnmanagedType.LPWStr)] string pszProperty, byte[] pbInput, int cbInput, int dwFlags);
    [DllImport("bcrypt.dll")]
    static extern int BCryptGenerateSymmetricKey(IntPtr hAlgorithm, out IntPtr phKey, IntPtr pbKeyObject, int cbKeyObject, byte[] pbSecret, int cbSecret, uint dwFlags);
    [DllImport("bcrypt.dll")]
    static extern int BCryptDecrypt(IntPtr hKey, byte[] pbInput, int cbInput, ref BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO pPaddingInfo, byte[] pbIV, int cbIV, byte[] pbOutput, int cbOutput, out int pcbResult, uint dwFlags);
    [DllImport("bcrypt.dll")]
    static extern int BCryptDestroyKey(IntPtr hKey);
    [DllImport("bcrypt.dll")]
    static extern int BCryptCloseAlgorithmProvider(IntPtr hAlgorithm, uint dwFlags);

    static byte[] DecryptAesGcm(byte[] key, byte[] nonce, byte[] cipher, byte[] tag) {
        IntPtr hAlg, hKey;
        if (BCryptOpenAlgorithmProvider(out hAlg, "AES", null, 0) != 0) return null;
        byte[] chainMode = Encoding.Unicode.GetBytes("ChainingModeGCM\\0");
        BCryptSetProperty(hAlg, "ChainingMode", chainMode, chainMode.Length, 0);
        if (BCryptGenerateSymmetricKey(hAlg, out hKey, IntPtr.Zero, 0, key, key.Length, 0) != 0) {
            BCryptCloseAlgorithmProvider(hAlg, 0);
            return null;
        }
        var authInfo = new BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO();
        authInfo.cbSize = Marshal.SizeOf(authInfo);
        authInfo.dwInfoVersion = 1;
        IntPtr pNonce = Marshal.AllocHGlobal(nonce.Length);
        IntPtr pTag = Marshal.AllocHGlobal(tag.Length);
        Marshal.Copy(nonce, 0, pNonce, nonce.Length);
        Marshal.Copy(tag, 0, pTag, tag.Length);
        authInfo.pbNonce = pNonce;
        authInfo.cbNonce = nonce.Length;
        authInfo.pbTag = pTag;
        authInfo.cbTag = tag.Length;

        byte[] plain = new byte[cipher.Length];
        int pcbResult = 0;
        int status = BCryptDecrypt(hKey, cipher, cipher.Length, ref authInfo, null, 0, plain, plain.Length, out pcbResult, 0);

        Marshal.FreeHGlobal(pNonce);
        Marshal.FreeHGlobal(pTag);
        BCryptDestroyKey(hKey);
        BCryptCloseAlgorithmProvider(hAlg, 0);
        return status == 0 ? plain : null;
    }

    static void Main(string[] args) {
        if (args.Length < 2) return;
        try {
            byte[] encKeyWithPrefix = Convert.FromBase64String(args[0]);
            byte[] encKey = new byte[encKeyWithPrefix.Length - 5];
            Array.Copy(encKeyWithPrefix, 5, encKey, 0, encKey.Length);
            byte[] masterKey = ProtectedData.Unprotect(encKey, null, DataProtectionScope.CurrentUser);

            for (int i = 1; i < args.Length; i++) {
                try {
                    byte[] raw = Convert.FromBase64String(args[i]);
                    byte[] nonce = new byte[12];
                    byte[] cipher = new byte[raw.Length - 3 - 12 - 16];
                    byte[] tag = new byte[16];
                    Array.Copy(raw, 3, nonce, 0, 12);
                    Array.Copy(raw, 15, cipher, 0, cipher.Length);
                    Array.Copy(raw, raw.Length - 16, tag, 0, 16);
                    byte[] dec = DecryptAesGcm(masterKey, nonce, cipher, tag);
                    if (dec != null) Console.WriteLine(Encoding.UTF8.GetString(dec));
                } catch {}
            }
        } catch {}
    }
}
"""


class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int), ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]


def apply_win11_native_backdrop(hwnd, backdrop_mode=2):
    if not hwnd:
        return
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(0x00242020)), 4)
        margins = MARGINS(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(int(backdrop_mode))), 4)
    except Exception:
        pass


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(c))) for c in rgb))


def parse_semver_tuple(ver_str):
    nums = [int(x) for x in re.findall(r"\d+", str(ver_str))]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


class AnimatedButton(tk.Button):
    def __init__(self, master, bg_color, hover_color, fg_color, **kwargs):
        super().__init__(
            master, bg=bg_color, fg=fg_color, activebackground=hover_color,
            activeforeground=fg_color, relief=tk.FLAT, bd=0, cursor="hand2", takefocus=0, **kwargs
        )
        self.default_bg, self.hover_bg, self.current_bg = bg_color, hover_color, bg_color
        self._anim_job = None
        self.bind("<Enter>", lambda _: self._animate_to(self.hover_bg))
        self.bind("<Leave>", lambda _: self._animate_to(self.default_bg))

    def set_palette(self, bg_color, hover_color, fg_color, animate=True):
        self.default_bg, self.hover_bg = bg_color, hover_color
        self.config(fg=fg_color, activebackground=hover_color, activeforeground=fg_color)
        if animate:
            self._animate_to(bg_color, steps=6)
        else:
            self.current_bg = bg_color
            self.config(bg=bg_color)

    def _animate_to(self, target_hex, steps=8):
        if str(self["state"]) == "disabled":
            return
        if self._anim_job:
            self.after_cancel(self._anim_job)
        s_rgb, t_rgb = hex_to_rgb(self.current_bg), hex_to_rgb(target_hex)

        def _step(s):
            t = s / float(steps)
            self.current_bg = rgb_to_hex(tuple(s_rgb[i] + (t_rgb[i] - s_rgb[i]) * t for i in range(3)))
            self.config(bg=self.current_bg)
            if s < steps:
                self._anim_job = self.after(12, _step, s + 1)

        _step(1)


class DiscordFarmixApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=DWM_GLASS_KEY)
        self.root.attributes("-transparentcolor", DWM_GLASS_KEY)

        for d in (CACHE_AVATARS_DIR, CACHE_ICONS_DIR, CACHE_BANNERS_DIR, CACHE_REWARDS_DIR, CACHE_UI_DIR):
            os.makedirs(d, exist_ok=True)

        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = min(1210, int(sw * 0.92)), min(790, int(sh * 0.88))
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.root.minsize(1080, 690)
        self.root.resizable(True, True)

        self.hwnd = None
        self.games_data = []
        self.filtered_games = []
        self.fetched_quests_cache = []
        self.quest_card_banners = {}
        self.quest_reward_icons_24 = {}
        self.quest_reward_icons_36 = {}
        self.quest_card_canvases = []
        self.animated_cards_list = []
        self.active_processes = []
        self.start_time = None
        self.timer_running = False
        self.quest_notified = False
        self.is_authenticated = False
        self.current_quest_target_sec = QUEST_TARGET_SECONDS

        self.current_reward_state = {"type": "none", "amount": 0, "name": "", "quest_id": ""}

        self.base_dummy_exe = None
        self.decryptor_exe = None
        self.toast_exe = None
        self.img_proc_exe = None

        self.avatar_photo = None
        self.game_icon_photo = None
        self.orbs_photo_56 = None
        self.orbs_photo_36 = None
        self.orbs_photo_22 = None

        self.lang = DEFAULT_LANGUAGE if DEFAULT_LANGUAGE in TRANSLATIONS else "en"
        self.lang_code_map = {v.get("lang_name", k): k for k, v in TRANSLATIONS.items()}
        self.code_to_lang_name = {k: v.get("lang_name", k) for k, v in TRANSLATIONS.items()}

        self.discord_token = ""
        self.is_vip = False
        self.has_nitro = False
        self.saved_game_query = ""
        self.saved_custom_exe = ""
        self.backdrop_mode = 2  # По умолчанию Mica (2)
        self.last_source_key = "source_api"
        self.active_game_title = ""
        self.active_pids_str = ""
        self.current_selected_game = None
        self.github_changelog_text = None
        self._slide_job = None
        self._card_glow_job = None

        self.launch_all_var = tk.BooleanVar(value=True)
        self.auto_stop_var = tk.BooleanVar(value=True)
        self.notify_var = tk.BooleanVar(value=True)
        self.autostart_var = tk.BooleanVar(value=self._check_windows_autostart())

        self.discord_user = None
        self.discord_username_tag = ""
        self._pulse_state = False

        self._load_config()
        self._configure_ttk_styles()
        self._try_load_orbs_png_direct()

        self._build_login_screen()
        self._build_dashboard_ui()
        self._enable_universal_clipboard_bindings()
        self._setup_win11_backdrop()
        self._apply_vip_and_nitro_ui()

        self._show_login_screen(animate=False)

        threading.Thread(target=self._compile_helper_binaries, daemon=True).start()
        threading.Thread(target=self._fetch_games, daemon=True).start()
        threading.Thread(target=self._check_github_updates_and_changelog, args=(False,), daemon=True).start()

        self.custom_exe_var.trace_add("write", lambda *_: self._save_config())
        self.token_var.trace_add("write", lambda *_: self._save_config())
        self._animate_status_pulse()

        if self.discord_token:
            self.login_status_lbl.config(text=self.tr("login_checking"), fg=COLORS["accent"])
            threading.Thread(target=self._verify_token_and_login, args=(self.discord_token, False), daemon=True).start()

    def tr(self, key, **kwargs):
        lang_dict = TRANSLATIONS.get(self.lang) or TRANSLATIONS.get("en", {})
        text = lang_dict.get(key) or TRANSLATIONS.get("en", {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    # --- ПЛАВНЫЕ АНИМАЦИИ БЕЗ СБРОСА DWM И БЕЗ МЕЛЬКАНИЯ ТЕКСТА ---
    def _animate_frame_slide_in(self, target_frame, start_y=0.028, steps=10):
        """
        Плавный 60 FPS Ease-Out Cubic сдвиг экрана без использования root.attributes("-alpha").
        Полностью исключает конфликт с -transparentcolor и мелькание текста!
        """
        if self._slide_job:
            self.root.after_cancel(self._slide_job)

        def _step(s):
            t = s / float(steps)
            ease = 1.0 - math.pow(1.0 - t, 3)
            cur_y = start_y * (1.0 - ease)
            target_frame.place_configure(relx=0.0, rely=cur_y, relwidth=1.0, relheight=1.0)
            if s < steps:
                self._slide_job = self.root.after(12, _step, s + 1)
            else:
                target_frame.place_configure(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
                self._slide_job = None

        _step(1)

    def _animate_cards_surface_pulse(self, start_hex="#1B1B20", end_hex="#232327", steps=8):
        """Мягкий цветовой переход карточек при смене языка или фона DWM без перерисовки окна."""
        if self._card_glow_job:
            self.root.after_cancel(self._card_glow_job)
        s_rgb, e_rgb = hex_to_rgb(start_hex), hex_to_rgb(end_hex)

        def _step(s):
            t = s / float(steps)
            ease = 1.0 - math.pow(1.0 - t, 2)
            cur_hex = rgb_to_hex(tuple(s_rgb[i] + (e_rgb[i] - s_rgb[i]) * ease for i in range(3)))
            for card_frame in self.animated_cards_list:
                if card_frame.winfo_exists():
                    card_frame.config(bg=cur_hex)
            if s < steps:
                self._card_glow_job = self.root.after(14, _step, s + 1)
            else:
                self._card_glow_job = None

        _step(1)

    # --- РАСЧЁТ И ОТОБРАЖЕНИЕ НАГРАДЫ ---
    def _calculate_effective_orbs(self, base_orbs):
        base_val = int(base_orbs or 0)
        return int(round(base_val * 1.2)) if self.has_nitro else base_val

    def _update_top_reward_badge(self):
        rtype = self.current_reward_state.get("type", "none")
        qid = self.current_reward_state.get("quest_id", "")

        if rtype == "orbs" and self.current_reward_state.get("amount", 0) > 0:
            eff_orbs = self._calculate_effective_orbs(self.current_reward_state["amount"])
            self.orb_reward_val_lbl.config(text=self.tr("orb_reward_fmt", amount=eff_orbs), fg=COLORS["text_primary"])
            if self.has_nitro:
                self.orb_reward_title_lbl.config(text=self.tr("reward_header_nitro"), fg=COLORS["nitro_pink"])
                self.orb_badge_wrap.config(highlightbackground=COLORS["nitro_pink"])
            else:
                self.orb_reward_title_lbl.config(text=self.tr("reward_header_orbs"), fg=COLORS["orb_purple"])
                self.orb_badge_wrap.config(highlightbackground="#4E387E")
            self._draw_orb_icon_on_canvas(self.orb_canvas, 20, 20, 17, self.orbs_photo_36)

        elif rtype == "item":
            item_name = self.current_reward_state.get("name") or "In-Game Item"
            self.orb_reward_title_lbl.config(text=self.tr("reward_header_item"), fg=COLORS["item_gold"])
            self.orb_reward_val_lbl.config(text=item_name[:16], fg=COLORS["text_primary"])
            self.orb_badge_wrap.config(highlightbackground=COLORS["item_gold"])
            item_img_36 = self.quest_reward_icons_36.get(qid)
            if item_img_36:
                self.orb_canvas.delete("all")
                self.orb_canvas.create_image(20, 20, image=item_img_36)
            else:
                self._draw_item_box_icon_on_canvas(self.orb_canvas, 20, 20, 15)

        else:
            self.orb_reward_title_lbl.config(text=self.tr("reward_header_none"), fg=COLORS["text_secondary"])
            self.orb_reward_val_lbl.config(text=self.tr("reward_val_none"), fg=COLORS["text_secondary"])
            self.orb_badge_wrap.config(highlightbackground=COLORS["border_card"])
            self._draw_badge_icon_on_canvas(self.orb_canvas, 20, 20, 14)

    # --- ЗАГРУЗКА И ОТРИСОВКА ИКОНОК ORBS, ПРЕДМЕТОВ И ЗНАЧКОВ ---
    def _find_orbs_png_path(self):
        for candidate in ("orbs.png", "Orbs.png", os.path.join(WORK_DIR, "orbs.png")):
            full = candidate if os.path.isabs(candidate) else os.path.join(BASE_DIR, candidate)
            if os.path.exists(full):
                return full
        return None

    def _try_load_orbs_png_direct(self):
        orbs_path = self._find_orbs_png_path()
        if not orbs_path:
            return
        try:
            raw_img = tk.PhotoImage(file=orbs_path)
            w = raw_img.width()
            self.orbs_photo_56 = raw_img.subsample(max(1, round(w / 56)), max(1, round(w / 56)))
            self.orbs_photo_36 = raw_img.subsample(max(1, round(w / 36)), max(1, round(w / 36)))
            self.orbs_photo_22 = raw_img.subsample(max(1, round(w / 22)), max(1, round(w / 22)))
        except Exception:
            pass

    def _upgrade_orbs_icons_with_resizer(self):
        orbs_path = self._find_orbs_png_path()
        if not orbs_path or not self.img_proc_exe or not os.path.exists(self.img_proc_exe):
            return
        try:
            p56 = os.path.join(CACHE_UI_DIR, "orbs_56.png")
            p36 = os.path.join(CACHE_UI_DIR, "orbs_36.png")
            p22 = os.path.join(CACHE_UI_DIR, "orbs_22.png")
            for out_p, sz in [(p56, "56"), (p36, "36"), (p22, "22")]:
                if not os.path.exists(out_p):
                    subprocess.run(
                        [self.img_proc_exe, "icon", orbs_path, out_p, sz, sz],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            self.root.after(0, lambda: self._apply_smoothed_orbs_files(p56, p36, p22))
        except Exception:
            pass

    def _apply_smoothed_orbs_files(self, p56, p36, p22):
        try:
            if os.path.exists(p56):
                self.orbs_photo_56 = tk.PhotoImage(file=p56)
            if os.path.exists(p36):
                self.orbs_photo_36 = tk.PhotoImage(file=p36)
            if os.path.exists(p22):
                self.orbs_photo_22 = tk.PhotoImage(file=p22)
            if hasattr(self, "login_orb_canvas"):
                self._draw_orb_icon_on_canvas(self.login_orb_canvas, 32, 32, 26, self.orbs_photo_56)
            self._update_top_reward_badge()
            self._redraw_all_quest_canvases()
        except Exception:
            pass

    def _draw_orb_icon_on_canvas(self, canvas, cx, cy, r, photo_img=None):
        canvas.delete("all")
        if photo_img:
            canvas.create_image(cx, cy, image=photo_img)
            return

        pts_oct = [(cx + r * math.cos(math.radians(i * 45 - 90)), cy + r * math.sin(math.radians(i * 45 - 90))) for i in range(8)]
        facet_colors = ["#FFFFFF", "#76E6D4", "#6CE0D0", "#6E56F8", "#4752E8", "#E45CF2", "#E86AF5", "#CA8BFF"]
        for i in range(8):
            p1, p2 = pts_oct[i], pts_oct[(i + 1) % 8]
            canvas.create_polygon(cx, cy, p1[0], p1[1], p2[0], p2[1], fill=facet_colors[i], outline="")

        dr = r * 0.74
        canvas.create_polygon(cx, cy - dr, cx + dr, cy, cx, cy + dr, cx - dr, cy, fill="#050C42", outline="#1B237E", width=1)
        sr_out, sr_in = r * 0.38, r * 0.13
        canvas.create_polygon(
            cx, cy - sr_out, cx + sr_in, cy - sr_in, cx + sr_out, cy, cx + sr_in, cy + sr_in,
            cx, cy + sr_out, cx - sr_in, cy + sr_in, cx - sr_out, cy, cx - sr_in, cy - sr_in,
            fill="#FFFFFF", outline=""
        )

    @staticmethod
    def _draw_item_box_icon_on_canvas(canvas, cx, cy, r):
        canvas.delete("all")
        canvas.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill="#3A2B18", outline="#FFB74D", width=1.5)
        canvas.create_text(cx, cy, text="🎁", fill="#FFB74D", font=("Segoe UI", 12))

    @staticmethod
    def _draw_badge_icon_on_canvas(canvas, cx, cy, r):
        canvas.delete("all")
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#25262E", outline="#525462", width=1.5)
        canvas.create_text(cx, cy, text="🏅", fill="#9E9EA8", font=("Segoe UI", 11))

    # --- ПЕРЕКЛЮЧЕНИЕ МЕЖДУ ОКНОМ ВХОДА И ПРОГРАММОЙ ЧЕРЕЗ PLACE (БЕЗ РЫВКОВ И МИГАНИЯ) ---
    def _show_login_screen(self, animate=True):
        self.is_authenticated = False
        self.dashboard_frame.place_forget()
        if animate:
            self._animate_frame_slide_in(self.login_outer_frame, start_y=0.025, steps=9)
        else:
            self.login_outer_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)

    def _show_dashboard_screen(self, animate=True):
        self.is_authenticated = True
        self.login_outer_frame.place_forget()
        self._apply_vip_and_nitro_ui()
        if animate:
            self._animate_frame_slide_in(self.dashboard_frame, start_y=0.025, steps=10)
            self._animate_cards_surface_pulse("#19191E", COLORS["bg_card"], steps=8)
        else:
            self.dashboard_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)

    def _logout_discord(self):
        self.stop_emulation()
        self.discord_token = ""
        self.token_var.set("")
        self.discord_user = None
        self.has_nitro = False
        self.fetched_quests_cache = []
        self._save_config()
        self.login_status_lbl.config(text="", fg=COLORS["text_secondary"])
        self._show_login_screen(animate=True)

    def _toggle_vip_status(self):
        self.is_vip = not self.is_vip
        self._apply_vip_and_nitro_ui()
        self._save_config()

    def _apply_vip_and_nitro_ui(self):
        if self.is_vip:
            self.vip_badge_lbl.config(text=self.tr("tier_vip"), fg=COLORS["vip_gold"], bg=COLORS["vip_bg"])
            self.sync_quest_btn.config(text=self.tr("btn_auto_quest"))
            self.sync_quest_btn.set_palette(COLORS["accent"], COLORS["accent_hover"], COLORS["accent_text"])
            self.chk_auto_stop_widget.config(state=tk.NORMAL)
            self.chk_autostart_widget.config(state=tk.NORMAL)
        else:
            self.vip_badge_lbl.config(text=self.tr("tier_free"), fg=COLORS["text_secondary"], bg=COLORS["bg_input"])
            self.sync_quest_btn.config(text=self.tr("btn_auto_quest_locked"))
            self.sync_quest_btn.set_palette(COLORS["secondary_btn"], COLORS["secondary_hover"], COLORS["text_secondary"])
            self.auto_stop_var.set(False)
            self.chk_auto_stop_widget.config(state=tk.DISABLED)
            self.chk_autostart_widget.config(state=tk.DISABLED)

        if self.has_nitro:
            self.nitro_status_lbl.config(text=self.tr("nitro_detected"), fg=COLORS["nitro_pink"], bg=COLORS["nitro_bg"])
        else:
            self.nitro_status_lbl.config(text=self.tr("nitro_none"), fg=COLORS["text_secondary"], bg=COLORS["bg_input"])

        self._update_top_reward_badge()
        self._redraw_all_quest_canvases()

    def _check_windows_autostart(self):
        if sys.platform != "win32":
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_REG_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, AUTORUN_REG_NAME)
                return bool(val)
        except Exception:
            return False

    def _toggle_windows_autostart(self):
        if not self.is_vip:
            self.autostart_var.set(False)
            messagebox.showinfo(APP_TITLE, self.tr("vip_only_msg"))
            return
        enable = self.autostart_var.get()
        if sys.platform == "win32":
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    if enable:
                        py_exe = sys.executable
                        pyw_exe = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
                        runner = pyw_exe if os.path.exists(pyw_exe) else py_exe
                        script_path = os.path.abspath(__file__)
                        cmd_str = f'"{runner}" "{script_path}"' if not getattr(sys, "frozen", False) else f'"{sys.executable}"'
                        winreg.SetValueEx(key, AUTORUN_REG_NAME, 0, winreg.REG_SZ, cmd_str)
                    else:
                        try:
                            winreg.DeleteValue(key, AUTORUN_REG_NAME)
                        except FileNotFoundError:
                            pass
            except Exception:
                pass
        self._save_config()

    def _enable_universal_clipboard_bindings(self):
        def _on_ctrl_key(event):
            w = event.widget
            if not isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
                return
            if event.keycode == 86:
                self._paste_into_widget(w)
                return "break"
            elif event.keycode == 67:
                w.event_generate("<<Copy>>")
                return "break"
            elif event.keycode == 88:
                w.event_generate("<<Cut>>")
                return "break"
            elif event.keycode == 65:
                w.select_range(0, tk.END)
                w.icursor(tk.END)
                return "break"

        self.root.bind_all("<Control-KeyPress>", _on_ctrl_key)
        self.ctx_menu = tk.Menu(
            self.root, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            activebackground=COLORS["accent"], activeforeground=COLORS["accent_text"],
            font=("Segoe UI", 9), bd=1, relief=tk.FLAT
        )
        for w in (self.login_token_entry, self.search_entry, self.exe_combo):
            w.bind("<Button-3>", self._show_context_menu)

    @staticmethod
    def _clean_token(raw_str):
        if not raw_str:
            return ""
        t = raw_str.strip().strip('"').strip("'")
        if t.lower().startswith("bearer "):
            t = t[7:].strip()
        return re.sub(r"\s+", "", t)

    def _paste_into_widget(self, widget):
        try:
            clip = self.root.clipboard_get()
        except Exception:
            return
        if not clip:
            return
        try:
            if widget.selection_present():
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except Exception:
            pass
        val = self._clean_token(clip) if widget == self.login_token_entry else clip.strip()
        widget.insert(tk.INSERT, val)

    def _show_context_menu(self, event):
        w = event.widget
        w.focus_set()
        self.ctx_menu.delete(0, tk.END)
        self.ctx_menu.add_command(label=self.tr("ctx_paste"), command=lambda: self._paste_into_widget(w))
        self.ctx_menu.add_command(label=self.tr("ctx_copy"), command=lambda: w.event_generate("<<Copy>>"))
        self.ctx_menu.add_command(label=self.tr("ctx_cut"), command=lambda: w.event_generate("<<Cut>>"))
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label=self.tr("ctx_clear"), command=lambda: w.delete(0, tk.END))
        self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _setup_win11_backdrop(self):
        self.root.update_idletasks()
        try:
            self.hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            apply_win11_native_backdrop(self.hwnd, self.backdrop_mode)
        except Exception:
            pass

    def _on_change_backdrop_mode(self, mode_int):
        if self.backdrop_mode == mode_int:
            return
        self.backdrop_mode = mode_int
        if self.hwnd:
            apply_win11_native_backdrop(self.hwnd, self.backdrop_mode)
        self._update_header_selectors_ui(animate=True)
        self._animate_cards_surface_pulse("#1D1D22", COLORS["bg_card"], steps=7)
        self._save_config()

    def _clear_lang_combo_focus(self, event=None):
        for cb in (self.lang_combo, self.login_lang_combo):
            try:
                cb.selection_clear()
            except Exception:
                pass
        self.root.focus_set()

    def _on_language_combo_selected(self, event=None):
        if event and isinstance(event.widget, ttk.Combobox):
            selected_name = event.widget.get()
        else:
            selected_name = self.lang_combo_var.get()

        self.lang_combo_var.set(selected_name)
        self._clear_lang_combo_focus()
        self.root.after(10, self._clear_lang_combo_focus)

        new_code = self.lang_code_map.get(selected_name, "en")
        if new_code != self.lang:
            self.lang = new_code
            self._refresh_ui_texts()
            self._animate_cards_surface_pulse("#1B1B20", COLORS["bg_card"], steps=7)
            self._save_config()

    def _update_header_selectors_ui(self, animate=False):
        for m_val, btn in [(3, self.btn_acrylic), (2, self.btn_mica), (4, self.btn_mica_alt)]:
            if self.backdrop_mode == m_val:
                btn.set_palette(COLORS["accent"], COLORS["accent_hover"], COLORS["accent_text"], animate=animate)
            else:
                btn.set_palette(COLORS["bg_input"], COLORS["secondary_hover"], COLORS["text_secondary"], animate=animate)

    def _refresh_ui_texts(self):
        self.login_title_lbl.config(text=self.tr("login_title"))
        self.login_sub_lbl.config(text=self.tr("login_subtitle"))
        self.login_tok_lbl.config(text=self.tr("login_token_label"))
        self.login_signin_btn.config(text=self.tr("login_btn_signin"))
        self.login_grab_btn.config(text=self.tr("login_btn_grab"))

        if self.games_data:
            self.subtitle_label.config(text=self.tr("subtitle_synced", source=self.tr(self.last_source_key), count=len(self.games_data)))
        else:
            self.subtitle_label.config(text=self.tr("subtitle_loading"))

        if self.timer_running:
            self.badge_label.config(text=self.tr("status_active"))
            self.status_label.config(text=self.tr("proc_active_fmt", game=self.active_game_title, pids=self.active_pids_str))
        else:
            self.badge_label.config(text=self.tr("status_idle"))
            self.status_label.config(text=self.tr("proc_stopped"))

        self.dwm_label_widget.config(text=self.tr("dwm_label"))
        self.quest_info_label.config(text=self.tr("quest_hint_default"))
        self.lib_header_lbl.config(text=self.tr("lib_header"))
        self.cfg_header_lbl.config(text=self.tr("cfg_header"))
        self.chk_launch_all_widget.config(text=self.tr("chk_launch_all"))
        self.timer_header_lbl.config(text=self.tr("timer_header"))
        self.chk_auto_stop_widget.config(text=self.tr("chk_auto_stop"))
        self.chk_notify_widget.config(text=self.tr("chk_notify"))
        self.chk_autostart_widget.config(text=self.tr("chk_autostart"))
        self.start_btn.config(text=self.tr("btn_start"))
        self.stop_btn.config(text=self.tr("btn_stop"))
        self.platform_badge_lbl.config(text=self.tr("platform_auto"))

        self.profile_header_lbl.config(text=self.tr("profile_header"))
        self.logout_btn.config(text=self.tr("btn_logout"))
        self.switch_vip_btn.config(text=self.tr("btn_switch_vip"))
        self.quests_panel_header_lbl.config(text=self.tr("quests_panel_header"))
        self.changelog_header_lbl.config(text=self.tr("changelog_header"))
        self.check_upd_btn.config(text=self.tr("btn_check_updates"))

        self._render_changelog_text(self.github_changelog_text or self.tr("changelog_fallback"))
        self._apply_vip_and_nitro_ui()
        self._update_selected_game_visual_card(self.current_selected_game)
        self._render_quests_cards()

    def _render_changelog_text(self, text_content):
        if not hasattr(self, "changelog_box"):
            return
        self.changelog_box.config(state=tk.NORMAL)
        self.changelog_box.delete("1.0", tk.END)
        self.changelog_box.insert(tk.END, text_content)
        self.changelog_box.config(state=tk.DISABLED)

    def _trigger_windows_notification(self, game_name):
        if not self.notify_var.get():
            return
        if self.toast_exe and os.path.exists(self.toast_exe):
            try:
                subprocess.Popen(
                    [self.toast_exe, self.tr("toast_title"), self.tr("toast_body", game=game_name)],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                pass

    def _animate_status_pulse(self):
        if self.timer_running:
            self._pulse_state = not self._pulse_state
            self.badge_label.config(fg=COLORS["success"] if self._pulse_state else "#3A8E32")
        self.root.after(700, self._animate_status_pulse)

    def _configure_ttk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        self.root.option_add("*TCombobox*Listbox.background", COLORS["bg_card"])
        self.root.option_add("*TCombobox*Listbox.foreground", COLORS["text_primary"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLORS["bg_selected"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", COLORS["accent"])
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        style.configure(
            "Lang.TCombobox",
            fieldbackground=COLORS["bg_input"],
            background=COLORS["bg_input"],
            foreground=COLORS["text_primary"],
            selectbackground=COLORS["bg_input"],
            selectforeground=COLORS["text_primary"],
            arrowcolor=COLORS["text_secondary"],
            bordercolor=COLORS["bg_input"],
            lightcolor=COLORS["bg_input"],
            darkcolor=COLORS["bg_input"],
            focusfill=COLORS["bg_input"],
            borderwidth=0,
            padding=4,
        )
        style.map(
            "Lang.TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"]), ("focus", COLORS["bg_input"]), ("!focus", COLORS["bg_input"])],
            foreground=[("readonly", COLORS["text_primary"]), ("focus", COLORS["text_primary"])],
            selectbackground=[("readonly", COLORS["bg_input"]), ("focus", COLORS["bg_input"]), ("!focus", COLORS["bg_input"])],
            selectforeground=[("readonly", COLORS["text_primary"]), ("focus", COLORS["text_primary"]), ("!focus", COLORS["text_primary"])],
            bordercolor=[("focus", COLORS["bg_input"]), ("!focus", COLORS["bg_input"])],
            lightcolor=[("focus", COLORS["bg_input"]), ("!focus", COLORS["bg_input"])],
            darkcolor=[("focus", COLORS["bg_input"]), ("!focus", COLORS["bg_input"])],
            arrowcolor=[("active", COLORS["accent"])],
        )

        style.configure(
            "WinUI.TCombobox",
            fieldbackground=COLORS["bg_input"],
            background=COLORS["bg_input"],
            foreground=COLORS["text_primary"],
            selectbackground=COLORS["bg_input"],
            selectforeground=COLORS["text_primary"],
            arrowcolor=COLORS["text_secondary"],
            bordercolor=COLORS["border_card"],
            lightcolor=COLORS["bg_input"],
            darkcolor=COLORS["bg_input"],
            padding=4,
        )
        style.map(
            "WinUI.TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"]), ("focus", COLORS["bg_input"])],
            foreground=[("readonly", COLORS["text_primary"]), ("focus", COLORS["text_primary"])],
            selectbackground=[("readonly", COLORS["bg_input"]), ("focus", COLORS["bg_input"])],
            selectforeground=[("readonly", COLORS["text_primary"]), ("focus", COLORS["text_primary"])],
            bordercolor=[("focus", COLORS["accent"])],
            arrowcolor=[("active", COLORS["accent"])],
        )

        style.configure(
            "WinUI.Vertical.TScrollbar", gripcount=0, background=COLORS["border_card"],
            darkcolor=COLORS["bg_card"], lightcolor=COLORS["bg_card"], troughcolor=COLORS["bg_card"],
            bordercolor=COLORS["bg_card"], arrowcolor=COLORS["text_secondary"], width=9
        )
        style.configure(
            "WinUI.Horizontal.TProgressbar", troughcolor=COLORS["bg_input"], background=COLORS["accent"],
            bordercolor=COLORS["bg_input"], lightcolor=COLORS["accent"], darkcolor=COLORS["accent"], thickness=6
        )

    def _create_card(self, parent, expand=False, pady=(0, 8), bg_override=None, fixed_height=None):
        card_bg = bg_override or COLORS["bg_card"]
        outer = tk.Frame(parent, bg=COLORS["border_card"], padx=1, pady=1)
        if fixed_height:
            outer.config(height=fixed_height)
            outer.pack_propagate(False)
        outer.pack(fill=tk.BOTH if expand else tk.X, expand=expand, pady=pady)
        inner = tk.Frame(outer, bg=card_bg, padx=14, pady=9)
        if fixed_height:
            inner.pack_propagate(False)
        inner.pack(fill=tk.BOTH, expand=True)
        if not bg_override:
            self.animated_cards_list.append(inner)
        return inner

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                saved_lang = d.get("lang", "en")
                self.lang = saved_lang if saved_lang in TRANSLATIONS else "en"
                self.discord_token = self._clean_token(d.get("token", ""))
                self.backdrop_mode = int(d.get("backdrop_mode", 2))
                self.is_vip = bool(d.get("is_vip", False))
                self.launch_all_var.set(bool(d.get("launch_all", True)))
                self.auto_stop_var.set(bool(d.get("auto_stop", True)))
                self.notify_var.set(bool(d.get("notify", True)))
                self.saved_game_query = str(d.get("last_search", ""))
                self.saved_custom_exe = str(d.get("last_exe", ""))
            except Exception:
                pass

    def _save_config(self):
        try:
            tok = self._clean_token(self.token_var.get()) if hasattr(self, "token_var") else self.discord_token
            srch = self.search_var.get().strip() if hasattr(self, "search_var") else self.saved_game_query
            exe = self.custom_exe_var.get().strip() if hasattr(self, "custom_exe_var") else self.saved_custom_exe
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "lang": self.lang,
                    "token": tok,
                    "backdrop_mode": self.backdrop_mode,
                    "is_vip": self.is_vip,
                    "launch_all": self.launch_all_var.get(),
                    "auto_stop": self.auto_stop_var.get(),
                    "notify": self.notify_var.get(),
                    "autostart": self.autostart_var.get(),
                    "last_search": srch,
                    "last_exe": exe,
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ==================== АВТООБНОВЛЕНИЕ И ИСТОРИЯ ОБНОВЛЕНИЙ С GITHUB ====================
    def _check_github_updates_and_changelog(self, manual_trigger=False):
        releases_data = None
        commits_data = None

        try:
            cmd = [
                "curl.exe", "-s", "-L", "--max-time", "10",
                "-H", "Accept: application/vnd.github+json",
                "-H", "User-Agent: DiscordFarmix-Updater",
                GITHUB_RELEASES_API
            ]
            res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0 and res.stdout:
                parsed = json.loads(res.stdout.decode("utf-8", errors="ignore"))
                if isinstance(parsed, list) and len(parsed) > 0:
                    releases_data = parsed
        except Exception:
            pass

        if not releases_data:
            try:
                cmd_c = [
                    "curl.exe", "-s", "-L", "--max-time", "10",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "User-Agent: DiscordFarmix-Updater",
                    GITHUB_COMMITS_API
                ]
                res_c = subprocess.run(cmd_c, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res_c.returncode == 0 and res_c.stdout:
                    parsed_c = json.loads(res_c.stdout.decode("utf-8", errors="ignore"))
                    if isinstance(parsed_c, list) and len(parsed_c) > 0:
                        commits_data = parsed_c
            except Exception:
                pass

        if releases_data:
            lines = []
            for rel in releases_data[:12]:
                tag = rel.get("tag_name") or rel.get("name") or "Release"
                title = rel.get("name") or tag
                body = (rel.get("body") or "").strip()
                lines.append(f"• {title} ({tag}):")
                if body:
                    for b_line in body.splitlines():
                        lines.append(f"  {b_line}")
                lines.append("")
            self.github_changelog_text = "\n".join(lines).strip()
            self.root.after(0, lambda: self._render_changelog_text(self.github_changelog_text))

            latest_rel = releases_data[0]
            latest_tag = str(latest_rel.get("tag_name") or "")
            if parse_semver_tuple(latest_tag) > APP_VERSION_NUM:
                self.root.after(0, lambda r=latest_rel: self._show_update_modal(r))
            elif manual_trigger:
                self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, self.tr("update_up_to_date", ver=APP_VERSION)))

        elif commits_data:
            lines = [f"• GitHub Commits ({GITHUB_REPO}):"]
            for c in commits_data[:10]:
                sha = str(c.get("sha", ""))[:7]
                msg = (c.get("commit", {}).get("message") or "").splitlines()[0]
                date_str = (c.get("commit", {}).get("author", {}).get("date") or "")[:10]
                lines.append(f"  [{sha}] ({date_str}) {msg}")
            lines.append("\n" + self.tr("changelog_fallback"))
            self.github_changelog_text = "\n".join(lines)
            self.root.after(0, lambda: self._render_changelog_text(self.github_changelog_text))
            if manual_trigger:
                self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, self.tr("update_up_to_date", ver=APP_VERSION)))
        else:
            if manual_trigger:
                self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, self.tr("update_up_to_date", ver=APP_VERSION)))

    def _show_update_modal(self, release_info):
        tag = release_info.get("tag_name") or "New"
        notes = release_info.get("body") or "Bug fixes and improvements."

        modal = tk.Toplevel(self.root)
        modal.title(self.tr("update_modal_title"))
        modal.configure(bg=COLORS["bg_card"])
        modal.geometry("500x360")
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.grab_set()

        modal.update_idletasks()
        try:
            m_hwnd = ctypes.windll.user32.GetParent(modal.winfo_id()) or modal.winfo_id()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(m_hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(m_hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(m_hwnd, 35, ctypes.byref(ctypes.c_int(0x00242020)), 4)
        except Exception:
            pass

        wrap = tk.Frame(modal, bg=COLORS["bg_card"], padx=22, pady=18)
        wrap.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            wrap, text=self.tr("update_modal_header", ver=tag),
            font=("Segoe UI Variable Display", 13, "bold"), fg=COLORS["accent"], bg=COLORS["bg_card"], anchor=tk.W
        ).pack(fill=tk.X)

        tk.Label(
            wrap, text=self.tr("update_modal_sub", cur=APP_VERSION),
            font=("Segoe UI", 8), fg=COLORS["text_secondary"], bg=COLORS["bg_card"], anchor=tk.W
        ).pack(fill=tk.X, pady=(2, 10))

        notes_box = tk.Text(
            wrap, height=10, font=("Segoe UI", 9),
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            relief=tk.FLAT, bd=0, padx=10, pady=8, wrap=tk.WORD,
            highlightbackground=COLORS["border_card"], highlightthickness=1
        )
        notes_box.pack(fill=tk.BOTH, expand=True, pady=(0, 14))
        notes_box.insert(tk.END, notes)
        notes_box.config(state=tk.DISABLED)

        status_lbl = tk.Label(wrap, text="", font=("Segoe UI", 8), fg=COLORS["accent"], bg=COLORS["bg_card"])
        status_lbl.pack(fill=tk.X, pady=(0, 6))

        btn_row = tk.Frame(wrap, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X)

        def _do_update():
            status_lbl.config(text=self.tr("update_downloading"))
            threading.Thread(target=self._download_and_apply_github_update, args=(modal, status_lbl), daemon=True).start()

        AnimatedButton(
            btn_row, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            fg_color=COLORS["accent_text"], text=self.tr("btn_update_now"),
            font=("Segoe UI", 9, "bold"), pady=7, command=_do_update
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        AnimatedButton(
            btn_row, bg_color=COLORS["secondary_btn"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["text_primary"], text=self.tr("btn_update_later"),
            font=("Segoe UI", 9, "bold"), pady=7, command=modal.destroy
        ).pack(side=tk.LEFT, padx=(6, 0), ipadx=14)

    def _download_and_apply_github_update(self, modal, status_lbl):
        try:
            for fname in ("locales.py", os.path.basename(__file__)):
                url = f"{GITHUB_RAW_MAIN}/{fname}"
                tmp_path = os.path.join(BASE_DIR, f"{fname}.upd")
                target_path = os.path.join(BASE_DIR, fname)
                res = subprocess.run(
                    ["curl.exe", "-s", "-L", "--max-time", "15", "-o", tmp_path, url],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 500:
                    shutil.move(tmp_path, target_path)
                elif os.path.exists(tmp_path):
                    os.remove(tmp_path)

            self.root.after(0, lambda: (
                modal.destroy(),
                self.stop_emulation(),
                os.execl(sys.executable, sys.executable, *sys.argv)
            ))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: status_lbl.config(text=f"Update failed: {err}", fg=COLORS["danger"]))

    # ==================== 1. ПОСТРОЕНИЕ ОКНА ВХОДА DISCORD ====================
    def _build_login_screen(self):
        self.login_outer_frame = tk.Frame(self.root, bg=DWM_GLASS_KEY)

        center_box = tk.Frame(self.login_outer_frame, bg=COLORS["border_card"], padx=1, pady=1)
        center_box.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=480)

        card = tk.Frame(center_box, bg=COLORS["bg_card"], padx=28, pady=24)
        card.pack(fill=tk.BOTH, expand=True)

        top_bar = tk.Frame(card, bg=COLORS["bg_card"])
        top_bar.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            top_bar, text=f"v{APP_VERSION}", font=("Consolas", 8, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_input"], padx=7, pady=2
        ).pack(side=tk.LEFT)

        self.lang_combo_var = tk.StringVar(value=self.code_to_lang_name.get(self.lang, "English"))
        self.login_lang_combo = ttk.Combobox(
            top_bar, textvariable=self.lang_combo_var,
            values=list(self.lang_code_map.keys()), state="readonly", takefocus=0,
            style="Lang.TCombobox", font=("Segoe UI", 8, "bold"), width=11
        )
        self.login_lang_combo.pack(side=tk.RIGHT)
        self.login_lang_combo.bind("<<ComboboxSelected>>", self._on_language_combo_selected)
        self.login_lang_combo.bind("<FocusIn>", self._clear_lang_combo_focus)

        self.login_orb_canvas = tk.Canvas(card, width=64, height=64, bg=COLORS["bg_card"], highlightthickness=0)
        self.login_orb_canvas.pack(pady=(4, 10))
        self._draw_orb_icon_on_canvas(self.login_orb_canvas, 32, 32, 26, self.orbs_photo_56)

        self.login_title_lbl = tk.Label(
            card, text=self.tr("login_title"), font=("Segoe UI Variable Display", 16, "bold"),
            fg=COLORS["text_primary"], bg=COLORS["bg_card"]
        )
        self.login_title_lbl.pack()

        self.login_sub_lbl = tk.Label(
            card, text=self.tr("login_subtitle"), font=("Segoe UI", 9),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"], wraplength=410
        )
        self.login_sub_lbl.pack(pady=(4, 18))

        self.login_tok_lbl = tk.Label(
            card, text=self.tr("login_token_label"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.login_tok_lbl.pack(anchor=tk.W, pady=(0, 5))

        self.token_var = tk.StringVar(value=self.discord_token)
        self.login_token_entry = tk.Entry(
            card, textvariable=self.token_var, show="•", font=("Consolas", 10),
            bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["accent"],
            relief=tk.FLAT, highlightbackground=COLORS["border_card"], highlightcolor=COLORS["accent"], highlightthickness=1
        )
        self.login_token_entry.pack(fill=tk.X, ipady=6, pady=(0, 12))

        self.login_signin_btn = AnimatedButton(
            card, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            fg_color=COLORS["accent_text"], text=self.tr("login_btn_signin"),
            font=("Segoe UI", 10, "bold"), pady=8, command=self._on_manual_login_click
        )
        self.login_signin_btn.pack(fill=tk.X, pady=(0, 8))

        self.login_grab_btn = AnimatedButton(
            card, bg_color=COLORS["secondary_btn"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["text_primary"], text=self.tr("login_btn_grab"),
            font=("Segoe UI", 9, "bold"), pady=7, command=self.auto_extract_discord_token
        )
        self.login_grab_btn.pack(fill=tk.X)

        self.login_status_lbl = tk.Label(
            card, text="", font=("Segoe UI", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"], wraplength=410
        )
        self.login_status_lbl.pack(pady=(12, 0))

    def _on_manual_login_click(self):
        tok = self._clean_token(self.token_var.get())
        if not tok:
            self.login_status_lbl.config(text=self.tr("login_err_empty"), fg=COLORS["warning"])
            return
        self.login_status_lbl.config(text=self.tr("login_checking"), fg=COLORS["accent"])
        threading.Thread(target=self._verify_token_and_login, args=(tok, False), daemon=True).start()

    # ==================== 2. ПОСТРОЕНИЕ ОСНОВНОГО РАБОЧЕГО ОКНА ====================
    def _build_dashboard_ui(self):
        self.dashboard_frame = tk.Frame(self.root, bg=DWM_GLASS_KEY, padx=16, pady=10)

        # --- ШАПКА (КНОПКА ПРОВЕРКИ ОБНОВЛЕНИЙ ОКОЛО НАДПИСИ ВЕРСИИ) ---
        header_card = self._create_card(self.dashboard_frame, pady=(0, 8), fixed_height=62)
        title_col = tk.Frame(header_card, bg=COLORS["bg_card"])
        title_col.pack(side=tk.LEFT, fill=tk.Y)

        title_row = tk.Frame(title_col, bg=COLORS["bg_card"])
        title_row.pack(anchor=tk.W)

        tk.Label(
            title_row, text="Discord Farmix", font=("Segoe UI Variable Display", 15, "bold"),
            fg=COLORS["text_primary"], bg=COLORS["bg_card"]
        ).pack(side=tk.LEFT)

        tk.Label(
            title_row, text=f"v{APP_VERSION}", font=("Consolas", 8, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_input"], padx=7, pady=2
        ).pack(side=tk.LEFT, padx=(8, 0), pady=(2, 0))

        # Кнопка проверки обновления прямо рядом с надписью версии
        self.check_upd_btn = AnimatedButton(
            title_row, bg_color=COLORS["secondary_btn"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["text_primary"], text=self.tr("btn_check_updates"), font=("Segoe UI", 8, "bold"),
            padx=9, pady=2, command=lambda: threading.Thread(target=self._check_github_updates_and_changelog, args=(True,), daemon=True).start()
        )
        self.check_upd_btn.pack(side=tk.LEFT, padx=(8, 0), pady=(2, 0))

        self.subtitle_label = tk.Label(
            title_col, text=self.tr("subtitle_loading"), font=("Segoe UI", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.subtitle_label.pack(anchor=tk.W, pady=(1, 0))

        right_header = tk.Frame(header_card, bg=COLORS["bg_card"])
        right_header.pack(side=tk.RIGHT, fill=tk.Y)

        top_badges_row = tk.Frame(right_header, bg=COLORS["bg_card"])
        top_badges_row.pack(anchor=tk.E)

        tk.Label(top_badges_row, text="🌐", font=("Segoe UI", 9), fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side=tk.LEFT, padx=(0, 4))
        self.lang_combo = ttk.Combobox(
            top_badges_row, textvariable=self.lang_combo_var,
            values=list(self.lang_code_map.keys()), state="readonly", takefocus=0,
            style="Lang.TCombobox", font=("Segoe UI", 8, "bold"), width=11
        )
        self.lang_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_combo_selected)
        self.lang_combo.bind("<FocusIn>", self._clear_lang_combo_focus)

        self.badge_frame = tk.Frame(
            top_badges_row, bg=COLORS["bg_input"], highlightbackground=COLORS["border_card"],
            highlightthickness=1, padx=10, pady=2
        )
        self.badge_frame.pack(side=tk.LEFT)

        self.badge_label = tk.Label(
            self.badge_frame, text=self.tr("status_idle"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"]
        )
        self.badge_label.pack()

        blur_row = tk.Frame(right_header, bg=COLORS["bg_card"])
        blur_row.pack(anchor=tk.E, pady=(5, 0))

        self.dwm_label_widget = tk.Label(
            blur_row, text=self.tr("dwm_label"), font=("Segoe UI", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.dwm_label_widget.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_mica = AnimatedButton(
            blur_row, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            fg_color=COLORS["accent_text"], text="Mica", font=("Segoe UI", 8, "bold"),
            padx=7, pady=1, command=lambda: self._on_change_backdrop_mode(2)
        )
        self.btn_mica.pack(side=tk.LEFT, padx=1)

        self.btn_acrylic = AnimatedButton(
            blur_row, bg_color=COLORS["bg_input"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["text_secondary"], text="Acrylic", font=("Segoe UI", 8, "bold"),
            padx=7, pady=1, command=lambda: self._on_change_backdrop_mode(3)
        )
        self.btn_acrylic.pack(side=tk.LEFT, padx=1)

        self.btn_mica_alt = AnimatedButton(
            blur_row, bg_color=COLORS["bg_input"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["text_secondary"], text="Dark Glass", font=("Segoe UI", 8, "bold"),
            padx=7, pady=1, command=lambda: self._on_change_backdrop_mode(4)
        )
        self.btn_mica_alt.pack(side=tk.LEFT, padx=1)
        self._update_header_selectors_ui(animate=False)

        # --- ДВУХКОЛОНОЧНЫЙ КОНТЕЙНЕР С ЗАБЛОКИРОВАННОЙ ШИРИНОЙ КОЛОНОК (uniform="main_cols" + pack_propagate(False)) ---
        columns_wrap = tk.Frame(self.dashboard_frame, bg=DWM_GLASS_KEY)
        columns_wrap.pack(fill=tk.BOTH, expand=True)
        columns_wrap.grid_propagate(False)
        columns_wrap.columnconfigure(0, weight=1, uniform="main_cols")
        columns_wrap.columnconfigure(1, weight=1, uniform="main_cols")
        columns_wrap.rowconfigure(0, weight=1)

        left_col = tk.Frame(columns_wrap, bg=DWM_GLASS_KEY)
        left_col.pack_propagate(False)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        right_col = tk.Frame(columns_wrap, bg=DWM_GLASS_KEY)
        right_col.pack_propagate(False)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        # ==================== ЛЕВАЯ КОЛОНКА ====================
        # 1. ВИЗУАЛЬНАЯ КАРТОЧКА ИГРЫ (ФИКСИРОВАННАЯ ВЫСОТА И ЗАБЛОКИРОВАННАЯ ШИРИНА)
        visual_card = self._create_card(left_col, bg_override=COLORS["bg_card_highlight"], fixed_height=78)
        vcard_row = tk.Frame(visual_card, bg=COLORS["bg_card_highlight"])
        vcard_row.pack(fill=tk.BOTH, expand=True)

        self.game_icon_canvas = tk.Canvas(
            vcard_row, width=56, height=56, bg=COLORS["bg_input"],
            highlightbackground=COLORS["border_card"], highlightthickness=1, bd=0
        )
        self.game_icon_canvas.pack(side=tk.LEFT, padx=(0, 12))

        # Фиксированный размер блока награды справа, чтобы он никогда не менял ширину карточки
        self.orb_badge_wrap = tk.Frame(
            vcard_row, bg=COLORS["bg_input"], highlightbackground=COLORS["border_card"],
            highlightthickness=1, width=165, height=54, padx=8, pady=4
        )
        self.orb_badge_wrap.pack_propagate(False)
        self.orb_badge_wrap.pack(side=tk.RIGHT, padx=(10, 0))

        self.orb_canvas = tk.Canvas(self.orb_badge_wrap, width=40, height=40, bg=COLORS["bg_input"], highlightthickness=0)
        self.orb_canvas.pack(side=tk.LEFT, padx=(0, 6))

        orb_txt_col = tk.Frame(self.orb_badge_wrap, bg=COLORS["bg_input"])
        orb_txt_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.orb_reward_title_lbl = tk.Label(
            orb_txt_col, text=self.tr("reward_header_none"), font=("Segoe UI", 7, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"], anchor=tk.W
        )
        self.orb_reward_title_lbl.pack(anchor=tk.W)

        self.orb_reward_val_lbl = tk.Label(
            orb_txt_col, text=self.tr("reward_val_none"), font=("Segoe UI", 9, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"], anchor=tk.W
        )
        self.orb_reward_val_lbl.pack(anchor=tk.W)

        game_meta_col = tk.Frame(vcard_row, bg=COLORS["bg_card_highlight"])
        game_meta_col.pack_propagate(False)
        game_meta_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_plat_row = tk.Frame(game_meta_col, bg=COLORS["bg_card_highlight"])
        title_plat_row.pack(fill=tk.X, pady=(2, 0))

        self.vcard_title_lbl = tk.Label(
            title_plat_row, text=self.tr("card_game_none"), font=("Segoe UI Variable Display", 11, "bold"),
            fg=COLORS["text_primary"], bg=COLORS["bg_card_highlight"], anchor=tk.W
        )
        self.vcard_title_lbl.pack(side=tk.LEFT)

        self.platform_badge_lbl = tk.Label(
            title_plat_row, text=self.tr("platform_auto"), font=("Segoe UI", 7, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_input"], padx=6, pady=1
        )
        self.platform_badge_lbl.pack(side=tk.LEFT, padx=(8, 0))

        self.quest_info_label = tk.Label(
            game_meta_col, text=self.tr("card_game_sub"), font=("Segoe UI", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card_highlight"], anchor=tk.W, justify=tk.LEFT
        )
        self.quest_info_label.pack(fill=tk.X, pady=(4, 0))

        self._draw_default_game_icon()
        self._update_top_reward_badge()

        # 2. БИБЛИОТЕКА ИГР
        search_card = self._create_card(left_col, expand=True)
        lib_top = tk.Frame(search_card, bg=COLORS["bg_card"])
        lib_top.pack(fill=tk.X, pady=(0, 4))

        self.lib_header_lbl = tk.Label(
            lib_top, text=self.tr("lib_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.lib_header_lbl.pack(side=tk.LEFT)

        self.sync_quest_btn = AnimatedButton(
            lib_top, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            fg_color=COLORS["accent_text"], text=self.tr("btn_auto_quest"), font=("Segoe UI", 8, "bold"),
            padx=10, pady=2, command=self.sync_and_auto_start_quest
        )
        self.sync_quest_btn.pack(side=tk.RIGHT)

        search_box_wrap = tk.Frame(search_card, bg=COLORS["bg_input"])
        search_box_wrap.pack(fill=tk.X)
        search_inner = tk.Frame(search_box_wrap, bg=COLORS["bg_input"], padx=8, pady=4)
        search_inner.pack(fill=tk.X)

        tk.Label(search_inner, text="🔎", font=("Segoe UI", 9), fg=COLORS["text_secondary"], bg=COLORS["bg_input"]).pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar(value=self.saved_game_query)
        self.search_var.trace_add("write", lambda *_: (self._filter_list(), self._save_config()))
        self.search_entry = tk.Entry(
            search_inner, textvariable=self.search_var, font=("Segoe UI", 9),
            bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["accent"], relief=tk.FLAT, bd=0
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_underline = tk.Frame(search_box_wrap, bg=COLORS["border_card"], height=2)
        self.search_underline.pack(fill=tk.X, side=tk.BOTTOM)
        self.search_entry.bind("<FocusIn>", lambda _: self.search_underline.config(bg=COLORS["accent"]))
        self.search_entry.bind("<FocusOut>", lambda _: self.search_underline.config(bg=COLORS["border_card"]))

        list_wrap = tk.Frame(search_card, bg=COLORS["bg_input"], highlightbackground=COLORS["border_card"], highlightthickness=1)
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        scrollbar = ttk.Scrollbar(list_wrap, style="WinUI.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.games_listbox = tk.Listbox(
            list_wrap, yscrollcommand=scrollbar.set, font=("Segoe UI", 9),
            bg=COLORS["bg_input"], fg=COLORS["text_primary"], selectbackground=COLORS["bg_selected"],
            selectforeground=COLORS["accent"], activestyle="none", relief=tk.FLAT, bd=0, highlightthickness=0, height=5, cursor="hand2"
        )
        self.games_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=3)
        self.games_listbox.bind("<<ListboxSelect>>", self._on_select_game)
        scrollbar.config(command=self.games_listbox.yview)

        # 3. ПАРАМЕТРЫ .EXE (ФИКСИРОВАННАЯ ВЫСОТА)
        config_card = self._create_card(left_col, fixed_height=88)
        self.cfg_header_lbl = tk.Label(
            config_card, text=self.tr("cfg_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.cfg_header_lbl.pack(anchor=tk.W, pady=(0, 4))

        self.custom_exe_var = tk.StringVar(value=self.saved_custom_exe)
        self.exe_combo = ttk.Combobox(config_card, textvariable=self.custom_exe_var, style="WinUI.TCombobox", font=("Consolas", 9))
        self.exe_combo.pack(fill=tk.X, pady=(0, 4))

        self.chk_launch_all_widget = tk.Checkbutton(
            config_card, text=self.tr("chk_launch_all"), variable=self.launch_all_var, command=self._save_config,
            font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            activebackground=COLORS["bg_card"], activeforeground=COLORS["accent"], selectcolor=COLORS["bg_input"], bd=0, highlightthickness=0, cursor="hand2"
        )
        self.chk_launch_all_widget.pack(anchor=tk.W)

        # 4. ТАЙМЕР И НАСТРОЙКИ (ФИКСИРОВАННАЯ ВЫСОТА)
        timer_card = self._create_card(left_col, fixed_height=104)
        timer_top = tk.Frame(timer_card, bg=COLORS["bg_card"])
        timer_top.pack(fill=tk.X)

        left_info = tk.Frame(timer_top, bg=COLORS["bg_card"])
        left_info.pack(side=tk.LEFT)

        self.timer_header_lbl = tk.Label(
            left_info, text=self.tr("timer_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.timer_header_lbl.pack(anchor=tk.W)

        self.status_label = tk.Label(
            left_info, text=self.tr("proc_stopped"), font=("Segoe UI", 8),
            fg=COLORS["text_primary"], bg=COLORS["bg_card"]
        )
        self.status_label.pack(anchor=tk.W, pady=(1, 0))

        self.timer_label = tk.Label(
            timer_top, text="00:00:00", font=("Segoe UI Variable Display", 18, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_card"]
        )
        self.timer_label.pack(side=tk.RIGHT)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(timer_card, variable=self.progress_var, maximum=100, style="WinUI.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(6, 4))

        notify_row = tk.Frame(timer_card, bg=COLORS["bg_card"])
        notify_row.pack(fill=tk.X)

        self.chk_auto_stop_widget = tk.Checkbutton(
            notify_row, text=self.tr("chk_auto_stop"), variable=self.auto_stop_var, command=self._save_config,
            font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_primary"], disabledforeground="#5E5E66",
            activebackground=COLORS["bg_card"], activeforeground=COLORS["accent"], selectcolor=COLORS["bg_input"], bd=0, highlightthickness=0, cursor="hand2"
        )
        self.chk_auto_stop_widget.pack(side=tk.LEFT, padx=(0, 14))

        self.chk_notify_widget = tk.Checkbutton(
            notify_row, text=self.tr("chk_notify"), variable=self.notify_var, command=self._save_config,
            font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            activebackground=COLORS["bg_card"], activeforeground=COLORS["accent"], selectcolor=COLORS["bg_input"], bd=0, highlightthickness=0, cursor="hand2"
        )
        self.chk_notify_widget.pack(side=tk.LEFT, padx=(0, 14))

        self.chk_autostart_widget = tk.Checkbutton(
            notify_row, text=self.tr("chk_autostart"), variable=self.autostart_var, command=self._toggle_windows_autostart,
            font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_primary"], disabledforeground="#5E5E66",
            activebackground=COLORS["bg_card"], activeforeground=COLORS["accent"], selectcolor=COLORS["bg_input"], bd=0, highlightthickness=0, cursor="hand2"
        )
        self.chk_autostart_widget.pack(side=tk.LEFT)

        # 5. КНОПКИ ЗАПУСКА / ОСТАНОВКИ
        btn_frame = tk.Frame(left_col, bg=DWM_GLASS_KEY)
        btn_frame.pack(fill=tk.X, pady=(2, 0))

        self.start_btn = AnimatedButton(
            btn_frame, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            fg_color=COLORS["accent_text"], text=self.tr("btn_start"), font=("Segoe UI", 9, "bold"),
            pady=8, command=self.start_emulation
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.stop_btn = AnimatedButton(
            btn_frame, bg_color=COLORS["bg_card"], hover_color=COLORS["danger_hover"],
            fg_color=COLORS["text_secondary"], text=self.tr("btn_stop"), font=("Segoe UI", 9, "bold"),
            pady=8, state=tk.DISABLED, command=self.stop_emulation
        )
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # ==================== ПРАВАЯ КОЛОНКА ====================
        # 1. КАРТОЧКА ПРОФИЛЯ (ФИКСИРОВАННАЯ ВЫСОТА)
        profile_card = self._create_card(right_col, fixed_height=102)
        prof_top = tk.Frame(profile_card, bg=COLORS["bg_card"])
        prof_top.pack(fill=tk.X, pady=(0, 6))

        self.profile_header_lbl = tk.Label(
            prof_top, text=self.tr("profile_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.profile_header_lbl.pack(side=tk.LEFT)

        self.logout_btn = AnimatedButton(
            prof_top, bg_color=COLORS["danger_bg"], hover_color=COLORS["danger_hover"],
            fg_color=COLORS["danger"], text=self.tr("btn_logout"), font=("Segoe UI", 8, "bold"),
            padx=8, pady=1, command=self._logout_discord
        )
        self.logout_btn.pack(side=tk.RIGHT)

        profile_row = tk.Frame(profile_card, bg=COLORS["bg_card"])
        profile_row.pack(fill=tk.X)

        self.avatar_canvas = tk.Canvas(
            profile_row, width=54, height=54, bg=COLORS["bg_input"],
            highlightbackground=COLORS["border_card"], highlightthickness=1, bd=0
        )
        self.avatar_canvas.pack(side=tk.LEFT, padx=(0, 12))
        self._draw_default_avatar("?")

        user_info_col = tk.Frame(profile_row, bg=COLORS["bg_card"])
        user_info_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.profile_name_lbl = tk.Label(
            user_info_col, text="Discord User", font=("Segoe UI Variable Display", 12, "bold"),
            fg=COLORS["text_primary"], bg=COLORS["bg_card"], anchor=tk.W
        )
        self.profile_name_lbl.pack(fill=tk.X)

        self.profile_sub_lbl = tk.Label(
            user_info_col, text="", font=("Segoe UI", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"], anchor=tk.W
        )
        self.profile_sub_lbl.pack(fill=tk.X, pady=(1, 4))

        tier_row = tk.Frame(user_info_col, bg=COLORS["bg_card"])
        tier_row.pack(fill=tk.X)

        self.vip_badge_lbl = tk.Label(
            tier_row, text=self.tr("tier_free"), font=("Segoe UI", 7, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"], padx=7, pady=2
        )
        self.vip_badge_lbl.pack(side=tk.LEFT)

        self.switch_vip_btn = AnimatedButton(
            tier_row, bg_color=COLORS["secondary_btn"], hover_color=COLORS["secondary_hover"],
            fg_color=COLORS["accent"], text=self.tr("btn_switch_vip"), font=("Segoe UI", 7, "bold"),
            padx=7, pady=2, command=self._toggle_vip_status
        )
        self.switch_vip_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.nitro_status_lbl = tk.Label(
            tier_row, text=self.tr("nitro_none"), font=("Segoe UI", 7, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"], padx=8, pady=2
        )
        self.nitro_status_lbl.pack(side=tk.LEFT, padx=(6, 0))

        # 2. АДАПТИВНЫЕ КАРТОЧКИ ДОСТУПНЫХ ИГРОВЫХ КВЕСТОВ
        quests_card = self._create_card(right_col, expand=True)
        self.quests_panel_header_lbl = tk.Label(
            quests_card, text=self.tr("quests_panel_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self.quests_panel_header_lbl.pack(anchor=tk.W, pady=(0, 5))

        q_canvas_wrap = tk.Frame(quests_card, bg=COLORS["bg_input"], highlightbackground=COLORS["border_card"], highlightthickness=1)
        q_canvas_wrap.pack(fill=tk.BOTH, expand=True)

        self.q_scroll = ttk.Scrollbar(q_canvas_wrap, orient=tk.VERTICAL, style="WinUI.Vertical.TScrollbar")
        self.q_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.quests_cards_canvas = tk.Canvas(
            q_canvas_wrap, bg=COLORS["bg_input"], bd=0, highlightthickness=0,
            yscrollcommand=self.q_scroll.set, height=220
        )
        self.quests_cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.q_scroll.config(command=self.quests_cards_canvas.yview)

        self.quests_inner_frame = tk.Frame(self.quests_cards_canvas, bg=COLORS["bg_input"])
        self.quests_canvas_window = self.quests_cards_canvas.create_window((0, 0), window=self.quests_inner_frame, anchor="nw")

        self.quests_inner_frame.bind(
            "<Configure>",
            lambda _: self.quests_cards_canvas.configure(scrollregion=self.quests_cards_canvas.bbox("all"))
        )
        self.quests_cards_canvas.bind(
            "<Configure>",
            lambda e: self.quests_cards_canvas.itemconfig(self.quests_canvas_window, width=e.width)
        )
        self.quests_cards_canvas.bind(
            "<Enter>",
            lambda _: self.quests_cards_canvas.bind_all("<MouseWheel>", lambda ev: self.quests_cards_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"))
        )
        self.quests_cards_canvas.bind(
            "<Leave>",
            lambda _: self.quests_cards_canvas.unbind_all("<MouseWheel>")
        )
        self._render_quests_cards()

        # 3. ИСТОРИЯ ОБНОВЛЕНИЙ С GITHUB
        changelog_card = self._create_card(right_col, pady=(0, 0), fixed_height=150)
        cl_top = tk.Frame(changelog_card, bg=COLORS["bg_card"])
        cl_top.pack(fill=tk.X, pady=(0, 4))

        self.changelog_header_lbl = tk.Label(
            cl_top, text=self.tr("changelog_header"), font=("Segoe UI", 8, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_card"]
        )
        self.changelog_header_lbl.pack(side=tk.LEFT)

        cl_wrap = tk.Frame(changelog_card, bg=COLORS["bg_input"], highlightbackground=COLORS["border_card"], highlightthickness=1)
        cl_wrap.pack(fill=tk.BOTH, expand=True)

        cl_scroll = ttk.Scrollbar(cl_wrap, orient=tk.VERTICAL, style="WinUI.Vertical.TScrollbar")
        cl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.changelog_box = tk.Text(
            cl_wrap, height=6, font=("Segoe UI", 8),
            bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
            yscrollcommand=cl_scroll.set,
            relief=tk.FLAT, bd=0, padx=8, pady=6, wrap=tk.WORD, highlightthickness=0
        )
        self.changelog_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cl_scroll.config(command=self.changelog_box.yview)
        self._render_changelog_text(self.tr("changelog_fallback"))

    def _draw_default_avatar(self, initials="?"):
        self.avatar_canvas.delete("all")
        self.avatar_canvas.create_oval(6, 6, 48, 48, fill="#32323A", outline=COLORS["accent"], width=1.5)
        self.avatar_canvas.create_text(27, 27, text=initials[:2].upper(), fill=COLORS["accent"], font=("Segoe UI", 12, "bold"))

    def _draw_default_game_icon(self, title="🎮"):
        self.game_icon_canvas.delete("all")
        self.game_icon_canvas.create_rectangle(4, 4, 52, 52, fill="#25252C", outline=COLORS["accent"], width=1)
        symbol = title[:2].upper() if title and title != "🎮" else "🎮"
        self.game_icon_canvas.create_text(28, 28, text=symbol, fill=COLORS["accent"], font=("Segoe UI", 12, "bold"))

    def _load_discord_avatar_cached(self, user_id, avatar_hash, display_name):
        if not user_id or not avatar_hash:
            self.root.after(0, lambda: self._draw_default_avatar(display_name[:2]))
            return

        cache_file = os.path.join(CACHE_AVATARS_DIR, f"{user_id}_{avatar_hash}.png")
        if os.path.exists(cache_file):
            self.root.after(0, lambda: self._apply_avatar_from_file(cache_file, display_name))
            return

        def _worker():
            url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=64"
            cmd = ["curl.exe", "-s", "-L", "--max-time", "8", url]
            try:
                res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0 and res.stdout and res.stdout.startswith(b"\x89PNG"):
                    with open(cache_file, "wb") as f:
                        f.write(res.stdout)
                    self.root.after(0, lambda: self._apply_avatar_from_file(cache_file, display_name))
                    return
            except Exception:
                pass
            self.root.after(0, lambda: self._draw_default_avatar(display_name[:2]))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_avatar_from_file(self, filepath, fallback_name):
        try:
            self.avatar_photo = tk.PhotoImage(file=filepath)
            self.avatar_canvas.delete("all")
            self.avatar_canvas.create_image(27, 27, image=self.avatar_photo)
        except Exception:
            self._draw_default_avatar(fallback_name[:2])

    def _update_selected_game_visual_card(self, game_obj, quest_reward_override=None):
        self.current_selected_game = game_obj
        if not game_obj:
            self.current_reward_state = {"type": "none", "amount": 0, "name": "", "quest_id": ""}
            self.vcard_title_lbl.config(text=self.tr("card_game_none"))
            self._draw_default_game_icon("🎮")
            self._update_top_reward_badge()
            return

        g_name = game_obj.get("name", "Game")
        g_id = str(game_obj.get("id", ""))
        g_icon = str(game_obj.get("icon", ""))
        exe_preview = game_obj["exes"][0] if game_obj.get("exes") else ""
        if len(exe_preview) > 36:
            exe_preview = "..." + exe_preview[-33:]

        if quest_reward_override:
            self.current_reward_state = quest_reward_override
        else:
            matched_q = next(
                (q for q in self.fetched_quests_cache if (g_id and q.get("app_id") == g_id) or q["game_title"].lower() == g_name.lower()),
                None
            )
            if matched_q:
                self.current_reward_state = {
                    "type": matched_q["reward_type"],
                    "amount": matched_q["base_orbs"],
                    "name": matched_q["reward_name"],
                    "quest_id": matched_q["id"],
                }
            else:
                self.current_reward_state = {"type": "none", "amount": 0, "name": "", "quest_id": ""}

        self._update_top_reward_badge()
        self.vcard_title_lbl.config(text=g_name[:22])
        self.quest_info_label.config(text=f"ID: {g_id or 'Custom'} • {exe_preview}", fg=COLORS["accent"])

        if not g_id or not g_icon:
            self._draw_default_game_icon(g_name)
            return

        cache_icon_path = os.path.join(CACHE_ICONS_DIR, f"{g_id}_{g_icon}.png")
        if os.path.exists(cache_icon_path):
            self._apply_game_icon_from_file(cache_icon_path, g_name)
            return

        self._draw_default_game_icon(g_name)

        def _icon_worker():
            url = f"https://cdn.discordapp.com/app-icons/{g_id}/{g_icon}.png?size=64"
            cmd = ["curl.exe", "-s", "-L", "--max-time", "8", url]
            try:
                res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0 and res.stdout and res.stdout.startswith(b"\x89PNG"):
                    with open(cache_icon_path, "wb") as f:
                        f.write(res.stdout)
                    self.root.after(0, lambda: self._apply_game_icon_from_file(cache_icon_path, g_name))
            except Exception:
                pass

        threading.Thread(target=_icon_worker, daemon=True).start()

    def _apply_game_icon_from_file(self, filepath, fallback_title):
        try:
            self.game_icon_photo = tk.PhotoImage(file=filepath)
            self.game_icon_canvas.delete("all")
            self.game_icon_canvas.create_image(28, 28, image=self.game_icon_photo)
        except Exception:
            self._draw_default_game_icon(fallback_title)

    # --- ЗАПРОСЫ К DISCORD API ---
    def _http_request(self, url, token=None, timeout=15):
        super_props = base64.b64encode(json.dumps({
            "os": "Windows", "browser": "Discord Client", "release_channel": "stable",
            "client_version": "1.0.9175", "os_version": "10.0.22631", "os_arch": "x64", "system_locale": "en-US",
        }).encode("utf-8")).decode("utf-8")

        cmd = [
            "curl.exe", "-s", "-L", "--compressed", "--max-time", str(timeout),
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.2 Safari/537.36",
            "-H", "Accept: application/json",
            "-H", "Origin: https://discord.com",
            "-H", f"X-Super-Properties: {super_props}",
        ]
        if token:
            cmd.extend(["-H", f"Authorization: {self._clean_token(token)}"])
        cmd.append(url)

        res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if res.returncode == 0 and res.stdout:
            text = res.stdout.decode("utf-8", errors="replace").strip()
            if text.startswith("{") or text.startswith("["):
                data = json.loads(text)
                if isinstance(data, dict) and data.get("code") == 0 and "401" in str(data.get("message", "")):
                    raise RuntimeError("401: Unauthorized")
                return data
            raise RuntimeError(f"HTTP Error: {text[:80]}")
        raise RuntimeError(f"curl error ({res.returncode})")

    def auto_extract_discord_token(self):
        self.login_status_lbl.config(text=self.tr("quest_extracting"), fg=COLORS["accent"])
        threading.Thread(target=self._extract_token_worker, daemon=True).start()

    def _extract_token_worker(self):
        appdata = os.getenv("APPDATA", "")
        clients = ["discord", "discordptb", "discordcanary"]
        candidate_tokens = []

        for client in clients:
            client_dir = os.path.join(appdata, client)
            local_state = os.path.join(client_dir, "Local State")
            leveldb_dir = os.path.join(client_dir, "Local Storage", "leveldb")
            if not os.path.exists(local_state) or not os.path.exists(leveldb_dir):
                continue

            try:
                with open(local_state, "r", encoding="utf-8") as f:
                    enc_key_b64 = json.load(f).get("os_crypt", {}).get("encrypted_key", "")
            except Exception:
                enc_key_b64 = ""

            db_files = sorted(
                glob.glob(os.path.join(leveldb_dir, "*.ldb")) + glob.glob(os.path.join(leveldb_dir, "*.log")),
                key=os.path.getmtime, reverse=True
            )

            enc_blobs = []
            for db_file in db_files:
                try:
                    with open(db_file, "rb") as f:
                        content = f.read().decode("utf-8", errors="ignore")
                    for m in re.findall(r'dQw4w9WgXcQ:([A-Za-z0-9+/=]+)', content):
                        if m not in enc_blobs:
                            enc_blobs.append(m)
                except Exception:
                    pass

            if enc_key_b64 and enc_blobs and self.decryptor_exe and os.path.exists(self.decryptor_exe):
                try:
                    proc = subprocess.run(
                        [self.decryptor_exe, enc_key_b64] + enc_blobs[:15],
                        capture_output=True, timeout=6, creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    for line in proc.stdout.decode("utf-8", errors="ignore").splitlines():
                        tok = self._clean_token(line)
                        if len(tok) > 45 and "." in tok and tok not in candidate_tokens:
                            candidate_tokens.append(tok)
                except Exception:
                    pass

        for tok in candidate_tokens:
            try:
                user_data = self._http_request(f"{DISCORD_API_BASE}/users/@me", token=tok, timeout=7)
                if isinstance(user_data, dict) and "id" in user_data:
                    self.root.after(0, lambda valid_t=tok, u=user_data: self._on_valid_token_found(valid_t, u))
                    return
            except Exception:
                continue

        self.root.after(0, lambda: self.login_status_lbl.config(text=self.tr("quest_token_manual"), fg=COLORS["warning"]))

    def _update_profile_ui(self, user_data):
        uid = str(user_data.get("id", ""))
        avatar_hash = user_data.get("avatar", "")
        display_name = user_data.get("global_name") or user_data.get("username") or "User"
        uname = user_data.get("username", "")

        premium_type = int(user_data.get("premium_type") or 0)
        self.has_nitro = (premium_type > 0)

        self.discord_user = display_name
        self.discord_username_tag = f"@{uname}" if uname else "Discord Active"

        self.profile_name_lbl.config(text=display_name, fg=COLORS["text_primary"])
        self.profile_sub_lbl.config(text=f"{self.discord_username_tag} • ID: {uid}", fg=COLORS["accent"])
        self._apply_vip_and_nitro_ui()
        self._load_discord_avatar_cached(uid, avatar_hash, display_name)

    def _on_valid_token_found(self, token, user_data):
        self.token_var.set(token)
        self.discord_token = token
        self._update_profile_ui(user_data)
        self._save_config()
        self._show_dashboard_screen(animate=True)
        threading.Thread(target=self._fetch_quests_only, args=(token, False), daemon=True).start()

    def sync_and_auto_start_quest(self):
        if not self.is_vip:
            messagebox.showinfo(APP_TITLE, self.tr("vip_only_msg"))
            return
        token = self._clean_token(self.token_var.get())
        if not token:
            self._show_login_screen(animate=True)
            return
        self.quest_info_label.config(text=self.tr("quest_fetching"), fg=COLORS["accent"])
        threading.Thread(target=self._fetch_quests_only, args=(token, True), daemon=True).start()

    def _verify_token_and_login(self, token, auto_start=False):
        token = self._clean_token(token)
        try:
            user_data = self._http_request(f"{DISCORD_API_BASE}/users/@me", token=token)
            if "id" not in user_data:
                raise RuntimeError("401: Unauthorized")
            self.root.after(0, lambda u=user_data: self._on_valid_token_found(token, u))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: (
                self._show_login_screen(animate=False),
                self.login_status_lbl.config(text=f"{self.tr('auth_error')}: {err}", fg=COLORS["danger"]),
            ))

    def _fetch_quests_only(self, token, auto_start=False):
        try:
            quests_resp = self._http_request(f"{DISCORD_API_BASE}/quests/@me", token=token)
            quests_list = quests_resp.get("quests", []) if isinstance(quests_resp, dict) else quests_resp
            self.root.after(0, lambda: self._process_fetched_quests(quests_list, auto_start))
        except Exception:
            self.root.after(0, lambda: self.quest_info_label.config(
                text=self.tr("quest_connected_pick", user=self.discord_user), fg=COLORS["success"]
            ))

    # --- ОПРЕДЕЛЕНИЕ ТИПА НАГРАДЫ КВЕСТА ---
    @staticmethod
    def _extract_quest_reward_details(cfg):
        rewards_cfg = cfg.get("rewards_config") or {}
        rewards_list = rewards_cfg.get("rewards") or cfg.get("rewards") or []
        assets = cfg.get("assets") or {}
        messages = cfg.get("messages") or {}

        for r in rewards_list:
            if not isinstance(r, dict):
                continue
            r_type = r.get("type")
            r_msg = r.get("messages") or {}
            r_name = str(r_msg.get("name") or r_msg.get("name_with_article") or messages.get("reward_name") or "").strip()
            r_asset = str(r.get("asset") or assets.get("reward") or "").strip()

            for k in ("orb_quantity", "orbs", "quantity", "amount"):
                val = r.get(k)
                if isinstance(val, int) and val > 0 and (r_type == 4 or "orb" in r_name.lower() or "орб" in r_name.lower() or k == "orb_quantity"):
                    return {"type": "orbs", "amount": val, "name": f"+{val} Orbs", "asset": ""}

            m_orb = re.search(r"(\d{2,5})\s*(?:Discord\s*)?(?:Orbs|орб)", r_name, re.IGNORECASE)
            if m_orb:
                amt = int(m_orb.group(1))
                return {"type": "orbs", "amount": amt, "name": f"+{amt} Orbs", "asset": ""}

            if r_name or r_asset:
                clean_item_name = r_name if r_name else "In-Game Item"
                return {"type": "item", "amount": 0, "name": clean_item_name, "asset": r_asset}

        fallback_name = str(messages.get("reward_name") or messages.get("quest_name") or "").strip()
        m_fb = re.search(r"(\d{2,5})\s*(?:Discord\s*)?(?:Orbs|орб)", fallback_name, re.IGNORECASE)
        if m_fb:
            amt = int(m_fb.group(1))
            return {"type": "orbs", "amount": amt, "name": f"+{amt} Orbs", "asset": ""}

        return {"type": "item", "amount": 0, "name": fallback_name or "Quest Item", "asset": str(assets.get("game_tile") or "")}

    def _process_fetched_quests(self, quests_list, auto_start):
        valid_quests = []
        now_utc = datetime.now(timezone.utc).timestamp()

        for q in quests_list:
            cfg = q.get("config", {})
            user_status = q.get("user_status") or {}

            if user_status.get("completed_at"):
                continue

            expires_str = cfg.get("expires_at")
            if expires_str:
                try:
                    exp_ts = datetime.fromisoformat(expires_str.replace("Z", "+00:00")).timestamp()
                    if exp_ts <= now_utc:
                        continue
                except Exception:
                    pass

            task_cfg = cfg.get("task_config_v2") or cfg.get("task_config") or {}
            tasks_dict = task_cfg.get("tasks") or {}

            selected_task_type = None
            target_seconds = 900
            if tasks_dict:
                for t_type in PLAY_TASK_TYPES:
                    if t_type in tasks_dict:
                        selected_task_type = t_type
                        target_seconds = int(tasks_dict[t_type].get("target", 900))
                        break
                if not selected_task_type:
                    continue
            else:
                selected_task_type = "PLAY_ON_DESKTOP"

            messages = cfg.get("messages", {})
            assets = cfg.get("assets", {})
            hero_candidates = [assets.get("quest_bar_hero"), assets.get("hero"), assets.get("game_tile")]
            hero_asset = ""
            for cand in hero_candidates:
                if cand and not str(cand).endswith(".mp4") and not str(cand).startswith("mp4:"):
                    hero_asset = str(cand)
                    break

            app_id = str(cfg.get("application", {}).get("id", ""))
            reward_info = self._extract_quest_reward_details(cfg)

            valid_quests.append({
                "id": str(q.get("id", "")),
                "game_title": messages.get("game_title") or messages.get("quest_name") or "Quest Game",
                "quest_name": messages.get("quest_name") or "Play on Desktop",
                "app_id": app_id,
                "enrolled": bool(user_status.get("enrolled_at")),
                "task_type": selected_task_type,
                "target_seconds": target_seconds,
                "platform": "PC (Windows)",
                "hero_asset": hero_asset,
                "reward_type": reward_info["type"],
                "base_orbs": reward_info["amount"],
                "reward_name": reward_info["name"],
                "reward_asset": reward_info["asset"],
            })

        valid_quests.sort(key=lambda x: (not x["enrolled"]))
        self.fetched_quests_cache = valid_quests
        self._render_quests_cards()

        if not valid_quests:
            self.quest_info_label.config(text=self.tr("quest_none_active", user=self.discord_user), fg=COLORS["warning"])
            return

        if self.is_vip and auto_start:
            self._apply_quest_selection(valid_quests[0], auto_start=True)

    # --- ОТРИСОВКА КАРТОЧЕК КВЕСТОВ ---
    def _render_quests_cards(self):
        if not hasattr(self, "quests_inner_frame"):
            return
        self.quest_card_canvases.clear()
        for child in self.quests_inner_frame.winfo_children():
            child.destroy()

        if not self.fetched_quests_cache:
            empty_lbl = tk.Label(
                self.quests_inner_frame, text=self.tr("quests_empty"),
                font=("Segoe UI", 9), fg=COLORS["text_secondary"], bg=COLORS["bg_input"], pady=30
            )
            empty_lbl.pack(fill=tk.X)
            return

        card_h = 84
        for q in self.fetched_quests_cache:
            q_id = q["id"]
            holder = tk.Frame(
                self.quests_inner_frame, bg=COLORS["border_card"], padx=1, pady=1, cursor="hand2"
            )
            holder.pack(fill=tk.X, expand=True, padx=4, pady=4)

            cv = tk.Canvas(
                holder, height=card_h, bg="#22232B", bd=0, highlightthickness=0, cursor="hand2"
            )
            cv.pack(fill=tk.X, expand=True)
            self.quest_card_canvases.append((cv, q))

            cv.bind("<Configure>", lambda e, c=cv, quest_obj=q: self._draw_single_quest_card_canvas(c, quest_obj, e.width, card_h))
            cv.bind("<Button-1>", lambda e, quest_obj=q: self._on_click_quest_card(quest_obj))
            cv.bind("<Enter>", lambda e, h=holder: h.config(bg=COLORS["accent"]))
            cv.bind("<Leave>", lambda e, h=holder: h.config(bg=COLORS["border_card"]))

            if q_id not in self.quest_card_banners:
                self._load_quest_banner_async(q, 520, card_h)
            if q["reward_type"] == "item" and q_id not in self.quest_reward_icons_24:
                self._load_quest_reward_item_icon_async(q)

    def _redraw_all_quest_canvases(self):
        for cv, q in self.quest_card_canvases:
            if cv.winfo_exists():
                w = max(360, cv.winfo_width())
                self._draw_single_quest_card_canvas(cv, q, w, 84)

    def _draw_single_quest_card_canvas(self, cv, q, w, h):
        if w < 100:
            w = 480
        cv.delete("all")
        q_id = q["id"]
        banner_img = self.quest_card_banners.get(q_id)
        if banner_img:
            cv.create_image(0, 0, image=banner_img, anchor="nw")
        else:
            cv.create_rectangle(0, 0, w, h, fill="#20222B", outline="")
            cv.create_polygon(w - 170, 0, w, 0, w, h, w - 230, h, fill="#292C3A", outline="")

        badge_w = 152
        bx1 = w - badge_w - 12
        bx2 = w - 12
        by1 = 15
        by2 = h - 15
        mid_y = h // 2

        tag_text = self.tr("tag_enrolled") if q["enrolled"] else self.tr("tag_available")
        tag_color = COLORS["success"] if q["enrolled"] else COLORS["accent"]
        mins = max(1, round(q.get("target_seconds", 900) / 60))

        cv.create_text(
            14, 18,
            text=f"● {tag_text.upper()}  •  🖥 {q['platform']}  •  ⏱ {mins}m",
            fill=tag_color, font=("Segoe UI", 8, "bold"), anchor="w"
        )
        cv.create_text(
            14, 43,
            text=q["game_title"][:26],
            fill="#FFFFFF", font=("Segoe UI Variable Display", 11, "bold"), anchor="w"
        )
        sub_q = q.get("quest_name") or "Play on Desktop"
        cv.create_text(
            14, 65,
            text=sub_q[:36],
            fill="#C8C8D2", font=("Segoe UI", 8), anchor="w"
        )

        rtype = q.get("reward_type", "orbs")
        icon_cx = bx1 + 22
        text_x = bx1 + 42

        if rtype == "orbs" and q.get("base_orbs", 0) > 0:
            eff_orbs = self._calculate_effective_orbs(q["base_orbs"])
            cv.create_rectangle(
                bx1, by1, bx2, by2,
                fill="#2B1932" if self.has_nitro else "#1D1A2B",
                outline=COLORS["nitro_pink"] if self.has_nitro else "#5B428F",
                width=1
            )
            if self.orbs_photo_22:
                cv.create_image(icon_cx, mid_y, image=self.orbs_photo_22)
            else:
                cv.create_oval(icon_cx - 9, mid_y - 9, icon_cx + 9, mid_y + 9, fill="#7C4DFF", outline="#FFFFFF")

            if self.has_nitro:
                cv.create_text(text_x, mid_y - 7, text=f"+{eff_orbs} Orbs", fill="#FFFFFF", font=("Segoe UI", 9, "bold"), anchor="w")
                cv.create_text(text_x, mid_y + 8, text="💎 1.2x NITRO", fill=COLORS["nitro_pink"], font=("Segoe UI", 7, "bold"), anchor="w")
            else:
                cv.create_text(text_x, mid_y, text=f"+{eff_orbs} Orbs", fill="#FFFFFF", font=("Segoe UI", 9, "bold"), anchor="w")
        else:
            cv.create_rectangle(
                bx1, by1, bx2, by2,
                fill=COLORS["item_bg"], outline=COLORS["item_gold"], width=1
            )
            item_img = self.quest_reward_icons_24.get(q_id)
            if item_img:
                cv.create_image(icon_cx, mid_y, image=item_img)
            else:
                cv.create_rectangle(icon_cx - 10, mid_y - 10, icon_cx + 10, mid_y + 10, fill="#3A2B18", outline=COLORS["item_gold"])
                cv.create_text(icon_cx, mid_y, text="🎁", fill=COLORS["item_gold"], font=("Segoe UI", 9))

            r_title = (q.get("reward_name") or "In-Game Item").strip()
            cv.create_text(text_x, mid_y - 7, text=r_title[:13], fill="#FFFFFF", font=("Segoe UI", 8, "bold"), anchor="w")
            cv.create_text(text_x, mid_y + 8, text="🎁 ITEM", fill=COLORS["item_gold"], font=("Segoe UI", 7, "bold"), anchor="w")

    def _load_quest_reward_item_icon_async(self, q):
        q_id = q["id"]
        r_asset = q.get("reward_asset", "").lstrip("/")
        if not q_id or not r_asset:
            return

        out_24 = os.path.join(CACHE_REWARDS_DIR, f"item24_{q_id}.png")
        out_36 = os.path.join(CACHE_REWARDS_DIR, f"item36_{q_id}.png")
        if os.path.exists(out_24) and os.path.exists(out_36):
            self._apply_reward_item_files(q_id, out_24, out_36)
            return

        def _worker():
            for _ in range(25):
                if self.img_proc_exe and os.path.exists(self.img_proc_exe):
                    break
                time.sleep(0.2)
            if not self.img_proc_exe or not os.path.exists(self.img_proc_exe):
                return

            raw_tmp = os.path.join(CACHE_REWARDS_DIR, f"raw_item_{q_id}.tmp")
            urls = [
                f"https://cdn.discordapp.com/quests/{q_id}/{r_asset}?format=png",
                f"https://cdn.discordapp.com/quests/{q_id}/{r_asset}.png",
                f"https://cdn.discordapp.com/quests/{q_id}/{r_asset}.jpg",
                f"https://cdn.discordapp.com/{r_asset}?format=png",
            ]
            for u in urls:
                subprocess.run(["curl.exe", "-s", "-L", "--max-time", "8", "-o", raw_tmp, u], creationflags=subprocess.CREATE_NO_WINDOW)
                if os.path.exists(raw_tmp) and os.path.getsize(raw_tmp) > 300:
                    subprocess.run([self.img_proc_exe, "icon", raw_tmp, out_24, "24", "24"], creationflags=subprocess.CREATE_NO_WINDOW)
                    subprocess.run([self.img_proc_exe, "icon", raw_tmp, out_36, "36", "36"], creationflags=subprocess.CREATE_NO_WINDOW)
                    if os.path.exists(out_24):
                        break

            if os.path.exists(raw_tmp):
                try:
                    os.remove(raw_tmp)
                except Exception:
                    pass
            if os.path.exists(out_24):
                self.root.after(0, lambda: self._apply_reward_item_files(q_id, out_24, out_36))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_reward_item_files(self, q_id, p24, p36):
        try:
            if os.path.exists(p24):
                self.quest_reward_icons_24[q_id] = tk.PhotoImage(file=p24)
            if os.path.exists(p36):
                self.quest_reward_icons_36[q_id] = tk.PhotoImage(file=p36)
            self._redraw_all_quest_canvases()
            if self.current_reward_state.get("quest_id") == q_id:
                self._update_top_reward_badge()
        except Exception:
            pass

    def _load_quest_banner_async(self, q, target_w, target_h):
        q_id = q["id"]
        asset = q.get("hero_asset", "")
        app_id = q.get("app_id", "")

        out_png = os.path.join(CACHE_BANNERS_DIR, f"banner_v15_{q_id}.png")
        if os.path.exists(out_png):
            self._apply_quest_banner_file(q, out_png)
            return

        def _worker():
            for _ in range(25):
                if self.img_proc_exe and os.path.exists(self.img_proc_exe):
                    break
                time.sleep(0.2)
            if not self.img_proc_exe or not os.path.exists(self.img_proc_exe):
                return

            raw_path = os.path.join(CACHE_BANNERS_DIR, f"raw_{q_id}.tmp")
            if asset:
                clean_asset = asset.lstrip("/")
                for u in (
                    f"https://cdn.discordapp.com/quests/{q_id}/{clean_asset}?format=png",
                    f"https://cdn.discordapp.com/quests/{q_id}/{clean_asset}.jpg",
                    f"https://cdn.discordapp.com/quests/{q_id}/{clean_asset}.png",
                    f"https://cdn.discordapp.com/{clean_asset}?format=png",
                ):
                    subprocess.run(["curl.exe", "-s", "-L", "--max-time", "8", "-o", raw_path, u], creationflags=subprocess.CREATE_NO_WINDOW)
                    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 800:
                        subprocess.run(
                            [self.img_proc_exe, "banner", raw_path, out_png, str(target_w), str(target_h)],
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if os.path.exists(out_png):
                            break

            if not os.path.exists(out_png):
                matched = next(
                    (g for g in self.games_data if (app_id and str(g.get("id")) == app_id) or q["game_title"].lower() in g["name"].lower()),
                    None
                )
                if matched and matched.get("id") and matched.get("icon"):
                    gid, gicon = matched["id"], matched["icon"]
                    icon_url = f"https://cdn.discordapp.com/app-icons/{gid}/{gicon}.png?size=256"
                    subprocess.run(["curl.exe", "-s", "-L", "--max-time", "8", "-o", raw_path, icon_url], creationflags=subprocess.CREATE_NO_WINDOW)
                    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 400:
                        subprocess.run(
                            [self.img_proc_exe, "iconbanner", raw_path, out_png, str(target_w), str(target_h)],
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )

            if os.path.exists(raw_path):
                try:
                    os.remove(raw_path)
                except Exception:
                    pass
            if os.path.exists(out_png):
                self.root.after(0, lambda: self._apply_quest_banner_file(q, out_png))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_quest_banner_file(self, q, png_path):
        try:
            img = tk.PhotoImage(file=png_path)
            self.quest_card_banners[q["id"]] = img
            self._redraw_all_quest_canvases()
        except Exception:
            pass

    def _on_click_quest_card(self, q):
        if not self.is_vip:
            messagebox.showinfo(APP_TITLE, self.tr("vip_only_msg"))
            return
        self._apply_quest_selection(q, auto_start=False)

    def _apply_quest_selection(self, tq, auto_start=False):
        self.current_quest_target_sec = max(60, int(tq.get("target_seconds", 900))) + 10
        reward_override = {
            "type": tq["reward_type"],
            "amount": tq["base_orbs"],
            "name": tq["reward_name"],
            "quest_id": tq["id"],
        }

        plat_str = tq.get("platform", "PC (Windows)")
        self.platform_badge_lbl.config(text=f"🖥 {plat_str}")

        matched = next(
            (g for g in self.games_data if (tq["app_id"] and str(g.get("id")) == tq["app_id"]) or tq["game_title"].lower() in g["name"].lower()),
            None
        )
        if matched:
            self.search_var.set(matched["name"])
            self._filter_list()
            if self.filtered_games:
                self.games_listbox.selection_clear(0, tk.END)
                self.games_listbox.selection_set(0)
                game = self.filtered_games[0]
                self.exe_combo["values"] = game["exes"]
                self.custom_exe_var.set(game["exes"][0])
                self._update_selected_game_visual_card(game, quest_reward_override=reward_override)
            exe_short = matched["exes"][0]
            if len(exe_short) > 32:
                exe_short = "..." + exe_short[-29:]
            self.quest_info_label.config(
                text=self.tr("quest_found_matched", title=tq["game_title"][:20], platform=plat_str, exe=exe_short),
                fg=COLORS["success"]
            )
            if auto_start and self.is_vip:
                self.start_emulation()
        else:
            self.search_var.set(tq["game_title"])
            self.current_reward_state = reward_override
            self._update_top_reward_badge()
            self.quest_info_label.config(
                text=self.tr("quest_found_manual", title=tq["game_title"][:20], appid=tq["app_id"], platform=plat_str),
                fg=COLORS["accent"]
            )

    # --- КОМПИЛЯЦИЯ ВСПОМОГАТЕЛЬНЫХ УТИЛИТ (.NET) ---
    def _compile_helper_binaries(self):
        os.makedirs(WORK_DIR, exist_ok=True)
        self.base_dummy_exe = os.path.join(WORK_DIR, "base_dummy_invisible_v15.exe")
        self.decryptor_exe = os.path.join(WORK_DIR, "token_decryptor_v15.exe")
        self.toast_exe = os.path.join(WORK_DIR, "toast_sender_v15.exe")
        self.img_proc_exe = os.path.join(WORK_DIR, "img_proc_v15.exe")

        csc_paths = [
            r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
            r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
        ]
        csc_exe = next((p for p in csc_paths if os.path.exists(p)), None)
        if not csc_exe:
            return

        for exe_path, cs_code, target_type, refs in [
            (self.base_dummy_exe, DUMMY_CS_CODE, "winexe", ["/r:System.Windows.Forms.dll", "/r:System.Drawing.dll"]),
            (self.decryptor_exe, TOKEN_DECRYPTOR_CS, "exe", ["/r:System.Security.dll"]),
            (self.toast_exe, TOAST_CS_CODE, "winexe", ["/r:System.Windows.Forms.dll", "/r:System.Drawing.dll"]),
            (self.img_proc_exe, IMAGE_PROC_CS_CODE, "exe", ["/r:System.Drawing.dll"]),
        ]:
            if not os.path.exists(exe_path):
                cs_file = exe_path + ".cs"
                with open(cs_file, "w", encoding="utf-8") as f:
                    f.write(cs_code)
                subprocess.run(
                    [csc_exe, f"/target:{target_type}", "/nologo", f"/out:{exe_path}"] + refs + [cs_file],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if os.path.exists(cs_file):
                    os.remove(cs_file)

        self._upgrade_orbs_icons_with_resizer()

    def _parse_raw_json(self, raw_data):
        parsed = []
        for app in raw_data:
            name = app.get("name")
            app_id = str(app.get("id", ""))
            icon_hash = str(app.get("icon") or "")
            exes = app.get("executables", [])
            win_exes = [
                e["name"].lstrip("/\\") for e in exes
                if e.get("os") == "win32" and e.get("name") and not e["name"].startswith(">") and not e.get("is_launcher", False)
            ] or [
                e["name"].lstrip("/\\") for e in exes
                if e.get("os") == "win32" and e.get("name") and not e["name"].startswith(">")
            ]
            if name and win_exes:
                parsed.append({"name": name, "id": app_id, "icon": icon_hash, "exes": win_exes})
        return sorted(parsed, key=lambda x: x["name"].lower())

    def _fetch_games(self):
        if os.path.exists(LOCAL_JSON_PATH):
            try:
                with open(LOCAL_JSON_PATH, "r", encoding="utf-8") as f:
                    self.games_data = self._parse_raw_json(json.load(f))
                self.root.after(0, lambda: self._on_games_loaded("source_local"))
                return
            except Exception:
                pass

        try:
            raw_data = self._http_request(DISCORD_DETECTABLE_URL, timeout=25)
            with open(LOCAL_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(raw_data, f)
            self.games_data = self._parse_raw_json(raw_data)
            self.root.after(0, lambda: self._on_games_loaded("source_api"))
        except Exception:
            self.root.after(0, lambda: self._on_games_loaded("source_local"))

    def _on_games_loaded(self, source_key):
        self.last_source_key = source_key
        self.subtitle_label.config(text=self.tr("subtitle_synced", source=self.tr(source_key), count=len(self.games_data)))
        self._filter_list()

    def _filter_list(self):
        q = self.search_var.get().lower().strip()
        self.games_listbox.delete(0, tk.END)
        self.filtered_games = [
            g for g in self.games_data
            if q in g["name"].lower() or any(q in ex.lower() for ex in g["exes"])
        ][:300]
        for g in self.filtered_games:
            self.games_listbox.insert(tk.END, f"  🎮  {g['name']}   —   {', '.join(g['exes'][:2])}")

    def _on_select_game(self, event):
        sel = self.games_listbox.curselection()
        if sel:
            game = self.filtered_games[sel[0]]
            self.exe_combo["values"] = game["exes"]
            self.custom_exe_var.set(game["exes"][0])
            self.platform_badge_lbl.config(text=self.tr("platform_auto"))
            self._update_selected_game_visual_card(game, quest_reward_override=None)
            self._save_config()

    def start_emulation(self):
        sel = self.games_listbox.curselection()
        selected_game = self.filtered_games[sel[0]] if sel else self.current_selected_game
        exe_input = self.custom_exe_var.get().strip().lstrip("/\\")

        if not exe_input and not selected_game:
            messagebox.showwarning(APP_TITLE, self.tr("warn_select_game"))
            return

        self.stop_emulation()
        self._save_config()

        if selected_game and self.launch_all_var.get() and exe_input in selected_game["exes"]:
            exes_to_launch, game_title = selected_game["exes"][:4], selected_game["name"]
        else:
            if not exe_input.lower().endswith(".exe"):
                exe_input += ".exe"
            exes_to_launch = [exe_input]
            game_title = selected_game["name"] if selected_game else os.path.basename(exe_input)

        base_run_dir = os.path.join(WORK_DIR, "running")
        launched_pids = []

        for rel_exe in exes_to_launch:
            target_exe_path = os.path.join(base_run_dir, os.path.normpath(rel_exe))
            try:
                os.makedirs(os.path.dirname(target_exe_path), exist_ok=True)
                shutil.copyfile(self.base_dummy_exe, target_exe_path)
                proc = subprocess.Popen([target_exe_path, game_title], cwd=os.path.dirname(target_exe_path))
                self.active_processes.append(proc)
                launched_pids.append(str(proc.pid))
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Failed to launch {target_exe_path}:\n{e}")

        if not self.active_processes:
            return

        self.active_game_title, self.active_pids_str = game_title[:24], ", ".join(launched_pids)
        self.quest_notified = False
        self.badge_label.config(text=self.tr("status_active"), fg=COLORS["success"])
        self.status_label.config(text=self.tr("proc_active_fmt", game=self.active_game_title, pids=self.active_pids_str), fg=COLORS["text_primary"])
        self.start_btn.config(state=tk.DISABLED, cursor="arrow")
        self.start_btn.set_palette(COLORS["bg_card"], COLORS["bg_card"], COLORS["text_secondary"])
        self.stop_btn.config(state=tk.NORMAL, cursor="hand2")
        self.stop_btn.set_palette(COLORS["danger_bg"], COLORS["danger_hover"], COLORS["danger"])

        self.start_time = time.time()
        self.timer_running = True
        self._update_timer()

    def stop_emulation(self, completed_automatically=False):
        self.timer_running = False
        for proc in self.active_processes:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass
        self.active_processes.clear()

        if completed_automatically:
            self.badge_label.config(text=self.tr("status_done"), fg=COLORS["accent"])
            self.status_label.config(text=self.tr("proc_auto_stopped"), fg=COLORS["success"])
            self._smooth_progress_to(100.0)
        else:
            self.badge_label.config(text=self.tr("status_idle"), fg=COLORS["text_secondary"])
            self.status_label.config(text=self.tr("proc_emulation_stopped"), fg=COLORS["text_secondary"])
            self._smooth_progress_to(0.0)

        self.start_btn.config(state=tk.NORMAL, cursor="hand2")
        self.start_btn.set_palette(COLORS["accent"], COLORS["accent_hover"], COLORS["accent_text"])
        self.stop_btn.config(state=tk.DISABLED, cursor="arrow")
        self.stop_btn.set_palette(COLORS["bg_card"], COLORS["bg_card"], COLORS["text_secondary"])

    def _smooth_progress_to(self, target_val):
        current = self.progress_var.get()
        diff = target_val - current
        if abs(diff) > 0.2:
            self.progress_var.set(current + diff * 0.25)
            self.root.after(20, self._smooth_progress_to, target_val)
        else:
            self.progress_var.set(target_val)

    def _update_timer(self):
        if self.timer_running and self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_int = int(elapsed)
            hrs, rem = divmod(elapsed_int, 3600)
            mins, secs = divmod(rem, 60)
            self.timer_label.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
            target_sec = self.current_quest_target_sec or QUEST_TARGET_SECONDS
            self._smooth_progress_to(min(100.0, (elapsed / target_sec) * 100.0))

            if elapsed_int >= target_sec and not self.quest_notified:
                self.quest_notified = True
                self._trigger_windows_notification(self.active_game_title)
                if self.is_vip and self.auto_stop_var.get():
                    self.stop_emulation(completed_automatically=True)
                    return
                self.badge_label.config(text=self.tr("status_done_15"), fg=COLORS["accent"])

            self.root.after(250, self._update_timer)

    def on_close(self):
        self._save_config()
        self.stop_emulation()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DiscordFarmixApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()