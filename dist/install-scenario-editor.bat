@echo off
chcp 65001
title DialBB-NC
cd /d %~dp0

echo "Installing scenario editor GUI."
dialbb-install-scenario-editor editor-gui.zip
pause
