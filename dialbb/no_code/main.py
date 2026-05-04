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

# main.py
#   dialbb no_code GUI main program
#
__version__ = "0.1"
__author__ = "Mikio Nakano"

import os
import sys
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import subprocess
import shutil
import zipfile
from typing import Dict, Optional, Any
from dataclasses import dataclass

from dialbb.no_code.tools.scenario_converter2json import (
    convert_excel_to_json as scenario_convert_excel_to_json,
)
from dialbb.no_code.tools.scenario_converter2excel import (
    convert_json_to_excel as scenario_convert_json_to_excel,
)
from dialbb.no_code.config_editor import edit_app_config, edit_test_config
from dialbb.no_code.function_editor import edit_scenario_functions
from dialbb.no_code.gui_utils import (
    read_gui_settings,
    ProcessManager,
    FileTimestamp,
    child_position,
    read_gui_text_data,
    gui_text, SettingData,
)
from dialbb.main import DialogueProcessor
from dialbb.paths import DIALBB_DIR, NC_PATH, APP_DIR, TEMPLATE_DIR
from dialbb.util.logger import get_logger
from dialbb.sim_tester.main import test_by_simulation


logger = get_logger("dialbb.no_code.main")

# paths  実行環境パス
APP_FILE_DIR: str = APP_DIR
PYEDITOR_DIR: str = os.path.join(DIALBB_DIR, "pyeditor")
PYEDITOR_EDITOR_SCRIPT: str = os.path.join(PYEDITOR_DIR, "scenario_editor.py")
PYEDITOR_STATE_GRAPH_JSON: str = os.path.join(PYEDITOR_DIR, "data", "state_graph.json")


APP_FILES: Dict[str, str] = {
    "scenario": "scenario.xlsx",
    "dst-knowledge": "dst-knowledge.xlsx",
    "scenario-functions": "scenario_functions.py",
    "config": "config.yml",
    "test-config": "test_config.yml",
}

TEST_CONFIG_FILES: str = os.path.join(
    NC_PATH, "simulation", "LANG", "simulation_config.yml"
)

# define application files  アプリファイルの定義

@dataclass
class RuntimeProcesses:
    """実行中プロセスの状態を保持する。"""

    editor_process: Optional[ProcessManager] = None
    dialbb_proc: Optional[ProcessManager] = None


PROCESS_STATE = RuntimeProcesses()

# application file timestamp アプリファイルのタイムスタンプ
app_file_timestamp: FileTimestamp = FileTimestamp(APP_FILE_DIR, list(APP_FILES.values()))


class AppFileFrame(ttk.Frame):
    """アプリファイル選択UIで使う拡張Frame（型情報用）。"""

    spec_app: tk.Label
    edit_box: tk.Entry


# -------- GUI Editor -------------------------------------
# Start GUI Editor GUIエディタ起動/停止
def exec_editor(file_path, parent, button) -> None:
    """シナリオエディタの起動/停止と保存連携を行う。"""
    if not PROCESS_STATE.editor_process:
        # エディタ起動処理
        # convert excel to JSON（PyEditor入力）
        ret = convert_excel_to_json(file_path, PYEDITOR_STATE_GRAPH_JSON)
        if not ret:
            return

        arg_lang = f"--lang={gui_text('language type')}"
        logger.info(
            "Starting pyEditor. OS: %s, Script: %s, Language: %s",
            sys.platform,
            PYEDITOR_EDITOR_SCRIPT,
            arg_lang,
        )
        if not os.path.exists(PYEDITOR_EDITOR_SCRIPT):
            messagebox.showerror(
                gui_text("msg_editor_err_title"),
                gui_text("msg_editor_err_msg"),
                detail=f"script not found: {PYEDITOR_EDITOR_SCRIPT}",
                parent=parent,
            )
            return

        PROCESS_STATE.editor_process = ProcessManager(
            PYEDITOR_EDITOR_SCRIPT,
            [PYEDITOR_STATE_GRAPH_JSON, arg_lang],
        )
        ret = PROCESS_STATE.editor_process.start()
        if not ret:
            PROCESS_STATE.editor_process = None
            messagebox.showerror(
                gui_text("msg_editor_err_title"),
                gui_text("msg_editor_err_msg"),
                detail=gui_text("msg_editor_err_detail"),
                parent=parent,
            )
            return

        button.configure(text=gui_text("btn_scenario_stop"))
    else:
        # エディタ終了前に保存確認
        save_confirm = messagebox.askyesno(
            gui_text("msg_warn_confirm"),
            gui_text("msg_warn_no_saved_detail"),
            parent=parent,
        )

        # no: 終了しない
        if not save_confirm:
            return

        # エディタ終了処理
        try:
            scenario_convert_json_to_excel(PYEDITOR_STATE_GRAPH_JSON, file_path)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error("JSON->Excel conversion failed: %s", e)
            messagebox.showerror(
                gui_text("msg_editor_err_title"),
                gui_text("msg_editor_err_msg"),
                detail=f"{e}",
                parent=parent,
            )

        # pyEditorプロセス停止
        PROCESS_STATE.editor_process.stop()
        PROCESS_STATE.editor_process = None
        button.configure(text=gui_text("btn_scenario_start"))


