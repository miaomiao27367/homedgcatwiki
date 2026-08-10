@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "update.ps1"
