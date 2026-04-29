"""
Azercell Automation Panel v6.0
main.py — PyQt6 App shell: topbar, tabs, theme/lang switching.

Migration from CustomTkinter → PyQt6.
All Selenium + requests business logic is UNCHANGED.
UI layer is fully rewritten with QSS theming.
"""
import os
import sys
import queue
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QSizePolicy, QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal, QSettings, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QPainter, QLinearGradient, QPaintEvent

import config as cfg
from config import C, T, STRINGS, set_theme, build_qss
from widgets import (
    mk_label, mk_button, mk_badge, font,
    FONT_UI, FONT_UI_B, FONT_HEAD, FONT_UI_S, FONT_SECTION,
)

# Tab modules — business logic untouched, only UI classes replaced
from tab_planning import TabPlanning          # ✅ migrated
from tab_msisdn   import TabMSISDN           # ✅ migrated
from tab_activation import TabActivation      # ✅ migrated

# ── Placeholder tab (remove after each tab is migrated) ──
class _PlaceholderTab(QWidget):
    def __init__(self, name: str):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"🔧  {name}\nMigration in progress…")
        lbl.setFont(font("Segoe UI", 16))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color:{C['muted']};")
        lay.addWidget(lbl)


# ══════════════════════════════════════════════════════
#  TOPBAR
# ══════════════════════════════════════════════════════
class TopBar(QFrame):
    theme_toggled  = pyqtSignal()
    lang_changed   = pyqtSignal(str)
    history_opened = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(64)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

        # Mouse position for gradient spotlight (0.5 = center default)
        self._mouse_x_ratio = 0.5

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 0, 20, 0)
        root.setSpacing(0)

        root.addStretch(1)

        # ── Right: controls ──────────────────────────
        right = QHBoxLayout()
        right.setSpacing(8)

        # History button
        self._hist_btn = QPushButton("▤  History")
        self._hist_btn.setFont(font("Segoe UI", 11))
        self._hist_btn.setFixedHeight(32)
        self._hist_btn.setStyleSheet(
            "QPushButton { background:rgba(255,255,255,0.10); color:white; "
            "border:1px solid rgba(255,255,255,0.18); border-radius:8px; padding:0 14px; }"
            "QPushButton:hover { background:rgba(255,255,255,0.20); }"
            "QPushButton:disabled { color:rgba(255,255,255,0.30); "
            "border-color:rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); }")
        self._hist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hist_btn.setEnabled(False)
        self._hist_btn.clicked.connect(self.history_opened)
        right.addWidget(self._hist_btn)

        # Language selector
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["EN", "AZ", "RU"])
        self._lang_combo.setCurrentText(cfg.CURRENT_LANG.upper())
        self._lang_combo.setFixedHeight(32)
        self._lang_combo.setFixedWidth(72)
        self._lang_combo.setFont(font("Segoe UI", 11))
        self._lang_combo.setStyleSheet(
            "QComboBox { background:rgba(255,255,255,0.10); color:white; "
            "border:1px solid rgba(255,255,255,0.18); border-radius:8px; padding:0 8px; }"
            "QComboBox::drop-down { border:none; width:20px; }"
            "QComboBox QAbstractItemView { background:#1A1130; color:white; "
            "selection-background-color:#5C2483; border:none; }")
        self._lang_combo.currentTextChanged.connect(
            lambda t: self.lang_changed.emit(t.lower()))
        right.addWidget(self._lang_combo)

        # Theme toggle
        self._theme_btn = QPushButton(T("light_mode") if cfg.is_dark() else T("dark_mode"))
        self._theme_btn.setFont(font("Segoe UI", 11))
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.setStyleSheet(
            "QPushButton { background:rgba(255,255,255,0.10); color:white; "
            "border:1px solid rgba(255,255,255,0.18); border-radius:8px; padding:0 14px; }"
            "QPushButton:hover { background:rgba(255,255,255,0.20); }")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self.theme_toggled)
        right.addWidget(self._theme_btn)

        right.addSpacing(8)
        # (Window min/max/close are handled by native Windows frame)

        root.addLayout(right)

    def mouseMoveEvent(self, event):
        self._mouse_x_ratio = event.position().x() / max(self.width(), 1)
        self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Base dark gradient (left → right)
        base = QLinearGradient(0, 0, w, 0)
        base.setColorAt(0.0, QColor("#0E0818"))
        base.setColorAt(0.5, QColor("#150F25"))
        base.setColorAt(1.0, QColor("#0E0818"))
        painter.fillRect(0, 0, w, h, base)

        # Mouse-following purple spotlight
        spot_x = self._mouse_x_ratio * w
        spot = QLinearGradient(spot_x - w * 0.35, 0, spot_x + w * 0.35, 0)
        spot.setColorAt(0.0, QColor(0, 0, 0, 0))
        spot.setColorAt(0.5, QColor(92, 36, 131, 90))   # purple glow
        spot.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, w, h, spot)

        # ── Centered title text ──────────────────────
        painter.setFont(font("Segoe UI", 16, bold=True))
        painter.setPen(QColor("white"))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Automation Panel")

        # Bottom accent line drawn directly
        accent = QLinearGradient(0, 0, w, 0)
        accent.setColorAt(0.0,              QColor(92, 36, 131, 0))
        accent.setColorAt(max(0.0, self._mouse_x_ratio - 0.3), QColor(92, 36, 131, 0))
        accent.setColorAt(self._mouse_x_ratio,                  QColor(167, 100, 220, 255))
        accent.setColorAt(min(1.0, self._mouse_x_ratio + 0.3),  QColor(92, 36, 131, 0))
        accent.setColorAt(1.0,              QColor(92, 36, 131, 0))
        painter.fillRect(0, h - 2, w, 2, accent)

        painter.end()

    # ── Window drag via topbar ──────────────────
    # (Native frame handles drag & maximize — no custom drag needed)

    def enable_history(self, enabled: bool):
        self._hist_btn.setEnabled(enabled)

    def update_theme_label(self):
        self._theme_btn.setText(
            T("light_mode") if cfg.is_dark() else T("dark_mode"))

    def update_lang_label(self):
        self._lang_combo.blockSignals(True)
        self._lang_combo.setCurrentText(cfg.CURRENT_LANG.upper())
        self._lang_combo.blockSignals(False)


