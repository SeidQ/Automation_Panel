"""
tab_activation.py — Tab 2: Activation (Dealer Online — API)
Modern card-based live console + clean table summary.
"""
import re
import threading
import queue
from copy import deepcopy
from datetime import datetime

import customtkinter as ctk
import requests

from config import (C, FONT_UI, FONT_UI_B, FONT_MONO_S, FONT_LABEL,
                    DEFAULT_TEST_DATA, TARIFF_TYPE_MAP, TARIFF_TYPE_RMAP, CITY_MAP,
                    save_state, load_section)
from widgets import mk_section, mk_field, mk_divider, mk_panel_header, mk_label


# ══════════════════════════════════════════════════════
#  PIPELINE STEPS
# ══════════════════════════════════════════════════════
STEPS = ["Login", "Check MHM", "Register"]


# ══════════════════════════════════════════════════════
#  API HELPERS
# ══════════════════════════════════════════════════════
def _extract_csrf(html):
    for pattern in [
        r'<meta[^>]*name=["\']_csrf["\'][^>]*content=["\'](.*?)["\']',
        r'<input[^>]*name=["\']_csrf["\'][^>]*value=["\'](.*?)["\']',
        r'["\']X-CSRF-TOKEN["\']\s*:\s*["\'](.*?)["\']',
    ]:
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return None


