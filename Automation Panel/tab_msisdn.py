"""
tab_msisdn.py — Tab 3: MSISDN Details (SFA API)
PyQt6 migration — no tkinter/CTk dependencies
"""
import threading
import requests

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QFrame, QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QFont

from config import (
    C, MSISDN_FIELD_META, MSISDN_GROUPS,
    STATUS_MAP, SIM_STATUS_MAP, PAYMENT_MAP,
)

SFA_BASE_URL = "http://sfa-api.appazercell.prod/api/v1"
SFA_AUTH     = "Basic bmV3Y3VzdG9tZXI6cmVtb3RzdWN3ZW4="


# ══════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════
def _font(family="Segoe UI", size=13, bold=False) -> QFont:
    f = QFont(family, size)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    return f

FONT_MONO_S = _font("Consolas", 12)
FONT_UI     = _font("Segoe UI", 13)
FONT_UI_B   = _font("Segoe UI", 13, bold=True)
FONT_UI_S   = _font("Segoe UI", 11)
FONT_UI_XS  = _font("Segoe UI", 10)
FONT_HEAD   = _font("Consolas", 22, bold=True)
FONT_ICON   = _font("Segoe UI", 32)


# ══════════════════════════════════════════════════════
#  API  (unchanged)
# ══════════════════════════════════════════════════════
def _is_simcard_number(value: str) -> bool:
    """Heuristic: SIM/ICC numbers are typically 18-22 digits long."""
    return value.isdigit() and 18 <= len(value) <= 22


def fetch_msisdn_details(msisdn):
    """Returns (data_dict, None) on success or (None, error_str) on failure."""
    try:
        r = requests.get(
            f"{SFA_BASE_URL}/msisdn-details",
            params={"msisdn": msisdn.strip()},
            headers={"Authorization": SFA_AUTH,
                     "Accept": "application/json",
                     "User-Agent": "AzercellAutomationPanel/5.0"},
            timeout=15,
        )
        if r.status_code == 404:
            return None, f"MSISDN not found: {msisdn}"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:200]}"
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Connection error — check network / VPN access to SFA API"
    except requests.exceptions.Timeout:
        return None, "Request timed out (15 s)"
    except Exception as e:
        return None, str(e)


def fetch_simcard_details(number):
    """Fetch SIM card details by ICC number. Returns (data_dict, None) or (None, error_str)."""
    try:
        r = requests.get(
            f"{SFA_BASE_URL}/simcard",
            params={"number": number.strip()},
            headers={"Authorization": SFA_AUTH,
                     "Accept": "application/json",
                     "User-Agent": "AzercellAutomationPanel/5.0"},
            timeout=15,
        )
        if r.status_code == 404:
            return None, f"SIM card not found: {number}"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:200]}"
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Connection error — check network / VPN access to SFA API"
    except requests.exceptions.Timeout:
        return None, "Request timed out (15 s)"
    except Exception as e:
        return None, str(e)


def fetch_auto(query: str):
    """
    Auto-detect input type:
      • 18-22 digit string  →  SIM card lookup
      • anything else       →  MSISDN lookup
    Returns (data_dict, None, source_label) or (None, error_str, source_label).
    """
    if _is_simcard_number(query):
        data, err = fetch_simcard_details(query)
        return data, err, "SIM"
    else:
        data, err = fetch_msisdn_details(query)
        return data, err, "MSISDN"


# ══════════════════════════════════════════════════════
#  WORKER THREAD
# ══════════════════════════════════════════════════════
class _FetchWorker(QObject):
    """Runs the API call in a background thread; emits result via signal."""
    finished = pyqtSignal(object, object, str)   # data, err, source

    def __init__(self, query: str):
        super().__init__()
        self._query = query

    def run(self):
        data, err, source = fetch_auto(self._query)
        self.finished.emit(data, err, source)


# ══════════════════════════════════════════════════════
#  SMALL UI HELPERS
# ══════════════════════════════════════════════════════
def _lbl(text: str, font_=None, color: str = None,
         align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    w = QLabel(text)
    w.setFont(font_ or FONT_UI)
    w.setAlignment(align)
    col = color or C["text"]
    w.setStyleSheet(f"color:{col}; background:transparent;")
    return w


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"color:{C['border2']};")
    return line


