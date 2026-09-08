@echo off
title yt-dlp GUI Launcher
cd /d "%~dp0"
start "" pythonw yt_dlp_gui.py
if %ERRORLEVEL% NEQ 0 (
    python yt_dlp_gui.py
    pause
)
