"""
tab_activation.py — Tab 2: Activation (Dealer Online — API)
PyQt6 migration — no tkinter/CTk dependencies.
Business logic (API calls, threading) is UNCHANGED.
"""
import re
import threading
import queue
from copy import deepcopy
from datetime import datetime

import requests

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QRadioButton, QButtonGroup, QScrollArea, QDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy,
    QAbstractScrollArea, QComboBox, QDialogButtonBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QSettings
from PyQt6.QtGui import QFont, QIntValidator, QColor

from config import (
    C, DEFAULT_TEST_DATA, TARIFF_TYPE_MAP, TARIFF_TYPE_RMAP, CITY_MAP,
    save_state, load_section,
)
from widgets import (
    mk_label, mk_button, mk_field, mk_password_field,
    Card, SectionHeader, Divider, PanelHeader,
    FONT_UI, FONT_UI_B, FONT_UI_S, FONT_MONO_S, FONT_LABEL,
    font,
)


# ══════════════════════════════════════════════════════
#  PIPELINE CONSTANTS  (unchanged)
# ══════════════════════════════════════════════════════
STEPS_POSTPAID = ["Login", "Check MHM", "Register"]
STEPS_PREPAID  = ["Login", "Check MHM", "Register"]

TARIFF_RCODE_MAP = {
    "371": "Yeni Her Yere",
    "939": "SuperSen 3GB",  "940": "SuperSen 6GB",
    "941": "SuperSen 10GB", "942": "SuperSen 20GB",
    "943": "SuperSen 30GB",
}
PREPAID_TARIFF_MAP = {
    "1091": "DigiMax Daily",  "1098": "DigiMax Weekly",
    "1105": "DigiMax 3GB",    "1112": "DigiMax 5GB",
    "1118": "DigiMax 10GB",   "1129": "DigiMax 25GB",
    "935":  "Travel Pack 30GB",
    "1132": "Premium+ 60GB",  "1194": "Premium+ 100GB",
}
PREPAID_TARIFF_RMAP = {v: k for k, v in PREPAID_TARIFF_MAP.items()}

POSTPAID_CODE_MAP = {v: k for k, v in TARIFF_RCODE_MAP.items()}
PREPAID_CODE_MAP  = {v: k for k, v in PREPAID_TARIFF_MAP.items()}


# ══════════════════════════════════════════════════════
#  ERROR CLEANER  (unchanged)
# ══════════════════════════════════════════════════════
def _clean_error(msg: str) -> str:
    for prefix in ("checkMHM: ", "registerCustomer failed: ", "addVoucher: "):
        if msg.startswith(prefix):
            msg = msg[len(prefix):]
    msg = re.sub(r"^\[?\d{3}\]?\s*[:\-]\s*", "", msg).strip()
    msg = re.sub(r"(\s+(500|null|None|error|Error))+\s*$", "", msg).strip()
    if not msg or re.fullmatch(r"\d{3}", msg):
        msg = "Unexpected server error"
    return msg


# ══════════════════════════════════════════════════════
#  API HELPERS  (unchanged)
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
    from requests.adapters import HTTPAdapter
    s = requests.Session()
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20,
                          max_retries=2, pool_block=False)
    s.mount("https://", adapter)
    s.mount("http://",  adapter)
    s.headers.update({
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Accept-Language":  "en-US,en;q=0.9",
        "Accept":           "text/html,application/xhtml+xml,application/xml;q=0.9,"
                            "image/avif,image/webp,image/apng,*/*;q=0.8,"
                            "application/signed-exchange;v=b3;q=0.7",
        "sec-ch-ua":        '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
    })
    s.get(f"{base_url}/login",
          headers={"Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
                   "Sec-Fetch-Site": "none", "Cache-Control": "max-age=0"},
          allow_redirects=True, timeout=20)
    login_resp = s.post(f"{base_url}/login",
                        data={"username": username, "password": password},
                        headers={"Content-Type": "application/x-www-form-urlencoded",
                                 "Origin": base_url, "Referer": f"{base_url}/login",
                                 "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
                                 "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1",
                                 "Cache-Control": "max-age=0"},
                        allow_redirects=False, timeout=20)
    location = login_resp.headers.get("Location", "")
    if login_resp.status_code in (301, 302, 303, 307, 308):
        if "/login" in location:
            raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")
        s.get(location if location.startswith("http") else f"{base_url}{location}",
              headers={"Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
                       "Sec-Fetch-Site": "same-origin"},
              allow_redirects=True, timeout=20)
    elif login_resp.status_code == 200:
        body = login_resp.text.lower()
        if "invalid" in body or "incorrect" in body or "bad credentials" in body:
            raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")
    if not s.cookies.get("SESSION"):
        raise Exception("Login failed — Sessiya yaradıla bilmədi, istifadəçi adı/şifrəni yoxlayın")
    page = s.get(f"{base_url}/customer",
                 headers={"Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
                          "Sec-Fetch-Site": "same-origin"},
                 allow_redirects=True, timeout=20)
    if "/login" in page.url:
        raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")
    csrf = _extract_csrf(page.text) or s.cookies.get("XSRF-TOKEN")
    if csrf:
        s.headers.update({"X-CSRF-TOKEN": csrf, "X-Requested-With": "XMLHttpRequest"})
    else:
        s.headers.update({"X-Requested-With": "XMLHttpRequest"})
    return s


def check_mhm(session, base_url, data):
    r = session.get(f"{base_url}/customer/checkMHM",
                    params={"documentType": "1", "documentNumber": data["DOC_NUMBER"],
                            "msisdn": data["MSISDN"], "simcard": data["SIMCARD"],
                            "customerType": data["PLAN_TYPE"], "companyVoen": "null",
                            "documentPin": data["DOC_PIN"], "requestType": data["TARIFF_TYPE"],
                            "companySun": "", "segmentType": ""},
                    headers={"Accept": "application/json, text/javascript, */*; q=0.01",
                             "Referer": f"{base_url}/customer"},
                    timeout=20)
    body = r.text.strip()
    if not body or body.startswith("<!"):
        raise Exception("checkMHM: session invalid")
    j = r.json()
    if isinstance(j, dict) and j.get("errorMessage"):
        raise Exception(f"checkMHM: {j['errorMessage']}")
    return j


def add_voucher(session, base_url, voucher, msisdn, simcard):
    r = session.get(f"{base_url}/customer/checkMHMAddVoucher",
                    params={"voucher": voucher, "msisdn": msisdn, "serial": simcard},
                    headers={"Accept": "application/json, text/javascript, */*; q=0.01",
                             "Referer": f"{base_url}/customer",
                             "X-KL-Ajax-Request": "Ajax_Request"},
                    timeout=20)
    if r.status_code == 404:
        raise Exception("addVoucher: Vauçer sistemdə tapılmadı")
    body = r.text.strip()
    if not body or body.startswith("<!"):
        raise Exception("addVoucher: session invalid")
    try:
        j = r.json()
    except Exception:
        raise Exception("addVoucher: Server returned an invalid response")
    if isinstance(j, dict):
        err = (j.get("errorMessage") or j.get("message") or
               j.get("error") or j.get("description") or j.get("detail"))
        if err and str(err).strip().lower() not in ("", "null", "none"):
            raise Exception(f"addVoucher: {err}")
        if j.get("success") is False or j.get("status") == "error":
            fallback = j.get("description") or j.get("detail") or "Vauçer sistemdə tapılmadı"
            raise Exception(f"addVoucher: {fallback}")
    return j