def create_session(base_url, username, password):
    s = requests.Session()
    s.headers.update({
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Accept-Language":  "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
    })
    s.post(f"{base_url}/login",
           data={"username": username, "password": password},
           headers={"Content-Type": "application/x-www-form-urlencoded",
                    "Accept":       "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer":      f"{base_url}/login",
                    "Origin":       base_url},
           allow_redirects=True)
    if not s.cookies.get("SESSION"):
        raise Exception("Login failed — SESSION cookie not found.")
    page = s.get(f"{base_url}/customer",
                 headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    csrf = _extract_csrf(page.text) or s.cookies.get("XSRF-TOKEN")
    if csrf:
        s.headers.update({"X-CSRF-TOKEN": csrf})
    return s


def check_mhm(session, base_url, data):
    r = session.get(
        f"{base_url}/customer/checkMHM",
        params={"documentType": "1", "documentNumber": data["DOC_NUMBER"],
                "msisdn": data["MSISDN"], "simcard": data["SIMCARD"],
                "customerType": data["PLAN_TYPE"], "companyVoen": "null",
                "documentPin": data["DOC_PIN"], "requestType": data["TARIFF_TYPE"],
                "companySun": "", "segmentType": ""},
        headers={"Accept":  "application/json, text/javascript, */*; q=0.01",
                 "Referer": f"{base_url}/customer"})
    body = r.text.strip()
    if not body or body.startswith("<!"):
        raise Exception("checkMHM: session invalid")
    j = r.json()
    if isinstance(j, dict) and j.get("errorMessage"):
        raise Exception(f"checkMHM: {j['errorMessage']}")
    return j


def register_customer(session, base_url, data, consts):
    r = session.get(
        f"{base_url}/customer/registerCustomer",
        params={"country": consts["COUNTRY"], "city": consts["CITY"],
                "zip": consts["ZIP_CODE"], "tariff": data["TARIFF"],
                "imei": "", "msisdnDeviceType": "voice", "email": consts["EMAIL"],
                "additionalAddress": "", "additionalCity": "", "additional": "true",
                "nationality": consts["NATIONALITY"],
                "phone_1_prefix": consts["PHONE_1_PREFIX"],
                "phone_1_number": consts["PHONE_1_NUMBER"],
                "phone_2_prefix": "", "phone_2_number": "",
                "fax_prefix": "", "fax_number": "",
                "importer": consts["IMPORTER"], "curator": consts["CURATOR"],
                "foreign_day": "", "foreign_month": "", "foreign_year": "",
                "documentType": "1", "documentNumber": data["DOC_NUMBER"],
                "documentSeries": "", "msisdn": data["MSISDN"],
                "simcard": data["SIMCARD"], "customerType": data["PLAN_TYPE_REG"],
                "companyVoen": "null", "documentPin": data["DOC_PIN"],
                "requestType": data["TARIFF_TYPE"], "companySun": "",
                "campaign": "0", "shouldOpenIntLine": "false",
                "shouldBlockAds": "false", "shouldRefuseVHF": "false",
                "street": "", "segmentType": ""},
        headers={"Accept": "application/json", "Referer": f"{base_url}/customer"})
    if r.status_code != 200:
        raise Exception(f"registerCustomer failed [{r.status_code}]: {r.text}")
    return r.json()


def run_single(data, base_url, username, password, consts, log_q, result_q, stop_ev):
    msisdn       = data["MSISDN"]
    tariff_label = TARIFF_TYPE_RMAP.get(data["TARIFF_TYPE"], data["TARIFF_TYPE"])

    def log(step_idx, msg, level="info", done=False, error=False):
        log_q.put({
            "ts":    datetime.now().strftime("%H:%M:%S"),
            "msg":   msg,
            "level": level,
            "msisdn": msisdn,
            "step":  step_idx,
            "total": len(STEPS),
            "done":  done,
            "error": error,
        })

    try:
        if stop_ev.is_set():
            return

        # Step 0 — Login
        log(0, "Connecting to Dealer Online...")
        session = create_session(base_url, username, password)
        log(0, "Session created", "success")

        # Step 1 — Check MHM
        log(1, "Validating document & MHM check...")
        check_mhm(session, base_url, data)
        log(1, "MHM check passed", "success")

        # Step 2 — Register
        log(2, "Registering customer...")
        register_customer(session, base_url, data, consts)
        log(2, "Registration complete", "success", done=True)

        result_q.put({"MSISDN": msisdn, "PLAN_TYPE": data["PLAN_TYPE"],
                      "TARIFF_TYPE": tariff_label, "STATUS": "PASSED", "ERROR": ""})

    except Exception as e:
        step_idx = 0
        msg = str(e).replace("checkMHM: ", "").replace("registerCustomer failed ", "")
        if "checkMHM" in str(e) or "MHM" in str(e):
            step_idx = 1
        elif "registerCustomer" in str(e):
            step_idx = 2
        log(step_idx, msg, "error", done=True, error=True)


# ══════════════════════════════════════════════════════
#  MSISDN CARD — live step tracker widget
# ══════════════════════════════════════════════════════
class MsisdnCard:
    STEP_ICONS = ["🔐", "🔍", "📝"]

    def __init__(self, parent, msisdn, plan_type, tariff_type, index):
        self.msisdn = msisdn

        self._frame = ctk.CTkFrame(parent, fg_color=("#251540", "#EDE8F5"),
                                   corner_radius=12, border_width=1,
                                   border_color=("#3D2260", "#C4B0DC"))
        self._frame.pack(fill="x", padx=6, pady=(0, 8))

        # ── Header ────────────────────────────────────
        hdr = ctk.CTkFrame(self._frame, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(10, 6))

        # Index badge
        badge = ctk.CTkFrame(hdr, fg_color=("#5C2483", "#5C2483"),
                             width=26, height=26, corner_radius=6)
        badge.pack(side="left", padx=(0, 8))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=str(index),
                     font=("Segoe UI", 10, "bold"),
                     text_color="white").place(relx=.5, rely=.5, anchor="center")

        ctk.CTkLabel(hdr, text=msisdn,
                     font=("Consolas", 13, "bold"),
                     text_color=("#EDE8F5", "#1A0A2E")).pack(side="left")

        ctk.CTkLabel(hdr, text=f"  {plan_type}  ·  {tariff_type}",
                     font=("Segoe UI", 10),
                     text_color=("#8B75B0", "#6B5A8A")).pack(side="left", padx=4)

        self._ts_lbl = ctk.CTkLabel(hdr,
                                    text=datetime.now().strftime("%H:%M:%S"),
                                    font=("Consolas", 10),
                                    text_color=("#8B75B0", "#6B5A8A"))
        self._ts_lbl.pack(side="right")

        self._badge = ctk.CTkLabel(hdr, text="  ⏳ RUNNING  ",
                                   font=("Segoe UI", 10, "bold"),
                                   text_color=("#F59E0B", "#D97706"),
                                   fg_color=("#1C1030", "#FFFFFF"), corner_radius=6)
        self._badge.pack(side="right", padx=(0, 8))

        # ── Step progress ─────────────────────────────
        steps_row = ctk.CTkFrame(self._frame, fg_color="transparent")
        steps_row.pack(fill="x", padx=14, pady=(0, 4))

        self._step_widgets = []  # (icon_lbl, name_lbl)
        for i, name in enumerate(STEPS):
            sf = ctk.CTkFrame(steps_row, fg_color="transparent")
            sf.pack(side="left")

            icon = ctk.CTkLabel(sf, text=self.STEP_ICONS[i],
                                font=("Segoe UI", 12),
                                text_color=("#8B75B0", "#6B5A8A"))
            icon.pack(side="left", padx=(0, 2))

            lbl = ctk.CTkLabel(sf, text=name,
                               font=("Segoe UI", 10),
                               text_color=("#8B75B0", "#6B5A8A"))
            lbl.pack(side="left")

            if i < len(STEPS) - 1:
                ctk.CTkLabel(sf, text="  →  ",
                             font=("Segoe UI", 10),
                             text_color=("#3D2260", "#C4B0DC")).pack(side="left")

            self._step_widgets.append((icon, lbl))

        # ── Detail line ───────────────────────────────
        self._detail = ctk.CTkLabel(self._frame, text="",
                                    font=("Consolas", 14),
                                    text_color=("#8B75B0", "#6B5A8A"),
                                    anchor="w")
        self._detail.pack(fill="x", padx=14, pady=(0, 10))

    def update_step(self, step_idx, msg, level, done=False, error=False):
        for i, (icon, lbl) in enumerate(self._step_widgets):
            if i < step_idx:
                icon.configure(text="✓", text_color=("#22C55E", "#16A34A"))
                lbl.configure(text_color=("#22C55E", "#16A34A"))
            elif i == step_idx:
                if error:
                    icon.configure(text="✗",  text_color=("#EF4444", "#DC2626"))
                    lbl.configure(text_color=("#EF4444", "#DC2626"))
                elif done:
                    icon.configure(text="✓",  text_color=("#22C55E", "#16A34A"))
                    lbl.configure(text_color=("#22C55E", "#16A34A"))
                else:
                    icon.configure(text=self.STEP_ICONS[i], text_color=("#F59E0B", "#D97706"))
                    lbl.configure(text_color=("#F59E0B", "#D97706"))
            else:
                icon.configure(text=self.STEP_ICONS[i], text_color=("#8B75B0", "#6B5A8A"))
                lbl.configure(text_color=("#8B75B0", "#6B5A8A"))

        color_map = {"success": C["success"], "error": C["error"],
                     "warning": C["warning"], "info": C["muted"]}
        self._detail.configure(text=f"  ↳ {msg}",
                               text_color=color_map.get(level, C["muted"]))

        if done and not error:
            self._frame.configure(border_color=("#22C55E", "#16A34A"))
            self._badge.configure(text="  ✅ PASSED  ",
                                  text_color=("#22C55E", "#16A34A"), fg_color="#0B2210")
        elif done and error:
            self._frame.configure(border_color=("#EF4444", "#DC2626"))
            self._badge.configure(text="  ❌ FAILED  ",
                                  text_color=("#EF4444", "#DC2626"), fg_color="#2A0A0A")

        self._ts_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))


