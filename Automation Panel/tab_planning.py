"""
tab_planning.py — Tab 1: Number Planning (Dealer Express — Selenium)
PyQt6 Migration — CustomTkinter → PyQt6
v6.0 — Full PyQt6 rewrite, business logic (Selenium) UNCHANGED.
"""
import os
import csv
import tempfile
import threading
import queue
from copy import deepcopy
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QHBoxLayout, QVBoxLayout, QGridLayout, QScrollArea,
    QTextEdit, QComboBox, QDialog, QSizePolicy, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QTextCursor

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import C, T, save_state, load_section
from widgets import (
    mk_label, mk_button, mk_entry, mk_combo, mk_field_row,
    mk_password_field, mk_eye_button, Card, SectionHeader, Divider, PanelHeader,
    FONT_MONO, FONT_MONO_S, FONT_LABEL, FONT_UI, FONT_UI_B,
    FONT_SECTION, font,
)


# ══════════════════════════════════════════════════════
#  CSV HEADERS  (unchanged)
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
    "B2C  (2)":     "2",
    "B2B  (1)":     "1",
    "Internal (3)": "3",
    "Guest  (4)":   "4",
}
_SEGMENT_RMAP = {v: k for k, v in _SEGMENT_OPTS.items()}

_UPDATE_TARIFFS = [
    "normal", "B2B_010_c1", "B2B_010_c2", "B2B_010_c3", "B2B_010_c4",
    "B2B_010_c5", "B2B_010_c6", "B2B_Gold", "B2B_Stndrd", "askercell",
    "azercell_test", "b2c_010", "b2c_010_prep", "b2c_010_veteran",
    "data", "data_109AZN", "data_129AZN", "data_129AZN_WTTX",
    "data_159AZN_WTTX", "data_99AZN", "data_mifi", "data_new", "data_old",
    "dovletcell", "esimesim_datafwa_devices", "gencol9",
    "unimediacell", "naxtel", "test_data_prepaid",
]


# ══════════════════════════════════════════════════════
#  CSV GENERATOR  (unchanged logic)
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

    plan_rows, update_rows, assign_rows = [], [], []

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

        plan_rows.append(  [msisdn, usage, plan_c, price, segment, simcard, public_f, numtype])
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
#  SELENIUM WORKER  (unchanged)
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

        # Step 1 — Assign to Contractor Dealer
        if stop_ev.is_set(): return
        log("🏢 Number Sales — Assigning to contractor dealer...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//li[@routerlink='/numbers']"))).click()

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
        log("  ✓ Assigned to contractor dealer (Azercell).", "success")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        # Step 2 — Number Planning
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
        log("  ✓ Planning CSV uploaded (is_public=0).")

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Plan numbers']/parent::button"))).click()
        log("  ✓ 'Plan numbers' clicked. Waiting for response...", "warning")
        wait30.until(EC.presence_of_element_located(
            (By.XPATH, "//snack-bar-container | //mat-snack-bar-container | "
                       "//div[contains(@class,'success')] | //div[contains(@class,'alert')]")))
        _wait_toast_gone(driver, wait)

        # Step 3 — Number Update
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
#  WORKER SIGNAL BRIDGE
#  (QThread alternative — uses plain thread + QTimer poll
#   same as main.py _poll mechanism, already wired up)
# ══════════════════════════════════════════════════════
class _DoneSignal(QObject):
    done = pyqtSignal()


