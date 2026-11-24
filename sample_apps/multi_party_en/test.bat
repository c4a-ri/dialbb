@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PORT=5000"
set "MAX_TURNS=30"
set "ALL_BOTS=0"
set "CLI=0"
cd /d "%~dp0..\.." || exit /b 1
if defined DIALBB_PYTHON goto parse
set "DIALBB_PYTHON=python"
if exist "%CD%\.venv\Scripts\python.exe" set "DIALBB_PYTHON=%CD%\.venv\Scripts\python.exe"

:parse
if "%~1"=="" goto validate
if "%~1"=="--all-bots" goto all_bots
if "%~1"=="--cli" goto cli
if "%~1"=="--port" goto port
if "%~1"=="--max-turns" goto max_turns
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
echo Unknown option: %~1
exit /b 2
:all_bots
set "ALL_BOTS=1"
shift
goto parse
:cli
set "CLI=1"
shift
goto parse
:port
if "%~2"=="" goto bad_port
set "PORT=%~2"
shift
shift
goto parse
:max_turns
if "%~2"=="" goto bad_max_turns
set "MAX_TURNS=%~2"
shift
shift
goto parse

:validate
rem Require 1-5 decimal digits with no leading zero, in the TCP port range.
echo(%PORT%| findstr /r /x "[1-9][0-9]*" >nul || goto bad_port
if not "%PORT:~5%"=="" goto bad_port
if %PORT% GTR 65535 goto bad_port
set MAX_TURNS | findstr /r /x "MAX_TURNS=[1-9][0-9]*" >nul || goto bad_max_turns
set "MODE=gui"
if "%CLI%"=="1" set "MODE=cli"
if "%ALL_BOTS%"=="1" set "MODE=bots"
"%DIALBB_PYTHON%" "sample_apps\run_multi_party_windows.py" en "%PORT%" "%MAX_TURNS%" "%MODE%"
exit /b %ERRORLEVEL%

:help
echo Usage: test.bat [--all-bots] [--cli] [--port PORT] [--max-turns MAX_TURNS]
echo Default: two DialBB participants and one human GUI participant.
echo --max-turns defaults to 30.
exit /b 0
:bad_port
echo --port requires an integer from 1 to 65535 without leading zeros.
exit /b 2
:bad_max_turns
echo --max-turns requires a positive integer without leading zeros.
exit /b 2
