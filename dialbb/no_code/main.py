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
import argparse
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import subprocess
import shutil
import zipfile
from dialbb.no_code.tools.knowledgeConverter2json import convert2json
from dialbb.no_code.tools.knowledgeConverter2excel import convert2excel
from dialbb.no_code.config_editor import edit_config
from dialbb.no_code.function_editor import edit_scenario_functions
from dialbb.no_code.gui_utils import (
    read_gui_settings,
    ProcessManager,
    FileTimestamp,
    central_position,
    child_position,
    read_gui_text_data,
    gui_text,
)
from typing import Dict, Optional

# paths  実行環境パス
SCRIPT_ROOT: str = os.path.dirname(os.path.abspath(__file__))
LIB_DIR: str = os.path.abspath(os.path.join(SCRIPT_ROOT, ".."))
NC_PATH: str = SCRIPT_ROOT
APP_FILE_DIR: str = os.path.join(NC_PATH, "app")
TEMPLATE_DIR: str = os.path.join(NC_PATH, "templates")
EDITOR_DIR: str = os.path.join(NC_PATH, "gui_editor")
DATA_DIR: str = os.path.join(NC_PATH, "data")

EDITOR_APL_EXE: str = os.path.join(
    os.environ.get("LOCALAPPDATA"),
    "Programs",
    "DialBB_Scenario_Editor",
    "DialBB_Scenario_Editor.exe",
)
EDITOR_APPDATA_DIR: str = os.path.join(
    os.environ.get("APPDATA"), "dialbb-scenario-editor"
)

# define application files  アプリファイルの定義
APP_FILES: Dict[str, str] = {
    "scenario": "scenario.xlsx",
    "nlu-knowledge": "nlu-knowledge.xlsx",
    "ner-knowledge": "ner-knowledge.xlsx",
    "scenario-functions": "scenario_functions.py",
    "config": "config.yml",
}


# dialbb process information  DialBBサーバのプロセス情報
dialbb_proc: Optional[ProcessManager] = None
dialbb_log_file: str = ""

# application file timestamp アプリファイルのタイムスタンプ
app_file_timestamp: float = FileTimestamp(APP_FILE_DIR, APP_FILES.values())


# -------- GUI Editor -------------------------------------
# Start GUI Editor GUIエディタ起動
def exec_editor(file_path, parent):
    # convert knowledge excel to JSON 知識記述Excel-json変換
    ret = convert_excel_to_json(
        file_path, os.path.join(EDITOR_APPDATA_DIR, "init.json")
    )
    if not ret:
        return

    arg_lang = f"--lang={gui_text('language type')}"
    print(f"exec_Editor os:{os.name} editor dir:{EDITOR_DIR} {arg_lang}")
    # invoke server サーバ起動
    cmd = os.path.join(NC_PATH, r"start_editor.py")
    editor_proc = ProcessManager(cmd, ["--mode=nc", arg_lang])
    ret = editor_proc.start()
    if ret:
        try:
            # シナリオエディタアプリの実行
            if not os.path.exists(EDITOR_APL_EXE):
                raise FileNotFoundError(
                    gui_text("msg_editor_err_notfound") + ": {EDITOR_APL_EXE}"
                )
            # アプリ起動 （言語種別引数あり）
            editor_apl = subprocess.Popen([EDITOR_APL_EXE, arg_lang])

            # waiting for an order to quit   終了の指示待ち
            messagebox.showinfo(
                gui_text("msg_editor_st_title"),
                gui_text("msg_editor_st_msg"),
                detail=gui_text("msg_editor_st_detail"),
                parent=parent,
            )
            # finish editing   終了処理
            json_file = os.path.join(DATA_DIR, "save.json")
            # エディタ保存データをチェック
            if not os.path.isfile(json_file):
                messagebox.showwarning(
                    "Warning",
                    gui_text("msg_warn_no_saved"),
                    detail=gui_text("msg_warn_no_saved_detail"),
                    parent=parent,
                )
            # recheck   WarningでSaveした場合を考慮して再チェックしてから変換
            if os.path.isfile(json_file):
                # convert JSON to Excel   json-知識記述Excel変換
                convert_json_to_excel(json_file, file_path)
                # remove temp file    tempファイル削除
                os.remove(json_file)

            # エディタアプリ停止
            os.system(f"taskkill /F /T /PID {editor_apl.pid}")

        except Exception as e:
            print(f"アプリ起動失敗: {e}")
            messagebox.showerror(
                gui_text("msg_editor_err_title"),
                gui_text("msg_editor_err_msg"),
                detail=f"{e}",
                parent=parent,
            )

        finally:
            # stop server   サーバ停止
            editor_proc.stop()
    else:
        messagebox.showerror(
            gui_text("msg_editor_err_title"),
            gui_text("msg_editor_err_msg"),
            detail=gui_text("msg_editor_err_detail"),
            parent=parent,
        )


