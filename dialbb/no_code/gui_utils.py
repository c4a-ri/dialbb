#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 C4A Research Institute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# gui_utils.py
#   functions used in GUI of Dialbb No Code
#
from __future__ import annotations

__version__ = "0.1"
__author__ = "Mikio Nakano"

import sys
import os
import json
import subprocess
import signal
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import yaml
from cryptography.fernet import Fernet
from dialbb.no_code import constants as c


# -------- Process manager class プロセス管理クラス -------------------------------------
# Cross-platform safe ProcessManager (Windows / macOS / Linux)
# Backward-compatible with your existing API while removing shell=True risks
class ProcessManager:
    """
    Safe process launcher used by GUI launcher.

    Compatible API:
        pm = ProcessManager(cmd, params, dialbb=False)
        pm.start()
        pm.stop()
        pm.get_log_file()

    Improvements:
      - No shell=True (prevents zombie + quoting bugs)
      - Proper process-group isolation
      - Clean termination on macOS/Linux
      - Windows job-style termination via CREATE_NEW_PROCESS_GROUP
      - Optional log capture (dialbb mode preserved)
    """

    def __init__(self, cmd: str, params: Optional[List[str]] = None, dialbb: bool = False) -> None:
        if not isinstance(cmd, str):
            raise TypeError("cmd must be str (script path)")

        if params is not None and not isinstance(params, list):
            raise TypeError("params must be list[str]")

        self.cmd = cmd
        self.params = params or []
        self.process: subprocess.Popen | None = None

        self.cmd = cmd
        self.params = params or []
        self.is_dialbb = dialbb

        self.process: Optional[subprocess.Popen] = None
        self.log_file: str = ""
        self._log_stream = None

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _build_command(self) -> List[str]:
        """Always execute using the current Python interpreter."""
        return [sys.executable, self.cmd, *self.params]

    def _prepare_log_file(self) -> None:
        if not self.is_dialbb:
            return

        os.environ["DIALBB_DEBUG"] = "yes"

        now = datetime.now()
        date = now.strftime("%Y%m%d")
        time = now.strftime("%H%M%S")

        home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or ".")
        log_dir = home / ".dialbb_nc_logs" / date
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = str(log_dir / f"{date}.{time}.txt")

    def _popen_kwargs(self):
        """Platform-safe process spawning."""
        kwargs = {}

        if os.name == "nt":
            # Windows
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # macOS / Linux
            kwargs["start_new_session"] = True

        return kwargs

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start(self, wait: bool = False) -> bool:
        """
        プロセス起動

        wait=True  : 終了まで待機（コンバータなど）
        wait=False : 非同期起動（GUIなど）
        """
        if self.process:
            raise RuntimeError("Process already running")
        
        stdout_target = None
        if self.is_dialbb:
            self._prepare_log_file()
            stdout_target = open(self.log_file, "w", encoding="utf-8")
        
        try:
            if os.name == "nt":
                # Windows:
                # CREATE_NEW_PROCESS_GROUP を付けないと CTRL_BREAK_EVENT が効かない
                cmd = [sys.executable, self.cmd] + self.params
                if stdout_target is not None:
                    self.process = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=stdout_target,
                        stderr=subprocess.STDOUT,
                    )
                else:
                    self.process = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    )
            else:
                # macOS / Linux:
                # start_new_session=True が最重要！！
                # → 親と完全に別セッションになる（killpgしてもGUIが死なない）
                cmd = ["python3", self.cmd] + self.params
                if stdout_target is not None:
                    self.process = subprocess.Popen(
                        cmd,
                        start_new_session=True,
                        stdout=stdout_target,
                        stderr=subprocess.STDOUT,
                    )
                else:
                    self.process = subprocess.Popen(
                        cmd,
                        start_new_session=True,
                    )
        
        except Exception:
            if stdout_target is not None:
                stdout_target.close()
            raise
        
        self._log_stream = stdout_target

        if wait:
            print(f"# Waiting process {self.cmd} ...")
            ret = self.process.wait()

            if ret != 0:
                print(f"# ERROR: process failed ({ret})")
                self.process = None
                if self._log_stream is not None:
                    self._log_stream.close()
                    self._log_stream = None
                return False

            print("# Process finished successfully.")
            self.process = None
            if self._log_stream is not None:
                self._log_stream.close()
                self._log_stream = None
            return True

        # 非同期起動確認
        if self.process.poll() is not None:
            print("# ERROR: failed to start process")
            self.process = None
            if self._log_stream is not None:
                self._log_stream.close()
                self._log_stream = None
            return False

        print(f"# Start process pid={self.process.pid}")
        return True

    # ------------------------------------------------------------------

    def stop(self) -> None:
        if not self.process:
            return

        print(f"# Stopping process pid={self.process.pid}")

        try:
            if os.name == "nt":
                # Windows: send CTRL_BREAK to process group
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
                self.process.wait(timeout=5)
            else:
                # macOS/Linux: terminate the whole session
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)

        except Exception:
            print("# Graceful stop failed -> killing")

            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
            except Exception:
                pass

            self.process.wait()

        finally:
            self.process = None
            if self._log_stream is not None:
                self._log_stream.close()
                self._log_stream = None

        print("# Process terminated")

    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    # ------------------------------------------------------------------

    def get_log_file(self) -> str:
        return self.log_file


