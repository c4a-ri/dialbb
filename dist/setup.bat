@echo off
chcp 65001
title DialBB install
cd /d %~dp0

:: Pythonがインストールされているかチェック
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pythonがインストールされていません。公式サイトからインストールしてください。
    pause
    exit /b
)

:: Wheelファイル名を取得
set WHL=dialbb*-py3-none-any.whl

for %%f in (%WHL%) do (
    set PKG=%%f
)
if "%PKG%"=="" (
    echo dialbbパッケージファイルは見つかりませんでした。
    pause
    exit /b
)

:: dialbbパッケージをインストール
echo DialBBパッケージ:%PKG%をインストールしています...
pip install %PKG%
if %errorlevel% neq 0 (
    echo パッケージのインストールに失敗しました。Python環境やpipの設定を確認してください。
) else (
    echo パッケージのインストールが完了しました！
)
pause
