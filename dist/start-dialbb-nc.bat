@echo off
chcp 65001
title DialBB-NC
cd /d %~dp0

:: start dialbb-nc
echo "Starting dialbb-nc."
dialbb-nc
pause
