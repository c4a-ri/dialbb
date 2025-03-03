@echo off
chcp 65001
title DialBB install
cd /d %~dp0

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo "Python is not installed. Please Install Python in advance."
    pause
    exit /b
)

:: Get wheel file name
set WHL=dialbb*-py3-none-any.whl

for %%f in (%WHL%) do (
    set PKG=%%f
)
if "%PKG%"=="" (
    echo "dialbb pakage was not found."
    pause
    exit /b
)

:: install dialbb pakcage.
echo Installing dialbb package:%PKG%
pip install --force-reinstall %PKG%
if %errorlevel% neq 0 (
    echo Failed to install dialbb package. Please check Python or pip environment.
) else (
    echo dialbb package has been successfully installed.
)
pause