# ══════════════════════════════════════════════════════
#  FOOTER / STATUS BAR
# ══════════════════════════════════════════════════════
class FooterBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet(
            f"background:{C['bg2']}; border-top:1px solid {C['border']};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)

        self._status = QLabel("● READY")
        self._status.setObjectName("status_ready")
        self._status.setFont(font("Segoe UI", 11, bold=True))
        lay.addWidget(self._status)

        lay.addStretch()

        designed = QLabel(T("designed_by"))
        designed.setFont(font("Segoe UI", 10))
        designed.setStyleSheet(f"color:{C['muted2']}; background:transparent;")
        lay.addWidget(designed)

    def set_status(self, text: str, state: str = "ready"):
        self._status.setText(text)
        id_map = {
            "ready":   "status_ready",
            "running": "status_running",
            "success": "status_success",
            "error":   "status_error",
        }
        self._status.setObjectName(id_map.get(state, "status_ready"))
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)


# ══════════════════════════════════════════════════════
#  CUSTOM CENTERED TAB BAR
# ══════════════════════════════════════════════════════
class CenteredTabBar(QWidget):
    """Fully custom tab bar centered horizontally + QStackedWidget content."""

    tab_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages   = []
        self._current = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Centered pill row
        bar_wrap = QHBoxLayout()
        bar_wrap.setContentsMargins(0, 12, 0, 12)
        bar_wrap.addStretch()

        self._pill = QFrame()
        self._pill.setStyleSheet(
            f"QFrame {{"
            f" background:{C['bg2']};"
            f" border-radius:14px;"
            f" border:1px solid {C['border']};"
            f"}}")
        self._pill_lay = QHBoxLayout(self._pill)
        self._pill_lay.setContentsMargins(5, 5, 5, 5)
        self._pill_lay.setSpacing(3)

        bar_wrap.addWidget(self._pill)
        bar_wrap.addStretch()
        outer.addLayout(bar_wrap)

        # Gradient separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            "border:none;"
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent,"
            f"stop:0.2 {C['border']},"
            f"stop:0.8 {C['border']},"
            f"stop:1 transparent);")
        outer.addWidget(sep)

        # Content
        self._stack = QStackedWidget()
        outer.addWidget(self._stack, 1)

    def addTab(self, widget: QWidget, label: str):
        idx = len(self._pages)
        btn = QPushButton(label)
        btn.setFont(font("Segoe UI", 13, bold=True))
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.setMinimumWidth(160)
        btn.clicked.connect(lambda _, i=idx: self.setCurrentIndex(i))
        self._pill_lay.addWidget(btn)
        self._stack.addWidget(widget)
        self._pages.append(btn)
        if idx == 0:
            self._style(0)

    def setCurrentIndex(self, idx: int):
        self._current = idx
        self._stack.setCurrentIndex(idx)
        self._style(idx)
        self.tab_changed.emit(idx)

    def currentIndex(self) -> int:
        return self._current

    def clear(self):
        for btn in self._pages:
            self._pill_lay.removeWidget(btn)
            btn.deleteLater()
        while self._stack.count():
            self._stack.removeWidget(self._stack.widget(0))
        self._pages.clear()
        self._current = 0

    def _style(self, active: int):
        for i, btn in enumerate(self._pages):
            if i == active:
                btn.setStyleSheet(
                    f"QPushButton {{"                    f" background:{C['purple']}; color:#fff;"                    f" border:none; border-radius:10px;"                    f" padding:7px 28px;"                    f"}}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{"                    f" background:transparent; color:{C['muted']};"                    f" border:none; border-radius:10px;"                    f" padding:7px 28px;"                    f"}}"                    f"QPushButton:hover {{"                    f" background:{C['card2']};"                    f" color:{C['text2']};"                    f"}}")


# ══════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setMinimumSize(1100, 720)
        # Native frame — maximize/minimize/close handled by Windows
        self._drag_pos = None

        # Shared queues & stop event (same as original)
        self._log_q   = queue.Queue()
        self._res_q   = queue.Queue()
        self._stop_ev = threading.Event()

        # Tab references
        self._tab_plan = None
        self._tab_act  = None
        self._tab_ms   = None

        # Poll timer (replaces CTk after() loop)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(80)

        # Settings (replaces userdata.json geometry)
        self._settings = QSettings("Azercell", "AutomationPanel")

        self._build()
        self._restore_geometry()

    # ══════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════
    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────
        self._topbar = TopBar()
        self._topbar.theme_toggled.connect(self._toggle_theme)
        self._topbar.lang_changed.connect(self._on_lang_change)
        self._topbar.history_opened.connect(self._open_history)
        root.addWidget(self._topbar)

        # ── Tab area ─────────────────────────────────
        self._tabs = CenteredTabBar()
        self._tabs.setContentsMargins(0, 0, 0, 0)

        # Build tab contents
        self._tab_plan = TabPlanning(self._log_q, T)                                # ✅ migrated
        self._tab_act  = TabActivation(self._log_q, self._res_q, self._stop_ev, T) # ✅ migrated
        self._tab_ms   = TabMSISDN(T)                                               # ✅ migrated

        self._tabs.addTab(self._tab_plan, T("tab_planning"))
        self._tabs.addTab(self._tab_act,  T("tab_activation"))
        self._tabs.addTab(self._tab_ms,   T("tab_msisdn"))

        tab_wrapper = QWidget()
        tw_lay = QVBoxLayout(tab_wrapper)
        tw_lay.setContentsMargins(0, 0, 0, 0)
        tw_lay.setSpacing(0)
        tw_lay.addWidget(self._tabs)
        root.addWidget(tab_wrapper, 1)

        # ── Footer ───────────────────────────────────
        self._footer = FooterBar()
        root.addWidget(self._footer)

    # ══════════════════════════════════════════════════
    #  POLL LOOP  (replaces CTk after(80, self._poll))
    # ══════════════════════════════════════════════════
    def _poll(self):
        # Drain log queue
        try:
            while True:
                item = self._log_q.get_nowait()
                if item.get("_tab") == "np":
                    if hasattr(self._tab_plan, "append_log"):
                        self._tab_plan.append_log(
                            item["ts"], item["msg"], item["level"])
                else:
                    if hasattr(self._tab_act, "append_log"):
                        self._tab_act.append_log(
                            item["ts"], item["msg"], item["level"],
                            item.get("msisdn"),
                            step=item.get("step", 0),
                            done=item.get("done", False),
                            error=item.get("error", False))
        except queue.Empty:
            pass

        # Drain result queue
        try:
            while True:
                r = self._res_q.get_nowait()
                if hasattr(self._tab_act, "collect_result"):
                    self._tab_act.collect_result(r)
        except queue.Empty:
            pass

    # ══════════════════════════════════════════════════
    #  THEME TOGGLE
    # ══════════════════════════════════════════════════
    def _toggle_theme(self):
        new_mode = "light" if cfg.is_dark() else "dark"
        set_theme(new_mode)
        QApplication.instance().setStyleSheet(build_qss())
        self._topbar.update_theme_label()
        self._footer.setStyleSheet(
            f"background:{C['bg2']}; border-top:1px solid {C['border']};")
        # Rebuild MSISDN tab results (color-sensitive)
        if hasattr(self._tab_ms, "rebuild"):
            self._tab_ms.rebuild()

    # ══════════════════════════════════════════════════
    #  LANGUAGE SWITCH
    # ══════════════════════════════════════════════════
    def _on_lang_change(self, lang: str):
        cfg.CURRENT_LANG = lang

        # Cache live data before rebuild
        act_data    = list(getattr(self._tab_act, "_test_data", []))
        act_results = list(getattr(self._tab_act, "_results",   []))
        act_history = list(getattr(self._tab_act, "_history",   []))
        ms_cache    = getattr(self._tab_ms, "get_cached_data",
                              lambda: (None, None))()
        active_idx  = self._tabs.currentIndex()

        # Rebuild all tabs with new language
        self._rebuild_tabs()

        # Restore data
        if act_data and hasattr(self._tab_act, "_test_data"):
            self._tab_act._test_data = act_data
            self._tab_act._results   = act_results
            self._tab_act._history   = act_history
            self._tab_act._render_data()

        # ms_cache is now (data, source) tuple from updated get_cached_data()
        if ms_cache and ms_cache[0] and hasattr(self._tab_ms, "restore"):
            self._tab_ms.restore(ms_cache[0], ms_cache[1] or "MSISDN")

        # Restore active tab
        self._tabs.setCurrentIndex(active_idx)
        self._topbar.update_lang_label()

    def _rebuild_tabs(self):
        """Remove and re-add all tabs with current language strings."""
        self._tabs.clear()

        self._tab_plan = TabPlanning(self._log_q, T)                                # ✅ migrated
        self._tab_act  = TabActivation(self._log_q, self._res_q, self._stop_ev, T) # ✅ migrated
        self._tab_ms   = TabMSISDN(T)                                               # ✅ migrated

        self._tabs.addTab(self._tab_plan, T("tab_planning"))
        self._tabs.addTab(self._tab_act,  T("tab_activation"))
        self._tabs.addTab(self._tab_ms,   T("tab_msisdn"))

    # ══════════════════════════════════════════════════
    #  HISTORY WINDOW
    # ══════════════════════════════════════════════════
    def _open_history(self):
        if not hasattr(self._tab_act, "build_history_tab"):
            return
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Activation History")
        dlg.resize(900, 600)
        dlg.setStyleSheet(build_qss())
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(8, 8, 8, 8)
        self._tab_act.build_history_tab(dlg)
        dlg.exec()

    # ══════════════════════════════════════════════════
    #  GEOMETRY PERSISTENCE  (QSettings replaces userdata.json)
    # ══════════════════════════════════════════════════
    def _restore_geometry(self):
        geo = self._settings.value("geometry")
        maximized = self._settings.value("maximized", False, type=bool)
        if geo:
            try:
                self.restoreGeometry(geo)
            except Exception:
                self.resize(1380, 880)
        else:
            self.resize(1380, 880)
        if maximized:
            self.showMaximized()
        else:
            self.show()

    def changeEvent(self, event):
        super().changeEvent(event)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("maximized",
                                self.windowState() == Qt.WindowState.WindowMaximized)
        self._poll_timer.stop()
        super().closeEvent(event)

    # ══════════════════════════════════════════════════
    #  PUBLIC: update footer status from tabs
    # ══════════════════════════════════════════════════
    def set_status(self, text: str, state: str = "ready"):
        self._footer.set_status(text, state)


