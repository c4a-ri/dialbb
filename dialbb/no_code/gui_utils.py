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
__version__ = "0.1"
__author__ = "Mikio Nakano"

import sys
import os
from tkinter import messagebox
import subprocess
from typing import List, Dict, Any
import json
from cryptography.fernet import Fernet
from datetime import datetime
import yaml


# -------- Process manager class プロセス管理クラス -------------------------------------
class ProcessManager:
    def __init__(self, cmd: str, params: List[str] = None, dialbb=False) -> None:
        if params is None:
            params = []
        self.cmd = cmd
        self.params = params
        self.is_dialbb = dialbb

        if self.is_dialbb:  # in case of dialbb app server process
            self.log_file = ""

    # プロセス起動
    def start(self) -> bool:
        # プロセス起動コマンド

        if self.is_dialbb:
            # debug mode
            os.environ["DIALBB_DEBUG"] = "yes"

            # current time
            current_date: str = datetime.now().strftime("%Y%m%d")
            current_time: str = datetime.now().strftime("%H%M%S")

            log_root_dir: str = os.environ.get(
                "HOMEPATH", os.environ.get("HOME", os.getcwd())
            )
            log_dir: str = os.path.join(log_root_dir, ".dialbb_nc_logs", current_date)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            self.log_file: str = os.path.join(
                log_dir, f"{current_date}.{current_time}.txt"
            )

            with open(self.log_file, "w") as fp:
                if os.name == "nt":  # windows
                    cmd = [sys.executable, self.cmd] + self.params
                else:
                    cmd = f"exec python {self.cmd} {' '.join(self.params)}"  # todo python3?
                print(f"CLI:{cmd}")
                self.process = subprocess.Popen(
                    cmd, stdout=fp, stderr=subprocess.STDOUT, shell=True
                )
        else:
            if os.name == "nt":
                # windows
                # Pythonの実行可能ファイルのパスを取得
                cmd = [sys.executable, self.cmd] + self.params
                print(f"CLI:{cmd}")
                self.process = subprocess.Popen(cmd)
            else:
                # Linux
                cmd = f"exec python {self.cmd} {' '.join(self.params)}"
                self.process = subprocess.Popen(cmd, shell=True)

        ret_code = self.process.poll()
        if ret_code is not None:
            messagebox.showerror(
                "ERROR", "Failed to start the server.", detail=self.process.stdout
            )
            return False
        print(f"# Start process pid={self.process.pid}.")
        return True

    # stop process プロセス停止
    def stop(self) -> None:
        # stp server サーバ停止
        if os.name == "nt":
            # windows
            os.system(f"taskkill /F /T /PID {self.process.pid}")
        else:
            # Linux
            self.process.terminate()
        self.process.wait()
        print(f"# Terminated process of {self.cmd}.")

    # show log file
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
    frame.geometry(
        f"{width}x{height}+{int(sw / 2 - width / 2)}+{int(sh / 2 - height / 2)}"
    )


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
