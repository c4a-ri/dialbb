#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# editor_main.py
#   dialbb GUI scenario editor main routine.
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import sys
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import subprocess
import webbrowser
import time
import platform
from typing import List
from tools.knowledgeConverter2json import convert2json
from tools.knowledgeConverter2excel import convert2excel

# 実行環境パス
SCRIPT_ROOT = os.path.dirname(os.path.abspath(__file__))
EDITOR_DIR: str = os.path.join(SCRIPT_ROOT, 'gui_editor')
print(f'SCRIPT_ROOT={SCRIPT_ROOT}\nEDITOR_DIR={EDITOR_DIR}')


# -------- プロセス管理クラス -------------------------------------
class Proc_mng:
    def __init__(self, cmd: str, param: List[str] = []) -> None:
        self.cmd = cmd
        self.param = param
        self.pf = platform.system()

    # プロセス起動
    def start(self) -> bool:
        # プロセス起動コマンド
        # ブラウザをアプリケーションモードで起動する
        if self.pf == 'Windows':
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
            messagebox.showerror('ERROR', "サーバ起動に失敗しました.", detail=self.process.stdout)
            return False
        print(f'# Start process pid={self.process.pid}.')
        return True
    
    # プロセス停止
    def stop(self) -> None:
        # サーバ停止
        if self.pf == 'Windows':
            # windows
            os.system(f"taskkill /F /T /PID {self.process.pid}")
        else:
            # Linux
            self.process.terminate()
        self.process.wait()
        print(f'# Terminated process of {self.cmd}.')


# カスタムメッセージダイアログのクラス
class CustomDialog(simpledialog.Dialog):
    def __init__(self, master, title=None, msg='', detail='', btn='OK') -> None:
        self.mater = master     # 親フレーム
        self.msg = msg          # 表示メッセージ
        self.detail = detail    # 表示Detail（省略可）
        self.btn = btn          # ボタンの文字（省略時"OK"）
        super(CustomDialog, self).__init__(parent=master, title=title)

    def body(self, master):
        # メッセージの表示
        self.label = tk.Label(master, text=self.msg)
        self.label.pack(padx=10, pady=5)
        # Detailの表示
        if self.detail:
            self.detail = tk.Label(master, text=self.detail)
            self.detail.pack(padx=10, pady=5)

    def buttonbox(self):
        # ボタンのテキストを指定文字にセット
        self.ok_button = tk.Button(self, text=self.btn, command=self.ok)
        self.ok_button.pack(pady=10, ipadx=10)


# -------- GUIエディタ関連 -------------------------------------
# GUIエディタ起動
def exec_Editor(parent):
    # 知識記述Excel-json変換
    init_json = os.path.join(EDITOR_DIR, 'static', 'data', 'init.json')
    ret = Conv_exl2json(parent.edit_box.get(), init_json)
    if not ret:
        return
    
    print(f"exec_Editor os:{os.name} editor dir:{EDITOR_DIR}")
    # サーバ起動
    cmd = os.path.join(SCRIPT_ROOT, 'start_editor.py')
    editor_proc = Proc_mng(cmd)
    ret = editor_proc.start()
    if ret:
        # ブラウザ起動
        try:
            time.sleep(2)
            # webbrowser.open('http://localhost:5000/', new=1, autoraise=True)
            pf = platform.system()
            # ブラウザをアプリケーションモードで起動する
            if pf == 'Windows':
                subprocess.Popen(["start", "chrome", "--app=http://localhost:5000/"], shell=True)
            elif pf == 'Darwin':
                # Mac OSX
                subprocess.Popen(["open", "-a", "'Google Chrome'", "--args",
                                  "'--app=http://localhost:5000/'"], shell=True)
        except Exception:
            pass

        # 終了の指示待ち
        # messagebox.showinfo("DialBB GUI Scenario Editor", msg, detail='http://localhost:5000/にアクセス！\n終了する時はOKボタンを押してください.')
        CustomDialog(parent, title='DialBB GUI Scenario Editor', btn='Stop',
                     msg='DialBB GUI Scenario Editor is running...',
                     detail='Please access http://localhost:5000/\nPress "Stop" to stop the server.')

        # 終了処理
        save_json = os.path.join(EDITOR_DIR, 'static', 'data', 'save.json')
        if not os.path.isfile(save_json):
            # messagebox.showwarning('Warning', 'サーバを終了すると保存機能は使えません、よろしいでしょうか？',
            #                        detail='必要な場合はエディタの[Save]ボタンでセーブしてから[OK]を押してください.')
            messagebox.showwarning('Warning', 'Scenario will not be saved if you stop the server. Do you want to continue?',
                                   detail='To save the scenario, press "Save" on the editor and then press "Stop".')
        # WarningでSaveした場合を考慮して再チェック
        if os.path.isfile(save_json):
            # json-知識記述Excel変換
            # Conv_json2exl(save_json, file_path)
            # Tempファイル削除
            os.remove(save_json)

        # サーバ停止
        editor_proc.stop()


