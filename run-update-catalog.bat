@echo off
title GitDoctor - Actualizar Catalogo
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0sync.ps1" -UpdateCatalog
