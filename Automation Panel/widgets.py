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


def mk_password_field(parent_layout, label: str, default: str = "",
                      label_width: int = 140) -> QLineEdit:
    """Labeled password entry with show/hide toggle."""
    e = mk_entry(password=True, width=0)
    e.setText(default)

    eye_btn = QPushButton("👁")
    eye_btn.setFixedSize(38, 38)
    eye_btn.setObjectName("btn_secondary")
    eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    eye_btn.setFont(font("Segoe UI", 14))
    eye_btn.setCheckable(True)

    def toggle(checked):
        e.setEchoMode(
            QLineEdit.EchoMode.Normal if checked
            else QLineEdit.EchoMode.Password)

    eye_btn.toggled.connect(toggle)

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
