"""
widgets.py — Reusable PyQt6 widget factory functions
Modern, production-grade UI components
"""
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QFrame,
    QHBoxLayout, QVBoxLayout, QComboBox, QSizePolicy,
    QFileDialog, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from config import C


# ══════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════
def font(family="Segoe UI", size=13, bold=False) -> QFont:
    f = QFont(family, size)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    return f

FONT_MONO   = font("Consolas", 13)
FONT_MONO_S = font("Consolas", 12)
FONT_LABEL  = font("Segoe UI", 13)
FONT_LABEL_B= font("Segoe UI", 13, bold=True)
FONT_SECTION= font("Segoe UI", 11, bold=True)
FONT_HEAD   = font("Segoe UI", 20, bold=True)
FONT_UI     = font("Segoe UI", 13)
FONT_UI_B   = font("Segoe UI", 13, bold=True)
FONT_UI_S   = font("Segoe UI", 11)


# ══════════════════════════════════════════════════════
#  BASE CARD FRAME
# ══════════════════════════════════════════════════════
class Card(QFrame):
    """Rounded card with subtle border."""
    def __init__(self, parent=None, variant="card"):
        super().__init__(parent)
        self.setObjectName(variant)
        self.setFrameShape(QFrame.Shape.NoFrame)


class SectionHeader(QWidget):
    """Colored left-bar + uppercase section label."""
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 4)
        lay.setSpacing(8)

        bar = QFrame()
        bar.setFixedSize(3, 16)
        bar.setStyleSheet(f"background:{C['purple']}; border-radius:2px;")
        lay.addWidget(bar)

        lbl = QLabel(text.upper())
        lbl.setObjectName("section")
        lbl.setFont(FONT_SECTION)
        lay.addWidget(lbl)
        lay.addStretch()


