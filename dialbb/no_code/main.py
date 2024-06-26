#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# main.py
#   dialbb no_code GUI main program
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import subprocess
import webbrowser
import shutil
import zipfile
from dialbb.no_code.tools.knowledgeConverter2json import convert2json
from dialbb.no_code.tools.knowledgeConverter2excel import convert2excel
from dialbb.no_code.config_editor import edit_config
from dialbb.no_code.gui_utils import gui_settings, ProcessManager, FileTimestamp, central_position, chaild_position
from typing import Dict, Any, List

# paths  実行環境パス
SCRIPT_ROOT: str = os.path.dirname(os.path.abspath(__file__))
LIB_DIR: str = os.path.abspath(os.path.join(SCRIPT_ROOT, '..'))
NC_PATH: str = SCRIPT_ROOT
APP_FILE_DIR: str = os.path.join(NC_PATH, 'app')
EDITOR_DIR: str = os.path.join(NC_PATH, 'gui_editor')
#print(f'SCRIPT_ROOT={SCRIPT_ROOT}\nNC_PATH={NC_PATH}\nLIB_DIR={LIB_DIR}\nAPP_FILE_DIR={APP_FILE_DIR}\nEDITOR_DIR={EDITOR_DIR}')

# define application files  アプリファイルの定義
APP_FILES: Dict[str, str] = {
    "scenario": "scenario.xlsx",
    "knowledge": "nlu-knowledge.xlsx",
    "config": "config.yml"
}

# dialbb process information  DialBBサーバのプロセス情報
dialbb_proc: bool = None

# application file timestamp アプリファイルのタイムスタンプ
app_file_timestamp: float = FileTimestamp(APP_FILE_DIR, APP_FILES.values())


# -------- GUI Editor -------------------------------------
# Start GUI Editor GUIエディタ起動
def exec_editor(file_path):
    # convert knowledge excel to JSON 知識記述Excel-json変換
    ret = convert_excel_to_json(file_path, f'{EDITOR_DIR}/static/data/init.json')
    if not ret:
        return
    
    print(f"exec_Editor os:{os.name} editor dir:{EDITOR_DIR}")
    # invoke server サーバ起動
    cmd = os.path.join(NC_PATH, r'start_editor.py')
    editor_proc = ProcessManager(cmd)
    ret = editor_proc.start()
    if ret:
        # invoke browser ブラウザ起動
        import time
        time.sleep(2)
        # webbrowser.open('http://localhost:5000/', new=1, autoraise=True)
        subprocess.Popen(["start", "msedge", "--app=http://localhost:5000/"], shell=True)

        # waiting for an order to quit   終了の指示待ち
        msg = 'Running GUI Editor...'
        messagebox.showinfo("GUI Editor", msg, detail='Access http://localhost:5000/\n Press OK to quit.')

        # finish editing   終了処理
        json_file = f'{EDITOR_DIR}/static/data/save.json'
        if not os.path.isfile(json_file):
            messagebox.showwarning('Warning', 'Scenario is not saved.',
                                   detail='Press [Save] button on the browser and then press [OK].')
        # recheck   WarningでSaveした場合を考慮して再チェック
        if os.path.isfile(json_file):
            # convert JSON to Excel   json-知識記述Excel変換
            convert_json_to_excel(json_file, file_path)
            # remove temp file    tempファイル削除
            os.remove(json_file)

        # stop server   サーバ停止
        editor_proc.stop()


#Excel→JSON変換処理
def convert_excel_to_json(xlsx: str, json: str):
    """
    Convert Excel to JSON

    :param xlsx:
    :param json:
    """
    result = False
    # メッセージを表示する
    if xlsx == "" or json == "":
        messagebox.showerror("Warning", "Excel file or Json file is not specified.")
    else:
        convert2json(xlsx, json)
        # messagebox.showinfo("File Convertor", f"{json}を生成しました.")
        result = True
    
    return result


