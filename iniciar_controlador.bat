@echo off
rem Doble clic: inicia el controlador emulado (ver iniciar_controlador.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_controlador.ps1" %*
pause
