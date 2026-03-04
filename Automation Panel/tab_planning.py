"""
tab_planning.py — Tab 1: Number Planning (Dealer Express — Selenium)
v5.1 — CSV auto-generation integrated.

Dəyişikliklər:
  • Fayl seçmə sahələri ÇIXARILDI
  • Sağ paneldə data-entry cədvəli əlavə edildi (Activation tabı kimi)
  • START zamanı 3 CSV avtomatik yaradılır (csv.QUOTE_ALL — type mismatch yoxdur)
  • Selenium müvəqqəti CSV-ləri upload edir, iş bitdikdən sonra silinir
  • Bütün mövcud Selenium məntiqi dəyişdirilmədən saxlanıldı
"""
import os
import csv
import tempfile
import threading
import queue
from copy import deepcopy
from datetime import datetime

import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import C, FONT_UI, FONT_UI_B, FONT_MONO_S, FONT_LABEL, FONT_SECTION
from config import save_state, load_section
from widgets import mk_section, mk_field, mk_divider, mk_panel_header, mk_label


# ══════════════════════════════════════════════════════
#  CSV HEADERS  (portalın gözlədiyi dəqiq sütun adları)
# ══════════════════════════════════════════════════════
_PLAN_HEADERS = [
    "Msisdn (9 digits long)",
    "Number usage type (VOICE or DATA)",
    "Payment plan 1-Postpaid   2-Prepaid",
    "Price (With qepik)",
    "Segment type      1 - B2B   2 - B2C  3 - Internal  4 - Guest",
    "Sim card serial  (19 or 20 digits long)",
    "Is public    0 - not public, 1 - public",
    "number type",
]

_UPDATE_HEADERS = [
    "Msisdn (9 digits long)",
    "Payment plan 1-Postpaid   2-Prepaid",
    "Price (with qepik)",
    "Segment type      1 - B2B   2 - B2C  3 - Internal  4 - Guest",
    "Sim card serial  (19 or 20 digits long)",
    "Description",
    "Is public    0 - not public, 1 - public ",
    "number type",
]

_PLAN_CODE = {"PostPaid": "1", "Prepaid": "2"}

_SEGMENT_OPTS = {
    "B2C  (2)":      "2",
    "B2B  (1)":      "1",
    "Internal (3)":  "3",
    "Guest  (4)":    "4",
}
_SEGMENT_RMAP = {v: k for k, v in _SEGMENT_OPTS.items()}


# ══════════════════════════════════════════════════════
#  CSV GENERATOR
# ══════════════════════════════════════════════════════
def _write_csv(path, headers, rows):
    """
    Dırnaqsız CSV — portal plain text gözləyir.
    utf-8-sig encoding BOM əlavə edir ki, portal encoding xətası verməsin.
    """
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(rows)


