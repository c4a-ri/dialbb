#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# gui_utils.py
#   functions used in GUI of Dialbb No Code
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import sys
import os
from tkinter import messagebox
import subprocess
from typing import List, Dict, Any
import json
from cryptography.fernet import Fernet


# -------- Process manager class プロセス管理クラス -------------------------------------
class ProcessManager:
    def __init__(self, cmd: str, param: List[str] = None) -> None:
        if param is None:
            param = []
        self.cmd = cmd
        self.param = param

    # プロセス起動
    def start(self) -> bool:
        # プロセス起動コマンド
        if os.name == 'nt':
            # windows
            # Pythonの実行可能ファイルのパスを取得
            cmd = [sys.executable, self.cmd] + self.param
            print(f'CLI:{cmd}')
            self.process = subprocess.Popen(cmd)
        else:
            # Linux
            cmd = f'exec python {self.cmd} {" ".join(self.param)}'
            self.process = subprocess.Popen(cmd, shell=True)

        ret_code = self.process.poll()
        if ret_code is not None:
            messagebox.showerror('ERROR', "Failed to start the server.",
                                 detail=self.process.stdout)
            return False
        print(f'# Start process pid={self.process.pid}.')
        return True
    
    # stop process プロセス停止
    def stop(self) -> None:
        # stp server サーバ停止
        if os.name == 'nt':
            # windows
            os.system(f"taskkill /F /T /PID {self.process.pid}")
        else:
            # Linux
            self.process.terminate()
        self.process.wait()
        print(f'# Terminated process of {self.cmd}.')


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
    label_gpt = 'OPENAI_API_KEY'
    label_app = 'Specify_application'

    # 暗号化キー
    key = '6QvOzPwlGXvFpvv4ZrL4RSrpxZmCUK7wSxnmd9qDzp4='
    
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
        # Fernetオブジェクトを作成する
        fernet = Fernet(self.key)

        # データをバイト列に変換
        byte_data = json.dumps(self.data).encode()

        # ファイルを暗号化する
        encrypted = fernet.encrypt(byte_data)

        # 暗号化したファイルを保存する
        with open(self.filename, 'wb') as file:
            file.write(encrypted)

    # ファイル復号化
    def _decryption(self):
        # Fernetオブジェクトを作成する
        fernet = Fernet(self.key)

        # 暗号化されたファイルを読み込む
        with open(self.filename, 'rb') as file:
            encrypted = file.read()

        # ファイルを復号化する
        result = fernet.decrypt(encrypted)
        self.data = json.loads(result.decode())

    # ゲッター
    def _get(self, key):
        return self.data.get(key, '')

    # セッター
    def _set(self, key, value):
        self.data[key] = value
        # ファイルに保存
        self._encryption()

    # アプリ名の表示
    def _disp_appname(self, app_name):
        if self.disp:
            # 表示エリアにセット
            self.disp['text'] = f'Specify application (Current app: {app_name})'

    # OPENAI_API_KEY取得
    def get_gptkey(self):
        return self._get(self.label_gpt)

    # OPENAI_API_KEY設定
    def set_gptkey(self, key):
        self._set(self.label_gpt, key)

    # アプリ名表示エリアの登録
    def reg_disp_aria(self, disp_area):
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


# -------- Functions -------------------------------------
# ウィンドウのサイズと中央表示の設定
def central_position(frame, width: int, height: int):
    # スクリーンの縦横サイズを取得する
    sw = frame.winfo_screenwidth()
    sh = frame.winfo_screenheight()
    # ウィンドウサイズと表示位置を指定する
    frame.geometry(f"{width}x{height}+{int(sw/2-width/2)}+{int(sh/2-height/2)}")


# 親ウジェットに重ねて子ウジェットを表示
def chaild_position(parent, chaild, width: int = 0, height: int = 0):
    # 親ウィンドウの位置に子ウィンドウを配置
    x = parent.winfo_rootx() + parent.winfo_width() // 4 - chaild.winfo_width() // 4
    y = parent.winfo_rooty() + parent.winfo_height() // 4 - chaild.winfo_height() // 4
    if width == 0 and height == 0:
        chaild.geometry(f"+{x}+{y}")
    else:
        chaild.geometry(f"{width}x{height}+{x}+{y}")


# GUIで利用するセッティング情報を制御
def gui_settings(file_path):
    return JsonInfo(file_path)