# Excel→JSON変換処理
def convert_excel_to_json(xlsx: str, json: str) -> bool:
    """
    Convert Excel to JSON

    :param xlsx:
    :param json:
    """
    result = False
    # メッセージを表示する
    if xlsx == "" or json == "":
        messagebox.showerror("Warning", gui_text("msg_convfile_nothing"))
    else:
        try:
            scenario_convert_excel_to_json(xlsx, json)
            result = True
        except (OSError, RuntimeError, ValueError) as e:
            logger.error("Excel->JSON conversion failed: %s", e)
            messagebox.showerror(
                "Error",
                gui_text("msg_editor_err_msg"),
                detail=f"{e}",
            )

    return result


# -------- DialBBサーバ関連 -------------------------------------
# DialBBサーバ起動/停止
def exec_dialbb(app_file, button) -> None:
    """DialBBサーバの起動/停止をトグルする。"""
    if PROCESS_STATE.dialbb_proc:
        # DialBBサーバ停止
        PROCESS_STATE.dialbb_proc.stop()
        PROCESS_STATE.dialbb_proc = None
        # ボタン表示切替
        button.config(text=gui_text("btn_dialbb_start"))
    else:
        logger.info("app_file:%s", app_file)
        # サーバ起動
        cmd = os.path.join(DIALBB_DIR, r"server/run_server.py")
        PROCESS_STATE.dialbb_proc = ProcessManager(cmd, [app_file], dialbb=True)
        ret = PROCESS_STATE.dialbb_proc.start()
        if ret:
            # ボタン表示切替
            button.config(text=gui_text("btn_dialbb_stop"))
        else:
            messagebox.showerror("Error", gui_text("msg_dialbb_err_start"))
            PROCESS_STATE.dialbb_proc = None


# Show log
def show_log() -> None:
    """DialBBログファイルを既定アプリで開く。"""
    if PROCESS_STATE.dialbb_proc:
        log_file = PROCESS_STATE.dialbb_proc.get_log_file()
    else:
        log_file = ""

    if log_file:
        logger.info("Opening log file: %s", log_file)
        if os.name == "nt":
            os.startfile(filepath=log_file)
        else:
            subprocess.run(["open", log_file], check=False)
    else:
        messagebox.showwarning("Warning", gui_text("msg_dialbb_warn_no_log"))