def build_csvs(data_rows):
    """
    UI data siyahısından 3 müvəqqəti CSV fayl yaradır.
    Returns: (plan_path, update_path, assign_path)
    """
    tmp = tempfile.gettempdir()
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    plan_path   = os.path.join(tmp, f"np_planning_{ts}.csv")
    update_path = os.path.join(tmp, f"np_update_{ts}.csv")
    assign_path = os.path.join(tmp, f"np_assign_{ts}.csv")

    plan_rows = []
    update_rows = []
    assign_rows = []

    for d in data_rows:
        msisdn   = str(d.get("MSISDN",      "")).strip()
        simcard  = str(d.get("SIMCARD",     "")).strip()
        plan_c   = _PLAN_CODE.get(d.get("PLAN_TYPE", "PostPaid"), "1")
        price    = str(d.get("PRICE",        "")).strip()
        segment  = str(d.get("SEGMENT",     "2")).strip()
        public_f = str(d.get("PUBLIC",       "0")).strip()
        usage    = str(d.get("USAGE",    "VOICE")).strip()
        numtype  = str(d.get("NUMBER_TYPE", "EXTERNAL")).strip()
        desc     = str(d.get("DESCRIPTION", "")).strip()

        plan_rows.append([msisdn, usage, plan_c, price, segment, simcard, public_f, numtype])
        update_rows.append([msisdn, plan_c, price, segment, simcard, desc, public_f, numtype])
        assign_rows.append([msisdn])

    _write_csv(plan_path,   _PLAN_HEADERS,   plan_rows)
    _write_csv(update_path, _UPDATE_HEADERS, update_rows)

    # Assign: başlıqsız, yalnız MSISDN-lər
    with open(assign_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for row in assign_rows:
            writer.writerow(row)

    return plan_path, update_path, assign_path


# ══════════════════════════════════════════════════════
#  SELENIUM WORKER  (dəyişdirilmədən saxlanıldı)
# ══════════════════════════════════════════════════════
def _find_chromedriver():
    import shutil
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
    if driver_path:
        return driver_path
    for candidate in [
        rf"C:\Users\{os.getenv('USERNAME', '')}\Desktop\chromedriver-win64\chromedriver.exe",
        rf"C:\Users\{os.getenv('USERNAME', '')}\Downloads\chromedriver-win64\chromedriver.exe",
        r"C:\chromedriver\chromedriver.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "chromedriver not found. Please place it on PATH or set path manually.")


def _wait_toast_gone(driver, wait):
    try:
        wait.until_not(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".mat-progress-bar, .loading-overlay")))
    except Exception:
        pass


def run_number_planning(cfg, log_q, stop_ev):
    def log(msg, level="info"):
        log_q.put({"ts": datetime.now().strftime("%H:%M:%S"),
                   "msg": msg, "level": level, "_tab": "np"})

    driver_path = cfg.get("chromedriver", "").strip() or _find_chromedriver()

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    wait   = WebDriverWait(driver, 15)
    wait30 = WebDriverWait(driver, 30)

    try:
        # ── Login ──────────────────────────────────────
        log("🔐 Logging in to Dealer Express...")
        driver.get(
            "https://rhsso.azercell.com/auth/realms/external/protocol/openid-connect/auth"
            "?client_id=dealer-manager"
            "&redirect_uri=https%3A%2F%2Fdealerexpress.azercell.com%2Fnumbers"
            "&state=9d426ab2-6db7-4242-8809-2293b6b219f6"
            "&response_mode=fragment&response_type=code&scope=openid"
            "&nonce=1f4053e4-a0d3-4be8-85c9-4021e95f00c6"
        )
        if stop_ev.is_set(): return

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//input[@id='username'])[1]"))).send_keys(cfg["username"])
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//input[@id='password'])[1]"))).send_keys(cfg["password"])
        driver.find_element(By.XPATH, "(//input[@id='kc-login'])[1]").click()
        wait30.until(EC.url_contains("dealerexpress.azercell.com"))
        log("✓ Login successful.", "success")

        # ── Step 1 — Number Planning ───────────────────
        if stop_ev.is_set(): return
        log("📋 Navigating to Number Planning...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//li[@routerlink='/planning']"))).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//div[@class='mat-radio-label-content'])[2]"))).click()
        log("  ✓ 'Preparing for resold' selected.")

        fi = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@id='fileInput']")))
        driver.execute_script("arguments[0].style.display='block';", fi)
        fi.send_keys(cfg["plan_file"])
        log(f"  ✓ Planning CSV uploaded.")

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Plan numbers']/parent::button"))).click()
        log("  ✓ 'Plan numbers' clicked. Waiting for response...", "warning")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        # ── Step 2 — Number Update ─────────────────────
        if stop_ev.is_set(): return
        log("🔄 Switching to Number Update tab...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//div[@id='mat-tab-label-0-1'])"))).click()

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//mat-select[@id='mat-select-3']"))).click()
        panel = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'mat-select-panel')]")))
        driver.execute_script("arguments[0].scrollTop = 1200;", panel)
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[@class='mat-option-text' and normalize-space()='normal']"))).click()
        log("  ✓ 'normal' tariff selected.")

        fi = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@id='fileInput']")))
        driver.execute_script("arguments[0].style.display='block';", fi)
        fi.send_keys(cfg["update_file"])
        log("  ✓ Update CSV uploaded.")

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Update numbers']/parent::button"))).click()
        log("  ✓ 'Update numbers' clicked.", "success")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        # ── Step 3 — Assign to Distributor ────────────
        if stop_ev.is_set(): return
        log("💼 Number Sales — Assigning to distributor...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//li[@routerlink='/numbers']"))).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//mat-select)[1]"))).click()
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'mat-select-panel')]")))
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[@class='mat-option-text' and normalize-space()='Elmar Abuzerli']")
        )).click()
        log("  ✓ 'Elmar Abuzerli' selected.")

        fi = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@id='fileInput']")))
        driver.execute_script("arguments[0].style.display='block';", fi)
        fi.send_keys(cfg["assign_file"])

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Assign (File)']/parent::button"))).click()
        log("  ✓ File assigned to Elmar Abuzerli.", "success")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')]")))
        _wait_toast_gone(driver, wait)

        # ── Step 4 — Assign to Contractor Dealer ──────
        if stop_ev.is_set(): return
        log("🏢 Number Sales — Assigning to contractor dealer...")
        radio = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[@class='mat-radio-label-content' "
                       "and contains(text(),'Assign to contractor dealer')]")))
        driver.execute_script("arguments[0].click();", radio)

        inp = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//input[contains(@class,'mat-autocomplete-trigger')]")))
        inp.click()
        inp.send_keys("Azercell")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[@class='mat-option-text' and contains(text(),'Azercell')]")
        )).click()
        log("  ✓ 'Azercell' selected.")

        fi = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@id='fileInput']")))
        driver.execute_script("arguments[0].style.display='block';", fi)
        fi.send_keys(cfg["assign_file"])

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Assign (File)']/parent::button"))).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Assign to contractor dealer']/parent::button")
        )).click()

        log("✅ Number Planning flow completed successfully!", "success")

    except Exception as e:
        log(f"✗ ERROR: {e}", "error")
        raise
    finally:
        driver.quit()
        # Müvəqqəti CSV-ləri sil
        for p in [cfg.get("plan_file"), cfg.get("update_file"), cfg.get("assign_file")]:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


