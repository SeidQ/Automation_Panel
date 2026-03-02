"""
config.py - Theme palettes, localization, fonts, constants
"""

import json
import os

# ══════════════════════════════════════════════════════
#  PERSISTENCE  — userdata.json next to this file
# ══════════════════════════════════════════════════════
_SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "userdata.json")

def save_state(section: str, data: dict):
    """Merge data into section and write to disk."""
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
#  THEME PALETTES
# ══════════════════════════════════════════════════════
DARK = {
    "bg":      "#120A1E",
    "card":    "#1C1030",
    "input":   "#251540",
    "border":  "#3D2260",
    "accent":  "#7C6EB0",
    "accent2": "#5C2483",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error":   "#EF4444",
    "text":    "#EDE8F5",
    "muted":   "#8B75B0",
}

LIGHT = {
    "bg":      "#F3F0F8",
    "card":    "#FFFFFF",
    "input":   "#EDE8F5",
    "border":  "#C4B0DC",
    "accent":  "#7C6EB0",
    "accent2": "#5C2483",
    "success": "#16A34A",
    "warning": "#D97706",
    "error":   "#DC2626",
    "text":    "#1A0A2E",
    "muted":   "#6B5A8A",
}

# Live palette — updated by update_C() on theme change
# Starts as DARK because app starts in dark visual mode (CTk "Light")
C = dict(DARK)

def update_C():
    """Sync C dict to current appearance mode.
    IMPORTANT: Our color tuples are (dark, light) — REVERSE of CTk convention.
    So our DARK palette = CTk 'Light' mode, LIGHT palette = CTk 'Dark' mode."""
    import customtkinter as _ctk
    src = DARK if _ctk.get_appearance_mode() == "Light" else LIGHT
    C.update(src)

def cv(key):
    """Return current-mode string for a palette key."""
    import customtkinter as _ctk
    src = DARK if _ctk.get_appearance_mode() == "Light" else LIGHT
    return src[key]


