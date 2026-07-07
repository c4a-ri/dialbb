@echo off
chcp 65001
title DialBB-NC
cd /d %~dp0

:: start dialbb-nc
echo "Starting dialbb-nc in Japanese UI mode."
dialbb-nc ja
pause
