"""
tab_activation.py — Tab 2: Activation (Dealer Online — API)
Modern card-based live console + clean table summary.
"""
import re
import threading
import queue
from copy import deepcopy
from datetime import datetime

import customtkinter as ctk
import requests

from config import (C, FONT_UI, FONT_UI_B, FONT_MONO_S, FONT_LABEL,
                    DEFAULT_TEST_DATA, TARIFF_TYPE_MAP, TARIFF_TYPE_RMAP, CITY_MAP,
                    save_state, load_section)
from widgets import mk_section, mk_field, mk_divider, mk_panel_header, mk_label



# ══════════════════════════════════════════════════════
#  DIALOG HELPER — center on parent monitor
# ══════════════════════════════════════════════════════
def _center_on_parent(dlg, parent, w=480, h=600):
    parent.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    dlg.geometry(f"{w}x{h}+{px+(pw-w)//2}+{py+(ph-h)//2}")


def _style_dialog(dlg):
    """Dark title bar + app icon. Re-applies icon at multiple delays to
    override CTk's own after() calls that reset it to the blue default."""
    import os as _os
    _ico = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Logo", "azercell.ico")
    _ico = _ico if _os.path.exists(_ico) else None

    def _apply():
        try:
            if _ico:
                dlg.iconbitmap(_ico)
        except Exception:
            pass
        try:
            from ctypes import windll, byref, sizeof, c_int
            dlg.update_idletasks()
            hwnd = windll.user32.GetParent(dlg.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x1E0A12)), sizeof(c_int))
        except Exception:
            pass

    # Apply immediately and then beat CTk's delayed icon-reset calls
    _apply()
    dlg.after(10,  _apply)
    dlg.after(100, _apply)
    dlg.after(300, _apply)

# ══════════════════════════════════════════════════════
#  PIPELINE STEPS
# ══════════════════════════════════════════════════════
STEPS_POSTPAID = ["Login", "Check MHM", "Register"]
STEPS_PREPAID  = ["Login", "Check MHM", "Register"]

# PostPaid tariff display names
TARIFF_RCODE_MAP = {
    "371": "Yeni Her Yere",
    "939": "SuperSen 3GB",
    "940": "SuperSen 6GB",
    "941": "SuperSen 10GB",
    "942": "SuperSen 20GB",
    "943": "SuperSen 30GB",
}

# Prepaid tariff codes -> display names
PREPAID_TARIFF_MAP = {
    "1091": "DigiMax Daily",
    "1098": "DigiMax Weekly",
    "1105": "DigiMax 3GB",
    "1112": "DigiMax 5GB",
    "1118": "DigiMax 10GB",
    "1129": "DigiMax 25GB",
    "935":  "Travel Pack 30GB",
    "1132": "Premium+ 60GB",
    "1194": "Premium+ 100GB",
}
PREPAID_TARIFF_RMAP = {v: k for k, v in PREPAID_TARIFF_MAP.items()}

# ══════════════════════════════════════════════════════
#  ERROR MESSAGE CLEANER
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
#  API HELPERS
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

    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20,
        max_retries=2,
        pool_block=False,
    )
    s.mount("https://", adapter)
    s.mount("http://",  adapter)

    s.headers.update({
        "User-Agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Accept-Language":   "en-US,en;q=0.9",
        "Accept":            "text/html,application/xhtml+xml,application/xml;q=0.9,"
                             "image/avif,image/webp,image/apng,*/*;q=0.8,"
                             "application/signed-exchange;v=b3;q=0.7",
        "sec-ch-ua":         '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile":  "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
    })

    s.get(
        f"{base_url}/login",
        headers={"Sec-Fetch-Dest": "document",
                 "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Site": "none",
                 "Cache-Control":  "max-age=0"},
        allow_redirects=True,
        timeout=20,
    )

    login_resp = s.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        headers={"Content-Type":  "application/x-www-form-urlencoded",
                 "Origin":         base_url,
                 "Referer":        f"{base_url}/login",
                 "Sec-Fetch-Dest": "document",
                 "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Site": "same-origin",
                 "Sec-Fetch-User": "?1",
                 "Cache-Control":  "max-age=0"},
        allow_redirects=False,
        timeout=20,
    )

    location = login_resp.headers.get("Location", "")

    if login_resp.status_code in (301, 302, 303, 307, 308):
        if "/login" in location:
            raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")
        s.get(
            location if location.startswith("http") else f"{base_url}{location}",
            headers={"Sec-Fetch-Dest": "document",
                     "Sec-Fetch-Mode": "navigate",
                     "Sec-Fetch-Site": "same-origin"},
            allow_redirects=True,
            timeout=20,
        )
    elif login_resp.status_code == 200:
        body = login_resp.text.lower()
        if "invalid" in body or "incorrect" in body or "bad credentials" in body:
            raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")

    if not s.cookies.get("SESSION"):
        raise Exception("Login failed — Sessiya yaradıla bilmədi, istifadəçi adı/şifrəni yoxlayın")

    page = s.get(
        f"{base_url}/customer",
        headers={"Sec-Fetch-Dest": "document",
                 "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Site": "same-origin"},
        allow_redirects=True,
        timeout=20,
    )

    if "/login" in page.url:
        raise Exception("Login failed — İstifadəçi adı və ya şifrə səhvdir")

    csrf = _extract_csrf(page.text) or s.cookies.get("XSRF-TOKEN")
    if csrf:
        s.headers.update({"X-CSRF-TOKEN": csrf,
                          "X-Requested-With": "XMLHttpRequest"})
    else:
        s.headers.update({"X-Requested-With": "XMLHttpRequest"})

    return s