# -------- ファイルタイムスタンプ管理クラス -------------------------------------
class FileTimestamp:
    """監視対象ファイル群の更新時刻を保持・比較するユーティリティ。"""
    files = []

    def __init__(self, dir: str, files: List[str] = None) -> None:
        """監視対象ディレクトリとファイル一覧を受け取り初期時刻を記録する。"""
        if files is None:
            files = []
        # list of files to process (full path)
        for f in files:
            self.files.append(os.path.join(dir, f))
        # 初期タイムスタンプ取得
        self.timestamps = self.get()

    # タイムスタンプ収集
    def get(self) -> List[float]:
        """監視対象ファイルのタイムスタンプ一覧を返す。"""
        result = []
        for f in self.files:
            if os.path.isfile(f):
                result.append(os.path.getmtime(f))
            else:
                result.append(0.0)
        return result

    # タイムスタンプ更新
    def update(self) -> None:
        """保持しているタイムスタンプを最新値で更新する。"""
        self.timestamps = self.get()

    # タイムスタンプ比較
    def check(self) -> bool:
        """初期取得時点から変更がない場合にTrueを返す。"""
        result = True
        now = self.get()
        for org, cur in zip(self.timestamps, now):
            if org != cur:
                result = False
                break
        return result


# setting JSON file
class SettingData:
    """GUI設定JSONの暗号化保存と取得を管理する。"""
    # データ要素
    key_openai_api_key = "OPENAI_API_KEY"
    key_anthropic_api_key = "ANTHROPIC_API_KEY"
    key_google_api_key = "GOOGLE_API_KEY"
    key_app_name = "application_name"
    key_model_list = "model_list"

    # 暗号化キー
    key = "6QvOzPwlGXvFpvv4ZrL4RSrpxZmCUK7wSxnmd9qDzp4="

    def __init__(self, filename):
        """設定ファイルを読み込み、なければ空設定で初期化する。"""
        self.filename = filename
        self.data = {}
        self.disp = None
        try:
            # ファイル読み込みデータ復号化
            self._decrypt()
        except FileNotFoundError:
            # 新規作成
            self.data = {}

    # ファイル暗号化ファイル書き込み
    def _encrypt_and_save(self):
        """設定データを暗号化してファイルへ保存する。"""
        # print(f'### Write setting json={self.data}')
        # Fernetオブジェクトを作成する
        fernet = Fernet(self.key)

        # データをバイト列に変換
        byte_data = json.dumps(self.data).encode()

        # ファイルを暗号化する
        encrypted = fernet.encrypt(byte_data)

        # 暗号化したファイルを保存する
        with open(self.filename, "wb") as file:
            file.write(encrypted)

    # ファイル復号化
    def _decrypt(self):
        """設定ファイルを復号化してメモリへ読み込む。"""
        # Fernetオブジェクトを作成する
        fernet = Fernet(self.key)

        # 暗号化されたファイルを読み込む
        with open(self.filename, "rb") as file:
            encrypted = file.read()

        # ファイルを復号化する
        result = fernet.decrypt(encrypted)
        self.data = json.loads(result.decode())
        # print(f'### Read setting json={self.data}')

    # ゲッター
    def _get(self, key):
        """指定キーの値を取得する。未設定時は空文字を返す。"""
        return self.data.get(key, "")

    # セッター
    def _set(self, key, value):
        """指定キーへ値を設定し、暗号化保存する。"""
        self.data[key] = value
        # ファイルに保存
        self._encrypt_and_save()

    # アプリ名の表示
    def _disp_appname(self, app_name):
        """登録済み表示エリアにアプリ名を反映する。"""
        if self.disp:
            # 表示エリアにセット
            self.disp["text"] = f"{gui_text('main_app_name')}: {app_name}"

    # OPENAI_API_KEY取得
    def get_openai_api_key(self):
        """OPENAI_API_KEY を取得する。"""
        return self._get(self.key_openai_api_key)

    # OPENAI_API_KEY設定
    def set_openai_api_key(self, key):
        """OPENAI_API_KEY を設定する。"""
        self._set(self.key_openai_api_key, key)

    def get_google_api_key(self):
        """OPENAI_API_KEY を取得する。"""
        return self._get(self.key_google_api_key)

    # OPENAI_API_KEY設定
    def set_google_api_key(self, key):
        """OPENAI_API_KEY を設定する。"""
        self._set(self.key_google_api_key, key)

    def get_anthropic_api_key(self):
        """OPENAI_API_KEY を取得する。"""
        return self._get(self.key_anthropic_api_key)

    # OPENAI_API_KEY設定
    def set_anthropic_api_key(self, key):
        """OPENAI_API_KEY を設定する。"""
        self._set(self.key_anthropic_api_key, key)

    # アプリ名表示エリアの登録
    def reg_disp_area(self, disp_area):
        """アプリ名表示用ウィジェットを登録する。"""
        self.disp = disp_area
        self._disp_appname(self._get(self.key_app_name))

    # アプリ名取得
    def get_appname(self):
        """設定済みアプリ名を取得する。"""
        return self._get(self.key_app_name)

    # アプリ名設定
    def set_appname(self, app_name):
        """アプリ名を設定し、表示エリアを更新する。"""
        self._set(self.key_app_name, app_name)
        # GUI表示の更新
        self._disp_appname(app_name)

    # GPT models取得
    def get_llm_models(self):
        """GPTモデル一覧を取得する。"""
        return self._get(self.key_model_list)

    # GPT models設定
    def set_llm_models(self, models: List[str]):
        """GPTモデル一覧を設定する。"""
        if not models:
            models = []
        self._set(self.key_model_list, models)


