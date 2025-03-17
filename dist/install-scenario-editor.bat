@echo off
chcp 65001
title DialBB-NC
cd /d %~dp0

:: start dialbb-nc
echo "Downloading scenario editor GUI."
if not exist "%~dp0\editor-gui.zip" (
   bitsadmin /transfer "download" https://c4a-ri.github.io/dialbb-scenario-editor/files/editor-gui.zip "%~dp0\editor-gui.zip"
)
echo "Installing scenario editor GUI."
dialbb-install-scenario-editor editor-gui.zip
pause
