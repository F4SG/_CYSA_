@echo off
rem Doble clic: elegir fuente, marcar carriles y contar (ver iniciar_conteo.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_conteo.ps1" %*
pause