# ══════════════════════════════════════════════════════
#  LOCALIZATION
# ══════════════════════════════════════════════════════
STRINGS = {
    "en": {
        "tab_planning":    "  📋 Number Planning  ",
        "tab_activation":  "  ⚡ Number Activation  ",
        "tab_msisdn":      "  🔍 MSISDN Details  ",
        "config":          "⚙️  CONFIGURATION",
        "login_express":   "🔐  DEALER EXPRESS LOGIN",
        "login_online":    "🔐  DEALER ONLINE LOGIN",
        "files":           "📁  FILES",
        "constants":       "⚙️  FIXED VALUES",
        "exec_mode":       "🔀  EXECUTION MODE",
        "parallel":        "Parallel  (fast)",
        "serial":          "Serial  (reliable)",
        "start":           "▶   START",
        "cancel":          "✕  CANCEL",
        "clear_log":       "🗑  Clear Log",
        "np_journal":      "📋  NUMBER PLANNING — LOG",
        "test_data":       "📋  TEST DATA",
        "results":         "📊  RESULTS",
        "add":             "＋  Add",
        "delete":          "✕  Del",
        "add_dialog":      "＋  New Test Data",
        "save":            "✓  Add",
        "ready":           "  ● READY  ",
        "running":         "● RUNNING",
        "success_status":  "● SUCCESS",
        "failed_status":   "● ERRORS",
        "cancelled":       "● CANCELLED",
        "rows":            "rows",
        "np_started":      "═══ Number Planning started ═══",
        "np_done":         "═══ Number Planning completed ═══",
        "act_started":     "═══ Activation started",
        "cancel_msg":      "✕ CANCEL — process aborted.",
        "summary_title":   "  📊  RESULT SUMMARY",
        "total":           "TOTAL",
        "passed":          "PASSED",
        "failed":          "FAILED",
        "light_mode":      "☀️ Light",
        "dark_mode":       "🌙 Dark",
        "msisdn_title":    "🔍  MSISDN NUMBER LOOKUP",
        "msisdn_enter":    "Enter MSISDN number",
        "msisdn_search":   "  🔍  Search  ",
        "msisdn_clear":    "🗑  Clear",
        "msisdn_result":   "📊  NUMBER DETAILS",
        "msisdn_loading":  "Fetching data...",
        "msisdn_error":    "Request failed",
        "msisdn_empty":    "Enter a number and press Search",
        "designed_by":     "Designed by Said",
        "val_not_selected": "not selected — please fill in.",
        "val_not_found":    "file not found:",
        "val_error_status": "Error",
    },
    "az": {
        "tab_planning":    "  📋 Nömrə Planlanması  ",
        "tab_activation":  "  ⚡ Nömrə Aktivasiya  ",
        "tab_msisdn":      "  🔍 MSISDN Detalları  ",
        "config":          "⚙️  KONFİQURASİYA",
        "login_express":   "🔐  DEALER EXPRESS GİRİŞ",
        "login_online":    "🔐  DEALER ONLINE GİRİŞ",
        "files":           "📁  FAYLLAR",
        "constants":       "⚙️  SABİT DƏYƏRLƏR",
        "exec_mode":       "🔀  İCRA REJİMİ",
        "parallel":        "Paralel  (sürətli)",
        "serial":          "Ardıcıl  (etibarlı)",
        "start":           "▶   START",
        "cancel":          "✕  LƏĞV ET",
        "clear_log":       "🗑  Logu Təmizlə",
        "np_journal":      "📋  NÖMRƏ PLANLANMASI — LOG",
        "test_data":       "📋  TEST DATA",
        "results":         "📊  NƏTİCƏLƏR",
        "add":             "＋  Əlavə",
        "delete":          "✕  Sil",
        "add_dialog":      "＋  Yeni Test Data",
        "save":            "✓  Əlavə Et",
        "ready":           "  ● HAZIR  ",
        "running":         "● İŞLƏYİR",
        "success_status":  "● UĞURLU",
        "failed_status":   "● XƏTA VAR",
        "cancelled":       "● LƏĞV EDİLDİ",
        "rows":            "sətir",
        "np_started":      "═══ Nömrə Planlanması başladı ═══",
        "np_done":         "═══ Nömrə Planlanması tamamlandı ═══",
        "act_started":     "═══ Aktivasiya başladı",
        "cancel_msg":      "✕ LƏĞV EDİLDİ — proses dayandırıldı.",
        "summary_title":   "  📊  NƏTİCƏ XÜLASƏSİ",
        "total":           "CƏMİ",
        "passed":          "KEÇDİ",
        "failed":          "UĞURSUZ",
        "light_mode":      "☀️ Açıq",
        "dark_mode":       "🌙 Tünd",
        "msisdn_title":    "🔍  MSISDN NÖMRƏ SORĞUSU",
        "msisdn_enter":    "MSISDN nömrəsini daxil edin",
        "msisdn_search":   "  🔍  Axtar  ",
        "msisdn_clear":    "🗑  Təmizlə",
        "msisdn_result":   "📊  NÖMRƏ DETALLAR",
        "msisdn_loading":  "Məlumat gətirilir...",
        "msisdn_error":    "Sorğu uğursuz oldu",
        "msisdn_empty":    "Nömrə daxil edib Axtar düyməsini basın",
        "designed_by":     "Designed by Said",
        "val_not_selected": "seçilməyib — zəhmət olmasa doldurun.",
        "val_not_found":    "fayl tapılmadı:",
        "val_error_status": "Xəta",
    },
    "ru": {
        "tab_planning":    "  📋 Планирование  ",
        "tab_activation":  "  ⚡ Активация  ",
        "tab_msisdn":      "  🔍 Детали MSISDN  ",
        "config":          "⚙️  КОНФИГУРАЦИЯ",
        "login_express":   "🔐  ВХОД DEALER EXPRESS",
        "login_online":    "🔐  ВХОД DEALER ONLINE",
        "files":           "📁  ФАЙЛЫ",
        "constants":       "⚙️  ФИКСИРОВАННЫЕ ЗНАЧЕНИЯ",
        "exec_mode":       "🔀  РЕЖИМ ВЫПОЛНЕНИЯ",
        "parallel":        "Параллельно  (быстро)",
        "serial":          "Последовательно  (надёжно)",
        "start":           "▶   СТАРТ",
        "cancel":          "✕  ОТМЕНА",
        "clear_log":       "🗑  Очистить лог",
        "np_journal":      "📋  ПЛАНИРОВАНИЕ — ЛОГ",
        "test_data":       "📋  ТЕСТОВЫЕ ДАННЫЕ",
        "results":         "📊  РЕЗУЛЬТАТЫ",
        "add":             "＋  Добавить",
        "delete":          "✕  Удалить",
        "add_dialog":      "＋  Новые тестовые данные",
        "save":            "✓  Добавить",
        "ready":           "  ● ГОТОВ  ",
        "running":         "● ВЫПОЛНЯЕТСЯ",
        "success_status":  "● УСПЕШНО",
        "failed_status":   "● ОШИБКИ",
        "cancelled":       "● ОТМЕНЕНО",
        "rows":            "строк",
        "np_started":      "═══ Планирование начато ═══",
        "np_done":         "═══ Планирование завершено ═══",
        "act_started":     "═══ Активация начата",
        "cancel_msg":      "✕ ОТМЕНА — процесс прерван.",
        "summary_title":   "  📊  СВОДКА РЕЗУЛЬТАТОВ",
        "total":           "ВСЕГО",
        "passed":          "ПРОШЛО",
        "failed":          "ПРОВАЛЕНО",
        "light_mode":      "☀️ Светлая",
        "dark_mode":       "🌙 Тёмная",
        "msisdn_title":    "🔍  ПОИСК НОМЕРА MSISDN",
        "msisdn_enter":    "Введите номер MSISDN",
        "msisdn_search":   "  🔍  Поиск  ",
        "msisdn_clear":    "🗑  Очистить",
        "msisdn_result":   "📊  ДЕТАЛИ НОМЕРА",
        "msisdn_loading":  "Загрузка данных...",
        "msisdn_error":    "Запрос не выполнен",
        "msisdn_empty":    "Введите номер и нажмите Поиск",
        "designed_by":     "Designed by Said",
        "val_not_selected": "не выбран — пожалуйста, заполните.",
        "val_not_found":    "файл не найден:",
        "val_error_status": "Ошибка",
    },
}

