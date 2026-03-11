@echo off
set PYEXE=C:\Users\sgaziyev\AppData\Local\Programs\Python\Python314\python.exe

echo Python yoxlanir...
"%PYEXE%" --version

echo Modullar yuklenilir...
"%PYEXE%" -m pip install pyinstaller customtkinter requests pillow selenium webdriver-manager

echo Build edilir...
"%PYEXE%" -m PyInstaller azercell.spec --clean --noconfirm

if errorlevel 1 (
    echo XETA: Build ugursuz
    pause
    exit /b 1
)

echo HAZIRDIR: dist\AzercellPanel.exe
explorer dist
pause
