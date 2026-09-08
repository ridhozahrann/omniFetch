@echo off
title Building OmniFetch Standalone Executable (.exe)
cd /d "%~dp0"
echo =======================================================
echo    Membundel OmniFetch GUI menjadi Standalone .exe
echo =======================================================
echo.

pyinstaller --noconfirm --onedir --windowed --name "OmniFetch" --clean yt_dlp_gui.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================
    echo ✅ Selesai! File Executable (.exe) berhasil dibuat di:
    echo    %cd%\dist\OmniFetch\OmniFetch.exe
    echo =======================================================
) else (
    echo.
    echo ❌ Terjadi kesalahan saat membuat file .exe!
)
pause
