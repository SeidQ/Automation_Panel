"""
config.py — Theme palettes, localization, fonts, constants
PyQt6 migration — no tkinter/CTk dependencies
"""

import json
import os

# ══════════════════════════════════════════════════════
#  PERSISTENCE
# ══════════════════════════════════════════════════════
_SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "userdata.json")


def save_state(section: str, data: dict):
    state = load_all()
    state[section] = data
    try:
        with open(_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_section(section: str) -> dict:
    return load_all().get(section, {})


def load_all() -> dict:
    try:
        if os.path.exists(_SAVE_FILE):
            with open(_SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# ══════════════════════════════════════════════════════
#  THEME PALETTES  (pure hex — no CTk tuples)
# ══════════════════════════════════════════════════════
DARK = {
    "bg":      "#0E0818",
    "bg2":     "#150F25",
    "card":    "#1A1130",
    "card2":   "#201540",
    "input":   "#221545",
    "border":  "#3D2260",
    "border2": "#5C2483",
    "accent":  "#7C6EB0",
    "accent2": "#6B3FA0",
    "purple":  "#5C2483",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error":   "#EF4444",
    "info":    "#3B82F6",
    "text":    "#EDE8F5",
    "text2":   "#C4B0DC",
    "muted":   "#8B75B0",
    "muted2":  "#6B5A8A",
}

LIGHT = {
    "bg":      "#F0EDF8",
    "bg2":     "#E8E3F5",
    "card":    "#FFFFFF",
    "card2":   "#F7F4FE",
    "input":   "#EDE8F5",
    "border":  "#C4B0DC",
    "border2": "#9B7DC8",
    "accent":  "#7C6EB0",
    "accent2": "#6B3FA0",
    "purple":  "#5C2483",
    "success": "#16A34A",
    "warning": "#D97706",
    "error":   "#DC2626",
    "info":    "#2563EB",
    "text":    "#1A0A2E",
    "text2":   "#3D2260",
    "muted":   "#6B5A8A",
    "muted2":  "#8B75B0",
}

# Active palette — mutated by set_theme()
C: dict = dict(DARK)
_CURRENT_THEME = "dark"


def set_theme(mode: str):
    """mode = 'dark' | 'light'"""
    global _CURRENT_THEME
    _CURRENT_THEME = mode
    C.update(DARK if mode == "dark" else LIGHT)


def is_dark() -> bool:
    return _CURRENT_THEME == "dark"


# ══════════════════════════════════════════════════════
#  QSS STYLESHEET GENERATOR
# ══════════════════════════════════════════════════════
def build_qss() -> str:
    """Generate full application QSS from current C palette."""
    c = C
    return f"""
/* ── Global ── */
QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: 'Segoe UI';
    font-size: 13px;
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {c['bg']};
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: {c['bg2']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border2']};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {c['bg2']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border2']};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c['accent']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Line Edit / Entry ── */
QLineEdit {{
    background-color: {c['input']};
    color: {c['text']};
    border: 1.5px solid {c['border']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    font-family: 'Consolas';
    selection-background-color: {c['purple']};
}}
QLineEdit:focus {{
    border-color: {c['accent2']};
    background-color: {c['card2']};
}}
QLineEdit:disabled {{
    color: {c['muted']};
    background-color: {c['bg2']};
    border-color: {c['border']};
}}
QLineEdit::placeholder {{
    color: {c['muted']};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {c['purple']};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI';
}}
QPushButton:hover {{
    background-color: {c['accent2']};
}}
QPushButton:pressed {{
    background-color: {c['border']};
}}
QPushButton:disabled {{
    background-color: {c['input']};
    color: {c['muted']};
}}

QPushButton#btn_secondary {{
    background-color: {c['input']};
    color: {c['text2']};
    border: 1px solid {c['border']};
}}
QPushButton#btn_secondary:hover {{
    background-color: {c['card2']};
    border-color: {c['border2']};
}}

QPushButton#btn_eye {{
    background-color: {c['input']};
    color: {c['text2']};
    border: 1px solid {c['border']};
    font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', 'Arial Unicode MS';
    font-size: 16px;
}}
QPushButton#btn_eye:hover {{
    background-color: {c['card2']};
}}
QPushButton#btn_eye:checked {{
    border-color: {c['purple']};
    color: {c['purple']};
}}

QPushButton#btn_danger {{
    background-color: transparent;
    color: {c['error']};
    border: 1px solid {c['error']};
}}
QPushButton#btn_danger:hover {{
    background-color: {c['error']};
    color: white;
}}

QPushButton#btn_success {{
    background-color: {c['success']};
    color: #0a2010;
}}
QPushButton#btn_success:hover {{
    background-color: #16A34A;
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {c['input']};
    color: {c['text']};
    border: 1.5px solid {c['border']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
}}
QComboBox:hover {{
    border-color: {c['border2']};
}}
QComboBox:focus {{
    border-color: {c['accent2']};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {c['muted']};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['card']};
    color: {c['text']};
    border: 1px solid {c['border2']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {c['purple']};
    selection-color: white;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 4px;
    min-height: 28px;
}}

/* ── Tab Bar ── */
QTabWidget::pane {{
    border: none;
    background-color: {c['bg']};
}}
QTabBar {{
    background-color: {c['bg2']};
    border-radius: 12px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c['muted']};
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 10px;
    margin: 4px 3px;
    min-width: 160px;
}}
QTabBar::tab:selected {{
    background-color: {c['purple']};
    color: #FFFFFF;
}}
QTabBar::tab:hover:!selected {{
    background-color: {c['card2']};
    color: {c['text2']};
}}

/* ── Table ── */
QTableWidget {{
    background-color: {c['card']};
    color: {c['text']};
    border: none;
    border-radius: 10px;
    gridline-color: {c['border']};
    font-size: 12px;
    font-family: 'Consolas';
    selection-background-color: {c['purple']};
    selection-color: white;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {c['border']};
}}
QTableWidget::item:selected {{
    background-color: {c['purple']};
    color: white;
}}
QHeaderView::section {{
    background-color: {c['bg2']};
    color: {c['muted']};
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 1px solid {c['border']};
}}

/* ── Text Edit (log) ── */
QTextEdit, QPlainTextEdit {{
    background-color: {c['bg2']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 8px;
    font-family: 'Consolas';
    font-size: 12px;
    selection-background-color: {c['purple']};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {c['border']};
    width: 1px;
    height: 1px;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {c['card2']};
    color: {c['text']};
    border: 1px solid {c['border2']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Checkbox ── */
QCheckBox {{
    color: {c['text2']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid {c['border2']};
    background-color: {c['input']};
}}
QCheckBox::indicator:checked {{
    background-color: {c['purple']};
    border-color: {c['purple']};
}}

/* ── RadioButton ── */
QRadioButton {{
    color: {c['text2']};
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 0px;
    height: 0px;
}}

/* ── Frames / Cards ── */
QFrame#card {{
    background-color: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
QFrame#card2 {{
    background-color: {c['card2']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
QFrame#topbar {{
    background-color: #130D24;
    border-bottom: 1px solid {c['border']};
}}
QFrame#sidebar {{
    background-color: {c['bg2']};
    border-right: 1px solid {c['border']};
}}
QFrame#divider {{
    background-color: {c['border']};
    max-height: 1px;
}}

/* ── Labels ── */
QLabel#title {{
    color: {c['text']};
    font-size: 20px;
    font-weight: 700;
}}
QLabel#subtitle {{
    color: {c['muted']};
    font-size: 12px;
}}
QLabel#section {{
    color: {c['muted2']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QLabel#badge_success {{
    color: {c['success']};
    background-color: rgba(34,197,94,0.12);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#badge_error {{
    color: {c['error']};
    background-color: rgba(239,68,68,0.12);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#badge_warning {{
    color: {c['warning']};
    background-color: rgba(245,158,11,0.12);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#badge_info {{
    color: {c['info']};
    background-color: rgba(59,130,246,0.12);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#status_ready {{
    color: {c['muted']};
    background-color: {c['input']};
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#status_running {{
    color: {c['warning']};
    background-color: rgba(245,158,11,0.12);
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#status_success {{
    color: {c['success']};
    background-color: rgba(34,197,94,0.12);
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#status_error {{
    color: {c['error']};
    background-color: rgba(239,68,68,0.12);
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 700;
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {c['input']};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background-color: {c['purple']};
    border-radius: 4px;
}}

/* ── Spin Box ── */
QSpinBox {{
    background-color: {c['input']};
    color: {c['text']};
    border: 1.5px solid {c['border']};
    border-radius: 8px;
    padding: 6px 10px;
}}
QSpinBox:focus {{
    border-color: {c['accent2']};
}}
"""


# ══════════════════════════════════════════════════════
#  LOCALIZATION  (unchanged from original)
# ══════════════════════════════════════════════════════
STRINGS = {
    "en": {
        "tab_planning":    "📋  Number Planning",
        "tab_activation":  "⚡  Activation",
        "tab_msisdn":      "🔍  MSISDN Lookup",
        "config":          "CONFIGURATION",
        "login_express":   "DEALER EXPRESS LOGIN",
        "login_online":    "DEALER ONLINE LOGIN",
        "files":           "FILES",
        "constants":       "FIXED VALUES",
        "exec_mode":       "EXECUTION MODE",
        "parallel":        "Parallel",
        "serial":          "Serial",
        "start":           "▶  START",
        "cancel":          "✕  CANCEL",
        "clear_log":       "Clear Log",
        "np_journal":      "NUMBER PLANNING — LOG",
        "test_data":       "TEST DATA",
        "results":         "RESULTS",
        "add":             "+ Add",
        "delete":          "Delete",
        "add_dialog":      "New Entry",
        "save":            "Add",
        "ready":           "● READY",
        "running":         "● RUNNING",
        "success_status":  "● SUCCESS",
        "failed_status":   "● ERRORS",
        "cancelled":       "● CANCELLED",
        "rows":            "rows",
        "np_started":      "═══ Number Planning started ═══",
        "np_done":         "═══ Number Planning completed ═══",
        "act_started":     "═══ Activation started",
        "cancel_msg":      "✕ CANCELLED — process aborted.",
        "summary_title":   "RESULT SUMMARY",
        "total":           "TOTAL",
        "passed":          "PASSED",
        "failed":          "FAILED",
        "light_mode":      "☀  Light",
        "dark_mode":       "🌙  Dark",
        "msisdn_title":    "MSISDN / SIM LOOKUP",
        "msisdn_enter":    "Enter MSISDN or ICCID…",
        "msisdn_search":   "Search",
        "msisdn_clear":    "Clear",
        "msisdn_result":   "NUMBER DETAILS",
        "msisdn_loading":  "Fetching data…",
        "msisdn_error":    "Request failed",
        "msisdn_empty":    "Enter a number and press Search",
        "designed_by":     "Designed by Said",
        "val_not_selected": "not selected — please fill in.",
        "val_not_found":    "file not found:",
        "val_error_status": "Error",
        "hist_clear":       "Clear History",
        "hist_empty":       "No activation history yet.",
        "hist_filter_all":  "All",
    },
    "az": {
        "tab_planning":    "📋  Nömrə Planlanması",
        "tab_activation":  "⚡  Aktivasiya",
        "tab_msisdn":      "🔍  MSISDN Axtarış",
        "config":          "KONFİQURASİYA",
        "login_express":   "DEALER EXPRESS GİRİŞ",
        "login_online":    "DEALER ONLINE GİRİŞ",
        "files":           "FAYLLAR",
        "constants":       "SABİT DƏYƏRLƏR",
        "exec_mode":       "İCRA REJİMİ",
        "parallel":        "Paralel",
        "serial":          "Ardıcıl",
        "start":           "▶  START",
        "cancel":          "✕  LƏĞV ET",
        "clear_log":       "Logu Təmizlə",
        "np_journal":      "NÖMRƏ PLANLANMASI — LOG",
        "test_data":       "TEST DATA",
        "results":         "NƏTİCƏLƏR",
        "add":             "+ Əlavə",
        "delete":          "Sil",
        "add_dialog":      "Yeni Qeyd",
        "save":            "Əlavə Et",
        "ready":           "● HAZIR",
        "running":         "● İŞLƏYİR",
        "success_status":  "● UĞURLU",
        "failed_status":   "● XƏTA VAR",
        "cancelled":       "● LƏĞV EDİLDİ",
        "rows":            "sətir",
        "np_started":      "═══ Nömrə Planlanması başladı ═══",
        "np_done":         "═══ Nömrə Planlanması tamamlandı ═══",
        "act_started":     "═══ Aktivasiya başladı",
        "cancel_msg":      "✕ LƏĞV EDİLDİ — proses dayandırıldı.",
        "summary_title":   "NƏTİCƏ XÜLASƏSİ",
        "total":           "CƏMİ",
        "passed":          "KEÇDİ",
        "failed":          "UĞURSUZ",
        "light_mode":      "☀  Açıq",
        "dark_mode":       "🌙  Tünd",
        "msisdn_title":    "MSISDN / SIM AXTARIŞ",
        "msisdn_enter":    "MSISDN və ya ICCID daxil edin…",
        "msisdn_search":   "Axtar",
        "msisdn_clear":    "Təmizlə",
        "msisdn_result":   "NÖMRƏ DETALLAR",
        "msisdn_loading":  "Məlumat gətirilir…",
        "msisdn_error":    "Sorğu uğursuz oldu",
        "msisdn_empty":    "Nömrə daxil edib Axtar düyməsini basın",
        "designed_by":     "Designed by Said",
        "val_not_selected": "seçilməyib — zəhmət olmasa doldurun.",
        "val_not_found":    "fayl tapılmadı:",
        "val_error_status": "Xəta",
        "hist_clear":       "Tarixçəni Təmizlə",
        "hist_empty":       "Hələ aktivasiya tarixçəsi yoxdur.",
        "hist_filter_all":  "Hamısı",
    },
    "ru": {
        "tab_planning":    "📋  Планирование",
        "tab_activation":  "⚡  Активация",
        "tab_msisdn":      "🔍  Поиск MSISDN",
        "config":          "КОНФИГУРАЦИЯ",
        "login_express":   "ВХОД DEALER EXPRESS",
        "login_online":    "ВХОД DEALER ONLINE",
        "files":           "ФАЙЛЫ",
        "constants":       "ФИКСИРОВАННЫЕ ЗНАЧЕНИЯ",
        "exec_mode":       "РЕЖИМ ВЫПОЛНЕНИЯ",
        "parallel":        "Параллельно",
        "serial":          "Последовательно",
        "start":           "▶  СТАРТ",
        "cancel":          "✕  ОТМЕНА",
        "clear_log":       "Очистить лог",
        "np_journal":      "ПЛАНИРОВАНИЕ — ЛОГ",
        "test_data":       "ТЕСТ ДАННЫЕ",
        "results":         "РЕЗУЛЬТАТЫ",
        "add":             "+ Добавить",
        "delete":          "Удалить",
        "add_dialog":      "Новая запись",
        "save":            "Добавить",
        "ready":           "● ГОТОВ",
        "running":         "● ВЫПОЛНЯЕТСЯ",
        "success_status":  "● УСПЕШНО",
        "failed_status":   "● ОШИБКИ",
        "cancelled":       "● ОТМЕНЕНО",
        "rows":            "строк",
        "np_started":      "═══ Планирование начато ═══",
        "np_done":         "═══ Планирование завершено ═══",
        "act_started":     "═══ Активация начата",
        "cancel_msg":      "✕ ОТМЕНА — процесс прерван.",
        "summary_title":   "СВОДКА РЕЗУЛЬТАТОВ",
        "total":           "ВСЕГО",
        "passed":          "ПРОШЛО",
        "failed":          "ПРОВАЛЕНО",
        "light_mode":      "☀  Светлая",
        "dark_mode":       "🌙  Тёмная",
        "msisdn_title":    "ПОИСК MSISDN / SIM",
        "msisdn_enter":    "Введите MSISDN или ICCID…",
        "msisdn_search":   "Поиск",
        "msisdn_clear":    "Очистить",
        "msisdn_result":   "ДЕТАЛИ НОМЕРА",
        "msisdn_loading":  "Загрузка данных…",
        "msisdn_error":    "Запрос не выполнен",
        "msisdn_empty":    "Введите номер и нажмите Поиск",
        "designed_by":     "Designed by Said",
        "val_not_selected": "не выбран — пожалуйста, заполните.",
        "val_not_found":    "файл не найден:",
        "val_error_status": "Ошибка",
        "hist_clear":       "Очистить историю",
        "hist_empty":       "История активаций пока пуста.",
        "hist_filter_all":  "Все",
    },
}

CURRENT_LANG = "en"


def T(key: str) -> str:
    return STRINGS.get(CURRENT_LANG, STRINGS["en"]).get(key, key)


# ══════════════════════════════════════════════════════
#  DATA CONSTANTS  (unchanged)
# ══════════════════════════════════════════════════════
DEFAULT_TEST_DATA = [
    {
        "MSISDN": "102989153", "SIMCARD": "2411010160896",
        "DOC_NUMBER": "AA0877974", "DOC_PIN": "70HF8GF",
        "TARIFF": "371", "PLAN_TYPE": "PostPaid",
        "PLAN_TYPE_REG": "PostPaid", "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989141", "SIMCARD": "2411010161241",
        "DOC_NUMBER": "AA3386081", "DOC_PIN": "7K51ES1",
        "TARIFF": "371", "PLAN_TYPE": "Postpaid",
        "PLAN_TYPE_REG": "Postpaid", "TARIFF_TYPE": "flat"
    },
]

TARIFF_TYPE_MAP  = {"Individual": "flat", "Corporate": "lat"}
TARIFF_TYPE_RMAP = {v: k for k, v in TARIFF_TYPE_MAP.items()}
CITY_MAP         = {"Baku": "Bak@012@"}

MSISDN_FIELD_META = {
    "msisdn":                {"label": "MSISDN",               "icon": "📱", "group": "identity"},
    "imsi":                  {"label": "IMSI",                 "icon": "🆔", "group": "identity"},
    "simCard":               {"label": "SIM Card",             "icon": "💳", "group": "identity"},
    "serial":                {"label": "Serial",               "icon": "🔢", "group": "identity"},
    "type":                  {"label": "SIM Type",             "icon": "📡", "group": "identity"},
    "status":                {"label": "Status",               "icon": "🔴", "group": "status"},
    "simCardStatus":         {"label": "SIM Status",           "icon": "💡", "group": "status"},
    "paymentPlan":           {"label": "Payment Plan",         "icon": "💰", "group": "status"},
    "activationTariff":      {"label": "Activation Tariff",    "icon": "📋", "group": "status"},
    "numberUsageType":       {"label": "Usage Type",           "icon": "📞", "group": "status"},
    "activationProfileForm": {"label": "Profile Form",         "icon": "📝", "group": "status"},
    "segmentType":           {"label": "Segment Type",         "icon": "🏷️", "group": "status"},
    "username":              {"label": "Username",             "icon": "👤", "group": "dealer"},
    "dealerId":              {"label": "Dealer ID",            "icon": "🏪", "group": "dealer"},
    "simCardDealerId":       {"label": "SIM Dealer ID",        "icon": "🏬", "group": "dealer"},
    "distributorId":         {"label": "Distributor ID",       "icon": "🏢", "group": "dealer"},
    "version":               {"label": "Version",              "icon": "📌", "group": "dealer"},
    "pin1":                  {"label": "PIN 1",                "icon": "🔑", "group": "security"},
    "pin2":                  {"label": "PIN 2",                "icon": "🔑", "group": "security"},
    "puk1":                  {"label": "PUK 1",                "icon": "🔐", "group": "security"},
    "puk2":                  {"label": "PUK 2",                "icon": "🔐", "group": "security"},
    "pin":                   {"label": "PIN",                  "icon": "🔒", "group": "security"},
    "price":                 {"label": "Price",                "icon": "💵", "group": "financial"},
    "finalPrice":            {"label": "Final Price",          "icon": "💴", "group": "financial"},
    "reservationFee":        {"label": "Reservation Fee",      "icon": "💶", "group": "financial"},
    "activationFee":         {"label": "Activation Fee",       "icon": "💷", "group": "financial"},
    "lastActionDate":        {"label": "Last Action Date",     "icon": "📅", "group": "misc"},
    "public":                {"label": "Public",               "icon": "🌐", "group": "misc"},
    "reservationId":         {"label": "Reservation ID",       "icon": "🎫", "group": "misc"},
    "reservationCode":       {"label": "Reservation Code",     "icon": "🎟️", "group": "misc"},
    "reservationDate":       {"label": "Reservation Date",     "icon": "📆", "group": "misc"},
    "description":           {"label": "Description",          "icon": "📄", "group": "misc"},
    "blockingSessionId":     {"label": "Blocking Session",     "icon": "🚫", "group": "misc"},
    "asanSoldType":          {"label": "ASAN Sold Type",       "icon": "🏷️", "group": "misc"},
    "logicalImsiType":       {"label": "Logical IMSI Type",    "icon": "🔖", "group": "misc"},
}

MSISDN_GROUPS = {
    "identity":  {"label": "📱  Identity",  "color_key": "accent2"},
    "status":    {"label": "🔴  Status",    "color_key": "warning"},
    "dealer":    {"label": "🏪  Dealer",    "color_key": "accent"},
    "security":  {"label": "🔐  Security",  "color_key": "error"},
    "financial": {"label": "💰  Financial", "color_key": "success"},
    "misc":      {"label": "📋  Details",   "color_key": "muted"},
}

STATUS_MAP = {
    1: ("FREE",     "#22C55E"),
    2: ("RESERVED", "#F59E0B"),
    3: ("SOLD",     "#3B82F6"),
    4: ("PLANNED",  "#8B5CF6"),
    5: ("BLOCKED",  "#EF4444"),
    6: ("INACTIVE", "#6B7280"),
}

SIM_STATUS_MAP = {
    1: ("ACTIVE",   "#22C55E"),
    2: ("INACTIVE", "#6B7280"),
    3: ("BLOCKED",  "#EF4444"),
}

PAYMENT_MAP = {1: "PostPaid", 2: "Prepaid"}