class Divider(QFrame):
    """1px horizontal line."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)


class PanelHeader(QWidget):
    """Purple banner used as card section title."""
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"background:{C['purple']}; border-radius:8px;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(text)
        lbl.setFont(FONT_SECTION)
        lbl.setStyleSheet("color:white; background:transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)


class StatusBadge(QLabel):
    """Colored status pill."""
    _ID_MAP = {
        "ready":   "status_ready",
        "running": "status_running",
        "success": "status_success",
        "error":   "status_error",
    }

    def __init__(self, text="● READY", state="ready", parent=None):
        super().__init__(text, parent)
        self.setObjectName(self._ID_MAP.get(state, "status_ready"))
        self.setFont(FONT_UI_S)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(28)

    def set_state(self, text: str, state: str):
        self.setText(text)
        self.setObjectName(self._ID_MAP.get(state, "status_ready"))
        # Force style refresh
        self.setStyleSheet(self.styleSheet())
        self.style().unpolish(self)
        self.style().polish(self)


# ══════════════════════════════════════════════════════
#  FIELD HELPERS
# ══════════════════════════════════════════════════════
def mk_label(text: str, color: str = None, bold: bool = False,
             size: int = 13, object_name: str = None) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font("Segoe UI", size, bold))
    style = f"color:{color or C['text']}; background:transparent;"
    lbl.setStyleSheet(style)
    if object_name:
        lbl.setObjectName(object_name)
    return lbl


def mk_entry(placeholder: str = "", width: int = 220,
             monospace: bool = True, password: bool = False) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFont(FONT_MONO if monospace else FONT_UI)
    e.setMinimumHeight(38)
    if width:
        e.setFixedWidth(width)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    return e


def mk_combo(values: list, default: str = "") -> QComboBox:
    cb = QComboBox()
    cb.addItems(values)
    if default in values:
        cb.setCurrentText(default)
    cb.setMinimumHeight(38)
    return cb


def mk_button(text: str, variant: str = "primary",
              height: int = 38, min_width: int = 100) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(FONT_UI_B)
    btn.setMinimumHeight(height)
    btn.setMinimumWidth(min_width)
    id_map = {
        "primary":   "",
        "secondary": "btn_secondary",
        "danger":    "btn_danger",
        "success":   "btn_success",
    }
    btn.setObjectName(id_map.get(variant, ""))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def mk_field_row(label: str, widget: QWidget,
                 label_width: int = 140) -> QHBoxLayout:
    """Returns an HBoxLayout: [label | widget]."""
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label)
    lbl.setFont(FONT_LABEL)
    lbl.setFixedWidth(label_width)
    lbl.setStyleSheet(f"color:{C['muted']}; background:transparent;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


def mk_field(parent_layout, label: str, default: str = "",
             password: bool = False, disabled: bool = False,
             label_width: int = 140) -> QLineEdit:
    """Add a labeled entry row to parent_layout. Returns the QLineEdit."""
    e = mk_entry(password=password, width=0)
    e.setText(default)
    if disabled:
        e.setReadOnly(True)
        e.setStyleSheet(
            f"color:{C['muted']}; background:{C['bg2']}; border-color:{C['border']};")
    row = mk_field_row(label, e, label_width)
    parent_layout.addLayout(row)
    return e


def mk_file_field(parent_layout, label: str, default: str = "",
                  label_width: int = 140) -> QLineEdit:
    """Labeled file-picker row. Returns the QLineEdit."""
    e = mk_entry(width=0)
    e.setText(default)

    btn = mk_button("📂", "secondary", height=38, min_width=42)
    btn.setFixedWidth(42)

    def browse():
        path, _ = QFileDialog.getOpenFileName(
            None, "Select file", "",
            "CSV files (*.csv);;All files (*.*)")
        if path:
            e.setText(path)

    btn.clicked.connect(browse)

    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label)
    lbl.setFont(FONT_LABEL)
    lbl.setFixedWidth(label_width)
    lbl.setStyleSheet(f"color:{C['muted']}; background:transparent;")
    row.addWidget(lbl)
    row.addWidget(e, 1)
    row.addWidget(btn)
    parent_layout.addLayout(row)
    return e


_EYE_OPEN = (
    "M12 5C7 5 2.73 8.11 1 12c1.73 3.89 6 7 11 7s9.27-3.11 11-7"
    "c-1.73-3.89-6-7-11-7zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"
)
_EYE_CLOSED = (
    "M17.94 11A10 10 0 0 0 12 5C7 5 2.73 8.11 1 12a10.16 10.16 0 0 0 5 5.92"
    "M6.53 6.53A9.94 9.94 0 0 0 1 12a10 10 0 0 0 14.54 5.46"
    "M22.99 12A10 10 0 0 0 12 5.01M2 2l20 20"
)


def mk_eye_button(entry: "QLineEdit") -> QPushButton:
    """Modern SVG eye button — no emoji, always renders."""
    from PyQt6.QtGui import QPainter, QPainterPath, QPen
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtCore import QByteArray

    def _make_icon(path_d: str, color: str) -> "QIcon":
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
            f' fill="none" stroke="{color}" stroke-width="2"'
            f' stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{path_d}"/></svg>'
        ).encode()
        renderer = QSvgRenderer(QByteArray(svg))
        from PyQt6.QtGui import QPixmap
        px = QPixmap(20, 20)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        renderer.render(p)
        p.end()
        return QIcon(px)

    btn = QPushButton()
    btn.setFixedSize(38, 38)
    btn.setObjectName("btn_eye")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setCheckable(True)

    col_off = "#8B75B0"
    col_on  = "#5C2483"

    icon_off = _make_icon(_EYE_OPEN,   col_off)
    icon_on  = _make_icon(_EYE_CLOSED, col_on)
    btn.setIcon(icon_off)
    btn.setIconSize(QSize(20, 20))

    def _toggle(checked: bool):
        entry.setEchoMode(
            QLineEdit.EchoMode.Normal if checked
            else QLineEdit.EchoMode.Password)
        btn.setIcon(icon_on if checked else icon_off)

    btn.toggled.connect(_toggle)
    return btn


def mk_password_field(parent_layout, label: str, default: str = "",
                      label_width: int = 140) -> QLineEdit:
    """Labeled password entry with show/hide toggle."""
    e = mk_entry(password=True, width=0)
    e.setText(default)

    eye_btn = mk_eye_button(e)

    row = QHBoxLayout()
    row.setSpacing(8)
    lbl = QLabel(label)
    lbl.setFont(FONT_LABEL)
    lbl.setFixedWidth(label_width)
    lbl.setStyleSheet(f"color:{C['muted']}; background:transparent;")
    row.addWidget(lbl)
    row.addWidget(e, 1)
    row.addWidget(eye_btn)
    parent_layout.addLayout(row)
    return e


# ══════════════════════════════════════════════════════
#  INFO BADGE
# ══════════════════════════════════════════════════════
def mk_badge(text: str, variant: str = "info") -> QLabel:
    """Colored badge pill."""
    lbl = QLabel(text)
    lbl.setFont(font("Segoe UI", 11, bold=True))
    id_map = {"success": "badge_success", "error": "badge_error",
              "warning": "badge_warning", "info": "badge_info"}
    lbl.setObjectName(id_map.get(variant, "badge_info"))
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl