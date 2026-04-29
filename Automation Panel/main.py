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
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor, QPalette

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

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 0, 16, 0)
        root.setSpacing(0)

        # ── Left: logo + title ──────────────────────
        left = QHBoxLayout()
        left.setSpacing(12)

        self._logo_lbl = QLabel()
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Logo", "azercell_logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                120, 48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._logo_lbl.setPixmap(pix)
        else:
            # Fallback badge
            self._logo_lbl.setText("A")
            self._logo_lbl.setFixedSize(36, 36)
            self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._logo_lbl.setStyleSheet(
                f"background:{C['purple']}; color:white; "
                "font-size:18px; font-weight:700; border-radius:8px;")
        left.addWidget(self._logo_lbl)

        title = QLabel("Automation Panel")
        title.setFont(font("Segoe UI", 18, bold=True))
        title.setStyleSheet(f"color:{C['text']}; background:transparent;")
        left.addWidget(title)

        root.addLayout(left)
        root.addStretch()

        # ── Center: version badge ────────────────────
        ver = QLabel("v6.0")
        ver.setFont(font("Segoe UI", 11))
        ver.setStyleSheet(
            f"color:{C['muted']}; background:transparent; margin-right:8px;")
        root.addWidget(ver)

        # ── Right: controls ──────────────────────────
        right = QHBoxLayout()
        right.setSpacing(8)

        # History button
        self._hist_btn = QPushButton("📋  History")
        self._hist_btn.setFont(font("Segoe UI", 11))
        self._hist_btn.setFixedHeight(32)
        self._hist_btn.setObjectName("btn_secondary")
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
        self._lang_combo.currentTextChanged.connect(
            lambda t: self.lang_changed.emit(t.lower()))
        right.addWidget(self._lang_combo)

        # Theme toggle
        self._theme_btn = QPushButton(T("light_mode") if cfg.is_dark() else T("dark_mode"))
        self._theme_btn.setFont(font("Segoe UI", 11))
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.setObjectName("btn_secondary")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self.theme_toggled)
        right.addWidget(self._theme_btn)

        root.addLayout(right)

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
#  CUSTOM TAB BAR  (styled QTabWidget wrapper)
# ══════════════════════════════════════════════════════
class MainTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocumentMode(False)
        self.tabBar().setFont(font("Segoe UI", 13, bold=True))
        self.tabBar().setExpanding(False)
        self.tabBar().setCursor(Qt.CursorShape.PointingHandCursor)


# ══════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Azercell Automation Panel")
        self.setMinimumSize(1100, 720)

        # App icon
        ico_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Logo", "azercell.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

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

        # ── Thin accent line below topbar ───────────
        accent_line = QFrame()
        accent_line.setFixedHeight(2)
        accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C['purple']}, stop:0.5 {C['accent2']}, stop:1 transparent);")
        root.addWidget(accent_line)

        # ── Tab area ─────────────────────────────────
        self._tabs = MainTabWidget()
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
        tw_lay.setContentsMargins(16, 12, 16, 8)
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
    app.setApplicationName("AzercellPanel")
    app.setOrganizationName("Azercell")

    # Apply initial dark theme
    set_theme("dark")
    set_theme("dark")
    app.setStyleSheet(build_qss())

    # Windows 11 dark title bar via ctypes
    window = App()
    _apply_dark_titlebar(window)

    sys.exit(app.exec())


def _apply_dark_titlebar(window: QMainWindow):
    """Apply dark title bar on Windows 10/11 (build 22000+)."""
    try:
        import ctypes
        hwnd = int(window.winId())
        color = ctypes.c_int(0x1E0A12)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass


if __name__ == "__main__":
    main()