def check_mhm(session, base_url, data):
    r = session.get(
        f"{base_url}/customer/checkMHM",
        params={"documentType": "1", "documentNumber": data["DOC_NUMBER"],
                "msisdn": data["MSISDN"], "simcard": data["SIMCARD"],
                "customerType": data["PLAN_TYPE"], "companyVoen": "null",
                "documentPin": data["DOC_PIN"], "requestType": data["TARIFF_TYPE"],
                "companySun": "", "segmentType": ""},
        headers={"Accept":  "application/json, text/javascript, */*; q=0.01",
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
    r = session.get(
        f"{base_url}/customer/checkMHMAddVoucher",
        params={"voucher": voucher, "msisdn": msisdn, "serial": simcard},
        headers={"Accept":  "application/json, text/javascript, */*; q=0.01",
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
            fallback = (j.get("description") or j.get("detail") or
                        "Vauçer sistemdə tapılmadı")
            raise Exception(f"addVoucher: {fallback}")

    return j


def register_customer(session, base_url, data, consts):
    r = session.get(
        f"{base_url}/customer/registerCustomer",
        params={"country": consts["COUNTRY"], "city": consts["CITY"],
                "zip": consts["ZIP_CODE"], "tariff": data["TARIFF"],
                "imei": "", "msisdnDeviceType": "voice", "email": consts["EMAIL"],
                "additionalAddress": "", "additionalCity": "", "additional": "true",
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
        headers={"Accept": "application/json", "Referer": f"{base_url}/customer"},
        timeout=30)

    try:
        j = r.json()
    except Exception:
        j = None

    if isinstance(j, dict):
        err = (j.get("errorMessage") or j.get("message") or
               j.get("error") or j.get("description") or j.get("detail"))
        if err and str(err).strip().lower() not in ("", "null", "none"):
            err_clean = str(err).strip()
            raise Exception(f"registerCustomer failed: {err_clean}")
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
        log_q.put({
            "ts":     datetime.now().strftime("%H:%M:%S"),
            "msg":    msg,
            "level":  level,
            "msisdn": msisdn,
            "step":   step_idx,
            "total":  len(STEPS),
            "done":   done,
            "error":  error,
            "steps":  STEPS,
        })

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
        elif ("Login failed" in raw or "SESSION" in raw or
              "session invalid" in raw.lower() or "Sessiya" in raw or
              "VPN" in raw or "əlçatmaz" in raw or "timeout" in raw.lower()):
            step_idx = 0
        else:
            step_idx = 0

        msg = _clean_error(raw)
        log(step_idx, msg, "error", done=True, error=True)
        result_q.put({"MSISDN": msisdn, "PLAN_TYPE": data["PLAN_TYPE"],
                      "TARIFF": data.get("TARIFF", ""),
                      "TARIFF_TYPE": tariff_label, "STATUS": "FAILED", "ERROR": msg})


# ══════════════════════════════════════════════════════
#  MSISDN CARD
# ══════════════════════════════════════════════════════
class MsisdnCard:
    STEP_ICONS = ["🔐", "🔍", "📝", "🎟️"]

    def __init__(self, parent, msisdn, plan_type, tariff_type, index, steps=None):
        self.msisdn = msisdn
        self._steps = steps or STEPS_POSTPAID

        self._frame = ctk.CTkFrame(parent, fg_color=("#251540", "#EDE8F5"),
                                   corner_radius=12, border_width=1,
                                   border_color=("#3D2260", "#C4B0DC"))
        self._frame.pack(fill="x", padx=6, pady=(0, 8))

        hdr = ctk.CTkFrame(self._frame, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(10, 6))

        badge = ctk.CTkFrame(hdr, fg_color=("#5C2483", "#5C2483"),
                             width=26, height=26, corner_radius=6)
        badge.pack(side="left", padx=(0, 8))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=str(index),
                     font=("Segoe UI", 12, "bold"),
                     text_color="white").place(relx=.5, rely=.5, anchor="center")

        ctk.CTkLabel(hdr, text=msisdn,
                     font=("Consolas", 13, "bold"),
                     text_color=("#EDE8F5", "#1A0A2E")).pack(side="left")
        ctk.CTkLabel(hdr, text=f"  {plan_type}  ·  {tariff_type}",
                     font=("Segoe UI", 12),
                     text_color=("#8B75B0", "#6B5A8A")).pack(side="left", padx=4)

        self._ts_lbl = ctk.CTkLabel(hdr, text=datetime.now().strftime("%H:%M:%S"),
                                    font=("Consolas", 13),
                                    text_color=("#8B75B0", "#6B5A8A"))
        self._ts_lbl.pack(side="right")

        self._badge = ctk.CTkLabel(hdr, text="  ⏳ RUNNING  ",
                                   font=("Segoe UI", 12, "bold"),
                                   text_color=("#F59E0B", "#D97706"),
                                   fg_color=("#1C1030", "#FFFFFF"), corner_radius=6)
        self._badge.pack(side="right", padx=(0, 8))

        steps_row = ctk.CTkFrame(self._frame, fg_color="transparent")
        steps_row.pack(fill="x", padx=14, pady=(0, 4))

        self._step_widgets = []
        for i, name in enumerate(self._steps):
            sf = ctk.CTkFrame(steps_row, fg_color="transparent")
            sf.pack(side="left")
            icon_char = self.STEP_ICONS[i] if i < len(self.STEP_ICONS) else "▸"
            icon = ctk.CTkLabel(sf, text=icon_char, font=("Segoe UI", 12),
                                text_color=("#8B75B0", "#6B5A8A"))
            icon.pack(side="left", padx=(0, 2))
            lbl = ctk.CTkLabel(sf, text=name, font=("Segoe UI", 12),
                               text_color=("#8B75B0", "#6B5A8A"))
            lbl.pack(side="left")
            if i < len(self._steps) - 1:
                ctk.CTkLabel(sf, text="  →  ", font=("Segoe UI", 12),
                             text_color=("#3D2260", "#C4B0DC")).pack(side="left")
            self._step_widgets.append((icon, lbl, icon_char))

        self._detail = ctk.CTkLabel(self._frame, text="", font=("Consolas", 14),
                                    text_color=("#8B75B0", "#6B5A8A"), anchor="w")
        self._detail.pack(fill="x", padx=14, pady=(0, 10))

    def bind_scroll(self, scroll_fn):
        """Bind mousewheel on all widgets in this card to scroll_fn."""
        def _bind_all(widget):
            try:
                widget.bind("<MouseWheel>", lambda e: scroll_fn(e), add="+")
            except Exception:
                pass
            for child in widget.winfo_children():
                _bind_all(child)
        _bind_all(self._frame)

    def update_step(self, step_idx, msg, level, done=False, error=False):
        for i, (icon, lbl, icon_char) in enumerate(self._step_widgets):
            if i < step_idx:
                icon.configure(text="✓", text_color=("#22C55E", "#16A34A"))
                lbl.configure(text_color=("#22C55E", "#16A34A"))
            elif i == step_idx:
                if error:
                    icon.configure(text="✗", text_color=("#EF4444", "#DC2626"))
                    lbl.configure(text_color=("#EF4444", "#DC2626"))
                elif done:
                    icon.configure(text="✓", text_color=("#22C55E", "#16A34A"))
                    lbl.configure(text_color=("#22C55E", "#16A34A"))
                else:
                    icon.configure(text=icon_char, text_color=("#F59E0B", "#D97706"))
                    lbl.configure(text_color=("#F59E0B", "#D97706"))
            else:
                icon.configure(text=icon_char, text_color=("#8B75B0", "#6B5A8A"))
                lbl.configure(text_color=("#8B75B0", "#6B5A8A"))

        color_map = {"success": C["success"], "error": C["error"],
                     "warning": C["warning"], "info": C["muted"]}
        self._detail.configure(text=f"  ↳ {msg}",
                               text_color=color_map.get(level, C["muted"]))

        if done and not error:
            self._frame.configure(border_color=("#22C55E", "#16A34A"))
            self._badge.configure(text="  ✅ PASSED  ",
                                  text_color=("#22C55E", "#16A34A"), fg_color="#0B2210")
        elif done and error:
            self._frame.configure(border_color=("#EF4444", "#DC2626"))
            self._badge.configure(text="  ❌ FAILED  ",
                                  text_color=("#EF4444", "#DC2626"), fg_color="#2A0A0A")

        self._ts_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))


# ══════════════════════════════════════════════════════
#  OVERLAY DROPDOWN HELPER
# ══════════════════════════════════════════════════════
def _mk_overlay_dd(parent_row, dlg, values, default="", on_change=None):
    import tkinter as tk

    val    = default if default in values else (values[0] if values else "")
    var    = ctk.StringVar(value=val)
    _popup = [None]

    trigger = ctk.CTkFrame(
        parent_row,
        fg_color="#251540",
        corner_radius=8, border_width=1,
        border_color="#5C2483",
        cursor="hand2", height=36)
    trigger.pack(side="left", fill="x", expand=True)
    trigger.pack_propagate(False)

    lbl = ctk.CTkLabel(
        trigger, text=f"  {val}",
        font=FONT_MONO_S, anchor="w",
        text_color="#EDE8F5")
    lbl.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)

    arr = ctk.CTkLabel(
        trigger, text="▾",
        font=("Segoe UI", 12),
        text_color="#8B75B0", width=28)
    arr.pack(side="right", padx=(0, 6), pady=4)

    def _close():
        if _popup[0] is not None:
            try:
                _popup[0].destroy()
            except Exception:
                pass
            _popup[0] = None
        arr.configure(text="▾")

    def _select(v):
        var.set(v)
        lbl.configure(text=f"  {v}")
        _close()
        if on_change:
            on_change(v)

    def _open():
        _close()

        def _do_open():
            dlg.update_idletasks()

            try:
                row_w = parent_row.winfo_width()
                tw = max(row_w - 120 - 16, 140)
            except Exception:
                tw = max(trigger.winfo_width(), 140)

            rx = trigger.winfo_rootx()
            ry = trigger.winfo_rooty() + trigger.winfo_height()

            ITEM_H  = 26
            MAX_VIS = 7
            n       = len(values)
            vis     = min(n, MAX_VIS)
            popup_h = ITEM_H * vis + 2

            popup = tk.Toplevel(dlg)
            popup.wm_overrideredirect(True)
            popup.wm_geometry(f"{tw}x{popup_h}+{rx}+{ry}")
            popup.lift()
            popup.focus_set()
            popup.configure(bg="#3D2260")

            outer = tk.Frame(popup, bg="#5C2483", bd=0)
            outer.pack(fill="both", expand=True, padx=1, pady=1)

            canvas = tk.Canvas(outer, bg="#1E1035", highlightthickness=0, bd=0)
            canvas.pack(side="left", fill="both", expand=True)

            if n > MAX_VIS:
                sb = tk.Scrollbar(outer, orient="vertical",
                                  command=canvas.yview,
                                  troughcolor="#251540",
                                  bg="#5C2483", activebackground="#7C6EB0",
                                  width=8, bd=0, relief="flat",
                                  elementborderwidth=0, highlightthickness=0)
                sb.pack(side="right", fill="y")
                canvas.configure(yscrollcommand=sb.set)

            inner = tk.Frame(canvas, bg="#1E1035")
            win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_inner_cfg(e):
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfig(win_id, width=canvas.winfo_width())
            def _on_canvas_cfg(e):
                canvas.itemconfig(win_id, width=canvas.winfo_width())
            inner.bind("<Configure>", _on_inner_cfg)
            canvas.bind("<Configure>", _on_canvas_cfg)

            def _on_wheel(e):
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            canvas.bind_all("<MouseWheel>", _on_wheel)
            popup.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

            cur = var.get()
            for v in values:
                is_sel = (v == cur)
                bg_btn = "#5C2483" if is_sel else "#1E1035"
                fg_txt = "#FFFFFF" if is_sel else "#C4B0DC"

                row = tk.Frame(inner, bg=bg_btn, cursor="hand2")
                row.pack(fill="x")

                item_lbl = tk.Label(
                    row, text=v,
                    font=("Segoe UI", 11),
                    bg=bg_btn, fg=fg_txt,
                    anchor="w", padx=12, pady=0,
                    cursor="hand2")
                item_lbl.pack(fill="x", ipady=4)

                def _on_enter(e, r=row, l=item_lbl):
                    r.configure(bg="#3D2260")
                    l.configure(bg="#3D2260", fg="#FFFFFF")
                def _on_leave(e, r=row, l=item_lbl, s=is_sel):
                    c = "#5C2483" if s else "#1E1035"
                    r.configure(bg=c)
                    l.configure(bg=c, fg="#FFFFFF" if s else "#C4B0DC")
                def _on_click(e, v=v):
                    _select(v)

                row.bind("<Enter>", _on_enter)
                row.bind("<Leave>", _on_leave)
                row.bind("<Button-1>", _on_click)
                item_lbl.bind("<Enter>", _on_enter)
                item_lbl.bind("<Leave>", _on_leave)
                item_lbl.bind("<Button-1>", _on_click)

                sep = tk.Frame(inner, bg="#2D1A50", height=1)
                sep.pack(fill="x")

            def _check_outside(e):
                try:
                    px, py = popup.winfo_rootx(), popup.winfo_rooty()
                    pw, ph = popup.winfo_width(), popup.winfo_height()
                    mx, my = popup.winfo_pointerx(), popup.winfo_pointery()
                    if not (px <= mx <= px + pw and py <= my <= py + ph):
                        _close()
                except Exception:
                    _close()
            popup.bind("<Leave>", _check_outside)

            _popup[0] = popup
            arr.configure(text="▴")

        dlg.after(1, _do_open)

    def _toggle(e=None):
        if _popup[0] is not None:
            _close()
        else:
            _open()

    trigger.bind("<Button-1>", lambda e: (_toggle(), "break"))
    lbl.bind("<Button-1>",     lambda e: (_toggle(), "break"))
    arr.bind("<Button-1>",     lambda e: (_toggle(), "break"))

    return var


# ══════════════════════════════════════════════════════
#  TAB 2 UI CLASS
# ══════════════════════════════════════════════════════
class TabActivation:
    BASE_URL = "https://dealer-online.azercell.com"

    # Records per page in history
    HIST_PAGE_SIZE = 10

    def __init__(self, tab, log_q: queue.Queue, result_q: queue.Queue,
                 stop_ev: threading.Event, T):
        self._tab      = tab
        self._log_q    = log_q
        self._result_q = result_q
        self._stop_ev  = stop_ev
        self._T        = T
        self._running  = False
        self._results  = []
        self._history  = []
        self._test_data = deepcopy(DEFAULT_TEST_DATA)
        self._sel_row  = None
        self._cards: dict = {}
        # History pagination state
        self._hist_page = 1
        self._build()

    # ══════════════════════════════════════════════════
    #  CONSOLE MOUSEWHEEL FIX
    # ══════════════════════════════════════════════════
    def _get_console_scroll_fn(self):
        """Return a scroll function that targets the console's internal canvas."""
        try:
            canvas = self._console._parent_canvas
            return lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            return None

    def _bind_console_mousewheel(self, widget):
        """Recursively bind mousewheel on widget and all children to console scroll."""
        scroll_fn = self._get_console_scroll_fn()
        if scroll_fn is None:
            return
        def _bind_all(w):
            try:
                w.bind("<MouseWheel>", lambda e: scroll_fn(e), add="+")
            except Exception:
                pass
            for child in w.winfo_children():
                _bind_all(child)
        _bind_all(widget)

    def _build(self):
        T   = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=5)
        tab.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(
            tab, fg_color=("#1C1030", "#FFFFFF"), corner_radius=14,
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        mk_panel_header(left, T("config"))
        mk_section(left, T("login_online"))

        url_row = ctk.CTkFrame(left, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 7))
        ctk.CTkLabel(url_row, text="Base URL", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=135, anchor="w").pack(side="left")
        ctk.CTkLabel(url_row, text="dealer-online.azercell.com",
                     text_color=("#8B75B0", "#6B5A8A"), font=FONT_MONO_S).pack(side="left")

        self._cred_user = mk_field(left, "Username", "ccequlamova")
        self._cred_pass = mk_field(left, "Password", "dealeronline", show="*")

        mk_divider(left)
        mk_section(left, T("constants"))
        self._c_city    = mk_field(left, "City",        "Baku",               disabled=True)
        self._c_zip     = mk_field(left, "ZIP",         "AZC1122",            disabled=True)
        self._c_imp     = mk_field(left, "Importer",    "AZERCELL",           disabled=True)
        self._c_cur     = mk_field(left, "Curator",     "TEST",               disabled=True)
        self._c_country = mk_field(left, "Country",     "AZERBAIJAN",         disabled=True)
        self._c_nat     = mk_field(left, "Nationality", "AZERBAIJAN",         disabled=True)
        self._c_ph1p    = mk_field(left, "Phone Prefix","10")
        self._c_ph1n    = mk_field(left, "Phone Number","2210462")
        self._c_email   = mk_field(left, "Email",       "sgaziyev@azercell.com")

        mk_divider(left)
        mk_section(left, T("exec_mode"))
        self._thread_var = ctk.StringVar(value="parallel")
        rf = ctk.CTkFrame(left, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        rf.pack(fill="x", padx=16, pady=(0, 12))
        for txt, val in [(T("parallel"), "parallel"), (T("serial"), "serial")]:
            ctk.CTkRadioButton(
                rf, text=txt, variable=self._thread_var, value=val,
                font=FONT_LABEL, text_color=("#EDE8F5", "#1A0A2E"),
                fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0")
            ).pack(anchor="w", padx=14, pady=6)

        mk_divider(left)
        bf = ctk.CTkFrame(left, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=(6, 16))

        self._run_btn = ctk.CTkButton(
            bf, text=T("start"), font=("Segoe UI", 14, "bold"),
            fg_color=("#5C2483", "#5C2483"), hover_color=("#7C6EB0", "#7C6EB0"),
            height=46, corner_radius=10, command=self._on_run)
        self._run_btn.pack(fill="x", pady=(0, 8))

        self._cancel_btn = ctk.CTkButton(
            bf, text=T("cancel"), font=FONT_UI_B,
            fg_color=("#EF4444", "#DC2626"), hover_color="#B91C1C",
            height=40, corner_radius=10, state="disabled",
            command=self._on_cancel)
        self._cancel_btn.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            bf, text=T("clear_log"), font=FONT_UI,
            fg_color=("#251540", "#EDE8F5"), hover_color=("#3D2260", "#C4B0DC"),
            text_color=("#8B75B0", "#6B5A8A"), height=36, corner_radius=10,
            command=self.clear_log
        ).pack(fill="x")

        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=2)
        right.rowconfigure(3, weight=3)
        right.columnconfigure(0, weight=1)

        th = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12, height=52)
        th.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        th.pack_propagate(False)
        mk_label(th, T("test_data"), color=C["muted"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=18, pady=14)
        self._td_count = mk_label(th, f"{len(self._test_data)} {T('rows')}",
                                  color=C["accent"], font=FONT_MONO_S)
        self._td_count.pack(side="right", padx=10)
        ctk.CTkButton(th, text=T("delete"), width=70, height=30,
                      font=("Segoe UI", 14, "bold"), fg_color=("#EF4444", "#DC2626"),
                      hover_color="#B91C1C", corner_radius=8,
                      command=self._delete_sel).pack(side="right", pady=10)
        ctk.CTkButton(th, text="✎  Edit", width=80, height=30,
                      font=("Segoe UI", 14, "bold"), fg_color="#B45309", hover_color="#92400E",
                      text_color="white", corner_radius=8,
                      command=self._open_edit).pack(side="right", padx=6, pady=10)
        ctk.CTkButton(th, text=T("add"), width=90, height=30,
                      font=("Segoe UI", 14, "bold"), fg_color=("#5C2483", "#5C2483"),
                      hover_color=("#7C6EB0", "#7C6EB0"), corner_radius=8,
                      command=self._open_add).pack(side="right", padx=6, pady=10)

        # ── Canvas-based data table ────────────────────
        import tkinter as _tk2

        _tbl_outer = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"),
                                  corner_radius=12, border_width=1,
                                  border_color=("#3D2260", "#C4B0DC"))
        _tbl_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        _tbl_outer.columnconfigure(0, weight=1)
        _tbl_outer.rowconfigure(1, weight=1)

        # Column header
        _col_hdr = ctk.CTkFrame(_tbl_outer, fg_color=("#251540", "#DDD5EE"),
                                corner_radius=0, height=32)
        _col_hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=1, pady=(1,0))
        _col_hdr.pack_propagate(False)
        _COLS = [("#",28),("MSISDN",100),("SIMCARD",130),("DOC_NO",90),
                 ("PIN",72),("TARIFF",140),("PLAN",82),("TYPE",90),("VOUCHER",0)]
        for _cn, _cw in _COLS:
            ctk.CTkLabel(_col_hdr, text=_cn, font=("Segoe UI", 12, "bold"),
                         text_color=("#8B75B0","#6B5A8A"),
                         width=_cw or 0, anchor="w").pack(
                side="left", padx=(10 if _cn=="#" else 6, 2),
                fill="x" if not _cw else None, expand=(not _cw))

        _db_canvas = _tk2.Canvas(_tbl_outer, bg="#1C1030", highlightthickness=0, bd=0)
        _db_canvas.grid(row=1, column=0, sticky="nsew")
        _db_sb = ctk.CTkScrollbar(_tbl_outer, orientation="vertical",
                                  command=_db_canvas.yview,
                                  button_color=("#3D2260","#C4B0DC"),
                                  button_hover_color=("#7C6EB0","#7C6EB0"))
        _db_sb.grid(row=1, column=1, sticky="ns", pady=(0,1))
        _db_canvas.configure(yscrollcommand=_db_sb.set)
        _db_inner = ctk.CTkFrame(_db_canvas, fg_color=("#1C1030","#FFFFFF"), corner_radius=0)
        _db_inner_id = _db_canvas.create_window((0,0), window=_db_inner, anchor="nw")

        def _db_on_inner(e=None): _db_canvas.configure(scrollregion=_db_canvas.bbox("all"))
        def _db_on_canvas(e=None): _db_canvas.itemconfig(_db_inner_id, width=_db_canvas.winfo_width())
        _db_inner.bind("<Configure>", _db_on_inner)
        _db_canvas.bind("<Configure>", _db_on_canvas)
        def _db_mw(e): _db_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        _db_canvas.bind("<MouseWheel>", _db_mw)
        _db_inner.bind("<MouseWheel>", _db_mw)

        self._data_box   = None
        self._db_canvas  = _db_canvas
        self._db_inner   = _db_inner
        self._db_bind_mw = _db_mw
        self._render_data()

        ch = ctk.CTkFrame(right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12, height=52)
        ch.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ch.pack_propagate(False)
        mk_label(ch, "⚡  LIVE CONSOLE", color=C["muted"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=18, pady=14)
        self._progress_lbl = mk_label(ch, "", color=C["accent"], font=FONT_MONO_S)
        self._progress_lbl.pack(side="right", padx=6)
        self._res_summary = mk_label(ch, "—", color=C["muted"], font=FONT_MONO_S)
        self._res_summary.pack(side="right", padx=10)

        self._console = ctk.CTkScrollableFrame(
            right, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12,
            border_width=1, border_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_color=("#3D2260", "#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0", "#7C6EB0"))
        self._console.grid(row=3, column=0, sticky="nsew")
        self._console.columnconfigure(0, weight=1)

        self._show_placeholder()

        self._load_state()
        for w in [self._cred_user, self._cred_pass,
                  self._c_ph1p, self._c_ph1n, self._c_email]:
            w.bind("<FocusOut>", self._autosave)
            w.bind("<KeyRelease>", self._autosave)
        self._thread_var.trace_add("write", self._autosave)

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
                widget.configure(state="normal")
                widget.delete(0, "end")
                widget.insert(0, val)
        if s.get("mode"):
            self._thread_var.set(s["mode"])
        if s.get("test_data"):
            self._test_data = s["test_data"]
            self._render_data()
        if s.get("history"):
            self._history = s["history"]

    def _autosave(self, *_):
        save_state("activation", {
            "username":  self._cred_user.get(),
            "password":  self._cred_pass.get(),
            "ph1p":      self._c_ph1p.get(),
            "ph1n":      self._c_ph1n.get(),
            "email":     self._c_email.get(),
            "mode":      self._thread_var.get(),
            "test_data": self._test_data,
            "history":   self._history,
        })

    # ══════════════════════════════════════════════════
    #  CONSOLE STATES
    # ══════════════════════════════════════════════════
    def _show_placeholder(self):
        for w in self._console.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._console,
                     text="▶  Press START to begin activation",
                     font=("Segoe UI", 12),
                     text_color=("#8B75B0", "#6B5A8A")).pack(pady=28)

    def _show_summary(self):
        for w in self._console.winfo_children():
            w.destroy()

        T      = self._T
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")

        hcard = ctk.CTkFrame(self._console, fg_color=("#5C2483", "#5C2483"), corner_radius=12)
        hcard.pack(fill="x", padx=6, pady=(6, 10))
        ctk.CTkLabel(hcard, text=T("summary_title"),
                     font=("Segoe UI", 14, "bold"),
                     text_color="white").pack(side="left", padx=18, pady=12)

        stats = ctk.CTkFrame(hcard, fg_color="transparent")
        stats.pack(side="right", padx=18)
        for lbl, val, col in [
            (T("total"),  str(len(self._results)), "white"),
            (T("passed"), str(passed),              C["success"]),
            (T("failed"), str(failed),              C["error"] if failed else C["muted"]),
        ]:
            sf = ctk.CTkFrame(stats, fg_color=("#120A1E", "#F3F0F8"), corner_radius=8)
            sf.pack(side="left", padx=4, pady=8)
            ctk.CTkLabel(sf, text=val, font=("Segoe UI", 18, "bold"),
                         text_color=col).pack(padx=14, pady=(6, 0))
            ctk.CTkLabel(sf, text=lbl, font=("Segoe UI", 9),
                         text_color=("#8B75B0", "#6B5A8A")).pack(padx=14, pady=(0, 6))

        col_hdr = ctk.CTkFrame(self._console, fg_color=("#251540", "#EDE8F5"), corner_radius=8)
        col_hdr.pack(fill="x", padx=6, pady=(0, 4))
        for txt, w in [("#", 32), ("MSISDN", 120), ("Plan", 90),
                       ("Type", 90), ("Status", 110), ("Note", 0)]:
            ctk.CTkLabel(col_hdr, text=txt, font=("Segoe UI", 12, "bold"),
                         text_color=("#8B75B0", "#6B5A8A"), width=w or 0, anchor="w"
                         ).pack(side="left", padx=(12 if txt == "#" else 4, 4), pady=7,
                                fill="x" if not w else None, expand=(not w))

        for i, r in enumerate(self._results, 1):
            ok     = r["STATUS"] == "PASSED"
            row_bg = "#0B2210" if ok else "#2A0A0A"
            bdr    = C["success"] if ok else C["error"]

            rc = ctk.CTkFrame(self._console, fg_color=row_bg,
                              corner_radius=10, border_width=1, border_color=bdr)
            rc.pack(fill="x", padx=6, pady=2)

            ctk.CTkLabel(rc, text=str(i), font=("Consolas", 13),
                         text_color=("#8B75B0", "#6B5A8A"), width=32, anchor="w"
                         ).pack(side="left", padx=(12, 4), pady=9)
            ctk.CTkLabel(rc, text=r["MSISDN"], font=("Consolas", 13, "bold"),
                         text_color=("#EDE8F5", "#1A0A2E"), width=120, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc, text=r["PLAN_TYPE"], font=("Segoe UI", 14),
                         text_color=("#8B75B0", "#6B5A8A"), width=90, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc, text=r["TARIFF_TYPE"], font=("Segoe UI", 14),
                         text_color=("#8B75B0", "#6B5A8A"), width=90, anchor="w"
                         ).pack(side="left", padx=4, pady=9)
            ctk.CTkLabel(rc, text="  ✅ PASSED  " if ok else "  ❌ FAILED  ",
                         font=("Segoe UI", 12, "bold"),
                         text_color=("#22C55E", "#16A34A") if ok else C["error"],
                         fg_color=("#1C1030", "#FFFFFF"), corner_radius=6
                         ).pack(side="left", padx=4, pady=9)
            if r["ERROR"]:
                ctk.CTkLabel(rc, text=f"↳ {r['ERROR']}",
                             font=("Consolas", 13),
                             text_color=("#EF4444", "#DC2626"), anchor="w"
                             ).pack(side="left", padx=8, pady=9, fill="x", expand=True)

        # ── FIX: bind mousewheel for all summary rows ──
        self._console.after(50, lambda: self._bind_console_mousewheel(self._console))

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
        self._run_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._progress_lbl.configure(text="")
        self._res_summary.configure(text="—", text_color=("#8B75B0", "#6B5A8A"))

        for w in self._console.winfo_children():
            w.destroy()

        username  = self._cred_user.get().strip()
        password  = self._cred_pass.get().strip()
        consts    = self._get_consts()
        mode      = self._thread_var.get()
        data_list = deepcopy(self._test_data)

        for i, d in enumerate(data_list, 1):
            tt    = TARIFF_TYPE_RMAP.get(d["TARIFF_TYPE"], d["TARIFF_TYPE"])
            steps = STEPS_PREPAID if d.get("PLAN_TYPE", "").lower() == "prepaid" else STEPS_POSTPAID
            card  = MsisdnCard(self._console, d["MSISDN"], d["PLAN_TYPE"], tt, i, steps=steps)
            self._cards[d["MSISDN"]] = card
            # ── FIX: bind mousewheel so scrolling works when mouse is over cards ──
            try:
                sf_canvas = self._console._parent_canvas
                card.bind_scroll(
                    lambda e, c=sf_canvas: c.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            except Exception:
                pass

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

            self._tab.after(100, self._force_done)

        threading.Thread(target=worker, daemon=True).start()

    def _force_done(self):
        if self._stop_ev.is_set():
            return
        if self._results:
            self.on_done()
        else:
            self._running = False
            self._run_btn.configure(state="normal")
            self._cancel_btn.configure(state="disabled")

    def _on_cancel(self):
        self._stop_ev.set()
        self._running = False
        self._run_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        for msisdn, card in self._cards.items():
            badge_text = card._badge.cget("text")
            if "RUNNING" in badge_text:
                card._frame.configure(border_color=("#EF4444", "#DC2626"))
                card._badge.configure(
                    text="  🚫 CANCELLED  ",
                    text_color=("#EF4444", "#DC2626"),
                    fg_color="#2A0A0A")
                card._detail.configure(
                    text="  ↳ Process cancelled by user",
                    text_color=C["error"])
        ts = datetime.now().strftime("%H:%M:%S")
        cancel_card = ctk.CTkFrame(
            self._console,
            fg_color="#2A0A0A", corner_radius=10,
            border_width=1, border_color="#EF4444")
        cancel_card.pack(fill="x", padx=6, pady=(8, 2))
        ctk.CTkLabel(
            cancel_card,
            text=f"🚫  [{ts}]  Process cancelled by user",
            font=("Segoe UI", 14, "bold"),
            text_color="#EF4444"
        ).pack(padx=14, pady=10)
        # ── FIX: bind mousewheel on cancel card too ──
        try:
            sf_canvas = self._console._parent_canvas
            def _bind_cancel(w):
                try:
                    w.bind("<MouseWheel>",
                           lambda e, c=sf_canvas: c.yview_scroll(
                               int(-1*(e.delta/120)), "units"), add="+")
                except Exception:
                    pass
                for ch in w.winfo_children():
                    _bind_cancel(ch)
            _bind_cancel(cancel_card)
        except Exception:
            pass

    # ══════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════
    def is_running(self):
        return self._running

    def get_test_count(self):
        return len(self._test_data)

    def collect_result(self, r):
        self._results.append(r)
        passed = sum(1 for x in self._results if x["STATUS"] == "PASSED")
        failed = sum(1 for x in self._results if x["STATUS"] == "FAILED")
        done   = len(self._results)
        self._progress_lbl.configure(
            text=f"{done} / {len(self._test_data)}", text_color=("#8B75B0", "#6B5A8A"))
        self._res_summary.configure(
            text=f"✅ {passed}   ❌ {failed}",
            text_color=("#22C55E", "#16A34A") if failed == 0 else C["error"])

    def on_done(self):
        self._running = False
        self._run_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        passed = sum(1 for r in self._results if r["STATUS"] == "PASSED")
        failed = sum(1 for r in self._results if r["STATUS"] == "FAILED")
        for r in self._results:
            if r.get("STATUS") == "PASSED":
                entry = dict(r)
                # ── Store full datetime: "Mar 06  14:35:22" ──
                now = datetime.now()
                entry["TIME"] = now.strftime("%b %d  %H:%M:%S")
                entry["DATE"] = now.strftime("%b %d")
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
        card.update_step(
            kw.get("step", 0), msg, level,
            done=kw.get("done", False),
            error=kw.get("error", False))
        # ── FIX: re-bind mousewheel after each card update (new children may appear) ──
        try:
            sf_canvas = self._console._parent_canvas
            card.bind_scroll(
                lambda e, c=sf_canvas: c.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        except Exception:
            pass

    def clear_log(self):
        self._cards.clear()
        self._results.clear()
        self._res_summary.configure(text="—", text_color=("#8B75B0", "#6B5A8A"))
        self._progress_lbl.configure(text="")
        self._show_placeholder()

    # ══════════════════════════════════════════════════
    #  HISTORY WINDOW
    # ══════════════════════════════════════════════════
    def build_history_tab(self, parent):
        T = self._T

        # ── grid: row 0=filter, 1=stats, 2=tbl_wrap(col-hdr+list), 3=pagination ──
        parent.rowconfigure(2, weight=1)
        parent.rowconfigure(3, weight=0)
        parent.columnconfigure(0, weight=1)

        fc = ctk.CTkFrame(parent, fg_color=("#1C1030", "#FFFFFF"),
                          corner_radius=14, border_width=1,
                          border_color=("#3D2260", "#C4B0DC"))
        fc.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        fc.columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(fc, text="🔎  FILTER & SEARCH",
                     font=("Segoe UI", 12, "bold"),
                     text_color=("#5C2483", "#5C2483")
                     ).grid(row=0, column=0, columnspan=3,
                            sticky="w", padx=16, pady=(10, 4))

        col0 = ctk.CTkFrame(fc, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        col0.grid(row=1, column=0, sticky="nsew", padx=(12, 5), pady=(0, 12))
        ctk.CTkLabel(col0, text="📱  MSISDN", font=("Segoe UI", 12, "bold"),
                     text_color=("#8B75B0", "#6B5A8A")).pack(anchor="w", padx=12, pady=(8, 3))
        self._hist_msisdn_var = ctk.StringVar()
        ctk.CTkEntry(col0, textvariable=self._hist_msisdn_var,
                     placeholder_text="Type to search...",
                     fg_color=("#1C1030", "#FFFFFF"), border_color=("#3D2260", "#C4B0DC"),
                     text_color=("#EDE8F5", "#1A0A2E"),
                     placeholder_text_color=("#3D2260", "#C4B0DC"),
                     font=("Consolas", 13), height=36, corner_radius=8
                     ).pack(fill="x", padx=12, pady=(0, 10))
        self._hist_msisdn_var.trace_add("write", lambda *_: self._hist_reset_page())

        col1 = ctk.CTkFrame(fc, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        col1.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0, 12))
        ctk.CTkLabel(col1, text="📋  TARIFF", font=("Segoe UI", 12, "bold"),
                     text_color=("#8B75B0", "#6B5A8A")).pack(anchor="w", padx=12, pady=(8, 3))
        self._hist_tariff_var = ctk.StringVar(value="All Tariffs")
        all_tariffs = (["All Tariffs"]
                       + list(TARIFF_RCODE_MAP.values())
                       + list(PREPAID_TARIFF_MAP.values()))

        _ht_open = [False]
        _ht_btns = {}
        _ht_wrap = ctk.CTkFrame(col1, fg_color="transparent")
        _ht_wrap.pack(fill="x", padx=12, pady=(0, 10))

        def _ht_close():
            _ht_lf.pack_forget()
            _ht_open[0] = False
            _ht_arr.configure(text="▾")

        def _ht_select(v):
            self._hist_tariff_var.set(v)
            _ht_lbl.configure(text=f"  {v}")
            for t, b in _ht_btns.items():
                b.configure(
                    fg_color=("#5C2483","#5C2483") if t==v else "transparent",
                    text_color="white" if t==v else "#EDE8F5")
            _ht_close()
            self._hist_reset_page()

        def _ht_toggle():
            if _ht_open[0]:
                _ht_close()
            else:
                _ht_lf.pack(fill="x", pady=(0,2))
                _ht_open[0] = True
                _ht_arr.configure(text="▴")

        _ht_trigger = ctk.CTkFrame(
            _ht_wrap, fg_color=("#1C1030","#FFFFFF"),
            corner_radius=8, border_width=1,
            border_color=("#5C2483","#5C2483"),
            cursor="hand2", height=36)
        _ht_trigger.pack(fill="x", pady=(0,2))
        _ht_trigger.pack_propagate(False)
        _ht_trigger.bind("<Button-1>", lambda e: _ht_toggle())

        _ht_lbl = ctk.CTkLabel(
            _ht_trigger, text="  All Tariffs",
            font=("Segoe UI", 14), anchor="w",
            text_color=("#EDE8F5","#1A0A2E"))
        _ht_lbl.pack(side="left", fill="x", expand=True, padx=(4,0), pady=4)
        _ht_lbl.bind("<Button-1>", lambda e: _ht_toggle())

        _ht_arr = ctk.CTkLabel(
            _ht_trigger, text="▾",
            font=("Segoe UI", 12),
            text_color=("#8B75B0","#6B5A8A"), width=28)
        _ht_arr.pack(side="right", padx=(0,6), pady=4)
        _ht_arr.bind("<Button-1>", lambda e: _ht_toggle())

        _ht_n = len(all_tariffs)
        _ht_h = 32 * min(_ht_n, 5)
        _ht_lf = ctk.CTkScrollableFrame(
            _ht_wrap, fg_color=("#251540","#EDE8F5"), corner_radius=8, height=_ht_h,
            scrollbar_button_color=("#3D2260","#C4B0DC"),
            scrollbar_button_hover_color=("#7C6EB0","#7C6EB0"))

        for v in all_tariffs:
            b = ctk.CTkButton(
                _ht_lf, text=v, font=("Consolas", 13), height=28,
                anchor="w", corner_radius=6,
                fg_color=("#5C2483","#5C2483") if v=="All Tariffs" else "transparent",
                hover_color=("#3D2260","#C4B0DC"),
                text_color="white" if v=="All Tariffs" else "#EDE8F5",
                command=lambda v=v: _ht_select(v))
            b.pack(fill="x", pady=1, padx=4)
            _ht_btns[v] = b

        col2 = ctk.CTkFrame(fc, fg_color=("#251540", "#EDE8F5"), corner_radius=10)
        col2.grid(row=1, column=2, sticky="nsew", padx=(5, 12), pady=(0, 12))
        ctk.CTkLabel(col2, text="💳  PLAN TYPE", font=("Segoe UI", 12, "bold"),
                     text_color=("#8B75B0", "#6B5A8A")).pack(anchor="w", padx=12, pady=(8, 3))
        plan_row = ctk.CTkFrame(col2, fg_color="transparent")
        plan_row.pack(fill="x", padx=12, pady=(0, 6))
        plan_row.columnconfigure((0, 1, 2), weight=1)
        self._hist_plan_var = ctk.StringVar(value="All")
        self._plan_btns = {}
        for col_idx, (val, lbl) in enumerate([("All", "All"), ("PostPaid", "PostPaid"), ("Prepaid", "Prepaid")]):
            b = ctk.CTkButton(
                plan_row, text=lbl, height=28,
                font=("Segoe UI", 12, "bold"), corner_radius=7,
                fg_color=("#5C2483", "#5C2483") if val == "All" else ("#3D2260", "#C4B0DC"),
                hover_color=("#7C6EB0", "#7C6EB0"), text_color="white",
                command=lambda v=val: self._set_plan_chip(v))
            b.grid(row=0, column=col_idx, padx=(0, 3) if col_idx < 2 else 0, sticky="ew")
            self._plan_btns[val] = b

        # ── Stats bar ──────────────────────────────────
        self._hist_stats_bar = ctk.CTkFrame(parent, fg_color=("#1C1030", "#FFFFFF"),
                                            corner_radius=10, height=36)
        self._hist_stats_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self._hist_stats_bar.pack_propagate(False)
        self._hist_stats_lbl = ctk.CTkLabel(self._hist_stats_bar, text="",
                                            font=("Segoe UI", 14),
                                            text_color=("#8B75B0", "#6B5A8A"))
        self._hist_stats_lbl.pack(side="left", padx=14)

        import tkinter as _tk

        tbl_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        tbl_wrap.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tbl_wrap.columnconfigure(0, weight=1)
        tbl_wrap.rowconfigure(1, weight=1)

        # ── Column header ──────────────────────────────
        col_hdr = ctk.CTkFrame(tbl_wrap, fg_color=("#251540", "#EDE8F5"),
                               corner_radius=8, height=34)
        col_hdr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        col_hdr.pack_propagate(False)

        _HDR = [
            ("#",      32,  12, 4),
            ("Date",   68,  8,  4),
            ("Time",   72,  7,  4),
            ("MSISDN", 120, 7,  4),
            ("Plan",   88,  3,  4),
            ("Tariff", 130, 12, 4),
            ("Status", 108, 11, 4),
            ("Note",   0,   8,  4),
        ]
        for txt, w, pxl, pxr in _HDR:
            ctk.CTkLabel(col_hdr, text=txt, font=("Segoe UI", 12, "bold"),
                         text_color=("#8B75B0", "#6B5A8A"),
                         width=w if w else 0, anchor="w").pack(
                side="left", padx=(pxl, pxr), pady=7,
                fill="x" if not w else None, expand=(not w))

        # ── Native Canvas + Scrollbar ──────────────────
        _canvas_bg = "#1C1030"
        _hist_canvas = _tk.Canvas(tbl_wrap, bg=_canvas_bg,
                                  highlightthickness=0, bd=0)
        _hist_canvas.grid(row=1, column=0, sticky="nsew")

        _scrollbar = ctk.CTkScrollbar(
            tbl_wrap,
            orientation="vertical",
            command=_hist_canvas.yview,
            button_color=("#3D2260", "#C4B0DC"),
            button_hover_color=("#7C6EB0", "#7C6EB0"))
        _scrollbar.grid(row=1, column=1, sticky="ns")

        _hist_canvas.configure(yscrollcommand=_scrollbar.set)

        # Inner frame that holds all rows
        _inner = ctk.CTkFrame(_hist_canvas, fg_color=("#1C1030", "#FFFFFF"),
                              corner_radius=0)
        _inner_id = _hist_canvas.create_window((0, 0), window=_inner,
                                               anchor="nw")

        def _on_inner_configure(e=None):
            _hist_canvas.configure(scrollregion=_hist_canvas.bbox("all"))

        def _on_canvas_configure(e=None):
            _hist_canvas.itemconfig(_inner_id, width=_hist_canvas.winfo_width())

        _inner.bind("<Configure>", _on_inner_configure)
        _hist_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            _hist_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        _hist_canvas.bind("<MouseWheel>", _on_mousewheel)
        _inner.bind("<MouseWheel>", _on_mousewheel)

        def _bind_mousewheel(w):
            w.bind("<MouseWheel>", _on_mousewheel, add="+")
            for c in w.winfo_children():
                _bind_mousewheel(c)

        # Store references for _hist_refresh to use
        self._hist_scroll  = _inner          # pack rows into _inner
        self._hist_canvas  = _hist_canvas
        self._hist_bind_mw = _bind_mousewheel

        # ── Pagination bar ─────────────────────────────
        self._hist_page_bar = ctk.CTkFrame(parent, fg_color=("#1C1030", "#FFFFFF"),
                                           corner_radius=10, height=42)
        self._hist_page_bar.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._hist_page_bar.pack_propagate(False)

        self._hist_refresh()

    # ── Pagination helpers ─────────────────────────────
    def _hist_reset_page(self):
        self._hist_page = 1
        self._hist_refresh()

    def _hist_goto_page(self, page):
        self._hist_page = page
        self._hist_refresh()

    def _build_pagination(self, total_pages):
        """Rebuild the pagination bar for the current page."""
        bar = self._hist_page_bar
        for w in bar.winfo_children():
            w.destroy()

        if total_pages <= 1:
            return

        cur = self._hist_page

        # ← Prev
        ctk.CTkButton(
            bar, text="←", width=36, height=28,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#3D2260", "#C4B0DC") if cur > 1 else ("#251540", "#EDE8F5"),
            hover_color=("#5C2483", "#5C2483"),
            text_color="white" if cur > 1 else ("#3D2260", "#C4B0DC"),
            corner_radius=8,
            state="normal" if cur > 1 else "disabled",
            command=lambda: self._hist_goto_page(cur - 1)
        ).pack(side="left", padx=(10, 4), pady=6)

        # Page number buttons — show up to 7 buttons with ellipsis
        pages_to_show = self._page_window(cur, total_pages)

        prev_p = None
        for p in pages_to_show:
            if prev_p is not None and p - prev_p > 1:
                ctk.CTkLabel(bar, text="…", font=("Segoe UI", 12),
                             text_color=("#8B75B0", "#6B5A8A"),
                             width=24).pack(side="left", padx=2, pady=6)
            is_cur = (p == cur)
            ctk.CTkButton(
                bar, text=str(p), width=34, height=28,
                font=("Segoe UI", 14, "bold" if is_cur else "normal"),
                fg_color=("#5C2483", "#5C2483") if is_cur else ("#251540", "#EDE8F5"),
                hover_color=("#7C6EB0", "#7C6EB0"),
                text_color="white" if is_cur else ("#EDE8F5", "#1A0A2E"),
                corner_radius=8,
                border_width=2 if is_cur else 0,
                border_color=("#7C6EB0", "#7C6EB0") if is_cur else ("#5C2483", "#5C2483"),
                command=lambda p=p: self._hist_goto_page(p)
            ).pack(side="left", padx=2, pady=6)
            prev_p = p

        # → Next
        ctk.CTkButton(
            bar, text="→", width=36, height=28,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#3D2260", "#C4B0DC") if cur < total_pages else ("#251540", "#EDE8F5"),
            hover_color=("#5C2483", "#5C2483"),
            text_color="white" if cur < total_pages else ("#3D2260", "#C4B0DC"),
            corner_radius=8,
            state="normal" if cur < total_pages else "disabled",
            command=lambda: self._hist_goto_page(cur + 1)
        ).pack(side="left", padx=(4, 10), pady=6)



    @staticmethod
    def _page_window(cur, total, max_btns=7):
        """Return a sorted list of page numbers to display (no ellipsis gaps here,
        caller inserts '…' when consecutive pages differ by > 1)."""
        if total <= max_btns:
            return list(range(1, total + 1))
        # Always show first, last, current and neighbours
        must = {1, total, cur}
        for d in (-2, -1, 1, 2):
            p = cur + d
            if 1 <= p <= total:
                must.add(p)
        # Fill up to max_btns from the middle
        result = sorted(must)
        if len(result) < max_btns:
            extras = [p for p in range(1, total + 1) if p not in must]
            for p in extras:
                result.append(p)
                if len(result) >= max_btns:
                    break
            result = sorted(result)
        return result

    def _set_plan_chip(self, val):
        self._hist_plan_var.set(val)
        for v, btn in self._plan_btns.items():
            btn.configure(fg_color=("#5C2483", "#5C2483") if v == val else ("#3D2260", "#C4B0DC"))
        self._hist_reset_page()

    def _set_status_chip(self, val):
        self._hist_status_var.set(val)
        for v, btn in self._status_btns.items():
            active = v == val
            btn.configure(fg_color=self._status_colors[v] if active else "#2A1A2A")
        self._hist_reset_page()

    def _hist_refresh(self):
        if not hasattr(self, "_hist_scroll"):
            return
        for w in self._hist_scroll.winfo_children():
            w.destroy()
        # Reset scroll to top
        if hasattr(self, "_hist_canvas"):
            self._hist_canvas.yview_moveto(0)

        T = self._T

        msisdn_q = self._hist_msisdn_var.get().strip() if hasattr(self, "_hist_msisdn_var") else ""
        tariff_q = self._hist_tariff_var.get()         if hasattr(self, "_hist_tariff_var") else "All Tariffs"
        plan_q   = self._hist_plan_var.get()           if hasattr(self, "_hist_plan_var")   else "All"

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
        if hasattr(self, "_hist_stats_lbl"):
            self._hist_stats_lbl.configure(
                text=f"  {total} record{'s' if total != 1 else ''}  ·  ✅ {passed}  ·  ❌ {failed}")

        # ── Pagination ─────────────────────────────────
        page_size   = self.HIST_PAGE_SIZE
        total_pages = max(1, (total + page_size - 1) // page_size)
        # Clamp current page
        if self._hist_page > total_pages:
            self._hist_page = total_pages
        if self._hist_page < 1:
            self._hist_page = 1
        cur_page = self._hist_page

        # Slice — show newest first (reversed), then paginate
        rows_rev = list(reversed(rows))
        start    = (cur_page - 1) * page_size
        end      = start + page_size
        page_rows = rows_rev[start:end]

        if not rows:
            ctk.CTkLabel(self._hist_scroll, text=T("hist_empty"),
                         font=("Segoe UI", 12),
                         text_color=("#8B75B0", "#6B5A8A")).pack(pady=32)
        else:
            # Global row number = reversed index across all filtered rows
            for i, r in enumerate(page_rows, start + 1):
                ok     = r.get("STATUS") == "PASSED"
                row_bg = "#0B2210" if ok else "#2A0A0A"
                bdr    = "#22C55E" if ok else "#EF4444"

                rc = ctk.CTkFrame(self._hist_scroll, fg_color=row_bg,
                                  corner_radius=10, border_width=1, border_color=bdr)
                rc.pack(fill="x", padx=4, pady=2)

                # ── Row cells — padx mirrors COL_DEFS in build_history_tab ──
                ctk.CTkLabel(rc, text=str(i), font=("Consolas", 13),
                             text_color=("#8B75B0", "#6B5A8A"), width=32, anchor="w"
                             ).pack(side="left", padx=(12, 4), pady=8)

                # Date / Time (backward compat with old TIME-only entries)
                date_str  = r.get("DATE",  "")
                clock_str = r.get("CLOCK", "")
                if not date_str:
                    raw_time = r.get("TIME", "—")
                    parts = raw_time.split()
                    if len(parts) >= 3:
                        date_str  = f"{parts[0]} {parts[1]}"
                        clock_str = parts[2] if len(parts) > 2 else ""
                    elif len(parts) == 2:
                        date_str  = f"{parts[0]} {parts[1]}"
                        clock_str = ""
                    else:
                        date_str  = raw_time
                        clock_str = ""

                ctk.CTkLabel(rc, text=date_str, font=("Consolas", 13),
                             text_color=("#8B75B0", "#6B5A8A"), width=68, anchor="w"
                             ).pack(side="left", padx=(4, 4), pady=8)
                ctk.CTkLabel(rc, text=clock_str, font=("Consolas", 13),
                             text_color=("#8B75B0", "#6B5A8A"), width=72, anchor="w"
                             ).pack(side="left", padx=(4, 4), pady=8)
                ctk.CTkLabel(rc, text=r.get("MSISDN", "—"), font=("Consolas", 13, "bold"),
                             text_color=("#EDE8F5", "#1A0A2E"), width=120, anchor="w"
                             ).pack(side="left", padx=(4, 4), pady=8)
                ctk.CTkLabel(rc, text=r.get("PLAN_TYPE", "—"), font=("Segoe UI", 14),
                             text_color=("#8B75B0", "#6B5A8A"), width=88, anchor="w"
                             ).pack(side="left", padx=(4, 4), pady=8)
                tariff_code = r.get("TARIFF", "")
                tariff_display = (TARIFF_RCODE_MAP.get(tariff_code)
                                  or PREPAID_TARIFF_MAP.get(tariff_code)
                                  or r.get("TARIFF_TYPE", "—"))
                ctk.CTkLabel(rc, text=tariff_display, font=("Segoe UI", 14),
                             text_color=("#8B75B0", "#6B5A8A"), width=130, anchor="w"
                             ).pack(side="left", padx=(4, 4), pady=8)
                ctk.CTkLabel(rc, text="  ✅ PASSED  " if ok else "  ❌ FAILED  ",
                             font=("Segoe UI", 12, "bold"),
                             text_color=("#22C55E", "#16A34A") if ok else "#EF4444",
                             fg_color=("#1C1030", "#FFFFFF"), corner_radius=6
                             ).pack(side="left", padx=(4, 4), pady=8)
                if r.get("ERROR"):
                    ctk.CTkLabel(rc, text=f"↳ {r['ERROR']}",
                                 font=("Consolas", 13),
                                 text_color=("#EF4444", "#DC2626"), anchor="w"
                                 ).pack(side="left", padx=(8, 4), pady=8, fill="x", expand=True)

        # ── Rebuild pagination bar ─────────────────────
        if hasattr(self, "_hist_page_bar"):
            self._build_pagination(total_pages)

        # ── Re-bind mousewheel after render ───────────
        if hasattr(self, "_hist_bind_mw"):
            self._hist_scroll.after(50, lambda: self._hist_bind_mw(self._hist_scroll))

    # ══════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════
    def _get_consts(self):
        city = self._c_city.get()
        return {
            "CITY":           CITY_MAP.get(city, city),
            "ZIP_CODE":       self._c_zip.get(),
            "IMPORTER":       self._c_imp.get(),
            "CURATOR":        self._c_cur.get(),
            "COUNTRY":        self._c_country.get(),
            "NATIONALITY":    self._c_nat.get(),
            "PHONE_1_PREFIX": self._c_ph1p.get(),
            "PHONE_1_NUMBER": self._c_ph1n.get(),
            "EMAIL":          self._c_email.get(),
        }

    def _render_data(self):
        """Full rebuild — only called when data changes (add/delete/edit)."""
        if not hasattr(self, "_db_inner") or self._db_inner is None:
            return
        import tkinter as _tk3
        import customtkinter as _ctk

        for w in self._db_inner.winfo_children():
            w.destroy()
        if hasattr(self, "_db_canvas"):
            self._db_canvas.yview_moveto(0)

        self._db_rows = []   # list of (frame, [label, ...])

        COL_W = [28, 100, 130, 90, 72, 140, 82, 90, 0]
        PADX  = 10
        muted = ("#8B75B0", "#6B5A8A")

        for i, d in enumerate(self._test_data):
            # separator before each row except first
            if i > 0:
                _tk3.Frame(self._db_inner, bg="#2A1A45", height=1).pack(fill="x")

            is_even  = (i % 2 == 0)
            norm_bg  = "#1C1030" if is_even else "#160C28"

            tt = TARIFF_TYPE_RMAP.get(d.get("TARIFF_TYPE",""), d.get("TARIFF_TYPE",""))
            if d.get("PLAN_TYPE","").lower() == "prepaid":
                tr = PREPAID_TARIFF_MAP.get(d.get("TARIFF",""), d.get("TARIFF","—"))
            else:
                tr = TARIFF_RCODE_MAP.get(d.get("TARIFF",""), d.get("TARIFF",""))

            plan     = d.get("PLAN_TYPE","")
            plan_clr = ("#22C55E","#16A34A") if plan.lower()=="postpaid" else ("#F59E0B","#D97706")

            rc = _ctk.CTkFrame(self._db_inner, fg_color=norm_bg,
                               corner_radius=0, height=38)
            rc.pack(fill="x")
            rc.pack_propagate(False)

            cells = [
                (str(i+1),               COL_W[0], ("Consolas", 13),        muted),
                (d.get("MSISDN",""),      COL_W[1], ("Consolas", 13,"bold"), ("#EDE8F5","#1A0A2E")),
                (d.get("SIMCARD",""),     COL_W[2], ("Consolas", 13),        muted),
                (d.get("DOC_NUMBER",""),  COL_W[3], ("Consolas", 13),        muted),
                (d.get("DOC_PIN",""),     COL_W[4], ("Consolas", 13),        muted),
                (tr,                      COL_W[5], ("Consolas", 13),        ("#EDE8F5","#1A0A2E")),
                (plan,                    COL_W[6], ("Consolas", 13,"bold"), plan_clr),
                (tt,                      COL_W[7], ("Consolas", 13),        muted),
                (d.get("VOUCHER",""),     COL_W[8], ("Consolas", 13),        muted),
            ]

            lbls = []
            for ci, (val, cw, fnt, clr) in enumerate(cells):
                px = (PADX, 2) if ci == 0 else (6, 2)
                lbl = _ctk.CTkLabel(rc, text=val, font=fnt, text_color=clr,
                                    width=cw or 0, anchor="w")
                lbl.pack(side="left", padx=px,
                         fill="x" if not cw else None, expand=(not cw))
                lbls.append(lbl)

            self._db_rows.append((rc, norm_bg, lbls))

            def _bind_row(widget, idx=i):
                widget.bind("<Button-1>",
                            lambda e, x=idx: self._on_row_click_idx(x))
                widget.bind("<MouseWheel>",
                            lambda e: self._db_canvas.yview_scroll(
                                int(-1*(e.delta/120)), "units"))
            _bind_row(rc)
            for lbl in lbls:
                _bind_row(lbl)

        self._td_count.configure(text=f"{len(self._test_data)} {self._T('rows')}")
        # apply selection highlight without rebuild
        self._apply_row_selection()

    def _apply_row_selection(self):
        """Recolor rows for current selection — no widget rebuild, no flicker."""
        if not hasattr(self, "_db_rows"):
            return
        for i, (rc, norm_bg, lbls) in enumerate(self._db_rows):
            is_sel  = (self._sel_row == i)
            row_bg  = "#3D1A6B" if is_sel else norm_bg
            txt_clr = ("#C4B0DC","#1A0A2E") if is_sel else ("#EDE8F5","#1A0A2E")
            try:
                rc.configure(fg_color=row_bg)
                # update MSISDN (col 1) and TARIFF (col 5) text color
                lbls[1].configure(text_color=txt_clr)
                lbls[5].configure(text_color=txt_clr)
            except Exception:
                pass

    def _on_row_click(self, event):
        pass  # legacy

    def _on_row_click_idx(self, idx):
        self._sel_row = idx if 0 <= idx < len(self._test_data) else None
        self._apply_row_selection()   # instant, no flicker

    def _delete_sel(self):
        if self._sel_row is None:
            return
        del self._test_data[self._sel_row]
        self._sel_row = None
        self._render_data()
        self._autosave()

    def _open_add(self):
        T   = self._T
        dlg = ctk.CTkToplevel(self._tab)
        dlg.title(T(""))
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()

        _add_win = load_section("add_dialog_window")
        _add_restored = False
        if _add_win:
            try:
                _geo = _add_win.get("geometry", "")
                if _geo:
                    dlg.geometry(_geo)
                    _add_restored = True
            except Exception:
                pass
        if not _add_restored:
            _center_on_parent(dlg, self._tab, w=500, h=660)

        _style_dialog(dlg)

        if _add_win and _add_win.get("maximized"):
            dlg.after(150, lambda: dlg.state("zoomed"))

        _add_geo_save_id = [None]
        _add_last_normal_geo = [dlg.geometry()]

        def _add_save_state():
            try:
                is_max = dlg.state() == "zoomed"
                geo = _add_last_normal_geo[0] if is_max else dlg.geometry()
                if not is_max:
                    _add_last_normal_geo[0] = geo
                save_state("add_dialog_window", {"geometry": geo, "maximized": is_max})
            except Exception:
                pass

        def _add_on_configure(event=None):
            try:
                if dlg.state() != "zoomed":
                    _add_last_normal_geo[0] = dlg.geometry()
            except Exception:
                pass
            if _add_geo_save_id[0] is not None:
                dlg.after_cancel(_add_geo_save_id[0])
            _add_geo_save_id[0] = dlg.after(600, _add_save_state)

        dlg.bind("<Configure>", _add_on_configure)

        dh = ctk.CTkFrame(dlg, fg_color=("#5C2483", "#5C2483"), corner_radius=0, height=52)
        dh.pack(fill="x")
        dh.pack_propagate(False)
        ctk.CTkLabel(dh, text=T("add_dialog"), font=("Segoe UI", 14, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        fields = {}
        frm = ctk.CTkScrollableFrame(dlg, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12)
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        for key in ["MSISDN", "DOC_NUMBER", "DOC_PIN"]:
            row = ctk.CTkFrame(frm, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(row, text=key, text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_LABEL, width=120, anchor="w").pack(side="left")
            if key == "MSISDN":
                vcmd = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 9), "%P")
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
                                 validate="key", validatecommand=vcmd)
            else:
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36)
            e.pack(side="left", fill="x", expand=True)
            fields[key] = e

        sc_row = ctk.CTkFrame(frm, fg_color="transparent")
        sc_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(sc_row, text="SIMCARD", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        prefix_lbl = ctk.CTkEntry(sc_row, fg_color=("#3D2260", "#C4B0DC"),
                                  border_color=("#3D2260", "#C4B0DC"),
                                  text_color=("#8B75B0", "#6B5A8A"),
                                  font=FONT_MONO_S, height=36, width=80)
        prefix_lbl.insert(0, "8999401")
        prefix_lbl.configure(state="disabled")
        prefix_lbl.pack(side="left", padx=(0, 4))
        sc_vcmd = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 13), "%P")
        sc_entry = ctk.CTkEntry(sc_row, fg_color=("#251540", "#EDE8F5"),
                                border_color=("#3D2260", "#C4B0DC"),
                                text_color=("#EDE8F5", "#1A0A2E"),
                                font=FONT_MONO_S, height=36,
                                validate="key", validatecommand=sc_vcmd)
        sc_entry.pack(side="left", fill="x", expand=True)

        pt_row = ctk.CTkFrame(frm, fg_color="transparent")
        pt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(pt_row, text="PLAN_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")

        POSTPAID_CODE_MAP = {
            "Yeni Her Yere": "371", "SuperSen 3GB":  "939",
            "SuperSen 6GB":  "940", "SuperSen 10GB": "941",
            "SuperSen 20GB": "942", "SuperSen 30GB": "943",
        }
        PREPAID_CODE_MAP_LOCAL = {v: k for k, v in PREPAID_TARIFF_MAP.items()}

        tr_row = ctk.CTkFrame(frm, fg_color="transparent")
        tr_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tr_row, text="TARIFF", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")

        tr_var = ctk.StringVar(value="Yeni Her Yere")
        _tr_state  = {"open": False}
        _tr_btns   = {}
        _tr_popup  = [None]
        _tr_values = [list(POSTPAID_CODE_MAP.keys())]

        tr_trigger = ctk.CTkFrame(
            tr_row,
            fg_color=("#251540", "#EDE8F5"),
            corner_radius=8, border_width=1,
            border_color=("#5C2483", "#5C2483"),
            cursor="hand2", height=36)
        tr_trigger.pack(side="left", fill="x", expand=True)
        tr_trigger.pack_propagate(False)

        tr_lbl = ctk.CTkLabel(
            tr_trigger, text=f"  {tr_var.get()}",
            font=FONT_MONO_S, anchor="w",
            text_color=("#EDE8F5", "#1A0A2E"))
        tr_lbl.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)

        tr_arr = ctk.CTkLabel(
            tr_trigger, text="▾",
            font=("Segoe UI", 12),
            text_color=("#8B75B0", "#6B5A8A"), width=28)
        tr_arr.pack(side="right", padx=(0, 6), pady=4)

        def _tr_close():
            if _tr_popup[0] is not None:
                try:
                    _tr_popup[0].destroy()
                except Exception:
                    pass
                _tr_popup[0] = None
            tr_arr.configure(text="▾")

        def _tr_select(v):
            tr_var.set(v)
            tr_lbl.configure(text=f"  {v}")
            _tr_close()

        def _tr_open_popup():
            import tkinter as tk
            _tr_close()

            def _do():
                dlg.update_idletasks()
                rx = tr_trigger.winfo_rootx()
                ry = tr_trigger.winfo_rooty() + tr_trigger.winfo_height()
                try:
                    tw = max(tr_row.winfo_width() - 120 - 16, 140)
                except Exception:
                    tw = max(tr_trigger.winfo_width(), 140)

                vals    = _tr_values[0]
                ITEM_H  = 26
                MAX_VIS = 7
                n       = len(vals)
                popup_h = ITEM_H * min(n, MAX_VIS) + 2

                popup = tk.Toplevel(dlg)
                popup.wm_overrideredirect(True)
                popup.wm_geometry(f"{tw}x{popup_h}+{rx}+{ry}")
                popup.lift()
                popup.focus_set()
                popup.configure(bg="#3D2260")

                outer = tk.Frame(popup, bg="#5C2483", bd=0)
                outer.pack(fill="both", expand=True, padx=1, pady=1)

                canvas = tk.Canvas(outer, bg="#1E1035", highlightthickness=0, bd=0)
                canvas.pack(side="left", fill="both", expand=True)

                if n > MAX_VIS:
                    sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                                      troughcolor="#251540", bg="#5C2483",
                                      activebackground="#7C6EB0", width=8, bd=0,
                                      relief="flat", elementborderwidth=0, highlightthickness=0)
                    sb.pack(side="right", fill="y")
                    canvas.configure(yscrollcommand=sb.set)

                inner = tk.Frame(canvas, bg="#1E1035")
                win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

                def _on_ic(e):
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    canvas.itemconfig(win_id, width=canvas.winfo_width())
                def _on_cc(e):
                    canvas.itemconfig(win_id, width=canvas.winfo_width())
                inner.bind("<Configure>", _on_ic)
                canvas.bind("<Configure>", _on_cc)

                def _on_wheel_tr(e):
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
                canvas.bind_all("<MouseWheel>", _on_wheel_tr)
                popup.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

                cur = tr_var.get()
                for v in vals:
                    is_sel = (v == cur)
                    bg_r = "#5C2483" if is_sel else "#1E1035"
                    fg_r = "#FFFFFF" if is_sel else "#C4B0DC"

                    row = tk.Frame(inner, bg=bg_r, cursor="hand2")
                    row.pack(fill="x")
                    il = tk.Label(row, text=v, font=("Segoe UI", 11),
                                  bg=bg_r, fg=fg_r, anchor="w", padx=12, cursor="hand2")
                    il.pack(fill="x", ipady=4)

                    def _oe(e, r=row, l=il):
                        r.configure(bg="#3D2260"); l.configure(bg="#3D2260", fg="#FFFFFF")
                    def _ol(e, r=row, l=il, s=is_sel):
                        c = "#5C2483" if s else "#1E1035"
                        r.configure(bg=c); l.configure(bg=c, fg="#FFFFFF" if s else "#C4B0DC")
                    def _oc(e, v=v): _tr_select(v)

                    for w in (row, il):
                        w.bind("<Enter>", _oe)
                        w.bind("<Leave>", _ol)
                        w.bind("<Button-1>", _oc)

                    tk.Frame(inner, bg="#2D1A50", height=1).pack(fill="x")

                def _on_tr_leave(e):
                    try:
                        px, py = popup.winfo_rootx(), popup.winfo_rooty()
                        pw, ph = popup.winfo_width(), popup.winfo_height()
                        mx, my = popup.winfo_pointerx(), popup.winfo_pointery()
                        if not (px <= mx <= px + pw and py <= my <= py + ph):
                            _tr_close()
                    except Exception:
                        _tr_close()
                popup.bind("<Leave>", _on_tr_leave)

                _tr_popup[0] = popup
                tr_arr.configure(text="▴")

            dlg.after(1, _do)

        def _tr_toggle(e=None):
            if _tr_popup[0] is not None:
                _tr_close()
            else:
                _tr_open_popup()

        tr_trigger.bind("<Button-1>", lambda e: (_tr_toggle(), "break"))
        tr_lbl.bind("<Button-1>",     lambda e: (_tr_toggle(), "break"))
        tr_arr.bind("<Button-1>",     lambda e: (_tr_toggle(), "break"))

        tt_row = ctk.CTkFrame(frm, fg_color="transparent")
        tt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tt_row, text="TARIFF_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tt_var = _mk_overlay_dd(tt_row, dlg, list(TARIFF_TYPE_MAP.keys()), "Individual")

        vc_row = ctk.CTkFrame(frm, fg_color="transparent")
        ctk.CTkLabel(vc_row, text="VOUCHER 🎟️", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        vc_vcmd = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 13), "%P")
        vc_entry = ctk.CTkEntry(vc_row, fg_color=("#251540", "#EDE8F5"),
                                border_color=("#5C2483", "#5C2483"),
                                text_color=("#EDE8F5", "#1A0A2E"),
                                placeholder_text="13-digit voucher code",
                                placeholder_text_color=("#8B75B0", "#6B5A8A"),
                                font=FONT_MONO_S, height=36,
                                validate="key", validatecommand=vc_vcmd)
        vc_entry.pack(side="left", fill="x", expand=True)

        def _sync_plan(plan_val):
            if plan_val == "Prepaid":
                _tr_values[0] = list(PREPAID_CODE_MAP_LOCAL.keys())
                first = _tr_values[0][0]
                tr_var.set(first)
                tr_lbl.configure(text=f"  {first}")
                vc_row.pack(fill="x", padx=12, pady=5)
            else:
                _tr_values[0] = list(POSTPAID_CODE_MAP.keys())
                first = _tr_values[0][0]
                tr_var.set(first)
                tr_lbl.configure(text=f"  {first}")
                vc_row.pack_forget()
            _tr_close()

        pt_var = _mk_overlay_dd(pt_row, dlg, ["PostPaid", "Prepaid"], "PostPaid",
                                on_change=_sync_plan)

        def save():
            row_data = {k: v.get().strip() for k, v in fields.items()}
            row_data["SIMCARD"]       = sc_entry.get().strip()
            row_data["PLAN_TYPE"]     = pt_var.get()
            row_data["PLAN_TYPE_REG"] = pt_var.get()
            if pt_var.get() == "Prepaid":
                row_data["TARIFF"]  = PREPAID_CODE_MAP_LOCAL.get(tr_var.get(), "1091")
                row_data["VOUCHER"] = vc_entry.get().strip()
            else:
                row_data["TARIFF"]  = POSTPAID_CODE_MAP.get(tr_var.get(), "371")
                row_data["VOUCHER"] = ""
            row_data["TARIFF_TYPE"] = TARIFF_TYPE_MAP.get(tt_var.get(), "flat")
            if not row_data["MSISDN"] or not sc_entry.get().strip():
                return
            self._test_data.append(row_data)
            self._render_data()
            self._autosave()
            dlg.destroy()

        ctk.CTkButton(dlg, text=T("save"), fg_color=("#5C2483", "#5C2483"),
                      hover_color=("#7C6EB0", "#7C6EB0"), font=("Segoe UI", 14, "bold"),
                      height=44, corner_radius=10, command=save
                      ).pack(fill="x", padx=16, pady=(0, 16))

    def _open_edit(self):
        if self._sel_row is None:
            return
        d   = self._test_data[self._sel_row]
        T   = self._T
        dlg = ctk.CTkToplevel(self._tab)
        dlg.title("")
        dlg.configure(fg_color=("#120A1E", "#F3F0F8"))
        dlg.grab_set()

        _edit_win = load_section("edit_dialog_window")
        _edit_restored = False
        if _edit_win:
            try:
                _geo = _edit_win.get("geometry", "")
                if _geo:
                    dlg.geometry(_geo)
                    _edit_restored = True
            except Exception:
                pass
        if not _edit_restored:
            _center_on_parent(dlg, self._tab, w=500, h=600)

        _style_dialog(dlg)

        if _edit_win and _edit_win.get("maximized"):
            dlg.after(150, lambda: dlg.state("zoomed"))

        _edit_geo_save_id = [None]
        _edit_last_normal_geo = [dlg.geometry()]

        def _edit_save_state():
            try:
                is_max = dlg.state() == "zoomed"
                geo = _edit_last_normal_geo[0] if is_max else dlg.geometry()
                if not is_max:
                    _edit_last_normal_geo[0] = geo
                save_state("edit_dialog_window", {"geometry": geo, "maximized": is_max})
            except Exception:
                pass

        def _edit_on_configure(event=None):
            try:
                if dlg.state() != "zoomed":
                    _edit_last_normal_geo[0] = dlg.geometry()
            except Exception:
                pass
            if _edit_geo_save_id[0] is not None:
                dlg.after_cancel(_edit_geo_save_id[0])
            _edit_geo_save_id[0] = dlg.after(600, _edit_save_state)

        dlg.bind("<Configure>", _edit_on_configure)

        dh = ctk.CTkFrame(dlg, fg_color="#B45309", corner_radius=0, height=52)
        dh.pack(fill="x")
        dh.pack_propagate(False)
        ctk.CTkLabel(dh, text="✎  Edit Test Data", font=("Segoe UI", 14, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        fields = {}
        frm = ctk.CTkScrollableFrame(dlg, fg_color=("#1C1030", "#FFFFFF"), corner_radius=12)
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        for key in ["MSISDN", "DOC_NUMBER", "DOC_PIN"]:
            row = ctk.CTkFrame(frm, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(row, text=key, text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_LABEL, width=120, anchor="w").pack(side="left")
            if key == "MSISDN":
                vcmd = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 9), "%P")
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36,
                                 validate="key", validatecommand=vcmd)
            else:
                e = ctk.CTkEntry(row, fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                                 text_color=("#EDE8F5", "#1A0A2E"), font=FONT_MONO_S, height=36)
            e.pack(side="left", fill="x", expand=True)
            e.insert(0, d.get(key, ""))
            fields[key] = e

        sc_row = ctk.CTkFrame(frm, fg_color="transparent")
        sc_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(sc_row, text="SIMCARD", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        prefix_lbl = ctk.CTkEntry(sc_row, fg_color=("#3D2260", "#C4B0DC"),
                                  border_color=("#3D2260", "#C4B0DC"),
                                  text_color=("#8B75B0", "#6B5A8A"),
                                  font=FONT_MONO_S, height=36, width=80)
        prefix_lbl.insert(0, "8999401")
        prefix_lbl.configure(state="disabled")
        prefix_lbl.pack(side="left", padx=(0, 4))
        sc_vcmd = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 13), "%P")
        sc_entry = ctk.CTkEntry(sc_row, fg_color=("#251540", "#EDE8F5"),
                                border_color=("#3D2260", "#C4B0DC"),
                                text_color=("#EDE8F5", "#1A0A2E"),
                                font=FONT_MONO_S, height=36,
                                validate="key", validatecommand=sc_vcmd)
        sc_entry.pack(side="left", fill="x", expand=True)
        existing_sc = d.get("SIMCARD", "")
        sc_entry.insert(0, existing_sc[7:] if existing_sc.startswith("8999401") else existing_sc)

        POSTPAID_CODE_MAP_E = {
            "Yeni Her Yere": "371", "SuperSen 3GB":  "939",
            "SuperSen 6GB":  "940", "SuperSen 10GB": "941",
            "SuperSen 20GB": "942", "SuperSen 30GB": "943",
        }
        PREPAID_CODE_MAP_E = {v: k for k, v in PREPAID_TARIFF_MAP.items()}
        is_prepaid_now = d.get("PLAN_TYPE", "PostPaid") == "Prepaid"

        if is_prepaid_now:
            init_tr = PREPAID_TARIFF_MAP.get(d.get("TARIFF", ""), list(PREPAID_CODE_MAP_E.keys())[0])
        else:
            pp_rmap = {v: k for k, v in POSTPAID_CODE_MAP_E.items()}
            init_tr = pp_rmap.get(d.get("TARIFF", "371"), "Yeni Her Yere")

        init_plan_vals = list(PREPAID_CODE_MAP_E.keys()) if is_prepaid_now else list(POSTPAID_CODE_MAP_E.keys())
        _tr_values_e = [init_plan_vals]

        tr_row = ctk.CTkFrame(frm, fg_color="transparent")
        tr_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tr_row, text="TARIFF", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")

        tr_var = ctk.StringVar(value=init_tr)
        _tr_popup_e  = [None]

        tr_trigger_e = ctk.CTkFrame(
            tr_row,
            fg_color=("#251540", "#EDE8F5"),
            corner_radius=8, border_width=1,
            border_color=("#5C2483", "#5C2483"),
            cursor="hand2", height=36)
        tr_trigger_e.pack(side="left", fill="x", expand=True)
        tr_trigger_e.pack_propagate(False)

        tr_lbl_e = ctk.CTkLabel(
            tr_trigger_e, text=f"  {init_tr}",
            font=FONT_MONO_S, anchor="w",
            text_color=("#EDE8F5", "#1A0A2E"))
        tr_lbl_e.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)

        tr_arr_e = ctk.CTkLabel(
            tr_trigger_e, text="▾",
            font=("Segoe UI", 12),
            text_color=("#8B75B0", "#6B5A8A"), width=28)
        tr_arr_e.pack(side="right", padx=(0, 6), pady=4)

        def _tr_close_e():
            if _tr_popup_e[0] is not None:
                try:
                    _tr_popup_e[0].destroy()
                except Exception:
                    pass
                _tr_popup_e[0] = None
            tr_arr_e.configure(text="▾")

        def _tr_select_e(v):
            tr_var.set(v)
            tr_lbl_e.configure(text=f"  {v}")
            _tr_close_e()

        def _tr_open_popup_e():
            import tkinter as tk
            _tr_close_e()

            def _do():
                dlg.update_idletasks()
                rx = tr_trigger_e.winfo_rootx()
                ry = tr_trigger_e.winfo_rooty() + tr_trigger_e.winfo_height()
                try:
                    tw = max(tr_row.winfo_width() - 120 - 16, 140)
                except Exception:
                    tw = max(tr_trigger_e.winfo_width(), 140)

                vals    = _tr_values_e[0]
                ITEM_H  = 26
                MAX_VIS = 7
                n       = len(vals)
                popup_h = ITEM_H * min(n, MAX_VIS) + 2

                popup = tk.Toplevel(dlg)
                popup.wm_overrideredirect(True)
                popup.wm_geometry(f"{tw}x{popup_h}+{rx}+{ry}")
                popup.lift()
                popup.focus_set()
                popup.configure(bg="#3D2260")

                outer = tk.Frame(popup, bg="#5C2483", bd=0)
                outer.pack(fill="both", expand=True, padx=1, pady=1)

                canvas = tk.Canvas(outer, bg="#1E1035", highlightthickness=0, bd=0)
                canvas.pack(side="left", fill="both", expand=True)

                if n > MAX_VIS:
                    sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                                      troughcolor="#251540", bg="#5C2483",
                                      activebackground="#7C6EB0", width=8, bd=0,
                                      relief="flat", elementborderwidth=0, highlightthickness=0)
                    sb.pack(side="right", fill="y")
                    canvas.configure(yscrollcommand=sb.set)

                inner = tk.Frame(canvas, bg="#1E1035")
                win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

                def _on_ic(e):
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    canvas.itemconfig(win_id, width=canvas.winfo_width())
                def _on_cc(e):
                    canvas.itemconfig(win_id, width=canvas.winfo_width())
                inner.bind("<Configure>", _on_ic)
                canvas.bind("<Configure>", _on_cc)

                def _on_wheel_tre(e):
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
                canvas.bind_all("<MouseWheel>", _on_wheel_tre)
                popup.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

                cur = tr_var.get()
                for v in vals:
                    is_sel = (v == cur)
                    bg_r = "#5C2483" if is_sel else "#1E1035"
                    fg_r = "#FFFFFF" if is_sel else "#C4B0DC"

                    row = tk.Frame(inner, bg=bg_r, cursor="hand2")
                    row.pack(fill="x")
                    il = tk.Label(row, text=v, font=("Segoe UI", 11),
                                  bg=bg_r, fg=fg_r, anchor="w", padx=12, cursor="hand2")
                    il.pack(fill="x", ipady=4)

                    def _oe(e, r=row, l=il):
                        r.configure(bg="#3D2260"); l.configure(bg="#3D2260", fg="#FFFFFF")
                    def _ol(e, r=row, l=il, s=is_sel):
                        c = "#5C2483" if s else "#1E1035"
                        r.configure(bg=c); l.configure(bg=c, fg="#FFFFFF" if s else "#C4B0DC")
                    def _oc(e, v=v): _tr_select_e(v)

                    for w in (row, il):
                        w.bind("<Enter>", _oe)
                        w.bind("<Leave>", _ol)
                        w.bind("<Button-1>", _oc)

                    tk.Frame(inner, bg="#2D1A50", height=1).pack(fill="x")

                def _on_tr_leave_e(e):
                    try:
                        px, py = popup.winfo_rootx(), popup.winfo_rooty()
                        pw, ph = popup.winfo_width(), popup.winfo_height()
                        mx, my = popup.winfo_pointerx(), popup.winfo_pointery()
                        if not (px <= mx <= px + pw and py <= my <= py + ph):
                            _tr_close_e()
                    except Exception:
                        _tr_close_e()
                popup.bind("<Leave>", _on_tr_leave_e)

                _tr_popup_e[0] = popup
                tr_arr_e.configure(text="▴")

            dlg.after(1, _do)

        def _tr_toggle_e(e=None):
            if _tr_popup_e[0] is not None:
                _tr_close_e()
            else:
                _tr_open_popup_e()

        tr_trigger_e.bind("<Button-1>", lambda e: (_tr_toggle_e(), "break"))
        tr_lbl_e.bind("<Button-1>",     lambda e: (_tr_toggle_e(), "break"))
        tr_arr_e.bind("<Button-1>",     lambda e: (_tr_toggle_e(), "break"))

        pt_row = ctk.CTkFrame(frm, fg_color="transparent")
        pt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(pt_row, text="PLAN_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")

        tt_row = ctk.CTkFrame(frm, fg_color="transparent")
        tt_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(tt_row, text="TARIFF_TYPE", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        tt_var = _mk_overlay_dd(tt_row, dlg, list(TARIFF_TYPE_MAP.keys()),
                                TARIFF_TYPE_RMAP.get(d.get("TARIFF_TYPE", "flat"), "Individual"))

        vc_row_e = ctk.CTkFrame(frm, fg_color="transparent")
        ctk.CTkLabel(vc_row_e, text="VOUCHER 🎟️", text_color=("#8B75B0", "#6B5A8A"),
                     font=FONT_LABEL, width=120, anchor="w").pack(side="left")
        vc_vcmd_e = (dlg.register(lambda s: (s == "" or s.isdigit()) and len(s) <= 13), "%P")
        vc_entry_e = ctk.CTkEntry(vc_row_e, fg_color=("#251540", "#EDE8F5"),
                                  border_color=("#5C2483", "#5C2483"),
                                  text_color=("#EDE8F5", "#1A0A2E"),
                                  placeholder_text="13-digit voucher code",
                                  placeholder_text_color=("#8B75B0", "#6B5A8A"),
                                  font=FONT_MONO_S, height=36,
                                  validate="key", validatecommand=vc_vcmd_e)
        vc_entry_e.pack(side="left", fill="x", expand=True)
        vc_entry_e.insert(0, d.get("VOUCHER", ""))

        def _sync_plan_e(plan_val):
            if plan_val == "Prepaid":
                _tr_values_e[0] = list(PREPAID_CODE_MAP_E.keys())
                first = _tr_values_e[0][0]
                tr_var.set(first)
                tr_lbl_e.configure(text=f"  {first}")
                vc_row_e.pack(fill="x", padx=12, pady=5)
            else:
                _tr_values_e[0] = list(POSTPAID_CODE_MAP_E.keys())
                first = _tr_values_e[0][0]
                tr_var.set(first)
                tr_lbl_e.configure(text=f"  {first}")
                vc_row_e.pack_forget()
            _tr_close_e()

        pt_var = _mk_overlay_dd(pt_row, dlg, ["PostPaid", "Prepaid"],
                                d.get("PLAN_TYPE", "PostPaid"),
                                on_change=_sync_plan_e)

        if is_prepaid_now:
            vc_row_e.pack(fill="x", padx=12, pady=5)

        def save():
            row_data = {k: v.get().strip() for k, v in fields.items()}
            row_data["SIMCARD"]       = sc_entry.get().strip()
            row_data["PLAN_TYPE"]     = pt_var.get()
            row_data["PLAN_TYPE_REG"] = pt_var.get()
            if pt_var.get() == "Prepaid":
                row_data["TARIFF"]  = PREPAID_CODE_MAP_E.get(tr_var.get(), "1091")
                row_data["VOUCHER"] = vc_entry_e.get().strip()
            else:
                row_data["TARIFF"]  = POSTPAID_CODE_MAP_E.get(tr_var.get(), "371")
                row_data["VOUCHER"] = ""
            row_data["TARIFF_TYPE"] = TARIFF_TYPE_MAP.get(tt_var.get(), "flat")
            if not row_data["MSISDN"] or not sc_entry.get().strip():
                return
            self._test_data[self._sel_row] = row_data
            self._render_data()
            self._autosave()
            dlg.destroy()

        ctk.CTkButton(dlg, text="✎  Yadda Saxla", fg_color="#B45309",
                      hover_color="#92400E", text_color="white",
                      font=("Segoe UI", 14, "bold"),
                      height=44, corner_radius=10, command=save
                      ).pack(fill="x", padx=16, pady=(0, 16))