# ══════════════════════════════════════════════════════
#  ROW DIALOG  (Add / Edit)
# ══════════════════════════════════════════════════════
class _RowDialog(QDialog):
    def __init__(self, parent, T, data: dict = None, is_edit: bool = False):
        super().__init__(parent)
        self._T      = T
        self._result = None
        self._is_edit = is_edit

        self.setWindowTitle("✎  Edit Row" if is_edit else "Add Row")
        self.setModal(True)
        self.setMinimumSize(520, 620)
        self.setMaximumWidth(560)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header banner
        hdr_frame = QFrame()
        hdr_frame.setFixedHeight(52)
        hdr_color = "#B45309" if is_edit else C["purple"]
        hdr_frame.setStyleSheet(f"background:{hdr_color};")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        hdr_lbl = QLabel("✎  Edit Planning Data" if is_edit else "New Planning Data")
        hdr_lbl.setFont(font("Segoe UI", 14, bold=True))
        hdr_lbl.setStyleSheet("color:white; background:transparent;")
        hdr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_lay.addWidget(hdr_lbl)
        root.addWidget(hdr_frame)

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_widget = QWidget()
        form_widget.setObjectName("card")
        form_lay = QVBoxLayout(form_widget)
        form_lay.setContentsMargins(20, 16, 20, 16)
        form_lay.setSpacing(10)
        scroll.setWidget(form_widget)
        root.addWidget(scroll, 1)

        d = data or {}

        from PyQt6.QtCore import QRegularExpression
        from PyQt6.QtGui import QRegularExpressionValidator

        # ── MSISDN ──
        self._e_msisdn = mk_entry(placeholder="9 digits", width=0)
        self._e_msisdn.setMaxLength(9)
        self._e_msisdn.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"\d{0,9}"), self._e_msisdn))
        self._e_msisdn.setText(d.get("MSISDN", ""))
        form_lay.addLayout(mk_field_row("MSISDN", self._e_msisdn))

        # ── SIM Card (prefix locked + suffix entry) ──
        sim_row_lbl = QLabel("SIMCARD")
        sim_row_lbl.setFont(FONT_LABEL)
        sim_row_lbl.setFixedWidth(140)
        sim_row_lbl.setStyleSheet(f"color:{C['muted']}; background:transparent;")

        pfx_lbl = QLineEdit("8999401")
        pfx_lbl.setReadOnly(True)
        pfx_lbl.setFixedWidth(78)
        pfx_lbl.setMinimumHeight(38)
        pfx_lbl.setStyleSheet(
            f"color:{C['muted']}; background:{C['bg2']}; "
            f"border:1.5px solid {C['border']}; border-radius:8px; padding:6px 8px;")
        pfx_lbl.setFont(FONT_MONO_S)

        self._e_simcard = mk_entry(placeholder="13 digits suffix", width=0)
        self._e_simcard.setMaxLength(13)
        self._e_simcard.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"\d{0,13}"), self._e_simcard))
        existing_sc = d.get("SIMCARD", "")
        self._e_simcard.setText(
            existing_sc[7:] if existing_sc.startswith("8999401") else existing_sc)

        sim_row = QHBoxLayout()
        sim_row.setSpacing(10)
        sim_row.addWidget(sim_row_lbl)
        sim_row.addWidget(pfx_lbl)
        sim_row.addWidget(self._e_simcard, 1)
        form_lay.addLayout(sim_row)

        # ── Dropdowns ──
        self._cb_plan    = mk_combo(["PostPaid", "Prepaid"], d.get("PLAN_TYPE", "PostPaid"))
        self._cb_usage   = mk_combo(["VOICE", "DATA"],       d.get("USAGE", "VOICE"))
        seg_disp = _SEGMENT_RMAP.get(d.get("SEGMENT", "2"), "B2C  (2)")
        self._cb_segment = mk_combo(list(_SEGMENT_OPTS.keys()), seg_disp)
        pub_def = "0  (not public)" if d.get("PUBLIC", "0") == "0" else "1  (public)"
        self._cb_public  = mk_combo(["0  (not public)", "1  (public)"], pub_def)
        self._cb_numtype = mk_combo(
            ["EXTERNAL", "INTERNAL", "GOLDEN"], d.get("NUMBER_TYPE", "EXTERNAL"))
        self._cb_tariff  = mk_combo(_UPDATE_TARIFFS, d.get("UPDATE_TARIFF", "normal"))

        form_lay.addLayout(mk_field_row("Plan Type",     self._cb_plan))
        form_lay.addLayout(mk_field_row("Usage Type",    self._cb_usage))
        form_lay.addLayout(mk_field_row("Segment",       self._cb_segment))

        # ── Price ──
        self._e_price = mk_entry(placeholder="qepik", width=0)
        self._e_price.setText(d.get("PRICE", ""))
        form_lay.addLayout(mk_field_row("Price (qepik)", self._e_price))

        form_lay.addLayout(mk_field_row("Public",        self._cb_public))
        form_lay.addLayout(mk_field_row("Number Type",   self._cb_numtype))

        # ── Description ──
        self._e_desc = mk_entry(placeholder="optional", width=0)
        self._e_desc.setText(d.get("DESCRIPTION", ""))
        form_lay.addLayout(mk_field_row("Description",   self._e_desc))

        form_lay.addLayout(mk_field_row("Update Tariff", self._cb_tariff))
        form_lay.addStretch()

        # ── Save button ──
        self._save_btn = QPushButton("✎  Save Changes" if is_edit else T("save"))
        self._save_btn.setFont(font("Segoe UI", 13, bold=True))
        self._save_btn.setMinimumHeight(44)
        self._hdr_color = '#B45309' if is_edit else C['purple']
        self._save_btn.setStyleSheet(
            f"background:{self._hdr_color}; color:white; border-radius:10px;")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)

        btn_wrap = QWidget()
        btn_wrap.setStyleSheet(f"background:{C['bg']};")
        btn_wrap_lay = QVBoxLayout(btn_wrap)
        btn_wrap_lay.setContentsMargins(20, 8, 20, 16)
        btn_wrap_lay.addWidget(self._save_btn)
        root.addWidget(btn_wrap)

        # ── Real-time validation ──
        self._e_msisdn.textChanged.connect(self._validate)
        self._e_simcard.textChanged.connect(self._validate)
        self._validate()

    def _validate(self):
        msisdn_ok = len(self._e_msisdn.text().strip()) == 9
        sim_ok    = len(self._e_simcard.text().strip()) == 13
        err_style = f'border:1.5px solid {C["error"]}; border-radius:8px;'
        self._e_msisdn.setStyleSheet('' if msisdn_ok else err_style)
        self._e_simcard.setStyleSheet('' if sim_ok else err_style)
        ok_color   = self._hdr_color
        dim_color  = C['border2']
        self._save_btn.setEnabled(msisdn_ok and sim_ok)
        self._save_btn.setStyleSheet(
            f"background:{ok_color if (msisdn_ok and sim_ok) else dim_color}; "
            f"color:white; border-radius:10px;")

    def _save(self):
        msisdn = self._e_msisdn.text().strip()
        sc_sfx = self._e_simcard.text().strip()
        if not msisdn or not sc_sfx:
            return
        self._result = {
            "MSISDN":        msisdn,
            "SIMCARD":       "8999401" + sc_sfx,
            "PLAN_TYPE":     self._cb_plan.currentText(),
            "USAGE":         self._cb_usage.currentText(),
            "SEGMENT":       _SEGMENT_OPTS.get(self._cb_segment.currentText(), "2"),
            "PRICE":         self._e_price.text().strip(),
            "PUBLIC":        self._cb_public.currentText().split()[0],
            "NUMBER_TYPE":   self._cb_numtype.currentText(),
            "DESCRIPTION":   self._e_desc.text().strip(),
            "UPDATE_TARIFF": self._cb_tariff.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result


# ══════════════════════════════════════════════════════
#  MAIN TAB WIDGET
# ══════════════════════════════════════════════════════


class _ClearableTable(QTableWidget):
    """QTableWidget that clears selection when clicking on empty area."""
    def mousePressEvent(self, event):
        idx = self.indexAt(event.pos())
        if not idx.isValid():
            self.clearSelection()
            self.setCurrentIndex(self.rootIndex())
        super().mousePressEvent(event)

class TabPlanning(QWidget):
    """Tab 1 — Number Planning. PyQt6 version."""

    def __init__(self, log_q: queue.Queue, T):
        super().__init__()
        self._log_q   = log_q
        self._T       = T
        self._running = False
        self._stop_ev = threading.Event()
        self._data    = []
        self._sel_row = None
        self._build()
        self._load_state()

    # ══════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════
    def _build(self):
        T = self._T

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        root.addWidget(splitter)

        # ── LEFT PANEL ────────────────────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(260)
        left_scroll.setMaximumWidth(340)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_w = QWidget()
        left_w.setObjectName("card")
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(16, 16, 16, 16)
        left_lay.setSpacing(8)
        left_scroll.setWidget(left_w)

        left_lay.addWidget(PanelHeader(T("config")))
        left_lay.addWidget(SectionHeader(T("login_express")))

        # Username
        self._np_user = mk_entry(placeholder="Username", width=0)
        self._np_user.setText("ccequlamova")
        left_lay.addLayout(mk_field_row("Username", self._np_user, label_width=80))

        # Password (with show/hide)
        pass_row = QHBoxLayout()
        pass_row.setSpacing(8)
        lbl_p = QLabel("Password")
        lbl_p.setFont(FONT_LABEL)
        lbl_p.setFixedWidth(80)
        lbl_p.setStyleSheet(f"color:{C['muted']}; background:transparent;")
        self._np_pass = mk_entry(password=True, width=0)
        self._np_pass.setText("Yltak_141012#")
        eye_btn = mk_eye_button(self._np_pass)
        pass_row.addWidget(lbl_p)
        pass_row.addWidget(self._np_pass, 1)
        pass_row.addWidget(eye_btn)
        left_lay.addLayout(pass_row)

        left_lay.addWidget(Divider())

        # CSV info card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setStyleSheet(
            f"QFrame#card {{ background:{C['card2']}; border-radius:10px; "
            f"border:1px solid {C['border']}; }}")
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(14, 10, 14, 10)
        info_lbl = QLabel(
            "📄  CSV files are generated automatically\n"
            "    from the data table on the right.\n"
            "    No manual file preparation needed.")
        info_lbl.setFont(font("Segoe UI", 10))
        info_lbl.setStyleSheet(f"color:{C['muted2']}; background:transparent;")
        info_lay.addWidget(info_lbl)
        left_lay.addWidget(info_card)

        left_lay.addWidget(Divider())

        # Buttons
        self._start_btn = mk_button(T("start"), "primary", height=46)
        self._start_btn.clicked.connect(self._on_start)
        left_lay.addWidget(self._start_btn)

        self._cancel_btn = mk_button(T("cancel"), "danger", height=40)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        left_lay.addWidget(self._cancel_btn)

        clear_btn = mk_button(T("clear_log"), "secondary", height=36)
        clear_btn.clicked.connect(self._clear_log)
        left_lay.addWidget(clear_btn)

        left_lay.addStretch()
        splitter.addWidget(left_scroll)

        # ── RIGHT PANEL ───────────────────────────────
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(12, 0, 0, 0)
        right_lay.setSpacing(8)

        # Data table header bar
        th = QFrame()
        th.setObjectName("card")
        th.setFixedHeight(52)
        th_lay = QHBoxLayout(th)
        th_lay.setContentsMargins(16, 0, 16, 0)
        th_lay.setSpacing(8)

        th_lay.addWidget(
            mk_label("PLANNING DATA", color=C["muted"], bold=True, size=11))

        self._td_count = mk_label(f"0 {T('rows')}", color=C["accent"])
        self._td_count.setFont(FONT_MONO_S)
        th_lay.addWidget(self._td_count)
        th_lay.addStretch()

        for _lbl, _fn, _oid, _ss in [
            (T("add"),    self._open_add,    "",
             f"QPushButton{{background:{C['purple']};color:#fff;border:none;"
             f"border-radius:7px;font-size:12px;font-weight:600;"
             f"padding:0 14px;height:32px;}}"
             f"QPushButton:hover{{background:{C['accent2']};}}"
             f"QPushButton:pressed{{background:{C['border2']};}}"),
            ("✎  Edit",           self._open_edit,   "",
             f"QPushButton{{background:{C['input']};color:{C['text2']};"
             f"border:1px solid {C['border']};border-radius:7px;"
             f"font-size:12px;font-weight:600;padding:0 14px;height:32px;}}"
             f"QPushButton:hover{{background:{C['card2']};border-color:{C['border2']};color:{C['text']};}}"
             f"QPushButton:pressed{{background:{C['border']};}}"),
            (f"✕  {T('delete')}", self._delete_sel,  "",
             f"QPushButton{{background:transparent;color:{C['error']};"
             f"border:1px solid {C['error']};border-radius:7px;"
             f"font-size:12px;font-weight:600;padding:0 14px;height:32px;}}"
             f"QPushButton:hover{{background:{C['error']};color:white;}}"
             f"QPushButton:pressed{{background:#B91C1C;}}"),
        ]:
            _b = QPushButton(_lbl)
            _b.setStyleSheet(_ss)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
            _b.clicked.connect(_fn)
            th_lay.addWidget(_b)

        right_lay.addWidget(th)

        # Data table — QTableWidget
        self._data_table = _ClearableTable()
        self._data_table.setColumnCount(9)
        self._data_table.setHorizontalHeaderLabels(
            ["#", "MSISDN", "SIMCARD", "PLAN",
             "USAGE", "SEG", "PRICE", "PUB", "TYPE"])
        self._data_table.setMinimumHeight(180)
        self._data_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._data_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._data_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._data_table.setAlternatingRowColors(True)
        self._data_table.verticalHeader().setVisible(False)
        self._data_table.setShowGrid(False)
        self._data_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        _phh = self._data_table.horizontalHeader()
        _phh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        _phh.setStretchLastSection(True)
        for _pci, _pw in enumerate([28, 110, 155, 80, 58, 42, 62, 36]):
            self._data_table.setColumnWidth(_pci, _pw)
        self._data_table.setStyleSheet(
            'QTableWidget { background:' + C["card2"] + '; color:' + C["text"] + ';'
            ' border:none; font-family:Consolas; font-size:12px;'
            ' alternate-background-color:' + C["bg2"] + ';'
            ' selection-background-color:transparent; }'
            'QTableWidget::item { padding:0 6px; border:none; }'
            'QTableWidget::item:selected { background:rgba(92,36,131,0.25);'
            ' color:' + C["text"] + '; border-left:2px solid ' + C["purple"] + '; }'
            'QHeaderView::section { background:' + C["input"] + '; color:' + C["muted"] + ';'
            ' font-family:Segoe UI; font-size:11px; font-weight:700;'
            ' border:none; padding:4px 6px;'
            ' border-right:1px solid ' + C["border"] + '; }'
        )
        self._data_table.itemSelectionChanged.connect(self._on_table_selection)
        right_lay.addWidget(self._data_table, 2)

        # Log header bar
        sh = QFrame()
        sh.setObjectName("card")
        sh.setFixedHeight(48)
        sh_lay = QHBoxLayout(sh)
        sh_lay.setContentsMargins(16, 0, 16, 0)
        sh_lay.addWidget(
            mk_label(T("np_journal"), color=C["muted"], bold=True, size=11))
        sh_lay.addStretch()

        self._status_lbl = QLabel(T("ready"))
        self._status_lbl.setFont(font("Consolas", 11, bold=True))
        self._status_lbl.setStyleSheet(
            f"color:{C['success']}; background:#0B2210; "
            "border-radius:8px; padding:2px 10px;")
        sh_lay.addWidget(self._status_lbl)
        right_lay.addWidget(sh)

        # Log box
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFont(FONT_MONO_S)
        self._log_box.setObjectName("logbox")
        self._log_box.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_lay.addWidget(self._log_box, 3)

        splitter.addWidget(right_w)
        splitter.setSizes([300, 700])

        # Autosave on field change
        self._np_user.textChanged.connect(self._autosave)
        self._np_pass.textChanged.connect(self._autosave)

        self._render_data()

    # ══════════════════════════════════════════════════
    #  PERSISTENCE
    # ══════════════════════════════════════════════════
    def _load_state(self):
        s = load_section("planning")
        if not s:
            return
        if s.get("username"):
            self._np_user.setText(s["username"])
        if s.get("password"):
            self._np_pass.setText(s["password"])
        if s.get("planning_data"):
            self._data = s["planning_data"]
            self._render_data()

    def _autosave(self, *_):
        save_state("planning", {
            "username":      self._np_user.text(),
            "password":      self._np_pass.text(),
            "planning_data": self._data,
        })

    # ══════════════════════════════════════════════════
    #  DATA TABLE
    # ══════════════════════════════════════════════════
    def _render_data(self):
        t = self._data_table
        t.setRowCount(0)
        for i, d in enumerate(self._data):
            t.insertRow(i)
            vals = [
                str(i + 1),
                d.get("MSISDN", ""),
                d.get("SIMCARD", ""),
                d.get("PLAN_TYPE", "PostPaid"),
                d.get("USAGE", "VOICE"),
                d.get("SEGMENT", "2"),
                d.get("PRICE", ""),
                d.get("PUBLIC", "0"),
                d.get("NUMBER_TYPE", "EXTERNAL"),
            ]
            for ci, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(i, ci, item)
            t.setRowHeight(i, 32)
        self._td_count.setText(f"{len(self._data)} {self._T('rows')}")
        if self._sel_row is not None and self._sel_row < t.rowCount():
            t.selectRow(self._sel_row)

    def _on_table_selection(self):
        rows = self._data_table.selectionModel().selectedRows()
        self._sel_row = rows[0].row() if rows else None

    def _delete_sel(self):
        if self._sel_row is None:
            return
        row_idx = self._sel_row
        self._sel_row = None
        del self._data[row_idx]
        self._render_data()
        self._autosave()

    def _open_add(self):
        self._open_row_dialog()

    def _open_edit(self):
        if self._sel_row is None:
            return
        self._open_row_dialog(edit_idx=self._sel_row)

    def _open_row_dialog(self, edit_idx=None):
        is_edit = edit_idx is not None
        row_idx = edit_idx
        d = self._data[row_idx] if is_edit else {}
        dlg = _RowDialog(self, self._T, data=d, is_edit=is_edit)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            if result:
                if is_edit:
                    self._data[row_idx] = result
                    self._sel_row = None
                else:
                    self._data.append(result)
                self._render_data()
                self._autosave()

    # ══════════════════════════════════════════════════
    #  START / CANCEL / DONE
    # ══════════════════════════════════════════════════
    def _on_start(self):
        if self._running:
            return

        username = self._np_user.text().strip()
        password = self._np_pass.text().strip()

        ts = datetime.now().strftime("%H:%M:%S")
        missing = []
        if not username: missing.append("Username")
        if not password: missing.append("Password")
        if not self._data:
            self._append_log(ts, f"⚠ Planning data is empty — {self._T('val_not_selected')}", "error")
            self._set_status(self._T("val_error_status"), C["error"], "#2A0A0A")
            return
        if missing:
            for f in missing:
                self._append_log(ts, f"⚠ '{f}' {self._T('val_not_selected')}", "error")
            self._set_status(self._T("val_error_status"), C["error"], "#2A0A0A")
            return

        self._running = True
        self._stop_ev.clear()
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._set_status(self._T("running"), C["warning"], "#2A1A05")
        self._append_log(datetime.now().strftime("%H:%M:%S"),
                         self._T("np_started"), "warning")

        data_snapshot = deepcopy(self._data)
        _sig = _DoneSignal()
        _sig.done.connect(self._on_done)

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
                cfg = {
                    "chromedriver": "",
                    "username":     username,
                    "password":     password,
                    "tariff":       _tariff,
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
                _sig.done.emit()   # thread-safe → Qt signal

        threading.Thread(target=worker, daemon=True).start()

    def _on_cancel(self):
        self._stop_ev.set()
        self._append_log(datetime.now().strftime("%H:%M:%S"),
                         self._T("cancel_msg"), "error")
        self._set_status(self._T("cancelled"), C["error"], "#2A0A0A")
        self._cancel_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        self._running = False

    def _on_done(self):
        self._running = False
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        if not self._stop_ev.is_set():
            self._set_status(self._T("success_status"), C["success"], "#0B2210")

    def _set_status(self, text: str, color: str, bg: str):
        self._status_lbl.setText(f"  {text}  ")
        self._status_lbl.setStyleSheet(
            f"color:{color}; background:{bg}; border-radius:8px; padding:2px 10px;")

    # ══════════════════════════════════════════════════
    #  LOG  (called from main.py _poll via append_log)
    # ══════════════════════════════════════════════════
    def append_log(self, ts: str, msg: str, level: str):
        self._append_log(ts, msg, level)

    def _append_log(self, ts: str, msg: str, level: str):
        _COLORS = {
            "info":    C["text"],
            "success": C["success"],
            "warning": C["warning"],
            "error":   C["error"],
        }
        cursor = self._log_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QColor(C["muted"]))
        cursor.insertText(f"[{ts}] ", fmt_ts)

        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor(_COLORS.get(level, C["text"])))
        cursor.insertText(f"{msg}\n", fmt_msg)

        self._log_box.setTextCursor(cursor)
        self._log_box.ensureCursorVisible()

    def _clear_log(self):
        self._log_box.clear()