@echo off
setlocal
title SteamGraveyard Setup and Launcher
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-windows.ps1"
if errorlevel 1 pause
endlocal
