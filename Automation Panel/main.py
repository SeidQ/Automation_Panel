"""
Azercell Automation Panel v5.0
main.py — App shell: top-bar, tabs, footer, poll loop.

Theme & language switching is done IN-PLACE — no destroy/rebuild.
All translatable strings are held in ctk.StringVar so they update instantly.
"""
import os
import queue
import threading
from datetime import datetime

import customtkinter as ctk

import config as cfg
from config import C, T, STRINGS, update_C
from tab_planning    import TabPlanning
from tab_activation  import TabActivation
from tab_msisdn      import TabMSISDN


# ══════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Azercell Automation Panel")
        self.geometry("1380x880")
        self.minsize(1100, 720)
        self.configure(fg_color=("#120A1E", "#F3F0F8"))

        # Shared queues & events (survive tab rebuilds)
        self._log_q   = queue.Queue()
        self._res_q   = queue.Queue()
        self._stop_ev = threading.Event()
        # _is_dark=True means the app is visually in DARK mode.
        # NOTE: All color tuples in this codebase are written as
        #       (dark_color, light_color), which is the REVERSE of what
        #       customtkinter expects (light_color, dark_color).
        # Therefore, to show the dark palette we must set CTk to "Light"
        # appearance mode, and vice-versa.
        self._is_dark = True

        # Tab instances (set during _build)
        self._tab_plan  = None
        self._tab_act   = None
        self._tab_ms    = None
        self._hist_win  = None

        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            ico_path = os.path.join(BASE_DIR, "Logo", "azercell.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

        self._build()
        self._poll()
        self.after(100, self._fix_titlebar)

    # ══════════════════════════════════════════════════
    #  BUILD — called once at startup
    # ══════════════════════════════════════════════════
    def _build(self):
        update_C()  # C dict-i build başlamazdan əvvəl sync et
        self.configure(fg_color=("#120A1E", "#F3F0F8"))

        outer = ctk.CTkFrame(self, fg_color=("#120A1E", "#F3F0F8"))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── Top bar ───────────────────────────────────
        # Bar is always dark purple regardless of theme — logo/nav area stays branded
        bar = ctk.CTkFrame(outer, fg_color="#1C1030", corner_radius=0, height=62)
        bar.grid(row=0, column=0, sticky="ew")
        bar.pack_propagate(False)

        # Logo / title
        tf = ctk.CTkFrame(bar, fg_color="#1C1030")
        tf.pack(side="left", padx=4)
        self._logo_img = None
        try:
            from PIL import Image
            img = Image.open("Logo/azercell_logo.png").resize((200, 200), Image.LANCZOS)
            self._logo_img = ctk.CTkImage(
                light_image=img, dark_image=img, size=(200, 200))
        except Exception:
            pass

        if self._logo_img:
            ctk.CTkLabel(tf, image=self._logo_img, text="").pack(
                side="left", padx=(0, 14))
            ctk.CTkLabel(tf, text="Automation Panel",
                         font=("Segoe UI", 19, "bold"),
                         text_color="#EDE8F5").pack(side="left")
        else:
            badge = ctk.CTkFrame(tf, fg_color=("#5C2483", "#5C2483"),
                                 width=36, height=36, corner_radius=8)
            badge.pack(side="left", padx=(0, 10))
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text="A",
                         font=("Segoe UI", 16, "bold"),
                         text_color="white").place(relx=.5, rely=.5, anchor="center")
            ctk.CTkLabel(tf, text="Automation Panel",
                         font=("Segoe UI", 19, "bold"),
                         text_color="#EDE8F5").pack(side="left")

        # Right controls
        rb = ctk.CTkFrame(bar, fg_color="transparent")
        rb.pack(side="right", padx=12)

        # When _is_dark=True  → button offers to switch to Light  → show T("light_mode")
        # When _is_dark=False → button offers to switch to Dark   → show T("dark_mode")
        self._theme_btn = ctk.CTkButton(
            rb,
            text=T("light_mode") if self._is_dark else T("dark_mode"),
            width=90, height=30, font=("Segoe UI", 11),
            fg_color="#251540", hover_color="#3D2260",
            text_color="#EDE8F5", corner_radius=8,
            command=self._toggle_theme)
        self._theme_btn.pack(side="right", padx=6)

        self._lang_var = ctk.StringVar(value=cfg.CURRENT_LANG.upper())
        ctk.CTkOptionMenu(
            rb, values=["EN", "AZ", "RU"],
            variable=self._lang_var, width=70, height=30,
            font=("Segoe UI", 11), fg_color="#251540",
            button_color="#5C2483", button_hover_color="#7C6EB0",
            dropdown_fg_color="#1C1030", text_color="#EDE8F5",
            dropdown_text_color="#EDE8F5",
            dropdown_hover_color="#3D2260",
            command=self._on_lang_change
        ).pack(side="right", padx=6)

        self._hist_btn = ctk.CTkButton(
            rb, text="📋 History",
            width=90, height=30, font=("Segoe UI", 11),
            fg_color="#251540", hover_color="#3D2260",
            text_color="#8B75B0", corner_radius=8,
            state="disabled", command=self._open_history)
        self._hist_btn.pack(side="right", padx=6)

        # ── Tabs ──────────────────────────────────────
        content = ctk.CTkFrame(outer, fg_color=("#120A1E", "#F3F0F8"))
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(10, 0))
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self._tabview = ctk.CTkTabview(
            content,
            fg_color=("#120A1E", "#F3F0F8"),
            segmented_button_fg_color="#1C1030",
            segmented_button_selected_color="#5C2483",
            segmented_button_selected_hover_color="#5C2483",
            segmented_button_unselected_color="#1C1030",
            segmented_button_unselected_hover_color="#3D2260",
            text_color="#EDE8F5",
            text_color_disabled=C["muted"],
            anchor="center",
        )
        self._tabview.grid(row=0, column=0, sticky="nsew")
        for key in ("tab_planning", "tab_activation", "tab_msisdn"):
            self._tabview.add(T(key))
        self._tabview._segmented_button.configure(
            font=("Segoe UI", 13, "bold"), height=42)
        self._tabview.configure(command=self._on_tab_change)

        # Instantiate tab controllers
        self._tab_plan = TabPlanning(
            self._tabview.tab(T("tab_planning")),
            self._log_q, T)
        self._tab_act = TabActivation(
            self._tabview.tab(T("tab_activation")),
            self._log_q, self._res_q, self._stop_ev, T)
        self._tab_ms = TabMSISDN(
            self._tabview.tab(T("tab_msisdn")), T)
        self.after(100, self._on_tab_change)

        # ── Footer ────────────────────────────────────
        footer = ctk.CTkFrame(outer, fg_color="#1C1030",
                              corner_radius=0, height=28)
        footer.grid(row=2, column=0, sticky="ew")
        footer.pack_propagate(False)
        ctk.CTkLabel(footer,
                     text=f"✦  {T('designed_by')}  ✦",
                     font=("Segoe UI", 10),
                     text_color=("#8B75B0", "#6B5A8A")
                     ).place(relx=.5, rely=.5, anchor="center")
        ctk.CTkLabel(footer, text="v5.0",
                     font=("Consolas", 9),
                     text_color=("#3D2260", "#C4B0DC")
                     ).pack(side="right", padx=14)

    # ══════════════════════════════════════════════════
    #  TAB CHANGE — enable/disable history button
    # ══════════════════════════════════════════════════
    def _on_tab_change(self):
        try:
            is_act = (self._tabview.get() == T("tab_activation"))
            self._hist_btn.configure(
                state="normal"       if is_act else "disabled",
                text_color="#EDE8F5" if is_act else "#8B75B0",
                fg_color="#3D2260"   if is_act else "#251540")
        except Exception:
            pass

    def _open_history(self):
        if self._hist_win and self._hist_win.winfo_exists():
            self._hist_win.lift()
            self._hist_win.focus_force()
            if self._tab_act:
                self._tab_act._hist_refresh()
            return

        win = ctk.CTkToplevel(self)
        win.title("📋  Activation History")
        win.configure(fg_color=("#120A1E", "#F3F0F8"))
        win.transient(self)
        win.lift()
        win.focus_force()
        try:
            import os as _os
            _ico = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo", "azercell.ico")
            if _os.path.exists(_ico):
                win.iconbitmap(_ico)
        except Exception:
            pass
        try:
            from ctypes import windll, byref, sizeof, c_int
            win.update_idletasks()
            hwnd = windll.user32.GetParent(win.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x1E0A12)), sizeof(c_int))
        except Exception:
            pass
        win.minsize(820, 500)
        self.update_idletasks()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        pw, ph = self.winfo_width(), self.winfo_height()
        ww, wh = 860, 580
        win.geometry(f"{ww}x{wh}+{px+(pw-ww)//2}+{py+(ph-wh)//2}")
        win.rowconfigure(0, weight=1)
        win.columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(win, fg_color=("#120A1E", "#F3F0F8"))
        inner.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        inner.rowconfigure(0, weight=0)
        inner.rowconfigure(1, weight=0)
        inner.rowconfigure(2, weight=0)
        inner.rowconfigure(3, weight=1)
        inner.columnconfigure(0, weight=1)

        if self._tab_act:
            self._tab_act.build_history_tab(inner)

        self._hist_win = win
        win.protocol("WM_DELETE_WINDOW",
                     lambda: setattr(self, "_hist_win", None) or win.destroy())

    # ══════════════════════════════════════════════════
    #  POLL LOOP  (120 ms → 80 ms for snappier log)
    # ══════════════════════════════════════════════════
    def _poll(self):
        # Drain log queue
        try:
            while True:
                item = self._log_q.get_nowait()
                if item.get("_tab") == "np":
                    if self._tab_plan:
                        self._tab_plan.append_log(
                            item["ts"], item["msg"], item["level"])
                else:
                    if self._tab_act:
                        self._tab_act.append_log(
                            item["ts"], item["msg"],
                            item["level"], item.get("msisdn"),
                            step=item.get("step", 0),
                            done=item.get("done", False),
                            error=item.get("error", False))
        except queue.Empty:
            pass

        # Drain result queue
        try:
            while True:
                r = self._res_q.get_nowait()
                if self._tab_act:
                    self._tab_act.collect_result(r)
        except queue.Empty:
            pass

        self.after(80, self._poll)
    # ══════════════════════════════════════════════════
    #  STATUS BAR
    # ══════════════════════════════════════════════════
    def _set_status(self, text, color, bg):
        pass

    # ══════════════════════════════════════════════════
    #  TITLE BAR COLOR  (Windows 11 / Win10 build 22000+)
    # ══════════════════════════════════════════════════
    def _fix_titlebar(self):
        self._apply_titlebar_color()

    def _apply_titlebar_color(self):
        try:
            from ctypes import windll, byref, sizeof, c_int
            # #1F011F sabit — hər iki themada eyni
            color = c_int(0x1E0A12)
            hwnd = windll.user32.GetParent(self.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, byref(color), sizeof(color))
        except Exception:
            pass

    # ══════════════════════════════════════════════════
    #  SMOOTH THEME TOGGLE
    #
    #  Color tuples in this project are (dark_color, light_color),
    #  i.e. the REVERSE of CTk convention (light_color, dark_color).
    #  So to display our DARK palette we must tell CTk to use "Light"
    #  appearance mode, and vice-versa.
    #
    #  _is_dark=True  → our dark look  → CTk "Light"
    #  _is_dark=False → our light look → CTk "Dark"
    # ══════════════════════════════════════════════════
    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        ctk_mode = "Light" if self._is_dark else "Dark"
        ctk.set_appearance_mode(ctk_mode)
        update_C()
        self._theme_btn.configure(
            text=T("light_mode") if self._is_dark else T("dark_mode"))
        if self._tab_ms:
            self._tab_ms.rebuild()
        self.after(50, self._apply_titlebar_color)

    # ══════════════════════════════════════════════════
    #  SMOOTH LANGUAGE SWITCH
    #  Only text strings are updated — no widget rebuild.
    # ══════════════════════════════════════════════════
    def _on_lang_change(self, choice):
        # Remember active tab before rebuild
        active_key = None
        tab_keys   = ["tab_planning", "tab_activation", "tab_msisdn"]
        try:
            active_name = self._tabview.get()
            old_strings = STRINGS.get(cfg.CURRENT_LANG, STRINGS["en"])
            for key in tab_keys:
                if old_strings.get(key) == active_name:
                    active_key = key
                    break
        except Exception:
            pass

        # Cache data
        cached_ms   = self._tab_ms.get_cached_data() if self._tab_ms else None
        act_data    = list(self._tab_act._test_data) if self._tab_act else None
        act_results = list(self._tab_act._results)  if self._tab_act else None
        act_history = list(self._tab_act._history)  if self._tab_act else None

        cfg.CURRENT_LANG = choice.lower()

        for w in self.winfo_children():
            w.destroy()

        self._build()

        if act_data    is not None: self._tab_act._test_data = act_data
        if act_results is not None: self._tab_act._results   = act_results
        if act_history is not None: self._tab_act._history   = act_history
        self._tab_act._render_data()

        if cached_ms:
            self._tab_ms.restore(cached_ms)

        self._lang_var.set(choice)

        # Restore active tab
        if active_key:
            try:
                self._tabview.set(T(active_key))
            except Exception:
                pass


# ══════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    # Fix multi-monitor DPI / transparency glitches on Windows (esp. mixed scaling).
    try:
        ctk.deactivate_automatic_dpi_awareness()
    except Exception:
        pass
    try:
        ctk.set_window_scaling(1.0)
        ctk.set_widget_scaling(1.0)
    except Exception:
        pass

    # Our color tuples are written as (dark_color, light_color),
    # which is inverted vs CTk's (light_color, dark_color) convention.
    # So to START in our dark visual theme we tell CTk to use "Light" mode.
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    App().mainloop()