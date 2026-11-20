@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
if defined DIALBB_PYTHON goto run
set "DIALBB_PYTHON=python"
if exist "%~dp0..\..\.venv\Scripts\python.exe" set "DIALBB_PYTHON=%~dp0..\..\.venv\Scripts\python.exe"
:run
"%DIALBB_PYTHON%" "%~dp0launch_test.py" %*
if errorlevel 1 pause
