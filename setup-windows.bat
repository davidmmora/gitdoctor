@echo off
title GitDoctor Setup - Windows
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
pause