# Excel→JSON変換処理
def convert_excel_to_json(xlsx: str, json: str):
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
        convert2json(xlsx, json)
        # messagebox.showinfo("File Convertor", f"{json}を生成しました.")
        result = True

    return result


# JSON→Excel変換処理
def convert_json_to_excel(json: str, xlsx: str) -> None:
    # メッセージを表示する
    if xlsx == "" or json == "":
        messagebox.showerror("Warning", gui_text("msg_convfile_nothing"))
    else:
        convert2excel(json, xlsx)
        messagebox.showinfo(
            "File Convertor", f"{xlsx}" + gui_text("msg_convfile_saved")
        )


# -------- DialBBサーバ関連 -------------------------------------
# DialBBサーバ起動
def exec_dialbb(app_file):
    global dialbb_proc
    global dialbb_log_file

    if dialbb_proc:
        messagebox.showwarning("Warning", gui_text("msg_editor_warn_server_already"))
    else:
        print(f"app_file:{app_file}")
        # サーバ起動
        cmd = os.path.join(LIB_DIR, r"server/run_server.py")
        dialbb_proc = ProcessManager(cmd, [app_file], dialbb=True)
        ret = dialbb_proc.start()
        dialbb_log_file = dialbb_proc.get_log_file()
        if not ret:
            dialbb_proc = None


# DialBBサーバ停止
def stop_dialbb():
    global dialbb_proc

    if dialbb_proc:
        # サーバ停止
        dialbb_proc.stop()
        dialbb_proc = None
    else:
        messagebox.showwarning("Warning", gui_text("msg_editor_warn_server_none"))


# Show log
def show_log():
    global dialbb_log_file

    if dialbb_log_file:
        print(f"Opening log file: {dialbb_log_file}")
        if os.name == "nt":
            os.startfile(filepath=dialbb_log_file)
        else:
            subprocess.run(["open", dialbb_log_file])
    else:
        messagebox.showwarning("Warning", gui_text("msg_editor_warn_no_log"))


# -------- GUI画面制御サブルーチン -------------------------------------
# ファイル設定エリアのフレームを作成して返却する
def set_file_frame(parent_frame, settings, label_text, file_type_list):
    # ラベルの作成
    file_frame = ttk.Frame(parent_frame, style="My.TLabelframe")
    file_frame.spec_app = tk.Label(file_frame)
    file_frame.spec_app.grid(column=0, columnspan=2, row=0, sticky=tk.W, padx=5)
    # アプリ名の表示エリアを登録して保存アプリ名を表示する
    settings.reg_disp_area(file_frame.spec_app)

    label = tk.Label(file_frame, text=gui_text("main_import"))
    label.grid(column=0, row=1, padx=0, sticky=tk.E)

    # テキストボックスの作成
    file_frame.edit_box = tk.Entry(file_frame)
    file_frame.edit_box.grid(column=1, row=1, sticky=tk.NSEW, padx=20)
    file_frame.grid_columnconfigure(0, weight=1)
    file_frame.grid_rowconfigure(1, weight=1)

    # select button
    select_button = ttk.Button(
        file_frame,
        text=gui_text("btn_select"),
        width=7,
        command=lambda: set_file_path_command(
            file_frame.edit_box, settings, label_text, file_type_list
        ),
    )
    select_button.grid(column=2, row=1, padx=5)

    # import button
    import_button = ttk.Button(
        file_frame,
        text=gui_text("btn_load"),
        width=12,
        command=lambda: import_application_file(
            file_frame.edit_box, settings, file_type_list
        ),
    )
    import_button.grid(column=3, row=1, padx=5)

    return file_frame