# -------- GUI画面制御サブルーチン -------------------------------------
# ファイル設定エリアのフレームを作成して返却する
def set_file_frame(parent_frame, settings, label_text, file_type_list) -> AppFileFrame:
    """アプリファイルの選択/読み込みUIフレームを作成する。"""
    # ラベルの作成
    # file_frame = ttk.Frame(parent_frame, style="My.TLabelframe")
    file_frame = AppFileFrame(parent_frame)
    file_frame.spec_app = tk.Label(file_frame)
    file_frame.spec_app.grid(column=1, columnspan=2, row=0, sticky=tk.W, padx=5)
    # アプリ名の表示エリアを登録して保存アプリ名を表示する
    settings.reg_disp_area(file_frame.spec_app)

    label = tk.Label(file_frame, text=gui_text("main_import"))
    # label.grid(column=0, row=1, padx=0, sticky=tk.E)
    label.grid(column=0, row=1, padx=0, pady=5, sticky=tk.E)

    # テキストボックスの作成
    file_frame.edit_box = tk.Entry(file_frame)
    file_frame.edit_box.grid(column=1, row=1, padx=20, sticky=tk.E + tk.W)
    file_frame.grid_columnconfigure(0, weight=0)
    file_frame.grid_rowconfigure(1, weight=1)

    # select button
    select_button = ttk.Button(
        file_frame,
        text=gui_text("btn_select"),
        command=lambda: set_file_path_command(
            file_frame.edit_box, settings, label_text, file_type_list
        ),
    )
    # select_button.grid(column=2, row=1, padx=5)
    select_button.grid(column=2, row=1, padx=5, pady=5)

    # import button
    import_button = ttk.Button(
        file_frame,
        text=gui_text("btn_load"),
        command=lambda: import_application_file(
            file_frame.edit_box, settings, file_type_list
        ),
    )
    # import_button.grid(column=3, row=1, padx=5)
    import_button.grid(column=3, row=1, padx=5, pady=5)

    file_frame.columnconfigure(1, weight=1)  # Entryを伸縮可能に

    return file_frame


# Excel編集処理
def edit_excel(file_path) -> None:
    """指定したExcelファイルを関連付けアプリで開く。"""
    logger.info("Editing Excel file: %s", file_path)
    # ファイルを関連付けされたアプリで開く
    if os.name == "nt":
        os.startfile(filepath=file_path)
    else:
        subprocess.run(["open", file_path], check=False)


# 開発Debug用
def sample_func() -> None:
    """開発確認用のダミー処理。"""
    # ボタンで起動するサンプル
    messagebox.showinfo("Information", "Not implemented.")


# -------- ボタンクリック対応処理 -------------------------------------
# [close]ボタン：メインウィンドウを閉じる
def close_dialbb_nc(root) -> None:
    """起動中プロセスを停止して no_code GUI を終了する。"""
    logger.info(
        "close_dialbb_nc dialbb_proc: %s editor_process: %s",
        PROCESS_STATE.dialbb_proc,
        PROCESS_STATE.editor_process,
    )
    if PROCESS_STATE.dialbb_proc:
        # dialbbサーバ停止
        PROCESS_STATE.dialbb_proc.stop()
        messagebox.showwarning("Warning", gui_text("msg_warn_forced_process_stop") % "dialbb-server")

    if PROCESS_STATE.editor_process:
        # エディタ用サーバ停止
        PROCESS_STATE.editor_process.stop()
        messagebox.showwarning("Warning", gui_text("msg_warn_forced_process_stop") % "editor-process")

    # 画面を閉じる
    root.quit()


# [cancel]ボタン：自ウィンドウを閉じる
def on_cancel(frame) -> None:
    """サブウィンドウを閉じる。"""
    # 画面を閉じる
    frame.destroy()


# [select]ボタン：アプリファイルの読み込み
def set_file_path_command(edit_box, _settings, title, file_type_list) -> None:
    """ファイル選択ダイアログで選んだパスを入力欄へ反映する。"""
    file_path = filedialog.askopenfilename(title=title, filetypes=file_type_list)
    if file_path:
        # パスをテキストボックスに設定する
        edit_box.delete(0, tk.END)
        edit_box.insert(tk.END, file_path)


def import_application_file(edit_box, settings, _file_type_list) -> None:
    """zip形式のアプリファイルを展開して設定へ反映する。"""
    file_path = edit_box.get()
    if file_path:
        logger.info("%s decompress to %s", file_path, APP_FILE_DIR)
        # zipファイルをシステムエリアに展開する
        with zipfile.ZipFile(file_path) as zf:
            zf.extractall(APP_FILE_DIR)

        # アプリケーション名の保存
        file_name, _ = os.path.splitext(os.path.basename(file_path))
        settings.set_appname(file_name)

        messagebox.showinfo("Import", f"{file_name}" + gui_text("msg_info_appload"))