# ══════════════════════════════════════════════════════
#  TAB 3 — PyQt6 implementation
# ══════════════════════════════════════════════════════
class TabMSISDN(QWidget):
    """Tab 3 — MSISDN / SIM Details.

    Usage in main.py:
        self._tab_ms = TabMSISDN(T)
        tab_widget.addTab(self._tab_ms, T("tab_msisdn"))
    """

    # Layout: which group goes in which column / grid row
    _COL = {"identity": 0, "status": 1, "dealer": 2,
            "security": 0, "financial": 1, "misc": 2}
    _ROW = {"identity": 0, "status": 0, "dealer": 0,
            "security": 1, "financial": 1, "misc": 1}

    def __init__(self, T, parent=None):
        super().__init__(parent)
        self._T      = T
        self._data   = None
        self._source = None   # "MSISDN" or "SIM"
        self._thread = None
        self._worker = None
        self._build()

    # ── Build ──────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ── Search bar card ──────────────────────────
        search_card = QFrame()
        search_card.setObjectName("card")
        search_card.setFixedHeight(52)
        search_card.setStyleSheet(
            f"background:{C['card']}; border-radius:12px;")

        sc_lay = QHBoxLayout(search_card)
        sc_lay.setContentsMargins(16, 0, 12, 0)
        sc_lay.setSpacing(10)

        title_lbl = _lbl(self._T("msisdn_title"),
                         _font("Segoe UI", 12, bold=True), C["muted"])
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        sc_lay.addWidget(title_lbl)
        sc_lay.addStretch()

        # Entry
        self._entry = QLineEdit()
        self._entry.setPlaceholderText(self._T("msisdn_enter"))
        self._entry.setFont(_font("Consolas", 14))
        self._entry.setFixedSize(280, 36)
        self._entry.setStyleSheet(f"""
            QLineEdit {{
                background:{C['input']}; color:{C['text']};
                border:1px solid {C['accent2']}; border-radius:8px;
                padding:4px 12px;
            }}
            QLineEdit:focus {{ border-color:{C['accent']}; }}
        """)
        self._entry.returnPressed.connect(self.do_search)
        sc_lay.addWidget(self._entry)

        # Search button
        self._search_btn = QPushButton(self._T("msisdn_search"))
        self._search_btn.setFont(_font("Segoe UI", 13, bold=True))
        self._search_btn.setFixedSize(100, 36)
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['accent2']}; color:white;
                border-radius:8px; font-weight:600;
            }}
            QPushButton:hover {{ background:{C['accent']}; }}
            QPushButton:disabled {{
                background:{C['input']}; color:{C['muted']};
            }}
        """)
        self._search_btn.clicked.connect(self.do_search)
        sc_lay.addWidget(self._search_btn)

        # Clear button
        clear_btn = QPushButton(self._T("msisdn_clear"))
        clear_btn.setFont(FONT_UI)
        clear_btn.setFixedSize(76, 36)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['input']}; color:{C['muted']};
                border:1px solid {C['border']}; border-radius:8px;
            }}
            QPushButton:hover {{ background:{C['card2']}; }}
        """)
        clear_btn.clicked.connect(self.clear)
        sc_lay.addWidget(clear_btn)

        root.addWidget(search_card)

        # ── Scroll area ──────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background:{C['bg']}; border:none; }}")

        self._results_widget = QWidget()
        self._results_widget.setStyleSheet(
            f"background:{C['bg']};")
        self._results_layout = QGridLayout(self._results_widget)
        self._results_layout.setContentsMargins(4, 4, 4, 4)
        self._results_layout.setSpacing(8)
        # 3 equal columns
        for col in range(3):
            self._results_layout.setColumnStretch(col, 1)

        self._scroll.setWidget(self._results_widget)
        root.addWidget(self._scroll, 1)

        self._show_placeholder()

    # ── Clear helper ──────────────────────────────────
    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── States ────────────────────────────────────────
    def _show_placeholder(self):
        self._clear_results()
        ph = self._state_frame("🔍", self._T("msisdn_empty"), C["muted"])
        self._results_layout.addWidget(ph, 0, 0, 1, 3)

    def _show_loading(self):
        self._clear_results()
        ph = self._state_frame("⏳", self._T("msisdn_loading"), C["warning"])
        self._results_layout.addWidget(ph, 0, 0, 1, 3)

    def _show_error(self, msg: str):
        self._clear_results()
        ph = self._state_frame("❌", self._T("msisdn_error"),
                               C["error"], subtitle=msg)
        self._results_layout.addWidget(ph, 0, 0, 1, 3)

    def _state_frame(self, icon: str, text: str, color: str,
                     subtitle: str = "") -> QFrame:
        """Generic centered state card (placeholder / loading / error)."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background:{C['card']}; border-radius:14px;")
        lay = QVBoxLayout(frame)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)
        lay.setContentsMargins(20, 40, 20, 40)

        icon_lbl = _lbl(icon, _font("Segoe UI", 48),
                        align=Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        msg_lbl = _lbl(text, _font("Segoe UI", 14, bold=True), color,
                       align=Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg_lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setFont(FONT_MONO_S)
            sub.setStyleSheet(f"color:{C['muted']}; background:transparent;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setWordWrap(True)
            lay.addWidget(sub)

        return frame

    # ── Search ────────────────────────────────────────
    def do_search(self):
        query = self._entry.text().strip()
        if not query:
            return

        self._search_btn.setEnabled(False)
        self._search_btn.setText("⏳")
        self._show_loading()

        # Run API call in background thread
        self._thread = QThread()
        self._worker = _FetchWorker(query)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_result)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_result(self, data, err, source):
        self._search_btn.setEnabled(True)
        self._search_btn.setText(self._T("msisdn_search"))
        if err:
            self._show_error(err)
        else:
            self._data   = data
            self._source = source
            self.render(data, source)

    def clear(self):
        self._entry.clear()
        self._data   = None
        self._source = None
        self._show_placeholder()

    # ── Render ────────────────────────────────────────
    def render(self, data: dict, source: str = "MSISDN"):
        """Render API JSON response: hero card + group cards."""
        self._clear_results()

        # ── Hero card ─────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(
            f"background:{C['accent2']}; border-radius:16px;")
        hero_lay = QHBoxLayout(hero)
        hero_lay.setContentsMargins(16, 12, 24, 12)
        hero_lay.setSpacing(0)

        # Left block: icon + primary id
        lh = QWidget()
        lh.setStyleSheet("background:transparent;")
        lh_lay = QVBoxLayout(lh)
        lh_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lh_lay.setSpacing(2)

        if source == "SIM":
            icon     = "💳"
            id_value = str(data.get("number",
                           data.get("iccid",
                           data.get("simNumber", "—"))))
            id_label = "SIM / ICC"
        else:
            icon     = "📱"
            id_value = str(data.get("msisdn", "—"))
            id_label = "MSISDN"

        lh_lay.addWidget(_lbl(icon, _font("Segoe UI", 32),
                              align=Qt.AlignmentFlag.AlignCenter))
        id_lbl = _lbl(id_value, _font("Consolas", 22, bold=True), "white",
                      align=Qt.AlignmentFlag.AlignCenter)
        lh_lay.addWidget(id_lbl)
        lh_lay.addWidget(_lbl(id_label, _font("Segoe UI", 10), "#C4B0DC",
                              align=Qt.AlignmentFlag.AlignCenter))
        hero_lay.addWidget(lh)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("color:#7C3DAB;")
        div.setFixedWidth(1)
        hero_lay.addWidget(div)
        hero_lay.addSpacing(10)

        # Pills block
        pills_w = QWidget()
        pills_w.setStyleSheet("background:transparent;")
        pills_lay = QHBoxLayout(pills_w)
        pills_lay.setSpacing(6)
        pills_lay.setContentsMargins(10, 0, 10, 0)
        pills_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        s_lbl, s_col = STATUS_MAP.get(
            data.get("status"), (str(data.get("status", "—")), C["muted"]))
        pills_lay.addWidget(self._pill("Status", s_lbl, s_col))

        ss_lbl, ss_col = SIM_STATUS_MAP.get(
            data.get("simCardStatus"),
            (str(data.get("simCardStatus", "—")), C["muted"]))
        pills_lay.addWidget(self._pill("SIM", ss_lbl, ss_col))

        pay = PAYMENT_MAP.get(data.get("paymentPlan"),
                              str(data.get("paymentPlan", "—")))
        pills_lay.addWidget(self._pill("Plan",  pay, C["success"]))
        pills_lay.addWidget(
            self._pill("Usage",
                       str(data.get("numberUsageType", "—")),
                       C["accent"]))
        hero_lay.addWidget(pills_w)
        hero_lay.addStretch()

        # Right block: meta info
        rh = QWidget()
        rh.setStyleSheet("background:transparent;")
        rh_lay = QVBoxLayout(rh)
        rh_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        rh_lay.setSpacing(4)

        rh_lay.addWidget(
            _lbl("👤 " + str(data.get("username", "—")),
                 _font("Consolas", 14, bold=True), "white",
                 align=Qt.AlignmentFlag.AlignRight))

        raw = data.get("lastActionDate", "")
        fmt = raw[:19].replace("T", "  ") if raw else "—"
        rh_lay.addWidget(
            _lbl("📅 " + fmt,
                 _font("Consolas", 11), "#C4B0DC",
                 align=Qt.AlignmentFlag.AlignRight))

        rh_lay.addWidget(
            _lbl(f"🏷️ v{data.get('version', '—')}  |  "
                 f"Segment {data.get('segmentType', '—')}",
                 _font("Segoe UI", 10), "#C4B0DC",
                 align=Qt.AlignmentFlag.AlignRight))

        badge_color = C["accent"] if source == "SIM" else C["success"]
        rh_lay.addWidget(
            _lbl(f"🔎 {source}",
                 _font("Segoe UI", 9, bold=True), badge_color,
                 align=Qt.AlignmentFlag.AlignRight))

        hero_lay.addWidget(rh)
        self._results_layout.addWidget(hero, 0, 0, 1, 3)

        # ── Group cards ──────────────────────────────
        group_data: dict[str, dict] = {g: {} for g in self._COL}
        for fk, fv in data.items():
            meta  = MSISDN_FIELD_META.get(fk)
            group = meta["group"] if meta else "misc"
            if group in group_data:
                group_data[group][fk] = fv

        for group_key, fields in group_data.items():
            if not fields:
                continue
            ginfo  = MSISDN_GROUPS.get(group_key,
                                        {"label": group_key, "color_key": "muted"})
            gcolor = C.get(ginfo["color_key"], C["muted"])
            col    = self._COL.get(group_key, 0)
            row    = self._ROW.get(group_key, 0) + 1  # +1 because row 0 = hero

            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:{C['card']}; border-radius:14px; }}"
                f"QLabel {{ background:transparent; }}")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(10, 10, 10, 10)
            card_lay.setSpacing(4)

            # Group header bar
            gh = QFrame()
            gh.setFixedHeight(38)
            gh.setStyleSheet(
                f"background:{C['input']}; border-radius:10px;")
            gh_lay = QHBoxLayout(gh)
            gh_lay.setContentsMargins(8, 0, 8, 0)
            gh_lay.setSpacing(6)

            color_bar = QFrame()
            color_bar.setFixedSize(4, 22)
            color_bar.setStyleSheet(
                f"background:{gcolor}; border-radius:2px;")
            gh_lay.addWidget(color_bar)

            gh_lbl = QLabel(ginfo["label"])
            gh_lbl.setFont(_font("Segoe UI", 11, bold=True))
            gh_lbl.setStyleSheet(f"color:{gcolor}; background:transparent;")
            gh_lay.addWidget(gh_lbl)
            gh_lay.addStretch()
            card_lay.addWidget(gh)

            # Fields
            for fk, fv in fields.items():
                meta    = MSISDN_FIELD_META.get(fk, {"label": fk, "icon": "•"})
                display = self._fmt(fk, fv)
                txt_col, bg_col = self._style(fk, fv)

                rf = QWidget()
                rf.setStyleSheet("background:transparent;")
                rf_lay = QHBoxLayout(rf)
                rf_lay.setContentsMargins(2, 1, 2, 1)
                rf_lay.setSpacing(6)

                # Field label
                field_lbl = QLabel(f"{meta['icon']}  {meta['label']}")
                field_lbl.setFont(FONT_UI_XS)
                field_lbl.setFixedWidth(160)
                field_lbl.setStyleSheet(
                    f"color:{C['muted']}; background:transparent;")
                rf_lay.addWidget(field_lbl)

                # Value — selectable QLabel in a colored frame
                vf = QFrame()
                vf.setStyleSheet(
                    f"background:{bg_col}; border-radius:6px;")
                vf_lay = QHBoxLayout(vf)
                vf_lay.setContentsMargins(8, 3, 8, 3)

                val_lbl = QLabel(display)
                val_lbl.setFont(FONT_MONO_S)
                val_lbl.setStyleSheet(
                    f"color:{txt_col}; background:transparent;")
                val_lbl.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse)
                val_lbl.setCursor(Qt.CursorShape.IBeamCursor)
                vf_lay.addWidget(val_lbl)
                rf_lay.addWidget(vf, 1)

                card_lay.addWidget(rf)

            card_lay.addSpacing(4)
            self._results_layout.addWidget(card, row, col)

        # Make group rows stretch equally
        for r in [1, 2]:
            self._results_layout.setRowStretch(r, 1)

    # ── Helpers ────────────────────────────────────────
    def _pill(self, label: str, value: str, color: str) -> QFrame:
        pill = QFrame()
        pill.setStyleSheet(
            f"background:{C['bg']}; border-radius:10px;")
        lay = QVBoxLayout(pill)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        lbl_w = QLabel(label)
        lbl_w.setFont(_font("Segoe UI", 9))
        lbl_w.setStyleSheet("color:#C4B0DC; background:transparent;")
        lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_w)

        val_w = QLabel(value)
        val_w.setFont(_font("Segoe UI", 12, bold=True))
        val_w.setStyleSheet(f"color:{color}; background:transparent;")
        val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(val_w)

        return pill

    def _fmt(self, key: str, val) -> str:
        if val is None:
            return "null"
        if key == "status":
            lbl, _ = STATUS_MAP.get(val, (str(val), None))
            return f"{val}  ({lbl})"
        if key == "simCardStatus":
            lbl, _ = SIM_STATUS_MAP.get(val, (str(val), None))
            return f"{val}  ({lbl})"
        if key == "paymentPlan":
            return f"{val}  ({PAYMENT_MAP.get(val, '?')})"
        if key == "lastActionDate" and isinstance(val, str) and "T" in val:
            return val[:19].replace("T", "  ")
        if isinstance(val, bool):
            return "✓  true" if val else "✗  false"
        return str(val)

    def _style(self, key: str, val):
        """Returns (text_color, bg_color)."""
        if val is None:
            return C["muted"], C["input"]
        if key == "status":
            _, col = STATUS_MAP.get(val, (None, C["muted"]))
            return col, C["input"]
        if key == "simCardStatus":
            _, col = SIM_STATUS_MAP.get(val, (None, C["muted"]))
            return col, C["input"]
        if key in ("pin1", "pin2", "puk1", "puk2"):
            return C["warning"], C["input"]
        if key in ("price", "finalPrice", "reservationFee", "activationFee"):
            return C["success"], C["input"]
        if isinstance(val, bool):
            return (C["success"] if val else C["error"]), C["input"]
        return C["text"], C["input"]

    # ── Public: state persistence across lang / theme changes ──
    def get_cached_data(self):
        return self._data, self._source

    def rebuild(self, T=None):
        """Recreate all widgets with the current C palette."""
        if T:
            self._T = T
        # Remove and rebuild layout contents
        for child in self.findChildren(QWidget):
            child.deleteLater()
        self._build()
        if self._data:
            self.render(self._data, self._source or "MSISDN")

    def restore(self, data: dict, source: str = "MSISDN"):
        if data:
            self._data   = data
            self._source = source
            self.render(data, source)