def register_customer(session, base_url, data, consts):
    r = session.get(f"{base_url}/customer/registerCustomer",
                    params={"country": consts["COUNTRY"], "city": consts["CITY"],
                            "zip": consts["ZIP_CODE"], "tariff": data["TARIFF"],
                            "imei": "", "msisdnDeviceType": "voice",
                            "email": consts["EMAIL"], "additionalAddress": "",
                            "additionalCity": "", "additional": "true",
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
                    headers={"Accept": "application/json",
                             "Referer": f"{base_url}/customer"},
                    timeout=30)
    try:
        j = r.json()
    except Exception:
        j = None
    if isinstance(j, dict):
        err = (j.get("errorMessage") or j.get("message") or
               j.get("error") or j.get("description") or j.get("detail"))
        if err and str(err).strip().lower() not in ("", "null", "none"):
            raise Exception(f"registerCustomer failed: {str(err).strip()}")
        if j.get("success") is False or j.get("status") == "error":
            raise Exception("registerCustomer failed: Nömrənin aktivasiyası zamanı xəta baş verdi")
    if r.status_code != 200:
        raise Exception("registerCustomer failed: Nömrənin aktivasiyası zamanı xəta baş verdi")
    return j


def run_single(data, base_url, username, password, consts, log_q, result_q, stop_ev):
    msisdn       = data["MSISDN"]
    is_prepaid   = data.get("PLAN_TYPE", "").lower() == "prepaid"
    STEPS        = STEPS_PREPAID if is_prepaid else STEPS_POSTPAID
    tariff_label = TARIFF_TYPE_RMAP.get(data["TARIFF_TYPE"], data["TARIFF_TYPE"])

    def log(step_idx, msg, level="info", done=False, error=False):
        log_q.put({"ts": datetime.now().strftime("%H:%M:%S"), "msg": msg,
                   "level": level, "msisdn": msisdn, "step": step_idx,
                   "total": len(STEPS), "done": done, "error": error,
                   "steps": STEPS})

    try:
        if stop_ev.is_set():
            return
        log(0, "Connecting to Dealer Online...")
        try:
            session = create_session(base_url, username, password)
        except requests.exceptions.ConnectionError:
            raise Exception("VPN bağlantısı yoxdur — dealer-online.azercell.com əlçatmazdır")
        except requests.exceptions.Timeout:
            raise Exception("Server cavab vermədi — VPN bağlantısını yoxlayın")
        except requests.exceptions.RequestException as e:
            if "HTTPConnectionPool" in str(e) or "ConnectionPool" in str(e):
                raise Exception("VPN bağlantısı yoxdur — dealer-online.azercell.com əlçatmazdır")
            raise

        def _cancel_hook(r, *args, **kwargs):
            if stop_ev.is_set():
                raise Exception("__CANCELLED__")
        session.hooks["response"].append(_cancel_hook)

        if stop_ev.is_set():
            return
        log(0, "Session created", "success")
        log(1, "Validating document & MHM check...")
        check_mhm(session, base_url, data)

        if stop_ev.is_set():
            return
        if is_prepaid:
            voucher = data.get("VOUCHER", "").strip()
            if not voucher:
                raise Exception("checkMHM: Prepaid aktivasiya üçün vauçer tələb olunur")
            add_voucher(session, base_url, voucher, data["MSISDN"], data["SIMCARD"])
            if stop_ev.is_set():
                return

        log(1, "MHM check passed", "success")
        log(2, "Registering customer...")
        register_customer(session, base_url, data, consts)

        if stop_ev.is_set():
            return
        log(2, "Registration complete", "success", done=True)
        result_q.put({"MSISDN": msisdn, "PLAN_TYPE": data["PLAN_TYPE"],
                      "TARIFF": data.get("TARIFF", ""),
                      "TARIFF_TYPE": tariff_label, "STATUS": "PASSED", "ERROR": ""})

    except Exception as e:
        if stop_ev.is_set() or "__CANCELLED__" in str(e):
            return
        raw = str(e)
        if "registerCustomer" in raw:
            step_idx = 2
        elif "checkMHM" in raw or "addVoucher" in raw:
            step_idx = 1
        else:
            step_idx = 0
        msg = _clean_error(raw)
        log(step_idx, msg, "error", done=True, error=True)
        result_q.put({"MSISDN": msisdn, "PLAN_TYPE": data["PLAN_TYPE"],
                      "TARIFF": data.get("TARIFF", ""),
                      "TARIFF_TYPE": tariff_label, "STATUS": "FAILED", "ERROR": msg})


# ══════════════════════════════════════════════════════
#  MSISDN CARD  (PyQt6)
# ══════════════════════════════════════════════════════
class MsisdnCard(QFrame):
    STEP_ICONS = ["🔐", "🔍", "📝", "🎟️"]

    def __init__(self, parent, msisdn, plan_type, tariff_type, index, steps=None):
        super().__init__(parent)
        self.msisdn = msisdn
        self._steps = steps or STEPS_POSTPAID
        self.setStyleSheet(f"""
            QFrame {{
                background:{C['card2']}; border-radius:12px;
                border:1px solid {C['border']};
            }}
            QLabel {{ background:transparent; border:none; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # ── Header row ─────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        badge = QLabel(str(index))
        badge.setFixedSize(26, 26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(font("Segoe UI", 12, bold=True))
        badge.setStyleSheet(
            f"background:{C['purple']}; color:white; border-radius:6px;")
        hdr.addWidget(badge)

        msisdn_lbl = QLabel(msisdn)
        msisdn_lbl.setFont(font("Consolas", 13, bold=True))
        msisdn_lbl.setStyleSheet(f"color:{C['text']};")
        hdr.addWidget(msisdn_lbl)

        meta_lbl = QLabel(f"  {plan_type}  ·  {tariff_type}")
        meta_lbl.setFont(font("Segoe UI", 12))
        meta_lbl.setStyleSheet(f"color:{C['muted']};")
        hdr.addWidget(meta_lbl)
        hdr.addStretch()

        self._badge = QLabel("  ⏳ RUNNING  ")
        self._badge.setFont(font("Segoe UI", 12, bold=True))
        self._badge.setStyleSheet(
            f"color:{C['warning']}; background:{C['bg2']}; border-radius:6px; padding:2px 6px;")
        hdr.addWidget(self._badge)

        self._ts_lbl = QLabel(datetime.now().strftime("%H:%M:%S"))
        self._ts_lbl.setFont(font("Consolas", 13))
        self._ts_lbl.setStyleSheet(f"color:{C['muted']};")
        hdr.addWidget(self._ts_lbl)
        root.addLayout(hdr)

        # ── Step progress row ───────────────────────
        steps_row = QHBoxLayout()
        steps_row.setSpacing(0)
        self._step_labels: list[tuple[QLabel, QLabel, str]] = []

        for i, name in enumerate(self._steps):
            icon_char = self.STEP_ICONS[i] if i < len(self.STEP_ICONS) else "▸"
            icon_lbl = QLabel(icon_char)
            icon_lbl.setFont(font("Segoe UI", 12))
            icon_lbl.setStyleSheet(f"color:{C['muted']};")
            steps_row.addWidget(icon_lbl)

            name_lbl = QLabel(f" {name}")
            name_lbl.setFont(font("Segoe UI", 12))
            name_lbl.setStyleSheet(f"color:{C['muted']};")
            steps_row.addWidget(name_lbl)

            if i < len(self._steps) - 1:
                arr = QLabel("  →  ")
                arr.setFont(font("Segoe UI", 12))
                arr.setStyleSheet(f"color:{C['border2']};")
                steps_row.addWidget(arr)

            self._step_labels.append((icon_lbl, name_lbl, icon_char))

        steps_row.addStretch()
        root.addLayout(steps_row)

        # ── Detail line ─────────────────────────────
        self._detail = QLabel("")
        self._detail.setFont(font("Consolas", 13))
        self._detail.setStyleSheet(f"color:{C['muted']};")
        root.addWidget(self._detail)

    def update_step(self, step_idx: int, msg: str, level: str,
                    done: bool = False, error: bool = False):
        for i, (icon, lbl, icon_char) in enumerate(self._step_labels):
            if i < step_idx:
                col = C["success"]
                icon.setText("✓")
            elif i == step_idx:
                if error:
                    col = C["error"]
                    icon.setText("✗")
                elif done:
                    col = C["success"]
                    icon.setText("✓")
                else:
                    col = C["warning"]
                    icon.setText(icon_char)
            else:
                col = C["muted"]
                icon.setText(icon_char)
            icon.setStyleSheet(f"color:{col};")
            lbl.setStyleSheet(f"color:{col};")

        color_map = {"success": C["success"], "error": C["error"],
                     "warning": C["warning"], "info": C["muted"]}
        detail_col = color_map.get(level, C["muted"])
        self._detail.setText(f"  ↳ {msg}")
        self._detail.setStyleSheet(f"color:{detail_col};")

        if done and not error:
            self.setStyleSheet(self.styleSheet().replace(
                C["border"], C["success"]))
            self._badge.setText("  ✅ PASSED  ")
            self._badge.setStyleSheet(
                f"color:{C['success']}; background:#0B2210; border-radius:6px; padding:2px 6px;")
        elif done and error:
            self.setStyleSheet(self.styleSheet().replace(
                C["border"], C["error"]))
            self._badge.setText("  ❌ FAILED  ")
            self._badge.setStyleSheet(
                f"color:{C['error']}; background:#2A0A0A; border-radius:6px; padding:2px 6px;")

        self._ts_lbl.setText(datetime.now().strftime("%H:%M:%S"))


# ══════════════════════════════════════════════════════
#  ADD / EDIT DIALOG
# ══════════════════════════════════════════════════════
class _DataDialog(QDialog):
    """Shared base for Add and Edit dialogs."""

    def __init__(self, parent, T, title: str, header_color: str,
                 initial: dict = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 600)
        self.setStyleSheet(f"QDialog {{ background:{C['bg2']}; }} "
                           f"QLabel {{ background:transparent; }}")
        self._T       = T
        self._result  = None
        self._initial = initial or {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Colored header ──────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(f"background:{header_color}; border-radius:0;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lbl = QLabel(title)
        hdr_lbl.setFont(font("Segoe UI", 14, bold=True))
        hdr_lbl.setStyleSheet("color:white; background:transparent;")
        hdr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_lay.addWidget(hdr_lbl)
        root.addWidget(hdr)

        # ── Scrollable form ─────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background:{C['card']}; border:none;")
        form_w = QWidget()
        form_w.setStyleSheet(f"background:{C['card']};")
        self._form = QVBoxLayout(form_w)
        self._form.setContentsMargins(16, 12, 16, 12)
        self._form.setSpacing(8)
        scroll.setWidget(form_w)
        root.addWidget(scroll, 1)

        self._build_form()

        # ── Save button ─────────────────────────────
        save_btn = QPushButton(T("save") if not initial else "✎  Yadda Saxla")
        save_btn.setFont(font("Segoe UI", 14, bold=True))
        save_btn.setFixedHeight(44)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:{header_color}; color:white;
                border:none; border-radius:0; font-weight:700;
            }}
            QPushButton:hover {{ opacity:0.9; }}
        """)
        save_btn.clicked.connect(self._on_save)
        root.addWidget(save_btn)

    def _field_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        lbl = QLabel(label)
        lbl.setFont(FONT_LABEL)
        lbl.setFixedWidth(130)
        lbl.setStyleSheet(f"color:{C['muted']};")
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    def _mk_entry(self, placeholder="", digits_only=False, max_len=0) -> QLineEdit:
        e = QLineEdit()
        e.setFont(FONT_MONO_S)
        e.setMinimumHeight(36)
        e.setPlaceholderText(placeholder)
        e.setStyleSheet(f"""
            QLineEdit {{
                background:{C['input']}; color:{C['text']};
                border:1px solid {C['border']}; border-radius:8px; padding:4px 10px;
            }}
            QLineEdit:focus {{ border-color:{C['accent2']}; }}
        """)
        if digits_only and max_len:
            pattern = f"\\d{{0,{max_len}}}" if max_len else "\\d*"
            e.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), e))
            e.setMaxLength(max_len)
        elif max_len:
            e.setMaxLength(max_len)
        return e

    def _mk_combo(self, values: list, current: str = "") -> QComboBox:
        cb = QComboBox()
        cb.addItems(values)
        if current in values:
            cb.setCurrentText(current)
        cb.setFont(FONT_MONO_S)
        cb.setMinimumHeight(36)
        cb.setStyleSheet(f"""
            QComboBox {{
                background:{C['input']}; color:{C['text']};
                border:1px solid {C['border']}; border-radius:8px;
                padding:4px 10px;
            }}
            QComboBox::drop-down {{ border:none; width:28px; }}
            QComboBox QAbstractItemView {{
                background:{C['card2']}; color:{C['text']};
                selection-background-color:{C['purple']};
            }}
        """)
        return cb

    def _build_form(self):
        d = self._initial

        # MSISDN
        self._e_msisdn = self._mk_entry(digits_only=True, max_len=9)
        self._e_msisdn.setText(d.get("MSISDN", ""))
        self._form.addLayout(self._field_row("MSISDN", self._e_msisdn))

        # DOC_NUMBER
        self._e_doc = self._mk_entry()
        self._e_doc.setText(d.get("DOC_NUMBER", ""))
        self._form.addLayout(self._field_row("DOC_NUMBER", self._e_doc))

        # DOC_PIN
        self._e_pin = self._mk_entry()
        self._e_pin.setText(d.get("DOC_PIN", ""))
        self._form.addLayout(self._field_row("DOC_PIN", self._e_pin))

        # SIMCARD — prefix + suffix
        sim_container = QWidget()
        sim_row = QHBoxLayout(sim_container)
        sim_row.setSpacing(6)
        prefix = QLineEdit("8999401")
        prefix.setFixedWidth(80)
        prefix.setReadOnly(True)
        prefix.setFont(FONT_MONO_S)
        prefix.setMinimumHeight(36)
        prefix.setStyleSheet(f"background:{C['border']}; color:{C['muted']}; "
                             f"border:1px solid {C['border']}; border-radius:8px; padding:4px 8px;")
        sim_row.addWidget(prefix)
        self._e_sim = self._mk_entry(digits_only=True, max_len=13)
        # Strip prefix if present
        sim_val = d.get("SIMCARD", "")
        if sim_val.startswith("8999401"):
            sim_val = sim_val[7:]
        self._e_sim.setText(sim_val)
        sim_row.addWidget(self._e_sim, 1)
        sim_lbl = QLabel("SIMCARD")
        sim_lbl.setFont(FONT_LABEL)
        sim_lbl.setFixedWidth(130)
        sim_lbl.setStyleSheet(f"color:{C['muted']};")
        sim_outer = QHBoxLayout()
        sim_outer.setSpacing(10)
        sim_outer.addWidget(sim_lbl)
        sim_outer.addLayout(sim_row, 1)
        self._form.addLayout(sim_outer)

        # PLAN_TYPE
        self._cb_plan = self._mk_combo(["PostPaid", "Prepaid"],
                                       d.get("PLAN_TYPE", "PostPaid"))
        self._form.addLayout(self._field_row("PLAN_TYPE", self._cb_plan))

        # TARIFF
        self._cb_tariff = self._mk_combo(
            list(POSTPAID_CODE_MAP.keys()),
            TARIFF_RCODE_MAP.get(d.get("TARIFF", "371"), "Yeni Her Yere"))
        self._form.addLayout(self._field_row("TARIFF", self._cb_tariff))

        # TARIFF_TYPE
        self._cb_tt = self._mk_combo(list(TARIFF_TYPE_MAP.keys()),
                                     TARIFF_TYPE_RMAP.get(d.get("TARIFF_TYPE", "flat"),
                                                          "Individual"))
        self._form.addLayout(self._field_row("TARIFF_TYPE", self._cb_tt))

        #        # VOUCHER (Prepaid only)
        self._e_voucher = self._mk_entry("13-digit voucher code",
                                         digits_only=True, max_len=13)
        self._e_voucher.setText(d.get("VOUCHER", ""))

        self._voucher_widget = QWidget()
        self._voucher_widget.setStyleSheet("background:transparent;")
        voucher_layout = QHBoxLayout(self._voucher_widget)
        voucher_layout.setContentsMargins(0, 0, 0, 0)
        voucher_layout.setSpacing(10)
        v_lbl = QLabel("VOUCHER 🎟️")
        v_lbl.setFont(FONT_LABEL)
        v_lbl.setFixedWidth(130)
        v_lbl.setStyleSheet(f"color:{C['muted']};")
        voucher_layout.addWidget(v_lbl)
        voucher_layout.addWidget(self._e_voucher, 1)
        self._form.addWidget(self._voucher_widget)

        self._voucher_widget.setVisible(
            d.get("PLAN_TYPE", "PostPaid") == "Prepaid")

        self._cb_plan.currentTextChanged.connect(self._on_plan_change)
        self._on_plan_change(self._cb_plan.currentText())

    def _on_plan_change(self, plan: str):
        is_pre = plan == "Prepaid"
        self._voucher_widget.setVisible(is_pre)
        if is_pre:
            vals = list(PREPAID_CODE_MAP.keys())
            current_tariff = PREPAID_TARIFF_MAP.get(self._initial.get("TARIFF", ""), vals[0])
        else:
            vals = list(POSTPAID_CODE_MAP.keys())
            current_tariff = TARIFF_RCODE_MAP.get(self._initial.get("TARIFF", "371"),
                                                   "Yeni Her Yere")
        self._cb_tariff.blockSignals(True)
        self._cb_tariff.clear()
        self._cb_tariff.addItems(vals)
        if current_tariff in vals:
            self._cb_tariff.setCurrentText(current_tariff)
        self._cb_tariff.blockSignals(False)

    def _on_save(self):
        msisdn = self._e_msisdn.text().strip()
        sim    = "8999401" + self._e_sim.text().strip()
        if not msisdn or not self._e_sim.text().strip():
            return
        plan = self._cb_plan.currentText()
        if plan == "Prepaid":
            tariff  = PREPAID_CODE_MAP.get(self._cb_tariff.currentText(), "1091")
            voucher = self._e_voucher.text().strip()
        else:
            tariff  = POSTPAID_CODE_MAP.get(self._cb_tariff.currentText(), "371")
            voucher = ""
        self._result = {
            "MSISDN":       msisdn,
            "SIMCARD":      sim,
            "DOC_NUMBER":   self._e_doc.text().strip(),
            "DOC_PIN":      self._e_pin.text().strip(),
            "PLAN_TYPE":    plan,
            "PLAN_TYPE_REG": plan,
            "TARIFF":       tariff,
            "TARIFF_TYPE":  TARIFF_TYPE_MAP.get(self._cb_tt.currentText(), "flat"),
            "VOUCHER":      voucher,
        }
        self.accept()

    def get_result(self):
        return self._result


