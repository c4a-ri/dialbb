@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PORT=5000"
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

:validate
rem Require 1-5 decimal digits with no leading zero, in the TCP port range.
echo(%PORT%| findstr /r /x "[1-9][0-9]*" >nul || goto bad_port
if not "%PORT:~5%"=="" goto bad_port
if %PORT% GTR 65535 goto bad_port
where curl.exe >nul 2>nul || goto no_curl
set "HUB_URL=http://localhost:%PORT%"
set "PROBE_URL=%HUB_URL%/socket.io/?EIO=4&transport=polling"
curl.exe --silent --output NUL --connect-timeout 1 --max-time 1 "%HUB_URL%/" >nul 2>nul
if not errorlevel 1 goto occupied
start "DialBB - hub" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.hub --port %PORT%"
set "ATTEMPTS=0"
:wait_hub
curl.exe --fail --silent --output NUL --connect-timeout 1 --max-time 1 "%PROBE_URL%" >nul 2>nul
if not errorlevel 1 goto spokes
set /a ATTEMPTS+=1 >nul
if %ATTEMPTS% GEQ 15 goto hub_failed
timeout /t 1 /nobreak >nul 2>nul
goto wait_hub

:spokes
start "DialBB - John" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config1.yml John --hub-url %HUB_URL%"
start "DialBB - Paul" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config2.yml Paul --hub-url %HUB_URL%"
if "%ALL_BOTS%"=="1" goto third_bot
if "%CLI%"=="1" goto third_cli
start "DialBB - Lisa" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.user_spoke_gui Lisa --hub-url %HUB_URL%"
echo Click Join in Lisa's GUI, then use Send or Ctrl+Enter.
exit /b 0
:third_cli
start "DialBB - Lisa" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.user_spoke Lisa --hub-url %HUB_URL%"
echo Press Enter in Lisa's console to join.
exit /b 0
:third_bot
start "DialBB - Lisa" "%ComSpec%" /d /s /k ""%DIALBB_PYTHON%" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config3.yml Lisa --hub-url %HUB_URL%"
exit /b 0

:help
echo Usage: test.bat [--all-bots] [--cli] [--port PORT]
echo Default: two DialBB participants and one human GUI participant.
exit /b 0
:bad_port
echo --port requires an integer from 1 to 65535 without leading zeros.
exit /b 2
:no_curl
echo curl.exe is required to check hub readiness.
exit /b 1
:occupied
echo Port %PORT% is already in use; choose another --port.
exit /b 1
:hub_failed
echo Hub did not start; check its console.
exit /b 1