# [create]ボタンの処理。templateファイルをコピーする。
def create_app_files(parent, settings) -> None:
    """テンプレートから新規アプリファイル一式を作成する。"""
    sub_menu = tk.Toplevel(parent)
    sub_menu.title(gui_text("cre_title"))
    sub_menu.grab_set()  # モーダルにする
    sub_menu.focus_set()  # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)

    # Label Frameを作成
    label_frame = ttk.Labelframe(
        sub_menu, text=gui_text("cre_language"), padding=(10), style="My.TLabelframe"
    )
    label_frame.pack(side="top", padx=5, pady=5)

    # ［英語/日本語］ラジオボタン
    radio_val = tk.StringVar()
    rb1 = ttk.Radiobutton(
        label_frame, text=gui_text("cre_english"), value="en", variable=radio_val
    )
    rb2 = ttk.Radiobutton(
        label_frame, text=gui_text("cre_japanese"), value="ja", variable=radio_val
    )

    # ボタンクリックされた際のイベント
    def btn_click():
        """選択言語のテンプレートをコピーして初期化する。"""
        lang = radio_val.get()
        if not lang:
            messagebox.showerror("Warning", gui_text("msg_cre_nolang"))
            return

        # templateファイルをコピー
        src_dir = os.path.join(NC_PATH, "templates", lang)
        if not os.path.isdir(src_dir):
            messagebox.showerror(
                "Error", gui_text("msg_warn_no_file"), detail=f"{src_dir}"
            )
            return

        # コピー先ディレクトリを作成（無ければ）
        os.makedirs(APP_FILE_DIR, exist_ok=True)

        # src_dir 内を再帰的にコピー（ディレクトリは merge、ファイルは上書き）
        try:
            for name in os.listdir(src_dir):
                s = os.path.join(src_dir, name)
                d = os.path.join(APP_FILE_DIR, name)
                if os.path.isdir(s):
                    # dirs_exist_ok=True 既に存在する場合に上書き
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        except (FileNotFoundError, PermissionError, shutil.Error, OSError) as e:
            messagebox.showerror("Error", gui_text("msg_warn_no_file"), detail=f"{e}")
            return

        messagebox.showinfo(
            "File copy",
            gui_text("msg_info_new_app"),
            detail=f"Language ={lang}",
        )

        # アプリケーション名の保存
        settings.set_appname(f"template_{lang}")

        # 画面を閉じる
        sub_menu.destroy()

    # Button
    ok_btn = ttk.Button(sub_menu, text=gui_text("btn_ok"), command=btn_click)
    can_btn = ttk.Button(
        sub_menu, text=gui_text("btn_cancel"), command=lambda: on_cancel(sub_menu)
    )

    # Layout
    label_frame.pack(side="top", padx=5, pady=5)
    rb1.pack(side="left", padx=5, pady=5)
    rb2.pack(side="left", padx=5, pady=5)
    can_btn.pack(side="right", padx=5, pady=5)
    ok_btn.pack(side="right", padx=5, pady=5)
    # サイズ＆表示位置の指定
    child_position(parent, sub_menu, width=250, height=130)


# [save]ボタンの処理。アプリファイルをzip圧縮して保存する
def export_app_file(file_path, settings):
    """アプリファイル一式をzipとして保存する。"""
    if file_path == "":
        # messagebox.showerror("Warning", "アプリケーションファイルが選択されていません.")
        # return
        base_dir = ""
    else:
        base_dir = os.path.dirname(file_path)

    zip_file = filedialog.asksaveasfilename(
        title=gui_text("msg_appfile_export"),
        initialdir=base_dir,
        filetypes=[("zip file", "*.zip")],
        defaultextension="zip",
    )
    if zip_file:
        logger.info("%s compress to %s", APP_FILES.values(), zip_file)
        # APP_FILE_DIR 配下の全ファイルを再帰的に圧縮する
        with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(APP_FILE_DIR):
                for fn in files:
                    fullpath = os.path.join(root, fn)
                    # zip 内のパスは APP_FILE_DIR を基準とした相対パスにする
                    arcname = os.path.relpath(fullpath, APP_FILE_DIR)
                    zf.write(fullpath, arcname=arcname)

        # アプリケーション名の保存
        file_name, _ = os.path.splitext(os.path.basename(zip_file))
        settings.set_appname(file_name)

        # ファイルタイムスタンプを更新
        app_file_timestamp.update()


