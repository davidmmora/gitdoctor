@echo off
title GitDoctor AI - Suite Clinica de Repositorios (Windows)
chcp 65001 >nul
if exist "%~dp0.git" (
    git -C "%~dp0" pull -q --ff-only >nul 2>&1
)
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0agent.py" %*
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        py "%~dp0agent.py" %*
    ) else (
        echo [ERROR] Python no esta disponible en el PATH del sistema.
        echo Descargalo e instalalo desde https://python.org marcando "Add Python to PATH".
    )
)
pause
