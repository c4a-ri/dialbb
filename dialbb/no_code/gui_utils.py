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
    files = []

    def __init__(self, dir: str, files: List[str] = None) -> None:
        if files is None:
            files = []
        # list of files to process (full path)
        for f in files:
            self.files.append(os.path.join(dir, f))
        # 初期タイムスタンプ取得
        self.timestamps = self.get()

    # タイムスタンプ収集
    def get(self) -> List[float]:
        result = []
        for f in self.files:
            if os.path.isfile(f):
                result.append(os.path.getmtime(f))
            else:
                result.append(0.0)
        return result

    # タイムスタンプ更新
    def update(self) -> None:
        self.timestamps = self.get()

    # タイムスタンプ比較
    def check(self) -> bool:
        result = True
        now = self.get()
        for org, cur in zip(self.timestamps, now):
            if org != cur:
                result = False
                break
        return result


# -------- JSONファイルの管理クラス -------------------------------------
class JsonInfo:
    # データ要素
    label_gpt = "OPENAI_API_KEY"
    label_app = "Specify_application"
    label_model = "gpt_models"

    # 暗号化キー
    key = "6QvOzPwlGXvFpvv4ZrL4RSrpxZmCUK7wSxnmd9qDzp4="

    def __init__(self, filename):
        self.filename = filename
        self.data = {}
        self.disp = None
        try:
            # ファイル読み込みデータ復号化
            self._decryption()
        except FileNotFoundError:
            # 新規作成
            self.data = {}

    # ファイル暗号化ファイル書き込み
    def _encryption(self):
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
    def _decryption(self):
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
        return self.data.get(key, "")

    # セッター
    def _set(self, key, value):
        self.data[key] = value
        # ファイルに保存
        self._encryption()

    # アプリ名の表示
    def _disp_appname(self, app_name):
        if self.disp:
            # 表示エリアにセット
            self.disp["text"] = f"{gui_text('main_app_name')}: {app_name}"

    # OPENAI_API_KEY取得
    def get_gptkey(self):
        return self._get(self.label_gpt)

    # OPENAI_API_KEY設定
    def set_gptkey(self, key):
        self._set(self.label_gpt, key)

    # アプリ名表示エリアの登録
    def reg_disp_area(self, disp_area):
        self.disp = disp_area
        self._disp_appname(self._get(self.label_app))

    # アプリ名取得
    def get_appname(self):
        return self._get(self.label_app)

    # アプリ名設定
    def set_appname(self, app_name):
        self._set(self.label_app, app_name)
        # GUI表示の更新
        self._disp_appname(app_name)

    # GPT models取得
    def get_gptmodels(self):
        return self._get(self.label_model)

    # GPT models設定
    def set_gptmodels(self, models: List[str]):
        if not models:
            models = []
        self._set(self.label_model, models)


# -------- Functions -------------------------------------
# ウィンドウのサイズと中央表示の設定
def central_position(frame, width: int, height: int):
    # スクリーンの縦横サイズを取得する
    sw = frame.winfo_screenwidth()
    sh = frame.winfo_screenheight()
    # ウィンドウサイズと表示位置を指定する
    frame.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}")


# 親ウジェットに重ねて子ウジェットを表示
def child_position(parent, child, width: int = 0, height: int = 0):
    # 親ウィンドウの位置に子ウィンドウを配置
    x = parent.winfo_rootx() + parent.winfo_width() // 4 - child.winfo_width() // 4
    y = parent.winfo_rooty() + parent.winfo_height() // 4 - child.winfo_height() // 4
    if width == 0 and height == 0:
        child.geometry(f"+{x}+{y}")
    else:
        child.geometry(f"{width}x{height}+{x}+{y}")


# GUIで利用するセッティング情報を制御
def read_gui_settings(file_path):
    return JsonInfo(file_path)


# GUIテキスト言語対応テーブル
GUI_TEXT_DATA = {}


# GUIで利用するラベルなどの言語データ読み込み
def read_gui_text_data(filename: str, lang: str):
    global GUI_TEXT_DATA

    # 多言語ファイルを読み込む
    with open(filename, "r", encoding="utf-8") as f:
        multi_lang_data = yaml.safe_load(f)

    # lang対応の辞書データを作成
    GUI_TEXT_DATA = {
        key: value.get(lang, f"[{key}]") for key, value in multi_lang_data.items()
    }


# 指定キーの言語データ取得
def gui_text(key: str):
    global GUI_TEXT_DATA

    if not key:
        return "Key is empty."

    return GUI_TEXT_DATA.get(key, f'No data found for "{key}"')
