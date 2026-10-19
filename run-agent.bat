@echo off
title GitDoctor AI - Suite Clinica de Repositorios

rem Auto-actualizar _sync silenciosamente si hay conexion con origin
if exist "%~dp0.git" (
    git -C "%~dp0" pull -q --ff-only 2>nul
)

python "%~dp0agent.py" %*
pause