# [setting]ボタンの処理。ユーザ情報の設定。
def set_api_keys(parent, settings: SettingData):
    """設定ダイアログを開き、APIキーを保存する。"""
    sub_menu = tk.Toplevel(parent)
    sub_menu.title(gui_text("set_title_api_keys"))
    sub_menu.grab_set()  # モーダルにする
    sub_menu.focus_set()  # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    child_position(parent, sub_menu)

    f1 = tk.Frame(sub_menu)  # Subフレーム生成

    # OPENAI_API_KEY入力エリア
    label1 = tk.Label(f1, text="OPENAI_API_KEY")
    openai_api_key_entry = tk.Entry(f1, width=50)
    label2 = tk.Label(f1, text="GOOGLE_API_KEY")
    google_api_key_entry = tk.Entry(f1, width=50)
    label3 = tk.Label(f1, text="ANTHROPIC_API_KEY")
    anthropic_api_key_entry = tk.Entry(f1, width=50)
    # 横方向のスクロールバーを作成
    horiz_scrollbar1 = tk.Scrollbar(f1, orient=tk.HORIZONTAL, command=openai_api_key_entry.xview)
    openai_api_key_entry.config(xscrollcommand=horiz_scrollbar1.set)
    horiz_scrollbar2 = tk.Scrollbar(f1, orient=tk.HORIZONTAL, command=google_api_key_entry.xview)
    google_api_key_entry.config(xscrollcommand=horiz_scrollbar2.set)
    horiz_scrollbar3 = tk.Scrollbar(f1, orient=tk.HORIZONTAL, command=anthropic_api_key_entry.xview)
    anthropic_api_key_entry.config(xscrollcommand=horiz_scrollbar3.set)

    # configの値を設定
    openai_api_key_entry.insert(0, settings.get_openai_api_key())
    google_api_key_entry.insert(0, settings.get_google_api_key())
    anthropic_api_key_entry.insert(0, settings.get_anthropic_api_key())

    # ボタンクリックされた際のイベント
    def ok_click():
        """設定値を保存してダイアログを閉じる。"""
        # OPENAI_KEYの登録
        key = openai_api_key_entry.get()
        settings.set_openai_api_key(key)
        os.environ["OPENAI_API_KEY"] = key

        key = google_api_key_entry.get()
        settings.set_google_api_key(key)
        os.environ["GOOGLE_API_KEY"] = key

        key = anthropic_api_key_entry.get()
        settings.set_anthropic_api_key(key)
        os.environ["ANTHROPIC_API_KEY"] = key

        messagebox.showinfo("Settings", gui_text("msg_saved"))
        # 画面を閉じる
        sub_menu.destroy()

    # Button
    ok_btn = ttk.Button(sub_menu, text=gui_text("btn_ok"), command=ok_click)
    can_btn = ttk.Button(
        sub_menu, text=gui_text("btn_cancel"), command=lambda: on_cancel(sub_menu)
    )

    # Layout
    label1.grid(column=0, row=0)
    label2.grid(column=0, row=2)
    label3.grid(column=0, row=4)

    openai_api_key_entry.grid(column=1, row=0, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar1.grid(column=1, row=1, sticky=tk.NSEW)
    google_api_key_entry.grid(column=1, row=2, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar2.grid(column=1, row=3, sticky=tk.NSEW)
    anthropic_api_key_entry.grid(column=1, row=4, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar3.grid(column=1, row=5, sticky=tk.NSEW)


    f1.grid_columnconfigure(1, weight=1)
    f1.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
    can_btn.pack(side="right", padx=5, pady=5)
    ok_btn.pack(side="right", padx=5, pady=5)


# 自動テスト実行
def exec_test(sub_menu: tk.Toplevel, chat_area: tk.Text) -> None:
    """シミュレーションテストを実行し、結果をチャット欄へ表示する。"""
    sub_menu.destroy()

    test_config_file = os.path.join(APP_FILE_DIR, APP_FILES["test-config"])
    app_config_file = os.path.join(APP_FILE_DIR, APP_FILES["config"])

    # シミュレーターの起動
    # result = test_by_simulation(test_config_file, app_config_file)
    chat_area.delete("1.0", tk.END)
    for result in test_by_simulation(test_config_file, app_config_file):
        # 対話結果を表示
        chat_area.insert(tk.END, result)
        chat_area.insert(tk.END, "\n")
        chat_area.update_idletasks()
        chat_area.see(tk.END)
    chat_area.insert(tk.END, "----Test complete----\n")


# テスト・サブメニュー
def submenu_test(parent, settings, chat_area: tk.Text) -> None:
    """テスト実行とテスト設定編集のサブメニューを表示する。"""
    # 選択画面を表示
    sub_menu: tk.Toplevel = tk.Toplevel(parent)
    sub_menu.title("Test Menu")
    sub_menu.grab_set()  # モーダルにする
    sub_menu.focus_set()  # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    child_position(parent, sub_menu, width=200, height=120)

    test_config_file = os.path.join(APP_FILE_DIR, APP_FILES["test-config"])

    # ボタンの作成
    btn_conf = ttk.Button(
        sub_menu,
        text=gui_text("btn_configuration"),
        command=lambda: edit_test_config(
            sub_menu,
            test_config_file,
            settings,
        ),
    )
    btn_conf.pack(side=tk.TOP, pady=5)

    btn_gui = ttk.Button(
        sub_menu,
        text=gui_text("btn_execute"),
        command=lambda: exec_test(sub_menu, chat_area),
    )
    btn_gui.pack(side=tk.TOP, pady=5)

    # Cancelボタン
    cancel_btn = ttk.Button(sub_menu, text="終了", command=lambda: on_cancel(sub_menu))
    cancel_btn.pack(side="right", padx=5, pady=5)


# create main frame
# Mainフレームを作成する関数
def set_main_frame(root_frame) -> None:
    """no_code メイン画面のウィジェットを構築する。"""
    # GUIセッティング情報の読み込み
    settings = read_gui_settings(os.path.join(NC_PATH, "settings.dat"))
    dialogue_processor_local: Optional[DialogueProcessor] = None

    # OPENAI_KEY環境変数の設定
    if settings.get_openai_api_key():
        os.environ["OPENAI_API_KEY"] = settings.get_openai_api_key()

    # App file Label 作成
    application_frame = ttk.Labelframe(
        root_frame, text=gui_text("main_title_1"), padding=10
    )

    # ファイル選択エリア作成（ファイルの拡張子を指定）
    file_frame = set_file_frame(
        application_frame,
        settings,
        gui_text("msg_appfile_select"),
        [("zip File", "*.zip")],
    )
    # file_frame.pack(fill=tk.BOTH)
    file_frame.grid(row=0, column=0, columnspan=3, sticky="ew")

    # ---(2025/10)Added Edit frame buttons ---
    edit_frame = ttk.Labelframe(
        application_frame, text=gui_text("main_title_3"), padding=5
    )
    edit_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
    application_frame.rowconfigure(2, weight=1)

    # edit_scenario button
    edit_scenario_btn = ttk.Button(
        edit_frame,
        text=gui_text("btn_scenario_start"),
        command=lambda: exec_editor(
            os.path.join(APP_FILE_DIR, APP_FILES["scenario"]),
            application_frame,
            edit_scenario_btn,
        ),
    )
    edit_scenario_btn.grid(row=0, column=1, padx=5, pady=5)

    # edit_dst_knowledge button
    edit_dst_knowledge_btn = ttk.Button(
        edit_frame,
        text=gui_text("btn_dst_knowledge"),
        command=lambda: edit_excel(
            os.path.join(APP_FILE_DIR, APP_FILES["dst-knowledge"])
        ),
    )
    edit_dst_knowledge_btn.grid(row=0, column=2, padx=5, pady=5)

    # edit_scenario_functions button
    edit_scenario_functions_btn = ttk.Button(
        edit_frame,
        text=gui_text("btn_scenario_func"),
        command=lambda: edit_scenario_functions(
            application_frame,
            os.path.join(APP_FILE_DIR, APP_FILES["scenario-functions"]),
        ),
    )
    edit_scenario_functions_btn.grid(row=0, column=3, padx=5, pady=5)
    # edit_config button
    edit_config_btn = ttk.Button(
        edit_frame,
        text=gui_text("btn_configuration"),
        command=lambda: edit_app_config(
            application_frame,
            os.path.join(APP_FILE_DIR, APP_FILES["config"]),
            TEMPLATE_DIR,
            settings,
        ),
    )
    edit_config_btn.grid(row=0, column=0, padx=5, pady=5)
    edit_frame.columnconfigure((0, 1, 2, 3), weight=1)
    # End of added edit frame buttons

    # createボタン:アプリファイルの新規作成
    create_btn = ttk.Button(
        application_frame,
        text=gui_text("btn_create"),
        command=lambda: create_app_files(application_frame, settings),
    )
    # create_btn.pack(side=tk.LEFT, padx=10, pady=10)
    create_btn.grid(row=1, column=0, padx=5, pady=10)

    # export ボタン:アプリファイルのzip保存
    export_btn = ttk.Button(
        application_frame,
        text=gui_text("btn_export"),
        command=lambda: export_app_file(file_frame.edit_box.get(), settings),
    )
    # export_btn.pack(side=tk.LEFT, padx=10, pady=10)
    export_btn.grid(row=1, column=1, padx=5, pady=10)

    application_frame.columnconfigure(0, weight=1)
    application_frame.columnconfigure(1, weight=1)
    application_frame.columnconfigure(2, weight=1)
    application_frame.pack(fill="x", padx=10, pady=10)

    # DialBB Label 作成
    dialbb_label = ttk.Labelframe(
        root_frame,
        text=gui_text("main_title_2"),
        padding=(10),
        style="My.TLabelframe",
    )

    # settingボタン:ユーザ情報の設定
    setting_btn = ttk.Button(
        dialbb_label,
        text=gui_text("btn_api_keys"),
        command=lambda: set_api_keys(file_frame, settings),
    )
    # setting_btn.pack(side=tk.LEFT, padx=10)
    setting_btn.grid(row=0, column=0, padx=5, pady=5)

    # startボタン:DialBBサーバ起動
    dialbb_btn = ttk.Button(
        dialbb_label,
        text=gui_text("btn_dialbb_start"),
        command=lambda: exec_dialbb(
            os.path.join(APP_FILE_DIR, APP_FILES["config"]), dialbb_btn
        ),
    )
    # start_btn.pack(side=tk.LEFT, padx=10)
    dialbb_btn.grid(row=0, column=2, padx=5, pady=5)

    # show log button
    show_log_btn = ttk.Button(
        dialbb_label, text=gui_text("btn_view_log"), command=show_log
    )
    # show_log_btn.pack(side=tk.LEFT, padx=10)
    show_log_btn.grid(row=0, column=3, padx=5, pady=5)

    dialbb_label.columnconfigure((0, 1, 2, 3, 4), weight=1)
    dialbb_label.pack(fill=tk.BOTH, padx=10, pady=10)

    # フレームの配置
    application_frame.pack(fill=tk.BOTH, padx=10, pady=20)
    dialbb_label.pack(fill=tk.BOTH, padx=10)

    # ---(2025/10)Added area for chat ---
    # TextとScrollbarをまとめるフレームを用意
    chat_frame = ttk.Frame(root_frame)
    chat_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)
    # チャット表示TextArea
    chat_area = tk.Text(
        chat_frame,
        height=16,
        wrap=tk.CHAR,
        state=tk.NORMAL,
        bg="white",
    )
    chat_area.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=5, expand=True)
    # スクロールバー
    scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=chat_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    # TextとScrollbarの連携
    chat_area.config(yscrollcommand=scrollbar.set)

    # auto test button
    test_btn = ttk.Button(
        dialbb_label,
        text=gui_text("btn_test"),
        command=lambda: submenu_test(dialbb_label, settings, chat_area),
    )
    test_btn.grid(row=0, column=4, padx=5, pady=5)

    # ユーザ入力枠
    u_input_frame = tk.Frame(root_frame)
    u_input_frame.pack(pady=(2, 10))
    u_input_label = tk.Label(u_input_frame, text="ユーザ入力:")
    u_input_label.pack(side=tk.LEFT)
    u_input = tk.Entry(u_input_frame, width=60, state=tk.DISABLED)
    u_input.pack(side=tk.LEFT)
    # リターンで送信
    u_input.bind("<Return>", lambda event: send_chat_message(u_input.get()))

    # dialbbメッセージ送信用ユーザIDとセッションID
    user_id = "test_user"
    session_id = ""

    # リクエストデータ作成
    def set_chat_message(
        user_id: str = "", session_id: str = "", user_utterance: str = ""
    ) -> Dict[str, Any]:
        """DialBB送信用のリクエスト辞書を作成する。"""
        data = {
            "user_id": user_id,
            "session_id": session_id,
            "user_utterance": user_utterance,
            "aux_data": {},
        }

        return data

    # レスポンス表示処理
    def display_response(resp: Dict[str, str]) -> str:
        """DialBB応答をチャット欄に表示して session_id を返す。"""
        session_id = resp.get("session_id", "")
        if session_id == "":
            chat_area.insert(tk.END, f"{gui_text('msg_chat_no_sessionid')}\n")
        else:
            output_msg = resp.get("system_utterance", gui_text("msg_chat_no_response"))
            chat_area.insert(tk.END, f"System: {output_msg}\n")
        chat_area.see(tk.END)

        return session_id

    # チャット開始処理
    def start_chat() -> None:
        """チャットセッションを開始して初回応答を表示する。"""
        nonlocal session_id, dialogue_processor_local

        chat_area.delete("1.0", tk.END)
        if u_input["state"] != tk.NORMAL:
            u_input.config(state=tk.NORMAL)
            u_input.focus_set()

        # dialbbをインスタンス化
        config = os.path.join(APP_FILE_DIR, APP_FILES["config"])
        dialogue_processor_local = DialogueProcessor(config)

        # 開始リクエスト送信
        request_json = {"user_id": user_id}
        resp = dialogue_processor_local.process(request_json, initial=True)
        # システムメッセージ表示
        session_id = display_response(resp)

    # ユーザ入力メッセージ送信処理
    def send_chat_message(message: str) -> None:
        """ユーザ発話を送信し、応答をチャット欄へ追記する。"""
        nonlocal session_id

        if message.strip() == "" or not dialogue_processor_local:
            return

        # 入力欄クリア
        u_input.delete(0, tk.END)

        # ユーザメッセージ表示
        chat_area.insert(tk.END, f"User: {message}\n")
        chat_area.update_idletasks()
        chat_area.see(tk.END)

        # DialBBサーバにメッセージを送信する
        # 送信データ設定
        req = set_chat_message(
            user_id=user_id, session_id=session_id, user_utterance=message
        )
        # リクエスト送信
        resp = dialogue_processor_local.process(req)
        # システムメッセージ表示
        session_id = display_response(resp)

    # chatボタン:チャット開始
    chat_btn = ttk.Button(
        dialbb_label,
        text=gui_text("btn_chat_start"),
        command=start_chat,
    )
    chat_btn.grid(row=0, column=1, padx=5, pady=5)

    # closeボタン
    close_btn = ttk.Button(
        root_frame,
        text=gui_text("btn_exit"),
        command=lambda: close_dialbb_nc(root_frame),
    )
    close_btn.pack(side=tk.BOTTOM, anchor=tk.E, padx=10, pady=5)


def main() -> None:
    """no_code GUI を起動してメインループを開始する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "lang",
        choices=["ja", "en"],
        nargs="?",
        default="ja",
        help="Language type: ja/en",
    )
    args = parser.parse_args()

    # GUI表示テキストデータを取得
    read_gui_text_data(lang=args.lang)

    # create root widget
    # Rootウジェットの生成
    root = tk.Tk()
    if os.name == "nt":
        root.minsize(600, 540)  # 最小サイズを設定
    else:
        root.tk.call("tk", "scaling", 1.2)  # スケーリングを1.0に設定
        root.minsize(600, 400)  # 最小サイズを設定
    # root.resizable(True, True)  # サイズ変更を許可

    # set title and icon
    # タイトルとアイコンを設定
    root.title(gui_text("main_title_top") + " " + DialogueProcessor.__version__)
    # photo = os.path.join(NC_PATH, 'img', 'dialbb-icon.png')
    # root.iconphoto(True, tk.PhotoImage(file=photo))

    # ウィンドウサイズと表示位置を指定
    # central_position(root, width=500, height=280)

    # GUIの画面構築
    set_main_frame(root)

    # Ensure DialBB server is stopped when the window is closed
    root.protocol("WM_DELETE_WINDOW", lambda: close_dialbb_nc(root))

    # 画面を表示する
    root.mainloop()


if __name__ == "__main__":
    main()