# ══════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════
def main():
    # HiDPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("")
    app.setOrganizationName("")

    # Apply initial dark theme
    set_theme("dark")
    set_theme("dark")
    app.setStyleSheet(build_qss())

    # Windows 11 dark title bar via ctypes
    window = App()
    window.setWindowTitle("")
    _apply_dark_titlebar(window)

    sys.exit(app.exec())


def _apply_dark_titlebar(window: QMainWindow):
    """
    Apply dark/purple native title bar on Windows 10/11.
    - DWMWA_USE_IMMERSIVE_DARK_MODE (20) → dark caption text & buttons
    - DWMWA_CAPTION_COLOR (35)          → dark background #0E0818
    - DWMWA_BORDER_COLOR (34)           → purple accent #5C2483
    """
    try:
        import ctypes
        hwnd = int(window.winId())
        # Erase title text at Win32 level
        ctypes.windll.user32.SetWindowTextW(hwnd, "")
        dwm = ctypes.windll.dwmapi

        # Dark mode caption (works Win10 1809+)
        dark = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))

        # Caption background color — deep dark purple #0E0818 (BGR for DWM)
        caption_color = ctypes.c_int(0x18080E)   # BGR: 0x18 0x08 0x0E
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))

        # Border/accent color — purple #5C2483 (BGR)
        border_color = ctypes.c_int(0x83245C)    # BGR: 0x83 0x24 0x5C
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))

    except Exception:
        pass


if __name__ == "__main__":
    main()