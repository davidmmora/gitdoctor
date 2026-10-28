@echo off
title GitDoctor Vigilante - Monitoreo Activo
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0agent.py" /vigilante
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        py "%~dp0agent.py" /vigilante
    ) else (
        echo [ERROR] Python no esta disponible en el PATH del sistema.
    )
)
pause
