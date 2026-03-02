"""
widgets.py — Reusable widget factory functions
"""
import customtkinter as ctk
from tkinter import filedialog
from config import C, FONT_MONO, FONT_MONO_S, FONT_LABEL, FONT_SECTION

def mk_label(parent, text, color=None, font=None, **kw):
    return ctk.CTkLabel(parent, text=text,
                        text_color=color or C["text"],
                        font=font or FONT_LABEL, **kw)


def mk_entry(parent, placeholder="", width=220, **kw):
    return ctk.CTkEntry(parent,
                        placeholder_text=placeholder,
                        fg_color=("#251540", "#EDE8F5"), border_color=("#3D2260", "#C4B0DC"),
                        text_color=("#EDE8F5", "#1A0A2E"),
                        placeholder_text_color=("#8B75B0", "#6B5A8A"),
                        font=FONT_MONO, height=38, width=width, **kw)


def mk_divider(parent):
    ctk.CTkFrame(parent, fg_color=("#3D2260", "#C4B0DC"), height=1).pack(
        fill="x", padx=16, pady=10)


def mk_section(parent, text):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=(14, 6))
    ctk.CTkFrame(f, fg_color=("#5C2483", "#5C2483"), width=3, height=16,
                 corner_radius=2).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(f, text=text, font=FONT_SECTION,
                 text_color=("#8B75B0", "#6B5A8A")).pack(side="left")


def mk_field(parent, lbl, default="", show=None, disabled=False, lbl_width=135):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=(0, 7))
    ctk.CTkLabel(f, text=lbl,
                 text_color=("#3D2260", "#C4B0DC") if disabled else C["muted"],
                 font=FONT_LABEL, width=lbl_width, anchor="w").pack(side="left")
    if disabled:
        e = ctk.CTkEntry(f, width=0, fg_color=("#120A1E", "#F3F0F8"),
                         border_color=("#3D2260", "#C4B0DC"), text_color=("#8B75B0", "#6B5A8A"),
                         font=FONT_MONO, height=38)
    else:
        kw_e = {"show": show} if show else {}
        e = mk_entry(f, width=0, **kw_e)
    e.pack(side="left", fill="x", expand=True)
    if disabled:
        e.configure(state="normal")
        e.insert(0, default)
        e.configure(state="disabled")
    else:
        e.insert(0, default)
    if show == "*":
        ctk.CTkButton(
            f, text="👁", width=34, height=34,
            fg_color="transparent", hover_color=("#3D2260", "#C4B0DC"),
            text_color=("#8B75B0", "#6B5A8A"), font=("Segoe UI", 14), corner_radius=6,
            command=lambda en=e: en.configure(
                show="" if en.cget("show") == "*" else "*")
        ).pack(side="left", padx=(4, 0))
    return e


def mk_file_field(parent, lbl, default="", lbl_width=135):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=(0, 7))
    ctk.CTkLabel(f, text=lbl, text_color=("#8B75B0", "#6B5A8A"),
                 font=FONT_LABEL, width=lbl_width, anchor="w").pack(side="left")
    e = mk_entry(f, width=0)
    e.pack(side="left", fill="x", expand=True)
    e.insert(0, default)

    def browse():
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            e.delete(0, "end")
            e.insert(0, path)

    ctk.CTkButton(
        f, text="📂", width=38, height=38,
        fg_color=("#3D2260", "#C4B0DC"), hover_color=("#5C2483", "#5C2483"),
        text_color=("#EDE8F5", "#1A0A2E"), font=("Segoe UI", 13), corner_radius=6,
        command=browse
    ).pack(side="left", padx=(5, 0))
    return e


def mk_panel_header(parent, text):
    """Purple banner used as card section title."""
    ph = ctk.CTkFrame(parent, fg_color=("#5C2483", "#5C2483"), corner_radius=10, height=44)
    ph.pack(fill="x", padx=12, pady=(12, 4))
    ph.pack_propagate(False)
    ctk.CTkLabel(ph, text=text, font=("Segoe UI", 11, "bold"),
                 text_color="white").place(relx=0.5, rely=0.5, anchor="center")