# Excel編集処理
def edit_excel(file_path):
    print(file_path)
    # ファイルを関連付けされたアプリで開く
    if os.name == "nt":
        os.startfile(filepath=file_path)
    else:
        subprocess.run(["open", file_path])


# 開発Debug用
def sample_func():
    # ボタンで起動するサンプル
    messagebox.showinfo("Information", "Not implemented.")


# -------- ボタンクリック対応処理 -------------------------------------
# [close]ボタン：メインウィンドウを閉じる
def close_dialbb_nc(root):
    global dialbb_proc
    global app_file_timestamp

    if dialbb_proc:
        # dialbbサーバ停止
        dialbb_proc.stop()

    # # アプリファイルの変更チェック
    # if not app_file_timestamp.check():
    #     ret = messagebox.askquestion("File changed", "アプリケーションファイルがエキスポートされていません。",
    #                                  detail="エキスポートせずに終了しますか？",
    #                                  icon='warning')
    #     if ret == 'no':
    #         return

    # 画面を閉じる
    root.quit()


# [cancel]ボタン：自ウィンドウを閉じる
def on_cancel(frame):
    # 画面を閉じる
    frame.destroy()


# [select]ボタン：アプリファイルの読み込み
def set_file_path_command(edit_box, settings, title, file_type_list):
    file_path = filedialog.askopenfilename(title=title, filetypes=file_type_list)
    if file_path:
        # パスをテキストボックスに設定する
        edit_box.delete(0, tk.END)
        edit_box.insert(tk.END, file_path)


def import_application_file(edit_box, settings, file_type_list):
    file_path = edit_box.get()
    if file_path:
        print(f"{file_path} decompress to {APP_FILE_DIR}")
        # zipファイルをシステムエリアに展開する
        with zipfile.ZipFile(file_path) as zf:
            zf.extractall(APP_FILE_DIR)

        # アプリケーション名の保存
        file_name, _ = os.path.splitext(os.path.basename(file_path))
        settings.set_appname(file_name)

        messagebox.showinfo("Import", f"{file_name}" + gui_text("msg_info_appload"))


# [edit]ボタン：編集するファイルを選択
def select_edit_file(parent, settings):
    global APP_FILES

    # 選択画面を表示
    sub_menu = tk.Toplevel(parent)
    sub_menu.title(gui_text("edt_list_title"))
    sub_menu.grab_set()  # モーダルにする
    sub_menu.focus_set()  # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    child_position(parent, sub_menu, width=300, height=250)

    # ボタンの作成
    btn_gui = ttk.Button(
        sub_menu,
        text=gui_text("btn_scenario"),
        width=20,
        command=lambda: [
            exec_editor(os.path.join(APP_FILE_DIR, APP_FILES["scenario"]), sub_menu),
            on_cancel(sub_menu),
        ],
    )
    btn_gui.pack(side=tk.TOP, pady=5)

    # btn_sce = ttk.Button(sub_menu, text="Scenario(Excel)", width=20,
    #                      command=lambda: [edit_excel(os.path.join(
    #                          APP_FILE_DIR, APP_FILES["scenario"])),
    #                          on_cancel(sub_menu)])
    # btn_sce.pack(side=tk.TOP, pady=5)

    btn_nlu = ttk.Button(
        sub_menu,
        text=gui_text("btn_lang_knowledge"),
        width=20,
        command=lambda: [
            edit_excel(os.path.join(APP_FILE_DIR, APP_FILES["nlu-knowledge"])),
            on_cancel(sub_menu),
        ],
    )
    btn_nlu.pack(side=tk.TOP, pady=5)

    btn_ner = ttk.Button(
        sub_menu,
        text=gui_text("btn_named_entity"),
        width=20,
        command=lambda: [
            edit_excel(os.path.join(APP_FILE_DIR, APP_FILES["ner-knowledge"])),
            on_cancel(sub_menu),
        ],
    )
    btn_ner.pack(side=tk.TOP, pady=5)

    btn_conf = ttk.Button(
        sub_menu,
        text=gui_text("btn_scenario_func"),
        width=20,
        command=lambda: edit_scenario_functions(
            sub_menu, os.path.join(APP_FILE_DIR, APP_FILES["scenario-functions"])
        ),
    )
    btn_conf.pack(side=tk.TOP, pady=5)

    btn_conf = ttk.Button(
        sub_menu,
        text=gui_text("btn_configuration"),
        width=20,
        command=lambda: edit_config(
            sub_menu,
            os.path.join(APP_FILE_DIR, APP_FILES["config"]),
            TEMPLATE_DIR,
            settings,
        ),
    )
    btn_conf.pack(side=tk.TOP, pady=5)

    # Cancelボタン
    cancel_btn = ttk.Button(
        sub_menu, text=gui_text("btn_exit"), command=lambda: on_cancel(sub_menu)
    )
    cancel_btn.pack(side="right", padx=5, pady=5)


