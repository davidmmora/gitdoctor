@echo off
title GitDoctor - Sincronizar
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0sync.ps1"
