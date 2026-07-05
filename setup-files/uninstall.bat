@echo off
chcp 65001
title DialBB uninstall
cd /d %~dp0

:: install dialbb pakcage.
echo Installing dialbb package:%PKG%
dialbb-uninstall
pip uninstall -y  dialbb
if %errorlevel% neq 0 (
    echo Failed to uninstall dialbb package. Please check Python or pip environment.
) else (
    echo dialbb package has been successfully uninstalled.
)
pause
