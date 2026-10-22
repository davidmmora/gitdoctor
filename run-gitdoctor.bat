@echo off
title GitDoctor AI - Suite Clinica de Repositorios (Windows)
chcp 65001 >nul
if exist "%~dp0.git" (
    git -C "%~dp0" pull -q --ff-only >nul 2>&1
)
python "%~dp0agent.py" %*
pause
