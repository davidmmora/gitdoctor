@echo off
title GitDoctor - Salida Segura y Pre-Flight
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0agent.py" /apagar
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        py "%~dp0agent.py" /apagar
    ) else (
        echo [ERROR] Python no esta disponible en el PATH del sistema.
    )
)
pause
