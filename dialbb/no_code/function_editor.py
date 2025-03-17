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
# editor_main.py
#   dialbb GUI scenario editor main routine.
#
# function_editor.py
#   GUI for editing scenario functions
#
__version__ = '0.1'
__author__ = 'Mikio Nakano'

import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import ruamel.yaml
from typing import Any, Dict, List

from dialbb.no_code.gui_utils import child_position


# manages function definitions
class FunctionManager:

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        with open(self.file_path, encoding='utf-8') as fp:
            self.scenario_functions: str = fp.read()

    def get_scenario_functions(self) -> str:
        return self.scenario_functions

    def set_sceario_functions(self, function_definitions: str) -> None:
        self.scenario_functions = function_definitions

    # save to scenario_functions.py
    def save(self) -> None:
        with open(self.file_path, mode='w', encoding='utf-8') as fp:
            print(self.scenario_functions, file=fp)


def edit_scenario_functions(parent, file_path: str):

    manager = FunctionManager(file_path)

    toplevel = tk.Toplevel(parent)
    toplevel.title('Scenario Functions')
    toplevel.grab_set()        # モーダルにする
    toplevel.focus_set()       # フォーカスを新しいウィンドウをへ移す
    toplevel.transient(parent)
    # サイズ＆表示位置の指定
    parent_x = parent.winfo_rootx() + parent.winfo_width() // 4 - toplevel.winfo_width() // 2
    parent_y = parent.winfo_rooty() + parent.winfo_height() // 10 - toplevel.winfo_height() // 2
    toplevel.geometry(f"600x600+{parent_x}+{parent_y}")

    # scenario_functions frame
    # scenario_functions_frame = ttk.Labelframe(sub_menu, text='Scenario Functions', padding=(10),
    #                                           style='My.TLabelframe')
    # scenario_functions_frame.pack(expand=True, fill=tk.Y, padx=5, pady=5)

    label = tk.Label(toplevel, text='Scenario Functions')
    textarea = scrolledtext.ScrolledText(toplevel, wrap=tk.NONE, width=80, height=30)
    # 横方向のスクロールバーを作成
    horiz_scrollbar1 = tk.Scrollbar(toplevel, orient=tk.HORIZONTAL,
                                    command=textarea.xview)
    textarea.config(xscrollcommand=horiz_scrollbar1.set)
    # configの値を設定
    textarea.insert(0., manager.get_scenario_functions())
    label.grid(column=1, row=1)
    textarea.grid(column=1, row=2, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
    horiz_scrollbar1.grid(column=1, row=3, columnspan=2, sticky=tk.NSEW)

    # OKボタン
    ok_btn = ttk.Button(toplevel, text='OK', command=lambda: ok_btn_click())
    # Cancelボタン
    cancel_btn = ttk.Button(toplevel, text='Cancel',
                            command=lambda: cancel_btn_click())

    # ウィンドウが表示された後に実行される処理を設定
    # toplevel.bind('<Map>', lambda event: on_window_shown())

    # Layout
    ok_btn.grid(column=1, row=4, padx=5, pady=5, sticky=tk.E)
    cancel_btn.grid(column=2, row=4, padx=5, pady=5, sticky=tk.E)

    #central_position(sub_menu, width=250, height=130)  # サイズ＆表示位置の指定

    def ok_btn_click():

        scenario_functions: str = textarea.get(1.0, tk.END)
        manager.set_sceario_functions(scenario_functions)
        manager.save()

        # 画面を閉じる
        toplevel.destroy()
        parent.destroy()

    def cancel_btn_click():
        # 画面を閉じる
        toplevel.destroy()
        parent.destroy()