# JSON→Excel変換処理
def convert_json_to_excel(json: str, xlsx: str) -> None:
    # メッセージを表示する
    if xlsx == "" or json == "":
        messagebox.showerror("Warning", "Excel file or Json file is not specified.")
    else:
        convert2excel(json, xlsx)
        messagebox.showinfo("File Convertor", f"Excel file {xlsx} created.")


# -------- DialBBサーバ関連 -------------------------------------
# DialBBサーバ起動
def exec_dialbb(app_file):
    global dialbb_proc

    if dialbb_proc:
        messagebox.showwarning('Warning', 'The DialBB server is already running.')
    else:
        print(f"app_file:{app_file}")
        # サーバ起動
        cmd = os.path.join(LIB_DIR, r'server/run_server.py')
        dialbb_proc = ProcessManager(cmd, [app_file])
        ret = dialbb_proc.start()
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
        messagebox.showwarning('Warning', 'The DialBB server is not running.')


# -------- GUI画面制御サブルーチン -------------------------------------
# ファイル設定エリアのフレームを作成して返却する
def set_file_frame(parent_frame, settings, label_text, file_type_list):
    # ラベルの作成
    file_frame = ttk.Frame(parent_frame, style='My.TLabelframe')
    file_frame.spec_app = tk.Label(file_frame, text=label_text)
    file_frame.spec_app.grid(column=0, row=0, sticky=tk.NSEW, padx=5)
    # アプリ名の表示エリアを登録して保存アプリ名を表示する
    settings.reg_disp_aria(file_frame.spec_app)
    
    # テキストボックスの作成
    file_frame.edit_box = tk.Entry(file_frame)
    file_frame.edit_box.grid(column=0, row=1, sticky=tk.NSEW, padx=5)
    file_frame.grid_columnconfigure(0, weight=1)
    file_frame.grid_rowconfigure(1, weight=1)
    
    # selectボタンの作成
    file_button = tk.Button(file_frame, text='select', width=5,
                            command=lambda: open_file_command(file_frame.edit_box,
                                                              settings,
                                                              file_type_list))
    file_button.grid(column=1, row=1, padx=5)
    
    # editボタンの作成:GUIエディタ起動
    btnEditor = tk.Button(file_frame, text="edit",
                          width=5, command=lambda: select_edit_file(file_frame))
    btnEditor.grid(column=2, row=1, padx=5)

    return file_frame


# Scenario編集の処理選択
def edit_scenario(parent, file_path):
    print(f'edit_scenario :{file_path}')
    # 編集方法の選択画面を作成
    sub_menu = tk.Toplevel(parent)    # Subフレーム生成
    sub_menu.title("Edit Scenario")
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.resizable(0, 0)
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    chaild_position(parent, sub_menu, width=250, height=100)

    # GUI画面構築
    f1 = tk.Frame(sub_menu)    # Subフレーム生成

    # Excel編集ボタンの作成
    excel_btn = ttk.Button(f1, text="Edit Excel File",
                           command=lambda: [edit_excel(file_path),
                                            on_cancel(sub_menu)])
    # GUIエディタ編集ボタンの作成
    editor_btn = ttk.Button(f1, text="Start GUI Editor",
                            command=lambda: [exec_editor(file_path),
                                             on_cancel(sub_menu)])
    # Cancelボタンの作成
    cancel_btn = ttk.Button(sub_menu, text="cancel", command=lambda: on_cancel(sub_menu))

    # 配置
    excel_btn.pack(side=tk.LEFT, padx=5)
    editor_btn.pack(side=tk.LEFT, padx=5)
    f1.pack(pady=20)
    cancel_btn.pack(side="bottom", padx=5, pady=5)


# Excel編集処理
def edit_excel(file_path):
    print(file_path)
    # ファイルを関連付けされたアプリで開く
    os.startfile(filepath=file_path)