# ══════════════════════════════════════════════════════
#  HISTORY DIALOG
# ══════════════════════════════════════════════════════
class _HistoryDialog(QDialog):
    HIST_PAGE_SIZE = 10

    def __init__(self, parent, T, history: list):
        super().__init__(parent)
        self.setWindowTitle("Activation History")
        self.resize(960, 640)
        self.setStyleSheet(f"QDialog {{ background:{C['bg']}; }} "
                           f"QLabel {{ background:transparent; }}")
        self._T       = T
        self._history = history
        self._page    = 1
        self._msisdn_filter  = ""
        self._tariff_filter  = "All Tariffs"
        self._plan_filter    = "All"

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self._build_filter(root)
        self._build_stats(root)
        self._build_table(root)
        self._build_pagination(root)
        self._refresh()

    def _build_filter(self, root):
        fc = QFrame()
        fc.setStyleSheet(f"background:{C['card']}; border-radius:12px;")
        fl = QGridLayout(fc)
        fl.setContentsMargins(12, 12, 12, 12)
        fl.setSpacing(10)
        fl.setColumnStretch(0, 1)
        fl.setColumnStretch(1, 1)
        fl.setColumnStretch(2, 1)

        # MSISDN
        col0 = QFrame()
        col0.setStyleSheet(f"background:{C['input']}; border-radius:10px;")
        c0l = QVBoxLayout(col0)
        c0l.setContentsMargins(10, 8, 10, 8)
        lbl0 = QLabel("📱  MSISDN")
        lbl0.setFont(font("Segoe UI", 12, bold=True))
        lbl0.setStyleSheet(f"color:{C['muted']};")
        c0l.addWidget(lbl0)
        self._flt_msisdn = QLineEdit()
        self._flt_msisdn.setPlaceholderText("Type to search...")
        self._flt_msisdn.setFont(font("Consolas", 13))
        self._flt_msisdn.setFixedHeight(36)
        self._flt_msisdn.setStyleSheet(
            f"background:{C['card']}; color:{C['text']}; "
            f"border:1px solid {C['border']}; border-radius:8px; padding:4px 8px;")
        self._flt_msisdn.textChanged.connect(lambda t: self._reset_page())
        c0l.addWidget(self._flt_msisdn)
        fl.addWidget(col0, 0, 0)

        # TARIFF
        col1 = QFrame()
        col1.setStyleSheet(f"background:{C['input']}; border-radius:10px;")
        c1l = QVBoxLayout(col1)
        c1l.setContentsMargins(10, 8, 10, 8)
        lbl1 = QLabel("📋  TARIFF")
        lbl1.setFont(font("Segoe UI", 12, bold=True))
        lbl1.setStyleSheet(f"color:{C['muted']};")
        c1l.addWidget(lbl1)
        all_tariffs = (["All Tariffs"]
                       + list(TARIFF_RCODE_MAP.values())
                       + list(PREPAID_TARIFF_MAP.values()))
        self._flt_tariff = QComboBox()
        self._flt_tariff.addItems(all_tariffs)
        self._flt_tariff.setFont(font("Consolas", 13))
        self._flt_tariff.setFixedHeight(36)
        self._flt_tariff.setStyleSheet(
            f"QComboBox {{ background:{C['card']}; color:{C['text']}; "
            f"border:1px solid {C['border']}; border-radius:8px; padding:4px 8px; }}"
            f"QComboBox QAbstractItemView {{ background:{C['card2']}; color:{C['text']}; "
            f"selection-background-color:{C['purple']}; }}")
        self._flt_tariff.currentTextChanged.connect(lambda _: self._reset_page())
        c1l.addWidget(self._flt_tariff)
        fl.addWidget(col1, 0, 1)

        # PLAN TYPE
        col2 = QFrame()
        col2.setStyleSheet(f"background:{C['input']}; border-radius:10px;")
        c2l = QVBoxLayout(col2)
        c2l.setContentsMargins(10, 8, 10, 8)
        lbl2 = QLabel("💳  PLAN TYPE")
        lbl2.setFont(font("Segoe UI", 12, bold=True))
        lbl2.setStyleSheet(f"color:{C['muted']};")
        c2l.addWidget(lbl2)
        plan_row = QHBoxLayout()
        plan_row.setSpacing(4)
        self._plan_btns = {}
        for val, lbl_txt in [("All", "All"), ("PostPaid", "PostPaid"), ("Prepaid", "Prepaid")]:
            btn = QPushButton(lbl_txt)
            btn.setFont(font("Segoe UI", 12, bold=True))
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = (val == "All")
            btn.setStyleSheet(
                f"background:{C['purple'] if is_active else C['card']}; color:white; "
                f"border:none; border-radius:7px;")
            btn.clicked.connect(lambda _, v=val: self._set_plan(v))
            plan_row.addWidget(btn)
            self._plan_btns[val] = btn
        c2l.addLayout(plan_row)
        fl.addWidget(col2, 0, 2)
        root.addWidget(fc)

    def _build_stats(self, root):
        self._stats_lbl = QLabel("")
        self._stats_lbl.setFont(font("Segoe UI", 13))
        self._stats_lbl.setStyleSheet(
            f"color:{C['muted']}; background:{C['card']}; "
            f"border-radius:10px; padding:6px 14px;")
        root.addWidget(self._stats_lbl)

    def _build_table(self, root):
        # Column header
        col_hdr = QFrame()
        col_hdr.setFixedHeight(34)
        col_hdr.setStyleSheet(
            f"background:{C['input']}; border-radius:8px;")
        ch_lay = QHBoxLayout(col_hdr)
        ch_lay.setContentsMargins(12, 0, 12, 0)
        ch_lay.setSpacing(0)
        _HDR = [("#", 32), ("Date", 80), ("Time", 76), ("MSISDN", 120),
                ("Plan", 88), ("Tariff", 130), ("Status", 110), ("Note", 0)]
        for txt, w in _HDR:
            lbl = QLabel(txt)
            lbl.setFont(font("Segoe UI", 12, bold=True))
            lbl.setStyleSheet(f"color:{C['muted']};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if w:
                lbl.setFixedWidth(w)
                ch_lay.addWidget(lbl)
            else:
                ch_lay.addWidget(lbl, 1)
        root.addWidget(col_hdr)

        # Scroll area
        self._table_scroll = QScrollArea()
        self._table_scroll.setWidgetResizable(True)
        self._table_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._table_scroll.setStyleSheet(f"background:{C['bg']}; border:none;")
        self._table_inner = QWidget()
        self._table_inner.setStyleSheet(f"background:{C['bg']};")
        self._table_layout = QVBoxLayout(self._table_inner)
        self._table_layout.setContentsMargins(0, 0, 0, 0)
        self._table_layout.setSpacing(3)
        self._table_layout.addStretch()
        self._table_scroll.setWidget(self._table_inner)
        root.addWidget(self._table_scroll, 1)

    def _build_pagination(self, root):
        self._page_bar = QHBoxLayout()
        self._page_bar.setSpacing(4)
        root.addLayout(self._page_bar)

    def _reset_page(self):
        self._page = 1
        self._refresh()

    def _set_plan(self, val: str):
        self._plan_filter = val
        for v, btn in self._plan_btns.items():
            active = (v == val)
            btn.setStyleSheet(
                f"background:{C['purple'] if active else C['card']}; color:white; "
                f"border:none; border-radius:7px;")
        self._reset_page()

    def _refresh(self):
        msisdn_q = self._flt_msisdn.text().strip()
        tariff_q = self._flt_tariff.currentText()
        plan_q   = self._plan_filter

        rows = list(self._history)
        if msisdn_q:
            rows = [r for r in rows if msisdn_q in r.get("MSISDN", "")]
        if tariff_q != "All Tariffs":
            rows = [r for r in rows
                    if TARIFF_RCODE_MAP.get(r.get("TARIFF", ""), "") == tariff_q
                    or PREPAID_TARIFF_MAP.get(r.get("TARIFF", ""), "") == tariff_q]
        if plan_q != "All":
            rows = [r for r in rows if r.get("PLAN_TYPE", "") == plan_q]

        total  = len(rows)
        passed = sum(1 for r in rows if r.get("STATUS") == "PASSED")
        failed = total - passed
        self._stats_lbl.setText(
            f"  {total} record{'s' if total != 1 else ''}  ·  ✅ {passed}  ·  ❌ {failed}")

        page_size   = self.HIST_PAGE_SIZE
        total_pages = max(1, (total + page_size - 1) // page_size)
        self._page  = max(1, min(self._page, total_pages))

        rows_rev  = list(reversed(rows))
        start     = (self._page - 1) * page_size
        page_rows = rows_rev[start:start + page_size]

        # Clear table
        while self._table_layout.count() > 1:
            item = self._table_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        if not rows:
            empty = QLabel(self._T("hist_empty"))
            empty.setFont(font("Segoe UI", 12))
            empty.setStyleSheet(f"color:{C['muted']};")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_layout.insertWidget(0, empty)
        else:
            for i, r in enumerate(page_rows, start + 1):
                ok     = r.get("STATUS") == "PASSED"
                row_bg = "#0B2210" if ok else "#2A0A0A"
                bdr    = C["success"] if ok else C["error"]

                rc = QFrame()
                rc.setStyleSheet(
                    f"QFrame {{ background:{row_bg}; border-radius:10px; "
                    f"border:1px solid {bdr}; }}"
                    f"QLabel {{ background:transparent; border:none; }}")
                rc_lay = QHBoxLayout(rc)
                rc_lay.setContentsMargins(12, 6, 12, 6)
                rc_lay.setSpacing(0)

                def _cell(txt, w=0, bold=False, color=None):
                    l = QLabel(txt)
                    l.setFont(font("Consolas" if not bold else "Segoe UI", 13, bold=bold))
                    l.setStyleSheet(f"color:{color or C['muted']};")
                    l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    if w:
                        l.setFixedWidth(w)
                        rc_lay.addWidget(l)
                    else:
                        rc_lay.addWidget(l, 1)

                date_str  = r.get("DATE", "")
                clock_str = r.get("CLOCK", "")
                if not date_str:
                    raw_time = r.get("TIME", "—")
                    parts = raw_time.split()
                    date_str  = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else raw_time
                    clock_str = parts[2] if len(parts) > 2 else ""

                tariff_code    = r.get("TARIFF", "")
                tariff_display = (TARIFF_RCODE_MAP.get(tariff_code)
                                  or PREPAID_TARIFF_MAP.get(tariff_code)
                                  or r.get("TARIFF_TYPE", "—"))

                _cell(str(i), 32)
                _cell(date_str,  80)
                _cell(clock_str, 76)
                _cell(r.get("MSISDN", "—"),     120, color=C["text"])
                _cell(r.get("PLAN_TYPE", "—"),   88)
                _cell(tariff_display,            130)
                status_lbl = QLabel("  ✅ PASSED  " if ok else "  ❌ FAILED  ")
                status_lbl.setFont(font("Segoe UI", 12, bold=True))
                status_lbl.setStyleSheet(
                    f"color:{C['success'] if ok else C['error']}; "
                    f"background:transparent;")
                status_lbl.setFixedWidth(110)
                rc_lay.addWidget(status_lbl)
                if r.get("ERROR"):
                    err_lbl = QLabel(f"↳ {r['ERROR']}")
                    err_lbl.setFont(font("Consolas", 12))
                    err_lbl.setStyleSheet(f"color:{C['error']};")
                    rc_lay.addWidget(err_lbl, 1)

                self._table_layout.insertWidget(self._table_layout.count() - 1, rc)

        # Rebuild pagination buttons
        while self._page_bar.count():
            item = self._page_bar.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        if total_pages > 1:
            self._page_bar.addStretch()

            def _page_btn(label, page, enabled):
                b = QPushButton(label)
                b.setFont(font("Segoe UI", 12, bold=True))
                b.setFixedSize(36, 28)
                b.setEnabled(enabled)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                is_cur = (label == str(self._page))
                b.setStyleSheet(
                    f"background:{C['purple'] if is_cur else C['input']}; color:white; "
                    f"border:none; border-radius:8px;")
                b.clicked.connect(lambda _, p=page: self._goto(p))
                self._page_bar.addWidget(b)

            _page_btn("←", self._page - 1, self._page > 1)
            for p in _page_window(self._page, total_pages):
                _page_btn(str(p), p, True)
            _page_btn("→", self._page + 1, self._page < total_pages)
            self._page_bar.addStretch()

    def _goto(self, page: int):
        self._page = page
        self._refresh()


def _page_window(cur, total, max_btns=7):
    if total <= max_btns:
        return list(range(1, total + 1))
    must = {1, total, cur}
    for d in (-2, -1, 1, 2):
        p = cur + d
        if 1 <= p <= total:
            must.add(p)
    result = sorted(must)
    if len(result) < max_btns:
        extras = [p for p in range(1, total + 1) if p not in must]
        for p in extras:
            result.append(p)
            if len(result) >= max_btns:
                break
        result = sorted(result)
    return result


# ══════════════════════════════════════════════════════
#  TAB 2 — PyQt6
# ══════════════════════════════════════════════════════
class TabActivation(QWidget):
    BASE_URL = "https://dealer-online.azercell.com"

    def __init__(self, log_q: queue.Queue, result_q: queue.Queue,
                 stop_ev: threading.Event, T, parent=None):
        super().__init__(parent)
        self._log_q    = log_q
        self._result_q = result_q
        self._stop_ev  = stop_ev
        self._T        = T
        self._running  = False
        self._results  = []
        self._history  = []
        self._test_data = deepcopy(DEFAULT_TEST_DATA)
        self._sel_row  = None
        self._cards: dict[str, MsisdnCard] = {}
        self._build()

    # ══════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════
    def _build(self):
        T   = self._T
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ── LEFT PANEL ────────────────────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setFixedWidth(360)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setStyleSheet(
            f"QScrollArea {{ background:{C['card']}; border:none; }}")

        left_w = QWidget()
        left_w.setStyleSheet(f"background:{C['card']};")
        left = QVBoxLayout(left_w)
        left.setContentsMargins(12, 12, 12, 12)
        left.setSpacing(6)
        left_scroll.setWidget(left_w)
        root.addWidget(left_scroll)

        # Config header
        ph = PanelHeader(T("config"))
        left.addWidget(ph)

        # Login section
        left.addWidget(SectionHeader(T("login_online")))
        url_row = QHBoxLayout()
        url_lbl = QLabel("Base URL")
        url_lbl.setFont(FONT_LABEL)
        url_lbl.setFixedWidth(130)
        url_lbl.setStyleSheet(f"color:{C['muted']};")
        url_val = QLabel("dealer-online.azercell.com")
        url_val.setFont(FONT_MONO_S)
        url_val.setStyleSheet(f"color:{C['muted']};")
        url_row.addWidget(url_lbl)
        url_row.addWidget(url_val, 1)
        left.addLayout(url_row)

        self._cred_user = mk_field(left, "Username", "ccequlamova")
        self._cred_pass = mk_password_field(left, "Password", "dealeronline")

        left.addWidget(Divider())
        left.addWidget(SectionHeader(T("constants")))

        self._c_city    = mk_field(left, "City",        "Baku",              disabled=True)
        self._c_zip     = mk_field(left, "ZIP",         "AZC1122",           disabled=True)
        self._c_imp     = mk_field(left, "Importer",    "AZERCELL",          disabled=True)
        self._c_cur     = mk_field(left, "Curator",     "TEST",              disabled=True)
        self._c_country = mk_field(left, "Country",     "AZERBAIJAN",        disabled=True)
        self._c_nat     = mk_field(left, "Nationality", "AZERBAIJAN",        disabled=True)
        self._c_ph1p    = mk_field(left, "Phone Prefix","10")
        self._c_ph1n    = mk_field(left, "Phone Number","2210462")
        self._c_email   = mk_field(left, "Email",       "sgaziyev@azercell.com")

        left.addWidget(Divider())
        left.addWidget(SectionHeader(T("exec_mode")))

        mode_frame = QFrame()
        mode_frame.setStyleSheet(
            f"background:{C['input']}; border-radius:10px;")
        mode_lay = QVBoxLayout(mode_frame)
        mode_lay.setContentsMargins(14, 6, 14, 6)
        self._mode_group = QButtonGroup(self)
        self._rb_parallel = QRadioButton(T("parallel"))
        self._rb_serial   = QRadioButton(T("serial"))
        self._rb_parallel.setChecked(True)
        for rb in (self._rb_parallel, self._rb_serial):
            rb.setFont(FONT_LABEL)
            rb.setStyleSheet(f"color:{C['text']};")
            mode_lay.addWidget(rb)
            self._mode_group.addButton(rb)
        left.addWidget(mode_frame)

        left.addWidget(Divider())
        # Buttons
        self._run_btn = mk_button(T("start"), "primary", height=46)
        self._run_btn.clicked.connect(self._on_run)
        left.addWidget(self._run_btn)

        self._cancel_btn = mk_button(T("cancel"), "danger", height=40)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        left.addWidget(self._cancel_btn)

        clear_btn = mk_button(T("clear_log"), "secondary", height=36)
        clear_btn.clicked.connect(self.clear_log)
        left.addWidget(clear_btn)
        left.addStretch()

        # ── RIGHT PANEL ──────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)
        root.addLayout(right, 1)

        # Test data header
        td_hdr = QFrame()
        td_hdr.setFixedHeight(52)
        td_hdr.setStyleSheet(
            f"background:{C['card']}; border-radius:12px;")
        tdh_lay = QHBoxLayout(td_hdr)
        tdh_lay.setContentsMargins(18, 0, 12, 0)

        td_title = QLabel(T("test_data"))
        td_title.setFont(font("Segoe UI", 14, bold=True))
        td_title.setStyleSheet(f"color:{C['muted']};")
        tdh_lay.addWidget(td_title)

        self._td_count = QLabel(f"{len(self._test_data)} {T('rows')}")
        self._td_count.setFont(FONT_MONO_S)
        self._td_count.setStyleSheet(f"color:{C['accent']};")
        tdh_lay.addWidget(self._td_count)
        tdh_lay.addStretch()

        for txt, variant, fn in [
            (T("add"),    "primary",   self._open_add),
            ("✎  Edit",  "secondary", self._open_edit),
            (T("delete"), "danger",   self._delete_sel),
        ]:
            btn = mk_button(txt, variant, height=30, min_width=70)
            btn.clicked.connect(fn)
            tdh_lay.addWidget(btn)
        right.addWidget(td_hdr)

        # Data table
        tbl_outer = QFrame()
        tbl_outer.setStyleSheet(
            f"background:{C['card']}; border-radius:12px; "
            f"border:1px solid {C['border']};")
        tbl_lay = QVBoxLayout(tbl_outer)
        tbl_lay.setContentsMargins(0, 0, 0, 0)
        tbl_lay.setSpacing(0)


        self._db_table = QTableWidget()
        self._db_table.setColumnCount(9)
        self._db_table.setHorizontalHeaderLabels(
            ["#", "MSISDN", "SIMCARD", "DOC_NO", "PIN",
             "TARIFF", "PLAN", "TYPE", "VOUCHER"])
        self._db_table.setFixedHeight(200)
        self._db_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._db_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._db_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._db_table.setAlternatingRowColors(True)
        self._db_table.verticalHeader().setVisible(False)
        self._db_table.setShowGrid(False)
        self._db_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        _hh = self._db_table.horizontalHeader()
        _hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        _hh.setStretchLastSection(True)
        for _ci, _w in enumerate([28, 100, 130, 90, 72, 140, 82, 90]):
            self._db_table.setColumnWidth(_ci, _w)
        self._db_table.setStyleSheet(
            'QTableWidget { background:' + C["card2"] + '; color:' + C["text"] + ';'
            ' border:none; font-family:Consolas; font-size:13px;'
            ' alternate-background-color:' + C["bg2"] + ';'
            ' selection-background-color:#3D1A6B; }'
            'QTableWidget::item { padding:0 6px; border:none; }'
            'QTableWidget::item:selected { background:#3D1A6B; color:' + C["accent2"] + '; }'
            'QHeaderView::section { background:' + C["input"] + '; color:' + C["muted"] + ';'
            ' font-family:Segoe UI; font-size:11px; font-weight:700;'
            ' border:none; padding:4px 6px; border-right:1px solid ' + C["border"] + '; }'
        )
        self._db_table.itemSelectionChanged.connect(self._on_table_selection)
        tbl_lay.addWidget(self._db_table)
        right.addWidget(tbl_outer)

        # Console header
        con_hdr = QFrame()
        con_hdr.setFixedHeight(52)
        con_hdr.setStyleSheet(
            f"background:{C['card']}; border-radius:12px;")
        cnh_lay = QHBoxLayout(con_hdr)
        cnh_lay.setContentsMargins(18, 0, 12, 0)
        cnh_title = QLabel("⚡  LIVE CONSOLE")
        cnh_title.setFont(font("Segoe UI", 14, bold=True))
        cnh_title.setStyleSheet(f"color:{C['muted']};")
        cnh_lay.addWidget(cnh_title)
        cnh_lay.addStretch()
        self._res_summary = QLabel("—")
        self._res_summary.setFont(FONT_MONO_S)
        self._res_summary.setStyleSheet(f"color:{C['muted']};")
        cnh_lay.addWidget(self._res_summary)
        self._progress_lbl = QLabel("")
        self._progress_lbl.setFont(FONT_MONO_S)
        self._progress_lbl.setStyleSheet(f"color:{C['accent']};")
        cnh_lay.addWidget(self._progress_lbl)
        right.addWidget(con_hdr)

        # Console scroll area
        self._console_scroll = QScrollArea()
        self._console_scroll.setWidgetResizable(True)
        self._console_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._console_scroll.setStyleSheet(
            f"QScrollArea {{ background:{C['card']}; border:1px solid {C['border']}; "
            f"border-radius:12px; }}")
        self._console_w = QWidget()
        self._console_w.setStyleSheet(f"background:{C['card']};")
        self._console_lay = QVBoxLayout(self._console_w)
        self._console_lay.setContentsMargins(8, 8, 8, 8)
        self._console_lay.setSpacing(8)
        self._console_lay.addStretch()
        self._console_scroll.setWidget(self._console_w)
        right.addWidget(self._console_scroll, 1)

        self._show_placeholder()
        self._render_data()
        self._load_state()

        # Autosave on field changes
        for w in (self._cred_user, self._cred_pass,
                  self._c_ph1p, self._c_ph1n, self._c_email):
            w.textChanged.connect(self._autosave)
        self._rb_parallel.toggled.connect(self._autosave)

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
                widget.setText(val)
        if s.get("mode") == "serial":
            self._rb_serial.setChecked(True)
        if s.get("test_data"):
            self._test_data = s["test_data"]
            self._render_data()
        if s.get("history"):
            self._history = s["history"]

    def _autosave(self, *_):
        save_state("activation", {
            "username":  self._cred_user.text(),
            "password":  self._cred_pass.text(),
            "ph1p":      self._c_ph1p.text(),
            "ph1n":      self._c_ph1n.text(),
            "email":     self._c_email.text(),
            "mode":      "parallel" if self._rb_parallel.isChecked() else "serial",
            "test_data": self._test_data,
            "history":   self._history,
        })

    # ══════════════════════════════════════════════════
    #  CONSOLE STATES
    # ══════════════════════════════════════════════════
    def _clear_console(self):
        while self._console_lay.count() > 1:
            item = self._console_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _show_placeholder(self):
        self._clear_console()
        ph = QLabel("▶  Press START to begin activation")
        ph.setFont(font("Segoe UI", 12))
        ph.setStyleSheet(f"color:{C['muted']};")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._console_lay.insertWidget(0, ph)

    def _show_summary(self):
        self._clear_console()
        T      = self._T
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")

        # Summary hero card
        hcard = QFrame()
        hcard.setStyleSheet(
            f"background:{C['purple']}; border-radius:12px; border:none;")
        hc_lay = QHBoxLayout(hcard)
        hc_lay.setContentsMargins(18, 8, 18, 8)

        title_lbl = QLabel(T("summary_title"))
        title_lbl.setFont(font("Segoe UI", 14, bold=True))
        title_lbl.setStyleSheet("color:white; background:transparent;")
        hc_lay.addWidget(title_lbl)
        hc_lay.addStretch()

        for lbl_txt, val, col in [
            (T("total"),  str(len(self._results)), "white"),
            (T("passed"), str(passed),              C["success"]),
            (T("failed"), str(failed),              C["error"] if failed else C["muted"]),
        ]:
            sf = QFrame()
            sf.setStyleSheet(
                f"background:{C['bg2']}; border-radius:8px; border:none;")
            sf_lay = QVBoxLayout(sf)
            sf_lay.setContentsMargins(14, 6, 14, 6)
            vl = QLabel(val)
            vl.setFont(font("Segoe UI", 18, bold=True))
            vl.setStyleSheet(f"color:{col};")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ll = QLabel(lbl_txt)
            ll.setFont(font("Segoe UI", 9))
            ll.setStyleSheet(f"color:{C['muted']};")
            ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sf_lay.addWidget(vl)
            sf_lay.addWidget(ll)
            hc_lay.addWidget(sf)

        self._console_lay.insertWidget(0, hcard)

        # Result rows col header
        col_hdr = QFrame()
        col_hdr.setFixedHeight(32)
        col_hdr.setStyleSheet(
            f"background:{C['input']}; border-radius:8px; border:none;")
        ch_lay = QHBoxLayout(col_hdr)
        ch_lay.setContentsMargins(12, 0, 12, 0)
        for txt, w in [("#", 32), ("MSISDN", 120), ("Plan", 90),
                       ("Type", 90), ("Status", 110), ("Note", 0)]:
            l = QLabel(txt)
            l.setFont(font("Segoe UI", 12, bold=True))
            l.setStyleSheet(f"color:{C['muted']};")
            if w:
                l.setFixedWidth(w)
                ch_lay.addWidget(l)
            else:
                ch_lay.addWidget(l, 1)
        self._console_lay.insertWidget(1, col_hdr)

        for i, r in enumerate(self._results, 1):
            ok     = r["STATUS"] == "PASSED"
            row_bg = "#0B2210" if ok else "#2A0A0A"
            bdr    = C["success"] if ok else C["error"]

            rc = QFrame()
            rc.setStyleSheet(
                f"QFrame {{ background:{row_bg}; border-radius:10px; "
                f"border:1px solid {bdr}; }}"
                f"QLabel {{ background:transparent; border:none; }}")
            rc_lay = QHBoxLayout(rc)
            rc_lay.setContentsMargins(12, 6, 12, 6)
            rc_lay.setSpacing(0)

            def _cell(txt, w=0, mono=True, color=None, bold=False):
                l = QLabel(txt)
                l.setFont(font("Consolas" if mono else "Segoe UI", 13, bold=bold))
                l.setStyleSheet(f"color:{color or C['muted']};")
                if w:
                    l.setFixedWidth(w)
                    rc_lay.addWidget(l)
                else:
                    rc_lay.addWidget(l, 1)

            _cell(str(i),           32)
            _cell(r["MSISDN"],      120, color=C["text"])
            _cell(r["PLAN_TYPE"],   90,  mono=False)
            _cell(r["TARIFF_TYPE"], 90,  mono=False)

            status = QLabel("  ✅ PASSED  " if ok else "  ❌ FAILED  ")
            status.setFont(font("Segoe UI", 12, bold=True))
            status.setStyleSheet(f"color:{C['success'] if ok else C['error']};")
            status.setFixedWidth(110)
            rc_lay.addWidget(status)

            if r["ERROR"]:
                err_l = QLabel(f"↳ {r['ERROR']}")
                err_l.setFont(font("Consolas", 12))
                err_l.setStyleSheet(f"color:{C['error']};")
                rc_lay.addWidget(err_l, 1)

            idx = self._console_lay.count() - 1
            self._console_lay.insertWidget(idx, rc)

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
        self._run_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress_lbl.setText("")
        self._res_summary.setText("—")
        self._clear_console()

        username  = self._cred_user.text().strip()
        password  = self._cred_pass.text().strip()
        consts    = self._get_consts()
        mode      = "parallel" if self._rb_parallel.isChecked() else "serial"
        data_list = deepcopy(self._test_data)

        for i, d in enumerate(data_list, 1):
            tt    = TARIFF_TYPE_RMAP.get(d["TARIFF_TYPE"], d["TARIFF_TYPE"])
            steps = STEPS_PREPAID if d.get("PLAN_TYPE", "").lower() == "prepaid" else STEPS_POSTPAID
            card  = MsisdnCard(None, d["MSISDN"], d["PLAN_TYPE"], tt, i, steps=steps)
            self._cards[d["MSISDN"]] = card
            idx = self._console_lay.count() - 1
            self._console_lay.insertWidget(idx, card)

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
            QTimer.singleShot(100, self._force_done)

        threading.Thread(target=worker, daemon=True).start()

    def _force_done(self):
        if self._stop_ev.is_set():
            return
        if self._results:
            self.on_done()
        else:
            self._running = False
            self._run_btn.setEnabled(True)
            self._cancel_btn.setEnabled(False)

    def _on_cancel(self):
        self._stop_ev.set()
        self._running = False
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

        for msisdn, card in self._cards.items():
            if "RUNNING" in card._badge.text():
                card._badge.setText("  🚫 CANCELLED  ")
                card._badge.setStyleSheet(
                    f"color:{C['error']}; background:#2A0A0A; "
                    f"border-radius:6px; padding:2px 6px;")
                card._detail.setText("  ↳ Process cancelled by user")
                card._detail.setStyleSheet(f"color:{C['error']};")

        ts = datetime.now().strftime("%H:%M:%S")
        cancel_card = QFrame()
        cancel_card.setStyleSheet(
            f"QFrame {{ background:#2A0A0A; border-radius:10px; "
            f"border:1px solid {C['error']}; }}"
            f"QLabel {{ background:transparent; border:none; }}")
        cc_lay = QHBoxLayout(cancel_card)
        cc_lbl = QLabel(f"🚫  [{ts}]  Process cancelled by user")
        cc_lbl.setFont(font("Segoe UI", 14, bold=True))
        cc_lbl.setStyleSheet(f"color:{C['error']};")
        cc_lay.addWidget(cc_lbl)
        idx = self._console_lay.count() - 1
        self._console_lay.insertWidget(idx, cancel_card)

        # Scroll to bottom
        sb = self._console_scroll.verticalScrollBar()
        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

    # ══════════════════════════════════════════════════
    #  PUBLIC API  (called from main.py poll loop)
    # ══════════════════════════════════════════════════
    def is_running(self):
        return self._running

    def collect_result(self, r):
        self._results.append(r)
        passed = sum(1 for x in self._results if x["STATUS"] == "PASSED")
        failed = sum(1 for x in self._results if x["STATUS"] == "FAILED")
        done   = len(self._results)
        self._progress_lbl.setText(f"{done} / {len(self._test_data)}")
        self._res_summary.setText(f"✅ {passed}   ❌ {failed}")
        self._res_summary.setStyleSheet(
            f"color:{C['success'] if failed == 0 else C['error']};")

    def on_done(self):
        self._running = False
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")
        for r in self._results:
            if r.get("STATUS") == "PASSED":
                entry = dict(r)
                now = datetime.now()
                entry["TIME"]  = now.strftime("%b %d  %H:%M:%S")
                entry["DATE"]  = now.strftime("%b %d")
                entry["CLOCK"] = now.strftime("%H:%M:%S")
                self._history.append(entry)
        self._show_summary()
        self._autosave()
        return passed, failed

    def append_log(self, ts, msg, level, msisdn=None, **kw):
        if not msisdn:
            return
        card = self._cards.get(msisdn)
        if not card:
            return
        card.update_step(kw.get("step", 0), msg, level,
                         done=kw.get("done", False),
                         error=kw.get("error", False))
        # Scroll console to bottom
        sb = self._console_scroll.verticalScrollBar()
        QTimer.singleShot(30, lambda: sb.setValue(sb.maximum()))

    def clear_log(self):
        self._cards.clear()
        self._results.clear()
        self._res_summary.setText("—")
        self._res_summary.setStyleSheet(f"color:{C['muted']};")
        self._progress_lbl.setText("")
        self._show_placeholder()

    def build_history_tab(self, parent_widget):
        """Open history in a QDialog window."""
        dlg = _HistoryDialog(parent_widget, self._T, self._history)
        dlg.exec()

    def _get_consts(self):
        city = self._c_city.text()
        return {
            "CITY":           CITY_MAP.get(city, city),
            "ZIP_CODE":       self._c_zip.text(),
            "IMPORTER":       self._c_imp.text(),
            "CURATOR":        self._c_cur.text(),
            "COUNTRY":        self._c_country.text(),
            "NATIONALITY":    self._c_nat.text(),
            "PHONE_1_PREFIX": self._c_ph1p.text(),
            "PHONE_1_NUMBER": self._c_ph1n.text(),
            "EMAIL":          self._c_email.text(),
        }

    # ══════════════════════════════════════════════════
    #  DATA TABLE
    # ══════════════════════════════════════════════════
    def _render_data(self):
        """Rebuild QTableWidget rows from self._test_data."""
        t = self._db_table
        t.setRowCount(0)
        for i, d in enumerate(self._test_data):
            t.insertRow(i)
            tt = TARIFF_TYPE_RMAP.get(
                d.get("TARIFF_TYPE", ""), d.get("TARIFF_TYPE", ""))
            if d.get("PLAN_TYPE", "").lower() == "prepaid":
                tr = PREPAID_TARIFF_MAP.get(
                    d.get("TARIFF", ""), d.get("TARIFF", "—"))
            else:
                tr = TARIFF_RCODE_MAP.get(
                    d.get("TARIFF", ""), d.get("TARIFF", ""))
            plan = d.get("PLAN_TYPE", "")
            vals = [
                str(i + 1),
                d.get("MSISDN", ""),
                d.get("SIMCARD", ""),
                d.get("DOC_NUMBER", ""),
                d.get("DOC_PIN", ""),
                tr, plan, tt,
                d.get("VOUCHER", ""),
            ]
            for ci, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if ci == 6:  # PLAN column
                    item.setForeground(QColor(
                        C["success"] if plan.lower() == "postpaid"
                        else C["warning"]))
                t.setItem(i, ci, item)
            t.setRowHeight(i, 34)
        self._td_count.setText(
            f"{len(self._test_data)} {self._T('rows')}")
        if self._sel_row is not None and self._sel_row < t.rowCount():
            t.selectRow(self._sel_row)

    def _on_table_selection(self):
        rows = self._db_table.selectionModel().selectedRows()
        self._sel_row = rows[0].row() if rows else None

    def _delete_sel(self):
        if self._sel_row is None:
            return
        row_idx = self._sel_row
        self._sel_row = None
        del self._test_data[row_idx]
        self._render_data()
        self._autosave()

    def _open_add(self):
        dlg = _DataDialog(self, self._T,
                          title=self._T("add_dialog"),
                          header_color=C["purple"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            if result:
                self._test_data.append(result)
                self._render_data()
                self._autosave()

    def _open_edit(self):
        if self._sel_row is None:
            return
        row_idx = self._sel_row
        dlg = _DataDialog(self, self._T,
                          title="✎  Edit Test Data",
                          header_color="#B45309",
                          initial=self._test_data[row_idx])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            if result:
                self._test_data[row_idx] = result
                self._sel_row = None
                self._render_data()
                self._autosave()