CURRENT_LANG = "en"

def T(key):
    return STRINGS.get(CURRENT_LANG, STRINGS["en"]).get(key, key)

# ══════════════════════════════════════════════════════
#  DEFAULT TEST DATA
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
    {
        "MSISDN": "102989142", "SIMCARD": "2411010161242",
        "DOC_NUMBER": "AA3386082", "DOC_PIN": "7K51ES2",
        "TARIFF": "371", "PLAN_TYPE": "Prepaid",
        "PLAN_TYPE_REG": "Prepaid", "TARIFF_TYPE": "flat"
    },
]

TARIFF_TYPE_MAP  = {"Individual": "flat", "Corporate": "lat"}
TARIFF_TYPE_RMAP = {v: k for k, v in TARIFF_TYPE_MAP.items()}
CITY_MAP         = {"Baku": "Bak@012@"}

# ══════════════════════════════════════════════════════
#  MSISDN FIELD METADATA
# ══════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════
FONT_MONO    = ("Consolas", 12)
FONT_MONO_S  = ("Consolas", 11)
FONT_UI      = ("Segoe UI", 13)
FONT_UI_B    = ("Segoe UI", 13, "bold")
FONT_HEAD    = ("Segoe UI", 19, "bold")
FONT_LABEL   = ("Segoe UI", 11)
FONT_SECTION = ("Segoe UI", 10, "bold")
FONT_TAB     = ("Segoe UI", 13, "bold")