# 開発Debug用
def sample_func():
    # ボタンで起動するサンプル
    messagebox.showinfo("Infomation", "Not implemented.")


# -------- ボタンクリック対応処理 -------------------------------------
# [close]ボタン：メインウィンドウを閉じる
def App_Close(root):
    global dialbb_proc
    global app_file_timestamp
    
    if dialbb_proc:
        # dialbbサーバ停止
        dialbb_proc.stop()

    # アプリファイルの変更チェック
    if not app_file_timestamp.check():
        ret = messagebox.askquestion("File changed", "Appliation file has not been saved!",
                                     detail="Exit without saving?", icon='warning')
        if ret == 'no':
            return

    # 画面を閉じる
    root.quit()


# [cancel]ボタン：自ウィンドウを閉じる
def on_cancel(frame):
    # 画面を閉じる
    frame.destroy()


# [select]ボタン：アプリファイルの読み込み
def open_file_command(edit_box, settings, file_type_list):
    file_path = filedialog.askopenfilename(filetypes=file_type_list)
    if file_path:
        # パスをテキストボックスに設定する
        edit_box.delete(0, tk.END)
        edit_box.insert(tk.END, file_path)
        
        print(f'{file_path} decompress to {APP_FILE_DIR}')
        # zipアフィルをシステムエリアに展開する
        with zipfile.ZipFile(file_path) as zf:
            zf.extractall(APP_FILE_DIR)

        # アプリケーション名の保存
        file_name, _ = os.path.splitext(os.path.basename(file_path))
        settings.set_appname(file_name)


# [edit]ボタン：編集するファイルを選択
def select_edit_file(parent):
    # dir = parent.edit_box.get()
    # if dir == '':
    #     messagebox.showerror("Warning", "アプリケーションファイルが選択されていません.")
    #     return

    # 選択画面を表示
    sub_menu = tk.Toplevel(parent)
    sub_menu.title("Select file")
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    chaild_position(parent, sub_menu, width=300, height=200)
    
    # Label Frameを作成
    label_frame = ttk.Labelframe(sub_menu, text='Application file', padding=(10),
                                 style='My.TLabelframe')
    label_frame.pack(side="top", padx=5, pady=5)

    # ラジオボタンの作成
    options = [
        ("Scenario", "scenario"),
        ("NLU knowledge", "knowledge"),
        ("Config", "config")
    ]
    selected = tk.StringVar()
    for text, value in options:
        ttk.Radiobutton(label_frame, text=text, value=value,
                        variable=selected).pack(anchor="w", padx=5, pady=2)

    # OKボタンとCancelボタンの作成
    ok_btn = ttk.Button(sub_menu, text="edit",
                           command=lambda: on_selected(selected.get()))
    cancel_btn = ttk.Button(sub_menu, text="close", command=lambda: on_cancel(sub_menu))
    cancel_btn.pack(side="right", padx=5, pady=5)
    ok_btn.pack(side="right", padx=5, pady=5)


    # 各ファイル編集処理の振り分け
    def on_selected(selected):
        global APP_FILES

        if not selected:
             messagebox.showerror("Warning", "Not selected.")
             return

        file_path = os.path.join(APP_FILE_DIR, APP_FILES[selected])
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", "File does not exist.",
                                detail=f'{file_path}')
            return
        
        # 選択ファイルの編集処理を起動
        if selected == 'scenario':
            # シナリオファイル
            edit_scenario(sub_menu, file_path)
        elif selected == 'knowledge':
            # 言語理解知識ファイル
            edit_excel(file_path)
        elif selected == 'config':
            # Configファイル
            edit_config(sub_menu, file_path)
        else:
            messagebox.showerror("Warning", "File is not selected.")


