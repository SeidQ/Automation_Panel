"""
tab_msisdn.py — Tab 3: MSISDN Details (SFA API)
"""
import threading
import requests
import customtkinter as ctk

from config import (C, FONT_MONO_S, FONT_UI,
                    MSISDN_FIELD_META, MSISDN_GROUPS,
                    STATUS_MAP, SIM_STATUS_MAP, PAYMENT_MAP)
from widgets import mk_label

SFA_BASE_URL = "http://sfa-api.appazercell.prod/api/v1"
SFA_AUTH     = "Basic bmV3Y3VzdG9tZXI6cmVtb3RzdWN3ZW4="


# ══════════════════════════════════════════════════════
#  API
# ══════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════
#  TAB 3 UI CLASS
# ══════════════════════════════════════════════════════
class TabMSISDN:
    """Builds and owns Tab 3 — MSISDN Details."""

    # Layout: which group goes in which column / grid row
    _COL = {"identity": 0, "status": 1, "dealer": 2,
            "security": 0, "financial": 1, "misc": 2}
    _ROW = {"identity": 1, "status": 1, "dealer": 1,
            "security": 2, "financial": 2, "misc": 2}

    def __init__(self, tab, T):
        self._tab  = tab
        self._T    = T
        self._data = None
        self._build()

    # ── Build ──────────────────────────────────────────
    def _build(self):
        T   = self._T
        tab = self._tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # Search bar
        search_card = ctk.CTkFrame(tab, fg_color=C["card"], corner_radius=14, height=80)
        search_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        search_card.pack_propagate(False)

        ctk.CTkLabel(search_card, text=T("msisdn_title"),
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["muted"]).pack(side="left", padx=20)

        sr = ctk.CTkFrame(search_card, fg_color="transparent")
        sr.pack(side="right", padx=16, fill="y")

        ctk.CTkButton(sr, text=T("msisdn_clear"), width=88, height=42,
                      font=FONT_UI, fg_color=C["input"], hover_color=C["border"],
                      text_color=C["muted"], corner_radius=10,
                      command=self.clear).pack(side="right", padx=(6, 0))

        self._search_btn = ctk.CTkButton(
            sr, text=T("msisdn_search"), width=120, height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color=C["accent2"], hover_color=C["accent"],
            text_color="white", corner_radius=10,
            command=self.do_search)
        self._search_btn.pack(side="right", padx=(6, 0))

        self._entry = ctk.CTkEntry(
            sr, placeholder_text=T("msisdn_enter"),
            fg_color=C["input"], border_color=C["accent2"],
            text_color=C["text"], placeholder_text_color=C["muted"],
            font=("Consolas", 15), height=42, width=280,
            border_width=2, corner_radius=10)
        self._entry.pack(side="right")
        self._entry.bind("<Return>", lambda _: self.do_search())

        # Results scroll frame
        self._results_frame = ctk.CTkScrollableFrame(
            tab, fg_color=C["bg"], corner_radius=12,
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"])
        self._results_frame.grid(row=1, column=0, sticky="nsew")
        self._results_frame.columnconfigure(0, weight=1)
        self._results_frame.columnconfigure(1, weight=1)
        self._results_frame.columnconfigure(2, weight=1)

        self._show_placeholder()

    # ── States ────────────────────────────────────────
    def _show_placeholder(self):
        self._clear_results()
        ph = ctk.CTkFrame(self._results_frame, fg_color=C["card"], corner_radius=14)
        ph.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=20)
        ctk.CTkLabel(ph, text="🔍", font=("Segoe UI", 48),
                     text_color="#EDE8F5").pack(pady=(30, 6))
        ctk.CTkLabel(ph, text=self._T("msisdn_empty"),
                     font=("Segoe UI", 14), text_color=C["muted"]).pack(pady=(0, 30))

    def _show_loading(self):
        self._clear_results()
        ph = ctk.CTkFrame(self._results_frame, fg_color=C["card"], corner_radius=14)
        ph.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=20)
        ctk.CTkLabel(ph, text="⏳", font=("Segoe UI", 48)).pack(pady=(30, 6))
        ctk.CTkLabel(ph, text=self._T("msisdn_loading"),
                     font=("Segoe UI", 14), text_color=C["warning"]).pack(pady=(0, 30))

    def _show_error(self, msg):
        self._clear_results()
        ph = ctk.CTkFrame(self._results_frame, fg_color=C["card"], corner_radius=14)
        ph.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=20)
        ctk.CTkLabel(ph, text="❌", font=("Segoe UI", 48)).pack(pady=(30, 6))
        ctk.CTkLabel(ph, text=self._T("msisdn_error"),
                     font=("Segoe UI", 14, "bold"), text_color=C["error"]).pack()
        ctk.CTkLabel(ph, text=msg, font=FONT_MONO_S,
                     text_color=C["muted"], wraplength=600).pack(pady=(4, 30))

    def _clear_results(self):
        for w in self._results_frame.winfo_children():
            w.destroy()

    # ── Search ────────────────────────────────────────
    def do_search(self):
        msisdn = self._entry.get().strip()
        if not msisdn:
            return
        self._search_btn.configure(state="disabled", text="⏳")
        self._show_loading()

        def worker():
            data, err = fetch_msisdn_details(msisdn)
            self._tab.after(0, lambda: self._on_result(data, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_result(self, data, err):
        self._search_btn.configure(state="normal",
                                   text=self._T("msisdn_search"))
        if err:
            self._show_error(err)
        else:
            self._data = data
            self.render(data)

    def clear(self):
        self._entry.delete(0, "end")
        self._data = None
        self._show_placeholder()

    # ── Render ────────────────────────────────────────
    def render(self, data):
        """Render JSON response as grouped hero + cards."""
        self._clear_results()

        # ── Hero card ──────────────────────────────
        hero = ctk.CTkFrame(self._results_frame,
                            fg_color=C["accent2"], corner_radius=16)
        hero.grid(row=0, column=0, columnspan=3,
                  sticky="ew", padx=4, pady=(4, 12))

        lh = ctk.CTkFrame(hero, fg_color="transparent")
        lh.pack(side="left", padx=24, pady=16)
        ctk.CTkLabel(lh, text="📱", font=("Segoe UI", 32)).pack()
        ctk.CTkLabel(lh, text=str(data.get("msisdn", "—")),
                     font=("Consolas", 26, "bold"), text_color="white").pack()
        ctk.CTkLabel(lh, text="MSISDN",
                     font=("Segoe UI", 10), text_color="#C4B0DC").pack()

        ctk.CTkFrame(hero, fg_color="#7C3DAB", width=1
                     ).pack(side="left", fill="y", padx=10, pady=10)

        pills = ctk.CTkFrame(hero, fg_color="transparent")
        pills.pack(side="left", padx=10, pady=16)

        s_lbl, s_col = STATUS_MAP.get(
            data.get("status"), (str(data.get("status")), C["muted"]))
        self._pill(pills, "Status",  s_lbl, s_col)

        ss_lbl, ss_col = SIM_STATUS_MAP.get(
            data.get("simCardStatus"), (str(data.get("simCardStatus")), C["muted"]))
        self._pill(pills, "SIM", ss_lbl, ss_col)

        pay = PAYMENT_MAP.get(data.get("paymentPlan"),
                              str(data.get("paymentPlan", "—")))
        self._pill(pills, "Plan",  pay, C["success"])
        self._pill(pills, "Usage", str(data.get("numberUsageType", "—")), C["accent"])

        rh = ctk.CTkFrame(hero, fg_color="transparent")
        rh.pack(side="right", padx=24, pady=16)
        ctk.CTkLabel(rh, text="👤 " + str(data.get("username", "—")),
                     font=("Consolas", 14, "bold"), text_color="white").pack(anchor="e")
        raw = data.get("lastActionDate", "")
        fmt = raw[:19].replace("T", "  ") if raw else "—"
        ctk.CTkLabel(rh, text="📅 " + fmt,
                     font=("Consolas", 11), text_color="#C4B0DC").pack(anchor="e", pady=(4, 0))
        ctk.CTkLabel(rh,
                     text=(f"🏷️ v{data.get('version', '—')}  |  "
                           f"Segment {data.get('segmentType', '—')}"),
                     font=("Segoe UI", 10), text_color="#C4B0DC").pack(anchor="e", pady=(4, 0))

        # ── Group cards ──────────────────────────
        group_data = {g: {} for g in self._COL}
        for fk, fv in data.items():
            meta  = MSISDN_FIELD_META.get(fk)
            group = meta["group"] if meta else "misc"
            if group in group_data:
                group_data[group][fk] = fv

        for group_key, fields in group_data.items():
            if not fields:
                continue
            ginfo  = MSISDN_GROUPS.get(group_key, {"label": group_key, "color_key": "muted"})
            gcolor = C.get(ginfo["color_key"], C["muted"])
            col    = self._COL.get(group_key, 0)
            row    = self._ROW.get(group_key, 1)

            card = ctk.CTkFrame(self._results_frame,
                                fg_color=C["card"], corner_radius=14)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

            # Group header bar
            gh = ctk.CTkFrame(card, fg_color=C["input"], corner_radius=10, height=38)
            gh.pack(fill="x", padx=10, pady=(10, 6))
            gh.pack_propagate(False)
            ctk.CTkFrame(gh, fg_color=gcolor, width=4, corner_radius=2
                         ).pack(side="left", fill="y", padx=(8, 6), pady=6)
            ctk.CTkLabel(gh, text=ginfo["label"],
                         font=("Segoe UI", 11, "bold"),
                         text_color=gcolor).pack(side="left", pady=6)

            # Fields
            for fk, fv in fields.items():
                meta = MSISDN_FIELD_META.get(
                    fk, {"label": fk, "icon": "•"})
                display = self._fmt(fk, fv)
                txt_col, bg_col = self._style(fk, fv)

                rf = ctk.CTkFrame(card, fg_color="transparent")
                rf.pack(fill="x", padx=12, pady=2)
                ctk.CTkLabel(rf,
                             text=f"{meta['icon']}  {meta['label']}",
                             font=("Segoe UI", 10), text_color=C["muted"],
                             width=160, anchor="w").pack(side="left")
                vf = ctk.CTkFrame(rf, fg_color=bg_col, corner_radius=6)
                vf.pack(side="left", fill="x", expand=True, pady=1)
                ctk.CTkLabel(vf, text=display, font=("Consolas", 11),
                             text_color=txt_col, anchor="w"
                             ).pack(side="left", padx=8, pady=3)
                ctk.CTkButton(vf, text="⎘", width=28, height=22,
                              font=("Segoe UI", 11), fg_color="transparent",
                              hover_color=C["border"], text_color=C["muted"],
                              corner_radius=6,
                              command=lambda v=display: (
                                  self._tab.clipboard_clear(),
                                  self._tab.clipboard_append(v)
                              )).pack(side="right", padx=4, pady=2)

            ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

        for r in [1, 2]:
            self._results_frame.rowconfigure(r, weight=1)

    # ── Helpers ────────────────────────────────────────
    def _pill(self, parent, label, value, color):
        pill = ctk.CTkFrame(parent, fg_color=C["bg"], corner_radius=10)
        pill.pack(side="left", padx=6)
        ctk.CTkLabel(pill, text=label,
                     font=("Segoe UI", 9), text_color="#C4B0DC").pack(padx=10, pady=(6, 0))
        ctk.CTkLabel(pill, text=value,
                     font=("Segoe UI", 12, "bold"), text_color=color
                     ).pack(padx=10, pady=(0, 6))

    def _fmt(self, key, val):
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

    def _style(self, key, val):
        """Returns (text_color, bg_color)."""
        if val is None:
            return C["muted"], C["input"]
        if key == "status":
            _, col = STATUS_MAP.get(val, (None, C["muted"]))
            return col, col + "22" if col.startswith("#") else C["input"]
        if key == "simCardStatus":
            _, col = SIM_STATUS_MAP.get(val, (None, C["muted"]))
            return col, col + "22" if col.startswith("#") else C["input"]
        if key in ("pin1", "pin2", "puk1", "puk2"):
            return C["warning"], C["input"]
        if key in ("price", "finalPrice", "reservationFee", "activationFee"):
            return C["success"], C["input"]
        if isinstance(val, bool):
            return (C["success"] if val else C["error"]), C["input"]
        return C["text"], C["input"]

    # ── Public: restore data after lang/theme change ──
    def get_cached_data(self):
        return self._data

    def rebuild(self, T=None):
        """Destroy and recreate all widgets with current C palette."""
        if T:
            self._T = T
        for w in self._tab.winfo_children():
            w.destroy()
        self._build()
        if self._data:
            self.render(self._data)

    def restore(self, data):
        if data:
            self._data = data
            self.render(data)