# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
sel_datas, sel_binaries, sel_hiddenimports = collect_all("selenium")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[*ctk_binaries, *sel_binaries],
    datas=[
        *ctk_datas,
        *sel_datas,
        ("Logo/azercell.ico",      "Logo"),
        ("Logo/azercell_logo.png", "Logo"),
    ],
    hiddenimports=[
        *ctk_hiddenimports,
        *sel_hiddenimports,
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
        "requests",
        "urllib3",
        "charset_normalizer",
        "idna",
        "certifi",
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.chrome",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.common.by",
        "selenium.webdriver.support",
        "selenium.webdriver.support.wait",
        "selenium.webdriver.support.expected_conditions",
        "webdriver_manager",
        "webdriver_manager.chrome",
        "tkinter",
        "tkinter.filedialog",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AzercellPanel",
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon="Logo/azercell.ico",
    onefile=True,
)