# [create]ボタンの処理。templateファイルをコピーする。
def create_app_files(parent, settings):
    global APP_FILES

    sub_menu = tk.Toplevel(parent)
    sub_menu.title("Select language")
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)

    # Label Frameを作成
    label_frame = ttk.Labelframe(sub_menu, text='Languege', padding=(10),
        style='My.TLabelframe')
    label_frame.pack(side="top", padx=5, pady=5)
    
    # ［英語/日本語］ラジオボタン
    radio_val = tk.StringVar()
    rb1 = ttk.Radiobutton(label_frame, text='English', value='en',
        variable=radio_val)
    rb2 = ttk.Radiobutton(label_frame, text='Japanese', value='ja',
        variable=radio_val)

    # Button
    button1 = ttk.Button(sub_menu, text='OK', padding=(20, 5),
        command=lambda : btn_click())

    # Layout
    label_frame.pack(side="top", padx=5, pady=5)
    rb1.pack(side="left", padx=5, pady=5)
    rb2.pack(side="left", padx=5, pady=5)
    button1.pack(side="bottom", padx=5, pady=5)
    # サイズ＆表示位置の指定
    chaild_position(parent, sub_menu, width=250, height=130)

    # ボタンクリックされた際のイベント
    def btn_click():
        lang = radio_val.get()
        if not lang:
             messagebox.showerror("Warning", "Language is not specified.")
             return

        # templateファイルをコピー
        for k, v in APP_FILES.items():
            org_file = os.path.join(NC_PATH, 'templates', lang, v)
            dist_file = os.path.join(APP_FILE_DIR, v)
            # print(f'Copy {org_file} => {dist_file}')

            # fileコピー
            try:
                shutil.copy2(org_file, dist_file)
            except FileNotFoundError:
                messagebox.showerror("Error", "File does not exist.",
                                     detail=f'{org_file}')
                return
        
        messagebox.showinfo("File copy", 'Application files created.',
                            detail=f'Lang = [{lang}]')
        
        # アプリケーション名の保存
        settings.set_appname(f'template_{lang}')

        # 画面を閉じる
        sub_menu.destroy()