# ══════════════════════════════════════════════════════
#  DIALOG HELPERS
# ══════════════════════════════════════════════════════
def _center_on_parent(dlg, parent, w=520, h=580):
    parent.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    dlg.geometry(f"{w}x{h}+{px+(pw-w)//2}+{py+(ph-h)//2}")

def _style_dialog(dlg):
    import os as _os
    try:
        _ico = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo", "azercell.ico")
        if _os.path.exists(_ico):
            dlg.iconbitmap(_ico)
    except Exception:
        pass
    try:
        from ctypes import windll, byref, sizeof, c_int
        dlg.update_idletasks()
        hwnd = windll.user32.GetParent(dlg.winfo_id())
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x1E0A12)), sizeof(c_int))
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  TAB 1 UI CLASS
# ══════════════════════════════════════════════════════
class TabPlanning:
    """Builds and owns Tab 1 — Number Planning."""

    def __init__(self, tab, log_q: queue.Queue, T):
        self._tab     = tab
        self._log_q   = log_q
        self._T       = T
        self._running = False
        self._stop_ev = threading.Event()
        self._data    = []      # list of row dicts
        self._sel_row = None
        self._build()

    # ── Build ──────────────────────────────────────────
    def _build(self):
        T   = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=5)
        tab.rowconfigure(0, weight=1)

        # ── LEFT: login + buttons ─────────────────────
        left = ctk.CTkScrollableFrame(
            tab, fg_color=("#1C1030", "#FFFFFF"), corner_radius=14,
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        mk_panel_header(left, T("config"))
        mk_section(left, T("login_express"))
        self._np_user = mk_field(left, "Username", "ccequlamova")
        self._np_pass = mk_field(left, "Password", "Yltak_141012#", show="*")
        mk_divider(left)

        # CSV info card
        info = ctk.CTkFrame(left, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        info.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(
            info,
            text="📄  CSV files are generated automatically\n"
                 "    from the data table on the right.\n"
                 "    No manual file preparation needed.",
            font=("Segoe UI", 10),
            text_color=("#8B75B0", "#6B5A8A"),
            justify="left"
        ).pack(padx=14, pady=10, anchor="w")

        mk_divider(left)

        bf = ctk.CTkFrame(left, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=(6, 16))

        self._start_btn = ctk.CTkButton(
            bf, text=T("start"), font=("Segoe UI", 14, "bold"),
            fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0"),
            height=46, corner_radius=10, command=self._on_start)
        self._start_btn.pack(fill="x", pady=(0, 8))

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
            command=self._clear_log).pack(fill="x")

        # ── RIGHT: data table + log ───────────────────
        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=2)   # data table
        right.rowconfigure(3, weight=3)   # log

        # Data table header
        th = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                          corner_radius=12, height=52)
        th.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        th.pack_propagate(False)

        mk_label(th, "📋  PLANNING DATA",
                 color=C["muted"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=18, pady=14)

        self._td_count = mk_label(
            th, f"0 {T('rows')}", color=C["accent"], font=FONT_MONO_S)
        self._td_count.pack(side="right", padx=10)

        ctk.CTkButton(
            th, text=T("delete"), width=70, height=30,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#EF4444", "#DC2626"), hover_color="#B91C1C",
            corner_radius=8, command=self._delete_sel
        ).pack(side="right", pady=10)

        ctk.CTkButton(
            th, text="✎  Edit", width=80, height=30,
            font=("Segoe UI", 11, "bold"),
            fg_color="#B45309", hover_color="#92400E",
            text_color="white", corner_radius=8,
            command=self._open_edit
        ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            th, text=T("add"), width=90, height=30,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0"),
            corner_radius=8, command=self._open_add
        ).pack(side="right", padx=6, pady=10)

        # Data table textbox
        self._data_box = ctk.CTkTextbox(
            right, font=FONT_MONO_S,
            fg_color=("#1C1030", "#FFFFFF"),
            text_color=("#EDE8F5", "#1A0A2E"),
            border_color=("#3D2260", "#C4B0DC"),
            border_width=1, corner_radius=12, wrap="none")
        self._data_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self._data_box.bind("<Button-1>", self._on_row_click)
        self._render_data()

        # Log header
        sh = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                          corner_radius=12, height=52)
        sh.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        sh.pack_propagate(False)
        mk_label(sh, T("np_journal"), color=C["muted"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=18, pady=14)
        self._status_lbl = ctk.CTkLabel(
            sh, text=T("ready"), font=("Consolas", 11, "bold"),
            text_color=("#22C55E", "#16A34A"), fg_color="#0B2210", corner_radius=8)
        self._status_lbl.pack(side="right", padx=18, pady=14)

        # Log textbox
        self._log_box = ctk.CTkTextbox(
            right, font=FONT_MONO_S, fg_color=("#1C1030", "#FFFFFF"),
            text_color=("#EDE8F5", "#1A0A2E"), border_color=("#3D2260", "#C4B0DC"),
            border_width=1, corner_radius=12, wrap="word", state="disabled")
        self._log_box.grid(row=3, column=0, sticky="nsew")
        for tag, color in [("info",    C["text"]),    ("success", C["success"]),
                           ("warning", C["warning"]), ("error",   C["error"]),
                           ("ts",      C["muted"])]:
            self._log_box.tag_config(tag, foreground=color)

        # Load saved state
        self._load_state()
        for w in [self._np_user, self._np_pass]:
            w.bind("<FocusOut>",   self._autosave)
            w.bind("<KeyRelease>", self._autosave)

    # ── Persistence ────────────────────────────────────
    def _load_state(self):
        s = load_section("planning")
        if not s:
            return
        for widget, key in [
            (self._np_user, "username"),
            (self._np_pass, "password"),
        ]:
            val = s.get(key, "")
            if val:
                widget.delete(0, "end")
                widget.insert(0, val)
        if s.get("planning_data"):
            self._data = s["planning_data"]
            self._render_data()

    def _autosave(self, *_):
        save_state("planning", {
            "username":      self._np_user.get(),
            "password":      self._np_pass.get(),
            "planning_data": self._data,
        })

    # ── Data table ─────────────────────────────────────
    def _render_data(self):
        self._data_box.configure(state="normal")
        self._data_box.delete("1.0", "end")
        self._data_box.tag_config("header",   foreground=C["muted"])
        self._data_box.tag_config("selected", background="#3D1A6B")

        hdr = (f"{'#':<3}  {'MSISDN':<12}  {'SIMCARD':<22}  "
               f"{'PLAN':<9}  {'USAGE':<6}  {'SEG':<5}  "
               f"{'PRICE':<8}  {'PUB':<4}  {'TYPE'}\n")
        self._data_box.insert("end", hdr, "header")
        self._data_box.insert("end", "─" * 96 + "\n", "header")

        for i, d in enumerate(self._data, 1):
            line = (
                f"{i:<3}  "
                f"{d.get('MSISDN',''):<12}  "
                f"{d.get('SIMCARD',''):<22}  "
                f"{d.get('PLAN_TYPE',''):<9}  "
                f"{d.get('USAGE','VOICE'):<6}  "
                f"{d.get('SEGMENT','2'):<5}  "
                f"{d.get('PRICE',''):<8}  "
                f"{d.get('PUBLIC','0'):<4}  "
                f"{d.get('NUMBER_TYPE','EXTERNAL')}\n"
            )
            self._data_box.insert(
                "end", line,
                "selected" if self._sel_row == i - 1 else "")

        self._data_box.configure(state="disabled")
        self._td_count.configure(text=f"{len(self._data)} {self._T('rows')}")

    def _on_row_click(self, event):
        idx      = int(self._data_box.index(f"@{event.x},{event.y}").split(".")[0])
        data_idx = idx - 3
        self._sel_row = data_idx if 0 <= data_idx < len(self._data) else None
        self._render_data()

    def _delete_sel(self):
        if self._sel_row is None:
            return
        del self._data[self._sel_row]
        self._sel_row = None
        self._render_data()
        self._autosave()

    def _open_add(self):
        self._open_row_dialog()

    def _open_edit(self):
        if self._sel_row is None:
            return
        self._open_row_dialog(edit_idx=self._sel_row)

    # ── Add / Edit dialog ──────────────────────────────
    def _open_row_dialog(self, edit_idx=None):
        T       = self._T
        is_edit = edit_idx is not None
        d       = self._data[edit_idx] if is_edit else {}

        dlg = ctk.CTkToplevel(self._tab)
        dlg.title("✎  Edit Row" if is_edit else "＋  Add Row")
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()
        _center_on_parent(dlg, self._tab, w=520, h=600)
        _style_dialog(dlg)

        hdr_col = "#B45309" if is_edit else "#5C2483"
        dh = ctk.CTkFrame(dlg, fg_color=hdr_col, corner_radius=0, height=52)
        dh.pack(fill="x")
        dh.pack_propagate(False)
        ctk.CTkLabel(
            dh,
            text="✎  Edit Planning Data" if is_edit else "＋  New Planning Data",
            font=("Segoe UI", 14, "bold"), text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")

        frm = ctk.CTkScrollableFrame(dlg, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12)
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Helper closures ───────────────────────────
        def _row(label):
            r = ctk.CTkFrame(frm, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(r, text=label, text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_LABEL, width=130, anchor="w").pack(side="left")
            return r

        def _entry_widget(parent_row, default="", digits_only=False, max_len=None):
            if digits_only and max_len:
                vcmd = (dlg.register(
                    lambda s, m=max_len: (s == "" or s.isdigit()) and len(s) <= m), "%P")
                e = ctk.CTkEntry(
                    parent_row,
                    fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                    text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
                    validate="key", validatecommand=vcmd)
            else:
                e = ctk.CTkEntry(
                    parent_row,
                    fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                    text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36)
            e.pack(side="left", fill="x", expand=True)
            if default:
                e.insert(0, str(default))
            return e

        def _option_widget(parent_row, values, default=""):
            var = ctk.StringVar(value=default if default in values else values[0])
            ctk.CTkOptionMenu(
                parent_row, values=values, variable=var,
                font=FONT_MONO_S,
                fg_color=("#251540", "#EDE8F5"),
                button_color=("#5C2483", "#5C2483"),
                button_hover_color=("#7C6EB0", "#7C6EB0"),
                dropdown_fg_color=("#1C1030", "#FFFFFF"),
                text_color=("#EDE8F5", "#1A0A2E"),
                dropdown_text_color="#EDE8F5",
                dropdown_hover_color="#3D2260",
            ).pack(side="left", fill="x", expand=True)
            return var

        # ── MSISDN ────────────────────────────────────
        e_msisdn = _entry_widget(_row("MSISDN"), d.get("MSISDN", ""),
                                 digits_only=True, max_len=9)

        # ── SIMCARD (prefix locked) ───────────────────
        sc_row = _row("SIMCARD")
        pfx = ctk.CTkEntry(
            sc_row, fg_color=("#3D2260", "#C4B0DC"),
            border_color=("#3D2260", "#C4B0DC"),
            text_color=("#8B75B0", "#6B5A8A"),
            font=FONT_MONO_S, height=36, width=80)
        pfx.insert(0, "8999401")
        pfx.configure(state="disabled")
        pfx.pack(side="left", padx=(0, 4))

        sc_vcmd = (dlg.register(
            lambda s: (s == "" or s.isdigit()) and len(s) <= 13), "%P")
        e_simcard = ctk.CTkEntry(
            sc_row,
            fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
            text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
            validate="key", validatecommand=sc_vcmd)
        e_simcard.pack(side="left", fill="x", expand=True)
        existing_sc = d.get("SIMCARD", "")
        e_simcard.insert(0, existing_sc[7:] if existing_sc.startswith("8999401") else existing_sc)

        # ── Plan Type ─────────────────────────────────
        v_plan = _option_widget(_row("Plan Type"),
                                ["PostPaid", "Prepaid"],
                                d.get("PLAN_TYPE", "PostPaid"))

        # ── Usage ─────────────────────────────────────
        v_usage = _option_widget(_row("Usage Type"),
                                 ["VOICE", "DATA"],
                                 d.get("USAGE", "VOICE"))

        # ── Segment ───────────────────────────────────
        seg_display = _SEGMENT_RMAP.get(d.get("SEGMENT", "2"), "B2C  (2)")
        v_seg = _option_widget(_row("Segment"),
                               list(_SEGMENT_OPTS.keys()),
                               seg_display)

        # ── Price ─────────────────────────────────────
        e_price = _entry_widget(_row("Price (qepik)"),
                                d.get("PRICE", ""),
                                digits_only=True, max_len=10)

        # ── Public ────────────────────────────────────
        pub_default = "0  (not public)" if d.get("PUBLIC", "0") == "0" else "1  (public)"
        v_public = _option_widget(_row("Public"),
                                  ["0  (not public)", "1  (public)"],
                                  pub_default)

        # ── Number Type ───────────────────────────────
        v_numtype = _option_widget(_row("Number Type"),
                                   ["EXTERNAL", "INTERNAL", "GOLDEN"],
                                   d.get("NUMBER_TYPE", "EXTERNAL"))

        # ── Description ───────────────────────────────
        e_desc = _entry_widget(_row("Description"), d.get("DESCRIPTION", ""))

        # ── Save ──────────────────────────────────────
        def save():
            msisdn = e_msisdn.get().strip()
            sc_sfx = e_simcard.get().strip()
            if not msisdn or not sc_sfx:
                return

            row_data = {
                "MSISDN":      msisdn,
                "SIMCARD":     "8999401" + sc_sfx,
                "PLAN_TYPE":   v_plan.get(),
                "USAGE":       v_usage.get(),
                "SEGMENT":     _SEGMENT_OPTS.get(v_seg.get(), "2"),
                "PRICE":       e_price.get().strip(),
                "PUBLIC":      v_public.get().split()[0],   # "0" or "1"
                "NUMBER_TYPE": v_numtype.get(),
                "DESCRIPTION": e_desc.get().strip(),
            }

            if is_edit:
                self._data[edit_idx] = row_data
            else:
                self._data.append(row_data)

            self._render_data()
            self._autosave()
            dlg.destroy()

        btn_col  = "#B45309" if is_edit else "#5C2483"
        btn_hvr  = "#92400E" if is_edit else "#7C6EB0"
        btn_text = "✎  Save Changes" if is_edit else T("save")

        ctk.CTkButton(
            dlg, text=btn_text,
            fg_color=btn_col, hover_color=btn_hvr,
            text_color="white", font=("Segoe UI", 13, "bold"),
            height=44, corner_radius=10, command=save
        ).pack(fill="x", padx=16, pady=(0, 16))

    # ── Start handler ──────────────────────────────────
    def _on_start(self):
        if self._running:
            return

        username = self._np_user.get().strip()
        password = self._np_pass.get().strip()

        # Validation
        missing = []
        if not username: missing.append("Username")
        if not password: missing.append("Password")
        if not self._data:
            self._append_log(
                datetime.now().strftime("%H:%M:%S"),
                f"⚠ Planning data is empty — {self._T('val_not_selected')}", "error")
            self._set_status(self._T("val_error_status"), C["error"], "#2A0A0A")
            return
        if missing:
            ts = datetime.now().strftime("%H:%M:%S")
            for f in missing:
                self._append_log(ts, f"⚠ '{f}' {self._T('val_not_selected')}", "error")
            self._set_status(self._T("val_error_status"), C["error"], "#2A0A0A")
            return

        self._running = True
        self._stop_ev.clear()
        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._set_status(self._T("running"), C["warning"], "#2A1A05")
        self._append_log(datetime.now().strftime("%H:%M:%S"),
                         self._T("np_started"), "warning")

        data_snapshot = deepcopy(self._data)

        def worker():
            try:
                # 1. CSV-ləri avtomatik yarat
                self._log_q.put({
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": f"📄 Generating CSVs for {len(data_snapshot)} row(s)...",
                    "level": "info", "_tab": "np"})

                plan_path, update_path, assign_path = build_csvs(data_snapshot)

                self._log_q.put({
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": "✓ CSVs generated (plain text, no quotes).",
                    "level": "success", "_tab": "np"})

                if self._stop_ev.is_set():
                    return

                # 2. Selenium işlət
                cfg = {
                    "chromedriver": "",
                    "username":     username,
                    "password":     password,
                    "plan_file":    plan_path,
                    "update_file":  update_path,
                    "assign_file":  assign_path,
                }
                run_number_planning(cfg, self._log_q, self._stop_ev)

                self._log_q.put({
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": self._T("np_done"),
                    "level": "success", "_tab": "np"})

            except Exception as e:
                self._log_q.put({
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": f"═══ ERROR: {e} ═══",
                    "level": "error", "_tab": "np"})
            finally:
                self._tab.after(0, self._on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_cancel(self):
        self._stop_ev.set()
        self._append_log(datetime.now().strftime("%H:%M:%S"),
                         self._T("cancel_msg"), "error")
        self._set_status(self._T("cancelled"), C["error"], "#2A0A0A")
        self._cancel_btn.configure(state="disabled")
        self._start_btn.configure(state="normal")
        self._running = False

    def _on_done(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        if not self._stop_ev.is_set():
            self._set_status(self._T("success_status"), C["success"], "#0B2210")

    def _set_status(self, text, color, bg):
        self._status_lbl.configure(
            text=f"  {text}  ", text_color=color, fg_color=bg)

    def append_log(self, ts, msg, level):
        self._append_log(ts, msg, level)

    def _append_log(self, ts, msg, level):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"[{ts}] ", "ts")
        self._log_box.insert("end", f"{msg}\n", level)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")