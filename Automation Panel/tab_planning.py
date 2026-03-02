"""
tab_planning.py — Tab 1: Number Planning (Dealer Express — Selenium)
All time.sleep() replaced with explicit WebDriverWait conditions.
"""
import os
import threading
import queue
from datetime import datetime

import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import C, FONT_UI, FONT_UI_B, FONT_MONO_S, FONT_SECTION
from config import save_state, load_section
from widgets import mk_section, mk_field, mk_file_field, mk_divider, mk_panel_header, mk_label


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
    """Wait until any loading overlay / spinner disappears (if present)."""
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
    # Two wait instances: normal (15 s) and slow (30 s) for uploads/heavy ops
    wait   = WebDriverWait(driver, 15)
    wait30 = WebDriverWait(driver, 30)

    try:
        # ── Login ─────────────────────────────────────
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

        # Wait for redirect to dealer express (URL changes)
        wait30.until(EC.url_contains("dealerexpress.azercell.com"))
        log("✓ Login successful.", "success")

        # ── Step 1 — Number Planning ──────────────────
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
        log(f"  ✓ File uploaded: {cfg['plan_file']}")

        plan_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Plan numbers']/parent::button")))
        plan_btn.click()
        log("  ✓ 'Plan numbers' clicked. Waiting for response...", "warning")

        # Wait for success/error notification instead of fixed sleep
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        # ── Step 2 — Number Update ────────────────────
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
        log(f"  ✓ File uploaded: {cfg['update_file']}")

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

        # Wait for confirmation
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


# ══════════════════════════════════════════════════════
#  TAB 1 UI CLASS
# ══════════════════════════════════════════════════════
class TabPlanning:
    """Builds and owns Tab 1 — Number Planning."""

    def __init__(self, tab, log_q: queue.Queue, T):
        self._tab      = tab
        self._log_q    = log_q
        self._T        = T
        self._running  = False
        self._stop_ev  = threading.Event()
        self._build()

    # ── Build ──────────────────────────────────────────
    def _build(self):
        T = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=5)
        tab.rowconfigure(0, weight=1)

        # Left panel
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

        mk_section(left, T("files"))
        self._np_plan_file = mk_file_field(left, "Planning File")
        self._np_update_file = mk_file_field(left, "Update File")
        self._np_assign_file = mk_file_field(left, "Assign File")
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

        ctk.CTkButton(bf, text=T("clear_log"), font=FONT_UI,
                      fg_color=("#251540", "#EDE8F5"), hover_color=("#3D2260", "#C4B0DC"),
                      text_color=("#8B75B0", "#6B5A8A"), height=36, corner_radius=10,
                      command=self._clear_log).pack(fill="x")

        # Right log panel
        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        sh = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12, height=52)
        sh.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        sh.pack_propagate(False)
        mk_label(sh, T("np_journal"), color=C["muted"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=18, pady=14)
        self._status_lbl = ctk.CTkLabel(
            sh, text=T("ready"), font=("Consolas", 11, "bold"),
            text_color=("#22C55E", "#16A34A"), fg_color="#0B2210", corner_radius=8)
        self._status_lbl.pack(side="right", padx=18, pady=14)

        self._log_box = ctk.CTkTextbox(
            right, font=FONT_MONO_S, fg_color=("#1C1030", "#FFFFFF"),
            text_color=("#EDE8F5", "#1A0A2E"), border_color=("#3D2260", "#C4B0DC"),
            border_width=1, corner_radius=12, wrap="word", state="disabled")
        self._log_box.grid(row=1, column=0, sticky="nsew")
        for tag, color in [("info", C["text"]), ("success", C["success"]),
                           ("warning", C["warning"]), ("error", C["error"]),
                           ("ts", C["muted"])]:
            self._log_box.tag_config(tag, foreground=color)


        # Load saved state and bind autosave
        self._load_state()
        for w in [self._np_user, self._np_pass,
                  self._np_plan_file, self._np_update_file, self._np_assign_file]:
            w.bind("<FocusOut>", self._autosave)
            w.bind("<KeyRelease>", self._autosave)

    # ── Persistence ────────────────────────────────────
    def _load_state(self):
        s = load_section("planning")
        if not s:
            return
        for widget, key in [
            (self._np_user,        "username"),
            (self._np_pass,        "password"),
            (self._np_plan_file,   "plan_file"),
            (self._np_update_file, "update_file"),
            (self._np_assign_file, "assign_file"),
        ]:
            val = s.get(key, "")
            if val:
                widget.delete(0, "end")
                widget.insert(0, val)

    def _autosave(self, *_):
        save_state("planning", {
            "username":    self._np_user.get(),
            "password":    self._np_pass.get(),
            "plan_file":   self._np_plan_file.get(),
            "update_file": self._np_update_file.get(),
            "assign_file": self._np_assign_file.get(),
        })

    # ── Handlers ──────────────────────────────────────
    def _on_start(self):
        if self._running:
            return
        self._running = True
        self._stop_ev.clear()
        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._set_status(self._T("running"), C["warning"], "#2A1A05")
        self._append_log(datetime.now().strftime("%H:%M:%S"),
                         self._T("np_started"), "warning")

        cfg = {
            "chromedriver": "",
            "username":     self._np_user.get().strip(),
            "password":     self._np_pass.get().strip(),
            "plan_file":    self._np_plan_file.get().strip(),
            "update_file":  self._np_update_file.get().strip(),
            "assign_file":  self._np_assign_file.get().strip(),
        }

        def worker():
            try:
                run_number_planning(cfg, self._log_q, self._stop_ev)
                self._log_q.put({"ts": datetime.now().strftime("%H:%M:%S"),
                                 "msg": self._T("np_done"),
                                 "level": "success", "_tab": "np"})
            except Exception as e:
                self._log_q.put({"ts": datetime.now().strftime("%H:%M:%S"),
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