# [save]ボタンの処理。アプリファイルをzip圧縮して保存する
def save_appfile(file_path, settings):
    global APP_FILES
    global app_file_timestamp

    if file_path == '':
        # messagebox.showerror("Warning", "アプリケーションファイルが選択されていません.")
        # return
        dir = ''
    else:
        dir = os.path.dirname(file_path)

    zip_file = filedialog.asksaveasfilename(title='Save App files',
                                            initialdir=dir,
                                            filetypes=[('zip file', '*.zip')],
                                            defaultextension='zip')
    if zip_file:
        print(f'{APP_FILES.values()} compress to {zip_file}')
        # zipアフィルを圧縮する
        with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED,) as zf:
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
    sub_menu.title("Settings")
    sub_menu.grab_set()        # モーダルにする
    sub_menu.focus_set()       # フォーカスを新しいウィンドウをへ移す
    sub_menu.transient(parent)
    # サイズ＆表示位置の指定
    chaild_position(parent, sub_menu)

    f1 = tk.Frame(sub_menu)    # Subフレーム生成

    # OPENAI_API_KEY入力エリア
    label1 = tk.Label(f1, text='OPENAI_API_KEY')
    api_key = tk.Entry(f1, width=30)
    # 横方向のスクロールバーを作成
    horiz_scrollbar1 = tk.Scrollbar(f1, orient=tk.HORIZONTAL,
                                    command=api_key.xview)
    api_key.config(xscrollcommand=horiz_scrollbar1.set)
    
    # configの値を設定
    api_key.insert(0, settings.get_gptkey())

    # Button
    ok_btn = ttk.Button(sub_menu, text='OK', command=lambda : ok_click())
    can_btn = ttk.Button(sub_menu, text="cancel", command=lambda: on_cancel(sub_menu))

    # Layout
    label1.grid(column=0, row=0)
    api_key.grid(column=1, row=0, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar1.grid(column=1, row=1, sticky=tk.NSEW)
    f1.grid_columnconfigure(1, weight=1)
    f1.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
    can_btn.pack(side="right", padx=5, pady=5)
    ok_btn.pack(side="right", padx=5, pady=5)


    #ボタンクリックされた際のイベント
    def ok_click():
        # OPENAI_KEYの登録
        key = api_key.get()
        settings.set_gptkey(key)
        # OPENAI_KEY環境変数をセット
        os.environ["OPENAI_KEY"] = key
        messagebox.showinfo("Settings", 'Saved.')
        # 画面を閉じる
        sub_menu.destroy()


# Mainフレームを作成する関数
def set_main_frame(root_frame):
    # GUIセッティング情報の読み込み
    settings = gui_settings(os.path.join(NC_PATH, 'settings.json'))
    # OPENAI_KEY環境変数の設定
    if settings.get_gptkey():
        os.environ["OPENAI_KEY"] = settings.get_gptkey()

    # App file Label 作成
    appfile_label = ttk.Labelframe(root_frame, text='Application file',
                                   padding=(10), style='My.TLabelframe')

    # ファイル選択エリア作成（ファイルの拡張子を指定）
    file_frame = set_file_frame(appfile_label, settings, "Specify application:",
                                [('zipファイル', '*.zip')])
    file_frame.pack(fill=tk.BOTH)

    # createボタン:アプリファイルの新規作成
    create_btn = tk.Button(appfile_label, text="create",
        width=5, command=lambda: create_app_files(appfile_label,
                                                  settings))
    create_btn.pack(side=tk.LEFT, padx=10, pady=10)

    # saveボタン:アプリファイルのzip保存
    save_btn = tk.Button(appfile_label, text="save", width=5,
         command=lambda: save_appfile(file_frame.edit_box.get(), settings))
    save_btn.pack(side=tk.LEFT, padx=10, pady=10)

    # settingボタン:ユーザ情報の設定
    setting_btn = tk.Button(appfile_label, text="setting",
        width=5, command=lambda: setting_json(file_frame, settings))
    setting_btn.pack(side=tk.LEFT, padx=10, pady=10)

    # DialBB Label 作成
    dialbb_label = ttk.Labelframe(root_frame,
        text='DialBB sever', padding=(10), style='My.TLabelframe')
    
    # startボタン:DialBBサーバ起動
    start_btn = tk.Button(dialbb_label, text="start",
        # width=5, command=lambda:exec_dialbb(os.path.join(DIALBB_DIR,
        #                                                  'sample_apps/chatgpt/config_ja.yml')))
        width=5, command=lambda:exec_dialbb(os.path.join(APP_FILE_DIR,
                                                         APP_FILES['config'])))
    start_btn.pack(side=tk.LEFT, padx=10)

    # stopボタン:DialBBサーバ停止
    stop_btn = tk.Button(dialbb_label, text="stop",
        width=5, command=stop_dialbb)
    stop_btn.pack(side=tk.LEFT, padx=10)

    # closeボタン
    close_btn = tk.Button(root_frame, text="close", width=5,
                          command=lambda:App_Close(root_frame))
    close_btn.pack(side=tk.BOTTOM, anchor=tk.NE, padx=10, pady=10)

    # フレームの配置
    appfile_label.pack(fill=tk.BOTH, padx=10, pady=20)
    dialbb_label.pack(fill=tk.BOTH, padx=10)


def main():
    # Rootウジェットの生成
    root = tk.Tk()

    # タイトルとアイコンを設定
    root.title("DialBB Manager")
    # photo = os.path.join(NC_PATH, 'img', 'dialbb-icon.png')
    # root.iconphoto(True, tk.PhotoImage(file=photo))

    # ウィンドウサイズと表示位置を指定
    central_position(root, width=400, height=280)
    
    # GUIの画面構築
    set_main_frame(root)

    # 画面を表示する
    root.mainloop()


if __name__ == '__main__':
    main()