# -------- Functions -------------------------------------
# ウィンドウのサイズと中央表示の設定
def central_position(frame, width: int, height: int):
    """ウィンドウを画面中央に配置する。"""
    # スクリーンの縦横サイズを取得する
    sw = frame.winfo_screenwidth()
    sh = frame.winfo_screenheight()
    # ウィンドウサイズと表示位置を指定する
    frame.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}")


# 親ウジェットに重ねて子ウジェットを表示
def child_position(parent, child, width: int = 0, height: int = 0):
    """親ウィンドウ付近に子ウィンドウを配置する。"""
    # 親ウィンドウの位置に子ウィンドウを配置
    x = parent.winfo_rootx() + parent.winfo_width() // 4 - child.winfo_width() // 4
    y = parent.winfo_rooty() + parent.winfo_height() // 4 - child.winfo_height() // 4
    if width == 0 and height == 0:
        child.geometry(f"+{x}+{y}")
    else:
        child.geometry(f"{width}x{height}+{x}+{y}")


# GUIで利用するセッティング情報を制御
def read_gui_settings(file_path):
    """GUI設定ファイルの管理オブジェクトを返す。"""
    return SettingData(file_path)


# GUI表示テキストの実データ（可変データ）はこのモジュールで保持
GUI_TEXT_DATA: dict[str, str] = {}


# GUIで利用するラベルなどの言語データ読み込み
def read_gui_text_data(
    filename: str = c.GUI_TEXT_DEFAULT_FILE,
    lang: str = c.GUI_TEXT_DEFAULT_LANG,
):
    """GUIテキスト辞書を読み込み、指定言語の表示文字列テーブルを構築する。"""
    global GUI_TEXT_DATA

    # 多言語ファイルを読み込む
    with open(filename, "r", encoding="utf-8") as f:
        multi_lang_data = yaml.safe_load(f)

    # lang対応の辞書データを作成
    GUI_TEXT_DATA = {
        key: value.get(lang, f"[{key}]") for key, value in multi_lang_data.items()
    }


def _ensure_gui_text_data() -> None:
    """GUIテキスト辞書が未初期化の場合にデフォルト設定で遅延ロードする。"""
    global GUI_TEXT_DATA

    if GUI_TEXT_DATA:
        return

    try:
        read_gui_text_data()
    except (FileNotFoundError, OSError, yaml.YAMLError, ValueError):
        GUI_TEXT_DATA = {}


# 指定キーの言語データ取得
def gui_text(key: str):
    """指定キーに対応するGUI表示文字列を返す。"""
    if not key:
        return "Key is empty."

    if not GUI_TEXT_DATA:
        _ensure_gui_text_data()

    return GUI_TEXT_DATA.get(key, f'No data found for "{key}"')