# Excel→JSON変換処理
def Conv_exl2json(xlsx, json):
    result = False

    if json:
        # フォルダが無ければ作成
        folder_path = os.path.dirname(json)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    # 変換処理起動
    convert2json(xlsx, json)
    result = True
    
    return result


# JSON→Excel変換処理
def Conv_json2exl(json, xlsx):
    # メッセージを表示する
    if xlsx == "" or json == "":
        messagebox.showerror("Warning", "ファイルが指定されていません.")
    else:
        # 変換処理起動
        convert2excel(json, xlsx)
        # messagebox.showinfo("File Convertor", f"{xlsx}を生成しました.")


# -------- GUI画面制御サブルーチン -------------------------------------
# ウィンドウのサイズと中央表示の設定
def central_position(frame, width: int, height: int):
    # スクリーンの縦横サイズを取得する
    sw=frame.winfo_screenwidth()
    sh=frame.winfo_screenheight()
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


# ファイル設定エリアのフレームを作成して返却する
def set_file_frame(parent_frame, label_text, file_type_list):
    # ラベルの作成
    file_frame = ttk.Frame(parent_frame, style='My.TLabelframe')
    file_frame.spec_app = tk.Label(file_frame, text=label_text)
    file_frame.spec_app.grid(column=0, row=0, sticky=tk.NSEW, padx=5)
    
    # テキストボックスの作成
    file_frame.edit_box = tk.Entry(file_frame)
    file_frame.edit_box.grid(column=0, row=1, sticky=tk.NSEW, padx=5)
    file_frame.grid_columnconfigure(0, weight=1)
    file_frame.grid_rowconfigure(1, weight=1)
    
    # selectボタンの作成
    file_button = tk.Button(file_frame, text='select', width=5,
                            command=lambda: open_file_command(file_frame.edit_box,
                                                              file_type_list))
    file_button.grid(column=1, row=1, padx=5)
    
    # editボタンの作成:GUIエディタ起動
    btnEditor = tk.Button(file_frame, text="edit", width=5,
                          command=lambda: exec_Editor(file_frame))
    btnEditor.grid(column=2, row=1, padx=5)

    return file_frame


# -------- ボタンクリック対応処理 -------------------------------------
# [close]ボタン：メインウィンドウを閉じる
def App_Close(root):
    global dialbb_proc
    global appfile_TS

    # 画面を閉じる
    root.quit()


# [cancel]ボタン：自ウィンドウを閉じる
def on_cancel(frame):
    # 画面を閉じる
    frame.destroy()


# [select]ボタン：アプリファイルの読み込み
def open_file_command(edit_box, file_type_list):
    file_path = filedialog.askopenfilename(filetypes=file_type_list)
    if file_path:
        # パスをテキストボックスに設定する
        edit_box.delete(0, tk.END)
        edit_box.insert(tk.END, file_path)


# Mainフレームを作成する関数
def set_main_frame(root_frame):
    # ファイル選択エリア作成（ファイルの拡張子を指定）
    file_frame = set_file_frame(root_frame, "Scenario file",
                                [('Excelファイル', '*.xlsx')])
    file_frame.pack(fill=tk.BOTH)

    # closeボタン
    close_btn = tk.Button(root_frame, text="close", width=5,
                          command=lambda: App_Close(root_frame))
    close_btn.pack(side=tk.BOTTOM, anchor=tk.NE, padx=10, pady=10)


def main():
    # Rootウジェットの生成
    root = tk.Tk()

    # タイトルとアイコンを設定
    root.title("DialBB GUI Scenario Editor")
    # photo = os.path.join(EDITOR_DIR, 'img', 'dialbb-icon.png')
    # root.iconphoto(True, tk.PhotoImage(file=photo))

    # ウィンドウサイズと表示位置を指定
    central_position(root, 400, 120)
    
    # GUIの画面構築
    set_main_frame(root)

    # 画面を表示する
    root.mainloop()


if __name__ == '__main__':
    main()