# ══════════════════════════════════════════════════════
#  TAB 2 UI CLASS
# ══════════════════════════════════════════════════════
class TabActivation:
    BASE_URL = "https://dealer-online.azercell.com"

    def __init__(self, tab, log_q: queue.Queue, result_q: queue.Queue,
                 stop_ev: threading.Event, T):
        self._tab      = tab
        self._log_q    = log_q
        self._result_q = result_q
        self._stop_ev  = stop_ev
        self._T        = T
        self._running  = False
        self._results  = []
        self._test_data = deepcopy(DEFAULT_TEST_DATA)
        self._sel_row  = None
        self._cards: dict = {}
        self._build()

    # ══════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════
    def _build(self):
        T   = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=5)
        tab.rowconfigure(0, weight=1)

        # ── Left config panel ─────────────────────────
        left = ctk.CTkScrollableFrame(
            tab, fg_color=("#1C1030", "#FFFFFF"), corner_radius=14,
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        mk_panel_header(left, T("config"))
        mk_section(left, T("login_online"))

        url_row = ctk.CTkFrame(left, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 7))
        ctk.CTkLabel(url_row, text="Base URL", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=135, anchor="w").pack(side="left")
        ctk.CTkLabel(url_row, text="dealer-online.azercell.com",
                     text_color=("#8B75B0", "#6B5A8A"), font=FONT_MONO_S).pack(side="left")

        self._cred_user = mk_field(left, "Username", "ccequlamova")
        self._cred_pass = mk_field(left, "Password", "dealeronline", show="*")

        mk_divider(left)
        mk_section(left, T("constants"))
        self._c_city    = mk_field(left, "City",        "Baku",               disabled=True)
        self._c_zip     = mk_field(left, "ZIP",         "AZC1122",            disabled=True)
        self._c_imp     = mk_field(left, "Importer",    "AZERCELL",           disabled=True)
        self._c_cur     = mk_field(left, "Curator",     "TEST",               disabled=True)
        self._c_country = mk_field(left, "Country",     "AZERBAIJAN",         disabled=True)
        self._c_nat     = mk_field(left, "Nationality", "AZERBAIJAN",         disabled=True)
        self._c_ph1p    = mk_field(left, "Phone Prefix","10")
        self._c_ph1n    = mk_field(left, "Phone Number","2210462")
        self._c_email   = mk_field(left, "Email",       "sgaziyev@azercell.com")

        mk_divider(left)
        mk_section(left, T("exec_mode"))
        self._thread_var = ctk.StringVar(value="parallel")
        rf = ctk.CTkFrame(left, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        rf.pack(fill="x", padx=16, pady=(0, 12))
        for txt, val in [(T("parallel"), "parallel"), (T("serial"), "serial")]:
            ctk.CTkRadioButton(
                rf, text=txt, variable=self._thread_var, value=val,
                font=FONT_LABEL, text_color=("#EDE8F5", "#1A0A2E"),
                fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0")
            ).pack(anchor="w", padx=14, pady=6)

        mk_divider(left)
        bf = ctk.CTkFrame(left, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=(6, 16))

        self._run_btn = ctk.CTkButton(
            bf, text=T("start"), font=("Segoe UI", 14, "bold"),
            fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0"),
            height=46, corner_radius=10, command=self._on_run)
        self._run_btn.pack(fill="x", pady=(0, 8))

        self._cancel_btn = ctk.CTkButton(
            bf, text=T("cancel"), font=FONT_UI_B,
            fg_color=("#EF4444", "#DC2626"), hover_color="#B91C1C",
            height=40, corner_radius=10, state="disabled",
            command=self._on_cancel)
        self._cancel_btn.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            bf, text=T("clear_log"), font=FONT_UI,
            fg_color=("#251540", "#EDE8F5"), hover_color=("#3D2260", "#C4B0DC"),
            text_color=("#8B75B0", "#6B5A8A"), height=36, corner_radius=10,
            command=self.clear_log
        ).pack(fill="x")

        # ── Right panel ───────────────────────────────
        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=2)
        right.rowconfigure(3, weight=3)
        right.columnconfigure(0, weight=1)

        # Test data header
        th = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12, height=52)
        th.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        th.pack_propagate(False)
        mk_label(th, T("test_data"), color=C["muted"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=18, pady=14)
        self._td_count = mk_label(th, f"{len(self._test_data)} {T('rows')}",
                                  color=C["accent"], font=FONT_MONO_S)
        self._td_count.pack(side="right", padx=10)
        ctk.CTkButton(th, text=T("delete"), width=70, height=30,
                      font=("Segoe UI", 11, "bold"), fg_color=("#EF4444", "#DC2626"),
                      hover_color="#B91C1C", corner_radius=8,
                      command=self._delete_sel).pack(side="right", pady=10)
        ctk.CTkButton(th, text="✎  Edit", width=80, height=30,
                      font=("Segoe UI", 11, "bold"), fg_color="#B45309", hover_color="#92400E",
                      text_color="white", corner_radius=8,
                      command=self._open_edit).pack(side="right", padx=6, pady=10)
        ctk.CTkButton(th, text=T("add"), width=90, height=30,
                      font=("Segoe UI", 11, "bold"), fg_color=("#5C2483", "#5C2483"),
                      hover_color=("#7C6EB0", "#7C6EB0"), corner_radius=8,
                      command=self._open_add).pack(side="right", padx=6, pady=10)

        # Test data table
        self._data_box = ctk.CTkTextbox(
            right, font=FONT_MONO_S, fg_color=("#1C1030", "#FFFFFF"),
            text_color=("#EDE8F5", "#1A0A2E"), border_color=("#3D2260", "#C4B0DC"),
            border_width=1, corner_radius=12, wrap="none")
        self._data_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self._data_box.bind("<Button-1>", self._on_row_click)
        self._render_data()

        # Live console header
        ch = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12, height=52)
        ch.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ch.pack_propagate(False)
        mk_label(ch, "⚡  LIVE CONSOLE", color=C["muted"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=18, pady=14)
        self._progress_lbl = mk_label(ch, "", color=C["accent"], font=FONT_MONO_S)
        self._progress_lbl.pack(side="right", padx=6)
        self._res_summary = mk_label(ch, "—", color=C["muted"], font=FONT_MONO_S)
        self._res_summary.pack(side="right", padx=10)

        # Live console scroll area
        self._console = ctk.CTkScrollableFrame(
            right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12,
            border_width=1, border_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        self._console.grid(row=3, column=0, sticky="nsew")
        self._console.columnconfigure(0, weight=1)

        self._show_placeholder()

        # Load saved state and bind autosave
        self._load_state()
        for w in [self._cred_user, self._cred_pass,
                  self._c_ph1p, self._c_ph1n, self._c_email]:
            w.bind("<FocusOut>", self._autosave)
            w.bind("<KeyRelease>", self._autosave)
        self._thread_var.trace_add("write", self._autosave)

    # ══════════════════════════════════════════════════
    #  PERSISTENCE
    # ══════════════════════════════════════════════════
    def _load_state(self):
        s = load_section("activation")
        if not s:
            return
        for widget, key in [
            (self._cred_user, "username"),
            (self._cred_pass, "password"),
            (self._c_ph1p,    "ph1p"),
            (self._c_ph1n,    "ph1n"),
            (self._c_email,   "email"),
        ]:
            val = s.get(key, "")
            if val:
                widget.configure(state="normal")
                widget.delete(0, "end")
                widget.insert(0, val)
        if s.get("mode"):
            self._thread_var.set(s["mode"])
        if s.get("test_data"):
            self._test_data = s["test_data"]
            self._render_data()

    def _autosave(self, *_):
        save_state("activation", {
            "username":  self._cred_user.get(),
            "password":  self._cred_pass.get(),
            "ph1p":      self._c_ph1p.get(),
            "ph1n":      self._c_ph1n.get(),
            "email":     self._c_email.get(),
            "mode":      self._thread_var.get(),
            "test_data": self._test_data,
        })

    # ══════════════════════════════════════════════════
    #  CONSOLE STATES
    # ══════════════════════════════════════════════════
    def _show_placeholder(self):
        for w in self._console.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._console,
                     text="▶  Press START to begin activation",
                     font=("Segoe UI", 12),
                     text_color=("#8B75B0", "#6B5A8A")).pack(pady=28)

    def _show_summary(self):
        for w in self._console.winfo_children():
            w.destroy()

        T      = self._T
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")

        # Summary header
        hcard = ctk.CTkFrame(self._console, fg_color=("#5C2483", "#5C2483"), corner_radius=12)
        hcard.pack(fill="x", padx=6, pady=(6, 10))
        ctk.CTkLabel(hcard, text=T("summary_title"),
                     font=("Segoe UI", 13, "bold"),
                     text_color="white").pack(side="left", padx=18, pady=12)

        stats = ctk.CTkFrame(hcard, fg_color="transparent")
        stats.pack(side="right", padx=18)
        for lbl, val, col in [
            (T("total"),  str(len(self._results)), "white"),
            (T("passed"), str(passed),              C["success"]),
            (T("failed"), str(failed),              C["error"] if failed else C["muted"]),
        ]:
            sf = ctk.CTkFrame(stats, fg_color=("#120A1E", "#F3F0F8"), corner_radius=8)
            sf.pack(side="left", padx=4, pady=8)
            ctk.CTkLabel(sf, text=val,
                         font=("Segoe UI", 18, "bold"),
                         text_color=col).pack(padx=14, pady=(6, 0))
            ctk.CTkLabel(sf, text=lbl,
                         font=("Segoe UI", 9),
                         text_color=("#8B75B0", "#6B5A8A")).pack(padx=14, pady=(0, 6))

        # Column headers
        col_hdr = ctk.CTkFrame(self._console, fg_color=("#251540", "#EDE8F5"), corner_radius=8)
        col_hdr.pack(fill="x", padx=6, pady=(0, 4))
        for txt, w in [("#", 32), ("MSISDN", 120), ("Plan", 90),
                       ("Type", 90), ("Status", 110), ("Note", 0)]:
            ctk.CTkLabel(col_hdr, text=txt,
                         font=("Segoe UI", 10, "bold"),
                         text_color=("#8B75B0", "#6B5A8A"),
                         width=w or 0, anchor="w"
                         ).pack(side="left",
                                padx=(12 if txt == "#" else 4, 4),
                                pady=7,
                                fill="x" if not w else None,
                                expand=(not w))

        # Result rows
        for i, r in enumerate(self._results, 1):
            ok     = r["STATUS"] == "PASSED"
            row_bg = "#0B2210" if ok else "#2A0A0A"
            bdr    = C["success"] if ok else C["error"]

            rc = ctk.CTkFrame(self._console, fg_color=row_bg,
                              corner_radius=10, border_width=1,
                              border_color=bdr)
            rc.pack(fill="x", padx=6, pady=2)

            ctk.CTkLabel(rc, text=str(i), font=("Consolas", 11),
                         text_color=("#8B75B0", "#6B5A8A"), width=32, anchor="w"
                         ).pack(side="left", padx=(12, 4), pady=9)
            ctk.CTkLabel(rc, text=r["MSISDN"], font=("Consolas", 12, "bold"),
                         text_color=("#EDE8F5", "#1A0A2E"), width=120, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc, text=r["PLAN_TYPE"], font=("Segoe UI", 11),
                         text_color=("#8B75B0", "#6B5A8A"), width=90, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc, text=r["TARIFF_TYPE"], font=("Segoe UI", 11),
                         text_color=("#8B75B0", "#6B5A8A"), width=90, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc,
                         text="  ✅ PASSED  " if ok else "  ❌ FAILED  ",
                         font=("Segoe UI", 10, "bold"),
                         text_color=("#22C55E", "#16A34A") if ok else C["error"],
                         fg_color=("#1C1030", "#FFFFFF"), corner_radius=6
                         ).pack(side="left", padx=4, pady=9)
            if r["ERROR"]:
                ctk.CTkLabel(rc, text=f"↳ {r['ERROR']}",
                             font=("Consolas", 10),
                             text_color=("#EF4444", "#DC2626"), anchor="w"
                             ).pack(side="left", padx=8, pady=9,
                                    fill="x", expand=True)

    # ══════════════════════════════════════════════════
    #  RUN / CANCEL
    # ══════════════════════════════════════════════════
    def _on_run(self):
        if self._running:
            return
        self._results.clear()
        self._cards.clear()
        self._stop_ev.clear()
        self._running = True
        self._run_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._progress_lbl.configure(text="")
        self._res_summary.configure(text="—", text_color=("#8B75B0", "#6B5A8A"))

        for w in self._console.winfo_children():
            w.destroy()

        username  = self._cred_user.get().strip()
        password  = self._cred_pass.get().strip()
        consts    = self._get_consts()
        mode      = self._thread_var.get()
        data_list = deepcopy(self._test_data)

        for i, d in enumerate(data_list, 1):
            tt   = TARIFF_TYPE_RMAP.get(d["TARIFF_TYPE"], d["TARIFF_TYPE"])
            card = MsisdnCard(self._console, d["MSISDN"], d["PLAN_TYPE"], tt, i)
            self._cards[d["MSISDN"]] = card

        def worker():
            if mode == "parallel":
                threads = [
                    threading.Thread(
                        target=run_single,
                        args=(d, self.BASE_URL, username, password,
                              consts, self._log_q, self._result_q, self._stop_ev),
                        daemon=True)
                    for d in data_list]
                for t in threads: t.start()
                for t in threads: t.join()
            else:
                for d in data_list:
                    if self._stop_ev.is_set():
                        break
                    run_single(d, self.BASE_URL, username, password,
                               consts, self._log_q, self._result_q, self._stop_ev)

            # Always re-enable buttons when work finishes
            self._tab.after(100, self._force_done)

        threading.Thread(target=worker, daemon=True).start()

    def _force_done(self):
        """Called from worker thread via after() — always resets button states."""
        self._running = False
        self._run_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        if self._results:
            self._show_summary()

    def _on_cancel(self):
        self._stop_ev.set()
        self._running = False
        self._run_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")

    # ══════════════════════════════════════════════════
    #  PUBLIC API  (called by App poll loop)
    # ══════════════════════════════════════════════════
    def is_running(self):
        return self._running

    def get_test_count(self):
        return len(self._test_data)

    def collect_result(self, r):
        self._results.append(r)
        passed = sum(1 for x in self._results if x["STATUS"] == "PASSED")
        failed = sum(1 for x in self._results if x["STATUS"] == "FAILED")
        done   = len(self._results)
        self._progress_lbl.configure(
            text=f"{done} / {len(self._test_data)}", text_color=("#8B75B0", "#6B5A8A"))
        self._res_summary.configure(
            text=f"✅ {passed}   ❌ {failed}",
            text_color=("#22C55E", "#16A34A") if failed == 0 else C["error"])

    def on_done(self):
        self._running = False
        self._run_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")
        self._show_summary()
        return passed, failed

    def append_log(self, ts, msg, level, msisdn=None, **kw):
        if not msisdn:
            return
        card = self._cards.get(msisdn)
        if not card:
            return
        card.update_step(
            kw.get("step", 0), msg, level,
            done=kw.get("done", False),
            error=kw.get("error", False))

    def clear_log(self):
        self._cards.clear()
        self._results.clear()
        self._res_summary.configure(text="—", text_color=("#8B75B0", "#6B5A8A"))
        self._progress_lbl.configure(text="")
        self._show_placeholder()

    # ══════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════
    def _get_consts(self):
        city = self._c_city.get()
        return {
            "CITY":           CITY_MAP.get(city, city),
            "ZIP_CODE":       self._c_zip.get(),
            "IMPORTER":       self._c_imp.get(),
            "CURATOR":        self._c_cur.get(),
            "COUNTRY":        self._c_country.get(),
            "NATIONALITY":    self._c_nat.get(),
            "PHONE_1_PREFIX": self._c_ph1p.get(),
            "PHONE_1_NUMBER": self._c_ph1n.get(),
            "EMAIL":          self._c_email.get(),
        }

    def _render_data(self):
        self._data_box.configure(state="normal")
        self._data_box.delete("1.0", "end")
        self._data_box.tag_config("header",   foreground=C["muted"])
        self._data_box.tag_config("selected", background="#3D1A6B")
        hdr = (f"{'#':<3}  {'MSISDN':<12}  {'SIMCARD':<15}  "
               f"{'DOC_NO':<10}  {'PIN':<8}  {'TARIFF':<14}  {'PLAN':<10}  {'TYPE'}\n")
        self._data_box.insert("end", hdr, "header")
        self._data_box.insert("end", "─" * 88 + "\n", "header")
        for i, d in enumerate(self._test_data, 1):
            tt = TARIFF_TYPE_RMAP.get(d["TARIFF_TYPE"], d["TARIFF_TYPE"])
            tr = "Yeni Her Yere" if d.get("TARIFF", "") == "371" else d.get("TARIFF", "")
            line = (f"{i:<3}  {d['MSISDN']:<12}  {d['SIMCARD']:<15}  "
                    f"{d['DOC_NUMBER']:<10}  {d['DOC_PIN']:<8}  "
                    f"{tr:<14}  {d['PLAN_TYPE']:<10}  {tt}\n")
            self._data_box.insert("end", line,
                                  "selected" if self._sel_row == i - 1 else "")
        self._data_box.configure(state="disabled")
        self._td_count.configure(
            text=f"{len(self._test_data)} {self._T('rows')}")

    def _on_row_click(self, event):
        idx = int(self._data_box.index(
            f"@{event.x},{event.y}").split(".")[0])
        data_idx = idx - 3
        self._sel_row = (data_idx
                         if 0 <= data_idx < len(self._test_data) else None)
        self._render_data()

    def _delete_sel(self):
        if self._sel_row is None:
            return
        del self._test_data[self._sel_row]
        self._sel_row = None
        self._render_data()
        self._autosave()

    def _open_add(self):
        T   = self._T
        dlg = ctk.CTkToplevel(self._tab)
        dlg.title(T("add_dialog"))
        dlg.geometry("480x560")
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()

        dh = ctk.CTkFrame(dlg, fg_color=("#5C2483", "#5C2483"), corner_radius=0, height=52)
        dh.pack(fill="x")
        dh.pack_propagate(False)
        ctk.CTkLabel(dh, text=T("add_dialog"), font=("Segoe UI", 14, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        fields = {}
        frm = ctk.CTkScrollableFrame(dlg, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12)
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        for key in ["MSISDN", "DOC_NUMBER", "DOC_PIN"]:
            row = ctk.CTkFrame(frm, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(row, text=key, text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_LABEL, width=120, anchor="w").pack(side="left")
            if key == "MSISDN":
                vcmd = (dlg.register(lambda s: len(s) <= 9), "%P")
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
                                 validate="key", validatecommand=vcmd)
            else:
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36)
            e.pack(side="left", fill="x", expand=True)
            fields[key] = e

        # SIMCARD — prefix 8999401 disabled + suffix max 6 chars
        sc_row = ctk.CTkFrame(frm, fg_color="transparent")
        sc_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(sc_row, text="SIMCARD", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        prefix_lbl = ctk.CTkEntry(sc_row, fg_color=("#3D2260", "#C4B0DC"),
                                  border_color=("#3D2260", "#C4B0DC"),
                                  text_color=("#8B75B0", "#6B5A8A"),
                                  font=FONT_MONO_S, height=36, width=80)
        prefix_lbl.insert(0, "8999401")
        prefix_lbl.configure(state="disabled")
        prefix_lbl.pack(side="left", padx=(0, 4))
        sc_vcmd = (dlg.register(lambda s: len(s) <= 6), "%P")
        sc_entry = ctk.CTkEntry(sc_row, fg_color=("#251540", "#EDE8F5"),
                                border_color=("#3D2260", "#C4B0DC"),
                                text_color=("#EDE8F5", "#1A0A2E"),
                                font=FONT_MONO_S, height=36,
                                validate="key", validatecommand=sc_vcmd)
        sc_entry.pack(side="left", fill="x", expand=True)

        # TARIFF dropdown
        TARIFF_CODE_MAP = {"Yeni Her Yere": "371"}
        tr_row = ctk.CTkFrame(frm, fg_color="transparent")
        tr_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tr_row, text="TARIFF", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tr_var = ctk.StringVar(value="Yeni Her Yere")
        tr_menu = ctk.CTkOptionMenu(
            tr_row, values=["Yeni Her Yere"], variable=tr_var,
            font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
            button_color=("#5C2483", "#5C2483"), button_hover_color=("#7C6EB0", "#7C6EB0"),
            dropdown_fg_color=("#1C1030", "#FFFFFF"), text_color=("#EDE8F5", "#1A0A2E"),
            dropdown_text_color="#EDE8F5", dropdown_hover_color="#3D2260",
        )
        tr_menu.pack(side="left", fill="x", expand=True)

        pt_row = ctk.CTkFrame(frm, fg_color="transparent")
        pt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(pt_row, text="PLAN_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        pt_var = ctk.StringVar(value="PostPaid")
        ctk.CTkOptionMenu(pt_row, values=["PostPaid", "Prepaid"], variable=pt_var,
                          font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
                          button_color=("#5C2483", "#5C2483"), button_hover_color=("#7C6EB0", "#7C6EB0"),
                          dropdown_fg_color=("#1C1030", "#FFFFFF"), text_color=("#EDE8F5", "#1A0A2E"),
                          dropdown_text_color="#EDE8F5", dropdown_hover_color="#3D2260",
                          ).pack(side="left", fill="x", expand=True)

        def _sync_tariff_by_plan(*_):
            if pt_var.get() == "Prepaid":
                tr_var.set("")
                tr_menu.configure(state="disabled")
            else:
                if not tr_var.get().strip():
                    tr_var.set("Yeni Her Yere")
                tr_menu.configure(state="normal")

        pt_var.trace_add("write", _sync_tariff_by_plan)
        _sync_tariff_by_plan()

        tt_row = ctk.CTkFrame(frm, fg_color="transparent")
        tt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tt_row, text="TARIFF_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tt_var = ctk.StringVar(value="Individual")
        ctk.CTkOptionMenu(tt_row, values=list(TARIFF_TYPE_MAP.keys()), variable=tt_var,
                          font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
                          button_color=("#5C2483", "#5C2483"), button_hover_color=("#7C6EB0", "#7C6EB0"),
                          dropdown_fg_color=("#1C1030", "#FFFFFF"), text_color=("#EDE8F5", "#1A0A2E"),
                          dropdown_text_color="#EDE8F5", dropdown_hover_color="#3D2260",
                          ).pack(side="left", fill="x", expand=True)

        def save():
            row_data = {k: v.get().strip() for k, v in fields.items()}
            row_data["SIMCARD"]       = "8999401" + sc_entry.get().strip()
            row_data["PLAN_TYPE"]     = pt_var.get()
            row_data["PLAN_TYPE_REG"] = pt_var.get()

            # ✅ Prepaid olduqda TARIFF boş saxla
            if pt_var.get() == "Prepaid":
                row_data["TARIFF"] = ""
            else:
                row_data["TARIFF"] = TARIFF_CODE_MAP.get(tr_var.get(), "371")

            row_data["TARIFF_TYPE"]   = TARIFF_TYPE_MAP[tt_var.get()]
            if not row_data["MSISDN"] or not sc_entry.get().strip():
                return
            self._test_data.append(row_data)
            self._render_data()
            self._autosave()
            dlg.destroy()

        ctk.CTkButton(dlg, text=T("save"), fg_color=("#5C2483", "#5C2483"),
                      hover_color=("#7C6EB0", "#7C6EB0"), font=("Segoe UI", 13, "bold"),
                      height=44, corner_radius=10, command=save
                      ).pack(fill="x", padx=16, pady=(0, 16))

    def _open_edit(self):
        if self._sel_row is None:
            return
        d   = self._test_data[self._sel_row]
        T   = self._T
        dlg = ctk.CTkToplevel(self._tab)
        dlg.title("✎  Edit Row")
        dlg.geometry("480x560")
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()

        dh = ctk.CTkFrame(dlg, fg_color="#B45309", corner_radius=0, height=52)
        dh.pack(fill="x")
        dh.pack_propagate(False)
        ctk.CTkLabel(dh, text="✎  Edit Test Data", font=("Segoe UI", 14, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        fields = {}
        frm = ctk.CTkScrollableFrame(dlg, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12)
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        for key in ["MSISDN", "DOC_NUMBER", "DOC_PIN"]:
            row = ctk.CTkFrame(frm, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(row, text=key, text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_LABEL, width=120, anchor="w").pack(side="left")
            if key == "MSISDN":
                vcmd = (dlg.register(lambda s: len(s) <= 9), "%P")
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
                                 validate="key", validatecommand=vcmd)
            else:
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36)
            e.pack(side="left", fill="x", expand=True)
            e.insert(0, d.get(key, ""))
            fields[key] = e

        # SIMCARD — prefix 8999401 disabled + suffix edit max 6 chars
        sc_row = ctk.CTkFrame(frm, fg_color="transparent")
        sc_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(sc_row, text="SIMCARD", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        prefix_lbl = ctk.CTkEntry(sc_row, fg_color=("#3D2260", "#C4B0DC"),
                                  border_color=("#3D2260", "#C4B0DC"),
                                  text_color=("#8B75B0", "#6B5A8A"),
                                  font=FONT_MONO_S, height=36, width=80)
        prefix_lbl.insert(0, "8999401")
        prefix_lbl.configure(state="disabled")
        prefix_lbl.pack(side="left", padx=(0, 4))
        sc_vcmd = (dlg.register(lambda s: len(s) <= 13), "%P")
        sc_entry = ctk.CTkEntry(sc_row, fg_color=("#251540", "#EDE8F5"),
                                border_color=("#3D2260", "#C4B0DC"),
                                text_color=("#EDE8F5", "#1A0A2E"),
                                font=FONT_MONO_S, height=36,
                                validate="key", validatecommand=sc_vcmd)
        sc_entry.pack(side="left", fill="x", expand=True)
        existing_sc = d.get("SIMCARD", "")
        if existing_sc.startswith("8999401"):
            sc_entry.insert(0, existing_sc[7:])
        else:
            sc_entry.insert(0, existing_sc)

        # TARIFF dropdown
        TARIFF_CODE_MAP  = {"Yeni Her Yere": "371"}
        TARIFF_RCODE_MAP = {"371": "Yeni Her Yere"}
        tr_row = ctk.CTkFrame(frm, fg_color="transparent")
        tr_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tr_row, text="TARIFF", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tr_var = ctk.StringVar(value=TARIFF_RCODE_MAP.get(d.get("TARIFF", "371"), "Yeni Her Yere"))
        tr_menu = ctk.CTkOptionMenu(tr_row, values=["Yeni Her Yere"], variable=tr_var,
                                    font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
                                    button_color=("#5C2483", "#5C2483"),
                                    button_hover_color=("#7C6EB0", "#7C6EB0"),
                                    dropdown_fg_color=("#1C1030", "#FFFFFF"),
                                    text_color=("#EDE8F5", "#1A0A2E"),
                                    dropdown_text_color="#EDE8F5",
                                    dropdown_hover_color="#3D2260",
                                    )
        tr_menu.pack(side="left", fill="x", expand=True)

        pt_row = ctk.CTkFrame(frm, fg_color="transparent")
        pt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(pt_row, text="PLAN_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        pt_var = ctk.StringVar(value=d.get("PLAN_TYPE", "PostPaid"))
        ctk.CTkOptionMenu(pt_row, values=["PostPaid", "Prepaid"], variable=pt_var,
                          font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
                          button_color=("#5C2483", "#5C2483"), button_hover_color=("#7C6EB0", "#7C6EB0"),
                          dropdown_fg_color=("#1C1030", "#FFFFFF"), text_color=("#EDE8F5", "#1A0A2E"),
                          dropdown_text_color="#EDE8F5", dropdown_hover_color="#3D2260",
                          ).pack(side="left", fill="x", expand=True)

        def _sync_tariff_by_plan(*_):
            if pt_var.get() == "Prepaid":
                tr_var.set("")
                tr_menu.configure(state="disabled")
            else:
                if not tr_var.get().strip():
                    tr_var.set("Yeni Her Yere")
                tr_menu.configure(state="normal")

        pt_var.trace_add("write", _sync_tariff_by_plan)
        _sync_tariff_by_plan()

        tt_row = ctk.CTkFrame(frm, fg_color="transparent")
        tt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tt_row, text="TARIFF_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tt_var = ctk.StringVar(value=TARIFF_TYPE_RMAP.get(d.get("TARIFF_TYPE", "flat"), "Individual"))
        ctk.CTkOptionMenu(tt_row, values=list(TARIFF_TYPE_MAP.keys()), variable=tt_var,
                          font=FONT_MONO_S, fg_color=("#251540", "#EDE8F5"),
                          button_color=("#5C2483", "#5C2483"), button_hover_color=("#7C6EB0", "#7C6EB0"),
                          dropdown_fg_color=("#1C1030", "#FFFFFF"), text_color=("#EDE8F5", "#1A0A2E"),
                          dropdown_text_color="#EDE8F5", dropdown_hover_color="#3D2260",
                          ).pack(side="left", fill="x", expand=True)

        def save():
            row_data = {k: v.get().strip() for k, v in fields.items()}
            row_data["SIMCARD"]       = sc_entry.get().strip()
            row_data["PLAN_TYPE"]     = pt_var.get()
            row_data["PLAN_TYPE_REG"] = pt_var.get()

            if pt_var.get() == "Prepaid":
                row_data["TARIFF"] = ""
            else:
                row_data["TARIFF"] = TARIFF_CODE_MAP.get(tr_var.get(), "371")

            row_data["TARIFF_TYPE"]   = TARIFF_TYPE_MAP[tt_var.get()]
            if not row_data["MSISDN"] or not sc_entry.get().strip():
                return
            self._test_data[self._sel_row] = row_data
            self._render_data()
            self._autosave()
            dlg.destroy()

        ctk.CTkButton(dlg, text="✎  Yadda Saxla", fg_color="#B45309",
                      hover_color="#92400E", text_color="white",
                      font=("Segoe UI", 13, "bold"),
                      height=44, corner_radius=10, command=save
                      ).pack(fill="x", padx=16, pady=(0, 16))