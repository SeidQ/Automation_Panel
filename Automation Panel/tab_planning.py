"""
tab_planning.py — Tab 1: Number Planning (Dealer Express — Selenium)
v5.3 — Dropdown overlay fix: place()-based popups, no layout push.
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
#  CSV HEADERS
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

_UPDATE_TARIFFS = [
    "normal",
    "B2B_010_c1",
    "B2B_010_c2",
    "B2B_010_c3",
    "B2B_010_c4",
    "B2B_010_c5",
    "B2B_010_c6",
    "B2B_Gold",
    "B2B_Stndrd",
    "askercell",
    "azercell_test",
    "b2c_010",
    "b2c_010_prep",
    "b2c_010_veteran",
    "data",
    "data_109AZN",
    "data_129AZN",
    "data_129AZN_WTTX",
    "data_159AZN_WTTX",
    "data_99AZN",
    "data_mifi",
    "data_new",
    "data_old",
    "dovletcell",
    "esimesim_datafwa_devices",
    "gencol9",
    "unimediacell",
    "naxtel",
    "test_data_prepaid",
]


# ══════════════════════════════════════════════════════
#  CSV GENERATOR
# ══════════════════════════════════════════════════════
def _write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(rows)


def build_csvs(data_rows):
    tmp = tempfile.gettempdir()
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    plan_path   = os.path.join(tmp, f"np_planning_{ts}.csv")
    update_path = os.path.join(tmp, f"np_update_{ts}.csv")
    assign_path = os.path.join(tmp, f"np_assign_{ts}.csv")

    plan_rows   = []
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

    with open(assign_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for row in assign_rows:
            writer.writerow(row)

    return plan_path, update_path, assign_path


# ══════════════════════════════════════════════════════
#  SELENIUM WORKER
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

        if stop_ev.is_set(): return
        log("📋 Navigating to Number Planning...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//li[@routerlink='/planning']"))).click()
        if stop_ev.is_set(): return
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//div[@class='mat-radio-label-content'])[2]"))).click()
        log("  ✓ 'Preparing for resold' selected.")

        if stop_ev.is_set(): return
        fi = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@id='fileInput']")))
        driver.execute_script("arguments[0].style.display='block';", fi)
        fi.send_keys(cfg["plan_file"])
        log("  ✓ Planning CSV uploaded.")

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Plan numbers']/parent::button"))).click()
        log("  ✓ 'Plan numbers' clicked. Waiting for response...", "warning")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        if stop_ev.is_set(): return
        log("🔄 Switching to Number Update tab...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//div[@id='mat-tab-label-0-1'])"))).click()

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//mat-select[@id='mat-select-3']"))).click()
        panel = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'mat-select-panel')]")))
        driver.execute_script("arguments[0].scrollTop = 1200;", panel)

        _tariff = cfg.get("tariff", "normal")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//span[@class='mat-option-text' and normalize-space()='{_tariff}']")
        )).click()
        log(f"  ✓ '{_tariff}' tariff selected.", "success")

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
    """Dark title bar + app icon. Re-applies icon at multiple delays to
    override CTk's own after() calls that reset it to the blue default.
    Also removes the system menu so clicking the icon shows no popup."""
    import os as _os
    _ico = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo", "azercell.ico")
    _ico = _ico if _os.path.exists(_ico) else None

    def _apply():
        try:
            if _ico:
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

    # Apply immediately and then beat CTk's delayed icon-reset calls
    _apply()
    dlg.after(10,  _apply)
    dlg.after(100, _apply)
    dlg.after(300, _apply)


# ══════════════════════════════════════════════════════
#  OVERLAY DROPDOWN HELPER
#  Toplevel popup — layout-u itələmir, etibarlı açılır
# ══════════════════════════════════════════════════════
def _mk_overlay_dd(parent_row, dlg, values, default="", on_change=None):
    """
    Clean scrollable dropdown using a borderless Toplevel popup.
    Never pushes sibling widgets. Returns a StringVar.
    """
    import tkinter as tk

    val    = default if default in values else (values[0] if values else "")
    var    = ctk.StringVar(value=val)
    _popup = [None]

    # ── Trigger ──────────────────────────────────────
    trigger = ctk.CTkFrame(
        parent_row,
        fg_color="#251540",
        corner_radius=8, border_width=1,
        border_color="#5C2483",
        cursor="hand2", height=36)
    trigger.pack(side="left", fill="x", expand=True)
    trigger.pack_propagate(False)

    lbl = ctk.CTkLabel(
        trigger, text=f"  {val}",
        font=FONT_MONO_S, anchor="w",
        text_color="#EDE8F5")
    lbl.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)

    arr = ctk.CTkLabel(
        trigger, text="▾",
        font=("Segoe UI", 12),
        text_color=("#8B75B0", "#6B5A8A"), width=28)
    arr.pack(side="right", padx=(0, 6), pady=4)

    def _close():
        if _popup[0] is not None:
            try:
                _popup[0].destroy()
            except Exception:
                pass
            _popup[0] = None
        arr.configure(text="▾")

    def _select(v):
        var.set(v)
        lbl.configure(text=f"  {v}")
        _close()
        if on_change:
            on_change(v)

    def _open():
        _close()

        def _do_open():
            dlg.update_idletasks()

            # Reliable width: parent_row width minus label column
            try:
                row_w = parent_row.winfo_width()
                tw = max(row_w - 130 - 16, 140)
            except Exception:
                tw = max(trigger.winfo_width(), 140)

            rx = trigger.winfo_rootx()
            ry = trigger.winfo_rooty() + trigger.winfo_height()

            ITEM_H   = 26   # height per item
            MAX_VIS  = 7    # max visible items before scroll
            n        = len(values)
            vis      = min(n, MAX_VIS)
            popup_h  = ITEM_H * vis + 2  # +2 for border

            popup = tk.Toplevel(dlg)
            popup.wm_overrideredirect(True)
            popup.wm_geometry(f"{tw}x{popup_h}+{rx}+{ry}")
            popup.lift()
            popup.focus_set()
            popup.configure(bg="#3D2260")

            # Outer border frame
            outer = tk.Frame(popup, bg="#5C2483", bd=0)
            outer.pack(fill="both", expand=True, padx=1, pady=1)

            # Scrollable canvas
            canvas = tk.Canvas(outer, bg="#1E1035", highlightthickness=0, bd=0)
            canvas.pack(side="left", fill="both", expand=True)

            # Scrollbar — only shown when needed
            if n > MAX_VIS:
                sb = tk.Scrollbar(outer, orient="vertical",
                                  command=canvas.yview,
                                  troughcolor="#251540",
                                  bg="#5C2483", activebackground="#7C6EB0",
                                  width=8, bd=0, relief="flat",
                                  elementborderwidth=0, highlightthickness=0)
                sb.pack(side="right", fill="y")
                canvas.configure(yscrollcommand=sb.set)

            inner = tk.Frame(canvas, bg="#1E1035")
            win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_inner_cfg(e):
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfig(win_id, width=canvas.winfo_width())
            def _on_canvas_cfg(e):
                canvas.itemconfig(win_id, width=canvas.winfo_width())
            inner.bind("<Configure>", _on_inner_cfg)
            canvas.bind("<Configure>", _on_canvas_cfg)

            def _on_wheel(e):
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            canvas.bind_all("<MouseWheel>", _on_wheel)
            popup.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

            # Items
            cur = var.get()
            for v in values:
                is_sel = (v == cur)
                bg_btn = "#5C2483" if is_sel else "#1E1035"
                fg_txt = "#FFFFFF" if is_sel else "#C4B0DC"

                row = tk.Frame(inner, bg=bg_btn, cursor="hand2")
                row.pack(fill="x", pady=0)

                item_lbl = tk.Label(
                    row, text=v,
                    font=("Segoe UI", 11),
                    bg=bg_btn, fg=fg_txt,
                    anchor="w", padx=12, pady=0,
                    cursor="hand2")
                item_lbl.pack(fill="x", ipady=4)

                def _on_enter(e, r=row, l=item_lbl):
                    r.configure(bg="#3D2260")
                    l.configure(bg="#3D2260", fg="#FFFFFF")
                def _on_leave(e, r=row, l=item_lbl, s=is_sel):
                    c = "#5C2483" if s else "#1E1035"
                    r.configure(bg=c)
                    l.configure(bg=c, fg="#FFFFFF" if s else "#C4B0DC")
                def _on_click(e, v=v):
                    _select(v)

                row.bind("<Enter>", _on_enter)
                row.bind("<Leave>", _on_leave)
                row.bind("<Button-1>", _on_click)
                item_lbl.bind("<Enter>", _on_enter)
                item_lbl.bind("<Leave>", _on_leave)
                item_lbl.bind("<Button-1>", _on_click)

                # Thin separator
                sep = tk.Frame(inner, bg="#2D1A50", height=1)
                sep.pack(fill="x")

            # Close on click outside
            def _check_outside(e):
                try:
                    px, py = popup.winfo_rootx(), popup.winfo_rooty()
                    pw, ph = popup.winfo_width(), popup.winfo_height()
                    mx, my = popup.winfo_pointerx(), popup.winfo_pointery()
                    if not (px <= mx <= px + pw and py <= my <= py + ph):
                        _close()
                except Exception:
                    _close()
            popup.bind("<Leave>", _check_outside)

            _popup[0] = popup
            arr.configure(text="▴")

        dlg.after(1, _do_open)

    def _toggle(e=None):
        if _popup[0] is not None:
            _close()
        else:
            _open()

    trigger.bind("<Button-1>", lambda e: (_toggle(), "break"))
    lbl.bind("<Button-1>",     lambda e: (_toggle(), "break"))
    arr.bind("<Button-1>",     lambda e: (_toggle(), "break"))

    return var


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
        self._data    = []
        self._sel_row = None
        self._build()

    def _build(self):
        T   = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=5)
        tab.rowconfigure(0, weight=1)

        # ── LEFT panel ────────────────────────────────
        left = ctk.CTkScrollableFrame(
            tab, fg_color=("#1C1030", "#FFFFFF"), corner_radius=14,
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._left_panel = left

        mk_panel_header(left, T("config"))
        mk_section(left, T("login_express"))
        self._np_user = mk_field(left, "Username", "ccequlamova")
        self._np_pass = mk_field(left, "Password", "Yltak_141012#", show="*")
        mk_divider(left)

        info = ctk.CTkFrame(left, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        info.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(
            info,
            text="📄  CSV files are generated automatically\n"
                 "    from the data table on the right.\n"
                 "    No manual file preparation needed.",
            font=("Segoe UI", 12),
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

        # ── RIGHT panel ───────────────────────────────
        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=2)
        right.rowconfigure(3, weight=3)
        self._right_panel = right

        th = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                          corner_radius=12, height=52)
        th.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        th.pack_propagate(False)

        mk_label(th, "📋  PLANNING DATA", color=C["muted"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=18, pady=14)

        self._td_count = mk_label(
            th, f"0 {T('rows')}", color=C["accent"], font=FONT_MONO_S)
        self._td_count.pack(side="right", padx=10)

        ctk.CTkButton(
            th, text=T("delete"), width=70, height=30,
            font=("Segoe UI", 14, "bold"),
            fg_color=("#EF4444", "#DC2626"), hover_color="#B91C1C",
            corner_radius=8, command=self._delete_sel
        ).pack(side="right", pady=10)

        ctk.CTkButton(
            th, text="✎  Edit", width=80, height=30,
            font=("Segoe UI", 14, "bold"),
            fg_color="#B45309", hover_color="#92400E",
            text_color="white", corner_radius=8,
            command=self._open_edit
        ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            th, text=T("add"), width=90, height=30,
            font=("Segoe UI", 14, "bold"),
            fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0"),
            corner_radius=8, command=self._open_add
        ).pack(side="right", padx=6, pady=10)

        # ── Canvas-based data table ────────────────────
        import tkinter as _tk2

        _tbl_outer = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                                  corner_radius=12, border_width=1,
                                  border_color=("#3D2260", "#C4B0DC"))
        _tbl_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        _tbl_outer.columnconfigure(0, weight=1)
        _tbl_outer.rowconfigure(1, weight=1)

        _col_hdr = ctk.CTkFrame(_tbl_outer, fg_color=("#251540", "#DDD5EE"),
                                corner_radius=0, height=32)
        _col_hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=1, pady=(1,0))
        _col_hdr.pack_propagate(False)
        _COLS = [("#",28),("MSISDN",100),("SIMCARD",170),("PLAN",82),
                 ("USAGE",60),("SEG",44),("PRICE",70),("PUB",40),("TYPE",90),("TARIFF",0)]
        for _cn, _cw in _COLS:
            ctk.CTkLabel(_col_hdr, text=_cn, font=("Segoe UI", 12,"bold"),
                         text_color=("#8B75B0","#6B5A8A"),
                         width=_cw or 0, anchor="w").pack(
                side="left", padx=(10 if _cn=="#" else 6, 2),
                fill="x" if not _cw else None, expand=(not _cw))

        _db_canvas = _tk2.Canvas(_tbl_outer, bg="#1C1030", highlightthickness=0, bd=0)
        _db_canvas.grid(row=1, column=0, sticky="nsew")
        _db_sb = ctk.CTkScrollbar(_tbl_outer, orientation="vertical",
                                  command=_db_canvas.yview,
                                  button_color=("#3D2260","#C4B0DC"),
                                  button_hover_color=("#7C6EB0","#7C6EB0"))
        _db_sb.grid(row=1, column=1, sticky="ns", pady=(0,1))
        _db_canvas.configure(yscrollcommand=_db_sb.set)
        _db_inner = ctk.CTkFrame(_db_canvas, fg_color=("#1C1030","#FFFFFF"), corner_radius=0)
        _db_inner_id = _db_canvas.create_window((0,0), window=_db_inner, anchor="nw")
        def _db_on_inner(e=None): _db_canvas.configure(scrollregion=_db_canvas.bbox("all"))
        def _db_on_canvas(e=None): _db_canvas.itemconfig(_db_inner_id, width=_db_canvas.winfo_width())
        _db_inner.bind("<Configure>", _db_on_inner)
        _db_canvas.bind("<Configure>", _db_on_canvas)
        def _db_mw(e): _db_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        _db_canvas.bind("<MouseWheel>", _db_mw)
        _db_inner.bind("<MouseWheel>", _db_mw)

        self._data_box   = None
        self._db_canvas  = _db_canvas
        self._db_inner   = _db_inner
        self._render_data()

        sh = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                          corner_radius=12, height=52)
        sh.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        sh.pack_propagate(False)
        mk_label(sh, T("np_journal"), color=C["muted"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=18, pady=14)
        self._status_lbl = ctk.CTkLabel(
            sh, text=T("ready"), font=("Consolas", 13, "bold"),
            text_color=("#22C55E", "#16A34A"), fg_color="#0B2210", corner_radius=8)
        self._status_lbl.pack(side="right", padx=18, pady=14)

        self._log_box = ctk.CTkTextbox(
            right, font=FONT_MONO_S, fg_color=("#1C1030", "#FFFFFF"),
            text_color=("#EDE8F5", "#1A0A2E"), border_color=("#3D2260", "#C4B0DC"),
            border_width=1, corner_radius=12, wrap="word", state="disabled")
        self._log_box.grid(row=3, column=0, sticky="nsew")
        for tag, color in [("info",    C["text"]),    ("success", C["success"]),
                           ("warning", C["warning"]), ("error",   C["error"]),
                           ("ts",      C["muted"])]:
            self._log_box.tag_config(tag, foreground=color)

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
        if not hasattr(self, "_db_inner") or self._db_inner is None:
            return
        import tkinter as _tk3
        import customtkinter as _ctk

        for w in self._db_inner.winfo_children():
            w.destroy()
        if hasattr(self, "_db_canvas"):
            self._db_canvas.yview_moveto(0)

        self._db_rows = []
        COL_W = [28, 100, 170, 82, 60, 44, 70, 40, 90, 0]
        muted = ("#8B75B0","#6B5A8A")

        for i, d in enumerate(self._data):
            if i > 0:
                _tk3.Frame(self._db_inner, bg="#2A1A45", height=1).pack(fill="x")

            is_even = (i % 2 == 0)
            norm_bg = "#1C1030" if is_even else "#160C28"

            plan     = d.get("PLAN_TYPE","")
            plan_clr = ("#22C55E","#16A34A") if plan.lower()=="postpaid" else ("#F59E0B","#D97706")

            rc = _ctk.CTkFrame(self._db_inner, fg_color=norm_bg,
                               corner_radius=0, height=38)
            rc.pack(fill="x")
            rc.pack_propagate(False)

            cells = [
                (str(i+1),                        COL_W[0], ("Consolas", 13),        muted),
                (d.get("MSISDN",""),               COL_W[1], ("Consolas", 13,"bold"), ("#EDE8F5","#1A0A2E")),
                (d.get("SIMCARD",""),              COL_W[2], ("Consolas", 13),        muted),
                (plan,                             COL_W[3], ("Consolas", 13,"bold"), plan_clr),
                (d.get("USAGE","VOICE"),           COL_W[4], ("Consolas", 13),        muted),
                (d.get("SEGMENT","2"),             COL_W[5], ("Consolas", 13),        muted),
                (d.get("PRICE",""),                COL_W[6], ("Consolas", 13),        muted),
                (d.get("PUBLIC","0"),              COL_W[7], ("Consolas", 13),        muted),
                (d.get("NUMBER_TYPE","EXTERNAL"),  COL_W[8], ("Consolas", 13),        muted),
                (d.get("UPDATE_TARIFF","normal"),  COL_W[9], ("Consolas", 13),        ("#EDE8F5","#1A0A2E")),
            ]

            lbls = []
            for ci, (val, cw, fnt, clr) in enumerate(cells):
                px = (10, 2) if ci == 0 else (6, 2)
                lbl = _ctk.CTkLabel(rc, text=val, font=fnt, text_color=clr,
                                    width=cw or 0, anchor="w")
                lbl.pack(side="left", padx=px,
                         fill="x" if not cw else None, expand=(not cw))
                lbls.append(lbl)

            self._db_rows.append((rc, norm_bg, lbls))

            def _bind_row(widget, idx=i):
                widget.bind("<Button-1>",
                            lambda e, x=idx: self._on_row_click_idx(x))
                widget.bind("<MouseWheel>",
                            lambda e: self._db_canvas.yview_scroll(
                                int(-1*(e.delta/120)), "units"))
            _bind_row(rc)
            for lbl in lbls:
                _bind_row(lbl)

        self._td_count.configure(text=f"{len(self._data)} {self._T('rows')}")
        self._apply_row_selection()

    def _apply_row_selection(self):
        if not hasattr(self, "_db_rows"):
            return
        for i, (rc, norm_bg, lbls) in enumerate(self._db_rows):
            is_sel = (self._sel_row == i)
            try:
                rc.configure(fg_color="#3D1A6B" if is_sel else norm_bg)
                lbls[1].configure(text_color=("#C4B0DC","#1A0A2E") if is_sel else ("#EDE8F5","#1A0A2E"))
                lbls[9].configure(text_color=("#C4B0DC","#1A0A2E") if is_sel else ("#EDE8F5","#1A0A2E"))
            except Exception:
                pass

    def _on_row_click(self, event):
        pass  # legacy

    def _on_row_click_idx(self, idx):
        self._sel_row = idx if 0 <= idx < len(self._data) else None
        self._apply_row_selection()

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
        dlg.title("")
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()

        # ── Restore saved geometry ──
        _section_key = "np_edit_dialog_window" if is_edit else "np_add_dialog_window"
        _dlg_win = load_section(_section_key)
        _dlg_restored = False
        if _dlg_win:
            try:
                _geo = _dlg_win.get("geometry", "")
                if _geo:
                    dlg.geometry(_geo)
                    _dlg_restored = True
            except Exception:
                pass
        if not _dlg_restored:
            _center_on_parent(dlg, self._tab, w=520, h=680)

        _style_dialog(dlg)

        # ── Restore maximized state ──
        if _dlg_win and _dlg_win.get("maximized"):
            dlg.after(150, lambda: dlg.state("zoomed"))

        # ── Save geometry on move/resize (debounced 600ms) ──
        _geo_save_id = [None]
        _last_normal_geo = [dlg.geometry()]

        def _dlg_save_state():
            try:
                is_max = dlg.state() == "zoomed"
                geo = _last_normal_geo[0] if is_max else dlg.geometry()
                if not is_max:
                    _last_normal_geo[0] = geo
                save_state(_section_key, {"geometry": geo, "maximized": is_max})
            except Exception:
                pass

        def _dlg_on_configure(event=None):
            try:
                if dlg.state() != "zoomed":
                    _last_normal_geo[0] = dlg.geometry()
            except Exception:
                pass
            if _geo_save_id[0] is not None:
                dlg.after_cancel(_geo_save_id[0])
            _geo_save_id[0] = dlg.after(600, _dlg_save_state)

        dlg.bind("<Configure>", _dlg_on_configure)

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

        e_msisdn  = _entry_widget(_row("MSISDN"), d.get("MSISDN", ""),
                                  digits_only=True, max_len=9)

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

        # All overlay dropdowns — no pack-push problem
        v_plan    = _mk_overlay_dd(_row("Plan Type"),
                                   dlg,
                                   ["PostPaid", "Prepaid"],
                                   d.get("PLAN_TYPE", "PostPaid"))
        v_usage   = _mk_overlay_dd(_row("Usage Type"),
                                   dlg,
                                   ["VOICE", "DATA"],
                                   d.get("USAGE", "VOICE"))
        seg_disp  = _SEGMENT_RMAP.get(d.get("SEGMENT", "2"), "B2C  (2)")
        v_seg     = _mk_overlay_dd(_row("Segment"),
                                   dlg,
                                   list(_SEGMENT_OPTS.keys()), seg_disp)
        e_price   = _entry_widget(_row("Price (qepik)"),
                                  d.get("PRICE", ""), digits_only=True, max_len=10)
        pub_def   = "Not Public" if d.get("PUBLIC", "0") == "0" else "Public"
        v_public = _mk_overlay_dd(_row("Public"),
                                  dlg,
                                  ["Not Public", "Public"], pub_def)
        v_numtype = _mk_overlay_dd(_row("Number Type"),
                                   dlg,
                                   ["EXTERNAL", "INTERNAL", "GOLDEN"],
                                   d.get("NUMBER_TYPE", "EXTERNAL"))
        e_desc    = _entry_widget(_row("Description"), d.get("DESCRIPTION", ""))

        # ── Update Tariff — overlay dropdown ──────────
        v_tariff  = _mk_overlay_dd(_row("Update Tariff"),
                                   dlg,
                                   _UPDATE_TARIFFS,
                                   d.get("UPDATE_TARIFF", "normal"))

        # ── Save ──────────────────────────────────────
        def save():
            msisdn = e_msisdn.get().strip()
            sc_sfx = e_simcard.get().strip()
            if not msisdn or not sc_sfx:
                return
            row_data = {
                "MSISDN":        msisdn,
                "SIMCARD":       "8999401" + sc_sfx,
                "PLAN_TYPE":     v_plan.get(),
                "USAGE":         v_usage.get(),
                "SEGMENT":       _SEGMENT_OPTS.get(v_seg.get(), "2"),
                "PRICE":         e_price.get().strip(),
                "PUBLIC":        "0" if v_public.get() == "Not Public" else "1",
                "NUMBER_TYPE":   v_numtype.get(),
                "DESCRIPTION":   e_desc.get().strip(),
                "UPDATE_TARIFF": v_tariff.get(),
            }
            if is_edit:
                self._data[edit_idx] = row_data
            else:
                self._data.append(row_data)
            self._render_data()
            self._autosave()
            dlg.destroy()

        ctk.CTkButton(
            dlg,
            text="✎  Save Changes" if is_edit else T("save"),
            fg_color="#B45309" if is_edit else "#5C2483",
            hover_color="#92400E" if is_edit else "#7C6EB0",
            text_color="white", font=("Segoe UI", 14, "bold"),
            height=44, corner_radius=10, command=save
        ).pack(fill="x", padx=16, pady=(0, 16))

    # ── Start / Cancel / Done ──────────────────────────
    def _on_start(self):
        if self._running:
            return

        username = self._np_user.get().strip()
        password = self._np_pass.get().strip()

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

                _tariff = data_snapshot[0].get("UPDATE_TARIFF", "normal") if data_snapshot else "normal"
                run_cfg = {
                    "chromedriver": "",
                    "username":     username,
                    "password":     password,
                    "tariff":       _tariff,
                    "plan_file":    plan_path,
                    "update_file":  update_path,
                    "assign_file":  assign_path,
                }
                run_number_planning(run_cfg, self._log_q, self._stop_ev)

                self._log_q.put({
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": self._T("np_done"),
                    "level": "success", "_tab": "np"})

            except Exception as e:
                if self._stop_ev.is_set():
                    # Already handled by _on_cancel — just clean up
                    pass
                else:
                    self._log_q.put({
                        "ts": datetime.now().strftime("%H:%M:%S"),
                        "msg": f"═══ ERROR: {e} ═══",
                        "level": "error", "_tab": "np"})
            finally:
                self._tab.after(0, self._on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_cancel(self):
        self._stop_ev.set()
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_log(ts, self._T("cancel_msg"), "error")
        self._set_status(self._T("cancelled"), C["error"], "#2A0A0A")
        self._cancel_btn.configure(state="disabled")
        self._start_btn.configure(state="normal")
        self._running = False

    def _on_done(self):
        # If user cancelled, don't override the cancelled status
        if self._stop_ev.is_set():
            self._running = False
            self._start_btn.configure(state="normal")
            self._cancel_btn.configure(state="disabled")
            return
        self._running = False
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
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