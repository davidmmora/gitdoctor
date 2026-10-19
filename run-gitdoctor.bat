@echo off
title GitDoctor AI - Suite Clinica de Repositorios (Windows)
chcp 65001 >nul
python "%~dp0agent.py" %*
pause