# [create]ボタンの処理。templateファイルをコピーする。
def create_app_files(parent, settings):
    global APP_FILES

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

    # Button
    ok_btn = ttk.Button(sub_menu, text=gui_text("btn_ok"), command=lambda: btn_click())
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

    # ボタンクリックされた際のイベント
    def btn_click():
        lang = radio_val.get()
        if not lang:
            messagebox.showerror("Warning", gui_text("msg_cre_nolang"))
            return

        # templateファイルをコピー
        for k, v in APP_FILES.items():
            org_file = os.path.join(NC_PATH, "templates", lang, v)
            dist_file = os.path.join(APP_FILE_DIR, v)
            # print(f'Copy {org_file} => {dist_file}')

            # fileコピー
            try:
                shutil.copy2(org_file, dist_file)
            except FileNotFoundError:
                messagebox.showerror(
                    "Error", gui_text("msg_warn_no_file"), detail=f"{org_file}"
                )
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


# [save]ボタンの処理。アプリファイルをzip圧縮して保存する
def export_app_file(file_path, settings):
    global APP_FILES
    global app_file_timestamp

    if file_path == "":
        # messagebox.showerror("Warning", "アプリケーションファイルが選択されていません.")
        # return
        dir = ""
    else:
        dir = os.path.dirname(file_path)

    zip_file = filedialog.asksaveasfilename(
        title=gui_text("msg_appfile_export"),
        initialdir=dir,
        filetypes=[("zip file", "*.zip")],
        defaultextension="zip",
    )
    if zip_file:
        print(f"{APP_FILES.values()} compress to {zip_file}")
        # zipアフィルを圧縮する
        with zipfile.ZipFile(
            zip_file,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zf:
            for fn in APP_FILES.values():
                zf.write(os.path.join(APP_FILE_DIR, fn), arcname=fn)

        # アプリケーション名の保存
        file_name, _ = os.path.splitext(os.path.basename(zip_file))
        settings.set_appname(file_name)

        # ファイルタイムスタンプを更新
        app_file_timestamp.update()


# [setting]ボタンの処理。ユーザ情報の設定。
def setting_json(parent, settings):
    sub_menu = tk.Toplevel(parent)
    sub_menu.title(gui_text("set_title_top"))
    sub_menu.grab_set()  # モーダルにする
    sub_menu.focus_set()  # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    child_position(parent, sub_menu)

    f1 = tk.Frame(sub_menu)  # Subフレーム生成

    # OPENAI_API_KEY入力エリア
    label1 = tk.Label(f1, text="OPENAI_API_KEY")
    api_key = tk.Entry(f1, width=30)
    # 横方向のスクロールバーを作成
    horiz_scrollbar1 = tk.Scrollbar(f1, orient=tk.HORIZONTAL, command=api_key.xview)
    api_key.config(xscrollcommand=horiz_scrollbar1.set)

    # configの値を設定
    api_key.insert(0, settings.get_gptkey())

    # Button
    ok_btn = ttk.Button(sub_menu, text=gui_text("btn_ok"), command=lambda: ok_click())
    can_btn = ttk.Button(
        sub_menu, text=gui_text("btn_cancel"), command=lambda: on_cancel(sub_menu)
    )

    # Layout
    label1.grid(column=0, row=0)
    api_key.grid(column=1, row=0, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar1.grid(column=1, row=1, sticky=tk.NSEW)
    f1.grid_columnconfigure(1, weight=1)
    f1.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
    can_btn.pack(side="right", padx=5, pady=5)
    ok_btn.pack(side="right", padx=5, pady=5)

    # ボタンクリックされた際のイベント
    def ok_click():
        # OPENAI_KEYの登録
        key = api_key.get()
        settings.set_gptkey(key)
        # OPENAI_KEY環境変数をセット
        os.environ["OPENAI_API_KEY"] = key
        messagebox.showinfo("Settings", gui_text("msg_saved"))
        # 画面を閉じる
        sub_menu.destroy()


# create main frame
# Mainフレームを作成する関数
def set_main_frame(root_frame):
    # GUIセッティング情報の読み込み
    settings = read_gui_settings(os.path.join(NC_PATH, "settings.dat"))

    # OPENAI_KEY環境変数の設定
    if settings.get_gptkey():
        os.environ["OPENAI_KEY"] = settings.get_gptkey()

    # App file Label 作成
    application_frame = ttk.Labelframe(
        root_frame, text=gui_text("main_title_1"), padding=(10), style="My.TLabelframe"
    )

    # ファイル選択エリア作成（ファイルの拡張子を指定）
    file_frame = set_file_frame(
        application_frame,
        settings,
        gui_text("msg_appfile_select"),
        [("zip File", "*.zip")],
    )
    file_frame.pack(fill=tk.BOTH)

    # createボタン:アプリファイルの新規作成
    create_btn = ttk.Button(
        application_frame,
        text=gui_text("btn_create"),
        width=10,
        command=lambda: create_app_files(application_frame, settings),
    )
    create_btn.pack(side=tk.LEFT, padx=10, pady=10)

    # editボタンの作成:GUIエディタ起動
    edit_button = ttk.Button(
        application_frame,
        text=gui_text("btn_edit"),
        width=7,
        command=lambda: select_edit_file(file_frame, settings),
    )
    edit_button.pack(side=tk.LEFT, padx=10, pady=10)

    # export ボタン:アプリファイルのzip保存
    export_btn = ttk.Button(
        application_frame,
        text=gui_text("btn_export"),
        width=10,
        command=lambda: export_app_file(file_frame.edit_box.get(), settings),
    )
    export_btn.pack(side=tk.LEFT, padx=10, pady=10)

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
        text=gui_text("btn_setting"),
        width=7,
        command=lambda: setting_json(file_frame, settings),
    )
    setting_btn.pack(side=tk.LEFT, padx=10)

    # startボタン:DialBBサーバ起動
    start_btn = ttk.Button(
        dialbb_label,
        text=gui_text("btn_exec"),
        width=7,
        command=lambda: exec_dialbb(os.path.join(APP_FILE_DIR, APP_FILES["config"])),
    )
    start_btn.pack(side=tk.LEFT, padx=10)

    # stopボタン:DialBBサーバ停止
    stop_btn = ttk.Button(
        dialbb_label, text=gui_text("btn_stop"), width=7, command=stop_dialbb
    )
    stop_btn.pack(side=tk.LEFT, padx=10)

    # show log button
    show_log_btn = ttk.Button(
        dialbb_label, text=gui_text("btn_view_log"), width=10, command=show_log
    )
    show_log_btn.pack(side=tk.LEFT, padx=10)

    # closeボタン
    close_btn = ttk.Button(
        root_frame,
        text=gui_text("btn_exit"),
        width=7,
        command=lambda: close_dialbb_nc(root_frame),
    )
    close_btn.pack(side=tk.BOTTOM, anchor=tk.NE, padx=10, pady=10)

    # フレームの配置
    application_frame.pack(fill=tk.BOTH, padx=10, pady=20)
    dialbb_label.pack(fill=tk.BOTH, padx=10)


def main():
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
    read_gui_text_data(os.path.join(NC_PATH, "gui_nc_text.yml"), args.lang)

    # create root widget
    # Rootウジェットの生成
    root = tk.Tk()
    if os.name != "nt":
        root.tk.call("tk", "scaling", 1.0)  # スケーリングを1.0に設定
        root.minsize(600, 400)  # 最小サイズを設定
    # root.resizable(True, True)  # サイズ変更を許可

    # set title and icon
    # タイトルとアイコンを設定
    root.title(gui_text("main_title_top"))
    # photo = os.path.join(NC_PATH, 'img', 'dialbb-icon.png')
    # root.iconphoto(True, tk.PhotoImage(file=photo))

    # ウィンドウサイズと表示位置を指定
    central_position(root, width=500, height=280)

    # GUIの画面構築
    set_main_frame(root)

    # 画面を表示する
    root.mainloop()


if __name__ == "__main__":
    main()
